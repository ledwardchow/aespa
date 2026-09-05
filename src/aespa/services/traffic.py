"""Traffic logging service.

Captures HTTP request/response pairs from both httpx and Playwright,
persists them to the DB, and exposes a polling endpoint for the frontend.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlmodel import Session, func, select

from aespa.db import get_engine

BODY_LIMIT = 8192  # 8 KB per body stored
SKIP_RESOURCE_TYPES = {"image", "font", "media"}  # noisy, rarely useful


def _body_preview(
    data: bytes | None, content_type: str = ""
) -> tuple[Optional[str], Optional[str], int, Optional[str]]:
    """Return a bounded display preview plus byte-level provenance."""
    if not data:
        return None, None, 0, None
    digest = hashlib.sha256(data).hexdigest()
    textual = any(
        marker in content_type.lower()
        for marker in (
            "text",
            "json",
            "xml",
            "html",
            "javascript",
            "x-www-form-urlencoded",
        )
    )
    if not textual and not content_type:
        try:
            decoded = data.decode("utf-8")
            textual = all(char.isprintable() or char in "\r\n\t" for char in decoded)
        except UnicodeDecodeError:
            textual = False
    if textual:
        return data.decode(errors="replace")[:BODY_LIMIT], "text", len(data), digest
    encoded = base64.b64encode(data[:BODY_LIMIT]).decode()
    return encoded, "base64", len(data), digest


# Enabled by the interactive terminal console. Keeping this logger above INFO by
# default prevents scanner payloads from spilling into ordinary server logs.
testing_traffic_log = logging.getLogger("aespa.testing.traffic")
testing_traffic_log.setLevel(logging.WARNING)

# In-memory cache of WAF detections, keyed by (run_kind, run_id), so the
# agentic scan loop can check "is this run behind a WAF?" on every tool call
# without a DB round-trip. Populated as a side effect of _write() below;
# the DB columns (TestRun/ApiTestRun.waf_*) are the durable copy used by the
# UI and across process restarts.
_waf_cache: dict[tuple[str, int], dict] = {}
_waf_cache_hydrated: set[tuple[str, int]] = set()

# The active browser target is tagged on the context while one self-contained
# browser action runs.  This lets asynchronous Playwright listeners persist the
# originating SPA page without depending on Playwright object internals.
_browser_context_tags: dict[
    int, tuple[Optional[int], Optional[str], Optional[str]]
] = {}


def set_browser_context_tag(
    ctx,
    page_id: Optional[int],
    session_label: Optional[str],
    interaction_id: Optional[str] = None,
) -> None:
    _browser_context_tags[id(ctx)] = (page_id, session_label, interaction_id)


def clear_browser_context_tag(ctx) -> None:
    _browser_context_tags.pop(id(ctx), None)


def _browser_context_tag(
    ctx,
) -> tuple[Optional[int], Optional[str], Optional[str]]:
    return _browser_context_tags.get(id(ctx), (None, None, None))


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


def _write(
    run_id: Optional[int],
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
    page_id: Optional[int] = None,
    session_label: Optional[str] = None,
    interaction_id: Optional[str] = None,
    code_execution_id: Optional[int] = None,
    batch_id: Optional[str] = None,
    batch_index: Optional[int] = None,
    agent_id: Optional[str] = None,
    agent_step: Optional[int] = None,
    owasp_category: Optional[str] = None,
    test_class: Optional[str] = None,
    obligation_id: Optional[int] = None,
    request_body_encoding: Optional[str] = None,
    request_body_size: Optional[int] = None,
    request_body_sha256: Optional[str] = None,
    response_body_encoding: Optional[str] = None,
    response_body_size: Optional[int] = None,
    response_body_sha256: Optional[str] = None,
) -> int:
    from aespa.models import TrafficEntry

    with Session(get_engine()) as s:
        entry = TrafficEntry(
            test_run_id=None if api_run_id is not None else run_id,
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
            page_id=page_id,
            session_label=session_label,
            interaction_id=interaction_id,
            code_execution_id=code_execution_id,
            batch_id=batch_id,
            batch_index=batch_index,
            agent_id=agent_id,
            agent_step=agent_step,
            owasp_category=owasp_category,
            test_class=test_class,
            obligation_id=obligation_id,
            request_body_encoding=request_body_encoding,
            request_body_size=request_body_size,
            request_body_sha256=request_body_sha256,
            response_body_encoding=response_body_encoding,
            response_body_size=response_body_size,
            response_body_sha256=response_body_sha256,
        )
        s.add(entry)
        s.flush()
        traffic_id = int(entry.id)
        s.commit()

    testing_traffic_log.info(
        "%s run %s  %s %s  %s",
        "api" if api_run_id is not None else "web",
        api_run_id if api_run_id is not None else run_id,
        method,
        url,
        status if status is not None else "FAILED",
        extra={
            "aespa_testing_traffic_id": traffic_id,
            "aespa_testing_run_kind": "api" if api_run_id is not None else "web",
            "aespa_testing_run_id": (api_run_id if api_run_id is not None else run_id),
            "aespa_testing_source": source,
            "aespa_testing_method": method,
            "aespa_testing_url": url,
            "aespa_testing_status": status,
            "aespa_testing_duration_ms": duration_ms,
            "aespa_testing_username": username,
            "aespa_testing_session_label": session_label,
            "aespa_testing_request_headers": request_headers,
            "aespa_testing_request_body": (request_body or "")[:BODY_LIMIT] or None,
            "aespa_testing_response_headers": response_headers,
            "aespa_testing_response_body": (response_body or "")[:BODY_LIMIT] or None,
        },
    )

    _maybe_record_waf(run_id, api_run_id, url, response_headers, response_body)
    return traffic_id


def _maybe_record_waf(
    run_id: Optional[int],
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

        from aespa.services.scope import authority_is_allowed, scope_authority

        req_authority = scope_authority(url) if url else ""
        if not req_authority:
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

            # Enforce scope check: only attribute a WAF to an in-scope host and port.
            if scope_hosts:
                if not authority_is_allowed(
                    url, scope_hosts, default_url=base_url or url
                ):
                    return
            elif base_url:
                req_hostname = (urlparse(url).hostname or "").lower()
                base_hostname = (urlparse(base_url).hostname or "").lower()
                if base_hostname and (
                    not _same_root_domain(req_hostname, base_hostname)
                    or not authority_is_allowed(url, [base_url], default_url=base_url)
                ):
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
                "page_id": e.page_id,
                "session_label": e.session_label,
                "code_execution_id": e.code_execution_id,
                "batch_id": e.batch_id,
                "batch_index": e.batch_index,
                "agent_id": e.agent_id,
                "agent_step": e.agent_step,
                "owasp_category": e.owasp_category,
                "test_class": e.test_class,
                "obligation_id": e.obligation_id,
                "request_body_encoding": e.request_body_encoding,
                "request_body_size": e.request_body_size,
                "request_body_sha256": e.request_body_sha256,
                "response_body_encoding": e.response_body_encoding,
                "response_body_size": e.response_body_size,
                "response_body_sha256": e.response_body_sha256,
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
        page_id: Optional[int] = None,
        session_label: Optional[str] = None,
        source: str = "httpx",
        provenance: Optional[dict] = None,
        **kwargs,
    ):
        self.run_id = run_id
        self.api_run_id = api_run_id
        self.username = username
        self.page_id = page_id
        self.session_label = session_label
        self.source = source
        self.provenance = dict(provenance or {})
        self.last_traffic_id: Optional[int] = None
        kwargs.pop("event_hooks", None)
        super().__init__(*args, **kwargs)

    async def send(self, request: httpx.Request, *args, **kwargs) -> httpx.Response:
        if self.run_id is None and self.api_run_id is None:
            return await super().send(request, *args, **kwargs)

        # For API runs there is no web TestRun row; _write receives None for
        # that owner and keys the entry on api_test_run_id.
        effective_run_id = self.run_id

        t0 = time.monotonic()
        try:
            response = await super().send(request, *args, **kwargs)
            duration_ms = int((time.monotonic() - t0) * 1000)

            response_bytes: bytes | None = None
            try:
                await response.aread()
                response_bytes = response.content
                ct = response.headers.get("content-type", "")
                resp_body, resp_encoding, resp_size, resp_sha256 = _body_preview(
                    response_bytes, ct
                )
            except Exception as e:
                resp_body = f"[Error reading response body: {e}]"
                resp_encoding, resp_size, resp_sha256 = "text", 0, None

            raw_body = request.content
            req_body, req_encoding, req_size, req_sha256 = _body_preview(
                raw_body or None, request.headers.get("content-type", "")
            )

            self.last_traffic_id = await asyncio.to_thread(
                _write,
                effective_run_id,
                self.source,
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
                self.page_id,
                self.session_label,
                None,
                self.provenance.get("code_execution_id"),
                self.provenance.get("batch_id"),
                self.provenance.get("batch_index"),
                self.provenance.get("agent_id"),
                self.provenance.get("agent_step"),
                self.provenance.get("owasp_category"),
                self.provenance.get("test_class"),
                self.provenance.get("obligation_id"),
                req_encoding,
                req_size,
                req_sha256,
                resp_encoding,
                resp_size,
                resp_sha256,
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
            req_body, req_encoding, req_size, req_sha256 = _body_preview(
                raw_body or None, request.headers.get("content-type", "")
            )

            self.last_traffic_id = await asyncio.to_thread(
                _write,
                effective_run_id,
                self.source,
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
                self.page_id,
                self.session_label,
                None,
                self.provenance.get("code_execution_id"),
                self.provenance.get("batch_id"),
                self.provenance.get("batch_index"),
                self.provenance.get("agent_id"),
                self.provenance.get("agent_step"),
                self.provenance.get("owasp_category"),
                self.provenance.get("test_class"),
                self.provenance.get("obligation_id"),
                req_encoding,
                req_size,
                req_sha256,
                "text",
                None,
                None,
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
    # API runs have no web TestRun row; _write stores NULL in that column.
    effective_run_id = run_id
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
    # API runs have no web TestRun row; _write stores NULL in that column.
    effective_run_id = run_id
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
            *_browser_context_tag(ctx),
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
            *_browser_context_tag(ctx),
        )

    ctx.on("request", on_request)
    ctx.on("response", on_response)
    ctx.on("requestfailed", on_request_failed)
