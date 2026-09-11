"""LLM configuration values independent of a database session."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResolvedLLMConfig(BaseModel):
    """A saved profile with its provider settings applied to a separate snapshot."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int | None
    name: str
    is_active: bool
    provider_id: int | None
    provider: str
    api_key: str | None = Field(repr=False)
    base_url: str | None
    username: str | None
    project_id: str | None
    model: str
    max_tokens: int
    max_context_tokens: int
    context_limit_source: str
    temperature: float | None
    reasoning_effort: str | None
    use_vision: bool
    force_tool_choice: bool
    updated_at: datetime
