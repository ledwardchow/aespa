"""A.L.I.C.E. chat API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from aespa.db import get_session
from aespa.models import TestRun
from aespa.services import alice as alice_svc

router = APIRouter(tags=["alice"])


class AliceChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/api/test-runs/{run_id}/alice/chat")
async def alice_chat(
    run_id: int,
    req: AliceChatRequest,
    session: Session = Depends(get_session),
) -> dict:
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    return await alice_svc.run_alice_turn(run_id, req.message, req.history)
