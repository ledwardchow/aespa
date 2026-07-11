"""A.L.I.C.E. chat API."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import AliceChatMessage, AliceChatSession, TestRun
from aespa.services import alice_tasks

router = APIRouter(tags=["alice"])

_UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(_UTC)


# ── Request shapes ────────────────────────────────────────────────────────────

class AliceRunRequest(BaseModel):
    message: str
    history: list[dict] = []
    tab_id: str = "tab-default"
    think_msg_id: str
    reply_msg_id: str


class AliceSessionsRequest(BaseModel):
    chats: list[dict]
    active_tab_id: str = "tab-default"


# ── Chat session persistence helpers ──────────────────────────────────────────

def _load_sessions(run_id: int, session: Session, run_kind: str = "web") -> dict:
    run = session.get(TestRun, run_id)
    # Stable per-run identity. SQLite reuses INTEGER PRIMARY KEY ids after the
    # highest run is deleted, so a new run can inherit a deleted run's id. The
    # client uses this token to detect that case and discard stale localStorage
    # belonging to the deleted run (otherwise it would show another run's chat).
    run_token = run.created_at.isoformat() if run and run.created_at else None

    sess_rows = session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .where(AliceChatSession.run_kind == run_kind)
        .order_by(AliceChatSession.position, AliceChatSession.id)
    ).all()

    chats = []
    for s in sess_rows:
        msg_rows = session.exec(
            select(AliceChatMessage)
            .where(AliceChatMessage.session_id == s.id)
            .order_by(AliceChatMessage.position, AliceChatMessage.id)
        ).all()
        def _safe_step_data(raw: str) -> dict:
            try:
                parsed = json.loads(raw or "{}")
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}

        chats.append({
            "id": s.session_key,
            "title": s.title,
            "messages": [
                {"id": m.message_key, "sender": m.sender,
                 "type": m.type, "text": m.text, "ts": m.ts,
                 "stepData": _safe_step_data(m.step_data_json)}
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


def _save_sessions(run_id: int, req: AliceSessionsRequest, session: Session, run_kind: str = "web") -> None:
    incoming_keys = {chat["id"] for chat in req.chats}
    now = _now()

    existing_sess = session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .where(AliceChatSession.run_kind == run_kind)
    ).all()
    by_key: dict[str, AliceChatSession] = {s.session_key: s for s in existing_sess}

    for s in existing_sess:
        if s.session_key not in incoming_keys:
            for m in session.exec(
                select(AliceChatMessage).where(AliceChatMessage.session_id == s.id)
            ).all():
                session.delete(m)
            session.delete(s)

    for pos, chat in enumerate(req.chats):
        key = chat["id"]
        is_active = key == req.active_tab_id

        if key in by_key:
            sess_row = by_key[key]
            sess_row.title = chat.get("title", sess_row.title)
            sess_row.position = pos
            sess_row.is_active = is_active
            sess_row.updated_at = now
        else:
            sess_row = AliceChatSession(
                test_run_id=run_id,
                run_kind=run_kind,
                session_key=key,
                title=chat.get("title", "Session"),
                position=pos,
                is_active=is_active,
            )
            session.add(sess_row)

        session.flush()

        incoming_msgs = chat.get("messages", [])
        incoming_msg_keys = {m["id"] for m in incoming_msgs}

        existing_msgs = session.exec(
            select(AliceChatMessage).where(AliceChatMessage.session_id == sess_row.id)
        ).all()
        msgs_by_key: dict[str, AliceChatMessage] = {m.message_key: m for m in existing_msgs}

        for m in existing_msgs:
            if m.message_key not in incoming_msg_keys:
                session.delete(m)

        for msg_pos, msg in enumerate(incoming_msgs):
            msg_key = msg["id"]
            if msg_key in msgs_by_key:
                row = msgs_by_key[msg_key]
                row.text = msg.get("text", row.text)
                row.step_data_json = json.dumps(msg.get("stepData") or {}, separators=(",", ":"), default=str)
                row.position = msg_pos
                row.updated_at = now
            else:
                session.add(AliceChatMessage(
                    session_id=sess_row.id,
                    message_key=msg_key,
                    sender=msg.get("sender", "alice"),
                    type=msg.get("type", "message"),
                    text=msg.get("text", ""),
                    step_data_json=json.dumps(msg.get("stepData") or {}, separators=(",", ":"), default=str),
                    ts=msg.get("ts", ""),
                    position=msg_pos,
                ))

    session.commit()


# ── Session persistence endpoints ─────────────────────────────────────────────

@router.get("/api/test-runs/{run_id}/alice/sessions")
def get_alice_sessions(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return _load_sessions(run_id, session)


@router.put("/api/test-runs/{run_id}/alice/sessions")
def save_alice_sessions(
    run_id: int,
    req: AliceSessionsRequest,
    session: Session = Depends(get_session),
) -> dict:
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    _save_sessions(run_id, req, session)
    return {"ok": True}


# ── Background task endpoints ─────────────────────────────────────────────────

@router.post("/api/test-runs/{run_id}/alice/run")
async def start_alice_run(
    run_id: int,
    req: AliceRunRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Start a background ALICE task (survives client disconnections)."""
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    await alice_tasks.start(
        run_id,
        tab_id=req.tab_id,
        think_msg_id=req.think_msg_id,
        reply_msg_id=req.reply_msg_id,
        message=req.message,
        history=req.history,
    )
    return {"ok": True}


@router.get("/api/test-runs/{run_id}/alice/stream")
async def alice_stream(
    run_id: int,
    cursor: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """SSE stream: replays buffered events from *cursor*, then live events."""
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return StreamingResponse(
        alice_tasks.stream_events(run_id, cursor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.delete("/api/test-runs/{run_id}/alice/run")
async def stop_alice_run(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Cancel the running ALICE task for this run."""
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    stopped = await alice_tasks.stop(run_id)
    return {"ok": True, "stopped": stopped}


@router.get("/api/test-runs/{run_id}/alice/status")
def alice_status(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Return whether an ALICE task is currently running for this run."""
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return alice_tasks.status(run_id)
