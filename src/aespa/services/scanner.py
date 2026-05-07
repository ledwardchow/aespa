"""Security scanner service.

Two-phase LLM-directed probe execution:
  1. plan_probes()  → LLM returns a list of HTTP / form probes for the page
  2. execute probes → httpx (url/header/idor) or Playwright (form injection)
  3. analyse_probes() → LLM interprets results, returns ScanFinding rows

Auth bootstrap: re-uses _authenticate() from crawler, then exports cookies +
JS storage tokens so httpx carries a live authenticated session.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, LLMConfig, ScanFinding, Site, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import traffic as traffic_svc
from aespa.services.settings import get_llm_config_for_run, get_run_scanner_policy

log = logging.getLogger("aespa.scanner")

# ── In-memory state ───────────────────────────────────────────────────────────

# Regular scan
_stop_requested: set[int] = set()
_active_tasks: dict[int, asyncio.Task] = {}
# Populated while a scan is running so the validator can reuse pre-authenticated sessions.
_active_sessions: dict[int, dict[int, dict]] = {}  # run_id → cred_id → session

# Thinking scan (independent)
_thinking_stop_requested: set[int] = set()
_thinking_tasks: dict[int, asyncio.Task] = {}
_thinking_scan_status: dict[int, str] = {}  # run_id → idle|running|complete|stopped|failed

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

MAX_PROBES_PER_PAGE = 50
MAX_FOLLOWUP_PROBES  = 20
REQUEST_TIMEOUT = 10.0
BODY_READ_LIMIT = 512 * 1024  # 512 KB
MIN_DELAY = 0.05              # ~20 req/s

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def sleep_between_probes(scanner_policy=None) -> None:
    delay = scanner_policy.min_delay_s if scanner_policy else MIN_DELAY
    if delay > 0:
        await asyncio.sleep(delay)


def _login_url_for_credential(default_login_url: Optional[str], cred) -> str:
    return (getattr(cred, "login_url", None) or default_login_url or "").strip()


def _severity_from_cvss(score: float | int | str | None) -> str:
    try:
        value = float(score or 0.0)
    except (TypeError, ValueError):
        value = 0.0
    if value >= 9.0:
        return "critical"
    if value >= 7.0:
        return "high"
    if value >= 4.0:
        return "medium"
    if value > 0.0:
        return "low"
    return "info"


def _cvss_score(value: float | int | str | None) -> float:
    try:
        return max(0.0, min(10.0, round(float(value or 0.0), 1)))
    except (TypeError, ValueError):
        return 0.0


def _compact_log_value(value, limit: int = 180) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, separators=(",", ":"))
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _thinking_payload_summary(url: str, body) -> str:
    parts: list[str] = []
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    if query:
        preview = ", ".join(
            f"{key}={_compact_log_value(values[-1], 60)}"
            for key, values in list(query.items())[:4]
        )
        parts.append(f"query payloads: {preview}")
    body_preview = _compact_log_value(body)
    if body_preview:
        parts.append(f"body payload: {body_preview}")
    return "; ".join(parts)


def _thinking_browser_payload_summary(steps) -> str:
    if not isinstance(steps, list):
        return ""
    parts: list[str] = []
    for step in steps[:6]:
        if not isinstance(step, dict):
            continue
        op = step.get("op")
        selector = step.get("selector")
        value = step.get("value") if "value" in step else step.get("key")
        url = step.get("url")
        detail = op or "step"
        if selector:
            detail += f" {selector}"
        if value is not None:
            detail += f"={_compact_log_value(value, 50)}"
        if url:
            detail += f" {_compact_log_value(url, 80)}"
        parts.append(detail)
    if isinstance(steps, list) and len(steps) > 6:
        parts.append(f"+{len(steps) - 6} more")
    return "; ".join(parts)


def _sign_hs256_jwt(secret: str, claims: dict, header: dict | None = None) -> str:
    import base64 as _b64
    import hashlib
    import hmac

    def _b64url(raw: bytes) -> str:
        return _b64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    jwt_header = {"typ": "JWT", "alg": "HS256"}
    if header:
        jwt_header.update(header)
    if jwt_header.get("alg") != "HS256":
        raise ValueError("only HS256 JWT signing is supported")
    signing_input = ".".join([
        _b64url(json.dumps(jwt_header, separators=(",", ":")).encode()),
        _b64url(json.dumps(claims, separators=(",", ":")).encode()),
    ])
    signature = hmac.new(
        secret.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _redact_candidate(candidate: dict) -> dict:
    return {
        "username": candidate.get("username") or candidate.get("email") or "",
        "password": "***",
    }


def _redact_sensitive_text(text: str) -> str:
    # Hide JWT-like bearer values in history/evidence. The session vault keeps
    # usable tokens separately under labels so the LLM does not need raw secrets.
    return re.sub(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        "[REDACTED_JWT]",
        text,
    )


def _extract_bearer_token_from_body(body: str) -> Optional[str]:
    try:
        data = json.loads(body)
    except Exception:
        data = None

    def _walk(value):
        if isinstance(value, dict):
            for key in ("token", "access_token", "jwt", "auth_token", "id_token"):
                token = value.get(key)
                if isinstance(token, str) and token.count(".") == 2:
                    return token
            for child in value.values():
                found = _walk(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = _walk(child)
                if found:
                    return found
        return None

    if data is not None:
        token = _walk(data)
        if token:
            return token

    match = re.search(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        body,
    )
    return match.group(0) if match else None


def _session_label(raw: str, existing: dict) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower()).strip("_")
    base = base[:40] or "session"
    label = base
    counter = 2
    while label in existing:
        label = f"{base}_{counter}"
        counter += 1
    return label


def _thinking_action_log_message(step: int, method: str, url: str, action: dict) -> str:
    note = _compact_log_value(action.get("note"), 240)
    observation = _compact_log_value(action.get("observation"), 220)
    hypothesis = _compact_log_value(
        action.get("hypothesis") or action.get("investigation") or action.get("objective"),
        220,
    )
    payload_purpose = _compact_log_value(action.get("payload_purpose"), 180)
    if method == "BROWSER":
        payload_summary = _thinking_browser_payload_summary(action.get("steps") or [])
    elif method == "CREDENTIAL_CHECK":
        count = len(action.get("candidates") or [])
        payload_summary = f"{min(count, 20)} bounded candidate(s)"
    else:
        payload_summary = _thinking_payload_summary(url, action.get("body"))

    lead = hypothesis or note or "next target behavior"
    message = f"Step {step}: investigating {lead}"
    if observation:
        message += f" after observing {observation}"
    if payload_purpose:
        message += f"; payload purpose: {payload_purpose}"
    if payload_summary:
        message += f" ({payload_summary})"
    return f"{message} — {method} {url}"


def _summary_list(values: list[str], limit: int = 3) -> str:
    unique: list[str] = []
    for value in values:
        compact = _compact_log_value(value, 180)
        if compact and compact not in unique:
            unique.append(compact)
    if not unique:
        return ""
    shown = unique[:limit]
    suffix = f"; +{len(unique) - limit} more" if len(unique) > limit else ""
    return "; ".join(shown) + suffix


def _followup_log_details(followup_probes: list[dict]) -> dict[str, str]:
    interesting = _summary_list([
        str(
            probe.get("interesting_result")
            or probe.get("observation")
            or probe.get("trigger")
            or probe.get("reason")
            or ""
        )
        for probe in followup_probes
    ])
    hypotheses = _summary_list([
        str(
            probe.get("hypothesis")
            or probe.get("tests")
            or probe.get("objective")
            or probe.get("desc")
            or ""
        )
        for probe in followup_probes
    ])
    payloads = _summary_list([
        str(probe.get("payload_purpose") or _thinking_payload_summary(probe.get("url") or "", probe.get("body")))
        for probe in followup_probes
    ])
    return {"interesting": interesting, "hypotheses": hypotheses, "payloads": payloads}


def _followup_log_message(followup_probes: list[dict], *, tense: str = "planning") -> str:
    count = len(followup_probes)
    plural = "s" if count != 1 else ""
    details = _followup_log_details(followup_probes)
    if tense == "complete":
        message = f"{count} follow-up probe{plural} executed"
    else:
        message = f"{count} follow-up probe{plural} planned"
    if details["interesting"]:
        message += f" because: {details['interesting']}"
    if details["hypotheses"]:
        message += f"; testing: {details['hypotheses']}"
    if details["payloads"]:
        message += f"; payload purpose: {details['payloads']}"
    return message


def _combined_evidence(request_evidence: str, response_evidence: str, summary: str = "") -> str:
    parts = []
    if summary:
        parts.append(summary.strip())
    if request_evidence:
        parts.append(f"REQUEST:\n{request_evidence.strip()}")
    if response_evidence:
        parts.append(f"RESPONSE:\n{response_evidence.strip()}")
    return "\n\n".join(parts)


def _finding_from_llm(
    *,
    run_id: int,
    page_id: int,
    page_url: str,
    raw: dict,
    result_by_url: dict[str, dict],
) -> ScanFinding:
    probe_urls = list(result_by_url.keys())
    llm_url = (raw.get("affected_url") or "").strip()
    if llm_url and llm_url != page_url:
        affected_url = llm_url
    elif probe_urls:
        desc = (raw.get("description", "") + " " + raw.get("title", "")).lower()
        affected_url = next((u for u in probe_urls if u.lower() in desc), probe_urls[0])
    else:
        affected_url = page_url

    matched = result_by_url.get(affected_url, {})
    request_evidence = str(matched.get("request_evidence") or raw.get("request_evidence") or "")
    response_evidence = str(matched.get("response_evidence") or raw.get("response_evidence") or "")
    evidence = _combined_evidence(
        request_evidence,
        response_evidence,
        str(raw.get("evidence") or matched.get("evidence") or ""),
    )
    cvss_score = _cvss_score(raw.get("cvss_score"))

    return ScanFinding(
        test_run_id=run_id,
        page_id=page_id,
        owasp_category=raw.get("owasp_category", "A00"),
        severity=_severity_from_cvss(cvss_score),
        title=raw.get("title", "Untitled finding"),
        description=raw.get("description", ""),
        impact=raw.get("impact", ""),
        likelihood=raw.get("likelihood", ""),
        recommendation=raw.get("recommendation", ""),
        cvss_score=cvss_score,
        cvss_vector=raw.get("cvss_vector", ""),
        affected_url=affected_url,
        evidence=evidence[:4000],
        request_evidence=request_evidence[:4000],
        response_evidence=response_evidence[:4000],
        screenshot_b64=matched.get("screenshot_b64"),
        validation_status="validating",
        validation_note="Validation queued.",
        created_at=_utcnow(),
    )


# ── Public entry points ───────────────────────────────────────────────────────

def request_stop(run_id: int) -> None:
    _stop_requested.add(run_id)
    task = _active_tasks.get(run_id)
    if task and not task.done():
        task.cancel()


def is_running(run_id: int) -> bool:
    return run_id in _active_tasks


def get_active_sessions(run_id: int) -> dict[int, dict] | None:
    """Return the pre-authenticated cred_sessions for a currently running scan, or None."""
    return _active_sessions.get(run_id)


# ── Thinking-scan public API ──────────────────────────────────────────────────

def is_thinking_running(run_id: int) -> bool:
    return run_id in _thinking_tasks


def request_thinking_stop(run_id: int) -> None:
    _thinking_stop_requested.add(run_id)
    if is_thinking_running(run_id):
        _thinking_scan_status[run_id] = "stopping"
        _emit_thinking_status(run_id)


def get_thinking_scan_status(run_id: int) -> dict:
    if is_thinking_running(run_id):
        status = _thinking_scan_status.get(run_id, "running")
    else:
        status = _thinking_scan_status.get(run_id, "idle")
    with Session(get_engine()) as s:
        findings_count = len(s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all())
    return {"status": status, "findings_count": findings_count}


async def start_scan(run_id: int, page_ids: list[int] | None = None) -> None:
    """Start a scan. Pass page_ids to scan only specific pages; omit to scan all in-scope pages."""
    if run_id in _active_tasks:
        return
    task = asyncio.create_task(
        _scan_task(run_id, page_ids=page_ids),
        name=f"scan-{run_id}",
    )
    _active_tasks[run_id] = task
    task.add_done_callback(lambda _: _active_tasks.pop(run_id, None))


MAX_THINKING_STEPS = 120


async def start_thinking_scan(run_id: int) -> None:
    """Start an LLM-directed (thinking) scan that dynamically decides what to test."""
    if run_id in _thinking_tasks:
        return
    task = asyncio.create_task(
        _thinking_scan_task(run_id),
        name=f"thinking-scan-{run_id}",
    )
    _thinking_tasks[run_id] = task
    task.add_done_callback(lambda _: _thinking_tasks.pop(run_id, None))


# ── Task wrapper ──────────────────────────────────────────────────────────────

async def _scan_task(run_id: int, page_ids: list[int] | None = None) -> None:
    try:
        await _do_scan(run_id, page_ids=page_ids)
    except asyncio.CancelledError:
        log.info("Scan task cancelled (stop requested) for run_id=%s", run_id)
        _mark_run(run_id, scan_status="stopped")
        _emit_scan_update(run_id)
        raise
    except Exception as exc:
        log.exception("Scan task failed for run_id=%s", run_id)
        _mark_run(run_id, scan_status="failed", error=str(exc)[:2000])
    finally:
        _stop_requested.discard(run_id)
        _active_sessions.pop(run_id, None)


# ── Thinking-scan task wrapper & core ─────────────────────────────────────────

def _emit_thinking_status(run_id: int) -> None:
    events_svc.emit(run_id, {"type": "thinking_scan_update", **get_thinking_scan_status(run_id)})


async def _thinking_scan_task(run_id: int) -> None:
    _thinking_scan_status[run_id] = "running"
    _mark_run(run_id, scan_status="running")
    _emit_scan_update(run_id)
    _emit_thinking_status(run_id)
    try:
        await _do_thinking_scan(run_id)
    except asyncio.CancelledError:
        log.info("Thinking scan task cancelled for run_id=%s", run_id)
        _thinking_scan_status[run_id] = "stopped"
        _mark_run(run_id, scan_status="stopped")
        _emit_scan_update(run_id)
        _emit_thinking_status(run_id)
        raise
    except Exception as exc:
        log.exception("Thinking scan task failed for run_id=%s", run_id)
        _thinking_scan_status[run_id] = "failed"
        _mark_run(run_id, scan_status="failed", error=str(exc)[:2000])
        _emit_scan_update(run_id)
        _emit_thinking_status(run_id)
    finally:
        _thinking_stop_requested.discard(run_id)


async def _do_thinking_scan(run_id: int) -> None:
    """LLM-directed scan: the model decides each HTTP request to issue, observes
    the response, and adaptively chooses what to probe next — exactly like a human
    tester working through curl."""
    # ── Load config ───────────────────────────────────────────────────────────
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config_for_run(s, run)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration. Configure it in Settings first.")
        scanner_policy = get_run_scanner_policy(s, run)
        creds = list(site.credentials)

        # Crawled pages — used for context and for resolving page_id on findings.
        all_pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
        ).all()
        pages_snapshot = [
            {
                "id": p.id,
                "url": p.url,
                "title": p.title or "",
                "context": p.llm_context or "",
                "page_text": p.page_text or "",
                "req_auth": p.req_auth,
                "takes_input": p.takes_input,
                "has_object_ref": p.has_object_ref,
                "has_business_logic": p.has_business_logic,
            }
            for p in all_pages
        ]
        first_page_id = all_pages[0].id if all_pages else None

        # Existing findings from the regular scan — feed as context so the LLM
        # knows what has already been found and can focus on new attack surface.
        existing_findings = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all()
        findings_snapshot = [
            {
                "title":       f.title,
                "severity":    f.severity,
                "owasp":       f.owasp_category,
                "affected_url": f.affected_url,
                "description": f.description[:200],
            }
            for f in existing_findings
        ]

        for obj in [*creds, site, llm_cfg, run]:
            s.expunge(obj)

    base_url      = site.base_url.rstrip("/")
    login_url     = site.login_url
    requires_auth = site.requires_auth

    log.info("=== Thinking scan start: run_id=%s base_url=%s ===", run_id, base_url)
    # Status is set to "running" by the task wrapper before calling this function.

    # ── Build crawl-context string for the LLM ────────────────────────────────
    # API pages get their full request/response transcript; regular pages get a
    # short LLM summary.  Keep the two groups separate so the LLM can quickly
    # identify which URLs are API endpoints vs navigable pages.
    page_lines: list[str] = []
    api_lines: list[str] = []
    for p in pages_snapshot[:50]:
        flags = ", ".join(
            k for k, v in [
                ("auth-required", p["req_auth"]),
                ("takes-input",   p["takes_input"]),
                ("object-refs",   p["has_object_ref"]),
                ("business-logic", p["has_business_logic"]),
            ] if v
        )
        header = f"  {p['url']}" + (f" [{flags}]" if flags else "")
        if p["title"].startswith("API "):
            # Show the full HTTP exchange (request headers, body, response headers, body)
            # so the LLM can identify parameters, auth schemes, IDs, and response structure.
            raw = p["page_text"] or p["context"]
            indented = "\n".join("    " + line for line in raw[:2000].splitlines())
            api_lines.append(header + ("\n" + indented if indented.strip() else ""))
        else:
            page_lines.append(
                header + (f"\n    {p['context'][:200]}" if p["context"] else "")
            )
    ctx_parts: list[str] = []
    if page_lines:
        ctx_parts.append("Application pages:\n" + "\n".join(page_lines))
    if api_lines:
        ctx_parts.append(
            "API endpoints (full HTTP exchange shown):\n" + "\n".join(api_lines)
        )
    crawl_context = "\n\n".join(ctx_parts) or "(no crawl data available)"

    # Summarise findings already known from the regular scan.
    if findings_snapshot:
        finding_lines = "\n".join(
            f"  [{f['severity'].upper()}] {f['owasp']} {f['title']} @ {f['affected_url']}: {f['description']}"
            for f in findings_snapshot[:30]
        )
        crawl_context += f"\n\nFindings already discovered by the regular scan (avoid re-testing these; focus on new areas):\n{finding_lines}"

    creds_for_llm = [
        {
            "username": c.username,
            "password": c.password,
            "login_url": _login_url_for_credential(login_url, c),
        }
        for c in creds
    ]

    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "thinking_scan",
        "status": "start",
        "message": f"LLM-directed scan started — up to {MAX_THINKING_STEPS} adaptive steps.",
    })

    # ── Bootstrap browser + auth session (Playwright) ─────────────────────────
    cookie_jar: dict[str, str] = {}
    auth_token: Optional[str] = None

    # ── Agentic loop ──────────────────────────────────────────────────────────
    history:     list[dict] = []
    all_results: list[dict] = []
    session_vault: dict[str, dict] = {}

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        browser_ctx = await browser.new_context(user_agent=_UA, ignore_https_errors=True)
        traffic_svc.setup_playwright_logging(browser_ctx, run_id)
        pw_page = await browser_ctx.new_page()

        try:
            await pw_page.goto(base_url, wait_until="domcontentloaded", timeout=20_000)
        except Exception:
            pass

        if requires_auth and creds:
            from aespa.services.crawler import _authenticate

            await _authenticate(
                pw_page,
                _login_url_for_credential(login_url, creds[0]),
                creds[0],
            )

        raw_cookies = await browser_ctx.cookies()
        cookie_jar = {c["name"]: c["value"] for c in raw_cookies}
        for key in ["access_token", "token", "jwt", "auth_token", "id_token",
                    "authToken", "accessToken"]:
            try:
                val = await pw_page.evaluate(
                    f"() => localStorage.getItem('{key}') || sessionStorage.getItem('{key}')"
                )
                if val:
                    auth_token = val
                    break
            except Exception:
                pass

        extra_headers: dict[str, str] = {}
        if auth_token:
            extra_headers["Authorization"] = f"Bearer {auth_token}"
            session_vault["configured_primary"] = {
                "label": "configured_primary",
                "kind": "bearer",
                "username": creds[0].username if creds else None,
                "source": "configured credential auth bootstrap",
                "extra_headers": {"Authorization": f"Bearer {auth_token}"},
                "cookies": cookie_jar,
            }

        async with httpx.AsyncClient(
            cookies=cookie_jar,
            headers={"User-Agent": _UA, **extra_headers},
            timeout=scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT,
            follow_redirects=True,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(
                run_id, username=creds[0].username if creds else None
            ),
        ) as hx:
            for step in range(1, MAX_THINKING_STEPS + 1):
                if run_id in _thinking_stop_requested:
                    break

                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "thinking_step",
                    "status": "deciding",
                    "message": f"Step {step}/{MAX_THINKING_STEPS}: LLM deciding next action…",
                    "data": {"step": step, "max_steps": MAX_THINKING_STEPS},
                })

                # Ask the LLM what to do next.
                try:
                    action = await llm_svc.thinking_next_action(
                        llm_cfg,
                        target_url=base_url,
                        crawl_context=crawl_context,
                        history=history,
                        max_steps=MAX_THINKING_STEPS,
                        current_step=step,
                        credentials=creds_for_llm,
                        sessions=[
                            {
                                "label": label,
                                "kind": session.get("kind"),
                                "username": session.get("username"),
                                "source": session.get("source"),
                            }
                            for label, session in session_vault.items()
                        ],
                        emit_fn=lambda evt: events_svc.emit(run_id, evt),
                    )
                except Exception as exc:
                    log.warning("thinking_next_action error at step %d: %s", step, exc)
                    break

                if action.get("action") == "done":
                    log.info("LLM completed thinking scan at step %d: %s", step, action.get("summary", ""))
                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_scan",
                        "status": "complete",
                        "message": f"LLM finished at step {step}: {action.get('summary', '')}",
                    })
                    break

                action_type = action.get("action")
                note = action.get("note") or f"Step {step}"

                if action_type == "browser":
                    url = (action.get("url") or base_url).strip()
                    method = "BROWSER"
                    steps = action.get("steps") or []
                    use_session = action.get("use_session") or action.get("as_session")
                    use_session = use_session if isinstance(use_session, str) else None
                    selected_session = session_vault.get(use_session) if use_session else None
                    payload_summary = _thinking_browser_payload_summary(steps)
                    action_message = _thinking_action_log_message(step, method, url, action)

                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": payload_summary,
                            "use_session": use_session,
                        },
                    })

                    try:
                        await browser_ctx.set_extra_http_headers(
                            selected_session.get("extra_headers", {})
                            if selected_session else {}
                        )
                    except Exception:
                        pass
                    result = await _run_thinking_browser_action(
                        pw_page,
                        action,
                        default_url=base_url,
                        scanner_policy=scanner_policy,
                    )
                    resp_body = str(result.get("body") or "")[:BODY_READ_LIMIT]
                    resp_status = result.get("status") or 0
                    resp_headers = result.get("headers") or {}
                    url = result.get("url") or url
                    req_body = {"steps": steps}
                    result["desc"] = note
                elif action_type == "jwt":
                    method = "JWT"
                    url = f"jwt://forge/{action.get('store_as') or 'token'}"
                    claims = action.get("claims") if isinstance(action.get("claims"), dict) else {}
                    header = action.get("header") if isinstance(action.get("header"), dict) else None
                    secret = str(action.get("secret") or "")
                    action_message = _thinking_action_log_message(step, method, url, action)
                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": _compact_log_value(claims),
                        },
                    })
                    try:
                        token = _sign_hs256_jwt(secret, claims, header)
                        label = action.get("store_as") or _session_label("forged_jwt", session_vault)
                        session_vault[label] = {
                            "label": label,
                            "kind": "bearer",
                            "username": f"sub:{claims.get('sub')}" if claims.get("sub") is not None else None,
                            "source": "jwt action",
                            "extra_headers": {"Authorization": f"Bearer {token}"},
                            "cookies": {},
                        }
                        resp_status = 200
                        resp_headers = {"content-type": "application/json"}
                        resp_body = json.dumps({
                            "store_as": label,
                            "token_type": "Bearer",
                            "authorization_header": "Bearer [REDACTED_JWT]",
                            "claims": claims,
                        })
                    except Exception as exc:
                        resp_status = 0
                        resp_headers = {}
                        resp_body = f"JWT signing failed: {exc}"
                    req_body = {
                        "claims": claims,
                        "header": header or {"typ": "JWT", "alg": "HS256"},
                        "store_as": action.get("store_as"),
                    }
                    request_evidence = (
                        f"JWT FORGE\nClaims:\n{json.dumps(claims, indent=2)[:2000]}"
                    )
                    response_evidence = f"Status: {resp_status}\n{resp_body[:3000]}"
                    result = {
                        "desc": note,
                        "url": url,
                        "status": resp_status,
                        "headers": resp_headers,
                        "body": resp_body[:1000],
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                    }
                elif action_type == "credential_check":
                    method = "CREDENTIAL_CHECK"
                    url = (action.get("url") or "").strip()
                    candidates = action.get("candidates")
                    if not isinstance(candidates, list):
                        candidates = []
                    candidates = [c for c in candidates if isinstance(c, dict)][:20]
                    username_field = action.get("username_field") or "username"
                    password_field = action.get("password_field") or "password"
                    success_statuses = action.get("success_statuses") or [200, 201]
                    try:
                        success_statuses = {int(s) for s in success_statuses}
                    except Exception:
                        success_statuses = {200, 201}
                    headers = action.get("headers") or {}
                    action_message = _thinking_action_log_message(step, method, url, action)

                    if not url:
                        log.warning("Thinking scan step %d: credential_check missing URL.", step)
                        break

                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": f"{len(candidates)} candidate(s)",
                        },
                    })

                    attempts: list[dict] = []
                    resp_status = 0
                    resp_headers = {}
                    for candidate in candidates:
                        created_label = None
                        body = {
                            username_field: candidate.get("username") or candidate.get("email") or "",
                            password_field: candidate.get("password") or "",
                        }
                        try:
                            merged_headers = dict(hx.headers)
                            merged_headers.update(headers)
                            merged_headers.setdefault("Content-Type", "application/json")
                            resp = await hx.request(
                                str(action.get("method") or "POST").upper(),
                                url,
                                json=body,
                                headers=merged_headers,
                            )
                            resp_status = resp.status_code
                            resp_headers = dict(resp.headers)
                            response_excerpt = resp.text[:800]
                            success = resp.status_code in success_statuses
                            token = _extract_bearer_token_from_body(resp.text) if success else None
                            if token:
                                username = (
                                    candidate.get("username")
                                    or candidate.get("email")
                                    or "discovered"
                                )
                                label = _session_label(str(username), session_vault)
                                created_label = label
                                session_vault[label] = {
                                    "label": label,
                                    "kind": "bearer",
                                    "username": username,
                                    "source": "credential_check",
                                    "extra_headers": {"Authorization": f"Bearer {token}"},
                                    "cookies": {},
                                }
                        except Exception as exc:
                            response_excerpt = f"Request failed: {exc}"
                            success = False
                        attempts.append({
                            **_redact_candidate(candidate),
                            "status": resp_status,
                            "success": success,
                            "session_label": created_label,
                            "response_excerpt": (
                                _redact_sensitive_text(response_excerpt[:300])
                                if success else ""
                            ),
                        })
                        await sleep_between_probes(scanner_policy)

                    successes = [a for a in attempts if a["success"]]
                    resp_body = json.dumps({
                        "attempts": attempts,
                        "successes": successes,
                        "stopped_at_cap": len((action.get("candidates") or [])) > 20,
                    })
                    req_body = {
                        "username_field": username_field,
                        "password_field": password_field,
                        "candidates": [_redact_candidate(c) for c in candidates],
                    }
                    request_evidence = (
                        f"CREDENTIAL CHECK {url}\n"
                        f"Candidates:\n{json.dumps(req_body['candidates'], indent=2)[:2000]}"
                    )
                    response_evidence = (
                        f"Successes: {len(successes)} of {len(attempts)}\n"
                        f"{json.dumps(attempts, indent=2)[:3000]}"
                    )
                    result = {
                        "desc": note,
                        "url": url,
                        "status": 200 if successes else resp_status,
                        "headers": resp_headers,
                        "body": resp_body[:1000],
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                    }
                    resp_status = result["status"]
                else:
                    # Execute the HTTP request.
                    method  = (action.get("method") or "GET").upper()
                    url     = (action.get("url") or "").strip()
                    headers = action.get("headers") or {}
                    body    = action.get("body")
                    use_session = action.get("use_session") or action.get("as_session")
                    use_session = use_session if isinstance(use_session, str) else None
                    selected_session = session_vault.get(use_session) if use_session else None
                    action_message = _thinking_action_log_message(step, method, url, action)
                    payload_summary = _thinking_payload_summary(url, body)

                    if not url:
                        log.warning("Thinking scan step %d: LLM returned empty URL — stopping.", step)
                        break

                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": payload_summary,
                            "use_session": use_session,
                        },
                    })

                    req_body_str = ""
                    try:
                        merged_headers = dict(hx.headers)
                        if selected_session and selected_session.get("extra_headers"):
                            merged_headers.update(selected_session["extra_headers"])
                        merged_headers.update(headers)
                        if isinstance(body, dict):
                            merged_headers.setdefault("Content-Type", "application/json")
                            resp = await hx.request(method, url, json=body, headers=merged_headers)
                            req_body_str = json.dumps(body)[:800]
                        elif isinstance(body, str) and body:
                            resp = await hx.request(method, url, content=body, headers=merged_headers)
                            req_body_str = body[:800]
                        else:
                            resp = await hx.request(method, url, headers=merged_headers)
                        raw_resp_body = resp.text[:BODY_READ_LIMIT]
                        token = _extract_bearer_token_from_body(raw_resp_body)
                        if token and resp.status_code < 400:
                            label = _session_label(
                                str(action.get("store_as") or "http_token"),
                                session_vault,
                            )
                            session_vault[label] = {
                                "label": label,
                                "kind": "bearer",
                                "username": None,
                                "source": f"{method} {url}",
                                "extra_headers": {"Authorization": f"Bearer {token}"},
                                "cookies": {},
                            }
                        resp_body    = _redact_sensitive_text(raw_resp_body)
                        resp_status  = resp.status_code
                        resp_headers = dict(resp.headers)
                    except Exception as exc:
                        log.warning("Thinking scan step %d HTTP error (%s %s): %s", step, method, url, exc)
                        resp_body    = f"Request failed: {exc}"
                        resp_status  = 0
                        resp_headers = {}

                    req_body = body
                    request_evidence = f"{method} {url}\n{json.dumps(headers)}\n{req_body_str}"
                    response_evidence = f"Status: {resp_status}\n{resp_body[:3000]}"
                    result = {
                        "desc": note,
                        "url": url,
                        "status": resp_status,
                        "headers": resp_headers,
                        "body": resp_body[:1000],
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                    }

                log.info("Thinking scan step %d: %s %s → %s", step, method, url, resp_status)

                step_record = {
                    "step":             step,
                    "note":             note,
                    "method":           method,
                    "url":              url,
                    "request_headers":  action.get("headers") or {},
                    "request_body":     req_body,
                    "response_status":  resp_status,
                    "response_headers": resp_headers,
                    "response_body":    resp_body,
                }
                history.append(step_record)

                all_results.append(result)

                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "thinking_step",
                    "status": "complete",
                    "message": f"Step {step}: {method} {url} → {resp_status}",
                    "data": {"step": step, "status": resp_status, "note": note},
                })

                await sleep_between_probes(scanner_policy)

    # ── Analyse results ───────────────────────────────────────────────────────
    if all_results:
        _thinking_scan_status[run_id] = "analysing"
        _emit_thinking_status(run_id)
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "thinking_analysis",
            "status": "start",
            "message": f"Analysing {len(all_results)} probe results for findings…",
        })
        try:
            raw_findings = await llm_svc.analyse_probes(llm_cfg, base_url, all_results)
            # Normalise titles against existing findings so the same vulnerability
            # class gets a consistent title regardless of which step found it.
            if raw_findings:
                with Session(get_engine()) as _s:
                    _existing = _s.exec(
                        select(ScanFinding).where(ScanFinding.test_run_id == run_id)
                    ).all()
                if _existing:
                    _summaries = [
                        {"title": f.title, "owasp_category": f.owasp_category, "severity": f.severity}
                        for f in _existing
                    ]
                    try:
                        raw_findings = await llm_svc.normalize_finding_titles(
                            llm_cfg, _summaries, raw_findings
                        )
                    except Exception as _ne:
                        log.warning("normalize_finding_titles failed (thinking scan): %s", _ne)
            with Session(get_engine()) as s:
                result_by_url = {r["url"]: r for r in all_results}

                # Build a URL → page_id lookup for best-match page assignment.
                url_to_page: dict[str, int] = {p["url"]: p["id"] for p in pages_snapshot}

                def _best_page_id(affected_url: str) -> int:
                    """Find the closest matching crawled page for a finding URL."""
                    if affected_url in url_to_page:
                        return url_to_page[affected_url]
                    # Partial match — pick the crawled page whose URL is a prefix.
                    for page_url, page_id in url_to_page.items():
                        if affected_url.startswith(page_url) or page_url.startswith(affected_url):
                            return page_id
                    return first_page_id  # fallback

                for raw in raw_findings:
                    affected = (raw.get("affected_url") or base_url).strip()
                    page_id  = _best_page_id(affected)
                    if page_id is None:
                        log.warning("Thinking scan: no page_id found for finding %s — skipping", affected)
                        continue
                    finding = _finding_from_llm(
                        run_id=run_id,
                        page_id=page_id,
                        page_url=affected,
                        raw=raw,
                        result_by_url=result_by_url,
                    )
                    s.add(finding)
                s.commit()
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_analysis",
                "status": "complete",
                "message": f"Analysis complete — {len(raw_findings)} potential finding(s) recorded.",
            })
        except Exception as exc:
            log.warning("Thinking scan analysis failed: %s", exc)

    stopped = run_id in _thinking_stop_requested
    _thinking_scan_status[run_id] = "stopped" if stopped else "complete"
    _mark_run(run_id, scan_status="stopped" if stopped else "complete")
    _emit_scan_update(run_id)
    _emit_thinking_status(run_id)
    log.info("=== Thinking scan %s: run_id=%s ===", "stopped" if stopped else "complete", run_id)


# ── Core scan ─────────────────────────────────────────────────────────────────

async def _export_cred_session(
    base_url: str, login_url: Optional[str], cred
) -> tuple[dict[str, str], Optional[str]]:
    """Launch a throw-away Playwright browser, authenticate as cred, and return
    (cookie_jar, auth_token) so httpx can impersonate that session."""
    from playwright.async_api import async_playwright

    from aespa.services.crawler import _authenticate

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=_UA, ignore_https_errors=True)
        page = await ctx.new_page()
        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=20_000)
        except Exception:
            pass
        credential_login_url = _login_url_for_credential(login_url, cred)
        if credential_login_url:
            await _authenticate(page, credential_login_url, cred)
        raw = await ctx.cookies()
        cookies = {c["name"]: c["value"] for c in raw}
        token: Optional[str] = None
        for key in ["access_token", "token", "jwt", "auth_token", "id_token",
                    "authToken", "accessToken"]:
            try:
                val = await page.evaluate(
                    f"() => localStorage.getItem('{key}') || sessionStorage.getItem('{key}')"
                )
                if val:
                    token = val
                    break
            except Exception:
                pass
        await browser.close()
    return cookies, token


async def _do_scan(run_id: int, page_ids: list[int] | None = None) -> None:
    from playwright.async_api import async_playwright

    # Load site, credentials, and LLM config (expunge before session closes).
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config_for_run(s, run)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration. Configure it in Settings first.")
        scanner_policy = get_run_scanner_policy(s, run)
        creds = list(site.credentials)
        for obj in [*creds, site, llm_cfg, run]:
            s.expunge(obj)

    base_url      = site.base_url.rstrip("/")
    login_url     = site.login_url
    requires_auth = site.requires_auth

    log.info("=== Scan start: run_id=%s base_url=%s ===", run_id, base_url)

    # Mark target pages as scan_status=pending. Findings are append-only until
    # the user explicitly deletes them, so scans can be compared across runs.
    with Session(get_engine()) as s:
        q = (
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)   # noqa: E712
            .where(CrawledPage.status == "crawled") # skip failed navigations
            .where(CrawledPage.page_text != None)   # noqa: E711  skip content-less pages
            .where(CrawledPage.page_text != "")
        )
        if page_ids:
            q = q.where(CrawledPage.id.in_(page_ids))
        pages = s.exec(q).all()
        for p in pages:
            p.scan_status = "pending"
            s.add(p)
        s.commit()
        page_ids = [p.id for p in pages]  # use resolved list from here on

    if not page_ids:
        log.info("No in-scope pages to scan.")
        _mark_run(run_id, scan_status="complete")
        return

    _mark_run(run_id, scan_status="running")

    # ── Site-level test plan ──────────────────────────────────────────────────
    # Before opening a browser, ask the LLM to reason about the application as a
    # whole and produce a structured attack plan.  The plan is passed as context
    # to every per-page scan so individual probe plans are more targeted.
    site_context: str = ""
    if page_ids:
        with Session(get_engine()) as s:
            all_pages_meta = s.exec(
                select(CrawledPage)
                .where(CrawledPage.test_run_id == run_id)
                .where(CrawledPage.in_scope != False)  # noqa: E712
            ).all()
            pages_meta = [
                {
                    "url": p.url,
                    "title": p.title or "",
                    "context": p.llm_context or "",
                    "req_auth": p.req_auth,
                    "takes_input": p.takes_input,
                    "has_object_ref": p.has_object_ref,
                    "has_business_logic": p.has_business_logic,
                }
                for p in all_pages_meta
            ]
        try:
            log.info("Generating site-level test plan (%d pages)...", len(pages_meta))
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "site_plan",
                "status": "start",
                "message": f"Building site-level attack plan from {len(pages_meta)} discovered pages\u2026",
            })
            site_plan = await llm_svc.generate_site_test_plan(llm_cfg, base_url, pages_meta)
            if site_plan:
                parts: list[str] = []
                if site_plan.get("app_summary"):
                    parts.append(site_plan["app_summary"])
                hypotheses = site_plan.get("attack_hypotheses") or []
                if hypotheses:
                    hyp_lines = "\n".join(
                        f"  - [{h.get('owasp','?')}] {h.get('hypothesis','')}: {h.get('description','')}"
                        for h in hypotheses[:8]
                    )
                    parts.append("Attack hypotheses:\n" + hyp_lines)
                if site_plan.get("critical_areas"):
                    parts.append("Critical areas: " + ", ".join(site_plan["critical_areas"]))
                if site_plan.get("test_notes"):
                    parts.append("Test notes: " + site_plan["test_notes"])
                site_context = "\n\n".join(p for p in parts if p)
                log.info("Site plan ready: %s", site_plan.get("app_summary", "(no summary)"))
                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "site_plan",
                    "status": "complete",
                    "message": site_plan.get("app_summary", ""),
                    "data": {
                        "app_summary": site_plan.get("app_summary"),
                        "hypotheses": site_plan.get("attack_hypotheses") or [],
                        "critical_areas": site_plan.get("critical_areas") or [],
                        "test_notes": site_plan.get("test_notes"),
                    },
                })
        except Exception as e:
            log.warning("Site test plan generation failed: %s", e)

    # Unique canary for stored XSS detection across pages.
    # Embedded in XSS probes so any page that stores + reflects it can be caught by the
    # post-scan sweep even if the injection and sink are on completely different pages.
    xss_canary = f"aespa{run_id}x"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
        )
        traffic_svc.setup_playwright_logging(ctx, run_id)
        pw_page = await ctx.new_page()

        # ── Auth bootstrap ────────────────────────────────────────────────────
        # Pre-load base URL, then authenticate to get a live session.
        try:
            await pw_page.goto(base_url, wait_until="domcontentloaded", timeout=20_000)
        except Exception as e:
            log.warning("Pre-load failed: %s", e)

        if requires_auth and creds:
            from aespa.services.crawler import _authenticate
            first_login_url = _login_url_for_credential(login_url, creds[0])
            log.info("Authenticating at %s", first_login_url)
            await _authenticate(pw_page, first_login_url, creds[0])
            log.info("Auth done. page.url=%s", pw_page.url)

        # ── Export auth state for httpx ───────────────────────────────────────
        raw_cookies = await ctx.cookies()
        cookie_jar: dict[str, str] = {c["name"]: c["value"] for c in raw_cookies}

        # Check for JWT/Bearer tokens in JS storage.
        auth_token: Optional[str] = None
        try:
            for key in ["access_token", "token", "jwt", "auth_token", "id_token",
                        "authToken", "accessToken"]:
                val = await pw_page.evaluate(
                    f"() => localStorage.getItem('{key}') || sessionStorage.getItem('{key}')"
                )
                if val:
                    auth_token = val
                    log.info("Found JS storage token under key '%s'", key)
                    break
        except Exception as e:
            log.warning("JS storage token extraction failed: %s", e)

        extra_headers: dict[str, str] = {}
        if auth_token:
            extra_headers["Authorization"] = f"Bearer {auth_token}"

        # ── Build per-credential sessions for BAC checks ──────────────────────
        # cred_sessions maps credential_id → {username, cookies, extra_headers}
        cred_sessions: dict[int, dict] = {}
        if requires_auth and creds:
            cred_sessions[creds[0].id] = {
                "username": creds[0].username,
                "cookies": cookie_jar,
                "extra_headers": extra_headers,
            }
            for extra_cred in creds[1:]:
                log.info("Exporting session for BAC checks: user=%s", extra_cred.username)
                ec_cookies, ec_token = await _export_cred_session(
                    base_url, _login_url_for_credential(login_url, extra_cred), extra_cred
                )
                cred_sessions[extra_cred.id] = {
                    "username": extra_cred.username,
                    "cookies": ec_cookies,
                    "extra_headers": {"Authorization": f"Bearer {ec_token}"} if ec_token else {},
                }

        # Expose sessions so the validator can reuse them while the scan is active.
        _active_sessions[run_id] = cred_sessions

        # Build httpx client with exported auth state.
        async with httpx.AsyncClient(
            cookies=cookie_jar,
            headers={"User-Agent": _UA, **extra_headers},
            timeout=scanner_policy.request_timeout_s,
            follow_redirects=scanner_policy.follow_redirects,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(run_id, username=creds[0].username if creds else None),
        ) as hx:
            # ── Per-page scanning ─────────────────────────────────────────────
            for page_id in page_ids:
                if run_id in _stop_requested:
                    log.info("Stop requested — aborting scan.")
                    break
                await _scan_page(run_id, page_id, hx, pw_page, llm_cfg, base_url,
                                 cred_sessions=cred_sessions, browser=browser,
                                 scanner_policy=scanner_policy,
                                 site_context=site_context,
                                 xss_canary=xss_canary)

            # ── Stored XSS sweep ───────────────────────────────────────────────────
            # Re-fetch every crawled page and look for the canary appearing unescaped.
            # This catches stored XSS where the injection and the rendering sink are
            # on two different pages — a pattern the per-page probe loop cannot see.
            if run_id not in _stop_requested:
                await _stored_xss_sweep(
                    run_id, hx, xss_canary,
                    scanner_policy=scanner_policy,
                )

    stopped = run_id in _stop_requested
    _mark_run(run_id, scan_status="stopped" if stopped else "complete")
    _emit_scan_update(run_id)
    log.info("=== Scan %s: run_id=%s ===", "stopped" if stopped else "complete", run_id)


# ── Per-page scan ─────────────────────────────────────────────────────────────

async def _scan_page(
    run_id: int,
    page_id: int,
    hx: httpx.AsyncClient,
    pw_page,
    llm_cfg,
    base_url: str,
    cred_sessions: dict | None = None,
    browser=None,
    scanner_policy=None,
    site_context: str = "",
    xss_canary: str = "",
) -> None:
    # Load page details.
    with Session(get_engine()) as s:
        page = s.get(CrawledPage, page_id)
        if page is None:
            return
        page_url    = page.url
        page_title  = page.title or ""
        page_text   = page.page_text or ""
        page_ctx    = page.llm_context or ""
        accessible_by: list[int] = json.loads(page.accessible_by or "[]")
        categories  = {
            "req_auth":          page.req_auth,
            "takes_input":       page.takes_input,
            "has_object_ref":    page.has_object_ref,
            "has_business_logic": page.has_business_logic,
        }
        page.scan_status = "running"
        s.add(page)
        s.commit()

    events_svc.emit(run_id, {"type": "node_scan_status", "page_id": page_id, "scan_status": "running"})
    log.info("Scanning page: %s", page_url)

    # Determine applicable OWASP checks based on page categories.
    applicable = _applicable_checks(categories)

    # Build a username → session lookup for as_user probe resolution.
    user_sessions: dict[str, dict] = {
        cs["username"]: cs for cs in (cred_sessions or {}).values()
    }
    users_list: list[dict] = [
        {"username": cs["username"], "label": cs.get("label")}
        for cs in (cred_sessions or {}).values()
    ] or None

    # Phase 1: LLM plans probes.
    try:
        probes = await llm_svc.plan_probes(
            llm_cfg, page_url, page_title, page_ctx, categories, applicable,
            users=users_list,
            site_context=site_context,
            xss_canary=xss_canary,
        )
    except Exception as e:
        log.warning("plan_probes failed for %s: %s", page_url, e)
        probes = []

    # Inject hard-coded probe templates before the LLM probes so they always run.
    deterministic: list[dict] = []
    if categories.get("takes_input"):
        iv = _input_validation_probes(page_url, xss_canary=xss_canary)
        log.info("  Input-validation probes: %d", len(iv))
        deterministic.extend(iv)
    if categories.get("has_object_ref"):
        # Emit a single "idor" marker; it gets expanded below after deduplication.
        deterministic.append({"type": "idor", "url": page_url, "desc": "IDOR (deterministic)"})

    # Combine deterministic + LLM probes, then expand all "idor" markers.
    combined = deterministic + probes

    # Expand "idor" markers — deduplicate by (URL, as_user) so the same page can be
    # expanded once per user context (e.g. primary session + a specific test user).
    all_probes: list[dict] = []
    expanded_idor_keys: set[tuple[str, str | None]] = set()
    for probe in combined:
        if probe.get("type") != "idor":
            all_probes.append(probe)
            continue
        idor_url = probe.get("url") or page_url
        as_user  = probe.get("as_user") or None
        key = (idor_url, as_user)
        if key in expanded_idor_keys:
            continue
        expanded_idor_keys.add(key)
        expanded = _idor_expand(idor_url, run_id, accessible_by, as_user=as_user)
        log.info("  IDOR expand %s → %d probes (url=%s, as_user=%s)",
                 probe.get("desc", ""), len(expanded), idor_url, as_user)
        all_probes.extend(expanded)

    max_probes = scanner_policy.max_probes_per_page if scanner_policy else MAX_PROBES_PER_PAGE
    all_probes = _prioritize_probes_for_cap(all_probes, max_probes, categories)
    log.info("  %d total probes for %s", len(all_probes), page_url)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "page_plan",
        "status": "complete",
        "page_url": page_url,
        "message": f"Planned {len(all_probes)} probe{'s' if len(all_probes) != 1 else ''}",
        "data": {"probe_count": len(all_probes)},
    })

    # Phase 2: Execute probes.
    results: list[dict] = []

    # Always run passive checks regardless of LLM probes.
    passive = await _passive_checks(
        hx, page_url, base_url,
        timeout=scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT,
    )
    results.extend(passive)

    for probe in all_probes:
        if run_id in _stop_requested:
            break
        try:
            if scanner_policy and scanner_policy.scan_mode == "passive":
                log.info("  Probe rejected by policy: passive mode (%s)", probe.get("desc", "?"))
                continue
            as_user_name = probe.get("as_user") or None
            session = user_sessions.get(as_user_name) if as_user_name else None
            if probe.get("type") == "form":
                result = await _run_form_probe(pw_page, probe, page_url,
                                               session=session, browser=browser)
            else:
                result = await _run_http_probe(hx, probe, page_url, session=session,
                                               scanner_policy=scanner_policy)
            if result:
                results.append(result)
        except Exception as e:
            log.debug("Probe error (%s): %s", probe.get("desc", "?"), e)
        await sleep_between_probes(scanner_policy)

    # Phase 2b: Iterative reasoning — LLM reviews initial results and generates
    # targeted follow-up probes, mirroring the adaptive approach used by a human
    # tester who observes partial results before deciding what to probe next.
    if results and run_id not in _stop_requested:
        try:
            max_followup = MAX_FOLLOWUP_PROBES
            followup_probes = await llm_svc.plan_followup_probes(
                llm_cfg, page_url, page_ctx, results, site_context=site_context,
            )
            followup_probes = followup_probes[:max_followup]
            log.info("  %d follow-up probes generated for %s", len(followup_probes), page_url)
        except Exception as e:
            log.warning("plan_followup_probes failed for %s: %s", page_url, e)
            followup_probes = []

        if followup_probes:
            followup_details = _followup_log_details(followup_probes)
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "page_followup",
                "status": "start",
                "page_url": page_url,
                "message": _followup_log_message(followup_probes),
                "data": {"followup_count": len(followup_probes), **followup_details},
            })

        for probe in followup_probes:
            if run_id in _stop_requested:
                break
            try:
                if scanner_policy and scanner_policy.scan_mode == "passive":
                    log.info("  Follow-up probe rejected by policy: passive mode (%s)", probe.get("desc", "?"))
                    continue
                as_user_name = probe.get("as_user") or None
                session = user_sessions.get(as_user_name) if as_user_name else None
                if probe.get("type") == "form":
                    result = await _run_form_probe(pw_page, probe, page_url,
                                                   session=session, browser=browser)
                else:
                    result = await _run_http_probe(hx, probe, page_url, session=session,
                                                   scanner_policy=scanner_policy)
                if result:
                    results.append(result)
            except Exception as e:
                log.debug("Follow-up probe error (%s): %s", probe.get("desc", "?"), e)
            await sleep_between_probes(scanner_policy)

        if followup_probes:
            followup_details = _followup_log_details(followup_probes)
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "page_followup",
                "status": "complete",
                "page_url": page_url,
                "message": _followup_log_message(followup_probes, tense="complete"),
                "data": {"followup_count": len(followup_probes), **followup_details},
            })

    # Phase 3: LLM analyses results and produces findings.
    try:
        raw_findings = await llm_svc.analyse_probes(llm_cfg, page_url, results)
    except Exception as e:
        log.warning("analyse_probes failed for %s: %s", page_url, e)
        raw_findings = []

    # Normalise titles against findings already saved for this run so that the
    # same vulnerability class discovered on multiple pages gets a single
    # consistent title and groups together in the report.
    if raw_findings:
        with Session(get_engine()) as s:
            existing_saved = s.exec(
                select(ScanFinding).where(ScanFinding.test_run_id == run_id)
            ).all()
        if existing_saved:
            existing_summaries = [
                {"title": f.title, "owasp_category": f.owasp_category, "severity": f.severity}
                for f in existing_saved
            ]
            try:
                raw_findings = await llm_svc.normalize_finding_titles(
                    llm_cfg, existing_summaries, raw_findings
                )
            except Exception as _ne:
                log.warning("normalize_finding_titles failed for %s: %s", page_url, _ne)

    log.info("  %d findings for %s", len(raw_findings), page_url)
    if raw_findings:
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "page_analysis",
            "status": "complete",
            "page_url": page_url,
            "message": f"{len(raw_findings)} potential issue{'s' if len(raw_findings) != 1 else ''} identified",
            "data": {"finding_count": len(raw_findings)},
        })

    # Build a URL→result lookup so we can attach evidence + screenshot to each finding.
    result_by_url: dict[str, dict] = {}
    for r in results:
        if r.get("url"):
            result_by_url[r["url"]] = r

    saved_finding_ids: list[int] = []

    # Persist findings and mark page complete.
    with Session(get_engine()) as s:
        for f in raw_findings:
            finding = _finding_from_llm(
                run_id=run_id,
                page_id=page_id,
                page_url=page_url,
                raw=f,
                result_by_url=result_by_url,
            )
            s.add(finding)
            s.flush()
            if finding.id is not None:
                saved_finding_ids.append(finding.id)
        pg = s.get(CrawledPage, page_id)
        if pg:
            pg.scan_status = "complete"
            s.add(pg)
        s.commit()

    if saved_finding_ids:
        from aespa.services import validator as validator_svc
        for finding_id in saved_finding_ids:
            await validator_svc.validate_finding_inline(
                run_id,
                finding_id,
                llm_cfg=llm_cfg,
                cred_sessions=cred_sessions or {},
                scanner_policy=scanner_policy,
            )

    events_svc.emit(run_id, {"type": "node_scan_status", "page_id": page_id, "scan_status": "complete"})

    # ── Phase 4: Broken Access Control checks ────────────────────────────────
    # Only meaningful when multiple credentials exist and this page was not
    # accessible to at least one of them during the crawl.
    if (
        cred_sessions
        and len(cred_sessions) > 1
        and accessible_by  # skip pages no-one could access (no ground truth)
        and len(accessible_by) < len(cred_sessions)
    ):
        log.info("  Running BAC checks for %s (accessible_by=%s)", page_url, accessible_by)
        bac_findings = await _run_bac_checks(
            run_id=run_id,
            page_id=page_id,
            llm_cfg=llm_cfg,
            page_url=page_url,
            page_title=page_title,
            page_text=page_text,
            accessible_by=accessible_by,
            cred_sessions=cred_sessions,
            timeout=scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT,
            follow_redirects=scanner_policy.follow_redirects if scanner_policy else True,
        )
        if bac_findings:
            saved_bac_ids: list[int] = []
            with Session(get_engine()) as s:
                for bf in bac_findings:
                    bf.validation_status = "validating"
                    bf.validation_note = "Validation queued."
                    s.add(bf)
                    s.flush()
                    if bf.id is not None:
                        saved_bac_ids.append(bf.id)
                s.commit()
            log.info("  BAC: %d finding(s) saved for %s", len(bac_findings), page_url)
            _emit_scan_update(run_id)
            from aespa.services import validator as validator_svc
            for finding_id in saved_bac_ids:
                await validator_svc.validate_finding_inline(
                    run_id,
                    finding_id,
                    llm_cfg=llm_cfg,
                    cred_sessions=cred_sessions or {},
                    scanner_policy=scanner_policy,
                )


# ── Broken Access Control checks ─────────────────────────────────────────────

_LOGIN_MARKERS = [
    'type="password"', "type='password'", "input[type=password]",
    "login", "sign in", "sign_in", "forgot password",
]

async def _run_bac_checks(
    run_id: int,
    page_id: int,
    llm_cfg: LLMConfig,
    page_url: str,
    page_title: str,
    page_text: str,
    accessible_by: list[int],
    cred_sessions: dict[int, dict],
    timeout: float = REQUEST_TIMEOUT,
    follow_redirects: bool = True,
) -> list[ScanFinding]:
    """For each credential that was NOT able to access this page during the crawl,
    try a direct GET request with that credential's session cookies. A 200 response
    whose body contains the original page's protected content indicates a Broken
    Access Control vulnerability. A direct 200 alone is not enough: shared URLs
    often render user-specific content for each user."""
    findings: list[ScanFinding] = []

    unauthorized = {
        cid: cs for cid, cs in cred_sessions.items()
        if cid not in accessible_by
    }
    if not unauthorized:
        return findings

    for cred_id, session in unauthorized.items():
        username = session["username"]
        cookies  = session["cookies"]
        hdrs     = {"User-Agent": _UA, **session.get("extra_headers", {})}

        try:
            async with httpx.AsyncClient(
                cookies=cookies, headers=hdrs,
                follow_redirects=follow_redirects, verify=False, timeout=timeout,
            ) as client:
                resp = await client.get(page_url)

            if resp.status_code not in (200, 201, 202):
                log.debug("  BAC: %s as '%s' → HTTP %s (expected, access denied)",
                          page_url, username, resp.status_code)
                continue

            body_lower = resp.text[:2000].lower()
            login_hits = sum(1 for m in _LOGIN_MARKERS if m in body_lower)
            if login_hits >= 2:
                log.debug("  BAC: %s as '%s' → login page detected (score=%d)",
                          page_url, username, login_hits)
                continue

            body = resp.text[:BODY_READ_LIMIT]
            content_type = resp.headers.get("content-type", "")
            if _looks_like_spa_shell(body, content_type):
                log.debug("  BAC: %s as '%s' → generic SPA shell, not protected content",
                          page_url, username)
                continue

            if not _body_contains_original_page_evidence(body, page_title, page_text):
                log.debug("  BAC: %s as '%s' → direct access returned different user-specific content",
                          page_url, username)
                continue

            # Server returned original protected content to a user who did not
            # reach it during crawl discovery.
            log.info("  BAC: POSSIBLE — %s returned original content with HTTP %s for user '%s'",
                     page_url, resp.status_code, username)

            cookie_preview = "; ".join(
                f"{k}={v[:12]}…" for k, v in list(cookies.items())[:4]
            ) or "(none)"
            request_evidence = (
                f"GET {page_url} HTTP/1.1\n"
                f"Cookie: {cookie_preview}"
            )
            response_evidence = (
                f"HTTP/1.1 {resp.status_code}\n"
                f"Content-Type: {resp.headers.get('content-type', '')}\n"
                f"Content-Length: {len(resp.content)}\n\n"
                f"{resp.text[:1200]}"
            )
            result = {
                "desc": "Broken Access Control: unauthorized page access",
                "url": page_url,
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text[:2000],
                "evidence": (
                    "A user that lacked access during crawl discovery received "
                    "recognizable protected content via direct request."
                ),
                "request_evidence": request_evidence,
                "response_evidence": response_evidence,
                "screenshot_b64": None,
                "as_user": username,
            }
            try:
                generated = await llm_svc.analyse_probes(llm_cfg, page_url, [result])
            except Exception as e:
                log.warning("BAC finding write-up generation failed for %s: %s", page_url, e)
                generated = []
            for raw in generated:
                findings.append(_finding_from_llm(
                    run_id=run_id,
                    page_id=page_id,
                    page_url=page_url,
                    raw=raw,
                    result_by_url={page_url: result},
                ))

        except Exception as e:
            log.debug("  BAC check error for %s as '%s': %s", page_url, username, e)

    return findings


def _looks_like_spa_shell(body: str, content_type: str) -> bool:
    if "html" not in content_type.lower() and not body.lstrip().lower().startswith("<!doctype html"):
        return False
    body_lower = body[:5000].lower()
    shell_markers = sum(1 for marker in (
        '<div id="root"', "<div id='root'", '<div id="app"', "<div id='app'",
        "bundle.js", "main.js", "app.js", "vite", "webpack", "static/js",
    ) if marker in body_lower)
    text_only = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", body_lower)
    words = re.findall(r"[a-z0-9]{3,}", text_only)
    return shell_markers >= 1 and len(set(words)) < 80


def _body_contains_original_page_evidence(body: str, page_title: str, page_text: str) -> bool:
    body_lower = body.lower()
    candidates = _protected_content_candidates(page_title, page_text)
    return any(candidate.lower() in body_lower for candidate in candidates)


def _protected_content_candidates(page_title: str, page_text: str) -> list[str]:
    generic_words = {
        "dashboard", "home", "profile", "settings", "account", "overview", "welcome",
        "logout", "sign out", "navigation", "menu", "search", "submit", "cancel",
    }
    candidates: list[str] = []
    for line in (page_text or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not 24 <= len(line) <= 220:
            continue
        lower = line.lower()
        if lower in generic_words:
            continue
        if sum(1 for word in generic_words if word in lower) >= 4:
            continue
        candidates.append(line)
        if len(candidates) >= 12:
            break
    if not candidates and page_title and len(page_title.strip()) >= 12:
        title = page_title.strip()
        if title.lower() not in generic_words:
            candidates.append(title)
    return candidates


# ── Passive checks ────────────────────────────────────────────────────────────

async def _passive_checks(
    hx: httpx.AsyncClient,
    url: str,
    base_url: str,
    timeout: float = REQUEST_TIMEOUT,
) -> list[dict]:
    """Fire a single GET to the page and check response headers / cookies."""
    results = []
    try:
        resp = await hx.get(url, timeout=timeout)
        headers = dict(resp.headers)
        body = resp.text[:500]
        status = resp.status_code

        # Check security headers.
        security_headers = {
            "strict-transport-security": "HSTS",
            "content-security-policy": "Content-Security-Policy",
            "x-frame-options": "X-Frame-Options",
            "x-content-type-options": "X-Content-Type-Options",
            "referrer-policy": "Referrer-Policy",
            "permissions-policy": "Permissions-Policy",
        }
        missing = [
            label for hdr, label in security_headers.items()
            if hdr not in {k.lower() for k in headers}
        ]

        # Auth bypass: same request without cookies.
        auth_bypass_status: Optional[int] = None
        try:
            anon = await hx.get(url, timeout=timeout,
                                headers={"Cookie": "", "Authorization": ""})
            auth_bypass_status = anon.status_code
        except Exception:
            pass

        headers_text = "\n".join(f"{k}: {v}" for k, v in headers.items())
        request_evidence = f"GET {url} HTTP/1.1"
        response_evidence = (
            f"HTTP/1.1 {status}\n{headers_text}\n\n{body}"
            + (f"\n\nMissing security headers: {', '.join(missing)}" if missing else "")
            + (f"\nAnonymous request status: {auth_bypass_status}" if auth_bypass_status else "")
        )
        evidence = _combined_evidence(request_evidence, response_evidence)
        results.append({
            "desc": "Passive: headers + auth-bypass check",
            "url": url,
            "status": status,
            "headers": headers,
            "body": body,
            "evidence": evidence,
            "request_evidence": request_evidence,
            "response_evidence": response_evidence,
            "screenshot_b64": None,
            "missing_security_headers": missing,
            "auth_bypass_status": auth_bypass_status,
        })

        # Check cookies for Secure / HttpOnly flags.
        if resp.cookies:
            cookie_issues = []
            for raw in resp.headers.get_list("set-cookie"):
                name = raw.split("=")[0].strip()
                flags = raw.lower()
                issues = []
                if "secure" not in flags:
                    issues.append("missing Secure flag")
                if "httponly" not in flags:
                    issues.append("missing HttpOnly flag")
                if "samesite" not in flags:
                    issues.append("missing SameSite attribute")
                if issues:
                    cookie_issues.append(f"{name}: {', '.join(issues)}")
            if cookie_issues:
                issue_text = " | ".join(cookie_issues)
                results.append({
                    "desc": "Passive: cookie attribute check",
                    "url": url,
                    "status": status,
                    "headers": {},
                    "body": issue_text,
                    "evidence": _combined_evidence(
                        f"GET {url} HTTP/1.1",
                        f"Cookie issues:\n{issue_text}",
                    ),
                    "request_evidence": f"GET {url} HTTP/1.1",
                    "response_evidence": f"Cookie issues:\n{issue_text}",
                    "screenshot_b64": None,
                })

    except Exception as e:
        log.debug("Passive check failed for %s: %s", url, e)

    return results


# ── HTTP probe execution ──────────────────────────────────────────────────────

async def _run_http_probe(
    hx: httpx.AsyncClient,
    probe: dict,
    page_url: str,
    session: dict | None = None,
    scanner_policy=None,
) -> Optional[dict]:
    method       = probe.get("method", "GET").upper()
    url          = probe.get("url") or page_url
    params       = probe.get("params") or {}
    body         = probe.get("body")
    extra_hdrs   = probe.get("headers") or {}
    desc         = probe.get("desc", url)
    as_user      = probe.get("as_user") or None

    rejection = _probe_policy_rejection(probe, page_url, scanner_policy)
    if rejection:
        log.info("  Probe rejected by policy: %s (%s)", rejection, desc)
        return None

    content, request_headers, body_preview = _prepare_probe_body(body, extra_hdrs)

    async def _execute(client: httpx.AsyncClient) -> dict:
        req = client.build_request(
            method, url,
            params=params,
            content=content,
            headers=request_headers,
        )
        resp = await client.send(req, follow_redirects=True)
        response_text = resp.text[:2000]

        req_headers_text = "\n".join(f"{k}: {v}" for k, v in req.headers.items()
                                     if k.lower() not in ("cookie",))
        resp_headers_text = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
        user_note = f"Sent as user: {as_user}\n" if as_user else ""
        request_evidence = (
            f"{user_note}{method} {req.url} HTTP/1.1\n{req_headers_text}"
            + (f"\n\n{body_preview[:2000]}" if body_preview else "")
        )
        response_evidence = (
            f"HTTP/1.1 {resp.status_code}\n{resp_headers_text}\n\n{response_text}"
        )
        evidence = _combined_evidence(request_evidence, response_evidence)
        return {
            "desc": desc,
            "url": str(resp.url),
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": response_text,
            "evidence": evidence,
            "request_evidence": request_evidence,
            "response_evidence": response_evidence,
            "screenshot_b64": None,
            "as_user": as_user,
        }

    try:
        if session:
            async with httpx.AsyncClient(
                cookies=session["cookies"],
                headers={"User-Agent": _UA, **session.get("extra_headers", {})},
                timeout=scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT,
                follow_redirects=scanner_policy.follow_redirects if scanner_policy else True,
                verify=False,
            ) as session_hx:
                return await _execute(session_hx)
        else:
            return await _execute(hx)
    except Exception as e:
        request_evidence = f"{method} {url} HTTP/1.1"
        response_evidence = f"REQUEST ERROR: {e}"
        return {
            "desc": desc, "url": url, "status": None, "headers": {}, "body": str(e),
            "evidence": _combined_evidence(request_evidence, response_evidence),
            "request_evidence": request_evidence,
            "response_evidence": response_evidence,
            "screenshot_b64": None,
            "as_user": as_user,
        }


def _prepare_probe_body(body, headers: dict | None) -> tuple[bytes | None, dict, str]:
    request_headers = dict(headers or {})
    if body is None:
        return None, request_headers, ""

    if isinstance(body, bytes):
        return body, request_headers, body.decode("utf-8", errors="replace")

    if isinstance(body, str):
        return body.encode(), request_headers, body

    body_text = json.dumps(body, separators=(",", ":"))
    if not any(str(k).lower() == "content-type" for k in request_headers):
        request_headers["Content-Type"] = "application/json"
    return body_text.encode(), request_headers, body_text


_INJECTION_HINTS = (
    "sqli", "sql injection", "xss", "script", "onerror", "onload", "alert(1)",
    "union select", "sleep(", "waitfor delay", "pg_sleep", "or 1=1", "or '1'='1",
    "order by 999", "extractvalue", "autofocus", "javascript:alert",
)


def _prioritize_probes_for_cap(probes: list[dict], max_probes: int, categories: dict) -> list[dict]:
    if max_probes <= 0:
        return []
    if len(probes) <= max_probes:
        return probes

    injection: list[dict] = []
    idor: list[dict] = []
    auth: list[dict] = []
    other: list[dict] = []

    for probe in probes:
        desc = str(probe.get("desc") or "")
        haystack = " ".join([
            desc,
            str(probe.get("url") or ""),
            json.dumps(probe.get("params") or {}, default=str),
            json.dumps(probe.get("body"), default=str),
        ]).lower()
        if any(hint in haystack for hint in _INJECTION_HINTS):
            injection.append(probe)
        elif "idor" in desc.lower():
            idor.append(probe)
        elif "auth" in desc.lower() or (probe.get("headers") or {}).get("Authorization") == "":
            auth.append(probe)
        else:
            other.append(probe)

    if categories.get("takes_input"):
        injection_quota = max(1, min(len(injection), max_probes * 3 // 5))
    else:
        injection_quota = min(len(injection), max_probes)

    selected: list[dict] = []
    selected.extend(injection[:injection_quota])
    remaining = max_probes - len(selected)
    selected.extend(other[:remaining])
    remaining = max_probes - len(selected)
    selected.extend(auth[:remaining])
    remaining = max_probes - len(selected)
    selected.extend(idor[:remaining])
    remaining = max_probes - len(selected)
    if remaining > 0 and injection_quota < len(injection):
        selected.extend(injection[injection_quota:injection_quota + remaining])

    return selected[:max_probes]


def _probe_policy_rejection(probe: dict, page_url: str, scanner_policy) -> str | None:
    if scanner_policy is None:
        return None

    method = str(probe.get("method", "GET")).upper()
    allowed_methods = scanner_policy.methods_by_mode.get(scanner_policy.scan_mode, [])
    if method not in allowed_methods:
        return f"method {method} is not allowed in {scanner_policy.scan_mode} mode"

    url = probe.get("url") or page_url
    parsed = urlparse(str(url))
    page = urlparse(page_url)
    if parsed.scheme and parsed.scheme not in scanner_policy.allowed_schemes:
        return f"scheme {parsed.scheme} is not allowed"
    if parsed.netloc:
        target_host = (parsed.hostname or "").lower()
        page_host = (page.hostname or "").lower()
        if target_host != page_host:
            allowed_subdomain = (
                scanner_policy.allow_subdomains
                and page_host
                and target_host.endswith("." + page_host)
            )
            if not allowed_subdomain:
                return f"host {target_host or parsed.netloc} is outside the page scope"

    headers = probe.get("headers") or {}
    blocked = {h.lower() for h in scanner_policy.blocked_headers}
    for header in headers:
        if str(header).lower() in blocked:
            return f"header {header} is blocked by policy"

    body = probe.get("body")
    if body is not None:
        if isinstance(body, str):
            body_size = len(body.encode())
        elif isinstance(body, bytes):
            body_size = len(body)
        else:
            body_size = len(json.dumps(body).encode())
        if body_size > scanner_policy.max_request_body_bytes:
            return f"request body is {body_size} bytes; limit is {scanner_policy.max_request_body_bytes}"

    return None


# ── Playwright form probe execution ───────────────────────────────────────────

async def _run_thinking_browser_action(
    pw_page,
    action: dict,
    default_url: str,
    scanner_policy=None,
) -> dict:
    """Execute a compact browser action chosen by the Thinking scan LLM."""
    import base64 as _b64

    url = (action.get("url") or default_url).strip()
    steps = action.get("steps") if isinstance(action.get("steps"), list) else []
    if not steps:
        steps = [{"op": "goto", "url": url}, {"op": "snapshot"}]

    timeout_ms = int((scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT) * 1000)
    last_status: Optional[int] = None
    last_headers: dict = {}
    action_log: list[str] = []

    for raw_step in steps[:20]:
        if not isinstance(raw_step, dict):
            continue
        op = str(raw_step.get("op") or "").lower().strip()
        try:
            if op == "goto":
                step_url = (raw_step.get("url") or url or default_url).strip()
                action_log.append(f"goto {step_url}")
                resp = await pw_page.goto(step_url, wait_until="domcontentloaded", timeout=timeout_ms)
                if resp:
                    last_status = resp.status
                    try:
                        last_headers = await resp.all_headers()
                    except Exception:
                        last_headers = {}
            elif op in {"fill", "type"}:
                selector = raw_step.get("selector")
                value = str(raw_step.get("value") or "")
                if not selector:
                    action_log.append(f"{op} skipped: missing selector")
                    continue
                action_log.append(f"{op} {selector}={_compact_log_value(value, 120)}")
                loc = pw_page.locator(selector).first
                await loc.wait_for(state="visible", timeout=5_000)
                if op == "fill":
                    await loc.fill(value, timeout=5_000)
                else:
                    await loc.type(value, delay=20, timeout=5_000)
            elif op == "click":
                selector = raw_step.get("selector")
                if not selector:
                    action_log.append("click skipped: missing selector")
                    continue
                action_log.append(f"click {selector}")
                await pw_page.locator(selector).first.click(timeout=5_000)
            elif op == "press":
                selector = raw_step.get("selector")
                key = raw_step.get("key") or "Enter"
                if not selector:
                    action_log.append("press skipped: missing selector")
                    continue
                action_log.append(f"press {selector} {key}")
                await pw_page.locator(selector).first.press(str(key), timeout=5_000)
            elif op == "wait":
                if raw_step.get("ms") is not None:
                    ms = max(0, min(int(raw_step.get("ms") or 0), 10_000))
                    action_log.append(f"wait {ms}ms")
                    await asyncio.sleep(ms / 1000)
                else:
                    state = str(raw_step.get("state") or "networkidle")
                    if state not in {"domcontentloaded", "load", "networkidle"}:
                        state = "networkidle"
                    action_log.append(f"wait {state}")
                    await pw_page.wait_for_load_state(state, timeout=timeout_ms)
            elif op == "snapshot":
                action_log.append("snapshot")
            else:
                action_log.append(f"unsupported op: {op or '(missing)'}")
        except Exception as exc:
            action_log.append(f"{op or 'step'} failed: {exc}")

    try:
        await pw_page.wait_for_load_state("networkidle", timeout=2_000)
    except Exception:
        pass

    final_url = pw_page.url or url or default_url
    try:
        title = await pw_page.title()
    except Exception:
        title = ""
    try:
        visible_text = await pw_page.locator("body").inner_text(timeout=2_000)
    except Exception:
        visible_text = ""
    try:
        html = await pw_page.content()
    except Exception:
        html = ""

    screenshot_b64: Optional[str] = None
    try:
        raw_png = await pw_page.screenshot(full_page=False)
        screenshot_b64 = _b64.b64encode(raw_png).decode()
    except Exception:
        pass

    body = (
        f"Final URL: {final_url}\n"
        f"Title: {title}\n"
        f"Action log:\n" + "\n".join(f"- {line}" for line in action_log) + "\n\n"
        f"Visible text excerpt:\n{visible_text[:3000]}\n\n"
        f"HTML excerpt:\n{html[:3000]}"
    )
    request_evidence = (
        f"BROWSER ACTION\nInitial URL: {url or default_url}\n"
        f"Steps:\n{json.dumps(steps, indent=2)[:3000]}"
    )
    response_evidence = (
        f"Final URL: {final_url}\n"
        f"Title: {title}\n"
        f"Last response status: {last_status}\n\n"
        f"Action log:\n" + "\n".join(f"- {line}" for line in action_log) + "\n\n"
        f"Visible text excerpt:\n{visible_text[:3000]}"
    )
    return {
        "desc": action.get("note") or "Browser action",
        "url": final_url,
        "status": last_status,
        "headers": last_headers,
        "body": body,
        "evidence": _combined_evidence(request_evidence, response_evidence),
        "request_evidence": request_evidence,
        "response_evidence": response_evidence,
        "screenshot_b64": screenshot_b64,
    }


async def _run_form_probe(
    pw_page,
    probe: dict,
    page_url: str,
    session: dict | None = None,
    browser=None,
) -> Optional[dict]:
    url      = probe.get("url") or page_url
    selector = probe.get("selector", "input")
    payload  = probe.get("payload", "")
    submit   = probe.get("submit_selector", "button[type=submit]")
    desc     = probe.get("desc", selector)
    as_user  = probe.get("as_user") or None

    # If a specific user session is requested and we have a browser, spin up a
    # temporary context pre-loaded with that user's cookies.
    target_page = pw_page
    temp_ctx = None
    if session and browser:
        try:
            temp_ctx = await browser.new_context(user_agent=_UA, ignore_https_errors=True)
            cookie_list = [
                {"name": k, "value": v, "url": url}
                for k, v in session["cookies"].items()
            ]
            if cookie_list:
                await temp_ctx.add_cookies(cookie_list)
            target_page = await temp_ctx.new_page()
        except Exception as e:
            log.warning("Failed to create browser context for as_user=%s: %s", as_user, e)
            temp_ctx = None
            target_page = pw_page

    try:
        await target_page.goto(url, wait_until="domcontentloaded", timeout=15_000)
        await target_page.wait_for_selector(selector, state="visible", timeout=5_000)

        field = target_page.locator(selector).first
        await field.fill("")
        await field.type(payload, delay=20)

        # Capture the network response on submit.
        response_body = ""
        response_status: Optional[int] = None
        try:
            async with target_page.expect_response(
                lambda r: r.url.startswith(url.split("?")[0]),
                timeout=8_000,
            ) as resp_info:
                sub_btn = target_page.locator(submit).first
                if await sub_btn.count() > 0:
                    await sub_btn.click()
                else:
                    await field.press("Enter")
            resp = await resp_info.value
            response_status = resp.status
            try:
                response_body = (await resp.text())[:2000]
            except Exception:
                pass
        except Exception:
            try:
                await target_page.wait_for_load_state("networkidle", timeout=6_000)
            except Exception:
                pass
            response_body = (await target_page.content())[:2000]

        screenshot_b64: Optional[str] = None
        try:
            raw_png = await target_page.screenshot(full_page=False)
            import base64 as _b64
            screenshot_b64 = _b64.b64encode(raw_png).decode()
        except Exception:
            pass

        user_note = f"Sent as user: {as_user}\n" if as_user else ""
        request_evidence = (
            f"{user_note}FORM PROBE\nURL: {url}\n"
            f"Field selector: {selector}\nPayload: {payload}"
        )
        response_evidence = (
            f"Response status: {response_status}\n\n"
            f"Response body excerpt:\n{response_body}"
        )
        evidence = _combined_evidence(request_evidence, response_evidence)

        return {
            "desc": desc,
            "url": url,
            "payload": payload,
            "status": response_status,
            "headers": {},
            "body": response_body,
            "evidence": evidence,
            "request_evidence": request_evidence,
            "response_evidence": response_evidence,
            "screenshot_b64": screenshot_b64,
            "as_user": as_user,
        }
    except Exception as e:
        log.debug("Form probe error (%s): %s", desc, e)
        return None
    finally:
        if temp_ctx:
            await temp_ctx.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

_IDOR_STEPS = [1, 2, 3, 5, 10, 25, 50, 100, 250, 500]


def _idor_candidates(orig: int) -> list[int]:
    """Spread of IDs within ±500 of orig, skipping non-positive values."""
    seen: set[int] = set()
    for step in _IDOR_STEPS:
        for candidate in (orig - step, orig + step):
            if candidate > 0 and candidate != orig:
                seen.add(candidate)
    return sorted(seen)


def _find_crawled_ids(
    run_id: int,
    url: str,
    path_pos: int,
    current_id: int,
    my_accessible_by: list[int],
) -> list[int]:
    """Return IDs found in other crawled pages that share the same URL structure
    as `url` but differ only at path position `path_pos`.

    Cross-user IDs (pages owned by different credentials) come first so IDOR
    tests against real peer data are prioritised over sequential guessing.
    """
    parsed  = urlparse(url)
    parts   = parsed.path.split("/")

    with Session(get_engine()) as s:
        pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)   # noqa: E712
        ).all()

    cross_user: list[int] = []
    same_user:  list[int] = []

    for page in pages:
        pp = urlparse(page.url)
        if pp.netloc != parsed.netloc:
            continue
        pparts = pp.path.split("/")
        if len(pparts) != len(parts):
            continue
        # All segments must match except the one at path_pos
        if not all(
            i == path_pos or pparts[i] == parts[i]
            for i in range(len(parts))
        ):
            continue
        candidate_str = pparts[path_pos]
        if not re.match(r"^\d+$", candidate_str):
            continue
        cid = int(candidate_str)
        if cid == current_id:
            continue

        page_accessible = json.loads(page.accessible_by or "[]")
        # Cross-user: page was reachable by at least one cred NOT in my set
        if any(c not in my_accessible_by for c in page_accessible):
            cross_user.append(cid)
        else:
            same_user.append(cid)

    return cross_user + same_user


def _idor_expand(
    url: str,
    run_id: int,
    my_accessible_by: list[int],
    as_user: str | None = None,
) -> list[dict]:
    """Expand an IDOR marker into concrete HTTP probe dicts.

    For each numeric ID in the URL:
      1. Query the crawl DB for IDs found on other users' pages (same URL pattern).
         These are the highest-confidence IDOR candidates.
      2. Fall back to a ±500 spread if no crawled IDs are available.
    Each candidate is tested both authenticated (IDOR) and unauthenticated (auth-bypass).

    as_user: when set, expanded probes carry this username so the probe runner sends
    them using that user's pre-authenticated session.
    """
    probes: list[dict] = []
    parsed = urlparse(url)
    parts  = parsed.path.split("/")

    for i, part in enumerate(parts):
        if not re.match(r"^\d+$", part):
            continue
        orig = int(part)

        known = _find_crawled_ids(run_id, url, i, orig, my_accessible_by)
        candidates = known[:20] if known else _idor_candidates(orig)
        source = "crawled" if known else "range"

        for cid in candidates:
            new_parts = parts.copy()
            new_parts[i] = str(cid)
            test_url = urlunparse(parsed._replace(path="/".join(new_parts)))
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {}, "body": None,
                "as_user": as_user,
                "desc": f"IDOR [{source}]: /{part}→/{cid}"
                        + (f" (as {as_user})" if as_user else ""),
            })
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {"Cookie": "", "Authorization": ""}, "body": None,
                "as_user": None,
                "desc": f"IDOR+unauth [{source}]: /{part}→/{cid}",
            })

    # ── Query parameters ───────────────────────────────────────────────────────
    qs = parse_qs(parsed.query, keep_blank_values=True)
    base_params = {k: v[0] for k, v in qs.items()}
    for param, vals in qs.items():
        if not (vals and re.match(r"^\d+$", vals[0])):
            continue
        orig = int(vals[0])
        for cid in _idor_candidates(orig):
            np = {**base_params, param: str(cid)}
            test_url = urlunparse(parsed._replace(query=urlencode(np)))
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {}, "body": None,
                "as_user": as_user,
                "desc": f"IDOR [range]: ?{param}={vals[0]}→{cid}"
                        + (f" (as {as_user})" if as_user else ""),
            })

    return probes


# Common injection payloads used for takes_input pages.
_SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1'--",
    '" OR "1"="1"--',
    "admin'--",
    "1 OR 1=1--",
    "0 OR 1=1",
    "-1 OR 1=1",
    "1 AND SLEEP(0)--",
    "1 AND SLEEP(1)--",
    "'; WAITFOR DELAY '0:0:1'--",
    "1); SELECT pg_sleep(1)--",
    "1; SELECT 1--",
    "' UNION SELECT NULL--",
    "1' ORDER BY 999--",
    "' AND extractvalue(1,concat(0x7e,version()))--",
]
_XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    '"><script>alert(1)</script>',
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(1)",
    "'><svg onload=alert(1)>",
    "<svg onload=alert(1)>",
    "<details open ontoggle=alert(1)>",
    "' autofocus onfocus=alert(1) x='",
    "%3Cscript%3Ealert(1)%3C/script%3E",
]
_SSTI_PAYLOADS = ["{{7*7}}", "${7*7}", "<%= 7*7 %>", "#{7*7}"]
_PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "....//....//etc/passwd",
]
_SSRF_PAYLOADS = [
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.1/",
    "http://[::1]/",
]
_CMD_PAYLOADS = ["; echo aespa_probe", "| echo aespa_probe", "$(echo aespa_probe)"]


def _input_validation_probes(url: str, xss_canary: str = "") -> list[dict]:
    """Generate HTTP-level input validation probes for every query parameter."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if not qs:
        return []

    probes: list[dict] = []
    xss_payloads = list(_XSS_PAYLOADS)
    # Canary variants: using <canary> lets the sweep detect unescaped HTML rendering
    # even if the app blocks known dangerous tags like <script>.
    if xss_canary:
        xss_payloads = [
            f"<{xss_canary}>",                              # tag-context canary
            f"alert('{xss_canary}')",                       # JS-context canary (no outer script tag)
            f'"><img src=x onerror=alert("{xss_canary}")>', # attribute breakout
            f"<script>alert('{xss_canary}')</script>",      # full script canary
        ] + xss_payloads
    all_payloads = (
        [(p, "SQLi")  for p in _SQLI_PAYLOADS]
        + [(p, "XSS")   for p in xss_payloads]
        + [(p, "SSTI")  for p in _SSTI_PAYLOADS]
        + [(p, "Path")  for p in _PATH_TRAVERSAL_PAYLOADS]
        + [(p, "SSRF")  for p in _SSRF_PAYLOADS]
        + [(p, "CMDi")  for p in _CMD_PAYLOADS]
    )
    base_params = {k: v[0] for k, v in qs.items()}
    for param in list(qs.keys())[:3]:       # test up to 3 params
        for payload, label in all_payloads:
            np = dict(base_params)
            np[param] = payload
            test_url = urlunparse(parsed._replace(query=urlencode(np)))
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {}, "body": None,
                "desc": f"{label} in param '{param}': {payload[:40]}",
            })
    return probes[:30]


# ── Stored XSS sweep ──────────────────────────────────────────────────────────

async def _stored_xss_sweep(
    run_id: int,
    hx: httpx.AsyncClient,
    canary: str,
    scanner_policy=None,
) -> None:
    """Re-fetch every crawled page and check for the XSS canary appearing unescaped.

    This detects stored XSS where the injection source (input page A) and the rendering
    sink (output page B) are on different pages — a pattern the per-page probe loop
    cannot see because it only checks the response to the same request that injected.

    Detection logic:
      - Look for <canary> unescaped in the HTML.  If properly encoded it would appear as
        &lt;canary&gt; and NOT match the raw string, so any raw match is conclusive.
      - Also look for alert('canary') / alert("canary") to catch LLM-generated probes
        that used the canary as the alert argument rather than wrapping it in a tag.
    """
    timeout = scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT

    with Session(get_engine()) as s:
        pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)   # noqa: E712
        ).all()
        page_list = [(p.id, p.url) for p in pages]

    log.info("Stored XSS sweep: checking %d pages for canary '%s'", len(page_list), canary)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "sweep",
        "status": "start",
        "message": f"Stored XSS sweep: re-fetching {len(page_list)} pages for canary\u2026",
    })

    # Detection patterns: these can only appear unescaped if the app rendered
    # attacker-controlled input without HTML-encoding it.
    tag_canary    = f"<{canary}>"           # from <canary> payload
    alert_canary1 = f"alert('{canary}')"    # JS context, single-quote
    alert_canary2 = f'alert("{canary}")'    # JS context, double-quote
    detect_patterns = (tag_canary, alert_canary1, alert_canary2)

    findings_to_save: list[ScanFinding] = []
    already_reported: set[str] = set()

    for page_id, page_url in page_list:
        if run_id in _stop_requested:
            break
        if page_url in already_reported:
            continue
        try:
            resp = await hx.get(page_url, timeout=timeout)
            if resp.status_code != 200:
                continue
            body = resp.text
            matched = next((p for p in detect_patterns if p in body), None)
            if matched is None:
                continue

            already_reported.add(page_url)
            idx     = body.find(matched)
            snippet = body[max(0, idx - 150): idx + len(matched) + 150]

            log.info("Stored XSS sweep: canary '%s' found on %s (match: %s)", canary, page_url, matched)

            request_evidence  = f"GET {page_url} HTTP/1.1\n(Post-scan stored XSS sweep, authenticated session)"
            response_evidence = (
                f"HTTP/1.1 {resp.status_code}\n\n"
                f"Matched pattern: {matched!r}\n"
                f"Context (±150 chars):\n...{snippet}..."
            )
            evidence = _combined_evidence(
                request_evidence, response_evidence,
                f"XSS canary '{canary}' injected during scanning was found stored and "
                f"rendered unescaped in this page's HTML response.",
            )

            findings_to_save.append(ScanFinding(
                test_run_id=run_id,
                page_id=page_id,
                owasp_category="A03",
                severity="high",
                title="Stored Cross-Site Scripting (XSS)",
                description=(
                    f"A unique XSS canary ('{canary}') injected into an input field during "
                    f"scanning was found stored and rendered unescaped in the HTML of this page. "
                    f"The canary was not present before the scan and was injected as part of XSS "
                    f"probe payloads targeting input fields elsewhere in the application. "
                    f"It subsequently appeared in this page's response, confirming that "
                    f"user-supplied input is stored in the database and reflected without "
                    f"HTML encoding."
                ),
                impact=(
                    "An attacker who can submit a JavaScript payload through any of the "
                    "application's input fields will have that script executed in every "
                    "authenticated user's browser that visits this page, enabling session "
                    "hijacking, credential theft, keylogging, or arbitrary actions on "
                    "behalf of the victim."
                ),
                likelihood=(
                    "High. The canary was confirmed stored and reflected. A real attacker "
                    "would substitute a script payload (e.g. a session-stealing cookie "
                    "exfiltration script) in place of the benign canary used here."
                ),
                recommendation=(
                    "Apply context-aware output encoding to all database-stored user input "
                    "before rendering it in HTML (HTML entity encoding for HTML contexts, "
                    "JS escaping for script contexts). Adopt a templating engine that "
                    "auto-escapes by default. Implement a strict Content-Security-Policy "
                    "that blocks inline scripts. Audit all fields that accept and display "
                    "user-supplied content for missing output sanitisation."
                ),
                cvss_score=8.0,
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:L/A:N",
                affected_url=page_url,
                evidence=evidence[:4000],
                request_evidence=request_evidence[:4000],
                response_evidence=response_evidence[:4000],
                screenshot_b64=None,
                validation_status="confirmed",
                validation_note=(
                    f"Canary pattern '{matched}' found in page response during post-scan sweep."
                ),
                created_at=_utcnow(),
            ))

        except Exception as e:
            log.debug("Stored XSS sweep error for %s: %s", page_url, e)

        await sleep_between_probes(scanner_policy)

    if findings_to_save:
        with Session(get_engine()) as s:
            for f in findings_to_save:
                s.add(f)
            s.commit()
        log.info("Stored XSS sweep: %d finding(s) saved", len(findings_to_save))
        _emit_scan_update(run_id)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "sweep",
        "status": "complete",
        "message": (
            f"Stored XSS sweep complete \u2014 {len(findings_to_save)} finding(s)"
            if findings_to_save else
            "Stored XSS sweep complete \u2014 canary not found in any page"
        ),
        "data": {"findings_count": len(findings_to_save)},
    })


def _applicable_checks(categories: dict) -> list[str]:
    checks = ["A02", "A05", "A06", "A08", "A09"]  # always-on
    if categories.get("req_auth"):
        checks += ["A01", "A07"]
    if categories.get("takes_input"):
        checks += ["A03", "A10"]
    if categories.get("has_object_ref"):
        checks.append("A01")
    if categories.get("has_business_logic"):
        checks.append("A04")
    return sorted(set(checks))


def _emit_scan_update(run_id: int) -> None:
    status = get_scan_status(run_id)
    events_svc.emit(run_id, {"type": "scan_update", **status})


def _mark_run(run_id: int, scan_status: str, error: str = "") -> None:
    """Persist scan_status on the TestRun (stored in the error_message field prefix)."""
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return
        # We persist scan status as a prefixed error_message so no schema change is needed.
        run.error_message = f"scan:{scan_status}" if not error else f"scan:{scan_status}:{error}"
        s.add(run)
        s.commit()


def get_scan_status(run_id: int) -> dict:
    with Session(get_engine()) as s:
        pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
        ).all()
        total = len(pages)
        done  = sum(1 for p in pages if p.scan_status == "complete")
        findings_count = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all().__len__()

        run = s.get(TestRun, run_id)
        em = (run.error_message or "") if run else ""
        if em.startswith("scan:"):
            parts = em.split(":", 2)
            status = parts[1] if len(parts) > 1 else "idle"
        elif is_running(run_id):
            status = "running"
        else:
            status = "idle"

    return {
        "total_pages": total,
        "pages_done": done,
        "findings_count": findings_count,
        "status": status,
    }
