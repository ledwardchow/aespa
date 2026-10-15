from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aespa.extensions import ExtensionDataStore

from . import codex, usage
from .models import Reading, now

Window = Literal["five_hour", "weekly"]


class ReadingIn(BaseModel):
    window: Window
    used_percent: float = Field(ge=0, le=100)
    observed_at: datetime | None = None
    resets_at: datetime | None = None
    note: str = Field(default="", max_length=500)


def build_router(store: ExtensionDataStore) -> APIRouter:
    router = APIRouter(tags=["chatgpt-plan-usage"])

    @router.get("/summary")
    def get_summary(window: Window = Query("five_hour")) -> dict:
        usage.sample(store)
        status = codex.status(store)
        # ChatGPT plan usage on another account does not move these readings.
        providers = (
            (usage.CODEX,)
            if status and status.get("same_account") is False
            else usage.PROVIDERS
        )
        return usage.summary(store, window, providers=providers) | {"codex": status}

    @router.post("/sample")
    def take_sample() -> dict:
        return {"added": usage.sample(store)}

    @router.post("/codex/check")
    def check_codex() -> dict:
        return codex.poll(store)

    @router.post("/readings", status_code=201)
    def add_reading(payload: ReadingIn) -> dict:
        # Count usage up to this moment before saving the reading.
        usage.sample(store)
        at = now()
        observed_at = usage.utc(payload.observed_at) or at
        if observed_at > at:
            raise HTTPException(422, "The reading time cannot be in the future")
        resets_at = usage.utc(payload.resets_at)
        length = usage.WINDOWS[payload.window]
        if resets_at is not None and not (
            observed_at <= resets_at <= observed_at + length + usage.RESET_TOLERANCE
        ):
            raise HTTPException(
                422,
                "The reset time must be after the reading and within one "
                + ("5-hour" if payload.window == "five_hour" else "weekly")
                + " window",
            )
        row = Reading(
            window=payload.window,
            used_percent=payload.used_percent,
            observed_at=observed_at,
            resets_at=resets_at,
            note=payload.note.strip(),
        )
        with store.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return usage.reading_out(row)

    @router.delete("/readings/{reading_id}", status_code=204)
    def delete_reading(reading_id: int) -> None:
        with store.session() as session:
            row = session.get(Reading, reading_id)
            if row is None:
                raise HTTPException(404, "Reading not found")
            session.delete(row)
            session.commit()

    return router
