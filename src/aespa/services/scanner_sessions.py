from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import ScannerSession


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stable_label(raw: str, existing: set[str] | None = None) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", (raw or "").strip().lower()).strip("_")
    base = base[:40] or "session"
    if existing is None:
        return base
    label = base
    counter = 2
    while label in existing:
        label = f"{base}_{counter}"
        counter += 1
    return label


def credential_label(username: str | None, *, primary: bool = False) -> str:
    if primary:
        return "configured_primary"
    return stable_label(f"configured_{username or 'user'}")


def _json_dump(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), default=str)


def _json_load(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _token_hint(extra_headers: dict[str, Any] | None) -> str | None:
    auth = ""
    for key, value in (extra_headers or {}).items():
        if str(key).lower() == "authorization":
            auth = str(value)
            break
    if not auth:
        return None
    parts = auth.split(None, 1)
    token = parts[1] if len(parts) == 2 else auth
    if len(token) <= 16:
        return token
    return f"{token[:8]}...{token[-6:]}"


def upsert_session(
    run_id: int,
    *,
    label: str,
    kind: str,
    account_label: str | None = None,
    username: str | None = None,
    credential_id: int | None = None,
    source: str = "scanner",
    cookies: dict[str, Any] | None = None,
    extra_headers: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    run_kind: str = "web",
) -> ScannerSession:
    normalized_label = stable_label(label)
    now = _utcnow()
    with Session(get_engine()) as session:
        existing = session.exec(
            select(ScannerSession)
            .where(ScannerSession.test_run_id == run_id)
            .where(ScannerSession.run_kind == run_kind)
            .where(ScannerSession.label == normalized_label)
        ).first()
        record = existing or ScannerSession(
            test_run_id=run_id, run_kind=run_kind, label=normalized_label
        )
        record.kind = kind
        # A later capture may refresh the auth material without knowing which
        # account originally produced it.  Do not erase attribution that was
        # already established for this durable label.
        if account_label is not None or record.account_label is None:
            record.account_label = account_label
        if username is not None or record.username is None:
            record.username = username
        if credential_id is not None or record.credential_id is None:
            record.credential_id = credential_id
        record.source = source
        record.cookies_json = _json_dump(cookies)
        record.extra_headers_json = _json_dump(extra_headers)
        record.session_metadata = _json_dump(metadata)
        record.token_hint = _token_hint(extra_headers)
        record.is_active = True
        record.updated_at = now
        if existing is None:
            record.created_at = now
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def ensure_anonymous_session(
    run_id: int, *, source: str = "scanner", run_kind: str = "web"
) -> ScannerSession:
    return upsert_session(
        run_id,
        label="anonymous",
        kind="anonymous",
        source=source,
        cookies={},
        extra_headers={},
        metadata={"description": "No cookies or Authorization header"},
        run_kind=run_kind,
    )


def list_run_sessions(
    run_id: int, *, active_only: bool = True, run_kind: str = "web"
) -> list[ScannerSession]:
    with Session(get_engine()) as session:
        query = (
            select(ScannerSession)
            .where(ScannerSession.test_run_id == run_id)
            .where(ScannerSession.run_kind == run_kind)
        )
        if active_only:
            query = query.where(ScannerSession.is_active == True)  # noqa: E712
        return list(session.exec(query.order_by(ScannerSession.label)))


def load_session_vault(run_id: int, *, run_kind: str = "web") -> dict[str, dict[str, Any]]:
    vault: dict[str, dict[str, Any]] = {}
    for record in list_run_sessions(run_id, run_kind=run_kind):
        vault[record.label] = {
            "label": record.label,
            "kind": record.kind,
            "account_label": record.account_label,
            "username": record.username,
            "credential_id": record.credential_id,
            "source": record.source,
            "cookies": _json_load(record.cookies_json),
            "extra_headers": _json_load(record.extra_headers_json),
            "metadata": _json_load(record.session_metadata),
        }
    return vault
