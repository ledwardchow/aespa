from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from aespa.db import get_session
from aespa.schemas import (
    PROVIDER_DEFAULT_MODELS,
    BurpRestApiConfigIn,
    BurpRestApiConfigOut,
    GlobalHttpHeaderConfigIn,
    GlobalHttpHeaderConfigOut,
    LLMConfigExport,
    LLMConfigIn,
    LLMConfigOut,
    LLMImportResult,
    LLMProviderConfigIn,
    LLMProviderConfigOut,
    ReportingDebugConfigIn,
    ReportingDebugConfigOut,
    ScannerPolicyIn,
    ScannerPolicyOut,
    SpecialistAgentConfigIn,
    SpecialistAgentConfigOut,
    UpstreamProxyConfigIn,
    UpstreamProxyConfigOut,
    ValidatorConfigIn,
    ValidatorConfigOut,
)
from aespa.services import burp_rest as burp_rest_svc
from aespa.services import settings as settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/llm", response_model=LLMConfigOut | None)
def get_llm_config(session: Session = Depends(get_session)) -> LLMConfigOut | None:
    cfg = settings_service.get_llm_config(session)
    if cfg is None:
        return None
    return settings_service.llm_profile_out(session, cfg)


@router.put("/llm", response_model=LLMConfigOut)
def upsert_llm_config(
    payload: LLMConfigIn,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.upsert_llm_config(session, payload)
    return settings_service.llm_profile_out(session, cfg)


@router.get("/llm/profiles", response_model=list[LLMConfigOut])
def list_llm_profiles(session: Session = Depends(get_session)) -> list[LLMConfigOut]:
    return [settings_service.llm_profile_out(session, cfg) for cfg in settings_service.list_llm_profiles(session)]


@router.post("/llm/profiles", response_model=LLMConfigOut)
def create_llm_profile(
    payload: LLMConfigIn,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.create_llm_profile(session, payload)
    return settings_service.llm_profile_out(session, cfg)


@router.put("/llm/profiles/{profile_id}", response_model=LLMConfigOut)
def update_llm_profile(
    profile_id: int,
    payload: LLMConfigIn,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.update_llm_profile(session, profile_id, payload)
    return settings_service.llm_profile_out(session, cfg)


@router.post("/llm/profiles/{profile_id}/activate", response_model=LLMConfigOut)
def activate_llm_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> LLMConfigOut:
    cfg = settings_service.activate_llm_profile(session, profile_id)
    return settings_service.llm_profile_out(session, cfg)


@router.delete("/llm/profiles/{profile_id}", status_code=204)
def delete_llm_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> Response:
    settings_service.delete_llm_profile(session, profile_id)
    return Response(status_code=204)


@router.get("/llm/providers", response_model=list[LLMProviderConfigOut])
def list_llm_providers(session: Session = Depends(get_session)) -> list[LLMProviderConfigOut]:
    return settings_service.list_llm_providers(session)


@router.post("/llm/providers", response_model=LLMProviderConfigOut)
def create_llm_provider(
    payload: LLMProviderConfigIn,
    session: Session = Depends(get_session),
) -> LLMProviderConfigOut:
    return settings_service.create_llm_provider(session, payload)


@router.put("/llm/providers/{provider_id}", response_model=LLMProviderConfigOut)
def update_llm_provider(
    provider_id: int,
    payload: LLMProviderConfigIn,
    session: Session = Depends(get_session),
) -> LLMProviderConfigOut:
    return settings_service.update_llm_provider(session, provider_id, payload)


@router.delete("/llm/providers/{provider_id}", status_code=204)
def delete_llm_provider(
    provider_id: int,
    session: Session = Depends(get_session),
) -> Response:
    settings_service.delete_llm_provider(session, provider_id)
    return Response(status_code=204)


@router.get("/llm/models")
def default_models() -> dict[str, list[str]]:
    """Return well-known model names for each provider (for UI dropdowns)."""
    return PROVIDER_DEFAULT_MODELS


@router.get("/llm/export", response_model=LLMConfigExport)
def export_llm_config(session: Session = Depends(get_session)) -> LLMConfigExport:
    """Export all LLM providers and profiles as a portable JSON bundle."""
    return settings_service.export_llm_config(session)


@router.post("/llm/import", response_model=LLMImportResult)
def import_llm_config(
    payload: LLMConfigExport,
    session: Session = Depends(get_session),
) -> LLMImportResult:
    """Import LLM providers and profiles from a previously exported bundle."""
    return settings_service.import_llm_config(session, payload)


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


@router.get("/specialist-agent-config", response_model=SpecialistAgentConfigOut)
def get_specialist_agent_config(
    session: Session = Depends(get_session),
) -> SpecialistAgentConfigOut:
    return settings_service.get_specialist_agent_config(session)


@router.put("/specialist-agent-config", response_model=SpecialistAgentConfigOut)
def upsert_specialist_agent_config(
    payload: SpecialistAgentConfigIn,
    session: Session = Depends(get_session),
) -> SpecialistAgentConfigOut:
    return settings_service.upsert_specialist_agent_config(session, payload)


@router.get("/adversarial-validator-config", response_model=ValidatorConfigOut)
def get_adversarial_validator_config(
    session: Session = Depends(get_session),
) -> ValidatorConfigOut:
    return settings_service.get_adversarial_validator_config(session)


@router.put("/adversarial-validator-config", response_model=ValidatorConfigOut)
def upsert_adversarial_validator_config(
    payload: ValidatorConfigIn,
    session: Session = Depends(get_session),
) -> ValidatorConfigOut:
    return settings_service.upsert_adversarial_validator_config(session, payload)


@router.get("/global-http-header", response_model=GlobalHttpHeaderConfigOut)
def get_global_http_header_config(
    session: Session = Depends(get_session),
) -> GlobalHttpHeaderConfigOut:
    return settings_service.get_global_http_header_config(session)


@router.put("/global-http-header", response_model=GlobalHttpHeaderConfigOut)
def upsert_global_http_header_config(
    payload: GlobalHttpHeaderConfigIn,
    session: Session = Depends(get_session),
) -> GlobalHttpHeaderConfigOut:
    return settings_service.upsert_global_http_header_config(session, payload)


@router.get("/reporting-debug", response_model=ReportingDebugConfigOut)
def get_reporting_debug_config(
    session: Session = Depends(get_session),
) -> ReportingDebugConfigOut:
    return settings_service.get_reporting_debug_config(session)


@router.put("/reporting-debug", response_model=ReportingDebugConfigOut)
def upsert_reporting_debug_config(
    payload: ReportingDebugConfigIn,
    session: Session = Depends(get_session),
) -> ReportingDebugConfigOut:
    return settings_service.upsert_reporting_debug_config(session, payload)
