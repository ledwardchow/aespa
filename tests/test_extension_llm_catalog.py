from __future__ import annotations

from dataclasses import replace

import pytest

from aespa.extensions.runtime import (
    ExtensionManager,
    ExtensionRecord,
    ExtensionRegistry,
)
from aespa.models import LLMProfile, TestRun
from aespa.services import settings as settings_service
from aespa.services.extension_llm_catalog import (
    ExtensionLLMModel,
    ExtensionLLMProfile,
    ExtensionLLMProvider,
    ExtensionLLMSnapshot,
    snapshot_out,
    validate_snapshot,
)


class Catalog:
    def __init__(self, snapshot):
        self.value = snapshot

    def snapshot(self):
        return self.value


def sample_snapshot():
    return ExtensionLLMSnapshot(
        providers=[ExtensionLLMProvider("aws", "AWS", "bedrock", ["anthropic.claude"])],
        models=[ExtensionLLMModel("claude", "Claude", "aws", "anthropic.claude")],
        profiles=[
            ExtensionLLMProfile("review", "Review", "claude", {"test_lead": "claude"})
        ],
    )


def test_extension_catalog_is_separate_and_resolves_role_model():
    manager = ExtensionManager()
    manager._loaded = True
    manager.extensions["example.llm"] = ExtensionRecord(
        id="example.llm",
        name="Example",
        version="1",
        aespa_api="1",
        capabilities=["llm.catalog"],
        source="test",
        data_namespace="example_llm",
    )
    registry = ExtensionRegistry(manager, "example.llm")
    registry.register_llm_catalog(Catalog(sample_snapshot()))

    items = manager.llm_catalog_items()
    assert items["providers"][0]["id"] == "extension:example.llm:provider:aws"
    assert items["providers"][0]["has_api_key"] is False
    assert items["profiles"][0]["extension_name"] == "Example"
    resolved = registry.resolve_llm_profile("review", "test_lead")
    assert resolved.provider == "bedrock"
    assert resolved.model == "anthropic.claude"
    assert resolved.api_key is None
    assert resolved.id is None


@pytest.mark.parametrize(
    "format", ["openai", "anthropic", "openrouter", "openai_compatible", "azure_openai"]
)
def test_extension_catalog_rejects_key_based_providers(format):
    snapshot = sample_snapshot()
    snapshot.providers[0] = replace(snapshot.providers[0], api_format=format)
    with pytest.raises(ValueError, match="cannot be stored"):
        validate_snapshot("example.llm", snapshot)


def test_extension_catalog_rejects_bad_references_and_duplicate_keys():
    snapshot = sample_snapshot()
    snapshot.profiles[0] = replace(snapshot.profiles[0], default_model_key="missing")
    with pytest.raises(ValueError, match="unknown model"):
        snapshot_out("example.llm", "Example", snapshot)
    snapshot = sample_snapshot()
    snapshot.models.append(snapshot.models[0])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_snapshot("example.llm", snapshot)


def test_extension_catalog_requires_declared_capability_and_storage_namespace():
    manager = ExtensionManager()
    manager.extensions["example.llm"] = ExtensionRecord(
        id="example.llm",
        name="Example",
        version="1",
        aespa_api="1",
        capabilities=[],
        source="test",
    )
    registry = ExtensionRegistry(manager, "example.llm")
    with pytest.raises(ValueError, match="llm.catalog"):
        registry.register_llm_catalog(Catalog(sample_snapshot()))
    manager.extensions["example.llm"].capabilities.append("llm.catalog")
    with pytest.raises(ValueError, match="data_namespace"):
        registry.register_llm_catalog(Catalog(sample_snapshot()))


def test_extension_catalog_rejects_credentials_in_base_url():
    snapshot = sample_snapshot()
    snapshot.providers[0] = replace(
        snapshot.providers[0], base_url="https://user:secret@example.test/?key=secret"
    )
    with pytest.raises(ValueError, match="cannot contain credentials"):
        validate_snapshot("example.llm", snapshot)


def test_extension_catalog_api_lists_registered_items(client, monkeypatch):
    manager = ExtensionManager()
    manager._loaded = True
    manager.extensions["example.llm"] = ExtensionRecord(
        id="example.llm",
        name="Example",
        version="1",
        aespa_api="1",
        capabilities=["llm.catalog"],
        source="test",
        data_namespace="example_llm",
    )
    catalog = Catalog(sample_snapshot())
    ExtensionRegistry(manager, "example.llm").register_llm_catalog(catalog)
    monkeypatch.setattr("aespa.extensions.get_extension_manager", lambda: manager)
    response = client.get("/api/settings/llm/extension-catalog")
    assert response.status_code == 200
    assert response.json()["profiles"][0]["default_model_name"] == "Claude"
    profiles = client.get("/api/settings/llm/profiles").json()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Review"
    assert profiles[0]["extension_id"] == "example.llm"
    assert isinstance(profiles[0]["id"], int)
    site = client.post(
        "/api/sites",
        json={
            "name": "Target",
            "base_url": "https://target.local",
            "requires_auth": False,
        },
    ).json()
    run = client.post(
        f"/api/sites/{site['id']}/test-runs",
        json={"name": "Extension profile scan", "llm_profile_id": profiles[0]["id"]},
    )
    assert run.status_code == 201
    assert run.json()["llm_profile_id"] == profiles[0]["id"]
    manager.llm_catalogs.clear()
    unavailable = client.post(
        f"/api/sites/{site['id']}/test-runs",
        json={"name": "Unavailable profile", "llm_profile_id": profiles[0]["id"]},
    )
    assert unavailable.status_code == 409
    assert client.get("/api/settings/llm/profiles").json() == []
    manager.llm_catalogs["example.llm"] = catalog
    restored = client.get("/api/settings/llm/profiles").json()
    assert restored[0]["id"] == profiles[0]["id"]
    assert (
        client.delete(f"/api/settings/llm/profiles/{restored[0]['id']}").status_code
        == 409
    )


def test_extension_profile_resolves_for_core_run_and_default(db_session, monkeypatch):
    manager = ExtensionManager()
    manager._loaded = True
    manager.extensions["example.llm"] = ExtensionRecord(
        id="example.llm",
        name="Example",
        version="1",
        aespa_api="1",
        capabilities=["llm.catalog"],
        source="test",
        data_namespace="example_llm",
    )
    catalog = Catalog(sample_snapshot())
    ExtensionRegistry(manager, "example.llm").register_llm_catalog(catalog)
    monkeypatch.setattr("aespa.extensions.get_extension_manager", lambda: manager)
    from aespa.services import settings_profiles

    profile = settings_profiles.list_scan_profiles(db_session)[0]
    assert profile.extension_ref == "extension:example.llm:profile:review"
    run = TestRun(site_id=1, name="Scan", llm_profile_id=profile.id)
    resolved = settings_service.get_llm_config_for_role(db_session, run, "test_lead")
    assert resolved.model == "anthropic.claude"
    updated = sample_snapshot()
    updated.providers[0] = replace(updated.providers[0], models=["anthropic.claude-v2"])
    updated.models[0] = replace(updated.models[0], model="anthropic.claude-v2")
    catalog.value = updated
    assert (
        settings_service.get_llm_config_for_role(db_session, run, "test_lead").model
        == "anthropic.claude-v2"
    )
    settings_profiles.activate_scan_profile(db_session, profile.id)
    assert (
        settings_service.get_llm_config_for_role(
            db_session, TestRun(site_id=1, name="Default"), "validator"
        ).model
        == "anthropic.claude-v2"
    )

    manager.llm_catalogs.clear()
    with pytest.raises(RuntimeError, match="unavailable"):
        settings_service.get_llm_config_for_role(db_session, run, "test_lead")
    assert db_session.get(LLMProfile, profile.id).extension_ref
