"""Slice 5: /api/api-test-runs/{id}/* — standalone + alias routes for ApiTestRun.

The ``ApiTestRun`` uses the same integer id space as ``TestRun``.
Alice, events, and agent-log endpoints already key on ``test_run_id`` in
``AliceChatSession``, ``AgentLog``, etc.  We add thin alias routes here so the
frontend can call the same alice/events/agent-log URLs against an ApiTestRun id
without any changes to the underlying services.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import (
    AgentLog,
    AliceChatMessage,
    AliceChatSession,
    ApiTestRun,
    ScanFinding,
    TrafficEntry,
)
from aespa.schemas import ApiTestRunSummary, ScanFindingOut
from aespa.services import alice_tasks

_UTC = timezone.utc

router = APIRouter(prefix="/api/api-test-runs", tags=["api-test-runs"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_run_or_404(session: Session, run_id: int) -> ApiTestRun:
    run = session.get(ApiTestRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API test run not found")
    return run


def _to_summary(run: ApiTestRun) -> ApiTestRunSummary:
    return ApiTestRunSummary.model_validate(run)


# ── Single run ─────────────────────────────────────────────────────────────────

@router.get("/{run_id}", response_model=ApiTestRunSummary)
def get_api_test_run(
    run_id: int, session: Session = Depends(get_session)
) -> ApiTestRunSummary:
    return _to_summary(_get_run_or_404(session, run_id))


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_test_run(run_id: int, session: Session = Depends(get_session)) -> None:
    run = _get_run_or_404(session, run_id)
    for sess in session.exec(select(AliceChatSession).where(AliceChatSession.test_run_id == run_id)).all():
        for msg in session.exec(select(AliceChatMessage).where(AliceChatMessage.session_id == sess.id)).all():
            session.delete(msg)
        session.delete(sess)
    for log in session.exec(select(AgentLog).where(AgentLog.test_run_id == run_id)).all():
        session.delete(log)
    session.delete(run)
    session.commit()


# ── Alice helper: build sessions payload from DB ──────────────────────────────

def _load_api_sessions(run_id: int, run: ApiTestRun, session: Session) -> dict:
    run_token = run.created_at.isoformat() if run.created_at else None

    sess_rows = session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .order_by(AliceChatSession.position, AliceChatSession.id)
    ).all()

    chats = []
    for s in sess_rows:
        msg_rows = session.exec(
            select(AliceChatMessage)
            .where(AliceChatMessage.session_id == s.id)
            .order_by(AliceChatMessage.position, AliceChatMessage.id)
        ).all()
        chats.append({
            "id": s.session_key,
            "title": s.title,
            "messages": [
                {"id": m.message_key, "sender": m.sender,
                 "type": m.type, "text": m.text, "ts": m.ts}
                for m in msg_rows
            ],
        })

    active = next((s for s in sess_rows if s.is_active), sess_rows[0] if sess_rows else None)
    latest_updated = max((s.updated_at for s in sess_rows), default=None)
    return {
        "chats": chats,
        "active_tab_id": active.session_key if active else "tab-default",
        "updated_at": latest_updated.isoformat() if latest_updated else None,
        "run_created_at": run_token,
    }


class AliceSessionsRequest(BaseModel):
    chats: list[dict]
    active_tab_id: str = "tab-default"


class AliceRunRequest(BaseModel):
    message: str
    history: list[dict] = []
    tab_id: str = "tab-default"
    think_msg_id: str
    reply_msg_id: str


def _save_api_sessions(run_id: int, req: AliceSessionsRequest, session: Session) -> None:
    from aespa.api.alice import AliceSessionsRequest as _AReq, _save_sessions
    # Delegate to the canonical implementation — same DB tables, same logic.
    _save_sessions(run_id, req, session)  # type: ignore[arg-type]


# ── Alice alias routes ─────────────────────────────────────────────────────────

@router.get("/{run_id}/alice/sessions")
def get_alice_sessions(run_id: int, session: Session = Depends(get_session)) -> dict:
    run = _get_run_or_404(session, run_id)
    return _load_api_sessions(run_id, run, session)


@router.put("/{run_id}/alice/sessions")
def save_alice_sessions(
    run_id: int, req: AliceSessionsRequest, session: Session = Depends(get_session)
) -> dict:
    _get_run_or_404(session, run_id)
    _save_api_sessions(run_id, req, session)
    return {"ok": True}


@router.post("/{run_id}/alice/run")
async def start_alice_run(
    run_id: int, req: AliceRunRequest, session: Session = Depends(get_session)
) -> dict:
    _get_run_or_404(session, run_id)
    await alice_tasks.start(
        run_id,
        tab_id=req.tab_id,
        think_msg_id=req.think_msg_id,
        reply_msg_id=req.reply_msg_id,
        message=req.message,
        history=req.history,
        run_type="api",
    )
    return {"ok": True}


@router.get("/{run_id}/alice/stream")
async def alice_stream(
    run_id: int,
    cursor: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    _get_run_or_404(session, run_id)
    return StreamingResponse(
        alice_tasks.stream_events(run_id, cursor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.delete("/{run_id}/alice/run")
async def stop_alice_run(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    stopped = await alice_tasks.stop(run_id)
    return {"ok": True, "stopped": stopped}


@router.get("/{run_id}/alice/status")
def alice_status(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    return alice_tasks.status(run_id)


# ── Events alias ───────────────────────────────────────────────────────────────

@router.get("/{run_id}/events")
def stream_events(run_id: int, session: Session = Depends(get_session)) -> StreamingResponse:
    _get_run_or_404(session, run_id)
    from aespa.services import events as events_svc
    return StreamingResponse(
        events_svc.stream(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ── Agent log alias ────────────────────────────────────────────────────────────

@router.get("/{run_id}/agent-log")
def get_agent_log(run_id: int, session: Session = Depends(get_session)) -> list:
    _get_run_or_404(session, run_id)
    rows = session.exec(
        select(AgentLog).where(AgentLog.test_run_id == run_id).order_by(AgentLog.id)
    ).all()
    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "role": r.role,
            "status": r.status,
            "current_task": r.current_task,
            "outcome": r.outcome,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ── Scan start / stop ──────────────────────────────────────────────────────────

@router.post("/{run_id}/scan/start")
async def start_api_scan(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import api_scanner
    await api_scanner.start_api_scan(run_id)
    return {"ok": True}


@router.post("/{run_id}/scan/stop")
async def stop_api_scan(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import api_scanner
    stopped = await api_scanner.stop_api_scan(run_id)
    return {"ok": True, "stopped": stopped}


@router.get("/{run_id}/scan/status")
def api_scan_status(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import api_scanner
    return api_scanner.get_scan_status(run_id)


# ── Findings alias ─────────────────────────────────────────────────────────────

@router.get("/{run_id}/findings", response_model=list[ScanFindingOut])
def get_api_findings(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[ScanFindingOut]:
    _get_run_or_404(session, run_id)
    findings = session.exec(
        select(ScanFinding).where(ScanFinding.api_test_run_id == run_id)
    ).all()
    _order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings = sorted(findings, key=lambda f: _order.get(f.severity, 5))
    return [ScanFindingOut.model_validate(f) for f in findings]


# ── Traffic alias ──────────────────────────────────────────────────────────────

@router.get("/{run_id}/traffic")
def get_api_traffic(
    run_id: int,
    since_id: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[dict]:
    _get_run_or_404(session, run_id)
    from aespa.services import traffic as traffic_svc
    return traffic_svc.get_traffic(0, since_id, api_run_id=run_id)


@router.get("/{run_id}/traffic/count")
def get_api_traffic_count(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    _get_run_or_404(session, run_id)
    from aespa.services import traffic as traffic_svc
    return {"count": traffic_svc.count_traffic(0, api_run_id=run_id)}
