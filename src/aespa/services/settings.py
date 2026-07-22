"""Service layer for application settings (LLM config, etc.)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, select

from aespa.models import (
    AdversarialValidatorConfig,
    BurpRestApiConfig,
    CloudflareAccessConfig,
    GlobalHttpHeaderConfig,
    LLMConfig,
    LLMProfile,
    LLMProviderConfig,
    ReportingDebugConfig,
    ScannerPolicy,
    SpecialistAgentConfig,
    TestRun,
    UpstreamProxyConfig,
)
from aespa.schemas import (
    BurpRestApiConfigIn,
    BurpRestApiConfigOut,
    CloudflareAccessConfigIn,
    CloudflareAccessConfigOut,
    GlobalHttpHeaderConfigIn,
    GlobalHttpHeaderConfigOut,
    LLMConfigExport,
    LLMConfigIn,
    LLMConfigOut,
    LLMExportProfileItem,
    LLMExportProviderItem,
    LLMImportResult,
    LLMProfileIn,
    LLMProfileOut,
    LLMProviderConfigIn,
    LLMProviderConfigOut,
    ReportingDebugConfigIn,
    ReportingDebugConfigOut,
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

# Canonical agent roles a profile can assign a Model to. A scan resolves each
# agent's model via get_llm_config_for_role(); unmapped roles fall back to the
# profile's default model.
AGENT_ROLES: tuple[str, ...] = (
    "crawler",
    "test_lead",
    "specialist",
    "validator",
    "api_scanner",
    "sast",
    "alice",
    "mentor",
)


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
        username=provider.username,
        project_id=provider.project_id,
        models=_provider_models(provider),
        has_api_key=bool(provider.api_key and provider.api_key.strip()),
        api_key=None,
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
    set_committed_value(cfg, "username", provider.username)
    set_committed_value(cfg, "project_id", provider.project_id)
    return cfg


def llm_profile_out_model(session: Session, cfg: LLMConfig) -> LLMConfigOut:
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
        has_api_key=bool(resolved.api_key and resolved.api_key.strip()),
        api_key=None,
        base_url=resolved.base_url,
        username=resolved.username,
        project_id=resolved.project_id,
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


def get_active_scan_profile(session: Session) -> LLMProfile | None:
    return session.exec(select(LLMProfile).where(LLMProfile.is_active == True)).first()  # noqa: E712


def _model_for_profile_role(
    session: Session, prof: LLMProfile, role: str | None
) -> LLMConfig | None:
    """Resolve a role model, with Mentor inheriting Test Lead before default."""
    model_id: int | None = None
    role_models = _json_loads(prof.role_models_json, {})
    if role is not None:
        raw = role_models.get(role)
        if raw is None and role == "mentor":
            raw = role_models.get("test_lead")
        if raw is not None:
            try:
                model_id = int(raw)
            except (TypeError, ValueError):
                model_id = None
    if model_id is None:
        model_id = prof.default_model_id
    if model_id is None:
        return None
    cfg = session.get(LLMConfig, model_id)
    return _profile_with_provider(session, cfg) if cfg is not None else None


def get_llm_config_for_role(
    session: Session, run: "TestRun", role: str | None = None
) -> LLMConfig | None:
    """Resolve the Model an agent should use for a run.

    Precedence: explicit per-run profile → explicit per-run (legacy) model →
    globally active profile → globally active model. Within a profile, an
    explicit per-role override beats the profile's default model.
    """
    # 1. Explicit per-run profile.
    profile_id = getattr(run, "llm_profile_id", None)
    if profile_id is not None:
        prof = session.get(LLMProfile, profile_id)
        if prof is not None:
            cfg = _model_for_profile_role(session, prof, role)
            if cfg is not None:
                return cfg
    # 2. Explicit per-run legacy model (back-compat with pre-profile runs).
    legacy_id = getattr(run, "llm_config_id", None)
    if legacy_id is not None:
        cfg = session.get(LLMConfig, legacy_id)
        if cfg is not None:
            return _profile_with_provider(session, cfg)
    # 3. Globally active profile.
    prof = get_active_scan_profile(session)
    if prof is not None:
        cfg = _model_for_profile_role(session, prof, role)
        if cfg is not None:
            return cfg
    # 4. Globally active model.
    return get_llm_config(session)


def get_llm_config_for_run(session: Session, run: "TestRun") -> LLMConfig | None:
    """Role-agnostic config for a run (resolves to the profile's default model)."""
    return get_llm_config_for_role(session, run, None)


def upsert_llm_config(session: Session, payload: LLMConfigIn) -> LLMConfig:
    cfg = get_llm_config(session)
    if cfg is None:
        cfg = LLMConfig(is_active=True)

    return _apply_llm_config(session, cfg, payload, activate=True)


def list_llm_profiles(session: Session) -> list[LLMConfig]:
    return list(
        session.exec(select(LLMConfig).order_by(LLMConfig.updated_at.desc())).all()
    )


def list_llm_providers(session: Session) -> list[LLMProviderConfigOut]:
    providers = session.exec(
        select(LLMProviderConfig).order_by(LLMProviderConfig.updated_at.desc())
    ).all()
    return [_provider_out(provider) for provider in providers]


def get_llm_provider(session: Session, provider_id: int) -> LLMProviderConfig:
    provider = session.get(LLMProviderConfig, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="LLM provider not found")
    return provider


def create_llm_provider(
    session: Session, payload: LLMProviderConfigIn
) -> LLMProviderConfigOut:
    provider = LLMProviderConfig()
    return _apply_llm_provider(session, provider, payload)


def update_llm_provider(
    session: Session, provider_id: int, payload: LLMProviderConfigIn
) -> LLMProviderConfigOut:
    provider = get_llm_provider(session, provider_id)
    return _apply_llm_provider(session, provider, payload)


def delete_llm_provider(session: Session, provider_id: int) -> None:
    provider = get_llm_provider(session, provider_id)
    if (
        session.exec(
            select(LLMConfig).where(LLMConfig.provider_id == provider_id)
        ).first()
        is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an LLM provider that is used by a profile",
        )
    session.delete(provider)
    session.commit()


def _apply_llm_provider(
    session: Session, provider: LLMProviderConfig, payload: LLMProviderConfigIn
) -> LLMProviderConfigOut:
    _ensure_unique_llm_provider_name(session, payload.name, provider.id)
    provider.name = payload.name
    provider.api_format = payload.api_format
    if payload.api_key is not None:
        key_str = payload.api_key.strip()
        provider.api_key = key_str if key_str else None
    provider.base_url = payload.base_url
    username = (payload.username or "").strip()
    provider.username = (
        username or None if payload.api_format == "github_copilot" else None
    )
    provider.project_id = payload.project_id
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
    return _apply_llm_config(
        session, cfg, payload, activate=(len(list_llm_profiles(session)) == 0)
    )


def update_llm_profile(
    session: Session, profile_id: int, payload: LLMConfigIn
) -> LLMConfig:
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
        replacement = session.exec(
            select(LLMConfig).order_by(LLMConfig.updated_at.desc())
        ).first()
        if replacement is not None:
            activate_llm_profile(session, replacement.id)


# ── Scan profiles (per-agent-role model assignment) ───────────────────────────


def list_scan_profiles(session: Session) -> list[LLMProfile]:
    return list(
        session.exec(select(LLMProfile).order_by(LLMProfile.updated_at.desc())).all()
    )


def get_scan_profile(session: Session, profile_id: int) -> LLMProfile:
    prof = session.get(LLMProfile, profile_id)
    if prof is None:
        raise HTTPException(status_code=404, detail="Scan profile not found")
    return prof


def create_scan_profile(session: Session, payload: LLMProfileIn) -> LLMProfile:
    prof = LLMProfile()
    return _apply_scan_profile(
        session, prof, payload, activate=(len(list_scan_profiles(session)) == 0)
    )


def update_scan_profile(
    session: Session, profile_id: int, payload: LLMProfileIn
) -> LLMProfile:
    prof = get_scan_profile(session, profile_id)
    return _apply_scan_profile(session, prof, payload, activate=prof.is_active)


def activate_scan_profile(session: Session, profile_id: int) -> LLMProfile:
    prof = get_scan_profile(session, profile_id)
    for p in session.exec(select(LLMProfile)).all():
        p.is_active = p.id == profile_id
        session.add(p)
    session.commit()
    session.refresh(prof)
    return prof


def delete_scan_profile(session: Session, profile_id: int) -> None:
    prof = get_scan_profile(session, profile_id)
    was_active = prof.is_active
    session.delete(prof)
    session.commit()
    if was_active:
        replacement = session.exec(
            select(LLMProfile).order_by(LLMProfile.updated_at.desc())
        ).first()
        if replacement is not None:
            activate_scan_profile(session, replacement.id)


def _apply_scan_profile(
    session: Session, prof: LLMProfile, payload: LLMProfileIn, activate: bool
) -> LLMProfile:
    _ensure_unique_scan_profile_name(session, payload.name, prof.id)
    if session.get(LLMConfig, payload.default_model_id) is None:
        raise HTTPException(
            status_code=422,
            detail="default_model_id does not reference an existing Model",
        )
    role_models: dict[str, int] = {}
    for role, model_id in (payload.role_models or {}).items():
        if role not in AGENT_ROLES:
            raise HTTPException(status_code=422, detail=f"Unknown agent role: {role}")
        if model_id is None:
            continue
        if session.get(LLMConfig, model_id) is None:
            raise HTTPException(
                status_code=422,
                detail=f"role_models[{role}] does not reference an existing Model",
            )
        role_models[role] = int(model_id)

    prof.name = payload.name
    prof.default_model_id = payload.default_model_id
    prof.role_models_json = _json_dumps(role_models)
    prof.is_active = bool(activate)
    prof.updated_at = _utcnow()

    if prof.is_active:
        for p in session.exec(select(LLMProfile)).all():
            if p.id != prof.id:
                p.is_active = False
                session.add(p)

    session.add(prof)
    session.commit()
    session.refresh(prof)
    return prof


def _ensure_unique_scan_profile_name(
    session: Session, name: str, current_id: int | None
) -> None:
    normalized = name.strip().casefold()
    for p in session.exec(select(LLMProfile)).all():
        if p.id != current_id and p.name.strip().casefold() == normalized:
            raise HTTPException(
                status_code=409, detail="A profile with that name already exists"
            )


def llm_profile_out(session: Session, prof: LLMProfile) -> LLMProfileOut:
    role_models = {
        k: int(v)
        for k, v in _json_loads(prof.role_models_json, {}).items()
        if v is not None
    }

    def _model_name(model_id: int | None) -> str | None:
        if model_id is None:
            return None
        model = session.get(LLMConfig, model_id)
        return model.name if model is not None else None

    return LLMProfileOut(
        id=prof.id,
        name=prof.name,
        is_active=prof.is_active,
        default_model_id=prof.default_model_id,
        default_model_name=_model_name(prof.default_model_id),
        role_models=role_models,
        role_model_names={k: _model_name(v) for k, v in role_models.items()},
        updated_at=prof.updated_at,
    )


def _apply_llm_config(
    session: Session, cfg: LLMConfig, payload: LLMConfigIn, activate: bool
) -> LLMConfig:
    _ensure_unique_llm_profile_name(session, payload.name, cfg.id)
    provider = get_llm_provider(session, payload.provider_id)
    if payload.model not in _provider_models(provider):
        raise HTTPException(
            status_code=422, detail="Model is not configured for the selected provider"
        )

    cfg.name = payload.name
    cfg.is_active = bool(activate)

    cfg.provider_id = payload.provider_id
    cfg.provider = provider.api_format
    cfg.api_key = provider.api_key
    cfg.base_url = provider.base_url
    cfg.username = provider.username
    cfg.project_id = provider.project_id
    cfg.model = payload.model
    cfg.max_tokens = payload.max_tokens
    cfg.temperature = payload.temperature
    cfg.use_vision = payload.use_vision
    cfg.force_tool_choice = payload.force_tool_choice
    cfg.updated_at = _utcnow()

    if cfg.is_active:
        for profile in session.exec(select(LLMConfig)).all():
            if profile.id != cfg.id:
                profile.is_active = False
                session.add(profile)

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg


def _ensure_unique_llm_profile_name(
    session: Session, name: str, current_id: int | None
) -> None:
    normalized = name.strip().casefold()
    for profile in session.exec(select(LLMConfig)).all():
        if profile.id != current_id and profile.name.strip().casefold() == normalized:
            raise HTTPException(
                status_code=409,
                detail="An LLM settings profile with that name already exists",
            )


def _ensure_unique_llm_provider_name(
    session: Session, name: str, current_id: int | None
) -> None:
    normalized = name.strip().casefold()
    for provider in session.exec(select(LLMProviderConfig)).all():
        if provider.id != current_id and provider.name.strip().casefold() == normalized:
            raise HTTPException(
                status_code=409, detail="An LLM provider with that name already exists"
            )


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
        execution_monitor_enabled=cfg.execution_monitor_enabled,
        max_consecutive_text_turns=getattr(cfg, "max_consecutive_text_turns", 3),
        enforce_full_coverage_obligations=getattr(
            cfg, "enforce_full_coverage_obligations", True
        ),
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


def upsert_scanner_policy(
    session: Session, payload: ScannerPolicyIn
) -> ScannerPolicyOut:
    cfg = session.get(ScannerPolicy, _SINGLETON_ID)
    if cfg is None:
        cfg = ScannerPolicy(id=_SINGLETON_ID)

    cfg.execution_monitor_enabled = payload.execution_monitor_enabled
    cfg.max_consecutive_text_turns = payload.max_consecutive_text_turns
    cfg.enforce_full_coverage_obligations = payload.enforce_full_coverage_obligations
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
    return RunScannerPolicyOut(
        **policy.model_dump(exclude={"updated_at"}),
        source="global_default",
        updated_at=policy.updated_at,
    )


def get_upstream_proxy_config(session: Session) -> UpstreamProxyConfigOut:
    cfg = session.get(UpstreamProxyConfig, _SINGLETON_ID)
    if cfg is None:
        return UpstreamProxyConfigOut(
            **UpstreamProxyConfigIn().model_dump(), updated_at=_utcnow()
        )
    return UpstreamProxyConfigOut(
        proxy_url=cfg.proxy_url,
        proxy_scanner=cfg.proxy_scanner,
        proxy_llm=cfg.proxy_llm,
        updated_at=cfg.updated_at,
    )


def upsert_upstream_proxy_config(
    session: Session, payload: UpstreamProxyConfigIn
) -> UpstreamProxyConfigOut:
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
        has_api_key=bool(cfg.api_key and cfg.api_key.strip()),
        api_key=None,
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


def get_burp_rest_api_config_model(session: Session) -> BurpRestApiConfig:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        return BurpRestApiConfig(id=_SINGLETON_ID)
    return cfg


def get_burp_rest_api_config(session: Session) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        return BurpRestApiConfigOut(
            **BurpRestApiConfigIn().model_dump(), updated_at=_utcnow()
        )
    return _burp_rest_api_config_from_model(cfg)


def get_specialist_agent_config(session: Session) -> SpecialistAgentConfigOut:
    cfg = session.get(SpecialistAgentConfig, _SINGLETON_ID)
    if cfg is None:
        return SpecialistAgentConfigOut(
            **SpecialistAgentConfigIn().model_dump(), updated_at=_utcnow()
        )
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


def upsert_burp_rest_api_config(
    session: Session, payload: BurpRestApiConfigIn
) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = BurpRestApiConfig(id=_SINGLETON_ID)

    cfg.enabled = payload.enabled
    cfg.api_url = payload.api_url
    if payload.api_key is not None:
        key_str = payload.api_key.strip()
        cfg.api_key = key_str if key_str else None
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
        return ValidatorConfigOut(
            **ValidatorConfigIn().model_dump(), updated_at=_utcnow()
        )
    return ValidatorConfigOut(
        enabled=cfg.enabled,
        max_steps=cfg.max_steps,
        min_severity=cfg.min_severity,
        end_scan_max_concurrent=cfg.end_scan_max_concurrent,
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
    cfg.end_scan_max_concurrent = payload.end_scan_max_concurrent
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
        return GlobalHttpHeaderConfigOut(
            **GlobalHttpHeaderConfigIn().model_dump(), updated_at=_utcnow()
        )
    try:
        parsed_headers = json.loads(cfg.headers_json or "[]")
        headers = parsed_headers if isinstance(parsed_headers, list) else []
    except (TypeError, json.JSONDecodeError):
        headers = []
    # Databases created before multi-header support have values only in these
    # legacy fields. Return that value until the user saves the new table.
    if not headers and cfg.header_name and cfg.header_value:
        headers = [{"header_name": cfg.header_name, "header_value": cfg.header_value}]
    return GlobalHttpHeaderConfigOut(
        headers=headers,
        updated_at=cfg.updated_at,
    )


def upsert_global_http_header_config(
    session: Session, payload: GlobalHttpHeaderConfigIn
) -> GlobalHttpHeaderConfigOut:
    cfg = session.get(GlobalHttpHeaderConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = GlobalHttpHeaderConfig(id=_SINGLETON_ID)
    cfg.headers_json = json.dumps(
        [header.model_dump() for header in payload.headers], separators=(",", ":")
    )
    # Keep the old columns in sync with the first header for a graceful rollback
    # to an earlier AESPA version.
    first_header = payload.headers[0] if payload.headers else None
    cfg.header_name = first_header.header_name if first_header else None
    cfg.header_value = first_header.header_value if first_header else None
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_global_http_header_config(session)


def get_reporting_debug_config(session: Session) -> ReportingDebugConfigOut:
    cfg = session.get(ReportingDebugConfig, _SINGLETON_ID)
    if cfg is None:
        return ReportingDebugConfigOut(
            **ReportingDebugConfigIn().model_dump(),
            updated_at=_utcnow(),
        )
    return ReportingDebugConfigOut(
        capture_enabled=cfg.capture_enabled,
        panel_enabled=cfg.panel_enabled,
        batch_max_concurrent=cfg.batch_max_concurrent,
        updated_at=cfg.updated_at,
    )


def upsert_reporting_debug_config(
    session: Session, payload: ReportingDebugConfigIn
) -> ReportingDebugConfigOut:
    cfg = session.get(ReportingDebugConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = ReportingDebugConfig(id=_SINGLETON_ID)
    cfg.capture_enabled = payload.capture_enabled
    cfg.panel_enabled = payload.panel_enabled
    cfg.batch_max_concurrent = payload.batch_max_concurrent
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_reporting_debug_config(session)


def get_cloudflare_access_config(session: Session) -> CloudflareAccessConfigOut:
    cfg = session.get(CloudflareAccessConfig, _SINGLETON_ID)
    if cfg is None:
        return CloudflareAccessConfigOut(audience=None, updated_at=_utcnow())
    return CloudflareAccessConfigOut(audience=cfg.audience, updated_at=cfg.updated_at)


def upsert_cloudflare_access_config(
    session: Session, payload: CloudflareAccessConfigIn
) -> CloudflareAccessConfigOut:
    cfg = session.get(CloudflareAccessConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = CloudflareAccessConfig(id=_SINGLETON_ID)
    # Normalise blank → None so the verifier cleanly falls back to "no audience".
    audience = (payload.audience or "").strip()
    cfg.audience = audience or None
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_cloudflare_access_config(session)


# ── LLM config export / import ────────────────────────────────────────────────


def _is_direct_loopback(request: Request | None) -> bool:
    if request is None or request.client is None:
        return False
    host = request.client.host
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        return False
    proxy_headers = (
        "cf-access-jwt-assertion",
        "cf-connecting-ip",
        "x-forwarded-for",
        "x-forwarded-host",
        "x-real-ip",
    )
    for h in proxy_headers:
        if h in request.headers:
            return False
    return True


def export_llm_config(
    session: Session, request: Request | None = None
) -> LLMConfigExport:
    """Serialize all LLM providers and profiles to a portable dict.

    If accessed directly from local loopback (without proxy headers), API keys
    are included in raw form for ease of export/import. If accessed remotely or
    via a reverse proxy (e.g. Cloudflare Access), API keys are omitted.
    """
    providers_db = session.exec(
        select(LLMProviderConfig).order_by(LLMProviderConfig.id)
    ).all()
    profiles_db = session.exec(select(LLMConfig).order_by(LLMConfig.id)).all()

    provider_id_to_name: dict[int, str] = {
        p.id: p.name for p in providers_db if p.id is not None
    }
    include_raw_keys = _is_direct_loopback(request)

    provider_items = [
        LLMExportProviderItem(
            name=p.name,
            api_format=p.api_format,
            base_url=p.base_url,
            username=p.username,
            project_id=p.project_id,
            models=_provider_models(p),
            has_api_key=bool(p.api_key and p.api_key.strip()),
            api_key=p.api_key if include_raw_keys else None,
            max_tpm=p.max_tpm,
            max_rpm=p.max_rpm,
        )
        for p in providers_db
    ]

    profile_items = [
        LLMExportProfileItem(
            name=c.name,
            provider_name=provider_id_to_name.get(c.provider_id, "")
            if c.provider_id is not None
            else "",
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
    existing_providers = {
        p.name.strip().casefold(): p
        for p in session.exec(select(LLMProviderConfig)).all()
    }

    for item in payload.providers:
        key = item.name.strip().casefold()
        if not item.models:
            raise HTTPException(
                status_code=422, detail=f"Provider '{item.name}' has no models listed"
            )
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
        username = (item.username or "").strip()
        provider.username = (
            username or None if item.api_format == "github_copilot" else None
        )
        provider.project_id = item.project_id
        if item.api_key is not None:
            key_str = item.api_key.strip()
            provider.api_key = key_str if key_str else None
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
    existing_profiles = {
        c.name.strip().casefold(): c for c in session.exec(select(LLMConfig)).all()
    }

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
            raise HTTPException(
                status_code=422,
                detail=f"Provider '{item.provider_name}' not found after import",
            )
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
