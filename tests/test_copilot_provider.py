from __future__ import annotations

import asyncio
import sqlite3
from types import SimpleNamespace

from aespa.models import LLMConfig
from aespa.services import copilot_provider


class _FakeSession:
    def __init__(self, kwargs, *, call_tool: bool):
        self.kwargs = kwargs
        self.call_tool = call_tool
        self.aborted = False
        self.disconnected = False
        self.prompt = None
        self.attachments = None
        self.handlers = [kwargs["on_event"]]
        self.tool_result = None

    async def send_and_wait(self, prompt, *, attachments=None, timeout=0):
        self.prompt = prompt
        self.attachments = attachments
        if self.call_tool:
            from copilot.tools import ToolInvocation

            tool = self.kwargs["tools"][0]
            await tool.handler(
                ToolInvocation(
                    session_id="session-1",
                    tool_call_id="call-1",
                    tool_name=tool.name,
                    arguments={"url": "https://target.local"},
                )
            )
            return None
        self._emit_usage()
        return SimpleNamespace(data=SimpleNamespace(content='{"ok": true}'))

    async def send(self, prompt):
        from copilot.generated.session_events import (
            AssistantMessageData,
            AssistantMessageToolRequest,
        )
        from copilot.tools import ToolInvocation

        self.prompt = prompt
        if not self.call_tool:
            self._emit(AssistantMessageData(content="complete", message_id="message-2"))
            self._emit_usage()
            return "message-2"

        request = AssistantMessageToolRequest(
            name=self.kwargs["tools"][0].name,
            tool_call_id="call-1",
            arguments={"url": "https://target.local"},
        )
        self._emit(
            AssistantMessageData(
                content="",
                message_id="message-1",
                tool_requests=[request],
            )
        )
        self._emit_usage()

        async def execute_tool():
            result = await self.kwargs["tools"][0].handler(
                ToolInvocation(
                    session_id="session-1",
                    tool_call_id="call-1",
                    tool_name=self.kwargs["tools"][0].name,
                    arguments={"url": "https://target.local"},
                )
            )
            self.tool_result = result.text_result_for_llm
            self._emit(
                AssistantMessageData(
                    content="assessment complete", message_id="message-2"
                )
            )
            self._emit_usage()

        asyncio.create_task(execute_tool())
        self.call_tool = False
        return "message-1"

    def on(self, handler):
        self.handlers.append(handler)

        def unsubscribe():
            self.handlers.remove(handler)

        return unsubscribe

    def _emit(self, data):
        event = SimpleNamespace(data=data)
        for handler in list(self.handlers):
            handler(event)

    def _emit_usage(self):
        from copilot.generated.session_events import (
            AssistantUsageCopilotUsage,
            AssistantUsageData,
        )

        self._emit(
            AssistantUsageData(
                model="gpt-5.6-terra",
                input_tokens=120,
                output_tokens=30,
                cache_read_tokens=80,
                copilot_usage=AssistantUsageCopilotUsage(total_nano_aiu=2_500_000_000),
                _quota_snapshots={
                    "ai_credits": SimpleNamespace(
                        _remaining_percentage=72.5,
                        _used_requests=20,
                        _entitlement_requests=100,
                        _is_unlimited_entitlement=False,
                        _token_based_billing=True,
                        _reset_date=None,
                    )
                },
            )
        )

    async def abort(self):
        self.aborted = True

    async def disconnect(self):
        self.disconnected = True


class _FakeClient:
    def __init__(self, *, call_tool: bool):
        self.call_tool = call_tool
        self.sessions = []

    async def create_session(self, **kwargs):
        session = _FakeSession(kwargs, call_tool=self.call_tool)
        self.sessions.append(session)
        return session


class _FakeRuntimeClient:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.instances.append(self)

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True


def _config() -> LLMConfig:
    return LLMConfig(provider="github_copilot", model="auto", max_tokens=4096)


def test_conversation_prompt_preserves_tool_history():
    prompt = copilot_provider.conversation_prompt(
        [
            {"role": "user", "content": "Inspect the target"},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call-0",
                        "name": "http_request",
                        "input": {"url": "https://target.local"},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call-0",
                        "content": "HTTP 200",
                    }
                ],
            },
        ]
    )

    assert "[USER]\nInspect the target" in prompt
    assert '"name": "http_request"' in prompt
    assert "TOOL RESULT call-0: HTTP 200" in prompt


def test_explicit_token_client_is_isolated_and_filters_environment(monkeypatch):
    import copilot

    _FakeRuntimeClient.instances.clear()
    copilot_provider._clients.clear()
    monkeypatch.setattr(copilot, "CopilotClient", _FakeRuntimeClient)
    monkeypatch.setenv("AESPA_PRIVATE_SECRET", "must-not-be-forwarded")
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "environment-token")
    monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
    config = _config()
    config.api_key = "explicit-user-token"

    async def exercise():
        client = await copilot_provider._get_client(config, "http://proxy.local:8080")
        base_directory = client.kwargs["base_directory"]
        await copilot_provider.close_clients()
        return client, base_directory

    client, base_directory = asyncio.run(exercise())
    assert client.started is True
    assert client.stopped is True
    assert client.kwargs["mode"] == "empty"
    assert client.kwargs["use_logged_in_user"] is False
    assert client.kwargs["github_token"] == "explicit-user-token"
    assert "AESPA_PRIVATE_SECRET" not in client.kwargs["env"]
    assert client.kwargs["env"]["COPILOT_GITHUB_TOKEN"] == "environment-token"
    assert client.kwargs["env"]["SYSTEMROOT"] == r"C:\Windows"
    assert client.kwargs["env"]["HTTPS_PROXY"] == "http://proxy.local:8080"
    assert not copilot_provider.Path(base_directory).exists()


def test_logged_in_client_uses_copilot_home_for_default_account(monkeypatch, tmp_path):
    import copilot

    copilot_home = tmp_path / "copilot-home"
    copilot_home.mkdir()
    _FakeRuntimeClient.instances.clear()
    copilot_provider._clients.clear()
    monkeypatch.setattr(copilot, "CopilotClient", _FakeRuntimeClient)
    monkeypatch.setenv("COPILOT_HOME", str(copilot_home))

    async def exercise():
        client = await copilot_provider._get_client(_config(), None)
        await copilot_provider.close_clients()
        return client

    client = asyncio.run(exercise())
    assert client.kwargs["mode"] == "copilot-cli"
    assert client.kwargs["use_logged_in_user"] is True
    assert client.kwargs["github_token"] is None
    assert client.kwargs["base_directory"] == str(copilot_home)
    assert copilot_home.exists()


def test_named_copilot_account_uses_its_stored_credential(monkeypatch, tmp_path):
    import copilot

    copilot_home = tmp_path / "copilot-home"
    copilot_home.mkdir()
    with sqlite3.connect(copilot_home / "data.db") as connection:
        connection.execute(
            "CREATE TABLE accounts (login TEXT, access_token TEXT, kind TEXT, "
            "is_default INTEGER)"
        )
        connection.execute(
            "INSERT INTO accounts VALUES (?, ?, 'github', 0)",
            ("named-user", "stored-account-token"),
        )

    _FakeRuntimeClient.instances.clear()
    copilot_provider._clients.clear()
    monkeypatch.setattr(copilot, "CopilotClient", _FakeRuntimeClient)
    monkeypatch.setenv("COPILOT_HOME", str(copilot_home))
    config = _config()
    config.username = "NAMED-user"

    async def exercise():
        client = await copilot_provider._get_client(config, None)
        base_directory = client.kwargs["base_directory"]
        await copilot_provider.close_clients()
        return client, base_directory

    client, base_directory = asyncio.run(exercise())
    assert client.kwargs["mode"] == "empty"
    assert client.kwargs["use_logged_in_user"] is False
    assert client.kwargs["github_token"] == "stored-account-token"
    assert not copilot_provider.Path(base_directory).exists()


def test_named_copilot_account_must_exist(monkeypatch, tmp_path):
    copilot_home = tmp_path / "copilot-home"
    copilot_home.mkdir()
    with sqlite3.connect(copilot_home / "data.db") as connection:
        connection.execute(
            "CREATE TABLE accounts (login TEXT, access_token TEXT, kind TEXT, "
            "is_default INTEGER)"
        )
    monkeypatch.setenv("COPILOT_HOME", str(copilot_home))

    try:
        copilot_provider._copilot_account_token("missing-user")
    except RuntimeError as exc:
        assert "missing-user" in str(exc)
    else:
        raise AssertionError("Missing Copilot account should fail")


def test_completion_with_tools_returns_captured_tool_call(monkeypatch):
    client = _FakeClient(call_tool=True)

    async def fake_get_client(config, proxy_url):
        return client

    monkeypatch.setattr(copilot_provider, "_get_client", fake_get_client)
    usage = []
    messages = [{"role": "user", "content": "Inspect the target"}]

    async def exercise():
        first = await copilot_provider.completion_with_tools(
            _config(),
            "Use one tool.",
            messages,
            [
                {
                    "name": "http_request",
                    "description": "Make an HTTP request.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                }
            ],
            lambda *args, **kwargs: usage.append((*args, kwargs)),
        )
        first_blocks, _, first_raw = first
        messages.append({"role": "assistant", "content": first_raw})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call-1",
                        "content": "HTTP 200",
                    }
                ],
            }
        )
        second = await copilot_provider.completion_with_tools(
            _config(),
            "Use one tool.",
            messages,
            [
                {
                    "name": "http_request",
                    "description": "Make an HTTP request.",
                    "input_schema": {"type": "object"},
                }
            ],
            lambda *args, **kwargs: usage.append((*args, kwargs)),
        )
        await copilot_provider.close_conversation(messages)
        return first, second, first_blocks

    (blocks, stop_reason, raw), (final_blocks, final_stop, _), _ = asyncio.run(
        exercise()
    )

    assert stop_reason == "tool_use"
    assert raw == blocks
    assert blocks == [
        {
            "type": "tool_use",
            "id": "call-1",
            "name": "http_request",
            "input": {"url": "https://target.local"},
            "text": None,
        }
    ]
    session = client.sessions[0]
    assert session.aborted is True
    assert session.disconnected is True
    assert session.tool_result == "HTTP 200"
    assert final_stop == "end_turn"
    assert final_blocks[0]["text"] == "assessment complete"
    assert len(client.sessions) == 1
    assert list(session.kwargs["available_tools"]) == ["custom:*"]
    assert session.kwargs["enable_config_discovery"] is False
    assert session.kwargs["skip_custom_instructions"] is True
    assert session.kwargs["memory"] == {"enabled": False}
    assert session.kwargs["skip_embedding_retrieval"] is True
    assert session.kwargs["enable_session_store"] is False
    assert session.kwargs["enable_session_telemetry"] is False
    assert len(usage) == 2
    assert usage[0][:5] == ("gpt-5.6-terra", 120, 30, 80, 0)
    assert usage[0][5]["ai_credits"] == 2.5
    assert usage[0][5]["requests"] == 1


def test_plain_completion_uses_no_tools_and_supports_image(monkeypatch):
    client = _FakeClient(call_tool=False)

    async def fake_get_client(config, proxy_url):
        return client

    monkeypatch.setattr(copilot_provider, "_get_client", fake_get_client)
    result = asyncio.run(
        copilot_provider.plain_completion(
            _config(), "Return JSON.", "cG5n", lambda *args, **kwargs: None
        )
    )

    assert result == '{"ok": true}'
    session = client.sessions[0]
    assert session.kwargs["tools"] == []
    assert list(session.kwargs["available_tools"]) == []
    assert session.attachments == [
        {
            "type": "blob",
            "data": "cG5n",
            "mimeType": "image/png",
            "displayName": "aespa-page.png",
        }
    ]
    assert session.disconnected is True
