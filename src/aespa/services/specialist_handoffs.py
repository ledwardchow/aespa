"""Persistent ownership and signal routing for specialist investigations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlparse

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    DiscoveredTarget,
    SpecialistHandoff,
    TargetAccessObservation,
    TrafficEntry,
)
from aespa.services.target_catalog import exact_url, state_identity

_UTC = timezone.utc
ACTIVE_STATUSES = ("queued", "running")
_ACCESS_FACT_KEYS = {
    "owner",
    "owner_id",
    "user_id",
    "account_id",
    "tenant_id",
    "role",
    "roles",
    "permissions",
    "entitlements",
    "access",
    "authorized",
    "is_admin",
    "can_read",
    "can_write",
    "can_edit",
    "can_delete",
}


def _stable_access_facts(body: str | None) -> str | None:
    try:
        payload = json.loads(body or "")
    except (TypeError, ValueError):
        return None
    facts: list[tuple[str, str]] = []

    def visit(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                name = str(key).lower()
                path = f"{prefix}.{name}" if prefix else name
                if name in _ACCESS_FACT_KEYS and not isinstance(child, (dict, list)):
                    facts.append((path, json.dumps(child, sort_keys=True, default=str)))
                elif name in _ACCESS_FACT_KEYS and isinstance(child, list):
                    facts.append((path, json.dumps(child, sort_keys=True, default=str)))
                elif isinstance(child, dict):
                    visit(child, path)
        elif isinstance(value, list):
            for item in value:
                visit(item, prefix)

    visit(payload)
    return json.dumps(sorted(facts), separators=(",", ":")) if facts else None


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
    try:
        return exact_url(str(url or "").strip())
    except ValueError:
        return str(url or "").strip()


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
    method: str = "GET",
    state_key: str | None = None,
    body_identity: str | None = None,
    actor_key: str | None = None,
    comparison_actor_key: str | None = None,
) -> str:
    material = json.dumps(
        [
            normalize_attack_class(attack_class),
            method.upper(),
            canonical_scope_url(target_url),
            state_identity(state_key),
            body_identity,
            str(parameter or "").strip().lower(),
            actor_key
            or (
                f"unknown:session:{session_label}"
                if session_label
                else "unknown:unresolved"
            ),
            comparison_actor_key,
        ],
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _revision_key(
    session: Session,
    run_id: int,
    run_kind: str,
    evidence_ids: tuple[int, ...],
    *,
    target_url: str,
    state_key: str | None,
    method: str,
    session_label: str | None,
    body_identity: str | None,
    actor_key: str,
    comparison_actor_key: str | None,
) -> str:
    facts = []
    for evidence_id in sorted(set(evidence_ids)):
        if run_kind == "web":
            row = session.get(TargetAccessObservation, evidence_id)
            target = session.get(DiscoveredTarget, row.target_id) if row else None
            if (
                row is None
                or target is None
                or row.test_run_id != run_id
                or target.test_run_id != run_id
                or target.url != canonical_scope_url(target_url)
                or target.state_identity != state_identity(state_key)
                or row.method.upper() != method.upper()
                or row.actor_key not in {actor_key, comparison_actor_key}
            ):
                raise ValueError(
                    "Handoff evidence must match the exact web target, method and actor"
                )
            traffic = (
                session.get(TrafficEntry, row.source_id)
                if row.source_kind == "traffic"
                else None
            )
            if (
                traffic is None
                or traffic.test_run_id != run_id
                or traffic.api_test_run_id is not None
            ):
                raise ValueError("Handoff evidence needs a direct web response")
            if body_identity is not None:
                from aespa.services.web_workprogram import _request_body_identity

                if _request_body_identity(traffic.request_body) != body_identity:
                    raise ValueError(
                        "Handoff evidence request body differs from the claimed scope"
                    )
        elif run_kind == "api":
            traffic = session.get(TrafficEntry, evidence_id)
            if (
                traffic is None
                or traffic.api_test_run_id != run_id
                or traffic.test_run_id is not None
                or canonical_scope_url(traffic.url) != canonical_scope_url(target_url)
                or traffic.method.upper() != method.upper()
                or (traffic.session_label or None) != session_label
            ):
                raise ValueError(
                    "Handoff evidence must match the exact API request and session"
                )
            if body_identity is not None:
                from aespa.services.web_workprogram import _request_body_identity

                if _request_body_identity(traffic.request_body) != body_identity:
                    raise ValueError(
                        "Handoff evidence request body differs from the claimed scope"
                    )
            row = None
        else:
            raise ValueError("Unsupported handoff run kind")
        facts.append(
            (
                row.actor_key if row else actor_key,
                row.result if row else traffic.status,
                traffic.status,
                _stable_access_facts(traffic.response_body),
            )
        )
    material = (
        json.dumps(sorted(set(facts)), separators=(",", ":")) if facts else "initial"
    )
    return hashlib.sha256(material.encode()).hexdigest()


def create_or_get_handoff(
    *,
    run_id: int,
    run_kind: str,
    attack_class: str,
    target_url: str,
    page_id: int | None,
    parameter: str | None,
    session_label: str | None,
    priority: int,
    rationale: str,
    dispatch_source: str,
    agent_id: str,
    method: str = "GET",
    state_key: str | None = None,
    body_identity: str | None = None,
    actor_key: str | None = None,
    comparison_actor_key: str | None = None,
    evidence_observation_ids: tuple[int, ...] = (),
    retry_request_id: str | None = None,
) -> tuple[SpecialistHandoff, bool]:
    normalized = normalize_attack_class(attack_class)
    fingerprint = handoff_fingerprint(
        normalized,
        target_url,
        parameter=parameter,
        session_label=session_label,
        method=method,
        state_key=state_key,
        body_identity=body_identity,
        actor_key=actor_key,
        comparison_actor_key=comparison_actor_key,
    )
    with Session(get_engine(), expire_on_commit=False) as session:
        revision_key = _revision_key(
            session,
            run_id,
            run_kind,
            evidence_observation_ids,
            target_url=target_url,
            state_key=state_key,
            method=method,
            session_label=session_label,
            body_identity=body_identity,
            actor_key=actor_key
            or (
                f"unknown:session:{session_label}"
                if session_label
                else "unknown:unresolved"
            ),
            comparison_actor_key=comparison_actor_key,
        )
        if retry_request_id:
            revision_key = hashlib.sha256(
                f"retry:{retry_request_id}".encode()
            ).hexdigest()
        row_fingerprint = hashlib.sha256(
            f"{fingerprint}:{revision_key}".encode()
        ).hexdigest()
        existing = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.scope_key == fingerprint)
            .where(SpecialistHandoff.revision_key == revision_key)
        ).first()
        if existing is not None:
            if existing.status == "failed" and (existing.outcome or "").startswith(
                "Interrupted before the specialist completed"
            ):
                conflict = session.exec(
                    select(SpecialistHandoff)
                    .where(SpecialistHandoff.run_kind == run_kind)
                    .where(SpecialistHandoff.run_id == run_id)
                    .where(SpecialistHandoff.scope_key == fingerprint)
                    .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
                ).first()
                if conflict is None:
                    existing.status = "queued"
                    existing.outcome = None
                    existing.completed_at = None
                    existing.updated_at = datetime.now(_UTC)
                    session.add(existing)
                    try:
                        session.commit()
                    except IntegrityError:
                        session.rollback()
                    else:
                        session.refresh(existing)
                        return existing, True
            if existing.page_id is None and page_id is not None:
                existing.page_id = page_id
                existing.updated_at = datetime.now(_UTC)
                session.add(existing)
                session.commit()
                session.refresh(existing)
            return existing, False
        active = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.scope_key == fingerprint)
            .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
        ).first()
        if active is None and evidence_observation_ids and not retry_request_id:
            prior = session.exec(
                select(SpecialistHandoff)
                .where(SpecialistHandoff.run_kind == run_kind)
                .where(SpecialistHandoff.run_id == run_id)
                .where(SpecialistHandoff.scope_key == fingerprint)
                .order_by(SpecialistHandoff.id.desc())
            ).first()
            if prior is not None and prior.revision_key == revision_key:
                return prior, False
        handoff = SpecialistHandoff(
            run_kind=run_kind,
            run_id=run_id,
            fingerprint=row_fingerprint,
            scope_key=fingerprint,
            revision_key=revision_key,
            method=method.upper(),
            state_identity=state_identity(state_key),
            body_identity=body_identity,
            actor_key=actor_key
            or (
                f"unknown:session:{session_label}"
                if session_label
                else "unknown:unresolved"
            ),
            comparison_actor_key=comparison_actor_key,
            attack_class=normalized,
            target_url=target_url,
            canonical_url=canonical_scope_url(target_url),
            page_id=page_id,
            parameter=parameter,
            session_label=session_label,
            priority=priority,
            rationale=rationale,
            dispatch_source=dispatch_source,
            agent_id=agent_id,
            status="deferred" if active is not None else "queued",
        )
        session.add(handoff)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.exec(
                select(SpecialistHandoff)
                .where(SpecialistHandoff.run_kind == run_kind)
                .where(SpecialistHandoff.run_id == run_id)
                .where(SpecialistHandoff.scope_key == fingerprint)
                .where(SpecialistHandoff.revision_key == revision_key)
            ).first()
            if existing is None:
                existing = session.exec(
                    select(SpecialistHandoff)
                    .where(SpecialistHandoff.run_kind == run_kind)
                    .where(SpecialistHandoff.run_id == run_id)
                    .where(SpecialistHandoff.scope_key == fingerprint)
                    .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
                ).first()
            if existing is None:
                raise
            return existing, False
        session.refresh(handoff)
        return handoff, active is None


def update_handoff(
    handoff_id: int,
    *,
    status: str | None = None,
    outcome: str | None = None,
    finding_id: int | None = None,
    page_id: int | None = None,
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
        if page_id is not None:
            handoff.page_id = page_id
        handoff.updated_at = now
        session.add(handoff)
        session.commit()


def activate_deferred(
    run_id: int, *, run_kind: str = "web", eligible_ids: set[int] | None = None
) -> list[SpecialistHandoff]:
    claimed: list[SpecialistHandoff] = []
    with Session(get_engine(), expire_on_commit=False) as session:
        deferred = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.status == "deferred")
            .order_by(SpecialistHandoff.id)
        ).all()
        for handoff in deferred:
            if eligible_ids is not None and handoff.id not in eligible_ids:
                continue
            active = session.exec(
                select(SpecialistHandoff)
                .where(SpecialistHandoff.run_id == run_id)
                .where(SpecialistHandoff.run_kind == run_kind)
                .where(SpecialistHandoff.scope_key == handoff.scope_key)
                .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
            ).first()
            if active is not None:
                continue
            handoff.status = "queued"
            handoff.updated_at = datetime.now(_UTC)
            session.add(handoff)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                continue
            claimed.append(handoff)
        return claimed


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
    method: str = "GET",
    state_key: str | None = None,
    body_identity: str | None = None,
    actor_key: str | None = None,
    comparison_actor_key: str | None = None,
) -> SpecialistHandoff | None:
    normalized = normalize_attack_class(attack_class)
    if not normalized:
        return None
    scope_key = handoff_fingerprint(
        normalized,
        target_url,
        parameter=parameter,
        session_label=session_label,
        method=method,
        state_key=state_key,
        body_identity=body_identity,
        actor_key=actor_key,
        comparison_actor_key=comparison_actor_key,
    )
    with Session(get_engine(), expire_on_commit=False) as session:
        return session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.scope_key == scope_key)
            .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
        ).first()


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


def reclaim_interrupted_handoffs(
    run_id: int, *, run_kind: str, limit: int
) -> list[SpecialistHandoff]:
    claimed: list[SpecialistHandoff] = []
    with Session(get_engine(), expire_on_commit=False) as session:
        rows = session.exec(
            select(SpecialistHandoff)
            .where(SpecialistHandoff.run_kind == run_kind)
            .where(SpecialistHandoff.run_id == run_id)
            .where(SpecialistHandoff.status == "failed")
            .order_by(SpecialistHandoff.id)
        ).all()
        for row in rows:
            if len(claimed) >= limit:
                break
            if not (row.outcome or "").startswith(
                "Interrupted before the specialist completed"
            ):
                continue
            if row.scope_key is None:
                continue
            active = session.exec(
                select(SpecialistHandoff)
                .where(SpecialistHandoff.run_kind == run_kind)
                .where(SpecialistHandoff.run_id == run_id)
                .where(SpecialistHandoff.scope_key == row.scope_key)
                .where(SpecialistHandoff.status.in_(ACTIVE_STATUSES))
            ).first()
            if active is not None:
                continue
            row.status = "queued"
            row.outcome = None
            row.completed_at = None
            row.updated_at = datetime.now(_UTC)
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                continue
            claimed.append(row)
    return claimed
