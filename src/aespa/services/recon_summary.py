from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    CrawledPage,
    Credential,
    PageCredentialView,
    PageOwaspTest,
    TargetIntelItem,
    TestRun,
    TrafficEntry,
)
from aespa.services.llm import OWASP_WEB_CATEGORIES, OWASP_WEB_LABELS

_ID_SEGMENT_RE = re.compile(r"^(?:\d+|[0-9a-f]{8}-[0-9a-f-]{27,})$", re.IGNORECASE)
_STATIC_ASSET_RE = re.compile(
    r"\.(?:js|css|png|jpe?g|gif|svg|ico|woff2?|ttf|eot|map)(?:$|[?#])",
    re.IGNORECASE,
)
_STATUS_ORDER = {
    "not_started": 0,
    "in_progress": 1,
    "covered": 2,
    "skipped": 2,
    "finding": 3,
}

_A03_INPUT_TEST_CLASSES = ("sqli", "reflected_xss", "stored_xss")


def build_recon_summary(
    run_id: int,
    session: Session | None = None,
    *,
    persist: bool = True,
) -> dict:
    """Build an evidence-backed, live attack-surface and coverage projection.

    The projection is intentionally descriptive. It does not invent risk scores or
    act as a second scan plan: the workprogram remains the source of truth for scan
    progress, while this summary makes its relationship to discovered routes visible.
    """
    own_session = session is None
    s = session or Session(get_engine())
    try:
        run = s.get(TestRun, run_id)
        pages = list(
            s.exec(
                select(CrawledPage)
                .where(CrawledPage.test_run_id == run_id)
                .where(CrawledPage.in_scope != False)  # noqa: E712
                .order_by(CrawledPage.depth, CrawledPage.url)
            )
        )
        intel_items = list(
            s.exec(
                select(TargetIntelItem)
                .where(TargetIntelItem.test_run_id == run_id)
                .order_by(TargetIntelItem.discovered_at.desc())
            )
        )
        views = list(
            s.exec(
                select(PageCredentialView).where(
                    PageCredentialView.test_run_id == run_id
                )
            )
        )
        cells = list(
            s.exec(select(PageOwaspTest).where(PageOwaspTest.test_run_id == run_id))
        )

        credentials: list[Credential] = []
        if run is not None:
            credentials = list(
                s.exec(select(Credential).where(Credential.site_id == run.site_id))
            )
        credential_map = {credential.id: credential for credential in credentials}

        page_access, access_profiles = _build_page_access(pages, views, credential_map)
        routes = _build_routes(pages, intel_items, page_access, credential_map)
        coverage = _build_coverage(cells, pages, routes)
        signals = _build_signals(pages, intel_items)
        technologies = _detect_technologies(s, run_id, pages, intel_items)

        access_counts = Counter(route["access"]["classification"] for route in routes)
        summary = {
            "schema_version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "route_count": len(routes),
            "routes": routes,
            "input_surface": {
                "routes": sum(bool(route["parameters"]) for route in routes),
                "parameters": len(
                    {
                        (route["canonical_url"], parameter)
                        for route in routes
                        for parameter in route["parameters"]
                    }
                ),
                "forms": sum("form" in route["kinds"] for route in routes),
                "observed_api_routes": sum(
                    "api_observation" in route["sources"] for route in routes
                ),
            },
            "access": {
                "profiles": access_profiles,
                "counts": {
                    key: access_counts.get(key, 0)
                    for key in ("anonymous", "authenticated", "mixed", "unknown")
                },
                "mixed_routes": [
                    route["canonical_url"]
                    for route in routes
                    if route["access"]["classification"] == "mixed"
                ],
            },
            "coverage": coverage,
            "signals": {
                "total": len(signals),
                "shown": min(len(signals), 100),
                "items": signals[:100],
            },
            "technologies": technologies,
        }
        if persist and run is not None:
            run.recon_summary = json.dumps(summary)
            s.add(run)
            s.commit()
        return summary
    finally:
        if own_session:
            s.close()


def _build_page_access(
    pages: list[CrawledPage],
    views: list[PageCredentialView],
    credential_map: dict[int | None, Credential],
) -> tuple[dict[str, dict], list[dict]]:
    by_page_id: dict[int, list[PageCredentialView]] = defaultdict(list)
    for view in views:
        by_page_id[view.page_id].append(view)

    page_access: dict[str, dict] = {}
    observed_profile_ids: set[int] = set()
    observed_usernames: set[str] = set()
    for page in pages:
        credential_ids: set[int] = set()
        usernames: set[str] = set()
        anonymous = page.req_auth is False
        try:
            credential_ids.update(
                int(value) for value in json.loads(page.accessible_by or "[]")
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        for view in by_page_id.get(page.id or -1, []):
            if view.credential_id is None and view.req_auth is False:
                anonymous = True
            if view.credential_id is not None:
                credential_ids.add(view.credential_id)
            if view.username:
                usernames.add(view.username)
        observed_profile_ids.update(credential_ids)
        observed_usernames.update(usernames)
        page_access[_canonical_url(page.url)] = {
            "anonymous": anonymous,
            "credential_ids": credential_ids,
            "usernames": usernames,
        }

    profiles = []
    for credential_id in sorted(observed_profile_ids):
        credential = credential_map.get(credential_id)
        profiles.append(
            {
                "credential_id": credential_id,
                "username": credential.username if credential else None,
                "label": (
                    credential.label or credential.username
                    if credential
                    else f"Credential {credential_id}"
                ),
            }
        )
    known_usernames = {profile["username"] for profile in profiles}
    for username in sorted(observed_usernames - known_usernames):
        profiles.append(
            {"credential_id": None, "username": username, "label": username}
        )
    return page_access, profiles


def _build_routes(
    pages: list[CrawledPage],
    intel_items: list[TargetIntelItem],
    page_access: dict[str, dict],
    credential_map: dict[int | None, Credential],
) -> list[dict]:
    grouped: dict[str, dict] = {}

    def add_route(
        destination: str,
        *,
        method: str = "GET",
        kind: str,
        source: str,
        parameter: str | None = None,
        confidence: float = 1.0,
        source_url: str | None = None,
    ) -> None:
        if not destination or _STATIC_ASSET_RE.search(destination):
            return
        canonical = _canonical_url(destination)
        if not canonical:
            return
        route = grouped.setdefault(
            canonical,
            {
                "canonical_url": canonical,
                "example_urls": [],
                "methods": set(),
                "parameters": set(),
                "kinds": set(),
                "sources": set(),
                "source_urls": set(),
                "confidence": 0.0,
            },
        )
        if destination not in route["example_urls"] and len(route["example_urls"]) < 5:
            route["example_urls"].append(destination)
        route["methods"].add((method or "GET").upper())
        if parameter and not _looks_like_route(parameter):
            route["parameters"].add(parameter)
        route["kinds"].add(kind)
        route["sources"].add(source or "unknown")
        if source_url and source_url != destination:
            route["source_urls"].add(source_url)
        route["confidence"] = max(route["confidence"], float(confidence or 0.0))

    for page in pages:
        add_route(
            page.url,
            kind=page.state_kind or "page",
            source="crawl",
            confidence=1.0,
        )

    for item in intel_items:
        if item.kind not in {"endpoint", "form", "input"}:
            continue
        destination = _intel_destination(item)
        if not destination:
            continue
        metadata = _json_object(item.item_metadata)
        provenance_urls = list(
            dict.fromkeys(url for url in (item.url, metadata.get("page_url")) if url)
        ) or [None]
        for provenance_url in provenance_urls:
            add_route(
                destination,
                method=item.method or "GET",
                kind=item.kind,
                source=item.source,
                parameter=item.key if item.kind == "input" else None,
                confidence=item.confidence,
                source_url=provenance_url,
            )
        if item.kind == "form":
            for field in metadata.get("fields") or []:
                parameter = field.get("name") or field.get("id")
                if parameter:
                    add_route(
                        destination,
                        method=item.method or "GET",
                        kind="form",
                        source=item.source,
                        parameter=str(parameter),
                        confidence=item.confidence,
                        source_url=metadata.get("page_url"),
                    )

    rows: list[dict] = []
    for canonical, route in grouped.items():
        access_sources = {canonical}
        access_sources.update(_canonical_url(url) for url in route["source_urls"])
        observations = [
            page_access[url] for url in access_sources if url in page_access
        ]
        anonymous = any(observation["anonymous"] for observation in observations)
        credential_ids = sorted(
            {
                credential_id
                for observation in observations
                for credential_id in observation["credential_ids"]
            }
        )
        usernames = sorted(
            {
                username
                for observation in observations
                for username in observation["usernames"]
            }
        )
        authenticated = bool(credential_ids or usernames)
        classification = (
            "mixed"
            if anonymous and authenticated
            else "anonymous"
            if anonymous
            else "authenticated"
            if authenticated
            else "unknown"
        )
        labels = []
        for credential_id in credential_ids:
            credential = credential_map.get(credential_id)
            labels.append(
                credential.label or credential.username
                if credential
                else f"Credential {credential_id}"
            )
        credential_usernames = {
            credential_map[credential_id].username
            for credential_id in credential_ids
            if credential_id in credential_map
        }
        labels.extend(
            username
            for username in usernames
            if username not in labels and username not in credential_usernames
        )
        rows.append(
            {
                "canonical_url": canonical,
                "example_urls": route["example_urls"],
                "methods": sorted(route["methods"]),
                "parameters": sorted(route["parameters"]),
                "kinds": sorted(route["kinds"]),
                "sources": sorted(route["sources"]),
                "source_urls": sorted(route["source_urls"])[:5],
                "confidence": round(route["confidence"], 2),
                "access": {
                    "classification": classification,
                    "anonymous": anonymous,
                    "credential_ids": credential_ids,
                    "labels": labels,
                },
                "coverage": {"total": 0, "statuses": {}, "categories": []},
            }
        )
    return sorted(
        rows,
        key=lambda route: (
            not bool(route["parameters"]),
            "api_observation" not in route["sources"],
            route["canonical_url"],
        ),
    )


def _build_coverage(
    cells: list[PageOwaspTest],
    pages: list[CrawledPage],
    routes: list[dict],
) -> dict:
    page_urls = {page.id: _canonical_url(page.url) for page in pages}
    page_map = {page.id: page for page in pages}
    route_map = {route["canonical_url"]: route for route in routes}
    status_counts = Counter()
    category_counts: dict[str, Counter] = defaultdict(Counter)
    class_counts: dict[str, Counter] = defaultdict(Counter)
    gaps: dict[str, set[str]] = defaultdict(set)
    grouped_cells: dict[str, dict[str, dict]] = defaultdict(dict)

    for cell in cells:
        try:
            test_classes = json.loads(cell.test_classes_json or "{}")
        except Exception:
            test_classes = {}
        if not isinstance(test_classes, dict):
            test_classes = {}
        page = page_map.get(cell.page_id)
        if cell.owasp_category == "A03" and bool(getattr(page, "takes_input", False)):
            for test_class in ("sqli", "reflected_xss", "stored_xss"):
                if test_class not in test_classes:
                    test_classes[test_class] = {"status": "not_started"}
        canonical = page_urls.get(cell.page_id)
        if canonical:
            current = grouped_cells[canonical].get(cell.owasp_category)
            if current is None:
                grouped_cells[canonical][cell.owasp_category] = {
                    "status": cell.status,
                    "test_classes": dict(test_classes),
                }
            else:
                if _STATUS_ORDER.get(cell.status, 0) > _STATUS_ORDER.get(
                    current["status"], 0
                ):
                    current["status"] = cell.status
                for test_class, state in test_classes.items():
                    if not isinstance(state, dict):
                        continue
                    previous = current["test_classes"].get(test_class)
                    state_status = str(state.get("status") or "not_started")
                    if previous is None or _STATUS_ORDER.get(
                        state_status, 0
                    ) > _STATUS_ORDER.get(
                        str(previous.get("status") or "not_started"), 0
                    ):
                        current["test_classes"][test_class] = state

    # Count the same obligations the matrix renders. Equivalent page URLs are
    # collapsed, absent categories are N/A, and A03 is represented only by its
    # applicable input test classes rather than its hidden parent row.
    display_by_route: dict[str, list[tuple[str, str, str | None]]] = defaultdict(list)
    for canonical, categories in grouped_cells.items():
        for category, cell in categories.items():
            if category == "A03":
                for test_class in _A03_INPUT_TEST_CLASSES:
                    state = cell["test_classes"].get(test_class)
                    if state is None:
                        continue
                    status = str(state.get("status") or "not_started")
                    display_by_route[canonical].append((category, status, test_class))
            else:
                display_by_route[canonical].append(
                    (category, str(cell.get("status") or "not_started"), None)
                )

    for canonical, obligations in display_by_route.items():
        for category, status, test_class in obligations:
            status_counts[status] += 1
            category_counts[category][status] += 1
            if test_class:
                class_counts[test_class][status] += 1
            if status in {"not_started", "in_progress"}:
                gaps[category].add(canonical)

    for canonical, route in route_map.items():
        obligations = display_by_route.get(canonical, [])
        statuses = Counter(status for _category, status, _test_class in obligations)
        category_statuses: dict[str, str] = {}
        for category, status, _test_class in obligations:
            current = category_statuses.get(category)
            if current is None or _STATUS_ORDER.get(status, 0) > _STATUS_ORDER.get(
                current, 0
            ):
                category_statuses[category] = status
        route["coverage"] = {
            "total": len(obligations),
            "statuses": dict(statuses),
            "categories": sorted(
                {category for category, _status, _class in obligations}
            ),
            "remaining_categories": sorted(
                category
                for category, status in category_statuses.items()
                if status in {"not_started", "in_progress"}
            ),
        }

    total = sum(status_counts.values())
    resolved = sum(
        status_counts[status] for status in ("covered", "finding", "skipped")
    )
    by_category = []
    for category in OWASP_WEB_CATEGORIES:
        counts = category_counts[category]
        category_total = sum(counts.values())
        if not category_total:
            continue
        by_category.append(
            {
                "category": category,
                "label": OWASP_WEB_LABELS.get(category, category),
                "total": category_total,
                "statuses": dict(counts),
                "remaining": counts["not_started"] + counts["in_progress"],
                "gap_routes": sorted(gaps[category])[:10],
                "gap_route_total": len(gaps[category]),
            }
        )
    by_category.sort(key=lambda item: (-item["remaining"], item["category"]))
    return {
        "seeded": bool(cells),
        "total": total,
        "resolved": resolved,
        "completion_percent": round(100 * resolved / total) if total else 0,
        "statuses": {status: status_counts.get(status, 0) for status in _STATUS_ORDER},
        "by_category": by_category,
        "by_test_class": [
            {
                "test_class": test_class,
                "statuses": dict(counts),
                "remaining": counts["not_started"] + counts["in_progress"],
            }
            for test_class, counts in sorted(class_counts.items())
        ],
    }


def _build_signals(
    pages: list[CrawledPage], intel_items: list[TargetIntelItem]
) -> list[dict]:
    signals: dict[tuple[str, str, str], dict] = {}

    def add(
        signal_type: str,
        label: str,
        url: str,
        *,
        evidence: str,
        source: str,
        confidence: float,
    ) -> None:
        if not url:
            return
        key = (signal_type, _canonical_url(url), label)
        existing = signals.get(key)
        item = {
            "type": signal_type,
            "label": label,
            "url": _canonical_url(url),
            "evidence": evidence[:240],
            "source": source,
            "confidence": round(float(confidence or 0.0), 2),
            "observations": 1,
        }
        if existing:
            existing["observations"] += 1
            existing["confidence"] = max(existing["confidence"], item["confidence"])
        else:
            signals[key] = item

    for page in pages:
        if page.has_object_ref:
            add(
                "object_reference",
                "Object-reference route",
                page.url,
                evidence="Crawler classified this route as containing an object reference.",
                source="crawl_analysis",
                confidence=0.8,
            )
        if page.has_business_logic:
            add(
                "business_logic",
                "Business operation",
                page.url,
                evidence="Crawler classified this route as business functionality.",
                source="crawl_analysis",
                confidence=0.8,
            )

    for item in intel_items:
        destination = _intel_destination(item) or item.url or ""
        if item.kind in {"input", "form"} and _looks_ssrf_param(item.key):
            add(
                "url_input",
                f"URL-like input: {item.key}",
                destination,
                evidence=item.evidence or item.value or item.key,
                source=item.source,
                confidence=item.confidence,
            )
        if item.kind == "response_field" and _looks_sensitive_name(item.key):
            add(
                "sensitive_field",
                f"Sensitive-looking field: {item.key}",
                destination,
                evidence=item.evidence or item.value or item.key,
                source=item.source,
                confidence=item.confidence,
            )
        if item.kind == "storage_key" and _looks_tokenish(item.key, item.value):
            add(
                "token_storage",
                f"Token storage: {item.key}",
                destination,
                evidence=item.evidence or item.value or item.key,
                source=item.source,
                confidence=item.confidence,
            )
        if _looks_like_public_config_endpoint(item):
            add(
                "operational_endpoint",
                "Operational/config endpoint",
                destination,
                evidence=item.evidence or item.key or item.value,
                source=item.source,
                confidence=item.confidence,
            )
    return sorted(
        signals.values(),
        key=lambda item: (
            -item["confidence"],
            -item["observations"],
            item["type"],
            item["url"],
        ),
    )


def _detect_technologies(
    session: Session,
    run_id: int,
    pages: list[CrawledPage],
    intel_items: list[TargetIntelItem],
) -> list[dict]:
    evidence_text = " ".join(
        [_intel_text(item) for item in intel_items]
        + [(page.llm_context or "")[:2000] for page in pages]
    ).lower()
    header_rows = list(
        session.exec(
            select(TrafficEntry.response_headers)
            .where(TrafficEntry.test_run_id == run_id)
            .limit(500)
        )
    )
    header_text = " ".join(header_rows).lower()
    haystack = f"{evidence_text} {header_text}"
    markers = {
        "react": "React",
        "vue": "Vue.js",
        "angular": "Angular",
        "next.js": "Next.js",
        "nuxt": "Nuxt",
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "ruby on rails": "Rails",
        "spring": "Spring",
        "express": "Express",
        "laravel": "Laravel",
        "graphql": "GraphQL",
        "jwt": "JWT",
        "oauth": "OAuth",
        "swagger": "Swagger/OpenAPI",
        "openapi": "Swagger/OpenAPI",
        "apache": "Apache",
        "nginx": "nginx",
        "php": "PHP",
    }
    found: dict[str, dict] = {}
    for marker, label in markers.items():
        if marker not in haystack or label in found:
            continue
        found[label] = {
            "name": label,
            "source": "response headers"
            if marker in header_text
            else "crawl intelligence",
        }
    return sorted(found.values(), key=lambda item: item["name"].lower())


def _intel_destination(item: TargetIntelItem) -> str:
    if item.kind == "endpoint":
        candidate = item.value if _looks_like_route(item.value) else item.key
        if not _looks_like_route(candidate):
            return ""
        return urljoin(item.url or "", candidate)
    if item.kind in {"form", "input"}:
        return item.url or ""
    return item.url or ""


def _canonical_url(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    path = "/".join(
        "{id}" if _ID_SEGMENT_RE.fullmatch(segment) else segment
        for segment in parts.path.split("/")
    )
    fragment = "/".join(
        "{id}" if _ID_SEGMENT_RE.fullmatch(segment) else segment
        for segment in parts.fragment.split("/")
    )
    query_parts = []
    for part in parts.query.split("&") if parts.query else []:
        key, separator, value_part = part.partition("=")
        normalized = "{id}" if _ID_SEGMENT_RE.fullmatch(value_part) else value_part
        query_parts.append(f"{key}{separator}{normalized}")
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path or "/",
            "&".join(query_parts),
            fragment,
        )
    )


def _looks_like_route(value: str | None) -> bool:
    text = str(value or "").strip()
    return text.startswith(("http://", "https://", "/", "#"))


def _json_object(value: str | None) -> dict:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _looks_like_public_config_endpoint(item: TargetIntelItem) -> bool:
    text = f"{_intel_destination(item)} {_intel_text(item)}".lower()
    if item.kind not in {"endpoint", "script"}:
        return False
    return any(
        marker in text
        for marker in (
            "/api/health",
            "/health",
            "/status",
            "/metrics",
            "/debug",
            "/config",
            "/actuator",
            "/server-status",
            "/.env",
        )
    )


def _intel_text(item: TargetIntelItem) -> str:
    return " ".join(
        str(value or "")
        for value in (item.kind, item.key, item.value, item.url, item.evidence)
    )


def _looks_sensitive_name(name: str) -> bool:
    return bool(
        re.search(
            r"(?:password|passwd|secret|token|api[_-]?key|private[_-]?key|session|ssn|credit[_-]?card)",
            name or "",
            re.IGNORECASE,
        )
    )


def _looks_tokenish(key: str, value: str) -> bool:
    return bool(
        re.search(r"(?:jwt|token|auth|session|bearer)", f"{key} {value}", re.IGNORECASE)
    )


def _looks_ssrf_param(name: str) -> bool:
    return bool(
        re.search(
            r"(?:url|uri|href|link|callback|webhook|redirect|image|avatar|feed|host|domain|proxy)",
            name or "",
            re.IGNORECASE,
        )
    )
