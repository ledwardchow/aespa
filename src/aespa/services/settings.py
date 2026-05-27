"""Service layer for application settings (LLM config, etc.)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, select

from aespa.models import AdversarialValidatorConfig, BurpRestApiConfig, GlobalHttpHeaderConfig, LLMConfig, LLMProviderConfig, ScannerPolicy, SpecialistAgentConfig, TestRun, UpstreamProxyConfig
from aespa.schemas import (
    BurpRestApiConfigIn,
    BurpRestApiConfigOut,
    GlobalHttpHeaderConfigIn,
    GlobalHttpHeaderConfigOut,
    LLMConfigExport,
    LLMConfigIn,
    LLMConfigOut,
    LLMExportProfileItem,
    LLMExportProviderItem,
    LLMImportResult,
    LLMProviderConfigIn,
    LLMProviderConfigOut,
    RunScannerPolicyOut,
    ScannerPolicyIn,
    ScannerPolicyOut,
    SpecialistAgentConfigIn,
    SpecialistAgentConfigOut,
    UpstreamProxyConfigIn,
    UpstreamProxyConfigOut,
    ValidatorConfigIn,
    ValidatorConfigOut,
)

_SINGLETON_ID = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _provider_models(provider: LLMProviderConfig) -> list[str]:
    models = _json_loads(provider.models_json, [])
    return [m for m in models if isinstance(m, str) and m.strip()]


def _provider_out(provider: LLMProviderConfig) -> LLMProviderConfigOut:
    return LLMProviderConfigOut(
        id=provider.id,
        name=provider.name,
        api_format=provider.api_format,
        base_url=provider.base_url,
        models=_provider_models(provider),
        api_key=provider.api_key,
        max_tpm=provider.max_tpm,
        max_rpm=provider.max_rpm,
        updated_at=provider.updated_at,
    )



def _profile_with_provider(session: Session, cfg: LLMConfig) -> LLMConfig:
    if cfg.provider_id is None:
        return cfg
    provider = session.get(LLMProviderConfig, cfg.provider_id)
    if provider is None:
        return cfg
    set_committed_value(cfg, "provider", provider.api_format)
    set_committed_value(cfg, "api_key", provider.api_key)
    set_committed_value(cfg, "base_url", provider.base_url)
    return cfg


def llm_profile_out(session: Session, cfg: LLMConfig) -> LLMConfigOut:
    resolved = _profile_with_provider(session, cfg)
    provider_name = None
    if cfg.provider_id is not None:
        provider = session.get(LLMProviderConfig, cfg.provider_id)
        provider_name = provider.name if provider is not None else None
    return LLMConfigOut(
        id=resolved.id,
        name=resolved.name,
        is_active=resolved.is_active,
        provider_id=resolved.provider_id,
        provider_name=provider_name,
        provider=resolved.provider,
        api_key=resolved.api_key,
        base_url=resolved.base_url,
        model=resolved.model,
        max_tokens=resolved.max_tokens,
        temperature=resolved.temperature,
        use_vision=resolved.use_vision,
        force_tool_choice=resolved.force_tool_choice,
        updated_at=resolved.updated_at,
    )


def get_llm_config(session: Session) -> LLMConfig | None:
    cfg = session.exec(select(LLMConfig).where(LLMConfig.is_active == True)).first()  # noqa: E712
    if cfg is None:
        return None
    return _profile_with_provider(session, cfg)


def get_llm_config_for_run(session: Session, run: "TestRun") -> LLMConfig | None:
    """Return the LLM config for a run: per-run override if set, else the active global one."""
    if run.llm_config_id is not None:
        cfg = session.get(LLMConfig, run.llm_config_id)
        if cfg is not None:
            return _profile_with_provider(session, cfg)
    return get_llm_config(session)


def upsert_llm_config(session: Session, payload: LLMConfigIn) -> LLMConfig:
    cfg = get_llm_config(session)
    if cfg is None:
        cfg = LLMConfig(is_active=True)

    return _apply_llm_config(session, cfg, payload, activate=True)


def list_llm_profiles(session: Session) -> list[LLMConfig]:
    return list(session.exec(select(LLMConfig).order_by(LLMConfig.updated_at.desc())).all())


def list_llm_providers(session: Session) -> list[LLMProviderConfigOut]:
    providers = session.exec(select(LLMProviderConfig).order_by(LLMProviderConfig.updated_at.desc())).all()
    return [_provider_out(provider) for provider in providers]


def get_llm_provider(session: Session, provider_id: int) -> LLMProviderConfig:
    provider = session.get(LLMProviderConfig, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="LLM provider not found")
    return provider


def create_llm_provider(session: Session, payload: LLMProviderConfigIn) -> LLMProviderConfigOut:
    provider = LLMProviderConfig()
    return _apply_llm_provider(session, provider, payload)


def update_llm_provider(session: Session, provider_id: int, payload: LLMProviderConfigIn) -> LLMProviderConfigOut:
    provider = get_llm_provider(session, provider_id)
    return _apply_llm_provider(session, provider, payload)


def delete_llm_provider(session: Session, provider_id: int) -> None:
    provider = get_llm_provider(session, provider_id)
    if session.exec(select(LLMConfig).where(LLMConfig.provider_id == provider_id)).first() is not None:
        raise HTTPException(status_code=409, detail="Cannot delete an LLM provider that is used by a profile")
    session.delete(provider)
    session.commit()


def _apply_llm_provider(session: Session, provider: LLMProviderConfig, payload: LLMProviderConfigIn) -> LLMProviderConfigOut:
    _ensure_unique_llm_provider_name(session, payload.name, provider.id)
    provider.name = payload.name
    provider.api_format = payload.api_format
    provider.api_key = payload.api_key
    provider.base_url = payload.base_url
    provider.models_json = _json_dumps(payload.models)
    provider.max_tpm = payload.max_tpm
    provider.max_rpm = payload.max_rpm
    provider.updated_at = _utcnow()
    session.add(provider)
    session.commit()
    session.refresh(provider)
    return _provider_out(provider)



def get_llm_profile(session: Session, profile_id: int) -> LLMConfig:
    cfg = session.get(LLMConfig, profile_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="LLM settings profile not found")
    return cfg


def create_llm_profile(session: Session, payload: LLMConfigIn) -> LLMConfig:
    cfg = LLMConfig()
    return _apply_llm_config(session, cfg, payload, activate=(len(list_llm_profiles(session)) == 0))


def update_llm_profile(session: Session, profile_id: int, payload: LLMConfigIn) -> LLMConfig:
    cfg = get_llm_profile(session, profile_id)
    return _apply_llm_config(session, cfg, payload, activate=cfg.is_active)


def activate_llm_profile(session: Session, profile_id: int) -> LLMConfig:
    cfg = get_llm_profile(session, profile_id)
    for profile in session.exec(select(LLMConfig)).all():
        profile.is_active = profile.id == profile_id
        session.add(profile)
    session.commit()
    session.refresh(cfg)
    return cfg


def delete_llm_profile(session: Session, profile_id: int) -> None:
    cfg = get_llm_profile(session, profile_id)
    was_active = cfg.is_active
    session.delete(cfg)
    session.commit()
    if was_active:
        replacement = session.exec(select(LLMConfig).order_by(LLMConfig.updated_at.desc())).first()
        if replacement is not None:
            activate_llm_profile(session, replacement.id)


def _apply_llm_config(session: Session, cfg: LLMConfig, payload: LLMConfigIn, activate: bool) -> LLMConfig:
    _ensure_unique_llm_profile_name(session, payload.name, cfg.id)
    provider = get_llm_provider(session, payload.provider_id)
    if payload.model not in _provider_models(provider):
        raise HTTPException(status_code=422, detail="Model is not configured for the selected provider")

    cfg.name        = payload.name
    cfg.is_active   = bool(activate)

    cfg.provider_id = payload.provider_id
    cfg.provider    = provider.api_format
    cfg.api_key     = provider.api_key
    cfg.base_url    = provider.base_url
    cfg.model       = payload.model
    cfg.max_tokens  = payload.max_tokens
    cfg.temperature = payload.temperature
    cfg.use_vision  = payload.use_vision
    cfg.force_tool_choice = payload.force_tool_choice
    cfg.updated_at  = _utcnow()

    if cfg.is_active:
        for profile in session.exec(select(LLMConfig)).all():
            if profile.id != cfg.id:
                profile.is_active = False
                session.add(profile)

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg


def _ensure_unique_llm_profile_name(session: Session, name: str, current_id: int | None) -> None:
    normalized = name.strip().casefold()
    for profile in session.exec(select(LLMConfig)).all():
        if profile.id != current_id and profile.name.strip().casefold() == normalized:
            raise HTTPException(status_code=409, detail="An LLM settings profile with that name already exists")


def _ensure_unique_llm_provider_name(session: Session, name: str, current_id: int | None) -> None:
    normalized = name.strip().casefold()
    for provider in session.exec(select(LLMProviderConfig)).all():
        if provider.id != current_id and provider.name.strip().casefold() == normalized:
            raise HTTPException(status_code=409, detail="An LLM provider with that name already exists")


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _json_dumps(value) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _policy_from_model(cfg: ScannerPolicy) -> ScannerPolicyOut:
    return ScannerPolicyOut(
        scan_mode=cfg.scan_mode,
        max_probes_per_page=cfg.max_probes_per_page,
        thinking_max_steps=cfg.thinking_max_steps,
        request_timeout_s=cfg.request_timeout_s,
        min_delay_s=cfg.min_delay_s,
        max_request_body_bytes=cfg.max_request_body_bytes,
        response_body_read_limit_bytes=cfg.response_body_read_limit_bytes,
        allowed_schemes=_json_loads(cfg.allowed_schemes, ["http", "https"]),
        methods_by_mode=_json_loads(cfg.methods_by_mode, None),
        blocked_headers=_json_loads(cfg.blocked_headers, ["host", "cookie"]),
        follow_redirects=cfg.follow_redirects,
        allow_subdomains=cfg.allow_subdomains,
        require_approval_for_destructive=cfg.require_approval_for_destructive,
        updated_at=cfg.updated_at,
    )


def get_scanner_policy(session: Session) -> ScannerPolicyOut:
    cfg = session.get(ScannerPolicy, _SINGLETON_ID)
    if cfg is None:
        return ScannerPolicyOut(**ScannerPolicyIn().model_dump(), updated_at=_utcnow())
    return _policy_from_model(cfg)


def upsert_scanner_policy(session: Session, payload: ScannerPolicyIn) -> ScannerPolicyOut:
    cfg = session.get(ScannerPolicy, _SINGLETON_ID)
    if cfg is None:
        cfg = ScannerPolicy(id=_SINGLETON_ID)

    cfg.scan_mode = payload.scan_mode
    cfg.max_probes_per_page = payload.max_probes_per_page
    cfg.thinking_max_steps = payload.thinking_max_steps
    cfg.request_timeout_s = payload.request_timeout_s
    cfg.min_delay_s = payload.min_delay_s
    cfg.max_request_body_bytes = payload.max_request_body_bytes
    cfg.response_body_read_limit_bytes = payload.response_body_read_limit_bytes
    cfg.allowed_schemes = _json_dumps(payload.allowed_schemes)
    cfg.methods_by_mode = _json_dumps(payload.methods_by_mode)
    cfg.blocked_headers = _json_dumps(payload.blocked_headers)
    cfg.follow_redirects = payload.follow_redirects
    cfg.allow_subdomains = payload.allow_subdomains
    cfg.require_approval_for_destructive = payload.require_approval_for_destructive
    cfg.updated_at = _utcnow()

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return _policy_from_model(cfg)


def get_run_scanner_policy(session: Session, run: TestRun) -> RunScannerPolicyOut:
    policy = get_scanner_policy(session)
    return RunScannerPolicyOut(**policy.model_dump(exclude={"updated_at"}), source="global_default", updated_at=policy.updated_at)


def get_upstream_proxy_config(session: Session) -> UpstreamProxyConfigOut:
    cfg = session.get(UpstreamProxyConfig, _SINGLETON_ID)
    if cfg is None:
        return UpstreamProxyConfigOut(**UpstreamProxyConfigIn().model_dump(), updated_at=_utcnow())
    return UpstreamProxyConfigOut(
        proxy_url=cfg.proxy_url,
        proxy_scanner=cfg.proxy_scanner,
        proxy_llm=cfg.proxy_llm,
        updated_at=cfg.updated_at,
    )


def upsert_upstream_proxy_config(session: Session, payload: UpstreamProxyConfigIn) -> UpstreamProxyConfigOut:
    cfg = session.get(UpstreamProxyConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = UpstreamProxyConfig(id=_SINGLETON_ID)
    cfg.proxy_url = payload.proxy_url
    cfg.proxy_scanner = payload.proxy_scanner
    cfg.proxy_llm = payload.proxy_llm
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_upstream_proxy_config(session)


def _burp_rest_api_config_from_model(cfg: BurpRestApiConfig) -> BurpRestApiConfigOut:
    return BurpRestApiConfigOut(
        enabled=cfg.enabled,
        api_url=cfg.api_url,
        api_key=cfg.api_key,
        scan_configuration_name=cfg.scan_configuration_name,
        scan_sqli=cfg.scan_sqli,
        scan_xss=cfg.scan_xss,
        scan_command_injection=cfg.scan_command_injection,
        scan_path_traversal=cfg.scan_path_traversal,
        scan_ssrf=cfg.scan_ssrf,
        scan_xxe=cfg.scan_xxe,
        scan_ssti=cfg.scan_ssti,
        updated_at=cfg.updated_at,
    )


def get_burp_rest_api_config(session: Session) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        return BurpRestApiConfigOut(**BurpRestApiConfigIn().model_dump(), updated_at=_utcnow())
    return _burp_rest_api_config_from_model(cfg)


def get_specialist_agent_config(session: Session) -> SpecialistAgentConfigOut:
    cfg = session.get(SpecialistAgentConfig, _SINGLETON_ID)
    if cfg is None:
        return SpecialistAgentConfigOut(**SpecialistAgentConfigIn().model_dump(), updated_at=_utcnow())
    return SpecialistAgentConfigOut(
        enabled=cfg.enabled,
        max_concurrent=cfg.max_concurrent,
        max_steps=cfg.max_steps,
        min_priority=cfg.min_priority,
        dispatch_idor=cfg.dispatch_idor,
        dispatch_auth_bypass=cfg.dispatch_auth_bypass,
        dispatch_sqli=cfg.dispatch_sqli,
        dispatch_xss=cfg.dispatch_xss,
        dispatch_business_logic=cfg.dispatch_business_logic,
        dispatch_ssrf=cfg.dispatch_ssrf,
        dispatch_path_traversal=cfg.dispatch_path_traversal,
        dispatch_cors=cfg.dispatch_cors,
        dispatch_crypto=cfg.dispatch_crypto,
        dispatch_config=cfg.dispatch_config,
        trigger_specialist_on_burp=cfg.trigger_specialist_on_burp,
        updated_at=cfg.updated_at,
    )


def upsert_specialist_agent_config(
    session: Session, payload: SpecialistAgentConfigIn
) -> SpecialistAgentConfigOut:
    cfg = session.get(SpecialistAgentConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = SpecialistAgentConfig(id=_SINGLETON_ID)
    cfg.enabled = payload.enabled
    cfg.max_concurrent = payload.max_concurrent
    cfg.max_steps = payload.max_steps
    cfg.min_priority = payload.min_priority
    cfg.dispatch_idor = payload.dispatch_idor
    cfg.dispatch_auth_bypass = payload.dispatch_auth_bypass
    cfg.dispatch_sqli = payload.dispatch_sqli
    cfg.dispatch_xss = payload.dispatch_xss
    cfg.dispatch_business_logic = payload.dispatch_business_logic
    cfg.dispatch_ssrf = payload.dispatch_ssrf
    cfg.dispatch_path_traversal = payload.dispatch_path_traversal
    cfg.dispatch_cors = payload.dispatch_cors
    cfg.dispatch_crypto = payload.dispatch_crypto
    cfg.dispatch_config = payload.dispatch_config
    cfg.trigger_specialist_on_burp = payload.trigger_specialist_on_burp
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_specialist_agent_config(session)


def upsert_burp_rest_api_config(session: Session, payload: BurpRestApiConfigIn) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = BurpRestApiConfig(id=_SINGLETON_ID)

    cfg.enabled = payload.enabled
    cfg.api_url = payload.api_url
    cfg.api_key = payload.api_key
    cfg.scan_configuration_name = payload.scan_configuration_name
    cfg.scan_sqli = payload.scan_sqli
    cfg.scan_xss = payload.scan_xss
    cfg.scan_command_injection = payload.scan_command_injection
    cfg.scan_path_traversal = payload.scan_path_traversal
    cfg.scan_ssrf = payload.scan_ssrf
    cfg.scan_xxe = payload.scan_xxe
    cfg.scan_ssti = payload.scan_ssti
    cfg.updated_at = _utcnow()

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return _burp_rest_api_config_from_model(cfg)


def get_adversarial_validator_config(session: Session) -> ValidatorConfigOut:
    cfg = session.get(AdversarialValidatorConfig, _SINGLETON_ID)
    if cfg is None:
        return ValidatorConfigOut(**ValidatorConfigIn().model_dump(), updated_at=_utcnow())
    return ValidatorConfigOut(
        enabled=cfg.enabled,
        max_steps=cfg.max_steps,
        min_severity=cfg.min_severity,
        auto_validate_inline=cfg.auto_validate_inline,
        require_concrete_disproof=cfg.require_concrete_disproof,
        updated_at=cfg.updated_at,
    )


def upsert_adversarial_validator_config(
    session: Session, payload: ValidatorConfigIn
) -> ValidatorConfigOut:
    cfg = session.get(AdversarialValidatorConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = AdversarialValidatorConfig(id=_SINGLETON_ID)
    cfg.enabled = payload.enabled
    cfg.max_steps = payload.max_steps
    cfg.min_severity = payload.min_severity
    cfg.auto_validate_inline = payload.auto_validate_inline
    cfg.require_concrete_disproof = payload.require_concrete_disproof
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_adversarial_validator_config(session)


def get_global_http_header_config(session: Session) -> GlobalHttpHeaderConfigOut:
    cfg = session.get(GlobalHttpHeaderConfig, _SINGLETON_ID)
    if cfg is None:
        return GlobalHttpHeaderConfigOut(**GlobalHttpHeaderConfigIn().model_dump(), updated_at=_utcnow())
    return GlobalHttpHeaderConfigOut(
        header_name=cfg.header_name,
        header_value=cfg.header_value,
        updated_at=cfg.updated_at,
    )


def upsert_global_http_header_config(
    session: Session, payload: GlobalHttpHeaderConfigIn
) -> GlobalHttpHeaderConfigOut:
    cfg = session.get(GlobalHttpHeaderConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = GlobalHttpHeaderConfig(id=_SINGLETON_ID)
    cfg.header_name = payload.header_name
    cfg.header_value = payload.header_value
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_global_http_header_config(session)


# ── LLM config export / import ────────────────────────────────────────────────

def export_llm_config(session: Session) -> LLMConfigExport:
    """Serialize all LLM providers and profiles to a portable dict."""
    providers_db = session.exec(select(LLMProviderConfig).order_by(LLMProviderConfig.id)).all()
    profiles_db = session.exec(select(LLMConfig).order_by(LLMConfig.id)).all()

    provider_id_to_name: dict[int, str] = {p.id: p.name for p in providers_db if p.id is not None}

    provider_items = [
        LLMExportProviderItem(
            name=p.name,
            api_format=p.api_format,
            base_url=p.base_url,
            models=_provider_models(p),
            api_key=p.api_key,
            max_tpm=p.max_tpm,
            max_rpm=p.max_rpm,
        )
        for p in providers_db
    ]

    profile_items = [
        LLMExportProfileItem(
            name=c.name,
            provider_name=provider_id_to_name.get(c.provider_id, "") if c.provider_id is not None else "",
            model=c.model,
            max_tokens=c.max_tokens,
            temperature=c.temperature,
            use_vision=c.use_vision,
            force_tool_choice=c.force_tool_choice,
            is_active=c.is_active,
        )
        for c in profiles_db
    ]

    return LLMConfigExport(
        exported_at=_utcnow(),
        providers=provider_items,
        profiles=profile_items,
    )


def import_llm_config(session: Session, payload: LLMConfigExport) -> LLMImportResult:
    """Merge exported LLM providers and profiles into the database.

    Matching is done by name (case-insensitive).
    Existing records are updated; missing ones are created.
    """
    result = LLMImportResult()

    # Fail fast on duplicate provider names in the payload
    seen_providers = set()
    for item in payload.providers:
        name_key = item.name.strip().casefold()
        if name_key in seen_providers:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate provider name '{item.name}' found in import payload",
            )
        seen_providers.add(name_key)

    # Fail fast on duplicate profile names in the payload
    seen_profiles = set()
    for item in payload.profiles:
        name_key = item.name.strip().casefold()
        if name_key in seen_profiles:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate profile name '{item.name}' found in import payload",
            )
        seen_profiles.add(name_key)

    # ── 1. Upsert providers ───────────────────────────────────────────────────
    provider_name_to_id: dict[str, int] = {}
    existing_providers = {p.name.strip().casefold(): p for p in session.exec(select(LLMProviderConfig)).all()}

    for item in payload.providers:
        key = item.name.strip().casefold()
        if not item.models:
            raise HTTPException(status_code=422, detail=f"Provider '{item.name}' has no models listed")
        provider = existing_providers.get(key)
        if provider is None:
            provider = LLMProviderConfig()
            result.providers_created += 1
            existing_providers[key] = provider
        else:
            result.providers_updated += 1
        provider.name = item.name
        provider.api_format = item.api_format
        provider.base_url = item.base_url
        provider.api_key = item.api_key
        provider.models_json = _json_dumps(item.models)
        provider.max_tpm = item.max_tpm
        provider.max_rpm = item.max_rpm
        provider.updated_at = _utcnow()
        session.add(provider)
        session.flush()  # assign id before we need it
        if provider.id is not None:
            provider_name_to_id[item.name.strip().casefold()] = provider.id

    session.flush()


    # refresh the map with any newly-created providers
    for p in session.exec(select(LLMProviderConfig)).all():
        if p.id is not None:
            provider_name_to_id.setdefault(p.name.strip().casefold(), p.id)

    # ── 2. Upsert profiles ────────────────────────────────────────────────────
    existing_profiles = {c.name.strip().casefold(): c for c in session.exec(select(LLMConfig)).all()}

    imported_active_name: str | None = None
    for item in payload.profiles:
        provider_key = item.provider_name.strip().casefold()
        provider_id = provider_name_to_id.get(provider_key)
        if provider_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"Profile '{item.name}' references unknown provider '{item.provider_name}'",
            )
        provider = session.get(LLMProviderConfig, provider_id)
        if provider is None:
            raise HTTPException(status_code=422, detail=f"Provider '{item.provider_name}' not found after import")
        if item.model not in _provider_models(provider):
            raise HTTPException(
                status_code=422,
                detail=f"Model '{item.model}' is not in the model list for provider '{item.provider_name}'",
            )

        key = item.name.strip().casefold()
        cfg = existing_profiles.get(key)
        if cfg is None:
            cfg = LLMConfig()
            result.profiles_created += 1
            existing_profiles[key] = cfg
        else:
            result.profiles_updated += 1

        cfg.name = item.name
        cfg.provider_id = provider_id
        cfg.provider = provider.api_format
        cfg.api_key = provider.api_key
        cfg.base_url = provider.base_url
        cfg.model = item.model
        cfg.max_tokens = item.max_tokens
        cfg.temperature = item.temperature
        cfg.use_vision = item.use_vision
        cfg.force_tool_choice = item.force_tool_choice
        cfg.is_active = False  # we handle activation below
        cfg.updated_at = _utcnow()
        session.add(cfg)

        if item.is_active:
            imported_active_name = item.name.strip().casefold()

    session.flush()

    # ── 3. Activate the designated profile (if any) ───────────────────────────
    if imported_active_name is not None:
        for cfg in session.exec(select(LLMConfig)).all():
            cfg.is_active = cfg.name.strip().casefold() == imported_active_name
            session.add(cfg)

    session.commit()
    return result
