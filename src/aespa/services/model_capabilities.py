"""Discover and match model reasoning/thinking capabilities.

Providers do not expose one common capability API.  This module keeps the
wire format small and predictable: ``supported_efforts`` is a list of values
the UI can offer, while ``None`` means that no capability was discovered.
An empty list is meaningful and means the provider explicitly reported that
the model does not support selectable effort.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from difflib import SequenceMatcher
from typing import Any, Awaitable, Callable

import httpx

log = logging.getLogger("aespa.llm.capabilities")

EFFORT_ORDER = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
PROVIDER_CAPABILITY_STRATEGIES = {
    "anthropic": "provider_model_list_then_documented_family_then_openrouter",
    "factory_droid": "droid_sdk_model_metadata_then_openrouter",
    "github_copilot": "copilot_sdk_model_metadata_then_openrouter",
    "openai_codex": "codex_app_server_model_metadata_then_openrouter",
    "google_antigravity": "antigravity_cli_model_variants_then_openrouter",
    "openai": "openai_model_list_then_documented_family_then_openrouter",
    "openai_compatible": "endpoint_model_metadata_then_openrouter",
    "openrouter": "openrouter_model_metadata",
    "google": "google_model_list_then_documented_family_then_openrouter",
    "bedrock": "bedrock_model_list_then_documented_family_then_openrouter",
    "bedrock_mantle": "mantle_model_list_then_documented_family_then_openrouter",
    "azure_openai": "azure_openai_model_list_then_documented_family_then_openrouter",
    "azure_foundry": "azure_openai_model_list_then_documented_family_then_openrouter",
    "azure_foundry_openai": "azure_openai_model_list_then_documented_family_then_openrouter",
    "azure_foundry_anthropic": "anthropic_model_list_then_documented_family_then_openrouter",
}
_CATALOG_TTL_S = 24 * 60 * 60
_catalog_cache: tuple[float, list[dict[str, Any]]] | None = None
_catalog_lock = asyncio.Lock()


def normalize_efforts(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    found: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            value = (
                value.get("name")
                or value.get("effort")
                or value.get("reasoningEffort")
                or value.get("value")
            )
        if hasattr(value, "value"):
            value = value.value
        if not isinstance(value, str):
            continue
        value = value.strip().lower().replace("_", "-")
        aliases = {"x-high": "xhigh", "very-high": "xhigh", "default": "auto"}
        value = aliases.get(value, value)
        if value in EFFORT_ORDER:
            found.add(value)
    return [value for value in EFFORT_ORDER if value in found]


def _native_capability(raw: Any) -> dict[str, Any] | None:
    """Normalize common SDK/provider metadata while preserving empty values."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raw = {
            key: getattr(raw, key)
            for key in (
                "supported_reasoning_efforts",
                "supportedReasoningEfforts",
                "default_reasoning_effort",
                "defaultReasoningEffort",
                "reasoning",
                "context_length",
                "context_window",
                "contextWindow",
                "max_input_tokens",
                "inputTokenLimit",
            )
            if hasattr(raw, key)
        }
    context_window = None
    for key in (
        "context_window_tokens",
        "context_length",
        "contextWindow",
        "context_window",
        "max_input_tokens",
        "inputTokenLimit",
        "input_token_limit",
    ):
        candidate = raw.get(key)
        try:
            candidate = int(candidate)
        except (TypeError, ValueError):
            continue
        if candidate >= 1024:
            context_window = candidate
            break
    supported_key = next(
        (
            key
            for key in (
                "supported_efforts",
                "supported_reasoning_efforts",
                "supportedReasoningEfforts",
            )
            if key in raw
        ),
        None,
    )
    reasoning = raw.get("reasoning") if isinstance(raw.get("reasoning"), dict) else {}
    if supported_key is None and not reasoning:
        if "supported_parameters" in raw:
            params = raw.get("supported_parameters") or []
            if "reasoning" in params or "reasoning_effort" in params:
                # OpenRouter sometimes exposes support without enumerating levels.
                result = {
                    "supported_efforts": None,
                    "source": "native",
                    "confidence": "provider",
                }
                if context_window is not None:
                    result["context_window_tokens"] = context_window
                return result
            # OpenRouter includes supported_parameters for every model. If the
            # reasoning parameter is absent, this is authoritative unsupported.
            result = {
                "supported_efforts": [],
                "source": "native",
                "confidence": "provider",
            }
            if context_window is not None:
                result["context_window_tokens"] = context_window
            return result
        if context_window is not None:
            return {
                "context_window_tokens": context_window,
                "source": "native",
                "confidence": "provider",
            }
        return None
    raw_supported = (
        raw.get(supported_key) if supported_key else reasoning.get("supported_efforts")
    )
    if raw_supported is None and not reasoning:
        return None
    efforts = normalize_efforts(raw_supported) if raw_supported is not None else None
    default = (
        raw.get("default_effort")
        or raw.get("default_reasoning_effort")
        or raw.get("defaultReasoningEffort")
        or reasoning.get("default_effort")
    )
    if isinstance(default, dict):
        default = (
            default.get("name")
            or default.get("effort")
            or default.get("reasoningEffort")
            or default.get("value")
        )
    result: dict[str, Any] = {"source": "native", "confidence": "provider"}
    if context_window is not None:
        result["context_window_tokens"] = context_window
    if isinstance(raw.get("strategy"), str):
        result["strategy"] = raw["strategy"]
    result["supported_efforts"] = efforts
    if isinstance(default, str) and default.strip():
        result["default_effort"] = default.strip().lower()
    elif hasattr(default, "value"):
        result["default_effort"] = str(default.value).strip().lower()
    if "mandatory" in reasoning:
        result["mandatory"] = bool(reasoning["mandatory"])
    return result


def normalize_model_name(value: str) -> str:
    value = value.strip().lower()
    # AWS Bedrock prefixes inference profiles with a geography and appends a
    # version suffix to foundation model IDs (for example
    # ``global.anthropic.claude-3-7-sonnet-20250219-v1:0``).
    value = re.sub(r"^(?:global|us|eu|apac)\.", "", value)
    value = re.sub(r"^(?:google|anthropic|openai)[/.]", "", value)
    value = re.sub(r"-v\d+(?::\d+)?$", "", value)
    value = re.sub(r"^(?:openrouter/|azure/|accounts/[^/]+/models/)", "", value)
    value = re.sub(r"[:@](?:free|nitro|extended|thinking|online)$", "", value)
    value = re.sub(r"-preview-\d{2}-\d{2}$", "", value)
    value = re.sub(r"-\d{2}-\d{2}$", "", value)
    value = re.sub(r"[-_](?:latest|preview|instruct)$", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def gemini_capability(model: str) -> dict[str, Any] | None:
    """Return documented Gemini thinking levels for recognizable model IDs."""
    name = normalize_model_name(model)
    if not name.startswith("gemini-"):
        return None
    if "2-5" in name:
        return {
            "supported_efforts": ["low", "medium", "high"],
            "source": "native",
            "confidence": "documented",
        }
    if "3-1-pro" in name or "3-1-flash-lite" in name:
        return {
            "supported_efforts": ["low", "medium", "high"],
            "source": "native",
            "confidence": "documented",
        }
    if "3-pro" in name:
        return {
            "supported_efforts": ["low", "high"],
            "source": "native",
            "confidence": "documented",
        }
    if any(marker in name for marker in ("3-flash", "3-5-flash", "3-6-flash")):
        return {
            "supported_efforts": ["minimal", "low", "medium", "high"],
            "source": "native",
            "confidence": "documented",
        }
    return None


def documented_model_capability(api_format: str, model: str) -> dict[str, Any] | None:
    if api_format == "google":
        capability = gemini_capability(model)
        if capability is not None:
            capability["strategy"] = "documented_registry"
        return capability
    if api_format == "bedrock":
        name = normalize_model_name(model)
        if any(
            marker in name
            for marker in (
                "claude-opus-4-6",
                "claude-sonnet-4-6",
                "claude-opus-4-8",
                "claude-sonnet-4-8",
            )
        ):
            return {
                "supported_efforts": ["low", "medium", "high"],
                "source": "native",
                "confidence": "documented",
                "strategy": "documented_registry",
            }
    if api_format in {"anthropic", "azure_foundry_anthropic"}:
        name = normalize_model_name(model)
        if any(
            marker in name
            for marker in (
                "claude-opus-4-6",
                "claude-sonnet-4-6",
                "claude-opus-4-8",
                "claude-sonnet-4-8",
            )
        ):
            return {
                "supported_efforts": ["low", "medium", "high"],
                "source": "native",
                "confidence": "documented",
                "strategy": "documented_registry",
            }
    if api_format in {
        "openai",
        "azure_openai",
        "azure_foundry",
        "azure_foundry_openai",
        "bedrock_mantle",
    }:
        name = normalize_model_name(model)
        if name.startswith(("gpt-5", "o3", "o4")):
            return {
                "supported_efforts": ["low", "medium", "high"],
                "source": "native",
                "confidence": "documented",
                "strategy": "documented_registry",
            }
    return None


def _match_score(requested: str, candidate: str) -> float:
    left, right = normalize_model_name(requested), normalize_model_name(candidate)
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.91
    left_tokens, right_tokens = set(left.split("-")), set(right.split("-"))
    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    return max(overlap * 0.9, SequenceMatcher(None, left, right).ratio() * 0.82)


def fuzzy_match_model(
    model: str, catalog: list[dict[str, Any]]
) -> dict[str, Any] | None:
    scored = []
    for item in catalog:
        candidate = item.get("id")
        if not isinstance(candidate, str):
            continue
        capability = _native_capability(item)
        if capability is None:
            continue
        score = _match_score(model, candidate)
        scored.append((score, candidate, capability))
    if not scored:
        return None
    scored.sort(reverse=True, key=lambda entry: entry[0])
    best = scored[0]
    # Require an exact/strong match and reject ties: a wrong thinking menu is
    # worse than showing only the safe Default option.
    if best[0] < 0.72 or (len(scored) > 1 and best[0] - scored[1][0] < 0.04):
        return None
    result = dict(best[2])
    result.update(
        {
            "source": "openrouter",
            "matched_model": best[1],
            "confidence": round(best[0], 3),
        }
    )
    return result


async def fetch_openrouter_catalog(*, force: bool = False) -> list[dict[str, Any]]:
    global _catalog_cache
    now = time.monotonic()
    if (
        not force
        and _catalog_cache is not None
        and now - _catalog_cache[0] < _CATALOG_TTL_S
    ):
        return _catalog_cache[1]
    async with _catalog_lock:
        now = time.monotonic()
        if (
            not force
            and _catalog_cache is not None
            and now - _catalog_cache[0] < _CATALOG_TTL_S
        ):
            return _catalog_cache[1]
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else []
        catalog = [item for item in data if isinstance(item, dict)]
        _catalog_cache = (time.monotonic(), catalog)
        return catalog


async def enrich_model_options(
    api_format: str,
    models: list[str],
    native_capabilities: dict[str, Any] | None = None,
    *,
    catalog_fetcher: Callable[[], Awaitable[list[dict[str, Any]]]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return per-model metadata, using OpenRouter only when native metadata is absent."""
    native_capabilities = native_capabilities or {}
    result: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for model in models:
        native = _native_capability(native_capabilities.get(model))
        if native is not None:
            native.setdefault("strategy", "native_metadata")
            result[model] = native
        else:
            missing.append(model)
    if not missing:
        return result
    try:
        catalog = await (catalog_fetcher or fetch_openrouter_catalog)()
    except Exception as exc:
        log.debug("OpenRouter capability fallback unavailable: %s", exc)
        return result
    for model in missing:
        matched = fuzzy_match_model(model, catalog)
        if matched is not None:
            matched["strategy"] = "openrouter_fuzzy_fallback"
            result[model] = matched
    return result


def capability_strategy(api_format: str) -> str:
    return PROVIDER_CAPABILITY_STRATEGIES.get(
        api_format, "provider_metadata_then_openrouter"
    )


def validate_effort(
    capability: dict[str, Any] | None, effort: str | None
) -> str | None:
    if effort is None or not effort.strip():
        return None
    value = effort.strip().lower()
    if value not in EFFORT_ORDER:
        raise ValueError(f"Unknown reasoning level: {effort}")
    if capability is not None and capability.get("supported_efforts") is not None:
        if value not in capability["supported_efforts"]:
            raise ValueError(
                f"Reasoning level '{effort}' is not supported by this model"
            )
    return value
