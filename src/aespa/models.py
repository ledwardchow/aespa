import json
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    event,
    text,
)
from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _run_identity_fk(*, nullable: bool = False) -> Column:
    return Column(
        Integer,
        ForeignKey("run_identity.id", ondelete="CASCADE"),
        nullable=nullable,
        index=True,
    )


def _run_identity_pk() -> Column:
    return Column(
        Integer,
        ForeignKey("run_identity.id", ondelete="CASCADE"),
        primary_key=True,
    )


class RunIdentity(SQLModel, table=True):
    """One globally unique identity shared by web, API, and SAST runs.

    The type-specific run tables retain their existing names and fields, but
    their primary keys now come from this single namespace.  ``legacy_id`` is
    retained only as migration/debug metadata; it is not an owner key.
    """

    __tablename__ = "run_identity"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str = Field(index=True)  # web | api | sast
    legacy_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class PublicReferenceNamespace(SQLModel, table=True):
    """Persistent public-reference namespace for one user-facing run."""

    __tablename__ = "public_reference_namespace"
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", name="uq_public_ref_owner"),
        UniqueConstraint("prefix", name="uq_public_ref_prefix"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_type: str = Field(index=True)  # web | api | sast | campaign
    owner_id: int = Field(index=True)
    prefix: str = Field(index=True, min_length=4, max_length=4)
    next_number: int = Field(default=1)
    created_at: datetime = Field(default_factory=_utcnow)


# ── Site / Credential ─────────────────────────────────────────────────────────


class AuthMode(str, Enum):
    auto = "auto"  # existing single-page Playwright form fill
    totp = "totp"  # auto + TOTP 2FA code from stored seed
    email_otp = "email_otp"  # auto + OTP read from a test mailbox page
    entra_id = "entra_id"  # Microsoft Entra ID multi-page browser flow
    guided = "guided"  # open headed browser, user logs in manually


class Site(SQLModel, table=True):
    __tablename__ = "site"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    base_url: str
    requires_auth: bool = Field(default=False)
    login_url: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    scan_guidance: Optional[str] = Field(default=None)  # Test Lead guidance
    scope_hosts: Optional[str] = Field(default=None)  # JSON list of host:port authorities
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    credentials: List["Credential"] = Relationship(
        back_populates="site",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Credential(SQLModel, table=True):
    __tablename__ = "credential"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id", index=True)
    username: str
    password: str  # plaintext — local pentesting tool
    # Optional JSON list of named login fields.  ``NULL`` means this is a legacy
    # username/password credential; the API presents those two columns as fields
    # without rewriting existing rows.
    login_fields_json: Optional[str] = Field(default=None)
    label: Optional[str] = Field(default=None)
    login_url: Optional[str] = Field(default=None)
    # ── Advanced auth fields ──────────────────────────────────────────────────
    auth_mode: str = Field(default=AuthMode.auto)
    totp_seed: Optional[str] = Field(
        default=None
    )  # base32 TOTP secret (write-only; not returned by API)
    test_mailbox_url: Optional[str] = Field(default=None)

    site: Optional[Site] = Relationship(back_populates="credentials")


# ── API Collection ────────────────────────────────────────────────────────────


class ApiCollection(SQLModel, table=True):
    """A collection of APIs to be security-tested, defined from uploaded docs.

    Parallel top-level entity to ``Site`` but targets a set of API endpoints
    rather than a crawlable web application.
    """

    __tablename__ = "api_collection"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    base_url: str
    description: Optional[str] = Field(default=None)
    servers: Optional[str] = Field(
        default=None
    )  # JSON list of additional server base URLs
    scope_hosts: Optional[str] = Field(default=None)  # JSON list of host:port authorities
    auth_summary_json: Optional[str] = Field(
        default=None
    )  # security schemes from parsed specs
    readiness_json: Optional[str] = Field(
        default=None
    )  # latest readiness assessment result
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ApiDocument(SQLModel, table=True):
    """An uploaded documentation file attached to an ``ApiCollection``.

    The raw bytes are stored on disk (``stored_path``); only metadata lives in
    the DB. Parsing into endpoints is performed in a later slice — until then
    ``status`` stays ``uploaded``.
    """

    __tablename__ = "api_document"

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: int = Field(foreign_key="api_collection.id", index=True)
    filename: str
    doc_type: str = Field(
        default="unknown"
    )  # openapi|swagger|postman|freetext|credentials|source_zip|unknown
    content_type: Optional[str] = Field(default=None)
    stored_path: str  # absolute path to the stored file
    size_bytes: int = Field(default=0)
    status: str = Field(default="uploaded")  # uploaded|parsed|failed
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class ApiEndpoint(SQLModel, table=True):
    """A single API endpoint discovered by parsing an ``ApiDocument``.

    This is the attack-surface unit for API test runs (Slices 6+).
    """

    __tablename__ = "api_endpoint"

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: int = Field(foreign_key="api_collection.id", index=True)
    source_doc_id: Optional[int] = Field(default=None, foreign_key="api_document.id")
    method: str  # GET, POST, PUT, …
    path: str  # /v1/widgets/{id}
    base_url: Optional[str] = Field(default=None)
    operation_id: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    parameters_json: str = Field(default="[]")  # [{name, in, required, schema}]
    request_body_schema_json: str = Field(default="{}")
    response_schema_json: str = Field(default="{}")
    security_json: str = Field(default="[]")  # [{"BearerAuth": []}]
    auth_required: bool = Field(default=False)
    tags_json: str = Field(default="[]")
    sample_request_json: str = Field(
        default="{}"
    )  # populated from examples / Postman bodies
    in_scope: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    # Slice 4 — readiness assessment results
    prereq_can_test: bool = Field(default=True)  # enough info to send a probe
    prereq_can_test_auth: bool = Field(
        default=True
    )  # have credentials for auth-required paths
    prereq_notes: str = Field(default="[]")  # JSON list of gap strings


class ApiCredential(SQLModel, table=True):
    """An authentication credential attached to an ``ApiCollection``.

    Populated from credentials/bearer files (Slice 3c) or entered manually.
    """

    __tablename__ = "api_credential"

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: int = Field(foreign_key="api_collection.id", index=True)
    scheme: str = Field(default="bearer")  # bearer|apikey|basic|cookie|header|login
    name: str = Field(
        default="Authorization"
    )  # header/param name; for login: the auth endpoint path
    value: str  # plaintext — local pentesting tool
    label: Optional[str] = Field(default=None)
    scope: str = Field(default="global")  # global|endpoint
    endpoint_id: Optional[int] = Field(default=None, foreign_key="api_endpoint.id")
    auth_endpoint: Optional[str] = Field(
        default=None
    )  # for login scheme: path of the token endpoint
    created_at: datetime = Field(default_factory=_utcnow)


# ── API Test Run ───────────────────────────────────────────────────────────────


class ApiTestRun(SQLModel, table=True):
    """A security test run against an ``ApiCollection``.

    Parallel to ``TestRun`` (which targets a Site) but operates against
    ``ApiEndpoint`` units rather than ``CrawledPage`` units.  The run id is
    used directly by the existing Alice / events / agent-log infrastructure
    (``AliceChatSession.test_run_id``, ``AgentLog.test_run_id``, etc.) via
    alias routes added in Slice 5.
    """

    __tablename__ = "api_test_run"

    id: Optional[int] = Field(default=None, sa_column=_run_identity_pk())
    collection_id: int = Field(foreign_key="api_collection.id", index=True)
    name: str
    status: str = Field(
        default="pending"
    )  # pending|running|completed|incomplete|failed|cancelled
    llm_config_id: Optional[int] = Field(default=None, foreign_key="llm_config.id")
    # Per-run model-mixing profile (null = use the globally active profile).
    llm_profile_id: Optional[int] = Field(default=None, foreign_key="llm_profile.id")
    coverage_mode: str = Field(
        default="track"
    )  # track (Quick) | enforce (Full) | sast_validate
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    recon_summary_json: Optional[str] = Field(default=None)
    token_usage_json: Optional[str] = Field(default=None)
    phase: str = Field(
        default="created",
        sa_column=Column(String, nullable=False, server_default=text("'created'")),
    )  # created|crawling|crawled|scanning|reporting|validating|finished
    outcome: Optional[str] = Field(
        default=None
    )  # complete|incomplete|failed|stopped|null
    terminal_reason: Optional[str] = Field(
        default=None
    )  # coverage_complete|model_done_rejected|stagnation|non_tool_loop|provider_error|user_stop|coverage_budget_exhausted
    # Legacy soft back-reference retained for imported databases; new API runs
    # use explicit run-owned ScanLead imports instead.
    sast_run_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    # Passive WAF/bot-manager fingerprint — see TestRun.waf_provider.
    waf_provider: Optional[str] = Field(default=None)
    waf_confidence: Optional[str] = Field(default=None)
    waf_evidence: Optional[str] = Field(default=None)


# ── API Endpoint Test (coverage matrix cell) ──────────────────────────────────


class ApiEndpointTest(SQLModel, table=True):
    """One coverage-matrix cell: a (ApiTestRun, ApiEndpoint, OWASP API category) triple.

    Seeded at scan start for every in-scope endpoint × applicable category
    (all API1–API10 in track mode).  Status progresses as the scan runs.
    """

    __tablename__ = "api_endpoint_test"

    id: Optional[int] = Field(default=None, primary_key=True)
    api_test_run_id: int = Field(sa_column=_run_identity_fk())
    endpoint_id: int = Field(foreign_key="api_endpoint.id", index=True)
    owasp_api_category: str  # API1 … API10
    status: str = Field(
        default="not_started"
    )  # not_started|in_progress|covered|skipped|finding
    skip_reason: Optional[str] = Field(default=None)
    finding_ids_json: str = Field(default="[]")  # JSON list of ScanFinding.id
    last_updated: datetime = Field(default_factory=_utcnow)


# ── LLM config ────────────────────────────────────────────────────────────────


class LLMProviderAPI(str, Enum):
    anthropic = "anthropic"
    factory_droid = "factory_droid"
    github_copilot = "github_copilot"
    openai_codex = "openai_codex"
    google_antigravity = "google_antigravity"
    openai = "openai"
    openai_compatible = "openai_compatible"
    openrouter = "openrouter"
    google = "google"
    bedrock = "bedrock"
    bedrock_mantle = "bedrock_mantle"
    azure_openai = "azure_openai"
    azure_foundry = "azure_foundry"
    azure_foundry_openai = "azure_foundry_openai"
    azure_foundry_anthropic = "azure_foundry_anthropic"


class LLMProviderConfig(SQLModel, table=True):
    """Reusable LLM provider connection settings."""

    __tablename__ = "llm_provider_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="Default Provider", index=True)
    api_format: str = Field(default=LLMProviderAPI.anthropic)
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    # Optional Copilot CLI account login. Blank uses Copilot CLI's default.
    username: Optional[str] = Field(default=None)
    # Bedrock Mantle project id (proj_…); sent as the OpenAI-Project header for
    # cost/usage attribution. Ignored by other provider formats.
    project_id: Optional[str] = Field(default=None)
    models_json: str = Field(default="[]")
    # Per-model capability metadata discovered from the provider or OpenRouter.
    # Kept as JSON so providers can add metadata without another migration.
    model_capabilities_json: str = Field(default="{}")
    max_tpm: Optional[int] = Field(default=None, nullable=True)
    max_rpm: Optional[int] = Field(default=None, nullable=True)
    updated_at: datetime = Field(default_factory=_utcnow)


class CodexIntegrationConfig(SQLModel, table=True):
    """Global local Codex CLI setting.

    Codex owns the ChatGPT credentials in its normal CLI home. AESPA only
    remembers an optional executable path.
    """

    __tablename__ = "codex_integration_config"

    id: Optional[int] = Field(default=1, primary_key=True)
    executable_path: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=_utcnow)


class LLMUsageMonth(SQLModel, table=True):
    """Independent monthly LLM usage ledger.

    This table deliberately has no foreign keys to runs or provider settings:
    usage must survive scan deletion and model/provider configuration changes.
    ``month`` is a local-calendar ``YYYY-MM`` key, chosen when the provider
    reports usage.
    """

    __tablename__ = "llm_usage_month"
    __table_args__ = (
        UniqueConstraint("month", "provider", "model", name="uq_llm_usage_month_key"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    month: str = Field(index=True)
    provider: str = Field(index=True)
    model: str = Field(index=True)
    base_url: Optional[str] = Field(default=None, nullable=True)
    requests: int = Field(default=0)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cache_read_tokens: int = Field(default=0)
    cache_write_tokens: int = Field(default=0)
    ai_credits: float = Field(default=0.0)
    factory_credits: float = Field(default=0.0)
    input_price_usd_per_million: Optional[float] = Field(default=None, nullable=True)
    output_price_usd_per_million: Optional[float] = Field(default=None, nullable=True)
    cache_read_price_usd_per_million: Optional[float] = Field(
        default=None, nullable=True
    )
    cache_write_price_usd_per_million: Optional[float] = Field(
        default=None, nullable=True
    )
    credit_price_usd_per_million: Optional[float] = Field(default=None, nullable=True)
    credit_unit: Optional[str] = Field(default=None, nullable=True)
    price_source: Optional[str] = Field(default=None, nullable=True)
    price_confidence: Optional[str] = Field(default=None, nullable=True)
    manual_override: bool = Field(default=False)
    price_updated_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class LLMPriceCatalog(SQLModel, table=True):
    """Latest reusable price data for future monthly usage rows."""

    __tablename__ = "llm_price_catalog"
    __table_args__ = (
        UniqueConstraint("provider", "model", name="uq_llm_price_catalog_key"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(index=True)
    model: str = Field(index=True)
    input_price_usd_per_million: Optional[float] = Field(default=None, nullable=True)
    output_price_usd_per_million: Optional[float] = Field(default=None, nullable=True)
    cache_read_price_usd_per_million: Optional[float] = Field(
        default=None, nullable=True
    )
    cache_write_price_usd_per_million: Optional[float] = Field(
        default=None, nullable=True
    )
    credit_price_usd_per_million: Optional[float] = Field(default=None, nullable=True)
    credit_unit: Optional[str] = Field(default=None, nullable=True)
    price_source: Optional[str] = Field(default=None, nullable=True)
    price_confidence: Optional[str] = Field(default=None, nullable=True)
    manual_override: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=_utcnow)


class LLMPriceFeed(SQLModel, table=True):
    """The last downloaded raw price map, retained for offline matching."""

    __tablename__ = "llm_price_feed"

    id: Optional[int] = Field(default=1, primary_key=True)
    source_url: str
    payload_json: str
    fetched_at: datetime = Field(default_factory=_utcnow)


class LLMConfig(SQLModel, table=True):
    """Saved LLM settings profile."""

    __tablename__ = "llm_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="Default", index=True)
    is_active: bool = Field(default=False, index=True)
    provider_id: Optional[int] = Field(
        default=None, foreign_key="llm_provider_config.id", index=True
    )
    provider: str = Field(default=LLMProviderAPI.anthropic)
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    # Denormalized from the provider for the Copilot SDK adapter.
    username: Optional[str] = Field(default=None)
    # Denormalized from the provider (see LLMProviderConfig.project_id).
    project_id: Optional[str] = Field(default=None)
    model: str = Field(default="claude-opus-4-5")
    max_tokens: int = Field(default=70000)
    temperature: Optional[float] = Field(default=None)
    # Explicit reasoning/thinking level. None means provider default (legacy behavior).
    reasoning_effort: Optional[str] = Field(default=None, nullable=True)
    # Whether to include page screenshots in LLM prompts (requires vision model)
    use_vision: bool = Field(default=False)
    # Whether to force tool choice using the wire format tool_choice: required/any
    force_tool_choice: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=_utcnow)


class LLMProfile(SQLModel, table=True):
    """A named per-agent-role model assignment.

    A profile maps each agent role (crawler, test_lead, specialist, …) to an
    ``LLMConfig`` ("Model"), falling back to ``default_model_id`` for roles not
    explicitly overridden. A scan selects a profile via ``*.llm_profile_id``;
    each agent resolves its model through ``get_llm_config_for_role()``.
    """

    __tablename__ = "llm_profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="Default", index=True)
    is_active: bool = Field(default=False, index=True)
    # The Model used for any role without an explicit override.
    default_model_id: Optional[int] = Field(default=None, foreign_key="llm_config.id")
    # JSON: {role: llm_config_id} — only roles overridden away from the default.
    role_models_json: str = Field(default="{}")
    updated_at: datetime = Field(default_factory=_utcnow)


class ScannerPolicy(SQLModel, table=True):
    """Singleton row (id always = 1) for scanner policy defaults."""

    __tablename__ = "scanner_policy"

    id: Optional[int] = Field(default=None, primary_key=True)
    execution_monitor_enabled: bool = Field(default=False)
    disable_deterministic_checks: bool = Field(default=False)
    max_consecutive_text_turns: int = Field(default=0)
    enforce_full_coverage_obligations: bool = Field(default=False)
    scan_mode: str = Field(default="aggressive")
    max_probes_per_page: int = Field(default=50)
    thinking_max_steps: int = Field(default=120)
    request_timeout_s: float = Field(default=10.0)
    min_delay_s: float = Field(default=0.05)
    max_request_body_bytes: int = Field(default=65536)
    response_body_read_limit_bytes: int = Field(default=512 * 1024)
    allowed_schemes: str = Field(default='["http", "https"]')
    methods_by_mode: str = Field(
        default='{"passive": ["GET", "HEAD"], "safe_active": ["GET", "POST", "HEAD"], "aggressive": ["GET", "POST", "PUT", "PATCH", "HEAD", "OPTIONS"], "destructive": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]}'
    )
    blocked_headers: str = Field(default='["host", "cookie"]')
    follow_redirects: bool = Field(default=True)
    allow_subdomains: bool = Field(default=True)
    require_approval_for_destructive: bool = Field(default=True)
    strict_locator_enforcement: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=_utcnow)


class CrawlerConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for crawler behavior settings."""

    __tablename__ = "crawler_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    js_endpoint_discovery_enabled: bool = Field(default=False)
    skip_dangerous_actions: bool = Field(default=True)
    suppress_form_submit_actions: bool = Field(default=True)
    block_non_idempotent_interactive_replay: bool = Field(default=True)
    enable_access_reconciliation: bool = Field(default=False)
    llm_max_concurrency: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
        description="Max concurrent LLM page analysis requests (None = unlimited)",
    )
    updated_at: datetime = Field(default_factory=_utcnow)


class ComponentMapperConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for component-mapper budgets."""

    __tablename__ = "component_mapper_config"

    id: Optional[int] = Field(default=1, primary_key=True)
    max_tool_calls: int = Field(default=250)
    max_source_files: int = Field(default=500)
    max_source_bytes: int = Field(default=50 * 1024 * 1024)
    max_facts: int = Field(default=500)
    max_concurrent: int = Field(default=4)
    max_trace_edges: int = Field(default=8)
    max_trace_components: int = Field(default=6)
    max_paths_per_lead: int = Field(default=10)
    min_trace_confidence: float = Field(default=0.50)
    updated_at: datetime = Field(default_factory=_utcnow)


class BurpRestApiConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for Burp Suite REST API integration settings."""

    __tablename__ = "burp_rest_api_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    enabled: bool = Field(default=False)
    api_url: str = Field(default="http://127.0.0.1:1337")
    api_key: Optional[str] = Field(default=None)
    scan_configuration_name: Optional[str] = Field(
        default="Audit checks - all except time-based detection methods"
    )
    # Vulnerability classes to route to Burp active scan
    scan_sqli: bool = Field(default=True)
    scan_xss: bool = Field(default=True)
    scan_command_injection: bool = Field(default=True)
    scan_path_traversal: bool = Field(default=True)
    scan_ssrf: bool = Field(default=True)
    scan_xxe: bool = Field(default=True)
    scan_ssti: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=_utcnow)


class UpstreamProxyConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for upstream proxy settings."""

    __tablename__ = "upstream_proxy_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    proxy_url: Optional[str] = Field(default=None)
    proxy_scanner: bool = Field(default=False)
    proxy_llm: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=_utcnow)


class SpecialistAgentConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for specialist agent dispatch settings."""

    __tablename__ = "specialist_agent_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    enabled: bool = Field(default=True)
    max_concurrent: int = Field(default=5)
    max_steps: int = Field(default=30)
    min_priority: int = Field(default=7)
    # Per attack-class dispatch toggles
    dispatch_idor: bool = Field(default=True)
    dispatch_auth_bypass: bool = Field(default=True)
    dispatch_sqli: bool = Field(default=True)
    dispatch_xss: bool = Field(default=True)
    dispatch_business_logic: bool = Field(default=True)
    dispatch_ssrf: bool = Field(default=True)
    dispatch_path_traversal: bool = Field(default=True)
    dispatch_cors: bool = Field(default=False)
    dispatch_crypto: bool = Field(default=True)
    dispatch_config: bool = Field(default=False)
    dispatch_file_upload: bool = Field(default=True)
    trigger_specialist_on_burp: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=_utcnow)


class AdversarialValidatorConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for adversarial validator settings."""

    __tablename__ = "adversarial_validator_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Global switch — False falls back to the legacy static-probe mode.
    enabled: bool = Field(default=True)
    # Step budget per finding in adversarial mode.
    max_steps: int = Field(default=20)
    # Skip validation for findings below this severity: critical|high|medium|low|info
    min_severity: str = Field(default="low")
    # Maximum simultaneous validators for manual and end-of-scan validation.
    end_scan_max_concurrent: int = Field(default=4)
    # When True, automatically validate each finding immediately after it is written
    # during a dynamic scan.  When False, validation is only triggered manually.
    auto_validate_inline: bool = Field(default=True)
    # When True (strict mode), only return a false_positive verdict when the validator
    # finds a *concrete* innocent explanation.  When False (lenient), failure to
    # reproduce the finding is treated as a false positive.
    require_concrete_disproof: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=_utcnow)


class GlobalHttpHeaderConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for global headers sent by scanners and crawlers."""

    __tablename__ = "global_http_header_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    # JSON array of {"header_name": "...", "header_value": "..."}. The two
    # legacy columns remain so existing databases can be upgraded without losing
    # their configured header.
    headers_json: str = Field(default="[]")
    header_name: Optional[str] = Field(default=None, max_length=200)
    header_value: Optional[str] = Field(default=None, max_length=2000)
    updated_at: datetime = Field(default_factory=_utcnow)


class ReportingDebugConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for reporting prompt debug features."""

    __tablename__ = "reporting_debug_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    capture_enabled: bool = Field(default=False)
    panel_enabled: bool = Field(default=False)
    batch_max_concurrent: int = Field(default=4)
    updated_at: datetime = Field(default_factory=_utcnow)


class BrowserDebugConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for Playwright browser debug settings."""

    __tablename__ = "browser_debug_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    browser_engine: str = Field(default="playwright_chromium")
    browser_visible: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=_utcnow)


class CloudflareAccessConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for Cloudflare Access JWT verification.

    ``audience`` is the optional Access application AUD tag. When set, the
    proxy-injected JWT is verified against it; when empty, audience checking is
    skipped (the legacy behaviour).
    """

    __tablename__ = "cloudflare_access_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    audience: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=_utcnow)


# ── Test runs ─────────────────────────────────────────────────────────────────


class TestRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    incomplete = "incomplete"
    failed = "failed"
    stopped = "stopped"
    paused = "paused"


class TestRun(SQLModel, table=True):
    __tablename__ = "test_run"

    id: Optional[int] = Field(default=None, sa_column=_run_identity_pk())
    site_id: int = Field(foreign_key="site.id", index=True)
    name: str
    status: str = Field(default=TestRunStatus.pending)
    # Crawl config
    use_screenshots: bool = Field(default=False)
    max_depth: int = Field(default=3)
    max_pages: int = Field(default=500)
    llm_max_concurrency: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
        description="Max concurrent LLM page analysis requests (None = unlimited)",
    )
    # ``url`` preserves the legacy link-following crawler. ``interactive`` also
    # records safe, reproducible browser states and conditional workflows.
    crawler_mode: str = Field(
        default="url",
        sa_column=Column(String, nullable=False, server_default=text("'url'")),
    )
    scan_mode: str = Field(default="aggressive")
    scanner_policy_json: str = Field(default="{}")
    # Progress
    pages_discovered: int = Field(default=0)
    current_url: Optional[str] = Field(default=None)
    # JSON: {username: {current_url, pages_visited}} — one entry per crawling credential
    per_user_progress: Optional[str] = Field(default=None)
    # Timestamps
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    # Optional per-run LLM model override (null = use the globally active one)
    llm_config_id: Optional[int] = Field(default=None, foreign_key="llm_config.id")
    # Per-run model-mixing profile (null = use the globally active profile).
    llm_profile_id: Optional[int] = Field(default=None, foreign_key="llm_profile.id")
    # Cached JSON attack-surface/coverage projection; the UI rebuilds it live.
    recon_summary: Optional[str] = Field(default=None)
    # Persisted token usage, including per-model estimated costs.
    token_usage_json: Optional[str] = Field(default=None)
    # Reproducibility metadata captured when the dynamic scan starts. Secrets and
    # provider connection details are intentionally excluded.
    execution_snapshot_json: Optional[str] = Field(default=None)
    # Compact operational metrics used to compare scanner architecture versions.
    scan_metrics_json: Optional[str] = Field(default=None)
    # Coverage mode: "track" (Quick), "enforce" (Full), or "sast_validate".
    coverage_mode: str = Field(
        default="track",
        sa_column=Column(String, nullable=False, server_default=text("'track'")),
    )
    phase: str = Field(
        default="created",
        sa_column=Column(String, nullable=False, server_default=text("'created'")),
    )  # created|crawling|crawled|scanning|reporting|validating|finished
    outcome: Optional[str] = Field(
        default=None
    )  # complete|incomplete|failed|stopped|null
    terminal_reason: Optional[str] = Field(
        default=None
    )  # coverage_complete|model_done_rejected|stagnation|non_tool_loop|provider_error|user_stop|coverage_budget_exhausted
    # Passive WAF/bot-manager fingerprint (see services/waf_detect.py), set the
    # first time a response carries an identifiable marker (e.g. Akamai's
    # bm_sz cookie or edge denial page). Surfaced on the Attack Surface tab and
    # used by the scan loop to route http_request calls through the browser
    # context instead of a raw httpx client, since a bare TLS client can never
    # pass a JS-based bot challenge.
    waf_provider: Optional[str] = Field(default=None)
    waf_confidence: Optional[str] = Field(default=None)  # "high" | "medium"
    waf_evidence: Optional[str] = Field(default=None)
    # When set, the crawl runs as this single credential only (no anon phase,
    # no other credentials).  NULL = crawl all phases (default behaviour).
    crawl_credential_id: Optional[int] = Field(
        default=None, foreign_key="credential.id"
    )
    # JSON list of page IDs for a deliberate state-focused scan. Empty/NULL
    # means the normal full-site scan. This is persisted so a queued sitemap
    # action survives a worker restart and is visible to the Test Lead.
    target_page_ids_json: Optional[str] = Field(default=None)
    target_session_label: Optional[str] = Field(default=None)

    @property
    def target_page_ids(self) -> list[int]:
        try:
            values = json.loads(self.target_page_ids_json or "[]")
            return [int(value) for value in values if str(value).isdigit()]
        except (TypeError, ValueError, json.JSONDecodeError):
            return []


class CrawledPage(SQLModel, table=True):
    __tablename__ = "crawled_page"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    url: str = Field(index=True)
    # URL is evidence/a navigation hint, not necessarily identity for SPA views.
    state_key: Optional[str] = Field(default=None, index=True)
    # Canonical, credential-neutral functionality label used in the site map.
    state_label: Optional[str] = Field(default=None)
    state_kind: str = Field(default="url")  # url | interactive | api
    replay_steps_json: str = Field(default="[]")
    # Credential that first reached this state.  Replay uses this identity by
    # default and never silently substitutes another user.
    replay_credential_id: Optional[int] = Field(
        default=None, foreign_key="credential.id", index=True
    )
    title: Optional[str] = Field(default=None)
    page_text: Optional[str] = Field(default=None)  # truncated ~10k chars
    screenshot_b64: Optional[str] = Field(default=None)
    llm_context: Optional[str] = Field(default=None)
    depth: int = Field(default=0)
    status: str = Field(default="crawled")  # crawled | failed | redirect
    error_message: Optional[str] = Field(default=None)
    in_scope: bool = Field(default=True)
    scan_status: str = Field(default="pending")  # pending | running | complete
    # LLM-assessed page categories (populated after analysis)
    req_auth: Optional[bool] = Field(default=None)  # Authentication Required
    takes_input: Optional[bool] = Field(default=None)  # Takes User Input
    has_object_ref: Optional[bool] = Field(default=None)  # Contains Object Reference
    has_business_logic: Optional[bool] = Field(
        default=None
    )  # Contains Business Functionality
    accessible_by: str = Field(
        default="[]"
    )  # JSON list of credential IDs that can access this page
    owasp_applicable_json: str = Field(
        default="{}"
    )  # JSON {A01: bool, …} OWASP Top 10:2025 applicability
    discovered_at: datetime = Field(default_factory=_utcnow)

    @property
    def owasp_applicable(self) -> dict:
        try:
            return json.loads(self.owasp_applicable_json or "{}")
        except Exception:
            return {}


class PageOwaspTest(SQLModel, table=True):
    """One cell in the web workprogram: a (TestRun, CrawledPage, OWASP category) triple.

    Seeded at scan start (or manually via the /coverage/seed endpoint).
    Status is persisted and updated as the scan runs.
    """

    __tablename__ = "page_owasp_test"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    page_id: int = Field(foreign_key="crawled_page.id", index=True)
    owasp_category: str  # A01 … A10
    status: str = Field(
        default="not_started"
    )  # not_started|in_progress|covered|skipped|finding
    skip_reason: Optional[str] = Field(default=None)
    finding_ids_json: str = Field(default="[]")  # JSON list of ScanFinding.id
    test_classes_json: str = Field(
        default="{}"
    )  # JSON {test_class: {status, finding_ids, last_updated}}
    last_updated: Optional[datetime] = Field(default_factory=_utcnow)
    created_at: datetime = Field(default_factory=_utcnow)


class PageLink(SQLModel, table=True):
    """Directed edge in the crawl graph: source page → target page."""

    __tablename__ = "page_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    source_page_id: int = Field(foreign_key="crawled_page.id", index=True)
    target_page_id: Optional[int] = Field(default=None, foreign_key="crawled_page.id")
    target_url: str
    link_text: Optional[str] = Field(default=None)
    action_kind: str = Field(default="navigate")
    action_data_json: str = Field(default="{}")
    # Shared with traffic rows so an interactive browser action can be tied to
    # the requests it caused, rather than to any request on the same page.
    interaction_id: Optional[str] = Field(default=None, index=True)


class TrafficEntry(SQLModel, table=True):
    """One HTTP request/response pair captured during a crawl or scan."""

    __tablename__ = "traffic_entry"

    id: Optional[int] = Field(default=None, primary_key=True)
    # API traffic is owned by api_test_run_id and has no web-run owner.
    test_run_id: Optional[int] = Field(
        default=None, sa_column=_run_identity_fk(nullable=True)
    )
    api_test_run_id: Optional[int] = Field(
        default=None, sa_column=_run_identity_fk(nullable=True)
    )  # set for API scan traffic
    source: str  # "playwright" | "httpx"
    created_at: datetime = Field(default_factory=_utcnow)
    method: str
    url: str
    request_headers: str = Field(default="{}")  # JSON
    request_body: Optional[str] = Field(default=None)
    status: Optional[int] = Field(default=None)
    response_headers: str = Field(default="{}")  # JSON
    response_body: Optional[str] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None)
    username: Optional[str] = Field(
        default=None
    )  # credential username that made the request
    # Optional page/session provenance.  URL matching remains a legacy fallback,
    # but interactive states sharing one URL need these explicit associations.
    page_id: Optional[int] = Field(
        default=None,
        foreign_key="crawled_page.id",
        index=True,
    )
    session_label: Optional[str] = Field(default=None, index=True)
    # Opaque id for one replayed browser action. Page-load traffic has no id.
    interaction_id: Optional[str] = Field(default=None, index=True)


class ScannerSession(SQLModel, table=True):
    """Reusable scanner session material discovered or configured during a run."""

    __tablename__ = "scanner_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    # Retained as a surface discriminator for compatibility and filtering.
    run_kind: str = Field(default="web", index=True)  # "web" | "api"
    label: str = Field(
        index=True
    )  # anonymous | configured_primary | forged_admin | ...
    kind: str = Field(
        default="cookie", index=True
    )  # anonymous | cookie | bearer | mixed
    account_label: Optional[str] = Field(default=None, index=True)
    username: Optional[str] = Field(default=None, index=True)
    credential_id: Optional[int] = Field(
        default=None, foreign_key="credential.id", index=True
    )
    source: str = Field(default="scanner")
    cookies_json: str = Field(default="{}")
    extra_headers_json: str = Field(default="{}")
    session_metadata: str = Field(default="{}")
    token_hint: Optional[str] = Field(default=None)
    token_fingerprint: Optional[str] = Field(default=None, index=True)
    lifecycle_state: str = Field(
        default="candidate", index=True
    )  # candidate | verified | active | invalid
    validation_url: Optional[str] = Field(default=None)
    last_status: Optional[int] = Field(default=None)
    last_validated_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class PageCredentialView(SQLModel, table=True):
    """Per-credential snapshot of a crawled page: screenshot, LLM context, and raw categories."""

    __tablename__ = "page_credential_view"

    id: Optional[int] = Field(default=None, primary_key=True)
    page_id: int = Field(foreign_key="crawled_page.id", index=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    credential_id: Optional[int] = Field(default=None)
    username: Optional[str] = Field(default=None)
    screenshot_b64: Optional[str] = Field(default=None)
    llm_context: Optional[str] = Field(default=None)
    page_text: Optional[str] = Field(default=None)
    req_auth: Optional[bool] = Field(default=None)
    takes_input: Optional[bool] = Field(default=None)
    has_object_ref: Optional[bool] = Field(default=None)
    has_business_logic: Optional[bool] = Field(default=None)
    owasp_applicable_json: str = Field(default="{}")  # JSON {A01: bool, …}


class TargetIntelItem(SQLModel, table=True):
    """Normalized target intelligence discovered during crawl and recon."""

    __tablename__ = "target_intel_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    kind: str = Field(
        index=True
    )  # endpoint | form | input | script | storage_key | id | token_hint | response_field
    key: str = Field(
        default="", index=True
    )  # stable label, e.g. route path, field name, script URL
    value: str = Field(default="")  # extracted value or display text
    url: Optional[str] = Field(default=None, index=True)
    method: Optional[str] = Field(default=None)
    source: str = Field(
        default="crawler"
    )  # dom | api_observation | js_asset | response_body
    confidence: float = Field(default=1.0)
    evidence: str = Field(default="")
    item_metadata: str = Field(default="{}")
    page_id: Optional[int] = Field(
        default=None, foreign_key="crawled_page.id", index=True
    )
    discovered_at: datetime = Field(default_factory=_utcnow)


class ScanFinding(SQLModel, table=True):
    """A security vulnerability found during an active scan."""

    __tablename__ = "scan_finding"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Stable user-facing reference. Database ``id`` remains the internal key
    # used by existing API mutation endpoints and scanner bookkeeping.
    public_reference: Optional[str] = Field(default=None, index=True)
    # Structured origin/provenance for findings that came from SAST or another
    # lead source. The owning test_run/api_test_run remains the run that holds
    # and, where applicable, validated the finding.
    origin_type: Optional[str] = Field(default=None, index=True)
    origin_run_type: Optional[str] = Field(default=None, index=True)
    origin_run_id: Optional[int] = Field(default=None, index=True)
    origin_lead_id: Optional[int] = Field(default=None, index=True)
    origin_reference: Optional[str] = Field(default=None)
    # Nullable: a finding belongs to EITHER a web TestRun (test_run_id) OR an
    # ApiTestRun (api_test_run_id), never both.  The two tables have independent
    # Both columns now reference the single global run-identity namespace.
    test_run_id: Optional[int] = Field(
        default=None, sa_column=_run_identity_fk(nullable=True)
    )
    page_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("crawled_page.id"),
            index=True,
            nullable=True,
        ),
    )
    owasp_category: str = Field(index=True)  # "A01" … "A10"
    severity: str  # critical | high | medium | low | info
    title: str
    description: str
    impact: str = Field(default="")
    likelihood: str = Field(default="")
    recommendation: str = Field(default="")
    cvss_score: float = Field(default=0.0)
    cvss_vector: str = Field(default="")
    affected_url: str = Field(default="")  # specific URL where the issue was observed
    evidence: str = Field(default="")  # formatted request + response excerpt
    request_evidence: str = Field(default="")
    response_evidence: str = Field(default="")
    evidence_json: str = Field(default="[]")
    merged_instances: str = Field(
        default="[]"
    )  # JSON list of consolidated cross-URL instances
    # Verified proof-of-concept: a runnable one-line validation command and optional
    # setup instructions. Populated only when the command was re-run server-side and
    # proven to reproduce the finding; otherwise left blank.
    poc_command: str = Field(default="")
    poc_setup: str = Field(default="")
    screenshot_b64: Optional[str] = Field(default=None)  # base64 PNG (form probes only)
    finding_source: str = Field(default="unknown", index=True)
    # Validation fields
    validation_status: str = Field(
        default="unvalidated"
    )  # unvalidated | validating | skipped | confirmed | unconfirmed | false_positive
    validation_note: Optional[str] = Field(
        default=None
    )  # LLM reasoning from validation
    # API test run attribution (nullable — only set for findings from API runs)
    api_test_run_id: Optional[int] = Field(
        default=None, sa_column=_run_identity_fk(nullable=True)
    )
    owasp_api_category: Optional[str] = Field(
        default=None, index=True
    )  # "API1" … "API10"
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def evidence_items(self) -> list[dict]:
        try:
            parsed = json.loads(self.evidence_json or "[]")
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    @property
    def reference(self) -> str:
        return self.public_reference or ""

    @property
    def origin(self) -> dict | None:
        if not self.origin_type and not self.origin_reference:
            return None
        label = {
            "sast": "SAST",
            "campaign": "Campaign",
            "dynamic": "Dynamic",
            "api": "API",
        }.get(self.origin_type or "", self.origin_type or "Unknown")
        return {
            "type": self.origin_type,
            "label": label,
            "run_type": self.origin_run_type,
            "run_id": self.origin_run_id,
            "lead_id": self.origin_lead_id,
            "reference": self.origin_reference,
        }

    @property
    def validated_by(self) -> dict | None:
        if self.origin_type not in {"sast", "campaign"}:
            return None
        if self.test_run_id is not None:
            return {"type": "web", "label": "Dynamic scan", "run_id": self.test_run_id}
        if self.api_test_run_id is not None:
            return {"type": "api", "label": "API scan", "run_id": self.api_test_run_id}
        return None


class CampaignFindingReference(SQLModel, table=True):
    """Stable campaign-local alias for a finding owned by a child run."""

    __tablename__ = "campaign_finding_reference"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "finding_id", name="uq_campaign_finding_reference"
        ),
        UniqueConstraint(
            "campaign_id", "public_reference", name="uq_campaign_public_reference"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(sa_column=_run_identity_fk())
    finding_id: int = Field(foreign_key="scan_finding.id", index=True)
    target_member_id: int = Field(foreign_key="campaign_target_member.id", index=True)
    public_reference: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class ScanLog(SQLModel, table=True):
    """Persisted scanner_phase event so the activity log survives page navigation."""

    __tablename__ = "scan_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    # Retained as a surface discriminator for compatibility and filtering.
    run_kind: str = Field(default="web", index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    phase: str  # thinking_step | site_plan | page_plan | …
    status: str = Field(default="")  # start | complete | running | deciding | …
    message: str = Field(default="")
    page_url: Optional[str] = Field(default=None)
    data_json: Optional[str] = Field(default=None)  # JSON blob for extra phase data


class ScanCheckpoint(SQLModel, table=True):
    """Persisted snapshot of the agentic loop state so an interrupted dynamic
    scan can be resumed exactly where it left off.

    One row per test_run (unique on test_run_id).  Upserted after every LLM
    turn so a crash loses at most one turn of work.
    """

    __tablename__ = "scan_checkpoint"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("run_identity.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            unique=True,
        )
    )
    # Full Anthropic multi-turn messages list serialised as JSON.
    messages_json: str = Field(default="[]")
    # Action-trace history list used by history_search / endpoint_detail context tools.
    history_json: str = Field(default="[]")
    # Serialised set of URLs that have failed 3+ times.
    blocked_urls_json: str = Field(default="[]")
    # Serialised dict of "METHOD:url" → failure count.
    failed_url_counts_json: str = Field(default="{}")
    # Scalar counters so the loop can resume with identical budget tracking.
    step_count: int = Field(default=0)
    progressive_findings_count: int = Field(default=0)
    consecutive_context_tools: int = Field(default=0)
    # Persisted bounded completion/progress policy; kept separate from the LLM
    # transcript so resume does not forget session attempts or loop protection.
    completion_state_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class RunPause(SQLModel, table=True):
    """A manually resumable pause, usually caused by a subscription quota."""

    __tablename__ = "run_pause"
    __table_args__ = (UniqueConstraint("run_kind", "run_id", name="uq_run_pause"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    run_kind: str = Field(index=True)  # web | api | sast | crawl
    run_id: int = Field(index=True)
    provider: str = Field(default="")
    reason: str = Field(default="quota")
    reset_at: Optional[datetime] = Field(default=None)
    message: str = Field(default="")
    snapshot_json: str = Field(default="{}")
    resume_stage: Optional[str] = Field(default=None)
    paused_at: datetime = Field(default_factory=_utcnow)


class AliceChatSession(SQLModel, table=True):
    """One ALICE chat tab per test run (many per run)."""

    __tablename__ = "alice_chat_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    # See AgentLog.run_kind — separates web-scan and API-scan rows that share the
    # same run_id. "web" | "api".
    run_kind: str = Field(default="web", index=True)
    session_key: str = Field(index=True)  # client-assigned tab ID, e.g. "tab-default"
    title: str = Field(default="Session 1")
    position: int = Field(default=0)  # tab ordering
    is_active: bool = Field(default=False)  # which tab is currently selected
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ── SAST Run ──────────────────────────────────────────────────────────────────


class SastRun(SQLModel, table=True):
    """A static-analysis scan over a source archive in an ApiCollection."""

    __tablename__ = "sast_run"

    id: Optional[int] = Field(default=None, sa_column=_run_identity_pk())
    # Nullable: API SAST runs key on a collection; standalone (web-oriented) runs
    # have no collection and carry their own uploaded archive instead.
    collection_id: Optional[int] = Field(
        default=None, foreign_key="api_collection.id", index=True
    )
    document_id: Optional[int] = Field(
        default=None, index=True
    )  # the source_zip analysed
    # Standalone runs store the uploaded archive directly (no ApiDocument).
    source_archive_path: Optional[str] = Field(
        default=None
    )  # absolute path to stored zip
    source_filename: Optional[str] = Field(default=None)  # original upload filename
    name: str
    status: str = Field(
        default="pending"
    )  # pending|scanning|completed|failed|cancelled
    # What triggered this run: None=standalone, or the dynamic run that spawned it
    triggered_by_run_type: Optional[str] = Field(default=None)  # "api" | "web"
    triggered_by_run_id: Optional[int] = Field(default=None, index=True)
    llm_config_id: Optional[int] = Field(default=None, foreign_key="llm_config.id")
    # Per-run model-mixing profile (null = use the globally active profile).
    llm_profile_id: Optional[int] = Field(default=None, foreign_key="llm_profile.id")
    leads_count: int = Field(default=0)
    # Persisted semantic phase state and deterministic file-review telemetry.
    # JSON keeps the run model compact while allowing the phase contract to
    # evolve without another table for every counter.
    phase_state_json: Optional[str] = Field(default=None)
    coverage_json: Optional[str] = Field(default=None)
    report_json: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    token_usage_json: Optional[str] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ScanLead(SQLModel, table=True):
    """An unproven investigation lead (from a SAST scan). Distinct from ScanFinding."""

    __tablename__ = "scan_lead"

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: Optional[int] = Field(default=None, index=True)
    producer_run_type: str = Field(
        default="sast", index=True
    )  # "sast" (future: "recon")
    producer_run_id: int = Field(index=True)  # SastRun.id that created it
    source: str = Field(default="sast", index=True)
    category: str = Field(default="")  # OWASP A0x / API0x (best-effort)
    severity: str = Field(default="medium")  # high | medium | low
    confidence: float = Field(default=0.0)  # 0..1 from the triage filter
    title: str = Field(default="")
    description: str = Field(default="")
    location: str = Field(default="")  # file:line / endpoint hint
    evidence: str = Field(default="")  # code snippet + data-flow note (from SAST)
    fingerprint: str = Field(default="", index=True)
    suggested_endpoint: str = Field(default="")
    source_trace_json: str = Field(default="{}")
    control_trace_json: str = Field(default="[]")
    sink_trace_json: str = Field(default="{}")
    counterevidence_json: str = Field(default="[]")
    proof_gaps_json: str = Field(default="[]")
    validation_status: str = Field(default="pending", index=True)
    validation_reasoning: str = Field(default="")
    attack_path_json: str = Field(default="{}")
    reportable: bool = Field(default=True, index=True)
    note: str = Field(default="")  # agent investigation outcome note (update_lead)
    status: str = Field(
        default="open", index=True
    )  # open|investigating|confirmed|dismissed|inconclusive
    investigated_by_run_type: Optional[str] = Field(default=None)  # "api" | "web"
    investigated_by_run_id: Optional[int] = Field(default=None)
    linked_finding_id: Optional[int] = Field(
        default=None
    )  # set when promoted to a finding
    # Stable user-facing reference. Original leads use producer_run_* as their
    # namespace; imported copies use imported_into_run_* as their namespace.
    public_reference: Optional[str] = Field(default=None, index=True)
    origin_reference: Optional[str] = Field(default=None)
    # Set on a *copy* imported into a dynamic run (e.g. a web TestRun). Originals
    # leave these NULL; producer_run_id on a copy still points at the source SAST
    # run for provenance. Copies are owned by (imported_into_run_type, _run_id).
    imported_into_run_type: Optional[str] = Field(default=None, index=True)  # "web"
    imported_into_run_id: Optional[int] = Field(default=None, index=True)
    # Origin and bounded path metadata used by campaign/frontend attack-path
    # views. These remain nullable so older standalone leads keep their meaning.
    origin_lead_id: Optional[int] = Field(default=None, index=True)
    trace_path_key: Optional[str] = Field(default=None, index=True)
    trace_status: str = Field(default="none")
    trace_confidence: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @property
    def reference(self) -> str:
        return self.public_reference or ""


# ── Applications & multi-repository campaigns ───────────────────────────────
#
# An Application groups named code components (repositories/micro-frontends),
# their immutable uploaded ZIP snapshots, and the existing Site/ApiCollection
# targets that make up one product. An AssessmentCampaign coordinates ordinary
# SastRun/TestRun/ApiTestRun children for one application, joining the global
# run_identity namespace (kind="campaign") so its events/logs never collide
# with a web/api/sast run id. See docs/architecture.md for the full design.


class Application(SQLModel, table=True):
    __tablename__ = "application"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ApplicationComponent(SQLModel, table=True):
    """A named repository or micro-frontend belonging to an Application."""

    __tablename__ = "application_component"
    __table_args__ = (
        UniqueConstraint("application_id", "name", name="uq_component_app_name"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True)
    name: str
    role: Optional[str] = Field(default=None)  # e.g. "Backend API", "Micro-frontend"
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ComponentSnapshot(SQLModel, table=True):
    """One immutable uploaded ZIP version for an ApplicationComponent.

    Snapshots are never edited in place — uploading again creates a new row so
    a campaign that already froze an older snapshot keeps its exact meaning.
    """

    __tablename__ = "component_snapshot"

    id: Optional[int] = Field(default=None, primary_key=True)
    component_id: int = Field(foreign_key="application_component.id", index=True)
    filename: str
    stored_path: str  # absolute path to the stored zip
    size_bytes: int = Field(default=0)
    sha256: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class ApplicationTarget(SQLModel, table=True):
    """An existing Site or ApiCollection attached to an Application.

    ``target_id`` refers to ``site.id`` or ``api_collection.id`` depending on
    ``target_type`` — the underlying target row is reused, never copied.

    ``component_id`` is an optional explicit ownership link.  When set, a
    campaign automatically imports that component's reportable SAST leads into
    this target's child run; inferred and cross-component leads remain
    review-gated.
    """

    __tablename__ = "application_target"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "target_type", "target_id", name="uq_app_target"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True)
    target_type: str = Field(index=True)  # "site" | "api_collection"
    target_id: int = Field(index=True)
    component_id: Optional[int] = Field(
        default=None, foreign_key="application_component.id", index=True
    )
    created_at: datetime = Field(default_factory=_utcnow)


class ComponentTargetHint(SQLModel, table=True):
    """An optional user-supplied code-to-live-target routing association.

    Purely advisory: it boosts deterministic correlation confidence but is
    never required for a campaign to run.
    """

    __tablename__ = "component_target_hint"
    __table_args__ = (
        UniqueConstraint("component_id", "target_id", name="uq_component_target_hint"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True)
    component_id: int = Field(foreign_key="application_component.id", index=True)
    target_id: int = Field(foreign_key="application_target.id", index=True)
    note: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class AssessmentCampaign(SQLModel, table=True):
    """One coordinated multi-repository test of an Application.

    Joins the global run_identity namespace (kind="campaign") purely so its
    SSE events / AgentLog / ScanLog rows use the shared id space; it does not
    reuse any web/api/sast run behavior directly.
    """

    __tablename__ = "assessment_campaign"

    id: Optional[int] = Field(default=None, sa_column=_run_identity_pk())
    application_id: int = Field(foreign_key="application.id", index=True)
    name: str
    status: str = Field(default="draft", index=True)
    # draft -> sast_running -> correlating -> awaiting_review -> dast_running
    # -> completed | incomplete | failed | stopped | interrupted
    max_parallel_sast: int = Field(default=2)
    llm_config_id: Optional[int] = Field(default=None, foreign_key="llm_config.id")
    llm_profile_id: Optional[int] = Field(default=None, foreign_key="llm_profile.id")
    warnings_json: str = Field(default="[]")  # plain-language partial-failure notes
    review_submitted_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    # Set by reconcile_campaigns() when a restart interrupts an active stage
    # (one of "sast_running" | "correlating" | "dast_running"); `retry_campaign`
    # reads this to resume the exact stage without recreating any child run.
    # Cleared once a retry is issued.
    interrupted_stage: Optional[str] = Field(default=None)
    # Optional per-campaign overrides for the component mapper's trace budget.
    # NULL means use the singleton ComponentMapperConfig value.
    max_trace_edges: Optional[int] = Field(default=None)
    max_trace_components: Optional[int] = Field(default=None)
    max_paths_per_lead: Optional[int] = Field(default=None)
    min_trace_confidence: Optional[float] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class CampaignSourceMember(SQLModel, table=True):
    """One frozen (component, snapshot) pair selected for a campaign."""

    __tablename__ = "campaign_source_member"
    __table_args__ = (
        UniqueConstraint("campaign_id", "component_id", name="uq_campaign_component"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(sa_column=_run_identity_fk())
    component_id: int = Field(foreign_key="application_component.id", index=True)
    snapshot_id: int = Field(foreign_key="component_snapshot.id", index=True)
    sast_run_id: Optional[int] = Field(default=None, index=True)
    status: str = Field(
        default="pending"
    )  # pending|running|completed|incomplete|failed|skipped
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class CampaignTargetMember(SQLModel, table=True):
    """One frozen live target (Site or ApiCollection) selected for a campaign."""

    __tablename__ = "campaign_target_member"
    __table_args__ = (
        UniqueConstraint("campaign_id", "target_id", name="uq_campaign_target"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(sa_column=_run_identity_fk())
    target_id: int = Field(foreign_key="application_target.id", index=True)
    target_type: str = Field(index=True)  # "site" | "api_collection"
    test_run_id: Optional[int] = Field(default=None, index=True)  # web child
    api_test_run_id: Optional[int] = Field(default=None, index=True)  # api child
    status: str = Field(
        default="pending"
    )  # pending|running|completed|incomplete|failed|skipped
    status_message: Optional[str] = Field(default=None)
    validation_summary_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ComponentFact(SQLModel, table=True):
    """One compact, deterministic interface fact recorded by a SAST run.

    Kept intentionally small (routes/calls/auth boundaries/queues/datastores/
    framework markers) so a campaign can join facts across repositories
    without ever passing whole source trees between agents.
    """

    __tablename__ = "component_fact"

    id: Optional[int] = Field(default=None, primary_key=True)
    sast_run_id: int = Field(index=True)  # SastRun.id that produced this fact
    # Populated via CampaignSourceMember lookup when the SastRun belongs to a
    # campaign; NULL for a standalone SAST run.
    component_id: Optional[int] = Field(
        default=None, foreign_key="application_component.id", index=True
    )
    fact_type: str = Field(index=True)  # route | http_call | auth_flow | auth_boundary | ...
    method: Optional[str] = Field(default=None)  # GET/POST/... when applicable
    path: Optional[str] = Field(default=None)  # /api/orders/{id}
    host: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)  # queue/datastore/client/framework name
    detail_json: str = Field(default="{}")  # small bounded extra structured info
    evidence_location: str = Field(default="")  # file:line
    fingerprint: str = Field(default="", index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class ComponentConnection(SQLModel, table=True):
    """One matched edge in a campaign's cross-repository application map."""

    __tablename__ = "component_connection"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "source_fact_id",
            "target_fact_id",
            "edge_kind",
            name="uq_component_connection_edge",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(sa_column=_run_identity_fk())
    source_component_id: int = Field(foreign_key="application_component.id", index=True)
    source_fact_id: int = Field(foreign_key="component_fact.id", index=True)
    target_component_id: int = Field(foreign_key="application_component.id", index=True)
    target_fact_id: int = Field(foreign_key="component_fact.id", index=True)
    match_kind: str = Field(default="deterministic")  # deterministic|hint|llm_assisted
    confidence: float = Field(default=0.0)
    rationale: str = Field(default="")
    evidence_json: str = Field(default="{}")
    # ``same_component`` edges are directed call/route hops within one SAST
    # run. Run ids make the edge unambiguous when a component has snapshots
    # from multiple campaigns.
    edge_kind: str = Field(default="calls", index=True)
    source_sast_run_id: Optional[int] = Field(default=None, index=True)
    target_sast_run_id: Optional[int] = Field(default=None, index=True)
    path_scope: str = Field(default="cross_component", index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class LeadTargetMapping(SQLModel, table=True):
    """A proposed (or reviewed) routing of one ScanLead to one live target."""

    __tablename__ = "lead_target_mapping"
    __table_args__ = (
        UniqueConstraint("campaign_id", "lead_id", "target_id", name="uq_lead_target"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(sa_column=_run_identity_fk())
    lead_id: int = Field(foreign_key="scan_lead.id", index=True)
    target_id: int = Field(foreign_key="application_target.id", index=True)
    target_type: str = Field(index=True)  # "site" | "api_collection"
    score: float = Field(default=0.0)
    rationale: str = Field(default="")
    evidence_json: str = Field(default="{}")
    status: str = Field(default="proposed", index=True)  # proposed|approved|rejected
    copied_lead_id: Optional[int] = Field(default=None)  # set once approved+copied
    reviewed_at: Optional[datetime] = Field(default=None)
    auto_approved: bool = Field(default=False)
    approved: Optional[bool] = Field(default=None)
    final_score: Optional[float] = Field(default=None)
    change_reason: Optional[str] = Field(default=None)
    path_json: str = Field(default="{}")
    approved_attack_path_json: str = Field(default="{}")
    final_attack_path_json: str = Field(default="{}")
    attack_path_changes_json: str = Field(default="[]")
    path_status: Optional[str] = Field(default=None, index=True)
    edited_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ScanLeadComponentProvenance(SQLModel, table=True):
    """Many-component provenance for a campaign-generated cross-repo ScanLead."""

    __tablename__ = "scan_lead_component_provenance"
    __table_args__ = (
        UniqueConstraint(
            "scan_lead_id", "component_id", name="uq_lead_component_provenance"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scan_lead_id: int = Field(foreign_key="scan_lead.id", index=True)
    component_id: int = Field(foreign_key="application_component.id", index=True)
    role: str = Field(default="contributing")  # primary|contributing
    fact_id: Optional[int] = Field(default=None, foreign_key="component_fact.id")
    created_at: datetime = Field(default_factory=_utcnow)


class AliceChatMessage(SQLModel, table=True):
    """One chat bubble inside an AliceChatSession."""

    __tablename__ = "alice_chat_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="alice_chat_session.id", index=True)
    message_key: str = Field(index=True)  # client-assigned message ID
    sender: str  # "user" | "alice"
    type: str = Field(default="message")  # "message" | "thinking"
    text: str = Field(default="")
    step_data_json: str = Field(default="{}")
    ts: str = Field(default="")
    position: int = Field(default=0)  # ordering within session
    updated_at: datetime = Field(default_factory=_utcnow)


class AgentLog(SQLModel, table=True):
    """Persisted agent_status event so the Agents panel survives page navigation.

    One row per emitted agent_status event that has ``_persist=True``.
    Analogous to ScanLog for scanner_phase events.
    """

    __tablename__ = "agent_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(sa_column=_run_identity_fk())
    # Retained as an event/presentation discriminator for compatibility.  The
    # integer itself is globally unique now.
    run_kind: str = Field(default="web", index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    agent_id: str = Field(
        index=True
    )  # e.g. "scanner", "validator-42", "burp-api-login"
    role: str  # Scanner | Specialist | Burp | Validator
    status: str  # active | complete | failed
    current_task: str = Field(default="")
    outcome: Optional[str] = Field(default=None)


# ── Phase Checkpoint & Obligation / Evidence Ledger ─────────────────────────


class PhaseCheckpoint(SQLModel, table=True):
    """Granular phase checkpoint with idempotency key for scan resume safety."""

    __tablename__ = "phase_checkpoint"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_kind: str = Field(default="web", index=True)  # web | api
    run_id: int = Field(sa_column=_run_identity_fk())
    phase: str = Field(
        index=True
    )  # crawl | recon | obligations | dynamic_scan | reporting | validation
    idempotency_key: str = Field(index=True)
    data_json: Optional[str] = Field(default=None)
    completed_at: datetime = Field(default_factory=_utcnow)


class ScanObligation(SQLModel, table=True):
    """A required or exploratory security test obligation."""

    __tablename__ = "scan_obligation"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_kind: str = Field(default="web", index=True)  # web | api
    run_id: int = Field(sa_column=_run_identity_fk())
    scan_mode: str = Field(default="quick")  # quick | full
    owasp_catalog: str = Field(default="web_2025")  # web_2025 | api_2023
    owasp_category: str = Field(index=True)  # A01..A10 or API1..API10
    vulnerability_technique: str = Field(index=True)  # sqli, idor, etc.
    route_template: str = Field(index=True)
    http_method: str = Field(default="GET")
    parameter: Optional[str] = Field(default=None)
    required_identity_comparison: Optional[str] = Field(default=None)
    status: str = Field(
        default="not_planned", index=True
    )  # not_planned|queued|attempted|evaluated|passed|finding|inconclusive|not_applicable|blocked
    exemption_reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ProbeExecution(SQLModel, table=True):
    """An executed probe linked to a ScanObligation."""

    __tablename__ = "probe_execution"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_kind: str = Field(default="web", index=True)  # web | api
    run_id: int = Field(sa_column=_run_identity_fk())
    obligation_id: int = Field(foreign_key="scan_obligation.id", index=True)
    traffic_id: Optional[int] = Field(
        default=None, foreign_key="traffic_entry.id", index=True
    )
    session_identity: Optional[str] = Field(default=None)
    payload_preview: Optional[str] = Field(default=None)  # redacted max 512 bytes
    status_code: Optional[int] = Field(default=None)
    response_time_ms: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class CoverageEvidence(SQLModel, table=True):
    """Proof of test result for a ProbeExecution."""

    __tablename__ = "coverage_evidence"

    id: Optional[int] = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="probe_execution.id", index=True)
    expected_behavior: Optional[str] = Field(default=None)
    observed_behavior: Optional[str] = Field(default=None)
    evaluation_oracle: str = Field(default="default_oracle")
    outcome: str = Field(
        default="inconclusive"
    )  # passed|finding|inconclusive|not_applicable|blocked
    evidence_hash: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


# Run ids used to be allocated independently by each run table.  Allocate the
# parent key from one small identity table instead, so an integer can never
# mean both a web run and an API/SAST run in the same database.
def _allocate_run_identity(mapper, connection, target) -> None:
    kind = {
        TestRun: "web",
        ApiTestRun: "api",
        SastRun: "sast",
        AssessmentCampaign: "campaign",
    }[type(target)]
    table = RunIdentity.__table__
    requested_id = target.id

    if requested_id is not None:
        occupied = connection.execute(
            table.select()
            .with_only_columns(table.c.id)
            .where(table.c.id == requested_id)
        ).first()
        if occupied is None:
            connection.execute(table.insert().values(id=requested_id, kind=kind))
            return

    values = {"kind": kind}
    if requested_id is not None:
        values["legacy_id"] = requested_id
    result = connection.execute(table.insert().values(**values))
    target.id = result.inserted_primary_key[0]


event.listens_for(TestRun, "before_insert")(_allocate_run_identity)
event.listens_for(ApiTestRun, "before_insert")(_allocate_run_identity)
event.listens_for(SastRun, "before_insert")(_allocate_run_identity)
event.listens_for(AssessmentCampaign, "before_insert")(_allocate_run_identity)
