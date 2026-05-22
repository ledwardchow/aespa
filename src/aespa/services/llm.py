"""Abstract LLM client wrappers for configured provider APIs."""
from __future__ import annotations

import asyncio
import base64
import httpx
import json
import logging
import os
import re
import time
from contextvars import ContextVar
from typing import Any, Optional
from urllib.parse import quote

from aespa.models import LLMConfig

log = logging.getLogger("aespa.llm")

_llm_proxy_var: ContextVar[str | None] = ContextVar('_llm_proxy', default=None)
_run_id_var: ContextVar[int | None] = ContextVar('_run_id', default=None)
_emit_fn_var: ContextVar[Any | None] = ContextVar('_emit_fn', default=None)

# Per-run token usage accumulator: {run_id: {model: {"input": N, "output": N, "cache_read": N, "cache_write": N}}}
_run_token_usage: dict[int, dict[str, dict[str, int]]] = {}

# Tracks which run_ids have already been seeded from DB this process lifetime.
_run_token_seeded: set[int] = set()


def _load_bucket_from_db(run_id: int) -> dict[str, dict[str, int]]:
    """Load persisted token usage for a run from the DB (best-effort)."""
    try:
        from aespa.db import get_engine
        from aespa.models import TestRun
        from sqlmodel import Session as _Session
        with _Session(get_engine()) as s:
            run = s.get(TestRun, run_id)
            if run and run.token_usage_json:
                return json.loads(run.token_usage_json)
    except Exception:
        pass
    return {}


def _persist_bucket_to_db(run_id: int, bucket: dict) -> None:
    """Write the current in-memory bucket for a run back to the DB (best-effort)."""
    try:
        from aespa.db import get_engine
        from aespa.models import TestRun
        from sqlmodel import Session as _Session
        with _Session(get_engine()) as s:
            run = s.get(TestRun, run_id)
            if run:
                run.token_usage_json = json.dumps(bucket)
                s.add(run)
                s.commit()
    except Exception:
        pass


def set_run_context(run_id: int, emit_fn: Any) -> None:
    """Set the current run context so LLM calls track token usage automatically.

    Seeds the in-memory bucket from DB on first call for this run_id so that
    token counts accumulate correctly across server restarts.
    """
    _run_id_var.set(run_id)
    _emit_fn_var.set(emit_fn)
    if run_id not in _run_token_seeded:
        existing = _load_bucket_from_db(run_id)
        if existing:
            # Merge DB data into the (possibly already-populated) in-memory bucket.
            bucket = _run_token_usage.setdefault(run_id, {})
            for model, counts in existing.items():
                if model not in bucket:
                    bucket[model] = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
                for k in ("input", "output", "cache_read", "cache_write"):
                    bucket[model][k] = max(bucket[model].get(k, 0), counts.get(k, 0))
        _run_token_seeded.add(run_id)


def clear_run_context() -> None:
    _run_id_var.set(None)
    _emit_fn_var.set(None)


def _record_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> None:
    """Accumulate token counts for the active run and fire a SSE event."""
    run_id = _run_id_var.get()
    if run_id is None:
        return
    bucket = _run_token_usage.setdefault(run_id, {})
    entry = bucket.setdefault(model, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0})
    entry["input"] += input_tokens
    entry["output"] += output_tokens
    entry["cache_read"] += cache_read_tokens
    entry["cache_write"] += cache_write_tokens
    _persist_bucket_to_db(run_id, bucket)
    emit_fn = _emit_fn_var.get()
    if emit_fn:
        try:
            total_in = sum(v["input"] for v in bucket.values())
            total_out = sum(v["output"] for v in bucket.values())
            total_cache_read = sum(v.get("cache_read", 0) for v in bucket.values())
            total_cache_write = sum(v.get("cache_write", 0) for v in bucket.values())
            emit_fn({
                "type": "token_usage_update",
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
                "totals": {
                    "total_input": total_in,
                    "total_output": total_out,
                    "total_cache_read": total_cache_read,
                    "total_cache_write": total_cache_write,
                    "by_model": {m: dict(v) for m, v in bucket.items()},
                },
            })
        except Exception:
            pass


def get_run_token_usage(run_id: int) -> dict:
    """Return accumulated token usage for a run.

    If the run isn't in the in-memory dict (e.g. after a server restart), falls
    back to the persisted DB value so the REST endpoint always returns data.
    """
    bucket = _run_token_usage.get(run_id)
    if bucket is None:
        bucket = _load_bucket_from_db(run_id)
    return {
        "total_input": sum(v["input"] for v in bucket.values()),
        "total_output": sum(v["output"] for v in bucket.values()),
        "total_cache_read": sum(v.get("cache_read", 0) for v in bucket.values()),
        "total_cache_write": sum(v.get("cache_write", 0) for v in bucket.values()),
        "by_model": {m: dict(v) for m, v in bucket.items()},
    }


def set_llm_proxy(url: str | None) -> None:
    _llm_proxy_var.set(url)


def _llm_client_kwargs() -> dict:
    """Returns {'http_client': ...} for SDK clients (Anthropic, OpenAI), always with verify=False."""
    proxy = _llm_proxy_var.get()
    return {"http_client": httpx.AsyncClient(verify=False, **{"proxy": proxy} if proxy else {})}


def _make_llm_http_client(**kwargs) -> httpx.AsyncClient:
    """Creates an httpx client for direct LLM calls, always with verify=False."""
    kwargs.setdefault("verify", False)
    if proxy := _llm_proxy_var.get():
        kwargs["proxy"] = proxy
    return httpx.AsyncClient(**kwargs)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ANALYSE_RESULTS_TEXT_BUDGET = 80_000
ANALYSE_RESULTS_PER_BATCH = 20
_THINKING_CONTEXT_TOOL_ARG_KEYS = {
    "site_map": ("filter", "search", "type", "flags", "limit"),
    "page_detail": ("page_id", "url", "include"),
    "history_search": ("query", "search", "limit"),
    "finding_list": ("severity", "owasp_category", "search", "limit"),
}
_THINKING_CONTEXT_TOOLS = frozenset(_THINKING_CONTEXT_TOOL_ARG_KEYS)


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
        # Stripped text has no JSON delimiters — the model may have embedded the answer
        # inside a thinking block.  Try searching the un-stripped original text so we can
        # still extract JSON that appears within <think>...</think> tags.
        raw_no_fence = re.sub(r"```(?:json|python)?\s*", "", raw).strip().rstrip("`").strip()
        alt_starts = [i for i, ch in enumerate(raw_no_fence) if ch == open_ch]
        if alt_starts:
            text = raw_no_fence
            starts = alt_starts
        else:
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


def _extract_action_json(raw: str) -> dict:
    action = _extract_json(raw, expect=dict)
    if not isinstance(action, dict):
        raise ValueError("action response was not a JSON object")
    return action


def _normalize_thinking_action(action: Any) -> Any:
    if not isinstance(action, dict):
        return action

    action_name = str(action.get("action") or "").strip()
    if action_name not in _THINKING_CONTEXT_TOOLS:
        return action

    arg_keys = _THINKING_CONTEXT_TOOL_ARG_KEYS[action_name]
    args = {}
    nested_args = action.get("args")
    if isinstance(nested_args, dict):
        args.update(nested_args)
    for key in arg_keys:
        if key in action and key not in args:
            args[key] = action[key]

    normalized = {key: value for key, value in action.items() if key not in arg_keys}
    normalized["action"] = "tool"
    normalized["tool"] = action_name
    normalized["args"] = args
    return normalized


_THINKING_CORRECTION_PROMPT = """\
Your previous response was not valid for the scanner control loop.

Return exactly one JSON object and no markdown or prose. The object must use one of these
actions: tool, http, browser, jwt, decode_jwt, credential_check, register_account,
finding_write, done.
"""

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
    if config.provider in ("azure_foundry", "azure_foundry_openai"):
        return await _azure_foundry_openai(config, prompt, screenshot_b64)
    if config.provider == "azure_foundry_anthropic":
        return await _azure_foundry_anthropic(config, prompt, screenshot_b64)
    if config.provider == "openrouter":
        return await _openrouter(config, prompt, screenshot_b64)
    if config.provider == "bedrock":
        return await _bedrock(config, prompt, screenshot_b64)
    return await _openai_compat(config, prompt, screenshot_b64)


async def plain_completion(config: LLMConfig, prompt: str) -> str:
    """Send a plain text prompt and return the raw response text."""
    return await _call(config, prompt, None)


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

    fallback_texts: list[str] = []
    # OpenAI-compatible gateways and local servers vary on where they expose
    # visible chain-of-thought / final text for reasoning models.
    for attr in ("reasoning_content", "reasoning", "output_text", "text"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip():
            fallback_texts.append(_strip_thinking_blocks(value).strip())

    if text:
        cleaned = _strip_thinking_blocks(text).strip()
        if not cleaned:
            # Stripping removed everything (entire content was a thinking block with no
            # answer outside).  Prefer a separate reasoning_content / fallback field when
            # available; otherwise return the original text so _extract_json can still
            # find JSON that was embedded inside the thinking block.
            if fallback_texts:
                return fallback_texts[0]
            return text
        if fallback_texts and any(ch in cleaned for ch in ("[", "{")):
            try:
                _extract_json(cleaned, expect=list)
            except Exception:
                try:
                    _extract_json(cleaned, expect=dict)
                except Exception:
                    return fallback_texts[0]
        return cleaned

    if fallback_texts:
        return fallback_texts[0]
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
    token_limit = config.max_tokens
    openai_reasoning_providers = (
        "openai",
        "azure_openai",
        "azure_foundry",
        "azure_foundry_openai",
    )
    uses_reasoning_params = (
        provider in openai_reasoning_providers
        and _model_needs_reasoning_params(config.model)
    )
    if uses_reasoning_params:
        kwargs["max_completion_tokens"] = token_limit
    else:
        kwargs["max_tokens"] = token_limit

    if not uses_reasoning_params:
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

    client = _ant.AsyncAnthropic(api_key=config.api_key, **_llm_client_kwargs())
    content: list = []
    if screenshot_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
        })
    content.append({"type": "text", "text": prompt})
    resp = await client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        messages=[{"role": "user", "content": content}],
    )
    _record_usage(config.model,
                  getattr(resp.usage, "input_tokens", 0),
                  getattr(resp.usage, "output_tokens", 0),
                  cache_read_tokens=getattr(resp.usage, "cache_read_input_tokens", 0),
                  cache_write_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0))
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
            max_output_tokens=config.max_tokens,
            temperature=config.temperature,
        ),
    )
    _um = getattr(resp, "usage_metadata", None)
    _record_usage(config.model,
                  getattr(_um, "prompt_token_count", 0) if _um else 0,
                  getattr(_um, "candidates_token_count", 0) if _um else 0)
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
    kwargs.update(_llm_client_kwargs())
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
    _u = getattr(resp, "usage", None)
    _record_usage(config.model,
                  getattr(_u, "prompt_tokens", 0) if _u else 0,
                  getattr(_u, "completion_tokens", 0) if _u else 0)
    return _extract_first_choice_text(resp)


async def _openrouter(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    from openai import AsyncOpenAI

    _or_kwargs: dict = {"api_key": config.api_key, "base_url": OPENROUTER_BASE_URL, **_llm_client_kwargs()}
    client = AsyncOpenAI(**_or_kwargs)

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
    _u = getattr(resp, "usage", None)
    _record_usage(config.model,
                  getattr(_u, "prompt_tokens", 0) if _u else 0,
                  getattr(_u, "completion_tokens", 0) if _u else 0)
    return _extract_first_choice_text(resp)


async def _azure_openai(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    from openai import AsyncAzureOpenAI

    _az_kwargs: dict = {
        "api_key": config.api_key,
        "azure_endpoint": config.base_url,
        "api_version": "2024-12-01-preview",
        **_llm_client_kwargs(),
    }
    client = AsyncAzureOpenAI(**_az_kwargs)

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
    _u = getattr(resp, "usage", None)
    _record_usage(config.model,
                  getattr(_u, "prompt_tokens", 0) if _u else 0,
                  getattr(_u, "completion_tokens", 0) if _u else 0)
    return _extract_first_choice_text(resp)


def _azure_foundry_openai_base_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith(("/openai/v1", "/v1")):
        return base
    if ".openai.azure.com" in base or ".services.ai.azure.com" in base:
        return f"{base}/openai/v1"
    return f"{base}/v1"


async def _azure_foundry_openai(
    config: LLMConfig,
    prompt: str,
    screenshot_b64: Optional[str],
) -> str:
    """Azure AI Foundry deployments that expose the OpenAI v1 chat completions API."""
    from openai import AsyncOpenAI

    _afo_kwargs: dict = {
        "api_key": config.api_key,
        "base_url": _azure_foundry_openai_base_url(config.base_url or ""),
        **_llm_client_kwargs(),
    }
    client = AsyncOpenAI(**_afo_kwargs)

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
    _u = getattr(resp, "usage", None)
    _record_usage(config.model,
                  getattr(_u, "prompt_tokens", 0) if _u else 0,
                  getattr(_u, "completion_tokens", 0) if _u else 0)
    return _extract_first_choice_text(resp)


def _azure_foundry_anthropic_messages_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/messages"):
        return base
    if base.endswith("/v1"):
        return f"{base}/messages"
    if base.endswith("/anthropic"):
        return f"{base}/v1/messages"
    if ".openai.azure.com" in base or ".services.ai.azure.com" in base:
        return f"{base}/anthropic/v1/messages"
    return f"{base}/v1/messages"


async def _azure_foundry_anthropic(
    config: LLMConfig,
    prompt: str,
    screenshot_b64: Optional[str],
) -> str:
    """Azure AI Foundry Claude deployments that expose Anthropic Messages semantics."""
    import httpx

    content: list[dict[str, Any]] = []
    if screenshot_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot_b64,
            },
        })
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "messages": [{"role": "user", "content": content}],
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": config.api_key or "",
        "anthropic-version": "2023-06-01",
    }

    async with _make_llm_http_client(timeout=120) as client:
        resp = await client.post(
            _azure_foundry_anthropic_messages_url(config.base_url or ""),
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    _af_u = data.get("usage", {})
    _record_usage(config.model, _af_u.get("input_tokens", 0), _af_u.get("output_tokens", 0),
                  cache_read_tokens=_af_u.get("cache_read_input_tokens", 0),
                  cache_write_tokens=_af_u.get("cache_creation_input_tokens", 0))
    return "".join(_content_part_text(block) for block in (data.get("content") or [])).strip()


def _extract_bedrock_text(data: dict[str, Any]) -> str:
    content = (((data.get("output") or {}).get("message") or {}).get("content") or [])
    if not isinstance(content, list):
        return ""
    return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()


def _bedrock_region_from_url(base_url: str) -> str:
    match = re.search(r"bedrock-runtime[.-]([a-z0-9-]+)\.", base_url)
    return match.group(1) if match else "us-east-1"


async def _bedrock(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    if config.api_key and not config.base_url:
        raise ValueError("Amazon Bedrock Runtime endpoint is required when using an API key")

    content: list[dict[str, Any]] = []
    if screenshot_b64:
        content.append({
            "image": {
                "format": "png",
                "source": {"bytes": screenshot_b64},
            }
        })
    content.append({"text": prompt})

    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": content}],
        "inferenceConfig": {
            "maxTokens": config.max_tokens,
            "temperature": config.temperature,
        },
    }
    if not config.api_key:
        import asyncio as _aio
        import boto3
        from botocore.config import Config as _BotocoreConfig

        region = (
            os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or _bedrock_region_from_url(config.base_url or "")
        )
        profile = os.getenv("AWS_PROFILE")
        _proxy_url = _llm_proxy_var.get()
        _model = config.model
        _messages = payload["messages"]
        _infer = payload["inferenceConfig"]
        _endpoint = config.base_url or None

        def _run_sync() -> dict:
            _session_kwargs = {"profile_name": profile} if profile else {}
            _session = boto3.Session(**_session_kwargs)
            _boto_cfg = _BotocoreConfig(proxies={"http": _proxy_url, "https": _proxy_url}) if _proxy_url else None
            _client = _session.client(
                "bedrock-runtime",
                region_name=region,
                endpoint_url=_endpoint,
                verify=not _proxy_url,
                **{"config": _boto_cfg} if _boto_cfg else {},
            )
            return _client.converse(
                modelId=_model,
                messages=_messages,
                inferenceConfig=_infer,
            )

        loop = _aio.get_event_loop()
        data = await loop.run_in_executor(None, _run_sync)
        _bd_u = data.get("usage", {})
        _record_usage(config.model, _bd_u.get("inputTokens", 0), _bd_u.get("outputTokens", 0),
                      cache_read_tokens=_bd_u.get("cacheReadInputTokenCount", 0),
                      cache_write_tokens=_bd_u.get("cacheWriteInputTokenCount", 0))
        return _extract_bedrock_text(data)

    if not config.base_url:
        raise ValueError("Amazon Bedrock Runtime endpoint is required")
    model_id = quote(config.model, safe="")
    url = f"{config.base_url.rstrip('/')}/model/{model_id}/converse"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with _make_llm_http_client(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        _resp_data = resp.json()
    _bd_u2 = _resp_data.get("usage", {})
    _record_usage(config.model, _bd_u2.get("inputTokens", 0), _bd_u2.get("outputTokens", 0),
                  cache_read_tokens=_bd_u2.get("cacheReadInputTokenCount", 0),
                  cache_write_tokens=_bd_u2.get("cacheWriteInputTokenCount", 0))
    return _extract_bedrock_text(_resp_data)


# ── Scanner LLM functions ─────────────────────────────────────────────────────

_PLAN_PROMPT = """\
You are a web application penetration tester. Given the page details below, generate a list \
of HTTP probes to test for OWASP Top 10 vulnerabilities.

URL: {url}
Title: {title}
LLM Context: {context}
{site_context_section}
Page categories:
- Authentication Required: {req_auth}
- Takes User Input: {takes_input}
- Contains Object Reference: {has_object_ref}
- Contains Business Logic: {has_business_logic}

Applicable OWASP checks: {applicable}

{users_section}
{category_guidance}
{xss_canary_section}
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
            "  • GATE BYPASS (high value): Look for pre-flight check or validation endpoints "
            "    (paths containing /check, /verify, /validate, /preflight, or similar) that the\n"
            "    client calls before a sensitive action. Generate two probes:\n"
            "      1. Call the check endpoint to observe what it enforces (e.g. requires_totp, requires_pin).\n"
            "      2. Call the action endpoint DIRECTLY without completing the check step, omitting any\n"
            "         field the check said was required (e.g. no totp_code, no pin). If the action\n"
            "         succeeds anyway, the enforcement is client-side only and the gate is bypassable.\n"
            "  • Try skipping steps: access later steps of a multi-step flow directly.\n"
            "  • Try parameter tampering: change price/amount/quantity fields to 0 or -1."
        )

    return "\n\n".join(sections) if sections else ""

_SEVERITY_CALIBRATION = """\
Severity calibration:
- Rate generic server or framework version disclosure as info by default, or low if the
  disclosed component is demonstrably obsolete or materially helps exploit a confirmed issue.
- Rate verbose stack traces, file paths, class names, and framework error pages as low by
  default. Raise to medium only when the response exposes secrets, credentials, tokens,
  exploitable SQL details, or sensitive user/business data.
- Rate CORS arbitrary Origin reflection, including Access-Control-Allow-Credentials: true,
  as low by default unless a browser-based proof shows sensitive authenticated data can be
  read cross-origin. Raise only when the evidence demonstrates real data exposure or account
  impact, not merely permissive headers.
- Do not rate informational disclosure as medium or high solely because it is remotely
  reachable. Severity should follow demonstrated impact, not theoretical chaining.
"""


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
    "title": "Reflected XSS in search parameter",
    "description": "The search parameter reflects user input without encoding.",
    "impact": "An attacker could execute JavaScript in a victim's browser and act as that user.",
    "likelihood": "Likely when attacker-controlled links can be delivered to authenticated users.",
    "recommendation": "Encode output by context, validate input, and add regression tests for this parameter.",
    "cvss_score": 6.1,
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
    "severity": "medium",
    "affected_url": "https://example.com/search?q=<script>alert(1)</script>",
    "evidence": "Short summary of the exact request and response evidence that proves the finding."
  }}
]

The "affected_url" must be the exact URL from the probe result that triggered this finding (copy it verbatim from the probe results above).
Write each finding using the report headings represented by these JSON fields:
- description: what is vulnerable and where.
- impact: what an attacker could achieve.
- likelihood: practical exploitability in this observed context.
- recommendation: specific remediation steps.

Score every finding using CVSS v3.1. Provide both cvss_score and cvss_vector.
Set severity from cvss_score: critical 9.0-10.0, high 7.0-8.9,
medium 4.0-6.9, low 0.1-3.9, info 0.0.

{severity_calibration}

Severity levels: critical, high, medium, low, info
OWASP categories: A01 (Broken Access Control), A02 (Cryptographic Failures), \
A03 (Injection), A04 (Insecure Design), A05 (Security Misconfiguration), \
A06 (Vulnerable Components), A07 (Auth Failures), A08 (Data Integrity), \
A09 (Logging/Monitoring), A10 (SSRF)

Be conservative — only report confirmed or highly likely issues, not theoretical ones.
If many findings are present, return the most important confirmed findings first. Keep each field
concise enough for a security report table/detail view; do not include raw full responses when a
short quoted excerpt proves the issue."""


async def plan_probes(
    config: LLMConfig,
    url: str,
    title: str,
    context: str,
    categories: dict[str, Any],
    applicable_checks: list[str],
    users: list[dict] | None = None,
    site_context: str = "",
    xss_canary: str = "",
) -> list[dict]:
    """Ask the LLM to generate a probe plan for a page. Returns list of probe dicts.

    users: optional list of {"username": str, "label": str|None} describing the test accounts
    available. When provided, the LLM can set "as_user" on each probe to control which
    authenticated session is used when sending the request.

    site_context: optional string summarising the site-level test plan produced by
    generate_site_test_plan(). When provided, it primes the LLM with app-wide attack
    hypotheses so individual page plans are more targeted.

    xss_canary: optional unique run-scoped token. When provided, the LLM is instructed
    to embed it in XSS payloads instead of alert(1), enabling cross-page stored XSS detection.
    """
    site_ctx_section = ""
    if site_context:
        site_ctx_section = f"\nSite-level test plan context (use to inform probe selection):\n{site_context}\n"
    xss_canary_section = ""
    if xss_canary:
        xss_canary_section = (
            f"\nStored XSS canary: use '{xss_canary}' as the alert argument in every XSS probe "
            f"instead of alert(1) — e.g. alert('{xss_canary}'), "
            f"onerror=alert('{xss_canary}'), onload=alert('{xss_canary}'). "
            f"Also include a probe that submits the bare token <{xss_canary}> as an input value. "
            f"This allows cross-page stored XSS to be detected in a post-scan sweep.\n"
        )
    prompt = _PLAN_PROMPT.format(
        url=url,
        title=title or "(no title)",
        context=context or "(no context)",
        site_context_section=site_ctx_section,
        req_auth=categories.get("req_auth"),
        takes_input=categories.get("takes_input"),
        has_object_ref=categories.get("has_object_ref"),
        has_business_logic=categories.get("has_business_logic"),
        applicable=", ".join(applicable_checks) if applicable_checks else "general checks only",
        users_section=_build_users_section(users),
        category_guidance=_build_category_guidance(categories, users=users),
        xss_canary_section=xss_canary_section,
    )
    raw = await _call(config, prompt, None)
    try:
        probes = _extract_json(raw or "", expect=list)
        if not isinstance(probes, list):
            return []
        # Include "idor" probes so that as_user set by the LLM is preserved when the
        # scanner expands them into concrete HTTP requests.
        return [p for p in probes if isinstance(p, dict) and p.get("type") in ("http", "form", "idor")]
    except Exception as _exc:
        log.warning(
            "plan_probes: failed to extract probe list from LLM response (%s). "
            "Raw response (first 500 chars): %r",
            _exc,
            (raw or "")[:500],
        )
        return []


async def analyse_probes(
    config: LLMConfig,
    url: str,
    results: list[dict],
    on_batch_complete=None,
) -> list[dict]:
    """Ask the LLM to analyse probe results and return a list of findings.

    on_batch_complete: optional async callable(turn_num, batch_size, batch_findings)
        called after each LLM batch completes.
    """
    if not results:
        return []

    findings: list[dict] = []
    batches = _chunk_probe_results(results)
    for turn_num, batch in enumerate(batches, start=1):
        batch_findings = await _analyse_probe_batch(config, url, batch)
        findings.extend(batch_findings)
        if on_batch_complete is not None:
            await on_batch_complete(turn_num, len(batch), batch_findings)
    return findings


def _format_probe_result(result: dict) -> str:
    return (
        f"--- Probe: {result.get('desc', result.get('url', '?'))} ---\n"
        f"Sent as user: {result.get('as_user') or '(primary session)'}\n"
        f"URL: {result.get('url')}\n"
        f"Status: {result.get('status')}\n"
        f"Request evidence:\n{str(result.get('request_evidence') or '')[:2000]}\n\n"
        f"Response evidence:\n{str(result.get('response_evidence') or '')[:3000]}\n\n"
        f"Response headers: {json.dumps(result.get('headers', {}))}\n"
        f"Response body excerpt: {str(result.get('body', ''))[:1000]}"
    )


def _chunk_probe_results(results: list[dict]) -> list[list[str]]:
    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_size = 0

    for result in results:
        formatted = _format_probe_result(result)
        separator_size = 2 if current_batch else 0
        next_size = current_size + separator_size + len(formatted)
        if current_batch and (
            len(current_batch) >= ANALYSE_RESULTS_PER_BATCH
            or next_size > ANALYSE_RESULTS_TEXT_BUDGET
        ):
            batches.append(current_batch)
            current_batch = []
            current_size = 0
            separator_size = 0
        current_batch.append(formatted)
        current_size += separator_size + len(formatted)

    if current_batch:
        batches.append(current_batch)
    return batches


async def _analyse_probe_batch(
    config: LLMConfig,
    url: str,
    result_texts: list[str],
) -> list[dict]:
    results_text = "\n\n".join(result_texts)
    prompt = _ANALYSE_PROMPT.format(
        url=url,
        results=results_text,
        severity_calibration=_SEVERITY_CALIBRATION,
    )
    raw = await _call(config, prompt, None)
    try:
        findings = _extract_json(raw or "", expect=list)
        if not isinstance(findings, list):
            return []
        required = {
            "owasp_category",
            "severity",
            "title",
            "description",
            "impact",
            "likelihood",
            "recommendation",
            "cvss_score",
            "affected_url",
            "evidence",
        }
        return [finding for finding in findings if isinstance(finding, dict) and required.issubset(finding)]
    except Exception as exc:
        log.warning(
            "analyse_probes: failed to extract findings from LLM response (%s). "
            "Raw response (first 500 chars): %r",
            exc,
            (raw or "")[:500],
        )
        return []


# ── Site-level test plan ──────────────────────────────────────────────────────

_SITE_PLAN_PROMPT = """\
You are a senior web application penetration tester preparing a security assessment.

Below is a summary of all pages discovered during crawling of the target web application.
Analyse the attack surface, reason through the application's architecture, and produce a
structured test plan with specific, actionable vulnerability hypotheses.

Target base URL: {base_url}

Discovered pages ({page_count} total):
{pages_summary}

Consider:
- What kind of application is this? (auth model, user roles, key data objects)
- What are the highest-value attack targets? (admin panels, financial operations, \
ID-bearing endpoints, privileged actions)
- What systemic vulnerabilities are likely based on the observed structure and page categories?
- What cross-endpoint attack chains deserve testing? For example: auth bypass by calling a \
final step directly without going through a gated check step; IDOR across resource types; \
privilege escalation by sending a lower-privilege token to an admin endpoint.

Return ONLY valid JSON in this exact format:
{{
  "app_summary": "2-3 sentence description of the application, its key roles, and security-relevant features",
  "attack_hypotheses": [
    {{
      "hypothesis": "Short label for this attack scenario",
      "description": "What to test, why it may be vulnerable, and which endpoints are involved",
      "target_pages": ["partial URL or pattern"],
      "owasp": "A01"
    }}
  ],
  "critical_areas": ["URL pattern or page type that deserves the most thorough testing"],
  "test_notes": "Specific techniques, IDs, credentials, header patterns, or sequences the scanner should use"
}}

Limit to the 8 most valuable attack hypotheses. Be specific and actionable."""


async def generate_site_test_plan(
    config: LLMConfig,
    base_url: str,
    pages: list[dict],
) -> dict:
    """Generate a site-level test plan from crawled page metadata.

    Returns a dict with keys: app_summary, attack_hypotheses, critical_areas, test_notes.
    Returns {} on failure.
    """
    if not pages:
        return {}
    pages_summary = "\n".join(
        f"  - {p['url']} | title={p.get('title') or '(no title)'!r} | "
        f"auth={p.get('req_auth')}, input={p.get('takes_input')}, "
        f"obj_ref={p.get('has_object_ref')}, biz_logic={p.get('has_business_logic')} | "
        f"{(p.get('context') or '')[:180]}"
        for p in pages[:60]
    )
    prompt = _SITE_PLAN_PROMPT.format(
        base_url=base_url,
        page_count=len(pages),
        pages_summary=pages_summary,
    )
    raw = await _call(config, prompt, None)
    try:
        plan = _extract_json(raw or "", expect=dict)
        if isinstance(plan, dict):
            return plan
    except Exception:
        pass
    return {}


# ── Follow-up probe planning ──────────────────────────────────────────────────

_FOLLOWUP_PROMPT = """\
You are a senior web application penetration tester reviewing mid-scan probe results.

You have just run an initial set of probes against the page below and received the results.
Your task is to reason through what you observe, identify any promising leads, and generate
targeted follow-up probes that would confirm, deepen, or chain from the potential issues.

Page URL: {url}
Page context: {context}

Site-level test plan context:
{site_context}

Initial probe results:
{initial_results}

Think through:
- Which results look anomalous or potentially vulnerable? (unexpected 200s on restricted pages, \
error messages that disclose stack traces or internals, reflected or stored payloads, \
differing responses for different input values, auth bypass indicators)
- For each interesting result, what follow-up probe would confirm or rule out the issue?
- Are there attack chains implied by multiple results together? In particular:
  • If a check/validate/verify endpoint responded saying something is required (e.g. TOTP, pin,
    2FA code, elevated privilege), probe the corresponding action endpoint DIRECTLY without
    providing that requirement, to test whether enforcement is server-side or only client-side.
  • If a response revealed a new endpoint URL, resource ID, token, or parameter — probe it.
  • If a check returned requires_X: true but the action endpoint is not yet probed — add a probe
    calling the action endpoint with the required field absent or empty.
- Did any response reveal new endpoints, IDs, tokens, or parameters worth testing?

Generate targeted follow-up probes. Prefer quality over quantity — a focused probe testing a
specific hypothesis is more valuable than re-running broad coverage.

Return ONLY valid JSON — an array of follow-up probe objects (max 20, return [] if no leads):
[
  {{
    "type": "http",
    "method": "GET",
    "url": "https://...",
    "params": {{}},
    "headers": {{}},
    "body": null,
    "as_user": null,
        "interesting_result": "Specific response status/body/header/behavior that made this worth following up",
        "hypothesis": "Specific vulnerability or enforcement behavior this probe is testing",
        "payload_purpose": "What the generated URL/body/header payload is intended to confirm or rule out, or null",
    "desc": "Follow-up: what this tests and why"
  }}
]

Return [] if no results look promising enough to warrant follow-up investigation.
Do not use vague wording like "looked interesting" without naming the exact signal and hypothesis."""


async def plan_followup_probes(
    config: LLMConfig,
    url: str,
    context: str,
    initial_results: list[dict],
    site_context: str = "",
) -> list[dict]:
    """Reason about initial probe results and generate targeted follow-up probes.

    This is the iterative-reasoning step: the LLM observes partial results, forms
    hypotheses about what looks interesting, and generates deeper targeted probes.
    Returns [] if nothing warrants follow-up or on failure.
    """
    if not initial_results:
        return []
    results_text = "\n\n".join(
        f"--- {r.get('desc', '?')} ---\n"
        f"URL: {r.get('url')}\n"
        f"Status: {r.get('status')}\n"
        f"Response body excerpt:\n{str(r.get('body', ''))[:600]}\n"
        f"Response evidence excerpt:\n{str(r.get('response_evidence', ''))[:600]}"
        for r in initial_results[:25]
    )
    prompt = _FOLLOWUP_PROMPT.format(
        url=url,
        context=context or "(no context)",
        site_context=site_context or "(no site-level context available)",
        initial_results=results_text,
    )
    raw = await _call(config, prompt, None)
    try:
        probes = _extract_json(raw or "", expect=list)
        if not isinstance(probes, list):
            return []
        return [p for p in probes if isinstance(p, dict) and p.get("type") in ("http", "form")]
    except Exception:
        return []


# ── Finding title normalisation ───────────────────────────────────────────────

_NORMALIZE_TITLES_PROMPT = """\
You are deduplicating security findings from a web application penetration test report.

EXISTING confirmed findings for this test run:
{existing_list}

NEW candidate findings just discovered (normalize these):
{new_list}

Rules:
- If a new finding is the same vulnerability class as an existing one (same OWASP category \
and root cause, possibly on a different URL), set its title to EXACTLY the existing title.
- If two new findings in this batch are the same class, give them the SAME title (pick the \
clearest one).
- If a new finding is genuinely different, keep its title as-is.
- Do NOT merge or drop findings — return one entry per new finding.

Return ONLY a JSON array, one object per new finding in the same order:
[{{"index": 0, "title": "..."}}, ...]
"""


async def normalize_finding_titles(
    config: "LLMConfig",
    existing_findings: list[dict],   # [{"title": ..., "owasp_category": ..., "severity": ...}]
    new_findings: list[dict],        # raw finding dicts from analyse_probes
) -> list[dict]:
    """Return new_findings with titles normalised against existing ones.

    On any failure the original new_findings list is returned unchanged.
    """
    if not new_findings or not existing_findings:
        return new_findings

    existing_list = "\n".join(
        f"  {i + 1}. [{f.get('owasp_category', '?')}] [{(f.get('severity') or '?').upper()}] {f['title']}"
        for i, f in enumerate(existing_findings[:60])
    )
    new_list = "\n".join(
        f"  {i}. [{f.get('owasp_category', '?')}] [{(f.get('severity') or '?').upper()}] {f.get('title', '?')}"
        + (f"\n     desc: {(f.get('description') or '')[:120]}" if f.get('description') else "")
        for i, f in enumerate(new_findings)
    )

    prompt = _NORMALIZE_TITLES_PROMPT.format(
        existing_list=existing_list,
        new_list=new_list,
    )
    try:
        raw = await _call(config, prompt, None)
        mappings = _extract_json(raw or "", expect=list)
        if not isinstance(mappings, list):
            return new_findings
        result = [dict(f) for f in new_findings]
        for entry in mappings:
            if not isinstance(entry, dict):
                continue
            idx = entry.get("index")
            title = (entry.get("title") or "").strip()
            if isinstance(idx, int) and 0 <= idx < len(result) and title:
                result[idx] = {**result[idx], "title": title}
        return result
    except Exception as exc:
        log.warning("normalize_finding_titles failed: %s", exc)
        return new_findings


def _format_findings_as_text(findings: list[dict]) -> str:
    """Format findings as structured text sorted by severity for LLM input.

    Works with both full _finding_summary dicts and compact _compact_finding_summary
    dicts, so it can be used in both the per-bucket and global deduplication prompts.
    """
    _sev = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    ordered = sorted(
        findings,
        key=lambda f: (_sev.get(str(f.get("severity") or "").lower(), 5), f.get("id") or 0),
    )
    parts = []
    for f in ordered:
        header = (
            f"### [{(f.get('severity') or 'unknown').upper()}] "
            f"Finding {f.get('id')} \u2014 {f.get('title') or '(untitled)'}"
        )
        lines = [
            header,
            f"OWASP: {f.get('owasp_category') or f.get('owasp') or 'unknown'}",
            f"URL: {f.get('affected_url') or f.get('url') or 'unknown'}",
        ]
        for key in ("description", "desc"):
            if v := str(f.get(key) or "").strip():
                lines.append(f"Description: {v}")
                break
        for key, label in (
            ("impact", "Impact"),
            ("likelihood", "Likelihood"),
            ("recommendation", "Recommendation"),
            ("evidence", "Evidence"),
        ):
            if v := str(f.get(key) or "").strip():
                lines.append(f"{label}: {v}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


_DEDUPLICATE_FINDINGS_PROMPT = """\
You are de-duplicating security findings from a web application penetration test.

Findings below are candidate duplicates because they share the same vulnerability
class and host target: {target}

Candidate findings (sorted by severity):

{findings_text}

Decide which findings are substantially the same issue in substance and target.

Rules:
- Group findings when a knowledgeable human security reviewer would collapse them into one
  report finding.
- Treat differing object IDs, account numbers, UUIDs, record references, or example values as
  duplicates when the vulnerability/root cause and target functionality are the same.
- Titles and writeups may differ; judge by vulnerability class, root cause, affected
  functionality, impact, and recommended fix.
- Do NOT group findings that affect different URL paths or parameters — XSS on
  /search and XSS on /login are separate vulnerable endpoints that must remain as
  separate findings even if they share the same vulnerability class.
- Do NOT group findings that are different vulnerability classes, different target
  functionality, or require meaningfully different remediation.
- Only include groups with at least two finding ids.

Return ONLY valid JSON in this exact format:
{{
  "duplicate_groups": [
    {{"ids": [1, 2], "reason": "short explanation"}}
  ]
}}
"""


async def deduplicate_finding_groups(
    config: "LLMConfig",
    *,
    target: str,
    findings: list[dict],
) -> list[list[int]]:
    """Return LLM-identified duplicate finding id groups for one target bucket."""
    if len(findings) < 2:
        return []

    truncated = []
    for finding in findings[:40]:
        truncated.append({
            "id": finding.get("id"),
            "owasp_category": finding.get("owasp_category"),
            "severity": finding.get("severity"),
            "affected_url": finding.get("affected_url"),
            "title": finding.get("title"),
            "description": str(finding.get("description") or "")[:1200],
            "impact": str(finding.get("impact") or "")[:600],
            "likelihood": str(finding.get("likelihood") or "")[:400],
            "recommendation": str(finding.get("recommendation") or "")[:600],
            "evidence": str(finding.get("evidence") or "")[:800],
        })

    prompt = _DEDUPLICATE_FINDINGS_PROMPT.format(
        target=target or "(unknown target)",
        findings_text=_format_findings_as_text(truncated),
    )
    try:
        raw = await _call(config, prompt, None)
        data = _extract_json(raw or "", expect=dict)
        groups = data.get("duplicate_groups") if isinstance(data, dict) else None
        if not isinstance(groups, list):
            return []
        allowed_ids = {
            int(finding["id"])
            for finding in findings
            if isinstance(finding.get("id"), int)
        }
        result: list[list[int]] = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("ids"), list):
                continue
            ids = []
            for raw_id in group["ids"]:
                if isinstance(raw_id, int) and raw_id in allowed_ids and raw_id not in ids:
                    ids.append(raw_id)
            if len(ids) >= 2:
                result.append(ids)
        return result
    except Exception as exc:
        log.warning("deduplicate_finding_groups failed: %s", exc)
        return []


_FINGERPRINT_PROMPT = """\
You are classifying security findings from a web application penetration test.

For each finding below, assign a short canonical "vulnerability fingerprint" that
captures:
  1. Vulnerability CLASS  (e.g. xss, sqli, idor, csrf, ssrf, broken-auth, ssti, xxe)
  2. Root-cause MECHANISM (e.g. reflection, stored, blind, missing-check, misconfig)
  3. Affected FUNCTIONALITY (e.g. login, search, user-profile, file-upload, admin-panel)

Findings that represent the SAME underlying vulnerability — even when found on
different URLs or paths — MUST receive IDENTICAL fingerprints.

For example, reflected XSS found on /search and on /login should both get
"xss:reflection:user-input" if the root cause is the same unescaped reflection.

Findings (sorted by severity):

{findings_text}

Return ONLY valid JSON:
{{
  "fingerprints": [
    {{"id": 1, "fingerprint": "xss:reflection:user-input"}},
    {{"id": 2, "fingerprint": "xss:reflection:user-input"}},
    {{"id": 3, "fingerprint": "sqli:error-based:login-form"}}
  ]
}}
"""


async def global_deduplicate_findings(
    config: "LLMConfig",
    *,
    findings: list[dict],
) -> list[list[int]]:
    """Two-phase global cross-target consolidation pass.

    Phase 1 — the LLM assigns a canonical vulnerability fingerprint to every finding.
    Phase 2 — findings that share an identical fingerprint are grouped deterministically
               without a second LLM call.
    """
    if len(findings) < 2:
        return []

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sorted_findings = sorted(
        findings,
        key=lambda f: (
            sev_order.get(str(f.get("severity") or "").lower(), 5),
            f.get("id") or 0,
        ),
    )
    batch = sorted_findings[:120]

    prompt = _FINGERPRINT_PROMPT.format(
        findings_text=_format_findings_as_text(batch),
    )
    try:
        raw = await _call(config, prompt, None)
        data = _extract_json(raw or "", expect=dict)
        fp_list = data.get("fingerprints") if isinstance(data, dict) else None
        if not isinstance(fp_list, list):
            return []
        allowed_ids = {
            int(f["id"])
            for f in findings
            if isinstance(f.get("id"), int)
        }
        # Phase 2: group by fingerprint.
        # Cross-URL groups are safe here — the merge step in deduplicate_findings
        # will consolidate different-URL instances into merged_instances rather than
        # deleting them, so all instance data is preserved.
        by_fp: dict[str, list[int]] = {}
        for entry in fp_list:
            if not isinstance(entry, dict):
                continue
            raw_id = entry.get("id")
            fp = str(entry.get("fingerprint") or "").strip().lower()
            if not fp or not isinstance(raw_id, int) or raw_id not in allowed_ids:
                continue
            by_fp.setdefault(fp, []).append(raw_id)
        return [ids for ids in by_fp.values() if len(ids) >= 2]
    except Exception as exc:
        log.warning("global_deduplicate_findings failed: %s", exc)
        return []


# ── LLM-directed (thinking) scan ─────────────────────────────────────────────

_THINKING_PENTEST_PLAYBOOK = """\
Recommended assessment strategy, distilled from effective manual pentest workflow:

1. Passive recon and fingerprinting
     - Start with the base URL, visible login/app/admin paths, robots.txt, sitemap.xml,
         and response headers.
     - Note missing or weak security headers, server/framework hints, public admin areas,
         exposed account data, comments, forms, and route/link structure.

2. Raw asset and JavaScript mining
     - Fetch raw HTML for important pages and enumerate every script src and link href.
     - Fetch JavaScript bundles and look for API base paths, endpoint lists, token storage
         keys, hardcoded routes, feature flags, role-specific APIs, preflight/check endpoints,
         and client-side-only enforcement.
     - After fetching a JS file, search its content using history_search with short code
         patterns like "fetch(", "axios.post(", "/api/", "baseUrl" — NOT English descriptions.
     - For single-page applications using hash routing (#/route), API endpoints used by a
         feature are ONLY discoverable by: (a) using the browser action to navigate to the
         SPA route, interact with its form (fill + submit), and capture the real API call in
         traffic logs, or (b) finding the path in a fetched JS source with history_search
         using code patterns. If /api/transfers or similar returns 404, do NOT keep guessing
         variations — use a browser action to navigate to #/transfers and submit the form.
     - Build and maintain an endpoint inventory from the JS and crawl context before
         spending too many steps on generic payloads.

3. API map and authentication boundary checks
     - Always check common unauthenticated operational endpoints early when in scope:
         /api/health, /health, /status, /api/status, /api/config, /api/debug, and
         /.well-known/security.txt. Treat jwt_secret, app keys, DB settings, phpinfo,
         environment, server versions, or stack traces as high-priority leads.
     - Test CORS on representative API endpoints by sending a harmless Origin header
         such as https://evil.example and inspect Access-Control-Allow-Origin and
         Access-Control-Allow-Credentials.
     - Probe discovered API endpoints unauthenticated first, then with available user tokens.
     - Compare 401/403/404/200 behavior on user, admin, account, profile, transaction,
         address-book, settings, and system endpoints.
     - Try lower-privilege tokens against admin endpoints and admin tokens against user
         endpoints if both token types are available.
     - If a public admin panel or admin login is discovered, try a very small set of obvious
         default credentials derived from the app context, such as admin/admin, admin/password,
         admin/admin123. Use credential_check for these bounded dictionaries. Do not brute-force.
     - For demo/seeded customer apps, test a tiny bounded set of obvious seeded passwords
         such as password and Password123! against discovered example users. Use at most a
         handful of users and passwords.

4. Account bootstrap and session/token analysis
     - If registration is available, create or use a disposable test account to obtain a
         legitimate session and inspect registration/login/profile responses for sensitive
         fields such as password_hash, totp_secret, roles, IDs, balances, account numbers,
         or JWTs.
     - Decode JWT payloads client-side when visible, then test only low-impact JWT issues
         such as alg=none rejection or issuer/role boundary confusion when appropriate.
     - If a response exposes a JWT signing secret, use the jwt action to create a
         controlled HS256 token for a small number of candidate customer IDs, then verify
         access with read-only endpoints such as /api/profile and /api/accounts.

5. Object ownership and IDOR testing
     - Enumerate IDs from list endpoints, detail endpoints, admin views, account numbers,
         transaction IDs, address-book IDs, and response bodies.
     - Test both list endpoints and individual detail endpoints because one may be scoped
         correctly while the other is vulnerable.
     - For every object lookup, ask: does the server verify this object belongs to the
         current user, or is it only fetching by numeric ID?

6. Business-logic gate bypass
     - Identify two-step flows with /check, /verify, /validate, /preflight, /setup, or
         client-side UI gating before a sensitive action.
     - First call the check endpoint to learn what it claims is required. Then call the
         actual action endpoint directly without the required field (for example no totp_code,
         pin, approval token, or confirmation) and verify whether the server enforces it.
     - For money/account flows, use disposable accounts and low-impact amounts where possible.
     - For banking apps, explicitly check loan/account creation rules, credit limits,
         redraw/transfer limits, sufficient-funds behavior, and whether action endpoints
         verify that source accounts belong to the authenticated user.

7. Input validation, stored XSS, and SQL injection
     - Prefer inputs discovered from actual forms/API bodies: search/filter/sort, name/title/
         description/comment/message, email/username, IDs, amount/quantity.
     - For SQLi, compare a baseline nonmatching search to quote-breaking, boolean, ORDER BY,
         UNION, and low-delay timing probes. Treat SQL error disclosure as valuable evidence.
     - For XSS, test both reflected and stored paths. If the server accepts raw HTML/JS in a
         create/update response, follow up by viewing the listing/detail/admin page where the
         value is rendered.

8. Error disclosure, rate limiting, and configuration checks
     - Send malformed-but-valid-shape requests to endpoints with typed parameters to look for
         stack traces, SQL errors, absolute file paths, class names, and debug traces.
     - Check login error differences for user enumeration, and use only a small bounded set
         of failed login attempts to detect missing throttling/lockout.
     - Re-check CSP, HSTS, X-Frame-Options, content sniffing, and referrer-policy headers on
         representative HTML and API responses.

Work like the transcript: recon → endpoint extraction → auth/session bootstrap → boundary tests →
business-logic bypass → IDOR/injection/error disclosure → concise confirmation. When a response
reveals a stronger lead than the current plan, follow that lead immediately.
"""

# ── WSTG technique quick-reference (distilled from OWASP WSTG skill prompts) ──
# These blocks add specific payloads, indicators, and decision criteria not
# already covered by the high-level playbook above.
# ── WSTG technique blocks — keyed by category ────────────────────────────────
# Each value is injected into the initial user message only when the selector
# determines it is relevant to the discovered attack surface.

WSTG_SKILLS: dict[str, str] = {
    "sqli": r"""─── SQL INJECTION (WSTG-INPV-05) ───────────────────────────────────────────────
Error-based probes: submit `'`, `''`, `1'`, `\`, `1 OR 1=1--`, `' OR ''='`
DB error signatures:
  MySQL:      "You have an error in your SQL syntax" / "Warning.*mysql"
  PostgreSQL: "pg_query()" / "unterminated quoted string" / "PostgreSQL.*ERROR"
  MSSQL:      "Microsoft OLE DB Provider" / "Unclosed quotation mark"
  Oracle:     "ORA-\d{5}" / "quoted string not properly terminated"
  SQLite:     "SQLite3::query" / "SQLITE_ERROR"
  Generic:    "SQLSTATE[" / "syntax error at or near"
Boolean-blind: send baseline → `1 AND 1=1--` (true) → `1 AND 1=2--` (false);
  if true matches baseline and false differs significantly → injectable.
Time-blind: MySQL `' AND SLEEP(5)--` | MSSQL `'; WAITFOR DELAY '0:0:5'--` |
  PostgreSQL `'; SELECT pg_sleep(5)--` — confirm with baseline timing.
UNION: find column count with `' ORDER BY N--`; find reflected column with
  `' UNION SELECT NULL,NULL,'x',NULL--`; extract `' UNION SELECT NULL,@@version--`.
Constraint: never DROP/INSERT/UPDATE/DELETE; limit to version/DB name for PoC.""",

    "xss": r"""─── XSS (WSTG-INPV-01/02) ──────────────────────────────────────────────────────
Step 0 — check for pre-identified sinks: call context_tool with tool="target_inventory"
  and args={"kind": "xss_sink"}. Each item has key=field_name, value=js_file_url, and
  evidence=code_context showing the unsanitized innerHTML assignment. For each sink:
    a. Find the write endpoint: call target_inventory with kind="input" and filter by
       the same field name (key) to get the URL and method that accepts that field.
    b. POST a payload to that write endpoint as the attacker session.
    c. Log in as a different user (victim session) and navigate to the page that loads
       the JS file identified in the sink item — verify execution via browser DOM check.
  This step finds cross-user stored XSS that generic fuzzing misses.
Step 1 — inject a unique canary string; check if it appears in the response.
Step 2 — identify rendering context, then use a context-matched payload:
  HTML body:      <script>alert(1)</script>  /  <img src=x onerror=alert(1)>  /  <svg/onload=alert(1)>
  HTML attribute: " onfocus="alert(1)" autofocus="  /  ' onmouseover='alert(1)
  JS string:      ';alert(1)//  /  </script><script>alert(1)//
  URL context:    javascript:alert(1)
Filter bypass: case variation <ScRiPt>, HTML entities &#x3C;script&#x3E;,
  tag alternatives <details open ontoggle=alert(1)>, double-encode %253C.
Stored XSS: submit payload → navigate to every related rendering page → confirm.""",

    "idor": r"""─── IDOR / AUTHORIZATION (WSTG-ATHZ-04) ────────────────────────────────────────
Object references: URL path `/api/users/123`, query `?id=123`, POST body `{"user_id":123}`.
Horizontal escalation: access own resource → swap ID to adjacent (+1/-1) or another user's.
Vertical escalation: use low-privilege session on admin-only endpoints.
Manipulation: sequential IDs, `?id=*`, `?id[]=100&id[]=101`, base64/hex IDs.
Response comparison: same data = IDOR; same structure different data = partial; error = check msg.""",

    "auth_bypass": r"""─── AUTHENTICATION BYPASS (WSTG-ATHN-04) ────────────────────────────────────────
Forced browsing: send protected endpoint request without any auth headers.
Bypass headers to add on protected endpoints:
  X-Original-URL: /admin  |  X-Rewrite-URL: /admin  |  X-Forwarded-For: 127.0.0.1
  X-Custom-IP-Authorization: 127.0.0.1  |  X-Real-IP: 127.0.0.1
Path variation: /Admin, /ADMIN, /admin/, /admin/., /admin%2fpanel, /admin;foo=bar/panel,
  /%61dmin (URL-encoded 'a'), /admin..
Method override: try HEAD, OPTIONS; add X-HTTP-Method-Override: GET header.
Parameter tampering: flip hidden `isAdmin=false` → true, `role=user` → admin in cookie/param.""",

    "ssrf": r"""─── SSRF (WSTG-INPV-19) ──────────────────────────────────────────────────────────
Candidate parameter names: url, uri, link, href, src, dest, redirect, target, path,
  file, page, next, callback, feed, fetch, load, resource, proxy, imageurl, webhook.
Internal targets:
  http://127.0.0.1/  |  http://localhost/  |  http://[::1]/
  http://169.254.169.254/latest/meta-data/              (AWS IMDSv1)
  http://metadata.google.internal/computeMetadata/v1/   (GCP — add Metadata-Flavor: Google header)
  http://169.254.169.254/metadata/instance?api-version=2021-02-01 (Azure — add Metadata: true)
Evidence: "ami-id", "instance-id", "computeMetadata", "vmId", "Welcome to nginx".
Filter bypass: hex IP `http://0x7f000001/`, octal `http://0177.0.0.1/`, decimal `http://2130706433/`,
  short form `http://127.1/`, `http://evil.com@127.0.0.1/`, redirect chain via external 302.
Constraint: if cloud credentials are found, report CRITICAL but do NOT use them.""",

    "csrf": r"""─── CSRF (WSTG-SESS-05) ──────────────────────────────────────────────────────────
Focus on state-changing endpoints (POST/PUT/DELETE): profile update, password/email change,
  transactions, admin actions.
Token validation tests (do each in turn):
  1. Remove token entirely — if request succeeds, token not enforced.
  2. Set token to empty string.  3. Replace with random same-length string.
  4. Reuse token from a previous session.
SameSite bypass: Lax permits top-level GET navigations; test if action works via GET/method-override.
Referer bypass: omit header entirely; `Referer: https://evil.target.com`.""",

    "cmdi": r"""─── COMMAND INJECTION (WSTG-INPV-12) ────────────────────────────────────────────
Separators (prefix with valid value): `; echo CANARY` | `| echo CANARY` | `&& echo CANARY`
  `` `echo CANARY` `` | `$(echo CANARY)` | `\necho CANARY`
Time-based blind: Unix `; sleep 5` / `$(sleep 5)` | Windows `& timeout /T 5 /NOBREAK`
  — measure baseline, inject, confirm with a different delay (3s) to rule out jitter.
Filter bypass: `{echo,CANARY}`, `echo$IFS CANARY`, base64 decode `$(echo Y2F0|base64 -d)`.
Constraint: limit to echo/sleep/id/whoami — no reverse shells, no rm/del.""",

    "cors": r"""─── CORS (WSTG-CLNT-07) ─────────────────────────────────────────────────────────
Test on every API endpoint that returns user data. Add `Origin: https://evil.com` to the request.
Vulnerable: response contains `Access-Control-Allow-Origin: https://evil.com`.
Default severity is low, including when `Access-Control-Allow-Credentials: true` is present.
Escalate only with browser-enforceable proof that sensitive authenticated data is readable
cross-origin, or when the permissive policy directly enables a confirmed account-impacting flow.
Also test: `Origin: null` (sandbox), `Origin: https://evil.target.com` (subdomain trust),
  `Origin: http://target.com` (scheme downgrade on HTTPS site).""",

    "headers": r"""─── SECURITY HEADERS (WSTG-CONF-07) ──────────────────────────────────────────────
Check main page, login page, API endpoints, and error pages. Expected values:
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Content-Security-Policy: restrictive — no unsafe-inline, no unsafe-eval, no *
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY or SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
Should be absent: Server (with version), X-Powered-By, X-AspNet-Version.
CSP weak patterns: unsafe-inline in script-src, *, data: in script-src, CDN hosting user content.""",

    "sessions": r"""─── SESSION MANAGEMENT (WSTG-SESS-01/02/03/07) ────────────────────────────────────
Cookie attributes — every session cookie must have: Secure (HTTPS), HttpOnly, SameSite=Strict|Lax.
Session fixation: capture token before login → log in → compare token. If unchanged: fixation vuln.
Logout invalidation: after clicking logout, re-send the old session cookie — if still valid, server
  does not invalidate tokens.
Token entropy: collect several tokens and check for sequential or timestamp-correlated patterns.""",

    "workflow": r"""─── WORKFLOW BYPASS (WSTG-BUSL-06) ────────────────────────────────────────────────
Multi-step flows: registration, checkout, password-reset, approval, onboarding wizards.
Step skipping: jump directly to the final confirmation/submit step without completing earlier steps.
Parameter tampering: modify hidden `step=3`, `status=approved`, `verified=true` fields.
Price/quantity manipulation: change `price=0.01`, `qty=-1`, modify discount values in POST body.
Race conditions: send the same state-changing request twice simultaneously.""",
}

# SSRF-indicative parameter names used by the selector.
_SSRF_PARAM_NAMES: frozenset[str] = frozenset({
    "url", "uri", "link", "href", "src", "dest", "destination", "redirect",
    "redirecturl", "target", "path", "file", "page", "next", "return",
    "returnurl", "callback", "feed", "fetch", "load", "resource", "proxy",
    "imageurl", "image_url", "webhook", "endpoint", "host", "site",
})

# URL path fragments that imply auth-related pages.
_AUTH_PATH_FRAGMENTS: frozenset[str] = frozenset({
    "/login", "/signin", "/sign-in", "/auth", "/authenticate",
    "/register", "/signup", "/sign-up", "/logout", "/password",
    "/account", "/profile", "/admin",
})

_SKILL_ORDER = (
    "sqli", "xss", "cmdi", "ssrf", "idor", "auth_bypass",
    "csrf", "sessions", "cors", "headers", "workflow",
)


def select_wstg_skills(
    pages: list[dict],
    intel_items: list[dict],
    *,
    requires_auth: bool = False,
    base_url: str = "",
) -> set[str]:
    """Evaluate crawl intelligence and return the set of WSTG skill keys to inject.

    Parameters
    ----------
    pages:
        List of page dicts from pages_snapshot (keys: url, req_auth,
        takes_input, has_object_ref, has_business_logic).
    intel_items:
        List of TargetIntelItem dicts (keys: kind, key, value, url).
    requires_auth:
        Whether the site requires authentication.
    base_url:
        Target base URL (used for path-pattern matching when page list is sparse).
    """
    selected: set[str] = {"headers"}  # security headers: always relevant

    page_urls_lower = [str(p.get("url") or "").lower() for p in pages]
    intel_kinds = {str(i.get("kind") or "") for i in intel_items}
    intel_keys_lower = {str(i.get("key") or "").lower() for i in intel_items}
    intel_values_lower = {str(i.get("value") or "").lower() for i in intel_items}
    intel_urls_lower = {str(i.get("url") or "").lower() for i in intel_items}

    # ── Injection surface ──────────────────────────────────────────────────────
    has_inputs = (
        any(p.get("takes_input") for p in pages)
        or "form" in intel_kinds
        or "input" in intel_kinds
    )
    if has_inputs:
        selected.update({"sqli", "xss", "cmdi"})

    # ── Authentication surface ─────────────────────────────────────────────────
    has_auth_pages = (
        requires_auth
        or any(p.get("req_auth") for p in pages)
        or any(
            frag in url
            for frag in _AUTH_PATH_FRAGMENTS
            for url in page_urls_lower
        )
        or "token_hint" in intel_kinds
    )
    if has_auth_pages:
        selected.update({"auth_bypass", "sessions"})
        if has_inputs:
            selected.add("csrf")

    # ── Object references / IDOR ───────────────────────────────────────────────
    has_object_refs = (
        any(p.get("has_object_ref") for p in pages)
        or "id" in intel_kinds
        or any("/api/" in url for url in page_urls_lower)
        or any(
            part.isdigit()
            for url in page_urls_lower
            for part in url.split("/")
            if part
        )
    )
    if has_object_refs:
        selected.add("idor")

    # ── SSRF — URL-type input parameters ──────────────────────────────────────
    has_ssrf_params = (
        any(key in _SSRF_PARAM_NAMES for key in intel_keys_lower)
        or any(val.startswith("http") for val in intel_values_lower)
        or any(
            any(name in url for name in ("webhook", "callback", "redirect", "proxy"))
            for url in page_urls_lower + list(intel_urls_lower)
        )
    )
    if has_ssrf_params:
        selected.add("ssrf")

    # ── API endpoints → CORS ───────────────────────────────────────────────────
    has_api = (
        any("/api/" in url or "/graphql" in url for url in page_urls_lower)
        or "endpoint" in intel_kinds
        or any("/api/" in url for url in intel_urls_lower)
    )
    if has_api:
        selected.add("cors")

    # ── Business logic / multi-step flows ─────────────────────────────────────
    has_business_logic = (
        any(p.get("has_business_logic") for p in pages)
        or any(
            frag in url
            for frag in ("/checkout", "/payment", "/order", "/cart",
                         "/transfer", "/confirm", "/submit", "/approve")
            for url in page_urls_lower
        )
    )
    if has_business_logic:
        selected.add("workflow")

    return selected


def build_wstg_skill_context(selected: set[str]) -> str:
    """Assemble selected WSTG skill blocks into a single context string."""
    blocks = [
        WSTG_SKILLS[key]
        for key in _SKILL_ORDER
        if key in selected and key in WSTG_SKILLS
    ]
    if not blocks:
        return ""
    return (
        "WSTG technique reference — selected for this target's attack surface:\n\n"
        + "\n\n".join(blocks)
    )


# ── Continuous agentic session (Anthropic native tool use) ────────────────────

TOOL_RESULT_CHAR_LIMIT = 8_000
# All providers that support native tool use and therefore run the continuous
# agentic session.  Non-Anthropic providers use the OpenAI function-calling
# wire format or the Bedrock Converse toolConfig format.
AGENTIC_LOOP_PROVIDERS = frozenset({
    "anthropic",
    "azure_foundry_anthropic",
    "bedrock",
    "openai",
    "openai_compatible",
    "openrouter",
    "azure_openai",
    "azure_foundry",
    "azure_foundry_openai",
    "google",
})

_THINKING_AGENT_SYSTEM = (
    "You are an expert web application penetration tester conducting a hands-on "
    "security assessment.\n"
    "Use the provided tools to investigate the target. Work iteratively — after each "
    "tool result, reason about what you observed and decide the single most valuable "
    "next action.\n\n"
    "Your conversation contains every prior tool result verbatim. "
    "You do NOT need reconstructed summaries — read your actual prior tool_result "
    "messages to find cookies, tokens, response bodies, and IDs you captured earlier. "
    "When you reference a prior response, quote the exact text from that tool_result.\n\n"
    + _THINKING_PENTEST_PLAYBOOK
    + "\n\nTool rules:\n"
    "- http_request: direct HTTP probes. Use for APIs, assets, headers, and endpoint testing.\n"
    "- browser: real browser. Use only when JavaScript execution, hash routing, or DOM "
    "interaction is genuinely required.\n"
    "- context_tool: look up crawl data, history, findings, or traffic without hitting "
    "the target. After 3 consecutive calls, either execute a probe/write a finding or "
    "include context_budget_reason with a concrete summary and why one more targeted "
    "scan round will change the next action.\n"
    "- write_finding: persist a confirmed finding with concrete evidence from prior results. "
    "No duplicates.\n"
    "- agent_dispatch: delegate a confirmed high-confidence lead to a Specialist Agent that "
    "runs concurrently so you can continue covering other attack surface. Call this as soon "
    "as you have concrete evidence of a testable vector — e.g. a confirmed stored-XSS sink "
    "with a verified injection point, an IDOR primitive where you can enumerate a foreign "
    "object ID, an auth bypass with a reproducible proof, or a SQLi indicator with a "
    "distinctive error or timing response. Set priority 7–10 based on severity. "
    "Attack classes: idor, auth_bypass, sqli, xss, business_logic, ssrf, path_traversal, "
    "cors, crypto, config. Dispatch immediately — do NOT keep probing the same lead "
    "yourself after dispatching.\n"
    "- done: end the assessment when all areas are covered and it is unlikely further vulnerabilities will be found.\n"
    "- Confirmed findings are CLOSED — do not re-probe them.\n"
    "- If a URL returns an empty body or errors 3+ times, stop probing it and switch "
    "attack surface.\n"
    "- If a browser fill/click fails, immediately fall back to http_request with POST body.\n"
)

THINKING_AGENT_TOOLS: list[dict] = [
    {
        "name": "http_request",
        "description": (
            "Make one HTTP request to the target. Use for APIs, raw assets, "
            "header checks, and direct endpoint testing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string"},
                "url": {"type": "string"},
                "headers": {"type": "object"},
                "body": {},
                "use_session": {"type": ["string", "null"]},
                "observation": {"type": "string"},
                "hypothesis": {"type": "string"},
                "payload_purpose": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["method", "url"],
        },
    },
    {
        "name": "browser",
        "description": (
            "Interact with the target using a real browser. Use when JavaScript "
            "execution, hash routes, form interaction, or DOM rendering is required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "use_session": {"type": ["string", "null"]},
                "steps": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Ordered ops: {op: goto|fill|type|click|press|wait|snapshot, ...}. "
                        "fill: selector+value. click: selector. press: selector+key. "
                        "wait: state or ms."
                    ),
                },
                "observation": {"type": "string"},
                "hypothesis": {"type": "string"},
                "payload_purpose": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["steps"],
        },
    },
    {
        "name": "context_tool",
        "description": (
            "Retrieve scanner context without hitting the target. "
            "Available: site_map, page_detail, history_search, finding_list, "
            "target_inventory, traffic_search, endpoint_detail, compare_responses, "
            "mutate_request, auth_matrix, extract_entities. "
            "After 3 consecutive calls, either act or include context_budget_reason "
            "explaining why another targeted context scan round is needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "args": {"type": "object"},
                "context_budget_reason": {"type": "string"},
                "observation": {"type": "string"},
                "hypothesis": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["tool"],
        },
    },
    {
        "name": "write_finding",
        "description": (
            "Record a confirmed security finding. Only call with concrete evidence "
            "from prior tool results. Do not re-write confirmed findings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "owasp_category": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "impact": {"type": "string"},
                "likelihood": {"type": "string"},
                "recommendation": {"type": "string"},
                "cvss_score": {"type": "number"},
                "cvss_vector": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low", "info"],
                },
                "affected_url": {"type": "string"},
                "evidence": {"type": "string"},
                "request_evidence": {"type": "string"},
                "response_evidence": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["title", "severity", "affected_url", "evidence"],
        },
    },
    {
        "name": "forge_jwt",
        "description": (
            "Forge a JWT with a modified payload after discovering an exposed "
            "HS256 signing secret."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "secret": {"type": "string"},
                "claims": {"type": "object"},
                "header": {"type": "object"},
                "store_as": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["secret", "claims"],
        },
    },
    {
        "name": "decode_jwt",
        "description": (
            "Decode a JWT to inspect its header and payload claims. "
            "Optionally verify the HS256 signature with a known secret."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "The raw JWT string to decode."},
                "secret": {"type": "string", "description": "HMAC secret to verify the HS256 signature (optional)."},
                "note": {"type": "string"},
            },
            "required": ["token"],
        },
    },
    {
        "name": "credential_check",
        "description": "Test a small explicit list of credentials (max 20) against a login endpoint.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string"},
                "username_field": {"type": "string"},
                "password_field": {"type": "string"},
                "candidates": {"type": "array", "items": {"type": "object"}},
                "headers": {"type": "object"},
                "success_statuses": {"type": "array", "items": {"type": "integer"}},
                "note": {"type": "string"},
            },
            "required": ["url", "candidates"],
        },
    },
    {
        "name": "register_account",
        "description": "Create one disposable account through a discovered registration endpoint.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string"},
                "body_format": {"type": "string", "enum": ["json", "form"]},
                "username_field": {"type": "string"},
                "email_field": {"type": "string"},
                "password_field": {"type": "string"},
                "include_username": {"type": "boolean"},
                "include_email": {"type": "boolean"},
                "extra_fields": {"type": "object"},
                "headers": {"type": "object"},
                "success_statuses": {"type": "array", "items": {"type": "integer"}},
                "store_as": {"type": "string"},
                "use_session": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "done",
        "description": (
            "End the assessment only after all discovered endpoints, authentication flows, "
            "IDOR surfaces, business logic paths, and injection points have been exhaustively "
            "tested. Do not call done simply because specialists have been dispatched — "
            "continue covering remaining attack surface directly until it is genuinely "
            "unlikely that further vulnerabilities will be found."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
    {
        "name": "agent_dispatch",
        "description": (
            "Dispatch a Specialist Agent to deep-dive on a strong, specific lead. "
            "Use when you have identified a high-confidence attack vector that warrants "
            "focused follow-up investigation beyond a single HTTP probe — for example, "
            "a confirmed IDOR primitive, an exposed signing secret, or a business-logic "
            "path with suspicious parameter handling. The specialist runs concurrently "
            "and reports back via context tools. Do not dispatch on speculative leads; "
            "only dispatch after gathering concrete evidence of a testable vector."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "attack_class": {
                    "type": "string",
                    "description": (
                        "One of: idor, auth_bypass, sqli, xss, business_logic, "
                        "ssrf, path_traversal, cors, crypto, config"
                    ),
                },
                "target_url": {
                    "type": "string",
                    "description": "The specific URL the specialist should focus on.",
                },
                "rationale": {
                    "type": "string",
                    "description": (
                        "Concrete evidence from prior tool results that justifies "
                        "dispatching this specialist."
                    ),
                },
                "priority": {
                    "type": "integer",
                    "description": "Estimated priority 1-10 for this lead.",
                },
                "note": {"type": "string"},
            },
            "required": ["attack_class", "target_url", "rationale"],
        },
    },
]

# Subset of tools available to specialist agents — no agent_dispatch (prevent
# recursive dispatch), no JWT/credential/register tools (specialist is narrowly
# focused on a specific lead).
SPECIALIST_AGENT_TOOLS: list[dict] = [
    t for t in THINKING_AGENT_TOOLS
    if t["name"] in {"http_request", "browser", "context_tool", "write_finding", "done"}
]


async def _call_with_tools(
    config: "LLMConfig",
    system_message: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> "tuple[list[dict], str, Any]":
    """Call an LLM with tool definitions.

    The *messages* list is always in Anthropic format (the canonical internal
    representation used by thinking_agentic_loop).  Each provider branch
    translates that list into the wire format it needs, calls the API, and
    returns results normalised back to Anthropic-style content blocks so the
    loop never has to know which provider it is talking to.

    Returns (content_blocks, stop_reason, raw_content_for_history) where
    content_blocks is a normalised list of dicts with {type, id, name, input, text}
    and raw_content_for_history is appended as the assistant message (always in
    Anthropic-format so the growing messages list stays consistent).
    """
    _active_tools = tools if tools is not None else THINKING_AGENT_TOOLS
    # ── Anthropic (direct) ────────────────────────────────────────────────────
    if config.provider == "anthropic":
        import anthropic as _ant

        client = _ant.AsyncAnthropic(api_key=config.api_key, **_llm_client_kwargs())
        resp = await client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system=[{"type": "text", "text": system_message, "cache_control": {"type": "ephemeral"}}],
            tools=_active_tools,
            messages=messages,
        )
        blocks = [
            {
                "type": b.type,
                "id": getattr(b, "id", None),
                "name": getattr(b, "name", None),
                "input": getattr(b, "input", None),
                "text": getattr(b, "text", None),
            }
            for b in (resp.content or [])
        ]
        _record_usage(config.model,
                      getattr(resp.usage, "input_tokens", 0),
                      getattr(resp.usage, "output_tokens", 0),
                      cache_read_tokens=getattr(resp.usage, "cache_read_input_tokens", 0),
                      cache_write_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0))
        return blocks, resp.stop_reason or "end_turn", resp.content

    # ── Azure AI Foundry (Anthropic endpoint) ─────────────────────────────────
    if config.provider == "azure_foundry_anthropic":
        payload = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "system": [{"type": "text", "text": system_message, "cache_control": {"type": "ephemeral"}}],
            "tools": _active_tools,
            "messages": messages,
        }
        hdrs = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": config.api_key or "",
            "anthropic-version": "2023-06-01",
        }
        async with _make_llm_http_client(timeout=120) as client:
            resp = await client.post(
                _azure_foundry_anthropic_messages_url(config.base_url or ""),
                headers=hdrs,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        content = data.get("content") or []
        blocks = [
            {
                "type": b.get("type"),
                "id": b.get("id"),
                "name": b.get("name"),
                "input": b.get("input"),
                "text": b.get("text"),
            }
            for b in content
        ]
        _cwt_u = data.get("usage", {})
        _record_usage(config.model, _cwt_u.get("input_tokens", 0), _cwt_u.get("output_tokens", 0),
                      cache_read_tokens=_cwt_u.get("cache_read_input_tokens", 0),
                      cache_write_tokens=_cwt_u.get("cache_creation_input_tokens", 0))
        return blocks, data.get("stop_reason") or "end_turn", content

    # ── AWS Bedrock (Converse API with toolConfig) ────────────────────────────
    if config.provider == "bedrock":
        import asyncio as _asyncio

        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "inputSchema": {"json": t.get("input_schema", {"type": "object"})},
                    }
                }
                for t in _active_tools
            ]
        }

        def _ant_msg_to_converse(msg: dict) -> dict:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, str):
                return {"role": role, "content": [{"text": content}]}
            cvt: list[dict] = []
            for blk in content:
                btype = blk.get("type")
                if btype == "text":
                    cvt.append({"text": blk.get("text") or ""})
                elif btype == "tool_use":
                    cvt.append({
                        "toolUse": {
                            "toolUseId": blk.get("id") or "",
                            "name": blk.get("name") or "",
                            "input": blk.get("input") or {},
                        }
                    })
                elif btype == "tool_result":
                    result_content = blk.get("content") or ""
                    cvt.append({
                        "toolResult": {
                            "toolUseId": blk.get("tool_use_id") or "",
                            "content": [{"text": result_content}]
                            if isinstance(result_content, str)
                            else result_content,
                        }
                    })
            return {"role": role, "content": cvt}

        converse_messages = [_ant_msg_to_converse(m) for m in messages]
        system_list = [
            {"text": system_message},
            {"cachePoint": {"type": "default"}},
        ]

        # Cache the static initial user message (crawl context + WSTG blocks).
        # It is messages[0] and never changes during the scan, so it qualifies
        # as a stable prefix.  The cachePoint is re-sent on every turn, which
        # is correct — Bedrock resets the TTL on each cache hit.
        if converse_messages and converse_messages[0].get("role") == "user":
            first_content = list(converse_messages[0].get("content") or [])
            if not any("cachePoint" in blk for blk in first_content):
                first_content = first_content + [{"cachePoint": {"type": "default"}}]
            converse_messages = [
                {**converse_messages[0], "content": first_content},
                *converse_messages[1:],
            ]

        if config.api_key:
            # Bearer-token path (SAML / federated credentials stored as api_key).
            # Uses the same HTTP endpoint as _bedrock() so SAML token users work.
            model_id = quote(config.model, safe="")
            url = f"{(config.base_url or '').rstrip('/')}/model/{model_id}/converse"
            payload: dict = {
                "messages": converse_messages,
                "system": system_list,
                "toolConfig": tool_config,
                "inferenceConfig": {
                    "maxTokens": config.max_tokens,
                    "temperature": config.temperature,
                },
            }
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            async with _make_llm_http_client(timeout=120) as _hx:
                _resp = await _hx.post(url, headers=headers, json=payload)
                _resp.raise_for_status()
                data = _resp.json()
        else:
            # Env-credential path (IAM role, ~/.aws/credentials, instance profile …).
            # Capture proxy URL now — ContextVar values are not inherited by threads.
            _proxy_url = _llm_proxy_var.get()

            def _run_converse():
                import boto3
                from botocore.config import Config as _BotocoreConfig

                region = (
                    os.getenv("AWS_REGION")
                    or os.getenv("AWS_DEFAULT_REGION")
                    or _bedrock_region_from_url(config.base_url or "")
                )
                profile = os.getenv("AWS_PROFILE")
                session_kwargs = {"profile_name": profile} if profile else {}
                session = boto3.Session(**session_kwargs)
                _boto_cfg = _BotocoreConfig(proxies={"http": _proxy_url, "https": _proxy_url}) if _proxy_url else None
                client = session.client(
                    "bedrock-runtime",
                    region_name=region,
                    endpoint_url=config.base_url or None,
                    verify=not _proxy_url,
                    **{"config": _boto_cfg} if _boto_cfg else {},
                )
                return client.converse(
                    modelId=config.model,
                    system=system_list,
                    messages=converse_messages,
                    toolConfig=tool_config,
                    inferenceConfig={
                        "maxTokens": config.max_tokens,
                        "temperature": config.temperature,
                    },
                )

            loop = _asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _run_converse)
        stop_reason_raw = data.get("stopReason") or "end_turn"
        stop_reason = "tool_use" if stop_reason_raw == "tool_use" else "end_turn"
        out_content = (
            ((data.get("output") or {}).get("message") or {}).get("content") or []
        )
        blocks: list[dict] = []
        for blk in out_content:
            if "text" in blk:
                blocks.append({"type": "text", "id": None, "name": None,
                                "input": None, "text": blk["text"]})
            elif "toolUse" in blk:
                tu = blk["toolUse"]
                blocks.append({"type": "tool_use", "id": tu.get("toolUseId"),
                                "name": tu.get("name"), "input": tu.get("input") or {},
                                "text": None})
        # Store as Anthropic-format so the messages list stays consistent
        raw_content_ant = [
            {"type": b["type"], **{
                k: v for k, v in b.items() if k != "type"
            }}
            for b in blocks
        ]
        _bdt_u = data.get("usage", {})
        _record_usage(config.model, _bdt_u.get("inputTokens", 0), _bdt_u.get("outputTokens", 0),
                      cache_read_tokens=_bdt_u.get("cacheReadInputTokenCount", 0),
                      cache_write_tokens=_bdt_u.get("cacheWriteInputTokenCount", 0))
        return blocks, stop_reason, raw_content_ant

    # ── OpenAI-style providers ─────────────────────────────────────────────────
    # Covers: openai, openai_compatible, openrouter, azure_openai,
    #         azure_foundry, azure_foundry_openai
    def _ant_tools_to_openai() -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object"}),
                },
            }
            for t in _active_tools
        ]

    def _ant_messages_to_openai(msgs: list[dict]) -> list[dict]:
        """Translate Anthropic-format messages list to OpenAI chat format."""
        result: list[dict] = [{"role": "system", "content": system_message}]
        for msg in msgs:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, str):
                result.append({"role": role, "content": content})
                continue
            if role == "user":
                tool_results = [b for b in content if b.get("type") == "tool_result"]
                text_blocks  = [b for b in content if b.get("type") == "text"]
                if tool_results:
                    for tr in tool_results:
                        rc = tr.get("content") or ""
                        result.append({
                            "role": "tool",
                            "tool_call_id": tr.get("tool_use_id") or "",
                            "content": rc if isinstance(rc, str) else json.dumps(rc),
                        })
                elif text_blocks:
                    result.append({
                        "role": "user",
                        "content": " ".join(b.get("text", "") for b in text_blocks),
                    })
            elif role == "assistant":
                text_parts    = [b.get("text", "") for b in content if b.get("type") == "text"]
                tool_use_blks = [b for b in content if b.get("type") == "tool_use"]
                oai_msg: dict = {
                    "role": "assistant",
                    "content": " ".join(filter(None, text_parts)) or None,
                }
                if tool_use_blks:
                    oai_msg["tool_calls"] = [
                        {
                            "id": b.get("id") or f"call_{i}",
                            "type": "function",
                            "function": {
                                "name": b.get("name") or "",
                                "arguments": json.dumps(b.get("input") or {}),
                            },
                        }
                        for i, b in enumerate(tool_use_blks)
                    ]
                result.append(oai_msg)
        return result

    if config.provider in (
        "openai", "openai_compatible", "openrouter",
        "azure_openai", "azure_foundry", "azure_foundry_openai",
    ):
        from openai import AsyncOpenAI

        client_kwargs: dict = {"api_key": config.api_key or "not-needed"}
        if config.provider == "openrouter":
            client_kwargs["base_url"] = OPENROUTER_BASE_URL
        elif config.provider in ("azure_openai", "azure_foundry", "azure_foundry_openai"):
            base = (config.base_url or "").rstrip("/")
            client_kwargs["base_url"] = (
                _azure_foundry_openai_base_url(base)
                if config.provider in ("azure_foundry", "azure_foundry_openai")
                else base
            )
        elif config.provider in ("openai", "openai_compatible") and config.base_url:
            base = config.base_url.rstrip("/")
            if not base.endswith("/v1"):
                base += "/v1"
            client_kwargs["base_url"] = base
        client_kwargs.update(_llm_client_kwargs())
        oai_client = AsyncOpenAI(**client_kwargs)
        oai_tools = _ant_tools_to_openai()
        oai_messages = _ant_messages_to_openai(messages)
        call_kwargs = _chat_completion_kwargs(
            config=config,
            provider=config.provider,
            messages=oai_messages,
        )
        call_kwargs["tools"] = oai_tools
        call_kwargs["tool_choice"] = "required"
        resp = await _create_chat_completion(oai_client, call_kwargs)
        choice = resp.choices[0]
        msg = choice.message
        finish = getattr(choice, "finish_reason", None) or "stop"
        blocks = []
        if msg.content:
            blocks.append({"type": "text", "id": None, "name": None,
                            "input": None, "text": msg.content})
        for tc in (getattr(msg, "tool_calls", None) or []):
            try:
                inp = json.loads(tc.function.arguments)
            except Exception:
                inp = {}
            blocks.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.function.name,
                "input": inp,
                "text": None,
            })
        stop_reason = "tool_use" if finish == "tool_calls" else "end_turn"
        _oai_u = getattr(resp, "usage", None)
        _record_usage(config.model,
                      getattr(_oai_u, "prompt_tokens", 0) if _oai_u else 0,
                      getattr(_oai_u, "completion_tokens", 0) if _oai_u else 0)
        return blocks, stop_reason, blocks  # store Anthropic-format in history

    # ── Google Gemini (function calling) ──────────────────────────────────────
    if config.provider == "google":
        from google import genai
        from google.genai import types as _gtypes

        def _ant_tools_to_gemini() -> list:
            fn_decls = []
            for t in _active_tools:
                schema = t.get("input_schema") or {}
                fn_decls.append(
                    _gtypes.FunctionDeclaration(
                        name=t["name"],
                        description=t.get("description", ""),
                        parameters=schema if schema else None,
                    )
                )
            return [_gtypes.Tool(function_declarations=fn_decls)]

        def _ant_contents_to_gemini(msgs: list[dict]) -> list:
            result = []
            for msg in msgs:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]
                parts: list = []
                if isinstance(content, str):
                    parts.append(_gtypes.Part(text=content))
                elif isinstance(content, list):
                    for blk in content:
                        btype = blk.get("type")
                        if btype == "text":
                            parts.append(_gtypes.Part(text=blk.get("text") or ""))
                        elif btype == "tool_use":
                            parts.append(_gtypes.Part(
                                function_call=_gtypes.FunctionCall(
                                    name=blk.get("name") or "",
                                    args=blk.get("input") or {},
                                )
                            ))
                        elif btype == "tool_result":
                            rc = blk.get("content") or ""
                            parts.append(_gtypes.Part(
                                function_response=_gtypes.FunctionResponse(
                                    name=blk.get("tool_use_id") or "",
                                    response={"result": rc},
                                )
                            ))
                if parts:
                    result.append(_gtypes.Content(role=role, parts=parts))
            return result

        g_client = genai.Client(api_key=config.api_key)
        g_tools = _ant_tools_to_gemini()
        g_contents = _ant_contents_to_gemini(messages)
        g_resp = await g_client.aio.models.generate_content(
            model=config.model,
            contents=g_contents,
            config=_gtypes.GenerateContentConfig(
                system_instruction=system_message,
                tools=g_tools,
                max_output_tokens=config.max_tokens,
                temperature=config.temperature,
            ),
        )
        blocks = []
        for part in (g_resp.candidates[0].content.parts if g_resp.candidates else []):
            if getattr(part, "text", None):
                blocks.append({"type": "text", "id": None, "name": None,
                                "input": None, "text": part.text})
            elif getattr(part, "function_call", None):
                fc = part.function_call
                blocks.append({
                    "type": "tool_use",
                    "id": fc.name,   # Gemini doesn't issue call IDs; use name
                    "name": fc.name,
                    "input": dict(fc.args) if fc.args else {},
                    "text": None,
                })
        stop_reason = (
            "tool_use"
            if any(b["type"] == "tool_use" for b in blocks)
            else "end_turn"
        )
        _g_um = getattr(g_resp, "usage_metadata", None)
        _record_usage(config.model,
                      getattr(_g_um, "prompt_token_count", 0) if _g_um else 0,
                      getattr(_g_um, "candidates_token_count", 0) if _g_um else 0)
        return blocks, stop_reason, blocks

    raise ValueError(f"Provider {config.provider!r} does not support native tool use")


async def thinking_agentic_loop(
    config: "LLMConfig",
    *,
    system_message: str,
    initial_user_message: str,
    tool_executor,
    emit_fn=None,
    stop_check=None,
    done_check=None,
    resume_messages: list[dict] | None = None,
    on_checkpoint=None,
    tools: list[dict] | None = None,
) -> str:
    """Run a continuous Anthropic tool-use session.

    Maintains a growing messages list so the model reads its own prior reasoning
    verbatim instead of from a lossy reconstructed summary.

    tool_executor: async (tool_name: str, tool_input: dict, step: int) -> str

    resume_messages: if provided, the loop restores this conversation history
        instead of building a fresh one from initial_user_message.  Used when
        resuming an interrupted scan.

    on_checkpoint: optional async callable ``(messages: list[dict]) -> None``
        invoked after every completed LLM turn so the caller can persist the
        current conversation state to durable storage.

    Returns the summary string from the final ``done`` call (empty string otherwise).
    """
    if resume_messages is not None:
        messages: list[dict] = resume_messages
    else:
        messages: list[dict] = [{"role": "user", "content": initial_user_message}]
    tool_call_count = 0
    final_summary = ""
    consecutive_text_only_turns = 0

    try:
      while True:
        if stop_check and stop_check():
            break

        if emit_fn:
            try:
                emit_fn({
                    "type": "scanner_phase",
                    "phase": "thinking_step",
                    "status": "deciding",
                    "message": (
                        f"Step {tool_call_count + 1}: "
                        "LLM deciding next action\u2026"
                    ),
                    "data": {
                        "step": tool_call_count + 1,
                        "mode": "agentic",
                    },
                })
            except Exception:
                pass

        try:
            if emit_fn:
                try:
                    emit_fn({
                        "type": "scanner_phase",
                        "phase": "llm_request",
                        "status": "pending",
                        "message": (
                            f"Step {tool_call_count + 1}: sending to LLM "
                            f"({len(messages)} messages in context)\u2026"
                        ),
                        "data": {
                            "step": tool_call_count + 1,
                            "message_count": len(messages),
                        },
                    })
                except Exception:
                    pass
            _step_no = tool_call_count + 1
            _t_llm = time.monotonic()
            _llm_fut = asyncio.ensure_future(
                _call_with_tools(config, system_message, messages, tools=tools)
            )
            while True:
                _done, _ = await asyncio.wait({_llm_fut}, timeout=30)
                if _done:
                    break
                _elapsed = int(time.monotonic() - _t_llm)
                if emit_fn:
                    try:
                        emit_fn({
                            "type": "scanner_phase",
                            "phase": "llm_heartbeat",
                            "status": "pending",
                            "message": (
                                f"Step {_step_no}: waiting for LLM response "
                                f"({_elapsed}s elapsed)\u2026"
                            ),
                        })
                    except Exception:
                        pass
            content_blocks, stop_reason, raw_content = _llm_fut.result()
        except Exception as exc:
            log.error(
                "thinking_agentic_loop: API error at step %d: %s",
                tool_call_count + 1, exc,
            )
            _exc_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "") if hasattr(exc, "response") else type(exc).__name__
            _is_expired = "ExpiredToken" in _exc_code or "ExpiredToken" in type(exc).__name__ or "expired" in str(exc).lower()
            if emit_fn:
                try:
                    if _is_expired:
                        _msg = (
                            f"Step {tool_call_count + 1}: AWS credentials have expired. "
                            "Please refresh your AWS credentials and resume the pentest."
                        )
                    else:
                        _msg = f"Step {tool_call_count + 1}: LLM API error — {exc}"
                    emit_fn({
                        "type": "scanner_phase",
                        "phase": "llm_response",
                        "status": "error",
                        "message": _msg,
                        "data": {"step": tool_call_count + 1, "error": str(exc)},
                    })
                except Exception:
                    pass
            break

        tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
        text_blocks = [b for b in content_blocks if b.get("type") == "text" and b.get("text")]

        if emit_fn:
            action_label = (
                ", ".join(b["name"] for b in tool_use_blocks)
                if tool_use_blocks else "end_turn"
            )
            try:
                emit_fn({
                    "type": "scanner_phase",
                    "phase": "llm_response",
                    "status": "complete",
                    "message": f"Step {tool_call_count + 1}: LLM \u2192 {action_label}",
                    "data": {
                        "step": tool_call_count + 1,
                        "raw_response": "\n".join(
                            b.get("text", "") for b in text_blocks
                        )[:4000],
                    },
                })
            except Exception:
                pass

        # Append the assistant turn to the growing conversation
        messages.append({"role": "assistant", "content": raw_content})

        if not tool_use_blocks:
            # OpenAI-style reasoning models occasionally narrate the next step instead
            # of emitting the required tool call. Treat that as a recoverable protocol
            # slip; only the explicit `done` tool is allowed to finish the scan.
            if text_blocks:
                final_summary = (text_blocks[-1].get("text") or "")[:500]
            consecutive_text_only_turns += 1
            if consecutive_text_only_turns >= 3:
                log.warning(
                    "thinking_agentic_loop: model returned %d consecutive text-only "
                    "turns; ending assessment.",
                    consecutive_text_only_turns,
                )
                break
            messages.append({
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": (
                        "Your previous response did not call a tool, so no scan action "
                        "was executed. Continue by calling exactly one tool now. Use "
                        "http_request, browser, context_tool, write_finding, forge_jwt, "
                        "decode_jwt, credential_check, or register_account for the next "
                        "assessment step. Call done only if the assessment is genuinely "
                        "complete and key attack areas have been covered."
                    ),
                }],
            })
            continue
        consecutive_text_only_turns = 0

        # Execute each tool call and collect results for the next user message
        tool_results = []
        session_done = False

        for block in tool_use_blocks:
            tool_call_count += 1
            tool_name = block.get("name") or ""
            tool_input = block.get("input") or {}
            tool_use_id = block.get("id") or ""

            if stop_check and stop_check():
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": "Scan stopped by user.",
                })
                session_done = True
                break

            if tool_name == "done":
                final_summary = str(tool_input.get("summary") or "")
                if done_check:
                    try:
                        done_ok, done_feedback = done_check(tool_input, tool_call_count)
                    except Exception as exc:
                        log.warning("thinking_agentic_loop: done_check failed: %s", exc)
                        done_ok, done_feedback = True, ""
                    if not done_ok:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": (
                                done_feedback
                                or "Assessment is not complete. Continue with one concrete tool call."
                            ),
                        })
                        session_done = False
                        break
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": "Assessment complete.",
                })
                session_done = True
                break

            try:
                result_str = await tool_executor(tool_name, tool_input, tool_call_count)
            except Exception as exc:
                log.warning(
                    "thinking_agentic_loop: tool %r step %d error: %s",
                    tool_name, tool_call_count, exc,
                )
                result_str = f"Tool execution error: {exc}"

            if len(result_str) > TOOL_RESULT_CHAR_LIMIT:
                omitted = len(result_str) - TOOL_RESULT_CHAR_LIMIT
                result_str = (
                    result_str[:TOOL_RESULT_CHAR_LIMIT]
                    + f"\n[{omitted} chars omitted — use context_tool/history_search for details]"
                )

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result_str,
            })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        if on_checkpoint:
            try:
                await on_checkpoint(messages)
            except Exception:
                pass  # checkpoint write failures must never abort the scan

        if session_done:
            break

    finally:
        # Save a final checkpoint on any exit — including CancelledError raised
        # by task.cancel() — so the conversation state is always recoverable.
        if on_checkpoint and len(messages) > 1:
            try:
                await on_checkpoint(messages)
            except Exception:
                pass

    return final_summary


_THINKING_NEXT_ACTION_PROMPT = """\
You are an expert web application penetration tester conducting a hands-on security assessment.
You are working iteratively: each turn you review everything learned so far and decide on ONE
specific action to take next, exactly like a human tester switching between curl and a browser.

Target base URL: {target_url}

Application context discovered during crawling:
{crawl_context}

{credentials_section}
{sessions_section}
RULE: Any vulnerability listed under CONFIRMED VULNERABILITIES is CLOSED — do not probe
it again or attempt to re-prove it. If you need an authenticated session to reach a NEW
endpoint, pick an existing session label from the list above; do not re-fetch secrets or
re-forge tokens for issues that are already confirmed.

Step {current_step} of {max_steps}.

{pentest_playbook}

History of previous actions and responses:
{history_text}

────────────────────────────────────────────────────────────────────────────────
TASK: What is the single most valuable action to take RIGHT NOW?

Think like a human tester:
- Use context tools to pull only the specific crawl/history/finding details you need. Do not
  assume route details are available inline unless they appear in the compact context or history.
- If a target-driven task graph is present in the crawl context, prefer high-priority queued
  or running tasks and reference the matching hypothesis in your observation/note.
- Start broad with site_map when route coverage is unclear, then use page_detail or
  history_search before sending a probe that depends on precise parameters or prior evidence.
- Mine earlier response bodies for tokens (JWT, session), IDs (account, user, transaction),
  API endpoints, error messages, and any other signals.
- Use discovered tokens in Authorization headers for subsequent requests.
- Test for IDOR by swapping IDs you found from one response into requests for another resource.
- Look for auth bypasses, privilege escalation, injection, business-logic flaws, info disclosure.
- Mine raw HTML and JavaScript for endpoint discovery before guessing paths blindly.
- Use HTTP actions for APIs, raw assets, headers, and direct endpoint testing.
- Use browser actions when the next probe depends on JavaScript execution, hash routes,
    form interaction, client-side state, DOM rendering, or screenshot evidence.
- Use register_account when a registration endpoint/form is discovered and a disposable
    low-impact account would improve auth, IDOR, or business-logic coverage.
- Prefer request sequences that prove server-side enforcement, especially check/verify endpoints
    followed by direct action endpoint calls that omit the supposedly required control.
- When you find something interesting, follow it up immediately — don't move on too quickly.
- Do not finish until you have covered the endpoint inventory, authentication boundaries,
    object ownership, business-logic gates, input validation, error disclosure, and headers,
    unless the crawl context clearly lacks that attack surface or steps are nearly exhausted.
- If step count is getting high, prefer discovering new attack surfaces over re-testing already-confirmed findings.
- Be explicit about what made the next request worthwhile. Do not use vague phrases like
    "found something interesting" unless you also name the specific signal and hypothesis.

{severity_calibration}

Return ONLY valid JSON (no markdown, no prose):

To fetch targeted scanner context without issuing a target request:
{{
  "action": "tool",
  "tool": "site_map",
  "args": {{"filter": "api takes-input", "limit": 20}},
  "observation": "The compact context does not include enough endpoint detail.",
  "hypothesis": "Input-taking API routes are the best next attack surface to enumerate.",
  "payload_purpose": "Retrieve only relevant route inventory instead of resending the full crawl.",
  "note": "Fetch the API site map before choosing the next probe."
}}

Context tools:
- site_map: args may include filter/search/type ("api" or "page"), flags (array of
  req_auth/takes_input/has_object_ref/has_business_logic), and limit.
- page_detail: args may include page_id or url and include (array of context/page_text/title/flags).
- history_search: args may include query and limit. Uses EXACT substring matching — use short
  code patterns ("fetch(", "/api/", "axios.post", a URL fragment, or a field name), NOT English
  descriptions. The query must appear verbatim in the stored request/response text.
- finding_list: args may include severity, owasp_category, search, and limit.
- target_inventory: args may include kind, source, search/filter, and limit; returns normalized
  endpoints, forms, inputs, scripts, storage keys, IDs, and response fields from crawl intelligence.
- search_assets: alias of target_inventory, useful with source/kind/search for JS/public asset leads.
- traffic_search: args may include method, status, search/filter, and limit; returns captured HTTP
  request/response excerpts from crawl and scans.
- endpoint_detail: args may include url or page_id and limit; returns page, intel, traffic, history,
  and extracted entities for that endpoint.
- compare_responses: args include left_step/baseline_step and right_step/variant_step from history;
  returns status, length, similarity, and term deltas.
- mutate_request: args may include step or url/method/body plus mutation ("input_validation",
  "idor", or "business_logic"); returns proposed http probe objects. Execute one with an http action.
- auth_matrix: args may include search/filter and limit; returns endpoints worth anonymous/user/role checks.
- extract_entities: args may include text, step, or page_id; returns URLs, paths, IDs, UUIDs, emails,
  redacted JWT hints, and error/debug lines.
- Context tools have an adaptive checkpoint: after 3 consecutive context-only calls,
  execute a probe/write a finding, or include context_budget_reason summarizing what
  you learned, naming the current hypothesis, and explaining why another targeted
  context scan round will change the next action.

To record a confirmed finding using prior evidence handles or response excerpts:
{{
  "action": "finding_write",
  "owasp_category": "A05",
  "title": "Verbose debug configuration disclosure",
  "description": "The health endpoint exposes runtime configuration fields.",
  "impact": "Attackers can use leaked implementation details to plan targeted attacks.",
  "likelihood": "Likely because the endpoint is publicly reachable.",
  "recommendation": "Remove secrets and debug configuration from public responses.",
  "cvss_score": 5.3,
  "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
  "severity": "medium",
  "affected_url": "https://.../api/health",
  "evidence": "Step 3 returned a 200 response containing debug=true.",
  "request_evidence": "GET https://.../api/health",
  "response_evidence": "Status: 200\\n{{...short excerpt...}}",
  "observation": "Specific response evidence that proves the issue",
  "hypothesis": "Why this is a confirmed security issue",
  "payload_purpose": "Persist the finding without another redundant probe",
  "note": "Record the confirmed issue with concise evidence."
}}

To make one HTTP request:
{{
  "action": "http",
  "method": "GET",
  "url": "https://...",
  "use_session": null,
  "headers": {{}},
  "body": null,
    "observation": "Specific signal from prior responses that this follows up, or initial coverage goal",
    "hypothesis": "Specific issue or behavior this request is investigating",
    "payload_purpose": "What the generated query/body/header payload is meant to test, or null",
    "note": "One sentence combining the observation, hypothesis, and why this request is valuable"
}}

HTTP body rules:
- Omit or set null when there is no body.
- Use a JSON object for JSON API payloads (Content-Type will be set automatically).
- Use a plain string for form-encoded or raw bodies.
- Set use_session to one of the reusable session labels when you want the scanner to
  attach a discovered token/session automatically.

To use the browser:
{{
  "action": "browser",
  "url": "https://...",
  "use_session": null,
  "steps": [
    {{"op": "goto", "url": "https://..."}},
    {{"op": "fill", "selector": "input[name='q']", "value": "test"}},
    {{"op": "click", "selector": "button[type='submit']"}},
    {{"op": "wait", "state": "networkidle"}},
    {{"op": "snapshot"}}
  ],
  "observation": "Specific signal from prior responses that requires browser/DOM follow-up",
  "hypothesis": "Specific issue or behavior this browser interaction is investigating",
  "payload_purpose": "What the typed/clicked payload is meant to test, or null",
  "note": "One sentence combining the observation, hypothesis, and why this browser action is valuable"
}}

Browser step rules:
- Supported ops: goto, fill, type, click, press, wait, snapshot.
- For press, include selector and key (for example "Enter").
- For wait, include state ("domcontentloaded", "load", or "networkidle") or ms.
- Keep browser actions short and targeted; do not browse aimlessly.
- Browser use_session currently applies bearer tokens as extra HTTP headers for navigation
  and fetches made after the session is selected.

To forge a JWT after discovering an exposed HS256 signing secret:
{{
  "action": "jwt",
  "secret": "secret-from-prior-response",
  "claims": {{
    "iss": "BankOfEd",
    "sub": 1,
    "jti": "aespa-test",
    "iat": 1778072559,
    "exp": 1778158959
  }},
  "header": {{"typ": "JWT", "alg": "HS256"}},
  "store_as": "customer_sub_1_token",
  "observation": "Specific response field that exposed the signing secret",
  "hypothesis": "Changing sub may impersonate another customer because the API trusts HS256 JWTs",
  "payload_purpose": "Create a controlled token for a read-only impersonation check",
  "note": "Forge an HS256 token from the exposed secret, then use it in a follow-up Authorization header."
}}

JWT rules:
- Only use this after a signing secret or equivalent HMAC key was observed in prior responses.
- Keep claims minimal and use read-only follow-up endpoints first.
- Do not forge admin tokens unless a distinct admin issuer/secret is observed.
- The scanner stores successful forged tokens as reusable in-memory sessions under store_as.

To test a tiny explicit login dictionary:
{{
  "action": "credential_check",
  "url": "https://.../api/admin/auth/login",
  "method": "POST",
  "username_field": "username",
  "password_field": "password",
  "candidates": [
    {{"username": "admin", "password": "admin"}},
    {{"username": "admin", "password": "admin123"}}
  ],
  "headers": {{"Content-Type": "application/json"}},
  "success_statuses": [200, 201],
  "observation": "Specific login endpoint and account naming clue that justify this check",
  "hypothesis": "The deployed demo/admin account may use default or seeded credentials",
  "payload_purpose": "Try a tiny bounded dictionary, not a brute-force attack",
  "note": "Check a small explicit credential list and stop after recording any successes."
}}

Credential-check rules:
- Maximum 20 candidates. Use fewer when possible.
- Only use obvious defaults, seeded/demo credentials, or credentials explicitly found in prior responses.
- Do not use generated wordlists, mutations, high-rate retries, or password spraying.
- Successful login responses with bearer tokens are stored as reusable in-memory sessions.
- Later actions should reference those sessions with use_session rather than copying tokens.

To create one disposable account through a discovered registration endpoint:
{{
    "action": "register_account",
    "url": "https://.../api/users/register",
    "method": "POST",
    "body_format": "json",
    "username_field": "username",
    "email_field": "email",
    "password_field": "password",
    "include_username": true,
    "include_email": true,
    "extra_fields": {{"role": "user"}},
    "headers": {{"Content-Type": "application/json"}},
    "success_statuses": [200, 201, 204],
    "store_as": "disposable_user_a",
    "observation": "The target exposes a public registration endpoint.",
    "hypothesis": "A fresh user account will allow authenticated boundary and IDOR checks.",
    "payload_purpose": "Create one low-impact disposable account for controlled testing.",
    "note": "Register a disposable user and store any returned cookies or bearer token as a reusable session."
}}

Register-account rules:
- Only use this for explicit signup/registration endpoints or forms found in crawl/intelligence/history.
- Create at most one account per distinct testing role unless a later IDOR/business-logic check needs a second user.
- Do not request privileged roles unless the registration endpoint itself exposes that field and the test is low-impact.
- Omit username/email/password values unless the form requires specific values; the scanner generates safe disposable values.
- Successful registration responses store a durable scanner session under store_as when cookies or bearer tokens are captured.

To finish the assessment (all key areas covered, or steps nearly exhausted):
{{
  "action": "done",
  "summary": "2-3 sentence summary of notable findings and tested areas"
}}
"""


async def thinking_next_action(
    config: LLMConfig,
    target_url: str,
    crawl_context: str,
    history: list[dict],
    max_steps: int,
    current_step: int,
    credentials: list[dict] | None = None,
    sessions: list[dict] | None = None,
    emit_fn=None,
) -> dict:
    """Ask the LLM for the next action in an agentic (thinking) scan.

    Returns a dict with either:
      {"action": "tool", "tool": ..., "args": {...}, "note": ...}
      {"action": "http", "method": ..., "url": ..., "headers": ..., "body": ..., "note": ...}
      {"action": "browser", "url": ..., "steps": [...], "note": ...}
      {"action": "jwt", "secret": ..., "claims": {...}, "header": {...}, "note": ...}
      {"action": "credential_check", "url": ..., "candidates": [...], "note": ...}
    {"action": "register_account", "url": ..., "store_as": ..., "note": ...}
      {"action": "finding_write", ...}
    or:
      {"action": "done", "summary": ...}
    """
    # Format history compactly. Full crawl/page details remain available via context tools.
    RECENT = 5
    MAX_HISTORY_CHARS = 18_000
    if not history:
        history_text = "(none — this is the first step)"
    else:
        lines: list[str] = []
        older_count = max(0, len(history) - RECENT)
        if older_count:
            older = history[:older_count]
            lines.append(
                f"Earlier history: {older_count} step(s) summarized. "
                f"Use history_search to retrieve details. "
                f"Recent earlier URLs: "
                + ", ".join(str(h.get("url") or "") for h in older[-8:] if h.get("url"))[:1000]
            )
        for h in history[-RECENT:]:
            method = str(h.get("method") or "")
            is_tool = method == "TOOL"
            _is_js_step = str(h.get("url") or "").split("?")[0].lower().endswith(".js")
            body_limit = 2200 if is_tool else (6000 if _is_js_step else 1400)
            resp_excerpt = str(h.get("response_body") or "")[:body_limit]
            req_body = h.get("request_body")
            req_body_str = (
                json.dumps(req_body, separators=(",", ":"), default=str)[:300]
                if isinstance(req_body, dict)
                else str(req_body or "")[:300]
            )
            response_headers = h.get("response_headers") or {}
            response_headers_str = (
                json.dumps(response_headers, separators=(",", ":"), default=str)[:350]
                if response_headers else "{}"
            )
            lines.append(
                f"Step {h.get('step')}: {method} {h.get('url')}\n"
                f"  Note: {h.get('note', '')}\n"
                f"  Request body: {req_body_str or '(none)'}\n"
                f"  Response status: {h.get('response_status')}\n"
                f"  Response headers: {response_headers_str}\n"
                f"  Response body: {resp_excerpt}"
            )
        history_text = "\n\n".join(lines)
        if len(history_text) > MAX_HISTORY_CHARS:
            history_text = (
                history_text[:MAX_HISTORY_CHARS]
                + "\n\n[history truncated; use history_search for older or larger response details]"
            )

    credentials_section = ""
    if credentials:
        cred_lines = [
            f"  - username={c['username']}  password={c['password']}"
            + (f"  login_url={c['login_url']}" if c.get("login_url") else "")
            for c in credentials
        ]
        credentials_section = (
            "Test credentials (use these to authenticate):\n"
            + "\n".join(cred_lines)
        )

    sessions_section = ""
    if sessions:
        session_lines = [
            f"  - label={s.get('label')}  kind={s.get('kind', 'bearer')}"
            + (f"  username={s.get('username')}" if s.get("username") else "")
            + (f"  source={s.get('source')}" if s.get("source") else "")
            for s in sessions
        ]
        sessions_section = (
            "Reusable authenticated sessions (includes sessions from prior scans) — "
            "use these labels instead of re-authenticating or re-forging tokens:\n"
            + "\n".join(session_lines)
        )

    prompt = _THINKING_NEXT_ACTION_PROMPT.format(
        target_url=target_url,
        crawl_context=crawl_context,
        credentials_section=credentials_section,
        sessions_section=sessions_section,
        current_step=current_step,
        max_steps=max_steps,
        pentest_playbook=_THINKING_PENTEST_PLAYBOOK,
        history_text=history_text,
        severity_calibration=_SEVERITY_CALIBRATION,
    )
    if emit_fn:
        try:
            emit_fn({
                "type": "scanner_phase",
                "phase": "llm_request",
                "status": "pending",
                "message": f"Step {current_step}: sending prompt ({len(prompt):,} chars) to LLM…",
                "data": {"step": current_step, "prompt": prompt},
            })
        except Exception:
            pass
    raw = await _call(config, prompt, None)
    action: dict
    try:
        action = _normalize_thinking_action(_extract_action_json(raw or ""))
    except Exception as exc:
        log.warning(
            "thinking_next_action: initial parse failed (%s), retrying with correction prompt. "
            "Raw (first 300 chars): %r",
            exc,
            (raw or "")[:300],
        )
        try:
            # Re-send the original prompt with the correction appended so the model
            # has full context and doesn't return a generic "no task provided" done.
            correction_with_context = (
                prompt
                + "\n\n---\n"
                + _THINKING_CORRECTION_PROMPT
            )
            raw2 = await _call(config, correction_with_context, None)
            action = _normalize_thinking_action(_extract_action_json(raw2 or ""))
            log.info("thinking_next_action: correction retry succeeded — action=%r", action.get("action"))
        except Exception as exc2:
            log.warning("thinking_next_action: retry also failed (%s). Ending assessment.", exc2)
            action = {"action": "done", "summary": "LLM did not return a valid action — assessment ended."}
    if emit_fn:
        try:
            emit_fn({
                "type": "scanner_phase",
                "phase": "llm_response",
                "status": "complete",
                "message": (
                    f"Step {current_step}: LLM → {action.get('action')}"
                    + (f" {action.get('tool','')}" if action.get('action') == 'tool' else '')
                    + (f" {action.get('method','')} {action.get('url','')}" if action.get('action') == 'http' else '')
                    + (f" {action.get('url','')}" if action.get('action') == 'browser' else '')
                    + (f" {action.get('store_as','')}" if action.get('action') == 'jwt' else '')
                    + (f" {action.get('url','')}" if action.get('action') == 'credential_check' else '')
                    + (f" {action.get('title','')}" if action.get('action') == 'finding_write' else '')
                    + (
                        f": {action.get('hypothesis') or action.get('note','')}"
                        if action.get('hypothesis') or action.get('note')
                        else ""
                    )
                ),
                "data": {"step": current_step, "raw_response": raw, "action": action},
            })
        except Exception:
            pass
    return action


# ── Adversarial validator LLM config ─────────────────────────────────────────

_ADVERSARIAL_VALIDATOR_SYSTEM = """\
You are an adversarial security reviewer. A vulnerability scanner reported a potential finding.

Your mandate is deliberately adversarial: your job is to DISPROVE the finding — to find the \
innocent explanation, not the guilty one.

You succeed when you find a concrete benign explanation for the evidence.
You confirm only when you have exhausted all reasonable disproofs.

Workflow
────────
1. Read the evidence with maximum scepticism. Identify the weakest assumption the scanner made \
— the single assumption that, if wrong, makes this a false positive.
2. Test that assumption first. Use the simplest, highest-information test you can devise.
3. If your test provides a concrete innocent explanation → call done(verdict="false_positive"), \
stating exactly what the innocent explanation is.
4. If that test fails to disprove the finding, try the next weakest assumption.
5. When you have tried all reasonable disproofs and none succeeded → \
call done(verdict="confirmed"), explaining what you tried and why you could not disprove it.

Hard rules
──────────
• A failed probe is NOT evidence of innocence. Network errors, rate-limiting, and \
mis-specified probes are your problem to work around — keep trying with a different approach.
• Never return false_positive based solely on failure to reproduce. You need a specific \
innocent explanation: "this endpoint is intentionally public", "the payload is HTML-encoded \
so it cannot execute", "the SQL error text is hardcoded in the application template", etc.
• Stay focused on the finding's core claim. Do not explore adjacent attack surface.
• You cannot write new findings. Your only output is a verdict via done().
"""

# Per-OWASP-category disproof strategies.  Keyed by two-character prefix (A01–A10).
_DISPROOF_HINTS: dict[str, str] = {
    "A01": """\
Disproof checklist for A01 (Broken Access Control / IDOR):
• Re-request the resource with no authentication at all (strip cookies and auth headers). \
If you receive the same data, the endpoint may be intentionally public — not an access \
control failure.
• Verify the response is not a generic SPA shell (React/Vue root div + bundled script \
tags with minimal readable text). A shell page is never sensitive data disclosure.
• For IDOR claims: confirm the session token in the original evidence belonged to a \
different user, not the legitimate owner. Session confusion in proxy tooling is a common \
false-positive source.
• Check whether the object ID appears in a public listing or URL. Sequential IDs on \
public resources (blog posts, product catalogue) are not IDOR unless sensitive \
user-specific data is returned.""",

    "A02": """\
Disproof checklist for A02 (Cryptographic Failures):
• Missing HTTPS: the target may sit behind a TLS-terminating reverse proxy. Verify \
whether the domain serves HTTPS on port 443 even if the scanner probed a direct backend \
port (80 / 8080 / 8443).
• Missing HSTS or weak cipher: re-request the URL directly without a proxy — intercepting \
proxies sometimes strip or downgrade security headers. Use compare_responses against \
a proxy-direct and a direct path if both are reachable.
• Weak password storage: confirm the allegedly plaintext secret appears in a live response \
body, not only in a static export or debug log that is already access-controlled.""",

    "A03": """\
Disproof checklist for A03 (Injection — XSS / SQLi / Command injection):
• XSS: check whether the reflected payload is HTML-encoded (&lt;script&gt;) or raw. \
HTML-encoding neutralises execution. Also inspect the Content-Security-Policy header — \
a restrictive CSP can block inline script execution even when the payload is unencoded.
• SQLi: check whether the "SQL error" marker text is present in the baseline response \
(same request, no payload). Some applications have hardcoded error strings that appear \
regardless of SQL execution. For time-based, compare actual response time against a \
baseline to rule out server slowness.
• Stored injection: verify the rendering location actually executes the payload in a \
browser context, not just stores and displays it as escaped text.""",

    "A04": """\
Disproof checklist for A04 (Insecure Design / Business Logic):
• Business logic flaws require precise preconditions. Reproduce the exact transaction \
sequence: same starting state, same user role, same parameter values. Variation in \
state often produces different results that look like a flaw but are not.
• Check whether the "unexpected" behaviour is actually documented. Some applications \
intentionally allow negative-value transactions, large transfers, or unusual role \
combinations for operational reasons.
• Race conditions require genuinely concurrent requests. Sequential probes cannot \
reproduce them — if you suspect the scanner triggered one by accident, discard \
the finding unless you can replicate it with actual concurrency.""",

    "A05": """\
Disproof checklist for A05 (Security Misconfiguration):
• Missing headers (X-Frame-Options, CSP, HSTS): re-request the endpoint directly to rule \
out proxy stripping. Check whether a meta-tag equivalent or a CDN-layer header covers \
the same protection.
• Exposed debug / admin endpoint: verify the endpoint returns meaningful sensitive data, \
not just an HTTP 200 with an empty body or a redirect to a login page.
• Default credentials: confirm the login actually succeeded with a privileged response \
(token, redirect to authenticated area), not just an HTTP 200 on the login endpoint.""",

    "A07": """\
Disproof checklist for A07 (Identification and Authentication Failures):
• Is the endpoint intentionally unauthenticated? Health checks (/health, /status, \
/ping), metrics endpoints, OpenAPI specs (/swagger, /openapi.json), and CORS preflight \
responses are typically public by design.
• For JWT issues: was the signing secret actually extracted from an application response, \
or is it a hypothesis? Verify by forging a token with the extracted secret and testing \
whether it is accepted by a protected endpoint.
• For missing auth on a sensitive endpoint: confirm the endpoint returns genuinely \
sensitive data without a session, not just a 200 OK with a generic page body.
• Was the scanner's "unauthenticated" request genuinely cookie-free? Some HTTP clients \
carry session cookies from a prior authenticated step automatically.""",

    "A10": """\
Disproof checklist for A10 (Server-Side Request Forgery):
• Does the application actually make an outbound request, or does it echo the URL in \
an error message? Issue a request targeting a host you control and check for an inbound \
connection to confirm real outbound activity.
• Is the "internal IP response" genuinely from an internal host, or does the error \
message coincidentally contain IP-like text in a static template?
• Does the application validate or whitelist URLs before issuing requests? Test with \
a valid external URL first to confirm the feature makes any outbound call at all, then \
probe with an internal address.""",
}


def _disproof_hints_for_finding(owasp_category: str) -> str:
    """Return category-specific disproof strategies or an empty string."""
    cat = (owasp_category or "").upper()
    for key, hints in _DISPROOF_HINTS.items():
        if cat.startswith(key):
            return hints
    return ""


_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def severity_meets_threshold(severity: str, min_severity: str) -> bool:
    """Return True when *severity* is at or above *min_severity*."""
    rank = _SEVERITY_RANK.get((severity or "low").lower(), 3)
    threshold = _SEVERITY_RANK.get((min_severity or "low").lower(), 3)
    return rank <= threshold


# Validator-specific tool: compare two requests side-by-side.
_COMPARE_RESPONSES_TOOL: dict = {
    "name": "compare_responses",
    "description": (
        "Send two HTTP requests (baseline and test) and compare their responses. "
        "Use to detect whether a payload causes a meaningful difference vs. a benign "
        "baseline. Returns both full responses with a status and body diff summary. "
        "This is the primary tool for disproving injection and access-control findings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "baseline": {
                "type": "object",
                "description": "Baseline request — benign input or no payload.",
                "properties": {
                    "method": {"type": "string"},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {},
                    "use_session": {"type": "string"},
                },
                "required": ["url"],
            },
            "test": {
                "type": "object",
                "description": "Test request — tampered or payload-bearing variant.",
                "properties": {
                    "method": {"type": "string"},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {},
                    "use_session": {"type": "string"},
                },
                "required": ["url"],
            },
            "note": {
                "type": "string",
                "description": "What you expect this comparison to reveal.",
            },
        },
        "required": ["baseline", "test"],
    },
}

# Validator done tool — carries verdict, reasoning, confidence instead of summary.
_VALIDATOR_DONE_TOOL: dict = {
    "name": "done",
    "description": (
        "Call when you have reached a verdict. "
        "Provide a specific reason grounded in your probe results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["confirmed", "false_positive"],
                "description": (
                    "confirmed: you tried all reasonable disproofs and could not find "
                    "an innocent explanation. "
                    "false_positive: you found a concrete benign explanation."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "2–4 sentences. For false_positive: state the specific innocent "
                    "explanation. For confirmed: state what you tried and why it failed."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Your confidence in the verdict.",
            },
        },
        "required": ["verdict", "reasoning"],
    },
}

# Tools available to the adversarial validator agent.
VALIDATOR_AGENT_TOOLS: list[dict] = [
    next(t for t in THINKING_AGENT_TOOLS if t["name"] == "http_request"),
    _COMPARE_RESPONSES_TOOL,
    next(t for t in THINKING_AGENT_TOOLS if t["name"] == "context_tool"),
    _VALIDATOR_DONE_TOOL,
]


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
