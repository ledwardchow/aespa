from fastapi.testclient import TestClient


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
    assert isinstance(data["anthropic"], list)
    assert isinstance(data["openrouter"], list)
    assert isinstance(data["bedrock"], list)
    assert data["bedrock"][:2] == [
        "global.anthropic.claude-sonnet-4-6",
        "global.anthropic.claude-opus-4-7",
    ]


def test_upsert_anthropic(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "anthropic",
        "api_key": "sk-ant-test",
        "model": "claude-opus-4-5",
        "max_tokens": 4096,
        "temperature": 0.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "anthropic"
    assert data["api_key"] == "sk-ant-test"
    assert data["model"] == "claude-opus-4-5"
    assert data["base_url"] is None


def test_upsert_openai(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "openai",
        "api_key": "sk-test",
        "model": "gpt-4o",
        "max_tokens": 2048,
        "temperature": 0.5,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "openai"
    assert data["temperature"] == 0.5


def test_upsert_openai_compatible(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "openai_compatible",
        "base_url": "http://localhost:1234/v1",
        "model": "llama-3.1-8b-instruct",
        "max_tokens": 2048,
        "temperature": 0.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "openai_compatible"
    assert data["base_url"] == "http://localhost:1234/v1"
    assert data["api_key"] is None


def test_upsert_openai_compatible_strips_trailing_slash(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "openai_compatible",
        "base_url": "http://localhost:1234/v1/",
        "model": "llama-3",
        "max_tokens": 1024,
        "temperature": 0.0,
    })
    assert r.status_code == 200
    assert r.json()["base_url"] == "http://localhost:1234/v1"


def test_upsert_openrouter(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "openrouter",
        "api_key": "sk-or-v1-test",
        "model": "openrouter/owl-alpha",
        "max_tokens": 2048,
        "temperature": 0.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "openrouter"
    assert data["api_key"] == "sk-or-v1-test"
    assert data["model"] == "openrouter/owl-alpha"
    assert data["base_url"] is None


def test_upsert_bedrock(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "bedrock",
        "api_key": "bedrock-test-key",
        "base_url": "https://bedrock-runtime.ap-southeast-2.amazonaws.com/",
        "model": "global.anthropic.claude-sonnet-4-6",
        "max_tokens": 64000,
        "temperature": 0.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "bedrock"
    assert data["api_key"] == "bedrock-test-key"
    assert data["base_url"] == "https://bedrock-runtime.ap-southeast-2.amazonaws.com"
    assert data["model"] == "global.anthropic.claude-sonnet-4-6"
    assert data["max_tokens"] == 64000


def test_upsert_bedrock_sso_profile(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "bedrock",
        "model": "global.anthropic.claude-sonnet-4-6",
        "max_tokens": 64000,
        "temperature": 0.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "bedrock"
    assert data["api_key"] is None
    assert data["base_url"] is None


def test_upsert_is_idempotent(client: TestClient):
    payload = {
        "provider": "anthropic",
        "api_key": "sk-ant-1",
        "model": "claude-opus-4-5",
        "max_tokens": 4096,
        "temperature": 0.0,
    }
    client.put("/api/settings/llm", json=payload)
    payload["api_key"] = "sk-ant-2"
    r = client.put("/api/settings/llm", json=payload)
    assert r.status_code == 200
    assert r.json()["api_key"] == "sk-ant-2"

    r2 = client.get("/api/settings/llm")
    assert r2.json()["api_key"] == "sk-ant-2"


def test_upsert_anthropic_missing_api_key(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "anthropic",
        "model": "claude-opus-4-5",
        "max_tokens": 4096,
        "temperature": 0.0,
    })
    assert r.status_code == 422


def test_upsert_openrouter_missing_api_key(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "openrouter",
        "model": "openrouter/owl-alpha",
        "max_tokens": 4096,
        "temperature": 0.0,
    })
    assert r.status_code == 422


def test_upsert_bedrock_missing_api_key_allows_sso_profile(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "bedrock",
        "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com",
        "model": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "max_tokens": 4096,
        "temperature": 0.0,
    })
    assert r.status_code == 200


def test_upsert_bedrock_missing_base_url(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "bedrock",
        "api_key": "bedrock-test-key",
        "model": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "max_tokens": 4096,
        "temperature": 0.0,
    })
    assert r.status_code == 422


def test_upsert_openai_compatible_missing_base_url(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "openai_compatible",
        "model": "llama-3",
        "max_tokens": 1024,
        "temperature": 0.0,
    })
    assert r.status_code == 422


def test_upsert_invalid_temperature(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "anthropic",
        "api_key": "sk-ant-x",
        "model": "claude-opus-4-5",
        "max_tokens": 4096,
        "temperature": 5.0,  # > 2
    })
    assert r.status_code == 422


def test_upsert_invalid_max_tokens(client: TestClient):
    r = client.put("/api/settings/llm", json={
        "provider": "openai",
        "api_key": "sk-x",
        "model": "gpt-4o",
        "max_tokens": 99999,  # > 64000
        "temperature": 0.0,
    })
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
