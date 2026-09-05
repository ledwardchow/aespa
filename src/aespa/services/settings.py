"""Service layer for application settings (LLM config, etc.)."""

from __future__ import annotations

import os

from fastapi import HTTPException, Request
from sqlmodel import Session, select

from aespa.models import (
    LLMConfig,
    LLMProfile,
    LLMProviderConfig,
    TestRun,
)
from aespa.schemas import (
    LLMConfigExport,
    LLMConfigOut,
    LLMExportProfileItem,
    LLMExportProviderItem,
    LLMImportResult,
)
from aespa.services.model_capabilities import (
    documented_model_capability,
    enrich_model_options,
    validate_effort,
)
from aespa.services.resolved_llm_config import ResolvedLLMConfig
from aespa.services.settings_integrations import (
    _burp_rest_api_config_from_model as _burp_rest_api_config_from_model,
)
from aespa.services.settings_integrations import (
    _policy_from_model as _policy_from_model,
)
from aespa.services.settings_integrations import (
    get_adversarial_validator_config as get_adversarial_validator_config,
)
from aespa.services.settings_integrations import (
    get_browser_debug_config as get_browser_debug_config,
)
from aespa.services.settings_integrations import (
    get_burp_rest_api_config as get_burp_rest_api_config,
)
from aespa.services.settings_integrations import (
    get_burp_rest_api_config_model as get_burp_rest_api_config_model,
)
from aespa.services.settings_integrations import (
    get_cloudflare_access_config as get_cloudflare_access_config,
)
from aespa.services.settings_integrations import (
    get_code_execution_config as get_code_execution_config,
)
from aespa.services.settings_integrations import (
    get_component_mapper_config as get_component_mapper_config,
)
from aespa.services.settings_integrations import (
    get_crawler_config as get_crawler_config,
)
from aespa.services.settings_integrations import (
    get_global_http_header_config as get_global_http_header_config,
)
from aespa.services.settings_integrations import (
    get_reporting_debug_config as get_reporting_debug_config,
)
from aespa.services.settings_integrations import (
    get_run_scanner_policy as get_run_scanner_policy,
)
from aespa.services.settings_integrations import (
    get_scanner_policy as get_scanner_policy,
)
from aespa.services.settings_integrations import (
    get_specialist_agent_config as get_specialist_agent_config,
)
from aespa.services.settings_integrations import (
    get_upstream_proxy_config as get_upstream_proxy_config,
)
from aespa.services.settings_integrations import (
    upsert_adversarial_validator_config as upsert_adversarial_validator_config,
)
from aespa.services.settings_integrations import (
    upsert_browser_debug_config as upsert_browser_debug_config,
)
from aespa.services.settings_integrations import (
    upsert_burp_rest_api_config as upsert_burp_rest_api_config,
)
from aespa.services.settings_integrations import (
    upsert_cloudflare_access_config as upsert_cloudflare_access_config,
)
from aespa.services.settings_integrations import (
    upsert_code_execution_config as upsert_code_execution_config,
)
from aespa.services.settings_integrations import (
    upsert_component_mapper_config as upsert_component_mapper_config,
)
from aespa.services.settings_integrations import (
    upsert_crawler_config as upsert_crawler_config,
)
from aespa.services.settings_integrations import (
    upsert_global_http_header_config as upsert_global_http_header_config,
)
from aespa.services.settings_integrations import (
    upsert_reporting_debug_config as upsert_reporting_debug_config,
)
from aespa.services.settings_integrations import (
    upsert_scanner_policy as upsert_scanner_policy,
)
from aespa.services.settings_integrations import (
    upsert_specialist_agent_config as upsert_specialist_agent_config,
)
from aespa.services.settings_integrations import (
    upsert_upstream_proxy_config as upsert_upstream_proxy_config,
)
from aespa.services.settings_profiles import (
    _apply_llm_config as _apply_llm_config,
)
from aespa.services.settings_profiles import (
    _apply_scan_profile as _apply_scan_profile,
)
from aespa.services.settings_profiles import (
    _ensure_unique_llm_profile_name as _ensure_unique_llm_profile_name,
)
from aespa.services.settings_profiles import (
    _ensure_unique_scan_profile_name as _ensure_unique_scan_profile_name,
)
from aespa.services.settings_profiles import (
    activate_llm_profile as activate_llm_profile,
)
from aespa.services.settings_profiles import (
    activate_scan_profile as activate_scan_profile,
)
from aespa.services.settings_profiles import (
    create_llm_profile as create_llm_profile,
)
from aespa.services.settings_profiles import (
    create_scan_profile as create_scan_profile,
)
from aespa.services.settings_profiles import (
    delete_llm_profile as delete_llm_profile,
)
from aespa.services.settings_profiles import (
    delete_scan_profile as delete_scan_profile,
)
from aespa.services.settings_profiles import (
    get_llm_profile as get_llm_profile,
)
from aespa.services.settings_profiles import (
    get_scan_profile as get_scan_profile,
)
from aespa.services.settings_profiles import (
    list_llm_profiles as list_llm_profiles,
)
from aespa.services.settings_profiles import (
    list_scan_profiles as list_scan_profiles,
)
from aespa.services.settings_profiles import (
    llm_profile_out as llm_profile_out,
)
from aespa.services.settings_profiles import (
    update_llm_profile as update_llm_profile,
)
from aespa.services.settings_profiles import (
    update_scan_profile as update_scan_profile,
)
from aespa.services.settings_profiles import (
    upsert_llm_config as upsert_llm_config,
)
from aespa.services.settings_providers import (
    _apply_llm_provider as _apply_llm_provider,
)
from aespa.services.settings_providers import (
    _context_window_from_capability as _context_window_from_capability,
)
from aespa.services.settings_providers import (
    _ensure_unique_llm_provider_name as _ensure_unique_llm_provider_name,
)
from aespa.services.settings_providers import (
    _provider_capabilities as _provider_capabilities,
)
from aespa.services.settings_providers import (
    _provider_models as _provider_models,
)
from aespa.services.settings_providers import (
    _provider_out as _provider_out,
)
from aespa.services.settings_providers import (
    create_llm_provider as create_llm_provider,
)
from aespa.services.settings_providers import (
    delete_llm_provider as delete_llm_provider,
)
from aespa.services.settings_providers import (
    detect_context_window as detect_context_window,
)
from aespa.services.settings_providers import (
    get_llm_provider as get_llm_provider,
)
from aespa.services.settings_providers import (
    list_llm_providers as list_llm_providers,
)
from aespa.services.settings_providers import (
    update_llm_provider as update_llm_provider,
)
from aespa.services.settings_values import (
    _SINGLETON_ID as _SINGLETON_ID,
)

# Compatibility exports for existing API and service callers.
from aespa.services.settings_values import (
    AGENT_ROLES as AGENT_ROLES,
)
from aespa.services.settings_values import (
    CONTEXT_WINDOW_FALLBACK as CONTEXT_WINDOW_FALLBACK,
)
from aespa.services.settings_values import (
    _json_dumps as _json_dumps,
)
from aespa.services.settings_values import (
    _json_loads as _json_loads,
)
from aespa.services.settings_values import (
    _utcnow as _utcnow,
)


def resolve_llm_config(
    session: Session, cfg: LLMConfig | ResolvedLLMConfig
) -> ResolvedLLMConfig:
    """Read provider settings without changing the saved profile object."""
    if isinstance(cfg, ResolvedLLMConfig):
        return cfg
    resolved = ResolvedLLMConfig.model_validate(cfg)
    provider = (
        session.get(LLMProviderConfig, cfg.provider_id)
        if cfg.provider_id is not None
        else None
    )
    if provider is None:
        return resolved
    return resolved.model_copy(
        update={
            "provider": provider.api_format,
            "api_key": provider.api_key,
            "base_url": provider.base_url,
            "username": provider.username,
            "project_id": provider.project_id,
        }
    )


def llm_profile_out_model(
    session: Session, cfg: LLMConfig | ResolvedLLMConfig
) -> LLMConfigOut:
    resolved = resolve_llm_config(session, cfg)
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
        max_context_tokens=resolved.max_context_tokens,
        context_limit_source=resolved.context_limit_source,
        temperature=resolved.temperature,
        use_vision=resolved.use_vision,
        force_tool_choice=resolved.force_tool_choice,
        reasoning_effort=resolved.reasoning_effort,
        updated_at=resolved.updated_at,
    )


def get_llm_config(session: Session) -> ResolvedLLMConfig | None:
    cfg = session.exec(select(LLMConfig).where(LLMConfig.is_active == True)).first()  # noqa: E712
    if cfg is None:
        return None
    return resolve_llm_config(session, cfg)


def get_active_scan_profile(session: Session) -> LLMProfile | None:
    return session.exec(select(LLMProfile).where(LLMProfile.is_active == True)).first()  # noqa: E712


def _model_for_profile_role(
    session: Session, prof: LLMProfile, role: str | None
) -> ResolvedLLMConfig | None:
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
    return resolve_llm_config(session, cfg) if cfg is not None else None


def get_llm_config_for_role(
    session: Session, run: "TestRun", role: str | None = None
) -> ResolvedLLMConfig | None:
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
            return resolve_llm_config(session, cfg)
    # 3. Globally active profile.
    prof = get_active_scan_profile(session)
    if prof is not None:
        cfg = _model_for_profile_role(session, prof, role)
        if cfg is not None:
            return cfg
    # 4. Globally active model.
    return get_llm_config(session)


def get_llm_config_for_run(
    session: Session, run: "TestRun"
) -> ResolvedLLMConfig | None:
    """Role-agnostic config for a run (resolves to the profile's default model)."""
    return get_llm_config_for_role(session, run, None)


async def discover_models_for_format(
    api_format: str,
    api_key: str | None = None,
    base_url: str | None = None,
    username: str | None = None,
) -> list[str]:
    options = await discover_model_options_for_format(
        api_format=api_format,
        api_key=api_key,
        base_url=base_url,
        username=username,
    )
    return list(options["models"])


async def discover_model_options_for_format(
    api_format: str,
    api_key: str | None = None,
    base_url: str | None = None,
    username: str | None = None,
) -> dict[str, object]:
    """Discover model names and per-model reasoning capability metadata."""
    native: dict[str, object] = {}
    discovered: list[str] = []
    if api_format == "factory_droid":
        from aespa.services import droid_provider

        fn = getattr(droid_provider, "discover_model_options", None)
        if fn:
            raw = await fn()
            discovered = [item["id"] for item in raw if item.get("id")]
            native = {item["id"]: item for item in raw if item.get("id")}
        else:
            discovered = await droid_provider.discover_models()
    elif api_format == "openai_codex":
        from aespa.services import codex_provider

        fn = getattr(codex_provider, "discover_model_options", None)
        if fn:
            raw = await fn()
            discovered = [item["id"] for item in raw if item.get("id")]
            native = {item["id"]: item for item in raw if item.get("id")}
        else:
            discovered = await codex_provider.discover_models()
    elif api_format == "google_antigravity":
        from aespa.services import antigravity_provider

        raw = await antigravity_provider.discover_model_options()
        discovered = [item["id"] for item in raw if item.get("id")]
        native = {item["id"]: item for item in raw if item.get("id")}
    elif api_format == "github_copilot":
        from aespa.services import copilot_provider

        fn = getattr(copilot_provider, "discover_model_options", None)
        if fn:
            raw = await fn()
            discovered = [item["id"] for item in raw if item.get("id")]
            native = {item["id"]: item for item in raw if item.get("id")}
        else:
            discovered = await copilot_provider.discover_models()
    elif api_format == "openrouter":
        from aespa.services import openrouter_provider

        key = api_key or os.getenv("OPENROUTER_API_KEY")
        raw = await openrouter_provider.discover_model_options(
            api_key=key, base_url=base_url
        )
        discovered = [item["id"] for item in raw if item.get("id")]
        native = {item["id"]: item for item in raw if item.get("id")}
    elif api_format == "openai":
        from aespa.services import model_discovery

        key = api_key or os.getenv("OPENAI_API_KEY")
        raw = await model_discovery.discover_openai_model_options(
            api_key=key, base_url=base_url
        )
        discovered = [item["id"] for item in raw]
        native = {item["id"]: item for item in raw}
    elif api_format == "openai_compatible":
        from aespa.services import model_discovery

        url = base_url or "http://localhost:1234/v1"
        raw = await model_discovery.discover_openai_model_options(
            api_key=api_key, base_url=url
        )
        discovered = [item["id"] for item in raw]
        native = {item["id"]: item for item in raw}
    elif api_format == "anthropic":
        from aespa.services import model_discovery

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        raw = await model_discovery.discover_anthropic_model_options(
            api_key=key, base_url=base_url
        )
        discovered = [item["id"] for item in raw]
        native = {item["id"]: item for item in raw}
    elif api_format == "google":
        from aespa.services import model_discovery

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        raw = await model_discovery.discover_google_model_options(
            api_key=key, base_url=base_url
        )
        discovered = [item["id"] for item in raw]
        native = {item["id"]: item for item in raw}
        for model in discovered:
            capability = documented_model_capability("google", model)
            if capability is not None:
                native[model] = native.get(model) or capability
    elif api_format in {"azure_openai", "azure_foundry", "azure_foundry_openai"}:
        from aespa.services import model_discovery

        key = api_key or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_API_KEY")
        raw = await model_discovery.discover_azure_openai_model_options(
            api_key=key, base_url=base_url
        )
        discovered = [item["id"] for item in raw]
        native = {item["id"]: item for item in raw}
    elif api_format == "azure_foundry_anthropic":
        from aespa.services import model_discovery

        key = api_key or os.getenv("AZURE_API_KEY")
        raw = await model_discovery.discover_anthropic_model_options(
            api_key=key, base_url=base_url
        )
        discovered = [item["id"] for item in raw]
        native = {item["id"]: item for item in raw}
    elif api_format == "bedrock":
        from aespa.services import model_discovery

        discovered = await model_discovery.discover_bedrock_models(region_name=base_url)
        native = {
            model: capability
            for model in discovered
            if (capability := documented_model_capability("bedrock", model)) is not None
        }
    elif api_format == "bedrock_mantle":
        from aespa.services import model_discovery

        raw = await model_discovery.discover_bedrock_mantle_model_options(
            api_key=api_key,
            base_url=base_url,
        )
        discovered = [item["id"] for item in raw]
        native = {item["id"]: item for item in raw}
    discovered = sorted(dict.fromkeys(discovered), key=str.casefold)
    for model in discovered:
        capability = documented_model_capability(api_format, model)
        existing = native.get(model)
        has_native_fields = isinstance(existing, dict) and any(
            key in existing
            for key in (
                "supported_efforts",
                "supported_reasoning_efforts",
                "supportedReasoningEfforts",
                "reasoning",
            )
        )
        if capability is not None and not has_native_fields:
            native[model] = capability
    capabilities = await enrich_model_options(api_format, discovered, native)
    return {"models": discovered, "capabilities": capabilities}


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
            model_capabilities=_provider_capabilities(p),
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
            max_context_tokens=c.max_context_tokens,
            temperature=c.temperature,
            reasoning_effort=c.reasoning_effort,
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
        provider.model_capabilities_json = _json_dumps(item.model_capabilities)
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
        if item.max_context_tokens is None:
            cfg.max_context_tokens, cfg.context_limit_source = detect_context_window(
                provider, item.model
            )
        else:
            cfg.max_context_tokens = item.max_context_tokens
            cfg.context_limit_source = "manual"
        if cfg.max_context_tokens <= item.max_tokens + 1024:
            raise HTTPException(
                status_code=422,
                detail="The model context window must leave at least 1024 tokens for input",
            )
        cfg.temperature = item.temperature
        try:
            cfg.reasoning_effort = validate_effort(
                _provider_capabilities(provider).get(item.model),
                item.reasoning_effort,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
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
