"""Abstract LLM client wrappers for configured provider APIs."""
from __future__ import annotations

import base64
import json
import re
from typing import Any, Optional

from aespa.models import LLMConfig


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _strip_thinking_blocks(raw: str) -> str:
    """Remove visible model reasoning wrappers while keeping the final answer."""
    text = raw
    block_tags = ("think", "thinking", "reasoning", "thought")
    for tag in block_tags:
        text = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Some local/OpenRouter reasoning models emit pseudo-markup blocks without a
    # closing tag when they are interrupted near the final JSON.
    text = re.sub(r"(?is)^\s*(?:reasoning|thinking|thought)\s*:\s*.*?(?=[\[{])", "", text)
    return text


def _extract_json(raw: str, expect: type = list) -> Any:
    """Robustly extract JSON from an LLM response.

    Handles:
    - <think>...</think> reasoning blocks (Gemma, QwQ, DeepSeek-R1, etc.)
    - Markdown code fences (```json ... ```)
    - Preamble / explanation text before the JSON
    - Trailing prose after the closing bracket
    """
    if not raw:
        raise ValueError("empty response")

    text = _strip_thinking_blocks(raw)
    # Strip markdown fences
    text = re.sub(r"```(?:json|python)?\s*", "", text).strip().rstrip("`").strip()

    # Fast path: the whole string is valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first balanced JSON container matching `expect` that parses.
    open_ch  = "[" if expect is list else "{"
    close_ch = "]" if expect is list else "}"
    starts = [i for i, ch in enumerate(text) if ch == open_ch]
    if not starts:
        raise ValueError(f"no '{open_ch}' found in LLM response")

    for start in starts:
        depth = 0
        in_str = False
        escape = False
        for i, ch in enumerate(text[start:], start):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_str:
                escape = True
                continue
            if ch == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError("could not extract balanced JSON from LLM response")

_ANALYSIS_PROMPT = """\
You are a web application security analyst performing reconnaissance on a target web application.

Analyse the following web page and return a JSON response.

URL: {url}
Title: {title}

Page content:
{text}

Return ONLY valid JSON in this exact format (no markdown fences):
{{
  "context": "2-4 sentence description of the page's purpose and the functionality it offers to users",
  "suggested_links": ["absolute_url_1", "absolute_url_2"],
  "categories": {{
    "req_auth": true,
    "takes_input": false,
    "has_object_ref": false,
    "has_business_logic": false
  }}
}}

For suggested_links: include up to 10 absolute URLs that appear as actual links on this page \
(same domain) and reveal the most important or interesting application functionality. Do not \
construct, guess, rewrite, or substitute URLs from IDs/account numbers visible in page text. \
Prefer links to forms, features, user actions, admin areas, API endpoints, etc. over navigation \
links already visible on every page.

For categories — answer true/false to each:
- req_auth: Does accessing or using this page require the user to be authenticated/logged in?
- takes_input: Does this page contain forms, input fields, search boxes, or otherwise accept data from the user?
- has_object_ref: Does the URL or page content reference a specific object by ID \
(e.g. id=1 in a query param, /accounts/42/ in the path, or a resource identifier in a POST body)?
- has_business_logic: Can this page trigger transactions, modify account data, transfer funds, \
create/update/delete records, or perform other business-significant operations?"""


PageCategories = dict  # keys: req_auth, takes_input, has_object_ref, has_business_logic → bool|None

_EMPTY_CATS: PageCategories = {
    "req_auth": None,
    "takes_input": None,
    "has_object_ref": None,
    "has_business_logic": None,
}


async def analyse_page(
    config: LLMConfig,
    url: str,
    title: str,
    text: str,
    screenshot_b64: Optional[str] = None,
) -> tuple[str, list[str], PageCategories]:
    """Return (context_description, suggested_links_list, categories_dict)."""
    prompt = _ANALYSIS_PROMPT.format(
        url=url,
        title=title or "(no title)",
        text=text[:8000],
    )
    raw = await _call(config, prompt, screenshot_b64 if config.use_vision else None)
    return _parse(raw, url)


async def judge_page_access(
    config: LLMConfig,
    *,
    url: str,
    original_title: str,
    original_text: str,
    candidate_title: str,
    candidate_text: str,
    candidate_username: str,
    screenshot_b64: Optional[str] = None,
) -> dict:
    """Return {"accessible": bool, "reasoning": str} for direct-access reconciliation."""
    prompt = f"""\
You are helping a penetration testing crawler decide whether a user truly has access to a page.

The crawler already confirmed the candidate user is authenticated and the browser did not show a login form.
Your job is to decide whether the candidate response is a successful, legitimate view of the same page/functionality,
or merely an authenticated error/denial/loading state.

Target URL: {url}
Candidate user: {candidate_username}

Original page title:
{original_title or "(no title)"}

Original page text excerpt:
{(original_text or "")[:4000]}

Candidate page title:
{candidate_title or "(no title)"}

Candidate page text excerpt:
{(candidate_text or "")[:4000]}

Return ONLY valid JSON in this exact format:
{{
  "accessible": true,
  "reasoning": "short explanation"
}}

Rules:
- Return accessible=true if the candidate page shows the same kind of real page/functionality for that user,
  even if account names, balances, IDs, or user-specific values differ.
- Return accessible=false if the candidate page shows a toast/error/denial/loading failure such as
  "could not load details", "not authorized", "access denied", "not found", blank content,
  a generic app shell, or anything indicating the requested object did not load.
- Do not require exact text equality. This is fuzzy semantic judgement about access to equivalent functionality.
"""
    raw = await _call(config, prompt, screenshot_b64 if config.use_vision else None)
    data = _extract_json(raw, expect=dict)
    if not isinstance(data, dict):
        return {"accessible": False, "reasoning": "LLM did not return an object."}
    return {
        "accessible": bool(data.get("accessible")),
        "reasoning": str(data.get("reasoning") or ""),
    }


def _parse(raw: Optional[str], page_url: str) -> tuple[str, list[str], PageCategories]:
    if not raw:
        return "", [], dict(_EMPTY_CATS)
    try:
        data = _extract_json(raw, expect=dict)
        if not isinstance(data, dict):
            return raw.strip(), [], dict(_EMPTY_CATS)
        context = str(data.get("context") or raw)
        links = data.get("suggested_links") or []
        if not isinstance(links, list):
            links = []
        safe_links = [str(l) for l in links if isinstance(l, str) and l.startswith("http")]
        # Parse categories — each value coerced to bool or None
        raw_cats = data.get("categories") or {}
        cats: PageCategories = {}
        for key in ("req_auth", "takes_input", "has_object_ref", "has_business_logic"):
            val = raw_cats.get(key)
            cats[key] = bool(val) if val is not None else None
        return context, safe_links, cats
    except Exception:
        return raw.strip(), [], dict(_EMPTY_CATS)


async def _call(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    if config.provider == "anthropic":
        return await _anthropic(config, prompt, screenshot_b64)
    if config.provider == "google":
        return await _google(config, prompt, screenshot_b64)
    if config.provider == "azure_openai":
        return await _azure_openai(config, prompt, screenshot_b64)
    if config.provider == "azure_foundry":
        return await _azure_foundry(config, prompt, screenshot_b64)
    if config.provider == "openrouter":
        return await _openrouter(config, prompt, screenshot_b64)
    return await _openai_compat(config, prompt, screenshot_b64)


def _content_part_text(part: Any) -> str:
    if part is None:
        return ""
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        part_type = str(part.get("type") or "")
        if part_type in ("reasoning", "reasoning_content", "thinking", "thought"):
            return ""
        if part_type in ("text", "output_text", "message"):
            value = part.get("text") or part.get("content")
            return value if isinstance(value, str) else ""
        value = part.get("text")
        return value if isinstance(value, str) else ""

    part_type = str(getattr(part, "type", "") or "")
    if part_type in ("reasoning", "reasoning_content", "thinking", "thought"):
        return ""
    text = getattr(part, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(part, "content", None)
    if isinstance(content, str):
        return content
    return ""


def _extract_message_text(message: Any) -> str:
    if message is None:
        return ""

    content = getattr(message, "content", None)
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(_content_part_text(part) for part in content)
    else:
        text = ""

    if text:
        return _strip_thinking_blocks(text).strip()

    # OpenAI-compatible gateways and local servers vary on where they expose
    # visible chain-of-thought / final text for reasoning models.
    for attr in ("reasoning_content", "reasoning", "output_text", "text"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip():
            return _strip_thinking_blocks(value).strip()
    return ""


def _model_needs_reasoning_params(model: str) -> bool:
    lowered = (model or "").lower().split("/")[-1]
    return (
        lowered.startswith(("o1", "o3", "o4"))
        or lowered.startswith("gpt-5")
        or "reasoning" in lowered
    )


def _chat_completion_kwargs(
    *,
    config: LLMConfig,
    messages: list[dict],
    provider: str,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
    }
    token_limit = min(config.max_tokens, 1024)
    if provider in ("openai", "azure_openai") and _model_needs_reasoning_params(config.model):
        kwargs["max_completion_tokens"] = token_limit
    else:
        kwargs["max_tokens"] = token_limit

    if not (provider in ("openai", "azure_openai") and _model_needs_reasoning_params(config.model)):
        kwargs["temperature"] = config.temperature
    return kwargs


async def _create_chat_completion(client: Any, kwargs: dict[str, Any]) -> Any:
    try:
        return await client.chat.completions.create(**kwargs)
    except Exception as exc:
        message = str(exc).lower()
        retry_kwargs = dict(kwargs)
        changed = False

        if "max_tokens" in retry_kwargs and ("max_tokens" in message or "max completion" in message):
            retry_kwargs["max_completion_tokens"] = retry_kwargs.pop("max_tokens")
            changed = True
        if "temperature" in retry_kwargs and "temperature" in message:
            retry_kwargs.pop("temperature", None)
            changed = True

        if not changed:
            raise
        return await client.chat.completions.create(**retry_kwargs)


def _extract_first_choice_text(resp: Any) -> str:
    choices = getattr(resp, "choices", None) or []
    if not choices:
        return ""
    return _extract_message_text(getattr(choices[0], "message", None))


async def _anthropic(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    import anthropic as _ant

    client = _ant.AsyncAnthropic(api_key=config.api_key)
    content: list = []
    if screenshot_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
        })
    content.append({"type": "text", "text": prompt})
    resp = await client.messages.create(
        model=config.model,
        max_tokens=min(config.max_tokens, 1024),
        temperature=config.temperature,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(_content_part_text(block) for block in (resp.content or [])).strip()


async def _google(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.api_key)
    parts: list = []
    if screenshot_b64:
        parts.append(types.Part.from_bytes(
            data=base64.b64decode(screenshot_b64),
            mime_type="image/png",
        ))
    parts.append(prompt)

    resp = await client.aio.models.generate_content(
        model=config.model,
        contents=parts,
        config=types.GenerateContentConfig(
            max_output_tokens=min(config.max_tokens, 8192),
            temperature=config.temperature,
        ),
    )
    return resp.text or ""


async def _openai_compat(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    from openai import AsyncOpenAI

    kwargs: dict = {"api_key": config.api_key or "not-needed"}
    if config.base_url:
        # The OpenAI SDK appends e.g. "/chat/completions" directly to base_url.
        # LM Studio / Ollama expect the /v1 prefix, so ensure it's present.
        base = config.base_url.rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        kwargs["base_url"] = base
    client = AsyncOpenAI(**kwargs)

    if screenshot_b64:
        msg_content: object = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
            {"type": "text", "text": prompt},
        ]
    else:
        msg_content = prompt

    resp = await _create_chat_completion(
        client,
        _chat_completion_kwargs(
            config=config,
            provider=config.provider,
            messages=[{"role": "user", "content": msg_content}],
        ),
    )
    return _extract_first_choice_text(resp)


async def _openrouter(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.api_key, base_url=OPENROUTER_BASE_URL)

    if screenshot_b64:
        msg_content: object = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
            {"type": "text", "text": prompt},
        ]
    else:
        msg_content = prompt

    resp = await _create_chat_completion(
        client,
        _chat_completion_kwargs(
            config=config,
            provider=config.provider,
            messages=[{"role": "user", "content": msg_content}],
        ),
    )
    return _extract_first_choice_text(resp)


async def _azure_openai(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        api_key=config.api_key,
        azure_endpoint=config.base_url,
        api_version="2024-12-01-preview",
    )

    if screenshot_b64:
        msg_content: object = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
            {"type": "text", "text": prompt},
        ]
    else:
        msg_content = prompt

    resp = await _create_chat_completion(
        client,
        _chat_completion_kwargs(
            config=config,
            provider=config.provider,
            messages=[{"role": "user", "content": msg_content}],
        ),
    )
    return _extract_first_choice_text(resp)


async def _azure_foundry(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    """Azure AI Foundry serverless endpoints are OpenAI-compatible."""
    from openai import AsyncOpenAI

    base = (config.base_url or "").rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"

    client = AsyncOpenAI(api_key=config.api_key, base_url=base)

    if screenshot_b64:
        msg_content: object = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
            {"type": "text", "text": prompt},
        ]
    else:
        msg_content = prompt

    resp = await _create_chat_completion(
        client,
        _chat_completion_kwargs(
            config=config,
            provider=config.provider,
            messages=[{"role": "user", "content": msg_content}],
        ),
    )
    return _extract_first_choice_text(resp)


# ── Scanner LLM functions ─────────────────────────────────────────────────────

_PLAN_PROMPT = """\
You are a web application penetration tester. Given the page details below, generate a list \
of HTTP probes to test for OWASP Top 10 vulnerabilities.

URL: {url}
Title: {title}
LLM Context: {context}

Page categories:
- Authentication Required: {req_auth}
- Takes User Input: {takes_input}
- Contains Object Reference: {has_object_ref}
- Contains Business Logic: {has_business_logic}

Applicable OWASP checks: {applicable}

{users_section}
{category_guidance}

Return ONLY valid JSON — an array of probe objects (no markdown fences):
[
  {{
    "type": "http",
    "method": "GET",
    "url": "https://...",
    "params": {{}},
    "headers": {{}},
    "body": null,
    "as_user": null,
    "desc": "Brief description of what this probe tests"
  }},
  {{
    "type": "form",
    "url": "https://...",
    "selector": "input[name='search']",
    "payload": "<script>alert(1)</script>",
    "submit_selector": "button[type=submit]",
    "as_user": null,
    "desc": "XSS in search field"
  }},
  {{
    "type": "idor",
    "url": "https://app.com/users/42",
    "as_user": "bob",
    "desc": "IDOR on user ID tested as low-privilege user"
  }}
]

General rules:
- Maximum 60 probes total. Prefer more targeted input-validation probes over repeating the same
    authorization/IDOR pattern. If you cannot include everything, preserve coverage in this order:
    SQL injection, XSS, object-reference tampering, authentication/authorization bypass, then other checks.
- "http" probes: sent directly via HTTP client (auth bypass, header checks, URL/query param injection, JSON/form body tampering, SSRF).
- "form" probes: require browser interaction (form input injection where CSRF tokens are needed).
- "idor" probes: mark a URL that contains an object ID for IDOR testing. Use ONE per URL — the \
scanner automatically finds peer IDs from the crawl and tests a ±500 range. \
Do NOT generate individual http probes for each sequential ID.
- Object references are not limited to REST-style path IDs. When testing authorization or IDOR, inspect and mutate IDs in:
    - path segments such as /accounts/42 or /api/users/7;
    - GET query parameters such as ?id=42, ?accountId=42, ?user_id=7;
    - request bodies for POST/PUT/PATCH/DELETE, including JSON objects, nested JSON objects/arrays, and form-like fields.
- For query-string IDs, put mutated values in the "params" object or in the URL query string.
- For JSON body IDs, put a JSON object/array in "body" and include "Content-Type": "application/json" in "headers" when appropriate.
- "as_user": set to a username from the available test users list to send the probe authenticated \
as that specific user. Set to null to use the primary session. Use this for authorization bypass \
testing — e.g. send a request as a low-privilege user to an endpoint that should be admin-only.
- For auth bypass probes: include a version with empty Cookie and Authorization headers.
- For injection probes, generate multiple payload variants per discovered input. Do not stop after one
    generic payload. Cover reflected, stored-like, encoded, quote-breaking, numeric, boolean, and timing cases
    where relevant. Keep payloads safe and non-destructive.
    - SQLi boolean/string: ' OR '1'='1'--  /  " OR "1"="1"--  /  admin'--
    - SQLi numeric: 1 OR 1=1--  /  0 OR 1=1  /  -1 OR 1=1
    - SQLi error/union/order: ' UNION SELECT NULL--  /  1' ORDER BY 999--  /  ' AND extractvalue(1,concat(0x7e,version()))--
    - SQLi timing: 1 AND SLEEP(1)--  /  '; WAITFOR DELAY '0:0:1'--  /  1); SELECT pg_sleep(1)--
    - XSS HTML/script: <script>alert(1)</script>  /  "><script>alert(1)</script>
    - XSS attribute breakouts: "><img src=x onerror=alert(1)>  /  ' autofocus onfocus=alert(1) x='
    - XSS SVG/event: <svg onload=alert(1)>  /  <details open ontoggle=alert(1)>
    - XSS encoded/url contexts: javascript:alert(1)  /  %3Cscript%3Ealert(1)%3C/script%3E
  - SSTI: {{7*7}}  /  ${{7*7}}
  - Path traversal: ../../../etc/passwd  /  ..%2F..%2Fetc%2Fpasswd
  - SSRF: http://169.254.169.254/latest/meta-data/
  - CMDi: ; echo aespa_probe  /  $(echo aespa_probe)
- Do NOT generate probes for checks not in the applicable list.
- Only generate probes relevant to this specific page."""


def _build_users_section(users: list[dict] | None) -> str:
    if not users:
        return ""
    lines = [
        "Available test users:",
        "Use the \"as_user\" field with one of these usernames to send a probe authenticated as that user.",
        "This is essential for testing broken access control (A01) — e.g. accessing admin resources",
        "as a regular user, or accessing another user's data.",
        "",
    ]
    for u in users:
        label = f" ({u['label']})" if u.get("label") else ""
        lines.append(f"  - {u['username']}{label}")
    return "\n".join(lines)


def _build_category_guidance(categories: dict, users: list[dict] | None = None) -> str:
    sections: list[str] = []

    if categories.get("has_object_ref"):
        user_note = ""
        if users:
            usernames = ", ".join(f'"{u["username"]}"' for u in users)
            user_note = (
                f"\n  • Set 'as_user' on IDOR probes to test cross-user access: use {usernames}."
            )
        sections.append(
            "OBJECT REFERENCE — HIGH PRIORITY (A01):\n"
            "This page contains or may use object IDs. Examine every object reference location, "
            "not only REST-style path segments:\n"
            "  • Path IDs: /accounts/42, /api/users/7, /orders/123.\n"
            "  • GET/query IDs: ?id=42, ?accountId=42, ?user_id=7, ?order=123.\n"
            "  • POST/PUT/PATCH/DELETE body IDs: JSON fields, nested JSON objects/arrays, and form-like body fields.\n"
            "Emit ONE 'idor' type probe per URL that contains a path object ID. The scanner will "
            "look up peer IDs from other crawled users and test a ±500 range automatically — do "
            "NOT generate individual http probes for each sequential path ID.\n"
            "Additionally, generate targeted 'http' probes for query and body object references:\n"
            "  • Substitute another user's known/likely ID into query parameters using the 'params' object.\n"
            "  • Replay POST/PUT/PATCH requests with a different user's ID substituted in JSON/body fields.\n"
            "  • Include nested JSON cases such as {'account': {'id': '...'}} or arrays where the context suggests them.\n"
            "  • Try string IDs where numeric is expected ('admin', 'null', '../../etc/passwd')."
            + user_note
        )

    if categories.get("takes_input"):
        sections.append(
            "TAKES INPUT — HIGHEST PRIORITY FOR THIS PAGE (A03, A10):\n"
            "This page accepts user input. Identify every query parameter, form field, and "
            "JSON body field from the URL and context, including request body excerpts captured during crawling.\n"
            "Prioritize SQL injection and XSS before lower-value auth/header probes. For each discovered "
            "input, generate several focused SQLi and XSS probes, not just one payload.\n"
            "SQLi coverage to include when applicable:\n"
            "  • Boolean/string auth-bypass style: ' OR '1'='1'--, \" OR \"1\"=\"1\"--, admin'--\n"
            "  • Numeric fields: 1 OR 1=1--, 0 OR 1=1, -1 OR 1=1\n"
            "  • Error/union/order probes: ' UNION SELECT NULL--, 1' ORDER BY 999--\n"
            "  • Low-impact timing probes: 1 AND SLEEP(1)--, '; WAITFOR DELAY '0:0:1'--, 1); SELECT pg_sleep(1)--\n"
            "XSS coverage to include when applicable:\n"
            "  • HTML/script contexts: <script>alert(1)</script>, \"><script>alert(1)</script>\n"
            "  • Attribute breakouts: \"><img src=x onerror=alert(1)>, ' autofocus onfocus=alert(1) x='\n"
            "  • SVG/event handlers: <svg onload=alert(1)>, <details open ontoggle=alert(1)>\n"
            "  • Encoded/url contexts: javascript:alert(1), %3Cscript%3Ealert(1)%3C/script%3E\n"
            "Also include, after SQLi/XSS coverage:\n"
            "  • SSTI: {{7*7}}  /  ${{7*7}}  /  <%= 7*7 %>\n"
            "  • Path traversal: ../../../etc/passwd  /  ..%2F..%2Fetc%2Fpasswd\n"
            "  • SSRF: http://169.254.169.254/latest/meta-data/\n"
            "  • CMDi: ; echo aespa_probe  /  $(echo aespa_probe)\n"
            "Use 'form' type probes for fields inside HTML forms; 'http' type for URL params and API bodies. "
            "For JSON APIs, replay the observed body shape and replace one field at a time with SQLi/XSS payloads. "
            "If there are many fields, test up to the five most security-relevant fields first: id/account/user/order, "
            "search/query/filter/sort, name/title/description/comment/message, email/username, amount/quantity."
        )

    if categories.get("req_auth"):
        sections.append(
            "REQUIRES AUTH (A07):\n"
            "  • Access the page with no cookies and no Authorization header — expect 401/403.\n"
            "  • Try common credential bypass headers: X-Original-URL, X-Forwarded-For: 127.0.0.1.\n"
            "  • Try path variations: append /.json, ;.css, %20 to the URL.\n"
            "  • If it's an API, try sending an expired/malformed JWT in the Authorization header."
        )

    if categories.get("has_business_logic"):
        sections.append(
            "BUSINESS LOGIC (A04):\n"
            "  • Infer the business operation from the context (e.g. transfer, purchase, withdraw).\n"
            "  • Try negative amounts, zero amounts, and extremely large values.\n"
            "  • Try replay: re-send the same action twice rapidly.\n"
            "  • Try skipping steps: access later steps of a multi-step flow directly.\n"
            "  • Try parameter tampering: change price/amount/quantity fields to 0 or -1."
        )

    return "\n\n".join(sections) if sections else ""

_ANALYSE_PROMPT = """\
You are a web application penetration tester reviewing probe results for OWASP vulnerabilities.

Page URL: {url}

Probe results:
{results}

For each result, determine whether it indicates a real vulnerability. Consider:
- Unexpected data disclosure (other users' data, admin data)
- Injection indicators (SQL errors, reflected payloads, template evaluation)
- Auth bypass (200 on a protected resource without credentials)
- Misconfiguration (missing security headers, verbose errors, version disclosure)
- SSRF responses (cloud metadata, internal IP responses)

Return ONLY valid JSON — an array of findings (empty array [] if none found, no markdown fences):
[
  {{
    "owasp_category": "A03",
    "severity": "high",
    "title": "Reflected XSS in search parameter",
    "description": "The search parameter reflects user input without encoding, allowing script injection.",
    "affected_url": "https://example.com/search?q=<script>alert(1)</script>",
    "evidence": "The payload was reflected verbatim in the response body at position 234."
  }}
]

The "affected_url" must be the exact URL from the probe result that triggered this finding (copy it verbatim from the probe results above).

Severity levels: critical, high, medium, low, info
OWASP categories: A01 (Broken Access Control), A02 (Cryptographic Failures), \
A03 (Injection), A04 (Insecure Design), A05 (Security Misconfiguration), \
A06 (Vulnerable Components), A07 (Auth Failures), A08 (Data Integrity), \
A09 (Logging/Monitoring), A10 (SSRF)

Be conservative — only report confirmed or highly likely issues, not theoretical ones."""


async def plan_probes(
    config: LLMConfig,
    url: str,
    title: str,
    context: str,
    categories: dict[str, Any],
    applicable_checks: list[str],
    users: list[dict] | None = None,
) -> list[dict]:
    """Ask the LLM to generate a probe plan for a page. Returns list of probe dicts.

    users: optional list of {"username": str, "label": str|None} describing the test accounts
    available. When provided, the LLM can set "as_user" on each probe to control which
    authenticated session is used when sending the request.
    """
    prompt = _PLAN_PROMPT.format(
        url=url,
        title=title or "(no title)",
        context=context or "(no context)",
        req_auth=categories.get("req_auth"),
        takes_input=categories.get("takes_input"),
        has_object_ref=categories.get("has_object_ref"),
        has_business_logic=categories.get("has_business_logic"),
        applicable=", ".join(applicable_checks) if applicable_checks else "general checks only",
        users_section=_build_users_section(users),
        category_guidance=_build_category_guidance(categories, users=users),
    )
    raw = await _call(config, prompt, None)
    try:
        probes = _extract_json(raw or "", expect=list)
        if not isinstance(probes, list):
            return []
        # Include "idor" probes so that as_user set by the LLM is preserved when the
        # scanner expands them into concrete HTTP requests.
        return [p for p in probes if isinstance(p, dict) and p.get("type") in ("http", "form", "idor")]
    except Exception:
        return []


async def analyse_probes(
    config: LLMConfig,
    url: str,
    results: list[dict],
) -> list[dict]:
    """Ask the LLM to analyse probe results and return a list of findings."""
    if not results:
        return []
    results_text = "\n\n".join(
        f"--- Probe: {r.get('desc', r.get('url', '?'))} ---\n"
        f"Sent as user: {r.get('as_user') or '(primary session)'}\n"
        f"Status: {r.get('status')}\n"
        f"Response headers: {json.dumps(r.get('headers', {}))}\n"
        f"Response body (truncated): {str(r.get('body', ''))[:500]}"
        for r in results
    )
    prompt = _ANALYSE_PROMPT.format(url=url, results=results_text)
    raw = await _call(config, prompt, None)
    try:
        findings = _extract_json(raw or "", expect=list)
        if not isinstance(findings, list):
            return []
        required = {"owasp_category", "severity", "title", "description", "evidence"}
        return [f for f in findings if isinstance(f, dict) and required.issubset(f)]
    except Exception:
        return []


# ── Validation LLM functions ──────────────────────────────────────────────────

_VALIDATION_PLAN_PROMPT = """\
You are a web application penetration tester. A security scanner flagged a potential vulnerability.
Generate targeted HTTP probes to CONFIRM or REFUTE this specific finding.

Finding:
- Title: {title}
- OWASP Category: {owasp_category}
- Severity: {severity}
- Affected URL: {affected_url}
- Description: {description}

Original evidence:
{evidence}

{users_section}

Strategy:
- Reproduce the exact condition that triggered the finding.
- For auth/access control issues: test with both privileged and unprivileged users (set as_user).
- For injection findings: repeat the exact payload and look for the evaluation marker.
- For missing header / config issues: re-request the URL and inspect the response.
- For IDOR: re-request the affected URL with a different user's session (set as_user).

Return ONLY valid JSON — an array of up to 10 probe objects (no markdown fences).
Use the same probe format as scanning (type, method, url, params, headers, body, as_user, desc).
Return [] if no targeted probes can be generated."""


_VALIDATION_VERDICT_PROMPT = """\
You are a web application penetration tester reviewing validation probe results.

Original finding:
- Title: {title}
- Description: {description}

Original evidence:
{evidence}

Validation probe results:
{results}

Based on the probe results, determine whether this finding is CONFIRMED or a FALSE POSITIVE.

Consider:
- Does any probe reproduce the vulnerability? (injection marker present, access granted, etc.)
- Does the server behaviour match what the original finding described?
- Could the original evidence have been a false positive (coincidental keyword, expected redirect)?

Return ONLY valid JSON (no markdown fences):
{{
  "verdict": "confirmed",
  "reasoning": "The validation probe reproduced the issue: the payload was reflected verbatim."
}}

"verdict" must be exactly "confirmed" or "false_positive".
"reasoning" should be 1–3 sentences explaining the decision."""


async def plan_validation_probes(
    config: LLMConfig,
    title: str,
    description: str,
    affected_url: str,
    evidence: str,
    owasp_category: str,
    severity: str,
    users: list[dict] | None = None,
) -> list[dict]:
    """Generate targeted probes to confirm or refute a specific finding."""
    prompt = _VALIDATION_PLAN_PROMPT.format(
        title=title,
        owasp_category=owasp_category,
        severity=severity,
        affected_url=affected_url,
        description=description,
        evidence=evidence[:2000],
        users_section=_build_users_section(users),
    )
    raw = await _call(config, prompt, None)
    try:
        probes = _extract_json(raw or "", expect=list)
        if not isinstance(probes, list):
            return []
        return [p for p in probes if isinstance(p, dict) and p.get("type") in ("http", "form")]
    except Exception:
        return []


async def validate_finding_result(
    config: LLMConfig,
    title: str,
    description: str,
    evidence: str,
    probe_results: list[dict],
) -> dict:
    """Return {"verdict": "confirmed"|"false_positive", "reasoning": str}."""
    if not probe_results:
        return {"verdict": "false_positive", "reasoning": "No validation probes reproduced the issue."}
    results_text = "\n\n".join(
        f"--- Probe: {r.get('desc', r.get('url', '?'))} ---\n"
        f"Sent as user: {r.get('as_user') or '(primary session)'}\n"
        f"Status: {r.get('status')}\n"
        f"Response headers: {json.dumps(r.get('headers', {}))}\n"
        f"Response body (truncated): {str(r.get('body', ''))[:400]}"
        for r in probe_results
    )
    prompt = _VALIDATION_VERDICT_PROMPT.format(
        title=title,
        description=description,
        evidence=evidence[:1500],
        results=results_text,
    )
    raw = await _call(config, prompt, None)
    try:
        data = _extract_json(raw or "", expect=dict)
        verdict = data.get("verdict", "")
        if verdict not in ("confirmed", "false_positive"):
            verdict = "confirmed"
        return {"verdict": verdict, "reasoning": str(data.get("reasoning", ""))}
    except Exception:
        return {"verdict": "confirmed", "reasoning": "Could not parse LLM validation response."}
