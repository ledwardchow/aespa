"""Stored crawl archive serialization and record restoration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlmodel import Session, select

from aespa.models import (
    AgentLog,
    CrawledPage,
    PageCredentialView,
    PageLink,
    PageOwaspTest,
    ScanLog,
    ScannerSession,
    Site,
    TargetIntelItem,
    TestRun,
    TestRunStatus,
    TrafficEntry,
)
from aespa.services import recon_summary as recon_summary_svc

_CRAWL_ARCHIVE_FORMAT = "aespa-crawl-export"
_CRAWL_ARCHIVE_VERSION = 1


class ArchiveError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _json_dict(value: str | None) -> dict:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _redacted_metadata(value: dict) -> dict:
    sensitive_terms = ("password", "secret", "token", "cookie", "authorization")
    redacted: dict = {}
    for key, raw in value.items():
        if any(term in str(key).lower() for term in sensitive_terms):
            redacted[key] = "[REDACTED]"
        elif isinstance(raw, dict):
            redacted[key] = _redacted_metadata(raw)
        else:
            redacted[key] = raw
    return redacted


def _normalise_base_url(url: str) -> str:
    """Compare target origins without treating a trailing slash as a mismatch."""
    parts = urlsplit(url.strip())
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/')}"


def build_archive(session: Session, run: TestRun) -> dict:
    """Create a complete crawl snapshot that can be scanned without recrawling."""
    site = session.get(Site, run.site_id)
    if site is None:
        raise ArchiveError(404, f"Site {run.site_id} not found")
    pages = list(
        session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run.id))
    )
    page_urls = {page.id: page.url for page in pages}
    page_state_keys = {page.id: page.state_key for page in pages}
    credentials = {cred.id: cred.username for cred in site.credentials}
    page_fields = (
        "url",
        "state_key",
        "state_label",
        "state_kind",
        "replay_steps_json",
        "replay_credential_id",
        "title",
        "page_text",
        "screenshot_b64",
        "llm_context",
        "depth",
        "status",
        "error_message",
        "in_scope",
        "scan_status",
        "req_auth",
        "takes_input",
        "has_object_ref",
        "has_business_logic",
        "accessible_by",
        "owasp_applicable_json",
    )
    return {
        "format": _CRAWL_ARCHIVE_FORMAT,
        "version": _CRAWL_ARCHIVE_VERSION,
        # The archive includes captured cookies, bearer tokens, and full HTTP
        # exchanges so the destination run behaves like the source after crawl.
        "contains_sensitive_authentication_data": True,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "site_base_url": site.base_url,
            "run_id": run.id,
            "run_name": run.name,
        },
        "crawl": {
            "progress": {
                "per_user_progress": run.per_user_progress,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat()
                if run.completed_at
                else None,
            },
            "pages": [
                {field: getattr(page, field) for field in page_fields} for page in pages
            ],
            "links": [
                {
                    "source_url": page_urls.get(link.source_page_id),
                    "source_state_key": page_state_keys.get(link.source_page_id),
                    "target_url": link.target_url,
                    "target_state_key": page_state_keys.get(link.target_page_id),
                    "link_text": link.link_text,
                    "action_kind": link.action_kind,
                    "action_data_json": link.action_data_json,
                    "interaction_id": link.interaction_id,
                }
                for link in session.exec(
                    select(PageLink).where(PageLink.test_run_id == run.id)
                )
                if page_urls.get(link.source_page_id)
            ],
            "credential_views": [
                {
                    "page_url": page_urls.get(view.page_id),
                    "page_state_key": page_state_keys.get(view.page_id),
                    "username": credentials.get(view.credential_id, view.username),
                    "screenshot_b64": view.screenshot_b64,
                    "llm_context": view.llm_context,
                    "page_text": view.page_text,
                    "req_auth": view.req_auth,
                    "takes_input": view.takes_input,
                    "has_object_ref": view.has_object_ref,
                    "has_business_logic": view.has_business_logic,
                    "owasp_applicable_json": view.owasp_applicable_json,
                }
                for view in session.exec(
                    select(PageCredentialView).where(
                        PageCredentialView.test_run_id == run.id
                    )
                )
                if page_urls.get(view.page_id)
            ],
            "target_intelligence": [
                {
                    "kind": item.kind,
                    "key": item.key,
                    "value": item.value,
                    "url": item.url,
                    "method": item.method,
                    "source": item.source,
                    "confidence": item.confidence,
                    "evidence": item.evidence,
                    "item_metadata": item.item_metadata,
                    "page_id": item.page_id,
                    "page_url": page_urls.get(item.page_id),
                    "page_state_key": page_state_keys.get(item.page_id),
                }
                for item in session.exec(
                    select(TargetIntelItem).where(TargetIntelItem.test_run_id == run.id)
                )
            ],
            # Keep the seeded coverage categories too.  The page JSON is the
            # source of truth for a fresh crawl, but these rows make archives
            # resilient to runs created before applicability was persisted.
            "owasp_categories": [
                {"page_url": page_urls.get(row.page_id), "category": row.owasp_category}
                for row in session.exec(
                    select(PageOwaspTest).where(PageOwaspTest.test_run_id == run.id)
                )
                if page_urls.get(row.page_id)
            ],
            "traffic": [
                {
                    "source": entry.source,
                    "method": entry.method,
                    "url": entry.url,
                    "request_headers": entry.request_headers,
                    "request_body": entry.request_body,
                    "status": entry.status,
                    "response_headers": entry.response_headers,
                    "response_body": entry.response_body,
                    "duration_ms": entry.duration_ms,
                    "username": entry.username,
                    "page_id": entry.page_id,
                    "page_url": page_urls.get(entry.page_id),
                    "page_state_key": page_state_keys.get(entry.page_id),
                    "interaction_id": entry.interaction_id,
                }
                for entry in session.exec(
                    select(TrafficEntry).where(TrafficEntry.test_run_id == run.id)
                )
            ],
            "scanner_sessions": [
                {
                    "label": record.label,
                    "kind": record.kind,
                    "username": record.username,
                    "credential_username": credentials.get(record.credential_id),
                    "source": record.source,
                    "cookies_json": record.cookies_json,
                    "extra_headers_json": record.extra_headers_json,
                    "session_metadata": record.session_metadata,
                    "token_hint": record.token_hint,
                    "lifecycle_state": record.lifecycle_state,
                    "validation_url": record.validation_url,
                    "last_status": record.last_status,
                    "is_active": record.is_active,
                }
                for record in session.exec(
                    select(ScannerSession)
                    .where(ScannerSession.test_run_id == run.id)
                    .where(ScannerSession.run_kind == "web")
                )
            ],
            # Preserve the crawl-only activity history for a destination run
            # that looks and behaves like it just completed that crawl.
            "activity": {
                "scan_log": [
                    {
                        "phase": entry.phase,
                        "status": entry.status,
                        "message": entry.message,
                        "page_url": entry.page_url,
                        "data_json": entry.data_json,
                    }
                    for entry in session.exec(
                        select(ScanLog)
                        .where(ScanLog.test_run_id == run.id)
                        .where(ScanLog.run_kind == "web")
                        .where(ScanLog.phase.in_(("crawl", "auth")))
                    )
                ],
                "agent_log": [
                    {
                        "agent_id": entry.agent_id,
                        "role": entry.role,
                        "status": entry.status,
                        "current_task": entry.current_task,
                        "outcome": entry.outcome,
                    }
                    for entry in session.exec(
                        select(AgentLog)
                        .where(AgentLog.test_run_id == run.id)
                        .where(AgentLog.run_kind == "web")
                        .where(AgentLog.agent_id == "crawler")
                    )
                ],
            },
        },
    }


def validate_archive(payload: object, site_base_url: str) -> dict:
    if not isinstance(payload, dict) or payload.get("format") != _CRAWL_ARCHIVE_FORMAT:
        raise ArchiveError(status=400, message="Not an AESPA crawl export file")
    if payload.get("version") != _CRAWL_ARCHIVE_VERSION:
        raise ArchiveError(status=400, message="Unsupported crawl export version")
    source = payload.get("source")
    crawl = payload.get("crawl")
    if (
        not isinstance(source, dict)
        or not isinstance(crawl, dict)
        or not isinstance(crawl.get("pages"), list)
    ):
        raise ArchiveError(status=400, message="Crawl export is missing page data")
    source_url = source.get("site_base_url")
    if not isinstance(source_url, str) or _normalise_base_url(
        source_url
    ) != _normalise_base_url(site_base_url):
        raise ArchiveError(
            status=400, message="This crawl export belongs to a different site URL"
        )
    return crawl


def restore_archive_records(
    session: Session, run_id: int, crawl: dict, site: Site
) -> dict[str, CrawledPage]:
    pages_by_identity: dict[str, CrawledPage] = {}
    pages_by_url: dict[str, CrawledPage] = {}
    allowed_page_fields = {
        "url",
        "state_key",
        "state_label",
        "state_kind",
        "replay_steps_json",
        "replay_credential_id",
        "title",
        "page_text",
        "screenshot_b64",
        "llm_context",
        "depth",
        "status",
        "error_message",
        "in_scope",
        "scan_status",
        "req_auth",
        "takes_input",
        "has_object_ref",
        "has_business_logic",
        "accessible_by",
        "owasp_applicable_json",
    }
    try:
        for item in crawl["pages"]:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("url"), str)
                or not item["url"]
            ):
                raise ValueError("page URL missing")
            page_identity = item.get("state_key") or item["url"]
            if page_identity in pages_by_identity:
                continue
            page = CrawledPage(
                test_run_id=run_id,
                **{
                    key: value
                    for key, value in item.items()
                    if key in allowed_page_fields
                },
            )
            session.add(page)
            session.flush()
            pages_by_identity[page_identity] = page
            pages_by_url.setdefault(page.url, page)

        for item in crawl.get("links", []):
            if not isinstance(item, dict) or not isinstance(
                item.get("target_url"), str
            ):
                continue
            source = pages_by_identity.get(
                item.get("source_state_key")
            ) or pages_by_url.get(item.get("source_url"))
            if source is None:
                continue
            target = pages_by_identity.get(
                item.get("target_state_key")
            ) or pages_by_url.get(item["target_url"])
            session.add(
                PageLink(
                    test_run_id=run_id,
                    source_page_id=source.id,
                    target_page_id=target.id if target else None,
                    target_url=item["target_url"],
                    link_text=item.get("link_text"),
                    action_kind=item.get("action_kind") or "navigate",
                    action_data_json=item.get("action_data_json") or "{}",
                    interaction_id=item.get("interaction_id"),
                )
            )

        credential_ids = {
            credential.username: credential.id for credential in site.credentials
        }
        for item in crawl.get("credential_views", []):
            if not isinstance(item, dict):
                continue
            page = pages_by_identity.get(
                item.get("page_state_key")
            ) or pages_by_url.get(item.get("page_url"))
            if page is None:
                continue
            username = (
                item.get("username") if isinstance(item.get("username"), str) else None
            )
            session.add(
                PageCredentialView(
                    test_run_id=run_id,
                    page_id=page.id,
                    credential_id=credential_ids.get(username),
                    username=username,
                    **{
                        key: item.get(key)
                        for key in (
                            "screenshot_b64",
                            "llm_context",
                            "page_text",
                            "req_auth",
                            "takes_input",
                            "has_object_ref",
                            "has_business_logic",
                            "owasp_applicable_json",
                        )
                    },
                )
            )

        for item in crawl.get("target_intelligence", []):
            if not isinstance(item, dict) or not isinstance(item.get("kind"), str):
                continue
            intel_page = pages_by_identity.get(
                item.get("page_state_key")
            ) or pages_by_url.get(item.get("page_url"))
            session.add(
                TargetIntelItem(
                    test_run_id=run_id,
                    **{
                        key: item.get(key)
                        for key in (
                            "kind",
                            "key",
                            "value",
                            "url",
                            "method",
                            "source",
                            "confidence",
                            "evidence",
                            "item_metadata",
                        )
                    },
                    page_id=intel_page.id if intel_page else None,
                )
            )
        for item in crawl.get("traffic", []):
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("method"), str)
                or not isinstance(item.get("url"), str)
            ):
                continue
            session.add(
                TrafficEntry(
                    test_run_id=run_id,
                    **{
                        key: item.get(key)
                        for key in (
                            "source",
                            "method",
                            "url",
                            "request_headers",
                            "request_body",
                            "status",
                            "response_headers",
                            "response_body",
                            "duration_ms",
                            "username",
                            "interaction_id",
                        )
                    },
                    page_id=(
                        (
                            pages_by_identity.get(item.get("page_state_key"))
                            or pages_by_url.get(item.get("page_url"))
                        ).id
                        if (
                            pages_by_identity.get(item.get("page_state_key"))
                            or pages_by_url.get(item.get("page_url"))
                        )
                        else None
                    ),
                    session_label=item.get("session_label"),
                )
            )
        for item in crawl.get("scanner_sessions", []):
            if not isinstance(item, dict) or not isinstance(item.get("label"), str):
                continue
            username = (
                item.get("username") if isinstance(item.get("username"), str) else None
            )
            credential_username = item.get("credential_username")
            if not isinstance(credential_username, str):
                credential_username = username
            session.add(
                ScannerSession(
                    test_run_id=run_id,
                    run_kind="web",
                    label=item["label"],
                    kind=item.get("kind") or "cookie",
                    username=username,
                    credential_id=credential_ids.get(credential_username),
                    source=item.get("source") or "crawler",
                    cookies_json=item.get("cookies_json") or "{}",
                    extra_headers_json=item.get("extra_headers_json") or "{}",
                    session_metadata=item.get("session_metadata") or "{}",
                    token_hint=item.get("token_hint"),
                    lifecycle_state=item.get("lifecycle_state") or "candidate",
                    validation_url=item.get("validation_url"),
                    last_status=item.get("last_status"),
                    is_active=bool(item.get("is_active", True)),
                )
            )
        activity = crawl.get("activity")
        if isinstance(activity, dict):
            for item in activity.get("scan_log", []):
                if not isinstance(item, dict) or not isinstance(item.get("phase"), str):
                    continue
                session.add(
                    ScanLog(
                        test_run_id=run_id,
                        run_kind="web",
                        phase=item["phase"],
                        status=item.get("status") or "",
                        message=item.get("message") or "",
                        page_url=item.get("page_url"),
                        data_json=item.get("data_json"),
                    )
                )
            for item in activity.get("agent_log", []):
                if not isinstance(item, dict) or not isinstance(
                    item.get("agent_id"), str
                ):
                    continue
                session.add(
                    AgentLog(
                        test_run_id=run_id,
                        run_kind="web",
                        agent_id=item["agent_id"],
                        role=item.get("role") or "Crawler",
                        status=item.get("status") or "complete",
                        current_task=item.get("current_task") or "",
                        outcome=item.get("outcome"),
                    )
                )
    except (TypeError, ValueError) as exc:
        session.rollback()
        raise ArchiveError(
            status=400, message=f"Invalid crawl export data: {exc}"
        ) from exc

    return pages_by_url


def finish_archive_import(
    session: Session, run: TestRun, crawl: dict, pages_by_url: dict[str, CrawledPage]
) -> TestRun:
    run_id = run.id
    # A real crawl leaves a recon summary behind.  Build it from the restored
    # pages and intelligence now so the Attack Surface panel is immediately
    # useful—without requiring a Dynamic Scan to run first.
    recon_summary_svc.build_recon_summary(run_id, session=session)

    # Older runs can have coverage cells even when their page applicability JSON
    # was not retained.  Fold those categories back into the imported page data,
    # then seed a fresh workprogram without copying coverage progress/results.
    archived_categories: dict[str, set[str]] = {}
    for item in crawl.get("owasp_categories", []):
        if not isinstance(item, dict):
            continue
        url, category = item.get("page_url"), item.get("category")
        if url in pages_by_url and isinstance(category, str):
            archived_categories.setdefault(url, set()).add(category)
    for page in pages_by_url.values():
        try:
            applicable = json.loads(page.owasp_applicable_json or "{}")
        except (TypeError, json.JSONDecodeError):
            applicable = {}
        if not isinstance(applicable, dict):
            applicable = {}
        categories = {
            category
            for category, is_applicable in applicable.items()
            if is_applicable and isinstance(category, str)
        } | archived_categories.get(page.url, set())
        for category in archived_categories.get(page.url, set()):
            applicable[category] = True
        page.owasp_applicable_json = json.dumps(applicable)
        session.add(page)
        for category in categories:
            session.add(
                PageOwaspTest(
                    test_run_id=run_id, page_id=page.id, owasp_category=category
                )
            )
    now = datetime.now(timezone.utc)
    run.status = TestRunStatus.complete
    run.pages_discovered = len(pages_by_url)
    run.started_at = now
    run.completed_at = now
    run.current_url = None
    progress = crawl.get("progress")
    run.per_user_progress = (
        progress.get("per_user_progress") if isinstance(progress, dict) else None
    )
    run.error_message = None
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
