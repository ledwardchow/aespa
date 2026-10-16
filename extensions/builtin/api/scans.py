"""Scan ownership, status responses, and Idempotency-Key handling."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from aespa.extensions import ExtensionDataStore

from .auth import Caller, new_secret
from .models import ApiIdempotency, ApiScan, ApiToken
from .schemas import DEFAULT_CALLBACK_EVENTS, CallbackConfig

EXTENSION_ID = "aespa.api"
BASE_PATH = f"/extension/{EXTENSION_ID}/v1"


def scan_id(kind: str, run_id: int) -> str:
    return f"{kind}-{run_id}"


def parse_scan_id(value: str) -> tuple[str, int]:
    kind, _, number = value.partition("-")
    if kind not in {"web", "sast"} or not number.isdigit():
        raise HTTPException(status_code=404, detail="Scan not found")
    return kind, int(number)


def links(kind: str, run_id: int) -> dict[str, str | None]:
    base = f"{BASE_PATH}/scans/{scan_id(kind, run_id)}"
    return {
        "self": base,
        "findings": f"{base}/findings",
        "summary": f"{base}/summary",
        "activity": f"{base}/activity",
        "sarif": f"{base}/sarif",
    }


def callback_events(row: ApiScan) -> list[str]:
    try:
        values = json.loads(row.callback_events_json or "[]")
    except (TypeError, ValueError):
        values = []
    return [str(value) for value in values]


def start_options(row: ApiScan) -> dict[str, Any]:
    try:
        value = json.loads(row.start_options_json or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def status_payload(core, row: ApiScan) -> dict[str, Any]:
    progress = core.runs.progress(row.run_id, scan_after_crawl=row.scan_after_crawl)
    if progress is None:
        raise HTTPException(
            status_code=404, detail="This scan's run was deleted in AESPA."
        )
    payload = {
        **progress,
        "scan_after_crawl": row.scan_after_crawl if row.kind == "web" else None,
        "links": links(row.kind, row.run_id),
        "callbacks": (
            {"url": row.callback_url, "events": callback_events(row)}
            if row.callback_url
            else None
        ),
    }
    if row.kind == "web":
        payload["site_id"] = core.web.site_id_for_run(row.run_id)
    return payload


def get_owned(store: ExtensionDataStore, caller: Caller, value: str) -> ApiScan:
    kind, run_id = parse_scan_id(value)
    with store.session() as session:
        row = session.exec(select(ApiScan).where(ApiScan.run_id == run_id)).first()
    if row is None or row.kind != kind or row.token_id != caller.token_id:
        raise HTTPException(status_code=404, detail="Scan not found")
    return row


def record_scan(
    store: ExtensionDataStore,
    caller: Caller,
    *,
    run_id: int,
    kind: str,
    scan_after_crawl: bool,
    callbacks: CallbackConfig | None,
    start_options: dict[str, Any] | None = None,
) -> tuple[ApiScan, str | None]:
    """Save the scan's owner and callback settings.

    Returns the row and, when AESPA created the callback secret, that secret so
    it can be shown once.
    """
    created_secret = None
    with store.session() as session:
        token = session.get(ApiToken, caller.token_id)
        url = secret = None
        events: list[str] = list(DEFAULT_CALLBACK_EVENTS)
        if callbacks is not None:
            url = str(callbacks.url)
            events = list(dict.fromkeys(callbacks.events))
            secret = callbacks.secret or (token.webhook_secret if token else None)
            if not secret:
                secret = created_secret = new_secret()
        elif token is not None and token.webhook_url:
            url, secret = token.webhook_url, token.webhook_secret
        row = ApiScan(
            run_id=run_id,
            kind=kind,
            token_id=caller.token_id,
            scan_after_crawl=scan_after_crawl,
            start_options_json=json.dumps(start_options or {}),
            callback_url=url,
            callback_secret=secret,
            callback_events_json=json.dumps(events),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    return row, created_secret


# ── Idempotency ──────────────────────────────────────────────────────────────


def request_hash(*parts: Any) -> str:
    text = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def claim_key(
    store: ExtensionDataStore, caller: Caller, key: str | None, digest: str
) -> tuple[int, Any] | None:
    """Reserve an Idempotency-Key, or return the saved response for it."""
    if not key:
        return None
    if len(key) > 200:
        raise HTTPException(status_code=422, detail="Idempotency-Key is too long.")
    with store.session() as session:
        existing = session.exec(
            select(ApiIdempotency)
            .where(ApiIdempotency.token_id == caller.token_id)
            .where(ApiIdempotency.key == key)
        ).first()
        if existing is None:
            session.add(
                ApiIdempotency(token_id=caller.token_id, key=key, request_hash=digest)
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="A request with this Idempotency-Key is still running.",
                ) from None
            return None
    if existing.request_hash != digest:
        raise HTTPException(
            status_code=422,
            detail="This Idempotency-Key was already used for a different request.",
        )
    if existing.response_json is None:
        raise HTTPException(
            status_code=409,
            detail="A request with this Idempotency-Key is still running.",
        )
    return existing.status_code or 200, json.loads(existing.response_json)


def save_key(
    store: ExtensionDataStore,
    caller: Caller,
    key: str | None,
    status_code: int,
    body: Any,
) -> None:
    if not key:
        return
    with store.session() as session:
        row = session.exec(
            select(ApiIdempotency)
            .where(ApiIdempotency.token_id == caller.token_id)
            .where(ApiIdempotency.key == key)
        ).first()
        if row is not None:
            row.status_code = status_code
            row.response_json = json.dumps(body, default=str)
            session.add(row)
            session.commit()


def release_key(store: ExtensionDataStore, caller: Caller, key: str | None) -> None:
    """Free a key whose request failed so the client can retry it."""
    if not key:
        return
    with store.session() as session:
        row = session.exec(
            select(ApiIdempotency)
            .where(ApiIdempotency.token_id == caller.token_id)
            .where(ApiIdempotency.key == key)
        ).first()
        if row is not None and row.response_json is None:
            session.delete(row)
            session.commit()
