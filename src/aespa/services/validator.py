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
import re
from typing import Optional

import httpx
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import Credential, CrawledPage, ScanFinding, Site, TestRun
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
_stop_requested: set[int] = set()


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
    unconfirmed = sum(1 for f in findings if f.validation_status == "unconfirmed")
    validating  = sum(1 for f in findings if f.validation_status == "validating")
    unvalidated = sum(1 for f in findings if f.validation_status == "unvalidated")
    if run_id in _stop_requested:
        status = "stopped"
    elif run_id in _validation_tasks:
        status = "running"
    elif total > 0 and unvalidated == 0 and validating == 0:
        status = "complete"
    else:
        status = "idle"
    return {
        "total": total,
        "confirmed": confirmed,
        "false_positives": false_pos,
        "unconfirmed": unconfirmed,
        "validating": validating,
        "unvalidated": unvalidated,
        "status": status,
    }


# ── Public entry points ───────────────────────────────────────────────────────

async def start_validation(run_id: int, finding_ids: list[int] | None = None) -> None:
    """Start validation as a background task. If a task is already running for this run, no-op."""
    if run_id in _validation_tasks:
        return
    _stop_requested.discard(run_id)
    task = asyncio.create_task(
        _validation_task(run_id, finding_ids=finding_ids),
        name=f"validate-{run_id}",
    )
    _validation_tasks[run_id] = task
    task.add_done_callback(lambda _: _validation_tasks.pop(run_id, None))


def request_stop(run_id: int) -> bool:
    """Request cancellation of background validation for a run."""
    task = _validation_tasks.get(run_id)
    if task is None:
        return False
    _stop_requested.add(run_id)
    _reset_validating_findings(run_id, "Validation stopped by user.")
    task.cancel()
    return True


async def validate_finding_inline(
    run_id: int,
    finding_id: int,
    llm_cfg=None,
    cred_sessions: dict[int, dict] | None = None,
    scanner_policy=None,
) -> None:
    """Validate a newly-created finding while a scan is still running."""
    loaded_llm_cfg = llm_cfg is None
    with Session(get_engine()) as s:
        finding = s.get(ScanFinding, finding_id)
        run = s.get(TestRun, run_id)
        if finding is None or run is None:
            return
        site = s.get(Site, run.site_id)
        if llm_cfg is None:
            llm_cfg = get_llm_config(s)
        if scanner_policy is None:
            scanner_policy = get_run_scanner_policy(s, run)
        creds = list(site.credentials) if site else []
        finding.validation_status = "validating"
        finding.validation_note = "Validation running."
        s.add(finding)
        s.commit()
        s.refresh(finding)
        loaded_objs = [finding, *creds, site, run]
        if loaded_llm_cfg:
            loaded_objs.append(llm_cfg)
        for obj in loaded_objs:
            if obj is not None:
                s.expunge(obj)

    events_svc.emit(run_id, {
        "type": "finding_validation_update",
        "finding_id": finding_id,
        "validation_status": "validating",
        "validation_note": "Validation running.",
    })

    if llm_cfg is None:
        await _persist_verdict(run_id, finding_id, "false_positive", "No LLM configuration was available for validation.")
        return

    if cred_sessions is None:
        cred_sessions = await _get_or_create_sessions(
            run_id, site.base_url.rstrip("/"), site.login_url,
            creds, site.requires_auth,
        ) if site else {}

    users_list: list[dict] | None = [
        {"username": cs["username"], "label": cs.get("label")}
        for cs in cred_sessions.values()
    ] or None
    user_sessions: dict[str, dict] = {cs["username"]: cs for cs in cred_sessions.values()}

    await _validate_one(
        run_id, finding, llm_cfg, user_sessions, users_list,
        scanner_policy, cred_sessions=cred_sessions,
    )


# ── Task wrapper ──────────────────────────────────────────────────────────────

async def _validation_task(run_id: int, finding_ids: list[int] | None = None) -> None:
    try:
        await _do_validate(run_id, finding_ids=finding_ids)
    except asyncio.CancelledError:
        log.info("Validation stopped for run_id=%s", run_id)
        _reset_validating_findings(run_id, "Validation stopped by user.")
    except Exception:
        log.exception("Validation task failed for run_id=%s", run_id)
        _reset_validating_findings(run_id, "Validation failed before a verdict was reached.")
    finally:
        _stop_requested.discard(run_id)


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
        if run_id in _stop_requested:
            _reset_validating_findings(run_id, "Validation stopped by user.")
            return
        await _validate_one(
            run_id, finding, llm_cfg, user_sessions, users_list,
            scanner_policy, cred_sessions=cred_sessions,
        )


async def _validate_one(
    run_id: int,
    finding: ScanFinding,
    llm_cfg,
    user_sessions: dict[str, dict],
    users_list: list[dict] | None,
    scanner_policy,
    cred_sessions: dict[int, dict] | None = None,
) -> None:
    log.info("Validating finding id=%s: %s", finding.id, finding.title)

    deterministic = await _deterministic_validate_finding(finding, cred_sessions or {}, scanner_policy)
    if deterministic:
        verdict, reasoning = deterministic
        await _persist_verdict(run_id, finding.id, verdict, reasoning)
        return

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
        await scanner_svc.sleep_between_probes(scanner_policy)

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

    await _persist_verdict(run_id, finding.id, verdict, reasoning)


async def _persist_verdict(run_id: int, finding_id: int, verdict: str, reasoning: str) -> None:
    with Session(get_engine()) as s:
        row = s.get(ScanFinding, finding_id)
        if row:
            row.validation_status = verdict
            row.validation_note = reasoning
            s.add(row)
        s.commit()

    events_svc.emit(run_id, {
        "type": "finding_validation_update",
        "finding_id": finding_id,
        "validation_status": verdict,
        "validation_note": reasoning,
    })


def _reset_validating_findings(run_id: int, note: str) -> None:
    with Session(get_engine()) as s:
        findings = s.exec(
            select(ScanFinding)
            .where(ScanFinding.test_run_id == run_id)
            .where(ScanFinding.validation_status == "validating")
        ).all()
        for finding in findings:
            finding.validation_status = "unvalidated"
            finding.validation_note = note
            s.add(finding)
        s.commit()

    for finding in findings:
        events_svc.emit(run_id, {
            "type": "finding_validation_update",
            "finding_id": finding.id,
            "validation_status": "unvalidated",
            "validation_note": note,
        })


async def _deterministic_validate_finding(
    finding: ScanFinding,
    cred_sessions: dict[int, dict],
    scanner_policy,
) -> tuple[str, str] | None:
    if not _is_access_control_finding(finding):
        return None
    if not cred_sessions:
        return ("unconfirmed", "Access-control validation could not run because no alternate user sessions were available.")

    with Session(get_engine()) as s:
        page = (
            s.get(CrawledPage, finding.page_id)
            if finding.page_id is not None
            else None
        )
        accessible_by = json.loads(page.accessible_by or "[]") if page else []
        page_text = page.page_text or "" if page else ""
        page_title = page.title or "" if page else ""

    if not accessible_by:
        return ("unconfirmed", "The crawl did not record a user that could access this page, so there is no access-control baseline to compare against.")

    unauthorized = {
        cred_id: session for cred_id, session in cred_sessions.items()
        if cred_id not in accessible_by
    }
    if not unauthorized:
        return ("unconfirmed", "No lower-privileged or unauthorized user session was available to reproduce the access-control issue.")

    url = finding.affected_url or ""
    if not url:
        return ("unconfirmed", "The finding did not include an affected URL to re-test.")

    for cred_id, session in unauthorized.items():
        username = session.get("username") or f"credential {cred_id}"
        try:
            async with httpx.AsyncClient(
                cookies=session.get("cookies", {}),
                headers={"User-Agent": _UA, **session.get("extra_headers", {})},
                timeout=scanner_policy.request_timeout_s,
                follow_redirects=scanner_policy.follow_redirects,
                verify=False,
            ) as client:
                resp = await client.get(url)
        except Exception as exc:
            return ("unconfirmed", f"Validation request as {username} failed: {exc}")

        if _response_denies_access(resp):
            continue

        body = resp.text[: scanner_policy.response_body_read_limit_bytes]
        content_type = resp.headers.get("content-type", "")
        if _looks_like_spa_shell(body, content_type):
            continue

        if _body_contains_page_evidence(body, page_title, page_text):
            return (
                "confirmed",
                f"Re-requesting the affected URL as {username} returned HTTP {resp.status_code} with protected-looking content rather than a denial or generic app shell.",
            )

    return (
        "false_positive",
        "Validation could not reproduce unauthorized access. Alternate users received an access denial, login response, generic SPA shell, or no protected content signal.",
    )


def _is_access_control_finding(finding: ScanFinding) -> bool:
    text = " ".join([
        finding.owasp_category or "",
        finding.title or "",
        finding.description or "",
    ]).lower()
    return any(term in text for term in (
        "a01", "access control", "authorization", "authorisation", "auth bypass",
        "broken access", "idor", "unauthorized", "unauthorised",
    ))


def _response_denies_access(resp: httpx.Response) -> bool:
    if resp.status_code in (401, 403, 404):
        return True
    if resp.status_code in (301, 302, 303, 307, 308) and "login" in str(resp.headers.get("location", "")).lower():
        return True
    body_lower = resp.text[:3000].lower()
    login_hits = sum(1 for marker in ("login", "sign in", "type=\"password\"", "type='password'", "forgot password") if marker in body_lower)
    denied_hits = sum(1 for marker in ("access denied", "forbidden", "unauthorized", "unauthorised", "not authorized", "not authorised") if marker in body_lower)
    return login_hits >= 2 or denied_hits >= 1


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


def _body_contains_page_evidence(body: str, page_title: str, page_text: str) -> bool:
    body_lower = body.lower()
    candidates: list[str] = []
    for line in (page_text or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if 24 <= len(line) <= 220:
            candidates.append(line)
        if len(candidates) >= 8:
            break
    if not candidates and page_title and len(page_title.strip()) >= 12:
        candidates.append(page_title.strip())
    return any(candidate.lower() in body_lower for candidate in candidates)


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

    content, request_headers, body_preview = scanner_svc._prepare_probe_body(body, extra_hdrs)

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
                content=content,
                headers=request_headers,
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
                + (f"\n{body_preview[:200]}" if body_preview else "")
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
