from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from aespa.models import LLMConfig
from aespa.services import droid_provider, llm


def test_droid_sessions_share_one_factory_project(monkeypatch, tmp_path):
    monkeypatch.setattr(droid_provider.tempfile, "gettempdir", lambda: str(tmp_path))

    first = droid_provider._workspace_directory()
    second = droid_provider._workspace_directory()

    assert first == second == tmp_path / "aespa-droid-workspace"
    assert first.is_dir()


def test_child_environment_does_not_forward_aespa_secrets(monkeypatch):
    monkeypatch.setenv("HOME", "/tmp/factory-home")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("AESPA_PRIVATE_SECRET", "do-not-forward")

    env = droid_provider._child_env("http://proxy.local:8080")

    assert env["HOME"] == "/tmp/factory-home"
    assert env["PATH"] == "/usr/bin"
    assert env["HTTPS_PROXY"] == "http://proxy.local:8080"
    assert "AESPA_PRIVATE_SECRET" not in env


def test_permission_handler_only_allows_aespa_mcp_tools():
    allowed = {
        "toolUses": [
            {
                "confirmationType": "mcp_tool",
                "details": {"serverName": "aespa", "actualToolName": "http_request"},
            }
        ]
    }
    built_in = {
        "toolUses": [
            {"confirmationType": "exec", "details": {"command": "curl target"}}
        ]
    }

    assert droid_provider._permission_handler(allowed) == "proceed_once"
    assert droid_provider._permission_handler(built_in) == "cancel"


def test_relay_surfaces_call_and_returns_aespa_result():
    async def exercise():
        events = asyncio.Queue()
        conversation = SimpleNamespace(
            token="secret",
            events=events,
            pending={},
        )
        server = await asyncio.start_server(
            lambda r, w: droid_provider._handle_relay(
                r, w, conversation, {"echo_probe"}
            ),
            "127.0.0.1",
            0,
        )
        port = server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(
            (
                json.dumps(
                    {
                        "token": "secret",
                        "params": {
                            "name": "echo_probe",
                            "arguments": {"value": "ok"},
                        },
                    }
                )
                + "\n"
            ).encode()
        )
        await writer.drain()

        event_type, tool = await events.get()
        assert event_type == "tool"
        assert tool["name"] == "echo_probe"
        conversation.pending[tool["id"]].future.set_result(("ok", False))
        response = json.loads(await reader.readline())

        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()
        return response

    assert asyncio.run(exercise()) == {
        "content": [{"type": "text", "text": "ok"}],
        "isError": False,
    }


def test_persistent_conversation_starts_next_user_turn(monkeypatch):
    async def exercise():
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "first response"},
            {"role": "user", "content": "second"},
        ]
        client = SimpleNamespace(messages=[])

        async def add_user_message(*, text):
            client.messages.append(text)

        client.add_user_message = add_user_message
        conversation = SimpleNamespace(
            client=client,
            events=asyncio.Queue(),
            pending={},
            drain_task=None,
            last_message_count=1,
            usage=None,
        )

        async def fake_drain(active):
            await active.events.put(("complete", "second response"))

        monkeypatch.setattr(droid_provider, "_drain", fake_drain)
        droid_provider._conversations[id(messages)] = conversation
        try:
            blocks, stop_reason, _ = await droid_provider.completion_with_tools(
                LLMConfig(provider="factory_droid", model="test-model"),
                "system",
                messages,
                [],
                lambda *args, **kwargs: None,
            )
        finally:
            droid_provider._conversations.pop(id(messages), None)

        assert client.messages == ["second"]
        assert blocks[0]["text"] == "second response"
        assert stop_reason == "end_turn"

    asyncio.run(exercise())


def test_turn_timeout_closes_conversation(monkeypatch):
    async def exercise():
        messages = [{"role": "user", "content": "waiting"}]
        conversation = SimpleNamespace(
            events=asyncio.Queue(),
            pending={},
            drain_task=None,
            last_message_count=1,
            usage=None,
        )
        droid_provider._conversations[id(messages)] = conversation
        closed = []

        async def fake_close(key):
            closed.append(key)
            droid_provider._conversations.pop(key, None)

        monkeypatch.setattr(droid_provider, "DROID_TURN_TIMEOUT_S", 0.001)
        monkeypatch.setattr(droid_provider, "_close_conversation", fake_close)
        try:
            await droid_provider.completion_with_tools(
                LLMConfig(provider="factory_droid", model="test-model"),
                "system",
                messages,
                [],
                lambda *args, **kwargs: None,
            )
        except RuntimeError as exc:
            assert str(exc) == "Factory Droid turn timed out"
        else:
            raise AssertionError("Expected the Droid turn to time out")

        assert closed == [id(messages)]

    asyncio.run(exercise())


def test_llm_service_dispatches_factory_droid(monkeypatch):
    async def exercise():
        config = LLMConfig(provider="factory_droid", model="test-model")
        messages = [{"role": "user", "content": "hello"}]

        async def fake_tools(*args):
            assert args[0] is config
            assert args[2] is messages
            return ([{"type": "text", "text": "tool path"}], "end_turn", [])

        monkeypatch.setattr(droid_provider, "completion_with_tools", fake_tools)
        blocks, stop_reason, _ = await llm._call_with_tools_impl(
            config, "system", messages, tools=[]
        )
        assert blocks[0]["text"] == "tool path"
        assert stop_reason == "end_turn"

        async def fake_plain(*args):
            return "stream path"

        monkeypatch.setattr(llm, "_factory_droid", fake_plain)
        chunks = [
            chunk
            async for chunk in llm.stream_chat_completion(config, "system", messages)
        ]
        assert chunks == ["stream path"]

    asyncio.run(exercise())


def test_droid_usage_records_cumulative_deltas_and_credits():
    recorded = []
    conversation = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=20,
            cache_read_tokens=30,
            cache_write_tokens=10,
        ),
        factory_credits=400,
        recorded_usage=(0, 0, 0, 0, 0),
    )
    config = LLMConfig(provider="factory_droid", model="test-model")

    droid_provider._record_usage(
        conversation, config, lambda *args, **kwargs: recorded.append((args, kwargs))
    )
    conversation.usage = SimpleNamespace(
        input_tokens=150,
        output_tokens=25,
        cache_read_tokens=50,
        cache_write_tokens=10,
    )
    conversation.factory_credits = 475
    droid_provider._record_usage(
        conversation, config, lambda *args, **kwargs: recorded.append((args, kwargs))
    )

    assert recorded[0][0] == ("test-model", 100, 20, 30, 10)
    assert recorded[0][1]["factory_credits"] == 400
    assert recorded[1][0] == ("test-model", 50, 5, 20, 0)
    assert recorded[1][1]["factory_credits"] == 75


def test_raw_droid_usage_captures_factory_credits():
    conversation = SimpleNamespace(factory_credits=0)

    droid_provider._capture_factory_credits(
        conversation,
        {
            "params": {
                "notification": {
                    "type": "session_token_usage_changed",
                    "tokenUsage": {"factoryCredits": 434},
                }
            }
        },
    )

    assert conversation.factory_credits == 434
