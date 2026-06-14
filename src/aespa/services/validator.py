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
import os
import re
import shlex
import subprocess
import tempfile
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import AdversarialValidatorConfig, Credential, CrawledPage, ScanFinding, Site, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import scanner as scanner_svc
from aespa.services.settings import get_adversarial_validator_config, get_llm_config, get_run_scanner_policy

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
        # Defensive: never run the site validator against an API-scan finding.
        # ApiTestRun and TestRun share an integer id space across separate tables,
        # so a stray inline-validation call with an ApiTestRun id can resolve to a
        # colliding (wrong) Site here. API findings are recorded via report_finding
        # and are not validated through the site/TestRun pipeline.
        if finding.api_test_run_id is not None:
            log.info(
                "Skipping inline validation for API finding %s (run_id=%s)",
                finding_id, run_id,
            )
            return
        site = s.get(Site, run.site_id)
        if llm_cfg is None:
            llm_cfg = get_llm_config(s)
        if scanner_policy is None:
            scanner_policy = get_run_scanner_policy(s, run)
        validator_cfg = get_adversarial_validator_config(s)
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
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": f"validator-{finding_id}",
        "role": "Validator",
        "status": "active",
        "current_task": f"Validating: {finding.title[:80]}",
        "outcome": None,
        "_persist": True,
    })

    if llm_cfg is None:
        await _persist_verdict(
            run_id,
            finding_id,
            "false_positive",
            "No LLM configuration was available for validation.",
            validation_results=[],
            source="validation_config",
        )
        return

    if cred_sessions is None:
        cred_sessions = await _get_or_create_sessions(
            run_id, str(site.base_url or "").strip(), site.login_url,
            creds, site.requires_auth,
        ) if site else {}

    users_list: list[dict] | None = [
        {"username": cs["username"], "label": cs.get("label")}
        for cs in cred_sessions.values()
    ] or None
    user_sessions: dict[str, dict] = {cs["username"]: cs for cs in cred_sessions.values()}

    await _validate_one(
        run_id, finding, llm_cfg, user_sessions, users_list,
        scanner_policy, cred_sessions=cred_sessions, validator_cfg=validator_cfg,
    )


# ── Task wrapper ──────────────────────────────────────────────────────────────

async def _validation_task(run_id: int, finding_ids: list[int] | None = None) -> None:
    llm_svc.set_run_context(run_id, lambda evt: events_svc.emit(run_id, evt))
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
        llm_svc.clear_run_context()


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
        validator_cfg = get_adversarial_validator_config(s)
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
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": f"validator-{f.id}",
            "role": "Validator",
            "status": "active",
            "current_task": f"Validating: {f.title[:80]}",
            "outcome": None,
            "_persist": True,
        })

    # Bootstrap sessions (reuse from active scan if possible).
    cred_sessions = await _get_or_create_sessions(
        run_id, str(site.base_url or "").strip(), site.login_url,
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
            scanner_policy, cred_sessions=cred_sessions, validator_cfg=validator_cfg,
        )


async def _run_adversarial_validator_loop(
    *,
    run_id: int,
    finding: ScanFinding,
    validator_cfg,
    llm_cfg,
    cred_sessions: dict[int, dict],
    scanner_policy,
) -> tuple[str, str, str, dict]:
    """Run the adversarial agentic validator loop for a single finding.

    Returns (verdict, reasoning, confidence, done_input) where verdict is
    "confirmed" or "false_positive" and done_input is the raw done() tool input
    (carrying any poc_request/poc_expect/poc_auth).
    """
    # Build the user message for the validator.
    disproof_hints = llm_svc._disproof_hints_for_finding(finding.owasp_category or "")
    initial_message = (
        f"**Finding to review**\n"
        f"Title: {finding.title}\n"
        f"OWASP Category: {finding.owasp_category or 'Unknown'}\n"
        f"Severity: {finding.severity or 'unknown'}\n"
        f"Affected URL: {finding.affected_url or 'unknown'}\n\n"
        f"**Description**\n{finding.description or 'No description.'}\n\n"
        f"**Scanner evidence**\n{finding.evidence or 'No evidence provided.'}"
    )
    if disproof_hints:
        initial_message += f"\n\n**Category-specific disproof strategies**\n{disproof_hints}"
    if validator_cfg.require_concrete_disproof:
        initial_message += (
            "\n\n**Validation mode: strict**\n"
            "Do NOT return false_positive unless you can state a specific innocent "
            "explanation. Failure to reproduce is not sufficient."
        )

    # Build a session map for the http_request tool (same format as scanner uses).
    # Key: username string → session dict with 'cookies' and 'extra_headers'.
    user_sessions_by_name: dict[str, dict] = {
        cs["username"]: cs for cs in cred_sessions.values()
    }
    primary_session = next(iter(user_sessions_by_name.values()), None)

    # Mutable verdict holder — set by the done() tool call.
    verdict_holder: list[tuple[str, str, str, dict]] = []
    step_counter: list[int] = [0]

    async def _tool_executor(tool_name: str, tool_input: dict, step: int) -> Any:  # noqa: ANN401
        step_counter[0] = step
        if tool_name == "http_request":
            return await _validator_http_request(
                tool_input, primary_session, user_sessions_by_name, scanner_policy, run_id=run_id
            )
        if tool_name == "compare_responses":
            return await _validator_compare_responses(
                tool_input, primary_session, user_sessions_by_name, scanner_policy, run_id=run_id
            )
        if tool_name == "context_tool":
            return await _validator_context_tool(tool_input, run_id, finding)
        if tool_name == "done":
            verdict = tool_input.get("verdict", "confirmed")
            reasoning = tool_input.get("reasoning", "")
            confidence = tool_input.get("confidence", "medium")
            verdict_holder.append((verdict, reasoning, confidence, dict(tool_input)))
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": f"validator-{finding.id}",
                "role": "Validator",
                "status": "active",
                "current_task": f"Verdict reached: {verdict}",
                "outcome": None,
                "_persist": True,
            })
            return {"verdict": verdict, "reasoning": reasoning}
        log.warning("Adversarial validator: unknown tool call '%s'", tool_name)
        return {"error": f"Unknown tool: {tool_name}"}

    def _stop_check() -> bool:
        return len(verdict_holder) > 0 or step_counter[0] >= validator_cfg.max_steps

    await llm_svc.thinking_agentic_loop(
        config=llm_cfg,
        system_message=llm_svc._ADVERSARIAL_VALIDATOR_SYSTEM,
        initial_user_message=initial_message,
        tool_executor=_tool_executor,
        stop_check=_stop_check,
        tools=llm_svc.VALIDATOR_AGENT_TOOLS,
    )

    if verdict_holder:
        return verdict_holder[0]
    # Step budget exhausted without a verdict.
    return (
        "confirmed",
        "Adversarial validator exhausted the step budget without finding a disproof.",
        "low",
        {},
    )


async def _validator_http_request(
    tool_input: dict,
    primary_session: dict | None,
    user_sessions: dict[str, dict],
    scanner_policy,
    run_id: Optional[int] = None,
) -> dict:
    method = (tool_input.get("method") or "GET").upper()
    url = tool_input.get("url", "")
    headers_in = tool_input.get("headers") or {}
    body = tool_input.get("body")
    use_session = tool_input.get("use_session")

    session = user_sessions.get(use_session) if use_session else primary_session
    cookies = session["cookies"] if session else {}
    hdrs = {"User-Agent": _UA, **(session.get("extra_headers", {}) if session else {})}

    content = None
    if body is not None:
        if isinstance(body, (dict, list)):
            content = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        else:
            content = str(body).encode()

    from aespa.services.traffic import LoggingAsyncClient
    try:
        async with LoggingAsyncClient(
            run_id=run_id,
            username=use_session or "validator",
            cookies=cookies,
            headers=hdrs,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=getattr(scanner_policy, "follow_redirects", True),
            verify=False,
        ) as client:
            req = client.build_request(method, url, content=content, headers=headers_in)
            t0 = time.perf_counter()
            resp = await client.send(req)
            duration_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:2000],
            "duration_ms": duration_ms,
            "url": str(resp.url),
        }
    except Exception as exc:
        return {"error": str(exc), "status": None, "headers": {}, "body": ""}


async def _validator_compare_responses(
    tool_input: dict,
    primary_session: dict | None,
    user_sessions: dict[str, dict],
    scanner_policy,
    run_id: Optional[int] = None,
) -> dict:
    """Execute baseline and test requests then return a comparison."""

    async def _fetch(spec: dict) -> dict:
        return await _validator_http_request(spec, primary_session, user_sessions, scanner_policy, run_id=run_id)

    baseline_spec = tool_input.get("baseline", {})
    test_spec = tool_input.get("test", {})
    note = tool_input.get("note", "")

    baseline_res, test_res = await asyncio.gather(
        _fetch(baseline_spec),
        _fetch(test_spec),
    )

    # Simple diff summary: status codes and body length difference.
    baseline_status = baseline_res.get("status")
    test_status = test_res.get("status")
    baseline_body = baseline_res.get("body", "")
    test_body = test_res.get("body", "")
    len_diff = len(test_body) - len(baseline_body)
    status_diff = (
        "same" if baseline_status == test_status
        else f"changed from {baseline_status} to {test_status}"
    )
    body_diff_summary = (
        f"Body length changed by {len_diff:+d} characters. "
        f"Status: {status_diff}."
    )

    return {
        "note": note,
        "baseline": baseline_res,
        "test": test_res,
        "diff_summary": body_diff_summary,
    }


async def _validator_context_tool(tool_input: dict, run_id: int, finding: ScanFinding) -> dict:
    """Provide finding context to the validator. Limited subset of the full context tool."""
    action = tool_input.get("action", "")
    if action == "get_finding":
        return {
            "id": finding.id,
            "title": finding.title,
            "description": finding.description,
            "owasp_category": finding.owasp_category,
            "severity": finding.severity,
            "affected_url": finding.affected_url,
            "evidence": finding.evidence,
        }
    # For other actions, return a helpful message rather than an error.
    return {"message": f"context_tool action '{action}' is not available to the validator. Use http_request or compare_responses to gather evidence directly."}


async def _validate_one(
    run_id: int,
    finding: ScanFinding,
    llm_cfg,
    user_sessions: dict[str, dict],
    users_list: list[dict] | None,
    scanner_policy,
    cred_sessions: dict[int, dict] | None = None,
    validator_cfg=None,
) -> None:
    log.info("Validating finding id=%s: %s", finding.id, finding.title)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "thinking_step",
        "status": "start",
        "message": f"Validating finding: {finding.title!r} — {finding.affected_url or 'no URL'}",
        "data": {"finding_id": finding.id},
    })

    # Load validator config lazily if not provided (e.g., from inline validation).
    if validator_cfg is None:
        with Session(get_engine()) as s:
            validator_cfg = get_adversarial_validator_config(s)

    deterministic = await _deterministic_validate_finding(finding, cred_sessions or {}, scanner_policy)
    if deterministic:
        verdict, reasoning, poc_spec = deterministic
        await _persist_verdict(
            run_id,
            finding.id,
            verdict,
            reasoning,
            validation_results=[],
            source="deterministic_validation",
        )
        if verdict == "confirmed":
            await _attach_poc_if_confirmed(
                run_id, finding,
                done_input=poc_spec,
                cred_sessions=cred_sessions or {},
                scanner_policy=scanner_policy,
            )
        return

    # Skip finding if it is below the configured severity threshold.
    if not llm_svc.severity_meets_threshold(
        str(finding.severity or "low"), validator_cfg.min_severity
    ):
        log.info(
            "  Skipping validation for finding %s (severity %s below threshold %s)",
            finding.id, finding.severity, validator_cfg.min_severity,
        )
        await _persist_verdict(
            run_id,
            finding.id,
            "unconfirmed",
            f"Skipped: severity '{finding.severity}' is below the configured threshold '{validator_cfg.min_severity}'.",
            validation_results=[],
            source="severity_threshold",
        )
        return

    # ── Adversarial validator (agentic loop) ─────────────────────────────────
    if validator_cfg.enabled:
        done_input: dict = {}
        try:
            verdict, reasoning, confidence, done_input = await _run_adversarial_validator_loop(
                run_id=run_id,
                finding=finding,
                validator_cfg=validator_cfg,
                llm_cfg=llm_cfg,
                cred_sessions=cred_sessions or {},
                scanner_policy=scanner_policy,
            )
        except Exception as e:
            log.warning("Adversarial validator loop failed for finding %s: %s", finding.id, e)
            verdict, reasoning = "confirmed", f"Adversarial validator encountered an error: {e}"
            confidence = "low"
        log.info("  Finding %s adversarial verdict: %s (confidence: %s)", finding.id, verdict, confidence)
        await _persist_verdict(
            run_id,
            finding.id,
            verdict,
            reasoning,
            validation_results=[],
            source="adversarial_validator",
        )
        if verdict == "confirmed":
            await _attach_poc_if_confirmed(
                run_id, finding,
                done_input=done_input,
                cred_sessions=cred_sessions or {},
                scanner_policy=scanner_policy,
            )
        return

    # ── Legacy static-probe fallback ─────────────────────────────────────────
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
                run_id=run_id,
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

    await _persist_verdict(
        run_id,
        finding.id,
        verdict,
        reasoning,
        validation_results=results,
        source="llm_validation",
    )


def _evidence_items_from_json(value: str | None) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _validation_evidence_items(
    *,
    verdict: str,
    reasoning: str,
    validation_results: list[dict] | None = None,
    source: str = "validation",
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [
        {
            "type": "validation_verdict",
            "label": "Validation verdict",
            "value": verdict,
            "confidence": verdict,
            "source": source,
        },
        {
            "type": "validation_reasoning",
            "label": "Validation reasoning",
            "value": reasoning or "No reasoning provided.",
            "confidence": verdict,
            "source": source,
        },
    ]
    for idx, result in enumerate((validation_results or [])[:3], start=1):
        summary = str(result.get("desc") or f"Validation probe {idx}")
        status = result.get("status")
        items.append({
            "type": "validation_probe",
            "label": f"Validation probe {idx}",
            "value": f"{summary}\nURL: {result.get('url') or ''}\nStatus: {status}",
            "confidence": verdict,
            "source": source,
            "metadata": {"url": result.get("url"), "status": status, "as_user": result.get("as_user")},
        })
        if result.get("duration_ms") is not None:
            items.append({
                "type": "timing",
                "label": f"Validation timing {idx}",
                "value": f"{round(float(result.get('duration_ms') or 0), 1)} ms",
                "confidence": verdict,
                "source": source,
            })
        if result.get("timing_delta_ms") is not None:
            items.append({
                "type": "timing_delta",
                "label": f"Validation timing delta {idx}",
                "value": f"{round(float(result.get('timing_delta_ms') or 0), 1)} ms",
                "confidence": verdict,
                "source": source,
            })
        if result.get("body_diff"):
            diff = result.get("body_diff")
            items.append({
                "type": "body_diff",
                "label": f"Validation body diff {idx}",
                "value": json.dumps(diff, indent=2, sort_keys=True) if isinstance(diff, dict) else str(diff),
                "confidence": verdict,
                "source": source,
            })
        if result.get("action_outcome"):
            items.append({
                "type": "action_outcome",
                "label": f"Validation action outcome {idx}",
                "value": str(result.get("action_outcome") or ""),
                "confidence": verdict,
                "source": source,
            })
        if result.get("request_evidence"):
            items.append({
                "type": "validation_request",
                "label": f"Validation request {idx}",
                "value": str(result.get("request_evidence") or ""),
                "format": "http",
                "confidence": verdict,
                "source": source,
            })
        if result.get("response_evidence"):
            items.append({
                "type": "validation_response",
                "label": f"Validation response {idx}",
                "value": str(result.get("response_evidence") or ""),
                "format": "http",
                "confidence": verdict,
                "source": source,
            })
    return items


async def _persist_verdict(
    run_id: int,
    finding_id: int,
    verdict: str,
    reasoning: str,
    *,
    validation_results: list[dict] | None = None,
    source: str = "validation",
) -> None:
    evidence_json = "[]"
    evidence_items: list[dict[str, Any]] = []
    finding_title = f"Finding #{finding_id}"
    with Session(get_engine()) as s:
        row = s.get(ScanFinding, finding_id)
        if row:
            finding_title = row.title or finding_title
            existing_items = _evidence_items_from_json(row.evidence_json)
            evidence_items = existing_items + _validation_evidence_items(
                verdict=verdict,
                reasoning=reasoning,
                validation_results=validation_results,
                source=source,
            )
            evidence_json = scanner_svc._evidence_items_json(*evidence_items)
            row.validation_status = verdict
            row.validation_note = reasoning
            row.evidence_json = evidence_json
            s.add(row)
        s.commit()

    events_svc.emit(run_id, {
        "type": "finding_validation_update",
        "finding_id": finding_id,
        "validation_status": verdict,
        "validation_note": reasoning,
        "evidence_json": evidence_json,
        "evidence_items": _evidence_items_from_json(evidence_json),
    })
    # Emit agent_status complete for this validator agent.
    outcome_map = {
        "confirmed": "Confirmed",
        "false_positive": "False positive",
        "unconfirmed": "Unconfirmed",
    }
    outcome_str = outcome_map.get(verdict, verdict.capitalize())
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": f"validator-{finding_id}",
        "role": "Validator",
        "status": "complete",
        "current_task": finding_title,
        "outcome": outcome_str,
        "_persist": True,
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
) -> tuple[str, str, dict | None] | None:
    if not _is_access_control_finding(finding):
        return None
    if not cred_sessions:
        return ("unconfirmed", "Access-control validation could not run because no alternate user sessions were available.", None)

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
        return ("unconfirmed", "The crawl did not record a user that could access this page, so there is no access-control baseline to compare against.", None)

    unauthorized = {
        cred_id: session for cred_id, session in cred_sessions.items()
        if cred_id not in accessible_by
    }
    if not unauthorized:
        return ("unconfirmed", "No lower-privileged or unauthorized user session was available to reproduce the access-control issue.", None)

    url = finding.affected_url or ""
    if not url:
        return ("unconfirmed", "The finding did not include an affected URL to re-test.", None)

    for cred_id, session in unauthorized.items():
        username = session.get("username") or f"credential {cred_id}"
        try:
            from aespa.services.traffic import LoggingAsyncClient
            async with LoggingAsyncClient(
                run_id=finding.test_run_id,
                username=username,
                cookies=session.get("cookies", {}),
                headers={"User-Agent": _UA, **session.get("extra_headers", {})},
                timeout=scanner_policy.request_timeout_s,
                follow_redirects=scanner_policy.follow_redirects,
                verify=False,
            ) as client:
                resp = await client.get(url)
        except Exception as exc:
            return ("unconfirmed", f"Validation request as {username} failed: {exc}", None)

        if _response_denies_access(resp):
            continue

        body = resp.text[: scanner_policy.response_body_read_limit_bytes]
        content_type = resp.headers.get("content-type", "")
        if _looks_like_spa_shell(body, content_type):
            continue

        evidence_match = _first_page_evidence_match(body, page_title, page_text)
        if evidence_match:
            poc_spec = {
                "poc_request": {"method": "GET", "url": url, "use_session": username},
                "poc_expect": {"status": resp.status_code, "body_contains": evidence_match},
                "poc_auth": {
                    "mechanism": "cookie_httponly",
                    "instructions": (
                        f"Log in as **{username}** (a user who should NOT be able to "
                        "access this resource) and capture that session."
                    ),
                },
            }
            return (
                "confirmed",
                f"Re-requesting the affected URL as {username} returned HTTP {resp.status_code} with protected-looking content rather than a denial or generic app shell.",
                poc_spec,
            )

    return (
        "false_positive",
        "Validation could not reproduce unauthorized access. Alternate users received an access denial, login response, generic SPA shell, or no protected content signal.",
        None,
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
    return bool(_first_page_evidence_match(body, page_title, page_text))


def _page_evidence_candidates(page_title: str, page_text: str) -> list[str]:
    candidates: list[str] = []
    for line in (page_text or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if 24 <= len(line) <= 220:
            candidates.append(line)
        if len(candidates) >= 8:
            break
    if not candidates and page_title and len(page_title.strip()) >= 12:
        candidates.append(page_title.strip())
    return candidates


def _first_page_evidence_match(body: str, page_title: str, page_text: str) -> str:
    body_lower = body.lower()
    for candidate in _page_evidence_candidates(page_title, page_text):
        if candidate.lower() in body_lower:
            return candidate
    return ""


# ── Proof-of-concept generation + verification ────────────────────────────────
# When a finding is confirmed, build a single runnable validation command and
# re-execute it (curl, in a temp dir) to prove it actually reproduces the issue.
# Only verified commands are persisted — "it works, or don't have it".

_POC_AUTH_FILE = "aespa-poc-auth.txt"
_POC_SAFE_METHODS = {"GET", "HEAD"}
_POC_BLOCKED_HEADERS = {"authorization", "cookie", "host", "content-length"}
_POC_MAX_HEADERS = 12
_POC_MAX_URL_LEN = 2048
_POC_TIMEOUT_S = 20


async def _attach_poc_if_confirmed(
    run_id: int,
    finding: ScanFinding,
    *,
    done_input: dict | None,
    cred_sessions: dict[int, dict],
    scanner_policy,
) -> None:
    """Build, verify, and persist a PoC command for a confirmed finding.

    Stores nothing if no reproducible request is available or verification fails.
    """
    if not isinstance(done_input, dict):
        return
    user_sessions_by_name: dict[str, dict] = {
        cs["username"]: cs for cs in cred_sessions.values() if cs.get("username")
    }
    try:
        built = await _build_and_verify_poc(
            finding, done_input, user_sessions_by_name, scanner_policy
        )
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("PoC build/verify failed for finding %s: %s", finding.id, exc)
        return
    if not built:
        return
    command, setup = built
    with Session(get_engine()) as s:
        row = s.get(ScanFinding, finding.id)
        if row is None:
            return
        row.poc_command = command
        row.poc_setup = setup
        s.add(row)
        s.commit()
    finding.poc_command = command
    finding.poc_setup = setup
    events_svc.emit(run_id, {
        "type": "finding_validation_update",
        "finding_id": finding.id,
        "poc_command": command,
        "poc_setup": setup,
    })
    log.info("Verified PoC attached to finding %s", finding.id)


async def _build_and_verify_poc(
    finding: ScanFinding,
    done_input: dict,
    user_sessions_by_name: dict[str, dict],
    scanner_policy,
) -> tuple[str, str] | None:
    poc_request = done_input.get("poc_request")
    if not isinstance(poc_request, dict):
        return None

    url = str(poc_request.get("url") or "").strip()
    if not _poc_url_in_scope(url, finding.affected_url):
        return None
    if len(url) > _POC_MAX_URL_LEN:
        return None

    method = str(poc_request.get("method") or "GET").upper()
    if method not in _POC_SAFE_METHODS:
        # Never ship a command that could mutate state.
        return None

    headers = _sanitise_poc_headers(poc_request.get("headers"))

    expect = poc_request_expect(done_input)
    if expect is None:
        return None

    # Resolve auth, if the request needs a session.
    use_session = str(poc_request.get("use_session") or "").strip()
    auth: dict | None = None
    setup = ""
    if use_session:
        session = user_sessions_by_name.get(use_session)
        if not session:
            return None
        poc_auth = done_input.get("poc_auth") if isinstance(done_input.get("poc_auth"), dict) else {}
        mechanism = str(poc_auth.get("mechanism") or "cookie_httponly")
        auth = _resolve_poc_auth(session, mechanism)
        if not auth:
            return None
        setup = _build_poc_setup(mechanism, use_session, str(poc_auth.get("instructions") or ""))

    command = _build_curl_command(
        method,
        url,
        headers,
        insecure=True,
        follow_redirects=bool(getattr(scanner_policy, "follow_redirects", True)),
        auth=auth,
    )

    verified = await asyncio.to_thread(
        _run_and_assert_curl, command, expect, auth["file_value"] if auth else None
    )
    if not verified:
        return None
    return command, setup


def poc_request_expect(done_input: dict) -> dict | None:
    """Return a usable assertion dict, or None if no positive assertion exists."""
    expect = done_input.get("poc_expect")
    if not isinstance(expect, dict):
        return None
    status = expect.get("status")
    body_contains = str(expect.get("body_contains") or "").strip()
    if not isinstance(status, int) and not body_contains:
        # Without a status or distinctive substring we cannot prove anything.
        return None
    return {
        "status": status if isinstance(status, int) else None,
        "body_contains": body_contains,
        "body_not_contains": str(expect.get("body_not_contains") or "").strip(),
    }


def _poc_url_in_scope(url: str, affected_url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    affected = urlparse(affected_url or "")
    # Constrain the PoC to the same host as the finding to avoid SSRF/out-of-scope.
    return bool(affected.netloc) and parsed.netloc.lower() == affected.netloc.lower()


def _sanitise_poc_headers(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    headers: dict[str, str] = {}
    for key, value in raw.items():
        name = str(key).strip()
        if not name or name.lower() in _POC_BLOCKED_HEADERS:
            continue
        headers[name] = str(value)
        if len(headers) >= _POC_MAX_HEADERS:
            break
    return headers


def _resolve_poc_auth(session: dict, mechanism: str) -> dict | None:
    """Resolve the live credential into a file value + header template.

    Returns {file_value, header_name, header_prefix} or None when the session
    cannot supply the requested credential type.
    """
    if mechanism == "bearer":
        extra = session.get("extra_headers", {}) or {}
        auth_value = next(
            (v for k, v in extra.items() if str(k).lower() == "authorization"),
            "",
        )
        token = str(auth_value).strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if not token:
            return None
        return {"file_value": token, "header_name": "Authorization", "header_prefix": "Bearer "}

    # cookie_readable / cookie_httponly both reproduce via the Cookie header.
    cookies = session.get("cookies", {}) or {}
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    if not cookie_str:
        return None
    return {"file_value": cookie_str, "header_name": "Cookie", "header_prefix": ""}


def _build_curl_command(
    method: str,
    url: str,
    headers: dict[str, str],
    *,
    insecure: bool,
    follow_redirects: bool,
    auth: dict | None,
) -> str:
    # Everything model-derived is shlex-quoted; only our own constant auth header
    # uses a shell substitution to read the credential from the token file.
    args = ["curl", "-s", "-S", "-i"]
    if insecure:
        args.append("-k")
    if follow_redirects:
        args.append("-L")
    args += ["--max-time", str(_POC_TIMEOUT_S)]
    if method != "GET":
        args += ["-X", method]
    for name, value in headers.items():
        args += ["-H", f"{name}: {value}"]
    args.append(url)
    command = shlex.join(args)
    if auth:
        command += f' -H "{auth["header_name"]}: {auth["header_prefix"]}$(cat {_POC_AUTH_FILE})"'
    return command


def _run_and_assert_curl(command: str, expect: dict, auth_file_value: str | None) -> bool:
    """Run the exact PoC command in a throwaway dir and check the assertion."""
    with tempfile.TemporaryDirectory(prefix="aespa-poc-") as tmp:
        if auth_file_value is not None:
            with open(os.path.join(tmp, _POC_AUTH_FILE), "w", encoding="utf-8") as fh:
                fh.write(auth_file_value)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=_POC_TIMEOUT_S + 10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log.debug("PoC curl execution failed: %s", exc)
            return False
    output = proc.stdout or ""
    return _poc_assertion_holds(expect, output)


def _poc_assertion_holds(expect: dict, output: str) -> bool:
    status_matches = re.findall(r"(?im)^HTTP/\d(?:\.\d)?\s+(\d{3})", output)
    last_status = int(status_matches[-1]) if status_matches else None
    expected_status = expect.get("status")
    if isinstance(expected_status, int):
        if last_status != expected_status:
            return False
    body_contains = expect.get("body_contains") or ""
    if body_contains and body_contains not in output:
        return False
    body_not_contains = expect.get("body_not_contains") or ""
    if body_not_contains and body_not_contains in output:
        return False
    # Require at least one positive signal to have been checked.
    return bool(isinstance(expected_status, int) or body_contains)


def _build_poc_setup(mechanism: str, username: str, instructions: str) -> str:
    """Markdown setup steps for capturing the session credential to a token file."""
    lines = [
        f"This finding requires an authenticated session (log in as **{username}** "
        "or an equivalent user).",
    ]
    if instructions.strip():
        lines.append("")
        lines.append(instructions.strip())
    lines.append("")
    lines.append(
        f"Capture the credential into a file named `{_POC_AUTH_FILE}` in the directory "
        "you run the command from:"
    )
    if mechanism == "bearer":
        lines.append("")
        lines.append("In the browser DevTools Console (adjust the storage key for the app):")
        lines.append("```js")
        lines.append("const token = localStorage.getItem('token'); // or sessionStorage")
        lines.append("const a = document.createElement('a');")
        lines.append(
            "a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));"
        )
        lines.append(f"a.download = '{_POC_AUTH_FILE}'; a.click();")
        lines.append("```")
    elif mechanism == "cookie_readable":
        lines.append("")
        lines.append("In the browser DevTools Console:")
        lines.append("```js")
        lines.append("const a = document.createElement('a');")
        lines.append(
            "a.href = URL.createObjectURL(new Blob([document.cookie], {type:'text/plain'}));"
        )
        lines.append(f"a.download = '{_POC_AUTH_FILE}'; a.click();")
        lines.append("```")
    else:  # cookie_httponly — JavaScript cannot read the cookie.
        lines.append("")
        lines.append(
            "The session cookie is HttpOnly, so JavaScript cannot read it. Instead, in "
            "DevTools open the **Network** tab, reload the page, click the request, and "
            f"copy the full `Cookie:` request header value into `{_POC_AUTH_FILE}`."
        )
    lines.append("")
    lines.append(f"Then move `{_POC_AUTH_FILE}` next to where you run the command below.")
    return "\n".join(lines)


# ── Probe execution ───────────────────────────────────────────────────────────

async def _run_validation_probe(
    probe: dict,
    primary_session: dict | None,
    override_session: dict | None,
    page_url: str,
    scanner_policy,
    run_id: Optional[int] = None,
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
        from aespa.services.traffic import LoggingAsyncClient
        async with LoggingAsyncClient(
            run_id=run_id,
            username=as_user or "validator",
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
            started = time.perf_counter()
            resp = await client.send(req, follow_redirects=scanner_policy.follow_redirects)
            duration_ms = int((time.perf_counter() - started) * 1000)
            resp_body = resp.text[:min(800, scanner_policy.response_body_read_limit_bytes)]
            req_hdrs_text = "\n".join(
                f"{k}: {v}" for k, v in req.headers.items() if k.lower() != "cookie"
            )
            resp_hdrs_text = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
            user_note = f"Sent as user: {as_user}\n" if as_user else ""
            request_evidence = scanner_svc._request_evidence(
                f"{user_note}{method} {req.url} HTTP/1.1\n{req_hdrs_text}"
                + (f"\n\n{body_preview}" if body_preview else "")
            )
            response_evidence = scanner_svc._response_evidence(
                f"HTTP/1.1 {resp.status_code}\n{resp_hdrs_text}\n\n{resp_body}"
            )
            evidence = (
                f"REQUEST:\n{request_evidence}\n\nRESPONSE:\n{response_evidence}"
            )
            return {
                "desc": desc,
                "url": str(resp.url),
                "status": resp.status_code,
                "duration_ms": duration_ms,
                "headers": dict(resp.headers),
                "body": resp_body,
                "action_outcome": "Validation probe completed.",
                "evidence": evidence,
                "request_evidence": request_evidence,
                "response_evidence": response_evidence,
                "as_user": as_user,
            }
    except Exception as e:
        request_evidence = scanner_svc._request_evidence(f"{method} {url} HTTP/1.1")
        response_evidence = scanner_svc._response_evidence(f"REQUEST ERROR: {e}")
        return {
            "desc": desc, "url": url, "status": None,
            "headers": {}, "body": str(e),
            "action_outcome": "Validation probe failed before receiving a response.",
            "evidence": f"REQUEST:\n{request_evidence}\n\nRESPONSE:\n{response_evidence}",
            "request_evidence": request_evidence,
            "response_evidence": response_evidence,
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
