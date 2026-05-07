"""Logging API — LLM call log and other audit endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import LLMCallLog

router = APIRouter(tags=["logging"])

_RETENTION_DAYS = 7


def _prune(session: Session) -> None:
    """Delete records older than the retention window. Best-effort."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
        old = session.exec(
            select(LLMCallLog).where(LLMCallLog.created_at < cutoff)
        ).all()
        for row in old:
            session.delete(row)
        session.commit()
    except Exception:
        pass


@router.get("/api/logs/llm-calls")
def list_llm_calls(
    limit: int = Query(default=200, le=1000),
    run_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[dict]:
    _prune(session)
    stmt = select(LLMCallLog).order_by(LLMCallLog.created_at.desc()).limit(limit)  # type: ignore[arg-type]
    if run_id is not None:
        stmt = select(LLMCallLog).where(LLMCallLog.test_run_id == run_id).order_by(LLMCallLog.created_at.desc()).limit(limit)  # type: ignore[arg-type]
    rows = session.exec(stmt).all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "test_run_id": r.test_run_id,
            "provider": r.provider,
            "model": r.model,
            "call_type": r.call_type,
            "duration_ms": r.duration_ms,
            "prompt": r.prompt,
            "response": r.response,
            "error": r.error,
        }
        for r in rows
    ]
