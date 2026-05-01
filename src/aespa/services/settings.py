"""Service layer for application settings (LLM config, etc.)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session

from aespa.models import LLMConfig
from aespa.schemas import LLMConfigIn

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
