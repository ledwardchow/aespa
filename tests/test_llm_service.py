import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

from aespa.models import LLMConfig
from aespa.services import llm


def test_agentic_context_compaction_preserves_recent_tool_pairs():
    messages = [{"role": "user", "content": "initial brief"}]
    for index in range(50):
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": f"call-{index}",
                        "name": "http_request",
                        "input": {
                            "method": "GET",
                            "url": f"https://target.local/api/items/{index}",
                            "secret": "must-not-enter-journal",
                        },
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
                        "tool_use_id": f"call-{index}",
                        "content": "Status: 200 " + ("x" * 1500),
                    }
                ],
            }
        )

    compacted, stats = llm.compact_agentic_messages(
        messages, max_context_chars=30_000, recent_messages=12
    )

    assert stats is not None
    assert stats["after_chars"] < stats["before_chars"]
    assert compacted[0]["role"] == "user"
    assert "CONTEXT JOURNAL" in str(compacted[0]["content"])
    assert "must-not-enter-journal" not in str(compacted[0]["content"])
    assert compacted[1]["role"] == "assistant"
    assert compacted[-1]["role"] == "user"


def test_limiter_oversized_estimate_does_not_hang():
    # A single request estimated larger than the entire per-minute budget must
    # not loop forever waiting for capacity that can never exist. Pre-fix, this
    # spun in acquire() until the timeout.
    limiter = llm.AsyncTokenBucketLimiter(tpm=1000)
    slept = asyncio.run(asyncio.wait_for(limiter.acquire(10_000), timeout=5))
    assert slept is False  # clamped to max_tokens; the full bucket satisfies it at once


def test_limiter_on_wait_fires_when_pacing():
    # When the bucket is empty the next acquire must pace, and on_wait must fire
    # (before the sleep) so callers can tell the user it is not stuck.
    limiter = llm.AsyncTokenBucketLimiter(tpm=6000)  # 100 tokens/sec
    waits: list[float] = []

    async def _run():
        await limiter.acquire(6000)  # drain the bucket
        await limiter.acquire(50, on_wait=lambda wt: waits.append(wt))  # ~0.5s pace

    asyncio.run(asyncio.wait_for(_run(), timeout=10))
    assert waits and waits[0] > 0


def test_limiter_reconcile_only_credits_what_was_reserved():
    # An oversized estimate reserves at most max_tokens; reconcile must credit back
    # only the reserved amount, not the unclamped estimate.
    limiter = llm.AsyncTokenBucketLimiter(tpm=1000)

    async def _run():
        await limiter.acquire(10_000)  # clamps to 1000, drains bucket to ~0
        await limiter.reconcile(10_000, 100)  # used 100 of 1000 reserved → credit ~900
        return limiter.available_tokens

    avail = asyncio.run(_run())
    assert 850 <= avail <= 1000


def test_agentic_loop_recovers_from_text_only_turn(monkeypatch):
    config = LLMConfig(
        provider="azure_foundry_openai",
        api_key="test-key",
        base_url="https://example.services.ai.azure.com",
        model="gpt-5.4",
        max_tokens=2048,
        temperature=0.0,
    )
    calls: list[list[dict]] = []
    executed: list[tuple[str, dict, int]] = []

    async def fake_call_with_tools(config_arg, system_message, messages, tools=None):
        calls.append(messages)
        if len(calls) == 1:
            block = {
                "type": "text",
                "id": None,
                "name": None,
                "input": None,
                "text": "I should inspect the site map next.",
            }
            return [block], "end_turn", [block]
        if len(calls) == 2:
            block = {
                "type": "tool_use",
                "id": "call_1",
                "name": "context_tool",
                "input": {"tool": "site_map", "args": {"limit": 5}},
                "text": None,
            }
            return [block], "tool_use", [block]
        block = {
            "type": "tool_use",
            "id": "call_2",
            "name": "done",
            "input": {"summary": "Complete."},
            "text": None,
        }
        return [block], "tool_use", [block]

    async def fake_tool_executor(name, tool_input, step):
        executed.append((name, tool_input, step))
        return "site map result"

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)

    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="start",
            tool_executor=fake_tool_executor,
        )
    )

    assert summary == "Complete."
    assert executed == [("context_tool", {"tool": "site_map", "args": {"limit": 5}}, 1)]
    correction_messages = [
        msg
        for msg in calls[1]
        if msg["role"] == "user"
        and isinstance(msg["content"], list)
        and msg["content"][0].get("type") == "text"
    ]
    assert "did not call a tool" in correction_messages[-1]["content"][0]["text"]


def test_agentic_loop_can_reject_premature_done(monkeypatch):
    config = LLMConfig(
        provider="azure_foundry_openai",
        api_key="test-key",
        base_url="https://example.services.ai.azure.com",
        model="gpt-5.4",
        max_tokens=2048,
        temperature=0.0,
    )
    executed: list[tuple[str, dict, int]] = []
    done_attempts = 0

    async def fake_call_with_tools(config_arg, system_message, messages, tools=None):
        nonlocal done_attempts
        if done_attempts == 0:
            done_attempts += 1
            block = {
                "type": "tool_use",
                "id": "call_done_1",
                "name": "done",
                "input": {"summary": "Finished."},
                "text": None,
            }
            return [block], "tool_use", [block]
        if not executed:
            assert "not complete" in messages[-1]["content"][0]["content"]
            block = {
                "type": "tool_use",
                "id": "call_1",
                "name": "http_request",
                "input": {
                    "method": "GET",
                    "url": "https://target.local/api/profile",
                    "use_session": "customer_1",
                },
                "text": None,
            }
            return [block], "tool_use", [block]
        block = {
            "type": "tool_use",
            "id": "call_done_2",
            "name": "done",
            "input": {"summary": "Really complete."},
            "text": None,
        }
        return [block], "tool_use", [block]

    async def fake_tool_executor(name, tool_input, step):
        executed.append((name, tool_input, step))
        return "Status: 200"

    def done_check(tool_input, step):
        return (bool(executed), "" if executed else "Assessment is not complete.")

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)

    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="start",
            tool_executor=fake_tool_executor,
            done_check=done_check,
        )
    )

    assert summary == "Really complete."
    assert executed == [
        (
            "http_request",
            {
                "method": "GET",
                "url": "https://target.local/api/profile",
                "use_session": "customer_1",
            },
            2,
        )
    ]


def test_agentic_loop_checkpoints_nonempty_assistant_turns(monkeypatch):
    config = LLMConfig(
        provider="bedrock",
        model="anthropic.claude-opus-test",
        max_tokens=2048,
    )
    checkpoints: list[list[dict]] = []
    calls = 0

    async def fake_call_with_tools(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return [], "end_turn", []
        done = {
            "type": "tool_use",
            "id": "done-1",
            "name": "done",
            "input": {"summary": "complete"},
            "text": None,
        }
        return [done], "tool_use", [done]

    async def checkpoint(messages):
        checkpoints.append(messages.copy())

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="start",
            tool_executor=lambda *args: None,
            on_checkpoint=checkpoint,
        )
    )

    assert summary == "complete"
    assistant_messages = [
        message for message in checkpoints[-1] if message["role"] == "assistant"
    ]
    assert all(message["content"] for message in assistant_messages)
    assert assistant_messages[0]["content"][0]["text"] == (
        "[The model returned no usable content blocks.]"
    )


def test_agentic_loop_logs_native_stop_and_terminal_no_tool_failure(monkeypatch):
    config = LLMConfig(
        provider="bedrock",
        model="global.anthropic.claude-opus-test",
        max_tokens=2048,
    )
    emitted: list[dict] = []

    async def fake_call_with_tools(*args, **kwargs):
        diagnostic = {
            "type": "provider_diagnostic",
            "provider": "bedrock",
            "model": config.model,
            "native_stop_reason": "guardrail_intervened",
            "transport": {"request_id": "request-123", "http_status": 200},
        }
        return [], "guardrail_intervened", [diagnostic]

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)

    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="start",
            tool_executor=lambda *args: None,
            emit_fn=emitted.append,
        )
    )

    assert summary == ""
    warnings = [
        event
        for event in emitted
        if event.get("phase") == "llm_response" and event.get("status") == "warning"
    ]
    assert len(warnings) == 3
    assert warnings[0]["data"]["native_stop_reason"] == "guardrail_intervened"
    assert warnings[0]["data"]["no_tool_retry"] == 1
    assert warnings[0]["data"]["provider_diagnostics"][0]["transport"] == {
        "request_id": "request-123",
        "http_status": 200,
    }
    terminal = [event for event in emitted if event.get("phase") == "llm_protocol"]
    assert len(terminal) == 1
    assert terminal[0]["status"] == "error"
    assert terminal[0]["data"]["termination_reason"] == (
        "consecutive_no_tool_responses"
    )
    assert terminal[0]["data"]["explicit_done"] is False


def test_agentic_loop_repairs_trailing_assistant_checkpoint_on_resume(monkeypatch):
    config = LLMConfig(
        provider="bedrock",
        model="global.anthropic.claude-opus-test",
        max_tokens=2048,
    )
    emitted: list[dict] = []
    captured_messages: list[dict] = []

    async def fake_call_with_tools(config_arg, system_message, messages, tools=None):
        captured_messages.extend(messages)
        done = {
            "type": "tool_use",
            "id": "done-after-resume",
            "name": "done",
            "input": {"summary": "resumed"},
            "text": None,
        }
        return [done], "tool_use", [done]

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="unused",
            tool_executor=lambda *args: None,
            emit_fn=emitted.append,
            resume_messages=[
                {"role": "user", "content": "start"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "provider_diagnostic",
                            "native_stop_reason": "guardrail_intervened",
                        }
                    ],
                },
            ],
        )
    )

    assert summary == "resumed"
    assert captured_messages[-1]["role"] == "user"
    assert (
        "previous model turn ended"
        in captured_messages[-1]["content"][0]["text"].lower()
    )
    repair_events = [
        event
        for event in emitted
        if event.get("phase") == "llm_protocol" and event.get("status") == "warning"
    ]
    assert repair_events[0]["data"]["repair_kind"] == "trailing_assistant_turn"


def test_agentic_loop_repairs_interrupted_tool_checkpoint_on_resume(monkeypatch):
    captured_messages: list[dict] = []

    async def fake_call_with_tools(config_arg, system_message, messages, tools=None):
        captured_messages.extend(messages)
        done = {
            "type": "tool_use",
            "id": "done-after-tool-repair",
            "name": "done",
            "input": {"summary": "resumed"},
            "text": None,
        }
        return [done], "tool_use", [done]

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)
    config = LLMConfig(provider="bedrock", model="opus-test", max_tokens=2048)
    asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="unused",
            tool_executor=lambda *args: None,
            resume_messages=[
                {"role": "user", "content": "start"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "interrupted-call",
                            "name": "http_request",
                            "input": {"url": "https://target.local"},
                        }
                    ],
                },
            ],
        )
    )

    repair = captured_messages[-1]
    assert repair["role"] == "user"
    assert repair["content"][0]["type"] == "tool_result"
    assert repair["content"][0]["tool_use_id"] == "interrupted-call"


def test_agentic_loop_applies_result_hook_and_bounded_termination(monkeypatch):
    config = LLMConfig(
        provider="openai",
        api_key="test-key",
        model="gpt-test",
        max_tokens=2048,
    )
    llm_calls = 0
    executed = 0

    async def fake_call_with_tools(*args, **kwargs):
        nonlocal llm_calls
        llm_calls += 1
        block = {
            "type": "tool_use",
            "id": "call-1",
            "name": "context_tool",
            "input": {"tool": "site_map"},
            "text": None,
        }
        return [block], "tool_use", [block]

    async def executor(*args):
        nonlocal executed
        executed += 1
        return "result"

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="start",
            tool_executor=executor,
            after_tool_result=lambda _n, _i, result, _s: result + " annotated",
            termination_check=lambda: "stagnant" if executed else None,
        )
    )

    assert summary == "stagnant"
    assert llm_calls == 1
    assert executed == 1


def test_agentic_loop_accounts_for_blocked_steps_and_augments_tool_schema(monkeypatch):
    config = LLMConfig(
        provider="openai", api_key="test-key", model="gpt-test", max_tokens=2048
    )
    rejected = 0
    executed = 0

    async def fake_call_with_tools(*args, **kwargs):
        properties = kwargs["tools"][0]["input_schema"]["properties"]
        assert "strategy_pivot_justification" in properties
        block = {
            "type": "tool_use",
            "id": f"call-{rejected}",
            "name": "http_request",
            "input": {"method": "GET", "url": "http://target.local/a"},
            "text": None,
        }
        return [block], "tool_use", [block]

    async def executor(*_args):
        nonlocal executed
        executed += 1
        return "unexpected"

    async def before(*_args):
        return "block", "blocked", None

    def after_rejection(_name, _input, result, _step):
        nonlocal rejected
        rejected += 1
        return result

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)
    summary = asyncio.run(
        llm.thinking_agentic_loop(
            config,
            system_message="system",
            initial_user_message="start",
            tool_executor=executor,
            tools=[
                {
                    "name": "http_request",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
            before_tool_execution=before,
            after_tool_rejection=after_rejection,
            termination_check=lambda: "bounded rejection" if rejected >= 2 else None,
        )
    )

    assert summary == "bounded rejection"
    assert rejected == 2
    assert executed == 0


def test_agentic_loop_raises_provider_refusal_instead_of_finishing(monkeypatch):
    config = LLMConfig(
        provider="azure_foundry_openai",
        api_key="test-key",
        base_url="https://example.services.ai.azure.com",
        model="gpt-5.6-sol",
        max_tokens=2048,
    )
    emitted: list[dict] = []

    async def fake_call_with_tools(*args, **kwargs):
        raise RuntimeError(
            "Error code: 400 - {'error': {'message': 'This content was flagged "
            "for possible cybersecurity risk.', 'code': 'cyber_policy'}}"
        )

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)

    with pytest.raises(llm.LLMRefusalError, match="cybersecurity risk"):
        asyncio.run(
            llm.thinking_agentic_loop(
                config,
                system_message="system",
                initial_user_message="start",
                tool_executor=lambda *args: None,
                emit_fn=emitted.append,
            )
        )

    refusal_events = [
        event
        for event in emitted
        if event.get("phase") == "llm_response" and event.get("status") == "error"
    ]
    assert len(refusal_events) == 1
    assert "provider refused" in refusal_events[0]["message"]


def test_agentic_loop_propagates_explicit_provider_refusal(monkeypatch):
    config = LLMConfig(
        provider="openai",
        api_key="test-key",
        model="gpt-test",
        max_tokens=2048,
    )

    async def fake_call_with_tools(*args, **kwargs):
        raise llm.LLMRefusalError("LLM provider refusal: request declined")

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)

    with pytest.raises(llm.LLMRefusalError, match="request declined"):
        asyncio.run(
            llm.thinking_agentic_loop(
                config,
                system_message="system",
                initial_user_message="start",
                tool_executor=lambda *args: None,
            )
        )


def test_agentic_loop_propagates_generic_api_error_instead_of_completing(monkeypatch):
    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        model="anthropic.claude-opus-test",
        max_tokens=2048,
    )
    emitted: list[dict] = []

    async def fake_call_with_tools(*args, **kwargs):
        raise RuntimeError("ValidationException: messages.51 content is empty")

    monkeypatch.setattr(llm, "_call_with_tools", fake_call_with_tools)

    with pytest.raises(RuntimeError, match="content is empty"):
        asyncio.run(
            llm.thinking_agentic_loop(
                config,
                system_message="system",
                initial_user_message="start",
                tool_executor=lambda *args: None,
                emit_fn=emitted.append,
            )
        )

    error_events = [
        event
        for event in emitted
        if event.get("phase") == "llm_response" and event.get("status") == "error"
    ]
    assert len(error_events) == 1
    assert "LLM API error" in error_events[0]["message"]


def test_openrouter_call_uses_openrouter_base_url(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["completion"] = kwargs
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="openrouter",
        api_key="sk-or-v1-test",
        model="openrouter/owl-alpha",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert {
        "api_key": "sk-or-v1-test",
        "base_url": llm.OPENROUTER_BASE_URL,
    }.items() <= captured["client"].items()
    assert captured["completion"] == {
        "model": "openrouter/owl-alpha",
        "max_tokens": 2048,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_azure_foundry_openai_call_uses_openai_v1_base_url(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["completion"] = kwargs
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="azure_foundry_openai",
        api_key="foundry-key",
        base_url="https://myresource.services.ai.azure.com",
        model="gpt-4o",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert {
        "api_key": "foundry-key",
        "base_url": "https://myresource.services.ai.azure.com/openai/v1",
    }.items() <= captured["client"].items()
    assert captured["completion"] == {
        "model": "gpt-4o",
        "max_tokens": 2048,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_legacy_azure_foundry_call_uses_openai_mode(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["completion"] = kwargs
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="azure_foundry",
        api_key="foundry-key",
        base_url="https://models.inference.ai.azure.com",
        model="Meta-Llama-3.3-70B-Instruct",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert captured["client"]["base_url"] == "https://models.inference.ai.azure.com/v1"


def test_azure_foundry_anthropic_call_uses_messages_api(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"content": [{"type": "text", "text": "ok"}]}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["post"] = kwargs
            return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    config = LLMConfig(
        provider="azure_foundry_anthropic",
        api_key="foundry-key",
        base_url="https://myresource.services.ai.azure.com",
        model="claude-sonnet-4-5",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert {"timeout": 120}.items() <= captured["client"].items()
    assert (
        captured["url"]
        == "https://myresource.services.ai.azure.com/anthropic/v1/messages"
    )
    assert captured["post"]["headers"]["x-api-key"] == "foundry-key"
    assert "api-key" not in captured["post"]["headers"]
    assert captured["post"]["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["post"]["json"] == {
        "model": "claude-sonnet-4-5",
        "max_tokens": 2048,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    }


def test_extract_json_ignores_visible_thinking_blocks():
    raw = """
<thinking>
I should inspect the page and then produce the requested object.
</thinking>
```json
{"context": "Account overview", "suggested_links": [], "categories": {"req_auth": true}}
```
"""

    data = llm._extract_json(raw, expect=dict)

    assert data["context"] == "Account overview"
    assert data["categories"]["req_auth"] is True


def test_extract_json_skips_invalid_reasoning_container():
    raw = """
I considered a Python-ish dict first: {'not': 'json'}.
The final answer is {"context": "Real JSON", "suggested_links": []}.
"""

    data = llm._extract_json(raw, expect=dict)

    assert data["context"] == "Real JSON"


def test_extract_json_handles_unclosed_think_tag_and_template_example():
    raw = """<think>
Let me analyze the original finding and rewrite it.
Looking at the template:
{
  "owasp_category": "A03",
  "title": "Short, report-ready title",
  "description": "What is vulnerable and where."
}
Let me write the real report-ready version.
Final output:{
  "owasp_category": "A05",
  "title": "Permissive CORS policy reflects arbitrary Origin header",
  "description": "The API at http://192.168.3.101/ applies a permissive CORS policy."
}"""

    data = llm._extract_json(raw, expect=dict)

    assert data["owasp_category"] == "A05"
    assert data["title"] == "Permissive CORS policy reflects arbitrary Origin header"


def test_page_analysis_parses_compact_function_label():
    _context, _links, categories = llm._parse(
        '{"page_label":"Register for Internet Banking today now",'
        '"context":"Registration form", "suggested_links": [], "categories": {}}',
        "https://target.local/register",
    )

    assert categories["page_label"] == "Register for Internet Banking today"


def test_extract_message_text_uses_final_content_before_reasoning():
    message = SimpleNamespace(
        reasoning_content='{"context":"wrong"}',
        content=[
            SimpleNamespace(type="reasoning", text="working..."),
            {"type": "text", "text": '{"context":"right"}'},
        ],
    )

    assert llm._extract_message_text(message) == '{"context":"right"}'


def test_extract_message_text_falls_back_to_reasoning_content():
    message = SimpleNamespace(
        content=None,
        reasoning_content='<think>scratchpad</think>{"context":"from fallback"}',
    )

    assert llm._extract_message_text(message) == '{"context":"from fallback"}'


def test_extract_message_text_falls_back_when_content_json_is_truncated():
    message = SimpleNamespace(
        content='[\n  {"owasp_category": "A03", "title": "partial", "cvss_vector": "CVSS:3.1/AV:N',
        reasoning_content="""
The final answer was:
```json
[
  {
    "owasp_category": "A03",
    "severity": "medium",
    "title": "Reflected XSS in Query Parameter",
    "description": "The q parameter is reflected without encoding.",
    "impact": "An attacker can execute script in another user's browser.",
    "likelihood": "Likely if a victim opens an attacker-controlled URL.",
    "recommendation": "Encode reflected output and validate the parameter.",
    "cvss_score": 6.1,
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
    "affected_url": "http://localhost:3000/assets/i18n/en.json?q=%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
    "evidence": "Payload is reflected in the response."
  }
]
```
""",
    )

    extracted = llm._extract_message_text(message)

    assert (
        llm._extract_json(extracted, expect=list)[0]["title"]
        == "Reflected XSS in Query Parameter"
    )


def test_thinking_next_action_prompt_requires_investigation_context(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_call(config, prompt, screenshot_b64):
        captured["prompt"] = prompt
        return """{
          "action": "http",
          "method": "GET",
          "url": "https://target.local/search?q=test",
          "headers": {},
          "body": null,
          "observation": "search accepts a q parameter",
          "hypothesis": "reflected input handling in search",
          "payload_purpose": "baseline reflection probe",
          "note": "Probe search reflection before adding XSS payloads."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Application pages:\n  https://target.local/search [takes-input]",
            history=[],
            max_steps=80,
            current_step=1,
        )
    )

    assert action["observation"] == "search accepts a q parameter"
    assert "observation" in captured["prompt"]
    assert "hypothesis" in captured["prompt"]
    assert "payload_purpose" in captured["prompt"]
    assert "found something interesting" in captured["prompt"]
    assert "Raw asset and JavaScript mining" in captured["prompt"]
    assert "endpoint inventory" in captured["prompt"]
    assert "admin/admin123" in captured["prompt"]
    assert "Business-logic gate bypass" in captured["prompt"]
    assert (
        "actual action endpoint directly without the required field"
        in captured["prompt"]
    )
    assert "individual detail endpoints" in captured["prompt"]
    assert "SQL error disclosure" in captured["prompt"]
    assert "/api/health" in captured["prompt"]
    assert "jwt_secret" in captured["prompt"]
    assert "CORS" in captured["prompt"]
    assert "Rate CORS arbitrary Origin reflection" in captured["prompt"]
    assert "loan/account creation rules" in captured["prompt"]
    assert '"action": "browser"' in captured["prompt"]
    assert '"action": "jwt"' in captured["prompt"]
    assert '"action": "credential_check"' in captured["prompt"]
    assert "Maximum 20 candidates" in captured["prompt"]
    assert "use_session" in captured["prompt"]
    assert (
        "Supported ops: goto, fill, type, click, press, wait, snapshot"
        in captured["prompt"]
    )


def test_thinking_next_action_history_includes_response_headers(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_call(config, prompt, screenshot_b64):
        captured["prompt"] = prompt
        return """{
          "action": "http",
          "method": "GET",
          "url": "https://target.local/admin/",
          "headers": {},
          "body": null,
          "observation": "homepage linked an admin panel",
          "hypothesis": "admin panel may expose auth or asset clues",
          "payload_purpose": null,
          "note": "Fetch the admin panel after discovering the public link."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Application pages:\n  https://target.local/",
            history=[
                {
                    "step": 1,
                    "method": "GET",
                    "url": "https://target.local/",
                    "note": "Initial fingerprinting",
                    "request_body": None,
                    "response_status": 200,
                    "response_headers": {
                        "content-type": "text/html",
                        "x-frame-options": "DENY",
                    },
                    "response_body": '<a href="/admin/">Admin</a>',
                }
            ],
            sessions=[
                {
                    "label": "found_admin_1",
                    "kind": "bearer",
                    "username": "admin",
                    "source": "credential_check",
                }
            ],
            max_steps=120,
            current_step=2,
        )
    )

    assert action["url"] == "https://target.local/admin/"
    assert "Response headers:" in captured["prompt"]
    assert "x-frame-options" in captured["prompt"]
    assert "content-type" in captured["prompt"]
    assert "found_admin_1" in captured["prompt"]
    assert (
        "found_admin_1" in captured["prompt"]
    )  # session label present in sessions section


def test_thinking_next_action_compacts_large_history(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_call(config, prompt, screenshot_b64):
        captured["prompt"] = prompt
        return """{
          "action": "tool",
          "tool": "history_search",
          "args": {"query": "password_hash", "limit": 3},
          "observation": "Earlier responses were summarized.",
          "hypothesis": "A previous response may contain evidence worth reviewing.",
          "payload_purpose": "Retrieve targeted history instead of resending all bodies.",
          "note": "Search history for the sensitive field before writing a finding."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    history = [
        {
            "step": i,
            "method": "GET",
            "url": f"https://target.local/api/{i}",
            "note": "Large response",
            "request_body": None,
            "response_status": 200,
            "response_headers": {"content-type": "application/json"},
            "response_body": "x" * 5000,
        }
        for i in range(20)
    ]

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Target: https://target.local",
            history=history,
            max_steps=120,
            current_step=21,
        )
    )

    assert action["action"] == "tool"
    assert len(captured["prompt"]) < 35_000
    assert "Earlier history: 15 step(s) summarized" in captured["prompt"]
    assert "Use history_search to retrieve details" in captured["prompt"]


def test_thinking_next_action_accepts_browser_action(monkeypatch):
    async def fake_call(config, prompt, screenshot_b64):
        return """{
          "action": "browser",
          "url": "https://target.local/banking/#/login",
          "steps": [
            {"op": "goto", "url": "https://target.local/banking/#/login"},
            {"op": "fill", "selector": "input[name='email']", "value": "test@example.com"},
            {"op": "fill", "selector": "input[name='password']", "value": "password123"},
            {"op": "click", "selector": "button[type='submit']"},
            {"op": "wait", "state": "networkidle"},
            {"op": "snapshot"}
          ],
          "observation": "The login flow is client-side rendered behind a hash route.",
          "hypothesis": "Browser execution may reveal authenticated API calls or DOM-only routes.",
          "payload_purpose": "Exercise the JS login form instead of guessing API behavior.",
          "note": "Use Playwright to execute the SPA login route and capture DOM/network evidence."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Application pages:\n  https://target.local/banking/#/login [takes-input]",
            history=[],
            max_steps=120,
            current_step=1,
        )
    )

    assert action["action"] == "browser"
    assert action["steps"][0]["op"] == "goto"
    assert action["steps"][-1]["op"] == "snapshot"


def test_thinking_next_action_accepts_jwt_action(monkeypatch):
    async def fake_call(config, prompt, screenshot_b64):
        return """{
          "action": "jwt",
          "secret": "test-secret",
          "claims": {"iss": "BankOfEd", "sub": 1, "jti": "aespa-test"},
          "header": {"typ": "JWT", "alg": "HS256"},
          "store_as": "customer_sub_1_token",
          "observation": "/api/health exposed jwt_secret.",
          "hypothesis": "The API may trust HS256 tokens signed with that secret.",
          "payload_purpose": "Create a controlled read-only impersonation token.",
          "note": "Forge a customer token, then use it on /api/profile."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="API endpoints:\n  https://target.local/api/health",
            history=[],
            max_steps=120,
            current_step=1,
        )
    )

    assert action["action"] == "jwt"
    assert action["claims"]["sub"] == 1
    assert action["store_as"] == "customer_sub_1_token"


def test_thinking_next_action_accepts_credential_check_action(monkeypatch):
    async def fake_call(config, prompt, screenshot_b64):
        return """{
          "action": "credential_check",
          "url": "https://target.local/api/admin/auth/login",
          "method": "POST",
          "username_field": "username",
          "password_field": "password",
          "candidates": [
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "admin123"}
          ],
          "headers": {"Content-Type": "application/json"},
          "success_statuses": [200],
          "observation": "The public admin login uses a default username placeholder.",
          "hypothesis": "The demo admin account may still use a seeded password.",
          "payload_purpose": "Try a tiny bounded dictionary, not brute force.",
          "note": "Check two obvious admin credentials and record any success."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Application pages:\n  https://target.local/admin/",
            history=[],
            max_steps=120,
            current_step=1,
        )
    )

    assert action["action"] == "credential_check"
    assert len(action["candidates"]) == 2
    assert action["candidates"][1]["password"] == "admin123"


def test_thinking_next_action_accepts_context_tool_action(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_call(config, prompt, screenshot_b64):
        captured["prompt"] = prompt
        return """{
          "action": "tool",
          "tool": "site_map",
          "args": {"filter": "api takes-input", "limit": 10},
          "observation": "Need endpoint inventory before probing.",
          "hypothesis": "Input-taking APIs are likely high-value targets.",
          "payload_purpose": "Fetch targeted crawl context.",
          "note": "Fetch the API site map before choosing a probe."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Crawl summary: 20 pages. Use context tools for details.",
            history=[],
            max_steps=120,
            current_step=1,
        )
    )

    assert action["action"] == "tool"
    assert action["tool"] == "site_map"
    assert action["args"]["limit"] == 10
    assert "Context tools:" in captured["prompt"]
    assert "context_budget_reason" in captured["prompt"]
    assert "adaptive checkpoint" in captured["prompt"]
    assert "page_detail" in captured["prompt"]
    assert "history_search" in captured["prompt"]


def test_thinking_next_action_normalizes_context_tool_alias(monkeypatch):
    async def fake_call(config, prompt, screenshot_b64):
        return """
Looking at the history, I need to search prior responses.

```json
{
  "action": "history_search",
  "query": "jwt secret signing key",
  "limit": 5,
  "observation": "The previous response was truncated.",
  "hypothesis": "A JWT secret may have appeared in prior response history.",
  "payload_purpose": "Search prior response history before making another request.",
  "note": "Search history for a JWT secret."
}
```
"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Crawl summary: compact.",
            history=[],
            max_steps=120,
            current_step=1,
        )
    )

    assert action["action"] == "tool"
    assert action["tool"] == "history_search"
    assert action["args"] == {"query": "jwt secret signing key", "limit": 5}
    assert action["note"] == "Search history for a JWT secret."


def test_thinking_next_action_accepts_finding_write_action(monkeypatch):
    async def fake_call(config, prompt, screenshot_b64):
        return """{
          "action": "finding_write",
          "owasp_category": "A05",
          "title": "Verbose debug configuration disclosure",
          "description": "The health endpoint exposes debug configuration.",
          "impact": "Attackers can use leaked implementation details.",
          "likelihood": "Likely because the endpoint is public.",
          "recommendation": "Remove debug fields from public responses.",
          "cvss_score": 5.3,
          "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
          "severity": "medium",
          "affected_url": "https://target.local/api/health",
          "evidence": "Step 2 returned debug=true.",
          "request_evidence": "GET https://target.local/api/health",
          "response_evidence": "Status: 200\\n{debug:true}",
          "observation": "The response exposed debug mode.",
          "hypothesis": "This is a confirmed info disclosure.",
          "payload_purpose": "Persist the finding.",
          "note": "Record the confirmed debug disclosure."
        }"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    action = asyncio.run(
        llm.thinking_next_action(
            config,
            target_url="https://target.local",
            crawl_context="Crawl summary: compact.",
            history=[],
            max_steps=120,
            current_step=3,
        )
    )

    assert action["action"] == "finding_write"
    assert action["title"] == "Verbose debug configuration disclosure"
    assert action["affected_url"] == "https://target.local/api/health"


def test_followup_prompt_requires_interesting_result_and_hypothesis(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_call(config, prompt, screenshot_b64):
        captured["prompt"] = prompt
        return """[
                    {
                        "type": "http",
                        "method": "POST",
                        "url": "https://target.local/api/transfers",
                        "params": {},
                        "headers": {},
                        "body": {"amount":100},
                        "as_user": null,
                        "interesting_result": "2FA check returned requires_2fa=true",
                        "hypothesis": "transfer endpoint may not enforce 2FA server-side",
                        "payload_purpose": "omit 2FA token",
                        "desc": "Follow-up: submit transfer without 2FA."
                    }
                ]"""

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    probes = asyncio.run(
        llm.plan_followup_probes(
            config,
            "https://target.local/transfer",
            "Transfer page",
            [
                {
                    "desc": "2FA check",
                    "url": "https://target.local/api/transfer/check",
                    "status": 200,
                    "body": '{"requires_2fa":true}',
                    "response_evidence": "Status: 200\nrequires_2fa=true",
                }
            ],
        )
    )

    assert probes[0]["interesting_result"].startswith("2FA check")
    assert "interesting_result" in captured["prompt"]
    assert "hypothesis" in captured["prompt"]
    assert "payload_purpose" in captured["prompt"]
    assert "looked interesting" in captured["prompt"]


def test_openai_reasoning_models_use_completion_tokens_and_default_temperature(
    monkeypatch,
):
    captured: dict[str, object] = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["completion"] = kwargs
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="openai",
        api_key="sk-test",
        model="o3-mini",
        max_tokens=2048,
        temperature=0.7,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert captured["completion"] == {
        "model": "o3-mini",
        "max_completion_tokens": 2048,
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_openai_caching_tokens_extraction_and_recording(monkeypatch):
    recorded_usages = []

    def fake_record_usage(
        model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0
    ):
        recorded_usages.append(
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
            }
        )

    monkeypatch.setattr(llm, "_record_usage", fake_record_usage)

    class FakeCompletions:
        async def create(self, **kwargs):
            message = SimpleNamespace(content="ok")
            usage = SimpleNamespace(
                prompt_tokens=1500,
                completion_tokens=200,
                prompt_tokens_details=SimpleNamespace(cached_tokens=800),
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)], usage=usage
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="openai",
        api_key="sk-test",
        model="gpt-4o",
        max_tokens=2048,
        temperature=0.7,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert len(recorded_usages) == 1
    assert recorded_usages[0] == {
        "model": "gpt-4o",
        "input_tokens": 1500,
        "output_tokens": 200,
        "cache_read_tokens": 800,
        "cache_write_tokens": 0,
    }


def test_openai_caching_tokens_extraction_missing_details(monkeypatch):
    recorded_usages = []

    def fake_record_usage(
        model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0
    ):
        recorded_usages.append(
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
            }
        )

    monkeypatch.setattr(llm, "_record_usage", fake_record_usage)

    class FakeCompletions:
        async def create(self, **kwargs):
            message = SimpleNamespace(content="ok")
            usage = SimpleNamespace(
                prompt_tokens=1500, completion_tokens=200, prompt_tokens_details=None
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)], usage=usage
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="openai",
        api_key="sk-test",
        model="gpt-4o",
        max_tokens=2048,
        temperature=0.7,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert len(recorded_usages) == 1
    assert recorded_usages[0] == {
        "model": "gpt-4o",
        "input_tokens": 1500,
        "output_tokens": 200,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }


def test_openai_compatible_retries_reasoning_parameter_mismatch(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            captured["completion"] = kwargs
            if self.calls == 1:
                raise ValueError("unsupported parameter: max_tokens")
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="openai_compatible",
        api_key=None,
        base_url="http://localhost:1234",
        model="local-reasoning-model",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert captured["completion"] == {
        "model": "local-reasoning-model",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.0,
        "max_completion_tokens": 2048,
    }


def test_bedrock_call_uses_converse_api_key(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": {
                    "message": {
                        "content": [{"text": "ok"}],
                    },
                },
            }

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["request"] = kwargs
            return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    config = LLMConfig(
        provider="bedrock",
        api_key="bedrock-test-key",
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert {"timeout": 120}.items() <= captured["client"].items()
    assert captured["url"] == (
        "https://bedrock-runtime.us-east-1.amazonaws.com/model/"
        "anthropic.claude-3-7-sonnet-20250219-v1%3A0/converse"
    )
    assert captured["request"] == {
        "headers": {
            "Authorization": "Bearer bedrock-test-key",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        "json": {
            "messages": [{"role": "user", "content": [{"text": "hello"}]}],
            "inferenceConfig": {"maxTokens": 2048, "temperature": 0.0},
        },
    }


def test_bedrock_call_uses_aws_sdk_when_api_key_blank(monkeypatch):
    captured: dict[str, object] = {}

    class FakeBedrockClient:
        def converse(self, **kwargs):
            captured["converse"] = kwargs
            return {
                "output": {
                    "message": {
                        "content": [{"text": "ok"}],
                    },
                },
            }

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session"] = kwargs

        def client(self, service_name, **kwargs):
            captured["client"] = {"service_name": service_name, **kwargs}
            return FakeBedrockClient()

    fake_boto3 = SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("AWS_PROFILE", "bedrock-dev")
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert captured["session"] == {"profile_name": "bedrock-dev"}
    assert {
        "service_name": "bedrock-runtime",
        "region_name": "us-east-1",
        "endpoint_url": "https://bedrock-runtime.us-east-1.amazonaws.com",
    }.items() <= captured["client"].items()
    assert captured["converse"] == {
        "modelId": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "messages": [{"role": "user", "content": [{"text": "hello"}]}],
        "inferenceConfig": {"maxTokens": 2048, "temperature": 0.0},
    }


def test_bedrock_call_uses_boto3_default_endpoint_when_api_key_and_base_url_blank(
    monkeypatch,
):
    captured: dict[str, object] = {}

    class FakeBedrockClient:
        def converse(self, **kwargs):
            captured["converse"] = kwargs
            return {
                "output": {
                    "message": {
                        "content": [{"text": "ok"}],
                    },
                },
            }

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session"] = kwargs

        def client(self, service_name, **kwargs):
            captured["client"] = {"service_name": service_name, **kwargs}
            return FakeBedrockClient()

    fake_boto3 = SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_REGION", "ap-southeast-2")
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url=None,
        model="global.anthropic.claude-sonnet-4-6",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert captured["session"] == {}
    assert {
        "service_name": "bedrock-runtime",
        "region_name": "ap-southeast-2",
        "endpoint_url": None,
    }.items() <= captured["client"].items()
    assert captured["converse"]["modelId"] == "global.anthropic.claude-sonnet-4-6"


def _fake_mantle_response(text="ok"):
    """A minimal OpenAI Responses-API response object for Mantle tests."""
    return SimpleNamespace(
        output_text=text,
        output=[],
        usage=SimpleNamespace(
            input_tokens=0,
            output_tokens=0,
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        ),
    )


def _fake_mantle_openai(captured: dict):
    """Build a FakeOpenAI class that records client kwargs and responses.create calls."""

    class FakeResponses:
        async def create(self, **kwargs):
            captured["responses"] = kwargs
            return _fake_mantle_response()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = FakeResponses()

    return FakeOpenAI


def test_bedrock_mantle_uses_responses_api_with_us_east_2_default(monkeypatch):
    """Mantle drives the OpenAI Responses API; with no base_url it defaults to us-east-2."""
    captured: dict[str, object] = {}
    monkeypatch.setattr("openai.AsyncOpenAI", _fake_mantle_openai(captured))
    monkeypatch.delenv("BEDROCK_MANTLE_REGION", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    config = LLMConfig(
        provider="bedrock_mantle",
        api_key="bedrock-api-key",
        base_url=None,
        model="openai.gpt-oss-120b",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert {
        "api_key": "bedrock-api-key",
        "base_url": "https://bedrock-mantle.us-east-2.api.aws/v1",
    }.items() <= captured["client"].items()
    # Responses API uses `input`, not `messages`.
    assert captured["responses"]["model"] == "openai.gpt-oss-120b"
    assert captured["responses"]["input"] == "hello"


def test_bedrock_mantle_honours_explicit_base_url_and_region_env(monkeypatch):
    """An explicit base_url wins; otherwise the region env var selects the endpoint."""
    captured: dict[str, object] = {}
    monkeypatch.setattr("openai.AsyncOpenAI", _fake_mantle_openai(captured))
    monkeypatch.setenv("AWS_REGION", "us-west-2")

    # Region env var drives the endpoint when no base_url is configured.
    cfg_region = LLMConfig(
        provider="bedrock_mantle",
        api_key="k",
        base_url=None,
        model="openai.gpt-oss-120b",
        max_tokens=64,
    )
    asyncio.run(llm._call(cfg_region, "hi", None))
    assert (
        captured["client"]["base_url"] == "https://bedrock-mantle.us-west-2.api.aws/v1"
    )

    # An explicit base_url overrides region resolution (and gains the /v1 suffix).
    cfg_explicit = LLMConfig(
        provider="bedrock_mantle",
        api_key="k",
        base_url="https://bedrock-mantle.eu-west-1.api.aws",
        model="openai.gpt-oss-120b",
        max_tokens=64,
    )
    asyncio.run(llm._call(cfg_explicit, "hi", None))
    assert (
        captured["client"]["base_url"] == "https://bedrock-mantle.eu-west-1.api.aws/v1"
    )


def test_bedrock_mantle_frontier_model_uses_openai_v1_path(monkeypatch):
    """gpt-5.x frontier models are served on the /openai/v1 path; gpt-oss on /v1."""
    captured: dict[str, object] = {}
    monkeypatch.setattr("openai.AsyncOpenAI", _fake_mantle_openai(captured))
    monkeypatch.delenv("BEDROCK_MANTLE_REGION", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    frontier = LLMConfig(
        provider="bedrock_mantle",
        api_key="k",
        base_url=None,
        model="openai.gpt-5.5",
        max_tokens=64,
    )
    asyncio.run(llm._call(frontier, "hi", None))
    assert (
        captured["client"]["base_url"]
        == "https://bedrock-mantle.us-east-2.api.aws/openai/v1"
    )

    oss = LLMConfig(
        provider="bedrock_mantle",
        api_key="k",
        base_url=None,
        model="openai.gpt-oss-120b",
        max_tokens=64,
    )
    asyncio.run(llm._call(oss, "hi", None))
    assert (
        captured["client"]["base_url"] == "https://bedrock-mantle.us-east-2.api.aws/v1"
    )


def test_bedrock_mantle_rewrites_explicit_base_url_path_per_model(monkeypatch):
    """An explicit base_url keeps its host but its path suffix is normalised per model."""
    captured: dict[str, object] = {}
    monkeypatch.setattr("openai.AsyncOpenAI", _fake_mantle_openai(captured))

    # User typed the /v1 host, but selected a frontier model → rewritten to /openai/v1.
    cfg = LLMConfig(
        provider="bedrock_mantle",
        api_key="k",
        base_url="https://bedrock-mantle.us-east-2.api.aws/v1",
        model="openai.gpt-5.4",
        max_tokens=64,
    )
    asyncio.run(llm._call(cfg, "hi", None))
    assert (
        captured["client"]["base_url"]
        == "https://bedrock-mantle.us-east-2.api.aws/openai/v1"
    )


def test_bedrock_mantle_skips_temperature_for_reasoning_models(monkeypatch):
    """gpt-5.x reasoning models must not receive a custom temperature."""
    captured: dict[str, object] = {}
    monkeypatch.setattr("openai.AsyncOpenAI", _fake_mantle_openai(captured))
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    config = LLMConfig(
        provider="bedrock_mantle",
        api_key="k",
        base_url=None,
        model="openai.gpt-5.5",
        max_tokens=64,
        temperature=0.2,
    )
    asyncio.run(llm._call(config, "hi", None))
    assert "temperature" not in captured["responses"]


def test_bedrock_mantle_sends_project_id(monkeypatch):
    """A configured Mantle project id is passed to the SDK (OpenAI-Project header)."""
    captured: dict[str, object] = {}
    monkeypatch.setattr("openai.AsyncOpenAI", _fake_mantle_openai(captured))

    config = LLMConfig(
        provider="bedrock_mantle",
        api_key="bedrock-api-key",
        base_url=None,
        project_id="proj_5d5ykleja6cwpirysbb7",
        model="openai.gpt-oss-120b",
        max_tokens=64,
    )

    asyncio.run(llm._call(config, "hello", None))

    assert captured["client"]["project"] == "proj_5d5ykleja6cwpirysbb7"


def test_bedrock_mantle_omits_project_when_unset(monkeypatch):
    """No project kwarg is sent when no project id is configured."""
    captured: dict[str, object] = {}
    monkeypatch.setattr("openai.AsyncOpenAI", _fake_mantle_openai(captured))

    config = LLMConfig(
        provider="bedrock_mantle",
        api_key="bedrock-api-key",
        base_url=None,
        model="openai.gpt-oss-120b",
        max_tokens=64,
    )

    asyncio.run(llm._call(config, "hello", None))

    assert "project" not in captured["client"]


def test_mantle_message_translation_to_responses_items():
    """Anthropic-format history maps to Responses message/function_call(_output) items."""
    messages = [
        {"role": "user", "content": "start"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "thinking"},
                {
                    "type": "tool_use",
                    "id": "call_1",
                    "name": "http_request",
                    "input": {"url": "/x"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "200 OK"},
            ],
        },
    ]
    items = llm._ant_messages_to_responses(messages)
    assert items[0] == {"type": "message", "role": "user", "content": "start"}
    assert {"type": "message", "role": "assistant", "content": "thinking"} in items
    fc = next(i for i in items if i["type"] == "function_call")
    assert fc["call_id"] == "call_1" and fc["name"] == "http_request"
    assert json.loads(fc["arguments"]) == {"url": "/x"}
    fco = next(i for i in items if i["type"] == "function_call_output")
    assert fco == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "200 OK",
    }


def test_mantle_tools_translation_to_responses():
    """Anthropic tool specs map to flat Responses function tools."""
    tools = [
        {"name": "t", "description": "d", "input_schema": {"type": "object"}},
    ]
    assert llm._ant_tools_to_responses(tools) == [
        {
            "type": "function",
            "name": "t",
            "description": "d",
            "parameters": {"type": "object"},
        },
    ]


def test_mantle_create_response_retries_dropping_temperature():
    """A temperature-rejection error triggers one retry without temperature."""
    calls: list[dict] = []

    class FakeResponses:
        async def create(self, **kwargs):
            calls.append(kwargs)
            if "temperature" in kwargs:
                raise RuntimeError("temperature is not supported with this model")
            return _fake_mantle_response()

    client = SimpleNamespace(responses=FakeResponses())
    out = asyncio.run(
        llm._create_response(
            client, {"model": "openai.gpt-5.5", "input": "hi", "temperature": 0.2}
        )
    )
    assert out.output_text == "ok"
    assert len(calls) == 2
    assert "temperature" not in calls[1]


def test_bedrock_mantle_sigv4_signs_with_bedrock_service(monkeypatch):
    """With no API key, Mantle requests are SigV4-signed under the 'bedrock' service."""
    import httpx
    from botocore.credentials import Credentials

    fake_creds = Credentials("AKIAEXAMPLE", "secret-key", token="session-token")

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        def get_credentials(self):
            return fake_creds

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=FakeSession))
    monkeypatch.delenv("AWS_PROFILE", raising=False)

    signer = llm._BedrockMantleSigV4Auth(region="us-east-2")
    request = httpx.Request(
        "POST",
        "https://bedrock-mantle.us-east-2.api.aws/v1/chat/completions",
        json={"model": "openai.gpt-oss-120b", "messages": []},
    )
    # Drive the sync auth flow so the request is signed in place.
    list(signer.sync_auth_flow(request))

    authorization = request.headers["Authorization"]
    assert authorization.startswith("AWS4-HMAC-SHA256")
    # Credential scope must name the resolved region and the "bedrock" service.
    assert "/us-east-2/bedrock/aws4_request" in authorization
    assert "x-amz-date" in request.headers
    # Temporary (role/STS) credentials must carry the session token.
    assert request.headers["x-amz-security-token"] == "session-token"


def test_bedrock_mantle_sigv4_errors_without_credentials(monkeypatch):
    """A clear error is raised when neither an API key nor AWS credentials exist."""
    import httpx

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        def get_credentials(self):
            return None

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=FakeSession))
    monkeypatch.delenv("AWS_PROFILE", raising=False)

    signer = llm._BedrockMantleSigV4Auth(region="us-east-2")
    request = httpx.Request(
        "POST", "https://bedrock-mantle.us-east-2.api.aws/v1/chat/completions", json={}
    )
    with pytest.raises(RuntimeError, match="No AWS credentials"):
        list(signer.sync_auth_flow(request))


@pytest.mark.anyio
async def test_bedrock_stream_uses_aws_sdk_when_api_key_blank(monkeypatch):
    captured = {}

    class FakeBedrockClient:
        def converse_stream(self, **kwargs):
            captured["converse_stream"] = kwargs
            return {
                "stream": [
                    {"contentBlockDelta": {"delta": {"text": "streaming "}}},
                    {"contentBlockDelta": {"delta": {"text": "response"}}},
                ]
            }

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session"] = kwargs

        def client(self, service_name, **kwargs):
            captured["client"] = {"service_name": service_name, **kwargs}
            return FakeBedrockClient()

    fake_boto3 = SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_REGION", "ap-southeast-2")
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url=None,
        model="global.anthropic.claude-sonnet-4-6",
        max_tokens=2048,
        temperature=0.0,
    )

    chunks = []
    async for chunk in llm.stream_chat_completion(
        config, "system prompt", [{"role": "user", "content": "hello"}]
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "streaming response"
    assert captured["session"] == {}
    assert {
        "service_name": "bedrock-runtime",
        "region_name": "ap-southeast-2",
        "endpoint_url": None,
    }.items() <= captured["client"].items()
    assert (
        captured["converse_stream"]["modelId"] == "global.anthropic.claude-sonnet-4-6"
    )
    assert captured["converse_stream"]["messages"] == [
        {"role": "user", "content": [{"text": "hello"}]}
    ]
    assert captured["converse_stream"]["system"] == [{"text": "system prompt"}]


@pytest.mark.anyio
async def test_bedrock_stream_uses_converse_api_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            yield 'data: {"contentBlockDelta": {"delta": {"text": "streaming "}}}'
            yield '{"contentBlockDelta": {"delta": {"text": "response"}}}'

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def stream(self, method, url, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["request"] = kwargs

            class StreamContext:
                async def __aenter__(self):
                    return FakeResponse()

                async def __aexit__(self, exc_type, exc, tb):
                    return None

            return StreamContext()

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    config = LLMConfig(
        provider="bedrock",
        api_key="bedrock-test-key",
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=2048,
        temperature=0.0,
    )

    chunks = []
    async for chunk in llm.stream_chat_completion(
        config, "system prompt", [{"role": "user", "content": "hello"}]
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "streaming response"
    assert {"timeout": 120}.items() <= captured["client"].items()
    assert captured["method"] == "POST"
    assert captured["url"] == (
        "https://bedrock-runtime.us-east-1.amazonaws.com/model/"
        "anthropic.claude-3-7-sonnet-20250219-v1%3A0/converse-stream"
    )
    assert captured["request"] == {
        "headers": {
            "Authorization": "Bearer bedrock-test-key",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        "json": {
            "messages": [{"role": "user", "content": [{"text": "hello"}]}],
            "system": [{"text": "system prompt"}],
            "inferenceConfig": {"maxTokens": 2048, "temperature": 0.0},
        },
    }


def test_analyse_probes_requires_structured_cvss_finding(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_call(config, prompt, screenshot_b64):
        captured["prompt"] = prompt
        return """
        [{
          "owasp_category": "A03",
          "severity": "medium",
          "title": "Reflected XSS in search",
          "description": "The q parameter is reflected without encoding.",
          "impact": "An attacker can execute script in another user's browser.",
          "likelihood": "Likely if a victim opens an attacker-controlled URL.",
          "recommendation": "Encode reflected output and validate the parameter.",
          "cvss_score": 6.1,
          "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
          "affected_url": "https://target.local/search?q=<script>alert(1)</script>",
          "evidence": "Payload is reflected in the response."
        }]
        """

    monkeypatch.setattr(llm, "_call", fake_call)

    config = LLMConfig(provider="openai_compatible", model="local")
    findings = asyncio.run(
        llm.analyse_probes(
            config,
            "https://target.local/search",
            [
                {
                    "desc": "XSS probe",
                    "url": "https://target.local/search?q=<script>alert(1)</script>",
                    "status": 200,
                    "headers": {"content-type": "text/html"},
                    "body": "<script>alert(1)</script>",
                    "request_evidence": "GET /search?q=<script>alert(1)</script> HTTP/1.1",
                    "response_evidence": "HTTP/1.1 200\n\n<script>alert(1)</script>",
                }
            ],
        )
    )

    assert findings[0]["impact"].startswith("An attacker")
    assert findings[0]["cvss_score"] == 6.1
    assert "description" in captured["prompt"]
    assert "CVSS v3.1" in captured["prompt"]
    assert (
        "Rate generic server or framework version disclosure as info"
        in captured["prompt"]
    )
    assert "Rate verbose stack traces" in captured["prompt"]
    assert "Rate CORS arbitrary Origin reflection" in captured["prompt"]
    assert "GET /search" in captured["prompt"]
    assert "HTTP/1.1 200" in captured["prompt"]


def test_analyse_probes_writes_reporting_replay_capture(monkeypatch):
    async def fake_call(config, prompt, screenshot_b64):  # noqa: ARG001
        return """
        [{
          "owasp_category": "A03",
          "severity": "medium",
          "title": "Reflected XSS in search",
          "description": "The q parameter is reflected without encoding.",
          "impact": "An attacker can execute script in another user's browser.",
          "likelihood": "Likely if a victim opens an attacker-controlled URL.",
          "recommendation": "Encode reflected output and validate the parameter.",
          "cvss_score": 6.1,
          "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
          "affected_url": "https://target.local/search?q=<script>alert(1)</script>",
          "evidence": "Payload is reflected in the response."
        }]
        """

    monkeypatch.setattr(llm, "_call", fake_call)
    captured: dict[str, object] = {}

    from aespa.services import reporting_debug

    monkeypatch.setattr(reporting_debug, "is_capture_enabled", lambda: True)
    monkeypatch.setattr(
        reporting_debug,
        "capture_reporting_batch",
        lambda **kwargs: captured.update(kwargs) or 1,
    )

    config = LLMConfig(provider="openai_compatible", model="local")
    findings = asyncio.run(
        llm.analyse_probes(
            config,
            "https://target.local/search",
            [
                {
                    "desc": "XSS probe",
                    "url": "https://target.local/search?q=<script>alert(1)</script>",
                    "status": 200,
                    "headers": {"content-type": "text/html"},
                    "body": "<script>alert(1)</script>",
                    "request_evidence": "GET /search?q=<script>alert(1)</script> HTTP/1.1",
                    "response_evidence": "HTTP/1.1 200\n\n<script>alert(1)</script>",
                }
            ],
        )
    )

    assert captured["url"] == "https://target.local/search"
    assert captured["result_texts"]
    assert captured["prompt_sha256"]
    assert captured["llm"]["model"] == "local"
    assert captured["findings"] == findings


def test_replay_reporting_capture_rebuilds_current_prompt(monkeypatch):
    prompts: list[str] = []

    async def fake_call(config, prompt, screenshot_b64):  # noqa: ARG001
        prompts.append(prompt)
        return """
        [{
          "owasp_category": "A05",
          "severity": "low",
          "title": "Verbose error response",
          "description": "A verbose framework error is returned.",
          "impact": "Attackers can use implementation details to refine attacks.",
          "likelihood": "Likely when the endpoint is reachable.",
          "recommendation": "Return generic errors and log details server-side.",
          "cvss_score": 3.1,
          "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
          "affected_url": "https://target.local/error",
          "evidence": "Stack trace was returned."
        }]
        """

    monkeypatch.setattr(llm, "_call", fake_call)
    capture = {
        "schema": llm.REPORTING_REPLAY_SCHEMA,
        "capture_id": "cap-1",
        "url": "https://target.local/error",
        "result_texts": ["--- Probe: verbose error ---\nHTTP/1.1 500"],
        "prompt": "old saved prompt",
    }

    config = LLMConfig(provider="openai_compatible", model="local")
    result = asyncio.run(llm.replay_reporting_capture(config, capture))

    assert prompts[0] != "old saved prompt"
    assert (
        "You are a web application penetration tester reviewing probe results"
        in prompts[0]
    )
    assert "HTTP/1.1 500" in prompts[0]
    assert result["source_capture_id"] == "cap-1"
    assert result["findings"][0]["title"] == "Verbose error response"


def test_replay_reporting_capture_can_use_saved_prompt(monkeypatch):
    prompts: list[str] = []

    async def fake_call(config, prompt, screenshot_b64):  # noqa: ARG001
        prompts.append(prompt)
        return "[]"

    monkeypatch.setattr(llm, "_call", fake_call)
    capture = {
        "schema": llm.REPORTING_REPLAY_SCHEMA,
        "url": "https://target.local",
        "result_texts": ["result text"],
        "prompt": "exact prompt from scan",
    }

    config = LLMConfig(provider="openai_compatible", model="local")
    asyncio.run(llm.replay_reporting_capture(config, capture, use_saved_prompt=True))

    assert prompts == ["exact prompt from scan"]


def test_replay_reporting_writeup_capture_uses_writeup_prompt(monkeypatch):
    prompts: list[str] = []

    async def fake_call(config, prompt, screenshot_b64):  # noqa: ARG001
        prompts.append(prompt)
        return """
        {
          "owasp_category": "A01",
          "severity": "high",
          "title": "IDOR exposes account statement",
          "description": "The statement endpoint returns another user's account data.",
          "impact": "An attacker can read sensitive account statements.",
          "likelihood": "Likely when account IDs are enumerable.",
          "recommendation": "Enforce object ownership checks server-side.",
          "cvss_score": 7.5,
          "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N",
          "affected_url": "https://target.local/accounts/2/statement",
          "evidence": "Captured response included another user's statement."
        }
        """

    monkeypatch.setattr(llm, "_call", fake_call)
    capture = {
        "schema": llm.REPORTING_REPLAY_SCHEMA,
        "kind": "writeup",
        "capture_id": 7,
        "source": "test_lead",
        "base_url": "https://target.local",
        "url": "https://target.local/accounts/2/statement",
        "finding": {
            "title": "Account statement IDOR",
            "affected_url": "https://target.local/accounts/2/statement",
            "evidence": "Other account returned.",
        },
        "evidence": {"response_evidence": "HTTP/1.1 200\nAlice Statement"},
    }

    config = LLMConfig(provider="openai_compatible", model="local")
    result = asyncio.run(llm.replay_reporting_writeup_capture(config, capture))

    assert "Original finding JSON" in prompts[0]
    assert "Supporting evidence" in prompts[0]
    assert result["source_capture_id"] == 7
    assert result["findings"][0]["title"] == "IDOR exposes account statement"


def test_analyse_probes_chunks_large_result_sets(monkeypatch):
    prompts: list[str] = []

    async def fake_call(config, prompt, screenshot_b64):
        prompts.append(prompt)
        if len(prompts) == 2:
            return """
            [{
              "owasp_category": "A05",
              "severity": "low",
              "title": "Verbose error response",
              "description": "A probe returned a verbose framework error.",
              "impact": "Attackers can use implementation details to refine attacks.",
              "likelihood": "Likely when the endpoint is reachable anonymously.",
              "recommendation": "Return generic errors and log details server-side.",
              "cvss_score": 3.1,
              "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
              "affected_url": "https://target.local/error/2",
              "evidence": "Stack trace was returned in the response."
            }]
            """
        return "[]"

    monkeypatch.setattr(llm, "_call", fake_call)
    monkeypatch.setattr(llm, "ANALYSE_RESULTS_TEXT_BUDGET", 100_000)
    monkeypatch.setattr(llm, "ANALYSE_RESULTS_PER_BATCH", 2)

    config = LLMConfig(provider="openai_compatible", model="local")
    results = [
        {
            "desc": f"Verbose error probe {index}",
            "url": f"https://target.local/error/{index}",
            "status": 500,
            "headers": {"content-type": "text/plain"},
            "body": "Traceback " + ("x" * 600),
            "request_evidence": f"GET /error/{index} HTTP/1.1",
            "response_evidence": "HTTP/1.1 500\n" + ("stack trace " * 80),
        }
        for index in range(6)
    ]

    findings = asyncio.run(llm.analyse_probes(config, "https://target.local", results))

    assert len(prompts) == 3
    assert findings[0]["title"] == "Verbose error response"


def test_bedrock_caching_tokens_extraction_boto3_sdk(monkeypatch):
    recorded_usages = []

    def fake_record_usage(
        model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0
    ):
        recorded_usages.append(
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
            }
        )

    monkeypatch.setattr(llm, "_record_usage", fake_record_usage)

    class FakeBedrockClient:
        def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "content": [{"text": "ok"}],
                    },
                },
                "usage": {
                    "inputTokens": 1000,
                    "outputTokens": 100,
                    "cacheReadInputTokens": 400,
                    "cacheWriteInputTokens": 200,
                },
            }

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        def client(self, service_name, **kwargs):
            return FakeBedrockClient()

    fake_boto3 = SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert len(recorded_usages) == 1
    assert recorded_usages[0] == {
        "model": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "input_tokens": 1000,
        "output_tokens": 100,
        "cache_read_tokens": 400,
        "cache_write_tokens": 200,
    }


def test_bedrock_caching_tokens_extraction_api_key(monkeypatch):
    recorded_usages = []

    def fake_record_usage(
        model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0
    ):
        recorded_usages.append(
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
            }
        )

    monkeypatch.setattr(llm, "_record_usage", fake_record_usage)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": {
                    "message": {
                        "content": [{"text": "ok"}],
                    },
                },
                "usage": {
                    "inputTokens": 1200,
                    "outputTokens": 150,
                    "cacheReadInputTokens": 500,
                    "cacheWriteInputTokens": 300,
                },
            }

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    config = LLMConfig(
        provider="bedrock",
        api_key="bedrock-test-key",
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=2048,
        temperature=0.0,
    )

    result = asyncio.run(llm._call(config, "hello", None))

    assert result == "ok"
    assert len(recorded_usages) == 1
    assert recorded_usages[0] == {
        "model": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "input_tokens": 1200,
        "output_tokens": 150,
        "cache_read_tokens": 500,
        "cache_write_tokens": 300,
    }


def test_bedrock_caching_tokens_extraction_call_with_tools(monkeypatch):
    recorded_usages = []

    def fake_record_usage(
        model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0
    ):
        recorded_usages.append(
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
            }
        )

    monkeypatch.setattr(llm, "_record_usage", fake_record_usage)

    class FakeBedrockClient:
        def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "content": [{"text": "ok"}],
                    },
                },
                "usage": {
                    "inputTokens": 2000,
                    "outputTokens": 250,
                    "cacheReadInputTokens": 800,
                    "cacheWriteInputTokens": 400,
                },
            }

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        def client(self, service_name, **kwargs):
            return FakeBedrockClient()

    fake_boto3 = SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=2048,
        temperature=0.0,
    )

    blocks, stop_reason, raw_content_ant = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="system",
            messages=[{"role": "user", "content": "hello"}],
            tools=[],
        )
    )

    assert blocks[0]["text"] == "ok"
    assert len(recorded_usages) == 1
    assert recorded_usages[0] == {
        "model": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "input_tokens": 2000,
        "output_tokens": 250,
        "cache_read_tokens": 800,
        "cache_write_tokens": 400,
    }


def test_bedrock_empty_response_preserves_native_diagnostics(monkeypatch):
    class FakeBedrockClient:
        def converse(self, **kwargs):  # noqa: ARG002
            return {
                "stopReason": "guardrail_intervened",
                "output": {"message": {"content": []}},
                "usage": {
                    "inputTokens": 1234,
                    "outputTokens": 0,
                    "cacheReadInputTokens": 1000,
                    "cacheWriteInputTokens": 0,
                },
                "metrics": {"latencyMs": 42},
                "trace": {"guardrail": "present"},
                "ResponseMetadata": {
                    "RequestId": "bedrock-request-123",
                    "HTTPStatusCode": 200,
                    "RetryAttempts": 0,
                },
            }

    class FakeSession:
        def __init__(self, **kwargs):  # noqa: ARG002
            pass

        def client(self, service_name, **kwargs):  # noqa: ARG002
            return FakeBedrockClient()

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=FakeSession))
    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="global.anthropic.claude-opus-test",
        max_tokens=2048,
    )

    blocks, stop_reason, raw_content = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="system",
            messages=[{"role": "user", "content": "hello"}],
            tools=[],
        )
    )

    assert blocks == []
    assert stop_reason == "guardrail_intervened"
    diagnostic = raw_content[-1]
    assert diagnostic["type"] == "provider_diagnostic"
    assert diagnostic["native_stop_reason"] == "guardrail_intervened"
    assert diagnostic["transport"] == {
        "http_status": 200,
        "request_id": "bedrock-request-123",
        "retry_attempts": 0,
    }
    assert diagnostic["guardrail_trace_present"] is True
    assert diagnostic["usage"]["input_tokens"] == 1234


def test_call_with_tools_preempts_tool_choice_for_reasoning_models(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["completion"] = kwargs
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="openai_compatible",
        api_key=None,
        base_url="http://localhost:1234",
        model="deepseek-r1-reasoning-model",
        max_tokens=2048,
        temperature=0.0,
    )

    blocks, stop_reason, raw_content = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="system message",
            messages=[{"role": "user", "content": "hello"}],
            tools=[],
        )
    )

    assert blocks[0]["text"] == "ok"
    assert "tool_choice" not in captured["completion"]


def test_call_with_tools_retries_without_tool_choice_on_error(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            captured[f"call_{self.calls}"] = kwargs
            if self.calls == 1:
                raise ValueError("Thinking mode does not support this tool_choice")
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="openai_compatible",
        api_key=None,
        base_url="http://localhost:1234",
        model="deepseek-v4-pro-custom",
        max_tokens=2048,
        temperature=0.0,
        force_tool_choice=True,
    )

    blocks, stop_reason, raw_content = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="system message",
            messages=[{"role": "user", "content": "hello"}],
            tools=[],
        )
    )

    assert blocks[0]["text"] == "ok"
    assert captured["call_1"]["tool_choice"] == "required"
    assert "tool_choice" not in captured["call_2"]


def test_call_with_tools_bedrock_mantle_uses_responses_api(monkeypatch):
    """Mantle tool-calling goes through the Responses API and parses its output items."""
    captured: dict[str, object] = {}

    class FakeResponses:
        async def create(self, **kwargs):
            captured["req"] = kwargs
            text_part = SimpleNamespace(type="output_text", text="thinking")
            msg_item = SimpleNamespace(type="message", content=[text_part])
            fc_item = SimpleNamespace(
                type="function_call",
                call_id="call_9",
                name="http_request",
                arguments='{"url": "/x"}',
            )
            return SimpleNamespace(
                output=[msg_item, fc_item],
                output_text="thinking",
                usage=SimpleNamespace(
                    input_tokens=1,
                    output_tokens=2,
                    input_tokens_details=SimpleNamespace(cached_tokens=0),
                ),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr("openai.AsyncOpenAI", FakeOpenAI)

    config = LLMConfig(
        provider="bedrock_mantle",
        api_key="k",
        base_url=None,
        model="openai.gpt-5.5",
        max_tokens=256,
        temperature=0.2,
        force_tool_choice=True,
    )

    blocks, stop_reason, raw = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="sys",
            messages=[{"role": "user", "content": "hello"}],
            tools=[
                {
                    "name": "http_request",
                    "description": "d",
                    "input_schema": {"type": "object"},
                },
            ],
        )
    )

    # Request used Responses shape: instructions + input list + flat tools.
    assert captured["req"]["instructions"] == "sys"
    assert isinstance(captured["req"]["input"], list)
    assert captured["req"]["tools"][0]["type"] == "function"
    assert captured["req"]["tool_choice"] == "required"
    # gpt-5.x reasoning model → temperature omitted.
    assert "temperature" not in captured["req"]
    # Output items parsed into text + tool_use blocks.
    assert any(b["type"] == "text" and b["text"] == "thinking" for b in blocks)
    tool_use = next(b for b in blocks if b["type"] == "tool_use")
    assert tool_use["id"] == "call_9"
    assert tool_use["name"] == "http_request"
    assert tool_use["input"] == {"url": "/x"}
    assert stop_reason == "tool_use"


def test_anthropic_caching_in_call_with_tools(monkeypatch):
    captured: dict[str, object] = {}

    class FakeMessages:
        async def create(self, **kwargs):
            captured["create_kwargs"] = kwargs
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text="response text",
                        id=None,
                        name=None,
                        input=None,
                    )
                ],
                stop_reason="end_turn",
                usage=SimpleNamespace(
                    input_tokens=10,
                    output_tokens=5,
                    cache_read_input_tokens=8,
                    cache_creation_input_tokens=2,
                ),
            )

    class FakeAsyncAnthropic:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.AsyncAnthropic", FakeAsyncAnthropic)

    config = LLMConfig(
        provider="anthropic",
        api_key="sk-test",
        model="claude-3-5-sonnet",
        max_tokens=2048,
        temperature=0.0,
    )

    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": "how are you?"},
    ]
    tools = [
        {
            "name": "get_weather",
            "description": "Get the weather",
            "input_schema": {"type": "object"},
        }
    ]

    blocks, stop_reason, raw_content = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="you are a helpful assistant",
            messages=messages,
            tools=tools,
        )
    )

    assert blocks[0]["text"] == "response text"
    create_kwargs = captured["create_kwargs"]

    # Verify messages have cache_control on the last message's last content block
    cached_messages = create_kwargs["messages"]
    assert len(cached_messages) == 3
    assert cached_messages[-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    # Verify original messages list was NOT mutated in-place
    assert "cache_control" not in messages[-1]
    if isinstance(messages[-1]["content"], list):
        assert "cache_control" not in messages[-1]["content"][-1]

    # Verify tools have cache_control on the last tool
    cached_tools = create_kwargs["tools"]
    assert len(cached_tools) == 1
    assert cached_tools[-1]["cache_control"] == {"type": "ephemeral"}
    # Verify original tools list was NOT mutated
    assert "cache_control" not in tools[-1]


def test_bedrock_caching_multiple_messages_in_call_with_tools(monkeypatch):
    captured: dict[str, object] = {}

    class FakeBedrockClient:
        def converse(self, **kwargs):
            captured["converse_kwargs"] = kwargs
            return {
                "output": {
                    "message": {
                        "content": [{"text": "ok"}],
                    },
                },
                "usage": {
                    "inputTokens": 2000,
                    "outputTokens": 250,
                    "cacheReadInputTokens": 800,
                    "cacheWriteInputTokens": 400,
                },
            }

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        def client(self, service_name, **kwargs):
            return FakeBedrockClient()

    fake_boto3 = SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=2048,
        temperature=0.0,
    )

    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": "how are you?"},
    ]

    blocks, stop_reason, raw_content = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="system prompt",
            messages=messages,
            tools=[],
        )
    )

    converse_kwargs = captured["converse_kwargs"]
    converse_messages = converse_kwargs["messages"]

    # Verify first user message has cachePoint
    assert converse_messages[0]["content"][-1] == {"cachePoint": {"type": "default"}}
    # Verify last user message has cachePoint
    assert converse_messages[-1]["content"][-1] == {"cachePoint": {"type": "default"}}


def test_bedrock_sanitizes_empty_history_and_preserves_reasoning(monkeypatch):
    captured: dict[str, object] = {}
    reasoning = {
        "reasoningText": {
            "text": "signed internal reasoning",
            "signature": "bedrock-signature",
        }
    }

    class FakeBedrockClient:
        def converse(self, **kwargs):
            captured["converse_kwargs"] = kwargs
            return {
                "stopReason": "tool_use",
                "output": {
                    "message": {
                        "content": [
                            {"reasoningContent": reasoning},
                            {
                                "toolUse": {
                                    "toolUseId": "tool-2",
                                    "name": "context_tool",
                                    "input": {"tool": "site_map"},
                                }
                            },
                        ],
                    },
                },
                "usage": {},
            }

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        def client(self, service_name, **kwargs):
            return FakeBedrockClient()

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=FakeSession))
    config = LLMConfig(
        provider="bedrock",
        api_key=None,
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        model="anthropic.claude-opus-test",
        max_tokens=2048,
    )
    messages = [
        {"role": "user", "content": "start"},
        {"role": "assistant", "content": []},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool-1",
                    "content": "",
                }
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "bedrock_reasoning",
                    "reasoning_content": reasoning,
                }
            ],
        },
        {"role": "user", "content": "continue"},
    ]

    blocks, stop_reason, raw_content = asyncio.run(
        llm._call_with_tools(
            config,
            system_message="system",
            messages=messages,
            tools=[],
        )
    )

    converse_messages = captured["converse_kwargs"]["messages"]
    assert all(message["content"] for message in converse_messages)
    assert converse_messages[1]["content"] == [
        {"text": "[No content was recorded for this turn.]"}
    ]
    assert converse_messages[2]["content"][0]["toolResult"]["content"] == [
        {"text": "[Tool completed without textual output.]"}
    ]
    assert converse_messages[3]["content"] == [{"reasoningContent": reasoning}]
    assert stop_reason == "tool_use"
    assert blocks[0]["name"] == "context_tool"
    assert raw_content[0] == {
        "type": "bedrock_reasoning",
        "reasoning_content": reasoning,
    }


def test_token_usage_tracking_for_sast_and_api():
    # Verify set_run_context and get_run_token_usage isolate by run_kind
    run_id = 888888
    llm.set_run_context(run_id, emit_fn=None, run_kind="sast")
    llm._record_usage("gpt-4", input_tokens=100, output_tokens=50)
    llm.clear_run_context()

    llm.set_run_context(run_id, emit_fn=None, run_kind="web")
    llm._record_usage("gpt-4", input_tokens=200, output_tokens=80)
    llm.clear_run_context()

    sast_usage = llm.get_run_token_usage(run_id, run_kind="sast")
    web_usage = llm.get_run_token_usage(run_id, run_kind="web")

    assert sast_usage["total_input"] == 100
    assert sast_usage["total_output"] == 50

    assert web_usage["total_input"] == 200
    assert web_usage["total_output"] == 80


def test_copilot_usage_callback_keeps_run_context_after_sdk_context_switch():
    run_id = 888889
    events = []
    llm.set_run_context(run_id, emit_fn=events.append, run_kind="api")
    callback = llm._copilot_usage_callback()
    llm.clear_run_context()

    callback(
        "gpt-5.6-terra",
        1_200,
        300,
        800,
        0,
        ai_credits=1.25,
        premium_requests=0,
        requests=1,
        copilot_quota={"remaining_percentage": 74, "reset_at": None},
    )

    usage = llm.get_run_token_usage(run_id, run_kind="api")
    assert usage["total_input"] == 1_200
    assert usage["total_cache_read"] == 800
    assert usage["total_ai_credits"] == 1.25
    assert usage["total_requests"] == 1
    assert usage["copilot_quota"]["remaining_percentage"] == 74
    assert events[-1]["totals"] == usage


def test_droid_usage_callback_records_factory_credits():
    run_id = 888890
    llm.set_run_context(run_id, emit_fn=None, run_kind="web")
    callback = llm._droid_usage_callback()
    llm.clear_run_context()

    callback(
        "claude-sonnet-4-6",
        100,
        20,
        30,
        10,
        factory_credits=434,
        requests=1,
    )

    usage = llm.get_run_token_usage(run_id)
    assert usage["total_factory_credits"] == 434
    assert usage["by_model"]["claude-sonnet-4-6"]["provider"] == "factory_droid"


def test_google_usage_treats_none_counters_as_zero(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        llm, "_record_usage", lambda *args, **kwargs: recorded.append((args, kwargs))
    )

    llm._record_google_usage(
        "gemini-test",
        SimpleNamespace(
            prompt_token_count=120,
            candidates_token_count=None,
            cached_content_token_count=None,
        ),
    )
    llm._record_google_usage("gemini-test", None)

    assert recorded == [
        (("gemini-test", 120, 0), {"cache_read_tokens": 0}),
        (("gemini-test", 0, 0), {"cache_read_tokens": 0}),
    ]
