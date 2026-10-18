from __future__ import annotations

import asyncio

import pytest

from aespa.models import LLMConfig
from aespa.services import codex_provider, llm
from aespa.services.prompts.refusal_recovery import (
    RefusalRecoveryPrompt,
    specialist_recovery_prompt,
)
from aespa.services.prompts.refusal_recovery import (
    test_lead_recovery_prompt as build_test_lead_recovery_prompt,
)
from aespa.services.prompts.test_lead import (
    _API_THINKING_AGENT_SYSTEM,
    _THINKING_PENTEST_PLAYBOOK,
    get_thinking_agent_system,
)


class ChatGPTCyberError(RuntimeError):
    def __init__(self, code: str = "cyber_policy") -> None:
        super().__init__(f"Provider refused: {code}")
        self.body = {"error": {"code": code}}


def _done(summary: str = "complete"):
    block = {
        "type": "tool_use",
        "id": "done-1",
        "name": "done",
        "input": {"summary": summary},
    }
    return [block], "tool_use", [block]


def _tool(name: str, tool_id: str):
    block = {
        "type": "tool_use",
        "id": tool_id,
        "name": name,
        "input": {},
    }
    return [block], "tool_use", [block]


def test_cyber_policy_gate_is_provider_and_code_specific():
    assert llm._is_explicit_openai_cyber_refusal(
        "openai_chatgpt_plan", ChatGPTCyberError()
    )
    assert not llm._is_explicit_openai_cyber_refusal(
        "openai_chatgpt_plan", ChatGPTCyberError("content_filter")
    )
    assert not llm._is_explicit_openai_cyber_refusal("openai", ChatGPTCyberError())
    assert not llm._is_explicit_openai_cyber_refusal(
        "openai_chatgpt_plan", RuntimeError("cyber_policy")
    )
    assert llm._is_explicit_openai_cyber_refusal(
        "openai_codex", codex_provider.CodexCyberPolicyError("cyber_policy")
    )
    assert not llm._is_explicit_openai_cyber_refusal(
        "openai_codex", codex_provider.CodexUnavailableError("cyber_policy")
    )


def test_codex_fallback_matches_only_observed_cyber_refusal():
    assert codex_provider._is_cyber_policy_turn_error(
        {
            "error": {
                "message": "This content was flagged for possible cybersecurity risk. If this seems wrong, try rephrasing your request."
            }
        }
    )
    assert codex_provider._is_cyber_policy_turn_error(
        {"error": {"code": "cyber_policy", "message": "blocked"}}
    )
    assert not codex_provider._is_cyber_policy_turn_error(
        {
            "error": {
                "code": "content_filter",
                "message": "This content was flagged for possible cybersecurity risk.",
            }
        }
    )
    assert not codex_provider._is_cyber_policy_turn_error(
        {"error": {"message": "A safety policy blocked the request."}}
    )


def test_scoped_prompts_keep_handoff_and_remove_broad_playbook():
    original = get_thinking_agent_system(False)
    scoped = build_test_lead_recovery_prompt(
        original_system=original,
        scoped_initial_user="Target: https://example.test\nApplication context:\nGET /search?q=",
        is_api_run=False,
    )
    assert scoped is not None
    assert _THINKING_PENTEST_PLAYBOOK in original
    assert _THINKING_PENTEST_PLAYBOOK not in scoped.system
    assert "Tool rules:" in scoped.system
    assert "GET /search?q=" in scoped.initial_user

    api = build_test_lead_recovery_prompt(
        original_system=_API_THINKING_AGENT_SYSTEM,
        scoped_initial_user="Target: https://example.test/api",
        is_api_run=True,
    )
    assert api is not None
    assert "Tool rules:" in api.system
    assert "one endpoint" in api.system

    specialist = specialist_recovery_prompt(
        attack_class="sqli", initial_user="Focus URL: https://example.test/search?q="
    )
    assert "Focus URL: https://example.test/search?q=" in specialist.initial_user
    assert "xp_cmdshell" not in specialist.system


def test_recovery_marker_stays_local_and_survives_compaction():
    marker = {"template_id": "web-test-lead-v1", "attempt": "sent", "step": 2}
    messages = [
        {
            "role": "user",
            "content": "Target: https://example.test",
            "_openai_refusal_recovery": marker,
        }
    ]
    for index in range(40):
        tool_id = f"tool-{index}"
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_id,
                        "name": "http_request",
                        "input": {"url": "https://example.test"},
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": "bounded result",
                    }
                ],
            }
        )
    compacted, stats = llm.compact_agentic_messages(
        messages,
        max_context_chars=4000,
        system_message="scoped system",
        recent_messages=8,
    )
    assert stats is not None
    assert compacted[0]["_openai_refusal_recovery"] == marker
    assert "_openai_refusal_recovery" not in str(
        llm._ant_messages_to_responses(compacted)
    )
    assert "_openai_refusal_recovery" not in codex_provider._conversation_prompt(
        "scoped system", compacted
    )


def test_scoped_opening_keeps_compacted_evidence():
    original = "old broad prompt\n\n[CONTEXT JOURNAL: 2 older messages]\n- GET /search"
    scoped = llm._scoped_opening_with_journal(original, "new scoped prompt")
    assert scoped.startswith("new scoped prompt")
    assert "old broad prompt" not in scoped
    assert "GET /search" in scoped


def test_scoped_retry_preserves_completed_tool_evidence(monkeypatch):
    config = LLMConfig(
        provider="openai_chatgpt_plan", model="gpt-6-sol", max_tokens=2048
    )
    prompt = RefusalRecoveryPrompt(
        "scoped system", "scoped opening", "web-test-lead-v1"
    )
    seen = []
    saved = []
    completed = []
    events = []

    async def fake_call(_config, system, messages, tools=None):
        seen.append((system, messages))
        if len(seen) == 1:
            return _tool("http_request", "probe-1")
        if len(seen) == 2:
            raise ChatGPTCyberError()
        assert system == "scoped system"
        assert messages[0]["content"] == "scoped opening"
        assert any(
            "baseline result" in str(message.get("content")) for message in messages
        )
        return _done()

    async def execute(_name, _args, _step):
        return "baseline result"

    async def checkpoint(messages, _step):
        saved.append(messages[0]["_openai_refusal_recovery"]["template_id"])

    async def completed_checkpoint(messages, _step):
        if "_openai_refusal_recovery" in messages[0]:
            completed.append(messages[0]["_openai_refusal_recovery"]["attempt"])

    monkeypatch.setattr(llm, "_call_with_tools", fake_call)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="original system",
            initial_user_message="original opening",
            tool_executor=execute,
            refusal_recovery_prompt=prompt,
            on_recovery_checkpoint=checkpoint,
            on_checkpoint=completed_checkpoint,
            emit_fn=events.append,
        )
    )
    assert summary == "complete"
    assert seen[0][0] == seen[1][0] == "original system"
    assert saved == ["web-test-lead-v1"]
    assert completed and all(attempt == "completed" for attempt in completed)
    assert any("shorter instructions" in event.get("message", "") for event in events)
    assert any(
        event.get("data", {}).get("refusal_recovery") == "accepted"
        and "continuing with done" in event.get("message", "")
        for event in events
    )


def test_no_scoped_prompt_keeps_identical_retry(monkeypatch):
    config = LLMConfig(
        provider="openai_chatgpt_plan", model="gpt-6-sol", max_tokens=2048
    )
    seen = []

    async def fake_call(_config, system, messages, tools=None):
        seen.append((system, messages[0]["content"]))
        if len(seen) == 1:
            raise ChatGPTCyberError()
        return _done()

    async def execute(_name, _args, _step):
        return "ok"

    monkeypatch.setattr(llm, "_call_with_tools", fake_call)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="original system",
            initial_user_message="original opening",
            tool_executor=execute,
        )
    )
    assert summary == "complete"
    assert seen == [
        ("original system", "original opening"),
        ("original system", "original opening"),
    ]


def test_accepted_scoped_retry_without_tool_reports_followup(monkeypatch):
    config = LLMConfig(
        provider="openai_chatgpt_plan", model="gpt-6-sol", max_tokens=2048
    )
    prompt = RefusalRecoveryPrompt(
        "scoped system", "scoped opening", "web-test-lead-v1"
    )
    calls = 0
    events = []

    async def fake_call(_config, _system, _messages, tools=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ChatGPTCyberError()
        if calls == 2:
            text_block = {"type": "text", "text": "Need a tool next."}
            return [text_block], "end_turn", [text_block]
        return _done()

    async def execute(_name, _args, _step):
        return "ok"

    monkeypatch.setattr(llm, "_call_with_tools", fake_call)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="original system",
            initial_user_message="original opening",
            tool_executor=execute,
            refusal_recovery_prompt=prompt,
            emit_fn=events.append,
        )
    )
    assert summary == "complete"
    assert any(
        event.get("data", {}).get("refusal_recovery") == "accepted"
        and "without a tool call" in event.get("message", "")
        for event in events
    )


def test_scoped_second_refusal_skips_without_dropping_evidence(monkeypatch):
    config = LLMConfig(
        provider="openai_chatgpt_plan", model="gpt-6-sol", max_tokens=2048
    )
    prompt = RefusalRecoveryPrompt(
        "scoped system", "scoped opening", "web-test-lead-v1"
    )
    seen = []
    events = []

    async def fake_call(_config, system, messages, tools=None):
        seen.append((system, messages))
        if len(seen) == 1:
            return _tool("http_request", "probe-1")
        if len(seen) in (2, 3):
            raise ChatGPTCyberError()
        assert any("baseline result" in str(m.get("content")) for m in messages)
        return _done("moved on")

    async def execute(_name, _args, _step):
        return "baseline result"

    monkeypatch.setattr(llm, "_call_with_tools", fake_call)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="original system",
            initial_user_message="original opening",
            tool_executor=execute,
            refusal_recovery_prompt=prompt,
            emit_fn=events.append,
        )
    )
    assert summary == "moved on"
    assert len(seen) == 4
    assert any(
        event.get("data", {}).get("refusal_recovery") == "refused"
        and "unresolved" in event.get("message", "")
        for event in events
    )


def test_codex_closes_refused_thread_before_scoped_retry(monkeypatch):
    config = LLMConfig(provider="openai_codex", model="gpt-6-sol", max_tokens=2048)
    prompt = RefusalRecoveryPrompt(
        "scoped system", "scoped opening", "web-test-lead-v1"
    )
    calls = []
    closed = []

    async def fake_call(_config, system, messages, tools=None):
        calls.append((system, messages))
        if len(calls) == 1:
            raise codex_provider.CodexCyberPolicyError(
                '{"error": {"message": "This content was flagged for possible cybersecurity risk."}}'
            )
        return _done()

    async def close(messages):
        closed.append(messages)

    async def execute(_name, _args, _step):
        return "ok"

    monkeypatch.setattr(llm, "_call_with_tools", fake_call)
    monkeypatch.setattr(codex_provider, "close_conversation", close)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="original system",
            initial_user_message="original opening",
            tool_executor=execute,
            refusal_recovery_prompt=prompt,
        )
    )
    assert summary == "complete"
    assert calls[0][0] == "original system"
    assert calls[1][0] == "scoped system"
    assert calls[0][1] is not calls[1][1]
    assert closed[0] is calls[0][1]
    assert closed[-1] is calls[1][1]


def test_checkpoint_failure_prevents_scoped_retry(monkeypatch):
    config = LLMConfig(
        provider="openai_chatgpt_plan", model="gpt-6-sol", max_tokens=2048
    )
    prompt = RefusalRecoveryPrompt(
        "scoped system", "scoped opening", "web-test-lead-v1"
    )
    calls = 0

    async def fake_call(_config, _system, _messages, tools=None):
        nonlocal calls
        calls += 1
        raise ChatGPTCyberError()

    async def fail_save(_messages, _step):
        raise OSError("checkpoint unavailable")

    monkeypatch.setattr(llm, "_call_with_tools", fake_call)
    with pytest.raises(OSError, match="checkpoint unavailable"):
        asyncio.run(
            llm.thinking_agentic_loop(
                config,
                system_message="original system",
                initial_user_message="original opening",
                tool_executor=lambda *_args: None,
                refusal_recovery_prompt=prompt,
                on_recovery_checkpoint=fail_save,
            )
        )
    assert calls == 1
