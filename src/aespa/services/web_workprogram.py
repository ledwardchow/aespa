"""Web workprogram: per-page × OWASP Top 10:2025 coverage matrix for web TestRuns."""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    CrawledPage,
    PageOwaspTest,
    ScanFinding,
    TargetIntelItem,
    TestRun,
)
from aespa.services import events as events_svc
from aespa.services.llm import OWASP_WEB_CATEGORIES, OWASP_WEB_LABELS

log = logging.getLogger(__name__)

_UTC = timezone.utc

# Matches a single path segment or query-param value that is a pure integer or UUID
_ID_RE = re.compile(
    r"^(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)

# Match "A01", "A02 - Cryptographic Failures", "A03:Injection" etc. → short code
_OWASP_CODE_RE = re.compile(r"\b(A\d{2})\b", re.IGNORECASE)


def _normalize_owasp_category(cat: str) -> str:
    """Extract the short OWASP code (A01–A10) from any variant the LLM may produce."""
    m = _OWASP_CODE_RE.search(cat or "")
    return m.group(1).upper() if m else (cat or "").strip().upper()


def _normalize_url(url: str) -> str:
    """Replace numeric/UUID path segments and query-param values with {id} placeholders."""
    path, _, qs = url.partition("?")
    norm_path = "/".join(_ID_RE.sub("{id}", seg) for seg in path.split("/"))
    if not qs:
        return norm_path
    # Normalise each query param value independently; keep key names as-is.
    norm_params = "&".join(
        f"{k}={_ID_RE.sub('{id}', v)}" if v else k
        for part in qs.split("&")
        for k, _, v in [part.partition("=")]
    )
    return f"{norm_path}?{norm_params}"


# Status precedence: higher rank must never be downgraded.
_STATUS_RANK = {
    "not_started": 0,
    "in_progress": 1,
    "covered": 2,
    "skipped": 2,
    "finding": 3,
}

# Cells in these states still need work; everything else is terminal.
_UNCOVERED_STATES = ("not_started", "in_progress")

_ENFORCE_DEFAULT_MAX_ATTEMPTS = 500
_ENFORCE_DEFAULT_TIME_BUDGET_S = 1800.0


# Static file extensions that are never meaningful pentest targets.
_STATIC_EXTS = re.compile(
    r"\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|map|txt|xml|pdf)(\?|$)",
    re.IGNORECASE,
)


def _is_static_asset(url: str) -> bool:
    """Return True for JS/CSS/image/font/map URLs that carry no server-side logic."""
    path = url.split("?")[0]
    return bool(_STATIC_EXTS.search(path))


def seed_web_workprogram(run_id: int) -> int:
    """Idempotently create PageOwaspTest rows for every in-scope page × applicable category.

    Adds rows for new pages or newly-applicable categories; never removes existing rows.
    Returns the number of new rows created.
    """
    with Session(get_engine(), expire_on_commit=False) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return 0

        pages = list(
            s.exec(
                select(CrawledPage)
                .where(CrawledPage.test_run_id == run_id)
                .where(CrawledPage.in_scope == True)  # noqa: E712
            ).all()
        )

        existing = {
            (row.page_id, row.owasp_category)
            for row in s.exec(
                select(PageOwaspTest).where(PageOwaspTest.test_run_id == run_id)
            ).all()
        }

        created = 0
        for page in pages:
            if _is_static_asset(page.url):
                continue  # skip JS/CSS/image/font — no server-side security logic to test
            try:
                applicable = json.loads(page.owasp_applicable_json or "{}")
            except Exception:
                applicable = {}
            for cat in OWASP_WEB_CATEGORIES:
                if applicable.get(cat) and (page.id, cat) not in existing:
                    s.add(
                        PageOwaspTest(
                            test_run_id=run_id,
                            page_id=page.id,
                            owasp_category=cat,
                        )
                    )
                    created += 1

        s.commit()

    log.info("seed_web_workprogram: run_id=%s created=%d cells", run_id, created)
    return created


# ── Coverage cell updates ─────────────────────────────────────────────────────


def update_web_coverage_cell(
    run_id: int,
    page_id: int,
    owasp_category: str,
    status: str,
    finding_id: int | None = None,
    skip_reason: str | None = None,
) -> None:
    """Upsert a web coverage cell with no-downgrade status semantics.

    If ``finding_id`` is given it is appended to ``finding_ids_json``.
    Status is never downgraded: once ``finding`` it cannot go back to ``covered``.
    ``skip_reason`` is recorded whenever supplied (used by enforce mode).
    """
    owasp_category = _normalize_owasp_category(
        owasp_category
    )  # "A02 - Crypto…" → "A02"
    with Session(get_engine()) as s:
        cell = s.exec(
            select(PageOwaspTest)
            .where(PageOwaspTest.test_run_id == run_id)
            .where(PageOwaspTest.page_id == page_id)
            .where(PageOwaspTest.owasp_category == owasp_category)
        ).first()
        if cell is None:
            cell = PageOwaspTest(
                test_run_id=run_id,
                page_id=page_id,
                owasp_category=owasp_category,
                status=status,
                last_updated=datetime.now(_UTC),
            )
        else:
            current_rank = _STATUS_RANK.get(cell.status, 0)
            new_rank = _STATUS_RANK.get(status, 0)
            if new_rank > current_rank:
                cell.status = status
                cell.last_updated = datetime.now(_UTC)
            elif finding_id is None and skip_reason is None:
                return
        if skip_reason is not None:
            cell.skip_reason = skip_reason
        if finding_id is not None:
            try:
                ids: list = json.loads(cell.finding_ids_json or "[]")
            except Exception:
                ids = []
            if finding_id not in ids:
                ids.append(finding_id)
                cell.finding_ids_json = json.dumps(ids)
        s.add(cell)
        s.commit()
    # Emit SSE only for high-value status transitions; skip in_progress (too frequent).
    if status in ("finding", "covered", "skipped"):
        events_svc.emit(
            run_id,
            {
                "type": "coverage_update",
                "page_id": page_id,
                "owasp_category": owasp_category,
                "status": status,
                "finding_id": finding_id,
            },
        )


def mark_in_progress_to_covered(run_id: int) -> None:
    """At scan completion (track mode), promote ``in_progress`` cells to ``covered``.

    ``not_started`` cells are left alone — they mean the scanner never sent
    a probe to that page × category pair.
    """
    with Session(get_engine()) as s:
        cells = list(
            s.exec(
                select(PageOwaspTest)
                .where(PageOwaspTest.test_run_id == run_id)
                .where(PageOwaspTest.status == "in_progress")
            ).all()
        )
        now = datetime.now(_UTC)
        for cell in cells:
            cell.status = "covered"
            cell.last_updated = now
            s.add(cell)
        s.commit()
    log.info("mark_in_progress_to_covered: run_id=%s promoted=%d", run_id, len(cells))


# ── post_probe_fn / post_finding_fn factories ─────────────────────────────────


def _make_web_post_probe_fn(run_id: int):
    """Return ``(url, method, owasp_category) → None`` for per-probe in_progress tracking.

    Matches the probed URL to a CrawledPage and flips the (page, category) cell
    to ``in_progress``.  If no CrawledPage exists for the URL yet (the test lead
    chose a page not in the original crawl), one is created on-the-fly so the
    workprogram can track it.
    """

    def _post_probe(url: str, method: str, owasp_category: str) -> None:  # noqa: ARG001
        cat = (owasp_category or "").strip().upper()
        if not cat:
            return
        url = (url or "").strip()
        if not url:
            return
        with Session(get_engine()) as s:
            pages = list(
                s.exec(
                    select(CrawledPage)
                    .where(CrawledPage.test_run_id == run_id)
                    .where(CrawledPage.in_scope == True)  # noqa: E712
                ).all()
            )
            page_id = _match_page_for_url(url, pages)
            if page_id is None:
                # Create a placeholder page so the workprogram can track this probe.
                page = CrawledPage(
                    test_run_id=run_id,
                    url=url,
                    in_scope=True,
                    status="crawled",
                    scan_status="pending",
                )
                s.add(page)
                s.flush()
                page_id = page.id
                s.commit()
                log.info(
                    "web_workprogram: created placeholder page id=%s url=%s run=%s",
                    page_id,
                    url,
                    run_id,
                )
        update_web_coverage_cell(run_id, page_id, cat, "in_progress")

    return _post_probe


def _clean_affected_url(raw: str) -> str:
    """Strip annotations and list-shaped values from a finding's affected_url.

    The LLM sometimes passes values like
    ``"http://t/api/foo, http://t/api/bar"`` or ``"http://t/* (all endpoints)"``
    which would never match a single crawled page.  This collapses those to
    the first clean URL so the post-finding hook has a chance of attributing
    the finding to a real page.
    """
    s = (raw or "").strip()
    if not s:
        return s
    # Strip a trailing parenthetical annotation.
    if "(" in s:
        s = s.split("(", 1)[0].strip()
    # Take the first comma-separated URL.
    if "," in s:
        s = s.split(",", 1)[0].strip()
    return s


def _make_web_post_finding_fn(run_id: int):
    """Return ``(ScanFinding) → None`` that flips the matching cell to ``finding``.

    Resolution chain (in order):
    1. ``affected_url`` (after stripping list/annotation noise) matched
       against in-scope crawled pages — exact + normalised match only.
    2. ``finding.page_id`` if it points to an in-scope page (this is the
       page the scanner already chose via prefix overlap, so a finding on
       ``/api/users/42`` whose ``page_id`` is ``/api/users`` lands on the
       right row instead of a new placeholder).
    3. Placeholder CrawledPage created with the cleaned affected_url.

    A placeholder is only the last resort — the LLM is increasingly being
    prompted to pass a single specific URL, so this branch should be hit
    rarely in practice.
    """

    def _post_finding(finding: Any) -> None:
        if finding is None:
            return
        if getattr(finding, "finding_source", None) == "deterministic_probe":
            return  # deterministic findings are excluded from the workprogram
        cat = (getattr(finding, "owasp_category", None) or "").strip().upper()
        if not cat:
            return
        fid = getattr(finding, "id", None)

        affected_url = _clean_affected_url(getattr(finding, "affected_url", None))

        with Session(get_engine()) as s:
            pages = list(
                s.exec(
                    select(CrawledPage)
                    .where(CrawledPage.test_run_id == run_id)
                    .where(CrawledPage.in_scope == True)  # noqa: E712
                ).all()
            )
            page_id: int | None = None
            if affected_url:
                page_id = _match_page_for_url(affected_url, pages)
            if page_id is None:
                # Fallback: trust the page the scanner already chose for this
                # finding (it uses prefix-overlap resolution inside
                # _dynamic_finding_page_id).  Only use it if the page still
                # exists in the crawl and is in-scope.
                hint_page_id = getattr(finding, "page_id", None)
                if hint_page_id is not None:
                    hint_page = next((p for p in pages if p.id == hint_page_id), None)
                    if hint_page is not None:
                        page_id = hint_page_id
            if page_id is None and affected_url:
                # Last resort: create a placeholder so no finding is silently
                # dropped.  The URL is already cleaned of list/annotation noise.
                page = CrawledPage(
                    test_run_id=run_id,
                    url=affected_url,
                    in_scope=True,
                    status="crawled",
                    scan_status="pending",
                )
                s.add(page)
                s.flush()
                page_id = page.id
                s.commit()
                log.info(
                    "web_workprogram: created placeholder page id=%s url=%s run=%s (finding)",
                    page_id,
                    affected_url,
                    run_id,
                )

        if page_id is None:
            return
        update_web_coverage_cell(run_id, page_id, cat, "finding", finding_id=fid)

    return _post_finding


def _match_page_for_url(url: str, pages: list[CrawledPage]) -> int | None:
    """Find the best matching CrawledPage id for the given URL.

    Tries exact match first, then normalised match (strips query string and
    trailing slash).  Returns None if no page matches — callers should create
    a placeholder page in that case.
    """
    url = (url or "").strip()
    # 1. Exact match
    for p in pages:
        if p.url == url:
            return p.id
    # 2. Normalised match — strip query strings and trailing slashes on both sides
    url_base = url.split("?")[0].rstrip("/")
    for p in pages:
        if p.url.split("?")[0].rstrip("/") == url_base:
            return p.id
    return None


# ── Enforce mode ──────────────────────────────────────────────────────────────


def _uncovered_web_cells(run_id: int) -> list[tuple[CrawledPage, str, str]]:
    """Return ``[(page, category, current_status)]`` for non-terminal cells."""
    with Session(get_engine(), expire_on_commit=False) as s:
        cells = list(
            s.exec(
                select(PageOwaspTest)
                .where(PageOwaspTest.test_run_id == run_id)
                .where(PageOwaspTest.status.in_(_UNCOVERED_STATES))  # type: ignore[attr-defined]
            ).all()
        )
        page_ids = {c.page_id for c in cells}
        pages = (
            {
                p.id: p
                for p in s.exec(
                    select(CrawledPage).where(CrawledPage.id.in_(page_ids))  # type: ignore[attr-defined]
                ).all()
            }
            if page_ids
            else {}
        )
    out: list[tuple[CrawledPage, str, str]] = []
    for c in cells:
        page = pages.get(c.page_id)
        if page is not None:
            out.append((page, c.owasp_category, c.status))
    return out


def get_web_coverage_gaps(run_id: int, *, limit: int = 12) -> dict[str, Any]:
    """Return a compact live list of useful uncovered web workprogram cells.

    This is intentionally not a second plan.  It projects canonical workprogram
    state into a bounded set of concrete next actions suitable for the Test Lead's
    context window and completion challenge.
    """
    limit = max(1, min(50, int(limit or 12)))
    with Session(get_engine(), expire_on_commit=False) as s:
        cells = list(
            s.exec(
                select(PageOwaspTest).where(PageOwaspTest.test_run_id == run_id)
            ).all()
        )
        page_ids = {cell.page_id for cell in cells}
        pages = {
            page.id: page
            for page in (
                s.exec(
                    select(CrawledPage).where(CrawledPage.id.in_(page_ids))  # type: ignore[attr-defined]
                ).all()
                if page_ids
                else []
            )
        }
        intel = list(
            s.exec(
                select(TargetIntelItem)
                .where(TargetIntelItem.test_run_id == run_id)
                .where(TargetIntelItem.kind == "endpoint")
            ).all()
        )

    totals: dict[str, int] = {status: 0 for status in _STATUS_RANK}
    for cell in cells:
        totals[cell.status] = totals.get(cell.status, 0) + 1

    method_by_url: dict[str, str] = {}
    for item in intel:
        candidate = str(item.url or item.value or item.key or "").strip()
        if candidate:
            method_by_url.setdefault(_normalize_url(candidate), (item.method or "GET").upper())

    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for cell in cells:
        if cell.status not in _UNCOVERED_STATES:
            continue
        page = pages.get(cell.page_id)
        if page is None or not page.in_scope or _is_static_asset(page.url):
            continue
        url = page.url
        normalized = _normalize_url(url)
        method = method_by_url.get(normalized, "GET")
        signals = []
        if page.takes_input:
            signals.append("takes input")
        if page.has_object_ref:
            signals.append("contains an object reference")
        if page.req_auth:
            signals.append("requires authentication")
        if page.has_business_logic:
            signals.append("contains business logic")
        if page.state_kind == "api" or "/api/" in url:
            signals.append("API route")
        reason = (
            f"{', '.join(signals)}; {cell.status.replace('_', ' ')} for "
            f"{cell.owasp_category}"
            if signals
            else f"applicable cell is {cell.status.replace('_', ' ')}"
        )
        # Evidence-first ordering: untouched input/API/object/auth surfaces first,
        # then stable page/category ordering. No synthetic risk score is exposed.
        rank = (
            0 if cell.status == "not_started" else 1,
            -int(bool(page.takes_input)),
            -int(page.state_kind == "api" or "/api/" in url),
            -int(bool(page.has_object_ref)),
            -int(bool(page.req_auth)),
            url,
            cell.owasp_category,
        )
        candidates.append(
            (
                rank,
                {
                    "page_id": page.id,
                    "url": url,
                    "method": method,
                    "owasp_category": cell.owasp_category,
                    "status": cell.status,
                    "access": "authenticated" if page.req_auth else "unknown_or_public",
                    "reason": reason,
                },
            )
        )

    candidates.sort(key=lambda item: item[0])
    return {
        "tool": "coverage_gaps",
        "run_id": run_id,
        "totals": totals,
        "next_actions": [item[1] for item in candidates[:limit]],
        "remaining": len(candidates),
        "truncated": len(candidates) > limit,
    }


def _build_web_enforce_directive(run_id: int) -> str:
    """Build the enforce-mode steering text appended to the agent's crawl context.

    Lists in-scope pages with their still-uncovered applicable OWASP categories
    and instructs the Test Lead to drive every cell to coverage, tagging each
    ``http_request`` with the ``owasp_category`` it exercises.
    """
    cells = _uncovered_web_cells(run_id)
    if not cells:
        return ""
    # Group by page
    grouped: dict[int, tuple[CrawledPage, list[str]]] = {}
    for page, cat, _status in cells:
        grouped.setdefault(page.id, (page, []))[1].append(cat)

    lines = [
        "=== ENFORCE COVERAGE MODE ===",
        "You MUST systematically test every in-scope page against each applicable "
        "OWASP Top-10 (2025) category in the checklist below. For EVERY http_request "
        "you send, set the `owasp_category` field to the category you are testing "
        "(A01–A10) so coverage is tracked. Work through the checklist methodically; "
        "do not call `done` until every page/category pair has been exercised, or "
        "you have documented why a category does not apply to a page.",
        "",
        "Coverage checklist (page → categories still to cover):",
    ]
    items = sorted(grouped.values(), key=lambda t: t[0].url)
    for page, cats in items[:60]:
        ordered = [c for c in OWASP_WEB_CATEGORIES if c in set(cats)]
        lines.append(f"  {page.url} → {', '.join(ordered)}")
    if len(items) > 60:
        lines.append(
            f"  … and {len(items) - 60} more pages (use context_tool page_list)."
        )
    return "\n".join(lines)


async def _enforce_web_coverage_loop(
    run_id: int,
    prober,
    *,
    max_attempts: int = _ENFORCE_DEFAULT_MAX_ATTEMPTS,
    time_budget_s: float = _ENFORCE_DEFAULT_TIME_BUDGET_S,
    stop_check=None,
    now_fn=None,
) -> dict:
    """Drive every still-uncovered web coverage cell to a terminal state.

    ``prober(page, category, current_status)`` must return ``(status, reason)``
    where status is ``covered`` / ``finding`` / ``skipped``.

    Mirrors ``_enforce_coverage_loop`` in ``api_scanner.py``.
    """
    import time as _time

    now_fn = now_fn or _time.monotonic
    if stop_check is None:

        def stop_check() -> bool:
            return False

    deadline = now_fn() + max(0.0, time_budget_s)
    stats: dict[str, Any] = {
        "attempted": 0,
        "covered": 0,
        "finding": 0,
        "skipped": 0,
        "budget_exhausted": False,
        "remaining": 0,
    }

    cells = _uncovered_web_cells(run_id)
    total = len(cells)
    events_svc.emit(
        run_id,
        {
            "type": "enforce_progress",
            "phase": "start",
            "remaining": total,
            "total": total,
            "message": f"Enforce mode: {total} coverage cell(s) to resolve.",
        },
    )

    for idx, (page, category, current_status) in enumerate(cells):
        if stop_check() or stats["attempted"] >= max_attempts or now_fn() >= deadline:
            stats["budget_exhausted"] = True
            break
        stats["attempted"] += 1
        try:
            status, reason = await prober(page, category, current_status)
        except Exception as exc:
            log.warning(
                "enforce prober error page=%s cat=%s: %s", page.id, category, exc
            )
            status, reason = "skipped", f"prober error: {exc}"
        if status not in ("covered", "finding", "skipped"):
            status, reason = "skipped", reason or "prober returned no decision"
        update_web_coverage_cell(
            run_id,
            page.id,
            category,
            status,
            skip_reason=reason if status == "skipped" else None,
        )
        stats[status] += 1
        if (idx + 1) % 5 == 0 or idx + 1 == total:
            events_svc.emit(
                run_id,
                {
                    "type": "enforce_progress",
                    "phase": "progress",
                    "remaining": total - (idx + 1),
                    "total": total,
                    "resolved": idx + 1,
                },
            )

    # Close out anything not reached within budget.
    for page, category, _status in _uncovered_web_cells(run_id):
        update_web_coverage_cell(
            run_id,
            page.id,
            category,
            "skipped",
            skip_reason="coverage budget exhausted",
        )
        stats["skipped"] += 1

    events_svc.emit(
        run_id,
        {
            "type": "enforce_progress",
            "phase": "complete",
            "covered": stats["covered"],
            "finding": stats["finding"],
            "skipped": stats["skipped"],
            "budget_exhausted": stats["budget_exhausted"],
            "message": (
                f"Enforce complete: {stats['covered']} covered, "
                f"{stats['finding']} finding, {stats['skipped']} skipped."
            ),
        },
    )
    log.info("enforce_web_coverage_loop: run_id=%s stats=%s", run_id, stats)
    return stats


def _make_web_enforce_prober(run_id: int, llm_cfg):  # noqa: ARG001
    """Build the default web enforce prober.

    Cells the broad agentic scan already exercised (``in_progress``) are promoted
    to ``covered``. For untouched (``not_started``) cells, a single cached LLM
    classification call per page decides, per category, whether it is genuinely
    not-applicable (→ ``skipped`` N/A reason) or applicable but not reached
    (→ ``skipped`` noting the budget was exhausted).
    """
    from aespa.services import llm as llm_svc

    # page_id → {category: (status, reason)}
    _cache: dict[int, dict[str, tuple[str, str]]] = {}

    async def _classify_page(page: CrawledPage) -> dict[str, tuple[str, str]]:
        try:
            applicable_raw = json.loads(page.owasp_applicable_json or "{}")
        except Exception:
            applicable_raw = {}
        cats = [c for c in OWASP_WEB_CATEGORIES if applicable_raw.get(c)]
        if not cats:
            return {}
        cat_lines = "\n".join(f"  - {c} ({OWASP_WEB_LABELS.get(c, c)})" for c in cats)
        prompt = (
            "You are triaging OWASP Top-10 (2025) test coverage for a single web "
            "page that an automated scan did not explicitly exercise. For each "
            "category below, decide whether it is genuinely applicable to this page.\n\n"
            f"Page URL: {page.url}\n"
            f"Title: {page.title or '(none)'}\n"
            f"Requires auth: {bool(page.req_auth)}\n"
            f"Takes user input: {bool(page.takes_input)}\n\n"
            f"Categories to triage:\n{cat_lines}\n\n"
            "Reply with ONLY a JSON object mapping each category id to "
            '{"applicable": true|false, "reason": "one short sentence"}. '
            "Mark applicable=false only when the category cannot meaningfully apply "
            "to this page. No prose, no markdown fences."
        )
        decisions: dict[str, tuple[str, str]] = {}
        try:
            raw = await llm_svc.plain_completion(llm_cfg, prompt)
            cleaned = re.sub(
                r"^```(?:json)?\s*", "", (raw or "").strip(), flags=re.IGNORECASE
            )
            cleaned = re.sub(r"\s*```$", "", cleaned.strip())
            m = re.search(r"\{.*\}", cleaned, re.DOTALL)
            parsed = json.loads(m.group(0)) if m else {}
        except Exception as exc:
            log.debug("enforce classify failed page=%s: %s", page.id, exc)
            parsed = {}
        for cat in cats:
            d = parsed.get(cat) if isinstance(parsed, dict) else None
            reason = (d or {}).get("reason", "") if isinstance(d, dict) else ""
            if isinstance(d, dict) and d.get("applicable") is False:
                decisions[cat] = (
                    "skipped",
                    f"not applicable: {reason}".strip().rstrip(":"),
                )
            else:
                note = reason or "applicable but not reached by the scan"
                decisions[cat] = ("skipped", f"not covered within scan budget — {note}")
        return decisions

    async def _prober(page: CrawledPage, category: str, current_status: str):
        if current_status == "in_progress":
            return ("covered", None)
        if page.id not in _cache:
            _cache[page.id] = await _classify_page(page)
        return _cache[page.id].get(
            category, ("skipped", "applicable but not reached by the scan")
        )

    return _prober


# ── Coverage matrix read ──────────────────────────────────────────────────────


def get_web_coverage_matrix(run_id: int) -> dict:
    """Return the full web workprogram matrix for a TestRun."""
    with Session(get_engine(), expire_on_commit=False) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return {}

        cells = list(
            s.exec(
                select(PageOwaspTest).where(PageOwaspTest.test_run_id == run_id)
            ).all()
        )

        if not cells:
            return {
                "run_id": run_id,
                "coverage_mode": getattr(run, "coverage_mode", "track") or "track",
                "categories": OWASP_WEB_CATEGORIES,
                "pages": [],
                "totals": {st: 0 for st in _STATUS_RANK},
                "seeded": False,
            }

        page_ids = {c.page_id for c in cells}
        pages = {
            p.id: p
            for p in s.exec(
                select(CrawledPage).where(CrawledPage.id.in_(page_ids))  # type: ignore[attr-defined]
            ).all()
        }

        findings = list(
            s.exec(select(ScanFinding).where(ScanFinding.test_run_id == run_id)).all()
        )
        coverage_mode = getattr(run, "coverage_mode", "track") or "track"

    # Build (page_id, owasp_category) → finding list; exclude deterministic probes
    finding_map: dict[tuple[int, str], list[dict]] = {}
    finding_by_id: dict[int, dict] = {}  # fallback for cells whose page_id diverged
    for f in findings:
        if f.finding_source == "deterministic_probe":
            continue
        fd = {
            "id": f.id,
            "title": f.title,
            "severity": f.severity,
            "owasp_category": f.owasp_category,
            "validation_status": f.validation_status,
            "description": f.description,
        }
        finding_by_id[f.id] = fd
        if f.page_id is None:
            continue
        key = (f.page_id, _normalize_owasp_category(f.owasp_category or ""))
        finding_map.setdefault(key, []).append(fd)

    # Build (page_id, category) → PageOwaspTest (keyed for fast lookup)
    cell_map: dict[tuple[int, str], PageOwaspTest] = {
        (c.page_id, c.owasp_category): c for c in cells
    }

    # Group pages by normalized URL pattern
    groups: dict[str, dict] = defaultdict(
        lambda: {"page_ids": [], "pages": [], "cells": {}}
    )
    for page in sorted(pages.values(), key=lambda p: p.url):
        pattern = _normalize_url(page.url)
        g = groups[pattern]
        g["page_ids"].append(page.id)
        g["pages"].append(page)
        for cat in OWASP_WEB_CATEGORIES:
            cell = cell_map.get((page.id, cat))
            if cell is None:
                continue
            cell_findings = finding_map.get((page.id, cat), [])
            # Use persisted status; fall back to derivation for legacy rows.
            status = (
                cell.status
                if cell.status != "not_started" or not cell_findings
                else "finding"
            )
            if not cell_findings and status == "not_started":
                pass  # leave as not_started
            try:
                fids_persisted: list = json.loads(cell.finding_ids_json or "[]")
            except Exception:
                fids_persisted = []
            # Merge persisted + live finding ids (in case a finding was added after last cell update)
            all_fids = list({f["id"] for f in cell_findings} | set(fids_persisted))
            # When cell_findings is empty but we have persisted IDs (page_id diverged),
            # resolve full finding details from finding_by_id so the UI can render writeups.
            if not cell_findings and all_fids:
                cell_findings = [
                    finding_by_id[fid] for fid in all_fids if fid in finding_by_id
                ]
            skip_reason = cell.skip_reason
            if cat not in g["cells"]:
                g["cells"][cat] = {
                    "status": status,
                    "skip_reason": skip_reason,
                    "finding_ids": all_fids,
                    "findings": cell_findings,
                }
            else:
                # Promote to highest status seen across pages in this group
                if _STATUS_RANK.get(status, 0) > _STATUS_RANK.get(
                    g["cells"][cat]["status"], 0
                ):
                    g["cells"][cat]["status"] = status
                    g["cells"][cat]["skip_reason"] = skip_reason
                g["cells"][cat]["finding_ids"].extend(
                    fid for fid in all_fids if fid not in g["cells"][cat]["finding_ids"]
                )
                g["cells"][cat]["findings"].extend(cell_findings)

    totals: dict[str, int] = {st: 0 for st in _STATUS_RANK}
    page_rows: list[dict] = []

    for pattern, g in sorted(groups.items()):
        if not g["cells"]:
            continue
        for cell in g["cells"].values():
            totals[cell["status"]] = totals.get(cell["status"], 0) + 1
        rep = g["pages"][0]
        page_rows.append(
            {
                "page_id": rep.id,
                "page_ids": g["page_ids"],
                "url": pattern,
                "title": rep.title or "",
                "req_auth": rep.req_auth,
                "cells": g["cells"],
            }
        )

    return {
        "run_id": run_id,
        "coverage_mode": coverage_mode,
        "categories": OWASP_WEB_CATEGORIES,
        "pages": page_rows,
        "totals": totals,
        "seeded": True,
    }


if __name__ == "__main__":
    assert _normalize_url("/#/customers/1") == "/#/customers/{id}"
    assert _normalize_url("/#/customers/2") == "/#/customers/{id}"
    assert _normalize_url("/api/users/123/posts/456") == "/api/users/{id}/posts/{id}"
    assert (
        _normalize_url("/api/v2/items/3e4d58e9-f9b6-4f1e-aedc-b4fc8a3e37a8")
        == "/api/v2/items/{id}"
    )
    assert _normalize_url("/about") == "/about"
    # Query string normalisation
    assert _normalize_url("/search?id=42") == "/search?id={id}"
    assert _normalize_url("/items?page=2&user_id=99") == "/items?page={id}&user_id={id}"
    assert _normalize_url("/items?q=hello&page=3") == "/items?q=hello&page={id}"
    assert (
        _normalize_url("/items?token=3e4d58e9-f9b6-4f1e-aedc-b4fc8a3e37a8")
        == "/items?token={id}"
    )
    assert _normalize_url("/about?ref=home") == "/about?ref=home"
    print("ok")
