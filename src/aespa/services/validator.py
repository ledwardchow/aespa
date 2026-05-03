"""Finding validator service.

For each unvalidated finding:
  1. Mark validation_status = "validating" and emit an event.
  2. LLM generates targeted validation probes for the specific finding.
  3. Probes are executed with per-user session support (reusing active scan sessions when
     available, otherwise bootstrapping fresh Playwright sessions).
  4. LLM reviews the probe traffic and returns a verdict: confirmed | false_positive.
  5. finding.validation_status and finding.validation_note are updated, and an event is emitted.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import Credential, ScanFinding, Site, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import scanner as scanner_svc
from aespa.services.settings import get_llm_config, get_run_scanner_policy

log = logging.getLogger("aespa.validator")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 10.0

# ── In-memory state ───────────────────────────────────────────────────────────

_validation_tasks: dict[int, asyncio.Task] = {}  # run_id → running task


def is_validating(run_id: int) -> bool:
    return run_id in _validation_tasks


def get_validation_status(run_id: int) -> dict:
    with Session(get_engine()) as s:
        findings = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all()
    total = len(findings)
    confirmed   = sum(1 for f in findings if f.validation_status == "confirmed")
    false_pos   = sum(1 for f in findings if f.validation_status == "false_positive")
    validating  = sum(1 for f in findings if f.validation_status == "validating")
    unvalidated = sum(1 for f in findings if f.validation_status == "unvalidated")
    if run_id in _validation_tasks:
        status = "running"
    elif total > 0 and unvalidated == 0 and validating == 0:
        status = "complete"
    else:
        status = "idle"
    return {
        "total": total,
        "confirmed": confirmed,
        "false_positives": false_pos,
        "validating": validating,
        "unvalidated": unvalidated,
        "status": status,
    }


# ── Public entry points ───────────────────────────────────────────────────────

async def start_validation(run_id: int, finding_ids: list[int] | None = None) -> None:
    """Start validation as a background task. If a task is already running for this run, no-op."""
    if run_id in _validation_tasks:
        return
    task = asyncio.create_task(
        _validation_task(run_id, finding_ids=finding_ids),
        name=f"validate-{run_id}",
    )
    _validation_tasks[run_id] = task
    task.add_done_callback(lambda _: _validation_tasks.pop(run_id, None))


# ── Task wrapper ──────────────────────────────────────────────────────────────

async def _validation_task(run_id: int, finding_ids: list[int] | None = None) -> None:
    try:
        await _do_validate(run_id, finding_ids=finding_ids)
    except Exception:
        log.exception("Validation task failed for run_id=%s", run_id)


# ── Core validation ───────────────────────────────────────────────────────────

async def _do_validate(run_id: int, finding_ids: list[int] | None = None) -> None:
    # Load run configuration.
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config(s)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration — configure it in Settings first.")
        scanner_policy = get_run_scanner_policy(s, run)
        creds = list(site.credentials)
        for obj in [*creds, site, llm_cfg, run]:
            s.expunge(obj)

    # Load the findings to validate.
    with Session(get_engine()) as s:
        q = select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        if finding_ids:
            q = q.where(ScanFinding.id.in_(finding_ids))
        else:
            q = q.where(ScanFinding.validation_status == "unvalidated")
        findings = s.exec(q).all()
        for f in findings:
            s.expunge(f)

    if not findings:
        log.info("Validation: no findings to validate for run_id=%s", run_id)
        return

    # Mark all target findings as "validating" immediately.
    with Session(get_engine()) as s:
        for f in findings:
            row = s.get(ScanFinding, f.id)
            if row:
                row.validation_status = "validating"
                s.add(row)
        s.commit()
    for f in findings:
        events_svc.emit(run_id, {
            "type": "finding_validation_update",
            "finding_id": f.id,
            "validation_status": "validating",
        })

    # Bootstrap sessions (reuse from active scan if possible).
    cred_sessions = await _get_or_create_sessions(
        run_id, site.base_url.rstrip("/"), site.login_url,
        creds, site.requires_auth,
    )

    users_list: list[dict] | None = [
        {"username": cs["username"], "label": cs.get("label")}
        for cs in cred_sessions.values()
    ] or None
    user_sessions: dict[str, dict] = {cs["username"]: cs for cs in cred_sessions.values()}

    # Validate each finding sequentially.
    for finding in findings:
        await _validate_one(run_id, finding, llm_cfg, user_sessions, users_list, scanner_policy)


async def _validate_one(
    run_id: int,
    finding: ScanFinding,
    llm_cfg,
    user_sessions: dict[str, dict],
    users_list: list[dict] | None,
    scanner_policy,
) -> None:
    log.info("Validating finding id=%s: %s", finding.id, finding.title)

    # Phase 1: LLM generates targeted validation probes.
    try:
        probes = await llm_svc.plan_validation_probes(
            config=llm_cfg,
            title=finding.title,
            description=finding.description,
            affected_url=finding.affected_url,
            evidence=finding.evidence,
            owasp_category=finding.owasp_category,
            severity=finding.severity,
            users=users_list,
        )
    except Exception as e:
        log.warning("plan_validation_probes failed for finding %s: %s", finding.id, e)
        probes = []

    log.info("  %d validation probes for finding %s", len(probes), finding.id)

    # Phase 2: Execute probes.
    results: list[dict] = []
    primary_session = next(iter(user_sessions.values()), None) if user_sessions else None

    for probe in probes:
        try:
            as_user_name = probe.get("as_user") or None
            session = user_sessions.get(as_user_name) if as_user_name else None
            result = await _run_validation_probe(
                probe, primary_session, session,
                page_url=finding.affected_url,
                scanner_policy=scanner_policy,
            )
            if result:
                results.append(result)
        except Exception as e:
            log.debug("Validation probe error (%s): %s", probe.get("desc", "?"), e)
        await asyncio.sleep(scanner_policy.min_delay_s)

    # Phase 3: LLM determines verdict.
    try:
        verdict_data = await llm_svc.validate_finding_result(
            config=llm_cfg,
            title=finding.title,
            description=finding.description,
            evidence=finding.evidence,
            probe_results=results,
        )
    except Exception as e:
        log.warning("validate_finding_result failed for finding %s: %s", finding.id, e)
        verdict_data = {"verdict": "confirmed", "reasoning": f"Validation error: {e}"}

    verdict = verdict_data.get("verdict", "confirmed")
    reasoning = verdict_data.get("reasoning", "")
    log.info("  Finding %s verdict: %s", finding.id, verdict)

    # Phase 4: Persist verdict.
    with Session(get_engine()) as s:
        row = s.get(ScanFinding, finding.id)
        if row:
            row.validation_status = verdict
            row.validation_note = reasoning
            s.add(row)
        s.commit()

    events_svc.emit(run_id, {
        "type": "finding_validation_update",
        "finding_id": finding.id,
        "validation_status": verdict,
        "validation_note": reasoning,
    })


# ── Probe execution ───────────────────────────────────────────────────────────

async def _run_validation_probe(
    probe: dict,
    primary_session: dict | None,
    override_session: dict | None,
    page_url: str,
    scanner_policy,
) -> Optional[dict]:
    """Execute a single HTTP probe using the appropriate session."""
    method     = probe.get("method", "GET").upper()
    url        = probe.get("url", "")
    params     = probe.get("params") or {}
    body       = probe.get("body")
    extra_hdrs = probe.get("headers") or {}
    desc       = probe.get("desc", url)
    as_user    = probe.get("as_user") or None

    rejection = scanner_svc._probe_policy_rejection(probe, page_url, scanner_policy)
    if rejection:
        log.info("  Validation probe rejected by policy: %s (%s)", rejection, desc)
        return None

    # Use the override session (specific user) if provided, else the primary.
    session = override_session or primary_session
    cookies = session["cookies"] if session else {}
    hdrs = {"User-Agent": _UA, **(session.get("extra_headers", {}) if session else {})}

    try:
        async with httpx.AsyncClient(
            cookies=cookies,
            headers=hdrs,
            timeout=scanner_policy.request_timeout_s,
            follow_redirects=scanner_policy.follow_redirects,
            verify=False,
        ) as client:
            req = client.build_request(
                method, url,
                params=params,
                content=body.encode() if isinstance(body, str) else body,
                headers=extra_hdrs,
            )
            resp = await client.send(req, follow_redirects=scanner_policy.follow_redirects)
            resp_body = resp.text[:min(800, scanner_policy.response_body_read_limit_bytes)]
            req_hdrs_text = "\n".join(
                f"{k}: {v}" for k, v in req.headers.items() if k.lower() != "cookie"
            )
            resp_hdrs_text = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
            user_note = f"Sent as user: {as_user}\n" if as_user else ""
            evidence = (
                f"{user_note}REQUEST:\n{method} {req.url} HTTP/1.1\n{req_hdrs_text}\n"
                + (f"\n{body[:200]}" if body else "")
                + f"\n\nRESPONSE:\nHTTP/1.1 {resp.status_code}\n{resp_hdrs_text}\n\n{resp_body}"
            )
            return {
                "desc": desc,
                "url": str(resp.url),
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp_body,
                "evidence": evidence,
                "as_user": as_user,
            }
    except Exception as e:
        return {
            "desc": desc, "url": url, "status": None,
            "headers": {}, "body": str(e),
            "evidence": f"REQUEST ERROR: {e}",
            "as_user": as_user,
        }


# ── Session management ────────────────────────────────────────────────────────

async def _get_or_create_sessions(
    run_id: int,
    base_url: str,
    login_url: Optional[str],
    creds: list[Credential],
    requires_auth: bool,
) -> dict[int, dict]:
    # Prefer sessions already established by an active scan.
    active = scanner_svc.get_active_sessions(run_id)
    if active:
        log.info("Validator: reusing %d active scanner sessions for run_id=%s", len(active), run_id)
        return active

    if not requires_auth or not creds:
        return {}

    log.info("Validator: bootstrapping %d sessions for run_id=%s", len(creds), run_id)
    cred_sessions: dict[int, dict] = {}
    for cred in creds:
        try:
            cookies, token = await scanner_svc._export_cred_session(base_url, login_url, cred)
            cred_sessions[cred.id] = {
                "username": cred.username,
                "label": getattr(cred, "label", None),
                "cookies": cookies,
                "extra_headers": {"Authorization": f"Bearer {token}"} if token else {},
            }
            log.info("  Bootstrapped session for user=%s", cred.username)
        except Exception as e:
            log.warning("  Failed to bootstrap session for user=%s: %s", cred.username, e)
    return cred_sessions
