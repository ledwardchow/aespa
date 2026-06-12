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

import httpx
from sqlmodel import Session, func, select

from aespa.db import get_engine

BODY_LIMIT = 8192                                 # 8 KB per body stored
SKIP_RESOURCE_TYPES = {"image", "font", "media"}  # noisy, rarely useful


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Low-level writer ──────────────────────────────────────────────────────────

# Sentinel test_run_id used when writing API-scan traffic (no real TestRun row).
_API_SENTINEL_RUN_ID = 0


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
    username: Optional[str] = None,
    api_run_id: Optional[int] = None,
) -> None:
    from aespa.models import TrafficEntry
    with Session(get_engine()) as s:
        entry = TrafficEntry(
            test_run_id=run_id,
            api_test_run_id=api_run_id,
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
            username=username,
        )
        s.add(entry)
        s.commit()


# ── Query ─────────────────────────────────────────────────────────────────────

def clear_traffic(run_id: int) -> None:
    from aespa.models import TrafficEntry
    with Session(get_engine()) as s:
        entries = s.exec(
            select(TrafficEntry).where(TrafficEntry.test_run_id == run_id)
        ).all()
        for e in entries:
            s.delete(e)
        s.commit()


def get_traffic(run_id: int, since_id: int = 0, *, api_run_id: Optional[int] = None) -> list[dict]:
    from aespa.models import TrafficEntry
    with Session(get_engine()) as s:
        q = select(TrafficEntry).where(TrafficEntry.id > since_id).order_by(TrafficEntry.id).limit(500)
        if api_run_id is not None:
            q = q.where(TrafficEntry.api_test_run_id == api_run_id)
        else:
            q = q.where(TrafficEntry.test_run_id == run_id)
        entries = s.exec(q).all()
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
                "username": e.username,
            }
            for e in entries
        ]


def count_traffic(run_id: int, *, api_run_id: Optional[int] = None) -> int:
    from aespa.models import TrafficEntry
    with Session(get_engine()) as s:
        q = select(func.count(TrafficEntry.id))
        if api_run_id is not None:
            q = q.where(TrafficEntry.api_test_run_id == api_run_id)
        else:
            q = q.where(TrafficEntry.test_run_id == run_id)
        return s.exec(q).one()


# ── Per-api-run traffic callbacks ────────────────────────────────────────────

# api_scanner.py registers a callable here when a scan starts so it can mark
# coverage cells in_progress as HTTP requests are made.  The callable signature
# is fn(api_run_id: int, method: str, url: str) -> None and is called from an
# asyncio.to_thread context (so must be thread-safe / DB-only, no SSE emits).
_api_traffic_hooks: dict[int, object] = {}  # api_run_id → callable


# ── Custom client for automatic logging ───────────────────────────────────────

class LoggingAsyncClient(httpx.AsyncClient):
    def __init__(self, *args, run_id: Optional[int] = None, username: Optional[str] = None, api_run_id: Optional[int] = None, **kwargs):
        self.run_id = run_id
        self.api_run_id = api_run_id
        self.username = username
        kwargs.pop("event_hooks", None)
        super().__init__(*args, **kwargs)

    async def send(self, request: httpx.Request, *args, **kwargs) -> httpx.Response:
        if self.run_id is None and self.api_run_id is None:
            return await super().send(request, *args, **kwargs)

        # For API runs there is no real TestRun row; use sentinel 0.
        effective_run_id = self.run_id if self.run_id is not None else _API_SENTINEL_RUN_ID

        t0 = time.monotonic()
        try:
            response = await super().send(request, *args, **kwargs)
            duration_ms = int((time.monotonic() - t0) * 1000)

            try:
                await response.aread()
                ct = response.headers.get("content-type", "")
                if any(t in ct for t in ("text", "json", "xml", "html", "javascript")):
                    resp_body: Optional[str] = response.text[:BODY_LIMIT]
                else:
                    resp_body = f"[binary, {len(response.content)} bytes]"
            except Exception as e:
                resp_body = f"[Error reading response body: {e}]"

            raw_body = request.content
            req_body: Optional[str] = (
                raw_body.decode(errors="replace")[:BODY_LIMIT] if raw_body else None
            )

            await asyncio.to_thread(
                _write,
                effective_run_id,
                "httpx",
                request.method,
                str(request.url),
                dict(request.headers),
                req_body,
                response.status_code,
                dict(response.headers),
                resp_body,
                duration_ms,
                self.username,
                self.api_run_id,
            )
            # Fire any registered coverage-tracking callback for API runs.
            if self.api_run_id is not None:
                hook = _api_traffic_hooks.get(self.api_run_id)
                if hook is not None:
                    await asyncio.to_thread(
                        hook, self.api_run_id, request.method, str(request.url)
                    )
            return response
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            raw_body = request.content
            req_body: Optional[str] = (
                raw_body.decode(errors="replace")[:BODY_LIMIT] if raw_body else None
            )

            await asyncio.to_thread(
                _write,
                effective_run_id,
                "httpx",
                request.method,
                str(request.url),
                dict(request.headers),
                req_body,
                None,
                {},
                f"[Request Failed: {type(exc).__name__} - {exc}]",
                duration_ms,
                self.username,
                self.api_run_id,
            )
            raise exc


# ── httpx event hooks (Legacy fallback) ───────────────────────────────────────

def make_httpx_hooks(run_id: int, username: Optional[str] = None) -> dict:
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
            username,
        )

    return {"request": [on_request], "response": [on_response]}


# ── Playwright BrowserContext handler ─────────────────────────────────────────

def setup_playwright_logging(ctx, run_id: int, username: Optional[str] = None) -> None:
    """Register request/response listeners on a Playwright BrowserContext."""
    _pending: dict[int, float] = {}
    _req_data: dict[int, dict] = {}

    async def on_request(request) -> None:
        # Only store timing and body here.  Full headers are read in on_response
        # via response.request.all_headers(), which is the only point where the
        # browser has finalised cookies, Authorization, and other internally-added
        # headers.  Reading them in on_request captures only what the caller
        # explicitly set, which is why callers were seeing just the host header.
        rid = id(request)
        _pending[rid] = time.monotonic()
        post_data = request.post_data
        if post_data is None:
            try:
                pd_json = request.post_data_json
                if pd_json is not None:
                    post_data = json.dumps(pd_json)
            except Exception:
                pass
        _req_data[rid] = {
            "method": request.method,
            "post_data": post_data,
        }

    async def on_response(response) -> None:
        if response.request.resource_type in SKIP_RESOURCE_TYPES:
            return

        rid = id(response.request)
        start = _pending.pop(rid, None)
        req_data = _req_data.pop(rid, {})
        duration_ms = int((time.monotonic() - start) * 1000) if start is not None else None

        # Read request headers here — the full set (cookies, Authorization, etc.)
        # is only available after the request has been sent.
        try:
            req_headers = await response.request.all_headers()
        except Exception:
            try:
                req_headers = dict(response.request.headers)
            except Exception:
                req_headers = {}

        # Prefer the body captured at request time; fall back to response.request.
        post_data = req_data.get("post_data")
        if post_data is None:
            try:
                post_data = response.request.post_data
                if post_data is None:
                    pd_json = response.request.post_data_json
                    if pd_json is not None:
                        post_data = json.dumps(pd_json)
            except Exception:
                pass

        # Use response.body() (raw bytes) — more reliable than response.text().
        # text() can fail if encoding detection breaks or the body is already consumed;
        # body() reads the raw CDP buffer directly.
        try:
            body_bytes = await response.body()
            ct = response.headers.get("content-type", "")
            if any(t in ct for t in ("text", "json", "xml", "html", "javascript")):
                resp_body: Optional[str] = body_bytes.decode(errors="replace")[:BODY_LIMIT]
            else:
                resp_body = f"[binary, {len(body_bytes)} bytes]"
        except Exception:
            try:
                resp_body = (await response.text())[:BODY_LIMIT]
            except Exception:
                resp_body = None

        try:
            all_resp_hdrs = await response.all_headers()
        except Exception:
            all_resp_hdrs = dict(response.headers)

        await asyncio.to_thread(
            _write,
            run_id,
            "playwright",
            req_data.get("method", response.request.method),
            response.url,
            req_headers,
            post_data,
            response.status,
            all_resp_hdrs,
            resp_body,
            duration_ms,
            username,
        )

    async def on_request_failed(request) -> None:
        if request.resource_type in SKIP_RESOURCE_TYPES:
            return

        rid = id(request)
        start = _pending.pop(rid, None)
        req_data = _req_data.pop(rid, {})
        duration_ms = int((time.monotonic() - start) * 1000) if start is not None else None

        try:
            req_headers = await request.all_headers()
        except Exception:
            try:
                req_headers = dict(request.headers)
            except Exception:
                req_headers = {}

        post_data = req_data.get("post_data")
        if post_data is None:
            try:
                post_data = request.post_data
                if post_data is None:
                    pd_json = request.post_data_json
                    if pd_json is not None:
                        post_data = json.dumps(pd_json)
            except Exception:
                pass

        error_text = request.failure or "Request failed"

        await asyncio.to_thread(
            _write,
            run_id,
            "playwright",
            req_data.get("method", request.method),
            request.url,
            req_headers,
            post_data,
            None,
            {},
            f"[Browser Request Failed: {error_text}]",
            duration_ms,
            username,
        )

    ctx.on("request", on_request)
    ctx.on("response", on_response)
    ctx.on("requestfailed", on_request_failed)
