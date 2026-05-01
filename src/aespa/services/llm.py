"""Abstract LLM client — wraps Anthropic, OpenAI, and OpenAI-compatible APIs."""
from __future__ import annotations

import json
import re
from typing import Optional

from aespa.models import LLMConfig

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
  "suggested_links": ["absolute_url_1", "absolute_url_2"]
}}

For suggested_links: include up to 10 absolute URLs from this page (same domain) that reveal the most \
important or interesting application functionality. Prefer links to forms, features, user actions, \
admin areas, API endpoints, etc. over navigation links already visible on every page."""


async def analyse_page(
    config: LLMConfig,
    url: str,
    title: str,
    text: str,
    screenshot_b64: Optional[str] = None,
) -> tuple[str, list[str]]:
    """Return (context_description, suggested_links_list)."""
    prompt = _ANALYSIS_PROMPT.format(
        url=url,
        title=title or "(no title)",
        text=text[:8000],
    )
    raw = await _call(config, prompt, screenshot_b64 if config.use_vision else None)
    return _parse(raw, url)


def _parse(raw: Optional[str], page_url: str) -> tuple[str, list[str]]:
    if not raw:
        return "", []
    try:
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        data = json.loads(clean)
        if not isinstance(data, dict):
            # Model returned a JSON array or scalar — use raw text as context
            return raw.strip(), []
        context = str(data.get("context") or raw)
        links = data.get("suggested_links") or []
        if not isinstance(links, list):
            links = []
        return context, [str(l) for l in links if isinstance(l, str) and l.startswith("http")]
    except Exception:
        # Any parse failure: return the raw text as-is for context
        return raw.strip(), []


async def _call(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    if config.provider == "anthropic":
        return await _anthropic(config, prompt, screenshot_b64)
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
