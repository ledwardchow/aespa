import asyncio
import sys
from types import SimpleNamespace

from aespa.models import LLMConfig
from aespa.services import llm


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

    summary = asyncio.run(llm.thinking_agentic_loop(
        config,
        system_message="system",
        initial_user_message="start",
        tool_executor=fake_tool_executor,
    ))

    assert summary == "Complete."
    assert executed == [("context_tool", {"tool": "site_map", "args": {"limit": 5}}, 1)]
    correction_messages = [
        msg for msg in calls[1]
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

    summary = asyncio.run(llm.thinking_agentic_loop(
        config,
        system_message="system",
        initial_user_message="start",
        tool_executor=fake_tool_executor,
        done_check=done_check,
    ))

    assert summary == "Really complete."
    assert executed == [(
        "http_request",
        {
            "method": "GET",
            "url": "https://target.local/api/profile",
            "use_session": "customer_1",
        },
        2,
    )]


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
    assert {"api_key": "sk-or-v1-test", "base_url": llm.OPENROUTER_BASE_URL}.items() <= captured["client"].items()
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
    assert {"api_key": "foundry-key", "base_url": "https://myresource.services.ai.azure.com/openai/v1"}.items() <= captured["client"].items()
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
    assert captured["url"] == "https://myresource.services.ai.azure.com/anthropic/v1/messages"
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

    assert llm._extract_json(extracted, expect=list)[0]["title"] == "Reflected XSS in Query Parameter"


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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Application pages:\n  https://target.local/search [takes-input]",
        history=[],
        max_steps=80,
        current_step=1,
    ))

    assert action["observation"] == "search accepts a q parameter"
    assert "observation" in captured["prompt"]
    assert "hypothesis" in captured["prompt"]
    assert "payload_purpose" in captured["prompt"]
    assert "found something interesting" in captured["prompt"]
    assert "Raw asset and JavaScript mining" in captured["prompt"]
    assert "endpoint inventory" in captured["prompt"]
    assert "admin/admin123" in captured["prompt"]
    assert "Business-logic gate bypass" in captured["prompt"]
    assert "actual action endpoint directly without the required field" in captured["prompt"]
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
    assert "Supported ops: goto, fill, type, click, press, wait, snapshot" in captured["prompt"]


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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Application pages:\n  https://target.local/",
        history=[{
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
            "response_body": "<a href=\"/admin/\">Admin</a>",
        }],
        sessions=[{
            "label": "found_admin_1",
            "kind": "bearer",
            "username": "admin",
            "source": "credential_check",
        }],
        max_steps=120,
        current_step=2,
    ))

    assert action["url"] == "https://target.local/admin/"
    assert "Response headers:" in captured["prompt"]
    assert "x-frame-options" in captured["prompt"]
    assert "content-type" in captured["prompt"]
    assert "found_admin_1" in captured["prompt"]
    assert "found_admin_1" in captured["prompt"]  # session label present in sessions section


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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Target: https://target.local",
        history=history,
        max_steps=120,
        current_step=21,
    ))

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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Application pages:\n  https://target.local/banking/#/login [takes-input]",
        history=[],
        max_steps=120,
        current_step=1,
    ))

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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="API endpoints:\n  https://target.local/api/health",
        history=[],
        max_steps=120,
        current_step=1,
    ))

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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Application pages:\n  https://target.local/admin/",
        history=[],
        max_steps=120,
        current_step=1,
    ))

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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Crawl summary: 20 pages. Use context tools for details.",
        history=[],
        max_steps=120,
        current_step=1,
    ))

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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Crawl summary: compact.",
        history=[],
        max_steps=120,
        current_step=1,
    ))

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
    action = asyncio.run(llm.thinking_next_action(
        config,
        target_url="https://target.local",
        crawl_context="Crawl summary: compact.",
        history=[],
        max_steps=120,
        current_step=3,
    ))

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
        probes = asyncio.run(llm.plan_followup_probes(
                config,
                "https://target.local/transfer",
                "Transfer page",
                [{
                        "desc": "2FA check",
                        "url": "https://target.local/api/transfer/check",
                        "status": 200,
                        "body": '{"requires_2fa":true}',
                        "response_evidence": "Status: 200\nrequires_2fa=true",
                }],
        ))

        assert probes[0]["interesting_result"].startswith("2FA check")
        assert "interesting_result" in captured["prompt"]
        assert "hypothesis" in captured["prompt"]
        assert "payload_purpose" in captured["prompt"]
        assert "looked interesting" in captured["prompt"]


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


def test_openai_caching_tokens_extraction_and_recording(monkeypatch):
    recorded_usages = []

    def fake_record_usage(model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0):
        recorded_usages.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
        })

    monkeypatch.setattr(llm, "_record_usage", fake_record_usage)

    class FakeCompletions:
        async def create(self, **kwargs):
            message = SimpleNamespace(content="ok")
            usage = SimpleNamespace(
                prompt_tokens=1500,
                completion_tokens=200,
                prompt_tokens_details=SimpleNamespace(cached_tokens=800)
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)

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

    def fake_record_usage(model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0):
        recorded_usages.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
        })

    monkeypatch.setattr(llm, "_record_usage", fake_record_usage)

    class FakeCompletions:
        async def create(self, **kwargs):
            message = SimpleNamespace(content="ok")
            usage = SimpleNamespace(
                prompt_tokens=1500,
                completion_tokens=200,
                prompt_tokens_details=None
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)

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


def test_bedrock_call_uses_boto3_default_endpoint_when_api_key_and_base_url_blank(monkeypatch):
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
    assert "Rate generic server or framework version disclosure as info" in captured["prompt"]
    assert "Rate verbose stack traces" in captured["prompt"]
    assert "Rate CORS arbitrary Origin reflection" in captured["prompt"]
    assert "GET /search" in captured["prompt"]
    assert "HTTP/1.1 200" in captured["prompt"]


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
