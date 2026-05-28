from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from aespa.db import get_session
from aespa.services import reporting_debug as reporting_debug_svc
from aespa.services.settings import get_llm_config

router = APIRouter(prefix="/api/reporting-debug", tags=["reporting_debug"])


class ReportingPromptIn(BaseModel):
    prompt_text: str = Field(min_length=1)


class ReportingPromptVersionCreateIn(BaseModel):
    key: str = reporting_debug_svc.PROMPT_KEY_ANALYSE
    name: str = Field(min_length=1)
    prompt_text: str | None = Field(default=None, min_length=1)


class ReportingPromptVersionUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    prompt_text: str | None = Field(default=None, min_length=1)


class ReportingReplayIn(BaseModel):
    prompt_version_id: int | None = None


@router.get("/prompt")
def get_prompt(key: str = reporting_debug_svc.PROMPT_KEY_ANALYSE) -> dict:
    try:
        return reporting_debug_svc.get_prompt(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Reporting prompt not found") from None


@router.get("/prompts")
def list_prompts() -> dict:
    return {"prompts": reporting_debug_svc.list_prompts()}


@router.put("/prompt")
def save_prompt(
    payload: ReportingPromptIn,
    key: str = reporting_debug_svc.PROMPT_KEY_ANALYSE,
) -> dict:
    try:
        return reporting_debug_svc.save_prompt(payload.prompt_text, key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Reporting prompt not found") from None


@router.post("/prompt/reset")
def reset_prompt(key: str = reporting_debug_svc.PROMPT_KEY_ANALYSE) -> dict:
    try:
        return reporting_debug_svc.reset_prompt(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Reporting prompt not found") from None


@router.get("/prompt-versions")
def list_prompt_versions(key: str = reporting_debug_svc.PROMPT_KEY_ANALYSE) -> dict:
    try:
        return {"versions": reporting_debug_svc.list_prompt_versions(key)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Reporting prompt not found") from None


@router.post("/prompt-versions")
def create_prompt_version(payload: ReportingPromptVersionCreateIn) -> dict:
    try:
        return reporting_debug_svc.create_prompt_version(
            key=payload.key,
            name=payload.name,
            prompt_text=payload.prompt_text,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Reporting prompt not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=409, detail="Prompt version name already exists") from None
        raise


@router.put("/prompt-versions/{version_id}")
def update_prompt_version(
    version_id: int,
    payload: ReportingPromptVersionUpdateIn,
) -> dict:
    try:
        return reporting_debug_svc.update_prompt_version(
            version_id,
            name=payload.name,
            prompt_text=payload.prompt_text,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Prompt version not found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=409, detail="Prompt version name already exists") from None
        raise


@router.delete("/prompt-versions/{version_id}")
def delete_prompt_version(version_id: int) -> dict:
    try:
        reporting_debug_svc.delete_prompt_version(version_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Prompt version not found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return {"ok": True}


@router.get("/captures")
def list_captures(limit: int = 100) -> dict:
    return {
        "db_path": str(reporting_debug_svc.debug_db_path()),
        "captures": reporting_debug_svc.list_captures(limit=limit),
    }


@router.get("/captures/{capture_id}")
def get_capture(capture_id: int) -> dict:
    capture = reporting_debug_svc.get_capture(capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="Reporting capture not found")
    return capture


@router.post("/captures/{capture_id}/replay")
async def replay_capture(
    capture_id: int,
    payload: ReportingReplayIn | None = None,
    session: Session = Depends(get_session),
) -> dict:
    config = get_llm_config(session)
    if config is None:
        raise HTTPException(status_code=409, detail="No active LLM profile configured")
    try:
        replay = reporting_debug_svc.create_replay(
            capture_id,
            prompt_version_id=payload.prompt_version_id if payload else None,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Reporting capture or prompt version not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    asyncio.create_task(reporting_debug_svc.run_replay(int(replay["id"]), config))
    return replay


@router.get("/replays")
def list_replays(limit: int = 50) -> dict:
    return {"replays": reporting_debug_svc.list_replays(limit=limit)}


@router.get("/replays/{replay_id}")
def get_replay(replay_id: int) -> dict:
    replay = reporting_debug_svc.get_replay(replay_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Reporting replay not found")
    return replay
