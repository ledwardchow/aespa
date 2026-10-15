from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from aespa.extensions import ExtensionDataStore

from . import codex, usage
from .models import Reading

Window = Literal["five_hour", "weekly"]


def build_router(store: ExtensionDataStore) -> APIRouter:
    router = APIRouter(tags=["chatgpt-plan-usage"])

    @router.get("/summary")
    def get_summary(window: Window = Query("weekly")) -> dict:
        usage.sample(store)
        status = codex.status(store)
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

    @router.delete("/readings/{reading_id}", status_code=204)
    def delete_reading(reading_id: int) -> None:
        with store.session() as session:
            row = session.get(Reading, reading_id)
            if row is None:
                raise HTTPException(404, "Reading not found")
            session.delete(row)
            session.commit()

    return router
