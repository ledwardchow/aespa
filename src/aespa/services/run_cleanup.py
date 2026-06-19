"""Reusable cascade-delete helpers for scan runs.

SQLite reuses the max autoincrement id, and ``TestRun`` / ``ApiTestRun`` /
``SastRun`` (plus ``ApiCollection``) all draw ids from independent counters that
collide.  When a run (or its parent collection) is deleted without removing its
child rows, a newly created run/collection reuses the freed id and inherits the
orphaned findings, traffic, logs, etc.  These helpers delete every row that keys
on a given run so nothing leaks into a reused id.

Each table is scoped to the run kind: findings/traffic key on the dedicated
``api_test_run_id`` column; coverage cells FK to ``api_test_run``; logs, scanner
sessions, and alice chats share the ``test_run_id`` column with web runs and are
disambiguated by ``run_kind`` / ``producer_run_type``.

The helpers ``session.delete`` rows but do not commit — the caller commits once,
so a collection delete can cascade many runs atomically.
"""
from __future__ import annotations

from sqlmodel import Session, select

from aespa.models import (
    AgentLog,
    AliceChatMessage,
    AliceChatSession,
    ApiEndpointTest,
    ApiTestRun,
    SastRun,
    ScanFinding,
    ScanLead,
    ScanLog,
    ScannerSession,
    TrafficEntry,
)


def cascade_delete_api_run(session: Session, run_id: int) -> None:
    """Delete an ``ApiTestRun`` and every row that keys on it."""
    for finding in session.exec(
        select(ScanFinding).where(ScanFinding.api_test_run_id == run_id)
    ).all():
        session.delete(finding)
    for entry in session.exec(
        select(TrafficEntry).where(TrafficEntry.api_test_run_id == run_id)
    ).all():
        session.delete(entry)
    for cell in session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == run_id)
    ).all():
        session.delete(cell)
    for ss in session.exec(
        select(ScannerSession)
        .where(ScannerSession.test_run_id == run_id)
        .where(ScannerSession.run_kind == "api")
    ).all():
        session.delete(ss)
    for slog in session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.run_kind == "api")
    ).all():
        session.delete(slog)
    for sess in session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .where(AliceChatSession.run_kind == "api")
    ).all():
        for msg in session.exec(
            select(AliceChatMessage).where(AliceChatMessage.session_id == sess.id)
        ).all():
            session.delete(msg)
        session.delete(sess)
    for log in session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "api")
    ).all():
        session.delete(log)
    run = session.get(ApiTestRun, run_id)
    if run is not None:
        session.delete(run)


def cascade_delete_sast_run(session: Session, run_id: int) -> None:
    """Delete a ``SastRun`` and every row that keys on it.

    Only the *original* leads are removed (``imported_into_run_id IS NULL``):
    copies imported into a dynamic run keep ``producer_run_id`` pointing here but
    belong to that run and are cleaned up when the run is deleted instead.
    """
    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_id == run_id)
        .where(ScanLead.producer_run_type == "sast")
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
    ).all():
        session.delete(lead)
    for slog in session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.run_kind == "sast")
    ).all():
        session.delete(slog)
    for log in session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "sast")
    ).all():
        session.delete(log)
    run = session.get(SastRun, run_id)
    if run is not None:
        # Best-effort removal of a standalone run's stored source archive.
        if run.source_archive_path:
            try:
                import os
                if os.path.isfile(run.source_archive_path):
                    os.remove(run.source_archive_path)
            except Exception:
                pass
        session.delete(run)
