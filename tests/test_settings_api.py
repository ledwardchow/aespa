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
    assert "github_copilot" in data
    assert "openai" in data
    assert "openai_compatible" in data
    assert "openrouter" in data
    assert "bedrock" in data
    assert "azure_foundry_openai" in data
    assert "azure_foundry_anthropic" in data
    assert isinstance(data["anthropic"], list)
    assert isinstance(data["openrouter"], list)
    assert isinstance(data["bedrock"], list)
    assert data["github_copilot"] == [
        "auto",
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "claude-sonnet-5",
        "claude-opus-4.8",
    ]
    assert data["openai"][:3] == [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
    ]
    assert data["bedrock"][:2] == [
        "global.anthropic.claude-opus-4-8",
        "global.anthropic.claude-sonnet-4-6",
    ]


def test_burp_rest_api_config_round_trip(client: TestClient):
    r = client.get("/api/settings/burp-rest-api")
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert r.json()["api_url"] == "http://127.0.0.1:1337"
    assert (
        r.json()["scan_configuration_name"]
        == "Audit checks - all except time-based detection methods"
    )
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


def test_cloudflare_access_config_round_trip(client: TestClient):
    # Defaults to no audience (legacy behaviour: audience check skipped).
    r = client.get("/api/settings/cloudflare-access")
    assert r.status_code == 200
    assert r.json()["audience"] is None

    r = client.put("/api/settings/cloudflare-access", json={"audience": "  abc123  "})
    assert r.status_code == 200
    # Whitespace is trimmed on the way in.
    assert r.json()["audience"] == "abc123"
    assert client.get("/api/settings/cloudflare-access").json()["audience"] == "abc123"

    # Blank clears it back to None so the verifier skips the audience check.
    r = client.put("/api/settings/cloudflare-access", json={"audience": "   "})
    assert r.status_code == 200
    assert r.json()["audience"] is None


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
    return client.post("/api/settings/llm/model-configs", json=payload)


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

    profile_r = _make_profile(
        client, provider["id"], name="OptionalTempProfile", temperature=None
    )
    assert profile_r.status_code == 200
    profile = profile_r.json()
    assert profile["temperature"] is None

    client.post(f"/api/settings/llm/model-configs/{profile['id']}/activate")
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


def test_create_github_copilot_provider_without_token(client: TestClient):
    provider_r = _make_provider(
        client,
        name="Copilot",
        api_format="github_copilot",
        base_url=None,
        username="copilot-user",
        models=["auto"],
        api_key=None,
    )
    assert provider_r.status_code == 200
    provider = provider_r.json()
    assert provider["api_format"] == "github_copilot"
    assert provider["username"] == "copilot-user"
    assert provider["models"] == ["auto"]
    assert provider["has_api_key"] is False

    profile_r = _make_profile(client, provider["id"], model="auto")
    assert profile_r.status_code == 200
    assert profile_r.json()["provider"] == "github_copilot"
    assert profile_r.json()["username"] == "copilot-user"


def test_bedrock_mantle_project_id_round_trips(client: TestClient):
    provider_r = _make_provider(
        client,
        name="Mantle",
        api_format="bedrock_mantle",
        base_url=None,
        project_id="proj_5d5ykleja6cwpirysbb7",
        models=["openai.gpt-oss-120b"],
        api_key="bedrock-key",
    )
    assert provider_r.status_code == 200
    provider = provider_r.json()
    assert provider["api_format"] == "bedrock_mantle"
    assert provider["project_id"] == "proj_5d5ykleja6cwpirysbb7"

    profile_r = _make_profile(client, provider["id"], model="openai.gpt-oss-120b")
    assert profile_r.status_code == 200
    # The project id is denormalized onto the resolved active profile.
    active = client.get("/api/settings/llm").json()
    assert active["provider"] == "bedrock_mantle"
    assert active["project_id"] == "proj_5d5ykleja6cwpirysbb7"


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

    r = client.put(
        f"/api/settings/llm/providers/{provider['id']}",
        json={
            "name": "Local OpenAI",
            "api_format": "openai",
            "base_url": "http://localhost:11434/v1",
            "models": ["llama-3", "gpt-4o"],
            "api_key": "sk-2",
        },
    )
    assert r.status_code == 200

    active = client.get("/api/settings/llm").json()
    assert active["has_api_key"] is True
    assert active["api_key"] is None
    assert active["base_url"] == "http://localhost:11434/v1"


def test_write_only_api_keys_behavior(client: TestClient):
    # 1. Create provider with API key
    p_resp = _make_provider(client, name="Secret Provider", api_key="sk-secret-123")
    assert p_resp.status_code == 200
    provider = p_resp.json()
    assert provider["has_api_key"] is True
    assert provider["api_key"] is None

    # 2. Get list of providers - key should be masked (None), has_api_key True
    list_r = client.get("/api/settings/llm/providers")
    assert list_r.status_code == 200
    p_item = next(p for p in list_r.json() if p["id"] == provider["id"])
    assert p_item["has_api_key"] is True
    assert p_item["api_key"] is None

    # 3. Update provider with api_key: null - key is preserved
    up_resp = client.put(
        f"/api/settings/llm/providers/{provider['id']}",
        json={
            "name": "Secret Provider Renamed",
            "api_format": "openai",
            "base_url": "http://localhost:1234/v1/",
            "models": ["llama-3", "gpt-4o"],
            "api_key": None,
        },
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["has_api_key"] is True

    # 4. Update provider with api_key: "" - key is cleared
    clear_resp = client.put(
        f"/api/settings/llm/providers/{provider['id']}",
        json={
            "name": "Secret Provider Renamed",
            "api_format": "openai",
            "base_url": "http://localhost:1234/v1/",
            "models": ["llama-3", "gpt-4o"],
            "api_key": "",
        },
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["has_api_key"] is False

    # 5. Burp REST API key write-only test
    burp_put = client.put(
        "/api/settings/burp-rest-api",
        json={
            "enabled": True,
            "api_url": "http://127.0.0.1:1337",
            "api_key": "burp-secret-key",
            "scan_configuration_name": "Audit",
            "scan_sqli": True,
            "scan_xss": True,
            "scan_command_injection": True,
            "scan_path_traversal": True,
            "scan_ssrf": True,
            "scan_xxe": True,
            "scan_ssti": True,
        },
    )
    assert burp_put.status_code == 200
    assert burp_put.json()["has_api_key"] is True
    assert burp_put.json()["api_key"] is None

    burp_get = client.get("/api/settings/burp-rest-api")
    assert burp_get.json()["has_api_key"] is True
    assert burp_get.json()["api_key"] is None


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
    r = _make_profile(client, provider["id"], max_tokens=300000)
    assert r.status_code == 422


# ── Scanner policy ───────────────────────────────────────────────────────────


def test_get_scanner_policy_defaults(client: TestClient):
    r = client.get("/api/settings/scanner-policy")
    assert r.status_code == 200
    data = r.json()
    assert data["execution_monitor_enabled"] is False
    assert data["scan_mode"] == "aggressive"
    assert "DELETE" not in data["methods_by_mode"]["aggressive"]
    assert data["max_probes_per_page"] == 50
    assert data["thinking_max_steps"] == 120
    assert data["min_delay_s"] == 0.05
    assert data["allowed_schemes"] == ["http", "https"]
    assert "POST" in data["methods_by_mode"]["safe_active"]


def test_upsert_scanner_policy(client: TestClient):
    payload = client.get("/api/settings/scanner-policy").json()
    payload.update(
        {
            "scan_mode": "aggressive",
            "execution_monitor_enabled": True,
            "max_probes_per_page": 25,
            "thinking_max_steps": 180,
            "request_timeout_s": 12.5,
            "min_delay_s": 0.1,
            "blocked_headers": ["host", "cookie", "x-admin"],
        }
    )
    r = client.put("/api/settings/scanner-policy", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["execution_monitor_enabled"] is True
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
            },
        ],
        "profiles": [],
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
            },
        ],
    }
    r = client.post("/api/settings/llm/import", json=payload_dup_profile)
    assert r.status_code == 422
    assert "Duplicate profile name" in r.json()["detail"]


def test_llm_profile_force_tool_choice_round_trip(client: TestClient):
    provider = _make_provider(client).json()

    # Verify defaults to False
    profile = _make_profile(client, provider["id"], name="Profile Default").json()
    assert profile["force_tool_choice"] is False

    # Enable it explicitly
    profile_enabled = _make_profile(
        client, provider["id"], name="Profile With Force", force_tool_choice=True
    ).json()
    assert profile_enabled["force_tool_choice"] is True

    # Get active config to verify it resolves correctly
    client.post(f"/api/settings/llm/model-configs/{profile_enabled['id']}/activate")
    active = client.get("/api/settings/llm").json()
    assert active["force_tool_choice"] is True


def test_export_import_write_only_keys(client: TestClient):
    # 1. Setup provider with key
    p = _make_provider(
        client, name="ExportProvider", api_key="secret-export-key"
    ).json()

    # 2. Direct loopback export includes raw key
    exp_r = client.get("/api/settings/llm/export")
    assert exp_r.status_code == 200
    export_data = exp_r.json()
    exp_p = next(
        item for item in export_data["providers"] if item["name"] == "ExportProvider"
    )
    assert exp_p["has_api_key"] is True
    assert exp_p["api_key"] == "secret-export-key"

    # 3. Export via proxy (e.g. Cloudflare Access headers present) masks raw key
    proxied_exp_r = client.get(
        "/api/settings/llm/export", headers={"CF-Connecting-IP": "203.0.113.1"}
    )
    assert proxied_exp_r.status_code == 200
    proxied_export_data = proxied_exp_r.json()
    p_exp_p = next(
        item
        for item in proxied_export_data["providers"]
        if item["name"] == "ExportProvider"
    )
    assert p_exp_p["has_api_key"] is True
    assert p_exp_p["api_key"] is None

    # 4. Import back proxied exported JSON (with api_key=None) - existing key in DB is preserved
    imp_r = client.post("/api/settings/llm/import", json=proxied_export_data)
    assert imp_r.status_code == 200

    # Verify key is still present
    list_r = client.get("/api/settings/llm/providers")
    updated_p = next(item for item in list_r.json() if item["id"] == p["id"])
    assert updated_p["has_api_key"] is True
    assert updated_p["api_key"] is None
