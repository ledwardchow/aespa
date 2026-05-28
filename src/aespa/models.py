import json
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Site / Credential ─────────────────────────────────────────────────────────

class Site(SQLModel, table=True):
    __tablename__ = "site"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    base_url: str
    requires_auth: bool = Field(default=False)
    login_url: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    scope_hosts: Optional[str] = Field(default=None)  # JSON list of in-scope hostnames
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
    label: Optional[str] = Field(default=None)
    login_url: Optional[str] = Field(default=None)

    site: Optional[Site] = Relationship(back_populates="credentials")


# ── LLM config ────────────────────────────────────────────────────────────────

class LLMProviderAPI(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    openai_compatible = "openai_compatible"
    openrouter = "openrouter"
    google = "google"
    bedrock = "bedrock"
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
    models_json: str = Field(default="[]")
    max_tpm: Optional[int] = Field(default=None, nullable=True)
    max_rpm: Optional[int] = Field(default=None, nullable=True)
    updated_at: datetime = Field(default_factory=_utcnow)



class LLMConfig(SQLModel, table=True):
    """Saved LLM settings profile."""

    __tablename__ = "llm_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="Default", index=True)
    is_active: bool = Field(default=False, index=True)
    provider_id: Optional[int] = Field(default=None, foreign_key="llm_provider_config.id", index=True)
    provider: str = Field(default=LLMProviderAPI.anthropic)
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    model: str = Field(default="claude-opus-4-5")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.0)
    # Whether to include page screenshots in LLM prompts (requires vision model)
    use_vision: bool = Field(default=False)
    # Whether to force tool choice using the wire format tool_choice: required/any
    force_tool_choice: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=_utcnow)


class ScannerPolicy(SQLModel, table=True):
    """Singleton row (id always = 1) for scanner policy defaults."""

    __tablename__ = "scanner_policy"

    id: Optional[int] = Field(default=None, primary_key=True)
    scan_mode: str = Field(default="safe_active")
    max_probes_per_page: int = Field(default=50)
    thinking_max_steps: int = Field(default=120)
    request_timeout_s: float = Field(default=10.0)
    min_delay_s: float = Field(default=0.05)
    max_request_body_bytes: int = Field(default=65536)
    response_body_read_limit_bytes: int = Field(default=512 * 1024)
    allowed_schemes: str = Field(default='["http", "https"]')
    methods_by_mode: str = Field(default='{"passive": ["GET", "HEAD"], "safe_active": ["GET", "POST", "HEAD"], "aggressive": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], "destructive": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]}')
    blocked_headers: str = Field(default='["host", "cookie"]')
    follow_redirects: bool = Field(default=True)
    allow_subdomains: bool = Field(default=True)
    require_approval_for_destructive: bool = Field(default=True)
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
    # When True, automatically validate each finding immediately after it is written
    # during a dynamic scan.  When False, validation is only triggered manually.
    auto_validate_inline: bool = Field(default=True)
    # When True (strict mode), only return a false_positive verdict when the validator
    # finds a *concrete* innocent explanation.  When False (lenient), failure to
    # reproduce the finding is treated as a false positive.
    require_concrete_disproof: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=_utcnow)


class GlobalHttpHeaderConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for a global extra HTTP header added to all scanner/crawler requests."""

    __tablename__ = "global_http_header_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    header_name: Optional[str] = Field(default=None, max_length=200)
    header_value: Optional[str] = Field(default=None, max_length=2000)
    updated_at: datetime = Field(default_factory=_utcnow)


class ReportingDebugConfig(SQLModel, table=True):
    """Singleton row (id always = 1) for reporting prompt debug features."""

    __tablename__ = "reporting_debug_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    capture_enabled: bool = Field(default=False)
    panel_enabled: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=_utcnow)


# ── Test runs ─────────────────────────────────────────────────────────────────

class TestRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"
    stopped = "stopped"


class TestRun(SQLModel, table=True):
    __tablename__ = "test_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id", index=True)
    name: str
    status: str = Field(default=TestRunStatus.pending)
    # Crawl config
    use_screenshots: bool = Field(default=False)
    max_depth: int = Field(default=3)
    max_pages: int = Field(default=50)
    scan_mode: str = Field(default="safe_active")
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
    # Optional per-run LLM profile override (null = use the globally active one)
    llm_config_id: Optional[int] = Field(default=None, foreign_key="llm_config.id")
    # JSON blob produced by build_recon_summary() at the end of the crawl phase
    recon_summary: Optional[str] = Field(default=None)
    # Persisted token usage: {model: {input, output, cache_read, cache_write}}
    token_usage_json: Optional[str] = Field(default=None)


class CrawledPage(SQLModel, table=True):
    __tablename__ = "crawled_page"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    url: str = Field(index=True)
    title: Optional[str] = Field(default=None)
    page_text: Optional[str] = Field(default=None)   # truncated ~10k chars
    screenshot_b64: Optional[str] = Field(default=None)
    llm_context: Optional[str] = Field(default=None)
    depth: int = Field(default=0)
    status: str = Field(default="crawled")            # crawled | failed
    error_message: Optional[str] = Field(default=None)
    in_scope: bool = Field(default=True)
    scan_status: str = Field(default="pending")   # pending | running | complete
    # LLM-assessed page categories (populated after analysis)
    req_auth: Optional[bool] = Field(default=None)         # Authentication Required
    takes_input: Optional[bool] = Field(default=None)      # Takes User Input
    has_object_ref: Optional[bool] = Field(default=None)   # Contains Object Reference
    has_business_logic: Optional[bool] = Field(default=None)  # Contains Business Functionality
    accessible_by: str = Field(default="[]")  # JSON list of credential IDs that can access this page
    discovered_at: datetime = Field(default_factory=_utcnow)


class PageLink(SQLModel, table=True):
    """Directed edge in the crawl graph: source page → target page."""

    __tablename__ = "page_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    source_page_id: int = Field(foreign_key="crawled_page.id", index=True)
    target_page_id: Optional[int] = Field(default=None, foreign_key="crawled_page.id")
    target_url: str
    link_text: Optional[str] = Field(default=None)


class TrafficEntry(SQLModel, table=True):
    """One HTTP request/response pair captured during a crawl or scan."""

    __tablename__ = "traffic_entry"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    source: str                                   # "playwright" | "httpx"
    created_at: datetime = Field(default_factory=_utcnow)
    method: str
    url: str
    request_headers: str = Field(default="{}")    # JSON
    request_body: Optional[str] = Field(default=None)
    status: Optional[int] = Field(default=None)
    response_headers: str = Field(default="{}")   # JSON
    response_body: Optional[str] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None)
    username: Optional[str] = Field(default=None)      # credential username that made the request


class ScannerSession(SQLModel, table=True):
    """Reusable scanner session material discovered or configured during a run."""

    __tablename__ = "scanner_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    label: str = Field(index=True)                 # anonymous | configured_primary | forged_admin | ...
    kind: str = Field(default="cookie", index=True)  # anonymous | cookie | bearer | mixed
    username: Optional[str] = Field(default=None, index=True)
    credential_id: Optional[int] = Field(default=None, foreign_key="credential.id", index=True)
    source: str = Field(default="scanner")
    cookies_json: str = Field(default="{}")
    extra_headers_json: str = Field(default="{}")
    session_metadata: str = Field(default="{}")
    token_hint: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class PageCredentialView(SQLModel, table=True):
    """Per-credential snapshot of a crawled page: screenshot, LLM context, and raw categories."""

    __tablename__ = "page_credential_view"

    id: Optional[int] = Field(default=None, primary_key=True)
    page_id: int = Field(foreign_key="crawled_page.id", index=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    credential_id: Optional[int] = Field(default=None)
    username: Optional[str] = Field(default=None)
    screenshot_b64: Optional[str] = Field(default=None)
    llm_context: Optional[str] = Field(default=None)
    page_text: Optional[str] = Field(default=None)
    req_auth: Optional[bool] = Field(default=None)
    takes_input: Optional[bool] = Field(default=None)
    has_object_ref: Optional[bool] = Field(default=None)
    has_business_logic: Optional[bool] = Field(default=None)


class TargetIntelItem(SQLModel, table=True):
    """Normalized target intelligence discovered during crawl and recon."""

    __tablename__ = "target_intel_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    kind: str = Field(index=True)              # endpoint | form | input | script | storage_key | id | token_hint | response_field
    key: str = Field(default="", index=True)   # stable label, e.g. route path, field name, script URL
    value: str = Field(default="")             # extracted value or display text
    url: Optional[str] = Field(default=None, index=True)
    method: Optional[str] = Field(default=None)
    source: str = Field(default="crawler")     # dom | api_observation | js_asset | response_body
    confidence: float = Field(default=1.0)
    evidence: str = Field(default="")
    item_metadata: str = Field(default="{}")
    discovered_at: datetime = Field(default_factory=_utcnow)


class PentestHypothesis(SQLModel, table=True):
    """Durable attack hypothesis derived from crawl intelligence and scan progress."""

    __tablename__ = "pentest_hypothesis"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    title: str = Field(index=True)
    description: str = Field(default="")
    attack_area: str = Field(default="", index=True)
    owasp_category: str = Field(default="")
    status: str = Field(default="open", index=True)  # open | testing | confirmed | rejected | unconfirmed
    priority: int = Field(default=50, index=True)
    confidence: float = Field(default=0.5)
    rationale: str = Field(default="")
    created_from: str = Field(default="")
    related_intel_ids: str = Field(default="[]")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class PentestTask(SQLModel, table=True):
    """Concrete work item in the LLM-directed pentest plan."""

    __tablename__ = "pentest_task"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    hypothesis_id: Optional[int] = Field(default=None, foreign_key="pentest_hypothesis.id", index=True)
    title: str = Field(index=True)
    description: str = Field(default="")
    target_url: str = Field(default="", index=True)
    method: str = Field(default="GET")
    task_type: str = Field(default="recon", index=True)
    status: str = Field(default="queued", index=True)  # queued | running | blocked | done | skipped
    priority: int = Field(default=50, index=True)
    evidence: str = Field(default="")
    result_summary: str = Field(default="")
    last_action_step: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ScanFinding(SQLModel, table=True):
    """A security vulnerability found during an active scan."""

    __tablename__ = "scan_finding"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    page_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("crawled_page.id"),
            index=True,
            nullable=True,
        ),
    )
    owasp_category: str = Field(index=True)   # "A01" … "A10"
    severity: str                              # critical | high | medium | low | info
    title: str
    description: str
    impact: str = Field(default="")
    likelihood: str = Field(default="")
    recommendation: str = Field(default="")
    cvss_score: float = Field(default=0.0)
    cvss_vector: str = Field(default="")
    affected_url: str = Field(default="")      # specific URL where the issue was observed
    evidence: str = Field(default="")          # formatted request + response excerpt
    request_evidence: str = Field(default="")
    response_evidence: str = Field(default="")
    evidence_json: str = Field(default="[]")
    merged_instances: str = Field(default="[]")  # JSON list of consolidated cross-URL instances
    screenshot_b64: Optional[str] = Field(default=None)  # base64 PNG (form probes only)
    finding_source: str = Field(default="unknown", index=True)
    # Validation fields
    validation_status: str = Field(default="unvalidated")  # unvalidated | validating | confirmed | unconfirmed | false_positive
    validation_note: Optional[str] = Field(default=None)   # LLM reasoning from validation
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def evidence_items(self) -> list[dict]:
        try:
            parsed = json.loads(self.evidence_json or "[]")
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []


class ScanLog(SQLModel, table=True):
    """Persisted scanner_phase event so the activity log survives page navigation."""

    __tablename__ = "scan_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    phase: str                              # thinking_step | site_plan | page_plan | …
    status: str = Field(default="")        # start | complete | running | deciding | …
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
    test_run_id: int = Field(foreign_key="test_run.id", index=True, unique=True)
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
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class AgentLog(SQLModel, table=True):
    """Persisted agent_status event so the Agents panel survives page navigation.

    One row per emitted agent_status event that has ``_persist=True``.
    Analogous to ScanLog for scanner_phase events.
    """

    __tablename__ = "agent_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    agent_id: str = Field(index=True)   # e.g. "scanner", "validator-42", "burp-api-login"
    role: str                            # Scanner | Specialist | Burp | Validator
    status: str                          # active | complete | failed
    current_task: str = Field(default="")
    outcome: Optional[str] = Field(default=None)
