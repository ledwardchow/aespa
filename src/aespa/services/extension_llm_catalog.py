"""Read-only LLM settings supplied from an extension's own data store."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import urlsplit

from aespa.services.resolved_llm_config import ResolvedLLMConfig
from aespa.services.settings_values import AGENT_ROLES

# These adapters use credentials owned by their CLI, SDK, or environment.
EXTENSION_LLM_FORMATS = frozenset(
    {
        "bedrock",
        "bedrock_mantle",
        "openai_codex",
        "github_copilot",
        "factory_droid",
        "google_vertex",
        "google_antigravity",
    }
)
_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$")


@dataclass(frozen=True)
class ExtensionLLMProvider:
    key: str
    name: str
    api_format: str
    models: list[str]
    base_url: str | None = None
    username: str | None = None
    project_id: str | None = None
    aws_profile: str | None = None
    location: str | None = None


@dataclass(frozen=True)
class ExtensionLLMModel:
    key: str
    name: str
    provider_key: str
    model: str
    max_tokens: int = 16384
    max_context_tokens: int = 200000
    max_tpm: int | None = None
    max_rpm: int | None = None
    temperature: float | None = None
    reasoning_effort: str | None = None
    use_vision: bool = False
    force_tool_choice: bool = False


@dataclass(frozen=True)
class ExtensionLLMProfile:
    key: str
    name: str
    default_model_key: str
    role_models: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtensionLLMSnapshot:
    providers: list[ExtensionLLMProvider]
    models: list[ExtensionLLMModel]
    profiles: list[ExtensionLLMProfile]


class ExtensionLLMCatalog(Protocol):
    """An extension reads these definitions from its own database on demand."""

    def snapshot(self) -> ExtensionLLMSnapshot: ...


def _id(extension_id: str, kind: str, key: str) -> str:
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise ValueError(f"Invalid extension LLM {kind} key")
    return f"extension:{extension_id}:{kind}:{key}"


def validate_snapshot(extension_id: str, snapshot: ExtensionLLMSnapshot) -> None:
    if not isinstance(snapshot, ExtensionLLMSnapshot):
        raise ValueError("LLM catalog must return an ExtensionLLMSnapshot")
    for kind, items in (
        ("provider", snapshot.providers),
        ("model", snapshot.models),
        ("profile", snapshot.profiles),
    ):
        keys = [_id(extension_id, kind, item.key) for item in items]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate extension LLM {kind} key")
        if any(not item.name.strip() for item in items):
            raise ValueError(f"Extension LLM {kind} names cannot be empty")
    providers = {item.key: item for item in snapshot.providers}
    models = {item.key: item for item in snapshot.models}
    for provider in snapshot.providers:
        if provider.api_format not in EXTENSION_LLM_FORMATS:
            raise ValueError(
                f"{provider.api_format!r} cannot be stored in an extension LLM catalog"
            )
        if not provider.models or any(
            not isinstance(model, str) or not model.strip() for model in provider.models
        ):
            raise ValueError("Extension LLM providers need non-empty model names")
        if provider.api_format == "google_vertex" and not provider.project_id:
            raise ValueError("Google Vertex AI requires a project ID")
        if provider.base_url:
            url = urlsplit(provider.base_url)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError(
                    "Extension LLM base URLs must be HTTPS and cannot contain credentials or query parameters"
                )
    for model in snapshot.models:
        provider = providers.get(model.provider_key)
        if provider is None or model.model not in provider.models:
            raise ValueError(
                f"Extension LLM model {model.key!r} has no matching provider model"
            )
        if model.max_tokens < 1 or model.max_context_tokens <= model.max_tokens + 1024:
            raise ValueError("Extension LLM model token limits are invalid")
        if (model.max_tpm is not None and model.max_tpm < 1) or (
            model.max_rpm is not None and model.max_rpm < 1
        ):
            raise ValueError("Extension LLM model rate limits must be positive")
        if model.temperature is not None and not 0 <= model.temperature <= 2:
            raise ValueError("Extension LLM model temperature must be between 0 and 2")
    for profile in snapshot.profiles:
        if profile.default_model_key not in models or any(
            key not in models for key in profile.role_models.values()
        ):
            raise ValueError(
                f"Extension LLM profile {profile.key!r} has an unknown model"
            )
        if any(role not in AGENT_ROLES for role in profile.role_models):
            raise ValueError(
                f"Extension LLM profile {profile.key!r} has an unknown role"
            )


def snapshot_out(
    extension_id: str, extension_name: str, snapshot: ExtensionLLMSnapshot
) -> dict:
    validate_snapshot(extension_id, snapshot)
    now = datetime.now(timezone.utc).isoformat()
    providers = {p.key: p for p in snapshot.providers}
    models = {m.key: m for m in snapshot.models}
    return {
        "providers": [
            {
                "id": _id(extension_id, "provider", p.key),
                "name": p.name,
                "api_format": p.api_format,
                "models": p.models,
                "base_url": p.base_url,
                "username": p.username,
                "project_id": p.project_id,
                "aws_profile": p.aws_profile,
                "location": p.location,
                "has_api_key": False,
                "updated_at": now,
                "extension_id": extension_id,
                "extension_name": extension_name,
            }
            for p in snapshot.providers
        ],
        "models": [
            {
                "id": _id(extension_id, "model", m.key),
                "name": m.name,
                "provider_id": _id(extension_id, "provider", m.provider_key),
                "provider_name": providers[m.provider_key].name,
                "provider": providers[m.provider_key].api_format,
                "model": m.model,
                "max_tokens": m.max_tokens,
                "max_context_tokens": m.max_context_tokens,
                "max_tpm": m.max_tpm,
                "max_rpm": m.max_rpm,
                "temperature": m.temperature,
                "reasoning_effort": m.reasoning_effort,
                "use_vision": m.use_vision,
                "force_tool_choice": m.force_tool_choice,
                "extension_id": extension_id,
                "extension_name": extension_name,
            }
            for m in snapshot.models
        ],
        "profiles": [
            {
                "id": _id(extension_id, "profile", p.key),
                "name": p.name,
                "is_active": False,
                "default_model_id": _id(extension_id, "model", p.default_model_key),
                "default_model_name": models[p.default_model_key].name,
                "role_models": {
                    role: _id(extension_id, "model", key)
                    for role, key in p.role_models.items()
                },
                "role_model_names": {
                    role: models[key].name for role, key in p.role_models.items()
                },
                "updated_at": now,
                "extension_id": extension_id,
                "extension_name": extension_name,
            }
            for p in snapshot.profiles
        ],
    }


def resolve_model(snapshot: ExtensionLLMSnapshot, model_key: str) -> ResolvedLLMConfig:
    """Give extension code a normal AESPA LLM config without a main-DB write."""
    model = next((item for item in snapshot.models if item.key == model_key), None)
    if model is None:
        raise KeyError(model_key)
    provider = next(
        item for item in snapshot.providers if item.key == model.provider_key
    )
    return ResolvedLLMConfig(
        id=None,
        name=model.name,
        is_active=False,
        provider_id=None,
        provider=provider.api_format,
        api_key=None,
        base_url=provider.base_url,
        username=provider.username,
        project_id=provider.project_id,
        aws_profile=provider.aws_profile,
        location=provider.location,
        model=model.model,
        max_tpm=model.max_tpm,
        max_rpm=model.max_rpm,
        max_tokens=model.max_tokens,
        max_context_tokens=model.max_context_tokens,
        context_limit_source="configured",
        temperature=model.temperature,
        reasoning_effort=model.reasoning_effort,
        use_vision=model.use_vision,
        force_tool_choice=model.force_tool_choice,
        updated_at=datetime.now(timezone.utc),
    )
