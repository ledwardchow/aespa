"""API-scan orchestration.

Provides the full Test-Lead + Specialist + Validator agentic scan pipeline for
``ApiTestRun``s — wiring the same ``_do_agentic_thinking_loop`` used by the web
scanner with API-specific overrides:

  * ``_API_THINKING_AGENT_SYSTEM`` system prompt (OWASP API Top 10 focused)
  * ``_api_context_tool_fn``  — delegates ``endpoint_list / endpoint_detail /
      collection_info / finding_list`` to the API context tool and routes all
      other sub-commands (history_search, traffic_search, …) to the shared
      web-scanner context tool
  * ``_set_api_finding_attrs`` post-save hook — stamps ``api_test_run_id`` and
    maps the OWASP category to the OWASP API Top-10 field on every finding
  * No browser/Playwright needed — REST APIs are all httpx
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    ApiCollection,
    ApiCredential,
    ApiEndpoint,
    ApiTestRun,
    ScanFinding,
)
from aespa.services import events as events_svc
from aespa.services import scanner_sessions
from aespa.services.prompts.test_lead import _API_THINKING_AGENT_SYSTEM

log = logging.getLogger(__name__)

_UTC = timezone.utc

# ── In-memory state ───────────────────────────────────────────────────────────

_scan_tasks: dict[int, asyncio.Task] = {}   # api_run_id → running asyncio.Task
_stop_requested: set[int] = set()


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
        creds = list(s.exec(
            select(ApiCredential).where(ApiCredential.collection_id == run.collection_id)
        ).all())

    seeded = 0
    scanner_sessions.ensure_anonymous_session(api_run_id, source="api_scanner")
    seeded += 1

    for cred in creds:
        label = cred.label or f"{cred.scheme}_{cred.id}"
        extra_headers: dict[str, str] = {}
        cookies: dict[str, str] = {}

        scheme = (cred.scheme or "bearer").lower()
        if scheme in ("bearer", "apikey", "header"):
            extra_headers[cred.name or "Authorization"] = (
                f"Bearer {cred.value}" if scheme == "bearer" and not cred.value.lower().startswith("bearer ")
                else cred.value
            )
        elif scheme == "cookie":
            parts = cred.value.split("=", 1)
            cookie_name = parts[0].strip() if len(parts) == 2 else cred.name or "session"
            cookie_val = parts[1].strip() if len(parts) == 2 else cred.value
            cookies[cookie_name] = cookie_val
        elif scheme == "basic":
            import base64 as _b64
            encoded = _b64.b64encode(cred.value.encode()).decode()
            extra_headers["Authorization"] = f"Basic {encoded}"

        kind = "bearer" if scheme == "bearer" else ("cookie" if scheme == "cookie" else "mixed")
        scanner_sessions.upsert_session(
            api_run_id,
            label=label,
            kind=kind,
            username=cred.label or f"cred_{cred.id}",
            credential_id=cred.id,
            source="api_scanner",
            cookies=cookies,
            extra_headers=extra_headers,
            metadata={"scheme": cred.scheme, "scope": cred.scope},
        )
        seeded += 1

    return seeded


# ── Context tool override ─────────────────────────────────────────────────────

# API-specific sub-commands routed to the alice context tool.
_API_CONTEXT_COMMANDS = frozenset({
    "endpoint_list", "endpoint_detail", "collection_info", "finding_list",
})

# Sub-commands that must fall through to the shared scanner context tool.
_SHARED_CONTEXT_COMMANDS = frozenset({
    "history_search", "target_inventory", "search_assets", "traffic_search",
    "compare_responses", "mutate_request", "extract_entities",
})


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
        # API inventory commands
        if tool_name in _API_CONTEXT_COMMANDS:
            return _run_api_context_tool(collection_id, api_run_id, tool_name, args)

        # site_map / page_detail → redirect to endpoint_list
        if tool_name in ("site_map", "page_detail"):
            return {
                "tool": tool_name,
                "note": "This is an API test run. Use endpoint_list / endpoint_detail instead.",
                "redirect": _run_api_context_tool(collection_id, api_run_id, "endpoint_list", args),
            }

        # Shared tools (history, traffic, entities, …)
        return _run_thinking_context_tool(
            tool_name, args,
            pages_snapshot=pages_snapshot or [],
            findings_snapshot=findings_snapshot or [],
            history=history or [],
            run_id=run_id,
            base_url=base_url,
        )

    return _fn


# ── Finding post-save hook ────────────────────────────────────────────────────

# Maps common OWASP Web Top 10 categories (used by write_finding) to the
# best-fit OWASP API Top 10 category.
_OWASP_WEB_TO_API: dict[str, str] = {
    "A01": "API5",   # Broken Access Control → BFLA
    "A02": "API2",   # Cryptographic Failures → Broken Authentication
    "A03": "API10",  # Injection → Unsafe Consumption
    "A04": "API8",   # Insecure Design → Misconfiguration
    "A05": "API8",   # Security Misconfiguration
    "A06": "API9",   # Vulnerable Components → Improper Inventory
    "A07": "API2",   # Identification & Authentication → Broken Auth
    "A08": "API3",   # Software & Data Integrity → Mass Assignment
    "A09": "API8",   # Security Logging → Misconfiguration
    "A10": "API7",   # SSRF
}


def _make_post_finding_fn(api_run_id: int):
    """Return a hook that stamps ``api_test_run_id`` and ``owasp_api_category`` on each finding."""

    def _fn(finding: ScanFinding) -> None:
        with Session(get_engine()) as s:
            f = s.get(ScanFinding, finding.id)
            if f is None:
                return
            f.api_test_run_id = api_run_id
            owasp = str(f.owasp_category or "").strip()
            # If the LLM wrote API1-API10 directly into owasp_category, move it.
            if owasp.upper().startswith("API"):
                f.owasp_api_category = owasp.upper()
            elif owasp.upper() in _OWASP_WEB_TO_API:
                f.owasp_api_category = _OWASP_WEB_TO_API[owasp.upper()]
            f.finding_source = f.finding_source or "api_scanner"
            s.add(f)
            s.commit()

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
        endpoints = list(s.exec(
            select(ApiEndpoint)
            .where(ApiEndpoint.collection_id == coll.id)
            .where(ApiEndpoint.in_scope == True)  # noqa: E712
            .order_by(ApiEndpoint.path, ApiEndpoint.method)
        ).all())
        creds = list(s.exec(
            select(ApiCredential).where(ApiCredential.collection_id == coll.id)
        ).all())

    lines: list[str] = [
        f"API Collection: {coll.name}",
        f"Base URL: {coll.base_url}",
    ]
    if coll.description:
        lines.append(f"Description: {coll.description}")

    auth_notes: list[str] = []
    for cred in creds:
        auth_notes.append(f"  - [{cred.scheme}] label={cred.label or cred.scheme}  scope={cred.scope}")
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
        lines.append(f"In-scope endpoints ({len(endpoints)} total):\n" + "\n".join(ep_summary))

    try:
        readiness = json.loads(coll.readiness_json or "{}")
        if readiness.get("overall") == "not_ready":
            lines.append(f"Readiness warning: {readiness.get('notes', '')}")
    except Exception:
        pass

    return "\n\n".join(lines)


# ── Main scan entry points ────────────────────────────────────────────────────

async def _do_api_thinking_scan(api_run_id: int) -> None:
    """Full Test-Lead + Specialist + Validator scan for an ApiTestRun.

    Loads API collection data, seeds sessions, then drives
    ``_do_agentic_thinking_loop`` with API-mode overrides — no Playwright needed.
    """
    from aespa.services.scanner import (
        _do_agentic_thinking_loop,
        _make_scanner_client,
        _scanner_proxy_var,
        _scanner_global_header_var,
        _load_findings_snapshot,
    )
    from aespa.services.settings import (
        get_llm_config_for_run,
        get_run_scanner_policy,
        get_specialist_agent_config,
        get_upstream_proxy_config,
        get_global_http_header_config,
    )
    from aespa.services import llm as llm_svc

    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            raise ValueError(f"ApiTestRun {api_run_id} not found")
        llm_cfg = get_llm_config_for_run(s, run)  # type: ignore[arg-type]
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration. Configure it in Settings first.")
        scanner_policy = get_run_scanner_policy(s, run)  # type: ignore[arg-type]
        specialist_cfg = get_specialist_agent_config(s)
        upstream_proxy = get_upstream_proxy_config(s)
        global_header_cfg = get_global_http_header_config(s)
        coll = s.get(ApiCollection, run.collection_id)
        base_url = (coll.base_url if coll else "").rstrip("/")
        for obj in [run, llm_cfg]:
            s.expunge(obj)

    scanner_proxy_url = upstream_proxy.proxy_url if upstream_proxy.proxy_scanner else None
    llm_proxy_url = upstream_proxy.proxy_url if upstream_proxy.proxy_llm else None

    global_http_header: dict[str, str] = {}
    if global_header_cfg.header_name and global_header_cfg.header_value:
        global_http_header = {global_header_cfg.header_name: global_header_cfg.header_value}

    _scanner_proxy_var.set(scanner_proxy_url)
    _scanner_global_header_var.set(global_http_header)
    llm_svc.set_llm_proxy(llm_proxy_url)
    llm_svc.set_run_context(api_run_id, lambda evt: events_svc.emit(api_run_id, evt))

    log.info("=== API thinking scan start: api_run_id=%s base_url=%s ===", api_run_id, base_url)

    # Seed scanner sessions from credentials.
    seed_sessions_from_credentials(api_run_id)
    session_vault = scanner_sessions.load_session_vault(api_run_id)

    # Build the initial LLM context from the API collection.
    crawl_context = _build_api_crawl_context(api_run_id)

    # Credential list for the LLM initial message.
    with Session(get_engine()) as s:
        run2 = s.get(ApiTestRun, api_run_id)
        coll2 = s.get(ApiCollection, run2.collection_id) if run2 else None
        creds_raw = list(s.exec(
            select(ApiCredential).where(
                ApiCredential.collection_id == coll2.id
            )
        ).all()) if coll2 else []
        collection_id = coll2.id if coll2 else 0

    creds_for_llm = [
        {
            "username": c.label or c.scheme,
            "password": c.value,
            "login_url": c.auth_endpoint or "",
        }
        for c in creds_raw
    ]

    # Pre-existing findings snapshot.
    findings_snapshot = _load_findings_snapshot(api_run_id)

    # Context tool + finding hooks.
    context_tool_fn = _make_api_context_tool_fn(collection_id, api_run_id)
    post_finding_fn = _make_post_finding_fn(api_run_id)

    events_svc.emit(api_run_id, {
        "type": "scanner_phase",
        "phase": "thinking_scan",
        "status": "start",
        "message": "API security scan started.",
    })
    events_svc.emit(api_run_id, {
        "type": "agent_status",
        "agent_id": "scanner",
        "role": "Test Lead",
        "status": "active",
        "current_task": "API security audit starting…",
        "outcome": None,
        "_persist": True,
    })

    # Run the agentic loop — no browser_ctx/pw_page needed for REST APIs.
    async with _make_scanner_client(run_id=None, api_run_id=api_run_id, verify=False) as hx:
        finding_count = await _do_agentic_thinking_loop(
            run_id=api_run_id,
            llm_cfg=llm_cfg,
            base_url=base_url,
            crawl_context=crawl_context,
            creds_for_llm=creds_for_llm,
            session_vault=session_vault,
            pages_snapshot=[],         # no crawled pages
            findings_snapshot=list(findings_snapshot),
            first_page_id=None,
            scanner_policy=scanner_policy,
            hx=hx,
            browser_ctx=None,          # no browser
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
            context_tool_fn=context_tool_fn,
            post_finding_fn=post_finding_fn,
        )

    log.info("API thinking scan complete: api_run_id=%s findings=%d", api_run_id, finding_count)

    # Mark run completed.
    with Session(get_engine()) as s:
        r = s.get(ApiTestRun, api_run_id)
        if r is not None and r.status == "scanning":
            r.status = "completed"
            r.completed_at = datetime.now(_UTC)
            r.updated_at = datetime.now(_UTC)
            s.add(r)
            s.commit()

    events_svc.emit(api_run_id, {
        "type": "scanner_phase",
        "phase": "scan_stopped",
        "status": "complete",
        "message": f"API scan complete. {finding_count} finding(s) recorded.",
    })
    events_svc.emit(api_run_id, {
        "type": "agent_status",
        "agent_id": "scanner",
        "role": "Test Lead",
        "status": "complete",
        "current_task": "Scan complete",
        "outcome": f"{finding_count} finding(s) recorded",
        "_persist": True,
    })
    llm_svc.clear_run_context()


async def _api_scan_task(api_run_id: int) -> None:
    _stop_requested.discard(api_run_id)
    try:
        await _do_api_thinking_scan(api_run_id)
    except asyncio.CancelledError:
        log.info("API scan cancelled: api_run_id=%s", api_run_id)
        _update_run_status(api_run_id, "cancelled")
        events_svc.emit(api_run_id, {
            "type": "scanner_phase",
            "phase": "scan_stopped",
            "status": "warning",
            "message": "API scan stopped by user.",
        })
        events_svc.emit(api_run_id, {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "stopped",
            "current_task": "Scan stopped",
            "outcome": "cancelled",
            "_persist": True,
        })
    except Exception as exc:
        log.exception("API scan error: api_run_id=%s", api_run_id)
        _update_run_status(api_run_id, "failed", str(exc))
        events_svc.emit(api_run_id, {
            "type": "scanner_phase",
            "phase": "scan_stopped",
            "status": "error",
            "message": f"API scan failed: {exc}",
        })
    finally:
        _scan_tasks.pop(api_run_id, None)
        _stop_requested.discard(api_run_id)


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

    with Session(get_engine()) as s:
        run = s.get(ApiTestRun, api_run_id)
        if run is None:
            raise ValueError(f"ApiTestRun {api_run_id} not found")
        run.status = "scanning"
        run.started_at = run.started_at or datetime.now(_UTC)
        run.updated_at = datetime.now(_UTC)
        s.add(run)
        s.commit()

    # Emit an immediate agent_status row so the Agents sidebar is non-empty.
    events_svc.emit(api_run_id, {
        "type": "agent_status",
        "agent_id": "scanner",
        "role": "Test Lead",
        "status": "active",
        "current_task": "API security scan starting…",
        "outcome": None,
        "_persist": True,
    })

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
        events_svc.emit(api_run_id, {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "idle",
            "current_task": "Scan stopped",
            "outcome": "stopped",
            "_persist": True,
        })
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
