from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class CredentialIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    label: str | None = None


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    password: str
    label: str | None = None


class SiteBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    base_url: HttpUrl
    requires_auth: bool = False
    login_url: HttpUrl | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _check_auth_consistency(self) -> "SiteBase":
        if self.requires_auth and self.login_url is None:
            raise ValueError("login_url is required when requires_auth is true")
        if not self.requires_auth and self.login_url is not None:
            raise ValueError("login_url must be omitted when requires_auth is false")
        return self


class SiteCreate(SiteBase):
    credentials: list[CredentialIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_credentials(self) -> "SiteCreate":
        if self.credentials and not self.requires_auth:
            raise ValueError("credentials are only allowed when requires_auth is true")
        return self


class SiteUpdate(SiteCreate):
    """Same shape as create; PUT replaces the full record."""


class SiteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    requires_auth: bool
    login_url: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    credential_count: int


class SiteDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    requires_auth: bool
    login_url: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    credentials: list[CredentialOut]


# ── LLM config schemas ────────────────────────────────────────────────────

LLMProviderLiteral = Literal["anthropic", "openai", "openai_compatible"]

PROVIDER_DEFAULT_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-3-5",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
    ],
    "openai_compatible": [],
}


class LLMConfigIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider: LLMProviderLiteral = "anthropic"
    api_key: str | None = None
    base_url: str | None = None
    model: str = Field(min_length=1)
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    use_vision: bool = False

    @model_validator(mode="after")
    def _check_provider_fields(self) -> "LLMConfigIn":
        if self.provider in ("anthropic", "openai") and not self.api_key:
            raise ValueError(f"api_key is required for provider '{self.provider}'")
        if self.provider == "openai_compatible" and not self.base_url:
            raise ValueError("base_url is required for openai_compatible provider")
        return self

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class LLMConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    api_key: str | None
    base_url: str | None
    model: str
    max_tokens: int
    temperature: float
    use_vision: bool
    updated_at: datetime


# ── Test run schemas ──────────────────────────────────────────────────────────

class TestRunCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=200)
    use_screenshots: bool = False
    max_depth: int = Field(default=3, ge=1, le=10)
    max_pages: int = Field(default=50, ge=5, le=500)


class TestRunUpdate(BaseModel):
    max_depth: int = Field(ge=1, le=10)
    max_pages: int = Field(ge=5, le=500)


class TestRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    name: str
    status: str
    use_screenshots: bool
    max_depth: int
    max_pages: int
    pages_discovered: int
    current_url: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class ScopeUpdate(BaseModel):
    in_scope: bool
    cascade: bool = False


class CrawledPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_run_id: int
    url: str
    title: str | None
    llm_context: str | None
    depth: int
    status: str
    error_message: str | None
    in_scope: bool = True
    req_auth: bool | None = None
    takes_input: bool | None = None
    has_object_ref: bool | None = None
    has_business_logic: bool | None = None
    discovered_at: datetime
    # screenshot returned separately via /pages/{id} to keep list responses light


class CrawledPageDetail(CrawledPageOut):
    page_text: str | None
    screenshot_b64: str | None


class GraphNode(BaseModel):
    id: int
    url: str
    title: str | None
    depth: int
    status: str
    context: str | None
    in_scope: bool = True
    scan_status: str = "pending"


class GraphLink(BaseModel):
    source: int
    target: int
    link_text: str | None


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]
