"""Settings profiles."""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from aespa.models import (
    ApiTestRun,
    AssessmentCampaign,
    LLMConfig,
    LLMProfile,
    SastRun,
    TestRun,
)
from aespa.schemas import (
    LLMConfigIn,
    LLMProfileIn,
    LLMProfileOut,
)
from aespa.services.model_capabilities import (
    validate_effort,
)
from aespa.services.settings_providers import (
    _provider_capabilities,
    _provider_models,
    detect_context_window,
    get_llm_provider,
)
from aespa.services.settings_values import (
    AGENT_ROLES,
    _json_dumps,
    _json_loads,
    _utcnow,
)


def upsert_llm_config(session: Session, payload: LLMConfigIn) -> LLMConfig:
    cfg = session.exec(select(LLMConfig).where(LLMConfig.is_active == True)).first()  # noqa: E712
    if cfg is None:
        cfg = LLMConfig(is_active=True)

    return _apply_llm_config(session, cfg, payload, activate=True)


def list_llm_profiles(session: Session) -> list[LLMConfig]:
    return list(
        session.exec(select(LLMConfig).order_by(LLMConfig.updated_at.desc())).all()
    )


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

    referencing_profiles = []
    for prof in session.exec(select(LLMProfile)).all():
        role_models = _json_loads(prof.role_models_json, {})
        if prof.default_model_id == profile_id or any(
            str(model_id) == str(profile_id) for model_id in role_models.values()
        ):
            referencing_profiles.append(prof.name)
    if referencing_profiles:
        names = ", ".join(sorted(referencing_profiles, key=str.casefold))
        raise HTTPException(
            status_code=409,
            detail=(
                f'Cannot delete model "{cfg.name}" because it is used by '
                f"scan profile(s): {names}. Update those profiles first."
            ),
        )

    # Determine replacement model if one exists
    replacement_model = session.exec(
        select(LLMConfig)
        .where(LLMConfig.id != profile_id)
        .order_by(LLMConfig.is_active.desc(), LLMConfig.updated_at.desc())
    ).first()
    replacement_model_id = (
        replacement_model.id if replacement_model is not None else None
    )

    # A model can be selected explicitly on past runs. Clear the reference before
    # deleting the model so those records fall back to the active configuration.
    for run_type in (TestRun, ApiTestRun, SastRun, AssessmentCampaign):
        for run in session.exec(
            select(run_type).where(run_type.llm_config_id == profile_id)
        ).all():
            run.llm_config_id = None
            session.add(run)

    session.delete(cfg)
    session.commit()
    if was_active and replacement_model_id is not None:
        activate_llm_profile(session, replacement_model_id)


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

    # A profile can be selected explicitly on any run type (or campaign). The
    # reference is optional, so clear it before deleting the profile and let
    # those records fall back to the globally active profile.
    for run_type in (TestRun, ApiTestRun, SastRun, AssessmentCampaign):
        for run in session.exec(
            select(run_type).where(run_type.llm_profile_id == profile_id)
        ).all():
            run.llm_profile_id = None
            session.add(run)

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
    provider = get_llm_provider(session, payload.provider_id)
    if payload.model not in _provider_models(provider):
        raise HTTPException(
            status_code=422, detail="Model is not configured for the selected provider"
        )

    name = (payload.name or "").strip()
    if not name:
        name = f"{provider.name}/{payload.model}"

    _ensure_unique_llm_profile_name(session, name, cfg.id)

    cfg.name = name
    cfg.is_active = bool(activate)

    cfg.provider_id = payload.provider_id
    cfg.provider = provider.api_format
    cfg.api_key = provider.api_key
    cfg.base_url = provider.base_url
    cfg.username = provider.username
    cfg.project_id = provider.project_id
    cfg.model = payload.model
    cfg.max_tokens = payload.max_tokens
    if payload.max_context_tokens is None:
        cfg.max_context_tokens, cfg.context_limit_source = detect_context_window(
            provider, payload.model
        )
    else:
        cfg.max_context_tokens = payload.max_context_tokens
        cfg.context_limit_source = "manual"
    if cfg.max_context_tokens <= payload.max_tokens + 1024:
        raise HTTPException(
            status_code=422,
            detail="The model context window must leave at least 1024 tokens for input",
        )
    cfg.temperature = payload.temperature
    cfg.use_vision = payload.use_vision
    cfg.force_tool_choice = payload.force_tool_choice
    capability = _provider_capabilities(provider).get(payload.model)
    try:
        cfg.reasoning_effort = validate_effort(capability, payload.reasoning_effort)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
