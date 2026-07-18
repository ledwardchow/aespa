"""API-scan orchestration.

Provides the full Test-Lead + Specialist + Validator agentic scan pipeline for
``ApiTestRun``s — wiring the same ``_do_agentic_thinking_loop`` used by the web
scanner with API-specific overrides:

  * ``_API_THINKING_AGENT_SYSTEM`` system prompt (OWASP API Top 10 focused)
  * ``_api_context_tool_fn``  — delegates ``endpoint_list / endpoint_detail /
      collection_info / finding_list`` to the API context tool and routes a
      safe subset (history_search, traffic_search, …) to the shared scanner
      context tool
  * ``_make_post_finding_fn`` post-save hook — maps the OWASP category to the
    OWASP API Top-10 field on every finding and updates the coverage matrix
    (``api_test_run_id`` is already set at creation time in API mode)
  * No browser/Playwright needed — REST APIs are all httpx
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    ApiCollection,
    ApiCredential,
    ApiEndpoint,
    ApiEndpointTest,
    ApiTestRun,
    ScanFinding,
)
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import scanner_sessions
from aespa.services.prompts.test_lead import (
    _API_THINKING_AGENT_SYSTEM,
    get_api_test_lead_tools,
)

log = logging.getLogger(__name__)

_UTC = timezone.utc

# ── In-memory state ───────────────────────────────────────────────────────────

_scan_tasks: dict[int, asyncio.Task] = {}  # api_run_id → running asyncio.Task
_stop_requested: set[int] = set()


# ── OWASP API Top 10 (2023) ───────────────────────────────────────────────────

OWASP_API_CATEGORIES: list[str] = [
    "API1",  # BOLA
    "API2",  # Broken Authentication
    "API3",  # BOPLA (Broken Object Property Level Authorization)
    "API4",  # Unrestricted Resource Consumption
    "API5",  # BFLA (Broken Function Level Authorization)
    "API6",  # Unrestricted Access to Sensitive Business Flows
    "API7",  # SSRF
    "API8",  # Security Misconfiguration
    "API9",  # Improper Inventory Management
    "API10",  # Unsafe Consumption of APIs
]

OWASP_API_LABELS: dict[str, str] = {
    "API1": "BOLA",
    "API2": "Broken Auth",
    "API3": "BOPLA",
    "API4": "Resource Consumption",
    "API5": "BFLA",
    "API6": "Business Flows",
    "API7": "SSRF",
    "API8": "Misconfiguration",
    "API9": "Inventory",
    "API10": "Unsafe Consumption",
}


def _applicable_categories(endpoint: ApiEndpoint) -> list[str]:
    """Return the OWASP API categories applicable to this endpoint (heuristic)."""
    import re as _re

    cats: list[str] = []
    method = (endpoint.method or "GET").upper()
    path = endpoint.path or ""

    # API1 BOLA — endpoints with a path parameter (/{id}, /{uuid}, etc.)
    if _re.search(r"\{[^}]+\}", path):
        cats.append("API1")

    # API2 Broken Authentication — all endpoints
    cats.append("API2")

    # API3 BOPLA — write operations that modify objects
    if method in ("PUT", "PATCH"):
        cats.append("API3")

    # API4 Unrestricted Resource Consumption — all endpoints
    cats.append("API4")

    # API5 BFLA — all endpoints (admin paths get higher weight, but we track all)
    cats.append("API5")

    # API6 Business Flows — POST endpoints (create/action verbs)
    if method in ("POST", "PUT", "PATCH"):
        cats.append("API6")

    # API7 SSRF — endpoints likely to accept URL-like inputs
    if any(
        kw in path.lower()
        for kw in (
            "url",
            "uri",
            "link",
            "redirect",
            "webhook",
            "callback",
            "proxy",
            "fetch",
            "import",
        )
    ):
        cats.append("API7")
    try:
        params = json.loads(endpoint.parameters_json or "[]")
        if any(
            any(
                kw in str(p.get("name", "")).lower()
                for kw in ("url", "uri", "link", "target", "src", "redirect")
            )
            for p in params
        ):
            cats.append("API7")
    except Exception:
        pass

    # API8 Security Misconfiguration — all endpoints
    cats.append("API8")

    # API9 Improper Inventory Management — every endpoint (track exposure)
    cats.append("API9")

    # API10 Unsafe Consumption of APIs — all endpoints
    cats.append("API10")

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for c in cats:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


# ── Coverage matrix helpers ───────────────────────────────────────────────────

# ── Endpoint cache (populated at scan start, cleared at scan end) ─────────────────

# api_run_id → (collection_id, [ApiEndpoint, ...])
_endpoint_cache: dict[int, tuple[int, list]] = {}


def seed_coverage_matrix(api_run_id: int) -> int:
    """Create ``ApiEndpointTest`` rows for every in-scope endpoint × applicable category.

    Idempotent — skips cells that already exist.  Returns the number of new cells created.
    Also populates the endpoint cache so the traffic hook can match URLs without extra
    DB round-trips.
    """
    with Session(get_engine(), expire_on_commit=False) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            return 0
        endpoints = list(
            s.exec(
                select(ApiEndpoint)
                .where(ApiEndpoint.collection_id == run.collection_id)
                .where(ApiEndpoint.in_scope == True)  # noqa: E712
            ).all()
        )
        collection_id = run.collection_id
        # Load existing cells so we can skip duplicates
        existing = set(
            (row.endpoint_id, row.owasp_api_category)
            for row in s.exec(
                select(ApiEndpointTest).where(
                    ApiEndpointTest.api_test_run_id == api_run_id
                )
            ).all()
        )
        created = 0
        now = datetime.now(_UTC)
        for ep in endpoints:
            for cat in _applicable_categories(ep):
                if (ep.id, cat) in existing:
                    continue
                cell = ApiEndpointTest(
                    api_test_run_id=api_run_id,
                    endpoint_id=ep.id,
                    owasp_api_category=cat,
                    status="not_started",
                    last_updated=now,
                )
                s.add(cell)
                created += 1
        s.commit()
    # Populate the endpoint cache for use by the traffic hook.
    _endpoint_cache[api_run_id] = (collection_id, endpoints)
    log.info(
        "seed_coverage_matrix: api_run_id=%s created=%d cells", api_run_id, created
    )
    return created


# Status precedence: a higher-ranked status must not be downgraded.
_STATUS_RANK: dict[str, int] = {
    "not_started": 0,
    "in_progress": 1,
    "covered": 2,
    "skipped": 2,
    "finding": 3,
}


def update_coverage_cell(
    api_run_id: int,
    endpoint_id: int,
    owasp_api_category: str,
    status: str,
    finding_id: int | None = None,
    skip_reason: str | None = None,
) -> None:
    """Upsert a coverage cell.  If ``finding_id`` is given it is appended to finding_ids_json.

    Status is never downgraded: once a cell is ``finding`` it cannot go back to
    ``covered``; once ``in_progress`` it cannot go back to ``not_started``, etc.
    ``skip_reason`` (used by enforce mode) is recorded whenever supplied.
    """
    with Session(get_engine()) as s:
        cell = s.exec(
            select(ApiEndpointTest)
            .where(ApiEndpointTest.api_test_run_id == api_run_id)
            .where(ApiEndpointTest.endpoint_id == endpoint_id)
            .where(ApiEndpointTest.owasp_api_category == owasp_api_category)
        ).first()
        if cell is None:
            cell = ApiEndpointTest(
                api_test_run_id=api_run_id,
                endpoint_id=endpoint_id,
                owasp_api_category=owasp_api_category,
                status=status,
                last_updated=datetime.now(_UTC),
            )
        else:
            # Only upgrade, never downgrade.
            current_rank = _STATUS_RANK.get(cell.status, 0)
            new_rank = _STATUS_RANK.get(status, 0)
            if new_rank > current_rank:
                cell.status = status
                cell.last_updated = datetime.now(_UTC)
            elif finding_id is None and skip_reason is None:
                # Nothing to update.
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
    # Emit a live SSE event only for high-value status changes (finding/covered/skipped).
    # in_progress is updated too frequently to justify SSE noise; the 5s poll handles it.
    if status in ("finding", "covered", "skipped"):
        events_svc.emit(
            api_run_id,
            {
                "type": "coverage_update",
                "endpoint_id": endpoint_id,
                "owasp_api_category": owasp_api_category,
                "status": status,
                "finding_id": finding_id,
            },
        )


def _make_post_probe_fn(api_run_id: int):
    """Return a callable ``(url, method, owasp_category) → None`` for per-category
    in_progress tracking.

    Called from the http_request executor after each API probe.  Uses the
    OWASP category the LLM explicitly declared on the tool call, so only the
    specific cell being tested flips to ``in_progress``.
    """

    def _post_probe(url: str, method: str, owasp_category: str) -> None:
        cached = _endpoint_cache.get(api_run_id)
        if cached is None:
            return
        _, endpoints = cached
        if not endpoints:
            return
        with Session(get_engine()) as s:
            coll = (
                s.get(ApiCollection, endpoints[0].collection_id) if endpoints else None
            )
            base_url = (coll.base_url if coll else "").rstrip("/")
        ep = _match_endpoint_for_url(url, endpoints, base_url)
        if ep is None:
            return
        cat = owasp_category.strip().upper()
        update_coverage_cell(api_run_id, ep.id, cat, "in_progress")

    return _post_probe


def mark_all_cells_covered(api_run_id: int) -> None:
    """At scan completion, promote ``in_progress`` cells to ``covered``.

    Only ``in_progress`` cells are promoted — these are endpoints the scanner
    actually sent requests to but raised no finding for.  ``not_started`` cells
    are left alone: they mean the scanner never touched that endpoint.
    """
    with Session(get_engine()) as s:
        cells = list(
            s.exec(
                select(ApiEndpointTest)
                .where(ApiEndpointTest.api_test_run_id == api_run_id)
                .where(ApiEndpointTest.status == "in_progress")
            ).all()
        )
        now = datetime.now(_UTC)
        for cell in cells:
            cell.status = "covered"
            cell.last_updated = now
            s.add(cell)
        s.commit()
    log.info(
        "mark_in_progress_to_covered: api_run_id=%s promoted=%d", api_run_id, len(cells)
    )


# ── Enforce coverage mode (Slice 8) ───────────────────────────────────────────

_ENFORCE_DEFAULT_MAX_ATTEMPTS = 300
_ENFORCE_DEFAULT_TIME_BUDGET_S = 1800.0

# Cells in these states still need work; everything else is terminal.
_UNCOVERED_STATES = ("not_started", "in_progress")


def _uncovered_cells(api_run_id: int) -> list[tuple[ApiEndpoint, str, str]]:
    """Return ``[(endpoint, category, current_status)]`` for non-terminal cells."""
    with Session(get_engine(), expire_on_commit=False) as s:
        cells = list(
            s.exec(
                select(ApiEndpointTest)
                .where(ApiEndpointTest.api_test_run_id == api_run_id)
                .where(ApiEndpointTest.status.in_(_UNCOVERED_STATES))  # type: ignore[attr-defined]
            ).all()
        )
        ep_ids = {c.endpoint_id for c in cells}
        endpoints = (
            {
                ep.id: ep
                for ep in s.exec(
                    select(ApiEndpoint).where(ApiEndpoint.id.in_(ep_ids))  # type: ignore[attr-defined]
                ).all()
            }
            if ep_ids
            else {}
        )
    out: list[tuple[ApiEndpoint, str, str]] = []
    for c in cells:
        ep = endpoints.get(c.endpoint_id)
        if ep is not None:
            out.append((ep, c.owasp_api_category, c.status))
    return out


def _build_enforce_directive(api_run_id: int) -> str:
    """Build the enforce-mode steering text appended to the agent's crawl context.

    Lists the in-scope endpoints with their applicable OWASP API categories and
    instructs the Test Lead to drive every cell to coverage, tagging each
    ``http_request`` with the ``owasp_category`` it exercises (so ``post_probe_fn``
    flips the right cell to ``in_progress``)."""
    cells = _uncovered_cells(api_run_id)
    if not cells:
        return ""
    grouped: dict[int, tuple[ApiEndpoint, list[str]]] = {}
    for ep, cat, _status in cells:
        grouped.setdefault(ep.id, (ep, []))[1].append(cat)

    lines = [
        "=== ENFORCE COVERAGE MODE ===",
        "You MUST systematically test every in-scope endpoint against each "
        "applicable OWASP API Top-10 category in the checklist below. For EVERY "
        "http_request you send, set the `owasp_category` field to the category "
        "you are testing (API1–API10) so coverage is tracked. Work through the "
        "checklist methodically; do not call `done` until every endpoint/category "
        "pair has been exercised, or you have documented why a category does not "
        "apply to an endpoint.",
        "",
        "Coverage checklist (endpoint → categories still to cover):",
    ]
    items = sorted(grouped.values(), key=lambda t: (t[0].path, t[0].method))
    for ep, cats in items[:60]:
        ordered = [c for c in OWASP_API_CATEGORIES if c in set(cats)]
        lines.append(f"  [{ep.method}] {ep.path} → {', '.join(ordered)}")
    if len(items) > 60:
        lines.append(f"  … and {len(items) - 60} more endpoints (use endpoint_list).")
    return "\n".join(lines)


async def _enforce_coverage_loop(
    api_run_id: int,
    prober,
    *,
    max_attempts: int = _ENFORCE_DEFAULT_MAX_ATTEMPTS,
    time_budget_s: float = _ENFORCE_DEFAULT_TIME_BUDGET_S,
    stop_check=None,
    now_fn=None,
) -> dict:
    """Drive every still-uncovered coverage cell to a terminal state.

    For each uncovered ``(endpoint, category)`` cell, ``prober(endpoint, category,
    current_status)`` is awaited and must return ``(status, reason)`` where
    ``status`` is one of ``covered`` / ``finding`` / ``skipped`` and ``reason`` is
    an optional string (recorded as the cell's skip reason for skips).

    The loop respects three budgets — a max attempt count, a wall-clock budget,
    and an optional ``stop_check`` (defaults to the module stop-request set).
    Any cells still uncovered when a budget is hit are marked ``skipped`` with
    reason "coverage budget exhausted". Returns a stats dict.
    """
    import time as _time

    now_fn = now_fn or _time.monotonic
    if stop_check is None:

        def stop_check() -> bool:
            return api_run_id in _stop_requested

    deadline = now_fn() + max(0.0, time_budget_s)
    stats: dict[str, Any] = {
        "attempted": 0,
        "covered": 0,
        "finding": 0,
        "skipped": 0,
        "budget_exhausted": False,
        "remaining": 0,
    }

    cells = _uncovered_cells(api_run_id)
    total = len(cells)
    events_svc.emit(
        api_run_id,
        {
            "type": "enforce_progress",
            "phase": "start",
            "remaining": total,
            "total": total,
            "message": f"Full mode: {total} coverage cell(s) to resolve.",
        },
    )

    for idx, (endpoint, category, current_status) in enumerate(cells):
        if stop_check() or stats["attempted"] >= max_attempts or now_fn() >= deadline:
            stats["budget_exhausted"] = True
            break
        stats["attempted"] += 1
        try:
            status, reason = await prober(endpoint, category, current_status)
        except Exception as exc:  # a failing prober must not abort the whole loop
            log.warning(
                "enforce prober error ep=%s cat=%s: %s", endpoint.id, category, exc
            )
            status, reason = "skipped", f"prober error: {exc}"
        if status not in ("covered", "finding", "skipped"):
            status, reason = "skipped", reason or "prober returned no decision"
        update_coverage_cell(
            api_run_id,
            endpoint.id,
            category,
            status,
            skip_reason=reason if status == "skipped" else None,
        )
        stats[status] += 1
        if (idx + 1) % 5 == 0 or idx + 1 == total:
            events_svc.emit(
                api_run_id,
                {
                    "type": "enforce_progress",
                    "phase": "progress",
                    "remaining": total - (idx + 1),
                    "total": total,
                    "resolved": idx + 1,
                },
            )

    # Close out anything not reached within budget so no cell is left dangling.
    for endpoint, category, _status in _uncovered_cells(api_run_id):
        update_coverage_cell(
            api_run_id,
            endpoint.id,
            category,
            "skipped",
            skip_reason="coverage budget exhausted",
        )
        stats["skipped"] += 1

    events_svc.emit(
        api_run_id,
        {
            "type": "enforce_progress",
            "phase": "complete",
            "covered": stats["covered"],
            "finding": stats["finding"],
            "skipped": stats["skipped"],
            "budget_exhausted": stats["budget_exhausted"],
            "message": (
                f"Full coverage complete: {stats['covered']} covered, "
                f"{stats['finding']} finding, {stats['skipped']} skipped."
            ),
        },
    )
    log.info("enforce_coverage_loop: api_run_id=%s stats=%s", api_run_id, stats)
    return stats


def _make_enforce_prober(api_run_id: int, llm_cfg, base_url: str):
    """Build the default enforce prober.

    Cells the broad agentic scan already exercised (``in_progress``) are promoted
    to ``covered``. For untouched (``not_started``) cells, a single LLM
    classification call per endpoint (cached) decides, per category, whether it is
    genuinely not-applicable (→ ``skipped`` with an N/A reason) or applicable but
    not reached (→ ``skipped`` noting it was not covered within budget). This
    guarantees every cell ends with a recorded rationale; the actual driving of
    coverage happens via the steered agent during the main loop.
    """
    from aespa.services import llm as llm_svc

    # endpoint_id → {category: (status, reason)}
    _cache: dict[int, dict[str, tuple[str, str]]] = {}

    async def _classify_endpoint(endpoint: ApiEndpoint) -> dict[str, tuple[str, str]]:
        import re

        cats = _applicable_categories(endpoint)
        cat_lines = "\n".join(f"  - {c} ({OWASP_API_LABELS.get(c, c)})" for c in cats)
        prompt = (
            "You are triaging OWASP API Security Top-10 (2023) test coverage for a "
            "single REST API endpoint that an automated scan did not explicitly "
            "exercise. For each category below, decide whether it is genuinely "
            "applicable to this endpoint.\n\n"
            f"Endpoint: [{endpoint.method}] {endpoint.path}\n"
            f"Auth required: {bool(endpoint.auth_required)}\n"
            f"Summary: {endpoint.summary or '(none)'}\n\n"
            f"Categories to triage:\n{cat_lines}\n\n"
            "Reply with ONLY a JSON object mapping each category id to "
            '{"applicable": true|false, "reason": "one short sentence"}. '
            "Mark applicable=false only when the category cannot meaningfully apply "
            "to this endpoint (e.g. SSRF on an endpoint that takes no URL-like "
            "input). No prose, no markdown fences."
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
            log.debug("enforce classify failed ep=%s: %s", endpoint.id, exc)
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

    async def _prober(endpoint: ApiEndpoint, category: str, current_status: str):
        # The agent already sent requests for this cell → it counts as covered.
        if current_status == "in_progress":
            return ("covered", None)
        if endpoint.id not in _cache:
            _cache[endpoint.id] = await _classify_endpoint(endpoint)
        return _cache[endpoint.id].get(
            category, ("skipped", "applicable but not reached by the scan")
        )

    return _prober


def get_coverage_matrix(api_run_id: int) -> dict:
    """Return the full coverage matrix for an ApiTestRun as a dict."""
    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            return {}
        endpoints = list(
            s.exec(
                select(ApiEndpoint)
                .where(ApiEndpoint.collection_id == run.collection_id)
                .where(ApiEndpoint.in_scope == True)  # noqa: E712
                .order_by(ApiEndpoint.path, ApiEndpoint.method)
            ).all()
        )
        cells = list(
            s.exec(
                select(ApiEndpointTest).where(
                    ApiEndpointTest.api_test_run_id == api_run_id
                )
            ).all()
        )
        findings = list(
            s.exec(
                select(ScanFinding).where(ScanFinding.api_test_run_id == api_run_id)
            ).all()
        )

    # Build a lookup: (endpoint_id, category) → cell
    cell_lookup: dict[tuple[int, str], ApiEndpointTest] = {
        (c.endpoint_id, c.owasp_api_category): c for c in cells
    }
    # Build a lookup: finding_id → summary dict (for the detail panel)
    finding_lookup: dict[int, dict] = {
        f.id: {
            "id": f.id,
            "title": f.title,
            "severity": f.severity,
            "owasp_api_category": f.owasp_api_category,
            "validation_status": f.validation_status,
            "description": f.description,
        }
        for f in findings
        if f.id is not None
    }

    totals: dict[str, int] = {
        s: 0 for s in ("not_started", "in_progress", "covered", "skipped", "finding")
    }
    endpoint_rows: list[dict] = []
    for ep in endpoints:
        ep_cats = _applicable_categories(ep)
        ep_cells: dict[str, dict] = {}
        for cat in ep_cats:
            cell = cell_lookup.get((ep.id, cat))
            if cell:
                cell_status = cell.status
                try:
                    fids = json.loads(cell.finding_ids_json or "[]")
                except Exception:
                    fids = []
            else:
                cell_status = "not_started"
                fids = []
            ep_cells[cat] = {
                "status": cell_status,
                "finding_ids": fids,
                "findings": [finding_lookup[i] for i in fids if i in finding_lookup],
            }
            totals[cell_status] = totals.get(cell_status, 0) + 1

        endpoint_rows.append(
            {
                "endpoint_id": ep.id,
                "method": ep.method,
                "path": ep.path,
                "auth_required": ep.auth_required,
                "prereq_can_test": ep.prereq_can_test,
                "prereq_can_test_auth": ep.prereq_can_test_auth,
                "prereq_notes": ep.prereq_notes,
                "cells": ep_cells,
            }
        )

    return {
        "run_id": api_run_id,
        "coverage_mode": run.coverage_mode,
        "categories": OWASP_API_CATEGORIES,
        "endpoints": endpoint_rows,
        "totals": totals,
    }


def _match_endpoint_for_url(
    affected_url: str,
    endpoints: list[ApiEndpoint],
    collection_base_url: str,
) -> ApiEndpoint | None:
    """Find the best-matching endpoint for a finding's affected_url.

    Strategy:
    1. Extract path from the URL.
    2. For each endpoint, convert path-template params (``{id}``) to a regex.
    3. Return the longest-matching endpoint path.
    """
    import re as _re
    from urllib.parse import urlparse

    try:
        parsed = urlparse(affected_url)
        url_path = parsed.path.rstrip("/") or "/"
    except Exception:
        return None

    best: ApiEndpoint | None = None
    best_len = -1

    for ep in endpoints:
        ep_path = ep.path.rstrip("/") or "/"
        # Convert {param} → a regex segment
        pattern = _re.sub(
            r"\{[^}]+\}",
            r"[^/]+",
            _re.escape(ep_path).replace(r"\{", "{").replace(r"\}", "}"),
        )
        try:
            if _re.fullmatch(pattern, url_path) and len(ep_path) > best_len:
                best = ep
                best_len = len(ep_path)
        except Exception:
            pass

    return best


# ── Scope helpers ─────────────────────────────────────────────────────────────


def _scope_hosts_for_run(api_run_id: int) -> list[str]:
    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            return []
        coll = s.get(ApiCollection, run.collection_id)
        if coll is None:
            return []
        try:
            return json.loads(coll.scope_hosts or "[]")
        except Exception:
            return []


def _api_check_scope(url: str, api_run_id: int) -> str | None:
    """Return an error string if ``url`` is out of scope, else None."""
    hosts = _scope_hosts_for_run(api_run_id)
    if not hosts:
        return None  # no scope restriction
    from urllib.parse import urlparse

    host = urlparse(url).hostname or ""
    if not any(host == h or host.endswith("." + h) for h in hosts):
        return f"Out of scope: {url} (allowed: {hosts})"
    return None


# ── Session seeding ───────────────────────────────────────────────────────────


def seed_sessions_from_credentials(api_run_id: int) -> int:
    """Create ``ScannerSession`` rows from ``ApiCredential`` rows for this run.

    Returns the number of sessions seeded.
    """
    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            return 0
        creds = list(
            s.exec(
                select(ApiCredential).where(
                    ApiCredential.collection_id == run.collection_id
                )
            ).all()
        )

    seeded = 0
    scanner_sessions.ensure_anonymous_session(
        api_run_id, source="api_scanner", run_kind="api"
    )
    seeded += 1

    for cred in creds:
        label = cred.label or f"{cred.scheme}_{cred.id}"
        extra_headers: dict[str, str] = {}
        cookies: dict[str, str] = {}

        scheme = (cred.scheme or "bearer").lower()
        if scheme in ("bearer", "apikey", "header"):
            extra_headers[cred.name or "Authorization"] = (
                f"Bearer {cred.value}"
                if scheme == "bearer" and not cred.value.lower().startswith("bearer ")
                else cred.value
            )
        elif scheme == "cookie":
            parts = cred.value.split("=", 1)
            cookie_name = (
                parts[0].strip() if len(parts) == 2 else cred.name or "session"
            )
            cookie_val = parts[1].strip() if len(parts) == 2 else cred.value
            cookies[cookie_name] = cookie_val
        elif scheme == "basic":
            import base64 as _b64

            encoded = _b64.b64encode(cred.value.encode()).decode()
            extra_headers["Authorization"] = f"Basic {encoded}"

        kind = (
            "bearer"
            if scheme == "bearer"
            else ("cookie" if scheme == "cookie" else "mixed")
        )
        scanner_sessions.upsert_session(
            api_run_id,
            label=label,
            kind=kind,
            account_label=cred.label,
            username=cred.label or f"cred_{cred.id}",
            credential_id=cred.id,
            source="api_scanner",
            cookies=cookies,
            extra_headers=extra_headers,
            metadata={"scheme": cred.scheme, "scope": cred.scope},
            run_kind="api",
        )
        seeded += 1

    return seeded


# ── Context tool override ─────────────────────────────────────────────────────

# API-specific sub-commands routed to the alice context tool.
_API_CONTEXT_COMMANDS = frozenset(
    {
        "endpoint_list",
        "endpoint_detail",
        "collection_info",
        "finding_list",
    }
)

# Sub-commands that must fall through to the shared scanner context tool.
_SHARED_CONTEXT_COMMANDS = frozenset(
    {
        "history_search",
        "traffic_search",
        "compare_responses",
        "mutate_request",
        "extract_entities",
    }
)

# These web-crawl inventory commands key their data solely by TestRun id. API
# run ids occupy a separate integer sequence and can collide with TestRun ids,
# so allowing either command here could expose an unrelated web run's intel.
_BLOCKED_API_CONTEXT_COMMANDS = frozenset({"target_inventory", "search_assets"})


def _make_api_context_tool_fn(collection_id: int, api_run_id: int):
    """Return a context_tool_fn that combines API inventory + shared tools."""
    from aespa.services.alice import _run_api_context_tool
    from aespa.services.scanner import _run_thinking_context_tool

    def _fn(
        tool_name: str,
        args: dict,
        *,
        pages_snapshot=None,
        findings_snapshot=None,
        history=None,
        run_id=None,
        base_url="",
    ) -> dict[str, Any]:
        if tool_name in _BLOCKED_API_CONTEXT_COMMANDS:
            return {
                "tool": tool_name,
                "error": (
                    f"{tool_name} is unavailable for API scans because it contains "
                    "web-crawl inventory. Use endpoint_list or endpoint_detail instead."
                ),
                "available_tools": sorted(
                    _API_CONTEXT_COMMANDS | _SHARED_CONTEXT_COMMANDS
                ),
            }

        # API inventory commands
        if tool_name in _API_CONTEXT_COMMANDS:
            return _run_api_context_tool(collection_id, api_run_id, tool_name, args)

        if tool_name in _SHARED_CONTEXT_COMMANDS:
            return _run_thinking_context_tool(
                tool_name,
                args,
                pages_snapshot=pages_snapshot or [],
                findings_snapshot=findings_snapshot or [],
                history=history or [],
                run_id=run_id,
                base_url=base_url,
            )

        return {
            "tool": tool_name,
            "error": "unknown or unavailable context tool for API scans",
            "available_tools": sorted(_API_CONTEXT_COMMANDS | _SHARED_CONTEXT_COMMANDS),
        }

    return _fn


# ── Finding post-save hook ────────────────────────────────────────────────────

# Maps common OWASP Web Top 10 categories (used by write_finding) to the
# best-fit OWASP API Top 10 category.
_OWASP_WEB_TO_API: dict[str, str] = {
    "A01": "API5",  # Broken Access Control → BFLA
    "A02": "API2",  # Cryptographic Failures → Broken Authentication
    "A03": "API10",  # Injection → Unsafe Consumption
    "A04": "API8",  # Insecure Design → Misconfiguration
    "A05": "API8",  # Security Misconfiguration
    "A06": "API9",  # Supply Chain → Improper Inventory
    "A07": "API2",  # Identification & Authentication → Broken Auth
    "A08": "API3",  # Software & Data Integrity → Mass Assignment
    "A09": "API8",  # Security Logging → Misconfiguration
    "A10": "API7",  # SSRF
}


def _make_post_finding_fn(api_run_id: int):
    """Return a hook that derives ``owasp_api_category`` for each finding and
    updates the coverage matrix cell for the finding's endpoint + category.

    ``api_test_run_id`` is already set at creation time (the finding writers run
    in API mode), so this hook only fills in the API-specific OWASP category,
    which the shared finding builder doesn't know about."""

    def _fn(finding: ScanFinding) -> None:
        with Session(get_engine()) as s:
            f = s.get(ScanFinding, finding.id)
            if f is None:
                return
            owasp = str(f.owasp_category or "").strip()
            # If the LLM wrote API1-API10 directly into owasp_category, move it.
            if owasp.upper().startswith("API"):
                f.owasp_api_category = owasp.upper()
            elif owasp.upper() in _OWASP_WEB_TO_API:
                f.owasp_api_category = _OWASP_WEB_TO_API[owasp.upper()]
            s.add(f)
            s.commit()
            s.refresh(f)
            owasp_api_cat = f.owasp_api_category
            affected_url = f.affected_url
            finding_id = f.id

        # Update the coverage matrix cell for this finding.
        if owasp_api_cat:
            with Session(get_engine()) as s:
                run = s.get(ApiTestRun, api_run_id)
                if run is not None:
                    endpoints = list(
                        s.exec(
                            select(ApiEndpoint)
                            .where(ApiEndpoint.collection_id == run.collection_id)
                            .where(ApiEndpoint.in_scope == True)  # noqa: E712
                        ).all()
                    )
                    coll = s.get(ApiCollection, run.collection_id)
                    base_url = (coll.base_url if coll else "").rstrip("/")

            ep = _match_endpoint_for_url(affected_url or "", endpoints, base_url)
            if ep is not None:
                update_coverage_cell(
                    api_run_id,
                    ep.id,
                    owasp_api_cat,
                    "finding",
                    finding_id=finding_id,
                )

    return _fn


# ── Discovered-credential persistence ─────────────────────────────────────────


def _make_persist_credential_fn(collection_id: int, api_run_id: int):
    """Return a hook that saves a credential discovered mid-scan to the API
    collection (as an ``ApiCredential``), not to a ``Site``.

    The shared scanner loop, when run for an ``ApiTestRun``, would otherwise call
    ``_maybe_persist_discovered_credential`` which resolves ``run_id`` as a
    ``TestRun`` id and writes a site ``Credential`` — wrong table, and (because
    test_run/api_test_run ids overlap) attached to an unrelated site.

    Discovered credentials are username/password test accounts validated against a
    login endpoint, so they map to ``scheme="login"`` with ``value="user:pass"`` —
    the same representation doc-derived login creds use (see ``api_docs.py``).
    """

    def _fn(username: str, password: str, login_url: str | None) -> None:
        value = f"{username}:{password}"
        with Session(get_engine()) as s:
            existing = s.exec(
                select(ApiCredential)
                .where(ApiCredential.collection_id == collection_id)
                .where(ApiCredential.value == value)
            ).first()
            if existing is not None:
                return
            cred = ApiCredential(
                collection_id=collection_id,
                scheme="login",
                name="username",
                value=value,
                label=username,
                scope="global",
                auth_endpoint=login_url or None,
            )
            s.add(cred)
            s.commit()

        log.info(
            "Discovered API credential saved: username=%r collection_id=%s",
            username,
            collection_id,
        )
        events_svc.emit(
            api_run_id,
            {
                "type": "credential_discovered",
                "username": username,
                "login_url": login_url,
                "message": (
                    f"Valid credential discovered: {username!r}. "
                    "Saved to the API collection's credential store as a login account."
                ),
            },
        )

    return _fn


# ── Crawl context builder ─────────────────────────────────────────────────────


def _build_api_crawl_context(api_run_id: int) -> str:
    """Build the initial LLM context string from the API collection + endpoints."""
    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            return ""
        coll = s.get(ApiCollection, run.collection_id)
        if coll is None:
            return ""
        endpoints = list(
            s.exec(
                select(ApiEndpoint)
                .where(ApiEndpoint.collection_id == coll.id)
                .where(ApiEndpoint.in_scope == True)  # noqa: E712
                .order_by(ApiEndpoint.path, ApiEndpoint.method)
            ).all()
        )
        creds = list(
            s.exec(
                select(ApiCredential).where(ApiCredential.collection_id == coll.id)
            ).all()
        )

    lines: list[str] = [
        f"API Collection: {coll.name}",
        f"Base URL: {coll.base_url}",
    ]
    if coll.description:
        lines.append(f"Description: {coll.description}")

    auth_notes: list[str] = []
    for cred in creds:
        auth_notes.append(
            f"  - [{cred.scheme}] label={cred.label or cred.scheme}  scope={cred.scope}"
        )
    if auth_notes:
        lines.append("Credentials available:\n" + "\n".join(auth_notes))

    ep_summary: list[str] = []
    for ep in endpoints[:80]:
        line = f"  [{ep.method}] {ep.path}"
        if ep.auth_required:
            line += " (auth)"
        if ep.summary:
            line += f" — {ep.summary}"
        ep_summary.append(line)
    if len(endpoints) > 80:
        ep_summary.append(f"  … and {len(endpoints) - 80} more (use endpoint_list)")
    if ep_summary:
        lines.append(
            f"In-scope endpoints ({len(endpoints)} total):\n" + "\n".join(ep_summary)
        )

    try:
        readiness = json.loads(coll.readiness_json or "{}")
        if readiness.get("overall") == "not_ready":
            lines.append(f"Readiness warning: {readiness.get('notes', '')}")
    except Exception:
        pass

    # Append this run's fresh SAST-lead copies. Collection originals are never
    # mutated by a dynamic scan, so every run independently reassesses them.
    try:
        from aespa.services.scan_leads import format_leads_for_run

        leads_block = format_leads_for_run("api", api_run_id)
        if leads_block:
            lines.append(leads_block)
    except Exception:
        pass

    return "\n\n".join(lines)


# ── Main scan entry points ────────────────────────────────────────────────────


async def _do_api_thinking_scan(api_run_id: int) -> None:
    """Full Test-Lead + Specialist + Validator scan for an ApiTestRun.

    Loads API collection data, seeds sessions, then drives
    ``_do_agentic_thinking_loop`` with API-mode overrides — no Playwright needed.
    """
    from aespa.services import llm as llm_svc
    from aespa.services.scanner import (
        _do_agentic_thinking_loop,
        _load_findings_snapshot,
        _make_scanner_client,
        _scanner_global_header_var,
        _scanner_proxy_var,
    )
    from aespa.services.settings import (
        get_global_http_header_config,
        get_llm_config_for_role,
        get_run_scanner_policy,
        get_specialist_agent_config,
        get_upstream_proxy_config,
    )

    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            raise ValueError(f"ApiTestRun {api_run_id} not found")
        llm_cfg = get_llm_config_for_role(s, run, "api_scanner")  # type: ignore[arg-type]
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration. Configure it in Settings first.")
        scanner_policy = get_run_scanner_policy(s, run)  # type: ignore[arg-type]
        specialist_cfg = get_specialist_agent_config(s)
        upstream_proxy = get_upstream_proxy_config(s)
        global_header_cfg = get_global_http_header_config(s)
        coll = s.get(ApiCollection, run.collection_id)
        base_url = (coll.base_url if coll else "").rstrip("/")
        coverage_mode = run.coverage_mode or "track"
        for obj in [run, llm_cfg]:
            s.expunge(obj)

    scanner_proxy_url = (
        upstream_proxy.proxy_url if upstream_proxy.proxy_scanner else None
    )
    llm_proxy_url = upstream_proxy.proxy_url if upstream_proxy.proxy_llm else None

    global_http_header: dict[str, str] = {}
    if global_header_cfg.header_name and global_header_cfg.header_value:
        global_http_header = {
            global_header_cfg.header_name: global_header_cfg.header_value
        }

    _scanner_proxy_var.set(scanner_proxy_url)
    _scanner_global_header_var.set(global_http_header)
    llm_svc.set_llm_proxy(llm_proxy_url)
    llm_svc.set_run_context(
        api_run_id, lambda evt: events_svc.emit(api_run_id, evt), run_kind="api"
    )

    log.info(
        "=== API thinking scan start: api_run_id=%s base_url=%s ===",
        api_run_id,
        base_url,
    )

    # Seed scanner sessions from credentials.
    seed_sessions_from_credentials(api_run_id)
    session_vault = scanner_sessions.load_session_vault(api_run_id, run_kind="api")

    # Build the per-category probe hook (replaces the old broad traffic hook).
    post_probe_fn = _make_post_probe_fn(api_run_id)

    # Build the initial LLM context from the API collection.
    crawl_context = _build_api_crawl_context(api_run_id)

    # In enforce mode, append the coverage checklist + directive so the agent
    # systematically drives every endpoint × applicable category to coverage.
    if coverage_mode == "enforce":
        directive = _build_enforce_directive(api_run_id)
        if directive:
            crawl_context = f"{crawl_context}\n\n{directive}"

    # Credential list for the LLM initial message.
    with Session(get_engine()) as s:
        run2 = s.get(ApiTestRun, api_run_id)
        coll2 = s.get(ApiCollection, run2.collection_id) if run2 else None
        creds_raw = (
            list(
                s.exec(
                    select(ApiCredential).where(ApiCredential.collection_id == coll2.id)
                ).all()
            )
            if coll2
            else []
        )
        collection_id = coll2.id if coll2 else 0

    creds_for_llm = []
    for c in creds_raw:
        # For login-scheme creds the value is "username:password" (see api_docs.py);
        # split it so the agent receives a usable password rather than the joined string.
        if (c.scheme or "").lower() == "login" and ":" in (c.value or ""):
            uname, _, pword = c.value.partition(":")
        else:
            uname, pword = (c.label or c.scheme), c.value
        creds_for_llm.append(
            {
                "username": uname,
                "password": pword,
                "login_url": c.auth_endpoint or "",
            }
        )

    # Pre-existing findings snapshot.
    findings_snapshot = _load_findings_snapshot(api_run_id, is_api_run=True)

    # Context tool + finding hooks.
    context_tool_fn = _make_api_context_tool_fn(collection_id, api_run_id)
    post_finding_fn = _make_post_finding_fn(api_run_id)
    persist_credential_fn = _make_persist_credential_fn(collection_id, api_run_id)

    # Register the post-finding coverage hook in the shared registry that
    # _persist_dynamic_finding actually fires (covers test-lead + specialist
    # paths). The post_finding_fn parameter alone is never invoked by the loop;
    # without this, API findings never flip their work-program cells. Mirrors
    # web's _do_thinking_scan. ponytail: popped in the finally below.
    from aespa.services.scanner import _finding_hooks

    _finding_hooks[api_run_id] = post_finding_fn

    events_svc.emit(
        api_run_id,
        {
            "type": "scanner_phase",
            "phase": "thinking_scan",
            "status": "start",
            "message": "API security scan started.",
        },
    )
    events_svc.emit(
        api_run_id,
        {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "active",
            "current_task": "API security audit starting…",
            "outcome": None,
            "_persist": True,
        },
    )

    # ── TLS/SSL posture (deterministic, always-on for HTTPS APIs) ─────────────
    # Records at most one consolidated finding summarising every transport-security
    # weakness. For APIs the accurate OWASP category is API8 (Security
    # Misconfiguration), which explicitly covers weak/missing TLS.
    if api_run_id not in _stop_requested:
        from aespa.services.scanner import (
            _run_tls_posture_module,
            _save_deterministic_findings,
        )

        tls_findings = await _run_tls_posture_module(
            run_id=api_run_id, base_url=base_url, is_api_run=True
        )
        for _tf in tls_findings:
            _tf.owasp_api_category = "API8"
        if tls_findings:
            _save_deterministic_findings(api_run_id, tls_findings, is_api_run=True)

    # Run the agentic loop — no browser_ctx/pw_page needed for REST APIs.
    async with _make_scanner_client(
        run_id=None, api_run_id=api_run_id, verify=False
    ) as hx:
        finding_count = await _do_agentic_thinking_loop(
            run_id=api_run_id,
            is_api_run=True,
            llm_cfg=llm_cfg,
            base_url=base_url,
            crawl_context=crawl_context,
            creds_for_llm=creds_for_llm,
            session_vault=session_vault,
            pages_snapshot=[],  # no crawled pages
            findings_snapshot=list(findings_snapshot),
            first_page_id=None,
            scanner_policy=scanner_policy,
            hx=hx,
            browser_ctx=None,  # no browser
            pw_page=None,
            history=[],
            all_results=[],
            resume_from=None,
            specialist_config=specialist_cfg,
            recon_summary=None,
            site_id=0,
            creds=None,
            login_url="",
            # API overrides
            system_message_override=_API_THINKING_AGENT_SYSTEM,
            tools_override=get_api_test_lead_tools(),
            scope_check_fn=lambda url: _api_check_scope(url, api_run_id),
            context_tool_fn=context_tool_fn,
            post_finding_fn=post_finding_fn,
            post_probe_fn=post_probe_fn,
            persist_credential_fn=persist_credential_fn,
        )

    log.info(
        "API thinking scan complete: api_run_id=%s findings=%d",
        api_run_id,
        finding_count,
    )

    # Resolve the coverage matrix to a terminal state.
    if coverage_mode == "enforce" and api_run_id not in _stop_requested:
        # Drive every still-uncovered cell to covered / skipped-with-reason.
        events_svc.emit(
            api_run_id,
            {
                "type": "agent_status",
                "agent_id": "scanner",
                "role": "Test Lead",
                "status": "active",
                "current_task": "Completing full coverage — resolving remaining cells…",
                "outcome": None,
                "_persist": True,
            },
        )
        prober = _make_enforce_prober(api_run_id, llm_cfg, base_url)
        await _enforce_coverage_loop(api_run_id, prober)
    else:
        # Track mode: promote cells the scan actually touched to covered.
        mark_all_cells_covered(api_run_id)
    # Remove endpoint cache.
    _endpoint_cache.pop(api_run_id, None)

    # Mark run completed.
    with Session(get_engine()) as s:
        r = s.get(ApiTestRun, api_run_id)
        if r is not None and r.status == "scanning":
            r.status = "completed"
            r.completed_at = datetime.now(_UTC)
            r.updated_at = datetime.now(_UTC)
            s.add(r)
            s.commit()

    events_svc.emit(
        api_run_id,
        {
            "type": "scanner_phase",
            "phase": "scan_stopped",
            "status": "complete",
            "message": f"API scan complete. {finding_count} finding(s) recorded.",
        },
    )
    events_svc.emit(
        api_run_id,
        {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "complete",
            "current_task": "Scan complete",
            "outcome": f"{finding_count} finding(s) recorded",
            "_persist": True,
        },
    )
    llm_svc.clear_run_context()


async def _api_scan_task(api_run_id: int) -> None:
    _stop_requested.discard(api_run_id)
    # Clear any leftover stop flag from a previous run so the loop doesn't
    # exit immediately on the very first iteration.
    try:
        from aespa.services.scanner import _thinking_stop_requested

        _thinking_stop_requested.discard(api_run_id)
    except Exception:
        pass
    try:
        await _do_api_thinking_scan(api_run_id)
    except asyncio.CancelledError:
        log.info("API scan cancelled: api_run_id=%s", api_run_id)
        _update_run_status(api_run_id, "cancelled")
        events_svc.emit(
            api_run_id,
            {
                "type": "scanner_phase",
                "phase": "scan_stopped",
                "status": "warning",
                "message": "API scan stopped by user.",
            },
        )
        events_svc.emit(
            api_run_id,
            {
                "type": "agent_status",
                "agent_id": "scanner",
                "role": "Test Lead",
                "status": "stopped",
                "current_task": "Scan stopped",
                "outcome": "cancelled",
                "_persist": True,
            },
        )
    except Exception as exc:
        log.exception("API scan error: api_run_id=%s", api_run_id)
        _update_run_status(api_run_id, "failed", str(exc))
        is_refusal = isinstance(exc, llm_svc.LLMRefusalError)
        failure_label = "LLM provider refusal" if is_refusal else "Scan failed"
        failure_message = str(exc)[:2000]
        events_svc.emit(
            api_run_id,
            {
                "type": "scanner_phase",
                "phase": "scan_failed",
                "status": "error",
                "message": f"{failure_label}: {failure_message}",
                "data": {"reason": "provider_refusal" if is_refusal else "error"},
            },
        )
        events_svc.emit(
            api_run_id,
            {
                "type": "agent_status",
                "agent_id": "scanner",
                "role": "Test Lead",
                "status": "failed",
                "current_task": failure_label,
                "outcome": failure_message,
                "_persist": True,
            },
        )
    finally:
        _scan_tasks.pop(api_run_id, None)
        _stop_requested.discard(api_run_id)
        # Clean up endpoint cache regardless of outcome.
        _endpoint_cache.pop(api_run_id, None)
        # Drop the post-finding coverage hook registered in _do_api_thinking_scan.
        try:
            from aespa.services.scanner import _finding_hooks

            _finding_hooks.pop(api_run_id, None)
        except Exception:
            pass


def _update_run_status(api_run_id: int, status: str, error: str | None = None) -> None:
    with Session(get_engine()) as s:
        r = s.get(ApiTestRun, api_run_id)
        if r is not None:
            r.status = status
            r.updated_at = datetime.now(_UTC)
            if error:
                r.error_message = error
            if status in ("completed", "failed", "cancelled"):
                r.completed_at = r.completed_at or datetime.now(_UTC)
            s.add(r)
            s.commit()


async def start_api_scan(api_run_id: int) -> None:
    """Start a full agentic API security scan for an ``ApiTestRun``."""
    if api_run_id in _scan_tasks:
        log.info("start_api_scan: scan already running for api_run_id=%s", api_run_id)
        return

    log.info("start_api_scan: api_run_id=%s", api_run_id)

    # Tag every event this run emits as run_kind='api'.  Run ids collide across
    # web / api / sast (independent counters), so the scope — not the id — is the
    # authoritative discriminator.  asyncio.create_task snapshots this context,
    # so the scan task (and its child specialist tasks) inherit the tag even
    # after this function returns.
    with events_svc.run_kind_scope("api"):
        with Session(get_engine()) as s:
            run = s.get(ApiTestRun, api_run_id)
            if run is None:
                raise ValueError(f"ApiTestRun {api_run_id} not found")
            run.status = "scanning"
            run.started_at = run.started_at or datetime.now(_UTC)
            run.updated_at = datetime.now(_UTC)
            s.add(run)
            s.commit()

        # Seed the coverage matrix before starting the scan task.
        seed_coverage_matrix(api_run_id)

        # Emit an immediate agent_status row so the Agents sidebar is non-empty.
        events_svc.emit(
            api_run_id,
            {
                "type": "agent_status",
                "agent_id": "scanner",
                "role": "Test Lead",
                "status": "active",
                "current_task": "API security scan starting…",
                "outcome": None,
                "_persist": True,
            },
        )

        task = asyncio.create_task(
            _api_scan_task(api_run_id),
            name=f"api-scan-{api_run_id}",
        )
        _scan_tasks[api_run_id] = task


async def stop_api_scan(api_run_id: int) -> bool:
    """Stop an in-progress API scan."""
    task = _scan_tasks.get(api_run_id)
    if task is not None:
        _stop_requested.add(api_run_id)
        task.cancel()
        # Also register a stop request with the scanner's stop mechanism.
        try:
            from aespa.services.scanner import _thinking_stop_requested

            _thinking_stop_requested.add(api_run_id)
        except Exception:
            pass
        _update_run_status(api_run_id, "cancelled")
        with events_svc.run_kind_scope("api"):
            events_svc.emit(
                api_run_id,
                {
                    "type": "agent_status",
                    "agent_id": "scanner",
                    "role": "Test Lead",
                    "status": "idle",
                    "current_task": "Scan stopped",
                    "outcome": "stopped",
                    "_persist": True,
                },
            )
        return True
    return False


def is_api_scan_running(api_run_id: int) -> bool:
    """Return True if an API scan task is currently active for this run."""
    return api_run_id in _scan_tasks and not _scan_tasks[api_run_id].done()


def get_scan_status(api_run_id: int) -> dict:
    """Return a scan-status dict."""
    running = api_run_id in _scan_tasks and not _scan_tasks[api_run_id].done()
    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        run_status = run.status if run else "unknown"
    return {
        "running": running,
        "status": "running" if running else run_status,
    }
