"""Traffic logging service.

Captures HTTP request/response pairs from both httpx and Playwright,
persists them to the DB, and exposes a polling endpoint for the frontend.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from aespa.db import get_engine

BODY_LIMIT = 8192                                 # 8 KB per body stored
SKIP_RESOURCE_TYPES = {"image", "font", "media"}  # noisy, rarely useful


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Low-level writer ──────────────────────────────────────────────────────────

def _write(
    run_id: int,
    source: str,
    method: str,
    url: str,
    request_headers: dict,
    request_body: Optional[str],
    status: Optional[int],
    response_headers: dict,
    response_body: Optional[str],
    duration_ms: Optional[int],
) -> None:
    from aespa.models import TrafficEntry
    with Session(get_engine()) as s:
        entry = TrafficEntry(
            test_run_id=run_id,
            source=source,
            created_at=_utcnow(),
            method=method,
            url=url,
            request_headers=json.dumps(request_headers),
            request_body=(request_body or "")[:BODY_LIMIT] or None,
            status=status,
            response_headers=json.dumps(response_headers),
            response_body=(response_body or "")[:BODY_LIMIT] or None,
            duration_ms=duration_ms,
        )
        s.add(entry)
        s.commit()


# ── Query ─────────────────────────────────────────────────────────────────────

def get_traffic(run_id: int, since_id: int = 0) -> list[dict]:
    from aespa.models import TrafficEntry
    with Session(get_engine()) as s:
        entries = s.exec(
            select(TrafficEntry)
            .where(TrafficEntry.test_run_id == run_id)
            .where(TrafficEntry.id > since_id)
            .order_by(TrafficEntry.id)
            .limit(500)
        ).all()
        return [
            {
                "id": e.id,
                "source": e.source,
                "created_at": e.created_at.isoformat(),
                "method": e.method,
                "url": e.url,
                "request_headers": json.loads(e.request_headers or "{}"),
                "request_body": e.request_body,
                "status": e.status,
                "response_headers": json.loads(e.response_headers or "{}"),
                "response_body": e.response_body,
                "duration_ms": e.duration_ms,
            }
            for e in entries
        ]


# ── httpx event hooks ─────────────────────────────────────────────────────────

def make_httpx_hooks(run_id: int) -> dict:
    """Return an httpx event_hooks dict that logs every request/response."""
    _pending: dict[int, float] = {}  # id(request) → monotonic start time

    async def on_request(request) -> None:
        _pending[id(request)] = time.monotonic()

    async def on_response(response) -> None:
        start = _pending.pop(id(response.request), None)
        duration_ms = int((time.monotonic() - start) * 1000) if start is not None else None

        # Ensure body bytes are fully read before accessing .text / .content.
        await response.aread()

        ct = response.headers.get("content-type", "")
        if any(t in ct for t in ("text", "json", "xml", "html", "javascript")):
            resp_body: Optional[str] = response.text[:BODY_LIMIT]
        else:
            resp_body = f"[binary, {len(response.content)} bytes]"

        req = response.request
        raw_body = req.content
        req_body: Optional[str] = (
            raw_body.decode(errors="replace")[:BODY_LIMIT] if raw_body else None
        )

        await asyncio.to_thread(
            _write,
            run_id,
            "httpx",
            req.method,
            str(req.url),
            dict(req.headers),
            req_body,
            response.status_code,
            dict(response.headers),
            resp_body,
            duration_ms,
        )

    return {"request": [on_request], "response": [on_response]}


# ── Playwright BrowserContext handler ─────────────────────────────────────────

def setup_playwright_logging(ctx, run_id: int) -> None:
    """Register request/response listeners on a Playwright BrowserContext."""
    _pending: dict[int, float] = {}
    _req_data: dict[int, dict] = {}

    def on_request(request) -> None:
        rid = id(request)
        _pending[rid] = time.monotonic()
        _req_data[rid] = {
            "method": request.method,
            "headers": dict(request.headers),
            "post_data": request.post_data,
        }

    async def on_response(response) -> None:
        if response.request.resource_type in SKIP_RESOURCE_TYPES:
            return

        rid = id(response.request)
        start = _pending.pop(rid, None)
        req_data = _req_data.pop(rid, {})
        duration_ms = int((time.monotonic() - start) * 1000) if start is not None else None

        try:
            ct = response.headers.get("content-type", "")
            if any(t in ct for t in ("text", "json", "xml", "html", "javascript")):
                resp_body: Optional[str] = (await response.text())[:BODY_LIMIT]
            else:
                resp_body = "[binary]"
        except Exception:
            resp_body = None

        await asyncio.to_thread(
            _write,
            run_id,
            "playwright",
            req_data.get("method", response.request.method),
            response.url,
            req_data.get("headers", {}),
            req_data.get("post_data"),
            response.status,
            dict(response.headers),
            resp_body,
            duration_ms,
        )

    ctx.on("request", on_request)
    ctx.on("response", on_response)
