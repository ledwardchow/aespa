"""Service layer for application settings (LLM config, etc.)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from aespa.models import BurpRestApiConfig, LLMConfig, ScannerPolicy, TestRun, UpstreamProxyConfig
from aespa.schemas import (
    BurpRestApiConfigIn,
    BurpRestApiConfigOut,
    LLMConfigIn,
    RunScannerPolicyOut,
    ScannerPolicyIn,
    ScannerPolicyOut,
    UpstreamProxyConfigIn,
    UpstreamProxyConfigOut,
)

_SINGLETON_ID = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_llm_config(session: Session) -> LLMConfig | None:
    return session.exec(select(LLMConfig).where(LLMConfig.is_active == True)).first()  # noqa: E712


def get_llm_config_for_run(session: Session, run: "TestRun") -> LLMConfig | None:
    """Return the LLM config for a run: per-run override if set, else the active global one."""
    if run.llm_config_id is not None:
        cfg = session.get(LLMConfig, run.llm_config_id)
        if cfg is not None:
            return cfg
    return get_llm_config(session)


def upsert_llm_config(session: Session, payload: LLMConfigIn) -> LLMConfig:
    cfg = get_llm_config(session)
    if cfg is None:
        cfg = LLMConfig(is_active=True)

    return _apply_llm_config(session, cfg, payload, activate=True)


def list_llm_profiles(session: Session) -> list[LLMConfig]:
    return list(session.exec(select(LLMConfig).order_by(LLMConfig.updated_at.desc())).all())


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

    cfg.name        = payload.name
    cfg.is_active   = bool(activate)

    cfg.provider    = payload.provider
    cfg.api_key     = payload.api_key
    cfg.base_url    = payload.base_url
    cfg.model       = payload.model
    cfg.max_tokens  = payload.max_tokens
    cfg.temperature = payload.temperature
    cfg.use_vision  = payload.use_vision
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
        scan_sqli=cfg.scan_sqli,
        scan_xss=cfg.scan_xss,
        updated_at=cfg.updated_at,
    )


def get_burp_rest_api_config(session: Session) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        return BurpRestApiConfigOut(**BurpRestApiConfigIn().model_dump(), updated_at=_utcnow())
    return _burp_rest_api_config_from_model(cfg)


def upsert_burp_rest_api_config(session: Session, payload: BurpRestApiConfigIn) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = BurpRestApiConfig(id=_SINGLETON_ID)

    cfg.enabled = payload.enabled
    cfg.api_url = payload.api_url
    cfg.api_key = payload.api_key
    cfg.scan_sqli = payload.scan_sqli
    cfg.scan_xss = payload.scan_xss
    cfg.updated_at = _utcnow()

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return _burp_rest_api_config_from_model(cfg)
