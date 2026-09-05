from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from aespa.services import codex_provider, statistics


class _AsyncLines:
    def __init__(self, *values):
        self._values = iter(values)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._values)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


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


def test_codex_child_env_keeps_windows_runtime_variables(monkeypatch):
    expected = {
        "SYSTEMROOT": r"C:\Windows",
        "WINDIR": r"C:\Windows",
        "COMSPEC": r"C:\Windows\System32\cmd.exe",
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "TEMP": r"C:\Temp",
        "TMP": r"C:\Temp",
        "HOMEDRIVE": "C:",
        "HOMEPATH": r"\Users\example",
    }
    for key, value in expected.items():
        monkeypatch.setenv(key, value)

    env = codex_provider._child_env()

    assert {key: env[key] for key in expected} == expected


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


def test_codex_rate_limit_scope_uses_regular_bucket_for_non_spark_model():
    snapshot = {
        "rateLimits": {"primary": {"usedPercent": 8}},
        "rateLimitsByLimitId": {
            "codex": {"primary": {"usedPercent": 8}},
            "codex_bengalfox": {
                "limitName": "GPT-5.3-Codex-Spark",
                "primary": {"usedPercent": 100},
            },
        },
    }

    applicable = codex_provider._rate_limit_scope_for_model(snapshot, "gpt-5.6-sol")

    assert applicable == {"primary": {"usedPercent": 8}}
    assert not codex_provider._rate_limit_is_exhausted(applicable)


def test_codex_rate_limit_scope_uses_spark_specific_bucket():
    snapshot = {
        "rateLimitsByLimitId": {
            "codex": {"primary": {"usedPercent": 8}},
            "codex_bengalfox": {
                "limitName": "GPT-5.3-Codex-Spark",
                "primary": {"usedPercent": 100},
            },
        }
    }

    applicable = codex_provider._rate_limit_scope_for_model(
        snapshot, "gpt-5.3-codex-spark"
    )

    assert applicable["primary"]["usedPercent"] == 100
    assert codex_provider._rate_limit_is_exhausted(applicable)


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


def _run_codex_completion_events(monkeypatch, events, *, tools=None):
    messages = [{"role": "user", "content": "check the findings"}]

    class FakeClient:
        async def request(self, method, params):  # noqa: ARG002
            if method == "account/rateLimits/read":
                return {"rateLimits": {"primary": {"usedPercent": 0}}}
            if method == "turn/start":
                return {"turn": {"id": "repair-turn"}}
            raise AssertionError(f"unexpected method: {method}")

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
                tools or [],
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


def test_codex_retryable_stream_error_waits_for_reconnected_turn(monkeypatch):
    blocks, stop_reason, _ = _run_codex_completion_events(
        monkeypatch,
        [
            (
                "error",
                {
                    "error": {
                        "message": "Reconnecting... 2/5",
                        "codexErrorInfo": {
                            "responseStreamDisconnected": {"httpStatusCode": None}
                        },
                    },
                    "willRetry": True,
                },
            ),
            ("item/agentMessage/delta", {"delta": "Recovered"}),
            ("turn/completed", {}),
        ],
    )

    assert stop_reason == "end_turn"
    assert blocks[0]["text"] == "Recovered"


def test_codex_terminal_stream_error_still_fails(monkeypatch):
    with pytest.raises(codex_provider.CodexUnavailableError) as raised:
        _run_codex_completion_events(
            monkeypatch,
            [
                (
                    "error",
                    {
                        "error": {"message": "Reconnect attempts exhausted"},
                        "willRetry": False,
                    },
                )
            ],
        )

    assert "Reconnect attempts exhausted" in str(raised.value)


def test_codex_retryable_stream_errors_are_bounded(monkeypatch):
    retryable = (
        "error",
        {
            "error": {"message": "Reconnecting... waiting for network"},
            "willRetry": True,
        },
    )
    with pytest.raises(codex_provider.CodexTransportError) as raised:
        _run_codex_completion_events(
            monkeypatch,
            [retryable] * (codex_provider.MAX_RETRYABLE_TURN_ERRORS + 1),
        )

    assert "remained disconnected" in str(raised.value)


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

    with pytest.raises(codex_provider.CodexTurnTimeoutError) as raised:
        _run_codex_completion_events(monkeypatch, [])

    assert "produced no usable AESPA response" in str(raised.value)
    assert "stalled turn" in str(raised.value)


def test_codex_client_failure_wakes_waiting_turn(monkeypatch):
    with pytest.raises(codex_provider.CodexTransportError) as raised:
        _run_codex_completion_events(
            monkeypatch,
            [("client/error", {"message": "Codex app-server reader stopped"})],
        )

    assert "reader stopped" in str(raised.value)


def test_codex_tool_failure_message_rotates_broken_session(monkeypatch):
    with pytest.raises(codex_provider.CodexToolSessionError) as raised:
        _run_codex_completion_events(
            monkeypatch,
            [
                (
                    "item/agentMessage/completed",
                    {
                        "text": (
                            "Assessment paused because AESPA’s dynamic tools stopped "
                            "responding. Confirmed findings were preserved."
                        )
                    },
                ),
                ("turn/completed", {}),
            ],
            tools=[{"name": "context_tool"}],
        )

    assert "replacing the broken Codex tool session" in str(raised.value)


def test_codex_named_tool_unavailable_rotates_broken_session(monkeypatch):
    with pytest.raises(codex_provider.CodexToolSessionError):
        _run_codex_completion_events(
            monkeypatch,
            [
                (
                    "turn/completed",
                    {
                        "text": (
                            "Unable to begin: AESPA's required context_tool and "
                            "http_request tools are not directly available in this session."
                        )
                    },
                )
            ],
            tools=[{"name": "context_tool"}, {"name": "http_request"}],
        )


def test_codex_environmental_unavailable_text_repairs_without_rotating(monkeypatch):
    blocks, stop_reason, _ = _run_codex_completion_events(
        monkeypatch,
        [
            (
                "turn/completed",
                {
                    "text": (
                        "The controlled payment gateway is unavailable, so I will "
                        "continue with the next route."
                    )
                },
            ),
            (
                "tool",
                {
                    "callId": "call-2",
                    "tool": "context_tool",
                    "arguments": {"tool": "lead_detail", "lead_id": "HHOA-030"},
                },
            ),
        ],
        tools=[{"name": "context_tool"}],
    )

    assert stop_reason == "tool_use"
    assert blocks[-1]["name"] == "context_tool"


def test_codex_repairs_text_only_turn_before_returning_to_scanner(monkeypatch):
    blocks, stop_reason, _ = _run_codex_completion_events(
        monkeypatch,
        [
            (
                "turn/completed",
                {"text": "Assessment still in progress; checking the next route."},
            ),
            (
                "tool",
                {
                    "callId": "call-3",
                    "tool": "context_tool",
                    "arguments": {"tool": "run_status"},
                },
            ),
        ],
        tools=[{"name": "context_tool"}],
    )

    assert stop_reason == "tool_use"
    assert blocks[-1]["name"] == "context_tool"


def test_codex_returns_text_after_required_tool_repairs_are_exhausted(monkeypatch):
    blocks, stop_reason, _ = _run_codex_completion_events(
        monkeypatch,
        [
            ("turn/completed", {"text": "First prose-only response."}),
            ("turn/completed", {"text": "Second prose-only response."}),
            ("turn/completed", {"text": "Third prose-only response."}),
        ],
        tools=[{"name": "context_tool"}],
    )

    assert stop_reason == "end_turn"
    assert blocks[0]["text"] == "Third prose-only response."


def test_codex_reader_failure_notifies_all_conversations():
    client = codex_provider._JsonRpcClient("codex")
    first = codex_provider._Conversation("thread-1", 0, client=client)
    second = codex_provider._Conversation("thread-2", 0, client=client)
    client._conversations = {"thread-1": first, "thread-2": second}

    client._wake_conversations(codex_provider.CodexTransportError("reader stopped"))

    assert first.events.get_nowait() == (
        "client/error",
        {"message": "reader stopped", "client": client},
    )
    assert second.events.get_nowait() == (
        "client/error",
        {"message": "reader stopped", "client": client},
    )


def test_codex_reader_matches_string_response_id():
    async def run():
        client = codex_provider._JsonRpcClient("codex")
        client.process = SimpleNamespace(
            stdout=_AsyncLines(b'{"jsonrpc":"2.0","id":"7","result":{"ok":true}}\n')
        )
        future = asyncio.get_running_loop().create_future()
        client._pending[7] = future

        await client._read_stdout()

        assert future.result() == {"ok": True}

    asyncio.run(run())


def test_codex_app_server_uses_large_stream_limit(monkeypatch):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            stdout=_AsyncLines(),
            stderr=_AsyncLines(),
            returncode=None,
        )

    async def run():
        client = codex_provider._JsonRpcClient("codex")

        async def fake_request(method, params):  # noqa: ARG001
            return {}

        async def fake_notify(method, params):  # noqa: ARG001
            return None

        client.request = fake_request
        client.notify = fake_notify
        monkeypatch.setattr(
            asyncio, "create_subprocess_exec", fake_create_subprocess_exec
        )

        await client.start()
        await asyncio.sleep(0)

    asyncio.run(run())

    assert captured["args"][:2] == ("codex", "app-server")
    assert captured["kwargs"]["limit"] == codex_provider.CODEX_STREAM_LIMIT_BYTES
    assert captured["kwargs"]["limit"] > 64 * 1024


def test_codex_reader_accepts_json_line_larger_than_asyncio_default():
    async def run():
        client = codex_provider._JsonRpcClient("codex")
        stdout = asyncio.StreamReader(limit=codex_provider.CODEX_STREAM_LIMIT_BYTES)
        message = {
            "jsonrpc": "2.0",
            "method": "warning",
            "params": {"message": "x" * (70 * 1024)},
        }
        stdout.feed_data((json.dumps(message) + "\n").encode())
        stdout.feed_eof()
        client.process = SimpleNamespace(stdout=stdout)

        await client._read_stdout()

        assert client._notifications.get_nowait() == message

    asyncio.run(run())


def test_codex_reader_keeps_string_tool_request_id():
    async def run():
        client = codex_provider._JsonRpcClient("codex")
        conversation = codex_provider._Conversation("thread-1", 0, client=client)
        client._conversations = {"thread-1": conversation}
        client.process = SimpleNamespace(
            stdout=_AsyncLines(
                b'{"jsonrpc":"2.0","id":"tool-request-1","method":"item/tool/call",'
                b'"params":{"threadId":"thread-1","callId":"call-1"}}\n'
            )
        )

        await client._read_stdout()

        assert conversation.pending_calls["call-1"][0] == "tool-request-1"
        assert await conversation.events.get() == (
            "tool",
            {"threadId": "thread-1", "callId": "call-1"},
        )

    asyncio.run(run())


def test_codex_reader_ignores_non_object_messages_and_params():
    async def run():
        client = codex_provider._JsonRpcClient("codex")
        client.process = SimpleNamespace(
            stdout=_AsyncLines(
                b"[]\n",
                b'{"jsonrpc":"2.0","method":"warning","params":[]}\n',
            )
        )

        await client._read_stdout()

        assert client._notifications.get_nowait() == {
            "jsonrpc": "2.0",
            "method": "warning",
            "params": [],
        }

    asyncio.run(run())


def test_codex_stalled_turn_rotates_thread_before_restarting_client(monkeypatch):
    calls = []

    async def fake_completion(*args, **kwargs):  # noqa: ARG001
        calls.append("completion")
        if calls.count("completion") == 1:
            raise codex_provider.CodexTurnTimeoutError("stalled")
        return ([{"type": "text", "text": "recovered"}], "end_turn", [])

    async def fake_abandon(messages, *, delete_thread=True):  # noqa: ARG001
        calls.append(("abandon", delete_thread))

    async def fake_restart(client):  # noqa: ARG001
        calls.append("restart")

    monkeypatch.setattr(codex_provider, "_completion_with_tools_once", fake_completion)
    monkeypatch.setattr(codex_provider, "_abandon_conversation", fake_abandon)
    monkeypatch.setattr(codex_provider, "_restart_client", fake_restart)

    result = asyncio.run(
        codex_provider.completion_with_tools(
            SimpleNamespace(model="auto"),
            "system",
            [{"role": "user", "content": "hello"}],
            [],
            lambda *args, **kwargs: None,
        )
    )

    assert result[0][0]["text"] == "recovered"
    assert calls == ["completion", ("abandon", True), "completion"]


def test_codex_restarts_client_when_replacement_thread_also_stalls(monkeypatch):
    calls = []
    fake_client = object()
    monkeypatch.setattr(codex_provider, "_client", fake_client)

    async def fake_completion(*args, **kwargs):  # noqa: ARG001
        calls.append("completion")
        if calls.count("completion") <= 2:
            raise codex_provider.CodexTurnTimeoutError("stalled")
        return ([{"type": "text", "text": "recovered"}], "end_turn", [])

    async def fake_abandon(messages, *, delete_thread=True):  # noqa: ARG001
        calls.append(("abandon", delete_thread))

    async def fake_restart(client, *, allow_restart=True):
        calls.append(("restart", client))
        return True if allow_restart else None

    monkeypatch.setattr(codex_provider, "_completion_with_tools_once", fake_completion)
    monkeypatch.setattr(codex_provider, "_abandon_conversation", fake_abandon)
    monkeypatch.setattr(codex_provider, "_restart_client", fake_restart)

    result = asyncio.run(
        codex_provider.completion_with_tools(
            SimpleNamespace(model="auto"),
            "system",
            [{"role": "user", "content": "hello"}],
            [],
            lambda *args, **kwargs: None,
        )
    )

    assert result[0][0]["text"] == "recovered"
    assert calls == [
        "completion",
        ("abandon", True),
        "completion",
        ("abandon", False),
        ("restart", fake_client),
        "completion",
    ]


def test_codex_transport_failure_stops_after_two_client_restarts(monkeypatch):
    calls = []
    fake_client = object()
    monkeypatch.setattr(codex_provider, "_client", fake_client)

    async def fake_completion(*args, **kwargs):  # noqa: ARG001
        calls.append("completion")
        raise codex_provider.CodexTransportError("reader stopped")

    async def fake_abandon(messages, *, delete_thread=True):  # noqa: ARG001
        calls.append(("abandon", delete_thread))

    async def fake_restart(client, *, allow_restart=True):
        calls.append(("restart", client, allow_restart))
        return True if allow_restart else None

    monkeypatch.setattr(codex_provider, "_completion_with_tools_once", fake_completion)
    monkeypatch.setattr(codex_provider, "_abandon_conversation", fake_abandon)
    monkeypatch.setattr(codex_provider, "_restart_client", fake_restart)

    with pytest.raises(codex_provider.CodexTransportError):
        asyncio.run(
            codex_provider.completion_with_tools(
                SimpleNamespace(model="auto"),
                "system",
                [{"role": "user", "content": "hello"}],
                [],
                lambda *args, **kwargs: None,
            )
        )

    assert calls == [
        "completion",
        ("abandon", False),
        ("restart", fake_client, True),
        "completion",
        ("abandon", False),
        ("restart", fake_client, True),
        "completion",
        ("abandon", False),
        ("restart", fake_client, False),
    ]


def test_codex_transport_recovery_targets_the_client_that_failed(monkeypatch):
    calls = []
    failed_client = codex_provider._JsonRpcClient("old-codex")
    replacement_client = codex_provider._JsonRpcClient("new-codex")
    monkeypatch.setattr(codex_provider, "_client", replacement_client)

    async def fake_completion(*args, **kwargs):  # noqa: ARG001
        calls.append("completion")
        if calls.count("completion") == 1:
            raise codex_provider.CodexTransportError(
                "old reader stopped", client=failed_client
            )
        return ([{"type": "text", "text": "recovered"}], "end_turn", [])

    async def fake_abandon(messages, *, delete_thread=True):  # noqa: ARG001
        calls.append(("abandon", delete_thread))

    async def fake_restart(client, *, allow_restart=True):
        calls.append(("restart", client, allow_restart))
        return False

    monkeypatch.setattr(codex_provider, "_completion_with_tools_once", fake_completion)
    monkeypatch.setattr(codex_provider, "_abandon_conversation", fake_abandon)
    monkeypatch.setattr(codex_provider, "_restart_client", fake_restart)

    result = asyncio.run(
        codex_provider.completion_with_tools(
            SimpleNamespace(model="auto"),
            "system",
            [{"role": "user", "content": "hello"}],
            [],
            lambda *args, **kwargs: None,
        )
    )

    assert result[0][0]["text"] == "recovered"
    assert calls == [
        "completion",
        ("abandon", False),
        ("restart", failed_client, True),
        "completion",
    ]


def test_codex_restart_does_not_close_a_newer_client(monkeypatch):
    old_client = codex_provider._JsonRpcClient("old-codex")
    replacement_client = codex_provider._JsonRpcClient("new-codex")
    monkeypatch.setattr(codex_provider, "_client", replacement_client)

    restarted = asyncio.run(codex_provider._restart_client(old_client))

    assert restarted is False
    assert codex_provider._client is replacement_client


def test_codex_flushes_terminal_tool_result_before_thread_close(monkeypatch):
    messages = [
        {"role": "user", "content": "validate the finding"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "done-call",
                    "name": "done",
                    "input": {"summary": "complete"},
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "done-call",
                    "content": "Assessment complete.",
                }
            ],
        },
    ]
    sent = []

    class FakeClient:
        async def _send_response(self, request_id, result):
            sent.append((request_id, result))

    conversation = codex_provider._Conversation(
        thread_id="thread-1",
        last_message_count=1,
        pending_calls={"done-call": (42, {"tool": "done"})},
    )
    monkeypatch.setattr(codex_provider, "_client", FakeClient())
    codex_provider._conversations[id(messages)] = conversation
    try:
        resolved = asyncio.run(codex_provider.flush_pending_tool_results(messages))
    finally:
        codex_provider._conversations.pop(id(messages), None)

    assert resolved == 1
    assert conversation.pending_calls == {}
    assert conversation.last_message_count == len(messages)
    assert sent == [
        (
            42,
            {
                "success": True,
                "contentItems": [{"type": "inputText", "text": "Assessment complete."}],
            },
        )
    ]


def test_codex_close_fails_unresolved_dynamic_callbacks(monkeypatch):
    messages = [{"role": "user", "content": "start"}]
    sent = []
    requests = []

    class FakeClient:
        def __init__(self):
            self._conversations = {"thread-1": conversation}

        async def _send_response(self, request_id, result):
            sent.append((request_id, result))

        async def request(self, method, params):
            requests.append((method, params))

    conversation = codex_provider._Conversation(
        thread_id="thread-1",
        last_message_count=1,
        pending_calls={"request-call": (77, {"tool": "http_request"})},
    )
    fake_client = FakeClient()
    monkeypatch.setattr(codex_provider, "_client", fake_client)
    codex_provider._conversations[id(messages)] = conversation

    asyncio.run(codex_provider.close_conversation(messages))

    assert sent[0][0] == 77
    assert sent[0][1]["success"] is False
    assert conversation.pending_calls == {}
    assert requests == [("thread/delete", {"threadId": "thread-1"})]
    assert id(messages) not in codex_provider._conversations
    assert "thread-1" not in fake_client._conversations


def test_codex_usage_uses_api_equivalent_dollar_estimate():
    result = statistics.estimate_usage_cost(
        "openai_codex",
        input_tokens=1000,
        output_tokens=1000,
        rates={
            "input_price_usd_per_million": 4,
            "output_price_usd_per_million": 20,
        },
    )
    assert result["estimated_cost_available"] is True
    assert result["estimated_total_cost_usd"] == 0.024


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
