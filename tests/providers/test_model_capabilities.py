from __future__ import annotations

import asyncio

from aespa.services.model_capabilities import (
    enrich_model_options,
    fuzzy_match_model,
    gemini_capability,
)


def test_openrouter_fuzzy_match_requires_a_clear_winner():
    catalog = [
        {
            "id": "openai/gpt-5.6",
            "reasoning": {"supported_efforts": ["low", "medium", "high"]},
        }
    ]
    result = fuzzy_match_model("gpt-5.6", catalog)
    assert result is not None
    assert result["supported_efforts"] == ["low", "medium", "high"]
    assert result["source"] == "openrouter"


def test_bedrock_model_id_matches_openrouter_model_id():
    catalog = [
        {
            "id": "anthropic/claude-3.7-sonnet",
            "reasoning": {"supported_efforts": ["low", "medium", "high"]},
        }
    ]
    result = fuzzy_match_model(
        "global.anthropic.claude-3-7-sonnet-20250219-v1:0", catalog
    )
    assert result is not None
    assert result["supported_efforts"] == ["low", "medium", "high"]


def test_gemini_preview_model_has_documented_levels_without_catalog_match():
    capability = gemini_capability("gemini-2.5-pro-preview-05-06")
    assert capability is not None
    assert capability["supported_efforts"] == ["low", "medium", "high"]


def test_native_empty_capability_blocks_openrouter_fallback():
    async def catalog():
        raise AssertionError("fallback should not be requested")

    result = asyncio.run(
        enrich_model_options(
            "openrouter",
            ["vendor/plain-model"],
            {"vendor/plain-model": {"supported_efforts": []}},
            catalog_fetcher=catalog,
        )
    )
    assert result["vendor/plain-model"]["supported_efforts"] == []


def test_native_context_window_is_preserved_without_reasoning_metadata():
    result = asyncio.run(
        enrich_model_options(
            "openai",
            ["gpt-context-model"],
            {"gpt-context-model": {"context_length": 131072}},
            catalog_fetcher=lambda: asyncio.sleep(0, result=[]),
        )
    )
    assert result["gpt-context-model"]["context_window_tokens"] == 131072


def test_unknown_capability_is_safe_default_only():
    result = asyncio.run(
        enrich_model_options(
            "openai_compatible",
            ["local/custom"],
            {},
            catalog_fetcher=lambda: asyncio.sleep(0, result=[]),
        )
    )
    assert "local/custom" not in result
