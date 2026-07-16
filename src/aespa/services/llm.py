"""Abstract LLM client wrappers for configured provider APIs."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional
from urllib.parse import quote

import httpx

from aespa.models import LLMConfig
from aespa.services.prompts.login_action import LOGIN_ACTION_PROMPT
from aespa.services.prompts.reporting import (
    _ANALYSE_PROMPT,
    _NORMALIZE_TITLES_PROMPT,
    _WRITEUP_REPLAY_PROMPT,
)

# Re-exported for consumers that import this from aespa.services.llm.
from aespa.services.prompts.specialist import SPECIALIST_AGENT_TOOLS  # noqa: F401
from aespa.services.prompts.test_lead import (
    _ANALYSIS_PROMPT,
    _AUTH_PATH_FRAGMENTS,
    _CREDENTIAL_PATH_FRAGMENTS,
    _FOLLOWUP_PROMPT,
    _PLAN_PROMPT,
    _SITE_PLAN_PROMPT,
    _SKILL_ORDER,
    _SSRF_PARAM_NAMES,
    _THINKING_CORRECTION_PROMPT,
    _THINKING_NEXT_ACTION_PROMPT,
    _THINKING_PENTEST_PLAYBOOK,
    THINKING_AGENT_TOOLS,
    WSTG_SKILLS,
)
from aespa.services.prompts.validator import (
    _ADVERSARIAL_VALIDATOR_SYSTEM,  # noqa: F401 — re-exported via aespa.services.llm
    _DISPROOF_HINTS,
    _VALIDATION_PLAN_PROMPT,
    _VALIDATION_VERDICT_PROMPT,
    VALIDATOR_AGENT_TOOLS,  # noqa: F401 — re-exported via aespa.services.llm
)

log = logging.getLogger("aespa.llm")

REPORTING_REPLAY_SCHEMA = "aespa.reporting.replay.v1"


class LLMRefusalError(RuntimeError):
    """The provider refused to process an agentic scan request."""


_REFUSAL_MARKERS = (
    "cyber_policy",
    "content was flagged for possible cybersecurity risk",
    "responsibleaipolicyviolation",
    "content_filter",
    "content filter",
    "guardrail_intervened",
    "guardrail intervened",
    "blocked by a safety",
    "blocked for safety",
    "safety policy",
    "policy violation",
)


def _is_llm_refusal(exc: BaseException) -> bool:
    """Return True for provider errors that explicitly identify a refusal."""
    if isinstance(exc, LLMRefusalError):
        return True
    parts = [str(exc)]
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            parts.append(str(getattr(response, "text", "") or ""))
        except Exception:
            pass
        try:
            parts.append(json.dumps(response.json(), default=str))
        except Exception:
            pass
    text = " ".join(parts).lower()
    return any(marker in text for marker in _REFUSAL_MARKERS)

_llm_proxy_var: ContextVar[str | None] = ContextVar("_llm_proxy", default=None)
_run_id_var: ContextVar[int | None] = ContextVar("_run_id", default=None)
_run_kind_var: ContextVar[str] = ContextVar("_run_kind", default="web")
_emit_fn_var: ContextVar[Any | None] = ContextVar("_emit_fn", default=None)
_last_call_tokens_var: ContextVar[Optional[dict[str, int]]] = ContextVar(
    "last_call_tokens", default=None
)

# Per-run token usage accumulator: {(run_kind, run_id): {model: {"input": N, "output": N, "cache_read": N, "cache_write": N}}}
_run_token_usage: dict[tuple[str, int], dict[str, dict[str, int]]] = {}

# Tracks which (run_kind, run_id) tuples have already been seeded from DB this process lifetime.
_run_token_seeded: set[tuple[str, int]] = set()


# ── Rate Limiting Core ────────────────────────────────────────────────────────


class AsyncTokenBucketLimiter:
    def __init__(self, tpm: int, rpm: Optional[int] = None):
        self.tpm = tpm
        self.rpm = rpm

        self.max_tokens = float(tpm)
        self.tokens_per_second = tpm / 60.0
        self.available_tokens = float(tpm)
        self.last_token_update = time.monotonic()

        self.max_requests = float(rpm) if rpm else 0.0
        self.requests_per_second = (rpm / 60.0) if rpm else 0.0
        self.available_requests = float(rpm) if rpm else 0.0
        self.last_request_update = time.monotonic()

        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int, on_wait=None) -> bool:
        # A single request can never need more than the entire per-minute budget;
        # cap the estimate so we wait at most 60s instead of rejecting.
        est = min(float(estimated_tokens), self.max_tokens)
        slept = False
        notified = False
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_token_update
                self.available_tokens = min(
                    self.max_tokens, self.available_tokens + elapsed * self.tokens_per_second
                )
                self.last_token_update = now

                if self.max_requests > 0:
                    req_elapsed = now - self.last_request_update
                    self.available_requests = min(
                        self.max_requests,
                        self.available_requests + req_elapsed * self.requests_per_second,
                    )
                    self.last_request_update = now

                has_tokens = self.available_tokens >= est
                has_reqs = self.max_requests == 0 or self.available_requests >= 1.0

                if has_tokens and has_reqs:
                    self.available_tokens -= est
                    if self.max_requests > 0:
                        self.available_requests -= 1.0
                    return slept

                wait_tokens = (
                    (est - self.available_tokens) / self.tokens_per_second
                    if not has_tokens
                    else 0.0
                )
                wait_reqs = (
                    (1.0 - self.available_requests) / self.requests_per_second
                    if not has_reqs and self.requests_per_second > 0
                    else 0.0
                )
                wait_time = max(wait_tokens, wait_reqs)
                slept = True

            if on_wait and not notified:
                notified = True
                try:
                    on_wait(wait_time)
                except Exception:
                    pass
            await asyncio.sleep(wait_time)

    async def reconcile(self, estimated_tokens: int, actual_tokens: int) -> None:
        async with self._lock:
            # Mirror the clamp in acquire(): only ``min(estimated, max_tokens)`` was
            # ever reserved, so only that much can be credited back.
            reserved = min(float(estimated_tokens), self.max_tokens)
            difference = reserved - actual_tokens
            self.available_tokens = min(
                self.max_tokens, max(0.0, self.available_tokens + difference)
            )


def estimate_tokens(
    prompt: str, screenshot_b64: Optional[str] = None, provider: str = "openai"
) -> int:
    text_tokens = int((len(prompt) / 4.0) * 1.1)
    vision_tokens = 0
    if screenshot_b64:
        if provider == "anthropic":
            vision_tokens = 1600
        elif provider in ("openai", "azure_openai", "openrouter"):
            vision_tokens = 765
        else:
            vision_tokens = 258
    return text_tokens + vision_tokens


_limiters: dict[str, AsyncTokenBucketLimiter] = {}
_limiters_lock = asyncio.Lock()


def get_limiter_for_config(config: LLMConfig) -> Optional[AsyncTokenBucketLimiter]:
    if config.provider_id is None:
        return None

    key = f"{config.provider}:{config.model}"
    try:
        from sqlmodel import Session

        from aespa.db import get_engine
        from aespa.models import LLMProviderConfig

        with Session(get_engine()) as session:
            provider = session.get(LLMProviderConfig, config.provider_id)
            if not provider or (not provider.max_tpm and not provider.max_rpm):
                _limiters.pop(key, None)
                return None

            tpm = provider.max_tpm or 10_000_000
            rpm = provider.max_rpm

            limiter = _limiters.get(key)
            if not limiter or limiter.tpm != tpm or limiter.rpm != rpm:
                _limiters[key] = AsyncTokenBucketLimiter(tpm=tpm, rpm=rpm)
    except Exception as e:
        log.warning(f"Failed to lookup rate limit for provider: {e}")

    return _limiters.get(key)



def _load_bucket_from_db(run_id: int, run_kind: str = "web") -> dict[str, dict[str, int]]:
    """Load persisted token usage for a run from the DB (best-effort)."""
    try:
        from sqlmodel import Session as _Session

        from aespa.db import get_engine
        from aespa.models import ApiTestRun, SastRun, TestRun

        with _Session(get_engine()) as s:
            model_cls = SastRun if run_kind == "sast" else ApiTestRun if run_kind == "api" else TestRun
            run = s.get(model_cls, run_id)
            if run and run.token_usage_json:
                return json.loads(run.token_usage_json)
    except Exception:
        pass
    return {}


def _persist_bucket_to_db(run_id: int, bucket: dict, run_kind: str = "web") -> None:
    """Write the current in-memory bucket for a run back to the DB (best-effort)."""
    try:
        from sqlmodel import Session as _Session

        from aespa.db import get_engine
        from aespa.models import ApiTestRun, SastRun, TestRun

        with _Session(get_engine()) as s:
            model_cls = SastRun if run_kind == "sast" else ApiTestRun if run_kind == "api" else TestRun
            run = s.get(model_cls, run_id)
            if run:
                run.token_usage_json = json.dumps(bucket)
                s.add(run)
                s.commit()
    except Exception:
        pass


def set_run_context(run_id: int, emit_fn: Any, run_kind: str = "web") -> None:
    """Set the current run context so LLM calls track token usage automatically.

    Seeds the in-memory bucket from DB on first call for this (run_kind, run_id) so that
    token counts accumulate correctly across server restarts.
    """
    _run_id_var.set(run_id)
    _run_kind_var.set(run_kind)
    _emit_fn_var.set(emit_fn)
    key = (run_kind, run_id)
    if key not in _run_token_seeded:
        existing = _load_bucket_from_db(run_id, run_kind)
        if existing:
            # Merge DB data into the (possibly already-populated) in-memory bucket.
            bucket = _run_token_usage.setdefault(key, {})
            for model, counts in existing.items():
                if model not in bucket:
                    bucket[model] = {
                        "input": 0,
                        "output": 0,
                        "cache_read": 0,
                        "cache_write": 0,
                    }
                for k in ("input", "output", "cache_read", "cache_write"):
                    bucket[model][k] = max(bucket[model].get(k, 0), counts.get(k, 0))
        _run_token_seeded.add(key)


def clear_run_context() -> None:
    _run_id_var.set(None)
    _run_kind_var.set("web")
    _emit_fn_var.set(None)


def _record_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> None:
    """Accumulate token counts for the active run and fire a SSE event."""
    _last_call_tokens_var.set(
        {"input": input_tokens + cache_read_tokens, "output": output_tokens}
    )
    run_id = _run_id_var.get()
    if run_id is None:
        return
    run_kind = _run_kind_var.get()
    key = (run_kind, run_id)
    bucket = _run_token_usage.setdefault(key, {})
    entry = bucket.setdefault(
        model, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    )
    entry["input"] += input_tokens
    entry["output"] += output_tokens
    entry["cache_read"] += cache_read_tokens
    entry["cache_write"] += cache_write_tokens
    _persist_bucket_to_db(run_id, bucket, run_kind)
    emit_fn = _emit_fn_var.get()
    if emit_fn:
        try:
            total_in = sum(v["input"] for v in bucket.values())
            total_out = sum(v["output"] for v in bucket.values())
            total_cache_read = sum(v.get("cache_read", 0) for v in bucket.values())
            total_cache_write = sum(v.get("cache_write", 0) for v in bucket.values())
            emit_fn(
                {
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
                }
            )
        except Exception:
            pass


def _record_google_usage(model: str, usage_metadata: Any | None) -> None:
    """Record Gemini usage, whose optional counters may be explicitly ``None``."""

    def _token_count(name: str) -> int:
        value = getattr(usage_metadata, name, 0) if usage_metadata else 0
        return value if isinstance(value, int) and value >= 0 else 0

    cached_tokens = _token_count("cached_content_token_count")
    prompt_tokens = _token_count("prompt_token_count")
    _record_usage(
        model,
        max(0, prompt_tokens - cached_tokens),
        _token_count("candidates_token_count"),
        cache_read_tokens=cached_tokens,
    )


def get_run_token_usage(run_id: int, run_kind: str = "web") -> dict:
    """Return accumulated token usage for a run.

    If the run isn't in the in-memory dict (e.g. after a server restart), falls
    back to the persisted DB value so the REST endpoint always returns data.
    """
    key = (run_kind, run_id)
    bucket = _run_token_usage.get(key)
    if bucket is None:
        bucket = _load_bucket_from_db(run_id, run_kind)
    return {
        "total_input": sum(v["input"] for v in bucket.values()),
        "total_output": sum(v["output"] for v in bucket.values()),
        "total_cache_read": sum(v.get("cache_read", 0) for v in bucket.values()),
        "total_cache_write": sum(v.get("cache_write", 0) for v in bucket.values()),
        "by_model": {m: dict(v) for m, v in bucket.items()},
    }


def set_llm_proxy(url: str | None) -> None:
    _llm_proxy_var.set(url)


def _emit_run_event(event: dict) -> None:
    """Emit an event to whatever log is wired for the active run.

    Routes through the context ``emit_fn`` set by ``set_run_context`` (the scanner
    log, the API scan log, the ALICE event/chat stream, …), falling back to
    ``events.emit(run_id)``.  Best-effort — never raises into an LLM call.
    """
    emit_fn = _emit_fn_var.get()
    if emit_fn is not None:
        try:
            emit_fn(event)
            return
        except Exception:
            pass
    run_id = _run_id_var.get()
    if run_id is not None:
        try:
            from aespa.services import events as _events

            _events.emit(run_id, event)
        except Exception:
            pass


def _emit_rate_limit_waiting(
    model: str, reserved_tokens: float, wait_time: float
) -> None:
    """Tell the user the scan is pacing for the rate limit (not stuck)."""
    _emit_run_event(
        {
            "type": "scanner_phase",
            "phase": "rate_limit",
            "status": "active",
            "message": (
                f"LLM rate limit reached — pacing requests to stay within the "
                f"configured limit (waiting ~{wait_time:.0f}s, reserved "
                f"{int(reserved_tokens):,} tokens for {model})…"
            ),
        }
    )


def _emit_rate_limit_cleared(model: str, used_tokens: int) -> None:
    _emit_run_event(
        {
            "type": "scanner_phase",
            "phase": "rate_limit",
            "status": "complete",
            "message": (
                f"LLM rate limit cleared — resuming "
                f"(used {used_tokens:,} tokens for {model})."
            ),
        }
    )


# Identifying headers attached to every outbound LLM request (e.g. for OpenRouter attribution).
_LLM_HEADERS = {"HTTP-Referer": "https://github.com/ledwardchow/aespa", "X-Title": "AESPA"}


def _llm_client_kwargs() -> dict:
    """Returns {'http_client': ...} for SDK clients (Anthropic, OpenAI).

    TLS verification is left ON for direct connections and only disabled when an
    upstream proxy is configured (to support HTTPS interception, e.g. Burp) —
    mirroring the Bedrock path. Disabling it unconditionally would expose the API
    key and prompt data to MITM even with no proxy in play.
    """
    proxy = _llm_proxy_var.get()
    return {
        "http_client": httpx.AsyncClient(
            verify=proxy is None,
            headers=_LLM_HEADERS,
            **{"proxy": proxy} if proxy else {},
        )
    }


def _make_llm_http_client(**kwargs) -> httpx.AsyncClient:
    """Creates an httpx client for direct LLM calls.

    Verifies TLS by default; only disables verification when an upstream proxy is
    configured (HTTPS interception). See ``_llm_client_kwargs`` for rationale.
    """
    proxy = _llm_proxy_var.get()
    kwargs.setdefault("verify", proxy is None)
    kwargs["headers"] = {**_LLM_HEADERS, **kwargs.get("headers", {})}
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.AsyncClient(**kwargs)


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ANALYSE_RESULTS_TEXT_BUDGET = 80_000
ANALYSE_RESULTS_PER_BATCH = 20
_THINKING_CONTEXT_TOOL_ARG_KEYS = {
    "site_map": ("filter", "search", "type", "flags", "limit"),
    "page_detail": ("page_id", "url", "include"),
    "history_search": ("query", "search", "limit"),
    "finding_list": ("severity", "owasp_category", "category", "search", "limit"),
}
_THINKING_CONTEXT_TOOLS = frozenset(_THINKING_CONTEXT_TOOL_ARG_KEYS)


def _strip_thinking_blocks(raw: str) -> str:
    """Remove visible model reasoning wrappers while keeping the final answer."""
    text = raw
    block_tags = ("think", "thinking", "reasoning", "thought")
    for tag in block_tags:
        text = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>", "", text, flags=re.DOTALL | re.IGNORECASE
        )

    # Some local/OpenRouter reasoning models emit pseudo-markup blocks without a
    # closing tag when they are interrupted near the final JSON.
    text = re.sub(
        r"(?is)^\s*(?:reasoning|thinking|thought)\s*:\s*.*?(?=[\[{])", "", text
    )
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
    open_ch = "[" if expect is list else "{"
    close_ch = "]" if expect is list else "}"
    starts = [i for i, ch in enumerate(text) if ch == open_ch]
    if not starts:
        # Stripped text has no JSON delimiters — the model may have embedded the answer
        # inside a thinking block.  Try searching the un-stripped original text so we can
        # still extract JSON that appears within <think>...</think> tags.
        raw_no_fence = (
            re.sub(r"```(?:json|python)?\s*", "", raw).strip().rstrip("`").strip()
        )
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


PageCategories = dict

_EMPTY_CATS: PageCategories = {
    "req_auth": None,
    "takes_input": None,
    "has_object_ref": None,
    "has_business_logic": None,
}

OWASP_WEB_CATEGORIES: list[str] = [
    "A01",
    "A02",
    "A03",
    "A04",
    "A05",
    "A06",
    "A07",
    "A08",
    "A09",
    "A10",
]

OWASP_WEB_LABELS: dict[str, str] = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Software & Data Supply Chain Failures",
    "A07": "Identification & Auth Failures",
    "A08": "Software & Data Integrity Failures",
    "A09": "Security Logging & Monitoring Failures",
    "A10": "SSRF",
}

_EMPTY_OWASP: dict[str, bool] = {cat: False for cat in OWASP_WEB_CATEGORIES}


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


_LOGIN_ACTIONS = {"fill", "click", "press", "done", "give_up"}


async def decide_login_action(
    config: LLMConfig,
    *,
    url: str,
    observation: str,
    username_hint: str,
    history: list[str],
    screenshot_b64: Optional[str] = None,
) -> dict:
    """Decide the single next browser action to log a user in.

    Returns ``{"action", "selector", "text", "value", "reason"}`` where
    ``action`` is one of fill/click/press/done/give_up. Used by the crawler's
    LLM-driven login fallback. The model returns ``{{username}}`` / ``{{password}}``
    placeholders rather than real secrets — the crawler substitutes them locally.
    On any parse failure this returns a ``give_up`` action so the caller stops
    cleanly rather than raising.
    """
    history_text = "\n".join(f"- {h}" for h in history[-12:]) or "(none yet)"
    prompt = LOGIN_ACTION_PROMPT.format(
        username_hint=username_hint or "(see credential)",
        url=url,
        observation=observation[:6000],
        history=history_text,
    )
    try:
        raw = await _call(config, prompt, screenshot_b64 if config.use_vision else None)
        action = _extract_action_json(raw)
    except Exception as exc:
        return {"action": "give_up", "reason": f"LLM action parse failed: {exc}"}

    name = str(action.get("action") or "").strip().lower()
    if name not in _LOGIN_ACTIONS:
        return {"action": "give_up", "reason": f"unknown action {name!r}"}
    return {
        "action": name,
        "selector": str(action.get("selector") or "").strip(),
        "text": str(action.get("text") or "").strip(),
        "value": str(action.get("value") or ""),
        "reason": str(action.get("reason") or "").strip(),
    }


def _parse(raw: Optional[str], page_url: str) -> tuple[str, list[str], PageCategories]:
    if not raw:
        return "", [], dict(_EMPTY_CATS)
    try:
        data = _extract_json(raw, expect=dict)
        if not isinstance(data, dict):
            return raw.strip(), [], dict(_EMPTY_CATS)
        context = str(data.get("context") or raw)
        label = " ".join(str(data.get("page_label") or "").split())
        links = data.get("suggested_links") or []
        if not isinstance(links, list):
            links = []
        safe_links = [
            str(u) for u in links if isinstance(u, str) and u.startswith("http")
        ]
        # Parse categories — each value coerced to bool or None
        raw_cats = data.get("categories") or {}
        cats: PageCategories = {}
        for key in ("req_auth", "takes_input", "has_object_ref", "has_business_logic"):
            val = raw_cats.get(key)
            cats[key] = bool(val) if val is not None else None
        # Parse OWASP applicability — normalise to {A01: bool, …}
        raw_owasp = data.get("owasp_applicable") or {}
        owasp: dict[str, bool] = dict(_EMPTY_OWASP)
        for cat in OWASP_WEB_CATEGORIES:
            entry = raw_owasp.get(cat)
            if isinstance(entry, dict):
                owasp[cat] = bool(entry.get("applicable"))
            elif entry is not None:
                owasp[cat] = bool(entry)
        cats["owasp_applicable"] = owasp
        cats["page_label"] = " ".join(label.split()[:5]) if label else ""
        return context, safe_links, cats
    except Exception:
        return raw.strip(), [], dict(_EMPTY_CATS)


async def _call(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    limiter = get_limiter_for_config(config)
    if limiter is None:
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
        if config.provider == "bedrock_mantle":
            return await _openai_responses(config, prompt, screenshot_b64)
        return await _openai_compat(config, prompt, screenshot_b64)

    estimated_input = estimate_tokens(prompt, screenshot_b64, config.provider)
    estimated_output = config.max_tokens or 4096
    total_estimated = estimated_input + estimated_output

    _last_call_tokens_var.set(None)
    # Notify the user the moment pacing starts (on_wait fires before the sleep),
    # so a rate-limited scan never looks frozen.
    slept = await limiter.acquire(
        total_estimated,
        on_wait=lambda wt: _emit_rate_limit_waiting(
            config.model, min(total_estimated, limiter.max_tokens), wt
        ),
    )

    try:
        if config.provider == "anthropic":
            resp = await _anthropic(config, prompt, screenshot_b64)
        elif config.provider == "google":
            resp = await _google(config, prompt, screenshot_b64)
        elif config.provider == "azure_openai":
            resp = await _azure_openai(config, prompt, screenshot_b64)
        elif config.provider in ("azure_foundry", "azure_foundry_openai"):
            resp = await _azure_foundry_openai(config, prompt, screenshot_b64)
        elif config.provider == "azure_foundry_anthropic":
            resp = await _azure_foundry_anthropic(config, prompt, screenshot_b64)
        elif config.provider == "openrouter":
            resp = await _openrouter(config, prompt, screenshot_b64)
        elif config.provider == "bedrock":
            resp = await _bedrock(config, prompt, screenshot_b64)
        elif config.provider == "bedrock_mantle":
            resp = await _openai_responses(config, prompt, screenshot_b64)
        else:
            resp = await _openai_compat(config, prompt, screenshot_b64)

        usage = _last_call_tokens_var.get()
        if usage:
            actual_total = usage["input"] + usage["output"]
            await limiter.reconcile(total_estimated, actual_total)
        else:
            actual_total = total_estimated
            await limiter.reconcile(total_estimated, total_estimated)

        if slept:
            _emit_rate_limit_cleared(config.model, actual_total)

        return resp
    except Exception:
        await limiter.reconcile(total_estimated, 0)
        raise


async def plain_completion(config: LLMConfig, prompt: str) -> str:
    """Send a plain text prompt and return the raw response text."""
    return await _call(config, prompt, None)


async def stream_chat_completion(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream a chat completion from the configured LLM provider in real-time."""
    if config.provider == "anthropic":
        import anthropic as _ant

        client = _ant.AsyncAnthropic(api_key=config.api_key, **_llm_client_kwargs())
        formatted_messages = []
        for m in messages:
            if m.get("role") in ("user", "assistant"):
                formatted_messages.append({"role": m["role"], "content": m["content"]})

        async with client.messages.stream(
            model=config.model,
            max_tokens=config.max_tokens,
            **(
                {"temperature": config.temperature}
                if config.temperature is not None
                else {}
            ),
            system=[{"type": "text", "text": system_message}],
            messages=formatted_messages,
        ) as stream:
            async for event in stream:
                if event.type == "text":
                    yield event.text

    elif config.provider == "bedrock":
        import threading

        converse_messages = []
        for m in messages:
            if m.get("role") in ("user", "assistant"):
                converse_messages.append(
                    {"role": m["role"], "content": [{"text": m["content"]}]}
                )
        system_list = [{"text": system_message}]

        if config.api_key:
            model_id = quote(config.model, safe="")
            infer_cfg: dict = {"maxTokens": config.max_tokens}
            if config.temperature is not None:
                infer_cfg["temperature"] = config.temperature
            url = f"{(config.base_url or '').rstrip('/')}/model/{model_id}/converse-stream"
            payload = {
                "messages": converse_messages,
                "system": system_list,
                "inferenceConfig": infer_cfg,
            }
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            try:
                async with _make_llm_http_client(timeout=120) as client:
                    async with client.stream(
                        "POST", url, headers=headers, json=payload
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith("data:"):
                                line = line[5:].strip()
                            try:
                                chunk = json.loads(line)
                                if "contentBlockDelta" in chunk:
                                    delta = chunk["contentBlockDelta"]["delta"]
                                    if "text" in delta:
                                        yield delta["text"]
                            except Exception:
                                pass
            except Exception as e:
                log.exception("Error in Bedrock API key stream completion")
                raise RuntimeError(f"Bedrock API key stream failed: {e}") from e
        else:
            _proxy_url = _llm_proxy_var.get()
            _model = config.model
            _messages = converse_messages
            _system = system_list
            _infer: dict = {"maxTokens": config.max_tokens}
            if config.temperature is not None:
                _infer["temperature"] = config.temperature
            _endpoint = config.base_url or None

            def _run_converse_stream():
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
                _boto_cfg = (
                    _BotocoreConfig(proxies={"http": _proxy_url, "https": _proxy_url})
                    if _proxy_url
                    else None
                )
                client = session.client(
                    "bedrock-runtime",
                    region_name=region,
                    endpoint_url=_endpoint,
                    verify=not _proxy_url,
                    **{"config": _boto_cfg} if _boto_cfg else {},
                )
                return client.converse_stream(
                    modelId=_model,
                    system=_system,
                    messages=_messages,
                    inferenceConfig=_infer,
                )

            q = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def _producer():
                try:
                    res = _run_converse_stream()
                    stream = res.get("stream")
                    if stream:
                        for chunk in stream:
                            if "contentBlockDelta" in chunk:
                                delta = chunk["contentBlockDelta"]["delta"]
                                if "text" in delta:
                                    loop.call_soon_threadsafe(
                                        q.put_nowait, ("text", delta["text"])
                                    )
                    loop.call_soon_threadsafe(q.put_nowait, ("done", None))
                except Exception as e:
                    loop.call_soon_threadsafe(q.put_nowait, ("error", e))

            thread = threading.Thread(target=_producer, daemon=True)
            thread.start()

            while True:
                item_type, val = await q.get()
                if item_type == "text":
                    yield val
                elif item_type == "done":
                    break
                elif item_type == "error":
                    raise RuntimeError(f"Bedrock SDK stream failed: {val}") from val

    elif config.provider == "bedrock_mantle":
        # Mantle uses the OpenAI Responses API (gpt-5.x are Responses-only).
        client = _make_bedrock_mantle_client(config)
        r_input = [
            {"type": "message", "role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]
        try:
            stream = await _create_response(
                client,
                _mantle_response_kwargs(
                    config, input=r_input, instructions=system_message, stream=True
                ),
            )
            async for event in stream:
                if getattr(event, "type", None) == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if delta:
                        yield delta
        except Exception as e:
            log.exception("Error in Bedrock Mantle responses stream")
            raise RuntimeError(f"Bedrock Mantle responses stream failed: {e}") from e

    else:
        from openai import AsyncOpenAI

        kwargs: dict = {"api_key": config.api_key or "not-needed"}
        if config.base_url:
            base = config.base_url.rstrip("/")
            if not base.endswith("/v1"):
                base += "/v1"
            kwargs["base_url"] = base
        kwargs.update(_llm_client_kwargs())
        client = AsyncOpenAI(**kwargs)

        formatted_messages = [{"role": "system", "content": system_message}]
        for m in messages:
            if m.get("role") in ("user", "assistant"):
                formatted_messages.append({"role": m["role"], "content": m["content"]})

        call_kwargs = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "messages": formatted_messages,
            "stream": True,
        }

        try:
            response = await client.chat.completions.create(**call_kwargs)
            async for chunk in response:
                if (
                    chunk.choices
                    and chunk.choices[0].delta
                    and chunk.choices[0].delta.content
                ):
                    yield chunk.choices[0].delta.content
        except Exception as e:
            log.exception("Error in OpenAI-compatible stream completion")
            raise RuntimeError(f"OpenAI-compatible stream failed: {e}") from e


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

    if not uses_reasoning_params and config.temperature is not None:
        kwargs["temperature"] = config.temperature
    return kwargs


async def _create_chat_completion(client: Any, kwargs: dict[str, Any]) -> Any:
    try:
        return await client.chat.completions.create(**kwargs)
    except Exception as exc:
        message = str(exc).lower()
        retry_kwargs = dict(kwargs)
        changed = False

        if "max_tokens" in retry_kwargs and (
            "max_tokens" in message or "max completion" in message
        ):
            retry_kwargs["max_completion_tokens"] = retry_kwargs.pop("max_tokens")
            changed = True
        if "temperature" in retry_kwargs and "temperature" in message:
            retry_kwargs.pop("temperature", None)
            changed = True
        if "tool_choice" in retry_kwargs and any(
            term in message
            for term in ("tool_choice", "tool choice", "thinking mode", "thinking_mode")
        ):
            retry_kwargs.pop("tool_choice", None)
            changed = True

        if not changed:
            raise
        return await client.chat.completions.create(**retry_kwargs)


def _extract_first_choice_text(resp: Any) -> str:
    choices = getattr(resp, "choices", None) or []
    if not choices:
        return ""
    return _extract_message_text(getattr(choices[0], "message", None))


async def _anthropic(
    config: LLMConfig, prompt: str, screenshot_b64: Optional[str]
) -> str:
    import anthropic as _ant

    client = _ant.AsyncAnthropic(api_key=config.api_key, **_llm_client_kwargs())
    content: list = []
    if screenshot_b64:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_b64,
                },
            }
        )
    content.append({"type": "text", "text": prompt})
    resp = await client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        **(
            {"temperature": config.temperature}
            if config.temperature is not None
            else {}
        ),
        messages=[{"role": "user", "content": content}],
    )
    _record_usage(
        config.model,
        getattr(resp.usage, "input_tokens", 0),
        getattr(resp.usage, "output_tokens", 0),
        cache_read_tokens=getattr(resp.usage, "cache_read_input_tokens", 0),
        cache_write_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0),
    )
    return "".join(_content_part_text(block) for block in (resp.content or [])).strip()


async def _google(config: LLMConfig, prompt: str, screenshot_b64: Optional[str]) -> str:
    from google import genai
    from google.genai import types

    _g_proxy = _llm_proxy_var.get()
    _g_http_opts: dict = {}
    if config.base_url:
        _g_http_opts["base_url"] = config.base_url
    _g_http_opts["httpx_async_client"] = httpx.AsyncClient(
        verify=_g_proxy is None,
        headers=_LLM_HEADERS,
        **({"proxy": _g_proxy} if _g_proxy else {}),
    )
    client = genai.Client(api_key=config.api_key, http_options=_g_http_opts)
    parts: list = []
    if screenshot_b64:
        parts.append(
            types.Part.from_bytes(
                data=base64.b64decode(screenshot_b64),
                mime_type="image/png",
            )
        )
    parts.append(prompt)

    resp = await client.aio.models.generate_content(
        model=config.model,
        contents=parts,
        config=types.GenerateContentConfig(
            max_output_tokens=config.max_tokens,
            **(
                {"temperature": config.temperature}
                if config.temperature is not None
                else {}
            ),
        ),
    )
    _record_google_usage(config.model, getattr(resp, "usage_metadata", None))
    return resp.text or ""


async def _openai_compat(
    config: LLMConfig, prompt: str, screenshot_b64: Optional[str]
) -> str:
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
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
            },
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
    _u_cached = (
        getattr(getattr(_u, "prompt_tokens_details", None), "cached_tokens", 0)
        if _u
        else 0
    )
    _record_usage(
        config.model,
        getattr(_u, "prompt_tokens", 0) if _u else 0,
        getattr(_u, "completion_tokens", 0) if _u else 0,
        cache_read_tokens=_u_cached,
    )
    return _extract_first_choice_text(resp)


# ── Bedrock Mantle (OpenAI Responses API) ─────────────────────────────────────
# Mantle's frontier OpenAI models (gpt-5.x) are served only via the Responses
# API (/v1/responses), not Chat Completions, so all Mantle traffic uses Responses.


def _ant_tools_to_responses(tools: list[dict]) -> list[dict]:
    """Anthropic-style tool specs → OpenAI Responses function tools (flat shape)."""
    return [
        {
            "type": "function",
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("input_schema", {"type": "object"}),
        }
        for t in tools
    ]


def _ant_messages_to_responses(messages: list[dict]) -> list[dict]:
    """Translate Anthropic-format history into a Responses ``input`` item list.

    Text turns become ``message`` items; assistant ``tool_use`` blocks become
    ``function_call`` items and user ``tool_result`` blocks become
    ``function_call_output`` items, keyed on the same ``call_id``.
    """
    items: list[dict] = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if isinstance(content, str):
            items.append({"type": "message", "role": role, "content": content})
            continue
        if role == "user":
            text_parts: list[str] = []
            for blk in content:
                btype = blk.get("type")
                if btype == "text":
                    text_parts.append(blk.get("text") or "")
                elif btype == "tool_result":
                    rc = blk.get("content") or ""
                    items.append(
                        {
                            "type": "function_call_output",
                            "call_id": blk.get("tool_use_id") or "",
                            "output": rc if isinstance(rc, str) else json.dumps(rc),
                        }
                    )
            joined = " ".join(p for p in text_parts if p)
            if joined:
                items.append({"type": "message", "role": "user", "content": joined})
        elif role == "assistant":
            text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
            joined = " ".join(p for p in text_parts if p)
            if joined:
                items.append(
                    {"type": "message", "role": "assistant", "content": joined}
                )
            for blk in content:
                if blk.get("type") == "tool_use":
                    items.append(
                        {
                            "type": "function_call",
                            "call_id": blk.get("id") or "",
                            "name": blk.get("name") or "",
                            "arguments": json.dumps(blk.get("input") or {}),
                        }
                    )
    return items


def _is_mantle_reasoning_model(model: str) -> bool:
    """True for Mantle reasoning models (gpt-5.x, o-series) that reject temperature.

    Mantle ids carry a vendor prefix (e.g. ``openai.gpt-5.5``), which the slash-based
    ``_model_needs_reasoning_params`` split doesn't catch — so match the substring too.
    """
    return "gpt-5" in (model or "").lower() or _model_needs_reasoning_params(model)


def _mantle_response_kwargs(
    config: LLMConfig,
    *,
    input: Any,
    instructions: Optional[str] = None,
    tools: Optional[list[dict]] = None,
    stream: bool = False,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": config.model,
        "input": input,
        "max_output_tokens": config.max_tokens,
    }
    if instructions is not None:
        kwargs["instructions"] = instructions
    # Reasoning models (gpt-5.x / o-series) reject a custom temperature; skip it
    # for them rather than pay a failed round-trip (the retry below is a backstop).
    if config.temperature is not None and not _is_mantle_reasoning_model(config.model):
        kwargs["temperature"] = config.temperature
    if tools is not None:
        kwargs["tools"] = tools
    if stream:
        kwargs["stream"] = True
    return kwargs


async def _create_response(client: Any, kwargs: dict[str, Any]) -> Any:
    """Call responses.create, retrying once without params the model rejects."""
    try:
        return await client.responses.create(**kwargs)
    except Exception as exc:
        message = str(exc).lower()
        retry = dict(kwargs)
        changed = False
        if "temperature" in retry and "temperature" in message:
            retry.pop("temperature", None)
            changed = True
        if "tool_choice" in retry and (
            "tool_choice" in message or "tool choice" in message
        ):
            retry.pop("tool_choice", None)
            changed = True
        if not changed:
            raise
        return await client.responses.create(**retry)


def _record_responses_usage(config: LLMConfig, resp: Any) -> None:
    usage = getattr(resp, "usage", None)
    _record_usage(
        config.model,
        getattr(usage, "input_tokens", 0) if usage else 0,
        getattr(usage, "output_tokens", 0) if usage else 0,
        cache_read_tokens=(
            getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0)
            if usage
            else 0
        ),
    )


def _extract_responses_text(resp: Any) -> str:
    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    parts: list[str] = []
    for item in getattr(resp, "output", None) or []:
        if getattr(item, "type", None) == "message":
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "output_text":
                    value = getattr(part, "text", None)
                    if isinstance(value, str):
                        parts.append(value)
    return "".join(parts).strip()


async def _openai_responses(
    config: LLMConfig, prompt: str, screenshot_b64: Optional[str]
) -> str:
    client = _make_bedrock_mantle_client(config)
    if screenshot_b64:
        r_input: Any = [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{screenshot_b64}",
                    },
                ],
            }
        ]
    else:
        r_input = prompt
    resp = await _create_response(
        client, _mantle_response_kwargs(config, input=r_input)
    )
    _record_responses_usage(config, resp)
    return _extract_responses_text(resp)


async def _openrouter(
    config: LLMConfig, prompt: str, screenshot_b64: Optional[str]
) -> str:
    from openai import AsyncOpenAI

    _or_kwargs: dict = {
        "api_key": config.api_key,
        "base_url": OPENROUTER_BASE_URL,
        **_llm_client_kwargs(),
    }
    client = AsyncOpenAI(**_or_kwargs)

    if screenshot_b64:
        msg_content: object = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
            },
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
    _u_cached = (
        getattr(getattr(_u, "prompt_tokens_details", None), "cached_tokens", 0)
        if _u
        else 0
    )
    _record_usage(
        config.model,
        getattr(_u, "prompt_tokens", 0) if _u else 0,
        getattr(_u, "completion_tokens", 0) if _u else 0,
        cache_read_tokens=_u_cached,
    )
    return _extract_first_choice_text(resp)


async def _azure_openai(
    config: LLMConfig, prompt: str, screenshot_b64: Optional[str]
) -> str:
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
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
            },
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
    _u_cached = (
        getattr(getattr(_u, "prompt_tokens_details", None), "cached_tokens", 0)
        if _u
        else 0
    )
    _record_usage(
        config.model,
        getattr(_u, "prompt_tokens", 0) if _u else 0,
        getattr(_u, "completion_tokens", 0) if _u else 0,
        cache_read_tokens=_u_cached,
    )
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
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
            },
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
    _u_cached = (
        getattr(getattr(_u, "prompt_tokens_details", None), "cached_tokens", 0)
        if _u
        else 0
    )
    _record_usage(
        config.model,
        getattr(_u, "prompt_tokens", 0) if _u else 0,
        getattr(_u, "completion_tokens", 0) if _u else 0,
        cache_read_tokens=_u_cached,
    )
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
    content: list[dict[str, Any]] = []
    if screenshot_b64:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_b64,
                },
            }
        )
    content.append({"type": "text", "text": prompt})

    payload: dict[str, Any] = {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    if config.temperature is not None:
        payload["temperature"] = config.temperature
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
    _record_usage(
        config.model,
        _af_u.get("input_tokens", 0),
        _af_u.get("output_tokens", 0),
        cache_read_tokens=_af_u.get("cache_read_input_tokens", 0),
        cache_write_tokens=_af_u.get("cache_creation_input_tokens", 0),
    )
    return "".join(
        _content_part_text(block) for block in (data.get("content") or [])
    ).strip()


def _extract_bedrock_text(data: dict[str, Any]) -> str:
    content = ((data.get("output") or {}).get("message") or {}).get("content") or []
    if not isinstance(content, list):
        return ""
    return "".join(
        part.get("text", "") for part in content if isinstance(part, dict)
    ).strip()


def _bedrock_region_from_url(base_url: str) -> str:
    match = re.search(r"bedrock-runtime[.-]([a-z0-9-]+)\.", base_url)
    return match.group(1) if match else "us-east-1"


# SigV4 signing name for the bedrock-mantle endpoint.  AWS signs Mantle requests
# (like the bedrock-runtime OpenAI-compatible endpoint) under the "bedrock"
# service name — NOT "bedrock-mantle".  Confirmed by the AWS SigV4 curl example
# (`--aws-sigv4 "aws:amz:<region>:bedrock"`) and litellm's Bedrock signer.
_BEDROCK_MANTLE_SIGV4_SERVICE = "bedrock"


def _bedrock_mantle_region() -> str:
    """Default region for Bedrock Mantle when no base URL is configured."""
    return (
        os.getenv("BEDROCK_MANTLE_REGION")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-east-2"
    )


def _bedrock_mantle_is_frontier_model(model: str) -> bool:
    """Frontier OpenAI models (gpt-5.x) are served on Mantle's ``/openai/v1`` path.

    The gpt-oss and other models use the plain ``/v1`` path instead — confirmed by
    the AWS launch blog and the OpenAI Bedrock cookbook.
    """
    return "gpt-5" in (model or "").lower()


def _bedrock_mantle_base_url(config: LLMConfig) -> str:
    """Resolve the OpenAI Responses base URL for a Bedrock Mantle config.

    The path is model-dependent: frontier ``openai.gpt-5.x`` models use
    ``/openai/v1`` while gpt-oss and others use ``/v1`` — so a single provider can
    serve both. An explicit ``base_url`` keeps its host (and region) but the path
    suffix is normalised to match the selected model. When blank, the region comes
    from ``BEDROCK_MANTLE_REGION``/``AWS_REGION``/``AWS_DEFAULT_REGION`` (default
    ``us-east-2``).
    """
    suffix = "/openai/v1" if _bedrock_mantle_is_frontier_model(config.model) else "/v1"
    if config.base_url:
        base = config.base_url.rstrip("/")
        # Drop any path suffix the user supplied, then re-apply the one this model
        # needs, so switching models on the same provider routes correctly.
        for known in ("/openai/v1", "/v1"):
            if base.endswith(known):
                base = base[: -len(known)]
                break
        return f"{base}{suffix}"
    return f"https://bedrock-mantle.{_bedrock_mantle_region()}.api.aws{suffix}"


def _bedrock_mantle_region_from_url(base_url: str) -> str:
    """Region used for SigV4 signing — must match the endpoint host's region."""
    match = re.search(r"bedrock-mantle\.([a-z0-9-]+)\.api\.aws", base_url)
    return match.group(1) if match else _bedrock_mantle_region()


class _BedrockMantleSigV4Auth(httpx.Auth):
    """httpx auth flow that SigV4-signs Bedrock Mantle requests with AWS creds.

    Lets the OpenAI SDK reach the OpenAI-compatible Mantle endpoint using the
    default boto3 credential chain (environment, shared profile, SSO, IAM role,
    instance/task role) instead of a Bedrock API key — mirroring the boto3 path
    of the Bedrock Runtime provider.  The refreshable credentials object is
    resolved once (lazily) and re-frozen per request so role/STS credentials
    rotate before they expire.
    """

    requires_request_body = True

    def __init__(self, region: str, profile: str | None = None):
        self._region = region
        self._profile = profile
        self._credentials = None

    def _resolve_credentials(self):
        if self._credentials is None:
            import boto3

            session = (
                boto3.Session(profile_name=self._profile)
                if self._profile
                else boto3.Session()
            )
            creds = session.get_credentials()
            if creds is None:
                raise RuntimeError(
                    "No AWS credentials found for Bedrock Mantle. Provide an "
                    "Amazon Bedrock API key, or configure AWS credentials "
                    "(environment, shared profile, SSO, or an IAM role)."
                )
            self._credentials = creds
        return self._credentials

    def _sign(self, request: httpx.Request) -> None:
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        frozen = self._resolve_credentials().get_frozen_credentials()
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers={
                "Content-Type": request.headers.get("Content-Type", "application/json")
            },
        )
        SigV4Auth(frozen, _BEDROCK_MANTLE_SIGV4_SERVICE, self._region).add_auth(
            aws_request
        )
        # Copy the signed headers (Authorization, X-Amz-Date, X-Amz-Security-Token)
        # onto the outgoing request, replacing the SDK's placeholder Bearer header.
        for key, value in aws_request.headers.items():
            request.headers[key] = value

    def sync_auth_flow(self, request: httpx.Request):
        self._sign(request)
        yield request

    async def async_auth_flow(self, request: httpx.Request):
        # botocore credential resolution / signing is synchronous and may touch
        # the filesystem or IMDS on first use; keep it off the event loop.
        await asyncio.get_running_loop().run_in_executor(None, self._sign, request)
        yield request


def _make_bedrock_mantle_client(config: LLMConfig):
    """Build an AsyncOpenAI client for Bedrock Mantle.

    With an API key, send it as a Bearer token (default OpenAI SDK behaviour).
    Without one, fall back to AWS credentials by SigV4-signing each request — the
    same key-or-boto3 split the Bedrock Runtime provider uses.
    """
    from openai import AsyncOpenAI

    base_url = _bedrock_mantle_base_url(config)
    # A Mantle project id is sent as the OpenAI-Project header (the SDK's
    # `project=` param) so usage is attributed to that project for cost tracking.
    project_id = getattr(config, "project_id", None) or None
    project_kwargs = {"project": project_id} if project_id else {}
    if config.api_key:
        return AsyncOpenAI(
            api_key=config.api_key,
            base_url=base_url,
            **project_kwargs,
            **_llm_client_kwargs(),
        )

    proxy = _llm_proxy_var.get()
    signer = _BedrockMantleSigV4Auth(
        region=_bedrock_mantle_region_from_url(base_url),
        profile=os.getenv("AWS_PROFILE"),
    )
    http_client = httpx.AsyncClient(
        verify=proxy is None,
        headers=_LLM_HEADERS,
        auth=signer,
        **({"proxy": proxy} if proxy else {}),
    )
    return AsyncOpenAI(
        api_key="not-needed",
        base_url=base_url,
        http_client=http_client,
        **project_kwargs,
    )


async def _bedrock(
    config: LLMConfig, prompt: str, screenshot_b64: Optional[str]
) -> str:
    if config.api_key and not config.base_url:
        raise ValueError(
            "Amazon Bedrock Runtime endpoint is required when using an API key"
        )

    content: list[dict[str, Any]] = []
    if screenshot_b64:
        content.append(
            {
                "image": {
                    "format": "png",
                    "source": {"bytes": screenshot_b64},
                }
            }
        )
    content.append({"text": prompt})

    _infer_cfg: dict[str, Any] = {"maxTokens": config.max_tokens}
    if config.temperature is not None:
        _infer_cfg["temperature"] = config.temperature
    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": content}],
        "inferenceConfig": _infer_cfg,
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
            _boto_cfg = (
                _BotocoreConfig(proxies={"http": _proxy_url, "https": _proxy_url})
                if _proxy_url
                else None
            )
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
        _record_usage(
            config.model,
            _bd_u.get("inputTokens", 0),
            _bd_u.get("outputTokens", 0),
            cache_read_tokens=_bd_u.get("cacheReadInputTokens", 0),
            cache_write_tokens=_bd_u.get("cacheWriteInputTokens", 0),
        )
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
    _record_usage(
        config.model,
        _bd_u2.get("inputTokens", 0),
        _bd_u2.get("outputTokens", 0),
        cache_read_tokens=_bd_u2.get("cacheReadInputTokens", 0),
        cache_write_tokens=_bd_u2.get("cacheWriteInputTokens", 0),
    )
    return _extract_bedrock_text(_resp_data)


# ── Scanner LLM functions ─────────────────────────────────────────────────────


def _build_users_section(users: list[dict] | None) -> str:
    if not users:
        return ""
    lines = [
        "Available test users:",
        'Use the "as_user" field with one of these usernames to send a probe authenticated as that user.',
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
            user_note = f"\n  • Set 'as_user' on IDOR probes to test cross-user access: use {usernames}."
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
            '  • HTML/script contexts: <script>alert(1)</script>, "><script>alert(1)</script>\n'
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
        applicable=", ".join(applicable_checks)
        if applicable_checks
        else "general checks only",
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
        return [
            p
            for p in probes
            if isinstance(p, dict) and p.get("type") in ("http", "form", "idor")
        ]
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
    max_concurrent_batches: int = 1,
) -> list[dict]:
    """Ask the LLM to analyse probe results and return a list of findings.

    on_batch_complete: optional async callable(turn_num, batch_size, batch_findings)
        called after each LLM batch completes.
    """
    if not results:
        return []

    batches = _chunk_probe_results(results)

    async def _analyse(turn_num: int, batch: list[str]) -> list[dict]:
        batch_findings = await _analyse_probe_batch(config, url, batch)
        if on_batch_complete is not None:
            await on_batch_complete(turn_num, len(batch), batch_findings)
        return batch_findings

    if max_concurrent_batches <= 1:
        batch_findings = [
            await _analyse(turn_num, batch)
            for turn_num, batch in enumerate(batches, start=1)
        ]
    else:
        semaphore = asyncio.Semaphore(max_concurrent_batches)

        async def _limited(turn_num: int, batch: list[str]) -> list[dict]:
            async with semaphore:
                return await _analyse(turn_num, batch)

        batch_findings = await asyncio.gather(*(
            _limited(turn_num, batch)
            for turn_num, batch in enumerate(batches, start=1)
        ))
    return [finding for batch in batch_findings for finding in batch]


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
    prompt = build_reporting_analyse_prompt(url, result_texts)
    raw = await _call(config, prompt, None)
    try:
        findings = parse_reporting_findings(raw or "")
        _capture_reporting_replay(
            config, url, result_texts, prompt, raw or "", findings
        )
        return findings
    except Exception as exc:
        _capture_reporting_replay(
            config, url, result_texts, prompt, raw or "", [], parse_error=str(exc)
        )
        log.warning(
            "analyse_probes: failed to extract findings from LLM response (%s). "
            "Raw response (first 500 chars): %r",
            exc,
            (raw or "")[:500],
        )
        return []


def build_reporting_analyse_prompt(
    url: str,
    result_texts: list[str],
    *,
    prompt_template: str | None = None,
) -> str:
    """Build the reporting/finding analysis prompt from replayable probe result text."""
    template = prompt_template or _ANALYSE_PROMPT
    return template.format(
        url=url,
        results="\n\n".join(result_texts),
    )


def parse_reporting_findings(raw: str) -> list[dict]:
    """Parse the reporting LLM response into the structured findings shape."""
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
    return [
        finding
        for finding in findings
        if isinstance(finding, dict) and required.issubset(finding)
    ]


def parse_reporting_finding(raw: str) -> dict:
    """Parse one report finding object from an LLM response."""
    finding = _extract_json(raw or "", expect=dict)
    if not isinstance(finding, dict):
        return {}
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
    return finding if required.issubset(finding) else {}


def build_reporting_writeup_prompt(
    *,
    source: str,
    base_url: str,
    finding: dict[str, Any],
    evidence: dict[str, Any],
    prompt_template: str | None = None,
) -> str:
    template = prompt_template or _WRITEUP_REPLAY_PROMPT
    return template.format(
        source=source,
        base_url=base_url,
        finding_json=json.dumps(finding, indent=2, ensure_ascii=False, default=str),
        evidence_json=json.dumps(evidence, indent=2, ensure_ascii=False, default=str),
    )


async def rewrite_finding_writeup(
    config: LLMConfig,
    *,
    source: str,
    base_url: str,
    finding_dict: dict[str, Any],
    evidence_dict: dict[str, Any],
) -> dict:
    """Rewrite a persisted finding's prose through the writeup prompt.

    Calls the LLM once with _WRITEUP_REPLAY_PROMPT and returns the parsed
    finding dict on success, or an empty dict if the response cannot be parsed.
    Does not invent evidence or create new findings — only improves wording.
    """
    prompt = build_reporting_writeup_prompt(
        source=source,
        base_url=base_url,
        finding=finding_dict,
        evidence=evidence_dict,
    )
    raw = await _call(config, prompt, None)
    return parse_reporting_finding(raw or "")


async def replay_reporting_writeup_capture(
    config: LLMConfig,
    capture: dict[str, Any],
    *,
    prompt_template: str | None = None,
) -> dict[str, Any]:
    """Replay one captured during-scan finding writeup through the reporting prompt."""
    if capture.get("schema") != REPORTING_REPLAY_SCHEMA:
        raise ValueError(
            f"unsupported reporting capture schema: {capture.get('schema')!r}"
        )
    finding = capture.get("finding")
    if not isinstance(finding, dict):
        raise ValueError("writeup capture must contain finding")
    evidence = capture.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    prompt = build_reporting_writeup_prompt(
        source=str(capture.get("source") or "unknown"),
        base_url=str(capture.get("base_url") or ""),
        finding=finding,
        evidence=evidence,
        prompt_template=prompt_template,
    )
    raw = await _call(config, prompt, None)
    parsed = parse_reporting_finding(raw or "")
    findings = [parsed] if parsed else []
    return {
        "schema": "aespa.reporting.replay.result.v1",
        "source_capture_schema": capture.get("schema"),
        "source_capture_id": capture.get("capture_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "url": str(capture.get("url") or finding.get("affected_url") or ""),
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_response": raw or "",
        "findings": findings,
    }


async def replay_reporting_capture(
    config: LLMConfig,
    capture: dict[str, Any],
    *,
    prompt_template: str | None = None,
    use_saved_prompt: bool = False,
) -> dict[str, Any]:
    """Replay one captured reporting prompt payload through the configured LLM."""
    if capture.get("schema") != REPORTING_REPLAY_SCHEMA:
        raise ValueError(
            f"unsupported reporting capture schema: {capture.get('schema')!r}"
        )
    url = str(capture.get("url") or "")
    result_texts = capture.get("result_texts")
    if (
        not url
        or not isinstance(result_texts, list)
        or not all(isinstance(x, str) for x in result_texts)
    ):
        raise ValueError("capture must contain url and result_texts")
    if use_saved_prompt and prompt_template is None:
        prompt = str(capture.get("prompt") or "")
        if not prompt:
            raise ValueError("capture does not contain a saved prompt")
    else:
        prompt = build_reporting_analyse_prompt(
            url, result_texts, prompt_template=prompt_template
        )
    raw = await _call(config, prompt, None)
    findings = parse_reporting_findings(raw or "")
    return {
        "schema": "aespa.reporting.replay.result.v1",
        "source_capture_schema": capture.get("schema"),
        "source_capture_id": capture.get("capture_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_response": raw or "",
        "findings": findings,
    }


def _capture_reporting_replay(
    config: LLMConfig,
    url: str,
    result_texts: list[str],
    prompt: str,
    raw_response: str,
    findings: list[dict],
    *,
    parse_error: str | None = None,
) -> None:
    try:
        from aespa.services import reporting_debug as reporting_debug_svc

        if not reporting_debug_svc.is_capture_enabled():
            return
        reporting_debug_svc.capture_reporting_batch(
            run_id=_run_id_var.get(),
            url=url,
            result_texts=result_texts,
            prompt=prompt,
            prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            llm={
                "provider": config.provider,
                "base_url": config.base_url,
                "model": config.model,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            },
            raw_response=raw_response,
            findings=findings,
            parse_error=parse_error,
        )
    except Exception as exc:
        log.warning("failed to write reporting replay capture: %s", exc)


# ── Site-level test plan ──────────────────────────────────────────────────────


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
        return [
            p
            for p in probes
            if isinstance(p, dict) and p.get("type") in ("http", "form")
        ]
    except Exception:
        return []


# ── Finding title normalisation ───────────────────────────────────────────────


async def normalize_finding_titles(
    config: "LLMConfig",
    existing_findings: list[
        dict
    ],  # [{"title": ..., "owasp_category": ..., "severity": ...}]
    new_findings: list[dict],  # raw finding dicts from analyse_probes
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
        + (
            f"\n     desc: {(f.get('description') or '')[:120]}"
            if f.get("description")
            else ""
        )
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


# ── LLM-directed (thinking) scan ─────────────────────────────────────────────


def select_wstg_skills(
    pages: list[dict],
    intel_items: list[dict],
    *,
    requires_auth: bool = False,
    base_url: str = "",
    login_url: str = "",
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
    login_url:
        The site's configured login URL, if any. A configured login URL is itself a
        credential endpoint, so it triggers the auth-robustness checks even when the
        login form sits at a non-standard path the URL-fragment match would miss.
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
        or any(frag in url for frag in _AUTH_PATH_FRAGMENTS for url in page_urls_lower)
        or "token_hint" in intel_kinds
    )
    if has_auth_pages:
        selected.update({"auth_bypass", "sessions"})
        if has_inputs:
            selected.add("csrf")

    # ── Credential endpoints → auth robustness ─────────────────────────────────
    # Weak password policy, rate-limiting, and lockout are only testable where
    # credentials are actually submitted (a login / registration / password form),
    # so gate this on credential-endpoint URLs — NOT the broad has_auth_pages,
    # which is true for any authenticated area (dashboards, /account, /admin).
    has_credential_endpoint = (
        bool(
            login_url.strip()
        )  # a configured login URL is itself a credential endpoint
        or any(
            frag in url
            for frag in _CREDENTIAL_PATH_FRAGMENTS
            for url in page_urls_lower
        )
    )
    if has_credential_endpoint:
        selected.add("auth_robustness")

    # ── Object references / IDOR ───────────────────────────────────────────────
    has_object_refs = (
        any(p.get("has_object_ref") for p in pages)
        or "id" in intel_kinds
        or any("/api/" in url for url in page_urls_lower)
        or any(
            part.isdigit() for url in page_urls_lower for part in url.split("/") if part
        )
    )
    if has_object_refs:
        selected.add("idor")

    # ── SSRF — URL-type input parameters or fetch-a-URL features ──────────────
    # SSRF often has no obvious url= parameter, so also look for feature fragments
    # (avatar/logo by URL, import/preview, webhook config, PDF/report export) in
    # parameter names and URLs — not just the canonical SSRF param-name list.
    _SSRF_FEATURE_FRAGMENTS = (
        "webhook",
        "callback",
        "redirect",
        "proxy",
        "import",
        "fetch",
        "preview",
        "unfurl",
        "avatar",
        "logo",
        "thumbnail",
        "screenshot",
        "/pdf",
        "/report",
        "/export",
        "/render",
        "remote",
    )
    has_ssrf_params = (
        any(key in _SSRF_PARAM_NAMES for key in intel_keys_lower)
        or any(val.startswith("http") for val in intel_values_lower)
        or any(
            any(frag in key for frag in _SSRF_FEATURE_FRAGMENTS)
            for key in intel_keys_lower
        )
        or any(
            any(frag in url for frag in _SSRF_FEATURE_FRAGMENTS)
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
    has_business_logic = any(p.get("has_business_logic") for p in pages) or any(
        frag in url
        for frag in (
            "/checkout",
            "/payment",
            "/order",
            "/cart",
            "/transfer",
            "/confirm",
            "/submit",
            "/approve",
        )
        for url in page_urls_lower
    )
    if has_business_logic:
        selected.add("workflow")

    # ── File upload surfaces ───────────────────────────────────────────────────
    has_file_upload = (
        "upload" in intel_kinds
        or any(
            frag in url
            for frag in ("/upload", "/file", "/attachment", "/import", "/media")
            for url in page_urls_lower
        )
        or any("upload" in key for key in intel_keys_lower)
        or any(
            val in ("file", "upload", "attachment", "multipart")
            for val in intel_values_lower
        )
    )
    if has_file_upload:
        selected.add("file_upload")

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
# wire format or the Bedrock Runtime toolConfig format.
AGENTIC_LOOP_PROVIDERS = frozenset(
    {
        "anthropic",
        "azure_foundry_anthropic",
        "bedrock",
        "bedrock_mantle",
        "openai",
        "openai_compatible",
        "openrouter",
        "azure_openai",
        "azure_foundry",
        "azure_foundry_openai",
        "google",
    }
)


def _with_anthropic_cache(
    messages: list[dict],
    tools: list[dict] | None,
) -> tuple[list[dict], list[dict] | None]:
    """Helper to copy messages and tools, and attach ephemeral cache points
    to the last item of each, avoiding in-place mutation of the caller's lists.
    """
    cached_messages = [dict(m) for m in messages]
    if cached_messages:
        last_msg = dict(cached_messages[-1])
        content = last_msg.get("content")
        if isinstance(content, str):
            content_list = [{"type": "text", "text": content}]
        elif isinstance(content, list):
            content_list = [dict(block) for block in content]
        else:
            content_list = []

        if content_list:
            # Attach cache_control to the last block in the content array
            content_list[-1] = {
                **content_list[-1],
                "cache_control": {"type": "ephemeral"},
            }
            last_msg["content"] = content_list
            cached_messages[-1] = last_msg

    cached_tools = None
    if tools is not None:
        cached_tools = [dict(t) for t in tools]
        if cached_tools:
            # Attach cache_control to the last tool definition
            cached_tools[-1] = {
                **cached_tools[-1],
                "cache_control": {"type": "ephemeral"},
            }

    return cached_messages, cached_tools


def _estimate_tools_call_tokens(system_message: str, messages: list[dict]) -> int:
    """Rough input-token estimate for an agentic (tool-using) call.

    The messages list is Anthropic-format; content is either a string or a list
    of blocks. We only need an order-of-magnitude figure to drive pacing, so flatten
    everything to text and reuse the same ~chars/4 heuristic as ``estimate_tokens``.
    """
    parts: list[str] = [system_message or ""]
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    # text / tool_result content / tool_use input — stringify cheaply.
                    parts.append(
                        str(
                            block.get("text")
                            or block.get("content")
                            or block.get("input")
                            or ""
                        )
                    )
        elif content is not None:
            parts.append(str(content))
    return estimate_tokens("\n".join(parts))


async def _call_with_tools(
    config: "LLMConfig",
    system_message: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> "tuple[list[dict], str, Any]":
    """Rate-limited entry point for an agentic (tool-using) LLM call.

    Paces through the same per-provider token bucket as the non-agentic ``_call``
    path so the configured ``max_tpm`` / ``max_rpm`` cover dynamic, API, SAST and
    ALICE scans too — not just page analysis. Emits a rate-limit notice into the
    active run's log the moment pacing begins, then dispatches to the per-provider
    implementation.
    """
    limiter = get_limiter_for_config(config)
    if limiter is None:
        return await _call_with_tools_impl(
            config, system_message, messages, tools=tools
        )

    estimated = _estimate_tools_call_tokens(system_message, messages) + (
        config.max_tokens or 4096
    )
    _last_call_tokens_var.set(None)
    slept = await limiter.acquire(
        estimated,
        on_wait=lambda wt: _emit_rate_limit_waiting(
            config.model, min(estimated, limiter.max_tokens), wt
        ),
    )
    try:
        result = await _call_with_tools_impl(
            config, system_message, messages, tools=tools
        )
        usage = _last_call_tokens_var.get()
        actual_total = (usage["input"] + usage["output"]) if usage else estimated
        await limiter.reconcile(estimated, actual_total)
        if slept:
            _emit_rate_limit_cleared(config.model, actual_total)
        return result
    except Exception:
        await limiter.reconcile(estimated, 0)
        raise


async def _call_with_tools_impl(
    config: "LLMConfig",
    system_message: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> "tuple[list[dict], str, Any]":
    """Call an LLM with tool definitions (per-provider dispatch).

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
        cached_messages, cached_tools = _with_anthropic_cache(messages, _active_tools)
        resp = await client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            **(
                {"temperature": config.temperature}
                if config.temperature is not None
                else {}
            ),
            system=[
                {
                    "type": "text",
                    "text": system_message,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=cached_tools,
            messages=cached_messages,
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
        _record_usage(
            config.model,
            getattr(resp.usage, "input_tokens", 0),
            getattr(resp.usage, "output_tokens", 0),
            cache_read_tokens=getattr(resp.usage, "cache_read_input_tokens", 0),
            cache_write_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0),
        )
        return blocks, resp.stop_reason or "end_turn", resp.content

    # ── Azure AI Foundry (Anthropic endpoint) ─────────────────────────────────
    if config.provider == "azure_foundry_anthropic":
        cached_messages, cached_tools = _with_anthropic_cache(messages, _active_tools)
        payload = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "system": [
                {
                    "type": "text",
                    "text": system_message,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "tools": cached_tools,
            "messages": cached_messages,
        }
        if config.temperature is not None:
            payload["temperature"] = config.temperature
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
        _record_usage(
            config.model,
            _cwt_u.get("input_tokens", 0),
            _cwt_u.get("output_tokens", 0),
            cache_read_tokens=_cwt_u.get("cache_read_input_tokens", 0),
            cache_write_tokens=_cwt_u.get("cache_creation_input_tokens", 0),
        )
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
                        "inputSchema": {
                            "json": t.get("input_schema", {"type": "object"})
                        },
                    }
                }
                for t in _active_tools
            ]
        }

        def _ant_msg_to_converse(msg: dict) -> dict:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, str):
                text = content.strip()
                return {
                    "role": role,
                    "content": [
                        {"text": text or "[No content was recorded for this turn.]"}
                    ],
                }
            cvt: list[dict] = []
            for blk in content or []:
                btype = blk.get("type")
                if btype == "text":
                    text = str(blk.get("text") or "").strip()
                    if text:
                        cvt.append({"text": text})
                elif btype == "tool_use":
                    cvt.append(
                        {
                            "toolUse": {
                                "toolUseId": blk.get("id") or "",
                                "name": blk.get("name") or "",
                                "input": blk.get("input") or {},
                            }
                        }
                    )
                elif btype == "tool_result":
                    result_content = blk.get("content") or ""
                    if isinstance(result_content, str):
                        tool_content = [
                            {
                                "text": result_content.strip()
                                or "[Tool completed without textual output.]"
                            }
                        ]
                    else:
                        tool_content = []
                        for result_block in result_content or []:
                            result_text = str(
                                result_block.get("text")
                                or (
                                    result_block.get("text", "")
                                    if result_block.get("type") == "text"
                                    else ""
                                )
                            ).strip()
                            if result_text:
                                tool_content.append({"text": result_text})
                            elif "json" in result_block:
                                tool_content.append({"json": result_block["json"]})
                        if not tool_content:
                            tool_content = [
                                {"text": "[Tool completed without textual output.]"}
                            ]
                    cvt.append(
                        {
                            "toolResult": {
                                "toolUseId": blk.get("tool_use_id") or "",
                                "content": tool_content,
                            }
                        }
                    )
                elif btype == "bedrock_reasoning":
                    reasoning_content = blk.get("reasoning_content")
                    if isinstance(reasoning_content, dict) and reasoning_content:
                        # Bedrock requires reasoning text/signatures to be replayed
                        # byte-for-byte in subsequent multi-turn requests.
                        cvt.append({"reasoningContent": reasoning_content})
            if not cvt:
                # Legacy checkpoints can contain an empty assistant turn when a
                # model returned reasoning-only or otherwise unsupported content.
                # Converse rejects Message.content=[] before the model is invoked.
                cvt.append({"text": "[No content was recorded for this turn.]"})
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

        # Cache the latest turn of the conversation history to enable prefix extension caching.
        if len(converse_messages) > 1:
            last_msg = converse_messages[-1]
            last_content = list(last_msg.get("content") or [])
            if not any("cachePoint" in blk for blk in last_content):
                last_content = last_content + [{"cachePoint": {"type": "default"}}]
            converse_messages[-1] = {**last_msg, "content": last_content}

        bedrock_transport: dict[str, Any] = {}
        if config.api_key:
            # Bearer-token path (SAML / federated credentials stored as api_key).
            # Uses the same HTTP endpoint as _bedrock() so SAML token users work.
            model_id = quote(config.model, safe="")
            _infer_agent: dict = {"maxTokens": config.max_tokens}
            if config.temperature is not None:
                _infer_agent["temperature"] = config.temperature
            url = f"{(config.base_url or '').rstrip('/')}/model/{model_id}/converse"
            payload: dict = {
                "messages": converse_messages,
                "system": system_list,
                "toolConfig": tool_config,
                "inferenceConfig": _infer_agent,
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
                response_headers = getattr(_resp, "headers", {}) or {}
                bedrock_transport = {
                    "http_status": getattr(_resp, "status_code", None),
                    "request_id": (
                        response_headers.get("x-amzn-requestid")
                        or response_headers.get("x-amz-request-id")
                    ),
                }
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
                _boto_cfg = (
                    _BotocoreConfig(proxies={"http": _proxy_url, "https": _proxy_url})
                    if _proxy_url
                    else None
                )
                client = session.client(
                    "bedrock-runtime",
                    region_name=region,
                    endpoint_url=config.base_url or None,
                    verify=not _proxy_url,
                    **{"config": _boto_cfg} if _boto_cfg else {},
                )
                _infer_converse: dict = {"maxTokens": config.max_tokens}
                if config.temperature is not None:
                    _infer_converse["temperature"] = config.temperature
                return client.converse(
                    modelId=config.model,
                    system=system_list,
                    messages=converse_messages,
                    toolConfig=tool_config,
                    inferenceConfig=_infer_converse,
                )

            loop = _asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _run_converse)
            response_metadata = data.get("ResponseMetadata") or {}
            bedrock_transport = {
                "http_status": response_metadata.get("HTTPStatusCode"),
                "request_id": response_metadata.get("RequestId"),
                "retry_attempts": response_metadata.get("RetryAttempts"),
            }
        stop_reason_raw = data.get("stopReason") or "end_turn"
        out_content = ((data.get("output") or {}).get("message") or {}).get(
            "content"
        ) or []
        blocks: list[dict] = []
        raw_content_ant: list[dict] = []
        for blk in out_content:
            if "reasoningContent" in blk:
                raw_content_ant.append(
                    {
                        "type": "bedrock_reasoning",
                        "reasoning_content": blk["reasoningContent"],
                    }
                )
            if "text" in blk:
                text = str(blk["text"] or "")
                if text:
                    normalized = {
                        "type": "text",
                        "id": None,
                        "name": None,
                        "input": None,
                        "text": text,
                    }
                    blocks.append(normalized)
                    raw_content_ant.append(normalized)
            elif "toolUse" in blk:
                tu = blk["toolUse"]
                normalized = {
                    "type": "tool_use",
                    "id": tu.get("toolUseId"),
                    "name": tu.get("name"),
                    "input": tu.get("input") or {},
                    "text": None,
                }
                blocks.append(normalized)
                raw_content_ant.append(normalized)
        _bdt_u = data.get("usage", {})
        _record_usage(
            config.model,
            _bdt_u.get("inputTokens", 0),
            _bdt_u.get("outputTokens", 0),
            cache_read_tokens=_bdt_u.get("cacheReadInputTokens", 0),
            cache_write_tokens=_bdt_u.get("cacheWriteInputTokens", 0),
        )
        if not blocks:
            # Preserve enough native response information to distinguish a
            # guardrail/context stop from a genuinely empty end turn.
            raw_content_ant.append(
                {
                    "type": "provider_diagnostic",
                    "provider": "bedrock",
                    "model": config.model,
                    "native_stop_reason": stop_reason_raw,
                    "content_block_types": [
                        next(iter(block), "unknown")
                        for block in out_content
                        if isinstance(block, dict)
                    ],
                    "usage": {
                        "input_tokens": _bdt_u.get("inputTokens", 0),
                        "output_tokens": _bdt_u.get("outputTokens", 0),
                        "cache_read_tokens": _bdt_u.get("cacheReadInputTokens", 0),
                        "cache_write_tokens": _bdt_u.get(
                            "cacheWriteInputTokens", 0
                        ),
                    },
                    "metrics": data.get("metrics") or {},
                    "transport": bedrock_transport,
                    "guardrail_trace_present": bool(data.get("trace")),
                }
            )
        return blocks, str(stop_reason_raw), raw_content_ant

    # ── Bedrock Mantle (OpenAI Responses API with function tools) ─────────────
    if config.provider == "bedrock_mantle":
        client = _make_bedrock_mantle_client(config)
        r_kwargs = _mantle_response_kwargs(
            config,
            input=_ant_messages_to_responses(messages),
            instructions=system_message,
            tools=_ant_tools_to_responses(_active_tools),
        )
        # Force a tool call unless disabled; if the model rejects forced tool
        # choice, _create_response retries once without it.
        if getattr(config, "force_tool_choice", True):
            r_kwargs["tool_choice"] = "required"
        resp = await _create_response(client, r_kwargs)

        blocks = []
        for item in getattr(resp, "output", None) or []:
            itype = getattr(item, "type", None)
            if itype == "message":
                for part in getattr(item, "content", None) or []:
                    if getattr(part, "type", None) == "output_text":
                        text_val = getattr(part, "text", None)
                        if text_val:
                            blocks.append(
                                {
                                    "type": "text",
                                    "id": None,
                                    "name": None,
                                    "input": None,
                                    "text": text_val,
                                }
                            )
            elif itype == "function_call":
                try:
                    inp = json.loads(getattr(item, "arguments", "") or "{}")
                except Exception:
                    inp = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": getattr(item, "call_id", None),
                        "name": getattr(item, "name", None),
                        "input": inp,
                        "text": None,
                    }
                )
        stop_reason = (
            "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        )
        _record_responses_usage(config, resp)
        return blocks, stop_reason, blocks  # store Anthropic-format in history

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
                text_blocks = [b for b in content if b.get("type") == "text"]
                if tool_results:
                    for tr in tool_results:
                        rc = tr.get("content") or ""
                        result.append(
                            {
                                "role": "tool",
                                "tool_call_id": tr.get("tool_use_id") or "",
                                "content": rc
                                if isinstance(rc, str)
                                else json.dumps(rc),
                            }
                        )
                elif text_blocks:
                    result.append(
                        {
                            "role": "user",
                            "content": " ".join(b.get("text", "") for b in text_blocks),
                        }
                    )
            elif role == "assistant":
                text_parts = [
                    b.get("text", "") for b in content if b.get("type") == "text"
                ]
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
        "openai",
        "openai_compatible",
        "openrouter",
        "azure_openai",
        "azure_foundry",
        "azure_foundry_openai",
    ):
        from openai import AsyncOpenAI

        client_kwargs: dict = {"api_key": config.api_key or "not-needed"}
        if config.provider == "openrouter":
            client_kwargs["base_url"] = OPENROUTER_BASE_URL
        elif config.provider in (
            "azure_openai",
            "azure_foundry",
            "azure_foundry_openai",
        ):
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
        model_lower = (config.model or "").lower()
        # Check if user explicitly disabled forcing tool choice, or if the model is a known reasoning model
        if not getattr(config, "force_tool_choice", True):
            pass
        elif (
            "r1" in model_lower
            or "reasoner" in model_lower
            or "thinking" in model_lower
        ):
            # Reasoning/thinking models do not support forced tool choice
            pass
        else:
            call_kwargs["tool_choice"] = "required"
        resp = await _create_chat_completion(oai_client, call_kwargs)
        choice = resp.choices[0]
        msg = choice.message
        refusal = getattr(msg, "refusal", None)
        if refusal:
            raise LLMRefusalError(f"LLM provider refusal: {refusal}")
        finish = getattr(choice, "finish_reason", None) or "stop"
        blocks = []
        if msg.content:
            blocks.append(
                {
                    "type": "text",
                    "id": None,
                    "name": None,
                    "input": None,
                    "text": msg.content,
                }
            )
        for tc in getattr(msg, "tool_calls", None) or []:
            try:
                inp = json.loads(tc.function.arguments)
            except Exception:
                inp = {}
            blocks.append(
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": inp,
                    "text": None,
                }
            )
        stop_reason = "tool_use" if finish == "tool_calls" else "end_turn"
        _oai_u = getattr(resp, "usage", None)
        _oai_cached = (
            getattr(getattr(_oai_u, "prompt_tokens_details", None), "cached_tokens", 0)
            if _oai_u
            else 0
        )
        _record_usage(
            config.model,
            getattr(_oai_u, "prompt_tokens", 0) if _oai_u else 0,
            getattr(_oai_u, "completion_tokens", 0) if _oai_u else 0,
            cache_read_tokens=_oai_cached,
        )
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
                            _ts = blk.get("thought_signature")
                            parts.append(
                                _gtypes.Part(
                                    function_call=_gtypes.FunctionCall(
                                        name=blk.get("name") or "",
                                        args=blk.get("input") or {},
                                    ),
                                    **(
                                        {"thought_signature": _ts}
                                        if _ts is not None
                                        else {}
                                    ),
                                )
                            )
                        elif btype == "tool_result":
                            rc = blk.get("content") or ""
                            parts.append(
                                _gtypes.Part(
                                    function_response=_gtypes.FunctionResponse(
                                        name=blk.get("tool_use_id") or "",
                                        response={"result": rc},
                                    )
                                )
                            )
                if parts:
                    result.append(_gtypes.Content(role=role, parts=parts))
            return result

        _g_proxy = _llm_proxy_var.get()
        _g_http_opts: dict = {}
        if config.base_url:
            _g_http_opts["base_url"] = config.base_url
        _g_http_opts["httpx_async_client"] = httpx.AsyncClient(
            verify=_g_proxy is None,
            headers=_LLM_HEADERS,
            **({"proxy": _g_proxy} if _g_proxy else {}),
        )
        g_client = genai.Client(api_key=config.api_key, http_options=_g_http_opts)
        g_tools = _ant_tools_to_gemini()
        g_contents = _ant_contents_to_gemini(messages)
        g_resp = await g_client.aio.models.generate_content(
            model=config.model,
            contents=g_contents,
            config=_gtypes.GenerateContentConfig(
                system_instruction=system_message,
                tools=g_tools,
                max_output_tokens=config.max_tokens,
                **(
                    {"temperature": config.temperature}
                    if config.temperature is not None
                    else {}
                ),
            ),
        )
        blocks = []
        for part in g_resp.candidates[0].content.parts if g_resp.candidates else []:
            if getattr(part, "text", None):
                blocks.append(
                    {
                        "type": "text",
                        "id": None,
                        "name": None,
                        "input": None,
                        "text": part.text,
                    }
                )
            elif getattr(part, "function_call", None):
                fc = part.function_call
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": fc.name,  # Gemini doesn't issue call IDs; use name
                        "name": fc.name,
                        "input": dict(fc.args) if fc.args else {},
                        "text": None,
                        "thought_signature": getattr(part, "thought_signature", None),
                    }
                )
        stop_reason = (
            "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        )
        _record_google_usage(
            config.model, getattr(g_resp, "usage_metadata", None)
        )
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
    after_tool_result=None,
    termination_check=None,
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

    after_tool_result: optional callable that may annotate a completed tool result.
    termination_check: optional callable returning a reason when an owning scan's
        progress policy requires a bounded automatic stop.

    Returns the summary string from the final ``done`` call (empty string otherwise).
    """
    resume_repair: dict[str, Any] | None = None
    if resume_messages is not None:
        messages = list(resume_messages)
        if messages and messages[-1].get("role") == "assistant":
            assistant_content = messages[-1].get("content")
            assistant_blocks = (
                assistant_content if isinstance(assistant_content, list) else []
            )
            interrupted_tools = [
                block
                for block in assistant_blocks
                if isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("id")
            ]
            if interrupted_tools:
                repair_content = [
                    {
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": (
                            "Tool execution was interrupted before a result was "
                            "checkpointed. Reassess the action before retrying it."
                        ),
                    }
                    for block in interrupted_tools
                ]
                repair_kind = "interrupted_tool_results"
            else:
                repair_content = [
                    {
                        "type": "text",
                        "text": (
                            "The previous model turn ended without a completed tool "
                            "exchange. Resume the assessment by calling exactly one tool."
                        ),
                    }
                ]
                repair_kind = "trailing_assistant_turn"
            messages.append({"role": "user", "content": repair_content})
            resume_repair = {
                "repair_kind": repair_kind,
                "interrupted_tool_count": len(interrupted_tools),
                "message_count_after_repair": len(messages),
            }
    else:
        messages: list[dict] = [{"role": "user", "content": initial_user_message}]
    tool_call_count = 0
    final_summary = ""
    consecutive_text_only_turns = 0

    if resume_repair and emit_fn:
        try:
            emit_fn(
                {
                    "type": "scanner_phase",
                    "phase": "llm_protocol",
                    "status": "warning",
                    "message": (
                        "Repaired resumed LLM checkpoint so the conversation ends "
                        "with a user message before the next provider call."
                    ),
                    "data": {
                        **resume_repair,
                        "provider": config.provider,
                        "model": config.model,
                    },
                }
            )
        except Exception:
            pass

    try:
        while True:
            if stop_check and stop_check():
                break
            if termination_check:
                try:
                    termination_reason = termination_check()
                except Exception as exc:
                    log.warning("thinking_agentic_loop: termination_check failed: %s", exc)
                    termination_reason = None
                if termination_reason:
                    final_summary = str(termination_reason)
                    if emit_fn:
                        try:
                            emit_fn(
                                {
                                    "type": "scanner_phase",
                                    "phase": "scan_stagnation",
                                    "status": "warning",
                                    "message": final_summary,
                                }
                            )
                        except Exception:
                            pass
                    break

            if emit_fn:
                try:
                    emit_fn(
                        {
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
                        }
                    )
                except Exception:
                    pass

            try:
                if emit_fn:
                    try:
                        emit_fn(
                            {
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
                            }
                        )
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
                            emit_fn(
                                {
                                    "type": "scanner_phase",
                                    "phase": "llm_heartbeat",
                                    "status": "pending",
                                    "message": (
                                        f"Step {_step_no}: waiting for LLM response "
                                        f"({_elapsed}s elapsed)\u2026"
                                    ),
                                }
                            )
                        except Exception:
                            pass
                content_blocks, stop_reason, raw_content = _llm_fut.result()
            except Exception as exc:
                log.error(
                    "thinking_agentic_loop: API error at step %d: %s",
                    tool_call_count + 1,
                    exc,
                )
                _is_refusal = _is_llm_refusal(exc)
                _exc_resp = getattr(exc, "response", None)
                _exc_code = (
                    _exc_resp.get("Error", {}).get("Code", "")
                    if isinstance(_exc_resp, dict)
                    else type(exc).__name__
                )
                _is_expired = (
                    "ExpiredToken" in _exc_code
                    or "ExpiredToken" in type(exc).__name__
                    or "expired" in str(exc).lower()
                )
                if emit_fn:
                    try:
                        if _is_expired:
                            _msg = (
                                f"Step {tool_call_count + 1}: AWS credentials have expired. "
                                "Please refresh your AWS credentials and resume the pentest."
                            )
                        elif _is_refusal:
                            _msg = (
                                f"Step {tool_call_count + 1}: LLM provider refused the "
                                f"scan request — {exc}"
                            )
                        else:
                            _msg = f"Step {tool_call_count + 1}: LLM API error — {exc}"
                        emit_fn(
                            {
                                "type": "scanner_phase",
                                "phase": "llm_response",
                                "status": "error",
                                "message": _msg,
                                "data": {
                                    "step": tool_call_count + 1,
                                    "error": str(exc),
                                },
                            }
                        )
                    except Exception:
                        pass
                if _is_refusal:
                    raise LLMRefusalError(
                        f"LLM provider refused the scan request at step "
                        f"{tool_call_count + 1}: {exc}"
                    ) from exc
                # A provider/serialization failure is not a successful terminal
                # condition. Propagate it so the owning scan is marked failed and
                # can be resumed from the final checkpoint.
                raise

            tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
            text_blocks = [
                b for b in content_blocks if b.get("type") == "text" and b.get("text")
            ]

            provider_diagnostics = [
                block
                for block in (raw_content if isinstance(raw_content, list) else [])
                if isinstance(block, dict)
                and block.get("type") == "provider_diagnostic"
            ]
            no_tool_attempt = consecutive_text_only_turns + 1
            no_usable_content = not tool_use_blocks and not text_blocks
            response_data = {
                "step": tool_call_count + 1,
                "raw_response": "\n".join(
                    b.get("text", "") for b in text_blocks
                )[:4000],
                "provider": config.provider,
                "model": config.model,
                "native_stop_reason": stop_reason,
                "tool_call_count": len(tool_use_blocks),
                "text_block_count": len(text_blocks),
                "no_usable_content": no_usable_content,
                "message_count": len(messages),
                "context_chars": len(json.dumps(messages, default=str)),
                "provider_diagnostics": provider_diagnostics,
            }
            if not tool_use_blocks:
                response_data["no_tool_retry"] = no_tool_attempt
                response_data["no_tool_retry_limit"] = 3

            if emit_fn:
                if tool_use_blocks:
                    action_label = ", ".join(b["name"] for b in tool_use_blocks)
                    response_status = "complete"
                    response_message = (
                        f"Step {tool_call_count + 1}: LLM → {action_label} "
                        f"(stop: {stop_reason})"
                    )
                else:
                    response_status = "warning"
                    response_kind = (
                        "empty response" if no_usable_content else "text-only response"
                    )
                    response_message = (
                        f"Step {tool_call_count + 1}: LLM returned {response_kind} "
                        f"without a tool call (native stop: {stop_reason}); "
                        f"retry {no_tool_attempt}/3"
                    )
                try:
                    emit_fn(
                        {
                            "type": "scanner_phase",
                            "phase": "llm_response",
                            "status": response_status,
                            "message": response_message,
                            "data": response_data,
                        }
                    )
                except Exception:
                    pass

            # Append the assistant turn to the growing conversation. Preserve a
            # non-empty marker when a provider returns no usable blocks so the
            # checkpoint itself remains valid for every messages API on resume.
            assistant_content = raw_content or [
                {
                    "type": "text",
                    "text": "[The model returned no usable content blocks.]",
                }
            ]
            messages.append({"role": "assistant", "content": assistant_content})

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
                    if emit_fn:
                        try:
                            emit_fn(
                                {
                                    "type": "scanner_phase",
                                    "phase": "llm_protocol",
                                    "status": "error",
                                    "message": (
                                        f"Step {tool_call_count + 1}: scan loop terminated "
                                        "after 3 consecutive responses without a tool call; "
                                        "the model did not call done."
                                    ),
                                    "data": {
                                        **response_data,
                                        "termination_reason": (
                                            "consecutive_no_tool_responses"
                                        ),
                                        "explicit_done": False,
                                    },
                                }
                            )
                        except Exception:
                            pass
                    break
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Your previous response did not call a tool, so no scan action "
                                    "was executed. Continue by calling exactly one tool now. Use "
                                    "http_request, browser, context_tool, write_finding, forge_jwt, "
                                    "decode_jwt, credential_check, or register_account for the next "
                                    "assessment step. Call done only if the assessment is genuinely "
                                    "complete and key attack areas have been covered."
                                ),
                            }
                        ],
                    }
                )
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
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": "Scan stopped by user.",
                        }
                    )
                    session_done = True
                    break

                if tool_name == "done":
                    final_summary = str(tool_input.get("summary") or "")
                    if done_check:
                        try:
                            done_ok, done_feedback = done_check(
                                tool_input, tool_call_count
                            )
                        except Exception as exc:
                            log.warning(
                                "thinking_agentic_loop: done_check failed: %s", exc
                            )
                            done_ok, done_feedback = True, ""
                        if not done_ok:
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": (
                                        done_feedback
                                        or "Assessment is not complete. Continue with one concrete tool call."
                                    ),
                                }
                            )
                            session_done = False
                            break
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": "Assessment complete.",
                        }
                    )
                    session_done = True
                    break

                try:
                    result_str = await tool_executor(
                        tool_name, tool_input, tool_call_count
                    )
                except Exception as exc:
                    log.warning(
                        "thinking_agentic_loop: tool %r step %d error: %s",
                        tool_name,
                        tool_call_count,
                        exc,
                    )
                    result_str = f"Tool execution error: {exc}"

                if after_tool_result:
                    try:
                        result_str = after_tool_result(
                            tool_name, tool_input, result_str, tool_call_count
                        )
                    except Exception as exc:
                        log.warning(
                            "thinking_agentic_loop: after_tool_result failed: %s", exc
                        )

                limit = 30000 if tool_name == "context_tool" else TOOL_RESULT_CHAR_LIMIT
                if len(result_str) > limit:
                    omitted = len(result_str) - limit
                    result_str = (
                        result_str[:limit]
                        + f"\n[{omitted} chars omitted — use context_tool/history_search for details]"
                    )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_str,
                    }
                )

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
                + ", ".join(
                    str(h.get("url") or "") for h in older[-8:] if h.get("url")
                )[:1000]
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
                if response_headers
                else "{}"
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
            "Test credentials (use these to authenticate):\n" + "\n".join(cred_lines)
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
    )
    if emit_fn:
        try:
            emit_fn(
                {
                    "type": "scanner_phase",
                    "phase": "llm_request",
                    "status": "pending",
                    "message": f"Step {current_step}: sending prompt ({len(prompt):,} chars) to LLM…",
                    "data": {"step": current_step, "prompt": prompt},
                }
            )
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
            correction_with_context = prompt + "\n\n---\n" + _THINKING_CORRECTION_PROMPT
            raw2 = await _call(config, correction_with_context, None)
            action = _normalize_thinking_action(_extract_action_json(raw2 or ""))
            log.info(
                "thinking_next_action: correction retry succeeded — action=%r",
                action.get("action"),
            )
        except Exception as exc2:
            log.warning(
                "thinking_next_action: retry also failed (%s). Ending assessment.", exc2
            )
            action = {
                "action": "done",
                "summary": "LLM did not return a valid action — assessment ended.",
            }
    if emit_fn:
        try:
            emit_fn(
                {
                    "type": "scanner_phase",
                    "phase": "llm_response",
                    "status": "complete",
                    "message": (
                        f"Step {current_step}: LLM → {action.get('action')}"
                        + (
                            f" {action.get('tool', '')}"
                            if action.get("action") == "tool"
                            else ""
                        )
                        + (
                            f" {action.get('method', '')} {action.get('url', '')}"
                            if action.get("action") == "http"
                            else ""
                        )
                        + (
                            f" {action.get('url', '')}"
                            if action.get("action") == "browser"
                            else ""
                        )
                        + (
                            f" {action.get('store_as', '')}"
                            if action.get("action") == "jwt"
                            else ""
                        )
                        + (
                            f" {action.get('url', '')}"
                            if action.get("action") == "credential_check"
                            else ""
                        )
                        + (
                            f" {action.get('title', '')}"
                            if action.get("action") == "finding_write"
                            else ""
                        )
                        + (
                            f": {action.get('hypothesis') or action.get('note', '')}"
                            if action.get("hypothesis") or action.get("note")
                            else ""
                        )
                    ),
                    "data": {
                        "step": current_step,
                        "raw_response": raw,
                        "action": action,
                    },
                }
            )
        except Exception:
            pass
    return action


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
        return [
            p
            for p in probes
            if isinstance(p, dict) and p.get("type") in ("http", "form")
        ]
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
        return {
            "verdict": "false_positive",
            "reasoning": "No validation probes reproduced the issue.",
        }
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
        return {
            "verdict": "confirmed",
            "reasoning": "Could not parse LLM validation response.",
        }
