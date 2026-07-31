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

BODY_LIMIT = 8192  # 8 KB per body stored
SKIP_RESOURCE_TYPES = {"image", "font", "media"}  # noisy, rarely useful

# In-memory cache of WAF detections, keyed by (run_kind, run_id), so the
# agentic scan loop can check "is this run behind a WAF?" on every tool call
# without a DB round-trip. Populated as a side effect of _write() below;
# the DB columns (TestRun/ApiTestRun.waf_*) are the durable copy used by the
# UI and across process restarts.
_waf_cache: dict[tuple[str, int], dict] = {}
_waf_cache_hydrated: set[tuple[str, int]] = set()


def get_cached_waf(run_id: int, *, api_run_id: Optional[int] = None) -> Optional[dict]:
    """Return the WAF detection, hydrating it from the run row when needed."""
    cache_key = ("api", api_run_id) if api_run_id is not None else ("web", run_id)
    cached = _waf_cache.get(cache_key)
    if cached is not None:
        return cached
    if cache_key in _waf_cache_hydrated:
        return None
    _waf_cache_hydrated.add(cache_key)

    try:
        from aespa.models import ApiTestRun, TestRun
        from aespa.services.waf_detect import strategy_for_provider

        with Session(get_engine()) as session:
            model = ApiTestRun if api_run_id is not None else TestRun
            run = session.get(model, api_run_id if api_run_id is not None else run_id)
            if run is None or not run.waf_provider:
                return None
            detection = {
                "provider": run.waf_provider,
                "confidence": run.waf_confidence or "medium",
                "evidence": run.waf_evidence or "",
                "strategy": strategy_for_provider(run.waf_provider),
            }
            _waf_cache[cache_key] = detection
            return detection
    except Exception:
        # Routing is best-effort. A failed hydration must not break a scan.
        return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_playwright_post_data(request) -> Optional[str]:
    """Best-effort extraction of Playwright request body.

    Some Playwright requests carry binary/compressed payloads where
    ``request.post_data`` raises UnicodeDecodeError. This helper never raises.
    """
    try:
        post_data = request.post_data
        if isinstance(post_data, str):
            return post_data
        if isinstance(post_data, (bytes, bytearray)):
            return bytes(post_data).decode(errors="replace")
    except UnicodeDecodeError:
        try:
            post_data_bytes = request.post_data_buffer
            if isinstance(post_data_bytes, (bytes, bytearray)) and post_data_bytes:
                return f"[binary, {len(post_data_bytes)} bytes]"
        except Exception:
            return "[binary request body]"
        return "[binary request body]"
    except Exception:
        pass

    try:
        pd_json = request.post_data_json
        if pd_json is not None:
            return json.dumps(pd_json)
    except Exception:
        pass

    try:
        post_data_bytes = request.post_data_buffer
        if isinstance(post_data_bytes, (bytes, bytearray)) and post_data_bytes:
            return bytes(post_data_bytes).decode(errors="replace")
    except Exception:
        pass

    return None


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

    _maybe_record_waf(run_id, api_run_id, url, response_headers, response_body)


def _maybe_record_waf(
    run_id: int,
    api_run_id: Optional[int],
    url: str,
    response_headers: dict,
    response_body: Optional[str],
) -> None:
    """Passively fingerprint a WAF/bot-manager from this response and persist
    the first (highest-confidence) detection for the run, both to the in-memory
    cache (fast path for the scan loop) and to the run row (durable, for the
    Attack Surface UI). Idempotent and best-effort — never raises.
    """
    from urllib.parse import urlparse

    from aespa.services.waf_detect import detect_waf

    try:
        detection = detect_waf(response_headers, response_body)
        if detection is None:
            return

        req_hostname = (urlparse(url).hostname or "").lower() if url else ""
        if not req_hostname:
            return

        cache_key = ("api", api_run_id) if api_run_id is not None else ("web", run_id)
        cached = _waf_cache.get(cache_key)
        if cached and cached.get("provider") == detection["provider"]:
            return  # already known; avoid a DB write on every matching request

        from aespa.models import ApiCollection, ApiTestRun, Site, TestRun
        from aespa.services.scope import _same_root_domain

        with Session(get_engine()) as s:
            if api_run_id is not None:
                api_run = s.get(ApiTestRun, api_run_id)
                if api_run is None:
                    return
                collection = (
                    s.get(ApiCollection, api_run.collection_id)
                    if api_run.collection_id
                    else None
                )
                scope_hosts = json.loads(
                    (collection.scope_hosts if collection else None) or "[]"
                )
                base_url = collection.base_url if collection else None
                run = api_run
            else:
                run = s.get(TestRun, run_id)
                if run is None:
                    return
                site = s.get(Site, run.site_id) if run.site_id else None
                scope_hosts = json.loads((site.scope_hosts if site else None) or "[]")
                base_url = site.base_url if site else None

            # Enforce scope check: only attribute WAF to in-scope hostnames
            if scope_hosts:
                if req_hostname not in scope_hosts:
                    return
            elif base_url:
                base_hostname = (urlparse(base_url).hostname or "").lower()
                if base_hostname and not _same_root_domain(req_hostname, base_hostname):
                    return

            if run.waf_provider == detection["provider"]:
                _waf_cache[cache_key] = detection
                _waf_cache_hydrated.add(cache_key)
                return
            _waf_cache[cache_key] = detection
            _waf_cache_hydrated.add(cache_key)
            run.waf_provider = detection["provider"]
            run.waf_confidence = detection["confidence"]
            run.waf_evidence = detection["evidence"][:500]
            s.add(run)
            s.commit()
    except Exception:
        # Passive fingerprinting must never break traffic logging.
        pass


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


def get_traffic(
    run_id: int, since_id: int = 0, *, api_run_id: Optional[int] = None
) -> list[dict]:
    from aespa.models import TrafficEntry

    with Session(get_engine()) as s:
        q = (
            select(TrafficEntry)
            .where(TrafficEntry.id > since_id)
            .order_by(TrafficEntry.id)
            .limit(500)
        )
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
    def __init__(
        self,
        *args,
        run_id: Optional[int] = None,
        username: Optional[str] = None,
        api_run_id: Optional[int] = None,
        **kwargs,
    ):
        self.run_id = run_id
        self.api_run_id = api_run_id
        self.username = username
        kwargs.pop("event_hooks", None)
        super().__init__(*args, **kwargs)

    async def send(self, request: httpx.Request, *args, **kwargs) -> httpx.Response:
        if self.run_id is None and self.api_run_id is None:
            return await super().send(request, *args, **kwargs)

        # For API runs there is no real TestRun row; use sentinel 0.
        effective_run_id = (
            self.run_id if self.run_id is not None else _API_SENTINEL_RUN_ID
        )

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


def make_httpx_hooks(
    run_id: Optional[int],
    username: Optional[str] = None,
    api_run_id: Optional[int] = None,
) -> dict:
    """Return an httpx event_hooks dict that logs every request/response.

    Pass ``api_run_id`` (with ``run_id=None``) for API-collection runs so traffic
    is keyed on the API column and shows up in the API traffic panel.
    """
    # API runs have no real TestRun row; test_run_id is NOT NULL, so use sentinel 0.
    effective_run_id = run_id if run_id is not None else _API_SENTINEL_RUN_ID
    _pending: dict[int, float] = {}  # id(request) → monotonic start time

    async def on_request(request) -> None:
        _pending[id(request)] = time.monotonic()

    async def on_response(response) -> None:
        start = _pending.pop(id(response.request), None)
        duration_ms = (
            int((time.monotonic() - start) * 1000) if start is not None else None
        )

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
            effective_run_id,
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
            api_run_id,
        )

    return {"request": [on_request], "response": [on_response]}


# ── Playwright BrowserContext handler ─────────────────────────────────────────


def setup_playwright_logging(
    ctx,
    run_id: Optional[int],
    username: Optional[str] = None,
    api_run_id: Optional[int] = None,
) -> None:
    """Register request/response listeners on a Playwright BrowserContext.

    Pass ``api_run_id`` (with ``run_id=None``) for API-collection runs so traffic
    is keyed on the API column and shows up in the API traffic panel.
    """
    # API runs have no real TestRun row; test_run_id is NOT NULL, so use sentinel 0.
    effective_run_id = run_id if run_id is not None else _API_SENTINEL_RUN_ID
    _pending: dict[int, float] = {}
    _req_data: dict[int, dict] = {}

    async def on_request(request) -> None:
        # Skip the same noisy resource types as on_response / on_request_failed.
        # Those handlers return early for SKIP_RESOURCE_TYPES *before* popping, so
        # storing skipped requests here (images/fonts/media — the bulk of browser
        # traffic) would leak _pending/_req_data entries that are never cleaned up.
        if request.resource_type in SKIP_RESOURCE_TYPES:
            return
        # Only store timing and body here.  Full headers are read in on_response
        # via response.request.all_headers(), which is the only point where the
        # browser has finalised cookies, Authorization, and other internally-added
        # headers.  Reading them in on_request captures only what the caller
        # explicitly set, which is why callers were seeing just the host header.
        rid = id(request)
        _pending[rid] = time.monotonic()
        post_data = _safe_playwright_post_data(request)
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
        duration_ms = (
            int((time.monotonic() - start) * 1000) if start is not None else None
        )

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
            post_data = _safe_playwright_post_data(response.request)

        # Use response.body() (raw bytes) — more reliable than response.text().
        # text() can fail if encoding detection breaks or the body is already consumed;
        # body() reads the raw CDP buffer directly.
        try:
            body_bytes = await response.body()
            ct = response.headers.get("content-type", "")
            if any(t in ct for t in ("text", "json", "xml", "html", "javascript")):
                resp_body: Optional[str] = body_bytes.decode(errors="replace")[
                    :BODY_LIMIT
                ]
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
            effective_run_id,
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
            api_run_id,
        )

    async def on_request_failed(request) -> None:
        if request.resource_type in SKIP_RESOURCE_TYPES:
            return

        rid = id(request)
        start = _pending.pop(rid, None)
        req_data = _req_data.pop(rid, {})
        duration_ms = (
            int((time.monotonic() - start) * 1000) if start is not None else None
        )

        try:
            req_headers = await request.all_headers()
        except Exception:
            try:
                req_headers = dict(request.headers)
            except Exception:
                req_headers = {}

        post_data = req_data.get("post_data")
        if post_data is None:
            post_data = _safe_playwright_post_data(request)

        error_text = request.failure or "Request failed"

        await asyncio.to_thread(
            _write,
            effective_run_id,
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
            api_run_id,
        )

    ctx.on("request", on_request)
    ctx.on("response", on_response)
    ctx.on("requestfailed", on_request_failed)
