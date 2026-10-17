"""Persistence helpers for manually resumable runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import RunPause


@dataclass(frozen=True)
class PauseKind:
    provider: str
    terminal_reason: str
    specialist_outcome: str


PAUSE_KINDS: dict[str, PauseKind] = {
    "quota": PauseKind(
        provider="openai_codex",
        terminal_reason="provider_quota",
        specialist_outcome="Specialist paused because the LLM allowance was exhausted.",
    ),
    "network": PauseKind(
        provider="llm",
        terminal_reason="provider_unreachable",
        specialist_outcome=(
            "Specialist paused because the LLM provider could not be reached."
        ),
    ),
    "budget": PauseKind(
        provider="llm",
        terminal_reason="budget_reached",
        specialist_outcome="Specialist paused because the run reached its LLM budget.",
    ),
}


def pause_kind(reason: str) -> PauseKind:
    return PAUSE_KINDS.get(reason, PAUSE_KINDS["quota"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def save_pause(
    run_kind: str,
    run_id: int,
    *,
    provider: str,
    message: str,
    reset_at: datetime | None = None,
    snapshot: dict[str, Any] | None = None,
    resume_stage: str | None = None,
    reason: str = "quota",
) -> RunPause:
    with Session(get_engine()) as session:
        row = session.exec(
            select(RunPause)
            .where(RunPause.run_kind == run_kind)
            .where(RunPause.run_id == run_id)
        ).first()
        if row is None:
            row = RunPause(run_kind=run_kind, run_id=run_id)
        row.provider = provider
        row.reason = reason
        row.message = message
        row.reset_at = reset_at
        row.snapshot_json = json.dumps(snapshot or {}, default=str)
        row.resume_stage = resume_stage
        row.paused_at = _utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_pause(run_kind: str, run_id: int) -> RunPause | None:
    with Session(get_engine()) as session:
        return session.exec(
            select(RunPause)
            .where(RunPause.run_kind == run_kind)
            .where(RunPause.run_id == run_id)
        ).first()


def clear_pause(run_kind: str, run_id: int) -> None:
    with Session(get_engine()) as session:
        row = session.exec(
            select(RunPause)
            .where(RunPause.run_kind == run_kind)
            .where(RunPause.run_id == run_id)
        ).first()
        if row is not None:
            session.delete(row)
            session.commit()


def pause_out(row: RunPause | None) -> dict[str, Any] | None:
    if row is None:
        return None
    try:
        snapshot = json.loads(row.snapshot_json or "{}")
    except (TypeError, ValueError):
        snapshot = {}
    return {
        "run_kind": row.run_kind,
        "run_id": row.run_id,
        "provider": row.provider,
        "reason": row.reason,
        "reset_at": row.reset_at,
        "message": row.message,
        "snapshot": snapshot,
        "resume_stage": row.resume_stage,
        "paused_at": row.paused_at,
    }
