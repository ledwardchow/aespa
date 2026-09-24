"""Run web active scanners supplied by trusted extensions."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.extensions import WebScanCandidate, WebScanContext, get_extension_manager
from aespa.models import ScanFinding, Site, TestRun
from aespa.services import events
from aespa.services.references import ensure_finding_reference
from aespa.services.scope import check_scope, scope_authority

log = logging.getLogger(__name__)
_tasks: dict[tuple[int, str], set[asyncio.Task]] = {}
_targets: set[tuple[int, str, str, str]] = set()


def _agent_id(scanner_id: str, candidate: WebScanCandidate) -> str:
    digest = hashlib.sha256(
        f"{scanner_id}:{candidate.vulnerability_class}:{candidate.url}".encode()
    ).hexdigest()[:12]
    prefix = scanner_id.split(".", 1)[0]
    return f"{prefix}-{digest}"


def _emit(
    run_id: int,
    scanner,
    candidate: WebScanCandidate,
    agent_id: str,
    status: str,
    message: str,
    *,
    task_id: str | None = None,
    outcome: str | None = None,
) -> None:
    phase = getattr(scanner, "phase", "external_active_scan")
    role = getattr(scanner, "agent_role", scanner.label)
    events.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": phase,
            "status": status,
            "message": message,
            "data": {
                "finding_id": candidate.finding_id,
                "url": candidate.url,
                "vuln_class": candidate.vulnerability_class,
                "task_id": task_id,
            },
        },
    )
    agent_status = {
        "start": "active",
        "running": "active",
        "complete": "complete",
        "error": "failed",
        "cancelled": "stopped",
    }[status]
    events.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": agent_id,
            "role": role,
            "status": agent_status,
            "current_task": f"Active scan: {candidate.url} ({candidate.vulnerability_class})",
            "outcome": outcome,
            "_persist": True,
        },
    )


def _auth(session_vault: dict) -> tuple[dict[str, str], dict[str, str]]:
    for session in (session_vault or {}).values():
        if session.get("kind") == "anonymous":
            continue
        cookies = dict(session.get("cookies") or {})
        headers = dict(session.get("extra_headers") or {})
        if cookies or headers:
            return cookies, headers
    return {}, {}


def _in_scope(run_id: int, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        site = session.get(Site, run.site_id) if run else None
        if site is None:
            return False
        # An empty explicit scope still means the site's own authority.
        if not site.scope_hosts or site.scope_hosts == "[]":
            if scope_authority(url) != scope_authority(site.base_url):
                return False
        site_id = site.id
    return check_scope(url, site_id, run_id) is None


def _save_issues(run_id: int, scanner, candidate: WebScanCandidate, result) -> int:
    saved = 0
    source = getattr(scanner, "finding_source", scanner.id)
    with Session(get_engine()) as session:
        for issue in result.issues:
            if not _in_scope(run_id, issue.affected_url):
                continue
            exists = session.exec(
                select(ScanFinding.id)
                .where(ScanFinding.test_run_id == run_id)
                .where(ScanFinding.affected_url == issue.affected_url)
                .where(ScanFinding.title == issue.title)
                .limit(1)
            ).first()
            if exists is not None:
                continue
            finding = ScanFinding(
                test_run_id=run_id,
                page_id=candidate.page_id,
                owasp_category=issue.owasp_category,
                severity=issue.severity,
                title=issue.title,
                description=issue.description,
                impact="",
                likelihood=f"Confidence: {issue.confidence}",
                recommendation=issue.recommendation,
                cvss_score=0.0,
                cvss_vector="",
                affected_url=issue.affected_url,
                evidence=f"{scanner.label} task {result.task_id} identified: {issue.title}",
                request_evidence=issue.request_evidence,
                response_evidence=issue.response_evidence,
                evidence_json="[]",
                screenshot_b64=None,
                finding_source=source,
                validation_status="confirmed",
                validation_note=f"Confirmed by {scanner.label} (task {result.task_id}).",
                created_at=datetime.now(timezone.utc),
            )
            session.add(finding)
            ensure_finding_reference(session, finding)
            saved += 1
        session.commit()
    if saved:
        from aespa.services.scanner import _emit_scan_update

        _emit_scan_update(run_id)
    return saved


async def _run(
    run_id: int,
    extension_id: str,
    scanner,
    candidate: WebScanCandidate,
    session_vault: dict,
) -> None:
    agent_id = _agent_id(scanner.id, candidate)
    target_key = (run_id, scanner.id, candidate.vulnerability_class, candidate.url)
    if not _in_scope(run_id, candidate.url):
        _targets.discard(target_key)
        return
    with events.run_kind_scope("web"):
        _emit(
            run_id,
            scanner,
            candidate,
            agent_id,
            "start",
            f"{scanner.label} triggered for {candidate.vulnerability_class} on {candidate.url}",
        )
        started = False
        try:
            manager = get_extension_manager()
            base_context = manager.context_for(extension_id)
            cookies, extra_headers = _auth(session_vault)

            def on_started(task_id: str) -> None:
                nonlocal started
                started = True
                _emit(
                    run_id,
                    scanner,
                    candidate,
                    agent_id,
                    "running",
                    f"{scanner.label} task {task_id} is running",
                    task_id=task_id,
                )

            context = WebScanContext(
                extension_id,
                base_context.settings,
                base_context.secrets,
                cookies=cookies,
                extra_headers=extra_headers,
                on_started=on_started,
            )
            if candidate.specialist_attack_class:
                from aespa.services.scanner import _schedule_external_specialist

                _schedule_external_specialist(
                    run_id,
                    candidate.url,
                    candidate.specialist_attack_class,
                    session_vault,
                )
            result = await scanner.scan(candidate, context)
            saved = _save_issues(run_id, scanner, candidate, result)
            _emit(
                run_id,
                scanner,
                candidate,
                agent_id,
                "complete",
                f"{scanner.label} task {result.task_id} complete: {len(result.issues)} issues, {saved} saved",
                task_id=result.task_id,
                outcome=f"{len(result.issues)} issues, {saved} saved",
            )
        except asyncio.CancelledError:
            _targets.discard(target_key)
            _emit(
                run_id,
                scanner,
                candidate,
                agent_id,
                "cancelled",
                f"{scanner.label} scan cancelled",
                outcome="Cancelled",
            )
            raise
        except Exception as exc:
            if not started:
                _targets.discard(target_key)
            log.warning(
                "External scanner %s failed for %s: %s", scanner.id, candidate.url, exc
            )
            _emit(
                run_id,
                scanner,
                candidate,
                agent_id,
                "error",
                f"{scanner.label} scan failed: {exc}",
                outcome=str(exc)[:200],
            )


def _schedule(
    run_id: int, session_vault: dict, kind: str, payload: dict[str, Any], note: str = ""
) -> None:
    manager = get_extension_manager()
    manager.ensure_loaded()
    for registered in list(manager.web_scanners.values()):
        extension_id, scanner = registered.extension_id, registered.scanner
        try:
            settings = manager.get_settings(extension_id)
            candidate = (
                scanner.candidate_from_finding(payload, settings)
                if kind == "finding"
                else scanner.candidate_from_investigation(payload, note, settings)
            )
            if candidate is None or not _in_scope(run_id, candidate.url):
                continue
            key = (run_id, scanner.id, candidate.vulnerability_class, candidate.url)
            if key in _targets:
                continue
            task = asyncio.get_running_loop().create_task(
                _run(run_id, extension_id, scanner, candidate, session_vault),
                name=f"external-scan-{run_id}-{scanner.id}",
            )
            _targets.add(key)
            task_key = (run_id, extension_id)
            _tasks.setdefault(task_key, set()).add(task)

            def finish_task(
                finished: asyncio.Task,
                task_key: tuple[int, str] = task_key,
                target_key: tuple[int, str, str, str] = key,
            ) -> None:
                tasks = _tasks.get(task_key)
                if tasks is not None:
                    tasks.discard(finished)
                    if not tasks:
                        _tasks.pop(task_key, None)
                if finished.cancelled():
                    _targets.discard(target_key)

            task.add_done_callback(finish_task)
        except RuntimeError:
            return
        except Exception:
            log.exception("Could not schedule external scanner %s", scanner.id)


def schedule_finding(run_id: int, finding: ScanFinding, session_vault: dict) -> None:
    _schedule(
        run_id,
        session_vault,
        "finding",
        {
            "id": finding.id,
            "page_id": finding.page_id,
            "title": finding.title,
            "description": finding.description,
            "owasp_category": finding.owasp_category,
            "affected_url": finding.affected_url,
        },
    )


def schedule_investigation(
    run_id: int, tool_input: dict, note: str, session_vault: dict
) -> None:
    _schedule(run_id, session_vault, "investigation", tool_input, note)


def cancel_run(run_id: int) -> None:
    for (task_run_id, _extension_id), tasks in list(_tasks.items()):
        if task_run_id == run_id:
            for task in list(tasks):
                task.cancel()


def cancel_extension(extension_id: str) -> None:
    for (_run_id, task_extension_id), tasks in list(_tasks.items()):
        if task_extension_id == extension_id:
            for task in list(tasks):
                task.cancel()
