"""Security scanner service.

Two-phase LLM-directed probe execution:
  1. plan_probes()  → LLM returns a list of HTTP / form probes for the page
  2. execute probes → httpx (url/header/idor) or Playwright (form injection)
  3. analyse_probes() → LLM interprets results, returns ScanFinding rows

Auth bootstrap: re-uses _authenticate() from crawler, then exports cookies +
JS storage tokens so httpx carries a live authenticated session.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import time
from contextvars import ContextVar as _ContextVar
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import Credential, CrawledPage, LLMConfig, ScanFinding, Site, TargetIntelItem, TestRun, TrafficEntry
from aespa.services import events as events_svc
from aespa.services import burp_rest as burp_rest_svc
from aespa.services import llm as llm_svc
from aespa.services import scanner_sessions as session_svc
from aespa.services import task_graph as task_graph_svc
from aespa.services import traffic as traffic_svc
from aespa.services import checkpoint as checkpoint_svc
from aespa.services.scope import check_scope, register_scope_host_for_run
from aespa.services.settings import get_burp_rest_api_config, get_global_http_header_config, get_llm_config_for_run, get_run_scanner_policy, get_upstream_proxy_config, get_specialist_agent_config
from aespa.services.prompts.specialist import (
    SPECIALIST_SYSTEM_PROMPT as _SPECIALIST_SYSTEM_PROMPT,
    SPECIALIST_SYSTEM_PROMPTS as _SPECIALIST_SYSTEM_PROMPTS,
    get_specialist_tools as _get_specialist_tools,
)
from aespa.services.prompts.test_lead import (
    _THINKING_AGENT_SYSTEM,
    _API_THINKING_AGENT_SYSTEM,
)

log = logging.getLogger("aespa.scanner")

_scanner_proxy_var: _ContextVar[str | None] = _ContextVar('_scanner_proxy', default=None)
_scanner_global_header_var: _ContextVar[dict[str, str]] = _ContextVar('_scanner_global_header', default={})


def _make_scanner_client(**kwargs) -> httpx.AsyncClient:
    kwargs.setdefault("verify", False)
    if proxy := _scanner_proxy_var.get():
        kwargs["proxy"] = proxy
    if global_header := _scanner_global_header_var.get():
        existing = kwargs.get("headers", {})
        kwargs["headers"] = {**global_header, **existing}
    
    run_id = kwargs.pop("run_id", None)
    username = kwargs.pop("username", None)
    api_run_id = kwargs.pop("api_run_id", None)
    
    from aespa.services.traffic import LoggingAsyncClient
    return LoggingAsyncClient(run_id=run_id, username=username, api_run_id=api_run_id, **kwargs)


def _playwright_proxy() -> dict:
    if proxy := _scanner_proxy_var.get():
        return {"proxy": {"server": proxy}}
    return {}


def _playwright_global_headers(session_extra_headers: dict | None = None) -> dict[str, str]:
    """Merge global extra header with session-specific extra headers for Playwright contexts."""
    merged = dict(_scanner_global_header_var.get())
    if session_extra_headers:
        merged.update(session_extra_headers)
    return merged


# ── In-memory state ───────────────────────────────────────────────────────────

# Populated while a scan is running so the validator can reuse pre-authenticated sessions.
_active_sessions: dict[int, dict[int, dict]] = {}  # run_id → cred_id → session

# Thinking scan (independent)
_thinking_stop_requested: set[int] = set()
_thinking_tasks: dict[int, asyncio.Task] = {}
_thinking_scan_status: dict[int, str] = {}  # run_id → idle|running|complete|stopped|failed
_burp_active_scan_targets: set[tuple[int, str, str]] = set()
_persist_write_locks: dict[int, asyncio.Lock] = {}

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

MAX_PROBES_PER_PAGE = 50
MAX_FOLLOWUP_PROBES  = 20
REQUEST_TIMEOUT = 10.0
BODY_READ_LIMIT = 512 * 1024  # 512 KB
EVIDENCE_TEXT_LIMIT = 128 * 1024
REQUEST_EVIDENCE_LIMIT = 64 * 1024
RESPONSE_EVIDENCE_LIMIT = 128 * 1024
EVIDENCE_ITEM_TEXT_LIMIT = 16 * 1024
EVIDENCE_JSON_LIMIT = 64 * 1024
MIN_DELAY = 0.05              # ~20 req/s
CONTEXT_TOOL_CHECKPOINT_INTERVAL = 3
CONTEXT_TOOL_CHECKPOINT_ERROR = (
    "context tool checkpoint reached; summarize what you learned, state the "
    "current hypothesis, and either execute a probe/write a finding or provide "
    "context_budget_reason to justify another targeted context scan round"
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ── Browser traffic capture constants ────────────────────────────────────────
_BROWSER_SKIP_RESOURCE_TYPES: frozenset[str] = frozenset({
    "image", "media", "font", "stylesheet", "ping", "other",
})
_BROWSER_SKIP_EXTENSIONS: tuple[str, ...] = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".css", ".map",
    ".mp4", ".webm", ".mp3", ".wav",
)
_BROWSER_TRAFFIC_BODY_LIMIT: int = 32 * 1024  # 32 KB per response body

# ── Mutation probe payload lists ──────────────────────────────────────────────
_SQLI_PAYLOADS: tuple[str, ...] = (
    "' OR '1'='1'--",
    '" OR "1"="1"--',
    "1 OR 1=1--",
    "' UNION SELECT NULL--",
    "1 AND SLEEP(1)--",
)
_XSS_PAYLOADS: tuple[str, ...] = (
    "<script>alert(1)</script>",
    '"><script>alert(1)</script>',
    "<svg onload=alert(1)>",
    "<img src=x onerror=alert(1)>",
    "<details open ontoggle=alert(1)>",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def sleep_between_probes(scanner_policy=None) -> None:
    delay = scanner_policy.min_delay_s if scanner_policy else MIN_DELAY
    if delay > 0:
        await asyncio.sleep(delay)


def _login_url_for_credential(default_login_url: Optional[str], cred) -> str:
    return (getattr(cred, "login_url", None) or default_login_url or "").strip()


def _severity_from_cvss(score: float | int | str | None) -> str:
    try:
        value = float(score or 0.0)
    except (TypeError, ValueError):
        value = 0.0
    if value >= 9.0:
        return "critical"
    if value >= 7.0:
        return "high"
    if value >= 4.0:
        return "medium"
    if value > 0.0:
        return "low"
    return "info"


def _cvss_score(value: float | int | str | None) -> float:
    try:
        return max(0.0, min(10.0, round(float(value or 0.0), 1)))
    except (TypeError, ValueError):
        return 0.0


def _compact_log_value(value, limit: int = 180) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, separators=(",", ":"))
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _infer_step_note(tool_name: str, tool_input: dict, step: int) -> str:
    """Return a human-readable description for an agentic step.

    Uses the explicit ``note`` field when the LLM provides it; otherwise
    derives a short description from the tool name and its key inputs so
    the UI never shows the unhelpful fallback 'Step N: Step N'.
    """
    explicit = tool_input.get("note")
    if explicit:
        return str(explicit)
    if tool_name == "http_request":
        method = (tool_input.get("method") or "HTTP").upper()
        url = tool_input.get("url") or ""
        return f"{method} {url}" if url else f"{method} request"
    if tool_name == "context_tool":
        inner = tool_input.get("tool") or "context lookup"
        return f"Query: {inner}"
    if tool_name == "write_finding":
        title = tool_input.get("title") or "untitled"
        return f"Write finding: {title}"
    if tool_name == "done":
        return "Completing assessment"
    if tool_name == "browser":
        action = tool_input.get("action") or "navigate"
        url = tool_input.get("url") or ""
        return f"Browser {action}: {url}" if url else f"Browser {action}"
    return tool_name


def _context_budget_reason(action: dict[str, Any]) -> str:
    for key in ("context_budget_reason", "budget_reason", "scan_reason"):
        value = action.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _context_tool_checkpoint_output(tool_name: str, consecutive_context_tools: int) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "error": CONTEXT_TOOL_CHECKPOINT_ERROR,
        "checkpoint": {
            "consecutive_context_tools": consecutive_context_tools,
            "checkpoint_interval": CONTEXT_TOOL_CHECKPOINT_INTERVAL,
            "next_options": [
                "execute a probe",
                "write a finding from existing evidence",
                (
                    "call a context tool again with context_budget_reason explaining "
                    "why more context will change the next action"
                ),
            ],
        },
    }


def _thinking_payload_summary(url: str, body) -> str:
    parts: list[str] = []
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    if query:
        preview = ", ".join(
            f"{key}={_compact_log_value(values[-1], 60)}"
            for key, values in list(query.items())[:4]
        )
        parts.append(f"query payloads: {preview}")
    body_preview = _compact_log_value(body)
    if body_preview:
        parts.append(f"body payload: {body_preview}")
    return "; ".join(parts)


def _thinking_browser_payload_summary(steps) -> str:
    if not isinstance(steps, list):
        return ""
    parts: list[str] = []
    for step in steps[:6]:
        if not isinstance(step, dict):
            continue
        op = step.get("op")
        selector = step.get("selector")
        value = step.get("value") if "value" in step else step.get("key")
        url = step.get("url")
        detail = op or "step"
        if selector:
            detail += f" {selector}"
        if value is not None:
            detail += f"={_compact_log_value(value, 50)}"
        if url:
            detail += f" {_compact_log_value(url, 80)}"
        parts.append(detail)
    if isinstance(steps, list) and len(steps) > 6:
        parts.append(f"+{len(steps) - 6} more")
    return "; ".join(parts)


def _sign_hs256_jwt(secret: str, claims: dict, header: dict | None = None) -> str:
    import base64 as _b64
    import hashlib
    import hmac

    def _b64url(raw: bytes) -> str:
        return _b64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    jwt_header = {"typ": "JWT", "alg": "HS256"}
    if header:
        jwt_header.update(header)
    if jwt_header.get("alg") != "HS256":
        raise ValueError("only HS256 JWT signing is supported")
    signing_input = ".".join([
        _b64url(json.dumps(jwt_header, separators=(",", ":")).encode()),
        _b64url(json.dumps(claims, separators=(",", ":")).encode()),
    ])
    signature = hmac.new(
        secret.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _decode_jwt(token: str, secret: str | None = None) -> dict:
    """Decode a JWT's header and payload without library dependencies.

    If *secret* is provided, also validate the HS256 signature and include
    a ``signature_valid`` boolean in the result.
    """
    import base64 as _b64
    import hashlib
    import hmac

    def _b64url_decode(segment: str) -> bytes:
        padding = 4 - len(segment) % 4
        if padding != 4:
            segment += "=" * padding
        return _b64.urlsafe_b64decode(segment)

    parts = token.strip().split(".")
    if len(parts) != 3:
        return {"error": "not a valid JWT (expected 3 dot-separated parts)"}

    try:
        header = json.loads(_b64url_decode(parts[0]))
    except Exception as exc:
        return {"error": f"failed to decode header: {exc}"}

    try:
        payload = json.loads(_b64url_decode(parts[1]))
    except Exception as exc:
        return {"error": f"failed to decode payload: {exc}"}

    result: dict = {"header": header, "payload": payload}

    if secret is not None:
        alg = header.get("alg", "")
        if alg != "HS256":
            result["signature_valid"] = None
            result["signature_note"] = (
                f"signature verification only supports HS256; token uses {alg!r}"
            )
        else:
            signing_input = f"{parts[0]}.{parts[1]}"
            expected_sig = hmac.new(
                secret.encode(),
                signing_input.encode(),
                hashlib.sha256,
            ).digest()
            try:
                actual_sig = _b64url_decode(parts[2])
            except Exception:
                actual_sig = b""
            result["signature_valid"] = hmac.compare_digest(expected_sig, actual_sig)

    return result


def _redact_candidate(candidate: dict) -> dict:
    return {
        "username": candidate.get("username") or candidate.get("email") or "",
        "password": "***",
    }


def _redact_sensitive_text(text: str) -> str:
    # Hide JWT-like bearer values in history/evidence. The session vault keeps
    # usable tokens separately under labels so the LLM does not need raw secrets.
    redacted = re.sub(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        "[REDACTED_JWT]",
        text,
    )
    return re.sub(
        r"(?im)^(\s*authorization\s*:\s*bearer\s+)[^\s\r\n]+",
        r"\1[REDACTED_BEARER]",
        redacted,
    )


def _extract_bearer_token_from_body(body: str) -> Optional[str]:
    try:
        data = json.loads(body)
    except Exception:
        data = None

    def _walk(value):
        if isinstance(value, dict):
            for key in ("token", "access_token", "jwt", "auth_token", "id_token"):
                token = value.get(key)
                if isinstance(token, str) and token.count(".") == 2:
                    return token
            for child in value.values():
                found = _walk(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = _walk(child)
                if found:
                    return found
        return None

    if data is not None:
        token = _walk(data)
        if token:
            return token

    match = re.search(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        body,
    )
    return match.group(0) if match else None


def _session_label(raw: str, existing: dict) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower()).strip("_")
    base = base[:40] or "session"
    label = base
    counter = 2
    while label in existing:
        label = f"{base}_{counter}"
        counter += 1
    return label


def _session_kind(cookies: dict | None, extra_headers: dict | None) -> str:
    has_cookies = bool(cookies)
    has_bearer = any(str(k).lower() == "authorization" for k in (extra_headers or {}))
    if has_cookies and has_bearer:
        return "mixed"
    if has_bearer:
        return "bearer"
    if has_cookies:
        return "cookie"
    return "anonymous"


def _maybe_persist_discovered_credential(
    run_id: int,
    username: str,
    password: str,
    login_url: str | None,
) -> bool:
    """Save a newly discovered valid credential to the site's credential store.

    Returns True if a new Credential row was created, False if one already
    existed for that username.  Emits a ``credential_discovered`` event
    prompting the user to re-crawl with the new account.
    """
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return False
        existing = s.exec(
            select(Credential)
            .where(Credential.site_id == run.site_id)
            .where(Credential.username == username)
        ).first()
        if existing is not None:
            return False
        cred = Credential(
            site_id=run.site_id,
            username=username,
            password=password,
            label="Discovered by dynamic scan",
            login_url=login_url or None,
        )
        s.add(cred)
        s.commit()

    log.info("Discovered credential saved: username=%r run_id=%s", username, run_id)
    events_svc.emit(run_id, {
        "type": "credential_discovered",
        "username": username,
        "login_url": login_url,
        "message": (
            f"Valid credential discovered: {username!r}. "
            "Saved to the site credential store. "
            "Re-run the crawl with this credential to test the authenticated attack surface."
        ),
    })
    return True


def _record_session(
    run_id: int,
    *,
    label: str,
    session_data: dict,
    source: str,
    credential_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    session_svc.upsert_session(
        run_id,
        label=label,
        kind=session_data.get("kind") or _session_kind(
            session_data.get("cookies"),
            session_data.get("extra_headers"),
        ),
        username=session_data.get("username"),
        credential_id=credential_id or session_data.get("credential_id"),
        source=source,
        cookies=session_data.get("cookies") or {},
        extra_headers=session_data.get("extra_headers") or {},
        metadata=metadata or session_data.get("metadata") or {},
    )


def _disposable_account_fields(action: dict, *, base_url: str) -> dict[str, Any]:
    suffix = secrets.token_hex(4)
    username = str(action.get("username") or f"aespa_{suffix}").strip()
    email = str(action.get("email") or f"aespa_{suffix}@example.invalid").strip()
    password = str(action.get("password") or f"Aespa-{suffix}-Test!23")
    username_field = str(action.get("username_field") or "username")
    email_field = str(action.get("email_field") or "email")
    password_field = str(action.get("password_field") or "password")
    include_username = action.get("include_username", True) is not False
    include_email = action.get("include_email", True) is not False
    extra_fields = action.get("extra_fields") if isinstance(action.get("extra_fields"), dict) else {}
    body = dict(extra_fields)
    if include_username:
        body[username_field] = username
    if include_email:
        body[email_field] = email
    body[password_field] = password
    return {
        "username": username,
        "email": email,
        "password": password,
        "body": body,
        "username_field": username_field,
        "email_field": email_field,
        "password_field": password_field,
        "metadata": {
            "registration_url": str(action.get("url") or base_url),
            "username": username,
            "email": email,
            "password": password,
            "generated": not any(action.get(k) for k in ("username", "email", "password")),
            "fields": {
                "username": username_field if include_username else None,
                "email": email_field if include_email else None,
                "password": password_field,
            },
        },
    }


def _redacted_account_body(body: dict[str, Any], password_field: str) -> dict[str, Any]:
    redacted = dict(body)
    for key in list(redacted):
        if str(key).lower() in {str(password_field).lower(), "password", "passwd", "pwd"}:
            redacted[key] = "***"
    return redacted


def _merge_persisted_sessions(run_id: int, cred_sessions: dict[int, dict]) -> dict[int, dict]:
    merged = dict(cred_sessions or {})
    existing_labels = {str(s.get("label") or "") for s in merged.values()}
    existing_credential_ids = {int(k) for k in merged if isinstance(k, int) and k > 0}
    synthetic_id = -1
    for label, stored in session_svc.load_session_vault(run_id).items():
        if label in existing_labels or stored.get("kind") == "anonymous":
            continue
        credential_id = stored.get("credential_id")
        if isinstance(credential_id, int) and credential_id > 0:
            if credential_id in existing_credential_ids:
                continue
            key = credential_id
            existing_credential_ids.add(credential_id)
        else:
            while synthetic_id in merged:
                synthetic_id -= 1
            key = synthetic_id
            synthetic_id -= 1
        merged[key] = {
            "label": label,
            "username": stored.get("username") or label,
            "credential_id": credential_id,
            "cookies": stored.get("cookies") or {},
            "extra_headers": stored.get("extra_headers") or {},
            "source": stored.get("source") or "scanner_session",
            "metadata": stored.get("metadata") or {},
        }
        existing_labels.add(label)
    return merged


def _thinking_action_log_message(step: int, method: str, url: str, action: dict) -> str:
    note = _compact_log_value(action.get("note"), 240)
    observation = _compact_log_value(action.get("observation"), 220)
    hypothesis = _compact_log_value(
        action.get("hypothesis") or action.get("investigation") or action.get("objective"),
        220,
    )
    payload_purpose = _compact_log_value(action.get("payload_purpose"), 180)
    if method == "BROWSER":
        payload_summary = _thinking_browser_payload_summary(action.get("steps") or [])
    elif method == "CREDENTIAL_CHECK":
        count = len(action.get("candidates") or [])
        payload_summary = f"{min(count, 20)} bounded candidate(s)"
    else:
        payload_summary = _thinking_payload_summary(url, action.get("body"))

    lead = hypothesis or note or "next target behavior"
    message = f"Step {step}: investigating {lead}"
    if observation:
        message += f" after observing {observation}"
    if payload_purpose:
        message += f"; payload purpose: {payload_purpose}"
    if payload_summary:
        message += f" ({payload_summary})"
    return f"{message} — {method} {url}"


def _summary_list(values: list[str], limit: int = 3) -> str:
    unique: list[str] = []
    for value in values:
        compact = _compact_log_value(value, 180)
        if compact and compact not in unique:
            unique.append(compact)
    if not unique:
        return ""
    shown = unique[:limit]
    suffix = f"; +{len(unique) - limit} more" if len(unique) > limit else ""
    return "; ".join(shown) + suffix


def _thinking_page_flags(page: dict[str, Any]) -> list[str]:
    return [
        label for key, label in [
            ("req_auth", "req_auth"),
            ("takes_input", "takes_input"),
            ("has_object_ref", "has_object_ref"),
            ("has_business_logic", "has_business_logic"),
        ] if page.get(key)
    ]


def _thinking_page_kind(page: dict[str, Any]) -> str:
    return "api" if str(page.get("title") or "").startswith("API ") else "page"


def _build_compact_thinking_context(
    base_url: str,
    pages_snapshot: list[dict[str, Any]],
    findings_snapshot: list[dict[str, Any]],
) -> str:
    total = len(pages_snapshot)
    api_pages = [p for p in pages_snapshot if _thinking_page_kind(p) == "api"]
    input_pages = [p for p in pages_snapshot if p.get("takes_input")]
    object_pages = [p for p in pages_snapshot if p.get("has_object_ref")]
    business_pages = [p for p in pages_snapshot if p.get("has_business_logic")]

    def _sample(label: str, pages: list[dict[str, Any]], limit: int = 8) -> str:
        if not pages:
            return f"{label}: none"
        lines = [
            f"  - page_id={p['id']} {_thinking_page_kind(p)} {p['url']}"
            + (f" [{', '.join(_thinking_page_flags(p))}]" if _thinking_page_flags(p) else "")
            for p in pages[:limit]
        ]
        suffix = f"\n  - +{len(pages) - limit} more" if len(pages) > limit else ""
        return f"{label}:\n" + "\n".join(lines) + suffix

    sections = [
        f"Target: {base_url}",
        (
            "Crawl summary: "
            f"{total} in-scope pages/endpoints; {len(api_pages)} API; "
            f"{len(input_pages)} input-taking; {len(object_pages)} object-reference; "
            f"{len(business_pages)} business-logic."
        ),
        "Use context tools for details instead of assuming full crawl data is inline.",
        _sample("High-value routes", input_pages + object_pages + business_pages),
        _sample("API sample", api_pages),
    ]
    if findings_snapshot:
        lines = [
            f"  - [{f['severity'].upper()}] {f['owasp']} {f['title']} @ {f['affected_url']}"
            for f in findings_snapshot
        ]
        sections.append(
            "CONFIRMED VULNERABILITIES — already proven, do NOT re-test:\n"
            "You may USE a confirmed exploit capability (e.g. a known JWT secret or admin "
            "password) only as a stepping stone to reach NEW endpoints. Do not spend steps "
            "re-proving issues already in this list.\n"
            + "\n".join(lines)
        )
    return "\n\n".join(sections)


def _build_thinking_context_from_recon_summary(
    run_id: int,
    base_url: str,
    findings_snapshot: list[dict[str, Any]],
) -> str:
    """Build the LLM opening context from the stored recon summary.

    Falls back to :func:`_build_compact_thinking_context` (with an empty
    pages_snapshot) when no summary is present, so old runs are unaffected.
    """
    import json as _json
    from aespa.models import TestRun as _TestRun

    with Session(get_engine()) as s:
        run = s.get(_TestRun, run_id)
        raw = run.recon_summary if run else None

    if not raw:
        # No summary yet — fall back to minimal compact context
        return _build_compact_thinking_context(base_url, [], findings_snapshot)

    try:
        summary = _json.loads(raw)
    except Exception:
        return _build_compact_thinking_context(base_url, [], findings_snapshot)

    trust_zones: dict = summary.get("trust_zones") or {}
    attack_classes: list[dict] = summary.get("attack_classes") or []
    tech_stack: list[str] = summary.get("tech_stack") or []
    credential_roles: list[str] = summary.get("credential_roles") or []
    entry_points: list[dict] = summary.get("entry_points") or []
    business_logic: list[str] = summary.get("business_logic_pages") or []

    zone_counts = {z: len(v) for z, v in trust_zones.items() if v}
    zone_str = "  ".join(f"{z.upper()}={n}" for z, n in zone_counts.items())
    ep_total = len(entry_points)

    sections = [
        f"Target: {base_url}",
        (
            "Attack surface snapshot:  "
            + zone_str
            + f"  entry_points={ep_total}"
            + (f"  business_logic={len(business_logic)}" if business_logic else "")
            + (f"\nTech stack: {', '.join(tech_stack)}" if tech_stack else "")
            + (f"\nCredential roles: {', '.join(credential_roles)}" if credential_roles else "")
        ),
        "Use context tools for page-level details instead of assuming full crawl data is inline.",
    ]

    if attack_classes:
        ac_lines = ["Identified attack classes (work through these in priority order):"]
        for cls in attack_classes:
            urls = cls.get("entry_point_urls") or []
            url_sample = ", ".join(urls[:4]) + ("…" if len(urls) > 4 else "")
            ac_lines.append(
                f"  [{cls['owasp']} P{cls['priority']}] {cls['id']} — {cls['rationale'][:160]}"
                + (f"\n    entry points: {url_sample}" if url_sample else "")
            )
        sections.append("\n".join(ac_lines))

    if findings_snapshot:
        lines = [
            f"  - [{f['severity'].upper()}] {f['owasp']} {f['title']} @ {f['affected_url']}"
            for f in findings_snapshot
        ]
        sections.append(
            "CONFIRMED VULNERABILITIES — already proven, do NOT re-test:\n"
            "You may USE a confirmed exploit capability (e.g. a known JWT secret or admin "
            "password) only as a stepping stone to reach NEW endpoints. Do not spend steps "
            "re-proving issues already in this list.\n"
            + "\n".join(lines)
        )

    return "\n\n".join(sections)


def _build_target_intelligence_context(run_id: int, limit: int = 80) -> str:
    with Session(get_engine()) as s:
        items = s.exec(
            select(TargetIntelItem)
            .where(TargetIntelItem.test_run_id == run_id)
            .order_by(TargetIntelItem.kind, TargetIntelItem.discovered_at.desc())
            .limit(limit)
        ).all()
    if not items:
        return ""

    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind] = counts.get(item.kind, 0) + 1
    lines = [
        "Target intelligence inventory:",
        "Counts in sampled inventory: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
    ]
    for item in items[:limit]:
        method = f" {item.method}" if item.method else ""
        url = f" @ {item.url}" if item.url else ""
        value = f" -> {_compact_log_value(item.value, 140)}" if item.value else ""
        evidence = f" ({_compact_log_value(item.evidence, 140)})" if item.evidence else ""
        lines.append(
            f"  - {item.kind}{method} {item.key}{value}{url}; source={item.source}{evidence}"
        )
    return "\n".join(lines)


def _thinking_tool_result_record(
    step: int,
    tool_name: str,
    args: dict[str, Any],
    output: dict[str, Any],
    note: str,
) -> dict[str, Any]:
    text = json.dumps(output, separators=(",", ":"), default=str)
    return {
        "step": step,
        "note": note,
        "method": "TOOL",
        "url": f"tool://{tool_name}",
        "request_headers": {},
        "request_body": args,
        "response_status": 200,
        "response_headers": {"content-type": "application/json"},
        "response_body": text[:6000],
    }


# Vulnerability-class vocabulary for the ``finding_list`` context tool. Agents
# think in the same attack-class slugs used elsewhere (attack_class, WSTG_SKILLS,
# specialist dispatch), not raw OWASP codes — so let them filter by class. Each
# slug maps to its OWASP code plus title/description keywords; a finding matches
# the category if EITHER its owasp code matches OR a keyword appears (findings
# are sometimes mis-categorised, so keyword matching is the safety net).
_FINDING_CATEGORY_FILTERS: dict[str, tuple[str, frozenset[str]]] = {
    "sqli":            ("a03", frozenset({"sql injection", "sqli", "sql error", "blind sql"})),
    "xss":             ("a03", frozenset({"xss", "cross-site scripting", "cross site scripting"})),
    "cmdi":            ("a03", frozenset({"command injection", "os command", "rce", "remote code execution", "code injection"})),
    "idor":            ("a01", frozenset({"idor", "insecure direct object", "broken access", "access control", "authorization bypass"})),
    "auth_bypass":     ("a07", frozenset({"authentication bypass", "auth bypass", "login bypass"})),
    "auth_robustness": ("a07", frozenset({"password", "brute force", "rate limit", "lockout", "credential"})),
    "sessions":        ("a07", frozenset({"session", "cookie", "session fixation"})),
    "ssrf":            ("a10", frozenset({"ssrf", "server-side request forgery", "server side request forgery"})),
    "csrf":            ("a01", frozenset({"csrf", "cross-site request forgery", "cross site request forgery"})),
    "cors":            ("a05", frozenset({"cors", "cross-origin", "cross origin"})),
    "headers":         ("a05", frozenset({"security header", "header missing", "missing header", "csp", "hsts", "x-frame-options", "content-security-policy"})),
    "workflow":        ("a04", frozenset({"workflow", "business logic", "race condition"})),
    "file_upload":     ("a05", frozenset({"file upload", "unrestricted file upload", "upload"})),
}

# OWASP codes shared by several classes (A03 = sqli/xss/cmdi, etc.) can't tell
# sibling classes apart, so the code only counts as a match when it maps to a
# single class; otherwise the keyword is the sole discriminator.
_FINDING_CATEGORY_UNIQUE_OWASP: frozenset[str] = frozenset(
    code
    for code, _ in _FINDING_CATEGORY_FILTERS.values()
    if sum(1 for c, _ in _FINDING_CATEGORY_FILTERS.values() if c == code) == 1
)

# Synonyms / abbreviations an agent might reach for → canonical slug above.
_FINDING_CATEGORY_ALIASES: dict[str, str] = {
    "sql": "sqli",
    "sql_injection": "sqli",
    "injection": "sqli",
    "cross_site_scripting": "xss",
    "command_injection": "cmdi",
    "rce": "cmdi",
    "os_command_injection": "cmdi",
    "access_control": "idor",
    "broken_access_control": "idor",
    "authz": "idor",
    "authentication": "auth_bypass",
    "auth": "auth_bypass",
    "session": "sessions",
    "security_headers": "headers",
    "header": "headers",
    "business_logic": "workflow",
    "upload": "file_upload",
}


def _load_findings_snapshot(run_id: int) -> list[dict[str, Any]]:
    """Load existing findings for a run as context-tool snapshots.

    Shared by the thinking scan, specialists and ALICE so the ``finding_list``
    context tool reflects what has actually been recorded in the DB.
    """
    with Session(get_engine()) as s:
        existing = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all()
    return [
        {
            "title":        f.title,
            "severity":     f.severity,
            "owasp":        f.owasp_category,
            "affected_url": f.affected_url,
            "description":  (f.description or "")[:200],
        }
        for f in existing
    ]


def _run_thinking_context_tool(
    tool_name: str,
    args: dict[str, Any],
    *,
    pages_snapshot: list[dict[str, Any]],
    findings_snapshot: list[dict[str, Any]],
    history: list[dict[str, Any]],
    run_id: int | None = None,
    base_url: str = "",
) -> dict[str, Any]:
    if not isinstance(args, dict):
        args = {}
    try:
        limit = max(1, min(100, int(args.get("limit") or 20)))
    except (TypeError, ValueError):
        limit = 20
    tool_name = (tool_name or "").strip()
    search = str(args.get("search") or args.get("filter") or "").lower()
    search_tokens = search.replace("-", "_").split()

    if tool_name == "site_map":
        route_type = str(args.get("type") or "").lower()
        flags = args.get("flags") if isinstance(args.get("flags"), list) else []
        flag_set = {str(flag) for flag in flags}
        pages: list[dict[str, Any]] = []
        for page in pages_snapshot:
            haystack = " ".join([
                str(page.get("url") or ""),
                str(page.get("title") or ""),
                str(page.get("context") or ""),
                " ".join(_thinking_page_flags(page)),
                _thinking_page_kind(page),
            ]).lower()
            if route_type and _thinking_page_kind(page) != route_type:
                continue
            if flag_set and not all(page.get(flag) for flag in flag_set):
                continue
            if search_tokens and not all(token in haystack for token in search_tokens):
                continue
            pages.append(page)
        return {
            "tool": "site_map",
            "count": len(pages),
            "routes": [
                {
                    "page_id": p["id"],
                    "kind": _thinking_page_kind(p),
                    "url": p["url"],
                    "title": p.get("title") or "",
                    "flags": _thinking_page_flags(p),
                    "context_excerpt": _compact_log_value(p.get("context"), 220),
                }
                for p in pages[:limit]
            ],
            "truncated": len(pages) > limit,
        }

    if tool_name == "page_detail":
        page_id = args.get("page_id")
        url = str(args.get("url") or "")
        include = args.get("include") if isinstance(args.get("include"), list) else []
        include_set = {str(item) for item in include} or {"title", "flags", "context", "page_text"}
        page = None
        for candidate in pages_snapshot:
            if page_id is not None and str(candidate.get("id")) == str(page_id):
                page = candidate
                break
            if url and candidate.get("url") == url:
                page = candidate
                break
        if not page:
            return {"tool": "page_detail", "error": "page not found", "page_id": page_id, "url": url}
        detail: dict[str, Any] = {
            "tool": "page_detail",
            "page_id": page["id"],
            "url": page["url"],
            "kind": _thinking_page_kind(page),
        }
        if "title" in include_set:
            detail["title"] = page.get("title") or ""
        if "flags" in include_set:
            detail["flags"] = _thinking_page_flags(page)
        if "context" in include_set:
            detail["context"] = str(page.get("context") or "")[:3000]
        if "page_text" in include_set or "transcript" in include_set:
            detail["page_text"] = str(page.get("page_text") or "")[:5000]
        return detail

    if tool_name == "history_search":
        query = str(args.get("query") or search).lower()
        matches: list[dict[str, Any]] = []
        for item in history:
            haystack = json.dumps(item, default=str).lower()
            if query and query not in haystack:
                continue
            matches.append({
                "step": item.get("step"),
                "method": item.get("method"),
                "url": item.get("url"),
                "note": item.get("note"),
                "request_body": _compact_log_value(item.get("request_body"), 500),
                "response_status": item.get("response_status"),
                "response_headers": item.get("response_headers"),
                "response_body": str(item.get("response_body") or "")[:2000],
            })
        return {"tool": "history_search", "count": len(matches), "matches": matches[-limit:]}

    if tool_name == "finding_list":
        severity = str(args.get("severity") or "").lower()
        owasp = str(args.get("owasp_category") or "").lower()
        # Vuln-class filter: agents pass slugs like "sqli"/"xss". Resolve aliases,
        # then match by owasp code OR title/description keyword. An unknown slug
        # degrades gracefully into an extra free-text search token.
        category = str(args.get("category") or "").strip().lower().replace("-", "_").replace(" ", "_")
        category = _FINDING_CATEGORY_ALIASES.get(category, category)
        cat_filter = _FINDING_CATEGORY_FILTERS.get(category)
        extra_tokens = list(search_tokens)
        if category and cat_filter is None:
            extra_tokens.extend(tok for tok in category.split("_") if tok)
        matches = []
        for finding in findings_snapshot:
            haystack = json.dumps(finding, default=str).lower()
            if severity and str(finding.get("severity") or "").lower() != severity:
                continue
            if owasp and str(finding.get("owasp") or "").lower() != owasp:
                continue
            if cat_filter is not None:
                cat_owasp, cat_keywords = cat_filter
                keyword_hit = any(kw in haystack for kw in cat_keywords)
                owasp_hit = (
                    cat_owasp in _FINDING_CATEGORY_UNIQUE_OWASP
                    and str(finding.get("owasp") or "").lower() == cat_owasp
                )
                if not (keyword_hit or owasp_hit):
                    continue
            if extra_tokens and not all(token in haystack for token in extra_tokens):
                continue
            matches.append(finding)
        return {"tool": "finding_list", "count": len(matches), "findings": matches[:limit]}

    if tool_name in {"target_inventory", "search_assets"}:
        if run_id is None:
            return {"tool": tool_name, "error": "run_id unavailable"}
        return _thinking_tool_target_inventory(run_id, args, limit, search_tokens)

    if tool_name == "traffic_search":
        if run_id is None:
            return {"tool": tool_name, "error": "run_id unavailable"}
        return _thinking_tool_traffic_search(run_id, args, limit, search_tokens)

    if tool_name == "endpoint_detail":
        if run_id is None:
            return {"tool": tool_name, "error": "run_id unavailable"}
        return _thinking_tool_endpoint_detail(
            run_id,
            args,
            pages_snapshot=pages_snapshot,
            history=history,
            limit=limit,
        )

    if tool_name == "compare_responses":
        return _thinking_tool_compare_responses(args, history=history)

    if tool_name == "mutate_request":
        return _thinking_tool_mutate_request(args, history=history, base_url=base_url)

    if tool_name == "auth_matrix":
        if run_id is None:
            return {"tool": tool_name, "error": "run_id unavailable"}
        return _thinking_tool_auth_matrix(run_id, base_url, args, limit)

    if tool_name == "extract_entities":
        return _thinking_tool_extract_entities(args, pages_snapshot=pages_snapshot, history=history, limit=limit)

    return {
        "tool": tool_name,
        "error": "unknown tool",
        "available_tools": [
            "site_map", "page_detail", "history_search", "finding_list",
            "target_inventory", "search_assets", "traffic_search", "endpoint_detail",
            "compare_responses", "mutate_request", "auth_matrix", "extract_entities",
        ],
    }


def _thinking_tool_target_inventory(
    run_id: int,
    args: dict[str, Any],
    limit: int,
    search_tokens: list[str],
) -> dict[str, Any]:
    kind = str(args.get("kind") or "").strip()
    source = str(args.get("source") or "").strip()
    with Session(get_engine()) as s:
        query = select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)
        if kind:
            query = query.where(TargetIntelItem.kind == kind)
        if source:
            query = query.where(TargetIntelItem.source == source)
        items = list(s.exec(
            query.order_by(TargetIntelItem.kind, TargetIntelItem.discovered_at.desc()).limit(1000)
        ))
    matches = []
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind] = counts.get(item.kind, 0) + 1
        haystack = _target_intel_text(item).lower()
        if search_tokens and not all(token in haystack for token in search_tokens):
            continue
        matches.append({
            "id": item.id,
            "kind": item.kind,
            "key": item.key,
            "value": _compact_log_value(item.value, 300),
            "url": item.url,
            "method": item.method,
            "source": item.source,
            "confidence": item.confidence,
            "evidence": _compact_log_value(item.evidence, 300),
            "metadata": _loads_json_dict(item.item_metadata),
        })
    return {
        "tool": "target_inventory",
        "counts": counts,
        "count": len(matches),
        "items": matches[:limit],
        "truncated": len(matches) > limit,
    }


def _thinking_tool_traffic_search(
    run_id: int,
    args: dict[str, Any],
    limit: int,
    search_tokens: list[str],
) -> dict[str, Any]:
    method = str(args.get("method") or "").upper()
    status = args.get("status")
    try:
        status_int = int(status) if status not in (None, "") else None
    except (TypeError, ValueError):
        status_int = None
    with Session(get_engine()) as s:
        query = select(TrafficEntry).where(TrafficEntry.test_run_id == run_id)
        if method:
            query = query.where(TrafficEntry.method == method)
        if status_int is not None:
            query = query.where(TrafficEntry.status == status_int)
        entries = list(s.exec(query.order_by(TrafficEntry.id.desc()).limit(1000)))
    matches = []
    for entry in entries:
        haystack = " ".join(str(part or "") for part in (
            entry.method, entry.url, entry.request_body, entry.response_body,
            entry.status, entry.username, entry.source,
        )).lower()
        if search_tokens and not all(token in haystack for token in search_tokens):
            continue
        matches.append({
            "id": entry.id,
            "source": entry.source,
            "method": entry.method,
            "url": entry.url,
            "status": entry.status,
            "duration_ms": entry.duration_ms,
            "username": entry.username,
            "request_headers": _safe_json_excerpt(entry.request_headers, 800),
            "request_body": _compact_log_value(entry.request_body, 1000),
            "response_headers": _safe_json_excerpt(entry.response_headers, 800),
            "response_body": _compact_log_value(entry.response_body, 1800),
        })
    matches = list(reversed(matches[:limit]))
    return {"tool": "traffic_search", "count": len(matches), "entries": matches}


def _thinking_tool_endpoint_detail(
    run_id: int,
    args: dict[str, Any],
    *,
    pages_snapshot: list[dict[str, Any]],
    history: list[dict[str, Any]],
    limit: int,
) -> dict[str, Any]:
    url = str(args.get("url") or "")
    page_id = args.get("page_id")
    if not url and page_id is not None:
        for page in pages_snapshot:
            if str(page.get("id")) == str(page_id):
                url = str(page.get("url") or "")
                break
    if not url:
        return {"tool": "endpoint_detail", "error": "url or page_id required"}

    detail: dict[str, Any] = {"tool": "endpoint_detail", "url": url}
    for page in pages_snapshot:
        if page.get("url") == url or str(page.get("id")) == str(page_id):
            detail["page"] = {
                "page_id": page.get("id"),
                "kind": _thinking_page_kind(page),
                "title": page.get("title") or "",
                "flags": _thinking_page_flags(page),
                "context": str(page.get("context") or "")[:2500],
                "page_text": str(page.get("page_text") or "")[:3000],
            }
            break

    with Session(get_engine()) as s:
        intel = list(s.exec(
            select(TargetIntelItem)
            .where(TargetIntelItem.test_run_id == run_id)
            .limit(1000)
        ))
        traffic = list(s.exec(
            select(TrafficEntry)
            .where(TrafficEntry.test_run_id == run_id)
            .order_by(TrafficEntry.id.desc())
            .limit(1000)
        ))

    detail["intel"] = [
        {
            "id": item.id,
            "kind": item.kind,
            "key": item.key,
            "value": _compact_log_value(item.value, 240),
            "method": item.method,
            "source": item.source,
            "evidence": _compact_log_value(item.evidence, 240),
        }
        for item in intel
        if _urls_related(url, item.url or item.value or item.key)
    ][:limit]
    detail["traffic"] = [
        {
            "id": entry.id,
            "method": entry.method,
            "url": entry.url,
            "status": entry.status,
            "username": entry.username,
            "request_body": _compact_log_value(entry.request_body, 600),
            "response_body": _compact_log_value(entry.response_body, 1200),
        }
        for entry in traffic
        if _urls_related(url, entry.url)
    ][:limit]
    detail["history"] = [
        {
            "step": item.get("step"),
            "method": item.get("method"),
            "url": item.get("url"),
            "status": item.get("response_status"),
            "note": item.get("note"),
            "response_body": str(item.get("response_body") or "")[:1200],
        }
        for item in history
        if _urls_related(url, str(item.get("url") or ""))
    ][-limit:]
    detail["entities"] = _extract_entities_from_text(json.dumps(detail, default=str), limit=limit)
    return detail


def _thinking_tool_compare_responses(args: dict[str, Any], *, history: list[dict[str, Any]]) -> dict[str, Any]:
    left = _resolve_history_record(args.get("left_step") or args.get("baseline_step"), history)
    right = _resolve_history_record(args.get("right_step") or args.get("variant_step"), history)
    if left is None or right is None:
        return {"tool": "compare_responses", "error": "left_step/baseline_step and right_step/variant_step must match history steps"}
    left_body = str(left.get("response_body") or "")
    right_body = str(right.get("response_body") or "")
    left_status = left.get("response_status")
    right_status = right.get("response_status")
    added, removed = _word_diff_summary(left_body, right_body)
    return {
        "tool": "compare_responses",
        "left": {"step": left.get("step"), "url": left.get("url"), "status": left_status, "length": len(left_body)},
        "right": {"step": right.get("step"), "url": right.get("url"), "status": right_status, "length": len(right_body)},
        "status_changed": left_status != right_status,
        "length_delta": len(right_body) - len(left_body),
        "similarity": _text_similarity(left_body, right_body),
        "added_terms": added[:30],
        "removed_terms": removed[:30],
        "left_excerpt": left_body[:1200],
        "right_excerpt": right_body[:1200],
    }


def _thinking_tool_mutate_request(args: dict[str, Any], *, history: list[dict[str, Any]], base_url: str) -> dict[str, Any]:
    source = _resolve_history_record(args.get("step"), history)
    url = str(args.get("url") or (source or {}).get("url") or base_url)
    method = str(args.get("method") or (source or {}).get("method") or "GET").upper()
    body = args.get("body")
    if body is None and source is not None:
        body = source.get("request_body")
    mutation = str(args.get("mutation") or args.get("kind") or "input_validation")
    probes = _mutated_probe_variants(method, url, body, mutation)
    return {
        "tool": "mutate_request",
        "source_step": source.get("step") if source else None,
        "mutation": mutation,
        "count": len(probes),
        "probes": probes[: max(1, min(20, int(args.get("limit") or 10)))],
        "note": "These are proposed probe objects. Execute one with an http action when appropriate.",
    }


def _thinking_tool_auth_matrix(run_id: int, base_url: str, args: dict[str, Any], limit: int) -> dict[str, Any]:
    targets = _auth_matrix_targets(run_id, base_url)
    search = str(args.get("search") or args.get("filter") or "").lower()
    if search:
        tokens = search.split()
        targets = [t for t in targets if all(token in json.dumps(t, default=str).lower() for token in tokens)]
    return {
        "tool": "auth_matrix",
        "count": len(targets),
        "targets": [
            {
                "url": t["url"],
                "method": t.get("method", "GET"),
                "requires_auth_or_sensitive": _target_requires_auth_or_sensitive(t),
                "accessible_by": t.get("accessible_by") or [],
                "page_id": t.get("page_id"),
                "source": t.get("source"),
                "has_object_ref": t.get("has_object_ref"),
                "has_business_logic": t.get("has_business_logic"),
            }
            for t in targets[:limit]
        ],
        "truncated": len(targets) > limit,
    }


def _thinking_tool_extract_entities(
    args: dict[str, Any],
    *,
    pages_snapshot: list[dict[str, Any]],
    history: list[dict[str, Any]],
    limit: int,
) -> dict[str, Any]:
    text = str(args.get("text") or "")
    if not text and args.get("step") is not None:
        record = _resolve_history_record(args.get("step"), history)
        if record:
            text = json.dumps(record, default=str)
    if not text and args.get("page_id") is not None:
        for page in pages_snapshot:
            if str(page.get("id")) == str(args.get("page_id")):
                text = " ".join(str(page.get(k) or "") for k in ("url", "title", "context", "page_text"))
                break
    if not text:
        text = "\n".join(str(item.get("response_body") or "") for item in history[-5:])
    return {
        "tool": "extract_entities",
        "entities": _extract_entities_from_text(text, limit=limit),
    }


def _target_intel_text(item: TargetIntelItem) -> str:
    return " ".join(str(part or "") for part in (
        item.kind, item.key, item.value, item.url, item.method, item.source,
        item.evidence, item.item_metadata,
    ))


def _loads_json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _safe_json_excerpt(value: str | None, limit: int) -> dict | str:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return {
                str(k): _compact_log_value(v, 180)
                for k, v in list(parsed.items())[:20]
            }
        return _compact_log_value(parsed, limit)
    except Exception:
        return _compact_log_value(value, limit)


def _urls_related(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    ap = urlparse(a)
    bp = urlparse(b)
    if ap.netloc and bp.netloc and ap.netloc != bp.netloc:
        return False
    return bool(ap.path and bp.path and (ap.path == bp.path or ap.path in bp.path or bp.path in ap.path))


def _resolve_history_record(step, history: list[dict[str, Any]]) -> dict[str, Any] | None:
    if step is None:
        return history[-1] if history else None
    for item in history:
        if str(item.get("step")) == str(step):
            return item
    return None


def _word_diff_summary(left: str, right: str) -> tuple[list[str], list[str]]:
    token_re = re.compile(r"[A-Za-z0-9_./:-]{3,}")
    left_tokens = set(token_re.findall(left or ""))
    right_tokens = set(token_re.findall(right or ""))
    added = sorted(right_tokens - left_tokens, key=lambda x: (len(x), x), reverse=True)
    removed = sorted(left_tokens - right_tokens, key=lambda x: (len(x), x), reverse=True)
    return added, removed


def _text_similarity(left: str, right: str) -> float:
    left_words = set(re.findall(r"[a-z0-9_]{3,}", (left or "").lower()))
    right_words = set(re.findall(r"[a-z0-9_]{3,}", (right or "").lower()))
    if not left_words and not right_words:
        return 1.0
    if not left_words or not right_words:
        return 0.0
    return round(len(left_words & right_words) / len(left_words | right_words), 3)


def _mutated_probe_variants(method: str, url: str, body, mutation: str) -> list[dict]:
    mutation_l = mutation.lower()
    probes: list[dict] = []
    if "idor" in mutation_l or "object" in mutation_l:
        probes.extend(_mutate_url_numeric_values(method, url, "IDOR object-reference mutation"))
        if isinstance(body, dict):
            for key, value in list(body.items())[:8]:
                if _looks_id_key(key) or re.fullmatch(r"\d+", str(value or "")):
                    for candidate in _numeric_mutations(value):
                        mutated = dict(body)
                        mutated[key] = candidate
                        probes.append({
                            "type": "http", "method": method, "url": url,
                            "headers": {}, "body": mutated,
                            "desc": f"IDOR body mutation {key}={candidate}",
                        })
    elif "business" in mutation_l or "amount" in mutation_l:
        if isinstance(body, dict):
            for key, value in list(body.items())[:10]:
                if _looks_business_value_key(key):
                    for candidate in ["0", "-1", "1", "999999999", str(value)]:
                        mutated = dict(body)
                        mutated[key] = candidate
                        probes.append({
                            "type": "http", "method": method, "url": url,
                            "headers": {}, "body": mutated,
                            "desc": f"Business logic boundary mutation {key}={candidate}",
                        })
    else:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        if qs:
            for param in list(qs.keys())[:3]:
                for payload, label in [(_SQLI_PAYLOADS[0], "SQLi"), (_XSS_PAYLOADS[2], "XSS"), ("{{7*7}}", "SSTI")]:
                    base_params = {k: v[0] for k, v in qs.items()}
                    base_params[param] = payload
                    probes.append({
                        "type": "http", "method": method, "url": urlunparse(parsed._replace(query=urlencode(base_params))),
                        "headers": {}, "body": None,
                        "desc": f"{label} mutation in query param {param}",
                    })
        if isinstance(body, dict):
            for key in list(body.keys())[:5]:
                for payload, label in [(_SQLI_PAYLOADS[0], "SQLi"), (_XSS_PAYLOADS[2], "XSS"), ("{{7*7}}", "SSTI")]:
                    mutated = dict(body)
                    mutated[key] = payload
                    probes.append({
                        "type": "http", "method": method, "url": url,
                        "headers": {}, "body": mutated,
                        "desc": f"{label} mutation in body field {key}",
                    })
    return probes[:40]


def _mutate_url_numeric_values(method: str, url: str, desc: str) -> list[dict]:
    parsed = urlparse(url)
    probes: list[dict] = []
    parts = parsed.path.split("/")
    for idx, part in enumerate(parts):
        if re.fullmatch(r"\d+", part or ""):
            for candidate in _numeric_mutations(part):
                mutated = parts.copy()
                mutated[idx] = candidate
                probes.append({
                    "type": "http", "method": method, "url": urlunparse(parsed._replace(path="/".join(mutated))),
                    "headers": {}, "body": None,
                    "desc": f"{desc}: path {part}->{candidate}",
                })
    qs = parse_qs(parsed.query, keep_blank_values=True)
    for key, values in list(qs.items())[:8]:
        if values and (re.fullmatch(r"\d+", values[0]) or _looks_id_key(key)):
            for candidate in _numeric_mutations(values[0]):
                params = {k: v[0] for k, v in qs.items()}
                params[key] = candidate
                probes.append({
                    "type": "http", "method": method, "url": urlunparse(parsed._replace(query=urlencode(params))),
                    "headers": {}, "body": None,
                    "desc": f"{desc}: query {key}={candidate}",
                })
    return probes


def _numeric_mutations(value) -> list[str]:
    try:
        base = int(value)
    except (TypeError, ValueError):
        base = 1
    candidates = [base - 1, base + 1, 1, 2, 999999]
    return [str(c) for c in candidates if c > 0 and c != base]


def _looks_id_key(key: str) -> bool:
    return bool(re.search(r"(?:^|_)(id|uuid|account|user|order|invoice|transaction|tenant)(?:_|$)", str(key), re.I))


def _looks_business_value_key(key: str) -> bool:
    return bool(re.search(r"(amount|price|total|quantity|qty|balance|limit|role|status|state)", str(key), re.I))


def _extract_entities_from_text(text: str, limit: int = 20) -> dict[str, list[str]]:
    text = text or ""
    urls = _unique_limited(re.findall(r"https?://[^\s\"'<>)}]+", text), limit)
    paths = _unique_limited(re.findall(r"(?<![A-Za-z0-9])/(?:api/)?[A-Za-z0-9_./{}:-]{2,}", text), limit)
    emails = _unique_limited(re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text), limit)
    uuids = _unique_limited(re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text, re.I), limit)
    jwt_like = _unique_limited(re.findall(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", text), limit)
    ids = _unique_limited(re.findall(r"\b(?:id|user_id|account_id|order_id|invoice_id|transaction_id|tenant_id)[\"'=:\s]+([A-Za-z0-9_-]{1,80})", text, re.I), limit)
    errors = _unique_limited([
        line.strip() for line in text.splitlines()
        if any(marker in line.lower() for marker in (
            "error", "exception", "traceback", "stack trace", "sql syntax",
            "unauthorized", "forbidden", "debug",
        ))
    ], limit)
    return {
        "urls": urls,
        "paths": paths,
        "emails": emails,
        "uuids": uuids,
        "ids": ids,
        "jwt_like": ["[REDACTED_JWT]" for _ in jwt_like],
        "errors": errors,
    }


def _unique_limited(values: list[str], limit: int) -> list[str]:
    out: list[str] = []
    for value in values:
        value = str(value).strip().rstrip(".,;")
        if value and value not in out:
            out.append(value)
        if len(out) >= limit:
            break
    return out


def _followup_log_details(followup_probes: list[dict]) -> dict[str, str]:
    interesting = _summary_list([
        str(
            probe.get("interesting_result")
            or probe.get("observation")
            or probe.get("trigger")
            or probe.get("reason")
            or ""
        )
        for probe in followup_probes
    ])
    hypotheses = _summary_list([
        str(
            probe.get("hypothesis")
            or probe.get("tests")
            or probe.get("objective")
            or probe.get("desc")
            or ""
        )
        for probe in followup_probes
    ])
    payloads = _summary_list([
        str(probe.get("payload_purpose") or _thinking_payload_summary(probe.get("url") or "", probe.get("body")))
        for probe in followup_probes
    ])
    return {"interesting": interesting, "hypotheses": hypotheses, "payloads": payloads}


def _followup_log_message(followup_probes: list[dict], *, tense: str = "planning") -> str:
    count = len(followup_probes)
    plural = "s" if count != 1 else ""
    details = _followup_log_details(followup_probes)
    if tense == "complete":
        message = f"{count} follow-up probe{plural} executed"
    else:
        message = f"{count} follow-up probe{plural} planned"
    if details["interesting"]:
        message += f" because: {details['interesting']}"
    if details["hypotheses"]:
        message += f"; testing: {details['hypotheses']}"
    if details["payloads"]:
        message += f"; payload purpose: {details['payloads']}"
    return message


def _combined_evidence(request_evidence: str, response_evidence: str, summary: str = "") -> str:
    parts = []
    if summary:
        parts.append(summary.strip())
    if request_evidence:
        parts.append(f"REQUEST:\n{request_evidence.strip()}")
    if response_evidence:
        parts.append(f"RESPONSE:\n{response_evidence.strip()}")
    return "\n\n".join(parts)


def _clip_evidence(value: str, limit: int) -> str:
    text = _redact_sensitive_text(str(value or ""))
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n\n[truncated {len(text) - limit} characters]"


def _full_evidence(request_evidence: str, response_evidence: str, summary: str = "") -> str:
    return _clip_evidence(
        _combined_evidence(request_evidence, response_evidence, summary),
        EVIDENCE_TEXT_LIMIT,
    )


def _request_evidence(value: str) -> str:
    return _clip_evidence(value, REQUEST_EVIDENCE_LIMIT)


def _response_evidence(value: str) -> str:
    return _clip_evidence(value, RESPONSE_EVIDENCE_LIMIT)


def _evidence_items_json(*items: dict) -> str:
    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        evidence_type = str(item.get("type") or "note").strip()[:80]
        label = str(item.get("label") or evidence_type.replace("_", " ").title()).strip()[:160]
        value = item.get("value")
        if value is None or value == "":
            continue
        cleaned_item: dict[str, object] = {
            "type": evidence_type,
            "label": label,
            "value": _clip_evidence(str(value), EVIDENCE_ITEM_TEXT_LIMIT),
        }
        for key in ("format", "source", "confidence"):
            if item.get(key):
                cleaned_item[key] = str(item[key])[:120]
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            cleaned_item["metadata"] = {
                str(k)[:80]: _clip_evidence(str(v), 1000)
                for k, v in metadata.items()
                if v is not None
            }
        cleaned.append(cleaned_item)

    text = json.dumps(cleaned, ensure_ascii=False)
    if len(text) <= EVIDENCE_JSON_LIMIT:
        return text
    return json.dumps(cleaned[: max(1, len(cleaned) // 2)], ensure_ascii=False)[:EVIDENCE_JSON_LIMIT]


def _evidence_items_from_json(value: str | None) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _http_evidence_items_json(
    request_evidence: str,
    response_evidence: str,
    *,
    summary: str = "",
    status: int | str | None = None,
    status_delta: str | None = None,
    duration_ms: int | float | None = None,
    timing_delta_ms: int | float | None = None,
    body_diff: str | dict | None = None,
    action_outcome: str | None = None,
    action_log: str | list | None = None,
    screenshot_b64: str | None = None,
    marker: str = "",
    confidence: str = "confirmed",
) -> str:
    items = []
    if summary:
        items.append({"type": "summary", "label": "Proof summary", "value": summary, "confidence": confidence})
    if status is not None:
        items.append({"type": "status", "label": "HTTP status", "value": status, "confidence": confidence})
    if status_delta:
        items.append({"type": "status_delta", "label": "Status delta", "value": status_delta, "confidence": confidence})
    if duration_ms is not None:
        items.append({"type": "timing", "label": "Response timing", "value": f"{round(float(duration_ms), 1)} ms", "confidence": confidence})
    if timing_delta_ms is not None:
        items.append({"type": "timing_delta", "label": "Timing delta", "value": f"{round(float(timing_delta_ms), 1)} ms", "confidence": confidence})
    if body_diff:
        diff_value = json.dumps(body_diff, indent=2, sort_keys=True) if isinstance(body_diff, dict) else str(body_diff)
        items.append({"type": "body_diff", "label": "Body diff", "value": diff_value, "confidence": confidence})
    if action_outcome:
        items.append({"type": "action_outcome", "label": "Action outcome", "value": action_outcome, "confidence": confidence})
    if action_log:
        log_value = "\n".join(str(line) for line in action_log) if isinstance(action_log, list) else str(action_log)
        items.append({"type": "action_log", "label": "Action log", "value": log_value, "confidence": confidence})
    if screenshot_b64:
        items.append({
            "type": "screenshot",
            "label": "Screenshot",
            "value": "Screenshot captured and attached to the finding.",
            "confidence": confidence,
            "metadata": {"bytes_base64": len(screenshot_b64)},
        })
    if marker:
        items.append({"type": "marker", "label": "Matched marker", "value": marker, "confidence": confidence})
    items.extend([
        {"type": "http_request", "label": "Request", "value": request_evidence, "format": "http", "confidence": confidence},
        {"type": "http_response", "label": "Response", "value": response_evidence, "format": "http", "confidence": confidence},
    ])
    return _evidence_items_json(*items)


def _finding_from_llm(
    *,
    run_id: int,
    page_id: int | None,
    page_url: str,
    raw: dict,
    result_by_url: dict[str, dict],
    validation_status: str = "validating",
    validation_note: str | None = "Validation queued.",
) -> ScanFinding:
    probe_urls = list(result_by_url.keys())
    llm_url = (raw.get("affected_url") or "").strip()
    if llm_url and llm_url != page_url:
        affected_url = llm_url
    elif probe_urls:
        desc = (raw.get("description", "") + " " + raw.get("title", "")).lower()
        affected_url = next((u for u in probe_urls if u.lower() in desc), probe_urls[0])
    else:
        affected_url = page_url

    matched = result_by_url.get(affected_url, {})
    request_evidence = str(matched.get("request_evidence") or raw.get("request_evidence") or "")
    response_evidence = str(matched.get("response_evidence") or raw.get("response_evidence") or "")
    summary_evidence = str(raw.get("evidence") or matched.get("evidence") or "")
    evidence = _combined_evidence(
        request_evidence,
        response_evidence,
        summary_evidence,
    )
    cvss_score = _cvss_score(raw.get("cvss_score"))
    prebuilt_items = _evidence_items_from_json(str(matched.get("evidence_json") or ""))
    if prebuilt_items:
        evidence_json = _evidence_items_json(
            {"type": "summary", "label": "Proof summary", "value": summary_evidence, "confidence": "validating" if validation_status == "validating" else validation_status},
            *prebuilt_items,
        )
    else:
        evidence_json = _http_evidence_items_json(
            request_evidence,
            response_evidence,
            summary=summary_evidence,
            status=matched.get("status"),
            duration_ms=matched.get("duration_ms"),
            timing_delta_ms=matched.get("timing_delta_ms"),
            body_diff=matched.get("body_diff"),
            action_outcome=matched.get("action_outcome"),
            action_log=matched.get("action_log"),
            screenshot_b64=matched.get("screenshot_b64"),
            confidence="validating" if validation_status == "validating" else validation_status,
        )

    return ScanFinding(
        test_run_id=run_id,
        page_id=page_id,
        owasp_category=raw.get("owasp_category", "A00"),
        severity=_severity_from_cvss(cvss_score),
        title=raw.get("title", "Untitled finding"),
        description=raw.get("description", ""),
        impact=raw.get("impact", ""),
        likelihood=raw.get("likelihood", ""),
        recommendation=raw.get("recommendation", ""),
        cvss_score=cvss_score,
        cvss_vector=raw.get("cvss_vector", ""),
        affected_url=affected_url,
        evidence=_clip_evidence(evidence, EVIDENCE_TEXT_LIMIT),
        request_evidence=_request_evidence(request_evidence),
        response_evidence=_response_evidence(response_evidence),
        evidence_json=evidence_json,
        screenshot_b64=matched.get("screenshot_b64"),
        finding_source=str(raw.get("finding_source") or "dynamic_scan"),
        validation_status=validation_status,
        validation_note=validation_note,
        created_at=_utcnow(),
    )


def _save_deterministic_findings(run_id: int, findings: list[ScanFinding]) -> int:
    saved = 0
    if not findings:
        return saved
    with Session(get_engine()) as s:
        for finding in findings:
            if _finding_exists(
                s,
                run_id=run_id,
                title=finding.title,
                affected_url=finding.affected_url,
                owasp_category=finding.owasp_category,
            ):
                continue
            s.add(finding)
            saved += 1
        s.commit()
    return saved


def _deterministic_sessions_from_vault(
    run_id: int,
    session_vault: dict[str, dict],
) -> dict[int, dict]:
    """Return credential-shaped sessions for deterministic auth/IDOR modules."""
    configured: dict[int, dict] = {}
    synthetic_id = -1
    for label, stored in (session_vault or {}).items():
        if stored.get("kind") == "anonymous":
            continue
        credential_id = stored.get("credential_id")
        if isinstance(credential_id, int) and credential_id > 0:
            key = credential_id
        else:
            while synthetic_id in configured:
                synthetic_id -= 1
            key = synthetic_id
            synthetic_id -= 1
        configured[key] = {
            "label": stored.get("label") or label,
            "username": stored.get("username") or label,
            "credential_id": credential_id,
            "cookies": stored.get("cookies") or {},
            "extra_headers": stored.get("extra_headers") or {},
            "source": stored.get("source") or "scanner_session",
            "metadata": stored.get("metadata") or {},
        }
    return _merge_persisted_sessions(run_id, configured)


def _run_deterministic_analysis_for_dynamic_results(
    *,
    run_id: int,
    base_url: str,
    pages_snapshot: list[dict],
    first_page_id: int | None,
    results: list[dict],
) -> int:
    """Persist deterministic findings from dynamic scan observations."""
    if not results:
        return 0

    findings: list[ScanFinding] = []
    with Session(get_engine()) as s:
        for result in results:
            affected = str(result.get("url") or base_url)
            page_id = _dynamic_finding_page_id(
                s,
                run_id=run_id,
                affected_url=affected,
                base_url=base_url,
                pages_snapshot=pages_snapshot,
                first_page_id=first_page_id,
            )
            findings.extend(_deterministic_findings_from_results(
                run_id=run_id,
                page_id=page_id or first_page_id,
                page_url=affected,
                results=[result],
            ))

    saved = _save_deterministic_findings(run_id, findings)
    if saved:
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "deterministic_analysis",
            "status": "complete",
            "message": f"{saved} deterministic finding(s) recorded from dynamic scan evidence.",
            "data": {"finding_count": saved},
        })
        _emit_scan_update(run_id)
    return saved


def _find_or_create_dynamic_page(
    session: Session,
    *,
    run_id: int,
    url: str,
    base_url: str,
) -> int | None:
    page_url = (url or base_url).strip() or base_url
    existing = session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == run_id)
        .where(CrawledPage.url == page_url)
    ).first()
    if existing:
        return existing.id

    page = CrawledPage(
        test_run_id=run_id,
        url=page_url,
        title="Dynamic Scan target",
        page_text="",
        llm_context="Discovered during Dynamic Scan.",
        depth=0,
        status="crawled",
        in_scope=True,
        scan_status="complete",
    )
    session.add(page)
    session.flush()

    run = session.get(TestRun, run_id)
    if run is not None:
        run.pages_discovered = (run.pages_discovered or 0) + 1

    return page.id


def _dynamic_page_url_for_finding(affected_url: str, base_url: str) -> str | None:
    affected_url = (affected_url or "").strip()
    if not affected_url:
        return None

    parsed = urlparse(affected_url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return affected_url

    if affected_url.startswith("/"):
        base = urlparse(base_url)
        if base.scheme and base.netloc:
            return urlunparse((base.scheme, base.netloc, affected_url, "", "", ""))

    return None


def _dynamic_finding_page_id(
    session: Session,
    *,
    run_id: int,
    affected_url: str,
    base_url: str,
    pages_snapshot: list[dict[str, Any]],
    first_page_id: int | None,
) -> int | None:
    url_to_page: dict[str, int] = {p["url"]: p["id"] for p in pages_snapshot}
    if affected_url in url_to_page:
        return url_to_page[affected_url]
    for page_url, page_id in url_to_page.items():
        if affected_url.startswith(page_url) or page_url.startswith(affected_url):
            return page_id

    dynamic_page_url = _dynamic_page_url_for_finding(affected_url, base_url)
    if dynamic_page_url:
        return _find_or_create_dynamic_page(
            session,
            run_id=run_id,
            url=dynamic_page_url,
            base_url=base_url,
        )

    return first_page_id if first_page_id is not None and not affected_url else None


def _dynamic_finding_exists(
    session: Session,
    *,
    run_id: int,
    title: str,
    affected_url: str,
    owasp_category: str,
) -> bool:
    existing = session.exec(
        select(ScanFinding)
        .where(ScanFinding.test_run_id == run_id)
        .where(ScanFinding.affected_url == affected_url)
    ).all()
    normalized_title = title.strip().lower()
    normalized_owasp = owasp_category.strip().lower()
    return any(
        f.title.strip().lower() == normalized_title
        or (
            f.owasp_category.strip().lower() == normalized_owasp
            and f.title.strip().lower() == normalized_title
        )
        for f in existing
    )


def _finding_exists(
    session: Session,
    *,
    run_id: int,
    title: str,
    affected_url: str,
    owasp_category: str = "",
) -> bool:
    existing = session.exec(
        select(ScanFinding)
        .where(ScanFinding.test_run_id == run_id)
        .where(ScanFinding.affected_url == affected_url)
    ).all()
    normalized_title = (title or "").strip().lower()
    normalized_owasp = (owasp_category or "").strip().lower()
    return any(
        f.title.strip().lower() == normalized_title
        or (
            normalized_owasp
            and f.owasp_category.strip().lower() == normalized_owasp
            and f.title.strip().lower() == normalized_title
        )
        for f in existing
    )


# ── Burp REST API helpers ──────────────────────────────────────────────────────

_SQLI_TITLE_KEYWORDS = frozenset(["sql injection", "sql error", "blind sql", "sqli", "sql blind"])
_XSS_TITLE_KEYWORDS = frozenset([
    "xss", "cross-site scripting", "cross site scripting",
    "reflected xss", "stored xss", "dom xss", "dom-based xss",
])
_COMMAND_INJECTION_KEYWORDS = frozenset([
    "command injection", "os command", "shell injection", "shell command",
    "rce", "remote code execution",
])
_PATH_TRAVERSAL_KEYWORDS = frozenset([
    "path traversal", "directory traversal", "file traversal",
    "local file inclusion", "remote file inclusion", "lfi", "rfi",
])
_SSRF_KEYWORDS = frozenset([
    "ssrf", "server-side request forgery", "server side request forgery",
])
_XXE_KEYWORDS = frozenset([
    "xxe", "xml external entity", "external entity",
])
_SSTI_KEYWORDS = frozenset([
    "ssti", "server-side template injection", "server side template injection",
    "template injection",
])


def _finding_triggers_burp_sqli(finding: ScanFinding) -> bool:
    title = (finding.title or "").lower()
    cat = (finding.owasp_category or "").lower()
    return (
        any(kw in title for kw in _SQLI_TITLE_KEYWORDS)
        or ("sql" in title and "inject" in title)
        or ("sql" in title and cat.startswith("a03"))
    )


def _finding_triggers_burp_xss(finding: ScanFinding) -> bool:
    title = (finding.title or "").lower()
    desc = (finding.description or "").lower()
    return (
        any(kw in title for kw in _XSS_TITLE_KEYWORDS)
        or any(kw in desc for kw in _XSS_TITLE_KEYWORDS)
        or "cross-site" in title
    )


def _finding_burp_vuln_class(finding: ScanFinding) -> str | None:
    text = " ".join([
        finding.title or "",
        finding.description or "",
        finding.owasp_category or "",
    ])
    return _burp_vuln_class_from_text(text)


def _burp_vuln_class_from_text(text: str) -> str | None:
    text = (text or "").lower()
    if (
        any(kw in text for kw in _SQLI_TITLE_KEYWORDS)
        or ("sql" in text and "inject" in text)
    ):
        return "SQL Injection"
    if any(kw in text for kw in _XSS_TITLE_KEYWORDS) or "cross-site" in text:
        return "XSS"
    if any(kw in text for kw in _COMMAND_INJECTION_KEYWORDS):
        return "Command Injection"
    if any(kw in text for kw in _PATH_TRAVERSAL_KEYWORDS):
        return "Path Traversal"
    if any(kw in text for kw in _SSRF_KEYWORDS):
        return "SSRF"
    if any(kw in text for kw in _XXE_KEYWORDS):
        return "XXE"
    if any(kw in text for kw in _SSTI_KEYWORDS):
        return "SSTI"
    return None


def _burp_class_enabled(config, vuln_class: str) -> bool:
    return {
        "SQL Injection": config.scan_sqli,
        "XSS": config.scan_xss,
        "Command Injection": config.scan_command_injection,
        "Path Traversal": config.scan_path_traversal,
        "SSRF": config.scan_ssrf,
        "XXE": config.scan_xxe,
        "SSTI": config.scan_ssti,
    }.get(vuln_class, False)


def _burp_investigation_candidate(tool_input: dict, note: str) -> tuple[str, str] | None:
    text = " ".join(
        str(tool_input.get(key) or "")
        for key in ("hypothesis", "payload_purpose", "observation", "url")
    )
    text = f"{note or ''} {text}"
    vuln_class = _burp_vuln_class_from_text(text)
    if not vuln_class:
        return None
    title = str(tool_input.get("hypothesis") or tool_input.get("payload_purpose") or note or vuln_class)
    return vuln_class, title[:200]


def _best_burp_auth(session_vault: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Return (cookies, extra_headers) from the first non-anonymous session found."""
    for label, session in (session_vault or {}).items():
        if session.get("kind") == "anonymous":
            continue
        cookies = dict(session.get("cookies") or {})
        headers = dict(session.get("extra_headers") or {})
        if cookies or headers:
            return cookies, headers
    return {}, {}


# Maps Burp vuln class strings to specialist attack_class values.
_BURP_VULN_TO_SPECIALIST_CLASS: dict[str, str] = {
    "SQL Injection":     "sqli",
    "XSS":               "xss",
    "Command Injection": "sqli",
    "Path Traversal":    "path_traversal",
    "SSRF":              "ssrf",
    "XXE":               "sqli",
    "SSTI":              "xss",
}


def _maybe_trigger_specialist_for_burp(
    run_id: int,
    url: str,
    vuln_class: str,
    session_vault: dict,
) -> None:
    """If trigger_specialist_on_burp is enabled, dispatch a specialist alongside the Burp scan."""
    import json as _json

    with Session(get_engine()) as s:
        specialist_cfg = get_specialist_agent_config(s)
        if not specialist_cfg.trigger_specialist_on_burp:
            return
        run = s.get(TestRun, run_id)
        if not run:
            return
        llm_cfg = get_llm_config_for_run(s, run)
        scanner_policy = get_run_scanner_policy(s, run)
        recon_raw = getattr(run, "recon_summary", None)
        recon_summary = _json.loads(recon_raw) if recon_raw else None
        site_id: int = getattr(run, "site_id", 0) or 0

    attack_class = _BURP_VULN_TO_SPECIALIST_CLASS.get(vuln_class, "xss")
    agent_id = _next_specialist_agent_id(run_id, attack_class)
    log.info(
        "debug trigger_specialist_on_burp: dispatching %s for %s url=%s",
        agent_id, vuln_class, url,
    )
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(
            _run_specialist_agent(
                run_id=run_id,
                agent_id=agent_id,
                attack_class=attack_class,
                target_url=url,
                rationale=(
                    f"Debug: triggered alongside Burp active scan for {vuln_class} on {url}"
                ),
                recon_summary_entry=None,
                session_vault=session_vault,
                llm_cfg=llm_cfg,
                base_url=url,
                scanner_policy=scanner_policy,
                max_steps=specialist_cfg.max_steps,
                site_id=site_id,
            ),
            name=f"specialist-debug-{run_id}-{agent_id}",
        )
        _specialist_tasks.setdefault(run_id, []).append(task)
        task.add_done_callback(
            lambda t, rid=run_id: _specialist_tasks.get(rid, []).remove(t)
            if t in _specialist_tasks.get(rid, []) else None
        )
    except RuntimeError:
        pass


async def _run_burp_active_scan_for_target(
    run_id: int,
    *,
    url: str,
    title: str,
    vuln_class: str,
    session_vault: dict,
    finding_id: int | None = None,
    page_id: int | None = None,
) -> None:
    """Fire-and-forget task: run Burp active scan on a specific candidate URL."""
    with Session(get_engine()) as s:
        burp_cfg = get_burp_rest_api_config(s)

    if not burp_cfg.enabled:
        return

    if not _burp_class_enabled(burp_cfg, vuln_class):
        return

    if not url.startswith(("http://", "https://")):
        return
    target_key = (run_id, vuln_class, url)
    if target_key in _burp_active_scan_targets:
        return
    _burp_active_scan_targets.add(target_key)

    log.info(
        "burp_rest: scheduling active scan for %s url=%s",
        vuln_class, url,
    )
    target_label = f'finding "{title}"' if finding_id is not None else f'investigation "{title}"'
    # Stable agent_id for this Burp scan (URL slug, truncated).
    _burp_agent_id = "burp-" + re.sub(r"[^a-z0-9]+", "-", url.lower())[:50].strip("-")
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "burp_active_scan",
        "status": "start",
        "message": (
            f"Burp active scan triggered for {vuln_class} {target_label} — {url}"
        ),
        "data": {"finding_id": finding_id, "url": url, "vuln_class": vuln_class},
    })
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": _burp_agent_id,
        "role": "Burp",
        "status": "active",
        "current_task": f"Active scan: {url} ({vuln_class})",
        "outcome": None,
        "_persist": True,
    })

    cookies, extra_headers = _best_burp_auth(session_vault)

    # Debug: if trigger_specialist_on_burp is set, dispatch a specialist alongside
    # the Burp scan.  We fire this immediately (before the launch attempt) so the
    # specialist still runs even when Burp is not reachable.
    _maybe_trigger_specialist_for_burp(run_id, url, vuln_class, session_vault)

    try:
        task_id = await burp_rest_svc.launch_active_scan(
            burp_cfg,
            url,
            cookies=cookies or None,
            extra_headers=extra_headers or None,
        )
    except Exception as exc:
        log.warning("burp_rest: failed to launch scan for %s %s: %s", vuln_class, url, exc)
        _burp_active_scan_targets.discard(target_key)
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "burp_active_scan",
            "status": "error",
            "message": f"Burp active scan launch failed: {exc}",
            "data": {"finding_id": finding_id, "url": url},
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": _burp_agent_id,
            "role": "Burp",
            "status": "failed",
            "current_task": "Launch failed",
            "outcome": str(exc)[:200],
            "_persist": True,
        })
        return

    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "burp_active_scan",
        "status": "running",
        "message": f"Burp active scan task {task_id} running for \"{title}\" — polling…",
        "data": {"finding_id": finding_id, "task_id": task_id, "url": url},
    })

    try:
        issues = await burp_rest_svc.wait_for_scan(burp_cfg, task_id)
    except Exception as exc:
        log.warning("burp_rest: scan task %d error: %s", task_id, exc)
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "burp_active_scan",
            "status": "error",
            "message": f"Burp active scan task {task_id} failed: {exc}",
            "data": {"finding_id": finding_id, "task_id": task_id},
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": _burp_agent_id,
            "role": "Burp",
            "status": "failed",
            "current_task": f"Scan task {task_id} failed",
            "outcome": str(exc)[:200],
            "_persist": True,
        })
        return

    if not issues:
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "burp_active_scan",
            "status": "complete",
            "message": f"Burp active scan task {task_id} completed — no issues found.",
            "data": {"finding_id": finding_id, "task_id": task_id, "issue_count": 0},
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": _burp_agent_id,
            "role": "Burp",
            "status": "complete",
            "current_task": f"Active scan: {url}",
            "outcome": "No issues found",
            "_persist": True,
        })
        return

    # Persist Burp findings as new ScanFinding rows
    saved_count = 0
    with Session(get_engine()) as s:
        for issue in issues:
            issue_url = issue.get("affected_url") or url
            issue_title = f"[Burp] {issue.get('name') or 'Unknown issue'}"
            owasp = "A03"  # Injection
            severity = issue.get("severity") or "medium"
            # Skip if already exists
            if _finding_exists(s, run_id=run_id, title=issue_title, affected_url=issue_url, owasp_category=owasp):
                continue
            new_finding = ScanFinding(
                test_run_id=run_id,
                page_id=page_id,
                owasp_category=owasp,
                severity=severity,
                title=issue_title,
                description=issue.get("description") or "",
                impact="",
                likelihood=f"Confidence: {issue.get('confidence', 'unknown')}",
                recommendation=issue.get("remediation") or "",
                cvss_score=0.0,
                cvss_vector="",
                affected_url=issue_url,
                evidence=f"Burp active scan task {task_id} identified: {issue.get('name')}",
                request_evidence=issue.get("request_evidence") or "",
                response_evidence=issue.get("response_evidence") or "",
                evidence_json="[]",
                screenshot_b64=None,
                finding_source="burp_active_scan",
                validation_status="confirmed",
                validation_note=f"Confirmed by Burp active scanner (task {task_id}).",
                created_at=_utcnow(),
            )
            s.add(new_finding)
            saved_count += 1
        if saved_count:
            s.commit()

    log.info(
        "burp_rest: task %d saved %d finding(s) for run_id=%s url=%s",
        task_id, saved_count, run_id, url,
    )
    if saved_count:
        _emit_scan_update(run_id)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "burp_active_scan",
        "status": "complete",
        "message": (
            f"Burp active scan task {task_id} complete — "
            f"{len(issues)} issue(s) found, {saved_count} saved."
        ),
        "data": {
            "finding_id": finding_id,
            "task_id": task_id,
            "url": url,
            "issue_count": len(issues),
            "saved_count": saved_count,
        },
    })
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": _burp_agent_id,
        "role": "Burp",
        "status": "complete",
        "current_task": f"Active scan: {url}",
        "outcome": f"{len(issues)} issue(s), {saved_count} saved",
        "_persist": True,
    })


async def _run_burp_active_scan_for_finding(
    run_id: int,
    finding: ScanFinding,
    session_vault: dict,
) -> None:
    """Fire-and-forget task: run Burp active scan on a specific finding's URL."""
    vuln_class = _finding_burp_vuln_class(finding)
    if not vuln_class:
        return
    await _run_burp_active_scan_for_target(
        run_id,
        url=finding.affected_url or "",
        title=finding.title or vuln_class,
        vuln_class=vuln_class,
        session_vault=session_vault,
        finding_id=finding.id,
        page_id=finding.page_id,
    )


def _schedule_burp_active_scan(
    run_id: int,
    finding: ScanFinding,
    session_vault: dict,
) -> None:
    """Schedule a Burp active scan as a background asyncio task (non-blocking)."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            _run_burp_active_scan_for_finding(run_id, finding, session_vault)
        )
    except RuntimeError:
        # No running event loop (e.g. during tests) — silently skip
        pass


def _schedule_burp_active_scan_for_investigation(
    run_id: int,
    tool_input: dict,
    note: str,
    session_vault: dict,
) -> None:
    candidate = _burp_investigation_candidate(tool_input, note)
    if not candidate:
        return
    url = str(tool_input.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return
    vuln_class, title = candidate
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            _run_burp_active_scan_for_target(
                run_id,
                url=url,
                title=title,
                vuln_class=vuln_class,
                session_vault=session_vault,
            )
        )
    except RuntimeError:
        pass


# ── Specialist agent dispatch ─────────────────────────────────────────────────

# Maps attack_class strings (from recon summary / agent_dispatch) to the
# corresponding boolean field on SpecialistAgentConfig.
_SPECIALIST_DISPATCH_CLASSES: dict[str, str] = {
    "idor":             "dispatch_idor",
    "auth_bypass":      "dispatch_auth_bypass",
    "sqli":             "dispatch_sqli",
    "xss":              "dispatch_xss",
    "business_logic":   "dispatch_business_logic",
    "ssrf":             "dispatch_ssrf",
    "path_traversal":   "dispatch_path_traversal",
    "cors":             "dispatch_cors",
    "crypto":           "dispatch_crypto",
    "config":           "dispatch_config",
    "file_upload":      "dispatch_file_upload",
}

# Per-run concurrency tracker: run_id → count of currently-running specialists.
_specialist_running: dict[int, int] = {}
# Per-scan-invocation dispatch counter used to generate unique agent_ids.
# This is a dict keyed by run_id so concurrent scans don't collide.
_specialist_seq: dict[int, int] = {}
# Tracks live specialist asyncio tasks so they can be cancelled on stop.
_specialist_tasks: dict[int, list[asyncio.Task]] = {}

# Pseudo-OOB reflected-SSRF detection: inject the canary URL into SSRF-prone
# parameters and flag any response that reflects the fingerprint back.
_ssrf_canary: dict[int, str] = {}
_SSRF_CANARY_URL = "https://example.com"
_SSRF_CANARY_FINGERPRINT = "Example Domain"


def _should_dispatch_specialist(
    attack_class: str,
    priority: int,
    config,  # SpecialistAgentConfigOut
) -> bool:
    """Return True if a specialist should be dispatched for this attack class."""
    if config is None or not config.enabled:
        return False
    if config.max_concurrent == 0:
        return False
    field = _SPECIALIST_DISPATCH_CLASSES.get(attack_class)
    if field is None or not getattr(config, field, False):
        return False
    # SSRF leads can rarely be confirmed without OOB infrastructure; dispatch
    # at a lower threshold so parameter-level evidence is sufficient.
    effective_min = 5 if attack_class == "ssrf" else config.min_priority
    if priority < effective_min:
        return False
    return True


def _specialist_at_capacity(run_id: int, config) -> bool:
    """Return True if the run has reached max_concurrent specialists."""
    running = _specialist_running.get(run_id, 0)
    return running >= (config.max_concurrent if config else 5)


def _next_specialist_agent_id(run_id: int, attack_class: str) -> str:
    seq = _specialist_seq.get(run_id, 0) + 1
    _specialist_seq[run_id] = seq
    return f"specialist-{attack_class}-{seq}"



async def _run_specialist_agent(
    *,
    run_id: int,
    agent_id: str,
    attack_class: str,
    target_url: str,
    rationale: str,
    recon_summary_entry: dict | None,
    session_vault: dict,
    llm_cfg,
    base_url: str,
    scanner_policy,
    max_steps: int,
    site_id: int,
) -> None:
    """Run a focused specialist agent for a specific vulnerability lead."""
    step_count = [0]  # mutable for closure

    # Build the opening brief from the dispatch payload + recon summary entry.
    recon_block = ""
    if recon_summary_entry:
        recon_block = (
            f"\nAttack class context from recon summary:\n"
            f"  class:      {recon_summary_entry.get('class', attack_class)}\n"
            f"  rationale:  {recon_summary_entry.get('rationale', '')}\n"
            f"  priority:   {recon_summary_entry.get('priority', '')}\n"
            f"  entry points: {', '.join(recon_summary_entry.get('entry_points', []))}\n"
        )

    # Derive primary session for HTTP requests from the vault.
    primary_session = (
        session_vault.get("configured_primary")
        or next(iter(session_vault.values()), None)
    )
    cookies = (primary_session or {}).get("cookies") or {}
    extra_headers = (primary_session or {}).get("extra_headers") or {}

    canary_block = ""
    if attack_class == "ssrf" and _ssrf_canary.get(run_id):
        canary_block = (
            f"\nSSRF canary: inject `{_SSRF_CANARY_URL}` as the value of SSRF-prone "
            f"parameters (url=, webhook=, redirect=, src=, callback=, fetch=, imageurl=, etc.).\n"
            f"If '{_SSRF_CANARY_FINGERPRINT}' appears in a response body, the server is "
            "fetching and reflecting external URLs — confirmed reflected SSRF.\n"
            "The tool executor will flag canary matches automatically with [SSRF CANARY MATCH].\n"
        )

    initial_message = (
        f"Target: {base_url}\n"
        f"Your mission: investigate the {attack_class} vulnerability lead below.\n"
        f"Focus URL: {target_url}\n"
        f"Lead rationale: {rationale}\n"
        f"{recon_block}"
        f"{canary_block}\n"
        f"You have a budget of {max_steps} steps. Begin immediately."
    )

    findings_written = [0]

    async def _tool_executor(tool_name: str, tool_input: dict, step: int) -> str:
        step_count[0] = step
        note = _infer_step_note(tool_name, tool_input, step)

        # Emit specialist_step as scanner_phase so it persists to scan_log
        # (Log tab) and also as specialist_step for the Agents panel thread view.
        step_event_data = {
            "agent_id": agent_id,
            "step": step,
            "action_type": (
                "http_request" if tool_name == "http_request"
                else "browser" if tool_name == "browser"
                else "tool" if tool_name == "context_tool"
                else "deciding"
            ),
            "method": tool_input.get("method"),
            "url": tool_input.get("url") or target_url,
            "observation": tool_input.get("observation"),
            "hypothesis": tool_input.get("hypothesis"),
            "payload_summary": tool_input.get("payload_summary"),
        }
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "specialist_step",
            "status": "running",
            "message": (
                f"[{agent_id}] Step {step}: "
                + (f"{tool_input.get('method')} {tool_input.get('url')}" if tool_name == "http_request"
                   else f"{tool_name}")
            ),
            "data": step_event_data,
        })
        events_svc.emit(run_id, {
            "type": "specialist_step",
            **step_event_data,
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": agent_id,
            "role": "Specialist",
            "status": "active",
            "current_task": f"Step {step}: {note}",
            "outcome": None,
        })

        if tool_name == "done":
            summary = str(tool_input.get("summary") or "")
            return summary

        if tool_name == "write_finding":
            affected = str(tool_input.get("affected_url") or target_url)
            _fw_title = str(tool_input.get("title") or "Untitled finding")
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": "reporting",
                "role": "Reporting",
                "status": "active",
                "current_task": f"Writing: {_fw_title}",
                "outcome": None,
                "_persist": True,
            })
            result_dict = {
                "source": "specialist_agent",
                "desc": note,
                "url": affected,
                "status": 200,
                "headers": {"content-type": "application/json"},
                "body": str(tool_input.get("evidence") or "")[:1000],
                "request_evidence": str(tool_input.get("request_evidence") or ""),
                "response_evidence": str(tool_input.get("response_evidence") or ""),
            }
            # Force finding_source to specialist_agent
            raw = {**tool_input, "finding_source": "specialist_agent"}
            async with _make_scanner_client(
                cookies=cookies,
                headers={"User-Agent": _UA, **extra_headers},
                timeout=scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT,
                follow_redirects=True,
                verify=False,
            ) as _hx:
                saved = await _persist_dynamic_finding(
                    run_id=run_id,
                    llm_cfg=llm_cfg,
                    raw=raw,
                    base_url=base_url,
                    pages_snapshot=[],
                    first_page_id=None,
                    result_by_url={affected: result_dict},
                    writeup_source=f"specialist:{agent_id}",
                )
            if saved is not None:
                findings_written[0] += 1
                _emit_scan_update(run_id)
                from aespa.services import validator as _validator_svc
                asyncio.create_task(
                    _validator_svc.validate_finding_inline(
                        run_id,
                        saved.id,
                        llm_cfg=llm_cfg,
                        cred_sessions=get_active_sessions(run_id) or {},
                        scanner_policy=scanner_policy,
                    )
                )
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": "reporting",
                "role": "Reporting",
                "status": "idle",
                "current_task": f"Wrote: {_fw_title}",
                "outcome": (
                    f"Saved [{tool_input.get('severity', '?')}] {_fw_title} (ID: {saved.id})"
                    if saved else
                    f"Duplicate skipped: {_fw_title}"
                ),
                "_persist": True,
            })
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "specialist_step",
                "status": "complete",
                "message": (
                    f"[{agent_id}] Step {step}: "
                    f"{'recorded finding' if saved else 'skipped duplicate'} "
                    f"{_fw_title}"
                ),
                "data": {**step_event_data, "finding_id": saved.id if saved else None},
            })
            if saved:
                return (
                    f"Finding recorded: \"{tool_input.get('title')}\" "
                    f"(severity: {tool_input.get('severity')}, ID: {saved.id})"
                )
            return (
                f"Duplicate skipped: \"{tool_input.get('title')}\" already exists. "
                "Move to a different test vector."
            )

        if tool_name == "http_request":
            _url = str(tool_input.get("url") or target_url)
            _scope_err = check_scope(_url, site_id, run_id)
            if _scope_err:
                return f"[SCOPE BLOCK] {_scope_err}"
            method = str(tool_input.get("method") or "GET").upper()
            url = str(tool_input.get("url") or target_url)
            headers = dict(tool_input.get("headers") or {})
            body = tool_input.get("body")
            use_session_label = tool_input.get("use_session") if isinstance(tool_input.get("use_session"), str) else None
            selected_session = session_vault.get(use_session_label) if use_session_label else None
            req_cookies = (selected_session or {}).get("cookies") or cookies
            req_headers = {"User-Agent": _UA, **extra_headers, **((selected_session or {}).get("extra_headers") or {}), **headers}
            async with _make_scanner_client(
                run_id=run_id,
                username="specialist",
                cookies=req_cookies,
                headers=req_headers,
                timeout=scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT,
                follow_redirects=True,
                verify=False,
                event_hooks=traffic_svc.make_httpx_hooks(run_id, username=f"specialist"),
            ) as _hx:
                try:
                    kwargs: dict = {}
                    if body is not None:
                        if isinstance(body, dict):
                            kwargs["json"] = body
                        else:
                            kwargs["content"] = str(body).encode()
                    resp = await _hx.request(method, url, **kwargs)
                    resp_body = resp.text[:BODY_READ_LIMIT]
                    _sp_canary_fp = _ssrf_canary.get(run_id)
                    _sp_canary_alert = (
                        f"[SSRF CANARY MATCH] Response contains '{_sp_canary_fp}' from "
                        f"{_SSRF_CANARY_URL} — the server fetched and reflected the canary URL. "
                        "Confirmed reflected SSRF. Write a finding immediately.\n\n"
                    ) if _sp_canary_fp and _sp_canary_fp in resp_body else ""
                    return (
                        f"{_sp_canary_alert}"
                        f"HTTP {resp.status_code} {method} {url}\n"
                        f"Response ({len(resp_body)} chars):\n{resp_body[:4096]}"
                    )
                except Exception as exc:
                    return f"Request failed: {exc}"

        if tool_name == "context_tool":
            ctx_tool = str(tool_input.get("tool") or "")
            ctx_args = tool_input.get("args") if isinstance(tool_input.get("args"), dict) else {}
            try:
                output = _run_thinking_context_tool(
                    ctx_tool, ctx_args,
                    pages_snapshot=[],
                    findings_snapshot=_load_findings_snapshot(run_id),
                    history=[],
                    run_id=run_id,
                    base_url=base_url,
                )
                import json as _json
                result = _json.dumps(output, separators=(",", ":"), default=str)
                return result[:8192]
            except Exception as exc:
                return f"Context tool error: {exc}"

        return f"Tool {tool_name} not supported in specialist context."

    # ── Run the agentic loop ───────────────────────────────────────────────────
    try:
        _specialist_running[run_id] = _specialist_running.get(run_id, 0) + 1
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": agent_id,
            "role": "Specialist",
            "status": "active",
            "current_task": f"Starting {attack_class} investigation on {target_url}",
            "outcome": None,
            "_persist": True,
        })

        await llm_svc.thinking_agentic_loop(
            llm_cfg,
            system_message=_SPECIALIST_SYSTEM_PROMPTS.get(attack_class, _SPECIALIST_SYSTEM_PROMPT),
            initial_user_message=initial_message,
            tool_executor=_tool_executor,
            stop_check=lambda: (
                step_count[0] >= max_steps
                or run_id in _thinking_stop_requested
            ),
            tools=_get_specialist_tools(attack_class),
        )

        outcome = (
            f"{findings_written[0]} new finding{'s' if findings_written[0] != 1 else ''}"
            if findings_written[0] > 0
            else "No additional issues found"
        )
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": agent_id,
            "role": "Specialist",
            "status": "complete",
            "current_task": outcome,
            "outcome": outcome,
            "_persist": True,
        })
        log.info("Specialist agent %s complete: %s", agent_id, outcome)
    except asyncio.CancelledError:
        log.info("Specialist agent %s cancelled", agent_id)
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": agent_id,
            "role": "Specialist",
            "status": "complete",
            "current_task": "Stopped",
            "outcome": "Stopped",
            "_persist": True,
        })
        raise
    except Exception as exc:
        log.warning("Specialist agent %s error: %s", agent_id, exc)
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": agent_id,
            "role": "Specialist",
            "status": "complete",
            "current_task": f"Error: {exc}",
            "outcome": "Error",
            "_persist": True,
        })
    finally:
        _specialist_running[run_id] = max(0, _specialist_running.get(run_id, 0) - 1)


def _schedule_specialist_agent(
    run_id: int,
    dispatch: dict,
    session_vault: dict,
    llm_cfg,
    base_url: str,
    scanner_policy,
    specialist_config,  # SpecialistAgentConfigOut
    recon_summary: dict | None,
    site_id: int = 0,
) -> str | None:
    """Gate-check and schedule a specialist agent as a background asyncio task.

    Returns the agent_id if dispatched, or None if dropped.
    """
    attack_class = str(dispatch.get("attack_class") or "").strip()
    priority = int(dispatch.get("priority") or 0)
    target_url = str(dispatch.get("target_url") or base_url)
    rationale = str(dispatch.get("rationale") or "")

    if not _should_dispatch_specialist(attack_class, priority, specialist_config):
        return None
    if _specialist_at_capacity(run_id, specialist_config):
        log.info(
            "Specialist dispatch for %s dropped: at capacity (%d/%d)",
            attack_class, _specialist_running.get(run_id, 0),
            specialist_config.max_concurrent,
        )
        return None

    # Find the matching entry in recon_summary.attack_classes if available.
    recon_entry: dict | None = None
    if recon_summary and isinstance(recon_summary.get("attack_classes"), list):
        for entry in recon_summary["attack_classes"]:
            if entry.get("class") == attack_class:
                recon_entry = entry
                break

    agent_id = _next_specialist_agent_id(run_id, attack_class)
    max_steps = specialist_config.max_steps if specialist_config else 30

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(
            _run_specialist_agent(
                run_id=run_id,
                agent_id=agent_id,
                attack_class=attack_class,
                target_url=target_url,
                rationale=rationale,
                recon_summary_entry=recon_entry,
                session_vault=session_vault,
                llm_cfg=llm_cfg,
                base_url=base_url,
                scanner_policy=scanner_policy,
                max_steps=max_steps,
                site_id=site_id,
            ),
            name=f"specialist-{run_id}-{agent_id}",
        )
        _specialist_tasks.setdefault(run_id, []).append(task)
        task.add_done_callback(
            lambda t, rid=run_id: _specialist_tasks.get(rid, []).remove(t)
            if t in _specialist_tasks.get(rid, []) else None
        )
    except RuntimeError:
        return None

    return agent_id


def dispatch_specialist_agent(
    run_id: int,
    attack_class: str,
    target_url: str,
    rationale: str,
    priority: int = 7,
) -> str | None:
    """Public entry-point for dispatching a specialist agent from ALICE or other callers.

    Bootstraps all scanner context (LLM config, policy, session vault, recon
    summary) from the database so callers only need run_id + attack parameters.
    Returns the agent_id string if dispatched, or None if gated out.
    """
    from aespa.services import scanner_sessions as session_svc
    from aespa.services.settings import get_llm_config_for_run, get_run_scanner_policy, get_specialist_agent_config

    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return None
        llm_cfg = get_llm_config_for_run(s, run)
        scanner_policy = get_run_scanner_policy(s, run)
        specialist_config = get_specialist_agent_config(s)
        site = s.get(Site, run.site_id)
        base_url = str(site.base_url or "").strip() if site else ""
        site_id = site.id if site else 0
        recon_summary: dict | None = None
        if run.recon_summary:
            try:
                import json as _json
                recon_summary = _json.loads(run.recon_summary)
            except Exception:
                pass

    session_vault = _merge_persisted_sessions(run_id, {})

    dispatch = {
        "attack_class": attack_class,
        "target_url": target_url,
        "rationale": rationale,
        "priority": priority,
    }

    return _schedule_specialist_agent(
        run_id=run_id,
        dispatch=dispatch,
        session_vault=session_vault,
        llm_cfg=llm_cfg,
        base_url=base_url,
        scanner_policy=scanner_policy,
        specialist_config=specialist_config,
        recon_summary=recon_summary,
        site_id=site_id,
    )


async def _persist_dynamic_finding(
    *,
    run_id: int,
    llm_cfg,
    raw: dict,
    base_url: str,
    pages_snapshot: list[dict[str, Any]],
    first_page_id: int | None,
    result_by_url: dict[str, dict],
    writeup_source: str | None = None,
    skip_normalize: bool = False,
) -> ScanFinding | None:
    """Persist a dynamic finding as soon as the thinking loop has enough evidence."""
    affected = (raw.get("affected_url") or base_url).strip() or base_url
    raw = {**raw, "affected_url": affected}

    # normalize_finding_titles renames new findings to match existing titles when
    # they share the same OWASP category — useful for the automated scanner, but
    # harmful for ALICE which already produces specific titles.  When the rename
    # produces a title that matches an existing finding at the same URL the finding
    # is silently dropped as a duplicate even though it is a distinct issue.
    if not skip_normalize:
        try:
            with Session(get_engine()) as s:
                existing = s.exec(
                    select(ScanFinding).where(ScanFinding.test_run_id == run_id)
                ).all()
                existing_summaries = [
                    {
                        "title": f.title,
                        "owasp_category": f.owasp_category,
                        "severity": f.severity,
                    }
                    for f in existing
                ]
            if existing_summaries:
                normalized = await llm_svc.normalize_finding_titles(
                    llm_cfg,
                    existing_summaries,
                    [raw],
                )
                if normalized:
                    raw = normalized[0]
                    affected = (raw.get("affected_url") or affected).strip() or affected
        except Exception as exc:
            log.warning("normalize_finding_titles failed (dynamic finding): %s", exc)

    lock = _persist_write_locks.setdefault(run_id, asyncio.Lock())
    async with lock:
        with Session(get_engine()) as s:
            page_id = _dynamic_finding_page_id(
                s,
                run_id=run_id,
                affected_url=affected,
                base_url=base_url,
                pages_snapshot=pages_snapshot,
                first_page_id=first_page_id,
            )

            if _dynamic_finding_exists(
                s,
                run_id=run_id,
                title=str(raw.get("title") or "Untitled finding"),
                affected_url=affected,
                owasp_category=str(raw.get("owasp_category") or "A00"),
            ):
                return None

            finding = _finding_from_llm(
                run_id=run_id,
                page_id=page_id,
                page_url=affected,
                raw=raw,
                result_by_url=result_by_url,
                validation_status="unvalidated",
                validation_note=None,
            )
            s.add(finding)
            s.commit()
            s.refresh(finding)
            _capture_dynamic_writeup_if_enabled(
                run_id=run_id,
                source=writeup_source or str(raw.get("finding_source") or "test_lead"),
                base_url=base_url,
                raw=raw,
                finding=finding,
                result_by_url=result_by_url,
            )
            # Snapshot data needed for the rewrite before the session closes.
            finding_id = finding.id
            _rewrite_source = writeup_source or str(raw.get("finding_source") or "test_lead")
            _rewrite_finding_dict = {
                "owasp_category": finding.owasp_category,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "impact": finding.impact,
                "likelihood": finding.likelihood,
                "recommendation": finding.recommendation,
                "cvss_score": finding.cvss_score,
                "cvss_vector": finding.cvss_vector,
                "affected_url": finding.affected_url,
                "evidence": finding.evidence,
                "request_evidence": finding.request_evidence,
                "response_evidence": finding.response_evidence,
            }
            _rewrite_evidence_dict = {
                "result": result_by_url.get(finding.affected_url) or {},
                "request_evidence": finding.request_evidence,
                "response_evidence": finding.response_evidence,
            }

    # Rewrite the finding's prose through the writeup prompt before validation.
    # Runs outside the persist lock so concurrent findings are not delayed.
    try:
        rewritten = await llm_svc.rewrite_finding_writeup(
            llm_cfg,
            source=_rewrite_source,
            base_url=base_url,
            finding_dict=_rewrite_finding_dict,
            evidence_dict=_rewrite_evidence_dict,
        )
        if rewritten:
            with Session(get_engine()) as s2:
                db_finding = s2.get(ScanFinding, finding_id)
                if db_finding is not None:
                    db_finding.owasp_category = str(rewritten.get("owasp_category") or db_finding.owasp_category)
                    db_finding.title = str(rewritten.get("title") or db_finding.title)
                    db_finding.description = str(rewritten.get("description") or db_finding.description)
                    db_finding.impact = str(rewritten.get("impact") or db_finding.impact)
                    db_finding.likelihood = str(rewritten.get("likelihood") or db_finding.likelihood)
                    db_finding.recommendation = str(rewritten.get("recommendation") or db_finding.recommendation)
                    db_finding.cvss_score = _cvss_score(rewritten.get("cvss_score"))
                    db_finding.cvss_vector = str(rewritten.get("cvss_vector") or db_finding.cvss_vector)
                    db_finding.severity = _severity_from_cvss(db_finding.cvss_score)
                    db_finding.evidence = str(rewritten.get("evidence") or db_finding.evidence)
                    db_finding.affected_url = str(rewritten.get("affected_url") or db_finding.affected_url)
                    s2.add(db_finding)
                    s2.commit()
                    s2.refresh(db_finding)
                    finding = db_finding
    except Exception as exc:
        log.warning("rewrite_finding_writeup failed for finding %s: %s", finding_id, exc)

    return finding


def _capture_dynamic_writeup_if_enabled(
    *,
    run_id: int,
    source: str,
    base_url: str,
    raw: dict,
    finding: ScanFinding,
    result_by_url: dict[str, dict],
) -> None:
    try:
        from aespa.services import reporting_debug as reporting_debug_svc

        if not reporting_debug_svc.is_capture_enabled():
            return
        affected = finding.affected_url or str(raw.get("affected_url") or base_url)
        evidence = {
            "result": result_by_url.get(affected) or result_by_url.get(str(affected)) or {},
            "request_evidence": finding.request_evidence,
            "response_evidence": finding.response_evidence,
            "evidence_items": finding.evidence_items,
        }
        reporting_debug_svc.capture_writeup(
            run_id=run_id,
            source=source,
            base_url=base_url,
            url=affected,
            finding={
                "owasp_category": finding.owasp_category,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "impact": finding.impact,
                "likelihood": finding.likelihood,
                "recommendation": finding.recommendation,
                "cvss_score": finding.cvss_score,
                "cvss_vector": finding.cvss_vector,
                "affected_url": finding.affected_url,
                "evidence": finding.evidence,
                "request_evidence": finding.request_evidence,
                "response_evidence": finding.response_evidence,
                "finding_source": finding.finding_source,
            },
            evidence=evidence,
        )
    except Exception as exc:
        log.warning("failed to capture dynamic writeup for replay: %s", exc)


def get_active_sessions(run_id: int) -> dict[int, dict] | None:
    """Return the pre-authenticated cred_sessions for a currently running scan, or None."""
    return _active_sessions.get(run_id)


# ── Thinking-scan public API ──────────────────────────────────────────────────

def is_thinking_running(run_id: int) -> bool:
    return run_id in _thinking_tasks


def request_thinking_stop(run_id: int) -> None:
    _thinking_stop_requested.add(run_id)
    # Cancel the main scan task immediately so it doesn't wait out a full LLM
    # round-trip or Playwright navigation before seeing the stop flag.
    task = _thinking_tasks.get(run_id)
    if task and not task.done():
        task.cancel()
    # Cancel all in-flight specialist tasks for this run.
    for spec_task in list(_specialist_tasks.get(run_id, [])):
        if not spec_task.done():
            spec_task.cancel()
    if is_thinking_running(run_id):
        _thinking_scan_status[run_id] = "stopping"
        _emit_thinking_status(run_id)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "stop_requested",
        "status": "warning",
        "message": "Stop requested — cancelling in-flight requests.",
    })
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": "scanner",
        "role": "Test Lead",
        "status": "active",
        "current_task": "Stopping scan…",
        "outcome": None,
    })


def get_thinking_scan_status(run_id: int) -> dict:
    if is_thinking_running(run_id):
        status = _thinking_scan_status.get(run_id, "running")
    else:
        status = _thinking_scan_status.get(run_id, "idle")
    with Session(get_engine()) as s:
        findings_count = len(s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all())
    return {"status": status, "findings_count": findings_count}


DEFAULT_THINKING_MAX_STEPS = 120


async def start_thinking_scan(run_id: int) -> None:
    """Start an LLM-directed (thinking) scan that dynamically decides what to test."""
    if run_id in _thinking_tasks:
        return
    # Clear any stale checkpoint so the scan starts fresh.
    checkpoint_svc.clear_checkpoint(run_id)
    task = asyncio.create_task(
        _thinking_scan_task(run_id),
        name=f"thinking-scan-{run_id}",
    )
    _thinking_tasks[run_id] = task
    task.add_done_callback(lambda _: _thinking_tasks.pop(run_id, None))


async def start_thinking_scan_resume(run_id: int) -> None:
    """Resume an interrupted LLM-directed scan from the last saved checkpoint.

    Unlike ``start_thinking_scan``, this does NOT clear the checkpoint so that
    ``_do_thinking_scan`` can detect it and restore the LLM conversation.
    """
    if run_id in _thinking_tasks:
        return
    task = asyncio.create_task(
        _thinking_scan_task(run_id),
        name=f"thinking-scan-resume-{run_id}",
    )
    _thinking_tasks[run_id] = task
    task.add_done_callback(lambda _: _thinking_tasks.pop(run_id, None))


# ── Thinking-scan task wrapper & core ─────────────────────────────────────────

def _emit_thinking_status(run_id: int) -> None:
    events_svc.emit(run_id, {"type": "thinking_scan_update", **get_thinking_scan_status(run_id)})


async def _thinking_scan_task(run_id: int) -> None:
    _thinking_scan_status[run_id] = "running"
    _emit_thinking_status(run_id)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "scan_started",
        "status": "start",
        "message": "Dynamic scan started.",
    })
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": "scanner",
        "role": "Test Lead",
        "status": "active",
        "current_task": "Dynamic scan started",
        "outcome": None,
        "_persist": True,
    })
    try:
        await _do_thinking_scan(run_id)
    except asyncio.CancelledError:
        log.info("Thinking scan task cancelled for run_id=%s", run_id)
        _thinking_scan_status[run_id] = "stopped"
        _emit_thinking_status(run_id)
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "scan_stopped",
            "status": "warning",
            "message": "Dynamic scan stopped by user.",
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "complete",
            "current_task": "Scan stopped",
            "outcome": "Stopped by user",
            "_persist": True,
        })
        raise
    except Exception as exc:
        log.exception("Thinking scan task failed for run_id=%s", run_id)
        _thinking_scan_status[run_id] = "failed"
        _emit_thinking_status(run_id)
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "failed",
            "current_task": "Scan failed",
            "outcome": str(exc)[:200],
            "_persist": True,
        })
    finally:
        _thinking_stop_requested.discard(run_id)
        _specialist_running.pop(run_id, None)
        _specialist_seq.pop(run_id, None)
        _specialist_tasks.pop(run_id, None)
        _ssrf_canary.pop(run_id, None)


async def _run_post_scan_llm_review(
    run_id: int,
    llm_cfg,
    baseline_max_id: int,
) -> None:
    """LLM pre-screen pass over findings created during the current dynamic scan.

    Findings the model flags as likely false positives are moved to
    ``validation_status='low_confidence'`` with the reasoning attached as
    ``validation_note``.  Findings that look credible remain ``unvalidated``
    so the normal per-finding validation flow can process them later.

    Only findings with id > baseline_max_id (i.e. created during this scan)
    are reviewed.
    """
    with Session(get_engine()) as s:
        q = (
            select(ScanFinding)
            .where(ScanFinding.test_run_id == run_id)
            .where(ScanFinding.validation_status == "unvalidated")
        )
        if baseline_max_id > 0:
            q = q.where(ScanFinding.id > baseline_max_id)
        candidates = s.exec(q).all()
        for f in candidates:
            s.expunge(f)

    if not candidates:
        return

    total_review_batches = (len(candidates) + 9) // 10
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "post_scan_review",
        "status": "start",
        "message": f"LLM pre-screen: reviewing {len(candidates)} finding(s) across {total_review_batches} turn(s)…",
    })
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": "reporting",
        "role": "Reporting",
        "status": "active",
        "current_task": f"Pre-screening {len(candidates)} finding(s) for false positives…",
        "_persist": True,
    })

    BATCH = 10
    low_confidence_ids: list[int] = []
    reasons: dict[int, str] = {}

    for batch_start in range(0, len(candidates), BATCH):
        batch = candidates[batch_start : batch_start + BATCH]
        turn_num = batch_start // BATCH + 1
        batch_lines = []
        for f in batch:
            ep = f.affected_url or "(no URL)"
            evidence_preview = (f.evidence or "")[:300].replace("\n", " ")
            batch_lines.append(
                f"ID:{f.id} | {f.severity.upper()} | {f.owasp_category} | {f.title}\n"
                f"  URL: {ep}\n"
                f"  Evidence: {evidence_preview}"
            )
        prompt = (
            "You are reviewing security findings produced by an automated web application "
            "scanner. For each finding decide whether it looks credible (ACCEPT) or is "
            "likely a false positive (LOW_CONFIDENCE).\n\n"
            "Mark LOW_CONFIDENCE only when there is a concrete reason to doubt the finding: "
            "the evidence shows a generic error unrelated to the claimed vulnerability, "
            "the payload is reflected as plain text without execution, the response status "
            "contradicts the claim, or the evidence is empty or too vague to confirm anything. "
            "When uncertain, mark ACCEPT.\n\n"
            "FINDINGS TO REVIEW:\n"
            + "\n\n".join(batch_lines)
            + "\n\nFor EACH finding respond with exactly one line:\n"
            "  <ID> | ACCEPT\n"
            "  <ID> | LOW_CONFIDENCE:<short reason>\n"
            "Do NOT include any other text."
        )
        batch_low_confidence: list[int] = []
        try:
            verdict_text = await llm_svc.plain_completion(llm_cfg, prompt)
        except Exception as exc:
            log.warning("Post-scan review batch failed (non-fatal): %s", exc)
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "post_review_turn",
                "status": "complete",
                "message": f"Turn {turn_num}/{total_review_batches}: review failed — {exc}",
                "data": {"turn": turn_num, "total_turns": total_review_batches, "error": str(exc)},
            })
            continue

        for line in verdict_text.strip().splitlines():
            parts = [p.strip() for p in line.split("|", 1)]
            if len(parts) != 2:
                continue
            try:
                fid = int(parts[0].replace("ID:", "").strip())
            except ValueError:
                continue
            verdict = parts[1].strip()
            if verdict.upper().startswith("LOW_CONFIDENCE"):
                reason = (
                    verdict.split(":", 1)[1].strip()
                    if ":" in verdict
                    else "Pre-screen: low confidence"
                )
                low_confidence_ids.append(fid)
                batch_low_confidence.append(fid)
                reasons[fid] = reason

        accepted_this_batch = len(batch) - len(batch_low_confidence)
        batch_msg = (
            f"Turn {turn_num}/{total_review_batches}: reviewed {len(batch)} finding(s)"
            f" → {accepted_this_batch} accepted"
            + (f", {len(batch_low_confidence)} flagged low confidence" if batch_low_confidence else "")
        )
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "post_review_turn",
            "status": "complete",
            "message": batch_msg,
            "data": {
                "turn": turn_num,
                "total_turns": total_review_batches,
                "batch_size": len(batch),
                "accepted": accepted_this_batch,
                "low_confidence": len(batch_low_confidence),
            },
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "reporting",
            "role": "Reporting",
            "status": "active",
            "current_task": batch_msg,
            "_persist": True,
        })

    if low_confidence_ids:
        with Session(get_engine()) as s:
            for fid in low_confidence_ids:
                row = s.get(ScanFinding, fid)
                if row and row.validation_status == "unvalidated":
                    row.validation_status = "low_confidence"
                    row.validation_note = reasons.get(fid, "Pre-screen flagged as low confidence.")
                    s.add(row)
            s.commit()
        for fid in low_confidence_ids:
            events_svc.emit(run_id, {
                "type": "finding_validation_update",
                "finding_id": fid,
                "validation_status": "low_confidence",
                "validation_note": reasons.get(fid, "Pre-screen flagged as low confidence."),
            })

    accepted = len(candidates) - len(low_confidence_ids)
    review_complete_msg = (
        f"Pre-screen complete: {accepted} accepted, "
        f"{len(low_confidence_ids)} flagged as low confidence."
    )
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "post_scan_review",
        "status": "complete",
        "message": review_complete_msg,
    })
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": "reporting",
        "role": "Reporting",
        "status": "complete",
        "current_task": "Pre-screen complete",
        "outcome": review_complete_msg,
        "_persist": True,
    })
    log.info(
        "Post-scan review run_id=%s: %d accepted, %d low_confidence",
        run_id, accepted, len(low_confidence_ids),
    )


async def _do_thinking_scan(run_id: int) -> None:
    """LLM-directed scan: the model decides each HTTP request to issue, observes
    the response, and adaptively chooses what to probe next — exactly like a human
    tester working through curl."""
    # ── Load config ───────────────────────────────────────────────────────────
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config_for_run(s, run)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration. Configure it in Settings first.")
        scanner_policy = get_run_scanner_policy(s, run)
        creds = list(site.credentials)
        thinking_max_steps = 0  # unused — no step limit

        # Crawled pages — used for context and for resolving page_id on findings.
        all_pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
        ).all()
        pages_snapshot = [
            {
                "id": p.id,
                "url": p.url,
                "title": p.title or "",
                "context": p.llm_context or "",
                "page_text": p.page_text or "",
                "req_auth": p.req_auth,
                "takes_input": p.takes_input,
                "has_object_ref": p.has_object_ref,
                "has_business_logic": p.has_business_logic,
            }
            for p in all_pages
        ]
        first_page_id = all_pages[0].id if all_pages else None

        # Existing findings from the regular scan — feed as context so the LLM
        # knows what has already been found and can focus on new attack surface.
        existing_findings = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all()
        findings_snapshot = [
            {
                "title":       f.title,
                "severity":    f.severity,
                "owasp":       f.owasp_category,
                "affected_url": f.affected_url,
                "description": f.description[:200],
            }
            for f in existing_findings
        ]
        # Capture the highest finding ID before the scan starts so the
        # post-scan review only considers findings created during this run.
        _pre_scan_max_id = max((f.id for f in existing_findings if f.id), default=0)

        # Load intel items for WSTG skill selection.
        _intel_rows = s.exec(
            select(TargetIntelItem)
            .where(TargetIntelItem.test_run_id == run_id)
            .limit(500)
        ).all()
        intel_items_for_selector = [
            {"kind": i.kind, "key": i.key, "value": i.value, "url": i.url}
            for i in _intel_rows
        ]

        upstream_proxy = get_upstream_proxy_config(s)
        scanner_proxy_url = upstream_proxy.proxy_url if upstream_proxy.proxy_scanner else None
        llm_proxy_url = upstream_proxy.proxy_url if upstream_proxy.proxy_llm else None
        specialist_cfg = get_specialist_agent_config(s)
        global_header_cfg = get_global_http_header_config(s)

        site_id = site.id  # captured before expunge for scope checks
        for obj in [*creds, site, llm_cfg, run]:
            s.expunge(obj)

    global_http_header: dict[str, str] = {}
    if global_header_cfg.header_name and global_header_cfg.header_value:
        global_http_header = {global_header_cfg.header_name: global_header_cfg.header_value}

    _scanner_proxy_var.set(scanner_proxy_url)
    _scanner_global_header_var.set(global_http_header)
    llm_svc.set_llm_proxy(llm_proxy_url)
    llm_svc.set_run_context(run_id, lambda evt: events_svc.emit(run_id, evt))

    base_url      = str(site.base_url or "").strip()
    login_url     = site.login_url
    requires_auth = site.requires_auth

    log.info("=== Thinking scan start: run_id=%s base_url=%s ===", run_id, base_url)
    # Status is set to "running" by the task wrapper before calling this function.

    # ── Resume detection ──────────────────────────────────────────────────────
    # If a checkpoint was saved from a previous run, restore it so the agentic
    # loop continues the exact same LLM conversation.  On a fresh start the
    # caller must call checkpoint_svc.clear_checkpoint(run_id) first.
    _resume_checkpoint = checkpoint_svc.load_checkpoint(run_id)
    resuming = _resume_checkpoint is not None
    if resuming:
        log.info(
            "Resuming thinking scan for run_id=%s from step %s",
            run_id,
            _resume_checkpoint.get("step_count", "?"),
        )
        _resume_msg = (
            f"Resuming scan from step {_resume_checkpoint.get('step_count', '?')} "
            f"({len(_resume_checkpoint.get('history') or [])} prior actions in context)."
        )
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "thinking_scan",
            "status": "resuming",
            "message": _resume_msg,
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "active",
            "current_task": f"Resuming from step {_resume_checkpoint.get('step_count', '?')}…",
            "outcome": None,
            "_persist": True,
        })

    if not resuming:
        # Run JS sink analysis so xss_sink intel items exist in the DB before the LLM
        # loop starts. The thinking-scan agent can then find them via target_inventory
        # without re-fetching and re-parsing JS source itself.
        async with _make_scanner_client(run_id=run_id, username="js_sink", verify=False, timeout=REQUEST_TIMEOUT) as _hx_sink:
            await _analyse_js_sinks(run_id, _hx_sink, scanner_policy=scanner_policy)

    # Keep the standing prompt compact. Detailed crawl transcripts and prior findings
    # are available through context tools so they are only sent when needed.
    recon_summary: dict | None = None
    if not resuming:
        recon_summary = task_graph_svc.build_recon_summary(run_id)

    crawl_context = _build_thinking_context_from_recon_summary(
        run_id,
        base_url,
        findings_snapshot,
    )
    intel_context = _build_target_intelligence_context(run_id)
    if intel_context:
        crawl_context = f"{crawl_context}\n\n{intel_context}"

    # Resolve a login URL for the selector: prefer the site-level one, else fall back
    # to the first credential that carries its own login_url. A configured login URL is
    # itself a credential endpoint, so this catches login forms at non-standard paths.
    _login_url_for_selector = (login_url or "").strip()
    if not _login_url_for_selector:
        for _c in creds:
            _cu = (getattr(_c, "login_url", None) or "").strip()
            if _cu:
                _login_url_for_selector = _cu
                break

    # Select and inject WSTG skill reference blocks based on observed attack surface.
    _selected_skills = llm_svc.select_wstg_skills(
        pages_snapshot,
        intel_items_for_selector,
        requires_auth=requires_auth,
        base_url=base_url,
        login_url=_login_url_for_selector,
    )
    _skill_context = llm_svc.build_wstg_skill_context(_selected_skills)
    if _skill_context:
        crawl_context = f"{crawl_context}\n\n{_skill_context}"
        log.info(
            "WSTG skills injected for run_id=%s: %s",
            run_id,
            ", ".join(sorted(_selected_skills)),
        )

    seeded_task_graph = task_graph_svc.seed_task_graph(run_id, summary=recon_summary) if not resuming else {}
    if seeded_task_graph.get("hypotheses_created") or seeded_task_graph.get("tasks_created"):
        events_svc.emit(run_id, {
            "type": "task_graph_update",
            "reason": "seeded",
            "data": seeded_task_graph,
        })

    creds_for_llm = [
        {
            "username": c.username,
            "password": c.password,
            "login_url": _login_url_for_credential(login_url, c),
        }
        for c in creds
    ]

    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "thinking_scan",
        "status": "start",
        "message": "LLM-directed scan started.",
    })

    # ── Bootstrap browser + auth session (Playwright) ─────────────────────────
    cookie_jar: dict[str, str] = {}
    auth_token: Optional[str] = None

    # ── Agentic loop ──────────────────────────────────────────────────────────
    history:     list[dict] = []
    all_results: list[dict] = []
    progressive_findings_count = 0
    session_svc.ensure_anonymous_session(run_id, source="dynamic_scan")
    session_vault: dict[str, dict] = session_svc.load_session_vault(run_id)
    consecutive_context_tools = 0
    failed_url_counts: dict[str, int] = {}  # "METHOD:url" → count of 404/error responses
    blocked_urls: set[str] = set()          # URLs tried 3+ times and still failing
    browser_url_counts: dict[str, int] = {}  # url → count of browser visits with failed steps
    login_failure_counts: dict[str, int] = {}  # url → count of 401/403 on login endpoints
    auth_bootstrap_warned = False           # prevent duplicate bootstrap warning events

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        browser_ctx = await browser.new_context(user_agent=_UA, ignore_https_errors=True, **_playwright_proxy())
        initial_headers = _playwright_global_headers()
        if initial_headers:
            await browser_ctx.set_extra_http_headers(initial_headers)
        traffic_svc.setup_playwright_logging(browser_ctx, run_id)
        pw_page = await browser_ctx.new_page()

        try:
            await pw_page.goto(base_url, wait_until="domcontentloaded", timeout=20_000)
        except Exception:
            pass

        if requires_auth and creds:
            # Check if the crawl phase already captured a guided session for this credential.
            # If so, inject it directly rather than opening another browser window.
            _primary_vault_session = (
                session_vault.get(f"guided_{creds[0].id}")
                or session_vault.get("configured_primary")
            )
            if _primary_vault_session and _primary_vault_session.get("cookies"):
                log.info(
                    "Dynamic scan: reusing vault session '%s' for %s (skipping auth bootstrap)",
                    _primary_vault_session.get("label", "?"), creds[0].username,
                )
                cookie_list = [
                    {"name": k, "value": v, "url": base_url}
                    for k, v in _primary_vault_session["cookies"].items()
                ]
                if cookie_list:
                    await browser_ctx.add_cookies(cookie_list)
                if _primary_vault_session.get("extra_headers"):
                    await browser_ctx.set_extra_http_headers(
                        _playwright_global_headers(_primary_vault_session["extra_headers"])
                    )
                try:
                    await pw_page.reload(wait_until="domcontentloaded", timeout=12_000)
                except Exception:
                    pass
            else:
                from aespa.services.crawler import _authenticate

                await _authenticate(
                    pw_page,
                    _login_url_for_credential(login_url, creds[0]),
                    creds[0],
                    run_id,
                )

        raw_cookies = await browser_ctx.cookies()
        cookie_jar = {c["name"]: c["value"] for c in raw_cookies}
        for key in ["access_token", "token", "jwt", "auth_token", "id_token",
                    "authToken", "accessToken"]:
            try:
                val = await pw_page.evaluate(
                    f"() => localStorage.getItem('{key}') || sessionStorage.getItem('{key}')"
                )
                if val:
                    auth_token = val
                    break
            except Exception:
                pass

        extra_headers: dict[str, str] = {}
        if auth_token:
            extra_headers["Authorization"] = f"Bearer {auth_token}"

        if requires_auth and creds and not cookie_jar and not auth_token:
            _cred_username = creds[0].username
            _warn_msg = (
                f"Configured credentials for '{_cred_username}' did not produce a session "
                f"after the login attempt — the password may be incorrect. "
                f"Check the username and password in site settings."
            )
            log.warning("Dynamic scan auth bootstrap: %s", _warn_msg)
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "credential_warning",
                "status": "warning",
                "message": _warn_msg,
            })
            auth_bootstrap_warned = True
            crawl_context = (
                f"WARNING: Configured credentials for '{_cred_username}' did not authenticate "
                f"successfully. The password may be wrong. Test unauthenticated attack surface "
                f"and do not spend steps retrying this credential.\n\n{crawl_context}"
            )

        if requires_auth and creds and (cookie_jar or extra_headers):
            configured_primary = {
                "label": "configured_primary",
                "kind": _session_kind(cookie_jar, extra_headers),
                "username": creds[0].username,
                "credential_id": creds[0].id,
                "source": "configured credential auth bootstrap",
                "extra_headers": extra_headers,
                "cookies": cookie_jar,
            }
            session_vault["configured_primary"] = configured_primary
            _record_session(
                run_id,
                label="configured_primary",
                session_data=configured_primary,
                source="dynamic_scan_auth_bootstrap",
                credential_id=creds[0].id,
                metadata={"login_url": _login_url_for_credential(login_url, creds[0])},
            )

        # ── Detect client-controlled authorization cookies ─────────────────────
        # If the login response set cookies whose names or values suggest that the
        # server trusts them for access-control decisions (e.g. SysAdmin=true,
        # Manager=false, role=admin), inject a high-priority prompt note so the
        # LLM tests cookie forgery before anything else.
        _priv_name_patterns = [
            "admin", "sysadmin", "role", "manager", "privilege", "level",
            "group", "perm", "isloggedin", "elevated", "superuser", "isadmin",
            "staff", "access",
        ]
        _bool_values = {"true", "false", "1", "0", "yes", "no"}
        _session_cookie_names = {
            "session", "sessid", "sessionid", "asp.net_sessionid",
            "phpsessid", "jsessionid", "csrftoken", "xsrf-token",
        }
        _suspicious_auth_cookies = {
            name: value
            for name, value in cookie_jar.items()
            if name.lower() not in _session_cookie_names
            and (
                any(pat in name.lower() for pat in _priv_name_patterns)
                or value.lower() in _bool_values
            )
        }
        if _suspicious_auth_cookies:
            _cookie_detail = ", ".join(
                f"{k}={v}" for k, v in _suspicious_auth_cookies.items()
            )
            log.info(
                "Thinking scan: suspicious client-controlled auth cookies detected: %s",
                _cookie_detail,
            )
            _cookie_alert = (
                f"PRIORITY FINDING LEAD — Client-controlled authorization cookies detected "
                f"after login: {_cookie_detail}. "
                f"The server appears to trust these cookie values for access-control. "
                f"Immediately test whether forging them (e.g. flipping a boolean flag or "
                f"changing a role value) grants unauthorized elevated access. "
                f"Issue HTTP requests with a manually crafted Cookie header that modifies "
                f"these values and compare responses to baseline. "
                f"This is a broken access control (A01/A07) finding if the server honours them."
            )
            crawl_context = f"{_cookie_alert}\n\n{crawl_context}"

        deterministic_sessions = _deterministic_sessions_from_vault(run_id, session_vault)
        _active_sessions[run_id] = deterministic_sessions
        if run_id not in _thinking_stop_requested:
            await _run_deterministic_site_modules(
                run_id=run_id,
                base_url=base_url,
                cred_sessions=deterministic_sessions,
                scanner_policy=scanner_policy,
            )

        async with _make_scanner_client(
            run_id=run_id,
            username=creds[0].username if creds else None,
            cookies=cookie_jar,
            headers={"User-Agent": _UA, **extra_headers},
            timeout=scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT,
            follow_redirects=True,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(
                run_id, username=creds[0].username if creds else None
            ),
        ) as hx:
            # ── Continuous session path (Anthropic native tool use) ────────────
            if llm_cfg.provider in llm_svc.AGENTIC_LOOP_PROVIDERS:
                progressive_findings_count = await _do_agentic_thinking_loop(
                    run_id=run_id, llm_cfg=llm_cfg, base_url=base_url,
                    crawl_context=crawl_context, creds_for_llm=creds_for_llm,
                    session_vault=session_vault, pages_snapshot=pages_snapshot,
                    findings_snapshot=findings_snapshot, first_page_id=first_page_id,
                    scanner_policy=scanner_policy,
                    hx=hx, browser_ctx=browser_ctx, pw_page=pw_page,
                    history=history, all_results=all_results,
                    resume_from=_resume_checkpoint,
                    specialist_config=specialist_cfg,
                    recon_summary=recon_summary,
                    site_id=site_id,
                    creds=creds,
                    login_url=login_url or "",
                )
            # ── Step-by-step path (fallback for non-agentic providers) ──────
            step = 0
            while True:
                if llm_cfg.provider in llm_svc.AGENTIC_LOOP_PROVIDERS:
                    break  # agentic loop already ran above
                step += 1
                if run_id in _thinking_stop_requested:
                    break

                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "thinking_step",
                    "status": "deciding",
                    "message": f"Step {step}: LLM deciding next action…",
                    "data": {"step": step},
                })
                events_svc.emit(run_id, {
                    "type": "agent_status",
                    "agent_id": "scanner",
                    "role": "Test Lead",
                    "status": "active",
                    "current_task": f"Step {step}: deciding next action…",
                    "outcome": None,
                })

                # Ask the LLM what to do next.
                try:
                    task_context = task_graph_svc.build_task_graph_context(run_id)
                    step_context = (
                        f"{crawl_context}\n\n{task_context}"
                        if task_context else crawl_context
                    )
                    if blocked_urls:
                        blocked_list = ", ".join(sorted(blocked_urls)[:12])
                        step_context = (
                            f"{step_context}\n\n"
                            f"BLOCKED PATHS — already failed 3+ times, do NOT probe these again: "
                            f"{blocked_list}. Switch to a completely different attack surface."
                        )
                    action = await llm_svc.thinking_next_action(
                        llm_cfg,
                        target_url=base_url,
                        crawl_context=step_context,
                        history=history,
                        current_step=step,
                        credentials=creds_for_llm,
                        sessions=[
                            {
                                "label": label,
                                "kind": session.get("kind"),
                                "username": session.get("username"),
                                "source": session.get("source"),
                            }
                            for label, session in session_vault.items()
                        ],
                        emit_fn=lambda evt: events_svc.emit(run_id, evt),
                    )
                except Exception as exc:
                    log.warning("thinking_next_action error at step %d: %s", step, exc)
                    break

                if action.get("action") == "done":
                    log.info("LLM completed thinking scan at step %d: %s", step, action.get("summary", ""))
                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_scan",
                        "status": "complete",
                        "message": f"LLM finished at step {step}: {action.get('summary', '')}",
                    })
                    break

                action_type = action.get("action")
                note = action.get("note") or f"Step {step}"

                if action_type == "tool":
                    tool_name = str(action.get("tool") or "").strip()
                    args = action.get("args") if isinstance(action.get("args"), dict) else {}
                    budget_reason = _context_budget_reason(action)
                    if (
                        consecutive_context_tools >= CONTEXT_TOOL_CHECKPOINT_INTERVAL
                        and not budget_reason
                    ):
                        output = _context_tool_checkpoint_output(
                            tool_name,
                            consecutive_context_tools,
                        )
                    else:
                        output = _run_thinking_context_tool(
                            tool_name,
                            args,
                            pages_snapshot=pages_snapshot,
                            findings_snapshot=findings_snapshot,
                            history=history,
                            run_id=run_id,
                            base_url=base_url,
                        )
                        if budget_reason:
                            output["context_budget_reason"] = budget_reason
                            output["context_budget_extended"] = True
                            consecutive_context_tools = 1
                        else:
                            consecutive_context_tools += 1
                    result_text = json.dumps(output, separators=(",", ":"), default=str)
                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "complete",
                        "message": f"Step {step}: context tool {tool_name} returned {len(result_text):,} chars",
                        "data": {
                            "step": step,
                            "tool": tool_name,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                        },
                    })
                    history.append(_thinking_tool_result_record(step, tool_name, args, output, note))
                    continue

                consecutive_context_tools = 0
                active_task_id = task_graph_svc.mark_task_running_for_action(run_id, action, step)

                if action_type == "finding_write":
                    affected = action.get("affected_url") or base_url
                    result = {
                        "source": "finding_write",
                        "desc": note,
                        "url": affected,
                        "status": 200,
                        "headers": {"content-type": "application/json"},
                        "body": str(action.get("evidence") or "")[:1000],
                        "request_evidence": str(action.get("request_evidence") or ""),
                        "response_evidence": str(action.get("response_evidence") or ""),
                    }
                    saved = await _persist_dynamic_finding(
                        run_id=run_id,
                        llm_cfg=llm_cfg,
                        raw=action,
                        base_url=base_url,
                        pages_snapshot=pages_snapshot,
                        first_page_id=first_page_id,
                        result_by_url={str(affected): result},
                        writeup_source="test_lead",
                    )
                    if saved is not None:
                        progressive_findings_count += 1
                        findings_snapshot.append({
                            "title": saved.title,
                            "severity": saved.severity,
                            "owasp": saved.owasp_category,
                            "affected_url": saved.affected_url,
                            "description": saved.description[:200],
                        })
                    history.append({
                        "step": step,
                        "note": note,
                        "method": "FINDING_WRITE",
                        "url": affected,
                        "request_headers": {},
                        "request_body": {
                            "title": action.get("title"),
                            "owasp_category": action.get("owasp_category"),
                            "cvss_score": action.get("cvss_score"),
                        },
                        "response_status": 200,
                        "response_headers": {"content-type": "application/json"},
                        "response_body": (
                            f"{'Saved' if saved is not None else 'Skipped duplicate'} "
                            f"finding: {action.get('title', 'Untitled finding')}. "
                            + (
                                "This finding already exists (recorded by a prior step). "
                                "Do NOT write it again. Your next action MUST "
                                "probe a completely different endpoint or attack category. "
                                if saved is None else ""
                            )
                            + f"{str(action.get('evidence') or '')[:1200]}"
                        ),
                    })
                    task_graph_svc.complete_task_after_result(
                        run_id,
                        active_task_id,
                        step=step,
                        method="FINDING_WRITE",
                        url=str(affected),
                        status=200,
                        note=note,
                        response_excerpt=str(action.get("evidence") or "")[:2000],
                        finding_written=saved is not None,
                    )
                    if saved is not None:
                        task_graph_svc.mark_related_hypothesis_confirmed(run_id, active_task_id)
                        _emit_scan_update(run_id)
                        _emit_thinking_status(run_id)
                        _schedule_burp_active_scan(run_id, saved, session_vault)
                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "complete",
                        "message": (
                            f"Step {step}: "
                            f"{'recorded finding' if saved is not None else 'skipped duplicate finding'} "
                            f"{action.get('title', 'Untitled finding')}"
                        ),
                        "data": {
                            "step": step,
                            "affected_url": affected,
                            "finding_id": saved.id if saved is not None else None,
                            "note": note,
                        },
                    })
                    continue

                # Initialise per-action state that the step_record block always reads.
                _js_paths: list[str] = []

                if action_type == "browser":
                    url = (action.get("url") or base_url).strip()
                    method = "BROWSER"
                    steps = action.get("steps") or []
                    use_session = action.get("use_session") or action.get("as_session")
                    use_session = use_session if isinstance(use_session, str) else None
                    selected_session = session_vault.get(use_session) if use_session else None
                    payload_summary = _thinking_browser_payload_summary(steps)
                    action_message = _thinking_action_log_message(step, method, url, action)

                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": payload_summary,
                            "use_session": use_session,
                        },
                    })

                    try:
                        if selected_session and selected_session.get("cookies"):
                            cookie_list = [
                                {"name": k, "value": v, "url": url}
                                for k, v in selected_session.get("cookies", {}).items()
                            ]
                            if cookie_list:
                                await browser_ctx.add_cookies(cookie_list)
                        await browser_ctx.set_extra_http_headers(
                            _playwright_global_headers(
                                (selected_session.get("extra_headers") or {}) if selected_session else {}
                            )
                        )
                    except Exception:
                        pass
                    result = await _run_thinking_browser_action(
                        pw_page,
                        action,
                        default_url=base_url,
                        scanner_policy=scanner_policy,
                    )
                    # Traffic is captured in-function and already formatted into body.
                    resp_body = str(result.get("body") or "")[:BODY_READ_LIMIT]
                    resp_status = result.get("status") or 0
                    resp_headers = result.get("headers") or {}
                    url = result.get("url") or url
                    req_body = {"steps": steps}
                    result["desc"] = note

                    # Track repeated failed browser interactions on the same URL.
                    _action_log = result.get("action_log") or []
                    _had_failures = any(" failed:" in line for line in _action_log)
                    if _had_failures:
                        _browser_url = action.get("url") or base_url
                        browser_url_counts[_browser_url] = (
                            browser_url_counts.get(_browser_url, 0) + 1
                        )
                        if browser_url_counts[_browser_url] >= 3:
                            blocked_urls.add(_browser_url)
                            log.debug(
                                "Thinking scan: browser URL blocked after 3 failed attempts: %s",
                                _browser_url,
                            )
                elif action_type == "jwt":
                    method = "JWT"
                    url = f"jwt://forge/{action.get('store_as') or 'token'}"
                    claims = action.get("claims") if isinstance(action.get("claims"), dict) else {}
                    header = action.get("header") if isinstance(action.get("header"), dict) else None
                    secret = str(action.get("secret") or "")
                    action_message = _thinking_action_log_message(step, method, url, action)
                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": _compact_log_value(claims),
                        },
                    })
                    try:
                        token = _sign_hs256_jwt(secret, claims, header)
                        label = action.get("store_as") or _session_label("forged_jwt", session_vault)
                        session_vault[label] = {
                            "label": label,
                            "kind": "bearer",
                            "username": f"sub:{claims.get('sub')}" if claims.get("sub") is not None else None,
                            "source": "jwt action",
                            "extra_headers": {"Authorization": f"Bearer {token}"},
                            "cookies": {},
                        }
                        _record_session(
                            run_id,
                            label=label,
                            session_data=session_vault[label],
                            source="dynamic_scan_jwt_action",
                            metadata={"claims": claims, "header": header or {"typ": "JWT", "alg": "HS256"}},
                        )
                        resp_status = 200
                        resp_headers = {"content-type": "application/json"}
                        resp_body = json.dumps({
                            "store_as": label,
                            "token_type": "Bearer",
                            "authorization_header": "Bearer [REDACTED_JWT]",
                            "claims": claims,
                        })
                    except Exception as exc:
                        resp_status = 0
                        resp_headers = {}
                        resp_body = f"JWT signing failed: {exc}"
                    req_body = {
                        "claims": claims,
                        "header": header or {"typ": "JWT", "alg": "HS256"},
                        "store_as": action.get("store_as"),
                    }
                    request_evidence = (
                        f"JWT FORGE\nClaims:\n{json.dumps(claims, indent=2)[:2000]}"
                    )
                    response_evidence = f"Status: {resp_status}\n{resp_body[:3000]}"
                    result = {
                        "desc": note,
                        "url": url,
                        "status": resp_status,
                        "headers": resp_headers,
                        "body": resp_body[:1000],
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                    }
                elif action_type == "decode_jwt":
                    method = "JWT_DECODE"
                    raw_token = str(action.get("token") or "").strip()
                    decode_secret = action.get("secret") or None
                    url = "jwt://decode"
                    action_message = _thinking_action_log_message(step, method, url, action)
                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step, "method": method, "url": url, "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                        },
                    })
                    if not raw_token:
                        resp_status = 0
                        resp_body = "decode_jwt: missing token"
                    else:
                        decoded = _decode_jwt(raw_token, secret=decode_secret)
                        resp_status = 200
                        resp_body = json.dumps(decoded)
                    resp_headers = {"content-type": "application/json"}
                    request_evidence = (
                        f"JWT DECODE\nVerify signature: {decode_secret is not None}"
                    )
                    response_evidence = f"Status: {resp_status}\n{resp_body[:3000]}"
                    result = {
                        "desc": note,
                        "url": url,
                        "status": resp_status,
                        "headers": resp_headers,
                        "body": resp_body[:1000],
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                    }
                elif action_type == "credential_check":
                    method = "CREDENTIAL_CHECK"
                    url = (action.get("url") or "").strip()
                    candidates = action.get("candidates")
                    if not isinstance(candidates, list):
                        candidates = []
                    candidates = [c for c in candidates if isinstance(c, dict)][:20]
                    username_field = action.get("username_field") or "username"
                    password_field = action.get("password_field") or "password"
                    success_statuses = action.get("success_statuses") or [200, 201]
                    try:
                        success_statuses = {int(s) for s in success_statuses}
                    except Exception:
                        success_statuses = {200, 201}
                    headers = action.get("headers") or {}
                    action_message = _thinking_action_log_message(step, method, url, action)

                    if not url:
                        log.warning("Thinking scan step %d: credential_check missing URL.", step)
                        break

                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": f"{len(candidates)} candidate(s)",
                        },
                    })

                    attempts: list[dict] = []
                    resp_status = 0
                    resp_headers = {}
                    for candidate in candidates:
                        created_label = None
                        body = {
                            username_field: candidate.get("username") or candidate.get("email") or "",
                            password_field: candidate.get("password") or "",
                        }
                        try:
                            merged_headers = dict(hx.headers)
                            merged_headers.update(headers)
                            merged_headers.setdefault("Content-Type", "application/json")
                            resp = await hx.request(
                                str(action.get("method") or "POST").upper(),
                                url,
                                json=body,
                                headers=merged_headers,
                            )
                            resp_status = resp.status_code
                            resp_headers = dict(resp.headers)
                            response_excerpt = resp.text[:800]
                            success = resp.status_code in success_statuses
                            token = _extract_bearer_token_from_body(resp.text) if success else None
                            if token:
                                username = (
                                    candidate.get("username")
                                    or candidate.get("email")
                                    or "discovered"
                                )
                                label = _session_label(str(username), session_vault)
                                created_label = label
                                session_vault[label] = {
                                    "label": label,
                                    "kind": "bearer",
                                    "username": username,
                                    "source": "credential_check",
                                    "extra_headers": {"Authorization": f"Bearer {token}"},
                                    "cookies": {},
                                }
                                _record_session(
                                    run_id,
                                    label=label,
                                    session_data=session_vault[label],
                                    source="dynamic_scan_credential_check",
                                    metadata={"login_url": url},
                                )
                            if success:
                                _maybe_persist_discovered_credential(
                                    run_id,
                                    username=str(
                                        candidate.get("username")
                                        or candidate.get("email")
                                        or "discovered"
                                    ),
                                    password=str(candidate.get("password") or ""),
                                    login_url=url or None,
                                )
                        except Exception as exc:
                            response_excerpt = f"Request failed: {exc}"
                            success = False
                        attempts.append({
                            **_redact_candidate(candidate),
                            "status": resp_status,
                            "success": success,
                            "session_label": created_label,
                            "response_excerpt": (
                                _redact_sensitive_text(response_excerpt[:300])
                                if success else ""
                            ),
                        })
                        await sleep_between_probes(scanner_policy)

                    successes = [a for a in attempts if a["success"]]
                    resp_body = json.dumps({
                        "attempts": attempts,
                        "successes": successes,
                        "stopped_at_cap": len((action.get("candidates") or [])) > 20,
                    })
                    req_body = {
                        "username_field": username_field,
                        "password_field": password_field,
                        "candidates": [_redact_candidate(c) for c in candidates],
                    }
                    request_evidence = (
                        f"CREDENTIAL CHECK {url}\n"
                        f"Candidates:\n{json.dumps(req_body['candidates'], indent=2)[:2000]}"
                    )
                    response_evidence = (
                        f"Successes: {len(successes)} of {len(attempts)}\n"
                        f"{json.dumps(attempts, indent=2)[:3000]}"
                    )
                    result = {
                        "desc": note,
                        "url": url,
                        "status": 200 if successes else resp_status,
                        "headers": resp_headers,
                        "body": resp_body[:1000],
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                    }
                    resp_status = result["status"]
                elif action_type == "register_account":
                    method = "REGISTER_ACCOUNT"
                    url = (action.get("url") or "").strip()
                    if not url:
                        log.warning("Thinking scan step %d: register_account missing URL.", step)
                        break
                    headers = action.get("headers") if isinstance(action.get("headers"), dict) else {}
                    success_statuses = action.get("success_statuses") or [200, 201, 204]
                    try:
                        success_statuses = {int(s) for s in success_statuses}
                    except Exception:
                        success_statuses = {200, 201, 204}
                    account = _disposable_account_fields(action, base_url=base_url)
                    body = account["body"]
                    redacted_body = _redacted_account_body(body, account["password_field"])
                    store_as = str(action.get("store_as") or f"disposable_{account['username']}")
                    use_session = action.get("use_session") or action.get("as_session")
                    use_session = use_session if isinstance(use_session, str) else None
                    selected_session = session_vault.get(use_session) if use_session else None
                    body_format = str(action.get("body_format") or "json").lower()
                    action_message = _thinking_action_log_message(step, method, url, action)

                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": f"register {account['username']} / {account['email']}",
                            "use_session": use_session,
                        },
                    })

                    resp_status = 0
                    resp_headers = {}
                    resp_body = ""
                    created_label = None
                    duration_ms: int | None = None
                    try:
                        merged_headers = dict(hx.headers)
                        if selected_session and selected_session.get("extra_headers"):
                            merged_headers.update(selected_session["extra_headers"])
                        merged_headers.update(headers)
                        selected_cookies = (
                            selected_session.get("cookies")
                            if selected_session and selected_session.get("cookies")
                            else None
                        )
                        if body_format == "form":
                            merged_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                            started = time.perf_counter()
                            resp = await hx.request(
                                str(action.get("method") or "POST").upper(),
                                url,
                                data=body,
                                headers=merged_headers,
                                cookies=selected_cookies,
                            )
                        else:
                            merged_headers.setdefault("Content-Type", "application/json")
                            started = time.perf_counter()
                            resp = await hx.request(
                                str(action.get("method") or "POST").upper(),
                                url,
                                json=body,
                                headers=merged_headers,
                                cookies=selected_cookies,
                            )
                        duration_ms = int((time.perf_counter() - started) * 1000)
                        resp_status = resp.status_code
                        resp_headers = dict(resp.headers)
                        raw_resp_body = resp.text[:BODY_READ_LIMIT]
                        resp_body = _redact_sensitive_text(raw_resp_body)
                        success = resp.status_code in success_statuses
                        token = _extract_bearer_token_from_body(raw_resp_body) if success else None
                        response_cookies = {k: v for k, v in resp.cookies.items()} if success else {}
                        extra_headers = {"Authorization": f"Bearer {token}"} if token else {}
                        if success:
                            created_label = _session_label(store_as, session_vault)
                            session_vault[created_label] = {
                                "label": created_label,
                                "kind": _session_kind(response_cookies, extra_headers),
                                "username": account["username"],
                                "source": "register_account",
                                "extra_headers": extra_headers,
                                "cookies": response_cookies,
                                "metadata": account["metadata"],
                            }
                            _record_session(
                                run_id,
                                label=created_label,
                                session_data=session_vault[created_label],
                                source="dynamic_scan_register_account",
                                metadata={
                                    **account["metadata"],
                                    "method": str(action.get("method") or "POST").upper(),
                                    "status": resp.status_code,
                                    "body_format": body_format,
                                },
                            )
                    except Exception as exc:
                        log.warning("Thinking scan step %d register_account error (%s): %s", step, url, exc)
                        resp_body = f"Registration request failed: {exc}"

                    req_body = redacted_body
                    request_evidence = _request_evidence(
                        f"REGISTER_ACCOUNT {url}\n{json.dumps(redacted_body, sort_keys=True)}"
                    )
                    response_evidence = _response_evidence(
                        "Status: "
                        f"{resp_status}\n"
                        + "\n".join(f"{k}: {v}" for k, v in resp_headers.items())
                        + f"\n\nCreated session label: {created_label or 'none'}\n{resp_body}"
                    )
                    result = {
                        "desc": note,
                        "url": url,
                        "status": resp_status,
                        "headers": resp_headers,
                        "body": resp_body,
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                        "evidence_json": _http_evidence_items_json(
                            request_evidence,
                            response_evidence,
                            summary=f"Disposable account registration attempted for {account['username']}.",
                            status=resp_status,
                            duration_ms=duration_ms,
                            action_outcome=(
                                f"Registration succeeded; stored reusable session label '{created_label}'."
                                if created_label else "Registration did not produce reusable auth material."
                            ),
                            marker=created_label or "no reusable auth material captured",
                            confidence="observed",
                        ),
                    }
                else:
                    # Execute the HTTP request.
                    method  = (action.get("method") or "GET").upper()
                    url     = (action.get("url") or "").strip()
                    headers = action.get("headers") or {}
                    body    = action.get("body")
                    use_session = action.get("use_session") or action.get("as_session")
                    use_session = use_session if isinstance(use_session, str) else None
                    selected_session = session_vault.get(use_session) if use_session else None
                    action_message = _thinking_action_log_message(step, method, url, action)
                    payload_summary = _thinking_payload_summary(url, body)

                    if not url:
                        log.warning("Thinking scan step %d: LLM returned empty URL — stopping.", step)
                        break

                    events_svc.emit(run_id, {
                        "type": "scanner_phase",
                        "phase": "thinking_step",
                        "status": "running",
                        "message": action_message,
                        "data": {
                            "step": step,
                            "method": method,
                            "url": url,
                            "note": note,
                            "observation": action.get("observation"),
                            "hypothesis": action.get("hypothesis"),
                            "payload_purpose": action.get("payload_purpose"),
                            "payload_summary": payload_summary,
                            "use_session": use_session,
                        },
                    })

                    req_body_str = ""
                    duration_ms: int | None = None
                    try:
                        merged_headers = dict(hx.headers)
                        if selected_session and selected_session.get("extra_headers"):
                            merged_headers.update(selected_session["extra_headers"])
                        merged_headers.update(headers)
                        selected_cookies = (
                            selected_session.get("cookies")
                            if selected_session and selected_session.get("cookies")
                            else None
                        )
                        if isinstance(body, dict):
                            merged_headers.setdefault("Content-Type", "application/json")
                            started = time.perf_counter()
                            resp = await hx.request(method, url, json=body, headers=merged_headers, cookies=selected_cookies)
                            duration_ms = int((time.perf_counter() - started) * 1000)
                            req_body_str = json.dumps(body)[:800]
                        elif isinstance(body, str) and body:
                            started = time.perf_counter()
                            resp = await hx.request(method, url, content=body, headers=merged_headers, cookies=selected_cookies)
                            duration_ms = int((time.perf_counter() - started) * 1000)
                            req_body_str = body[:800]
                        else:
                            started = time.perf_counter()
                            resp = await hx.request(method, url, headers=merged_headers, cookies=selected_cookies)
                            duration_ms = int((time.perf_counter() - started) * 1000)
                        raw_resp_body = resp.text[:BODY_READ_LIMIT]
                        token = _extract_bearer_token_from_body(raw_resp_body)
                        if token and resp.status_code < 400:
                            label = _session_label(
                                str(action.get("store_as") or "http_token"),
                                session_vault,
                            )
                            session_vault[label] = {
                                "label": label,
                                "kind": "bearer",
                                "username": None,
                                "source": f"{method} {url}",
                                "extra_headers": {"Authorization": f"Bearer {token}"},
                                "cookies": {},
                            }
                            _record_session(
                                run_id,
                                label=label,
                                session_data=session_vault[label],
                                source="dynamic_scan_http_response",
                                metadata={"method": method, "url": url},
                            )
                        resp_body    = _redact_sensitive_text(raw_resp_body)
                        resp_status  = resp.status_code
                        resp_headers = dict(resp.headers)
                        # Auto-extract API endpoint paths from JavaScript responses so the
                        # LLM can find them without needing to parse JS bodies manually.
                        _ct = resp_headers.get("content-type", "").lower()
                        _is_js = "javascript" in _ct or url.split("?")[0].lower().endswith(".js")
                        if _is_js and resp_status == 200:
                            # Capture /api/... paths and also bare paths that look like
                            # API routes (e.g. '/transfers', '/own-transfers', '/payments').
                            _raw_paths = re.findall(
                                r'["\']((?:/api)?/[a-zA-Z0-9_-][a-zA-Z0-9_/{}.-]*)["\']',
                                raw_resp_body,
                            )
                            # Filter out obvious static assets and keep meaningful paths.
                            _js_paths = list(dict.fromkeys(
                                p for p in _raw_paths
                                if len(p) >= 4
                                and not p.endswith((".js", ".css", ".html", ".png", ".ico"))
                                and not p.startswith("//")
                            ))[:40]
                            if _js_paths:
                                try:
                                    from aespa.services.crawler import _save_intel_item as _si
                                    for _p in _js_paths:
                                        _si(
                                            run_id=run_id, kind="endpoint", key=_p, value=_p,
                                            url=url, method="GET", source="js_mining_dynamic",
                                            confidence=0.8,
                                            evidence=f"Extracted from {url} at step {step}",
                                        )
                                except Exception as _exc:
                                    log.debug("Dynamic JS path extraction failed: %s", _exc)
                    except Exception as exc:
                        log.warning("Thinking scan step %d HTTP error (%s %s): %s", step, method, url, exc)
                        resp_body    = f"Request failed: {exc}"
                        resp_status  = 0
                        resp_headers = {}

                    req_body = body
                    request_evidence = _request_evidence(
                        f"{method} {url}\n{json.dumps(headers, sort_keys=True)}\n{req_body_str}"
                    )
                    response_evidence = _response_evidence(
                        "Status: "
                        f"{resp_status}\n"
                        + "\n".join(f"{k}: {v}" for k, v in resp_headers.items())
                        + f"\n\n{resp_body}"
                    )
                    result = {
                        "desc": note,
                        "url": url,
                        "status": resp_status,
                        "duration_ms": duration_ms,
                        "headers": resp_headers,
                        "body": resp_body,
                        "request_evidence": request_evidence,
                        "response_evidence": response_evidence,
                        "action_outcome": "HTTP request completed." if resp_status else "HTTP request failed.",
                        "evidence_json": _http_evidence_items_json(
                            request_evidence,
                            response_evidence,
                            summary=note,
                            status=resp_status,
                            duration_ms=duration_ms,
                            action_outcome="HTTP request completed." if resp_status else "HTTP request failed.",
                            confidence="observed",
                        ),
                    }

                log.info("Thinking scan step %d: %s %s → %s", step, method, url, resp_status)

                _resp_body_for_history = resp_body
                if _js_paths:
                    _paths_note = (
                        f"[{len(_js_paths)} API path(s) auto-extracted from JS and added to "
                        f"target intelligence: {', '.join(_js_paths[:15])}]\n\n"
                    )
                    _resp_body_for_history = _paths_note + resp_body

                step_record = {
                    "step":             step,
                    "note":             note,
                    "method":           method,
                    "url":              url,
                    "request_headers":  action.get("headers") or {},
                    "request_body":     req_body,
                    "response_status":  resp_status,
                    "response_headers": resp_headers,
                    "response_body":    _resp_body_for_history,
                }
                history.append(step_record)

                # Track failed or uninformative probes and surface them as blocked URLs.
                # "Uninformative" includes error codes AND 200s with an empty body — the
                # latter catches API endpoints that silently return nothing (e.g. content-
                # length: 0) regardless of how many times they are retried.
                _probe_key = f"{method}:{url}"
                _is_uninformative = (
                    resp_status in (0, 404, 405)
                    or resp_status >= 500
                    or (resp_status == 200 and len(resp_body.strip()) < 5)
                )
                if _is_uninformative:
                    failed_url_counts[_probe_key] = failed_url_counts.get(_probe_key, 0) + 1
                    if failed_url_counts[_probe_key] >= 3:
                        blocked_urls.add(url)
                        log.debug(
                            "Thinking scan: URL blocked after 3 uninformative responses: %s %s",
                            method, url,
                        )
                # For repeated failures push the tool budget up so the LLM must think
                # (pick tools or a different approach) rather than blindly retrying.
                if failed_url_counts.get(_probe_key, 0) >= 2:
                    consecutive_context_tools = max(consecutive_context_tools - 1, 0)

                # Detect repeated 401/403 on login-like endpoints — likely a bad password.
                _is_login_endpoint = method == "POST" and any(
                    term in url.lower()
                    for term in ("/login", "/auth/", "/signin", "/authenticate", "/token")
                )
                if _is_login_endpoint and resp_status in (401, 403):
                    login_failure_counts[url] = login_failure_counts.get(url, 0) + 1
                    if login_failure_counts[url] == 2 and not auth_bootstrap_warned:
                        _cred_username = creds[0].username if creds else "configured user"
                        _lf_msg = (
                            f"Repeated {resp_status} from {url} — the configured credentials "
                            f"for '{_cred_username}' are likely incorrect. "
                            f"Check the password in site settings and do not retry this login."
                        )
                        log.warning("Thinking scan: %s", _lf_msg)
                        events_svc.emit(run_id, {
                            "type": "scanner_phase",
                            "phase": "credential_warning",
                            "status": "warning",
                            "message": _lf_msg,
                        })

                all_results.append(result)
                task_graph_svc.complete_task_after_result(
                    run_id,
                    active_task_id,
                    step=step,
                    method=method,
                    url=url,
                    status=resp_status,
                    note=note,
                    response_excerpt=resp_body[:2000],
                )

                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "thinking_step",
                    "status": "complete",
                    "message": f"Step {step}: {method} {url} → {resp_status}",
                    "data": {"step": step, "status": resp_status, "note": note},
                })

                await sleep_between_probes(scanner_policy)

    # ── Analyse results ───────────────────────────────────────────────────────
    if all_results:
        _thinking_scan_status[run_id] = "analysing"
        _emit_thinking_status(run_id)
        deterministic_saved = _run_deterministic_analysis_for_dynamic_results(
            run_id=run_id,
            base_url=base_url,
            pages_snapshot=pages_snapshot,
            first_page_id=first_page_id,
            results=all_results,
        )
        total_batches = len(llm_svc._chunk_probe_results(all_results))
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "thinking_analysis",
            "status": "start",
            "message": (
                f"Analysing {len(all_results)} probe result(s); "
                f"{progressive_findings_count} progressive and "
                f"{deterministic_saved} deterministic finding(s) already recorded…"
            ),
        })
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "reporting",
            "role": "Reporting",
            "status": "active",
            "current_task": f"Analysing {len(all_results)} probe result(s) across {total_batches} LLM turn(s)…",
            "_persist": True,
        })
        try:
            _reporting_batch_findings: list[dict] = []

            async def _on_batch_complete(turn_num: int, batch_size: int, batch_findings: list[dict]) -> None:
                _reporting_batch_findings.extend(batch_findings)
                found = len(batch_findings)
                cumulative = len(_reporting_batch_findings)
                msg = (
                    f"Turn {turn_num}/{total_batches}: analysed {batch_size} probe(s)"
                    + (f" → {found} finding(s) identified" if found else " → no new findings")
                    + (f" ({cumulative} total so far)" if cumulative and turn_num < total_batches else "")
                )
                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "reporting_turn",
                    "status": "complete",
                    "message": msg,
                    "data": {
                        "turn": turn_num,
                        "total_turns": total_batches,
                        "batch_size": batch_size,
                        "findings_this_turn": found,
                        "findings_cumulative": cumulative,
                        "titles": [f.get("title", "Untitled") for f in batch_findings],
                    },
                })
                events_svc.emit(run_id, {
                    "type": "agent_status",
                    "agent_id": "reporting",
                    "role": "Reporting",
                    "status": "active",
                    "current_task": msg,
                    "_persist": True,
                })

            raw_findings = await llm_svc.analyse_probes(
                llm_cfg, base_url, all_results, on_batch_complete=_on_batch_complete
            )
            # Normalise titles against existing findings so the same vulnerability
            # class gets a consistent title regardless of which step found it.
            if raw_findings:
                with Session(get_engine()) as _s:
                    _existing = _s.exec(
                        select(ScanFinding).where(ScanFinding.test_run_id == run_id)
                    ).all()
                if _existing:
                    _summaries = [
                        {"title": f.title, "owasp_category": f.owasp_category, "severity": f.severity}
                        for f in _existing
                    ]
                    try:
                        raw_findings = await llm_svc.normalize_finding_titles(
                            llm_cfg, _summaries, raw_findings
                        )
                    except Exception as _ne:
                        log.warning("normalize_finding_titles failed (thinking scan): %s", _ne)
            with Session(get_engine()) as s:
                result_by_url = {r["url"]: r for r in all_results}
                saved_count = 0
                duplicate_count = 0

                for raw in raw_findings:
                    affected = (raw.get("affected_url") or base_url).strip()
                    page_id = _dynamic_finding_page_id(
                        s,
                        run_id=run_id,
                        affected_url=affected,
                        base_url=base_url,
                        pages_snapshot=pages_snapshot,
                        first_page_id=first_page_id,
                    )
                    if _dynamic_finding_exists(
                        s,
                        run_id=run_id,
                        title=str(raw.get("title") or "Untitled finding"),
                        affected_url=affected,
                        owasp_category=str(raw.get("owasp_category") or "A00"),
                    ):
                        duplicate_count += 1
                        continue
                    finding = _finding_from_llm(
                        run_id=run_id,
                        page_id=page_id,
                        page_url=affected,
                        raw=raw,
                        result_by_url=result_by_url,
                    )
                    s.add(finding)
                    saved_count += 1
                s.commit()
            message = f"Analysis complete — {saved_count} finding(s) recorded."
            if duplicate_count:
                message += f" {duplicate_count} duplicate finding(s) skipped."
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_analysis",
                "status": "complete",
                "message": message,
            })
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": "reporting",
                "role": "Reporting",
                "status": "complete",
                "current_task": "Probe analysis complete",
                "outcome": message,
                "_persist": True,
            })
        except Exception as exc:
            log.warning("Thinking scan analysis failed: %s", exc)

    stopped = run_id in _thinking_stop_requested
    if not stopped:
        try:
            await _run_post_scan_llm_review(run_id, llm_cfg, _pre_scan_max_id)
        except Exception as _rev_exc:
            log.warning("Post-scan review failed (non-fatal): %s", _rev_exc)
    _thinking_scan_status[run_id] = "stopped" if stopped else "complete"
    _emit_thinking_status(run_id)
    log.info("=== Thinking scan %s: run_id=%s ===", "stopped" if stopped else "complete", run_id)
    # Count findings created during this scan for the agent outcome summary.
    with Session(get_engine()) as _s:
        _finding_count = len(_s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all())
    events_svc.emit(run_id, {
        "type": "agent_status",
        "agent_id": "scanner",
        "role": "Test Lead",
        "status": "complete",
        "current_task": "Scan complete",
        "outcome": f"{_finding_count} finding(s) recorded",
        "_persist": True,
    })
    llm_svc.clear_run_context()


# ── Agentic loop helper ───────────────────────────────────────────────────────

# Maps Anthropic tool names → action strings expected by the task-graph service.
_TOOL_NAME_TO_ACTION: dict[str, str] = {
    "http_request":    "http",
    "browser":         "browser",
    "context_tool":    "tool",
    "write_finding":   "finding_write",
    "forge_jwt":       "jwt",
    "decode_jwt":      "jwt",
    "credential_check": "credential_check",
    "register_account": "register_account",
    "agent_dispatch":  "agent_dispatch",
    "done":            "done",
}


async def _do_agentic_thinking_loop(
    *,
    run_id: int,
    llm_cfg,
    base_url: str,
    crawl_context: str,
    creds_for_llm: list[dict],
    session_vault: dict,
    pages_snapshot: list[dict],
    findings_snapshot: list[dict],
    first_page_id: Optional[int],
    scanner_policy,
    hx,
    browser_ctx,
    pw_page,
    history: list[dict],
    all_results: list[dict],
    resume_from: dict | None = None,
    specialist_config=None,
    recon_summary: dict | None = None,
    site_id: int = 0,
    creds: list | None = None,
    login_url: str = "",
    # API-mode overrides — when provided these replace the web-scan defaults
    system_message_override: str | None = None,
    context_tool_fn=None,   # callable(tool_name, args, **kw) -> dict; replaces _run_thinking_context_tool
    post_finding_fn=None,   # callable(ScanFinding) -> None; called after every persisted finding
    post_probe_fn=None,     # callable(url, method, owasp_category) -> None; called after every http_request
    persist_credential_fn=None,  # callable(username, password, login_url) -> None; replaces site-credential persistence
) -> int:
    """Run the continuous tool-use agentic scan (Anthropic native tool use path).

    Maintains a growing messages list so the model reads its own prior reasoning
    verbatim.  Returns progressive_findings_count.

    resume_from: optional checkpoint dict returned by ``checkpoint_svc.load_checkpoint``.
        When provided, the loop restores history, blocked URLs, and counters from
        the checkpoint and passes the persisted messages list to thinking_agentic_loop
        so the LLM continues the exact same conversation.
    """
    progressive_findings_count = 0
    _consecutive_ctx_tools = [0]  # mutable via list so the closure can write it
    _consecutive_auth_failures = [0]  # primary-session 401/403 streak
    _reauth_count = [0]  # total re-auth attempts this scan
    _REAUTH_THRESHOLD = 5
    _REAUTH_MAX = 2

    async def _try_reauth() -> bool:
        """Re-authenticate on pw_page and refresh hx + session_vault cookies."""
        if not creds or _reauth_count[0] >= _REAUTH_MAX:
            return False
        _reauth_count[0] += 1
        _consecutive_auth_failures[0] = 0
        log.info(
            "Dynamic scan: session expiry detected — re-authenticating (attempt %d/%d)",
            _reauth_count[0], _REAUTH_MAX,
        )
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "session_reauth",
            "status": "start",
            "message": (
                f"Session expired — re-authenticating with "
                f"{creds[0].username} (attempt {_reauth_count[0]})…"
            ),
        })
        try:
            from aespa.services.crawler import _authenticate
            _cred_login_url = _login_url_for_credential(login_url, creds[0])
            await _authenticate(pw_page, _cred_login_url, creds[0], run_id)
            raw_cookies = await browser_ctx.cookies()
            new_cookies = {c["name"]: c["value"] for c in raw_cookies}
            # Refresh the httpx client's cookie jar in-place
            for name, value in new_cookies.items():
                hx.cookies.set(name, value)
            # Refresh session vault
            if new_cookies:
                prev = session_vault.get("configured_primary") or {}
                session_vault["configured_primary"] = {
                    **prev,
                    "cookies": new_cookies,
                }
                _record_session(
                    run_id,
                    label="configured_primary",
                    session_data=session_vault["configured_primary"],
                    source="dynamic_scan_reauth",
                    credential_id=creds[0].id,
                    metadata={"login_url": _cred_login_url},
                )
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "session_reauth",
                "status": "complete",
                "message": "Re-authentication succeeded — continuing scan.",
            })
            return bool(new_cookies)
        except Exception as _reauth_exc:
            log.warning("Dynamic scan re-auth failed: %s", _reauth_exc)
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "session_reauth",
                "status": "error",
                "message": f"Re-authentication failed: {_reauth_exc}",
            })
            return False

    # ── Restore state from checkpoint (resume path) ───────────────────────────
    resume_messages: list[dict] | None = None
    if resume_from:
        history.extend(resume_from.get("history") or [])
        _blocked: set[str] = resume_from.get("blocked_urls") or set()
        _failed: dict[str, int] = resume_from.get("failed_url_counts") or {}
        progressive_findings_count = resume_from.get("progressive_findings_count") or 0
        _consecutive_ctx_tools[0] = resume_from.get("consecutive_context_tools") or 0
        resume_messages = resume_from.get("messages") or None
        log.info(
            "Resuming agentic loop for run_id=%s from step %s (%d history entries, "
            "%d messages in LLM context)",
            run_id,
            resume_from.get("step_count", "?"),
            len(history),
            len(resume_messages) if resume_messages else 0,
        )
    else:
        _blocked: set[str] = set()
        _failed: dict[str, int] = {}

    _ssrf_canary[run_id] = _SSRF_CANARY_FINGERPRINT

    pending_session_labels: set[str] = set()

    def _mark_session_pending(label: str | None) -> None:
        if label:
            pending_session_labels.add(str(label))

    def _mark_session_used(label: str | None, status: int) -> None:
        if label and status not in (0, 401, 403):
            pending_session_labels.discard(str(label))

    def _agentic_done_check(tool_input: dict, step: int) -> tuple[bool, str]:
        if pending_session_labels:
            label_list = ", ".join(sorted(pending_session_labels)[:5])
            return False, (
                "Assessment is not complete. You created or captured reusable "
                f"authenticated session label(s) that have not been exercised yet: "
                f"{label_list}. Before calling done, call http_request with "
                f"use_session set to one of those labels against authenticated API "
                f"endpoints such as /api/profile, /api/accounts, /api/transfers, "
                f"or another endpoint discovered in the JavaScript/API inventory. "
                f"If a session fails, report the exact status and then try a different "
                f"valid session or endpoint."
            )
        if history:
            last = history[-1]
            last_status = int(last.get("response_status") or 0)
            last_method = str(last.get("method") or "")
            if last_status in (401, 403) and any(
                (sd.get("extra_headers") or {}).get("Authorization")
                for sd in session_vault.values()
            ):
                return False, (
                    "Assessment is not complete. The previous request ended with "
                    f"{last_status} ({last_method} {last.get('url')}) while bearer "
                    "sessions exist in the session vault. Retry the relevant protected "
                    "endpoint with a concrete use_session label before calling done."
                )
        return True, ""

    # ── Build the initial user message ────────────────────────────────────────
    creds_text = ""
    if creds_for_llm:
        c_lines = [
            f"  - username={c['username']}  password={c['password']}"
            + (f"  login_url={c['login_url']}" if c.get("login_url") else "")
            for c in creds_for_llm
        ]
        creds_text = "Test credentials:\n" + "\n".join(c_lines)

    sessions_text = ""
    if session_vault:
        s_lines = [
            f"  - label={label}  kind={sd.get('kind', 'bearer')}"
            + (f"  username={sd.get('username')}" if sd.get("username") else "")
            + (f"  source={sd.get('source')}" if sd.get("source") else "")
            for label, sd in session_vault.items()
        ]
        sessions_text = (
            "Reusable authenticated sessions — use these labels instead of "
            "re-authenticating:\n" + "\n".join(s_lines)
        )

    task_context = task_graph_svc.build_task_graph_context(run_id)
    initial_message = "\n\n".join(filter(None, [
        f"Target: {base_url}",
        f"Application context:\n{crawl_context}",
        creds_text,
        sessions_text,
        task_context or "",
        "Begin the assessment.",
    ]))

    # ── Tool executor closure ─────────────────────────────────────────────────
    async def _tool_executor(tool_name: str, tool_input: dict, step: int) -> str:
        nonlocal progressive_findings_count
        note = _infer_step_note(tool_name, tool_input, step)

        # Emit live agent_status update for every agentic step (SSE only, not persisted).
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "active",
            "current_task": f"Step {step}: {note}",
            "outcome": None,
        })

        # ── context_tool ──────────────────────────────────────────────────────
        if tool_name == "context_tool":
            inner_tool = str(tool_input.get("tool") or "").strip()
            args = tool_input.get("args") if isinstance(tool_input.get("args"), dict) else {}
            budget_reason = _context_budget_reason(tool_input)
            if (
                _consecutive_ctx_tools[0] >= CONTEXT_TOOL_CHECKPOINT_INTERVAL
                and not budget_reason
            ):
                output = _context_tool_checkpoint_output(
                    inner_tool,
                    _consecutive_ctx_tools[0],
                )
            else:
                if context_tool_fn is not None:
                    output = context_tool_fn(
                        inner_tool, args,
                        pages_snapshot=pages_snapshot,
                        findings_snapshot=findings_snapshot,
                        history=history,
                        run_id=run_id,
                        base_url=base_url,
                    )
                else:
                    output = _run_thinking_context_tool(
                        inner_tool, args,
                        pages_snapshot=pages_snapshot,
                        findings_snapshot=findings_snapshot,
                        history=history,
                        run_id=run_id,
                        base_url=base_url,
                    )
                if budget_reason:
                    output["context_budget_reason"] = budget_reason
                    output["context_budget_extended"] = True
                    _consecutive_ctx_tools[0] = 1
                else:
                    _consecutive_ctx_tools[0] += 1
            result_text = json.dumps(output, separators=(",", ":"), default=str)
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "complete",
                "message": (
                    f"Step {step}: context tool {inner_tool} returned "
                    f"{len(result_text):,} chars"
                ),
                "data": {
                    "step": step,
                    "tool": inner_tool,
                    "note": note,
                    "observation": tool_input.get("observation"),
                    "hypothesis": tool_input.get("hypothesis"),
                },
            })
            history.append(
                _thinking_tool_result_record(step, inner_tool, args, output, note)
            )
            return result_text

        # Non-context tools reset the consecutive counter
        _consecutive_ctx_tools[0] = 0

        action_for_task = {
            "action": _TOOL_NAME_TO_ACTION.get(tool_name, tool_name),
            **tool_input,
        }
        active_task_id = task_graph_svc.mark_task_running_for_action(
            run_id, action_for_task, step
        )

        # ── write_finding ─────────────────────────────────────────────────────
        if tool_name == "write_finding":
            affected = str(tool_input.get("affected_url") or base_url)
            _fw_title = str(tool_input.get("title") or "Untitled finding")
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": "reporting",
                "role": "Reporting",
                "status": "active",
                "current_task": f"Writing: {_fw_title}",
                "outcome": None,
                "_persist": True,
            })
            fw_result = {
                "source": "finding_write",
                "desc": note,
                "url": affected,
                "status": 200,
                "headers": {"content-type": "application/json"},
                "body": str(tool_input.get("evidence") or "")[:1000],
                "request_evidence": str(tool_input.get("request_evidence") or ""),
                "response_evidence": str(tool_input.get("response_evidence") or ""),
            }
            saved = await _persist_dynamic_finding(
                run_id=run_id,
                llm_cfg=llm_cfg,
                raw=tool_input,
                base_url=base_url,
                pages_snapshot=pages_snapshot,
                first_page_id=first_page_id,
                result_by_url={affected: fw_result},
                writeup_source="test_lead",
            )
            if saved is not None:
                progressive_findings_count += 1
                if post_finding_fn is not None:
                    try:
                        post_finding_fn(saved)
                    except Exception as _pf_exc:
                        log.warning("post_finding_fn error: %s", _pf_exc)
                findings_snapshot.append({
                    "title": saved.title,
                    "severity": saved.severity,
                    "owasp": saved.owasp_category,
                    "affected_url": saved.affected_url,
                    "description": saved.description[:200],
                })
            history.append({
                "step": step,
                "note": note,
                "method": "FINDING_WRITE",
                "url": affected,
                "request_headers": {},
                "request_body": {
                    "title": tool_input.get("title"),
                    "owasp_category": tool_input.get("owasp_category"),
                },
                "response_status": 200,
                "response_headers": {"content-type": "application/json"},
                "response_body": (
                    f"{'Saved' if saved is not None else 'Skipped duplicate'} "
                    f"finding: {tool_input.get('title', 'Untitled')}. "
                    + (
                        "This finding already exists. Do NOT write it again. "
                        "Move to a completely different endpoint or attack category. "
                        if saved is None else ""
                    )
                    + str(tool_input.get("evidence") or "")[:600]
                ),
            })
            task_graph_svc.complete_task_after_result(
                run_id, active_task_id,
                step=step, method="FINDING_WRITE", url=affected, status=200,
                note=note,
                response_excerpt=str(tool_input.get("evidence") or "")[:2000],
                finding_written=saved is not None,
            )
            if saved is not None:
                task_graph_svc.mark_related_hypothesis_confirmed(run_id, active_task_id)
                _emit_scan_update(run_id)
                _emit_thinking_status(run_id)
                _schedule_burp_active_scan(run_id, saved, session_vault)
                from aespa.services import validator as _validator_svc
                asyncio.create_task(
                    _validator_svc.validate_finding_inline(
                        run_id,
                        saved.id,
                        llm_cfg=llm_cfg,
                        cred_sessions=get_active_sessions(run_id) or {},
                        scanner_policy=scanner_policy,
                    )
                )
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": "reporting",
                "role": "Reporting",
                "status": "idle",
                "current_task": f"Wrote: {_fw_title}",
                "outcome": (
                    f"Saved [{tool_input.get('severity', '?')}] {_fw_title} (ID: {saved.id})"
                    if saved is not None else
                    f"Duplicate skipped: {_fw_title}"
                ),
                "_persist": True,
            })
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "complete",
                "message": (
                    f"Step {step}: "
                    f"{'recorded finding' if saved is not None else 'skipped duplicate finding'} "
                    f"{_fw_title}"
                ),
                "data": {
                    "step": step,
                    "affected_url": affected,
                    "finding_id": saved.id if saved is not None else None,
                    "note": note,
                },
            })
            if saved is not None:
                return (
                    f"Finding recorded: \"{tool_input.get('title')}\" "
                    f"(severity: {tool_input.get('severity')}, "
                    f"OWASP: {tool_input.get('owasp_category')}, ID: {saved.id})"
                )
            return (
                f"Duplicate skipped: \"{tool_input.get('title')}\" already exists. "
                "Do NOT write it again. Move to a different attack surface."
            )

        # ── browser ───────────────────────────────────────────────────────────
        if tool_name == "browser":
            br_url = (tool_input.get("url") or base_url).strip()
            _scope_err = check_scope(br_url, site_id, run_id)
            if _scope_err:
                return f"[SCOPE BLOCK] {_scope_err}"
            steps_list = tool_input.get("steps") or []
            use_session_label = (
                tool_input.get("use_session")
                if isinstance(tool_input.get("use_session"), str) else None
            )
            selected_session = session_vault.get(use_session_label) if use_session_label else None
            payload_summary = _thinking_browser_payload_summary(steps_list)
            action_message = _thinking_action_log_message(step, "BROWSER", br_url, tool_input)
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "running",
                "message": action_message,
                "data": {
                    "step": step, "method": "BROWSER", "url": br_url, "note": note,
                    "observation": tool_input.get("observation"),
                    "hypothesis": tool_input.get("hypothesis"),
                    "payload_purpose": tool_input.get("payload_purpose"),
                    "payload_summary": payload_summary,
                    "use_session": use_session_label,
                },
            })
            try:
                if selected_session and selected_session.get("cookies"):
                    cookie_list = [
                        {"name": k, "value": v, "url": br_url}
                        for k, v in selected_session["cookies"].items()
                    ]
                    if cookie_list:
                        await browser_ctx.add_cookies(cookie_list)
                await browser_ctx.set_extra_http_headers(
                    _playwright_global_headers(
                        (selected_session.get("extra_headers") or {}) if selected_session else {}
                    )
                )
            except Exception:
                pass
            br_result = await _run_thinking_browser_action(
                pw_page, tool_input, default_url=base_url, scanner_policy=scanner_policy,
            )
            resp_body = str(br_result.get("body") or "")[:BODY_READ_LIMIT]
            resp_status = br_result.get("status") or 0
            resp_headers = br_result.get("headers") or {}
            final_url = br_result.get("url") or br_url
            try:
                register_scope_host_for_run(run_id, final_url)
            except Exception:
                pass
            action_log = br_result.get("action_log") or []
            request_evidence = _request_evidence(
                f"BROWSER {final_url}\nSteps: {json.dumps(steps_list)[:800]}"
            )
            response_evidence = _response_evidence(
                f"Status: {resp_status}\nURL: {final_url}\n"
                + "\n".join(action_log)
                + f"\n\n{resp_body}"
            )
            br_result_dict = {
                "desc": note, "url": final_url, "status": resp_status,
                "headers": resp_headers, "body": resp_body,
                "request_evidence": request_evidence,
                "response_evidence": response_evidence,
                "action_outcome": "Browser interaction completed.",
            }
            history.append({
                "step": step, "note": note, "method": "BROWSER", "url": final_url,
                "request_headers": {}, "request_body": {"steps": steps_list},
                "response_status": resp_status, "response_headers": resp_headers,
                "response_body": resp_body,
            })
            all_results.append(br_result_dict)
            _mark_session_used(use_session_label, resp_status)
            # Evict expired/invalid named sessions from the vault on 401/403
            _br_session_evicted = False
            if resp_status in (401, 403) and use_session_label and use_session_label in session_vault:
                del session_vault[use_session_label]
                _br_session_evicted = True
                log.info(
                    "Agentic scan: evicted expired session '%s' (401/403 on BROWSER %s)",
                    use_session_label, final_url,
                )
            # Track primary-session 401/403 streak for re-auth trigger
            if resp_status in (401, 403) and not use_session_label:
                _consecutive_auth_failures[0] += 1
                if _consecutive_auth_failures[0] >= _REAUTH_THRESHOLD:
                    await _try_reauth()
            elif not use_session_label:
                _consecutive_auth_failures[0] = 0
            task_graph_svc.complete_task_after_result(
                run_id, active_task_id,
                step=step, method="BROWSER", url=final_url, status=resp_status,
                note=note, response_excerpt=resp_body[:2000],
            )
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "complete",
                "message": f"Step {step}: BROWSER {final_url} \u2192 {resp_status}",
                "data": {"step": step, "status": resp_status, "note": note},
            })
            await sleep_between_probes(scanner_policy)
            action_log_text = "\n".join(action_log) if action_log else "(none)"
            _br_eviction_note = (
                f"[SESSION EVICTED] Session label '{use_session_label}' returned "
                f"{resp_status} and has been removed from the session vault. "
                "Do not use this label again.\n\n"
            ) if _br_session_evicted else ""
            return (
                _br_eviction_note
                + f"Browser: {final_url}\nStatus: {resp_status}\n"
                f"Action log:\n{action_log_text}\nPage content:\n{resp_body}"
            )

        # ── decode_jwt ────────────────────────────────────────────────────────
        if tool_name == "decode_jwt":
            raw_token = str(tool_input.get("token") or "").strip()
            decode_secret = tool_input.get("secret") or None
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "running",
                "message": _thinking_action_log_message(
                    step, "JWT_DECODE", "jwt://decode", tool_input
                ),
                "data": {"step": step, "method": "JWT_DECODE", "note": note},
            })
            if not raw_token:
                return "decode_jwt: missing token"
            decoded = _decode_jwt(raw_token, secret=decode_secret)
            history.append({
                "step": step, "note": note, "method": "JWT_DECODE",
                "url": "jwt://decode",
                "request_headers": {}, "request_body": {"verify": decode_secret is not None},
                "response_status": 200, "response_headers": {},
                "response_body": json.dumps(decoded)[:2000],
            })
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "complete",
                "message": f"Step {step}: JWT decoded",
                "data": {"step": step, "note": note},
            })
            return json.dumps(decoded)

        # ── forge_jwt ─────────────────────────────────────────────────────────
        if tool_name == "forge_jwt":
            jwt_secret = str(tool_input.get("secret") or "")
            jwt_claims = (
                tool_input.get("claims")
                if isinstance(tool_input.get("claims"), dict) else {}
            )
            jwt_header = (
                tool_input.get("header")
                if isinstance(tool_input.get("header"), dict) else None
            )
            jwt_store_as = tool_input.get("store_as")
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "running",
                "message": _thinking_action_log_message(
                    step, "JWT", f"jwt://forge/{jwt_store_as or 'token'}", tool_input
                ),
                "data": {"step": step, "method": "JWT", "note": note},
            })
            try:
                jwt_token = _sign_hs256_jwt(jwt_secret, jwt_claims, jwt_header)
                jwt_label = jwt_store_as or _session_label("forged_jwt", session_vault)
                session_vault[jwt_label] = {
                    "label": jwt_label,
                    "kind": "bearer",
                    "username": (
                        f"sub:{jwt_claims.get('sub')}"
                        if jwt_claims.get("sub") is not None else None
                    ),
                    "source": "forge_jwt tool",
                    "extra_headers": {"Authorization": f"Bearer {jwt_token}"},
                    "cookies": {},
                }
                _record_session(
                    run_id, label=jwt_label,
                    session_data=session_vault[jwt_label],
                    source="dynamic_scan_jwt_action",
                    metadata={
                        "claims": jwt_claims,
                        "header": jwt_header or {"typ": "JWT", "alg": "HS256"},
                    },
                )
                jwt_resp_body = json.dumps({"store_as": jwt_label, "claims": jwt_claims})
                jwt_resp_status = 200
                _mark_session_pending(jwt_label)
            except Exception as exc:
                jwt_resp_body = f"JWT signing failed: {exc}"
                jwt_resp_status = 0
                jwt_label = None
            history.append({
                "step": step, "note": note, "method": "JWT",
                "url": f"jwt://forge/{jwt_store_as or 'token'}",
                "request_headers": {}, "request_body": {"claims": jwt_claims},
                "response_status": jwt_resp_status, "response_headers": {},
                "response_body": jwt_resp_body,
            })
            task_graph_svc.complete_task_after_result(
                run_id, active_task_id,
                step=step, method="JWT",
                url=f"jwt://forge/{jwt_label or 'token'}",
                status=jwt_resp_status, note=note,
                response_excerpt=jwt_resp_body[:500],
            )
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "complete",
                "message": (
                    f"Step {step}: JWT forge "
                    f"{'succeeded' if jwt_label else 'failed'}"
                ),
                "data": {"step": step, "note": note},
            })
            if jwt_label:
                return (
                    f"JWT forged and stored as session label \"{jwt_label}\".\n"
                    f"Use use_session=\"{jwt_label}\" in subsequent http_request calls.\n"
                    f"Claims: {json.dumps(jwt_claims)}"
                )
            return jwt_resp_body

        # ── credential_check ──────────────────────────────────────────────────
        if tool_name == "credential_check":
            cc_url = str(tool_input.get("url") or "").strip()
            cc_candidates = tool_input.get("candidates")
            if not isinstance(cc_candidates, list):
                cc_candidates = []
            cc_candidates = [c for c in cc_candidates if isinstance(c, dict)][:20]
            cc_ufield = str(tool_input.get("username_field") or "username")
            cc_pfield = str(tool_input.get("password_field") or "password")
            try:
                cc_ok_statuses = {int(s) for s in (tool_input.get("success_statuses") or [200, 201])}
            except Exception:
                cc_ok_statuses = {200, 201}
            cc_extra_hdrs = tool_input.get("headers") or {}
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "running",
                "message": _thinking_action_log_message(
                    step, "CREDENTIAL_CHECK", cc_url, tool_input
                ),
                "data": {
                    "step": step, "method": "CREDENTIAL_CHECK", "url": cc_url,
                    "note": note,
                    "payload_summary": f"{len(cc_candidates)} candidate(s)",
                },
            })
            cc_attempts: list[dict] = []
            cc_resp_status = 0
            cc_resp_headers: dict = {}
            for candidate in cc_candidates:
                cc_body = {
                    cc_ufield: candidate.get("username") or candidate.get("email") or "",
                    cc_pfield: candidate.get("password") or "",
                }
                try:
                    cc_merged = dict(hx.headers)
                    cc_merged.update(cc_extra_hdrs)
                    cc_merged.setdefault("Content-Type", "application/json")
                    cc_r = await hx.request(
                        str(tool_input.get("method") or "POST").upper(),
                        cc_url, json=cc_body, headers=cc_merged,
                    )
                    cc_resp_status = cc_r.status_code
                    cc_resp_headers = dict(cc_r.headers)
                    cc_excerpt = cc_r.text[:800]
                    cc_success = cc_r.status_code in cc_ok_statuses
                    cc_token = (
                        _extract_bearer_token_from_body(cc_r.text) if cc_success else None
                    )
                    cc_created_label = None
                    if cc_token:
                        cc_uname = (
                            candidate.get("username")
                            or candidate.get("email")
                            or "discovered"
                        )
                        cc_created_label = _session_label(str(cc_uname), session_vault)
                        session_vault[cc_created_label] = {
                            "label": cc_created_label, "kind": "bearer",
                            "username": cc_uname, "source": "credential_check",
                            "extra_headers": {"Authorization": f"Bearer {cc_token}"},
                            "cookies": {},
                        }
                        _record_session(
                            run_id, label=cc_created_label,
                            session_data=session_vault[cc_created_label],
                            source="dynamic_scan_credential_check",
                            metadata={"login_url": cc_url},
                        )
                        _mark_session_pending(cc_created_label)
                    if cc_success:
                        cc_disc_user = str(
                            candidate.get("username")
                            or candidate.get("email")
                            or "discovered"
                        )
                        cc_disc_pass = str(candidate.get("password") or "")
                        if persist_credential_fn is not None:
                            # API mode: route to the collection-aware persister.
                            # run_id is an ApiTestRun id here, so the TestRun-based
                            # site persister must not be used.
                            try:
                                persist_credential_fn(
                                    username=cc_disc_user,
                                    password=cc_disc_pass,
                                    login_url=cc_url or None,
                                )
                            except Exception as _pc_exc:
                                log.warning("persist_credential_fn error: %s", _pc_exc)
                        else:
                            _maybe_persist_discovered_credential(
                                run_id,
                                username=cc_disc_user,
                                password=cc_disc_pass,
                                login_url=cc_url or None,
                            )
                except Exception as exc:
                    cc_excerpt = f"Request failed: {exc}"
                    cc_success = False
                    cc_created_label = None
                cc_attempts.append({
                    **_redact_candidate(candidate),
                    "status": cc_resp_status, "success": cc_success,
                    "session_label": cc_created_label,
                    "response_excerpt": (
                        _redact_sensitive_text(cc_excerpt[:300]) if cc_success else ""
                    ),
                })
                await sleep_between_probes(scanner_policy)
            cc_successes = [a for a in cc_attempts if a["success"]]
            cc_resp_body = json.dumps(
                {"attempts": cc_attempts, "successes": cc_successes}
            )
            history.append({
                "step": step, "note": note, "method": "CREDENTIAL_CHECK",
                "url": cc_url, "request_headers": {}, "request_body": cc_candidates,
                "response_status": 200 if cc_successes else cc_resp_status,
                "response_headers": cc_resp_headers, "response_body": cc_resp_body,
            })
            all_results.append({
                "desc": note, "url": cc_url,
                "status": 200 if cc_successes else cc_resp_status,
                "headers": cc_resp_headers, "body": cc_resp_body,
                "request_evidence": f"CREDENTIAL_CHECK {cc_url}",
                "response_evidence": cc_resp_body,
            })
            task_graph_svc.complete_task_after_result(
                run_id, active_task_id,
                step=step, method="CREDENTIAL_CHECK", url=cc_url,
                status=200 if cc_successes else cc_resp_status,
                note=note, response_excerpt=cc_resp_body[:2000],
            )
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "complete",
                "message": (
                    f"Step {step}: credential_check {cc_url} — "
                    f"{len(cc_successes)} success(es) of {len(cc_attempts)}"
                ),
                "data": {"step": step, "note": note},
            })
            return cc_resp_body

        # ── register_account ──────────────────────────────────────────────────
        if tool_name == "register_account":
            ra_url = str(tool_input.get("url") or "").strip()
            if not ra_url:
                return "register_account: missing URL"
            ra_hdrs = (
                tool_input.get("headers")
                if isinstance(tool_input.get("headers"), dict) else {}
            )
            try:
                ra_ok_statuses = {
                    int(s) for s in (tool_input.get("success_statuses") or [200, 201, 204])
                }
            except Exception:
                ra_ok_statuses = {200, 201, 204}
            ra_account = _disposable_account_fields(tool_input, base_url=base_url)
            ra_body = ra_account["body"]
            ra_redacted = _redacted_account_body(ra_body, ra_account["password_field"])
            ra_store_as = str(
                tool_input.get("store_as") or f"disposable_{ra_account['username']}"
            )
            ra_fmt = str(tool_input.get("body_format") or "json").lower()
            ra_use_session = (
                tool_input.get("use_session")
                if isinstance(tool_input.get("use_session"), str) else None
            )
            ra_sel_session = session_vault.get(ra_use_session) if ra_use_session else None
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "running",
                "message": _thinking_action_log_message(
                    step, "REGISTER_ACCOUNT", ra_url, tool_input
                ),
                "data": {
                    "step": step, "method": "REGISTER_ACCOUNT", "url": ra_url,
                    "note": note,
                    "payload_summary": (
                        f"register {ra_account['username']} / {ra_account['email']}"
                    ),
                },
            })
            ra_resp_status = 0
            ra_resp_hdrs: dict = {}
            ra_resp_body = ""
            ra_created_label = None
            try:
                ra_merged = dict(hx.headers)
                if ra_sel_session and ra_sel_session.get("extra_headers"):
                    ra_merged.update(ra_sel_session["extra_headers"])
                ra_merged.update(ra_hdrs)
                ra_sel_cookies = (
                    ra_sel_session.get("cookies")
                    if ra_sel_session and ra_sel_session.get("cookies") else None
                )
                if ra_fmt == "form":
                    ra_merged.setdefault(
                        "Content-Type", "application/x-www-form-urlencoded"
                    )
                    ra_r = await hx.request(
                        str(tool_input.get("method") or "POST").upper(),
                        ra_url, data=ra_body, headers=ra_merged, cookies=ra_sel_cookies,
                    )
                else:
                    ra_merged.setdefault("Content-Type", "application/json")
                    ra_r = await hx.request(
                        str(tool_input.get("method") or "POST").upper(),
                        ra_url, json=ra_body, headers=ra_merged, cookies=ra_sel_cookies,
                    )
                ra_resp_status = ra_r.status_code
                ra_resp_hdrs = dict(ra_r.headers)
                ra_raw = ra_r.text[:BODY_READ_LIMIT]
                ra_resp_body = _redact_sensitive_text(ra_raw)
                ra_ok = ra_r.status_code in ra_ok_statuses
                ra_token = _extract_bearer_token_from_body(ra_raw) if ra_ok else None
                ra_resp_cookies = {k: v for k, v in ra_r.cookies.items()} if ra_ok else {}
                ra_extra_hdrs = {"Authorization": f"Bearer {ra_token}"} if ra_token else {}
                if ra_ok:
                    ra_created_label = _session_label(ra_store_as, session_vault)
                    session_vault[ra_created_label] = {
                        "label": ra_created_label,
                        "kind": _session_kind(ra_resp_cookies, ra_extra_hdrs),
                        "username": ra_account["username"],
                        "source": "register_account",
                        "extra_headers": ra_extra_hdrs,
                        "cookies": ra_resp_cookies,
                        "metadata": ra_account["metadata"],
                    }
                    _record_session(
                        run_id, label=ra_created_label,
                        session_data=session_vault[ra_created_label],
                        source="dynamic_scan_register_account",
                        metadata={**ra_account["metadata"], "status": ra_r.status_code},
                    )
                    if ra_extra_hdrs or ra_resp_cookies:
                        _mark_session_pending(ra_created_label)
            except Exception as exc:
                log.warning(
                    "Agentic loop register_account error (%s): %s", ra_url, exc
                )
                ra_resp_body = f"Registration failed: {exc}"
            history.append({
                "step": step, "note": note, "method": "REGISTER_ACCOUNT",
                "url": ra_url, "request_headers": {}, "request_body": ra_redacted,
                "response_status": ra_resp_status,
                "response_headers": ra_resp_hdrs,
                "response_body": ra_resp_body,
            })
            all_results.append({
                "desc": note, "url": ra_url, "status": ra_resp_status,
                "headers": ra_resp_hdrs, "body": ra_resp_body,
                "request_evidence": f"REGISTER_ACCOUNT {ra_url}",
                "response_evidence": f"Status: {ra_resp_status}\n{ra_resp_body}",
            })
            task_graph_svc.complete_task_after_result(
                run_id, active_task_id,
                step=step, method="REGISTER_ACCOUNT", url=ra_url,
                status=ra_resp_status, note=note,
                response_excerpt=ra_resp_body[:500],
            )
            events_svc.emit(run_id, {
                "type": "scanner_phase",
                "phase": "thinking_step",
                "status": "complete",
                "message": (
                    f"Step {step}: REGISTER_ACCOUNT {ra_url} \u2192 {ra_resp_status}"
                    + (
                        f" (session: {ra_created_label})"
                        if ra_created_label else " (no session captured)"
                    )
                ),
                "data": {"step": step, "note": note},
            })
            if ra_created_label:
                return (
                    f"Registration succeeded. Session stored as \"{ra_created_label}\".\n"
                    f"Status: {ra_resp_status}\nBody: {ra_resp_body[:500]}"
                )
            return (
                f"Registration attempted. Status: {ra_resp_status}\n"
                f"Body: {ra_resp_body[:500]}"
            )

        # ── agent_dispatch ────────────────────────────────────────────────────
        if tool_name == "agent_dispatch":
            dispatched_id = _schedule_specialist_agent(
                run_id=run_id,
                dispatch=tool_input,
                session_vault=session_vault,
                llm_cfg=llm_cfg,
                base_url=base_url,
                scanner_policy=scanner_policy,
                specialist_config=specialist_config,
                recon_summary=recon_summary,
                site_id=site_id,
            )
            task_graph_svc.complete_task_after_result(
                run_id, active_task_id,
                step=step, method="AGENT_DISPATCH",
                url=str(tool_input.get("target_url") or base_url),
                status=200 if dispatched_id else 0,
                note=note,
                response_excerpt=dispatched_id or "dropped",
            )
            if dispatched_id:
                events_svc.emit(run_id, {
                    "type": "agent_status",
                    "agent_id": dispatched_id,
                    "role": "Specialist",
                    "status": "queued",
                    "current_task": f"Queued: {tool_input.get('attack_class')} on {tool_input.get('target_url')}",
                    "outcome": None,
                    "_persist": True,
                })
                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "thinking_step",
                    "status": "complete",
                    "message": (
                        f"Step {step}: dispatched specialist {dispatched_id} "
                        f"({tool_input.get('attack_class')} → "
                        f"{tool_input.get('target_url')})"
                    ),
                    "data": {"step": step, "note": note, "agent_id": dispatched_id},
                })
                history.append({
                    "step": step, "note": note, "method": "AGENT_DISPATCH",
                    "url": str(tool_input.get("target_url") or base_url),
                    "request_headers": {}, "request_body": tool_input,
                    "response_status": 200, "response_headers": {},
                    "response_body": f"Specialist {dispatched_id} dispatched.",
                })
                return (
                    f"Specialist agent dispatched: {dispatched_id}\n"
                    f"Class: {tool_input.get('attack_class')}\n"
                    f"Target: {tool_input.get('target_url')}\n"
                    f"Rationale: {tool_input.get('rationale')}"
                )
            else:
                drop_reason = (
                    "capacity reached"
                    if specialist_config and _specialist_at_capacity(run_id, specialist_config)
                    else "class disabled or priority too low"
                )
                events_svc.emit(run_id, {
                    "type": "scanner_phase",
                    "phase": "thinking_step",
                    "status": "complete",
                    "message": (
                        f"Step {step}: specialist dispatch dropped "
                        f"({tool_input.get('attack_class')}: {drop_reason})"
                    ),
                    "data": {"step": step, "note": note},
                })
                history.append({
                    "step": step, "note": note, "method": "AGENT_DISPATCH",
                    "url": str(tool_input.get("target_url") or base_url),
                    "request_headers": {}, "request_body": tool_input,
                    "response_status": 0, "response_headers": {},
                    "response_body": f"Specialist dispatch dropped: {drop_reason}.",
                })
                return (
                    f"Specialist dispatch dropped ({drop_reason}). "
                    "Continue investigating directly."
                )

        # ── http_request (default) ────────────────────────────────────────────
        hr_method = str(tool_input.get("method") or "GET").upper()
        hr_url = str(tool_input.get("url") or "").strip()
        if not hr_url:
            return "http_request: missing URL"
        _scope_err = check_scope(hr_url, site_id, run_id)
        if _scope_err:
            return f"[SCOPE BLOCK] {_scope_err}"
        hr_headers = tool_input.get("headers") or {}
        hr_body = tool_input.get("body")
        hr_use_session = (
            tool_input.get("use_session")
            if isinstance(tool_input.get("use_session"), str) else None
        )
        hr_sel_session = session_vault.get(hr_use_session) if hr_use_session else None
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "thinking_step",
            "status": "running",
            "message": _thinking_action_log_message(
                step, hr_method, hr_url, tool_input
            ),
            "data": {
                "step": step, "method": hr_method, "url": hr_url, "note": note,
                "observation": tool_input.get("observation"),
                "hypothesis": tool_input.get("hypothesis"),
                "payload_purpose": tool_input.get("payload_purpose"),
                "payload_summary": _thinking_payload_summary(hr_url, hr_body),
                "use_session": hr_use_session,
            },
        })
        _schedule_burp_active_scan_for_investigation(
            run_id, tool_input, note, session_vault
        )
        hr_resp_status = 0
        hr_resp_headers: dict = {}
        hr_resp_body = ""
        hr_req_body_str = ""
        hr_duration_ms: Optional[int] = None
        _js_paths: list[str] = []
        try:
            hr_merged = dict(hx.headers)
            if hr_sel_session and hr_sel_session.get("extra_headers"):
                hr_merged.update(hr_sel_session["extra_headers"])
            hr_merged.update(hr_headers)
            hr_sel_cookies = (
                hr_sel_session.get("cookies")
                if hr_sel_session and hr_sel_session.get("cookies") else None
            )
            hr_started = time.perf_counter()
            if isinstance(hr_body, dict):
                hr_merged.setdefault("Content-Type", "application/json")
                hr_r = await hx.request(
                    hr_method, hr_url, json=hr_body,
                    headers=hr_merged, cookies=hr_sel_cookies,
                )
                hr_req_body_str = json.dumps(hr_body)[:800]
            elif isinstance(hr_body, str) and hr_body:
                hr_r = await hx.request(
                    hr_method, hr_url, content=hr_body,
                    headers=hr_merged, cookies=hr_sel_cookies,
                )
                hr_req_body_str = hr_body[:800]
            else:
                hr_r = await hx.request(
                    hr_method, hr_url,
                    headers=hr_merged, cookies=hr_sel_cookies,
                )
            hr_duration_ms = int((time.perf_counter() - hr_started) * 1000)
            hr_raw = hr_r.text[:BODY_READ_LIMIT]
            hr_token = _extract_bearer_token_from_body(hr_raw)
            if hr_token and hr_r.status_code < 400:
                hr_lbl = _session_label(
                    str(tool_input.get("store_as") or "http_token"), session_vault
                )
                session_vault[hr_lbl] = {
                    "label": hr_lbl, "kind": "bearer", "username": None,
                    "source": f"{hr_method} {hr_url}",
                    "extra_headers": {"Authorization": f"Bearer {hr_token}"},
                    "cookies": {},
                }
                _record_session(
                    run_id, label=hr_lbl, session_data=session_vault[hr_lbl],
                    source="dynamic_scan_http_response",
                    metadata={"method": hr_method, "url": hr_url},
                )
                _mark_session_pending(hr_lbl)
            hr_resp_body = _redact_sensitive_text(hr_raw)
            hr_resp_status = hr_r.status_code
            hr_resp_headers = dict(hr_r.headers)
            # JS path extraction
            _ct_r = hr_resp_headers.get("content-type", "").lower()
            _is_js_r = (
                "javascript" in _ct_r
                or hr_url.split("?")[0].lower().endswith(".js")
            )
            if _is_js_r and hr_resp_status == 200:
                _raw_paths_r = re.findall(
                    r'["\']((?:/api)?/[a-zA-Z0-9_-][a-zA-Z0-9_/{}.-]*)["\']',
                    hr_raw,
                )
                _js_paths = list(dict.fromkeys(
                    p for p in _raw_paths_r
                    if len(p) >= 4
                    and not p.endswith((".js", ".css", ".html", ".png", ".ico"))
                    and not p.startswith("//")
                ))[:40]
                if _js_paths:
                    try:
                        from aespa.services.crawler import _save_intel_item as _si
                        for _p in _js_paths:
                            _si(
                                run_id=run_id, kind="endpoint", key=_p, value=_p,
                                url=hr_url, method="GET", source="js_mining_dynamic",
                                confidence=0.8,
                                evidence=f"Extracted from {hr_url} at step {step}",
                            )
                    except Exception:
                        pass
        except Exception as exc:
            log.warning(
                "Agentic loop HTTP error (%s %s): %s", hr_method, hr_url, exc
            )
            hr_resp_body = f"Request failed: {exc}"

        hr_req_ev = _request_evidence(
            f"{hr_method} {hr_url}\n"
            f"{json.dumps(hr_headers, sort_keys=True)}\n{hr_req_body_str}"
        )
        hr_resp_ev = _response_evidence(
            f"Status: {hr_resp_status}\n"
            + "\n".join(f"{k}: {v}" for k, v in hr_resp_headers.items())
            + f"\n\n{hr_resp_body}"
        )
        hr_result = {
            "desc": note, "url": hr_url, "status": hr_resp_status,
            "duration_ms": hr_duration_ms, "headers": hr_resp_headers,
            "body": hr_resp_body,
            "request_evidence": hr_req_ev,
            "response_evidence": hr_resp_ev,
            "action_outcome": (
                "HTTP request completed." if hr_resp_status else "HTTP request failed."
            ),
            "evidence_json": _http_evidence_items_json(
                hr_req_ev, hr_resp_ev,
                summary=note, status=hr_resp_status, duration_ms=hr_duration_ms,
                action_outcome=(
                    "HTTP request completed."
                    if hr_resp_status else "HTTP request failed."
                ),
                confidence="observed",
            ),
        }
        log.info(
            "Agentic scan step %d: %s %s \u2192 %s",
            step, hr_method, hr_url, hr_resp_status,
        )
        _resp_body_for_history = hr_resp_body
        if _js_paths:
            _resp_body_for_history = (
                f"[{len(_js_paths)} API path(s) auto-extracted from JS: "
                f"{', '.join(_js_paths[:15])}]\n\n"
                + hr_resp_body
            )
        history.append({
            "step": step, "note": note,
            "method": hr_method, "url": hr_url,
            "request_headers": hr_headers, "request_body": hr_body,
            "response_status": hr_resp_status,
            "response_headers": hr_resp_headers,
            "response_body": _resp_body_for_history,
        })
        all_results.append(hr_result)
        _mark_session_used(hr_use_session, hr_resp_status)
        # Notify coverage tracker with the declared OWASP category (API runs only).
        if post_probe_fn is not None:
            _hr_owasp = str(tool_input.get("owasp_category") or "").strip()
            if _hr_owasp:
                try:
                    post_probe_fn(hr_url, hr_method, _hr_owasp)
                except Exception as _pp_exc:
                    log.debug("post_probe_fn error: %s", _pp_exc)
        # Evict expired/invalid named sessions from the vault on 401/403
        _hr_session_evicted = False
        if hr_resp_status in (401, 403) and hr_use_session and hr_use_session in session_vault:
            del session_vault[hr_use_session]
            _hr_session_evicted = True
            log.info(
                "Agentic scan: evicted expired session '%s' (401/403 on %s %s)",
                hr_use_session, hr_method, hr_url,
            )
        # Track primary-session 401/403 streak for re-auth trigger
        if hr_resp_status in (401, 403) and not hr_use_session:
            _consecutive_auth_failures[0] += 1
            if _consecutive_auth_failures[0] >= _REAUTH_THRESHOLD:
                await _try_reauth()
        elif not hr_use_session:
            _consecutive_auth_failures[0] = 0
        task_graph_svc.complete_task_after_result(
            run_id, active_task_id,
            step=step, method=hr_method, url=hr_url, status=hr_resp_status,
            note=note, response_excerpt=hr_resp_body[:2000],
        )
        events_svc.emit(run_id, {
            "type": "scanner_phase",
            "phase": "thinking_step",
            "status": "complete",
            "message": f"Step {step}: {hr_method} {hr_url} \u2192 {hr_resp_status}",
            "data": {"step": step, "status": hr_resp_status, "note": note},
        })
        await sleep_between_probes(scanner_policy)
        # Build the result string that goes back into the conversation
        key_hdrs = {
            k: v for k, v in hr_resp_headers.items()
            if k.lower() in (
                "content-type", "content-length", "location",
                "set-cookie", "www-authenticate", "x-powered-by",
                "server", "access-control-allow-origin",
            )
        }
        _canary_fp = _ssrf_canary.get(run_id)
        _canary_alert = (
            f"[SSRF CANARY MATCH] Response contains '{_canary_fp}' from "
            f"{_SSRF_CANARY_URL} — the server fetched and reflected the canary URL. "
            "This is confirmed reflected SSRF. Write a finding immediately.\n\n"
        ) if _canary_fp and _canary_fp in hr_resp_body else ""
        _eviction_note = (
            f"[SESSION EVICTED] Session label '{hr_use_session}' returned "
            f"{hr_resp_status} and has been removed from the session vault. "
            "Do not use this label again.\n\n"
        ) if _hr_session_evicted else ""
        return (
            _canary_alert
            + _eviction_note
            + f"Method: {hr_method}\nURL: {hr_url}\nStatus: {hr_resp_status}\n"
            + (f"Duration: {hr_duration_ms}ms\n" if hr_duration_ms else "")
            + (
                "Key headers:\n"
                + "\n".join(f"  {k}: {v}" for k, v in key_hdrs.items())
                + "\n"
                if key_hdrs else ""
            )
            + f"Body:\n{hr_resp_body}"
        )

    # ── Run the loop ──────────────────────────────────────────────────────────
    async def _on_checkpoint_callback(messages: list[dict]) -> None:
        """Persist the full loop state after each completed LLM turn."""
        checkpoint_svc.save_checkpoint(
            run_id,
            messages=messages,
            history=history,
            blocked_urls=_blocked,
            failed_url_counts=_failed,
            step_count=len(messages),
            progressive_findings_count=progressive_findings_count,
            consecutive_context_tools=_consecutive_ctx_tools[0],
        )

    await llm_svc.thinking_agentic_loop(
        llm_cfg,
        system_message=system_message_override if system_message_override is not None else _THINKING_AGENT_SYSTEM,
        initial_user_message=initial_message,
        tool_executor=_tool_executor,
        emit_fn=lambda evt: events_svc.emit(run_id, evt),
        stop_check=lambda: run_id in _thinking_stop_requested,
        done_check=_agentic_done_check,
        resume_messages=resume_messages,
        on_checkpoint=_on_checkpoint_callback,
    )
    return progressive_findings_count

async def _run_deterministic_site_modules(
    *,
    run_id: int,
    base_url: str,
    cred_sessions: dict[int, dict],
    scanner_policy=None,
) -> None:
    """Run deterministic site-level modules that do not require LLM reasoning."""
    if scanner_policy and scanner_policy.scan_mode == "passive":
        return

    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "deterministic_modules",
        "status": "start",
        "message": "Running deterministic auth and IDOR modules…",
    })
    findings: list[ScanFinding] = []
    findings.extend(await _run_auth_matrix_module(
        run_id=run_id,
        base_url=base_url,
        cred_sessions=cred_sessions,
        scanner_policy=scanner_policy,
    ))
    findings.extend(await _run_idor_matrix_module(
        run_id=run_id,
        cred_sessions=cred_sessions,
        scanner_policy=scanner_policy,
    ))
    saved = _save_deterministic_findings(run_id, findings)
    if saved:
        _emit_scan_update(run_id)
    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "deterministic_modules",
        "status": "complete",
        "message": f"Deterministic modules complete — {saved} finding(s) recorded.",
        "data": {"finding_count": saved},
    })


async def _run_auth_matrix_module(
    *,
    run_id: int,
    base_url: str,
    cred_sessions: dict[int, dict],
    scanner_policy=None,
) -> list[ScanFinding]:
    """Check high-value endpoints anonymously and across available sessions."""
    targets = _auth_matrix_targets(run_id, base_url)
    if not targets:
        return []
    timeout = scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT
    follow_redirects = scanner_policy.follow_redirects if scanner_policy else True
    findings: list[ScanFinding] = []

    for target in targets[:80]:
        if run_id in _thinking_stop_requested:
            break
        url = target["url"]
        method = target.get("method") or "GET"
        if method not in {"GET", "HEAD", "OPTIONS"}:
            method = "GET"
        if not _same_origin_or_relative(base_url, url):
            continue

        anon_result = await _fetch_matrix_url(
            run_id,
            url,
            method=method,
            timeout=timeout,
            follow_redirects=follow_redirects,
        )
        if not anon_result:
            continue
        if _is_successful_access(anon_result) and _target_requires_auth_or_sensitive(target):
            findings.append(_auth_matrix_finding(
                run_id=run_id,
                target=target,
                result=anon_result,
                title="Unauthenticated access to protected endpoint",
                description=(
                     "The deterministic auth matrix requested a protected or sensitive-looking "
                     "endpoint without cookies or Authorization and received a successful response."
                ),
                actor="anonymous",
                cvss_score=6.5,
            ))

        if not cred_sessions or "/admin" not in url.lower():
            await sleep_between_probes(scanner_policy)
            continue

        for cred_id, session in cred_sessions.items():
            if cred_id in set(target.get("accessible_by") or []):
                continue
            result = await _fetch_matrix_url(
                run_id,
                url,
                method=method,
                session=session,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )
            if result and _is_successful_access(result) and not _looks_like_denial(result["body"]):
                findings.append(_auth_matrix_finding(
                    run_id=run_id,
                    target=target,
                    result=result,
                    title="Unauthorized role access to admin endpoint",
                    description=(
                        "A credential that was not observed with access to this admin-looking "
                        "endpoint received a successful direct response."
                    ),
                    actor=session.get("username") or f"credential {cred_id}",
                    cvss_score=8.1,
                ))
            await sleep_between_probes(scanner_policy)

    return findings


async def _run_idor_matrix_module(
    *,
    run_id: int,
    cred_sessions: dict[int, dict],
    scanner_policy=None,
) -> list[ScanFinding]:
    """Compare object-reference pages across users using crawled ground truth."""
    if not cred_sessions or len(cred_sessions) < 2:
        return []
    timeout = scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT
    follow_redirects = scanner_policy.follow_redirects if scanner_policy else True
    with Session(get_engine()) as s:
        pages = list(s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
            .where(CrawledPage.status == "crawled")
        ))

    findings: list[ScanFinding] = []
    id_pages = [
        page for page in pages
        if _url_has_object_reference(page.url) and json.loads(page.accessible_by or "[]")
    ]
    for page in id_pages[:80]:
        if run_id in _thinking_stop_requested:
            break
        accessible = set(json.loads(page.accessible_by or "[]"))
        unauthorized = [
            (cred_id, session)
            for cred_id, session in cred_sessions.items()
            if cred_id not in accessible
        ]
        if not unauthorized:
            continue
        for cred_id, session in unauthorized[:3]:
            result = await _fetch_matrix_url(
                run_id,
                page.url,
                method="GET",
                session=session,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )
            if not result or not _is_successful_access(result):
                continue
            if _looks_like_denial(result["body"]) or _looks_like_spa_shell(
                result["body"], result["headers"].get("content-type", "")
            ):
                continue
            if not _body_contains_original_page_evidence(result["body"], page.title or "", page.page_text or ""):
                continue
            findings.append(_idor_matrix_finding(
                run_id=run_id,
                page=page,
                result=result,
                actor=session.get("username") or f"credential {cred_id}",
            ))
            break
        await sleep_between_probes(scanner_policy)
    return findings


def _auth_matrix_targets(run_id: int, base_url: str) -> list[dict]:
    targets: dict[str, dict] = {}
    with Session(get_engine()) as s:
        pages = list(s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
        ))
        intel = list(s.exec(
            select(TargetIntelItem)
            .where(TargetIntelItem.test_run_id == run_id)
            .where(TargetIntelItem.kind.in_(["endpoint", "script"]))
        ))

    for page in pages:
        targets[page.url] = {
            "url": page.url,
            "method": "GET",
            "source": "crawled_page",
            "req_auth": page.req_auth,
            "has_object_ref": page.has_object_ref,
            "has_business_logic": page.has_business_logic,
            "accessible_by": json.loads(page.accessible_by or "[]"),
            "page_id": page.id,
        }
    for item in intel:
        raw_url = item.value or item.url or item.key
        url = _absolute_target_url(base_url, raw_url)
        if not url:
            continue
        targets.setdefault(url, {
            "url": url,
            "method": (item.method or "GET").upper(),
            "source": item.source,
            "req_auth": None,
            "has_object_ref": _url_has_object_reference(url),
            "has_business_logic": False,
            "accessible_by": [],
            "page_id": None,
            "intel_key": item.key,
        })
    return sorted(
        targets.values(),
        key=lambda t: (
            0 if _target_requires_auth_or_sensitive(t) else 1,
            t["url"],
        ),
    )


async def _fetch_matrix_url(
    run_id: int,
    url: str,
    *,
    method: str = "GET",
    session: dict | None = None,
    timeout: float = REQUEST_TIMEOUT,
    follow_redirects: bool = True,
) -> dict | None:
    headers = {"User-Agent": _UA}
    cookies = None
    actor = "anonymous"
    if session:
        headers.update(session.get("extra_headers", {}))
        cookies = session.get("cookies", {})
        actor = session.get("username") or "credential"
    try:
        async with _make_scanner_client(
            run_id=run_id,
            username=actor,
            cookies=cookies,
            headers=headers,
            follow_redirects=follow_redirects,
            verify=False,
            timeout=timeout,
        ) as client:
            resp = await client.request(method, url)
        request_evidence = (
            f"{method} {url} HTTP/1.1\n"
            f"Actor: {actor}\n"
            f"Authorization: {'present' if session and session.get('extra_headers') else 'none'}"
        )
        response_evidence = (
            f"HTTP/1.1 {resp.status_code}\n"
            + "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
            + "\n\n"
            + resp.text[:2000]
        )
        return {
            "url": str(resp.url),
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:BODY_READ_LIMIT],
            "request_evidence": request_evidence,
            "response_evidence": response_evidence,
        }
    except Exception as exc:
        log.debug("Deterministic matrix request failed for %s: %s", url, exc)
        return None


def _auth_matrix_finding(
    *,
    run_id: int,
    target: dict,
    result: dict,
    title: str,
    description: str,
    actor: str,
    cvss_score: float,
) -> ScanFinding:
    return ScanFinding(
        test_run_id=run_id,
        page_id=target.get("page_id"),
        owasp_category="A01",
        severity=_severity_from_cvss(cvss_score),
        title=title,
        description=description,
        impact=(
            "Attackers may be able to access protected application functionality or "
            "sensitive operational data without the intended authentication or role checks."
        ),
        likelihood="Confirmed by deterministic auth matrix request.",
        recommendation=(
            "Enforce server-side authentication and authorization on the endpoint. "
            "Do not rely on client-side route hiding or UI controls."
        ),
        cvss_score=cvss_score,
        cvss_vector="",
        affected_url=result.get("url") or target["url"],
        evidence=_full_evidence(
            result["request_evidence"],
            result["response_evidence"],
            f"Actor `{actor}` received HTTP {result['status']} for a protected/sensitive endpoint.",
        ),
        request_evidence=_request_evidence(result["request_evidence"]),
        response_evidence=_response_evidence(result["response_evidence"]),
        evidence_json=_http_evidence_items_json(
            result["request_evidence"],
            result["response_evidence"],
            summary=f"Actor `{actor}` received HTTP {result['status']} for a protected/sensitive endpoint.",
            status=result.get("status"),
        ),
        finding_source="deterministic_probe",
        validation_status="confirmed",
        validation_note="Confirmed by deterministic auth matrix module.",
        created_at=_utcnow(),
    )


def _idor_matrix_finding(
    *,
    run_id: int,
    page: CrawledPage,
    result: dict,
    actor: str,
) -> ScanFinding:
    return ScanFinding(
        test_run_id=run_id,
        page_id=page.id,
        owasp_category="A01",
        severity="high",
        title="Insecure direct object reference",
        description=(
            "A credential that was not observed with access to this object-reference URL "
            "could request it directly and received recognizable protected content."
        ),
        impact=(
            "A user may be able to access another user's records or tenant data by "
            "guessing or reusing object identifiers."
        ),
        likelihood="Confirmed by deterministic IDOR matrix comparison.",
        recommendation=(
            "Enforce object ownership checks on every request using server-side authorization "
            "logic. Avoid exposing predictable object identifiers where possible."
        ),
        cvss_score=8.1,
        cvss_vector="",
        affected_url=page.url,
        evidence=_full_evidence(
            result["request_evidence"],
            result["response_evidence"],
            f"Actor `{actor}` received content matching the protected object page.",
        ),
        request_evidence=_request_evidence(result["request_evidence"]),
        response_evidence=_response_evidence(result["response_evidence"]),
        evidence_json=_http_evidence_items_json(
            result["request_evidence"],
            result["response_evidence"],
            summary=f"Actor `{actor}` received content matching the protected object page.",
            status=result.get("status"),
            marker="protected object page content matched",
        ),
        finding_source="deterministic_probe",
        validation_status="confirmed",
        validation_note="Confirmed by deterministic IDOR matrix module.",
        created_at=_utcnow(),
    )


def _target_requires_auth_or_sensitive(target: dict) -> bool:
    url = str(target.get("url") or "").lower()
    if target.get("req_auth") is True:
        return True
    if target.get("has_business_logic") or target.get("has_object_ref"):
        return True
    return any(marker in url for marker in (
        "/admin", "/account", "/accounts", "/user", "/users", "/profile",
        "/transfer", "/transaction", "/invoice", "/order", "/config", "/debug",
        "/metrics", "/openapi", "/swagger",
    ))


def _is_successful_access(result: dict) -> bool:
    status = result.get("status")
    if status not in (200, 201, 202, 204, 206):
        return False
    body = result.get("body") or ""
    return not _looks_like_denial(body)


def _looks_like_denial(body: str) -> bool:
    text = (body or "")[:5000].lower()
    return any(marker in text for marker in (
        "unauthorized", "forbidden", "access denied", "permission denied",
        "not authorized", "login required", "please log in", "sign in",
        "authentication required", "invalid token",
    ))


def _url_has_object_reference(url: str) -> bool:
    parsed = urlparse(url)
    if re.search(r"/(?:[0-9]+|[0-9a-f]{8,}(?:-[0-9a-f]{4,}){2,})(?:[/?.#]|$)", parsed.path, re.I):
        return True
    qs = parse_qs(parsed.query, keep_blank_values=True)
    return any(
        re.search(r"(?:^|_)(id|uuid|account|user|order|invoice|transaction)(?:_|$)", key, re.I)
        and values
        for key, values in qs.items()
    )


def _absolute_target_url(base_url: str, raw_url: str) -> str:
    raw_url = (raw_url or "").strip()
    if not raw_url or raw_url.startswith(("javascript:", "mailto:", "#")):
        return ""
    parsed = urlparse(raw_url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return raw_url
    if raw_url.startswith("/"):
        base = urlparse(base_url)
        return urlunparse((base.scheme, base.netloc, raw_url, "", "", ""))
    return ""


def _same_origin_or_relative(base_url: str, url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc:
        return True
    base = urlparse(base_url)
    return parsed.scheme in {"http", "https"} and parsed.netloc == base.netloc


def _looks_like_spa_shell(body: str, content_type: str) -> bool:
    if "html" not in content_type.lower() and not body.lstrip().lower().startswith("<!doctype html"):
        return False
    body_lower = body[:5000].lower()
    shell_markers = sum(1 for marker in (
        '<div id="root"', "<div id='root'", '<div id="app"', "<div id='app'",
        "bundle.js", "main.js", "app.js", "vite", "webpack", "static/js",
    ) if marker in body_lower)
    text_only = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", body_lower)
    words = re.findall(r"[a-z0-9]{3,}", text_only)
    return shell_markers >= 1 and len(set(words)) < 80


def _protected_content_candidates(page_title: str, page_text: str) -> list[str]:
    generic_words = {
        "dashboard", "home", "profile", "settings", "account", "overview", "welcome",
        "logout", "sign out", "navigation", "menu", "search", "submit", "cancel",
    }
    candidates: list[str] = []
    for line in (page_text or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not 24 <= len(line) <= 220:
            continue
        lower = line.lower()
        if lower in generic_words:
            continue
        if sum(1 for word in generic_words if word in lower) >= 4:
            continue
        candidates.append(line)
        if len(candidates) >= 12:
            break
    if not candidates and page_title and len(page_title.strip()) >= 12:
        title = page_title.strip()
        if title.lower() not in generic_words:
            candidates.append(title)
    return candidates


def _body_contains_original_page_evidence(body: str, page_title: str, page_text: str) -> bool:
    body_lower = body.lower()
    candidates = _protected_content_candidates(page_title, page_text)
    return any(candidate.lower() in body_lower for candidate in candidates)


# ── Deterministic result analysis ─────────────────────────────────────────────

_SQL_ERROR_PATTERNS = (
    "sql syntax", "mysql", "postgresql", "sqlite", "ora-", "odbc",
    "unterminated quoted string", "you have an error in your sql syntax",
    "syntax error at or near", "unclosed quotation mark", "sqlstate",
)
_SENSITIVE_FIELD_PATTERNS = (
    "password_hash", "passwordhash", "passwd", "jwt_secret", "api_key",
    "apikey", "secret_key", "private_key", "totp_secret", "mfa_secret",
    "access_token", "refresh_token", "debug", "stack_trace",
)


def _deterministic_findings_from_results(
    *,
    run_id: int,
    page_id: int | None,
    page_url: str,
    results: list[dict],
) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        desc = str(result.get("desc") or "")
        url = str(result.get("url") or page_url)
        body = str(result.get("body") or "")
        status = result.get("status")
        haystack = f"{desc}\n{url}\n{body}".lower()

        def add(title: str, owasp: str, score: float, description: str, impact: str, recommendation: str) -> None:
            key = (title, url)
            if key in seen:
                return
            seen.add(key)
            findings.append(ScanFinding(
                test_run_id=run_id,
                page_id=page_id,
                owasp_category=owasp,
                severity=_severity_from_cvss(score),
                title=title,
                description=description,
                impact=impact,
                likelihood="Confirmed by deterministic response analysis.",
                recommendation=recommendation,
                cvss_score=score,
                cvss_vector="",
                affected_url=url,
                evidence=_clip_evidence(str(result.get("evidence") or _combined_evidence(
                    str(result.get("request_evidence") or ""),
                    str(result.get("response_evidence") or body),
                )), EVIDENCE_TEXT_LIMIT),
                request_evidence=_request_evidence(str(result.get("request_evidence") or "")),
                response_evidence=_response_evidence(str(result.get("response_evidence") or body)),
                evidence_json=_http_evidence_items_json(
                    str(result.get("request_evidence") or ""),
                    str(result.get("response_evidence") or body),
                    summary="Confirmed by deterministic response analysis.",
                    status=status,
                    marker=title,
                ),
                screenshot_b64=result.get("screenshot_b64"),
                finding_source="deterministic_probe",
                validation_status="confirmed",
                validation_note="Confirmed by deterministic module.",
                created_at=_utcnow(),
            ))

        if ("sqli" in desc.lower() or any(p in haystack for p in ("' or '1'='1", "union select", "order by 999"))) and (
            any(pattern in haystack for pattern in _SQL_ERROR_PATTERNS) or status == 500
        ):
            add(
                "SQL injection error disclosure",
                "A03",
                7.1,
                "An SQL injection probe produced a database error or server error indicative of unsafely handled input.",
                "Attackers may be able to extract or modify database data by crafting SQL payloads.",
                "Use parameterized queries, strict input validation, and generic error handling.",
            )

        reflected_payload = _reflected_payload_from_result(result)
        if reflected_payload and reflected_payload in body and _looks_xss_payload(reflected_payload):
            add(
                "Reflected cross-site scripting",
                "A03",
                6.1,
                "A script-capable payload was reflected in the response body without being removed or encoded.",
                "Attackers could execute JavaScript in a victim browser if they can deliver a crafted URL or form submission.",
                "Apply context-aware output encoding and reject dangerous HTML/JavaScript input where it is not expected.",
            )

        if "ssti" in desc.lower() and "49" in body and any(marker in haystack for marker in ("{{7*7}}", "${7*7}", "<%= 7*7 %>", "#{7*7}")):
            add(
                "Server-side template injection",
                "A03",
                8.0,
                "A template expression probe appears to have been evaluated by the server.",
                "Template injection can lead to data exposure or remote code execution depending on the template engine.",
                "Do not evaluate user-controlled strings as templates; sandbox template engines and validate input.",
            )

        if ("path" in desc.lower() or "../" in haystack or "%2f" in haystack) and "root:x:0:0" in body:
            add(
                "Path traversal file disclosure",
                "A05",
                7.5,
                "A traversal payload returned content consistent with a system password file.",
                "Attackers may read arbitrary files from the server filesystem.",
                "Normalize paths, enforce allow-listed file roots, and reject traversal sequences before file access.",
            )

        if ("cmdi" in desc.lower() or "aespa_probe" in haystack) and "aespa_probe" in body:
            add(
                "Command injection",
                "A03",
                9.1,
                "A command-injection marker appeared in the response after a shell metacharacter probe.",
                "Attackers may execute arbitrary commands on the application server.",
                "Avoid shell invocation with user input; use safe APIs and strict allow-list validation.",
            )

        if any(pattern in haystack for pattern in _SENSITIVE_FIELD_PATTERNS) and _looks_like_json_or_api(result):
            add(
                "Sensitive data exposed in API response",
                "A02",
                6.5,
                "The response contains field names commonly associated with secrets, hashes, tokens, debug state, or privileged metadata.",
                "Attackers can use leaked secrets or implementation details to compromise accounts or chain further attacks.",
                "Remove sensitive fields from client-facing responses and enforce response DTO allow-lists.",
            )

    return findings


def _reflected_payload_from_result(result: dict) -> str:
    desc = str(result.get("desc") or "")
    if ":" in desc:
        candidate = desc.split(":", 1)[1].strip()
        if candidate:
            return candidate[:200]
    parsed = urlparse(str(result.get("url") or ""))
    qs = parse_qs(parsed.query, keep_blank_values=True)
    for values in qs.values():
        for value in values:
            if _looks_xss_payload(value):
                return value
    payload = str(result.get("payload") or "")
    return payload if _looks_xss_payload(payload) else ""


def _looks_xss_payload(value: str) -> bool:
    lower = (value or "").lower()
    return any(marker in lower for marker in (
        "<script", "onerror=", "onload=", "ontoggle=", "javascript:alert",
        "<svg", "autofocus", "<details", "alert(",
    ))


def _looks_like_json_or_api(result: dict) -> bool:
    headers = {str(k).lower(): str(v).lower() for k, v in (result.get("headers") or {}).items()}
    content_type = headers.get("content-type", "")
    url = str(result.get("url") or "").lower()
    body = str(result.get("body") or "").lstrip()
    return "json" in content_type or "/api/" in url or body.startswith(("{", "["))


# ── Passive checks ────────────────────────────────────────────────────────────

async def _run_thinking_browser_action(
    pw_page,
    action: dict,
    default_url: str,
    scanner_policy=None,
) -> dict:
    """Execute a compact browser action chosen by the Thinking scan LLM.

    Captures all HTTP traffic made during the action via local page-level listeners
    and includes a formatted summary directly in the response body so the LLM sees
    it immediately without needing a traffic_search call.
    """
    import base64 as _b64

    url = (action.get("url") or default_url).strip()
    steps = action.get("steps") if isinstance(action.get("steps"), list) else []
    if not steps:
        steps = [{"op": "goto", "url": url}, {"op": "snapshot"}]

    timeout_ms = int((scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT) * 1000)
    last_status: Optional[int] = None
    last_headers: dict = {}
    action_log: list[str] = []
    started = time.perf_counter()

    # ── Local traffic capture ─────────────────────────────────────────────────
    # Register page-level listeners that collect traffic in-memory.  These fire
    # in addition to the context-level handler that writes to the DB, so the DB
    # record is unchanged.  Reading body() bytes here (rather than text()) is
    # the most reliable approach: body() reads the raw buffer that Playwright
    # already has, whereas text() can fail if encoding detection breaks.
    _pending_reqs: dict[int, dict] = {}
    _captured: list[dict] = []

    async def _cap_request(req) -> None:
        # Store timing and body only; full headers read in _cap_response.
        rid = id(req)
        post_data = req.post_data
        if post_data is None:
            try:
                pd_json = req.post_data_json
                if pd_json is not None:
                    post_data = json.dumps(pd_json)
            except Exception:
                pass
        _pending_reqs[rid] = {
            "method": req.method,
            "url":    req.url,
            "post_data": post_data,
            "t0":    time.monotonic(),
        }

    async def _cap_response(resp) -> None:
        if resp.request.resource_type in _BROWSER_SKIP_RESOURCE_TYPES:
            return
        rid = id(resp.request)
        req_info = _pending_reqs.pop(rid, {})
        dur = int((time.monotonic() - req_info.get("t0", time.monotonic())) * 1000)

        # Full request headers — only reliable after the request has been sent.
        try:
            req_headers = await resp.request.all_headers()
        except Exception:
            try:
                req_headers = dict(resp.request.headers)
            except Exception:
                req_headers = {}

        # Prefer body captured at request time; fall back to resp.request.
        post_data = req_info.get("post_data")
        if post_data is None:
            try:
                post_data = resp.request.post_data
                if post_data is None:
                    pd_json = resp.request.post_data_json
                    if pd_json is not None:
                        post_data = json.dumps(pd_json)
            except Exception:
                pass

        try:
            body_bytes = await resp.body()
            ct = resp.headers.get("content-type", "")
            if any(t in ct for t in ("text", "json", "xml", "html", "javascript")):
                resp_text: Optional[str] = body_bytes.decode(errors="replace")[:_BROWSER_TRAFFIC_BODY_LIMIT]
            else:
                resp_text = f"[binary, {len(body_bytes)} bytes]"
        except Exception:
            resp_text = None

        _captured.append({
            "method":          req_info.get("method", resp.request.method),
            "url":             resp.url,
            "status":          resp.status,
            "request_headers": req_headers,
            "request_body":    post_data,
            "response_body":   resp_text,
            "content_type":    resp.headers.get("content-type", ""),
            "duration_ms":     dur,
        })

    pw_page.on("request", _cap_request)
    pw_page.on("response", _cap_response)
    # ─────────────────────────────────────────────────────────────────────────

    try:
        for raw_step in steps[:20]:
            if not isinstance(raw_step, dict):
                continue
            op = str(raw_step.get("op") or "").lower().strip()
            try:
                if op == "goto":
                    step_url = (raw_step.get("url") or url or default_url).strip()
                    action_log.append(f"goto {step_url}")
                    resp = await pw_page.goto(step_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    if resp:
                        last_status = resp.status
                        try:
                            last_headers = await resp.all_headers()
                        except Exception:
                            last_headers = {}
                elif op in {"fill", "type"}:
                    selector = raw_step.get("selector")
                    value = str(raw_step.get("value") or "")
                    if not selector:
                        action_log.append(f"{op} skipped: missing selector")
                        continue
                    action_log.append(f"{op} {selector}={_compact_log_value(value, 120)}")
                    loc = pw_page.locator(selector).first
                    await loc.wait_for(state="visible", timeout=5_000)
                    if op == "fill":
                        await loc.fill(value, timeout=5_000)
                    else:
                        await loc.type(value, delay=20, timeout=5_000)
                elif op == "click":
                    selector = raw_step.get("selector")
                    if not selector:
                        action_log.append("click skipped: missing selector")
                        continue
                    action_log.append(f"click {selector}")
                    await pw_page.locator(selector).first.click(timeout=5_000)
                elif op == "press":
                    selector = raw_step.get("selector")
                    key = raw_step.get("key") or "Enter"
                    if not selector:
                        action_log.append("press skipped: missing selector")
                        continue
                    action_log.append(f"press {selector} {key}")
                    await pw_page.locator(selector).first.press(str(key), timeout=5_000)
                elif op == "wait":
                    if raw_step.get("ms") is not None:
                        ms = max(0, min(int(raw_step.get("ms") or 0), 10_000))
                        action_log.append(f"wait {ms}ms")
                        await asyncio.sleep(ms / 1000)
                    else:
                        state = str(raw_step.get("state") or "networkidle")
                        if state not in {"domcontentloaded", "load", "networkidle"}:
                            state = "networkidle"
                        action_log.append(f"wait {state}")
                        await pw_page.wait_for_load_state(state, timeout=timeout_ms)
                elif op == "snapshot":
                    action_log.append("snapshot")
                else:
                    action_log.append(f"unsupported op: {op or '(missing)'}")
            except Exception as exc:
                action_log.append(f"{op or 'step'} failed: {exc}")

        try:
            await pw_page.wait_for_load_state("networkidle", timeout=2_000)
        except Exception:
            pass

    finally:
        # Always deregister local listeners regardless of whether steps succeeded.
        try:
            pw_page.remove_listener("request", _cap_request)
            pw_page.remove_listener("response", _cap_response)
        except Exception:
            pass

    final_url = pw_page.url or url or default_url
    try:
        title = await pw_page.title()
    except Exception:
        title = ""
    try:
        visible_text = await pw_page.locator("body").inner_text(timeout=2_000)
    except Exception:
        visible_text = ""
    try:
        html = await pw_page.content()
    except Exception:
        html = ""

    screenshot_b64: Optional[str] = None
    try:
        raw_png = await pw_page.screenshot(full_page=False)
        screenshot_b64 = _b64.b64encode(raw_png).decode()
    except Exception:
        pass

    # ── Build traffic summary ─────────────────────────────────────────────────
    # Filter to API / same-origin non-asset requests and format them for the LLM.
    _api_entries = [
        t for t in _captured
        if "/api/" in t["url"]
        or (
            not any(t["url"].split("?")[0].endswith(ext) for ext in _BROWSER_SKIP_EXTENSIONS)
            and not t["url"].startswith("data:")
            and not t["url"].startswith("blob:")
        )
    ]
    _traffic_section = ""
    if _api_entries:
        _lines: list[str] = []
        for t in _api_entries[:15]:
            _lines.append(f"  {t['method']} {t['url']} → {t['status']}")
            if t.get("request_body"):
                _lines.append(f"    Request body: {t['request_body'][:400]}")
            if t.get("response_body"):
                _lines.append(f"    Response: {t['response_body'][:600]}")
        _traffic_section = (
            "[Traffic captured during browser interaction:]\n"
            + "\n".join(_lines)
            + "\n\n"
        )
    # ─────────────────────────────────────────────────────────────────────────

    body = (
        _traffic_section
        + f"Final URL: {final_url}\n"
        + f"Title: {title}\n"
        + f"Action log:\n" + "\n".join(f"- {line}" for line in action_log) + "\n\n"
        + f"Visible text excerpt:\n{visible_text[:3000]}\n\n"
        + f"HTML excerpt:\n{html[:3000]}"
    )
    request_evidence = (
        f"BROWSER ACTION\nInitial URL: {url or default_url}\n"
        f"Steps:\n{json.dumps(steps, indent=2)[:3000]}"
    )
    response_evidence = (
        f"Final URL: {final_url}\n"
        f"Title: {title}\n"
        f"Last response status: {last_status}\n\n"
        f"Action log:\n" + "\n".join(f"- {line}" for line in action_log) + "\n\n"
        + (_traffic_section if _traffic_section else "")
        + f"Visible text excerpt:\n{visible_text[:3000]}"
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    outcome = "Browser action completed."
    if any(" failed:" in line for line in action_log):
        outcome = "Browser action completed with failed steps."
    return {
        "desc": action.get("note") or "Browser action",
        "url": final_url,
        "status": last_status,
        "headers": last_headers,
        "body": body,
        "captured_traffic": _captured,
        "duration_ms": duration_ms,
        "action_log": action_log,
        "action_outcome": outcome,
        "evidence": _combined_evidence(request_evidence, response_evidence),
        "request_evidence": request_evidence,
        "response_evidence": response_evidence,
        "evidence_json": _http_evidence_items_json(
            request_evidence,
            response_evidence,
            summary=action.get("note") or "Browser action",
            status=last_status,
            duration_ms=duration_ms,
            action_outcome=outcome,
            action_log=action_log,
            screenshot_b64=screenshot_b64,
            confidence="observed",
        ),
        "screenshot_b64": screenshot_b64,
    }


async def _analyse_js_sinks(
    run_id: int,
    hx: httpx.AsyncClient,
    scanner_policy=None,
) -> list[dict]:
    """Fetch every JS file discovered during crawling and grep for unsanitized innerHTML sinks.

    For each match where no sanitizer call (escapeHtml, DOMPurify, etc.) wraps the value:
    - Saves a TargetIntelItem(kind='xss_sink') so the thinking-scan agent can find it.
    - Saves an info-severity ScanFinding so the user sees it in the findings panel
      before dynamic confirmation runs.
    - Emits scanner_phase events at start and completion.

    Returns a list of sink dicts (field, js_file, snippet) for the completion event payload.
    """
    timeout = scanner_policy.request_timeout_s if scanner_policy else REQUEST_TIMEOUT

    with Session(get_engine()) as s:
        script_items = s.exec(
            select(TargetIntelItem)
            .where(TargetIntelItem.test_run_id == run_id)
            .where(TargetIntelItem.kind == "script")
        ).all()

    if not script_items:
        return []

    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "js_sink_analysis",
        "status": "start",
        "message": f"JS sink analysis: scanning {len(script_items)} script file(s) for unsanitized innerHTML sinks…",
    })

    _SINK_RE = re.compile(
        r'(\.innerHTML\s*[+=]|\.outerHTML\s*[+=]|document\.write\s*\(|insertAdjacentHTML\s*\()',
        re.MULTILINE,
    )
    _SANITIZER_RE = re.compile(
        r'escapeHtml|DOMPurify|sanitize|htmlEncode|encodeHtml|\.escape\(',
        re.IGNORECASE,
    )
    # Extract a dotted field name from the sink context, e.g. "tx.description"
    _FIELD_RE = re.compile(r'\b(?:tx|item|entry|row|data|msg|rec|obj|comment|result)\s*\.\s*([a-zA-Z_]\w*)')

    from aespa.services.crawler import _save_intel_item as _si

    found_sinks: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for script_item in script_items:
        js_url = script_item.value or script_item.url or script_item.key
        if not js_url:
            continue
        try:
            resp = await hx.get(js_url, timeout=timeout)
            if resp.status_code != 200:
                continue
            body = resp.text
        except Exception as exc:
            log.debug("JS sink analysis: failed to fetch %s: %s", js_url, exc)
            continue

        for m in _SINK_RE.finditer(body):
            ctx_start = max(0, m.start() - 200)
            ctx_end   = min(len(body), m.end() + 200)
            context   = body[ctx_start:ctx_end]

            if _SANITIZER_RE.search(context):
                continue

            field_m    = _FIELD_RE.search(context)
            field_name = field_m.group(1) if field_m else m.group(1).strip().rstrip("(= ")

            dedup = (js_url, field_name)
            if dedup in seen:
                continue
            seen.add(dedup)

            snippet = context.replace("\n", " ").strip()[:400]
            log.info("JS sink analysis: unsanitized %s for field '%s' in %s", m.group(1).strip(), field_name, js_url)

            _si(
                run_id=run_id,
                kind="xss_sink",
                key=field_name,
                value=js_url,
                url=js_url,
                method="GET",
                source="js_sink_analysis",
                confidence=0.85,
                evidence=snippet,
                metadata={"js_file": js_url, "pattern": m.group(1).strip()},
            )
            found_sinks.append({"field": field_name, "js_file": js_url, "snippet": snippet[:200]})

    if found_sinks:
        info_findings: list[ScanFinding] = []
        for sink in found_sinks:
            info_findings.append(ScanFinding(
                test_run_id=run_id,
                owasp_category="A03",
                severity="info",
                title=f"Potential stored XSS sink identified in JS source: {sink['field']}",
                description=(
                    f"Static analysis of {sink['js_file']} found an unsanitized innerHTML "
                    f"assignment using the field '{sink['field']}'. No escapeHtml(), DOMPurify, "
                    f"or equivalent sanitizer call was found in the surrounding context.\n\n"
                    f"Code context:\n{sink['snippet']}"
                ),
                impact=(
                    "If an attacker controls the value of this field via any writable API "
                    "endpoint, the payload will execute as JavaScript in every user's browser "
                    "that renders this view."
                ),
                likelihood=(
                    "Unconfirmed — this is a static finding. Requires dynamic confirmation "
                    "that the field is writable and that the rendered output reaches this sink."
                ),
                recommendation=(
                    "Wrap all user-supplied values rendered via innerHTML with escapeHtml() or "
                    "equivalent HTML encoding. Prefer textContent over innerHTML for plain-text "
                    "values. Add a strict Content-Security-Policy as defence-in-depth."
                ),
                cvss_score=0.0,
                affected_url=sink["js_file"],
                finding_source="deterministic_probe",
                validation_status="unvalidated",
                created_at=_utcnow(),
            ))
        with Session(get_engine()) as s:
            for f in info_findings:
                s.add(f)
            s.commit()
        _emit_scan_update(run_id)

    events_svc.emit(run_id, {
        "type": "scanner_phase",
        "phase": "js_sink_analysis",
        "status": "complete",
        "message": (
            f"JS sink analysis: found {len(found_sinks)} unsanitized innerHTML sink(s)"
            if found_sinks else
            "JS sink analysis: no unsanitized innerHTML sinks found"
        ),
        "sinks": found_sinks,
    })
    return found_sinks


def _emit_scan_update(run_id: int) -> None:
    status = get_scan_status(run_id)
    events_svc.emit(run_id, {"type": "scan_update", **status})


def get_scan_status(run_id: int) -> dict:
    with Session(get_engine()) as s:
        findings_count = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all().__len__()
    return {
        "total_pages": 0,
        "pages_done": 0,
        "findings_count": findings_count,
        "status": "idle",
    }
