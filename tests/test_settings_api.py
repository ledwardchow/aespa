from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


def test_get_llm_config_initially_null(client: TestClient):
    r = client.get("/api/settings/llm")
    assert r.status_code == 200
    assert r.json() is None


def test_get_default_models(client: TestClient):
    r = client.get("/api/settings/llm/models")
    assert r.status_code == 200
    data = r.json()
    assert "anthropic" in data
    assert "openai" in data
    assert "openai_compatible" in data
    assert "openrouter" in data
    assert "bedrock" in data
    assert "azure_foundry_openai" in data
    assert "azure_foundry_anthropic" in data
    assert isinstance(data["anthropic"], list)
    assert isinstance(data["openrouter"], list)
    assert isinstance(data["bedrock"], list)
    assert data["bedrock"][:2] == [
        "global.anthropic.claude-sonnet-4-6",
        "global.anthropic.claude-opus-4-7",
    ]


def test_burp_rest_api_config_round_trip(client: TestClient):
    r = client.get("/api/settings/burp-rest-api")
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert r.json()["api_url"] == "http://127.0.0.1:1337"
    assert r.json()["scan_configuration_name"] == "Audit checks - all except time-based detection methods"
    assert r.json()["scan_sqli"] is True
    assert r.json()["scan_xss"] is True
    assert r.json()["scan_command_injection"] is True
    assert r.json()["scan_path_traversal"] is True
    assert r.json()["scan_ssrf"] is True
    assert r.json()["scan_xxe"] is True
    assert r.json()["scan_ssti"] is True

    payload = {
        "enabled": True,
        "api_url": "http://127.0.0.1:1337",
        "api_key": None,
        "scan_configuration_name": "Fast audit",
        "scan_sqli": False,
        "scan_xss": True,
        "scan_command_injection": False,
        "scan_path_traversal": True,
        "scan_ssrf": False,
        "scan_xxe": True,
        "scan_ssti": True,
    }
    r = client.put("/api/settings/burp-rest-api", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    assert data["api_url"] == "http://127.0.0.1:1337"
    assert data["scan_configuration_name"] == "Fast audit"
    assert data["scan_sqli"] is False
    assert data["scan_xss"] is True
    assert data["scan_command_injection"] is False
    assert data["scan_path_traversal"] is True
    assert data["scan_ssrf"] is False
    assert data["scan_xxe"] is True
    assert data["scan_ssti"] is True


def _make_provider(client: TestClient, **overrides):
    payload = {
        "name": "Local OpenAI",
        "api_format": "openai",
        "base_url": "http://localhost:1234/v1/",
        "models": ["llama-3", "gpt-4o"],
        "api_key": None,
    }
    payload.update(overrides)
    return client.post("/api/settings/llm/providers", json=payload)


def _make_profile(client: TestClient, provider_id: int, **overrides):
    payload = {
        "name": "Default",
        "provider_id": provider_id,
        "model": "llama-3",
        "max_tokens": 4096,
        "temperature": 0.0,
        "use_vision": False,
    }
    payload.update(overrides)
    return client.post("/api/settings/llm/profiles", json=payload)


def test_create_provider_and_profile(client: TestClient):
    provider_r = _make_provider(client)
    assert provider_r.status_code == 200
    provider = provider_r.json()
    assert provider["api_format"] == "openai"
    assert provider["base_url"] == "http://localhost:1234/v1"
    assert provider["models"] == ["llama-3", "gpt-4o"]

    profile_r = _make_profile(client, provider["id"], temperature=0.5)
    assert profile_r.status_code == 200
    profile = profile_r.json()
    assert profile["provider_id"] == provider["id"]
    assert profile["provider_name"] == "Local OpenAI"
    assert profile["provider"] == "openai"
    assert profile["base_url"] == "http://localhost:1234/v1"
    assert profile["model"] == "llama-3"
    assert profile["temperature"] == 0.5

    active = client.get("/api/settings/llm").json()
    assert active["api_key"] is None
    assert active["provider"] == "openai"


def test_create_profile_with_optional_temperature(client: TestClient):
    provider_r = _make_provider(client)
    assert provider_r.status_code == 200
    provider = provider_r.json()

    profile_r = _make_profile(client, provider["id"], name="OptionalTempProfile", temperature=None)
    assert profile_r.status_code == 200
    profile = profile_r.json()
    assert profile["temperature"] is None

    client.post(f"/api/settings/llm/profiles/{profile['id']}/activate")
    active = client.get("/api/settings/llm").json()
    assert active["temperature"] is None


def test_create_bedrock_provider_with_blank_api_key(client: TestClient):
    provider_r = _make_provider(
        client,
        name="AWS Bedrock",
        api_format="bedrock",
        base_url=None,
        models=["global.anthropic.claude-sonnet-4-6"],
        api_key=None,
    )
    assert provider_r.status_code == 200
    provider = provider_r.json()
    assert provider["api_format"] == "bedrock"
    assert provider["api_key"] is None
    assert provider["base_url"] is None

    profile_r = _make_profile(
        client,
        provider["id"],
        model="global.anthropic.claude-sonnet-4-6",
    )
    assert profile_r.status_code == 200
    active = client.get("/api/settings/llm").json()
    assert active["provider"] == "bedrock"
    assert active["api_key"] is None
    assert active["base_url"] is None


def test_legacy_provider_formats_are_supported(client: TestClient):
    cases = [
        ("openai_compatible", "llama-3"),
        ("openrouter", "openrouter/owl-alpha"),
        ("google", "gemini-2.5-flash-preview-04-17"),
        ("azure_openai", "gpt-4o"),
        ("azure_foundry_openai", "gpt-4o"),
        ("azure_foundry_anthropic", "claude-sonnet-4-5"),
    ]
    for api_format, model in cases:
        provider_r = _make_provider(
            client,
            name=f"{api_format} provider",
            api_format=api_format,
            base_url="https://example.test/v1",
            models=[model],
            api_key="test-key",
        )
        assert provider_r.status_code == 200
        provider = provider_r.json()
        assert provider["api_format"] == api_format

        profile_r = _make_profile(
            client,
            provider["id"],
            name=f"{api_format} profile",
            model=model,
        )
        assert profile_r.status_code == 200
        assert profile_r.json()["provider"] == api_format


def test_provider_update_changes_runtime_profile_connection(client: TestClient):
    provider = _make_provider(client, api_key="sk-1").json()
    _make_profile(client, provider["id"])

    r = client.put(f"/api/settings/llm/providers/{provider['id']}", json={
        "name": "Local OpenAI",
        "api_format": "openai",
        "base_url": "http://localhost:11434/v1",
        "models": ["llama-3", "gpt-4o"],
        "api_key": "sk-2",
    })
    assert r.status_code == 200

    active = client.get("/api/settings/llm").json()
    assert active["api_key"] == "sk-2"
    assert active["base_url"] == "http://localhost:11434/v1"


def test_run_llm_config_resolves_provider_fields_on_session_instance():
    from aespa import models as _models  # noqa: F401
    from aespa.models import LLMConfig, LLMProviderConfig, Site, TestRun
    from aespa.services import settings as settings_service

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            provider = LLMProviderConfig(
                name="Azure Claude",
                api_format="azure_foundry_anthropic",
                api_key="provider-key",
                base_url="https://example.services.ai.azure.com/anthropic/v1",
                models_json='["claude-sonnet-4-5"]',
            )
            profile = LLMConfig(
                name="Claude profile",
                is_active=True,
                provider_id=1,
                model="claude-sonnet-4-5",
                api_key=None,
                base_url=None,
            )
            site = Site(name="Target", base_url="https://target.local")
            session.add(provider)
            session.add(profile)
            session.add(site)
            session.commit()
            session.refresh(site)
            run = TestRun(site_id=site.id, name="Run", llm_config_id=profile.id)
            session.add(run)
            session.commit()
            session.refresh(run)

            cfg = settings_service.get_llm_config_for_run(session, run)

            assert inspect(cfg).session is session
            assert session.is_modified(cfg) is False
            assert cfg.provider == "azure_foundry_anthropic"
            assert cfg.api_key == "provider-key"
            assert cfg.base_url == "https://example.services.ai.azure.com/anthropic/v1"

            settings_service.get_run_scanner_policy(session, run)
            assert session.is_modified(cfg) is False
            session.expunge(cfg)
            assert cfg.api_key == "provider-key"

        with Session(engine) as session:
            persisted = session.get(LLMConfig, profile.id)
            assert persisted.api_key is None
            assert persisted.base_url is None
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_profile_model_must_belong_to_provider(client: TestClient):
    provider = _make_provider(client).json()
    r = _make_profile(client, provider["id"], model="not-configured")
    assert r.status_code == 422


def test_cannot_delete_provider_used_by_profile(client: TestClient):
    provider = _make_provider(client).json()
    _make_profile(client, provider["id"])
    r = client.delete(f"/api/settings/llm/providers/{provider['id']}")
    assert r.status_code == 409


def test_provider_validation(client: TestClient):
    r = _make_provider(client, models=["", "  "])
    assert r.status_code == 422

    r = _make_provider(client, base_url="localhost:1234/v1")
    assert r.status_code == 422


def test_upsert_invalid_temperature(client: TestClient):
    provider = _make_provider(client).json()
    r = _make_profile(client, provider["id"], temperature=5.0)
    assert r.status_code == 422


def test_upsert_invalid_max_tokens(client: TestClient):
    provider = _make_provider(client).json()
    r = _make_profile(client, provider["id"], max_tokens=99999)
    assert r.status_code == 422


# ── Scanner policy ───────────────────────────────────────────────────────────

def test_get_scanner_policy_defaults(client: TestClient):
    r = client.get("/api/settings/scanner-policy")
    assert r.status_code == 200
    data = r.json()
    assert data["scan_mode"] == "safe_active"
    assert data["max_probes_per_page"] == 50
    assert data["thinking_max_steps"] == 120
    assert data["min_delay_s"] == 0.05
    assert data["allowed_schemes"] == ["http", "https"]
    assert "POST" in data["methods_by_mode"]["safe_active"]


def test_upsert_scanner_policy(client: TestClient):
    payload = client.get("/api/settings/scanner-policy").json()
    payload.update({
        "scan_mode": "aggressive",
        "max_probes_per_page": 25,
        "thinking_max_steps": 180,
        "request_timeout_s": 12.5,
        "min_delay_s": 0.1,
        "blocked_headers": ["host", "cookie", "x-admin"],
    })
    r = client.put("/api/settings/scanner-policy", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["scan_mode"] == "aggressive"
    assert data["max_probes_per_page"] == 25
    assert data["thinking_max_steps"] == 180
    assert data["blocked_headers"] == ["host", "cookie", "x-admin"]

    r2 = client.get("/api/settings/scanner-policy")
    assert r2.json()["request_timeout_s"] == 12.5


def test_upsert_scanner_policy_invalid_limit(client: TestClient):
    payload = client.get("/api/settings/scanner-policy").json()
    payload["max_probes_per_page"] = 9999
    r = client.put("/api/settings/scanner-policy", json=payload)
    assert r.status_code == 422


def test_upsert_scanner_policy_invalid_method(client: TestClient):
    payload = client.get("/api/settings/scanner-policy").json()
    payload["methods_by_mode"]["safe_active"] = ["GET", "BAD METHOD"]
    r = client.put("/api/settings/scanner-policy", json=payload)
    assert r.status_code == 422


def test_import_llm_config_rejects_duplicate_names(client: TestClient):
    # Duplicate provider names
    payload_dup_provider = {
        "exported_at": "2026-05-24T10:00:00Z",
        "providers": [
            {
                "name": "DuplicateProvider",
                "api_format": "openai",
                "base_url": "http://localhost:1234/v1",
                "models": ["gpt-4"],
                "api_key": "some-key",
            },
            {
                "name": "duplicateprovider",
                "api_format": "openai",
                "base_url": "http://localhost:5678/v1",
                "models": ["gpt-4"],
                "api_key": "some-other-key",
            }
        ],
        "profiles": []
    }
    r = client.post("/api/settings/llm/import", json=payload_dup_provider)
    assert r.status_code == 422
    assert "Duplicate provider name" in r.json()["detail"]

    # Duplicate profile names
    payload_dup_profile = {
        "exported_at": "2026-05-24T10:00:00Z",
        "providers": [
            {
                "name": "SomeProvider",
                "api_format": "openai",
                "base_url": "http://localhost:1234/v1",
                "models": ["gpt-4"],
                "api_key": "some-key",
            }
        ],
        "profiles": [
            {
                "name": "DuplicateProfile",
                "provider_name": "SomeProvider",
                "model": "gpt-4",
                "max_tokens": 1000,
                "temperature": 0.0,
                "use_vision": False,
                "is_active": True,
            },
            {
                "name": "duplicateprofile",
                "provider_name": "SomeProvider",
                "model": "gpt-4",
                "max_tokens": 2000,
                "temperature": 0.5,
                "use_vision": False,
                "is_active": False,
            }
        ]
    }
    r = client.post("/api/settings/llm/import", json=payload_dup_profile)
    assert r.status_code == 422
    assert "Duplicate profile name" in r.json()["detail"]


def test_llm_profile_force_tool_choice_round_trip(client: TestClient):
    provider = _make_provider(client).json()
    
    # Verify defaults to True
    profile = _make_profile(client, provider["id"], name="Profile With Force").json()
    assert profile["force_tool_choice"] is True

    # Disable it explicitly
    profile_disabled = _make_profile(
        client, 
        provider["id"], 
        name="Profile Without Force", 
        force_tool_choice=False
    ).json()
    assert profile_disabled["force_tool_choice"] is False

    # Get active config to verify it resolves correctly
    client.post(f"/api/settings/llm/profiles/{profile_disabled['id']}/activate")
    active = client.get("/api/settings/llm").json()
    assert active["force_tool_choice"] is False
