"""Persistent ownership and signal routing for specialist investigations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlparse, urlunparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import SpecialistHandoff

_UTC = timezone.utc
ACTIVE_STATUSES = ("queued", "running")

_CLASS_ALIASES = {
    "idor": "idor",
    "bola": "idor",
    "access_control": "idor",
    "broken_access_control": "idor",
    "auth_bypass": "auth_bypass",
    "authentication_bypass": "auth_bypass",
    "broken_auth": "auth_bypass",
    "sqli": "sqli",
    "sql": "sqli",
    "sql_injection": "sqli",
    "xss": "xss",
    "reflected_xss": "xss",
    "stored_xss": "xss",
    "persistent_xss": "xss",
    "cross_site_scripting": "xss",
    "business_logic": "business_logic",
    "business_logic_abuse": "business_logic",
    "workflow": "business_logic",
    "ssrf": "ssrf",
    "server_side_request_forgery": "ssrf",
    "path_traversal": "path_traversal",
    "directory_traversal": "path_traversal",
    "lfi": "path_traversal",
    "cors": "cors",
    "crypto": "crypto",
    "cryptographic_failures": "crypto",
    "config": "config",
    "security_misconfiguration": "config",
    "file_upload": "file_upload",
    "upload": "file_upload",
    "unrestricted_file_upload": "file_upload",
}

_SSRF_KEYS = {
    "url",
    "uri",
    "webhook",
    "callback",
    "redirect",
    "src",
    "fetch",
    "imageurl",
    "image_url",
}
_UPLOAD_KEYS = {"file", "filename", "attachment", "upload", "avatar", "document"}
_SQL_ERROR_MARKERS = (
    "sql syntax",
    "sqlite error",
    "postgresql error",
    "mysql_fetch",
    "unterminated quoted string",
    "ora-01756",
    "sqlstate[",
)


def normalize_attack_class(value: Any) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return _CLASS_ALIASES.get(key, "")


def canonical_scope_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    path = re.sub(r"//+", "/", parsed.path or "/")
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path.rstrip("/") or "/",
            "",
            "",
            "",
        )
    )


def infer_parameter(url: str, body: Any = None, explicit: Any = None) -> str | None:
    if str(explicit or "").strip():
        return str(explicit).strip().lower()
    keys = [
        key.lower() for key, _ in parse_qsl(urlparse(url).query, keep_blank_values=True)
    ]
    if isinstance(body, dict):
        keys.extend(str(key).lower() for key in body)
    elif isinstance(body, str):
        keys.extend(
            match.lower() for match in re.findall(r"(?:^|[&?])([A-Za-z0-9_.-]+)=", body)
        )
    signal_keys = [key for key in keys if key in _SSRF_KEYS or key in _UPLOAD_KEYS]
    if len(set(signal_keys)) == 1:
        return signal_keys[0]
    return None


def handoff_fingerprint(
    attack_class: str,
    target_url: str,
    *,
    parameter: str | None = None,
    session_label: str | None = None,
) -> str:
    material = "|".join(
        (
            normalize_attack_class(attack_class),
            canonical_scope_url(target_url),
            str(parameter or "").strip().lower(),
            str(session_label or "").strip().lower(),
        )
    )
    return hashlib.sha256(material.encode()).hexdigest()


def create_or_get_handoff(
    *,
    run_id: int,
    run_kind: str,
    attack_class: str,
    target_url: str,
    parameter: str | None,
    session_label: str | None,
    priority: int,
    rationale: str,
    dispatch_source: str,
    agent_id: str,
) -> tuple[SpecialistHandoff, bool]:
    normalized = normalize_attack_class(attack_class)
    fingerprint = handoff_fingerprint(
        normalized,
        target_url,
        parameter=parameter,
        session_label=session_label,
    )
    with Session(get_engine(), expire_on_commit=False) as session:
        existing = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.fingerprint == fingerprint)
        ).first()
        if existing is not None:
            return existing, False
        handoff = SpecialistHandoff(
            run_kind=run_kind,
            run_id=run_id,
            fingerprint=fingerprint,
            attack_class=normalized,
            target_url=target_url,
            canonical_url=canonical_scope_url(target_url),
            parameter=parameter,
            session_label=session_label,
            priority=priority,
            rationale=rationale,
            dispatch_source=dispatch_source,
            agent_id=agent_id,
        )
        session.add(handoff)
        session.commit()
        session.refresh(handoff)
        return handoff, True


def update_handoff(
    handoff_id: int,
    *,
    status: str | None = None,
    outcome: str | None = None,
    finding_id: int | None = None,
) -> None:
    with Session(get_engine()) as session:
        handoff = session.get(SpecialistHandoff, handoff_id)
        if handoff is None:
            return
        now = datetime.now(_UTC)
        if status:
            handoff.status = status
            if status == "running" and handoff.started_at is None:
                handoff.started_at = now
            if status in {"completed", "failed", "cancelled"}:
                handoff.completed_at = now
        if outcome is not None:
            handoff.outcome = outcome
        if finding_id is not None:
            handoff.finding_id = finding_id
        handoff.updated_at = now
        session.add(handoff)
        session.commit()


def get_handoff(handoff_id: int) -> SpecialistHandoff | None:
    with Session(get_engine(), expire_on_commit=False) as session:
        return session.get(SpecialistHandoff, handoff_id)


def find_active_conflict(
    run_id: int,
    *,
    run_kind: str,
    attack_class: str,
    target_url: str,
    parameter: str | None = None,
    session_label: str | None = None,
) -> SpecialistHandoff | None:
    normalized = normalize_attack_class(attack_class)
    if not normalized:
        return None
    canonical = canonical_scope_url(target_url)
    with Session(get_engine(), expire_on_commit=False) as session:
        candidates = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.attack_class == normalized)
            .where(SpecialistHandoff.canonical_url == canonical)
            .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
        ).all()
    for candidate in candidates:
        if candidate.parameter and parameter and candidate.parameter != parameter:
            continue
        if (
            candidate.session_label
            and session_label
            and candidate.session_label != session_label
        ):
            continue
        return candidate
    return None


def infer_attack_class(tool_input: dict[str, Any]) -> str:
    explicit = normalize_attack_class(
        tool_input.get("attack_class") or tool_input.get("test_class")
    )
    if explicit:
        return explicit
    text = " ".join(
        str(tool_input.get(key) or "")
        for key in ("title", "hypothesis", "payload_purpose", "note", "evidence")
    ).lower()
    category = str(tool_input.get("owasp_category") or "").upper()
    checks = (
        ("file_upload", ("file upload", "multipart", "upload")),
        ("ssrf", ("ssrf", "webhook", "server-side request forgery")),
        ("path_traversal", ("path traversal", "directory traversal", "lfi")),
        ("sqli", ("sql injection", "sqli", "sql syntax")),
        ("xss", ("cross-site scripting", "xss", "<script", "onerror")),
        ("idor", ("idor", "foreign object", "broken access control")),
        ("auth_bypass", ("auth bypass", "authentication bypass")),
        ("business_logic", ("business logic", "workflow bypass")),
    )
    for attack_class, markers in checks:
        if any(marker in text for marker in markers):
            return attack_class
    return {
        "A07": "auth_bypass",
        "A10": "ssrf",
        "A04": "business_logic",
    }.get(category, "")


def automatic_candidate(
    tool_input: dict[str, Any],
    *,
    response_status: int,
    response_headers: dict[str, Any],
    response_body: str,
) -> dict[str, Any] | None:
    """Return a conservative automatic handoff for strong, cheap-to-detect signals."""
    url = str(tool_input.get("url") or "")
    body = tool_input.get("body")
    parameter = infer_parameter(url, body, tool_input.get("parameter"))
    keys = {
        key.lower() for key, _ in parse_qsl(urlparse(url).query, keep_blank_values=True)
    }
    if isinstance(body, dict):
        keys.update(str(key).lower() for key in body)
    content_type = str(response_headers.get("content-type") or "").lower()
    request_text = json.dumps(body, default=str).lower() if body is not None else ""
    path = urlparse(url).path.lower()

    if keys & _SSRF_KEYS and "example domain" not in response_body.lower():
        return {
            "attack_class": "ssrf",
            "priority": 6,
            "parameter": parameter,
            "rationale": f"Request exposed an SSRF-prone parameter on {url}.",
        }
    if (
        keys & _UPLOAD_KEYS
        or "multipart/form-data" in request_text
        or "multipart/form-data" in content_type
        or re.search(r"(?:^|/)(?:upload|attachments?)(?:/|$)", path)
    ):
        return {
            "attack_class": "file_upload",
            "priority": 8,
            "parameter": parameter,
            "rationale": f"Request reached a file-upload surface on {url}.",
        }
    lowered_response = response_body.lower()
    if response_status >= 500 and any(
        marker in lowered_response for marker in _SQL_ERROR_MARKERS
    ):
        return {
            "attack_class": "sqli",
            "priority": 9,
            "parameter": parameter,
            "rationale": f"Response from {url} contained a database error after an active probe.",
        }
    explicit_class = infer_attack_class(tool_input)
    if explicit_class == "xss" and any(
        marker in lowered_response for marker in ("<script", "onerror=", "onload=")
    ):
        return {
            "attack_class": "xss",
            "priority": 8,
            "parameter": parameter,
            "rationale": f"An XSS payload was reflected by {url}; a specialist should verify execution context.",
        }
    return None


def consume_feedback(run_id: int, *, run_kind: str) -> list[str]:
    with Session(get_engine(), expire_on_commit=False) as session:
        rows = list(
            session.exec(
                select(SpecialistHandoff)
                .where(SpecialistHandoff.run_kind == run_kind)
                .where(SpecialistHandoff.run_id == run_id)
                .where(
                    SpecialistHandoff.status.in_(("completed", "failed", "cancelled"))
                )
                .where(SpecialistHandoff.feedback_delivered == False)  # noqa: E712
                .order_by(SpecialistHandoff.id)
            ).all()
        )
        messages = []
        for row in rows:
            finding = f" Finding #{row.finding_id}." if row.finding_id else ""
            messages.append(
                f"{row.agent_id or 'Specialist'} finished {row.attack_class} on "
                f"{row.target_url}: {row.outcome or row.status}.{finding}"
            )
            row.feedback_delivered = True
            row.updated_at = datetime.now(_UTC)
            session.add(row)
        session.commit()
        return messages


def list_handoffs(run_id: int, *, run_kind: str) -> list[dict[str, Any]]:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .order_by(SpecialistHandoff.id.desc())
            .limit(50)
        ).all()
        return [
            {
                "agent_id": row.agent_id,
                "attack_class": row.attack_class,
                "target_url": row.target_url,
                "parameter": row.parameter,
                "priority": row.priority,
                "source": row.dispatch_source,
                "status": row.status,
                "finding_id": row.finding_id,
                "outcome": row.outcome,
            }
            for row in rows
        ]


def recover_interrupted_handoffs(run_id: int, *, run_kind: str) -> int:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
        ).all()
        now = datetime.now(_UTC)
        for row in rows:
            row.status = "failed"
            row.outcome = "Interrupted before the specialist completed. The scope is available again."
            row.completed_at = now
            row.updated_at = now
            session.add(row)
        session.commit()
        return len(rows)
