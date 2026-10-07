from __future__ import annotations

import asyncio
import json

import pytest

from aespa.models import LLMConfig
from aespa.services import claude_cli_provider, llm


def test_claude_cli_tool_response_uses_aespa_tools(monkeypatch):
    async def fake_invoke(config, prompt, **kwargs):
        assert "Tool result earlier" in prompt
        assert "http_request" in kwargs["system"]
        return {
            "structured_output": {
                "text": "Checking the endpoint",
                "tool_calls": [{"name": "http_request", "input": {"url": "/health"}}],
            }
        }

    monkeypatch.setattr(claude_cli_provider, "_invoke", fake_invoke)
    config = LLMConfig(provider="claude_cli", model="sonnet")
    blocks, reason, history = asyncio.run(
        claude_cli_provider.completion_with_tools(
            config,
            "Use the tool",
            [{"role": "user", "content": "Tool result earlier"}],
            [
                {
                    "name": "http_request",
                    "description": "Make a request",
                    "input_schema": {"type": "object"},
                }
            ],
        )
    )
    assert reason == "tool_use"
    assert blocks == history
    assert blocks[1]["name"] == "http_request"
    assert blocks[1]["input"] == {"url": "/health"}
    assert blocks[1]["id"].startswith("toolu_")


def test_claude_cli_rejects_unknown_tool(monkeypatch):
    async def fake_invoke(*args, **kwargs):
        return {
            "structured_output": {
                "text": "",
                "tool_calls": [{"name": "Bash", "input": {}}],
            }
        }

    monkeypatch.setattr(claude_cli_provider, "_invoke", fake_invoke)
    with pytest.raises(RuntimeError, match="invalid AESPA tool call"):
        asyncio.run(
            claude_cli_provider.completion_with_tools(
                LLMConfig(provider="claude_cli", model="sonnet"),
                "",
                [],
                [{"name": "http_request", "input_schema": {"type": "object"}}],
            )
        )


@pytest.mark.parametrize(
    ("selected_model", "cli_model"),
    [
        ("sonnet", "sonnet"),
        ("mythos", "claude-mythos-5"),
        ("mythos-5", "claude-mythos-5"),
        ("claude-mythos-5", "claude-mythos-5"),
    ],
)
def test_claude_cli_process_disables_own_tools_and_records_usage(
    monkeypatch, selected_model, cli_model
):
    seen = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self, payload):
            seen["prompt"] = payload
            return json.dumps(
                {
                    "result": "done",
                    "usage": {"input_tokens": 9, "output_tokens": 2},
                }
            ).encode(), b""

    async def fake_subprocess(*cmd, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = kwargs["env"]
        return FakeProcess()

    monkeypatch.setattr(claude_cli_provider, "_executable", lambda: "/usr/bin/claude")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    monkeypatch.setenv("AESPA_PRIVATE_SECRET", "secret")
    usage = []
    result = asyncio.run(
        claude_cli_provider.plain_completion(
            LLMConfig(provider="claude_cli", model=selected_model),
            "say hi",
            usage_callback=lambda *args: usage.append(args),
        )
    )
    assert result == "done"
    assert seen["prompt"] == b"say hi"
    assert seen["cmd"][seen["cmd"].index("--tools") + 1] == ""
    assert seen["cmd"][seen["cmd"].index("--model") + 1] == cli_model
    assert "--safe-mode" in seen["cmd"]
    assert "AESPA_PRIVATE_SECRET" not in seen["env"]
    assert usage == [(cli_model, 9, 2, 0, 0)]


def test_llm_dispatches_claude_cli(monkeypatch):
    async def fake_plain(*args):
        return "hello"

    monkeypatch.setattr(claude_cli_provider, "plain_completion", fake_plain)
    assert (
        asyncio.run(
            llm._dispatch_completion(
                LLMConfig(provider="claude_cli", model="sonnet"),
                "prompt",
                None,
            )
        )
        == "hello"
    )
