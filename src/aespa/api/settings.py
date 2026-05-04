from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from aespa.db import get_session
from aespa.schemas import LLMConfigIn, LLMConfigOut, PROVIDER_DEFAULT_MODELS, ScannerPolicyIn, ScannerPolicyOut
from aespa.services import settings as settings_service


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/llm", response_model=LLMConfigOut | None)
def get_llm_config(session: Session = Depends(get_session)) -> LLMConfigOut | None:
    cfg = settings_service.get_llm_config(session)
    if cfg is None:
        return None
    return LLMConfigOut.model_validate(cfg)


@router.put("/llm", response_model=LLMConfigOut)
def upsert_llm_config(
    payload: LLMConfigIn,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.upsert_llm_config(session, payload)
    return LLMConfigOut.model_validate(cfg)


@router.get("/llm/models")
def default_models() -> dict[str, list[str]]:
    """Return well-known model names for each provider (for UI dropdowns)."""
    return PROVIDER_DEFAULT_MODELS


@router.get("/scanner-policy", response_model=ScannerPolicyOut)
def get_scanner_policy(session: Session = Depends(get_session)) -> ScannerPolicyOut:
    return settings_service.get_scanner_policy(session)


@router.put("/scanner-policy", response_model=ScannerPolicyOut)
def upsert_scanner_policy(
    payload: ScannerPolicyIn,
    session: Session = Depends(get_session),
) -> ScannerPolicyOut:
    return settings_service.upsert_scanner_policy(session, payload)
