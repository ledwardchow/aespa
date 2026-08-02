from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from aespa.db import get_session
from aespa.services import statistics as statistics_service

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


@router.get("/llm")
def get_llm_statistics(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
) -> dict:
    return statistics_service.get_statistics(session, month)


@router.post("/llm/prices/refresh")
def refresh_llm_prices(session: Session = Depends(get_session)) -> dict:
    try:
        return statistics_service.refresh_prices(session)
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=502, detail=f"Price download failed: {exc}"
        ) from exc


@router.put("/llm/prices")
def update_llm_prices(
    payload: dict,
    session: Session = Depends(get_session),
) -> dict:
    try:
        return statistics_service.set_prices(session, payload)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/llm")
def reset_llm_statistics(session: Session = Depends(get_session)) -> dict[str, str]:
    statistics_service.reset_statistics(session)
    return {"status": "reset"}
