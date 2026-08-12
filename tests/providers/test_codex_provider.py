from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from aespa.services import codex_provider, statistics


def test_codex_child_env_uses_cli_default_home(monkeypatch):
    monkeypatch.setenv("HOME", "/users/example")
    monkeypatch.setenv("CODEX_HOME", "/users/example/custom-codex")

    env = codex_provider._child_env()

    assert env["HOME"] == "/users/example"
    assert env["CODEX_HOME"] == "/users/example/custom-codex"


def test_codex_child_env_does_not_inject_a_private_home(monkeypatch):
    monkeypatch.setenv("HOME", "/users/example")
    monkeypatch.delenv("CODEX_HOME", raising=False)

    env = codex_provider._child_env()

    assert env["HOME"] == "/users/example"
    assert "CODEX_HOME" not in env


def test_codex_tool_schema_uses_dynamic_tool_wire_shape():
    schema = codex_provider._tool_schema(
        {
            "name": "http_request",
            "description": "Send a request",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
            },
        }
    )
    assert schema == {
        "type": "function",
        "name": "http_request",
        "description": "Send a request",
        "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}},
    }


def test_codex_usage_delta_counts_cumulative_notifications_once():
    conversation = codex_provider._Conversation(thread_id="t", last_message_count=0)
    first = codex_provider._usage_delta(
        conversation,
        {"usage": {"inputTokens": 100, "cachedInputTokens": 40, "outputTokens": 12}},
    )
    second = codex_provider._usage_delta(
        conversation,
        {"usage": {"inputTokens": 125, "cachedInputTokens": 55, "outputTokens": 20}},
    )
    assert first["inputTokens"] == 100
    assert first["cachedInputTokens"] == 40
    assert second["inputTokens"] == 25
    assert second["cachedInputTokens"] == 15
    assert second["outputTokens"] == 8


def test_codex_usage_delta_reads_current_app_server_nested_totals():
    conversation = codex_provider._Conversation(thread_id="t", last_message_count=0)
    params = {
        "threadId": "t",
        "turnId": "turn-1",
        "tokenUsage": {
            "total": {
                "inputTokens": 125,
                "cachedInputTokens": 55,
                "cacheWriteInputTokens": 4,
                "outputTokens": 20,
                "reasoningOutputTokens": 8,
                "totalTokens": 157,
            },
            "last": {
                "inputTokens": 25,
                "cachedInputTokens": 15,
                "cacheWriteInputTokens": 4,
                "outputTokens": 8,
                "reasoningOutputTokens": 3,
                "totalTokens": 36,
            },
            "modelContextWindow": 200_000,
        },
    }

    delta = codex_provider._usage_delta(conversation, params)

    assert delta == {
        "inputTokens": 125,
        "cachedInputTokens": 55,
        "cacheWriteInputTokens": 4,
        "outputTokens": 20,
        "reasoningOutputTokens": 8,
        "totalTokens": 157,
    }


def test_codex_usage_includes_reasoning_tokens_in_output_total():
    calls = []
    codex_provider._emit_usage(
        lambda *args, **kwargs: calls.append((args, kwargs)),
        "gpt-5.6-sol",
        {"inputTokens": 10, "outputTokens": 4, "reasoningOutputTokens": 6},
    )
    assert calls[0][0][1:3] == (10, 10)


def test_codex_zero_usage_notification_does_not_add_a_model_call():
    calls = []
    codex_provider._emit_usage(
        lambda *args, **kwargs: calls.append((args, kwargs)),
        "gpt-5.6-sol",
        {},
    )

    assert calls == []


def test_codex_quota_error_keeps_reset_and_snapshot():
    snapshot = {"limitId": "daily", "resetsAt": 123}
    error = codex_provider.CodexQuotaError("limit reached", snapshot=snapshot)
    assert str(error) == "limit reached"
    assert error.snapshot == snapshot
    assert SimpleNamespace(snapshot=error.snapshot).snapshot["limitId"] == "daily"


def test_codex_rate_limit_error_extracts_retry_delay():
    payload = {
        "error": {
            "message": "Rate limit reached for model on tokens per min (TPM)",
            "additionalDetails": "Please try again in 47ms.",
        }
    }
    assert codex_provider._is_rate_limit_error(payload) is True
    assert codex_provider._extract_retry_after(payload) == 0.047


def test_codex_rate_limit_error_recognizes_full_numeric_window():
    payload = {
        "additionalDetails": (
            "Limit 40000000, Used 40000000, Requested 31709. Please try again in 47ms."
        )
    }
    assert codex_provider._rate_limit_error_has_full_window(payload) is True


def test_codex_rate_limit_snapshot_detects_full_window():
    assert codex_provider._rate_limit_is_exhausted(
        {"rateLimits": {"primary": {"usedPercent": 100, "resetsAt": 123}}}
    )
    assert not codex_provider._rate_limit_is_exhausted(
        {"rateLimits": {"primary": {"usedPercent": 74, "resetsAt": 123}}}
    )


def test_codex_rate_limit_snapshot_detects_numeric_full_window():
    assert codex_provider._rate_limit_is_exhausted(
        {"rateLimits": {"primary": {"limit": 40_000_000, "used": 40_000_000}}}
    )
    assert not codex_provider._rate_limit_is_exhausted(
        {"rateLimits": {"primary": {"limit": 40_000_000, "used": 39_999_999}}}
    )


def test_codex_preflight_stops_a_full_window_before_starting_a_turn(monkeypatch):
    calls = []

    class FakeClient:
        async def request(self, method, params):
            calls.append((method, params))
            return {"rateLimits": {"primary": {"usedPercent": 100, "resetsAt": 123}}}

    async def fake_get_client():
        return FakeClient()

    monkeypatch.setattr(codex_provider, "_get_client", fake_get_client)
    with pytest.raises(codex_provider.CodexRateLimitError) as raised:
        asyncio.run(
            codex_provider._completion_with_tools_once(
                SimpleNamespace(model="auto"),
                "system",
                [{"role": "user", "content": "hello"}],
                [],
                lambda *args, **kwargs: None,
            )
        )

    assert raised.value.snapshot["preflight"] is True
    assert calls == [("account/rateLimits/read", {})]


def _run_codex_completion_events(monkeypatch, events):
    messages = [{"role": "user", "content": "check the findings"}]

    class FakeClient:
        async def request(self, method, params):  # noqa: ARG002
            assert method == "account/rateLimits/read"
            return {"rateLimits": {"primary": {"usedPercent": 0}}}

    async def fake_get_client():
        return FakeClient()

    async def run():
        conversation = codex_provider._Conversation(
            thread_id="thread-1", last_message_count=len(messages)
        )
        for event in events:
            await conversation.events.put(event)
        codex_provider._conversations[id(messages)] = conversation
        try:
            return await codex_provider._completion_with_tools_once(
                SimpleNamespace(model="auto"),
                "system",
                messages,
                [],
                lambda *args, **kwargs: None,
            )
        finally:
            codex_provider._conversations.pop(id(messages), None)

    monkeypatch.setattr(codex_provider, "_get_client", fake_get_client)
    return asyncio.run(run())


def test_codex_message_completion_does_not_hide_later_tool_call(monkeypatch):
    blocks, stop_reason, _ = _run_codex_completion_events(
        monkeypatch,
        [
            ("item/agentMessage/delta", {"delta": "Checking status"}),
            ("item/agentMessage/delta", {"delta": "."}),
            ("item/agentMessage/completed", {"text": "Checking status."}),
            (
                "tool",
                {
                    "callId": "call-1",
                    "tool": "context_tool",
                    "arguments": {"tool": "run_status"},
                },
            ),
        ],
    )

    assert stop_reason == "tool_use"
    assert blocks == [
        {
            "type": "text",
            "id": None,
            "name": None,
            "input": None,
            "text": "Checking status.",
        },
        {
            "type": "tool_use",
            "id": "call-1",
            "name": "context_tool",
            "input": {"tool": "run_status"},
            "text": None,
        },
    ]


def test_codex_turn_completion_joins_streamed_message_deltas(monkeypatch):
    blocks, stop_reason, _ = _run_codex_completion_events(
        monkeypatch,
        [
            ("item/agentMessage/delta", {"delta": "Validation"}),
            ("item/agentMessage/delta", {"delta": " is running."}),
            ("item/agentMessage/completed", {}),
            ("turn/completed", {}),
        ],
    )

    assert stop_reason == "end_turn"
    assert blocks[0]["text"] == "Validation is running."


def test_codex_internal_wait_fails_immediately_instead_of_hanging(monkeypatch):
    with pytest.raises(codex_provider.CodexUnavailableError) as raised:
        _run_codex_completion_events(
            monkeypatch,
            [
                (
                    "item/started",
                    {
                        "item": {
                            "type": "collabAgentToolCall",
                            "tool": "wait",
                        }
                    },
                )
            ],
        )

    assert "internal 'wait' tool" in str(raised.value)
    assert "AESPA stopped the turn" in str(raised.value)


def test_codex_turn_timeout_has_a_useful_error(monkeypatch):
    monkeypatch.setattr(codex_provider, "TURN_TIMEOUT_S", 0.001)

    with pytest.raises(codex_provider.CodexUnavailableError) as raised:
        _run_codex_completion_events(monkeypatch, [])

    assert "produced no usable AESPA response" in str(raised.value)
    assert "stalled turn" in str(raised.value)


def test_codex_subscription_usage_has_no_dollar_estimate():
    result = statistics.estimate_usage_cost(
        "openai_codex", input_tokens=1000, output_tokens=1000
    )
    assert result["estimated_cost_available"] is False
    assert result["estimated_total_cost_usd"] == 0


def test_codex_login_uses_device_code_flow(monkeypatch):
    calls = []

    class FakeClient:
        async def request(self, method, params):
            calls.append((method, params))
            return {
                "type": "chatgptDeviceCode",
                "loginId": "login-1",
                "verificationUrl": "https://auth.openai.com/codex/device",
                "userCode": "ABCD-1234",
            }

    async def fake_get_client():
        return FakeClient()

    monkeypatch.setattr(codex_provider, "_get_client", fake_get_client)
    result = asyncio.run(codex_provider.login_start())

    assert result["verificationUrl"].startswith("https://auth.openai.com/")
    assert calls == [("account/login/start", {"type": "chatgptDeviceCode"})]


def test_codex_thread_uses_app_server_sandbox_wire_value():
    calls = []

    class FakeClient:
        def __init__(self):
            self._conversations = {}

        async def request(self, method, params):
            calls.append((method, params))
            return {"thread": {"id": "thread-1"}}

    conversation = asyncio.run(
        codex_provider._start_thread(
            FakeClient(),
            SimpleNamespace(model="auto"),
            "system",
            [{"role": "user", "content": "hello"}],
            [],
        )
    )

    assert conversation.thread_id == "thread-1"
    assert calls[0][0] == "thread/start"
    assert calls[0][1]["sandbox"] == "read-only"
