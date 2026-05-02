"""Abstract LLM client — wraps Anthropic, OpenAI, OpenAI-compatible, and Google Gemini APIs."""
from __future__ import annotations

import base64
import json
import re
from typing import Any, Optional

from aespa.models import LLMConfig


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

    # Strip thinking/reasoning blocks
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    # Strip markdown fences
    text = re.sub(r"```(?:json|python)?\s*", "", text).strip().rstrip("`").strip()

    # Fast path: the whole string is valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON container matching `expect`
    open_ch  = "[" if expect is list else "{"
    close_ch = "]" if expect is list else "}"
    start = text.find(open_ch)
    if start == -1:
        raise ValueError(f"no '{open_ch}' found in LLM response")

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
                return json.loads(text[start : i + 1])

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

For suggested_links: include up to 10 absolute URLs from this page (same domain) that reveal the most \
important or interesting application functionality. Prefer links to forms, features, user actions, \
admin areas, API endpoints, etc. over navigation links already visible on every page.

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
    return await _openai_compat(config, prompt, screenshot_b64)


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
    # resp.content is a list of blocks; find the first one that has text.
    # (Extended thinking models may prepend a ThinkingBlock before the TextBlock.)
    for block in (resp.content or []):
        text = getattr(block, "text", None)
        if text is not None:
            return str(text)
    return ""


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

    resp = await client.chat.completions.create(
        model=config.model,
        max_tokens=min(config.max_tokens, 1024),
        temperature=config.temperature,
        messages=[{"role": "user", "content": msg_content}],
    )
    # Safely access choices — guard against None or empty list
    choices = getattr(resp, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    if message is None:
        return ""
    return getattr(message, "content", None) or ""


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
    "desc": "Brief description of what this probe tests"
  }},
  {{
    "type": "form",
    "url": "https://...",
    "selector": "input[name='search']",
    "payload": "<script>alert(1)</script>",
    "submit_selector": "button[type=submit]",
    "desc": "XSS in search field"
  }},
  {{
    "type": "idor",
    "url": "https://app.com/users/42",
    "desc": "IDOR on user ID — scanner will test adjacent and crawled IDs automatically"
  }}
]

General rules:
- Maximum 30 probes total.
- "http" probes: sent directly via HTTP client (auth bypass, header checks, URL param injection, SSRF).
- "form" probes: require browser interaction (form input injection where CSRF tokens are needed).
- "idor" probes: mark a URL that contains an object ID for IDOR testing. Use ONE per URL — the \
scanner automatically finds peer IDs from the crawl and tests a ±500 range. \
Do NOT generate individual http probes for each sequential ID.
- For auth bypass probes: include a version with empty Cookie and Authorization headers.
- For injection payloads use safe, non-destructive test strings:
  - SQLi: ' OR '1'='1  /  1' AND SLEEP(0)--  /  1; SELECT 1--
  - XSS: <script>alert(1)</script>  /  "><img src=x onerror=alert(1)>
  - SSTI: {{7*7}}  /  ${{7*7}}
  - Path traversal: ../../../etc/passwd  /  ..%2F..%2Fetc%2Fpasswd
  - SSRF: http://169.254.169.254/latest/meta-data/
  - CMDi: ; echo aespa_probe  /  $(echo aespa_probe)
- Do NOT generate probes for checks not in the applicable list.
- Only generate probes relevant to this specific page."""


def _build_category_guidance(categories: dict) -> str:
    sections: list[str] = []

    if categories.get("has_object_ref"):
        sections.append(
            "OBJECT REFERENCE — HIGH PRIORITY (A01):\n"
            "This page contains numeric object IDs in the URL. Emit ONE 'idor' type probe per "
            "URL that contains an ID. The scanner will look up peer IDs from other crawled users "
            "and test a ±500 range automatically — do NOT generate individual http probes for "
            "each sequential ID.\n"
            "Additionally, generate 'http' probes for:\n"
            "  • String IDs where numeric is expected ('admin', 'null', '../../etc/passwd').\n"
            "  • POST/PUT replay with a different user's ID substituted in the request body."
        )

    if categories.get("takes_input"):
        sections.append(
            "TAKES INPUT — HIGH PRIORITY (A03, A10):\n"
            "This page accepts user input. Identify every query parameter, form field, and "
            "JSON body field from the URL and context.\n"
            "For each parameter test ALL of the following:\n"
            "  • SQLi: ' OR '1'='1  /  1' AND SLEEP(0)--  /  1 UNION SELECT NULL--\n"
            "  • XSS: <script>alert(1)</script>  /  \"><img src=x onerror=alert(1)>\n"
            "  • SSTI: {{7*7}}  /  ${{7*7}}  /  <%= 7*7 %>\n"
            "  • Path traversal: ../../../etc/passwd  /  ..%2F..%2Fetc%2Fpasswd\n"
            "  • SSRF: http://169.254.169.254/latest/meta-data/\n"
            "  • CMDi: ; echo aespa_probe  /  $(echo aespa_probe)\n"
            "Use 'form' type probes for fields inside HTML forms; 'http' type for URL params.\n"
            "Generate at least one probe per payload category per input field."
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
) -> list[dict]:
    """Ask the LLM to generate a probe plan for a page. Returns list of probe dicts."""
    prompt = _PLAN_PROMPT.format(
        url=url,
        title=title or "(no title)",
        context=context or "(no context)",
        req_auth=categories.get("req_auth"),
        takes_input=categories.get("takes_input"),
        has_object_ref=categories.get("has_object_ref"),
        has_business_logic=categories.get("has_business_logic"),
        applicable=", ".join(applicable_checks) if applicable_checks else "general checks only",
        category_guidance=_build_category_guidance(categories),
    )
    raw = await _call(config, prompt, None)
    try:
        probes = _extract_json(raw or "", expect=list)
        if not isinstance(probes, list):
            return []
        return [p for p in probes if isinstance(p, dict) and p.get("type") in ("http", "form")]
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
