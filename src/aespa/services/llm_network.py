"""Saved network settings for outbound LLM and supporting HTTP requests."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from aespa.db import get_engine
from aespa.services.settings_integrations import get_upstream_proxy_config


def configured_llm_network() -> tuple[str | None, str | None]:
    """Return the configured LLM proxy and PEM CA bundle without changing state."""
    with Session(get_engine()) as session:
        config = get_upstream_proxy_config(session)
    proxy = config.llm_proxy_url if config.proxy_llm else None
    return proxy, config.llm_ca_bundle_path


def httpx_options(proxy_url: str | None = None) -> dict[str, Any]:
    """Use the same TLS policy as built in LLM calls."""
    saved_proxy, ca_bundle = configured_llm_network()
    proxy = proxy_url if proxy_url is not None else saved_proxy
    options: dict[str, Any] = {"verify": ca_bundle or proxy is None}
    if proxy:
        options["proxy"] = proxy
    return options


def child_network_env(
    env: dict[str, str], proxy_url: str | None = None
) -> dict[str, str]:
    """Pass saved proxy and CA settings to a CLI without changing parent env."""
    saved_proxy, ca_bundle = configured_llm_network()
    proxy = proxy_url if proxy_url is not None else saved_proxy
    if proxy:
        env["HTTP_PROXY"] = proxy
        env["HTTPS_PROXY"] = proxy
    if ca_bundle:
        env["SSL_CERT_FILE"] = ca_bundle
        env["NODE_EXTRA_CA_CERTS"] = ca_bundle
        env["AWS_CA_BUNDLE"] = ca_bundle
    return env
