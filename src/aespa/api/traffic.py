"""Traffic log API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from aespa.db import get_session
from aespa.models import TestRun
from aespa.services import traffic as traffic_svc

router = APIRouter(tags=["traffic"])


@router.get("/api/test-runs/{run_id}/traffic")
def get_traffic(
    run_id: int,
    since_id: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[dict]:
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return traffic_svc.get_traffic(run_id, since_id)


@router.get("/api/test-runs/{run_id}/traffic/count")
def get_traffic_count(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return {"count": traffic_svc.count_traffic(run_id)}


@router.delete("/api/test-runs/{run_id}/traffic", status_code=204)
def clear_traffic(
    run_id: int,
    session: Session = Depends(get_session),
) -> None:
    if session.get(TestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    traffic_svc.clear_traffic(run_id)
