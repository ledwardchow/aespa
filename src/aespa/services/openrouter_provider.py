"""OpenRouter model discovery adapter."""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("aespa.llm.openrouter")

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


async def discover_models(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[str]:
    """Return model IDs available through the OpenRouter API."""
    url = (base_url or OPENROUTER_DEFAULT_BASE_URL).rstrip("/") + "/models"
    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    client_kwargs: dict[str, Any] = {"timeout": 10.0, "headers": headers}
    if proxy_url:
        client_kwargs["proxy"] = proxy_url

    async with httpx.AsyncClient(**client_kwargs) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        raw_models = payload.get("data") or []
        discovered = [
            m.get("id")
            for m in raw_models
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m.get("id")
        ]
        return discovered
