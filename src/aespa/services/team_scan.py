"""Sequential Test Lead ensemble for the experimental Team web scan mode."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import PhaseCheckpoint, ScanFinding, TestRun
from aespa.services import checkpoint as checkpoint_svc
from aespa.services import events as events_svc

_UTC = timezone.utc
_PHASE = "team_scan_member"

TEAM_ASSIGNMENTS = (
    {
        "key": "primary",
        "label": "Primary Tester",
        "run_preflight": True,
        "final": False,
        "mission": (
            "Run the normal broad Standard pentest. Build an application-wide view, "
            "test the most promising routes and workflows, investigate imported leads, "
            "and dispatch specialists when a focused lead needs confirmation."
        ),
    },
    {
        "key": "independent",
        "label": "Pair Tester",
        "run_preflight": False,
        "final": False,
        "mission": (
            "Perform an independent second look. Use a different route and test order "
            "from a typical broad scan. Start with less-tested routes, identity boundaries, "
            "complete workflows, and server-side inputs. Existing coverage means a probe "
            "ran, not that the area is exhausted. Retest high-risk authorization, injection, "
            "authentication, and business-logic assumptions when you have a distinct method. "
            "Do not repeat an existing confirmed finding."
        ),
    },
    {
        "key": "closer",
        "label": "QA Tester",
        "run_preflight": False,
        "final": True,
        "mission": (
            "Close the Team scan. Call coverage_gaps first and exercise the most important "
            "remaining route, category, input-class, and identity checks. Review traffic, "
            "sessions, object identifiers, response differences, findings, and unresolved "
            "leads from the earlier members. Spend follow-up probes on cross-route attack "
            "chains and strong unexplained signals. Do not recreate confirmed findings."
        ),
    },
)


def reset_team_progress(run_id: int) -> None:
    """Remove saved Team-member completion markers for a fresh scan."""
    with Session(get_engine()) as session:
        rows = session.exec(
            select(PhaseCheckpoint)
            .where(PhaseCheckpoint.run_kind == "web")
            .where(PhaseCheckpoint.run_id == run_id)
            .where(PhaseCheckpoint.phase == _PHASE)
        ).all()
        for row in rows:
            session.delete(row)
        session.commit()


def _completed_members(run_id: int) -> set[str]:
    with Session(get_engine()) as session:
        return {
            row.idempotency_key
            for row in session.exec(
                select(PhaseCheckpoint)
                .where(PhaseCheckpoint.run_kind == "web")
                .where(PhaseCheckpoint.run_id == run_id)
                .where(PhaseCheckpoint.phase == _PHASE)
            ).all()
        }


def _set_run_active(run_id: int) -> None:
    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        run.status = "running"
        run.phase = "scanning"
        run.outcome = None
        run.terminal_reason = None
        run.completed_at = None
        session.add(run)
        session.commit()


def _save_member_complete(run_id: int, assignment: dict) -> None:
    checkpoint_svc.save_phase_checkpoint(
        run_id,
        _PHASE,
        assignment["key"],
        {
            "label": assignment["label"],
            "completed_at": datetime.now(_UTC).isoformat(),
        },
        run_kind="web",
    )


def _finding_count(run_id: int) -> int:
    with Session(get_engine()) as session:
        return len(
            session.exec(
                select(ScanFinding).where(ScanFinding.test_run_id == run_id)
            ).all()
        )


async def run_team_scan(run_id: int) -> None:
    """Run fresh Standard Test Lead conversations as one resumable Team scan."""
    from aespa.services import scanner as scanner_svc

    completed = _completed_members(run_id)
    events_svc.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Co-ordinator",
            "status": "active",
            "current_task": "Co-ordinating Team scan",
            "outcome": None,
            "_persist": True,
        },
    )
    for index, assignment in enumerate(TEAM_ASSIGNMENTS, start=1):
        if assignment["key"] in completed:
            continue
        _set_run_active(run_id)
        events_svc.emit(
            run_id,
            {
                "type": "scanner_phase",
                "phase": "team_member",
                "status": "start",
                "message": (
                    f"Starting Team member {index}/{len(TEAM_ASSIGNMENTS)}: "
                    f"{assignment['label']}."
                ),
                "data": {
                    "member": assignment["key"],
                    "member_index": index,
                    "member_total": len(TEAM_ASSIGNMENTS),
                },
            },
        )
        events_svc.emit(
            run_id,
            {
                "type": "agent_status",
                "agent_id": "scanner",
                "role": "Test Co-ordinator",
                "status": "active",
                "current_task": (
                    f"Co-ordinating {assignment['label']}: {assignment['mission']}"
                ),
                "outcome": None,
                "_persist": True,
            },
        )
        events_svc.emit(
            run_id,
            {
                "type": "agent_status",
                "agent_id": f"team-{assignment['key']}",
                "role": assignment["label"],
                "status": "active",
                "current_task": "Starting assigned test pass",
                "outcome": None,
                "_persist": True,
            },
        )
        try:
            await scanner_svc._do_thinking_scan(
                run_id,
                effective_coverage_mode="standard",
                team_assignment=assignment,
            )
        except asyncio.CancelledError:
            events_svc.emit(
                run_id,
                {
                    "type": "agent_status",
                    "agent_id": f"team-{assignment['key']}",
                    "role": assignment["label"],
                    "status": "complete",
                    "current_task": "Team scan stopped",
                    "outcome": "Stopped before this Team member completed",
                    "_persist": True,
                },
            )
            raise
        _save_member_complete(run_id, assignment)
        checkpoint_svc.clear_checkpoint(run_id)
        count = _finding_count(run_id)
        events_svc.emit(
            run_id,
            {
                "type": "agent_status",
                "agent_id": f"team-{assignment['key']}",
                "role": assignment["label"],
                "status": "complete",
                "current_task": "Team member complete",
                "outcome": f"Finished with {count} total finding(s) recorded so far",
                "_persist": True,
            },
        )
        events_svc.emit(
            run_id,
            {
                "type": "scanner_phase",
                "phase": "team_member",
                "status": "complete",
                "message": f"{assignment['label']} completed.",
                "data": {
                    "member": assignment["key"],
                    "member_index": index,
                    "member_total": len(TEAM_ASSIGNMENTS),
                    "finding_count": count,
                },
            },
        )
