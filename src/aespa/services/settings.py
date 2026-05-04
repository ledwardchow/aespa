"""Service layer for application settings (LLM config, etc.)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session

from aespa.models import LLMConfig, ScannerPolicy, TestRun
from aespa.schemas import LLMConfigIn, RunScannerPolicyOut, ScannerPolicyBase, ScannerPolicyIn, ScannerPolicyOut

_SINGLETON_ID = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_llm_config(session: Session) -> LLMConfig | None:
    return session.get(LLMConfig, _SINGLETON_ID)


def upsert_llm_config(session: Session, payload: LLMConfigIn) -> LLMConfig:
    cfg = session.get(LLMConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = LLMConfig(id=_SINGLETON_ID)

    cfg.provider    = payload.provider
    cfg.api_key     = payload.api_key
    cfg.base_url    = payload.base_url
    cfg.model       = payload.model
    cfg.max_tokens  = payload.max_tokens
    cfg.temperature = payload.temperature
    cfg.use_vision  = payload.use_vision
    cfg.updated_at  = _utcnow()

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg


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


def scanner_policy_snapshot(policy: ScannerPolicyBase) -> str:
    return policy.model_dump_json()


def get_run_scanner_policy(session: Session, run: TestRun) -> RunScannerPolicyOut:
    snapshot = _json_loads(run.scanner_policy_json, {})
    if snapshot:
        policy = ScannerPolicyIn(**snapshot)
        return RunScannerPolicyOut(**policy.model_dump(), source="run_snapshot", updated_at=None)
    policy = get_scanner_policy(session)
    return RunScannerPolicyOut(**policy.model_dump(exclude={"updated_at"}), source="global_default", updated_at=policy.updated_at)


def update_run_scanner_policy(session: Session, run: TestRun, payload: ScannerPolicyIn) -> RunScannerPolicyOut:
    run.scan_mode = payload.scan_mode
    run.scanner_policy_json = scanner_policy_snapshot(payload)
    session.add(run)
    session.commit()
    session.refresh(run)
    return get_run_scanner_policy(session, run)
