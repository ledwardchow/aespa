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
        "max_tokens": 2048,
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
        "max_completion_tokens": 2048,
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
    assert captured["client"] == {"timeout": 120}
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
    findings = asyncio.run(llm.analyse_probes(config, "https://target.local/search", [{
        "desc": "XSS probe",
        "url": "https://target.local/search?q=<script>alert(1)</script>",
        "status": 200,
        "headers": {"content-type": "text/html"},
        "body": "<script>alert(1)</script>",
        "request_evidence": "GET /search?q=<script>alert(1)</script> HTTP/1.1",
        "response_evidence": "HTTP/1.1 200\n\n<script>alert(1)</script>",
    }]))

    assert findings[0]["impact"].startswith("An attacker")
    assert findings[0]["cvss_score"] == 6.1
    assert "description" in captured["prompt"]
    assert "CVSS v3.1" in captured["prompt"]
    assert "GET /search" in captured["prompt"]
    assert "HTTP/1.1 200" in captured["prompt"]
