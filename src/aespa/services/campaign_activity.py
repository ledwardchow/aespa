"""Stored campaign activity and reconnect cursors."""

from __future__ import annotations

import re

from sqlmodel import Session, select

from aespa.models import (
    AgentLog,
    ScanLog,
)
from aespa.schemas import (
    CampaignActivityEntry,
)

_ACTIVITY_CURSOR_RE = re.compile(r"^(\d+)\.(\d+)$")


def _parse_activity_cursor(cursor: str | None) -> tuple[int, int]:
    """Parse an ``event_id``/cursor of the form ``"<agent_id>.<scan_id>"``.

    A missing, empty, or malformed cursor resumes from the very beginning
    (``0, 0``) rather than raising — a stale or garbled ``Last-Event-ID``
    must never wedge a reconnecting client.
    """
    if not cursor:
        return (0, 0)
    match = _ACTIVITY_CURSOR_RE.match(cursor.strip())
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2)))


def _load_campaign_activity_entries(
    session: Session,
    campaign_id: int,
    after_agent_id: int = 0,
    after_scan_id: int = 0,
) -> tuple[list[CampaignActivityEntry], int, int]:
    """Load every persisted campaign activity row strictly after the given
    watermarks, in stable chronological order, and return the new watermarks.

    AgentLog and ScanLog each have their own independent id sequence, so
    "after cursor" is tracked as one watermark per table; ties in
    ``created_at`` are broken by table then id so the merge order never
    depends on incidental query/dict ordering.
    """
    agent_rows = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == campaign_id)
        .where(AgentLog.run_kind == "campaign")
        .where(AgentLog.id > after_agent_id)
    ).all()
    scan_rows = session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == campaign_id)
        .where(ScanLog.run_kind == "campaign")
        .where(ScanLog.id > after_scan_id)
    ).all()

    combined: list[tuple[object, int, str, int]] = [
        (e.created_at, 0, "agent", e.id) for e in agent_rows
    ] + [(e.created_at, 1, "scan", e.id) for e in scan_rows]
    combined.sort(key=lambda row: (row[0], row[1], row[3]))
    by_id = {("agent", e.id): e for e in agent_rows}
    by_id.update({("scan", e.id): e for e in scan_rows})

    entries: list[CampaignActivityEntry] = []
    max_agent, max_scan = after_agent_id, after_scan_id
    for _created_at, _order, kind, row_id in combined:
        row = by_id[(kind, row_id)]
        if kind == "agent":
            max_agent = max(max_agent, row_id)
            entries.append(
                CampaignActivityEntry(
                    event_id=f"{max_agent}.{max_scan}",
                    timestamp=row.created_at,
                    type="agent_status",
                    status=row.status,
                    role=row.role,
                    task=row.current_task,
                    outcome=row.outcome,
                )
            )
        else:
            max_scan = max(max_scan, row_id)
            entries.append(
                CampaignActivityEntry(
                    event_id=f"{max_agent}.{max_scan}",
                    timestamp=row.created_at,
                    type="scanner_phase",
                    status=row.status,
                    phase=row.phase,
                    message=row.message,
                )
            )
    return entries, max_agent, max_scan
