from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from aespa.models import LLMConfig
from aespa.services import chatgpt_plan, llm


@pytest.mark.parametrize(
    ("payload", "expected_client_id"),
    [
        ({}, None),
        ({"client_id": None}, None),
        ({"client_id": "oaiapp_saved"}, "oaiapp_saved"),
    ],
)
def test_plan_login_accepts_new_and_returning_accounts(
    client: TestClient, monkeypatch, payload, expected_client_id
):
    async def start_login(client_id):
        assert client_id == expected_client_id
        return {"login_id": "attempt", "url": "https://auth.openai.com/example"}

    monkeypatch.setattr(chatgpt_plan, "start_login", start_login)
    response = client.post("/api/settings/llm/chatgpt-plan/login", json=payload)
    assert response.status_code == 200
    assert response.json()["login_id"] == "attempt"


def test_plan_provider_keeps_selected_account_out_of_api_credentials(
    client: TestClient,
):
    response = client.post(
        "/api/settings/llm/providers",
        json={
            "name": "My ChatGPT plan",
            "api_format": "openai_chatgpt_plan",
            "username": "oaiapp_test",
            "api_key": "must-not-be-saved",
            "base_url": "https://example.test",
            "models": ["gpt-6.1-sol"],
        },
    )
    assert response.status_code == 200
    saved = response.json()
    assert saved["username"] == "oaiapp_test"
    assert saved["api_key"] is None
    assert saved["base_url"] is None


def test_plan_model_discovery_reports_signed_out_account(
    client: TestClient, monkeypatch
):
    async def unavailable(_client_id):
        raise RuntimeError("Sign in with ChatGPT")

    monkeypatch.setattr(chatgpt_plan, "discover_models", unavailable)
    response = client.post(
        "/api/settings/llm/discover-model-options",
        json={"api_format": "openai_chatgpt_plan", "username": "oaiapp_test"},
    )
    assert response.status_code == 502
    assert "Check that it is signed in" in response.json()["detail"]


def test_plan_discovery_adds_verified_models_and_documented_limits(
    client: TestClient, monkeypatch
):
    async def catalog(_client_id):
        return ["gpt-6-astra", "gpt-5.6-sol"]

    async def access(_client_id, *, force=False):
        return {
            "models": ["gpt-6-sol", "gpt-6-luna", "gpt-daybreak-red-latest"],
            "daybreak": {"blue": True, "red": True},
        }

    monkeypatch.setattr(chatgpt_plan, "discover_models", catalog)
    monkeypatch.setattr(chatgpt_plan, "check_access", access)
    response = client.post(
        "/api/settings/llm/discover-model-options",
        json={"api_format": "openai_chatgpt_plan", "username": "oaiapp_test"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["models"] == [
        "gpt-6-astra",
        "gpt-5.6-sol",
        "gpt-6-sol",
        "gpt-6-luna",
        "gpt-daybreak-red-latest",
    ]
    assert result["catalog_complete"] is True
    assert result["capabilities"]["gpt-6-sol"]["context_window_tokens"] == 1_050_000
    assert result["capabilities"]["gpt-6-sol"]["max_output_tokens"] == 128_000
    assert result["capabilities"]["gpt-6-sol"]["default_effort"] == "medium"
    assert result["capabilities"]["gpt-6-luna"]["default_effort"] == "xhigh"
    assert (
        result["capabilities"]["gpt-daybreak-red-latest"]["context_window_tokens"]
        == 400_000
    )

    async def catalog_unavailable(_client_id):
        raise RuntimeError("catalog unavailable")

    monkeypatch.setattr(chatgpt_plan, "discover_models", catalog_unavailable)
    partial = client.post(
        "/api/settings/llm/discover-model-options",
        json={"api_format": "openai_chatgpt_plan", "username": "oaiapp_test"},
    )
    assert partial.status_code == 200
    assert partial.json()["catalog_complete"] is False
    assert partial.json()["models"] == [
        "gpt-6-sol",
        "gpt-6-luna",
        "gpt-daybreak-red-latest",
    ]


def test_plan_provider_refresh_fills_default_model_settings(
    client: TestClient, db_session
):
    from aespa.services.model_capabilities import documented_model_capability
    from aespa.services.settings_providers import repair_chatgpt_plan_models

    capability = documented_model_capability("openai_chatgpt_plan", "gpt-6-luna")
    payload = {
        "name": "ChatGPT plan test",
        "api_format": "openai_chatgpt_plan",
        "username": "oaiapp_test",
        "models": ["gpt-6-luna", "gpt-6-sol"],
        "model_capabilities": {},
    }
    provider = client.post("/api/settings/llm/providers", json=payload).json()
    models = client.get("/api/settings/llm/model-configs").json()
    assert {item["model"] for item in models} == {"gpt-6-luna", "gpt-6-sol"}
    model = next(item for item in models if item["model"] == "gpt-6-luna")
    assert model["max_tokens"] == 128_000
    assert model["reasoning_effort"] == "xhigh"
    assert provider["model_capabilities"]["gpt-6-luna"]["default_effort"] == "xhigh"

    # Existing providers created before documented metadata was stored are
    # repaired on startup without changing their scan-profile model IDs.
    stale = db_session.get(LLMConfig, model["id"])
    stale.max_tokens = 16384
    stale.max_context_tokens = 128000
    stale.context_limit_source = "fallback"
    stale.reasoning_effort = "medium"
    db_session.add(stale)
    db_session.commit()
    repair_chatgpt_plan_models(db_session)
    db_session.refresh(stale)
    assert stale.max_tokens == 128_000
    assert stale.max_context_tokens == 1_050_000
    assert stale.reasoning_effort == "xhigh"
    repair_chatgpt_plan_models(db_session)
    assert len(client.get("/api/settings/llm/model-configs").json()) == 2
    stale.reasoning_effort = "medium"
    db_session.add(stale)
    db_session.commit()
    repair_chatgpt_plan_models(db_session)
    db_session.refresh(stale)
    assert stale.reasoning_effort == "medium"  # A later manual choice is preserved.
    stale.reasoning_effort = "xhigh"
    db_session.add(stale)
    db_session.commit()

    payload["model_capabilities"] = {"gpt-6-luna": capability}
    refreshed = client.put(
        f"/api/settings/llm/providers/{provider['id']}", json=payload
    )
    assert refreshed.status_code == 200
    updated = client.get("/api/settings/llm/model-configs").json()
    saved = next(item for item in updated if item["id"] == model["id"])
    assert saved["max_context_tokens"] == 1_050_000
    assert saved["max_tokens"] == 128_000
    assert saved["reasoning_effort"] == "xhigh"
    assert saved["username"] == "oaiapp_test"

    automatic = client.post(
        "/api/settings/llm/model-configs",
        json={
            "name": "Auto Luna",
            "provider_id": provider["id"],
            "model": "gpt-6-luna",
        },
    )
    assert automatic.status_code == 200
    assert automatic.json()["max_tokens"] == 128_000
    assert automatic.json()["reasoning_effort"] == "xhigh"

    rejected = client.put(
        f"/api/settings/llm/model-configs/{model['id']}",
        json={
            "provider_id": provider["id"],
            "model": "gpt-6-luna",
            "max_tokens": 128_001,
        },
    )
    assert rejected.status_code == 422

    oversized_context = client.put(
        f"/api/settings/llm/model-configs/{model['id']}",
        json={
            "provider_id": provider["id"],
            "model": "gpt-6-luna",
            "max_context_tokens": 1_050_001,
        },
    )
    assert oversized_context.status_code == 422

    payload["username"] = "oaiapp_other"
    switched = client.put(f"/api/settings/llm/providers/{provider['id']}", json=payload)
    assert switched.status_code == 200
    updated = client.get("/api/settings/llm/model-configs").json()
    assert (
        next(item for item in updated if item["id"] == model["id"])["username"]
        == "oaiapp_other"
    )


def test_plan_request_uses_supported_streaming_shape():
    config = SimpleNamespace(
        provider="openai_chatgpt_plan",
        base_url=None,
        model="gpt-6.1-sol",
        max_tokens=4096,
        reasoning_effort="low",
        temperature=0.2,
    )
    tool = {"type": "function", "name": "check", "parameters": {"type": "object"}}
    result = llm._responses_request_kwargs(
        config,
        input=[{"type": "message", "role": "user", "content": "hello"}],
        instructions="Scan the target",
        tools=[tool],
    )

    assert result["store"] is False
    assert result["stream"] is True
    assert result["tools"] == [
        {
            "type": "namespace",
            "name": "aespa",
            "description": "Tools provided by AESPA for this scan.",
            "tools": [tool],
        }
    ]
    assert result["include"] == ["reasoning.encrypted_content"]
    assert "temperature" not in result
    assert "max_output_tokens" not in result


def test_plan_response_counts_one_request(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        llm, "_record_usage", lambda *args, **kwargs: recorded.append(kwargs)
    )
    config = LLMConfig(provider="openai_chatgpt_plan", model="gpt-6-sol")
    response = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=20,
            input_tokens_details=SimpleNamespace(cached_tokens=30),
        ),
        prompt_cache_key=None,
    )
    llm._record_responses_usage(config, response)
    assert recorded[0]["requests"] == 1


def test_plan_context_budget_keeps_full_output_space_for_plain_requests(monkeypatch):
    config = LLMConfig(
        provider="openai_chatgpt_plan",
        model="gpt-6-sol",
        max_tokens=4_000,
        max_context_tokens=10_000,
    )
    with pytest.raises(llm.LLMContextLimitError):
        llm._context_budget_for_request(config, input_tokens=6_000)

    captured = {}

    async def fake_call(config_arg, prompt, screenshot):
        captured.update(config=config_arg, prompt=prompt)
        return "ok"

    monkeypatch.setattr(llm, "_call", fake_call)
    result = asyncio.run(
        llm.plain_completion(config, "evidence " * 10_000, system_prompt="Scan safely.")
    )
    assert result == "ok"
    assert captured["config"].max_tokens == 4_000
    assert (
        llm.estimate_tokens(
            captured["prompt"], provider="openai_chatgpt_plan", model="gpt-6-sol"
        )
        <= 4_976
    )


def test_plan_access_check_verifies_unlisted_models_and_daybreak(monkeypatch):
    async def token(_client_id):
        return "test-token"

    monkeypatch.setattr(chatgpt_plan, "access_token", token)
    chatgpt_plan._access_checks.clear()

    def handler(request):
        assert request.headers["authorization"] == "Bearer test-token"
        model = json.loads(request.content)["model"]
        if model == "gpt-daybreak-red-latest":
            return httpx.Response(403, json={"error": {"code": "model_access_denied"}})
        cyber = "daybreak_blue" if model != "gpt-6.1-sol" else "standard"
        event = {
            "type": "response.completed",
            "response": {"access_programs": {"cyber": cyber}},
        }
        return httpx.Response(200, text=f"data: {json.dumps(event)}\n\n")

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        chatgpt_plan.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    access = asyncio.run(chatgpt_plan.check_access("oaiapp_test", force=True))
    assert {"gpt-6-sol", "gpt-6-luna"}.issubset(access["models"])
    assert access["daybreak"] == {"blue": True, "red": False}


def test_plan_sends_daybreak_program_for_supported_scan_models(monkeypatch):
    async def access(_client_id, *, force=False):
        return {"daybreak": {"blue": True, "red": True}}

    monkeypatch.setattr(chatgpt_plan, "check_access", access)

    async def request(model):
        config = SimpleNamespace(username="oaiapp_test", model=model)
        kwargs = {}
        await llm._add_daybreak_access(config, kwargs)
        return kwargs

    for model in ("gpt-6-sol", "gpt-6-luna", "gpt-daybreak-blue-latest", "gpt-6-astra"):
        assert asyncio.run(request(model)) == {
            "extra_body": {"access_programs": {"cyber": "daybreak_blue"}}
        }
    assert asyncio.run(request("gpt-daybreak-red-latest")) == {
        "extra_body": {"access_programs": {"cyber": "daybreak_red"}}
    }
    assert asyncio.run(request("gpt-5.6-luna")) == {}


def test_plan_stream_requires_completion_and_pauses_on_usage_limit():
    class Stream:
        def __init__(self, events):
            self.events = iter(events)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.events)
            except StopIteration as exc:
                raise StopAsyncIteration from exc

    class Responses:
        def __init__(self, events):
            self.events = events

        async def create(self, **kwargs):
            assert kwargs["stream"] is True
            return Stream(self.events)

    async def call(events):
        return await llm._chatgpt_plan_response(
            SimpleNamespace(responses=Responses(events)), {"stream": True}
        )

    completed = SimpleNamespace(
        type="response.completed", response=SimpleNamespace(output=[object()])
    )
    assert asyncio.run(call([completed])) is completed.response
    with pytest.raises(RuntimeError, match="without any output items"):
        asyncio.run(
            call(
                [
                    SimpleNamespace(
                        type="response.completed",
                        response=SimpleNamespace(output=[]),
                    )
                ]
            )
        )
    for item_type in ("message", "function_call"):
        item = SimpleNamespace(type=item_type)
        response = asyncio.run(
            call(
                [
                    SimpleNamespace(type="response.output_item.done", item=item),
                    SimpleNamespace(
                        type="response.completed",
                        response=SimpleNamespace(output=[]),
                    ),
                ]
            )
        )
        assert response.output == [item]
    with pytest.raises(RuntimeError, match="without a completed response"):
        asyncio.run(call([]))
    failed = SimpleNamespace(
        type="response.failed",
        response=SimpleNamespace(
            error=SimpleNamespace(code="subscription_sharing_usage_limit_exceeded")
        ),
    )
    with pytest.raises(llm.LLMQuotaPauseError):
        asyncio.run(call([failed]))


def test_id_token_checks_signature_audience_and_nonce():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk["kid"] = "test-key"

    class Http:
        async def get(self, url):
            assert url == chatgpt_plan.JWKS_URL
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"keys": [jwk]},
            )

    token = jwt.encode(
        {
            "iss": chatgpt_plan.ISSUER,
            "aud": "oaiapp_example",
            "sub": "user-1",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "nonce": "expected",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    claims = asyncio.run(
        chatgpt_plan._validate_id_token(Http(), token, "oaiapp_example", "expected")
    )
    assert claims["sub"] == "user-1"
    with pytest.raises(ValueError, match="nonce"):
        asyncio.run(
            chatgpt_plan._validate_id_token(Http(), token, "oaiapp_example", "wrong")
        )
    with pytest.raises(jwt.InvalidAudienceError):
        asyncio.run(chatgpt_plan._validate_id_token(Http(), token, "other", "expected"))


def test_plan_provider_returns_scanner_tool_call(monkeypatch):
    calls = []
    response = SimpleNamespace(output=[])
    tool_call = SimpleNamespace(
        type="function_call",
        call_id="call_1",
        name="aespa.check",
        arguments='{"url":"https://example.test"}',
    )

    class Responses:
        async def create(self, **kwargs):
            calls.append(kwargs)

            async def events():
                yield SimpleNamespace(type="response.output_item.done", item=tool_call)
                yield SimpleNamespace(type="response.completed", response=response)

            return events()

    async def client(_config):
        return SimpleNamespace(responses=Responses())

    async def access(_client_id, *, force=False):
        return {"daybreak": {"blue": True, "red": True}}

    monkeypatch.setattr(chatgpt_plan, "check_access", access)
    monkeypatch.setattr(llm, "_make_chatgpt_plan_client", client)
    monkeypatch.setattr(llm, "_record_responses_usage", lambda *args, **kwargs: None)
    config = SimpleNamespace(
        provider="openai_chatgpt_plan",
        base_url=None,
        model="gpt-6.1-sol",
        max_tokens=4096,
        reasoning_effort="low",
        temperature=None,
        force_tool_choice=False,
    )
    blocks, stop, history = asyncio.run(
        llm._call_with_tools_impl(
            config,
            "Scan the target",
            [{"role": "user", "content": "Check this URL"}],
            tools=[
                {
                    "name": "check",
                    "description": "Check a URL",
                    "input_schema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                    },
                }
            ],
        )
    )
    assert calls[0]["tools"][0]["name"] == "aespa"
    assert calls[0]["extra_body"] == {"access_programs": {"cyber": "daybreak_blue"}}
    assert calls[0]["input"] == [
        {"type": "message", "role": "user", "content": "Check this URL"}
    ]
    assert blocks == [
        {
            "type": "tool_use",
            "id": "call_1",
            "name": "check",
            "input": {"url": "https://example.test"},
            "text": None,
        }
    ]
    assert stop == "tool_use"
    assert history[0]["type"] == "responses_output_item"


def test_login_uses_dynamic_registration_and_stable_host_id(monkeypatch, tmp_path):
    monkeypatch.setattr(chatgpt_plan, "_storage_path", lambda: tmp_path / "plan.json")

    class Server:
        sockets = [SimpleNamespace(getsockname=lambda: ("127.0.0.1", 1455))]

        def close(self):
            pass

    async def start_server(callback, host, port):
        assert host == "127.0.0.1" and port == 0
        return Server()

    monkeypatch.setattr(chatgpt_plan.asyncio, "start_server", start_server)

    async def start_twice():
        first = await chatgpt_plan.start_login()
        second = await chatgpt_plan.start_login()
        return first, second

    first, second = asyncio.run(start_twice())
    first_query = parse_qs(urlsplit(first["url"]).query)
    second_query = parse_qs(urlsplit(second["url"]).query)
    assert first_query["client_id"] == ["dynamic_agent_client"]
    assert first_query["agent_name_hint"] == ["AESPA"]
    assert first_query["scope"] == [chatgpt_plan.SCOPES]
    assert first_query["redirect_uri"] == ["http://127.0.0.1:1455/auth/callback"]
    assert first_query["ext_agent_host_id"] == second_query["ext_agent_host_id"]
    assert first_query["state"] != second_query["state"]


def test_expired_token_refreshes_once_for_concurrent_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(chatgpt_plan, "_storage_path", lambda: tmp_path / "plan.json")
    chatgpt_plan._write(
        {
            "host_id": "urn:uuid:12345678-1234-4123-8123-123456789abc",
            "active": "oaiapp_test",
            "accounts": {
                "oaiapp_test": {
                    "subject": "user-1",
                    "access_token": "expired",
                    "refresh_token": "old-refresh",
                    "expires_at": 0,
                    "scopes": ["chatgpt.tokens.use.direct"],
                }
            },
        }
    )
    calls = []

    class Http:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def post(self, url, data):
            calls.append((url, data))
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 3600,
                },
            )

    monkeypatch.setattr(chatgpt_plan.httpx, "AsyncClient", lambda **_kwargs: Http())

    async def concurrent():
        return await asyncio.gather(
            chatgpt_plan.access_token("oaiapp_test"),
            chatgpt_plan.access_token("oaiapp_test"),
        )

    assert asyncio.run(concurrent()) == ["new-access", "new-access"]
    assert len(calls) == 1
    assert calls[0][1]["refresh_token"] == "old-refresh"
    assert (
        chatgpt_plan._read()["accounts"]["oaiapp_test"]["refresh_token"]
        == "new-refresh"
    )


def test_login_callback_saves_validated_tokens_without_exposing_them(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(chatgpt_plan, "_storage_path", lambda: tmp_path / "plan.json")
    callbacks = []

    class Server:
        sockets = [SimpleNamespace(getsockname=lambda: ("127.0.0.1", 1455))]

        def close(self):
            pass

    async def start_server(callback, _host, _port):
        callbacks.append(callback)
        return Server()

    class Http:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def post(self, _url, data):
            assert data["redirect_uri"] == "http://127.0.0.1:1455/auth/callback"
            assert data["client_id"] == "oaiapp_test"
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "id_token": "signed-id-token",
                    "access_token": "secret-access",
                    "refresh_token": "secret-refresh",
                    "scope": chatgpt_plan.SCOPES,
                    "expires_in": 3600,
                },
            )

    async def validate(_http, token, client_id, nonce):
        assert token == "signed-id-token"
        assert client_id == "oaiapp_test"
        assert nonce
        return {"sub": "user-1", "email": "user@example.test"}

    class Writer:
        def __init__(self):
            self.body = b""

        def write(self, data):
            self.body += data

        async def drain(self):
            pass

        def close(self):
            pass

        async def wait_closed(self):
            pass

    monkeypatch.setattr(chatgpt_plan.asyncio, "start_server", start_server)
    monkeypatch.setattr(chatgpt_plan.httpx, "AsyncClient", lambda **_kwargs: Http())
    monkeypatch.setattr(chatgpt_plan, "_validate_id_token", validate)

    async def complete_login():
        login = await chatgpt_plan.start_login()
        state = parse_qs(urlsplit(login["url"]).query)["state"][0]
        reader = SimpleNamespace(
            readline=lambda: asyncio.sleep(
                0,
                result=(
                    f"GET /auth/callback?code=abc&state={state}&client_id=oaiapp_test HTTP/1.1\r\n"
                ).encode(),
            )
        )
        writer = Writer()
        await callbacks[0](reader, writer)
        return login, writer

    login, writer = asyncio.run(complete_login())
    assert chatgpt_plan.login_status(login["login_id"])["status"] == "complete"
    assert chatgpt_plan.status()["accounts"][0]["email"] == "user@example.test"
    assert "secret-access" not in str(chatgpt_plan.status())
    assert b"secret-access" not in writer.body
    assert (
        chatgpt_plan._read()["accounts"]["oaiapp_test"]["refresh_token"]
        == "secret-refresh"
    )
