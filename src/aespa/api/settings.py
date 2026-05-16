from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from aespa.db import get_session
from aespa.schemas import (
    BurpRestApiConfigIn,
    BurpRestApiConfigOut,
    LLMConfigIn,
    LLMConfigOut,
    PROVIDER_DEFAULT_MODELS,
    ScannerPolicyIn,
    ScannerPolicyOut,
    UpstreamProxyConfigIn,
    UpstreamProxyConfigOut,
)
from aespa.services import settings as settings_service
from aespa.services import burp_rest as burp_rest_svc


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


@router.get("/llm/profiles", response_model=list[LLMConfigOut])
def list_llm_profiles(session: Session = Depends(get_session)) -> list[LLMConfigOut]:
    return [LLMConfigOut.model_validate(cfg) for cfg in settings_service.list_llm_profiles(session)]


@router.post("/llm/profiles", response_model=LLMConfigOut)
def create_llm_profile(
    payload: LLMConfigIn,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.create_llm_profile(session, payload)
    return LLMConfigOut.model_validate(cfg)


@router.put("/llm/profiles/{profile_id}", response_model=LLMConfigOut)
def update_llm_profile(
    profile_id: int,
    payload: LLMConfigIn,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.update_llm_profile(session, profile_id, payload)
    return LLMConfigOut.model_validate(cfg)


@router.post("/llm/profiles/{profile_id}/activate", response_model=LLMConfigOut)
def activate_llm_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.activate_llm_profile(session, profile_id)
    return LLMConfigOut.model_validate(cfg)


@router.delete("/llm/profiles/{profile_id}", status_code=204)
def delete_llm_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> Response:
    settings_service.delete_llm_profile(session, profile_id)
    return Response(status_code=204)


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


@router.get("/burp-rest-api", response_model=BurpRestApiConfigOut)
def get_burp_rest_api_config(session: Session = Depends(get_session)) -> BurpRestApiConfigOut:
    return settings_service.get_burp_rest_api_config(session)


@router.put("/burp-rest-api", response_model=BurpRestApiConfigOut)
def upsert_burp_rest_api_config(
    payload: BurpRestApiConfigIn,
    session: Session = Depends(get_session),
) -> BurpRestApiConfigOut:
    return settings_service.upsert_burp_rest_api_config(session, payload)


@router.post("/burp-rest-api/test-connection")
async def test_burp_rest_api_connection(
    session: Session = Depends(get_session),
) -> dict:
    cfg = settings_service.get_burp_rest_api_config(session)
    ok, message = await burp_rest_svc.test_connection(cfg)
    return {"ok": ok, "message": message}


@router.get("/upstream-proxy", response_model=UpstreamProxyConfigOut)
def get_upstream_proxy_config(session: Session = Depends(get_session)) -> UpstreamProxyConfigOut:
    return settings_service.get_upstream_proxy_config(session)


@router.put("/upstream-proxy", response_model=UpstreamProxyConfigOut)
def upsert_upstream_proxy_config(
    payload: UpstreamProxyConfigIn,
    session: Session = Depends(get_session),
) -> UpstreamProxyConfigOut:
    return settings_service.upsert_upstream_proxy_config(session, payload)
