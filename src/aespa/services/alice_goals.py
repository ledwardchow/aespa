"""Persistent lifecycle state for ALICE goal mode."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import AliceGoal

ACTIVE_STATUSES = {"active", "waiting_input"}
TERMINAL_STATUSES = {"completed", "blocked", "cleared", "failed"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def goal_out(goal: AliceGoal | None) -> dict[str, Any] | None:
    if goal is None:
        return None
    return {
        "id": goal.id,
        "run_kind": goal.run_kind,
        "run_id": goal.test_run_id,
        "tab_id": goal.session_key,
        "objective": goal.objective,
        "status": goal.status,
        "checkpoint": _json_object(goal.checkpoint_json),
        "completion": _json_object(goal.completion_json),
        "blocker": goal.blocker,
        "pause_reason": goal.pause_reason,
        "cycle_count": goal.cycle_count,
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        "paused_at": goal.paused_at.isoformat() if goal.paused_at else None,
        "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
    }


def get_goal(run_kind: str, run_id: int, tab_id: str | None = None) -> AliceGoal | None:
    with Session(get_engine()) as session:
        query = select(AliceGoal).where(
            AliceGoal.run_kind == run_kind,
            AliceGoal.test_run_id == run_id,
        )
        if tab_id is not None:
            query = query.where(AliceGoal.session_key == tab_id)
        return session.exec(query.order_by(AliceGoal.updated_at.desc())).first()


def create_goal(run_kind: str, run_id: int, tab_id: str, objective: str) -> AliceGoal:
    objective = objective.strip()
    if not objective:
        raise ValueError("A goal needs an objective.")
    with Session(get_engine()) as session:
        row = session.exec(
            select(AliceGoal).where(
                AliceGoal.run_kind == run_kind,
                AliceGoal.test_run_id == run_id,
                AliceGoal.session_key == tab_id,
            )
        ).first()
        now = _now()
        if row is None:
            row = AliceGoal(
                run_kind=run_kind,
                test_run_id=run_id,
                session_key=tab_id,
                objective=objective,
            )
        else:
            row.objective = objective
            row.status = "active"
            row.checkpoint_json = "{}"
            row.completion_json = "{}"
            row.blocker = ""
            row.pause_reason = ""
            row.cycle_count = 0
            row.paused_at = None
            row.completed_at = None
            row.updated_at = now
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def update_goal(
    goal_id: int,
    *,
    status: str | None = None,
    checkpoint: dict[str, Any] | None = None,
    completion: dict[str, Any] | None = None,
    blocker: str | None = None,
    pause_reason: str | None = None,
    increment_cycle: bool = False,
) -> AliceGoal | None:
    with Session(get_engine()) as session:
        row = session.get(AliceGoal, goal_id)
        if row is None:
            return None
        now = _now()
        if status is not None:
            row.status = status
            if status == "paused":
                row.paused_at = now
            elif status in TERMINAL_STATUSES:
                row.completed_at = now
        if checkpoint is not None:
            row.checkpoint_json = json.dumps(checkpoint, separators=(",", ":"), default=str)
        if completion is not None:
            row.completion_json = json.dumps(completion, separators=(",", ":"), default=str)
        if blocker is not None:
            row.blocker = blocker
        if pause_reason is not None:
            row.pause_reason = pause_reason
        if increment_cycle:
            row.cycle_count += 1
        row.updated_at = now
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def reconcile_interrupted_goals() -> int:
    """Pause goals that cannot still have a live task after process startup."""
    with Session(get_engine()) as session:
        rows = list(session.exec(select(AliceGoal).where(AliceGoal.status == "active")))
        now = _now()
        for row in rows:
            row.status = "paused"
            row.pause_reason = "AESPA restarted while this goal was running."
            row.paused_at = now
            row.updated_at = now
            session.add(row)
        session.commit()
        return len(rows)
