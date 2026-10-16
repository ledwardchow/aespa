"""One progress format for web and SAST runs.

Used by integrations that poll a run or send status callbacks. Everything here
only reads; it never changes a run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    PageOwaspTest,
    SastRun,
    SastWorkItem,
    ScanFinding,
    ScanLead,
    ScanLog,
    Site,
    TestRun,
)

# Overall state of a run, the same for every kind.
STATES = (
    "queued",
    "preparing",
    "running",
    "needs_action",
    "paused",
    "completed",
    "failed",
    "stopped",
)
TERMINAL_STATES = {"completed", "failed", "stopped"}
SEVERITIES = ("critical", "high", "medium", "low", "info")

_CRAWL_PHASES = {
    "created",
    "crawling",
    "exploring_workflows",
    "reconciling",
    "finalizing",
}
_REVIEW_PHASES = {"validating", "reporting"}
_WEB_UNFINISHED_CELLS = ("not_started", "in_progress")


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def run_kind(session: Session, run_id: int) -> str | None:
    """Return ``web`` or ``sast`` for a run ID. Run IDs are unique across kinds."""
    if session.get(TestRun, run_id) is not None:
        return "web"
    if session.get(SastRun, run_id) is not None:
        return "sast"
    return None


def _severity_counts(values: list[str]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for value in values:
        key = (value or "").lower()
        if key in counts:
            counts[key] += 1
    return counts


def _web_needs_action(session: Session, run: TestRun) -> dict | None:
    """Report a login that is waiting for a person at the browser."""
    from aespa.services import crawler

    site = session.get(Site, run.site_id)
    credentials = {cred.id: cred for cred in (site.credentials if site else [])}
    for credential_id, done in list(getattr(crawler, "_guided_registry", {}).items()):
        if credential_id in credentials and not done.is_set():
            cred = credentials[credential_id]
            return {
                "type": "guided_login",
                "credential_id": credential_id,
                "message": (
                    f"Sign in as {cred.label or cred.username or 'this user'} "
                    "in the AESPA browser window, then confirm in AESPA."
                ),
            }
    for key, event in list(getattr(crawler, "_entra_retry_registry", {}).items()):
        if key[0] == run.id and not event.is_set():
            return {
                "type": "authenticator_approval",
                "credential_id": key[1],
                "message": "Approve the Microsoft sign-in request, then retry in AESPA.",
            }
    return None


def _web_percent(session: Session, run_id: int) -> int | None:
    total = session.exec(
        select(func.count()).where(PageOwaspTest.test_run_id == run_id)
    ).one()
    if not total:
        return None
    unfinished = session.exec(
        select(func.count())
        .where(PageOwaspTest.test_run_id == run_id)
        .where(PageOwaspTest.status.in_(_WEB_UNFINISHED_CELLS))
    ).one()
    return int(round(100 * (total - unfinished) / total))


def _web_progress(session: Session, run: TestRun, scan_after_crawl: bool) -> dict:
    from aespa.services import crawl_then_pentest, crawler, scanner, validator

    run_id = run.id
    crawling = crawler.is_running(run_id)
    scanning = scanner.is_thinking_running(run_id)
    reviewing = validator.is_validating(run_id)
    scan_waiting = crawl_then_pentest.is_pending(run_id)
    status = str(run.status)
    percent: int | None = None
    message = ""

    if crawling or scan_waiting or scanning or reviewing:
        state = "running"
        if crawling:
            phase = "crawling"
            message = f"Crawled {run.pages_discovered} pages"
        elif scanning and run.phase not in _REVIEW_PHASES:
            phase = "scanning"
            percent = _web_percent(session, run_id)
            message = "Testing pages"
        elif scanning or reviewing:
            phase = "reviewing"
            message = "Checking findings"
        else:
            phase = "scanning"
            message = "Starting the scan"
    elif status == "paused":
        state, phase = "paused", run.phase
        message = run.terminal_reason or "Paused"
    elif status == "failed":
        state, phase = "failed", run.phase
    elif status == "stopped":
        state, phase = "stopped", run.phase
    elif status in {"complete", "incomplete"}:
        state, phase = "completed", "finished"
        if run.phase == "crawled":
            phase = "crawled"
            if scan_after_crawl:
                message = "The crawl finished but the scan did not start."
        else:
            percent = 100
    elif status == "running":
        # Saved as running, but no task is active (for example after a restart).
        state = "running"
        phase = "crawling" if run.phase in _CRAWL_PHASES else run.phase
    else:
        state, phase = "queued", "created"

    if state == "completed" and run.phase == "crawled" and scan_after_crawl:
        state = "failed"
    needs_action = _web_needs_action(session, run) if state == "running" else None
    if needs_action is not None:
        state = "needs_action"
        message = needs_action["message"]

    findings = session.exec(
        select(ScanFinding.severity).where(ScanFinding.test_run_id == run_id)
    ).all()
    return {
        "state": state,
        "phase": phase,
        "status": status,
        "outcome": run.outcome,
        "percent": percent,
        "message": message or (run.terminal_reason or ""),
        "counts": {
            "pages": run.pages_discovered,
            "max_pages": run.max_pages,
            "findings": _severity_counts(list(findings)),
        },
        "needs_action": needs_action,
        "error": run.error_message if state == "failed" else None,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.completed_at) if state in TERMINAL_STATES else None,
    }


def _sast_percent(session: Session, run_id: int) -> int | None:
    from aespa.services.sast_workprogram import TERMINAL_WORK_STATUSES

    total = session.exec(
        select(func.count()).where(SastWorkItem.sast_run_id == run_id)
    ).one()
    if not total:
        return None
    resolved = session.exec(
        select(func.count())
        .where(SastWorkItem.sast_run_id == run_id)
        .where(SastWorkItem.status.in_(TERMINAL_WORK_STATUSES))
    ).one()
    return int(round(100 * resolved / total))


def _sast_progress(session: Session, run: SastRun) -> dict:
    from aespa.services import sast_scanner, sast_sources

    run_id = run.id
    status = str(run.status)
    running = sast_scanner.is_sast_scan_running(run_id)
    preparing = sast_sources.is_source_preparation_running(run_id)
    percent: int | None = None
    message = ""
    if preparing or status == "preparing":
        state, phase, message = "preparing", "preparing_source", "Preparing the source"
    elif running or status in {"running", "scanning"}:
        state, phase = "running", "analyzing"
        percent = _sast_percent(session, run_id)
        message = "Reviewing the code"
    elif status == "paused":
        state, phase = "paused", "analyzing"
        message = run.error_message or "Paused"
    elif status in {"completed", "inconclusive"}:
        state, phase, percent = "completed", "finished", 100
    elif status == "failed":
        state, phase = "failed", "finished"
    elif status == "cancelled":
        state, phase = "stopped", "finished"
    else:
        state, phase = "queued", "created"

    leads = session.exec(
        select(ScanLead.severity)
        .where(ScanLead.producer_run_type == "sast")
        .where(ScanLead.producer_run_id == run_id)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        .where(ScanLead.reportable == True)  # noqa: E712
    ).all()
    return {
        "state": state,
        "phase": phase,
        "status": status,
        "outcome": (
            (status if status == "inconclusive" else run.completion_status)
            if state == "completed"
            else None
        ),
        "percent": percent,
        "message": message,
        "counts": {"findings": _severity_counts(list(leads))},
        "needs_action": None,
        "error": run.error_message if state == "failed" else None,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.completed_at) if state in TERMINAL_STATES else None,
    }


def get_progress(
    run_id: int, *, scan_after_crawl: bool = False, session: Session | None = None
) -> dict[str, Any] | None:
    """Return the run's progress, or ``None`` if no web or SAST run has this ID.

    ``scan_after_crawl`` tells a web run that a crawl alone is not the end of
    the job, so a crawl that finished without starting its scan is a failure.
    """
    if session is None:
        with Session(get_engine()) as owned:
            return get_progress(
                run_id, scan_after_crawl=scan_after_crawl, session=owned
            )
    web = session.get(TestRun, run_id)
    if web is not None:
        body = _web_progress(session, web, scan_after_crawl)
        return {"id": f"web-{run_id}", "kind": "web", "name": web.name, **body}
    sast = session.get(SastRun, run_id)
    if sast is not None:
        body = _sast_progress(session, sast)
        return {"id": f"sast-{run_id}", "kind": "sast", "name": sast.name, **body}
    return None


def list_activity(
    run_id: int, *, after: int = 0, limit: int = 100, session: Session | None = None
) -> list[dict[str, Any]]:
    """Return activity log lines after the cursor, oldest first."""
    if session is None:
        with Session(get_engine()) as owned:
            return list_activity(run_id, after=after, limit=limit, session=owned)
    rows = session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.id > after)
        .order_by(ScanLog.id)
        .limit(max(1, min(limit, 500)))
    ).all()
    return [
        {
            "cursor": row.id,
            "at": _iso(row.created_at),
            "phase": row.phase,
            "status": row.status,
            "message": row.message,
            "url": row.page_url,
        }
        for row in rows
    ]
