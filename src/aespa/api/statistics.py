from __future__ import annotations

from datetime import date as calendar_date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from aespa.db import get_session
from aespa.services import statistics as statistics_service

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


@router.get("/llm")
def get_llm_statistics(
    view: Literal["all_time", "monthly", "weekly", "daily", "custom"] = "monthly",
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    date: calendar_date | None = None,
    start: calendar_date | None = None,
    end: calendar_date | None = None,
    session: Session = Depends(get_session),
) -> dict:
    try:
        if month is not None:
            calendar_date.fromisoformat(f"{month}-01")
            if view != "monthly":
                raise ValueError("month is only valid for the monthly view")
        return statistics_service.get_statistics_view(
            session, view=view, month=month, anchor=date, start=start, end=end
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
