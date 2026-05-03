"""Server-Sent Events endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from aespa.db import get_session
from aespa.models import TestRun
from aespa.services import events as events_svc

router = APIRouter(tags=["events"])


@router.get("/api/test-runs/{run_id}/events")
async def sse_stream(
    run_id: int,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return StreamingResponse(
        events_svc.stream(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
