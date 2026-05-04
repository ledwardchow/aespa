import asyncio
from types import SimpleNamespace

from aespa.models import LLMConfig
from aespa.services import llm


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
    assert captured["client"] == {
        "api_key": "sk-or-v1-test",
        "base_url": llm.OPENROUTER_BASE_URL,
    }
    assert captured["completion"] == {
        "model": "openrouter/owl-alpha",
        "max_tokens": 1024,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": "hello"}],
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


def test_openai_reasoning_models_use_completion_tokens_and_default_temperature(monkeypatch):
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
        "max_completion_tokens": 1024,
        "messages": [{"role": "user", "content": "hello"}],
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
        "max_completion_tokens": 1024,
    }
