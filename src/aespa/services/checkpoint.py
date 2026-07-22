"""Checkpoint service for dynamic scan resumption.

Provides upsert / load / clear helpers that persist the entire agentic-loop
state (LLM messages, action history, blocked-URL tracking, and loop counters)
to the ``scan_checkpoint`` table after every LLM turn.  A crashed or stopped
scan can be resumed by re-loading this state without loss of LLM context.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import ScanCheckpoint

log = logging.getLogger("aespa.checkpoint")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_checkpoint(
    run_id: int,
    *,
    messages: list[dict],
    history: list[dict],
    blocked_urls: set[str],
    failed_url_counts: dict[str, int],
    step_count: int,
    progressive_findings_count: int,
    consecutive_context_tools: int,
    completion_state: dict[str, Any] | None = None,
) -> None:
    """Upsert a checkpoint row for *run_id*.  Called after every LLM turn."""
    try:
        with Session(get_engine()) as s:
            existing = s.exec(
                select(ScanCheckpoint).where(ScanCheckpoint.test_run_id == run_id)
            ).first()

            now = _utcnow()
            if existing:
                existing.messages_json = json.dumps(messages, default=str)
                existing.history_json = json.dumps(history, default=str)
                existing.blocked_urls_json = json.dumps(list(blocked_urls), default=str)
                existing.failed_url_counts_json = json.dumps(
                    failed_url_counts, default=str
                )
                existing.step_count = step_count
                existing.progressive_findings_count = progressive_findings_count
                existing.consecutive_context_tools = consecutive_context_tools
                existing.completion_state_json = json.dumps(
                    completion_state or {}, default=str
                )
                existing.updated_at = now
                s.add(existing)
            else:
                row = ScanCheckpoint(
                    test_run_id=run_id,
                    messages_json=json.dumps(messages, default=str),
                    history_json=json.dumps(history, default=str),
                    blocked_urls_json=json.dumps(list(blocked_urls), default=str),
                    failed_url_counts_json=json.dumps(failed_url_counts, default=str),
                    step_count=step_count,
                    progressive_findings_count=progressive_findings_count,
                    consecutive_context_tools=consecutive_context_tools,
                    completion_state_json=json.dumps(
                        completion_state or {}, default=str
                    ),
                    created_at=now,
                    updated_at=now,
                )
                s.add(row)
            s.commit()
    except Exception:
        log.exception("checkpoint.save_checkpoint failed for run_id=%s", run_id)


def load_checkpoint(run_id: int) -> dict[str, Any] | None:
    """Return the persisted checkpoint for *run_id*, or *None* if none exists.

    The returned dict has the following keys:

    * ``messages``                 — list[dict]  (Anthropic multi-turn format)
    * ``history``                  — list[dict]  (action-trace records)
    * ``blocked_urls``             — set[str]
    * ``failed_url_counts``        — dict[str, int]
    * ``step_count``               — int
    * ``progressive_findings_count`` — int
    * ``consecutive_context_tools``  — int
    * ``completion_state``           — dict (bounded done/progress policy)
    * ``updated_at``               — datetime
    """
    try:
        with Session(get_engine()) as s:
            row = s.exec(
                select(ScanCheckpoint).where(ScanCheckpoint.test_run_id == run_id)
            ).first()
            if row is None:
                return None
            return {
                "messages": json.loads(row.messages_json or "[]"),
                "history": json.loads(row.history_json or "[]"),
                "blocked_urls": set(json.loads(row.blocked_urls_json or "[]")),
                "failed_url_counts": json.loads(row.failed_url_counts_json or "{}"),
                "step_count": row.step_count,
                "progressive_findings_count": row.progressive_findings_count,
                "consecutive_context_tools": row.consecutive_context_tools,
                "completion_state": json.loads(row.completion_state_json or "{}"),
                "updated_at": row.updated_at,
            }
    except Exception:
        log.exception("checkpoint.load_checkpoint failed for run_id=%s", run_id)
        return None


def clear_checkpoint(run_id: int) -> None:
    """Delete the checkpoint row for *run_id* if it exists."""
    try:
        with Session(get_engine()) as s:
            row = s.exec(
                select(ScanCheckpoint).where(ScanCheckpoint.test_run_id == run_id)
            ).first()
            if row is not None:
                s.delete(row)
                s.commit()
    except Exception:
        log.exception("checkpoint.clear_checkpoint failed for run_id=%s", run_id)


def checkpoint_status(run_id: int) -> dict[str, Any]:
    """Return a lightweight status dict suitable for the API response schema."""
    try:
        with Session(get_engine()) as s:
            row = s.exec(
                select(ScanCheckpoint).where(ScanCheckpoint.test_run_id == run_id)
            ).first()
            if row is None:
                return {"exists": False, "step_count": None, "updated_at": None}
            return {
                "exists": True,
                "step_count": row.step_count,
                "updated_at": row.updated_at,
            }
    except Exception:
        log.exception("checkpoint.checkpoint_status failed for run_id=%s", run_id)
        return {"exists": False, "step_count": None, "updated_at": None}


def save_phase_checkpoint(
    run_id: int,
    phase: str,
    idempotency_key: str,
    data: dict[str, Any] | None = None,
    run_kind: str = "web",
) -> None:
    """Save a granular phase checkpoint for resume idempotence."""
    from aespa.models import PhaseCheckpoint

    try:
        with Session(get_engine()) as s:
            existing = s.exec(
                select(PhaseCheckpoint)
                .where(PhaseCheckpoint.run_kind == run_kind)
                .where(PhaseCheckpoint.run_id == run_id)
                .where(PhaseCheckpoint.phase == phase)
                .where(PhaseCheckpoint.idempotency_key == idempotency_key)
            ).first()
            now = _utcnow()
            if existing:
                existing.data_json = json.dumps(data or {})
                existing.completed_at = now
                s.add(existing)
            else:
                row = PhaseCheckpoint(
                    run_kind=run_kind,
                    run_id=run_id,
                    phase=phase,
                    idempotency_key=idempotency_key,
                    data_json=json.dumps(data or {}),
                    completed_at=now,
                )
                s.add(row)
            s.commit()
    except Exception:
        log.exception(
            "save_phase_checkpoint failed for run_id=%s phase=%s key=%s",
            run_id,
            phase,
            idempotency_key,
        )


def has_phase_checkpoint(
    run_id: int,
    phase: str,
    idempotency_key: str,
    run_kind: str = "web",
) -> bool:
    """Return True if a granular phase checkpoint exists."""
    from aespa.models import PhaseCheckpoint

    try:
        with Session(get_engine()) as s:
            row = s.exec(
                select(PhaseCheckpoint)
                .where(PhaseCheckpoint.run_kind == run_kind)
                .where(PhaseCheckpoint.run_id == run_id)
                .where(PhaseCheckpoint.phase == phase)
                .where(PhaseCheckpoint.idempotency_key == idempotency_key)
            ).first()
            return row is not None
    except Exception:
        log.exception(
            "has_phase_checkpoint failed for run_id=%s phase=%s key=%s",
            run_id,
            phase,
            idempotency_key,
        )
        return False
