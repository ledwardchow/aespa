from __future__ import annotations

from datetime import datetime
import re
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

LLMProviderLiteral = Literal[
    "anthropic", "openai", "openai_compatible", "google", "azure_openai", "azure_foundry"
]

PROVIDER_DEFAULT_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-3-7-sonnet-20250219",
        "claude-haiku-3-5",
        "claude-3-5-sonnet-20241022",
    ],
    "openai": [
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4o",
        "gpt-4o-mini",
        "o4-mini",
        "o3",
        "o3-mini",
    ],
    "openai_compatible": [],
    "google": [
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    "azure_openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "o3",
        "o3-mini",
        "o4-mini",
    ],
    "azure_foundry": [
        "Meta-Llama-3.3-70B-Instruct",
        "Meta-Llama-3.1-70B-Instruct",
        "Mistral-large-2411",
        "Phi-4",
        "DeepSeek-R1",
        "gpt-4o",
        "o3-mini",
    ],
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
        _needs_key = ("anthropic", "openai", "google", "azure_openai", "azure_foundry")
        _needs_url = ("openai_compatible", "azure_openai", "azure_foundry")
        if self.provider in _needs_key and not self.api_key:
            raise ValueError(f"api_key is required for provider '{self.provider}'")
        if self.provider in _needs_url and not self.base_url:
            raise ValueError(f"base_url is required for provider '{self.provider}'")
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


# ── Scanner policy schemas ───────────────────────────────────────────────────

ScanModeLiteral = Literal["passive", "safe_active", "aggressive", "destructive"]
SchemeLiteral = Literal["http", "https"]

SCAN_MODES: tuple[str, ...] = ("passive", "safe_active", "aggressive", "destructive")
DEFAULT_METHODS_BY_MODE: dict[str, list[str]] = {
    "passive": ["GET", "HEAD"],
    "safe_active": ["GET", "POST", "HEAD"],
    "aggressive": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    "destructive": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
}


class ScannerPolicyBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scan_mode: ScanModeLiteral = "safe_active"
    max_probes_per_page: int = Field(default=50, ge=0, le=500)
    request_timeout_s: float = Field(default=10.0, ge=1.0, le=120.0)
    min_delay_s: float = Field(default=0.2, ge=0.0, le=60.0)
    max_request_body_bytes: int = Field(default=65536, ge=0, le=10 * 1024 * 1024)
    response_body_read_limit_bytes: int = Field(default=512 * 1024, ge=1024, le=10 * 1024 * 1024)
    allowed_schemes: list[SchemeLiteral] = Field(default_factory=lambda: ["http", "https"], min_length=1)
    methods_by_mode: dict[str, list[str]] = Field(default_factory=lambda: {
        k: list(v) for k, v in DEFAULT_METHODS_BY_MODE.items()
    })
    blocked_headers: list[str] = Field(default_factory=lambda: ["host", "cookie"])
    follow_redirects: bool = True
    allow_subdomains: bool = True
    require_approval_for_destructive: bool = True

    @field_validator("methods_by_mode", mode="before")
    @classmethod
    def _normalize_methods_by_mode(cls, v):
        if v is None:
            return {k: list(methods) for k, methods in DEFAULT_METHODS_BY_MODE.items()}
        out: dict[str, list[str]] = {}
        for mode, methods in dict(v).items():
            if mode not in SCAN_MODES:
                raise ValueError(f"Unknown scan mode '{mode}'")
            if not isinstance(methods, list) or not methods:
                raise ValueError(f"methods_by_mode.{mode} must be a non-empty list")
            normalized = []
            for method in methods:
                method_s = str(method).strip().upper()
                if not re.fullmatch(r"[A-Z]{2,16}", method_s):
                    raise ValueError(f"Invalid HTTP method '{method}'")
                if method_s not in normalized:
                    normalized.append(method_s)
            out[mode] = normalized
        for mode, methods in DEFAULT_METHODS_BY_MODE.items():
            out.setdefault(mode, list(methods))
        return out

    @field_validator("blocked_headers", mode="before")
    @classmethod
    def _normalize_blocked_headers(cls, v):
        if v is None:
            return ["host", "cookie"]
        out = []
        for header in list(v):
            header_s = str(header).strip().lower()
            if not re.fullmatch(r"[a-z0-9!#$%&'*+.^_`|~-]+", header_s):
                raise ValueError(f"Invalid header name '{header}'")
            if header_s not in out:
                out.append(header_s)
        return out

    @model_validator(mode="after")
    def _check_current_mode_methods(self) -> "ScannerPolicyBase":
        if self.scan_mode not in self.methods_by_mode or not self.methods_by_mode[self.scan_mode]:
            raise ValueError("methods_by_mode must include methods for the selected scan_mode")
        return self


class ScannerPolicyIn(ScannerPolicyBase):
    pass


class ScannerPolicyOut(ScannerPolicyBase):
    updated_at: datetime


class RunScannerPolicyOut(ScannerPolicyBase):
    source: Literal["run_snapshot", "global_default"]
    updated_at: datetime | None = None


# ── Test run schemas ──────────────────────────────────────────────────────────

class TestRunCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=200)
    use_screenshots: bool = False
    max_depth: int = Field(default=3, ge=1, le=10)
    max_pages: int = Field(default=50, ge=5, le=500)
    scan_mode: ScanModeLiteral = "safe_active"


class TestRunUpdate(BaseModel):
    max_depth: int = Field(ge=1, le=10)
    max_pages: int = Field(ge=5, le=500)


class CredentialSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    label: str | None


class TestRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    name: str
    status: str
    use_screenshots: bool
    max_depth: int
    max_pages: int
    scan_mode: str = "safe_active"
    pages_discovered: int
    current_url: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    credentials: list[CredentialSummary] = []
    scanner_policy: dict = Field(default_factory=dict)
    # Per-credential crawl progress: {username: {current_url, pages_visited}}
    per_user_progress: dict = Field(default_factory=dict)

    @field_validator("per_user_progress", mode="before")
    @classmethod
    def _coerce_per_user_progress(cls, v):
        import json as _json
        if v is None or v == "":
            return {}
        if isinstance(v, str):
            return _json.loads(v)
        return v


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
    accessible_by: list[int] = []


class GraphLink(BaseModel):
    source: int
    target: int
    link_text: str | None


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class TrafficEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    created_at: datetime
    method: str
    url: str
    request_headers: dict
    request_body: str | None
    status: int | None
    response_headers: dict
    response_body: str | None
    duration_ms: int | None
    username: str | None


class ScanFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_run_id: int
    page_id: int
    owasp_category: str
    severity: str
    title: str
    description: str
    affected_url: str
    evidence: str
    screenshot_b64: str | None
    validation_status: str
    validation_note: str | None
    created_at: datetime


class ValidationStatusOut(BaseModel):
    total: int
    confirmed: int
    false_positives: int
    validating: int
    unvalidated: int
    status: str   # idle | running | stopped | complete


class PageCredentialViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credential_id: int | None
    username: str | None
    screenshot_b64: str | None
    llm_context: str | None
    req_auth: bool | None
    takes_input: bool | None
    has_object_ref: bool | None
    has_business_logic: bool | None


class ScanStatusOut(BaseModel):
    total_pages: int
    pages_done: int
    findings_count: int
    status: str   # idle | running | complete | stopped | failed
