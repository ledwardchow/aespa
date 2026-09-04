"""Resolved settings must remain independent of stored ORM rows."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlmodel import Session

from aespa.models import LLMConfig, LLMProviderConfig
from aespa.schemas import LLMConfigIn
from aespa.services import settings
from aespa.services.resolved_llm_config import ResolvedLLMConfig


def test_resolving_and_serializing_does_not_change_saved_profile(db_session: Session):
    provider = LLMProviderConfig(
        name="Provider",
        api_format="openai",
        api_key="provider-key",
        base_url="https://provider.example/v1",
        username="provider-user",
        project_id="provider-project",
    )
    db_session.add(provider)
    db_session.flush()
    profile = LLMConfig(
        provider_id=provider.id,
        provider="anthropic",
        api_key="stored-key",
        base_url="https://stored.example",
        username="stored-user",
        project_id="stored-project",
        model="test-model",
        is_active=True,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    before = profile.model_dump()

    resolved = settings.get_llm_config(db_session)
    response = settings.llm_profile_out_model(db_session, profile)

    assert isinstance(resolved, ResolvedLLMConfig)
    assert resolved.provider == "openai"
    assert resolved.api_key == "provider-key"
    assert resolved.base_url == "https://provider.example/v1"
    assert resolved.username == "provider-user"
    assert resolved.project_id == "provider-project"
    assert profile.model_dump() == before
    assert profile not in db_session.dirty
    assert response.api_key is None
    assert response.has_api_key is True
    assert response.provider == "openai"
    assert "provider-key" not in repr(resolved)

    profile.name = "Renamed"
    db_session.commit()
    db_session.refresh(profile)
    assert profile.api_key == "stored-key"
    assert profile.base_url == "https://stored.example"
    assert resolved.name == "Default"
    db_session.expunge_all()
    assert resolved.api_key == "provider-key"
    assert resolved.model == "test-model"


@pytest.mark.parametrize("provider_id", [None, 999999])
def test_missing_provider_returns_independent_legacy_values(db_session, provider_id):
    profile = LLMConfig(provider_id=provider_id, api_key="legacy-key", is_active=True)
    db_session.add(profile)
    db_session.commit()
    run = SimpleNamespace(llm_profile_id=None, llm_config_id=profile.id)

    resolved = settings.get_llm_config_for_run(db_session, run)

    assert isinstance(resolved, ResolvedLLMConfig)
    assert resolved.model_dump() == profile.model_dump()
    profile.model = "changed-after-resolution"
    assert resolved.model != profile.model


def test_upsert_updates_stored_profile_after_reading_resolved_config(db_session):
    provider = LLMProviderConfig(
        name="Provider", api_format="openai", models_json='["test-model"]'
    )
    db_session.add(provider)
    db_session.flush()
    profile = LLMConfig(provider_id=provider.id, model="test-model", is_active=True)
    db_session.add(profile)
    db_session.commit()
    original_id = profile.id
    snapshot = settings.get_llm_config(db_session)

    updated = settings.upsert_llm_config(
        db_session,
        LLMConfigIn(
            name="Updated", provider_id=provider.id, model="test-model", max_tokens=100
        ),
    )

    assert isinstance(updated, LLMConfig)
    assert updated is profile
    assert updated.id == original_id
    assert db_session.get(LLMConfig, original_id).name == "Updated"
    assert snapshot.name == "Default"
