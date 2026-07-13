from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import sys
from collections import deque
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    AuthMode,
    CrawledPage,
    PageCredentialView,
    PageLink,
    TargetIntelItem,
    TestRun,
    TestRunStatus,
)
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import traffic as traffic_svc
from aespa.services.settings import (
    get_global_http_header_config,
    get_llm_config_for_role,
    get_upstream_proxy_config,
)

log = logging.getLogger("aespa.crawler")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ── In-memory state ───────────────────────────────────────────────────────────

_stop_requested: set[int] = set()
_active_tasks: dict[int, asyncio.Task] = {}

# Guided login registry: credential_id -> asyncio.Event (set by the confirm endpoint)
_guided_registry: dict[int, asyncio.Event] = {}
# Ready registry: credential_id -> asyncio.Event (set by the /ready endpoint after user clicks "I'm Ready")
_guided_ready_registry: dict[int, asyncio.Event] = {}
# Per-run lock: ensures guided logins happen one at a time (no simultaneous browser windows)
_guided_locks: dict[int, asyncio.Lock] = {}
# Captured guided-session cookies/headers keyed by (run_id, credential_id) so reconcile
# can reuse them instead of opening a second browser window.
_guided_session_cache: dict[tuple[int, int], dict] = {}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def request_stop(run_id: int) -> None:
    _stop_requested.add(run_id)
    task = _active_tasks.get(run_id)
    if task and not task.done():
        task.cancel()


def is_running(run_id: int) -> bool:
    return run_id in _active_tasks


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _page_function_label(value: object) -> str | None:
    """Keep model-provided page labels compact enough for graph nodes."""
    label = " ".join(str(value or "").split())
    # A shared CrawledPage is not owned by the credential that discovered it.
    # Recover gracefully if a model nevertheless returns e.g. "Zoe's Accounts".
    label = re.sub(r"^[A-Z][\w-]*[’']s\s+", "", label)
    words = label.split()
    return " ".join(words[:5]) if words else None


def _login_url_for_credential(default_login_url: str, cred) -> str:
    return (getattr(cred, "login_url", None) or default_login_url or "").strip()


# ── Public entry point ────────────────────────────────────────────────────────


async def start_crawl(run_id: int) -> None:
    if run_id in _active_tasks:
        return
    # Tag every event this crawl emits as run_kind='web'.  Run ids collide across
    # web / api / sast, so the scope — snapshotted by create_task below into the
    # crawl task and any worker it spawns — is the authoritative discriminator.
    # Without it, an unscoped agent_status emit for an id that was also a SAST/API
    # run would be mis-tagged and leak into that run's Agents tab.
    with events_svc.run_kind_scope("web"):
        task = asyncio.create_task(_crawl_task(run_id), name=f"crawl-{run_id}")
    _active_tasks[run_id] = task
    task.add_done_callback(lambda _: _active_tasks.pop(run_id, None))


# ── Task wrapper ──────────────────────────────────────────────────────────────


async def _crawl_task(run_id: int) -> None:
    try:
        await _do_crawl(run_id)
    except asyncio.CancelledError:
        log.info("Crawl task cancelled (stop requested) for run_id=%s", run_id)
        with Session(get_engine()) as s:
            run = s.get(TestRun, run_id)
            if run and run.status == TestRunStatus.running:
                run.status = TestRunStatus.stopped
                run.completed_at = _utcnow()
                s.add(run)
                s.commit()
        events_svc.emit(run_id, {"type": "run_update", "status": "stopped"})
        raise
    except Exception as exc:
        with Session(get_engine()) as s:
            run = s.get(TestRun, run_id)
            if run and run.status == TestRunStatus.running:
                run.status = TestRunStatus.failed
                run.error_message = str(exc)[:2000]
                run.completed_at = _utcnow()
                s.add(run)
                s.commit()
    finally:
        _stop_requested.discard(run_id)


# ── Shared state for parallel crawlers ───────────────────────────────────────


class _CrawlShared:
    def __init__(self, crawled_norms: dict, state_keys: dict, pages_done: int) -> None:
        self.crawled_norms: dict[str, int] = crawled_norms  # norm_url → page_id
        self.state_keys: dict[str, int] = state_keys  # SPA interaction fingerprint → page_id
        self.lock: asyncio.Lock = asyncio.Lock()
        self.pages_done: int = pages_done


# ── Progress logging ──────────────────────────────────────────────────────────


def _crawl_log(
    run_id: int,
    phase: str,
    status: str,
    message: str,
    *,
    page_url: str | None = None,
    data: dict | None = None,
) -> None:
    """Emit a user-visible Activity-Log line as a ``scanner_phase`` event.

    These are persisted to ``scan_log`` (events.py) and rendered in the Activity
    Log panel, so the user can follow crawl/auth progress live and after page
    navigation. ``status`` drives the badge suffix in the UI: ``start`` → "…",
    ``complete`` → "✓", ``error`` → "✗"; anything else renders plain.
    Best-effort: never raises. No-op when ``run_id`` is falsy.
    """
    if not run_id:
        return
    try:
        evt: dict = {
            "type": "scanner_phase",
            "phase": phase,
            "status": status,
            "message": message,
        }
        if page_url:
            evt["page_url"] = page_url
        if data is not None:
            evt["data"] = data
        events_svc.emit(run_id, evt)
    except Exception:
        pass


# ── Core orchestrator ─────────────────────────────────────────────────────────


async def _do_crawl(run_id: int) -> None:
    llm_svc.set_run_context(run_id, lambda evt: events_svc.emit(run_id, evt))
    try:
        await _do_crawl_inner(run_id)
    finally:
        llm_svc.clear_run_context()


async def _do_crawl_inner(run_id: int) -> None:
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        from aespa.models import Site

        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config_for_role(s, run, "crawler")
        if llm_cfg is None:
            raise RuntimeError(
                "No LLM configuration found. Configure it in Settings first."
            )
        creds = list(site.credentials)
        upstream_proxy = get_upstream_proxy_config(s)
        crawl_proxy_url = (
            upstream_proxy.proxy_url if upstream_proxy.proxy_scanner else None
        )
        global_header_cfg = get_global_http_header_config(s)
        for obj in [*creds, site, llm_cfg, run]:
            s.expunge(obj)

    _pw_proxy = {"proxy": {"server": crawl_proxy_url}} if crawl_proxy_url else {}
    _global_http_header: dict[str, str] = {}
    if global_header_cfg.header_name and global_header_cfg.header_value:
        _global_http_header = {
            global_header_cfg.header_name: global_header_cfg.header_value
        }
    base_url = _site_base_url(site.base_url)
    login_url = site.login_url or ""
    requires_auth = site.requires_auth
    max_depth = run.max_depth
    max_pages = run.max_pages
    crawler_mode = run.crawler_mode if run.crawler_mode in {"url", "interactive"} else "url"
    _parsed = urlparse(base_url)
    base_netloc = _parsed.netloc
    _bp = _parsed.path
    base_path: str = (_bp if _bp.endswith("/") else _bp + "/") if _bp else "/"

    log.info(
        "=== Crawl start: run_id=%s base_url=%s mode=%s max_depth=%s max_pages=%s creds=%d ===",
        run_id,
        base_url,
        crawler_mode,
        max_depth,
        max_pages,
        len(creds),
    )

    with Session(get_engine()) as s:
        existing = s.exec(
            select(CrawledPage).where(CrawledPage.test_run_id == run_id)
        ).all()
        for ep in existing:
            s.expunge(ep)

    shared = _CrawlShared(
        crawled_norms={_norm(ep.url): ep.id for ep in existing},
        state_keys={ep.state_key: ep.id for ep in existing if ep.state_key},
        pages_done=len(existing),
    )

    _update_run(
        run_id,
        status=TestRunStatus.running,
        started_at=_utcnow(),
        completed_at=None,
        error_message=None,
        pages_discovered=shared.pages_done,
        current_url=base_url,
        per_user_progress=None,
    )
    events_svc.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": "crawler",
            "role": "Crawler",
            "status": "active",
            "current_task": "Crawling application…",
            "outcome": None,
            "_persist": True,
        },
    )
    _crawl_log(
        run_id,
        "crawl",
        "start",
        f"Crawl started — {base_url} "
        f"(max {max_pages} pages, depth {max_depth}, {len(creds)} credential(s))",
        page_url=base_url,
    )

    phases = ([None] + list(creds)) if (requires_auth and creds) else [None]

    tasks = [
        asyncio.create_task(
            _crawl_as_credential(
                run_id=run_id,
                cred=cred,
                shared=shared,
                base_url=base_url,
                login_url=login_url,
                requires_auth=requires_auth,
                max_depth=max_depth,
                max_pages=max_pages,
                crawler_mode=crawler_mode,
                llm_cfg=llm_cfg,
                base_netloc=base_netloc,
                base_path=base_path,
                phase_idx=idx,
                total_phases=len(phases),
                pw_proxy=_pw_proxy,
                global_http_header=_global_http_header,
            ),
            name=f"crawl-{run_id}-cred{idx}",
        )
        for idx, cred in enumerate(phases)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            log.error("Crawl task raised: %s", r)

    await _reconcile_direct_access(
        run_id=run_id,
        creds=creds,
        base_url=base_url,
        login_url=login_url,
        requires_auth=requires_auth,
        llm_cfg=llm_cfg,
        pw_proxy=_pw_proxy,
        global_http_header=_global_http_header,
    )

    # OR-merge page categories from all credential views into each CrawledPage.
    _merge_all_categories(run_id)

    # Seed the workprogram now that we have the full page list + OWASP categories.
    if run_id not in _stop_requested:
        from aespa.services.web_workprogram import (
            seed_web_workprogram,
        )  # ponytail: local import avoids circular

        try:
            seeded = seed_web_workprogram(run_id)
            log.info(
                "workprogram seeded after crawl: run_id=%s cells=%d", run_id, seeded
            )
        except Exception:
            log.warning(
                "workprogram seed failed after crawl (non-fatal)", exc_info=True
            )

    final_status = (
        TestRunStatus.stopped if run_id in _stop_requested else TestRunStatus.complete
    )
    log.info(
        "=== Crawl done: run_id=%s status=%s pages=%d ===",
        run_id,
        final_status,
        shared.pages_done,
    )
    _update_run(
        run_id,
        status=final_status,
        completed_at=_utcnow(),
        current_url=None,
        pages_discovered=shared.pages_done,
    )
    _crawl_log(
        run_id,
        "crawl",
        "error" if final_status == TestRunStatus.stopped else "complete",
        (
            f"Crawl stopped — {shared.pages_done} page(s) discovered"
            if final_status == TestRunStatus.stopped
            else f"Crawl complete — {shared.pages_done} page(s) discovered"
        ),
    )
    # Clean up the per-run lock (small object). The session cache is intentionally
    # kept alive so the dynamic scan phase (same run_id) can reuse guided sessions.
    _guided_locks.pop(run_id, None)
    events_svc.emit(
        run_id,
        {
            "type": "run_update",
            "status": final_status,
            "pages_discovered": shared.pages_done,
            "current_url": None,
        },
    )
    events_svc.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": "crawler",
            "role": "Crawler",
            "status": "complete",
            "current_task": "Crawl complete",
            "outcome": f"{shared.pages_done} page(s) discovered",
            "_persist": True,
        },
    )


# ── Per-credential BFS ────────────────────────────────────────────────────────


async def _crawl_as_credential(
    *,
    run_id: int,
    cred,
    shared: _CrawlShared,
    base_url: str,
    login_url: str,
    requires_auth: bool,
    max_depth: int,
    max_pages: int,
    crawler_mode: str,
    llm_cfg,
    base_netloc: str,
    base_path: str,
    phase_idx: int,
    total_phases: int,
    pw_proxy: dict,
    global_http_header: dict[str, str],
) -> None:
    from playwright.async_api import async_playwright

    username = cred.username if cred else "unauthenticated"
    credential_id = cred.id if cred else None
    credential_login_url = _login_url_for_credential(login_url, cred)

    log.info(
        "=== Phase %d/%d: user=%s ===",
        phase_idx + 1,
        total_phases,
        username or "anonymous",
    )
    events_svc.emit(
        run_id,
        {
            "type": "crawl_phase",
            "phase": phase_idx + 1,
            "total_phases": total_phases,
            "username": username,
        },
    )
    _crawl_log(
        run_id,
        "crawl",
        "info",
        f"Phase {phase_idx + 1}/{total_phases}: crawling as {username}",
    )

    local_pages = 0  # pages actually navigated to by this credential

    async with async_playwright() as p:
        # <-loopback> removes Chromium's default proxy bypass for localhost so
        # loopback-target traffic reaches Burp/ZAP when a proxy is configured.
        _args = ["--proxy-bypass-list=<-loopback>"] if pw_proxy else []
        browser = await p.chromium.launch(headless=True, args=_args)
        ctx = await browser.new_context(
            user_agent=_UA,
            ignore_https_errors=True,
            **pw_proxy,
        )
        if global_http_header:
            await ctx.set_extra_http_headers(global_http_header)
        traffic_svc.setup_playwright_logging(ctx, run_id, username=username)
        page = await ctx.new_page()
        observed_api_calls: list[dict] = []
        auth_check_snapshot: dict | None = None

        async def _record_api_response(response) -> None:
            try:
                # Stamp the page this call fired on *synchronously*, before the
                # body await below. A slow `response.text()` can otherwise resolve
                # after the crawl has moved to the next URL, and the call would be
                # attributed to that page instead. (See the promote step.)
                page_url = page.url
                if not _same_domain(response.url, base_netloc):
                    return
                resource_type = response.request.resource_type
                content_type = response.headers.get("content-type", "")
                if not _is_api_response_candidate(
                    response.url, resource_type, content_type
                ):
                    return
                body = ""
                if _response_body_is_text(content_type):
                    try:
                        body = (await response.text())[:10_000]
                    except Exception:
                        body = ""
                try:
                    request_headers = await response.request.all_headers()
                except Exception:
                    request_headers = dict(response.request.headers)
                try:
                    response_headers = dict(response.headers)
                except Exception:
                    response_headers = {}
                observed_api_calls.append(
                    {
                        "url": response.url,
                        "method": response.request.method,
                        "request_headers": request_headers,
                        "request_body": response.request.post_data,
                        "status": response.status,
                        "content_type": content_type,
                        "response_headers": response_headers,
                        "body": body,
                        "page_url": page_url,
                    }
                )
            except Exception as exc:
                log.debug("API response collection failed: %s", exc)

        page.on("response", _record_api_response)

        await _best_effort_preload(page, base_url, username)
        if phase_idx == 0:
            await _mine_public_assets(
                run_id=run_id,
                page=page,
                base_url=base_url,
                base_netloc=base_netloc,
            )

        if requires_auth and cred:
            log.info("Authenticating as %s at %s", cred.username, credential_login_url)
            await _authenticate(
                page, credential_login_url, cred, run_id, llm_cfg=llm_cfg
            )
            auth_check_snapshot = await _capture_auth_check_snapshot(
                page, credential_login_url
            )

        observed_api_calls.clear()

        queued: set[str] = {_norm(base_url)}
        queue: deque[tuple[str, int, Optional[int]]] = deque([(base_url, 0, None)])

        while queue:
            if run_id in _stop_requested:
                break

            url, depth, parent_id = queue.popleft()
            norm = _norm(url)

            if requires_auth and _is_session_ending_url(url):
                log.info("Skipping session-ending URL during crawl: %s", url)
                continue

            # ── Reserve or look up page in shared state ───────────────────────
            page_id: int
            is_first: bool
            async with shared.lock:
                if norm in shared.crawled_norms:
                    page_id = shared.crawled_norms[norm]
                    is_first = False
                elif depth > max_depth:
                    continue
                elif shared.pages_done >= max_pages:
                    # max_pages caps the total number of distinct site-map nodes
                    # (shared across every phase), so the node count never exceeds
                    # it. Already-known URLs above still fall through so each phase
                    # can record its own access view of them. Same global cap the
                    # API-page promotion path uses (_promote_api_calls).
                    continue
                else:
                    page_id = _save_page_placeholder(run_id, url, depth)
                    shared.crawled_norms[norm] = page_id
                    shared.pages_done += 1
                    is_first = True

            local_pages += 1
            _update_run(run_id, current_url=url, pages_discovered=shared.pages_done)
            # Write the intended URL into per_user_progress immediately so the
            # polling API response reflects what the crawler is currently visiting.
            _update_credential_progress(run_id, username, url, local_pages)
            events_svc.emit(
                run_id,
                {
                    "type": "crawl_progress",
                    "username": username,
                    "pages_visited": local_pages,
                    "current_url": url,
                },
            )

            # ── Navigate ──────────────────────────────────────────────────────
            try:
                resp = await _goto_with_auth_recovery(
                    page,
                    url,
                    requires_auth=requires_auth,
                    credential=cred,
                    login_url=credential_login_url,
                    username=username,
                    auth_check_snapshot=auth_check_snapshot,
                    run_id=run_id,
                    llm_cfg=llm_cfg,
                )
            except Exception as nav_err:
                if is_first:
                    _update_page(
                        page_id, status="failed", error_message=str(nav_err)[:500]
                    )
                continue

            if resp is not None and resp.status >= 400:
                if is_first:
                    _update_page(
                        page_id, status="failed", error_message=f"HTTP {resp.status}"
                    )
                continue

            # ── SPA URL guard + redirect deduplication ────────────────────────
            raw_final = page.url
            if _same_domain(raw_final, base_netloc) and not _in_base_scope(
                raw_final, base_netloc, base_path
            ):
                final_url = url
            else:
                final_url = raw_final

            norm_final = _norm(final_url)
            if norm_final != norm:
                async with shared.lock:
                    if norm_final in shared.crawled_norms:
                        existing_id = shared.crawled_norms[norm_final]
                        if is_first:
                            _update_page(page_id, status="redirect")
                            shared.crawled_norms[norm] = existing_id
                            shared.pages_done -= 1
                        page_id = existing_id
                        is_first = False
                    elif is_first:
                        _update_page(page_id, url=final_url)
                        shared.crawled_norms[norm_final] = page_id

            # ── DOM-based accessibility check (login form = not accessible) ───
            on_login = await _page_requires_login(page, credential_login_url)

            if on_login:
                if is_first:
                    _update_page(page_id, status="crawled")
                log.debug(
                    "  Login form for %s (user=%s) — inaccessible", final_url, username
                )
                continue

            # ── Content extraction ────────────────────────────────────────────
            # Settle: let client-rendered content paint before snapshotting.
            # Returns instantly once the DOM has text or links (static pages);
            # an SPA waits only as long as it needs, capped well under the old
            # flat 2s. ponytail: content signal beats a fixed sleep.
            try:
                await page.wait_for_function(
                    "() => document.body && ("
                    "document.body.innerText.trim().length > 0 || "
                    "document.querySelector('a[href]'))",
                    timeout=2000,
                )
            except Exception:
                pass
            title = await page.title()
            try:
                text = await page.evaluate("() => document.body.innerText")
            except Exception:
                text = ""

            screenshot_b64: Optional[str] = None
            try:
                raw = await page.screenshot(type="png", full_page=False)
                screenshot_b64 = base64.b64encode(raw).decode()
            except Exception:
                pass

            try:
                raw_links: list[dict] = await page.evaluate(
                    """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                        href: a.href,
                        text: (a.textContent || '').trim().slice(0, 80)
                    }))"""
                )
            except Exception:
                raw_links = []

            same_domain_links = [
                (r["href"], r["text"])
                for r in raw_links
                if _same_domain(r["href"], base_netloc)
            ]
            await _record_page_intelligence(
                run_id=run_id,
                page=page,
                page_url=final_url,
                text=text,
                raw_links=raw_links,
                base_netloc=base_netloc,
                username=username,
            )

            # ── LLM analysis ──────────────────────────────────────────────────
            cats: dict = {
                "req_auth": None,
                "takes_input": None,
                "has_object_ref": None,
                "has_business_logic": None,
            }
            context = ""
            suggested: list[str] = []
            if _is_api_page(final_url, text):
                context = "[API endpoint — LLM analysis skipped]"
            else:
                try:
                    context, suggested, cats = await llm_svc.analyse_page(
                        llm_cfg, final_url, title, text[:8000], screenshot_b64
                    )
                    log.info(
                        "  LLM ok for %s (user=%s) cats=%s", final_url, username, cats
                    )
                except Exception as e:
                    log.warning("  LLM failed for %s: %s", final_url, e)
                    context = f"[LLM failed: {e}]"

            # ── Persist per-credential view ───────────────────────────────────
            _save_credential_view(
                page_id,
                run_id,
                credential_id,
                username,
                screenshot_b64,
                context,
                text[:10_000],
                cats,
            )
            _update_accessible_by(page_id, credential_id)

            # ── Update main CrawledPage if first to fill it ───────────────────
            with Session(get_engine()) as s:
                cp = s.get(CrawledPage, page_id)
                fill_main = (
                    cp is not None
                    and cp.status in ("processing", "crawled")
                    and not cp.title
                )
                first_success = cp is not None and cp.status == "processing"

            if is_first or fill_main:
                _update_page(
                    page_id,
                    url=final_url,
                    state_label=_page_function_label(cats.get("page_label")),
                    title=title,
                    page_text=text[:10_000],
                    screenshot_b64=screenshot_b64,
                    llm_context=context,
                    status="crawled",
                    depth=depth,
                    req_auth=cats["req_auth"],
                    takes_input=cats["takes_input"],
                    has_object_ref=cats["has_object_ref"],
                    has_business_logic=cats["has_business_logic"],
                    owasp_applicable_json=json.dumps(
                        cats.get("owasp_applicable") or {}
                    ),
                )
                if is_first:
                    _save_link(run_id, parent_id, page_id, final_url)

            # ── SSE ───────────────────────────────────────────────────────────
            with Session(get_engine()) as s:
                cp = s.get(CrawledPage, page_id)
                ab = json.loads(cp.accessible_by if cp else "[]")

            if is_first or first_success:
                events_svc.emit(
                    run_id,
                    {
                        "type": "page_added",
                        "username": username,
                        "node": {
                            "id": page_id,
                            "url": final_url,
                            "state_label": _page_function_label(cats.get("page_label")),
                            "title": title,
                            "depth": depth,
                            "status": "crawled",
                            "context": context,
                            "in_scope": True,
                            "scan_status": "pending",
                            "accessible_by": ab,
                        },
                        "link": {
                            "source": parent_id,
                            "target": page_id,
                            "link_text": None,
                        }
                        if parent_id
                        else None,
                    },
                )
            else:
                events_svc.emit(
                    run_id,
                    {
                        "type": "node_accessible_by",
                        "page_id": page_id,
                        "username": username,
                    },
                )

            events_svc.emit(
                run_id,
                {
                    "type": "run_update",
                    "status": "running",
                    "pages_discovered": shared.pages_done,
                    "current_url": final_url,
                    "username": username,
                },
            )

            # ── Enqueue links ─────────────────────────────────────────────────
            # Promote only the API calls captured while THIS page was loaded
            # (matched by the page stamp recorded when each response fired). A
            # straggler from a previous page — whose body download finished late —
            # carries that page's stamp and is dropped here rather than being
            # misattributed to the current page. Snapshot + clear is atomic w.r.t.
            # the event loop (no await between), so concurrent response handlers
            # can't lose an append. ``norm``/``norm_final`` cover the page's
            # requested and post-redirect URLs.
            page_norms = {norm, norm_final}
            page_calls = [
                c
                for c in observed_api_calls
                if _norm(c.get("page_url") or "") in page_norms
            ]
            observed_api_calls.clear()
            await _promote_api_calls(
                run_id=run_id,
                calls=page_calls,
                source_page_id=page_id,
                source_depth=depth,
                shared=shared,
                max_pages=max_pages,
                credential_id=credential_id,
                username=username,
                llm_cfg=llm_cfg,
            )

            # URL crawling intentionally remains the default. In interactive
            # mode, safely explore client-side views rooted at this document.
            # This runs after API-call promotion so replay traffic is not
            # attributed to the URL page currently being processed.
            if crawler_mode == "interactive" and depth < max_depth:
                await _explore_interactive_states(
                    run_id=run_id,
                    page=page,
                    root_url=final_url,
                    root_page_id=page_id,
                    root_depth=depth,
                    shared=shared,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    credential_id=credential_id,
                    username=username,
                    llm_cfg=llm_cfg,
                    base_netloc=base_netloc,
                )

            if depth < max_depth:
                filtered_suggested = _filter_suggested_links(
                    suggested, same_domain_links, base_netloc
                )
                if len(filtered_suggested) < len(suggested):
                    log.info(
                        "Dropped %d LLM-suggested crawl URL(s) that were not observed as page links for %s",
                        len(suggested) - len(filtered_suggested),
                        final_url,
                    )
                for sugg_url in reversed(filtered_suggested):
                    n = _norm(sugg_url)
                    if (
                        n not in queued
                        and _same_domain(sugg_url, base_netloc)
                        and not _is_session_ending_url(sugg_url)
                    ):
                        queued.add(n)
                        queue.appendleft((sugg_url, depth + 1, page_id))
                for link_url, link_text in same_domain_links:
                    n = _norm(link_url)
                    if (
                        n not in queued
                        and _same_domain(link_url, base_netloc)
                        and not _is_session_ending_url(link_url, link_text)
                    ):
                        queued.add(n)
                        queue.append((link_url, depth + 1, page_id))

        await browser.close()

    _update_credential_progress(run_id, username, None, local_pages, done=True)
    events_svc.emit(
        run_id,
        {
            "type": "crawl_progress",
            "username": username,
            "pages_visited": local_pages,
            "current_url": None,
            "done": True,
        },
    )
    _crawl_log(
        run_id,
        "crawl",
        "complete",
        f"Finished crawling as {username} — {local_pages} page(s)",
    )


# ── Interactive SPA state discovery ──────────────────────────────────────────

_INTERACTIVE_ACTION_LIMIT = 12
_INTERACTIVE_DANGER_RE = re.compile(
    r"\b(?:delete|remove|destroy|logout|log\s*out|sign\s*out|purchase|pay|checkout|"
    r"transfer|send\s+money|revoke|cancel\s+subscription)\b",
    re.IGNORECASE,
)


async def _interactive_controls(page) -> list[dict]:
    """Return conservative, navigation-like controls with replayable locators.

    Forms and destructive-looking controls are deliberately excluded. This is a
    discovery feature, not permission to execute business actions.
    """
    try:
        controls = await page.evaluate(
            """() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
                && getComputedStyle(el).visibility !== 'hidden';
              const candidates = Array.from(document.querySelectorAll(
                'button, [role="button"], [role="tab"], [role="menuitem"], summary, [aria-haspopup="dialog"]'
              ));
              return candidates.filter(el => visible(el) && !el.disabled && !el.closest('form')).slice(0, 80).map(el => {
                const tag = el.tagName.toLowerCase();
                const role = el.getAttribute('role') || (tag === 'summary' ? 'button' : 'button');
                const name = (el.getAttribute('aria-label') || el.innerText || el.textContent || '')
                  .replace(/\\s+/g, ' ').trim().slice(0, 80);
                const testid = el.getAttribute('data-testid') || el.getAttribute('data-test') || null;
                return {role, name, testid, expanded: el.getAttribute('aria-expanded'), selected: el.getAttribute('aria-selected')};
              });
            }"""
        )
    except Exception:
        return []
    unique: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for control in controls or []:
        role = str(control.get("role") or "button")
        name = str(control.get("name") or "").strip()
        testid = str(control.get("testid") or "")
        if not name or _INTERACTIVE_DANGER_RE.search(name):
            continue
        key = (role, name, testid)
        if key in seen:
            continue
        seen.add(key)
        unique.append({
            "role": role,
            "name": name,
            "testid": testid or None,
            "selector": _interactive_selector(role, name, testid),
        })
        if len(unique) >= _INTERACTIVE_ACTION_LIMIT:
            break
    return unique


def _interactive_selector(role: str, name: str, testid: str) -> str:
    """Produce the Playwright selector persisted in a replay recipe."""
    if testid:
        return f'[data-testid={json.dumps(testid)}]'
    escaped_name = json.dumps(name)
    if role == "tab":
        return f'[role="tab"]:has-text({escaped_name})'
    if role == "menuitem":
        return f'[role="menuitem"]:has-text({escaped_name})'
    return f'button:has-text({escaped_name}), [role="button"]:has-text({escaped_name})'


async def _replay_interactive_steps(page, steps: list[dict]) -> bool:
    for step in steps:
        try:
            if step.get("selector"):
                locator = page.locator(step["selector"])
            elif step.get("testid"):
                locator = page.get_by_test_id(step["testid"])
            else:
                locator = page.get_by_role(step.get("role") or "button", name=step.get("name") or "", exact=True)
            if await locator.count() < 1:
                return False
            await locator.first.click(timeout=4_000)
            try:
                await page.wait_for_timeout(200)
                await page.wait_for_load_state("domcontentloaded", timeout=2_000)
            except Exception:
                pass
        except Exception:
            return False
    return True


async def _interactive_state_snapshot(page) -> dict | None:
    try:
        raw = await page.evaluate(
            """() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
                && getComputedStyle(el).visibility !== 'hidden';
              const text = el => (el.getAttribute('aria-label') || el.innerText || el.textContent || '')
                .replace(/\\s+/g, ' ').trim().slice(0, 100);
              const pick = selector => Array.from(document.querySelectorAll(selector)).filter(visible).slice(0, 20).map(text);
              return {
                headings: pick('h1,h2,h3,[role="heading"]'),
                dialogs: pick('[role="dialog"],[aria-modal="true"]'),
                forms: Array.from(document.forms).filter(visible).slice(0, 12).map(f =>
                  Array.from(f.querySelectorAll('input,textarea,select')).map(el => el.name || el.type || el.id).join('|')),
                controls: Array.from(document.querySelectorAll('button,[role="button"],[role="tab"],[role="menuitem"]'))
                  .filter(visible).slice(0, 30).map(el => `${el.getAttribute('role') || el.tagName}:${text(el)}:${el.getAttribute('aria-selected') || ''}`),
                title: document.title || '',
              };
            }"""
        )
        text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        title = await page.title()
        normalized = re.sub(r"\b\d{2,}\b", "#", json.dumps(raw, sort_keys=True))
        state_key = "spa:" + _norm(page.url) + ":" + hashlib.sha256(normalized.encode()).hexdigest()[:24]
        label = next(iter(raw.get("dialogs") or []), "") or next(iter(raw.get("headings") or []), "") or title or "Interactive view"
        screenshot_b64 = None
        try:
            screenshot_b64 = base64.b64encode(await page.screenshot(type="png", full_page=False)).decode()
        except Exception:
            pass
        return {"key": state_key, "label": str(label)[:160], "title": title, "text": text or "", "screenshot_b64": screenshot_b64}
    except Exception:
        return None


async def _explore_interactive_states(
    *, run_id: int, page, root_url: str, root_page_id: int, root_depth: int,
    shared: _CrawlShared, max_depth: int, max_pages: int, credential_id: Optional[int],
    username: Optional[str], llm_cfg, base_netloc: str,
) -> None:
    """Breadth-first exploration of safe client-side states beneath one URL page."""
    pending: deque[tuple[list[dict], int, int]] = deque([([], root_page_id, root_depth)])
    seen_recipes: set[str] = set()
    while pending and run_id not in _stop_requested:
        steps, parent_id, state_depth = pending.popleft()
        if steps:
            try:
                await page.goto(root_url, wait_until="domcontentloaded", timeout=15_000)
            except Exception:
                continue
            if not await _replay_interactive_steps(page, steps):
                continue
            snapshot = await _interactive_state_snapshot(page)
            if not snapshot or not _same_domain(page.url, base_netloc):
                continue
            async with shared.lock:
                page_id = shared.state_keys.get(snapshot["key"])
                is_new = page_id is None
                if is_new:
                    if shared.pages_done >= max_pages:
                        continue
                    page_id = _save_page_placeholder(run_id, page.url, state_depth)
                    shared.state_keys[snapshot["key"]] = page_id
                    shared.pages_done += 1
            action = steps[-1]
            _save_link(
                run_id, parent_id, page_id, page.url, link_text=action["name"],
                action_kind="click", action_data={"replay_steps": steps},
            )
            if is_new:
                context = "[Interactive SPA state reached by replay]"
                cats = {"req_auth": None, "takes_input": None, "has_object_ref": None, "has_business_logic": None}
                try:
                    context, _unused, cats = await llm_svc.analyse_page(
                        llm_cfg, page.url, snapshot["title"], snapshot["text"][:8000], snapshot["screenshot_b64"]
                    )
                except Exception as exc:
                    log.debug("Interactive state analysis failed: %s", exc)
                page_label = _page_function_label(cats.get("page_label")) or snapshot["label"]
                _update_page(
                    page_id, url=page.url, state_key=snapshot["key"], state_label=page_label,
                    state_kind="interactive", replay_steps_json=json.dumps(steps), title=snapshot["title"],
                    page_text=snapshot["text"][:10_000], screenshot_b64=snapshot["screenshot_b64"],
                    llm_context=context, status="crawled", depth=state_depth,
                    req_auth=cats.get("req_auth"), takes_input=cats.get("takes_input"),
                    has_object_ref=cats.get("has_object_ref"), has_business_logic=cats.get("has_business_logic"),
                    owasp_applicable_json=json.dumps(cats.get("owasp_applicable") or {}),
                )
                _update_run(run_id, pages_discovered=shared.pages_done)
                events_svc.emit(run_id, {"type": "page_added", "username": username, "node": {
                    "id": page_id, "url": page.url, "state_label": page_label, "state_kind": "interactive",
                    "title": snapshot["title"], "depth": state_depth, "status": "crawled", "context": context,
                    "in_scope": True, "scan_status": "pending", "accessible_by": [credential_id] if credential_id else [],
                }, "link": {"source": parent_id, "target": page_id, "link_text": action["name"], "action_kind": "click"}})
            _save_credential_view(page_id, run_id, credential_id, username, snapshot["screenshot_b64"],
                                  "[Interactive SPA state]", snapshot["text"][:10_000], {})
            _update_accessible_by(page_id, credential_id)
            current_id = page_id
        else:
            current_id = root_page_id

        if state_depth >= max_depth:
            continue
        for action in await _interactive_controls(page):
            recipe = steps + [action]
            recipe_key = json.dumps(recipe, sort_keys=True)
            if recipe_key not in seen_recipes:
                seen_recipes.add(recipe_key)
                pending.append((recipe, current_id, state_depth + 1))


# ── DB helpers ────────────────────────────────────────────────────────────────


def _save_page_placeholder(run_id: int, url: str, depth: int) -> int:
    """Atomically create a stub CrawledPage and return its ID."""
    from aespa.services.scope import register_scope_host_for_run

    with Session(get_engine()) as s:
        cp = CrawledPage(
            test_run_id=run_id,
            url=url,
            depth=depth,
            status="processing",
            accessible_by="[]",
        )
        s.add(cp)
        s.commit()
        s.refresh(cp)
        s.expunge(cp)
    # Fire-and-forget: doesn't matter if this fails
    try:
        register_scope_host_for_run(run_id, url)
    except Exception:
        pass
    return cp.id


def _update_page(page_id: int, **kwargs) -> None:
    with Session(get_engine()) as s:
        cp = s.get(CrawledPage, page_id)
        if cp is None:
            return
        for k, v in kwargs.items():
            setattr(cp, k, v)
        s.add(cp)
        s.commit()


def _save_credential_view(
    page_id: int,
    run_id: int,
    credential_id: Optional[int],
    username: Optional[str],
    screenshot_b64: Optional[str],
    llm_context: Optional[str],
    page_text: Optional[str],
    cats: dict,
) -> None:
    owasp_json = json.dumps(cats.get("owasp_applicable") or {})
    with Session(get_engine()) as s:
        existing = s.exec(
            select(PageCredentialView)
            .where(PageCredentialView.page_id == page_id)
            .where(PageCredentialView.test_run_id == run_id)
            .where(PageCredentialView.credential_id == credential_id)
        ).first()
        if existing:
            existing.username = username
            existing.screenshot_b64 = screenshot_b64
            existing.llm_context = llm_context
            existing.page_text = page_text
            existing.req_auth = cats.get("req_auth")
            existing.takes_input = cats.get("takes_input")
            existing.has_object_ref = cats.get("has_object_ref")
            existing.has_business_logic = cats.get("has_business_logic")
            existing.owasp_applicable_json = owasp_json
            s.add(existing)
            s.commit()
            return
        view = PageCredentialView(
            page_id=page_id,
            test_run_id=run_id,
            credential_id=credential_id,
            username=username,
            screenshot_b64=screenshot_b64,
            llm_context=llm_context,
            page_text=page_text,
            req_auth=cats.get("req_auth"),
            takes_input=cats.get("takes_input"),
            has_object_ref=cats.get("has_object_ref"),
            has_business_logic=cats.get("has_business_logic"),
            owasp_applicable_json=owasp_json,
        )
        s.add(view)
        s.commit()


# ── Target intelligence collection ───────────────────────────────────────────

_ENDPOINT_RE = re.compile(
    r"""(?P<quote>['"`])(?P<path>(?:https?://[^'"`\s<>]+|/(?:api|admin|auth|graphql|v\d+|[\w.-]+/)[^'"`\s<>]*))(?P=quote)"""
)
_FETCH_CALL_RE = re.compile(
    r"\b(?:fetch|axios(?:\.(?P<axios_method>get|post|put|patch|delete|head|options))?)\s*\(\s*(?P<quote>['\"`])(?P<url>https?://[^'\"`\s<>]+|/[^'\"`\s<>]+)(?P=quote)(?P<args>[\s\S]{0,500}?)\)",
    re.IGNORECASE,
)
_AXIOS_OBJECT_RE = re.compile(
    r"\baxios\s*\(\s*\{(?P<object>[\s\S]{0,900}?)\}\s*\)",
    re.IGNORECASE,
)
_ROUTE_LITERAL_RE = re.compile(
    r"(?:path|route|url|href|to)\s*[:=]\s*(['\"`])(?P<path>/[^'\"`\s<>]+)\1",
    re.IGNORECASE,
)
_STORAGE_ACCESS_RE = re.compile(
    r"\b(?:localStorage|sessionStorage)\s*\.\s*(?:getItem|setItem|removeItem)\s*\(\s*(['\"`])(?P<key>[^'\"`]{1,120})\1",
    re.IGNORECASE,
)
_FEATURE_FLAG_RE = re.compile(
    r"(['\"`])(?P<key>(?:feature|flag|enable|disable|beta|experimental|admin)[A-Za-z0-9_.:-]{2,100})\1\s*[:=]\s*(?P<value>true|false|['\"`][^'\"`]{0,120}['\"`]|\d+)",
    re.IGNORECASE,
)
_JWT_STORAGE_KEY_RE = re.compile(
    r"\b(?:access[_-]?token|auth[_-]?token|id[_-]?token|jwt|bearer|session[_-]?token)\b",
    re.IGNORECASE,
)
_INTERESTING_FIELD_RE = re.compile(
    r"\b(?:password_hash|passwd|totp_secret|jwt_secret|secret|api_key|debug|stack|trace|role|is_admin)\b",
    re.IGNORECASE,
)
_SOURCE_MAPPING_RE = re.compile(r"sourceMappingURL=([^\s*]+)")
_PUBLIC_ASSET_PATHS = (
    "/robots.txt",
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/manifest.json",
    "/asset-manifest.json",
    "/.well-known/security.txt",
    "/openapi.json",
    "/swagger.json",
    "/api/openapi.json",
    "/api/swagger.json",
    "/config.json",
    "/api/config",
    "/api/health",
    "/health",
    "/status",
    "/api/status",
)
_ADMIN_PATH_RE = re.compile(
    r"/(?:admin|manage|management|moderator|staff|backoffice|internal|superuser)(?:[/?.#-]|$)",
    re.IGNORECASE,
)
_VALIDATION_PATH_RE = re.compile(
    r"/(?:validate|verify|verification|check|preflight|csrf|captcha|otp|mfa|2fa)(?:[/?.#-]|$)",
    re.IGNORECASE,
)
_AUTH_PATH_RE = re.compile(
    r"/(?:login|logout|signup|register|auth|token|session|password|reset)(?:[/?.#-]|$)",
    re.IGNORECASE,
)


def _save_intel_item(
    *,
    run_id: int,
    kind: str,
    key: str,
    value: str = "",
    url: str | None = None,
    method: str | None = None,
    source: str = "crawler",
    confidence: float = 1.0,
    evidence: str = "",
    metadata: dict | None = None,
) -> None:
    key = str(key or "")[:500]
    value = str(value or "")[:2000]
    evidence = str(evidence or "")[:2000]
    method = method.upper() if method else None
    metadata_text = json.dumps(metadata or {}, separators=(",", ":"), default=str)[
        :4000
    ]
    with Session(get_engine()) as s:
        existing = s.exec(
            select(TargetIntelItem)
            .where(TargetIntelItem.test_run_id == run_id)
            .where(TargetIntelItem.kind == kind)
            .where(TargetIntelItem.key == key)
            .where(TargetIntelItem.value == value)
            .where(TargetIntelItem.url == url)
            .where(TargetIntelItem.method == method)
            .where(TargetIntelItem.source == source)
        ).first()
        if existing:
            return
        s.add(
            TargetIntelItem(
                test_run_id=run_id,
                kind=kind,
                key=key,
                value=value,
                url=url,
                method=method,
                source=source,
                confidence=max(0.0, min(1.0, float(confidence))),
                evidence=evidence,
                item_metadata=metadata_text,
            )
        )
        s.commit()


async def _record_page_intelligence(
    *,
    run_id: int,
    page,
    page_url: str,
    text: str,
    raw_links: list[dict],
    base_netloc: str,
    username: Optional[str],
) -> None:
    """Extract durable target inventory facts from a rendered page."""
    for item in _extract_ids_from_text(text):
        _save_intel_item(
            run_id=run_id,
            kind="id",
            key=item["key"],
            value=item["value"],
            url=page_url,
            source="page_text",
            evidence=item["evidence"],
            metadata={"username": username},
        )

    for link in raw_links[:300]:
        href = str(link.get("href") or "")
        if not href or not _same_domain(href, base_netloc):
            continue
        _save_intel_item(
            run_id=run_id,
            kind="endpoint",
            key=_path_key(href),
            value=href,
            url=page_url,
            method="GET",
            source="dom_link",
            evidence=str(link.get("text") or "")[:200],
            metadata={"username": username},
        )

    dom = await _extract_dom_intelligence(page)
    for script_url in dom["scripts"]:
        if not _same_domain(script_url, base_netloc):
            continue
        _save_intel_item(
            run_id=run_id,
            kind="script",
            key=_path_key(script_url),
            value=script_url,
            url=page_url,
            method="GET",
            source="dom_script",
            metadata={"username": username},
        )

    for asset_url in dom["assets"]:
        if not _same_domain(asset_url, base_netloc):
            continue
        _save_intel_item(
            run_id=run_id,
            kind="asset",
            key=_path_key(asset_url),
            value=asset_url,
            url=page_url,
            method="GET",
            source="dom_asset",
            metadata={"username": username},
        )

    for form in dom["forms"]:
        form_url = form.get("action") or page_url
        method = str(form.get("method") or "GET").upper()
        fields = form.get("fields") or []
        _save_intel_item(
            run_id=run_id,
            kind="form",
            key=_path_key(form_url),
            value=str(form.get("selector") or ""),
            url=form_url,
            method=method,
            source="dom_form",
            evidence=", ".join(
                f.get("name") or f.get("id") or f.get("type") or "field"
                for f in fields[:12]
            ),
            metadata={"page_url": page_url, "fields": fields, "username": username},
        )
        for field in fields:
            field_key = str(
                field.get("name") or field.get("id") or field.get("selector") or ""
            )
            if not field_key:
                continue
            _save_intel_item(
                run_id=run_id,
                kind="input",
                key=field_key,
                value=str(field.get("type") or ""),
                url=form_url,
                method=method,
                source="dom_form",
                metadata={
                    "page_url": page_url,
                    "form_selector": form.get("selector"),
                    "username": username,
                },
            )

    for key in dom["storage_keys"]:
        _save_intel_item(
            run_id=run_id,
            kind="storage_key",
            key=key,
            value=key,
            url=page_url,
            source="browser_storage",
            confidence=0.9 if _JWT_STORAGE_KEY_RE.search(key) else 0.7,
            metadata={"username": username},
        )

    await _mine_script_intelligence(
        run_id=run_id,
        page=page,
        page_url=page_url,
        script_urls=dom["scripts"],
        base_netloc=base_netloc,
    )


async def _extract_dom_intelligence(page) -> dict:
    try:
        return await page.evaluate(
            """() => {
              const cssPath = (el) => {
                if (!el || !el.tagName) return "";
                const id = el.id ? "#" + CSS.escape(el.id) : "";
                const name = el.getAttribute("name") ? `[name="${el.getAttribute("name").replace(/"/g, '\\"')}"]` : "";
                return el.tagName.toLowerCase() + id + name;
              };
              const fieldsFor = (form) => Array.from(form.querySelectorAll("input, textarea, select, button"))
                .slice(0, 80).map((el) => ({
                  selector: cssPath(el),
                  name: el.getAttribute("name") || "",
                  id: el.id || "",
                  type: el.getAttribute("type") || el.tagName.toLowerCase(),
                  autocomplete: el.getAttribute("autocomplete") || "",
                  placeholder: el.getAttribute("placeholder") || "",
                }));
              return {
                scripts: Array.from(document.querySelectorAll("script[src]")).map(s => s.src),
                assets: Array.from(document.querySelectorAll("link[href]"))
                  .filter(l => /manifest|modulepreload|preload|prefetch|stylesheet|icon/i.test(l.rel || ""))
                  .map(l => l.href),
                forms: Array.from(document.querySelectorAll("form")).slice(0, 50).map((form, idx) => ({
                  selector: form.id ? `form#${CSS.escape(form.id)}` : `form:nth-of-type(${idx + 1})`,
                  action: form.action || location.href,
                  method: (form.method || "GET").toUpperCase(),
                  fields: fieldsFor(form),
                })),
                storage_keys: [
                  ...Array.from({length: localStorage.length}, (_, i) => localStorage.key(i)),
                  ...Array.from({length: sessionStorage.length}, (_, i) => sessionStorage.key(i)),
                ].filter(Boolean),
              };
            }"""
        )
    except Exception as exc:
        log.debug("DOM intelligence extraction failed: %s", exc)
        return {"scripts": [], "assets": [], "forms": [], "storage_keys": []}


async def _mine_script_intelligence(
    *,
    run_id: int,
    page,
    page_url: str,
    script_urls: list[str],
    base_netloc: str,
) -> None:
    seen: set[str] = set()
    for script_url in script_urls[:20]:
        if (
            not script_url
            or script_url in seen
            or not _same_domain(script_url, base_netloc)
        ):
            continue
        seen.add(script_url)
        try:
            resp = await page.request.get(script_url, timeout=10_000)
            if not resp.ok:
                continue
            body = (await resp.text())[:500_000]
        except Exception as exc:
            log.debug("Script mining failed for %s: %s", script_url, exc)
            continue
        _mine_asset_text(
            run_id=run_id,
            asset_url=script_url,
            body=body,
            source="js_asset",
            page_url=page_url,
        )
        for sourcemap_url in _extract_sourcemap_urls(script_url, body)[:3]:
            if not _same_domain(sourcemap_url, base_netloc):
                continue
            try:
                sm_resp = await page.request.get(sourcemap_url, timeout=10_000)
                if not sm_resp.ok:
                    continue
                sm_body = (await sm_resp.text())[:500_000]
            except Exception as exc:
                log.debug("Sourcemap mining failed for %s: %s", sourcemap_url, exc)
                continue
            _save_intel_item(
                run_id=run_id,
                kind="asset",
                key=_path_key(sourcemap_url),
                value=sourcemap_url,
                url=script_url,
                method="GET",
                source="sourcemap",
                confidence=0.8,
                metadata={"page_url": page_url},
            )
            _mine_asset_text(
                run_id=run_id,
                asset_url=sourcemap_url,
                body=sm_body,
                source="sourcemap",
                page_url=page_url,
            )


async def _mine_public_assets(
    *,
    run_id: int,
    page,
    base_url: str,
    base_netloc: str,
) -> None:
    for asset_url in _public_asset_candidates(base_url):
        if not _same_domain(asset_url, base_netloc):
            continue
        try:
            resp = await page.request.get(asset_url, timeout=8_000)
            status = getattr(resp, "status", None)
            if status is None or status >= 400:
                continue
            content_type = str(
                (getattr(resp, "headers", {}) or {}).get("content-type", "")
            )
            body = (await resp.text())[:500_000]
        except Exception as exc:
            log.debug("Public asset mining failed for %s: %s", asset_url, exc)
            continue
        _save_intel_item(
            run_id=run_id,
            kind="asset",
            key=_path_key(asset_url),
            value=asset_url,
            url=asset_url,
            method="GET",
            source="public_asset",
            confidence=0.9,
            evidence=f"HTTP {status}; {content_type}"[:200],
        )
        _mine_asset_text(
            run_id=run_id,
            asset_url=asset_url,
            body=body,
            source="public_asset",
            page_url=base_url,
        )


def _mine_asset_text(
    *,
    run_id: int,
    asset_url: str,
    body: str,
    source: str,
    page_url: str,
) -> None:
    for endpoint in _extract_endpoint_strings(body)[:150]:
        resolved = _resolve_asset_reference(asset_url, endpoint)
        _save_intel_item(
            run_id=run_id,
            kind="endpoint",
            key=_path_key(resolved),
            value=resolved,
            url=asset_url,
            source=source,
            confidence=0.8,
            evidence=endpoint,
            metadata={"page_url": page_url},
        )
    for call in _extract_js_api_calls(body)[:150]:
        resolved = _resolve_asset_reference(asset_url, call["url"])
        _save_intel_item(
            run_id=run_id,
            kind="endpoint",
            key=_path_key(resolved),
            value=resolved,
            url=asset_url,
            method=call.get("method") or "GET",
            source=source,
            confidence=0.92,
            evidence=call.get("evidence") or call["url"],
            metadata={
                "page_url": page_url,
                "discovery": "js_api_call",
                **call.get("metadata", {}),
            },
        )
        for field in call.get("body_fields", [])[:30]:
            _save_intel_item(
                run_id=run_id,
                kind="input",
                key=field,
                value="js_request_body",
                url=resolved,
                method=call.get("method") or "GET",
                source=source,
                confidence=0.8,
                metadata={
                    "page_url": page_url,
                    "asset_url": asset_url,
                    "discovery": "js_api_call",
                },
            )
    for route in _extract_js_route_paths(body)[:150]:
        resolved = _resolve_asset_reference(asset_url, route["path"])
        _save_intel_item(
            run_id=run_id,
            kind="endpoint",
            key=_path_key(resolved),
            value=resolved,
            url=asset_url,
            method="GET",
            source=source,
            confidence=route.get("confidence", 0.75),
            evidence=route.get("evidence") or route["path"],
            metadata={
                "page_url": page_url,
                "discovery": route.get("discovery", "js_route"),
                "category": route.get("category"),
            },
        )
    for lead in _extract_js_path_leads(body)[:120]:
        resolved = _resolve_asset_reference(asset_url, lead["path"])
        _save_intel_item(
            run_id=run_id,
            kind="endpoint",
            key=_path_key(resolved),
            value=resolved,
            url=asset_url,
            method=lead.get("method") or "GET",
            source=source,
            confidence=lead.get("confidence", 0.82),
            evidence=lead.get("evidence") or lead["path"],
            metadata={
                "page_url": page_url,
                "discovery": "js_path_lead",
                "category": lead.get("category"),
            },
        )
    for endpoint in _extract_sitemap_locations(body)[:200]:
        _save_intel_item(
            run_id=run_id,
            kind="endpoint",
            key=_path_key(endpoint),
            value=endpoint,
            url=asset_url,
            method="GET",
            source=source,
            confidence=0.9,
            evidence="sitemap location",
            metadata={"page_url": page_url},
        )
    for endpoint in _extract_robots_paths(asset_url, body)[:100]:
        _save_intel_item(
            run_id=run_id,
            kind="endpoint",
            key=_path_key(endpoint),
            value=endpoint,
            url=asset_url,
            method="GET",
            source=source,
            confidence=0.7,
            evidence="robots directive",
            metadata={"page_url": page_url},
        )
    for key in sorted(set(m.group(0) for m in _JWT_STORAGE_KEY_RE.finditer(body)))[:50]:
        _save_intel_item(
            run_id=run_id,
            kind="storage_key",
            key=key,
            value=key,
            url=asset_url,
            source=source,
            confidence=0.8,
            metadata={"page_url": page_url},
        )
    for key in _extract_storage_keys_from_js(body)[:100]:
        _save_intel_item(
            run_id=run_id,
            kind="storage_key",
            key=key,
            value=key,
            url=asset_url,
            source=source,
            confidence=0.9 if _JWT_STORAGE_KEY_RE.search(key) else 0.75,
            evidence="JavaScript storage access",
            metadata={"page_url": page_url, "discovery": "storage_api"},
        )
    for flag in _extract_feature_flags(body)[:100]:
        _save_intel_item(
            run_id=run_id,
            kind="feature_flag",
            key=flag["key"],
            value=flag["value"],
            url=asset_url,
            source=source,
            confidence=0.75,
            evidence=flag["evidence"],
            metadata={"page_url": page_url},
        )
    for field in _extract_interesting_response_fields(body):
        _save_intel_item(
            run_id=run_id,
            kind="response_field",
            key=field["key"],
            value=field["value"],
            url=asset_url,
            source=source,
            confidence=0.8,
            evidence=field["evidence"],
            metadata={"page_url": page_url},
        )


def _record_api_intelligence(
    *,
    run_id: int,
    call: dict,
    source_page_id: int,
    username: Optional[str],
) -> None:
    url = str(call.get("url") or "")
    method = str(call.get("method") or "GET").upper()
    if not url:
        return
    _save_intel_item(
        run_id=run_id,
        kind="endpoint",
        key=_path_key(url),
        value=url,
        url=url,
        method=method,
        source="api_observation",
        confidence=1.0,
        evidence=f"Observed {method} during crawl; status={call.get('status')}",
        metadata={"source_page_id": source_page_id, "username": username},
    )

    request_body = str(call.get("request_body") or "")
    for field in _extract_jsonish_keys(request_body)[:80]:
        _save_intel_item(
            run_id=run_id,
            kind="input",
            key=field,
            value="request_body",
            url=url,
            method=method,
            source="api_request",
            metadata={"source_page_id": source_page_id, "username": username},
        )

    body = str(call.get("body") or "")[:50_000]
    for item in _extract_ids_from_text(body):
        _save_intel_item(
            run_id=run_id,
            kind="id",
            key=item["key"],
            value=item["value"],
            url=url,
            method=method,
            source="api_response",
            evidence=item["evidence"],
            metadata={"source_page_id": source_page_id, "username": username},
        )
    for field in _extract_interesting_response_fields(body):
        _save_intel_item(
            run_id=run_id,
            kind="response_field",
            key=field["key"],
            value=field["value"],
            url=url,
            method=method,
            source="api_response",
            confidence=0.9,
            evidence=field["evidence"],
            metadata={"source_page_id": source_page_id, "username": username},
        )


def _extract_endpoint_strings(text: str) -> list[str]:
    out: list[str] = []
    for match in _ENDPOINT_RE.finditer(text or ""):
        path = match.group("path").strip()
        if path and path not in out:
            out.append(path)
    return out


def _extract_js_api_calls(text: str) -> list[dict]:
    calls: list[dict] = []
    seen: set[tuple[str, str]] = set()
    body = text or ""
    for match in _FETCH_CALL_RE.finditer(body[:500_000]):
        url = match.group("url").strip()
        args = match.group("args") or ""
        method = (
            match.group("axios_method")
            or _extract_method_from_js_options(args)
            or "GET"
        ).upper()
        key = (method, url)
        if key in seen:
            continue
        seen.add(key)
        calls.append(
            {
                "url": url,
                "method": method,
                "evidence": body[
                    max(0, match.start() - 80) : min(len(body), match.end() + 120)
                ],
                "body_fields": _dedupe_strings(
                    [
                        *_extract_jsonish_keys(args),
                        *_extract_js_shorthand_object_keys(args),
                    ]
                ),
                "metadata": {"call": "fetch_or_axios"},
            }
        )
        if len(calls) >= 200:
            return calls

    for match in _AXIOS_OBJECT_RE.finditer(body[:500_000]):
        obj = match.group("object") or ""
        url_match = re.search(
            r"\burl\s*:\s*(['\"`])(?P<url>https?://[^'\"`\s<>]+|/[^'\"`\s<>]+)\1", obj
        )
        if not url_match:
            continue
        method_match = re.search(r"\bmethod\s*:\s*(['\"`])(?P<method>[A-Za-z]+)\1", obj)
        url = url_match.group("url").strip()
        method = (method_match.group("method") if method_match else "GET").upper()
        key = (method, url)
        if key in seen:
            continue
        seen.add(key)
        calls.append(
            {
                "url": url,
                "method": method,
                "evidence": body[
                    max(0, match.start() - 80) : min(len(body), match.end() + 120)
                ],
                "body_fields": _dedupe_strings(
                    [
                        *_extract_jsonish_keys(obj),
                        *_extract_js_shorthand_object_keys(obj),
                    ]
                ),
                "metadata": {"call": "axios_object"},
            }
        )
        if len(calls) >= 200:
            break
    return calls


def _extract_method_from_js_options(text: str) -> str | None:
    match = re.search(
        r"\bmethod\s*:\s*(['\"`])(?P<method>GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\1",
        text or "",
        re.IGNORECASE,
    )
    return match.group("method") if match else None


def _extract_js_shorthand_object_keys(text: str) -> list[str]:
    keys: list[str] = []
    for match in re.finditer(r"\{(?P<body>[^{}]{1,500})\}", text or ""):
        for token in re.split(r"\s*,\s*", match.group("body")):
            token = token.strip()
            if (
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{1,80}", token)
                and token not in keys
            ):
                keys.append(token)
    return keys


def _dedupe_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _extract_js_route_paths(text: str) -> list[dict]:
    routes: list[dict] = []
    seen: set[str] = set()
    body = text or ""
    for match in _ROUTE_LITERAL_RE.finditer(body[:500_000]):
        path = match.group("path").strip()
        if not _looks_like_route_path(path) or path in seen:
            continue
        seen.add(path)
        routes.append(
            {
                "path": path,
                "category": _path_category(path),
                "confidence": 0.86 if _path_category(path) else 0.72,
                "discovery": "route_literal",
                "evidence": body[
                    max(0, match.start() - 80) : min(len(body), match.end() + 80)
                ],
            }
        )
        if len(routes) >= 200:
            break
    return routes


def _extract_js_path_leads(text: str) -> list[dict]:
    leads: list[dict] = []
    seen: set[str] = set()
    for path in _extract_endpoint_strings(text):
        category = _path_category(path)
        if not category or path in seen:
            continue
        seen.add(path)
        leads.append(
            {
                "path": path,
                "category": category,
                "method": "POST"
                if category in {"auth", "validation"}
                and re.search(
                    r"/(?:login|register|signup|verify|validate|check|preflight)",
                    path,
                    re.IGNORECASE,
                )
                else "GET",
                "confidence": 0.9
                if category in {"admin", "validation", "auth"}
                else 0.82,
                "evidence": path,
            }
        )
    return leads


def _extract_storage_keys_from_js(text: str) -> list[str]:
    keys: list[str] = []
    for match in _STORAGE_ACCESS_RE.finditer(text or ""):
        key = match.group("key").strip()
        if key and key not in keys:
            keys.append(key)
        if len(keys) >= 120:
            break
    return keys


def _extract_feature_flags(text: str) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    seen: set[str] = set()
    body = text or ""
    for match in _FEATURE_FLAG_RE.finditer(body[:500_000]):
        key = match.group("key").strip()
        value = match.group("value").strip().strip("'\"`")[:200]
        if key in seen:
            continue
        seen.add(key)
        flags.append(
            {
                "key": key,
                "value": value,
                "evidence": body[
                    max(0, match.start() - 80) : min(len(body), match.end() + 80)
                ],
            }
        )
        if len(flags) >= 120:
            break
    return flags


def _looks_like_route_path(path: str) -> bool:
    if not path or not path.startswith("/") or path.startswith("//"):
        return False
    if len(path) > 240 or any(ch in path for ch in " \t\r\n<>{}"):
        return False
    return True


def _path_category(path: str) -> str | None:
    if _ADMIN_PATH_RE.search(path):
        return "admin"
    if _VALIDATION_PATH_RE.search(path):
        return "validation"
    if _AUTH_PATH_RE.search(path):
        return "auth"
    if re.search(
        r"/(?:feature|flag|beta|experiment|config)(?:[/?.#-]|$)", path, re.IGNORECASE
    ):
        return "feature"
    return None


def _public_asset_candidates(base_url: str) -> list[str]:
    parsed = urlparse(base_url)
    origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    prefixes = {origin}
    app_path = parsed.path
    if app_path and app_path != "/":
        app_prefix = (
            app_path if app_path.endswith("/") else app_path.rsplit("/", 1)[0] + "/"
        )
        prefixes.add(urljoin(origin + "/", app_prefix.lstrip("/")))

    candidates: list[str] = []
    for prefix in sorted(prefixes):
        for path in _PUBLIC_ASSET_PATHS:
            candidate = urljoin(prefix.rstrip("/") + "/", path.lstrip("/"))
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _resolve_asset_reference(asset_url: str, reference: str) -> str:
    if reference.startswith(("http://", "https://")):
        return reference
    return urljoin(asset_url, reference)


def _extract_sitemap_locations(text: str) -> list[str]:
    locations: list[str] = []
    for match in re.finditer(
        r"<loc>\s*([^<\s]+)\s*</loc>", text or "", flags=re.IGNORECASE
    ):
        url = match.group(1).strip()
        if url and url not in locations:
            locations.append(url)
    return locations


def _extract_robots_paths(asset_url: str, text: str) -> list[str]:
    paths: list[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        directive, value = line.split(":", 1)
        if directive.strip().lower() not in {"allow", "disallow", "sitemap"}:
            continue
        value = value.strip()
        if not value or value == "/":
            continue
        resolved = _resolve_asset_reference(asset_url, value)
        if resolved not in paths:
            paths.append(resolved)
    return paths


def _extract_sourcemap_urls(script_url: str, text: str) -> list[str]:
    urls: list[str] = []
    for match in _SOURCE_MAPPING_RE.finditer(text or ""):
        value = match.group(1).strip()
        if not value or value.startswith("data:"):
            continue
        resolved = _resolve_asset_reference(script_url, value)
        if resolved not in urls:
            urls.append(resolved)
    return urls


def _extract_jsonish_keys(text: str) -> list[str]:
    keys: list[str] = []
    if not text:
        return keys
    try:
        data = json.loads(text)
    except Exception:
        data = None
    if data is not None:

        def _walk(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(k, str) and k not in keys:
                        keys.append(k)
                    _walk(v)
            elif isinstance(value, list):
                for child in value:
                    _walk(child)

        _walk(data)
        return keys
    for key in re.findall(r'"([A-Za-z_][A-Za-z0-9_-]{1,80})"\s*:', text):
        if key not in keys:
            keys.append(key)
    for key in re.findall(r"\b([A-Za-z_][A-Za-z0-9_-]{1,80})\s*:", text):
        if key not in keys:
            keys.append(key)
    return keys


def _extract_ids_from_text(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if not text:
        return items
    patterns = [
        r'"(?P<key>[A-Za-z_][A-Za-z0-9_-]*(?:id|ID|Id))"\s*:\s*"?(?P<value>[A-Za-z0-9_-]{1,80})"?',
        r'\b(?P<key>[A-Za-z_][A-Za-z0-9_-]*(?:id|ID|Id))\s*[=:]\s*"?(?P<value>[A-Za-z0-9_-]{1,80})"?',
    ]
    seen: set[tuple[str, str]] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text[:50_000]):
            key = match.group("key")
            value = match.group("value")
            if not value or (key, value) in seen:
                continue
            seen.add((key, value))
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            items.append({"key": key, "value": value, "evidence": text[start:end]})
            if len(items) >= 100:
                return items
    return items


def _extract_interesting_response_fields(text: str) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for key in _extract_jsonish_keys(text):
        if not _INTERESTING_FIELD_RE.search(key):
            continue
        value = ""
        match = re.search(
            rf'"{re.escape(key)}"\s*:\s*(".*?"|[^,\n\r}}]+)', text[:50_000]
        )
        if match:
            value = match.group(1).strip().strip('"')[:200]
            evidence = match.group(0)[:500]
        else:
            evidence = key
        fields.append({"key": key, "value": value, "evidence": evidence})
    return fields[:50]


def _path_key(url: str) -> str:
    try:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return parsed.path or "/"
    except Exception:
        pass
    return str(url or "")[:500]


async def _promote_api_calls(
    *,
    run_id: int,
    calls: list[dict],
    source_page_id: int,
    source_depth: int,
    shared: _CrawlShared,
    max_pages: int,
    credential_id: Optional[int],
    username: Optional[str],
    llm_cfg,
) -> None:
    for call in _dedupe_api_calls(calls):
        url = call.get("url") or ""
        if not url:
            continue
        api_title, api_context, api_categories = await _analyse_api_call(
            llm_cfg, call, credential_id
        )
        norm = _norm(url)
        async with shared.lock:
            if norm in shared.crawled_norms:
                page_id = shared.crawled_norms[norm]
                is_new = False
            elif shared.pages_done >= max_pages:
                continue
            else:
                page_id = _save_api_page(
                    run_id,
                    call,
                    source_depth + 1,
                    credential_id,
                    title=api_title,
                    context=api_context,
                    categories=api_categories,
                )
                shared.crawled_norms[norm] = page_id
                shared.pages_done += 1
                is_new = True

        _update_accessible_by(page_id, credential_id)
        _save_credential_view(
            page_id,
            run_id,
            credential_id,
            username,
            None,
            api_context,
            _api_page_text(call)[:10_000],
            api_categories,
        )
        _save_link(run_id, source_page_id, page_id, url)

        if is_new:
            _update_run(run_id, pages_discovered=shared.pages_done)
            events_svc.emit(
                run_id,
                {
                    "type": "page_added",
                    "username": username,
                    "node": {
                        "id": page_id,
                        "url": url,
                        "title": api_title,
                        "depth": source_depth + 1,
                        "status": "crawled",
                        "context": api_context,
                        "in_scope": True,
                        "scan_status": "pending",
                        "accessible_by": [credential_id]
                        if credential_id is not None
                        else [],
                    },
                    "link": {
                        "source": source_page_id,
                        "target": page_id,
                        "link_text": "API call",
                    },
                },
            )
        else:
            events_svc.emit(
                run_id,
                {
                    "type": "node_accessible_by",
                    "page_id": page_id,
                    "username": username,
                },
            )

        _record_api_intelligence(
            run_id=run_id,
            call=call,
            source_page_id=source_page_id,
            username=username,
        )


def _dedupe_api_calls(calls: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    result: list[dict] = []
    for call in calls:
        key = (
            str(call.get("method") or "GET").upper(),
            _norm(str(call.get("url") or "")),
        )
        if not key[1] or key in seen:
            continue
        seen.add(key)
        result.append(call)
    return result


async def _analyse_api_call(
    llm_cfg, call: dict, credential_id: Optional[int]
) -> tuple[str, str, dict]:
    title = _api_title(call)
    fallback_context = _api_context(call)
    fallback_categories = _api_categories(call, credential_id)
    try:
        context, _suggested, cats = await llm_svc.analyse_page(
            llm_cfg,
            call.get("url") or "",
            title,
            _api_analysis_text(call),
            None,
        )
        return (
            title,
            _combine_api_context(fallback_context, context),
            _merge_api_categories(fallback_categories, cats),
        )
    except Exception as exc:
        log.warning("  LLM API analysis failed for %s: %s", call.get("url"), exc)
        return title, fallback_context, fallback_categories


def _save_api_page(
    run_id: int,
    call: dict,
    depth: int,
    credential_id: Optional[int],
    *,
    title: str,
    context: str,
    categories: dict,
) -> int:
    with Session(get_engine()) as s:
        cp = CrawledPage(
            test_run_id=run_id,
            url=call.get("url") or "",
            title=title,
            page_text=_api_page_text(call)[:10_000],
            screenshot_b64=None,
            llm_context=context,
            depth=depth,
            status="crawled",
            req_auth=categories.get("req_auth"),
            takes_input=categories.get("takes_input"),
            has_object_ref=categories.get("has_object_ref"),
            has_business_logic=categories.get("has_business_logic"),
            owasp_applicable_json=json.dumps(categories.get("owasp_applicable") or {}),
            accessible_by=json.dumps(
                [credential_id] if credential_id is not None else []
            ),
        )
        s.add(cp)
        s.commit()
        s.refresh(cp)
        s.expunge(cp)
        return cp.id


def _api_title(call: dict) -> str:
    parsed = urlparse(call.get("url") or "")
    method = str(call.get("method") or "GET").upper()
    status = call.get("status")
    status_text = f" {status}" if status is not None else ""
    return f"API {method}{status_text} {parsed.path or '/'}"


def _api_context(call: dict) -> str:
    method = str(call.get("method") or "GET").upper()
    status = call.get("status")
    content_type = call.get("content_type") or ""
    request_body = (call.get("request_body") or "").strip()
    context = (
        f"[API endpoint] Observed {method} request during crawl. "
        f"HTTP status: {status if status is not None else 'unknown'}. "
        f"Content-Type: {content_type or 'unknown'}. Screenshot capture was skipped."
    )
    if request_body:
        context += f"\nRequest body excerpt:\n{request_body[:4000]}"
    return context


def _api_analysis_text(call: dict) -> str:
    return _api_page_text(call)


def _api_page_text(call: dict) -> str:
    method = str(call.get("method") or "GET").upper()
    url = call.get("url") or ""
    status = call.get("status")
    request_headers = call.get("request_headers") or {}
    response_headers = call.get("response_headers") or {}
    request_body = (call.get("request_body") or "")[:8000]
    body = (call.get("body") or "")[:8000]
    return (
        f"=== HTTP exchange observed during crawl ===\n"
        f"\nREQUEST\n"
        f"{method} {url}\n"
        f"Headers:\n{_format_headers(request_headers)}\n"
        f"\nBody:\n{request_body or '(none)'}\n"
        f"\nRESPONSE\n"
        f"Status: {status if status is not None else 'unknown'}\n"
        f"Headers:\n{_format_headers(response_headers)}\n"
        f"\nBody:\n{body or '(none)'}"
    )


def _format_headers(headers: dict, *, max_value_len: int = 200) -> str:
    """Format HTTP headers for display, abbreviating long cookie/set-cookie values."""
    lines = []
    for k, v in (headers or {}).items():
        v_str = str(v)
        if k.lower() in ("cookie", "set-cookie") and len(v_str) > 80:
            v_str = v_str[:80] + f"… ({len(v_str)} chars total)"
        elif len(v_str) > max_value_len:
            v_str = v_str[:max_value_len] + "…"
        lines.append(f"  {k}: {v_str}")
    return "\n".join(lines) if lines else "  (none)"


def _header_value(headers: dict, name: str) -> str | None:
    wanted = name.lower()
    for key, value in (headers or {}).items():
        if str(key).lower() == wanted:
            return str(value)
    return None


def _combine_api_context(fallback_context: str, llm_context: str) -> str:
    llm_context = (llm_context or "").strip()
    if not llm_context:
        return fallback_context
    return f"{fallback_context}\n\n{llm_context}"


def _api_categories(call: dict, credential_id: Optional[int]) -> dict:
    method = str(call.get("method") or "GET").upper()
    url = call.get("url") or ""
    request_body = call.get("request_body") or ""
    url_lower = url.lower()
    body_lower = request_body.lower()
    is_mutating = method in ("POST", "PUT", "PATCH", "DELETE")
    has_id = _url_has_object_ref(url) or _body_has_object_ref(request_body)
    is_auth_endpoint = any(
        kw in url_lower
        for kw in (
            "/login",
            "/logout",
            "/auth",
            "/token",
            "/session",
            "/password",
            "/reset",
            "/register",
            "/signup",
            "/oauth",
        )
    )
    has_url_param = bool(
        re.search(
            r"[?&](?:url|uri|href|src|redirect|callback|proxy|fetch|target)=", url_lower
        )
    ) or bool(
        re.search(
            r'"(?:url|uri|href|src|redirect|callback|proxy|fetch|target)"\s*:',
            body_lower,
        )
    )

    owasp_applicable = {
        "A01": has_id or credential_id is not None,  # Broken Access Control
        "A02": is_auth_endpoint
        or bool(
            re.search(r"password|secret|token|key|credential", body_lower)
        ),  # Cryptographic Failures
        "A03": is_mutating or bool(request_body),  # Injection
        "A04": is_mutating,  # Insecure Design
        "A05": True,  # Security Misconfiguration (headers etc.)
        "A06": False,  # Supply Chain — can't tell from request alone
        "A07": is_auth_endpoint or credential_id is not None,  # Auth Failures
        "A08": is_mutating,  # Software & Data Integrity
        "A09": is_mutating,  # Logging & Monitoring
        "A10": has_url_param,  # SSRF
    }
    return {
        "req_auth": credential_id is not None,
        "takes_input": method not in ("GET", "HEAD", "OPTIONS") or bool(request_body),
        "has_object_ref": has_id,
        "has_business_logic": None,
        "owasp_applicable": owasp_applicable,
    }


def _body_has_object_ref(body: str) -> bool:
    text = (body or "")[:20_000]
    if not text:
        return False
    lowered = text.lower()
    if re.search(
        r'"(?:id|[a-z0-9_]*(?:id|account|user|customer|order)[a-z0-9_]*)"\s*:\s*"?\d+',
        lowered,
    ):
        return True
    if re.search(
        r"(?:^|[&?])(?:id|account|accountid|user|userid|customer|customerid|order|orderid)=\d+",
        lowered,
    ):
        return True
    return False


def _merge_api_categories(fallback: dict, llm_categories: dict) -> dict:
    merged = dict(fallback)
    for key in ("req_auth", "takes_input", "has_object_ref", "has_business_logic"):
        if llm_categories.get(key) is not None:
            merged[key] = llm_categories[key]
    if fallback.get("takes_input"):
        merged["takes_input"] = True
    if fallback.get("has_object_ref"):
        merged["has_object_ref"] = True
    if fallback.get("req_auth"):
        merged["req_auth"] = True
    # Pass through OWASP applicability from LLM; OR-merge with heuristic fallback
    llm_owasp = llm_categories.get("owasp_applicable") or {}
    heuristic_owasp = fallback.get("owasp_applicable") or {}
    if llm_owasp or heuristic_owasp:
        merged["owasp_applicable"] = {
            cat: llm_owasp.get(cat, False) or heuristic_owasp.get(cat, False)
            for cat in set(list(llm_owasp) + list(heuristic_owasp))
        }
    return merged


async def _persist_recon_session(run_id: int, cred, page) -> None:
    """Capture the cookies/bearer of an authenticated reconcile page into the vault.

    Guided logins persist themselves; auto/totp creds otherwise vanish after
    reconcile, leaving the validator with no alternate user sessions.
    """
    try:
        raw_cookies = await page.context.cookies()
        cookies = {c["name"]: c["value"] for c in raw_cookies}
        token = None
        for key in ("access_token", "token", "jwt", "auth_token", "id_token",
                    "authToken", "accessToken"):
            try:
                val = await page.evaluate(
                    "(k) => localStorage.getItem(k) || sessionStorage.getItem(k)",
                    key,
                )
            except Exception:
                val = None
            if val:
                token = val
                break
        if not cookies and not token:
            return  # auth produced no session — nothing to record
        from aespa.services import scanner_sessions as _ss

        _ss.upsert_session(
            run_id,
            label=f"recon_{cred.id}",
            kind="bearer" if token and not cookies else "cookie",
            username=cred.username,
            credential_id=cred.id,
            source="reconcile_login",
            cookies=cookies,
            extra_headers={"Authorization": f"Bearer {token}"} if token else None,
        )
    except Exception as exc:
        log.warning("  reconcile: could not persist session for %s: %s",
                    getattr(cred, "username", "?"), exc)


async def _reconcile_direct_access(
    *,
    run_id: int,
    creds: list,
    base_url: str,
    login_url: str,
    requires_auth: bool,
    llm_cfg,
    pw_proxy: dict,
    global_http_header: dict[str, str],
) -> None:
    """Mark pages as accessible when a credential can load a known URL directly.

    Crawl discovery answers "did this user find a link here?". Authorization needs a
    separate direct-load check because shared URLs can render user-specific content.
    """
    if not requires_auth or len(creds) < 2:
        return

    from playwright.async_api import async_playwright

    with Session(get_engine()) as s:
        pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.status == "crawled")
        ).all()
        page_rows = [
            (
                p.id,
                p.url,
                p.title or "",
                p.page_text or "",
                json.loads(p.accessible_by or "[]"),
            )
            for p in pages
            if p.id is not None and p.url
        ]

    if not page_rows:
        return

    log.info("Reconciling direct page access across %d credential(s)", len(creds))
    total_checks = len(creds) * len(page_rows)
    checks_done = 0
    events_svc.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": "crawler",
            "role": "Crawler",
            "status": "active",
            "current_task": f"Verifying cross-user access (0/{total_checks})…",
            "outcome": None,
            "_persist": True,
        },
    )
    _crawl_log(
        run_id,
        "reconcile",
        "start",
        f"Verifying cross-user page access — {total_checks} check(s) across "
        f"{len(creds)} credential(s)",
    )
    async with async_playwright() as p:
        _args = ["--proxy-bypass-list=<-loopback>"] if pw_proxy else []
        browser = await p.chromium.launch(headless=True, args=_args)
        try:
            for cred in creds:
                if run_id in _stop_requested:
                    break
                credential_login_url = _login_url_for_credential(login_url, cred)
                ctx = await browser.new_context(
                    user_agent=_UA, ignore_https_errors=True, **pw_proxy
                )
                if global_http_header:
                    await ctx.set_extra_http_headers(global_http_header)
                traffic_svc.setup_playwright_logging(
                    ctx, run_id, username=cred.username
                )
                page = await ctx.new_page()
                try:
                    try:
                        await page.goto(
                            base_url, wait_until="domcontentloaded", timeout=20_000
                        )
                    except Exception:
                        pass
                    await _authenticate(
                        page, credential_login_url, cred, run_id, llm_cfg=llm_cfg
                    )
                    # Persist this credential's session to the vault so the dynamic
                    # scan and the validator's access-control check have alternate
                    # user sessions. Without this, only guided logins and the primary
                    # ever reach the vault, so the validator reports "no alternate
                    # user sessions were available" for every privesc finding.
                    await _persist_recon_session(run_id, cred, page)
                    auth_check_snapshot = await _capture_auth_check_snapshot(
                        page, credential_login_url
                    )

                    for (
                        page_id,
                        page_url,
                        page_title,
                        page_text,
                        accessible_by,
                    ) in page_rows:
                        if run_id in _stop_requested:
                            break
                        checks_done += 1
                        events_svc.emit(
                            run_id,
                            {
                                "type": "agent_status",
                                "agent_id": "crawler",
                                "role": "Crawler",
                                "status": "active",
                                "current_task": (
                                    f"Verifying cross-user access "
                                    f"({checks_done}/{total_checks})…"
                                ),
                                "outcome": None,
                                "_persist": True,
                            },
                        )
                        if cred.id in accessible_by:
                            continue
                        if _is_session_ending_url(page_url):
                            continue
                        (
                            accessible,
                            title,
                            text,
                            screenshot_b64,
                        ) = await _direct_load_accessible(
                            page,
                            page_url,
                            requires_auth=requires_auth,
                            credential=cred,
                            login_url=credential_login_url,
                            username=cred.username,
                            auth_check_snapshot=auth_check_snapshot,
                            recover_api_auth=False,
                            run_id=run_id,
                            llm_cfg=llm_cfg,
                        )
                        if not accessible:
                            continue
                        access_ok, access_reason = await _confirm_direct_page_access(
                            llm_cfg=llm_cfg,
                            url=page_url,
                            original_title=page_title,
                            original_text=page_text,
                            candidate_title=title,
                            candidate_text=text,
                            candidate_username=cred.username,
                            screenshot_b64=screenshot_b64,
                        )
                        if not access_ok:
                            log.info(
                                "  Direct access rejected: user=%s page=%s reason=%s",
                                cred.username,
                                page_url,
                                access_reason,
                            )
                            continue
                        log.info(
                            "  Direct access confirmed: user=%s page=%s",
                            cred.username,
                            page_url,
                        )
                        _save_credential_view(
                            page_id,
                            run_id,
                            cred.id,
                            cred.username,
                            screenshot_b64,
                            f"[Direct access reconciliation] {access_reason}",
                            text[:10_000],
                            {},
                        )
                        _update_accessible_by(page_id, cred.id)
                        accessible_by.append(cred.id)
                        events_svc.emit(
                            run_id,
                            {
                                "type": "node_accessible_by",
                                "page_id": page_id,
                                "username": cred.username,
                            },
                        )
                finally:
                    await ctx.close()
        finally:
            await browser.close()
    _crawl_log(
        run_id,
        "reconcile",
        "complete",
        "Cross-user access verification complete",
    )


async def _direct_load_accessible(
    page,
    url: str,
    *,
    requires_auth: bool = False,
    credential=None,
    login_url: str = "",
    username: Optional[str] = None,
    auth_check_snapshot: dict | None = None,
    recover_api_auth: bool = True,
    run_id: int = 0,
    llm_cfg=None,
) -> tuple[bool, str, str, Optional[str]]:
    try:
        resp = await _goto_with_auth_recovery(
            page,
            url,
            requires_auth=requires_auth,
            credential=credential,
            login_url=login_url,
            username=username,
            auth_check_snapshot=auth_check_snapshot,
            recover_api_auth=recover_api_auth,
            run_id=run_id,
            llm_cfg=llm_cfg,
        )
    except Exception:
        return False, "", "", None

    if resp is not None and resp.status >= 400:
        return False, "", "", None

    try:
        pw_loc = page.locator("input[type='password']").first
        on_login = (await pw_loc.count() > 0) and (await pw_loc.is_visible())
    except Exception:
        on_login = False
    if on_login:
        return False, "", "", None

    await page.wait_for_timeout(800)
    try:
        title = await page.title()
    except Exception:
        title = ""
    try:
        text = await page.evaluate("() => document.body.innerText")
    except Exception:
        text = ""
    if _looks_like_login_text(text) or not text.strip():
        return False, title, text, None
    screenshot_b64: Optional[str] = None
    try:
        raw = await page.screenshot(type="png", full_page=False)
        screenshot_b64 = base64.b64encode(raw).decode()
    except Exception:
        pass
    return True, title, text, screenshot_b64


async def _confirm_direct_page_access(
    *,
    llm_cfg,
    url: str,
    original_title: str,
    original_text: str,
    candidate_title: str,
    candidate_text: str,
    candidate_username: str,
    screenshot_b64: Optional[str],
) -> tuple[bool, str]:
    if _looks_like_access_failure_text(candidate_text):
        return (
            False,
            "The direct-load response contains an access failure or loading error message.",
        )
    if not candidate_text.strip():
        return False, "The direct-load response did not contain meaningful page text."
    try:
        verdict = await llm_svc.judge_page_access(
            llm_cfg,
            url=url,
            original_title=original_title,
            original_text=original_text,
            candidate_title=candidate_title,
            candidate_text=candidate_text,
            candidate_username=candidate_username,
            screenshot_b64=screenshot_b64,
        )
    except Exception as exc:
        log.warning(
            "  LLM access reconciliation failed for %s as %s: %s",
            url,
            candidate_username,
            exc,
        )
        return False, "Access reconciliation could not get a reliable LLM judgement."

    accessible = bool(verdict.get("accessible"))
    reasoning = str(verdict.get("reasoning") or "No reasoning returned.")[:1000]
    return accessible, reasoning


def _looks_like_login_text(text: str) -> bool:
    body = (text or "").lower()[:3000]
    login_hits = sum(
        1
        for marker in ("login", "log in", "sign in", "password", "forgot password")
        if marker in body
    )
    denied_hits = sum(
        1
        for marker in ("access denied", "forbidden", "unauthorized", "unauthorised")
        if marker in body
    )
    return login_hits >= 2 or denied_hits >= 1


def _looks_like_access_failure_text(text: str) -> bool:
    body = (text or "").lower()[:5000]
    return any(
        marker in body
        for marker in (
            "could not load",
            "couldn't load",
            "failed to load",
            "unable to load",
            "cannot load",
            "can't load",
            "not authorized",
            "not authorised",
            "unauthorized",
            "unauthorised",
            "access denied",
            "forbidden",
            "permission denied",
            "does not have access",
            "no access",
            "not found",
            "account not found",
            "details unavailable",
            "details could not be loaded",
        )
    )


def _looks_like_denied_or_login_wall_text(text: str) -> bool:
    body = (text or "").lower()[:3000]
    denied_hits = sum(
        1
        for marker in (
            "access denied",
            "forbidden",
            "unauthorized",
            "unauthorised",
            "session expired",
            "session has expired",
        )
        if marker in body
    )
    if denied_hits:
        return True
    login_wall_hits = sum(
        1
        for marker in (
            "login required",
            "please log in",
            "please sign in",
            "you must log in",
            "you must sign in",
            "authentication required",
        )
        if marker in body
    )
    return login_wall_hits >= 1


def _merge_all_categories(run_id: int) -> None:
    """OR-merge LLM categories from all credential views into each CrawledPage."""
    with Session(get_engine()) as s:
        pages = s.exec(
            select(CrawledPage).where(CrawledPage.test_run_id == run_id)
        ).all()
        for cp in pages:
            views = s.exec(
                select(PageCredentialView)
                .where(PageCredentialView.test_run_id == run_id)
                .where(PageCredentialView.page_id == cp.id)
            ).all()
            if not views:
                continue
            for attr in (
                "req_auth",
                "takes_input",
                "has_object_ref",
                "has_business_logic",
            ):
                vals = [getattr(v, attr) for v in views if getattr(v, attr) is not None]
                if vals:
                    setattr(cp, attr, any(vals))
            # OR-merge OWASP applicability: a category is applicable if any credential view says so
            merged_owasp: dict[str, bool] = {}
            for v in views:
                try:
                    view_owasp = json.loads(v.owasp_applicable_json or "{}")
                except Exception:
                    view_owasp = {}
                for cat, val in view_owasp.items():
                    merged_owasp[cat] = merged_owasp.get(cat, False) or bool(val)
            if merged_owasp:
                cp.owasp_applicable_json = json.dumps(merged_owasp)
            s.add(cp)
        s.commit()


def _update_accessible_by(page_id: int, credential_id: Optional[int]) -> None:
    if credential_id is None:
        return
    with Session(get_engine()) as s:
        cp = s.get(CrawledPage, page_id)
        if cp is None:
            return
        ab: list[int] = json.loads(cp.accessible_by or "[]")
        if credential_id not in ab:
            ab.append(credential_id)
            cp.accessible_by = json.dumps(ab)
            s.add(cp)
            s.commit()


def _save_link(
    run_id: int,
    source_id: Optional[int],
    target_id: int,
    target_url: str,
    *,
    link_text: Optional[str] = None,
    action_kind: str = "navigate",
    action_data: Optional[dict] = None,
) -> None:
    if source_id is None:
        return
    with Session(get_engine()) as s:
        existing = s.exec(
            select(PageLink)
            .where(PageLink.test_run_id == run_id)
            .where(PageLink.source_page_id == source_id)
            .where(PageLink.target_page_id == target_id)
            .where(PageLink.target_url == target_url)
            .where(PageLink.action_kind == action_kind)
        ).first()
        if existing:
            return
        pl = PageLink(
            test_run_id=run_id,
            source_page_id=source_id,
            target_page_id=target_id,
            target_url=target_url,
            link_text=link_text,
            action_kind=action_kind,
            action_data_json=json.dumps(action_data or {}),
        )
        s.add(pl)
        s.commit()


def _update_run(run_id: int, **kwargs) -> None:
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return
        for k, v in kwargs.items():
            setattr(run, k, v)
        s.add(run)
        s.commit()


def _update_credential_progress(
    run_id: int,
    username: Optional[str],
    current_url: str | None,
    pages_visited: int,
    *,
    done: bool = False,
) -> None:
    """Persist per-credential crawl progress so the UI can read it on load/refresh."""
    if not username:
        return
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return
        progress = json.loads(run.per_user_progress or "{}")
        progress[username] = {
            "current_url": current_url,
            "pages_visited": pages_visited,
            "done": done,
            "updated_at": _utcnow().isoformat(),
        }
        run.per_user_progress = json.dumps(progress)
        s.add(run)
        s.commit()


def _clear_pages(run_id: int) -> None:
    with Session(get_engine()) as s:
        links = s.exec(select(PageLink).where(PageLink.test_run_id == run_id)).all()
        for link in links:
            s.delete(link)
        views = s.exec(
            select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)
        ).all()
        for v in views:
            s.delete(v)
        pages = s.exec(
            select(CrawledPage).where(CrawledPage.test_run_id == run_id)
        ).all()
        for p in pages:
            s.delete(p)
        s.commit()


# ── URL utilities ─────────────────────────────────────────────────────────────


def _norm(url: str) -> str:
    try:
        p = urlparse(url)
        path = p.path.rstrip("/") or "/"
        frag = p.fragment if p.fragment.startswith("/") else ""
        return urlunparse(
            (p.scheme.lower(), p.netloc.lower(), path, p.params, p.query, frag)
        )
    except Exception:
        return url


_DEFAULT_PORTS = {"http": "80", "https": "443"}


def _norm_netloc(netloc: str, scheme: str) -> str:
    """Lower-case a netloc and drop the scheme's default port + any userinfo.

    So ``example.com`` and ``example.com:443`` (under https) compare equal — a
    bare prefix-equality check on the raw netloc treats those as different hosts
    and wrongly drops same-site links that only differ by an explicit default port.
    """
    netloc = netloc.lower()
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[1]  # strip user:pass@
    host, sep, port = netloc.rpartition(":")
    # rpartition only yields a port when there is a colon AND the tail is numeric
    # (guards IPv6 literals like ``[::1]`` whose tail is not all digits).
    if sep and port.isdigit():
        if port == _DEFAULT_PORTS.get(scheme):
            return host
        return f"{host}:{port}"
    return netloc


def _same_domain(url: str, base_netloc: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        # Normalise both sides against the candidate's scheme so an implicit vs
        # explicit default port (e.g. :443 on https) does not split the host.
        return _norm_netloc(parsed.netloc, parsed.scheme) == _norm_netloc(
            base_netloc, parsed.scheme
        )
    except Exception:
        return False


def _filter_suggested_links(
    suggested: list[str],
    observed_links: list[tuple[str, str]],
    base_netloc: str,
) -> list[str]:
    observed_by_norm = {
        _norm(url): url
        for url, link_text in observed_links
        if _same_domain(url, base_netloc) and not _is_session_ending_url(url, link_text)
    }
    filtered: list[str] = []
    seen: set[str] = set()
    for url in suggested:
        norm = _norm(url)
        if norm in observed_by_norm and norm not in seen:
            filtered.append(observed_by_norm[norm])
            seen.add(norm)
    return filtered


def _in_base_scope(url: str, base_netloc: str, base_path: str) -> bool:
    if not _same_domain(url, base_netloc):
        return False
    if base_path == "/":
        return True
    p = urlparse(url).path
    return p.startswith(base_path) or p == base_path.rstrip("/")


def _is_api_page(url: str, text: str) -> bool:
    path = urlparse(url).path.lower()
    if any(
        pat in path
        for pat in (
            "/api/",
            "/v1/",
            "/v2/",
            "/v3/",
            "/rest/",
            "/graphql",
            "/swagger",
            "/openapi",
        )
    ):
        return True
    stripped = (text or "").lstrip()
    return len(stripped) > 2 and stripped[0] in ("{", "[")


def _is_api_response_candidate(url: str, resource_type: str, content_type: str) -> bool:
    path = urlparse(url).path.lower()
    if any(
        pat in path
        for pat in (
            "/api/",
            "/v1/",
            "/v2/",
            "/v3/",
            "/rest/",
            "/graphql",
            "/swagger",
            "/openapi",
        )
    ):
        return True
    if resource_type in ("fetch", "xhr"):
        return True
    ctype = (content_type or "").lower()
    return any(token in ctype for token in ("json", "xml", "graphql"))


def _response_body_is_text(content_type: str) -> bool:
    ctype = (content_type or "").lower()
    return any(
        token in ctype
        for token in ("text", "json", "xml", "html", "javascript", "graphql")
    )


def _url_has_object_ref(url: str) -> bool:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if any(part.isdigit() for part in path_parts):
        return True
    query = parsed.query.lower()
    return any(
        marker in query
        for marker in ("id=", "account=", "user=", "customer=", "order=")
    )


def _is_session_ending_url(url: str, link_text: str | None = None) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        parsed = None
    haystack = " ".join(
        [
            (parsed.path if parsed else url) or "",
            (parsed.query if parsed else "") or "",
            link_text or "",
        ]
    ).lower()
    compact = "".join(ch for ch in haystack if ch.isalnum())
    return any(
        marker in compact
        for marker in (
            "logout",
            "signout",
            "signoff",
            "logoff",
            "endsession",
            "destroysession",
            "invalidatesession",
        )
    )


def _same_url_without_fragment(left: str, right: str) -> bool:
    try:
        lhs = urlparse(left)
        r = urlparse(right)
        return (
            lhs.scheme.lower(),
            lhs.netloc.lower(),
            lhs.path.rstrip("/") or "/",
            lhs.query,
        ) == (
            r.scheme.lower(),
            r.netloc.lower(),
            r.path.rstrip("/") or "/",
            r.query,
        )
    except Exception:
        return False


def _response_suggests_session_dropped(resp) -> bool:
    return resp is not None and resp.status in (401, 419, 440)


async def _page_requires_login(page, login_url: str) -> bool:  # noqa: ARG001
    try:
        pw_loc = page.locator("input[type='password']").first
        if (await pw_loc.count() > 0) and (await pw_loc.is_visible()):
            return True
    except Exception:
        pass
    try:
        text = await page.evaluate("() => document.body.innerText")
    except Exception:
        text = ""
    return _looks_like_denied_or_login_wall_text(text)


async def _goto_with_auth_recovery(
    page,
    url: str,
    *,
    requires_auth: bool,
    credential,
    login_url: str,
    username: Optional[str],
    auth_check_snapshot: dict | None = None,
    recover_api_auth: bool = True,
    run_id: int = 0,
    llm_cfg=None,
):
    response = None
    for attempt in range(2):
        response = await _goto_lenient(page, url, timeout=20_000)
        try:
            # networkidle is unreliable on apps with polling/analytics/websockets
            # (never goes idle → full timeout burned). Keep it short — it's a
            # best-effort settle, not a correctness gate.
            await page.wait_for_load_state("networkidle", timeout=3_000)
        except Exception:
            pass
        if not requires_auth or credential is None or not login_url:
            return response
        session_dropped = _response_suggests_session_dropped(
            response
        ) or await _page_requires_login(page, login_url)
        if not session_dropped:
            return response
        if attempt == 0:
            if not recover_api_auth and _api_response_should_not_reauth(url, response):
                log.debug(
                    "API response looked unauthenticated for user=%s at %s; treating as inaccessible response",
                    username,
                    url,
                )
                return response
            if await _auth_check_still_authenticated(
                page, auth_check_snapshot, login_url, username
            ):
                log.info(
                    "Session-drop signal was false for user=%s at %s; known-good page still loads",
                    username,
                    url,
                )
                return response
            if _api_response_should_not_reauth(url, response):
                log.info(
                    "API response looked unauthenticated for user=%s at %s, but no browser-login proof; treating as inaccessible response",
                    username,
                    url,
                )
                return response
            log.info(
                "Session appears to have dropped for user=%s at %s; re-authenticating and retrying",
                username,
                url,
            )
            _crawl_log(
                run_id,
                "auth",
                "info",
                f"Session dropped for {username or 'user'} — re-authenticating",
                page_url=url,
            )
            await _authenticate(page, login_url, credential, run_id, llm_cfg=llm_cfg)
            continue
        log.warning(
            "Session still appears unauthenticated after retry for user=%s at %s",
            username,
            url,
        )
        return response
    return response


def _site_base_url(value: str) -> str:
    """Preserve the configured path, including a trailing slash for mounted apps."""
    return str(value or "").strip()


async def _best_effort_preload(page, url: str, username: Optional[str]) -> None:
    try:
        await _goto_lenient(page, url, timeout=20_000)
    except Exception as exc:
        log.warning("Pre-load failed for user=%s: %s", username, exc)


async def _goto_lenient(page, url: str, timeout: int = 20_000):
    try:
        return await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    except Exception as exc:
        if _navigation_reached_target(page, url, exc):
            log.info(
                "Navigation to %s timed out waiting for domcontentloaded, but the browser reached the target URL; continuing.",
                url,
            )
            return None
        raise


def _navigation_reached_target(page, url: str, exc: Exception) -> bool:
    if "timeout" not in str(exc).lower():
        return False
    current_url = str(getattr(page, "url", "") or "")
    if not current_url:
        return False
    return _same_url_without_fragment(current_url, url)


def _api_response_should_not_reauth(url: str, response) -> bool:
    if not _is_api_page(url, ""):
        return False
    return response is None or response.status in (401, 403, 404, 419, 440)


async def _capture_auth_check_snapshot(page, login_url: str) -> dict | None:
    try:
        if await _page_requires_login(page, login_url):
            return None
    except Exception:
        return None
    try:
        title = await page.title()
    except Exception:
        title = ""
    try:
        text = await page.evaluate("() => document.body.innerText")
    except Exception:
        text = ""
    if not text.strip() or _looks_like_login_text(text):
        return None
    return {
        "url": page.url,
        "title": title or "",
        "text": text[:5000],
    }


async def _auth_check_still_authenticated(
    page,
    snapshot: dict | None,
    login_url: str,
    username: Optional[str],
) -> bool:
    if not snapshot or not snapshot.get("url"):
        return False
    check_page = None
    try:
        check_page = await page.context.new_page()
        response = await check_page.goto(
            snapshot["url"], wait_until="domcontentloaded", timeout=15_000
        )
        try:
            await check_page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            pass
        if _response_suggests_session_dropped(response) or await _page_requires_login(
            check_page, login_url
        ):
            return False
        try:
            title = await check_page.title()
        except Exception:
            title = ""
        try:
            text = await check_page.evaluate("() => document.body.innerText")
        except Exception:
            text = ""
        if not text.strip() or _looks_like_login_text(text):
            return False
        return _auth_check_matches_snapshot(snapshot, title, text)
    except Exception as exc:
        log.debug("Auth sanity check failed for user=%s: %s", username, exc)
        return False
    finally:
        if check_page is not None:
            try:
                await check_page.close()
            except Exception:
                pass


def _auth_check_matches_snapshot(snapshot: dict, title: str, text: str) -> bool:
    original_title = (snapshot.get("title") or "").strip().lower()
    candidate_title = (title or "").strip().lower()
    if original_title and candidate_title and original_title != candidate_title:
        return False

    original_tokens = _meaningful_text_tokens(snapshot.get("text") or "")
    candidate_tokens = _meaningful_text_tokens(text or "")
    if not original_tokens or not candidate_tokens:
        return False
    overlap = len(original_tokens & candidate_tokens)
    threshold = min(8, max(3, len(original_tokens) // 4))
    return overlap >= threshold


def _meaningful_text_tokens(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "you",
        "your",
        "are",
        "this",
        "that",
        "with",
        "from",
        "login",
        "logout",
        "sign",
        "menu",
        "home",
        "page",
        "click",
        "submit",
        "cancel",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", (text or "").lower()[:5000])
        if token not in stop
    }


# ── Authentication ────────────────────────────────────────────────────────────

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _detect_mfa_prompt(page) -> bool:
    """Return True if the page shows an MFA / OTP input field."""
    otp_selectors = [
        "input[name*='otp' i]",
        "input[id*='otp' i]",
        "input[name*='mfa' i]",
        "input[id*='mfa' i]",
        "input[name*='2fa' i]",
        "input[id*='2fa' i]",
        "input[name*='code' i]",
        "input[id*='code' i]",
        "input[placeholder*='code' i]",
        "input[placeholder*='otp' i]",
        "input[placeholder*='authenticator' i]",
        "input[autocomplete='one-time-code']",
    ]
    for sel in otp_selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                return True
        except Exception:
            pass
    return False


async def _fill_totp_if_prompted(page, credential) -> None:
    """If an MFA prompt is visible, generate and fill the TOTP code."""
    if not await _detect_mfa_prompt(page):
        return
    if not credential.totp_seed:
        log.warning(
            "  _fill_totp: MFA prompt detected but no totp_seed set for %s",
            credential.username,
        )
        return
    try:
        import pyotp

        code = pyotp.TOTP(credential.totp_seed).now()
    except Exception as exc:
        log.warning("  _fill_totp: could not generate TOTP code: %s", exc)
        return

    otp_selectors = [
        "input[autocomplete='one-time-code']",
        "input[name*='otp' i]",
        "input[id*='otp' i]",
        "input[name*='code' i]",
        "input[id*='code' i]",
        "input[name*='mfa' i]",
        "input[id*='mfa' i]",
        "input[placeholder*='code' i]",
    ]
    filled = False
    for sel in otp_selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.fill(code)
                filled = True
                break
        except Exception:
            pass

    if not filled:
        log.warning(
            "  _fill_totp: could not locate OTP input field for %s", credential.username
        )
        return

    # Submit the MFA form
    for sel in [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Verify')",
        "button:has-text('Submit')",
        "button:has-text('Next')",
        "button:has-text('Sign in')",
    ]:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click()
                break
        except Exception:
            pass

    try:
        await page.wait_for_load_state("networkidle", timeout=12_000)
    except Exception:
        pass
    await page.wait_for_timeout(1000)
    log.info("  _fill_totp: TOTP code filled and submitted for %s", credential.username)


async def _authenticate_guided(page, login_url: str, credential, run_id: int) -> None:
    """Open a headed browser window so the user can log in interactively.

    Captures cookies from the headed session and injects them into the
    headless crawl context.  Emits a ``guided_login_required`` SSE event so
    the web UI can show the "I'm Done" button.

    When multiple credentials use guided mode, browsers open one at a time so
    the user always knows which account to log in as.

    Requires a graphical display.  On headless servers, raises RuntimeError
    with instructions to use ``seed`` mode instead.
    """
    has_display = (
        sys.platform == "darwin"
        or bool(os.environ.get("DISPLAY"))
        or bool(os.environ.get("WAYLAND_DISPLAY"))
    )
    if not has_display:
        events_svc.emit(
            run_id,
            {
                "type": "guided_login_failed",
                "credential_id": credential.id,
                "username": credential.username,
                "message": (
                    f"Guided login for '{credential.username}' requires a graphical display. "
                    "This scanner appears to be running on a headless host. "
                    "Guided browser login only works when the scanner is running locally with a GUI."
                ),
            },
        )
        log.warning(
            "  _authenticate_guided: no display available for '%s' (cred_id=%s) — skipping",
            credential.username,
            credential.id,
        )
        return

    # Acquire the per-run lock so only one guided browser opens at a time
    if run_id not in _guided_locks:
        _guided_locks[run_id] = asyncio.Lock()
    async with _guided_locks[run_id]:
        ready_event = asyncio.Event()
        done_event = asyncio.Event()
        _guided_ready_registry[credential.id] = ready_event
        _guided_registry[credential.id] = done_event

        # Phase 1: notify the UI — browser is NOT yet open; user must click "I'm Ready" first
        events_svc.emit(
            run_id,
            {
                "type": "guided_login_required",
                "credential_id": credential.id,
                "username": credential.username,
                "message": (
                    f"Login required for '{credential.username}'. "
                    'Click "I\'m Ready" in the UI when you are ready to log in.'
                ),
            },
        )

        log.info(
            "  _authenticate_guided: waiting for ready signal from UI for %s (cred_id=%s)",
            credential.username,
            credential.id,
        )

        # Wait for user to click "I'm Ready" (5 min timeout)
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=300)
        except asyncio.TimeoutError:
            log.warning(
                "  _authenticate_guided: timed out waiting for ready signal (cred_id=%s)",
                credential.id,
            )
            _guided_ready_registry.pop(credential.id, None)
            _guided_registry.pop(credential.id, None)
            return
        _guided_ready_registry.pop(credential.id, None)

        # Phase 2: open the browser and let the user log in
        events_svc.emit(
            run_id,
            {
                "type": "guided_login_browser_open",
                "credential_id": credential.id,
                "username": credential.username,
            },
        )

        log.info(
            "  _authenticate_guided: opening browser for %s (cred_id=%s)",
            credential.username,
            credential.id,
        )

        captured_cookies: list = []
        captured_headers: dict[str, str] = {}

        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=False)
            try:
                ctx = await browser.new_context(
                    user_agent=_UA, ignore_https_errors=True
                )

                # Capture any Authorization headers sent during navigation
                async def _capture_auth_header(request) -> None:
                    auth = request.headers.get("authorization")
                    if auth and not captured_headers.get("Authorization"):
                        captured_headers["Authorization"] = auth

                ctx.on("request", _capture_auth_header)

                guided_page = await ctx.new_page()
                try:
                    await guided_page.goto(
                        login_url, wait_until="domcontentloaded", timeout=15_000
                    )
                except Exception as nav_err:
                    log.warning(
                        "  _authenticate_guided: initial navigation error: %s", nav_err
                    )

                # Wait for user to confirm (5 min timeout)
                try:
                    await asyncio.wait_for(done_event.wait(), timeout=300)
                except asyncio.TimeoutError:
                    log.warning(
                        "  _authenticate_guided: timed out waiting for user confirmation (cred_id=%s)",
                        credential.id,
                    )

                # Brief pause so any in-flight auth redirects / cookie-sets finish
                # before we snapshot the context's cookies.
                await asyncio.sleep(1.5)
                captured_cookies = await ctx.cookies()
                log.info(
                    "  _authenticate_guided: captured %d cookie(s) for %s",
                    len(captured_cookies),
                    credential.username,
                )

                # Capture ALL localStorage and sessionStorage from every open page
                # in the context (not just known key names) so SPAs that store tokens
                # under arbitrary keys are handled correctly.
                captured_local_storage: dict[str, str] = {}
                captured_session_storage: dict[str, str] = {}
                try:
                    captured_local_storage = (
                        await guided_page.evaluate(
                            "() => Object.fromEntries(Object.entries(localStorage))"
                        )
                        or {}
                    )
                except Exception:
                    pass
                try:
                    captured_session_storage = (
                        await guided_page.evaluate(
                            "() => Object.fromEntries(Object.entries(sessionStorage))"
                        )
                        or {}
                    )
                except Exception:
                    pass
                log.info(
                    "  _authenticate_guided: captured %d localStorage + %d sessionStorage "
                    "entries for %s",
                    len(captured_local_storage),
                    len(captured_session_storage),
                    credential.username,
                )

                # Heuristic: pick the most likely bearer token from storage to use
                # as an Authorization header for httpx / non-browser requests.
                _bearer_keys = [
                    "access_token",
                    "accessToken",
                    "token",
                    "jwt",
                    "id_token",
                    "idToken",
                    "auth_token",
                    "authToken",
                    "bearer_token",
                ]
                _all_storage = {**captured_session_storage, **captured_local_storage}
                for _sk in _bearer_keys:
                    _sv = _all_storage.get(_sk)
                    if _sv and not captured_headers.get("Authorization"):
                        captured_headers["Authorization"] = f"Bearer {_sv}"
                        log.info(
                            "  _authenticate_guided: found token in storage key '%s' for %s",
                            _sk,
                            credential.username,
                        )
                        break
                # If no known key matched, fall back to any value that looks like a JWT
                if not captured_headers.get("Authorization"):
                    for _sk, _sv in _all_storage.items():
                        if (
                            isinstance(_sv, str)
                            and _sv.startswith("eyJ")
                            and _sv.count(".") >= 2
                        ):
                            captured_headers["Authorization"] = f"Bearer {_sv}"
                            log.info(
                                "  _authenticate_guided: JWT-shaped value found in storage key '%s' for %s",
                                _sk,
                                credential.username,
                            )
                            break
            finally:
                await browser.close()
                _guided_registry.pop(credential.id, None)
                _guided_ready_registry.pop(credential.id, None)

        # Build the injectable list regardless of whether cookies were captured.
        # We always write to the cache so subsequent _authenticate calls for this
        # credential don't open another window (even if capture failed).
        #
        # Normalisation is critical: Playwright's ctx.cookies() returns fields that
        # add_cookies rejects — leading-dot domains (".localhost"), expires=-1 for
        # session cookies, and sameSite values outside {"Strict","Lax","None"}.
        # Using "url" instead of "domain"+"path" is the most reliable injection form.
        injectable = []
        _valid_samesite = {"Strict", "Lax", "None"}
        for c in captured_cookies:
            if not isinstance(c, dict) or not c.get("name") or "value" not in c:
                continue
            entry: dict = {"name": c["name"], "value": c["value"], "url": login_url}
            # Optional fields — only include when they are valid
            if c.get("httpOnly"):
                entry["httpOnly"] = True
            if c.get("secure"):
                entry["secure"] = True
            ss = c.get("sameSite")
            if ss in _valid_samesite:
                entry["sameSite"] = ss
            exp = c.get("expires")
            if exp is not None and isinstance(exp, (int, float)) and exp > 0:
                entry["expires"] = int(exp)
            injectable.append(entry)
        log.info(
            "  _authenticate_guided: built %d injectable cookie(s) from %d captured for %s",
            len(injectable),
            len(captured_cookies),
            credential.username,
        )

        if not injectable and not captured_headers.get("Authorization"):
            log.warning(
                "  _authenticate_guided: no injectable cookies and no bearer token for %s — "
                "session capture may have failed. The headless crawl will proceed "
                "unauthenticated for this credential.",
                credential.username,
            )
            events_svc.emit(
                run_id,
                {
                    "type": "scanner_phase",
                    "phase": "guided_login_warning",
                    "status": "warning",
                    "message": (
                        f"No session cookies were captured for '{credential.username}' "
                        "after guided login. The crawl for this credential may be "
                        "unauthenticated. Try again or use 'guided' mode and complete the "
                        "login fully before clicking I'm Done."
                    ),
                },
            )

        if injectable:
            try:
                await page.context.add_cookies(injectable)
                # Verify injection actually worked by reading cookies back
                _verify = await page.context.cookies()
                _injected_names = {ck["name"] for ck in _verify}
                _expected_names = {e["name"] for e in injectable}
                _missing = _expected_names - _injected_names
                if _missing:
                    log.warning(
                        "  _authenticate_guided: %d cookie(s) missing after injection for %s: %s",
                        len(_missing),
                        credential.username,
                        _missing,
                    )
                else:
                    log.info(
                        "  _authenticate_guided: verified %d cookie(s) in context for %s",
                        len(_injected_names & _expected_names),
                        credential.username,
                    )
            except Exception as exc:
                log.warning(
                    "  _authenticate_guided: add_cookies failed for %s: %s",
                    credential.username,
                    exc,
                )

        if captured_headers:
            try:
                await page.context.set_extra_http_headers(captured_headers)
            except Exception as exc:
                log.warning(
                    "  _authenticate_guided: could not set extra headers: %s", exc
                )

        # Reload so the headless context picks up the injected cookies,
        # then restore localStorage and sessionStorage from the headed session.
        try:
            await page.reload(wait_until="domcontentloaded", timeout=12_000)
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass
        if captured_local_storage:
            try:
                await page.evaluate(
                    "(entries) => { for (const [k,v] of Object.entries(entries)) "
                    "localStorage.setItem(k, v); }",
                    captured_local_storage,
                )
                log.info(
                    "  _authenticate_guided: restored %d localStorage entries for %s",
                    len(captured_local_storage),
                    credential.username,
                )
            except Exception as exc:
                log.warning(
                    "  _authenticate_guided: localStorage restore failed: %s", exc
                )
        if captured_session_storage:
            try:
                await page.evaluate(
                    "(entries) => { for (const [k,v] of Object.entries(entries)) "
                    "sessionStorage.setItem(k, v); }",
                    captured_session_storage,
                )
                log.info(
                    "  _authenticate_guided: restored %d sessionStorage entries for %s",
                    len(captured_session_storage),
                    credential.username,
                )
            except Exception as exc:
                log.warning(
                    "  _authenticate_guided: sessionStorage restore failed: %s", exc
                )

        events_svc.emit(
            run_id,
            {
                "type": "guided_login_confirmed",
                "credential_id": credential.id,
                "username": credential.username,
                "cookie_count": len(injectable),
            },
        )
        # Cache the captured session so reconcile and the dynamic scan can reuse it without a second window
        _guided_session_cache[(run_id, credential.id)] = {
            "cookies": {
                c["name"]: c["value"]
                for c in captured_cookies
                if "name" in c and "value" in c
            },
            "headers": captured_headers,
            "injectable": injectable,
            "local_storage": captured_local_storage,
            "session_storage": captured_session_storage,
        }
        # Persist to session vault DB so the dynamic scan phase can load it via load_session_vault()
        try:
            from aespa.services import scanner_sessions as _ss

            _ss.upsert_session(
                run_id,
                label=f"guided_{credential.id}",
                kind="cookie",
                username=credential.username,
                credential_id=credential.id,
                source="guided_login",
                cookies=_guided_session_cache[(run_id, credential.id)]["cookies"],
                extra_headers=captured_headers or None,
            )
        except Exception as _vs_exc:
            log.warning(
                "  _authenticate_guided: could not persist session to vault: %s",
                _vs_exc,
            )


async def _authenticate(
    page, login_url: str, credential, run_id: int = 0, llm_cfg=None
) -> None:
    """Dispatch to the correct auth strategy based on ``credential.auth_mode``.

    For guided credentials that already have a cached session (from the crawl
    phase), cookies are injected directly without opening a new browser window.

    When ``llm_cfg`` is supplied and the deterministic auto/totp login fails to
    clear the login form, falls back to the LLM-driven adaptive login
    (``_authenticate_smart``) which can handle modal/no-route, non-standard and
    multi-step login flows.
    """
    mode = getattr(credential, "auth_mode", None) or AuthMode.auto
    try:
        mode = AuthMode(mode)
    except ValueError:
        mode = AuthMode.auto

    # If this is a guided credential with a pre-captured session, inject directly
    if mode == AuthMode.guided and run_id:
        cached = _guided_session_cache.get((run_id, credential.id))
        if cached:
            log.info(
                "  _authenticate: reusing cached guided session for %s (cred_id=%s)",
                credential.username,
                credential.id,
            )
            # Re-build from the flat cookies dict using url-based format (most reliable)
            cookies_dict = cached.get("cookies") or {}
            if cookies_dict:
                cookie_list = [
                    {"name": k, "value": v, "url": login_url}
                    for k, v in cookies_dict.items()
                ]
                try:
                    await page.context.add_cookies(cookie_list)
                    log.info(
                        "  _authenticate: injected %d cached cookie(s) for %s",
                        len(cookie_list),
                        credential.username,
                    )
                except Exception as exc:
                    log.warning(
                        "  _authenticate: could not inject cached cookies: %s", exc
                    )
            if cached.get("headers"):
                try:
                    await page.context.set_extra_http_headers(cached["headers"])
                except Exception as exc:
                    log.warning(
                        "  _authenticate: could not set cached headers: %s", exc
                    )
            try:
                await page.reload(wait_until="domcontentloaded", timeout=12_000)
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass
            # Restore localStorage and sessionStorage
            if cached.get("local_storage"):
                try:
                    await page.evaluate(
                        "(entries) => { for (const [k,v] of Object.entries(entries)) "
                        "localStorage.setItem(k, v); }",
                        cached["local_storage"],
                    )
                except Exception as exc:
                    log.warning("  _authenticate: localStorage restore failed: %s", exc)
            if cached.get("session_storage"):
                try:
                    await page.evaluate(
                        "(entries) => { for (const [k,v] of Object.entries(entries)) "
                        "sessionStorage.setItem(k, v); }",
                        cached["session_storage"],
                    )
                except Exception as exc:
                    log.warning(
                        "  _authenticate: sessionStorage restore failed: %s", exc
                    )
            return

    username = getattr(credential, "username", "?")
    if mode in (AuthMode.auto, AuthMode.totp):
        _crawl_log(run_id, "auth", "start", f"Authenticating as {username}…")

    if mode == AuthMode.totp:
        await _authenticate_auto(page, login_url, credential)
        await _fill_totp_if_prompted(page, credential)
    elif mode == AuthMode.guided:
        await _authenticate_guided(page, login_url, credential, run_id)
        return
    else:
        await _authenticate_auto(page, login_url, credential)

    # Smart fallback: if the deterministic heuristic failed to clear the login
    # form, let the LLM figure the login out (modal/no-route, odd fields, multi-step).
    if llm_cfg is not None:
        try:
            still_blocked = await _page_requires_login(page, login_url)
        except Exception:
            still_blocked = False
        if still_blocked:
            await _authenticate_smart(page, login_url, credential, run_id, llm_cfg)

    # Report the auth outcome to the Activity Log.
    if mode in (AuthMode.auto, AuthMode.totp):
        try:
            blocked = await _page_requires_login(page, login_url)
        except Exception:
            blocked = False
        if blocked:
            _crawl_log(
                run_id,
                "auth",
                "error",
                f"Could not log in as {username} — login form still present",
            )
        else:
            _crawl_log(run_id, "auth", "complete", f"Logged in as {username}")


# Elements that open a modal/drawer login form on pages with no dedicated
# login route. Tried in order; first visible one is clicked.
_LOGIN_TRIGGER_SELECTORS = [
    "a:has-text('Log in')",
    "button:has-text('Log in')",
    "a:has-text('Sign in')",
    "button:has-text('Sign in')",
    "a:has-text('Login')",
    "button:has-text('Login')",
    "a[href*='login' i]",
    "[class*='login' i]",
    "[id*='login' i]",
]


async def _reveal_login_form(page) -> None:
    """Click a login trigger to reveal a modal login form, if no form is visible.

    Handles sites where the login dialog has no URL route — navigating to the
    login_url lands on an ordinary page and the form only appears after clicking
    a "Log in"/"Sign in" control. No-op (cheap) when a form is already present.
    """
    try:
        pw = page.locator("input[type='password']").first
        if await pw.count() > 0 and await pw.is_visible():
            return
    except Exception:
        return

    for sel in _LOGIN_TRIGGER_SELECTORS:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click()
                await page.wait_for_timeout(800)
                log.info("  _authenticate: clicked login trigger %r", sel)
                return
        except Exception:
            pass


async def _authenticate_auto(page, login_url: str, credential) -> None:
    """Best-effort form-based login."""
    try:
        await page.goto(login_url, wait_until="domcontentloaded", timeout=15_000)
        try:
            await page.wait_for_selector("input", state="visible", timeout=8_000)
        except Exception:
            log.warning("  _authenticate: no <input> visible at %s", login_url)
        await page.wait_for_timeout(300)

        # Modal logins with no URL route: reveal the form before looking for fields.
        await _reveal_login_form(page)

        # Fill username
        username_filled = False
        for sel in [
            "input[autocomplete='username']",
            "input[autocomplete='email']",
            "input[type='email']",
            "input[name*='user' i]",
            "input[name*='email' i]",
            "input[id*='user' i]",
            "input[id*='email' i]",
            "input[type='text']",
        ]:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.fill(credential.username)
                    username_filled = True
                    break
            except Exception:
                pass

        if not username_filled:
            log.warning("  _authenticate: could not find username field")
            return

        # Reveal password field if hidden
        pass_loc = page.locator("input[type='password']").first
        if not (await pass_loc.count() > 0 and await pass_loc.is_visible()):
            for sel in [
                "button:has-text('Next')",
                "button:has-text('Continue')",
                "button[type='submit']",
            ]:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        await loc.click()
                        await page.wait_for_timeout(800)
                        break
                except Exception:
                    pass

        # Fill password
        try:
            pass_loc = page.locator("input[type='password']").first
            if await pass_loc.count() > 0 and await pass_loc.is_visible():
                await pass_loc.fill(credential.password)
        except Exception:
            pass

        # Submit
        submitted = False
        for sel in [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Log in')",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
            "button:has-text('Submit')",
            "button:has-text('Continue')",
        ]:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.click()
                    submitted = True
                    break
            except Exception:
                pass

        if not submitted:
            log.warning("  _authenticate: could not find submit button")

        try:
            await page.wait_for_load_state("networkidle", timeout=12_000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        try:
            pw_visible = (
                await page.locator("input[type='password']").first.count() > 0
                and await page.locator("input[type='password']").first.is_visible()
            )
        except Exception:
            pw_visible = False

        if pw_visible:
            log.warning(
                "  _authenticate: password field still visible — auth likely failed. page.url=%s",
                page.url,
            )
        else:
            log.info(
                "  _authenticate: success — login form gone. page.url=%s", page.url
            )

    except Exception as auth_err:
        log.warning("  _authenticate: exception: %s", auth_err)


# ── LLM-driven adaptive login fallback ────────────────────────────────────────
# Used when the deterministic _authenticate_auto heuristic fails (login form
# still present). Observes the page and lets the LLM drive the login one action
# at a time, handling modal/no-route logins, non-standard fields and multi-step
# flows that the hardcoded selector lists cannot.

_SMART_LOGIN_MAX_STEPS = 6


async def _build_login_observation(page) -> str:
    """Render a compact text snapshot of forms + clickable controls for the LLM.

    Reuses _extract_dom_intelligence for form/field structure and adds the
    visible buttons/links a login flow might need to click.
    """
    dom = await _extract_dom_intelligence(page)
    lines: list[str] = []

    forms = dom.get("forms") or []
    if forms:
        lines.append("Forms:")
        for form in forms[:6]:
            lines.append(f"  form {form.get('selector', '')}:")
            for fld in (form.get("fields") or [])[:25]:
                desc = ", ".join(
                    f"{k}={v}"
                    for k, v in (
                        ("type", fld.get("type")),
                        ("name", fld.get("name")),
                        ("id", fld.get("id")),
                        ("autocomplete", fld.get("autocomplete")),
                        ("placeholder", fld.get("placeholder")),
                    )
                    if v
                )
                lines.append(f"    - {fld.get('selector', '')}  [{desc}]")
    else:
        lines.append("Forms: (none found)")

    try:
        controls = await page.evaluate(
            """() => Array.from(document.querySelectorAll(
                 "button, a, [role='button'], input[type='submit']"))
               .filter(el => el.offsetParent !== null)
               .slice(0, 40)
               .map(el => ({
                 tag: el.tagName.toLowerCase(),
                 text: (el.innerText || el.value || el.getAttribute('aria-label')
                        || el.getAttribute('title') || '').trim().slice(0, 60),
                 id: el.id || '',
                 sel: el.id ? '#' + CSS.escape(el.id) : '',
               }))
               .filter(c => c.text || c.id)"""
        )
    except Exception:
        controls = []

    if controls:
        lines.append("Clickable controls:")
        for c in controls:
            label = c.get("text") or c.get("id") or ""
            sel = c.get("sel") or ""
            lines.append(
                f"  - <{c.get('tag')}> {label!r}{f'  sel={sel}' if sel else ''}"
            )

    return "\n".join(lines)


async def _apply_login_substitutions(value: str, credential) -> str:
    """Replace {{username}}/{{password}} tokens with the real credential locally."""
    value = value.replace("{{username}}", credential.username or "")
    value = value.replace("{{password}}", credential.password or "")
    return value


async def _locate_login_target(page, action: dict):
    """Resolve a Playwright locator from an action's selector, falling back to text."""
    selector = (action.get("selector") or "").strip()
    if selector:
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                return loc
        except Exception:
            pass
    text = (action.get("text") or "").strip()
    if text:
        try:
            loc = page.get_by_text(text, exact=False).first
            if await loc.count() > 0:
                return loc
        except Exception:
            pass
    return None


async def _authenticate_smart(
    page, login_url: str, credential, run_id: int, llm_cfg
) -> None:
    """LLM-driven login loop: observe → decide → act → re-check, up to N steps.

    Best-effort: never raises. Stops on success (login form gone), on the LLM's
    done/give_up, or when the step budget is exhausted. Logs reasons only — never
    credential values.
    """
    if llm_cfg is None:
        return

    log.info(
        "  _authenticate_smart: heuristic login failed for %s — trying LLM-driven login",
        getattr(credential, "username", "?"),
    )
    events_svc.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": "crawler",
            "role": "Crawler",
            "status": "active",
            "current_task": f"Figuring out the login form for {credential.username}…",
            "outcome": None,
        },
    )
    _crawl_log(
        run_id,
        "auth",
        "info",
        f"Standard login failed for {credential.username} — using AI to work out "
        "the login form",
    )

    history: list[str] = []
    use_vision = bool(getattr(llm_cfg, "use_vision", False))

    for step in range(_SMART_LOGIN_MAX_STEPS):
        try:
            observation = await _build_login_observation(page)
        except Exception as exc:
            log.warning("  _authenticate_smart: observation failed: %s", exc)
            return

        screenshot_b64 = None
        if use_vision:
            try:
                raw = await page.screenshot(type="png", full_page=False)
                screenshot_b64 = base64.b64encode(raw).decode()
            except Exception:
                screenshot_b64 = None

        try:
            action = await llm_svc.decide_login_action(
                llm_cfg,
                url=page.url,
                observation=observation,
                username_hint=credential.username,
                history=history,
                screenshot_b64=screenshot_b64,
            )
        except Exception as exc:
            log.warning("  _authenticate_smart: LLM call failed: %s", exc)
            return

        name = action.get("action")
        reason = action.get("reason") or ""
        log.info("  _authenticate_smart: step %d → %s (%s)", step + 1, name, reason)
        _crawl_log(
            run_id,
            "auth",
            "info",
            f"AI login step {step + 1}: {name}" + (f" — {reason}" if reason else ""),
        )

        if name == "done":
            history.append(f"done: {reason}")
            break
        if name == "give_up":
            log.info("  _authenticate_smart: LLM gave up — %s", reason)
            history.append(f"give_up: {reason}")
            break

        try:
            if name == "press":
                target = await _locate_login_target(page, action)
                key = (action.get("value") or "Enter").strip() or "Enter"
                if target is not None:
                    await target.press(key)
                else:
                    await page.keyboard.press(key)
                history.append(f"pressed {key}")
            elif name == "click":
                target = await _locate_login_target(page, action)
                if target is None:
                    history.append(f"click target not found ({reason})")
                else:
                    await target.click(timeout=5_000)
                    history.append(f"clicked: {reason}")
            elif name == "fill":
                target = await _locate_login_target(page, action)
                if target is None:
                    history.append(f"fill target not found ({reason})")
                else:
                    value = await _apply_login_substitutions(
                        action.get("value") or "", credential
                    )
                    await target.fill(value)
                    # Record which credential token was used, never the value.
                    token = (
                        "username"
                        if "{{username}}" in (action.get("value") or "")
                        else "password"
                        if "{{password}}" in (action.get("value") or "")
                        else "text"
                    )
                    history.append(f"filled {token} field ({reason})")
        except Exception as exc:
            log.warning("  _authenticate_smart: action %s failed: %s", name, exc)
            history.append(f"{name} errored: {exc}")

        try:
            await page.wait_for_timeout(900)
        except Exception:
            pass

        # Success check: login form gone.
        try:
            if not await _page_requires_login(page, login_url):
                log.info(
                    "  _authenticate_smart: success — login form gone. page.url=%s",
                    page.url,
                )
                return
        except Exception:
            pass

    if await _page_requires_login(page, login_url):
        log.warning(
            "  _authenticate_smart: could not complete login for %s after %d steps",
            credential.username,
            _SMART_LOGIN_MAX_STEPS,
        )
