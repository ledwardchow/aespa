from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class CredentialIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    label: str | None = None
    login_url: HttpUrl | None = None
    # Advanced auth
    auth_mode: str = "auto"
    totp_seed: str | None = None  # base32 TOTP secret; stored write-only


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    password: str
    label: str | None = None
    login_url: str | None = None
    auth_mode: str = "auto"
    # totp_seed is intentionally excluded (write-only)


class SiteBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    base_url: HttpUrl
    requires_auth: bool = False
    login_url: HttpUrl | None = None
    notes: str | None = None
    scan_guidance: str | None = None
    scope_hosts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_auth_consistency(self) -> "SiteBase":
        if not self.requires_auth and self.login_url is not None:
            raise ValueError("login_url must be omitted when requires_auth is false")
        return self


class SiteCreate(SiteBase):
    credentials: list[CredentialIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_credentials(self) -> "SiteCreate":
        if self.credentials and not self.requires_auth:
            raise ValueError("credentials are only allowed when requires_auth is true")
        if self.requires_auth:
            if self.login_url is None and not self.credentials:
                raise ValueError(
                    "login_url is required when no credential login_url is provided"
                )
            if self.login_url is None and any(
                c.login_url is None for c in self.credentials
            ):
                raise ValueError(
                    "each credential must include login_url when site login_url is omitted"
                )
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
    scope_hosts: list[str] = Field(default_factory=list)


class SiteDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    requires_auth: bool
    login_url: str | None
    notes: str | None
    scan_guidance: str | None
    created_at: datetime
    updated_at: datetime
    credentials: list[CredentialOut]
    scope_hosts: list[str] = Field(default_factory=list)


# ── API Collection schemas ────────────────────────────────────────────────


class ApiCollectionBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    base_url: HttpUrl
    description: str | None = None
    servers: list[str] = Field(default_factory=list)
    scope_hosts: list[str] = Field(default_factory=list)


class ApiCollectionCreate(ApiCollectionBase):
    pass


class ApiCollectionUpdate(ApiCollectionBase):
    """Same shape as create; PUT replaces the full record."""


class ApiCollectionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    endpoint_count: int = 0
    document_count: int = 0
    servers: list[str] = Field(default_factory=list)
    scope_hosts: list[str] = Field(default_factory=list)


class ApiCollectionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    servers: list[str] = Field(default_factory=list)
    scope_hosts: list[str] = Field(default_factory=list)
    readiness_json: str | None = None  # raw JSON; frontend parses it


class ApiDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    filename: str
    doc_type: str
    content_type: str | None
    size_bytes: int
    status: str
    error_message: str | None
    created_at: datetime


class ApiEndpointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    source_doc_id: int | None
    method: str
    path: str
    base_url: str | None
    operation_id: str | None
    summary: str | None
    parameters_json: str
    request_body_schema_json: str
    security_json: str
    auth_required: bool
    tags_json: str
    sample_request_json: str
    in_scope: bool
    created_at: datetime
    # Slice 4 — readiness assessment
    prereq_can_test: bool
    prereq_can_test_auth: bool
    prereq_notes: str  # JSON list of gap strings


class ApiCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    scheme: str
    name: str
    # value intentionally omitted from output schema
    label: str | None
    scope: str
    endpoint_id: int | None
    auth_endpoint: str | None  # set when scheme == "login"
    created_at: datetime


class ApiCredentialCreate(BaseModel):
    scheme: str = "bearer"
    name: str = "Authorization"
    value: str
    label: str | None = None
    scope: str = "global"
    endpoint_id: int | None = None
    auth_endpoint: str | None = None  # set when scheme == "login"


# ── API Test Run schemas ──────────────────────────────────────────────────────


class ApiTestRunCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None  # auto-generated if omitted
    llm_config_id: int | None = None
    llm_profile_id: int | None = None
    coverage_mode: str = "track"  # track|enforce


class ApiTestRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    name: str
    status: str
    phase: str = "created"
    outcome: str | None = None
    terminal_reason: str | None = None
    coverage_mode: str
    llm_config_id: int | None
    llm_profile_id: int | None = None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


# ── Slice 7 — Coverage matrix schemas ────────────────────────────────────────


class ApiEndpointTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    api_test_run_id: int
    endpoint_id: int
    owasp_api_category: str
    status: str
    skip_reason: str | None
    finding_ids_json: str
    last_updated: datetime


class ApiCoverageEndpointRow(BaseModel):
    """One endpoint row in the coverage matrix."""

    endpoint_id: int
    method: str
    path: str
    auth_required: bool
    prereq_can_test: bool
    prereq_can_test_auth: bool
    prereq_notes: str  # JSON list of gap strings
    cells: dict[str, dict]  # owasp_api_category → {status, finding_ids}


class ApiCoverageMatrixOut(BaseModel):
    """Full coverage matrix for one ApiTestRun."""

    run_id: int
    coverage_mode: str
    categories: list[str]  # ordered API1..API10
    endpoints: list[ApiCoverageEndpointRow]
    totals: dict[str, int]  # status → count across all cells


# ── SAST schemas ──────────────────────────────────────────────────────────────


class SastRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int | None
    document_id: int | None
    source_filename: str | None
    name: str
    status: str
    triggered_by_run_type: str | None
    triggered_by_run_id: int | None
    llm_config_id: int | None
    llm_profile_id: int | None = None
    leads_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScanLeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int | None
    producer_run_type: str
    producer_run_id: int
    source: str
    category: str
    severity: str
    confidence: float
    title: str
    description: str
    location: str
    evidence: str
    note: str
    status: str
    investigated_by_run_type: str | None
    investigated_by_run_id: int | None
    linked_finding_id: int | None
    imported_into_run_type: str | None
    imported_into_run_id: int | None
    created_at: datetime
    updated_at: datetime


# ── LLM config schemas ────────────────────────────────────────────────────

LLMProviderAPILiteral = Literal[
    "anthropic",
    "github_copilot",
    "openai",
    "openai_compatible",
    "openrouter",
    "google",
    "bedrock",
    "bedrock_mantle",
    "azure_openai",
    "azure_foundry",
    "azure_foundry_openai",
    "azure_foundry_anthropic",
]

PROVIDER_DEFAULT_MODELS: dict[str, list[str]] = {
    "github_copilot": [
        "auto",
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "claude-sonnet-5",
        "claude-opus-4.8",
    ],
    "anthropic": [
        "claude-opus-4-8",
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-3-7-sonnet-20250219",
        "claude-haiku-3-5",
        "claude-3-5-sonnet-20241022",
    ],
    "openai": [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-5.5",
        "gpt-5.4",
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
    "openrouter": [
        "openrouter/owl-alpha",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "poolside/laguna-xs.2:free",
        "poolside/laguna-m.1:free",
    ],
    "google": [
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    "bedrock": [
        "global.anthropic.claude-opus-4-8",
        "global.anthropic.claude-sonnet-4-6",
        "global.anthropic.claude-opus-4-7",
    ],
    # Mantle is driven via the OpenAI Responses API, which supports the frontier
    # GPT-5.x models and the gpt-oss models. Claude families are Converse/Messages
    # only on Mantle — use the Amazon Bedrock Runtime provider for those.
    "bedrock_mantle": [
        "openai.gpt-5.5",
        "openai.gpt-5.4",
        "openai.gpt-oss-120b",
        "openai.gpt-oss-20b",
    ],
    "azure_openai": [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "o3",
        "o3-mini",
        "o4-mini",
    ],
    "azure_foundry": [
        "gpt-4o",
        "gpt-4.1",
        "o3-mini",
        "DeepSeek-R1",
        "Meta-Llama-3.3-70B-Instruct",
        "Meta-Llama-3.1-70B-Instruct",
        "Mistral-large-2411",
        "Phi-4",
    ],
    "azure_foundry_openai": [
        "gpt-4o",
        "gpt-4.1",
        "gpt-4.1-mini",
        "o3",
        "o3-mini",
        "o4-mini",
        "DeepSeek-R1",
        "Meta-Llama-3.3-70B-Instruct",
        "Mistral-large-2411",
        "Phi-4",
    ],
    "azure_foundry_anthropic": [
        "claude-opus-4-8",
        "claude-sonnet-4-5",
        "claude-opus-4-1",
        "claude-3-7-sonnet-20250219",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ],
}


class LLMProviderConfigIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(default="Default Provider", min_length=1, max_length=120)
    api_format: LLMProviderAPILiteral = "anthropic"
    base_url: str | None = None
    username: str | None = Field(default=None, max_length=255)
    project_id: str | None = Field(default=None, max_length=120)
    models: list[str] = Field(default_factory=list, min_length=1)
    api_key: str | None = None
    max_tpm: int | None = Field(default=None, ge=1)
    max_rpm: int | None = Field(default=None, ge=1)

    @field_validator("models")
    @classmethod
    def _validate_models(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for model in v:
            model = model.strip()
            if not model:
                continue
            key = model.casefold()
            if key not in seen:
                cleaned.append(model)
                seen.add(key)
        if not cleaned:
            raise ValueError("at least one model name is required")
        return cleaned

    @field_validator("base_url")
    @classmethod
    def _validate_provider_base_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class LLMProviderConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    api_format: str
    base_url: str | None
    username: str | None = None
    project_id: str | None = None
    models: list[str] = Field(default_factory=list)
    has_api_key: bool = False
    api_key: str | None = None
    max_tpm: int | None = None
    max_rpm: int | None = None
    updated_at: datetime


class LLMConfigIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(default="Default", min_length=1, max_length=120)
    provider_id: int
    model: str = Field(min_length=1)
    max_tokens: int = Field(default=70000, ge=1, le=256000)
    temperature: Optional[float] = Field(default=None)
    use_vision: bool = False
    force_tool_choice: bool = False

    @field_validator("temperature")
    @classmethod
    def _validate_temperature(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v


class LLMConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
    provider_id: int | None = None
    provider_name: str | None = None
    provider: str
    has_api_key: bool = False
    api_key: str | None = None
    base_url: str | None
    username: str | None = None
    project_id: str | None = None
    model: str
    max_tokens: int
    temperature: Optional[float] = None
    use_vision: bool
    force_tool_choice: bool
    updated_at: datetime


class LLMProfileIn(BaseModel):
    """A per-agent-role model assignment. ``default_model_id`` covers any role not
    present in ``role_models``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(default="Default", min_length=1, max_length=120)
    default_model_id: int
    # role → LLMConfig id; only roles overridden away from the default.
    role_models: dict[str, int] = Field(default_factory=dict)


class LLMProfileOut(BaseModel):
    id: int
    name: str
    is_active: bool
    default_model_id: int | None = None
    default_model_name: str | None = None
    role_models: dict[str, int] = Field(default_factory=dict)
    role_model_names: dict[str, str | None] = Field(default_factory=dict)
    updated_at: datetime


# ── Scanner policy schemas ───────────────────────────────────────────────────

ScanModeLiteral = Literal["passive", "safe_active", "aggressive", "destructive"]
SchemeLiteral = Literal["http", "https"]

SCAN_MODES: tuple[str, ...] = ("passive", "safe_active", "aggressive", "destructive")
DEFAULT_METHODS_BY_MODE: dict[str, list[str]] = {
    "passive": ["GET", "HEAD"],
    "safe_active": ["GET", "POST", "HEAD"],
    "aggressive": ["GET", "POST", "PUT", "PATCH", "HEAD", "OPTIONS"],
    "destructive": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
}


class ScannerPolicyBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    execution_monitor_enabled: bool = False
    disable_deterministic_checks: bool = False
    max_consecutive_text_turns: int = Field(default=0, ge=0, le=50)
    enforce_full_coverage_obligations: bool = False
    scan_mode: ScanModeLiteral = "aggressive"
    max_probes_per_page: int = Field(default=50, ge=0, le=500)
    thinking_max_steps: int = Field(default=120, ge=1, le=1000)
    request_timeout_s: float = Field(default=10.0, ge=1.0, le=120.0)
    min_delay_s: float = Field(default=0.05, ge=0.0, le=60.0)
    max_request_body_bytes: int = Field(default=65536, ge=0, le=10 * 1024 * 1024)
    response_body_read_limit_bytes: int = Field(
        default=512 * 1024, ge=1024, le=10 * 1024 * 1024
    )
    allowed_schemes: list[SchemeLiteral] = Field(
        default_factory=lambda: ["http", "https"], min_length=1
    )
    methods_by_mode: dict[str, list[str]] = Field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_METHODS_BY_MODE.items()}
    )
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
        if (
            self.scan_mode not in self.methods_by_mode
            or not self.methods_by_mode[self.scan_mode]
        ):
            raise ValueError(
                "methods_by_mode must include methods for the selected scan_mode"
            )
        return self


class ScannerPolicyIn(ScannerPolicyBase):
    pass


class ScannerPolicyOut(ScannerPolicyBase):
    updated_at: datetime


class RunScannerPolicyOut(ScannerPolicyBase):
    source: Literal["run_snapshot", "global_default"]
    updated_at: datetime | None = None


class UpstreamProxyConfigBase(BaseModel):
    proxy_url: str | None = Field(default=None, max_length=500)
    proxy_scanner: bool = False
    proxy_llm: bool = False

    @field_validator("proxy_url")
    @classmethod
    def _normalize_proxy_url(cls, v):
        if not v:
            return None
        v = v.strip()
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("proxy_url must start with http:// or https://")
        return v


class UpstreamProxyConfigIn(UpstreamProxyConfigBase):
    pass


class UpstreamProxyConfigOut(UpstreamProxyConfigBase):
    updated_at: datetime


class BurpRestApiConfigBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = False
    api_url: str = Field(default="http://127.0.0.1:1337", min_length=1, max_length=500)
    api_key: str | None = None
    scan_configuration_name: str | None = Field(
        default="Audit checks - all except time-based detection methods",
        max_length=200,
    )
    scan_sqli: bool = True
    scan_xss: bool = True
    scan_command_injection: bool = True
    scan_path_traversal: bool = True
    scan_ssrf: bool = True
    scan_xxe: bool = True
    scan_ssti: bool = True

    @field_validator("api_url")
    @classmethod
    def _normalize_api_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("api_url must start with http:// or https://")
        return v

    @field_validator("scan_configuration_name")
    @classmethod
    def _normalize_scan_configuration_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class BurpRestApiConfigIn(BurpRestApiConfigBase):
    pass


class BurpRestApiConfigOut(BurpRestApiConfigBase):
    has_api_key: bool = False
    api_key: str | None = None
    updated_at: datetime


# ── Specialist agent config schemas ──────────────────────────────────────────


class SpecialistAgentConfigBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = True
    max_concurrent: int = Field(default=5, ge=0, le=20)
    max_steps: int = Field(default=30, ge=1, le=200)
    min_priority: int = Field(default=7, ge=1, le=10)
    dispatch_idor: bool = True
    dispatch_auth_bypass: bool = True
    dispatch_sqli: bool = True
    dispatch_xss: bool = True
    dispatch_business_logic: bool = True
    dispatch_ssrf: bool = True
    dispatch_path_traversal: bool = True
    dispatch_cors: bool = False
    dispatch_crypto: bool = True
    dispatch_config: bool = False
    dispatch_file_upload: bool = True
    trigger_specialist_on_burp: bool = False


class SpecialistAgentConfigIn(SpecialistAgentConfigBase):
    pass


class SpecialistAgentConfigOut(SpecialistAgentConfigBase):
    updated_at: datetime


# ── Adversarial Validator config schemas ──────────────────────────────────────


class ValidatorConfigBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = True
    max_steps: int = Field(default=20, ge=1, le=50)
    min_severity: str = Field(
        default="low", pattern=r"^(critical|high|medium|low|info)$"
    )
    end_scan_max_concurrent: int = Field(default=4, ge=1, le=8)
    auto_validate_inline: bool = True
    require_concrete_disproof: bool = True


class ValidatorConfigIn(ValidatorConfigBase):
    pass


class ValidatorConfigOut(ValidatorConfigBase):
    updated_at: datetime


# ── Global HTTP header config schemas ─────────────────────────────────────────


class GlobalHttpHeader(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    header_name: str = Field(min_length=1, max_length=200)
    header_value: str = Field(max_length=2000)

    @field_validator("header_name")
    @classmethod
    def _normalize_header_name(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[a-zA-Z0-9!#$%&'*+.^_`|~-]+", v):
            raise ValueError(f"Invalid HTTP header name '{v}'")
        return v

    @field_validator("header_value")
    @classmethod
    def _normalize_header_value(cls, v: str) -> str:
        return v.strip()


class GlobalHttpHeaderConfigBase(BaseModel):
    headers: list[GlobalHttpHeader] = Field(default_factory=list, max_length=100)

    @field_validator("headers")
    @classmethod
    def _reject_duplicate_headers(
        cls, v: list[GlobalHttpHeader]
    ) -> list[GlobalHttpHeader]:
        names = [header.header_name.lower() for header in v]
        if len(names) != len(set(names)):
            raise ValueError("HTTP header names must be unique")
        return v


class GlobalHttpHeaderConfigIn(GlobalHttpHeaderConfigBase):
    pass


class GlobalHttpHeaderConfigOut(GlobalHttpHeaderConfigBase):
    updated_at: datetime


# ── Reporting debug config schemas ───────────────────────────────────────────


class ReportingDebugConfigBase(BaseModel):
    capture_enabled: bool = False
    panel_enabled: bool = False
    batch_max_concurrent: int = Field(default=4, ge=1, le=8)


class ReportingDebugConfigIn(ReportingDebugConfigBase):
    pass


class ReportingDebugConfigOut(ReportingDebugConfigBase):
    updated_at: datetime


# ── Cloudflare Access config schemas ─────────────────────────────────────────


class CloudflareAccessConfigBase(BaseModel):
    # Empty/blank string is treated as "no audience" → audience check skipped.
    audience: str | None = None


class CloudflareAccessConfigIn(CloudflareAccessConfigBase):
    pass


class CloudflareAccessConfigOut(CloudflareAccessConfigBase):
    updated_at: datetime


# ── LLM config export / import schemas ───────────────────────────────────────


class LLMExportProviderItem(BaseModel):
    name: str
    api_format: str
    base_url: str | None = None
    username: str | None = None
    project_id: str | None = None
    models: list[str]
    has_api_key: bool = False
    api_key: str | None = None
    max_tpm: int | None = None
    max_rpm: int | None = None


class LLMExportProfileItem(BaseModel):
    name: str
    provider_name: str
    model: str
    max_tokens: int = 70000
    temperature: Optional[float] = None
    use_vision: bool = False
    force_tool_choice: bool = False
    is_active: bool = False


class LLMConfigExport(BaseModel):
    version: int = 1
    exported_at: datetime
    providers: list[LLMExportProviderItem]
    profiles: list[LLMExportProfileItem]


class LLMImportResult(BaseModel):
    providers_created: int = 0
    providers_updated: int = 0
    profiles_created: int = 0
    profiles_updated: int = 0


# ── Test run schemas ──────────────────────────────────────────────────────────


class TestRunCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=200)
    use_screenshots: bool = False
    max_depth: int = Field(default=3, ge=1, le=10)
    max_pages: int = Field(default=500, ge=5, le=500)
    crawler_mode: Literal["url", "interactive"] = "url"
    llm_config_id: int | None = None
    llm_profile_id: int | None = None


class TestRunUpdate(BaseModel):
    max_depth: int = Field(ge=1, le=10)
    max_pages: int = Field(ge=5, le=500)
    crawler_mode: Literal["url", "interactive"] | None = None
    llm_config_id: int | None = None
    llm_profile_id: int | None = None


class CredentialSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    label: str | None
    auth_mode: str = "auto"
    has_totp_seed: bool = False


class TestRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    name: str
    status: str
    phase: str = "created"
    outcome: str | None = None
    terminal_reason: str | None = None
    use_screenshots: bool
    max_depth: int
    max_pages: int
    crawler_mode: str = "url"
    scan_mode: str = "aggressive"
    scan_status: str = "idle"
    scan_total_pages: int = 0
    scan_pages_done: int = 0
    thinking_status: str = "idle"
    pages_discovered: int
    current_url: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    credentials: list[CredentialSummary] = []
    scanner_policy: dict = Field(default_factory=dict)
    llm_config_id: int | None = None
    llm_profile_id: int | None = None
    # Per-credential crawl progress: {username: {current_url, pages_visited}}
    per_user_progress: dict = Field(default_factory=dict)
    scope_hosts: list[str] = Field(default_factory=list)

    @field_validator("per_user_progress", mode="before")
    @classmethod
    def _coerce_per_user_progress(cls, v):
        import json as _json

        if v is None or v == "":
            return {}
        if isinstance(v, str):
            return _json.loads(v)
        return v


class ActiveJobSummary(BaseModel):
    run_id: int
    site_id: Optional[int] = None
    site_name: Optional[str] = None
    run_name: str
    job_type: str
    status: str
    run_type: str = "web"  # "web" | "api"
    collection_id: Optional[int] = None
    collection_name: Optional[str] = None
    pages_done: int | None = None
    total_pages: int | None = None
    findings_count: int | None = None
    current_url: str | None = None
    started_at: datetime | None = None
    created_at: datetime


class ScopeUpdate(BaseModel):
    in_scope: bool
    cascade: bool = False


class CrawledPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_run_id: int
    url: str
    state_key: str | None = None
    state_label: str | None = None
    state_kind: str = "url"
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
    owasp_applicable: dict[str, bool] = {}
    discovered_at: datetime
    # screenshot returned separately via /pages/{id} to keep list responses light


class CrawledPageDetail(CrawledPageOut):
    page_text: str | None
    screenshot_b64: str | None
    replay_steps_json: str = "[]"


class GraphNode(BaseModel):
    id: int
    url: str
    state_label: str | None = None
    state_kind: str = "url"
    title: str | None
    depth: int
    status: str
    context: str | None
    in_scope: bool = True
    scan_status: str = "pending"
    accessible_by: list[int] = []
    accessible_anonymously: bool = False


class GraphLink(BaseModel):
    source: int
    target: int
    link_text: str | None
    action_kind: str = "navigate"


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class TargetIntelItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_run_id: int
    kind: str
    key: str
    value: str
    url: str | None
    method: str | None
    source: str
    confidence: float
    evidence: str
    item_metadata: dict = Field(default_factory=dict)
    discovered_at: datetime

    @field_validator("item_metadata", mode="before")
    @classmethod
    def _coerce_metadata(cls, v):
        import json as _json

        if v is None or v == "":
            return {}
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return {}
        return v


class TargetIntelSummary(BaseModel):
    counts: dict[str, int] = Field(default_factory=dict)
    items: list[TargetIntelItemOut] = Field(default_factory=list)


class ScannerSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_run_id: int
    label: str
    kind: str
    account_label: str | None
    username: str | None
    credential_id: int | None
    source: str
    cookie_names: list[str] = Field(default_factory=list)
    header_names: list[str] = Field(default_factory=list)
    token_hint: str | None
    lifecycle_state: str = "candidate"
    validation_url: str | None = None
    last_status: int | None = None
    last_validated_at: datetime | None = None
    session_metadata: dict = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ScannerSessionSummary(BaseModel):
    counts: dict[str, int] = Field(default_factory=dict)
    sessions: list[ScannerSessionOut] = Field(default_factory=list)


class ScannerSessionUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None


class ScannerSessionValidationItem(BaseModel):
    session_id: int
    label: str
    outcome: str  # valid | evicted | error
    status_code: int | None = None
    error: str | None = None


class ScannerSessionValidationResult(BaseModel):
    checked: int = 0
    valid: int = 0
    evicted: int = 0
    errors: int = 0
    skipped: int = 0
    results: list[ScannerSessionValidationItem] = Field(default_factory=list)


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
    test_run_id: int | None = None
    page_id: int | None
    owasp_category: str
    severity: str
    title: str
    description: str
    impact: str = ""
    likelihood: str = ""
    recommendation: str = ""
    cvss_score: float = 0.0
    cvss_vector: str = ""
    affected_url: str
    evidence: str
    request_evidence: str = ""
    response_evidence: str = ""
    evidence_json: str = "[]"
    evidence_items: list[dict] = Field(default_factory=list)
    screenshot_b64: str | None
    finding_source: str = "unknown"
    validation_status: str
    validation_note: str | None
    merged_instances: str = "[]"
    poc_command: str = ""
    poc_setup: str = ""
    api_test_run_id: int | None = None
    owasp_api_category: str | None = None
    created_at: datetime


class ScanFindingImportIn(BaseModel):
    owasp_category: str = "A00"
    severity: str = "info"
    title: str
    description: str = ""
    impact: str = ""
    likelihood: str = ""
    recommendation: str = ""
    cvss_score: float = 0.0
    cvss_vector: str = ""
    affected_url: str = ""
    evidence: str = ""
    request_evidence: str = ""
    response_evidence: str = ""
    evidence_items: list[dict] = Field(default_factory=list)
    finding_source: str = "manual_import"
    validation_status: str = "unvalidated"
    validation_note: str | None = None
    merged_instances: str = "[]"
    poc_command: str = ""
    poc_setup: str = ""


class ScanFindingUpdateIn(BaseModel):
    """Partial, user-driven edit of a single finding. Every field is optional;
    only fields explicitly supplied are applied (see services/findings.py)."""

    severity: str | None = None
    validation_status: str | None = None
    title: str | None = None
    description: str | None = None
    impact: str | None = None
    likelihood: str | None = None
    recommendation: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    affected_url: str | None = None
    owasp_category: str | None = None
    owasp_api_category: str | None = None
    evidence: str | None = None
    request_evidence: str | None = None
    response_evidence: str | None = None
    validation_note: str | None = None


class ScanFindingImportResult(BaseModel):
    imported: int
    findings: list[ScanFindingOut]


class ValidationStatusOut(BaseModel):
    total: int
    confirmed: int
    false_positives: int
    unconfirmed: int = 0
    skipped: int = 0
    validating: int
    unvalidated: int
    status: str  # idle | running | stopped | complete


class PageCredentialViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credential_id: int | None
    username: str | None
    screenshot_b64: str | None
    llm_context: str | None
    page_text: str | None
    req_auth: bool | None
    takes_input: bool | None
    has_object_ref: bool | None
    has_business_logic: bool | None


class ScanStatusOut(BaseModel):
    total_pages: int
    pages_done: int
    findings_count: int
    status: str  # idle | running | complete | stopped | failed


class ScanCheckpointStatusOut(BaseModel):
    """Returned by GET /thinking-scan/checkpoint to tell the UI whether a
    resumable checkpoint exists for this run."""

    exists: bool
    step_count: int | None = None
    updated_at: datetime | None = None
