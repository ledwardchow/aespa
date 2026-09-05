"""Settings providers."""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from aespa.models import (
    LLMConfig,
    LLMProviderConfig,
)
from aespa.schemas import (
    LLMProviderConfigIn,
    LLMProviderConfigOut,
)
from aespa.services.settings_values import (
    CONTEXT_WINDOW_FALLBACK,
    _json_dumps,
    _json_loads,
    _utcnow,
)


def _provider_models(provider: LLMProviderConfig) -> list[str]:
    models = _json_loads(provider.models_json, [])
    return [m for m in models if isinstance(m, str) and m.strip()]


def _provider_capabilities(provider: LLMProviderConfig) -> dict[str, dict]:
    value = _json_loads(getattr(provider, "model_capabilities_json", "{}"), {})
    return value if isinstance(value, dict) else {}


def _context_window_from_capability(value: object) -> int | None:
    if not isinstance(value, dict):
        return None
    for key in (
        "context_window_tokens",
        "context_length",
        "contextWindow",
        "context_window",
        "max_input_tokens",
        "inputTokenLimit",
        "input_token_limit",
    ):
        candidate = value.get(key)
        try:
            candidate = int(candidate)
        except (TypeError, ValueError):
            continue
        if candidate >= 1024:
            return candidate
    return None


def detect_context_window(provider: LLMProviderConfig, model: str) -> tuple[int, str]:
    """Resolve a model context window from exact persisted provider metadata."""
    capability = _provider_capabilities(provider).get(model)
    if isinstance(capability, dict) and capability.get("source") == "openrouter":
        matched = str(capability.get("matched_model") or "").casefold()
        requested = model.casefold()
        if matched and matched != requested and matched.rsplit("/", 1)[-1] != requested:
            capability = None
    detected = _context_window_from_capability(capability)
    if detected is not None:
        source = str(capability.get("context_window_source") or "provider")
        return detected, source
    # These are deliberately conservative defaults for models whose provider
    # endpoint does not expose a context value. The UI marks them as fallback.
    return CONTEXT_WINDOW_FALLBACK, "fallback"


def _provider_out(provider: LLMProviderConfig) -> LLMProviderConfigOut:
    return LLMProviderConfigOut(
        id=provider.id,
        name=provider.name,
        api_format=provider.api_format,
        base_url=provider.base_url,
        username=provider.username,
        project_id=provider.project_id,
        models=_provider_models(provider),
        model_capabilities=_provider_capabilities(provider),
        has_api_key=bool(provider.api_key and provider.api_key.strip()),
        api_key=None,
        max_tpm=provider.max_tpm,
        max_rpm=provider.max_rpm,
        updated_at=provider.updated_at,
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
    if payload.api_format in {"factory_droid", "openai_codex"}:
        provider.api_key = None
    elif payload.api_key is not None:
        key_str = payload.api_key.strip()
        provider.api_key = key_str if key_str else None
    provider.base_url = (
        None
        if payload.api_format in {"factory_droid", "openai_codex"}
        else payload.base_url
    )
    username = (payload.username or "").strip()
    provider.username = (
        username or None if payload.api_format == "github_copilot" else None
    )
    provider.project_id = (
        None
        if payload.api_format in {"factory_droid", "openai_codex"}
        else payload.project_id
    )
    provider.models_json = _json_dumps(payload.models)
    provider.model_capabilities_json = _json_dumps(
        {
            model: payload.model_capabilities.get(model, {})
            for model in payload.models
            if model in payload.model_capabilities
        }
    )
    provider.max_tpm = payload.max_tpm
    provider.max_rpm = payload.max_rpm
    provider.updated_at = _utcnow()
    session.add(provider)
    session.commit()
    session.refresh(provider)
    return _provider_out(provider)


def _ensure_unique_llm_provider_name(
    session: Session, name: str, current_id: int | None
) -> None:
    normalized = name.strip().casefold()
    for provider in session.exec(select(LLMProviderConfig)).all():
        if provider.id != current_id and provider.name.strip().casefold() == normalized:
            raise HTTPException(
                status_code=409, detail="An LLM provider with that name already exists"
            )
