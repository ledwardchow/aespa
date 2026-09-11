"""Console-only database backup and cleanup operations."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy import delete, text
from sqlmodel import Session, SQLModel, select

from aespa.db import get_engine
from aespa.models import (
    ApiTestRun,
    AssessmentCampaign,
    PublicReferenceNamespace,
    SastRun,
    TestRun,
)
from aespa.services import run_cleanup


class DatabaseOperationError(RuntimeError):
    """Raised when a database operation cannot run safely."""


def _has_active_jobs(session: Session) -> bool:
    from aespa.services import (
        alice_tasks,
        api_scanner,
        campaigns,
        code_execution,
        crawler,
        sast_scanner,
        scanner,
        validator,
    )

    for run_id in session.exec(select(TestRun.id)).all():
        alice = alice_tasks.get(run_id, run_type="site")
        if (
            crawler.is_running(run_id)
            or scanner.is_thinking_running(run_id)
            or validator.is_validating(run_id)
            or (alice is not None and not alice.done)
        ):
            return True
    for run_id in session.exec(select(ApiTestRun.id)).all():
        alice = alice_tasks.get(run_id, run_type="api")
        if api_scanner.is_api_scan_running(run_id) or (
            alice is not None and not alice.done
        ):
            return True
    if any(
        sast_scanner.is_sast_scan_running(run_id)
        for run_id in session.exec(select(SastRun.id)).all()
    ):
        return True
    if any(
        campaigns.is_campaign_running(campaign_id)
        for campaign_id in session.exec(select(AssessmentCampaign.id)).all()
    ):
        return True
    return code_execution.has_active_executions()


def _require_idle(session: Session) -> None:
    if _has_active_jobs(session):
        raise DatabaseOperationError(
            "Stop all active scans and agent jobs before changing the database."
        )


def backup_database(destination: Path) -> Path:
    """Create a consistent SQLite backup at *destination*."""
    engine = get_engine()
    if engine.dialect.name != "sqlite":
        raise DatabaseOperationError("Database backup currently requires SQLite.")

    destination = destination.expanduser().resolve()
    if destination.exists():
        raise DatabaseOperationError(f"Backup file already exists: {destination}")
    if not destination.parent.is_dir():
        raise DatabaseOperationError(
            f"Backup folder does not exist: {destination.parent}"
        )

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with engine.connect() as connection:
            source = connection.connection.driver_connection
            with sqlite3.connect(temporary) as target:
                source.backup(target)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def clear_scans() -> int:
    """Delete every scan run while preserving targets and configuration."""
    with Session(get_engine()) as session:
        _require_idle(session)
        run_count = len(session.exec(select(TestRun.id)).all())
        run_count += len(session.exec(select(ApiTestRun.id)).all())
        run_count += len(session.exec(select(SastRun.id)).all())
        run_count += len(session.exec(select(AssessmentCampaign.id)).all())

        for campaign_id in list(session.exec(select(AssessmentCampaign.id)).all()):
            run_cleanup.cascade_delete_campaign(session, campaign_id)
        session.flush()
        for run_id in list(session.exec(select(TestRun.id)).all()):
            run_cleanup.cascade_delete_web_run(session, run_id)
        for run_id in list(session.exec(select(ApiTestRun.id)).all()):
            run_cleanup.cascade_delete_api_run(session, run_id)
        for run_id in list(session.exec(select(SastRun.id)).all()):
            run_cleanup.cascade_delete_sast_run(session, run_id)

        session.execute(
            delete(PublicReferenceNamespace).where(
                PublicReferenceNamespace.owner_type.in_(
                    ("web", "api", "sast", "campaign")
                )
            )
        )
        session.commit()
        return run_count


def reset_database() -> None:
    """Delete every application record while retaining the database schema."""
    with Session(get_engine()) as session:
        _require_idle(session)
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.execute(delete(table))
        if get_engine().dialect.name == "sqlite":
            session.execute(text("DELETE FROM sqlite_sequence"))
        session.commit()
