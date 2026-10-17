"""Request and response models for API v1.

These models are the public contract and the source of the OpenAPI
definition. Add optional fields rather than renaming or removing fields; a
breaking change needs a new ``/v2`` path.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from aespa.schemas import (
    CredentialIn,
    LoginField,
    SiteCreate,
    TestRunCreate,
    WebCoverageModeLiteral,
)

from .examples import SCAN_STATUS as SCAN_STATUS_EXAMPLE

SCAN_ID_PATTERN = r"^(web|sast)-[0-9]+$"
Severity = Literal["critical", "high", "medium", "low", "info"]
State = Literal[
    "queued",
    "preparing",
    "running",
    "needs_action",
    "paused",
    "completed",
    "failed",
    "stopped",
]
Scope = Literal["sast", "web", "sites"]
CallbackEvent = Literal[
    "scan.started",
    "scan.phase_changed",
    "scan.progress",
    "scan.needs_action",
    "scan.paused",
    "scan.completed",
    "scan.failed",
    "scan.stopped",
]
CALLBACK_EVENTS: tuple[str, ...] = CallbackEvent.__args__
DEFAULT_CALLBACK_EVENTS = [
    event for event in CALLBACK_EVENTS if event != "scan.progress"
]

_WRITE_ONLY = {"writeOnly": True, "format": "password"}


class ErrorResponse(BaseModel):
    detail: str | dict[str, Any] | list[Any] = Field(
        description="What went wrong. Validation errors list each field."
    )


ERRORS = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "The token lacks a required scope"},
    404: {
        "model": ErrorResponse,
        "description": "Not found, or owned by another token",
    },
    409: {
        "model": ErrorResponse,
        "description": "The request conflicts with the current state",
    },
    422: {"model": ErrorResponse, "description": "The request is not valid"},
}


# ── Sites ────────────────────────────────────────────────────────────────────


class LoginFieldIn(LoginField):
    value: str = Field(
        min_length=1,
        description="Value typed into this field. Never returned.",
        json_schema_extra=_WRITE_ONLY,
    )


class CredentialCreate(CredentialIn):
    """A user account AESPA signs in as.

    Send ``username`` and ``password``, or ``login_fields`` for custom login
    forms. ``auth_mode`` is one of ``auto`` (single form), ``totp`` (form plus
    TOTP code from ``totp_seed``), ``email_otp`` (code read from
    ``test_mailbox_url``), ``entra_id`` (Microsoft sign-in), or ``guided`` (a
    person signs in at the AESPA browser window).
    """

    id: int | None = Field(
        default=None,
        description="On PUT, the ID of an existing credential to keep and update.",
    )
    password: str | None = Field(
        default=None,
        description="Never returned.",
        json_schema_extra=_WRITE_ONLY,
    )
    totp_seed: str | None = Field(
        default=None,
        description="Base32 TOTP secret. Never returned. On PUT, omit to keep the saved seed.",
        json_schema_extra=_WRITE_ONLY,
    )
    login_fields: list[LoginFieldIn] = Field(default_factory=list)
    auth_mode: Literal["auto", "totp", "email_otp", "entra_id", "guided"] = "auto"


class SiteIn(SiteCreate):
    """Everything AESPA needs to test a web site."""

    credentials: list[CredentialCreate] = Field(
        default_factory=list,
        description="Accounts to sign in as. Requires requires_auth=true.",
    )
    scope_hosts: list[str] = Field(
        default_factory=list,
        description="Extra hosts or URL prefixes that are in scope. The base URL's host is always in scope.",
    )


class LoginFieldOut(BaseModel):
    key: str | None
    label: str | None
    sensitive: bool
    selector: str | None = None
    value: str | None = Field(description="Empty for sensitive fields.")


class CredentialOut(BaseModel):
    id: int
    label: str | None
    username: str | None
    login_url: str | None
    auth_mode: str
    test_mailbox_url: str | None
    has_password: bool
    has_totp_seed: bool
    login_fields: list[LoginFieldOut]


class WorkflowOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    goal: str
    start_url: str
    instructions: str


class SiteOut(BaseModel):
    id: int
    name: str
    base_url: str
    requires_auth: bool
    login_url: str | None
    notes: str | None
    scan_guidance: str | None
    workflow_data: list[WorkflowOut]
    scope_hosts: list[str]
    credentials: list[CredentialOut]
    created_at: str | None
    updated_at: str | None


# ── Callbacks ────────────────────────────────────────────────────────────────


class CallbackConfig(BaseModel):
    url: HttpUrl = Field(description="Where AESPA sends a POST for each event.")
    events: list[CallbackEvent] = Field(
        default_factory=lambda: list(DEFAULT_CALLBACK_EVENTS),
        description="Events to send. scan.progress is sent at most once a minute.",
    )
    secret: str | None = Field(
        default=None,
        min_length=16,
        max_length=200,
        description=(
            "Key for the X-AESPA-Signature header. If omitted, the token's webhook "
            "secret is used, or a new secret is returned once in the response."
        ),
        json_schema_extra=_WRITE_ONLY,
    )


class CallbackOut(BaseModel):
    url: str
    events: list[str]
    secret: str | None = Field(
        default=None,
        description="Returned only when AESPA created the secret for this scan.",
    )


# ── Scans ────────────────────────────────────────────────────────────────────


class WebScanCreate(TestRunCreate):
    """Create a web scan for an existing Site or a Site described here."""

    site_id: int | None = Field(default=None, description="An existing Site.")
    site: SiteIn | None = Field(
        default=None,
        description="Create a Site, or update the Site with the same name when update_site is true.",
    )
    update_site: bool = Field(
        default=False,
        description="Replace an existing Site with the same name instead of returning 409.",
    )
    crawl_credential_id: int | None = Field(
        default=None, description="Crawl as this credential only."
    )
    coverage_mode: WebCoverageModeLiteral | None = Field(
        default=None,
        description="Scan depth: track (Quick), standard, enforce (Full), deep, team, or sast_validate.",
    )
    start: bool = Field(default=True, description="Start crawling now.")
    scan_after_crawl: bool = Field(
        default=True, description="Start the dynamic scan when the crawl succeeds."
    )
    unattended: bool = Field(
        default=True,
        description="Reject credentials that need a person to sign in (auth_mode guided).",
    )
    callbacks: CallbackConfig | None = None


class SourceScanCreate(BaseModel):
    provider_id: str = Field(
        description="A SAST source provider, for example aespa.githubrepository."
    )
    parameters: dict[str, Any] = Field(
        description='Provider fields, for example {"repository": "owner/repo", "ref": "main"}.'
    )
    name: str | None = None
    analysis_mode: Literal["light", "deep"] = "deep"
    llm_profile_id: int | None = None
    start: bool = True
    callbacks: CallbackConfig | None = None


class SourceField(BaseModel):
    """A value to send in parameters when creating a scan from this source."""

    key: str = Field(description="The parameters key.")
    label: str
    type: str = Field(description="text, select, boolean, or another input type.")
    required: bool
    placeholder: str | None = None
    help: str | None = None
    default: Any = None
    options: list[dict[str, str]] = Field(
        default_factory=list, description="Choices for select fields."
    )


class SastSource(BaseModel):
    """An enabled extension that can prepare source code for a SAST scan."""

    id: str = Field(
        description="Send as provider_id to POST /sast/scans/from-source.",
        examples=["aespa.githubrepository"],
    )
    name: str
    description: str
    extension: str = Field(description="The extension that provides it.")
    available: bool = Field(
        description="False when it is not set up yet, for example a missing tool."
    )
    message: str = Field(description="Why it is or isn't available.")
    fields: list[SourceField]


class FindingCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class Counts(BaseModel):
    findings: FindingCounts
    pages: int | None = None
    max_pages: int | None = None


class NeedsAction(BaseModel):
    type: str = Field(description="guided_login or authenticator_approval")
    credential_id: int | None = None
    message: str


class ScanLinks(BaseModel):
    self: str
    findings: str
    summary: str
    activity: str
    sarif: str | None = None


class ScanStatus(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [SCAN_STATUS_EXAMPLE]})

    id: str = Field(pattern=SCAN_ID_PATTERN, examples=["web-42", "sast-17"])
    kind: Literal["web", "sast"]
    name: str
    state: State
    phase: str | None = Field(
        description=(
            "Web: crawling, scanning, reviewing, crawled, finished. "
            "SAST: preparing_source, analyzing, finished."
        )
    )
    status: str = Field(description="AESPA's own run status, for troubleshooting.")
    outcome: str | None
    percent: int | None = Field(
        description="Share of planned tests done, when AESPA can measure it."
    )
    message: str
    counts: Counts
    needs_action: NeedsAction | None
    resumable: bool | None = Field(
        default=None,
        description=(
            "SAST: true when POST /sast/scans/{scan_id}/resume can continue the scan "
            "from its saved progress. Null for web scans."
        ),
    )
    error: str | None
    site_id: int | None = None
    scan_after_crawl: bool | None = None
    created_at: str | None
    started_at: str | None
    finished_at: str | None
    links: ScanLinks
    callbacks: CallbackOut | None = None


class ScanList(BaseModel):
    items: list[ScanStatus]
    total: int
    offset: int
    limit: int


class FindingLocation(BaseModel):
    url: str | None = None
    raw: str | None = None
    file: str | None = None
    line: int | None = None
    column: int | None = None
    endpoint: str | None = None


class FindingEvidence(BaseModel):
    summary: str | None = None
    request: str | None = None
    response: str | None = None


class Finding(BaseModel):
    id: int
    reference: str | None
    title: str
    severity: str
    category: str | None
    description: str
    status: str
    dismissed: bool
    location: FindingLocation
    evidence: FindingEvidence
    created_at: str | None
    impact: str | None = None
    recommendation: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    source: str | None = None
    proof_of_concept: str | None = None
    confidence: float | None = None
    classification: str | None = None
    validation_status: str | None = None
    reportable: bool | None = None


class FindingPage(BaseModel):
    scan_id: str
    partial: bool = Field(description="True while the scan is still running.")
    items: list[Finding]
    total: int
    offset: int
    limit: int


class Gate(BaseModel):
    fail_on: Severity
    blocking_findings: int
    passed: bool


class Summary(BaseModel):
    scan_id: str
    state: State
    partial: bool
    total: int
    by_severity: FindingCounts
    by_category: dict[str, int]
    gate: Gate | None = None
    duration_seconds: float | None = None


class ActivityItem(BaseModel):
    cursor: int
    at: str | None
    phase: str
    status: str
    message: str
    url: str | None


class ActivityPage(BaseModel):
    items: list[ActivityItem]
    next_cursor: int = Field(description="Pass as after= to get newer lines.")


class Delivery(BaseModel):
    id: str
    event: str
    url: str
    status: Literal["pending", "delivered", "failed"]
    attempts: int
    last_status_code: int | None
    last_error: str | None
    created_at: str | None
    delivered_at: str | None
    next_attempt_at: str | None


class TokenInfo(BaseModel):
    """The token that sent the request."""

    name: str
    prefix: str = Field(description="The first characters of the token.")
    scopes: list[Scope]
    scan_access: Literal["own", "all"] = Field(
        description=(
            "own: only scans this token created. all: every web or SAST scan its "
            "scopes allow, including scans started in AESPA."
        )
    )


class LlmProfile(BaseModel):
    """A scan profile: which LLM models AESPA uses for a scan."""

    id: int = Field(description="Send as llm_profile_id when creating a scan.")
    name: str
    active: bool = Field(description="Used for scans created without llm_profile_id.")
    default_model: str | None = Field(description="The profile's main model.")


class StopResult(BaseModel):
    stopped: bool
    scan: ScanStatus


# ── Callback payload ─────────────────────────────────────────────────────────


class CallbackPayload(BaseModel):
    """Body of every callback. Fetch findings with the scan's links."""

    id: str = Field(description="Delivery ID, also sent as X-AESPA-Delivery.")
    event: CallbackEvent
    created_at: str
    scan: ScanStatus
