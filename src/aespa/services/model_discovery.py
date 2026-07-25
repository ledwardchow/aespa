"""Provider-neutral model discovery helper for external LLM APIs."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

log = logging.getLogger("aespa.llm.model_discovery")


async def discover_openai_models(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[str]:
    """Return model IDs available from OpenAI or OpenAI-compatible endpoints."""
    url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/models"
    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    client_kwargs: dict[str, Any] = {"timeout": 10.0, "headers": headers}
    if proxy_url:
        client_kwargs["proxy"] = proxy_url

    async with httpx.AsyncClient(**client_kwargs) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json().get("data") or []
        ids = [
            m.get("id")
            for m in data
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m.get("id")
        ]
        return ids


async def discover_anthropic_models(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[str]:
    """Return model IDs available from the Anthropic API."""
    url = (base_url or "https://api.anthropic.com").rstrip("/") + "/v1/models"
    headers: dict[str, str] = {
        "Accept": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if api_key and api_key.strip():
        headers["x-api-key"] = api_key.strip()

    client_kwargs: dict[str, Any] = {"timeout": 10.0, "headers": headers}
    if proxy_url:
        client_kwargs["proxy"] = proxy_url

    async with httpx.AsyncClient(**client_kwargs) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json().get("data") or []
        ids = [
            m.get("id")
            for m in data
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m.get("id")
        ]
        return ids


async def discover_google_models(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[str]:
    """Return model IDs available from the Google Gemini API."""
    root_url = (base_url or "https://generativelanguage.googleapis.com").rstrip("/")
    url = f"{root_url}/v1beta/models"
    headers: dict[str, str] = {"Accept": "application/json"}
    params: dict[str, str] = {}
    if api_key and api_key.strip():
        params["key"] = api_key.strip()
        headers["x-goog-api-key"] = api_key.strip()

    client_kwargs: dict[str, Any] = {
        "timeout": 10.0,
        "headers": headers,
        "params": params,
    }
    if proxy_url:
        client_kwargs["proxy"] = proxy_url

    async with httpx.AsyncClient(**client_kwargs) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json().get("models") or []
        ids: list[str] = []
        for m in data:
            if not isinstance(m, dict):
                continue
            name = m.get("name") or ""
            if name.startswith("models/"):
                name = name[7:]
            methods = m.get("supportedGenerationMethods") or []
            if name and (not methods or "generateContent" in methods):
                ids.append(name)
        return ids


async def discover_bedrock_models(
    region_name: str | None = None,
) -> list[str]:
    """Return foundation model IDs and system-defined inference profile IDs available from AWS Bedrock."""

    def _fetch() -> list[str]:
        import re
        from urllib.parse import urlparse

        import boto3

        region = None
        endpoint_url = None

        val = (region_name or "").strip()
        if val.startswith(("http://", "https://")):
            endpoint_url = val
            parsed = urlparse(val)
            host = parsed.netloc or parsed.path
            match = re.search(r"([a-z]{2}-[a-z]+-\d+)", host)
            if match:
                region = match.group(1)
        elif val:
            region = val

        region = (
            region
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

        client_kwargs: dict[str, Any] = {"region_name": region}
        if endpoint_url:
            if "bedrock-runtime" in endpoint_url:
                control_url = endpoint_url.replace("bedrock-runtime", "bedrock")
                client_kwargs["endpoint_url"] = control_url
            else:
                client_kwargs["endpoint_url"] = endpoint_url

        client = boto3.client("bedrock", **client_kwargs)

        # 1. System-defined inference profiles (includes global.*, us.*, eu.*, apac.*)
        profiles: list[str] = []
        try:
            resp = client.list_inference_profiles(typeEquals="SYSTEM_DEFINED")
            summaries = resp.get("inferenceProfileSummaries") or []
            profiles = [
                p.get("inferenceProfileId")
                for p in summaries
                if isinstance(p, dict)
                and isinstance(p.get("inferenceProfileId"), str)
                and p.get("inferenceProfileId")
            ]
        except Exception as exc:
            log.warning("Bedrock list_inference_profiles failed: %s", exc)

        globals_list = [p for p in profiles if p.startswith("global.")]
        regionals_list = [p for p in profiles if not p.startswith("global.")]

        # 2. On-demand foundation models
        foundation: list[str] = []
        try:
            response = client.list_foundation_models(byInferenceType="ON_DEMAND")
            summaries = response.get("modelSummaries") or []
            foundation = [
                m.get("modelId")
                for m in summaries
                if isinstance(m, dict)
                and isinstance(m.get("modelId"), str)
                and m.get("modelId")
            ]
        except Exception as exc:
            log.warning("Bedrock list_foundation_models failed: %s", exc)

        combined: list[str] = []
        for item in globals_list + regionals_list + foundation:
            if item and item not in combined:
                combined.append(item)

        return combined

    return await asyncio.to_thread(_fetch)
