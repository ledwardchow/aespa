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
    records = await discover_openai_model_options(
        api_key=api_key, base_url=base_url, proxy_url=proxy_url
    )
    return [record["id"] for record in records]


async def discover_openai_model_options(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """Return raw OpenAI-compatible model records for capability inspection."""
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
        return [
            m
            for m in data
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m.get("id")
        ]


async def discover_bedrock_mantle_model_options(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """Return models exposed by Mantle's OpenAI-compatible Models API."""
    root = (base_url or "https://bedrock-mantle.us-east-2.api.aws").rstrip("/")
    for suffix in ("/openai/v1", "/v1"):
        if root.endswith(suffix):
            root = root[: -len(suffix)]
            break
    url = f"{root}/v1/models"
    headers: dict[str, str] = {"Accept": "application/json"}
    client_kwargs: dict[str, Any] = {"timeout": 10.0, "headers": headers}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    else:
        from aespa.services.llm import (
            _bedrock_mantle_region_from_url,
            _BedrockMantleSigV4Auth,
        )

        client_kwargs["auth"] = _BedrockMantleSigV4Auth(
            region=_bedrock_mantle_region_from_url(root),
            profile=os.getenv("AWS_PROFILE"),
        )
    if proxy_url:
        client_kwargs["proxy"] = proxy_url
        client_kwargs["verify"] = False

    async with httpx.AsyncClient(**client_kwargs) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else []
    return [
        item
        for item in (data or [])
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id")
    ]


async def discover_azure_openai_model_options(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """Discover Azure OpenAI/Foundry models using Azure's model-list route."""
    root = (base_url or "").rstrip("/")
    if "/openai/v1" in root:
        url = root + "/models"
    else:
        if not root.endswith("/openai"):
            root += "/openai"
        url = root + "/models?api-version=2024-10-21"
    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key and api_key.strip():
        headers["api-key"] = api_key.strip()
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    client_kwargs: dict[str, Any] = {"timeout": 10.0, "headers": headers}
    if proxy_url:
        client_kwargs["proxy"] = proxy_url
    async with httpx.AsyncClient(**client_kwargs) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    rows = (
        payload.get("data", payload.get("models", []))
        if isinstance(payload, dict)
        else []
    )
    return [row for row in rows if isinstance(row, dict) and row.get("id")]


async def discover_anthropic_models(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[str]:
    """Return model IDs available from the Anthropic API."""
    records = await discover_anthropic_model_options(
        api_key=api_key, base_url=base_url, proxy_url=proxy_url
    )
    return [record["id"] for record in records]


async def discover_anthropic_model_options(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """Return raw Anthropic model records for capability inspection."""
    root_url = (base_url or "https://api.anthropic.com").rstrip("/")
    url = root_url + "/models" if root_url.endswith("/v1") else root_url + "/v1/models"
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
        return [
            m
            for m in data
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m.get("id")
        ]


async def discover_google_models(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[str]:
    """Return model IDs available from the Google Gemini API."""
    records = await discover_google_model_options(
        api_key=api_key, base_url=base_url, proxy_url=proxy_url
    )
    return [record["id"] for record in records]


async def discover_google_model_options(
    api_key: str | None = None,
    base_url: str | None = None,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """Return normalized Google model records for capability inspection."""
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
        records: list[dict[str, Any]] = []
        for m in data:
            if not isinstance(m, dict):
                continue
            name = m.get("name") or ""
            if name.startswith("models/"):
                name = name[7:]
            methods = m.get("supportedGenerationMethods") or []
            if name and (not methods or "generateContent" in methods):
                records.append({**m, "id": name})
        return records


def _vertex_publisher_model_id(name: str) -> str | None:
    """Return a portable serverless publisher model id.

    Vertex endpoint and tuned-model resources are deliberately excluded. AESPA
    only supports publisher models that do not require a user-managed endpoint.
    """
    value = name.strip().strip("/")
    if not value or "/endpoints/" in value or "/locations/" in value:
        return None
    if value.startswith("publishers/"):
        parts = value.split("/")
        if len(parts) >= 4 and parts[2] == "models":
            publisher = parts[1]
            model = "/".join(parts[3:])
            return model if publisher == "google" else f"{publisher}/{model}"
        return None
    return value if value.startswith("gemini-") else None


async def discover_google_vertex_model_options(
    project_id: str,
    location: str = "global",
) -> list[dict[str, Any]]:
    """List serverless Google publisher models through Vertex AI and ADC."""
    from google import genai
    from google.genai import types

    project = project_id.strip()
    if not project:
        raise ValueError("Google Cloud project id is required for Vertex AI")
    region = (location or "global").strip() or "global"
    client = genai.Client(
        vertexai=True,
        project=project,
        location=region,
        http_options=types.HttpOptions(api_version="v1"),
    )
    async_client = client.aio
    records: list[dict[str, Any]] = []
    try:
        pager = await async_client.models.list(config={"query_base": True})
        async for model in pager:
            model_id = _vertex_publisher_model_id(str(getattr(model, "name", "")))
            if not model_id:
                continue
            actions = [
                str(action).replace("_", "").casefold()
                for action in (getattr(model, "supported_actions", None) or [])
            ]
            if actions and not any(
                action.endswith("generatecontent") for action in actions
            ):
                continue
            record: dict[str, Any] = {"id": model_id}
            input_limit = getattr(model, "input_token_limit", None)
            output_limit = getattr(model, "output_token_limit", None)
            if isinstance(input_limit, int) and input_limit > 0:
                record["input_token_limit"] = input_limit
            if isinstance(output_limit, int) and output_limit > 0:
                record["output_token_limit"] = output_limit
            if actions:
                record["supported_actions"] = list(
                    getattr(model, "supported_actions", None) or []
                )
            records.append(record)
    finally:
        await async_client.aclose()
    return records


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
            or "ap-southeast-2"
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
