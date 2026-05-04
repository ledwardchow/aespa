from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, urlunparse

log = logging.getLogger("aespa.crawler")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, PageCredentialView, PageLink, TestRun, TestRunStatus
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import traffic as traffic_svc
from aespa.services.settings import get_llm_config

# ── In-memory state ───────────────────────────────────────────────────────────

_stop_requested: set[int] = set()
_active_tasks: dict[int, asyncio.Task] = {}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def request_stop(run_id: int) -> None:
    _stop_requested.add(run_id)


def is_running(run_id: int) -> bool:
    return run_id in _active_tasks


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Public entry point ────────────────────────────────────────────────────────

async def start_crawl(run_id: int) -> None:
    if run_id in _active_tasks:
        return
    task = asyncio.create_task(_crawl_task(run_id), name=f"crawl-{run_id}")
    _active_tasks[run_id] = task
    task.add_done_callback(lambda _: _active_tasks.pop(run_id, None))


# ── Task wrapper ──────────────────────────────────────────────────────────────

async def _crawl_task(run_id: int) -> None:
    try:
        await _do_crawl(run_id)
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
    def __init__(self, crawled_norms: dict, pages_done: int) -> None:
        self.crawled_norms: dict[str, int] = crawled_norms  # norm_url → page_id
        self.lock: asyncio.Lock = asyncio.Lock()
        self.pages_done: int = pages_done


# ── Core orchestrator ─────────────────────────────────────────────────────────

async def _do_crawl(run_id: int) -> None:
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        from aespa.models import Site
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config(s)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration found. Configure it in Settings first.")
        creds = list(site.credentials)
        for obj in [*creds, site, llm_cfg, run]:
            s.expunge(obj)

    base_url      = site.base_url.rstrip("/")
    login_url     = site.login_url or ""
    requires_auth = site.requires_auth
    max_depth     = run.max_depth
    max_pages     = run.max_pages
    _parsed       = urlparse(base_url)
    base_netloc   = _parsed.netloc
    _bp           = _parsed.path
    base_path: str = (_bp if _bp.endswith("/") else _bp + "/") if _bp else "/"

    log.info("=== Crawl start: run_id=%s base_url=%s max_depth=%s max_pages=%s creds=%d ===",
             run_id, base_url, max_depth, max_pages, len(creds))

    with Session(get_engine()) as s:
        existing = s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
        for ep in existing:
            s.expunge(ep)

    shared = _CrawlShared(
        crawled_norms={_norm(ep.url): ep.id for ep in existing},
        pages_done=len(existing),
    )

    _update_run(run_id, status=TestRunStatus.running, started_at=_utcnow(),
                completed_at=None, error_message=None,
                pages_discovered=shared.pages_done, current_url=base_url,
                per_user_progress=None)

    phases = creds if (requires_auth and creds) else [None]

    tasks = [
        asyncio.create_task(
            _crawl_as_credential(
                run_id=run_id, cred=cred, shared=shared,
                base_url=base_url, login_url=login_url,
                requires_auth=requires_auth, max_depth=max_depth,
                max_pages=max_pages, llm_cfg=llm_cfg,
                base_netloc=base_netloc, base_path=base_path,
                phase_idx=idx, total_phases=len(phases),
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
    )

    # OR-merge page categories from all credential views into each CrawledPage.
    _merge_all_categories(run_id)

    final_status = TestRunStatus.stopped if run_id in _stop_requested else TestRunStatus.complete
    log.info("=== Crawl done: run_id=%s status=%s pages=%d ===",
             run_id, final_status, shared.pages_done)
    _update_run(run_id, status=final_status, completed_at=_utcnow(),
                current_url=None, pages_discovered=shared.pages_done)
    events_svc.emit(run_id, {
        "type": "run_update", "status": final_status,
        "pages_discovered": shared.pages_done, "current_url": None,
    })


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
    llm_cfg,
    base_netloc: str,
    base_path: str,
    phase_idx: int,
    total_phases: int,
) -> None:
    from playwright.async_api import async_playwright

    username      = cred.username if cred else None
    credential_id = cred.id if cred else None

    log.info("=== Phase %d/%d: user=%s ===", phase_idx + 1, total_phases, username or "anonymous")
    events_svc.emit(run_id, {
        "type": "crawl_phase",
        "phase": phase_idx + 1,
        "total_phases": total_phases,
        "username": username,
    })

    local_pages = 0  # pages actually navigated to by this credential

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=_UA,
            ignore_https_errors=True,
        )
        traffic_svc.setup_playwright_logging(ctx, run_id, username=username)
        page = await ctx.new_page()

        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=20_000)
        except Exception as e:
            log.warning("Pre-load failed for user=%s: %s", username, e)

        if requires_auth and cred:
            log.info("Authenticating as %s", cred.username)
            await _authenticate(page, login_url, cred)

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
                elif shared.pages_done >= max_pages or depth > max_depth:
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
            events_svc.emit(run_id, {
                "type": "crawl_progress",
                "username": username,
                "pages_visited": local_pages,
                "current_url": url,
            })

            # ── Navigate ──────────────────────────────────────────────────────
            try:
                resp = await _goto_with_auth_recovery(
                    page, url,
                    requires_auth=requires_auth,
                    credential=cred,
                    login_url=login_url,
                    username=username,
                )
            except Exception as nav_err:
                if is_first:
                    _update_page(page_id, status="failed", error_message=str(nav_err)[:500])
                continue

            if resp is not None and resp.status >= 400:
                if is_first:
                    _update_page(page_id, status="failed",
                                 error_message=f"HTTP {resp.status}")
                continue

            # ── SPA URL guard + redirect deduplication ────────────────────────
            raw_final = page.url
            if _same_domain(raw_final, base_netloc) and not _in_base_scope(raw_final, base_netloc, base_path):
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
            on_login = await _page_requires_login(page, login_url)

            if on_login:
                if is_first:
                    _update_page(page_id, status="crawled")
                log.debug("  Login form for %s (user=%s) — inaccessible", final_url, username)
                continue

            # ── Content extraction ────────────────────────────────────────────
            await page.wait_for_timeout(2000)
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

            # ── LLM analysis ──────────────────────────────────────────────────
            cats: dict = {
                "req_auth": None, "takes_input": None,
                "has_object_ref": None, "has_business_logic": None,
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
                    log.info("  LLM ok for %s (user=%s) cats=%s", final_url, username, cats)
                except Exception as e:
                    log.warning("  LLM failed for %s: %s", final_url, e)
                    context = f"[LLM failed: {e}]"

            # ── Persist per-credential view ───────────────────────────────────
            _save_credential_view(
                page_id, run_id, credential_id, username,
                screenshot_b64, context, text[:10_000], cats,
            )
            _update_accessible_by(page_id, credential_id)

            # ── Update main CrawledPage if first to fill it ───────────────────
            with Session(get_engine()) as s:
                cp = s.get(CrawledPage, page_id)
                fill_main = cp is not None and cp.status in ("processing", "crawled") and not cp.title
                first_success = cp is not None and cp.status == "processing"

            if is_first or fill_main:
                _update_page(
                    page_id, url=final_url, title=title,
                    page_text=text[:10_000], screenshot_b64=screenshot_b64,
                    llm_context=context, status="crawled", depth=depth,
                    req_auth=cats["req_auth"], takes_input=cats["takes_input"],
                    has_object_ref=cats["has_object_ref"],
                    has_business_logic=cats["has_business_logic"],
                )
                if is_first:
                    _save_link(run_id, parent_id, page_id, final_url)

            # ── SSE ───────────────────────────────────────────────────────────
            with Session(get_engine()) as s:
                cp = s.get(CrawledPage, page_id)
                ab = json.loads(cp.accessible_by if cp else "[]")

            if is_first or first_success:
                events_svc.emit(run_id, {
                    "type": "page_added",
                    "username": username,
                    "node": {
                        "id": page_id, "url": final_url, "title": title,
                        "depth": depth, "status": "crawled",
                        "context": context, "in_scope": True,
                        "scan_status": "pending", "accessible_by": ab,
                    },
                    "link": {"source": parent_id, "target": page_id, "link_text": None}
                            if parent_id else None,
                })
            else:
                events_svc.emit(run_id, {
                    "type": "node_accessible_by",
                    "page_id": page_id, "username": username,
                })

            events_svc.emit(run_id, {
                "type": "run_update", "status": "running",
                "pages_discovered": shared.pages_done,
                "current_url": final_url, "username": username,
            })

            # ── Enqueue links ─────────────────────────────────────────────────
            if depth < max_depth:
                filtered_suggested = _filter_suggested_links(suggested, same_domain_links, base_netloc)
                if len(filtered_suggested) < len(suggested):
                    log.info(
                        "Dropped %d LLM-suggested crawl URL(s) that were not observed as page links for %s",
                        len(suggested) - len(filtered_suggested), final_url,
                    )
                for sugg_url in reversed(filtered_suggested):
                    n = _norm(sugg_url)
                    if n not in queued and _same_domain(sugg_url, base_netloc) and not _is_session_ending_url(sugg_url):
                        queued.add(n)
                        queue.appendleft((sugg_url, depth + 1, page_id))
                for link_url, link_text in same_domain_links:
                    n = _norm(link_url)
                    if n not in queued and _same_domain(link_url, base_netloc) and not _is_session_ending_url(link_url, link_text):
                        queued.add(n)
                        queue.append((link_url, depth + 1, page_id))

        await browser.close()

    events_svc.emit(run_id, {
        "type": "crawl_progress",
        "username": username,
        "pages_visited": local_pages,
        "current_url": None,
        "done": True,
    })


# ── DB helpers ────────────────────────────────────────────────────────────────

def _save_page_placeholder(run_id: int, url: str, depth: int) -> int:
    """Atomically create a stub CrawledPage and return its ID."""
    with Session(get_engine()) as s:
        cp = CrawledPage(
            test_run_id=run_id, url=url, depth=depth,
            status="processing", accessible_by="[]",
        )
        s.add(cp)
        s.commit()
        s.refresh(cp)
        s.expunge(cp)
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
    with Session(get_engine()) as s:
        existing = s.exec(
            select(PageCredentialView)
            .where(PageCredentialView.page_id == page_id)
            .where(PageCredentialView.credential_id == credential_id)
        ).first()
        if existing:
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
        )
        s.add(view)
        s.commit()


async def _reconcile_direct_access(
    *,
    run_id: int,
    creds: list,
    base_url: str,
    login_url: str,
    requires_auth: bool,
    llm_cfg,
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
            (p.id, p.url, p.title or "", p.page_text or "", json.loads(p.accessible_by or "[]"))
            for p in pages
            if p.id is not None and p.url
        ]

    if not page_rows:
        return

    log.info("Reconciling direct page access across %d credential(s)", len(creds))
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for cred in creds:
                if run_id in _stop_requested:
                    break
                ctx = await browser.new_context(user_agent=_UA, ignore_https_errors=True)
                traffic_svc.setup_playwright_logging(ctx, run_id, username=cred.username)
                page = await ctx.new_page()
                try:
                    try:
                        await page.goto(base_url, wait_until="domcontentloaded", timeout=20_000)
                    except Exception:
                        pass
                    await _authenticate(page, login_url, cred)

                    for page_id, page_url, page_title, page_text, accessible_by in page_rows:
                        if run_id in _stop_requested:
                            break
                        if cred.id in accessible_by:
                            continue
                        if _is_session_ending_url(page_url):
                            continue
                        accessible, title, text, screenshot_b64 = await _direct_load_accessible(
                            page,
                            page_url,
                            requires_auth=requires_auth,
                            credential=cred,
                            login_url=login_url,
                            username=cred.username,
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
                                cred.username, page_url, access_reason,
                            )
                            continue
                        log.info("  Direct access confirmed: user=%s page=%s", cred.username, page_url)
                        _save_credential_view(
                            page_id, run_id, cred.id, cred.username,
                            screenshot_b64,
                            f"[Direct access reconciliation] {access_reason}",
                            text[:10_000],
                            {},
                        )
                        _update_accessible_by(page_id, cred.id)
                        accessible_by.append(cred.id)
                        events_svc.emit(run_id, {
                            "type": "node_accessible_by",
                            "page_id": page_id,
                            "username": cred.username,
                        })
                finally:
                    await ctx.close()
        finally:
            await browser.close()


async def _direct_load_accessible(
    page,
    url: str,
    *,
    requires_auth: bool = False,
    credential=None,
    login_url: str = "",
    username: Optional[str] = None,
) -> tuple[bool, str, str, Optional[str]]:
    try:
        resp = await _goto_with_auth_recovery(
            page,
            url,
            requires_auth=requires_auth,
            credential=credential,
            login_url=login_url,
            username=username,
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
        return False, "The direct-load response contains an access failure or loading error message."
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
        log.warning("  LLM access reconciliation failed for %s as %s: %s", url, candidate_username, exc)
        return False, "Access reconciliation could not get a reliable LLM judgement."

    accessible = bool(verdict.get("accessible"))
    reasoning = str(verdict.get("reasoning") or "No reasoning returned.")[:1000]
    return accessible, reasoning


def _looks_like_login_text(text: str) -> bool:
    body = (text or "").lower()[:3000]
    login_hits = sum(
        1 for marker in ("login", "log in", "sign in", "password", "forgot password")
        if marker in body
    )
    denied_hits = sum(
        1 for marker in ("access denied", "forbidden", "unauthorized", "unauthorised")
        if marker in body
    )
    return login_hits >= 2 or denied_hits >= 1


def _looks_like_access_failure_text(text: str) -> bool:
    body = (text or "").lower()[:5000]
    return any(marker in body for marker in (
        "could not load", "couldn't load", "failed to load", "unable to load",
        "cannot load", "can't load", "not authorized", "not authorised",
        "unauthorized", "unauthorised", "access denied", "forbidden",
        "permission denied", "does not have access", "no access", "not found",
        "account not found", "details unavailable", "details could not be loaded",
    ))


def _looks_like_denied_or_login_wall_text(text: str) -> bool:
    body = (text or "").lower()[:3000]
    denied_hits = sum(
        1 for marker in (
            "access denied", "forbidden", "unauthorized", "unauthorised",
            "session expired", "session has expired",
        )
        if marker in body
    )
    if denied_hits:
        return True
    login_wall_hits = sum(
        1 for marker in (
            "login required", "please log in", "please sign in",
            "you must log in", "you must sign in", "authentication required",
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
                select(PageCredentialView).where(PageCredentialView.page_id == cp.id)
            ).all()
            if not views:
                continue
            for attr in ("req_auth", "takes_input", "has_object_ref", "has_business_logic"):
                vals = [getattr(v, attr) for v in views if getattr(v, attr) is not None]
                if vals:
                    setattr(cp, attr, any(vals))
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


def _save_link(run_id: int, source_id: Optional[int], target_id: int, target_url: str) -> None:
    if source_id is None:
        return
    with Session(get_engine()) as s:
        pl = PageLink(
            test_run_id=run_id,
            source_page_id=source_id,
            target_page_id=target_id,
            target_url=target_url,
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
    run_id: int, username: Optional[str], current_url: str, pages_visited: int
) -> None:
    """Persist per-credential crawl progress so the UI can read it on load/refresh."""
    if not username:
        return
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return
        progress = json.loads(run.per_user_progress or "{}")
        progress[username] = {"current_url": current_url, "pages_visited": pages_visited}
        run.per_user_progress = json.dumps(progress)
        s.add(run)
        s.commit()


def _clear_pages(run_id: int) -> None:
    with Session(get_engine()) as s:
        links = s.exec(select(PageLink).where(PageLink.test_run_id == run_id)).all()
        for l in links:
            s.delete(l)
        views = s.exec(
            select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)
        ).all()
        for v in views:
            s.delete(v)
        pages = s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
        for p in pages:
            s.delete(p)
        s.commit()


# ── URL utilities ─────────────────────────────────────────────────────────────

def _norm(url: str) -> str:
    try:
        p = urlparse(url)
        path = p.path.rstrip("/") or "/"
        frag = p.fragment if p.fragment.startswith("/") else ""
        return urlunparse((p.scheme.lower(), p.netloc.lower(), path, p.params, p.query, frag))
    except Exception:
        return url


def _same_domain(url: str, base_netloc: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and parsed.netloc.lower() == base_netloc.lower()
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
    if any(pat in path for pat in ("/api/", "/v1/", "/v2/", "/v3/", "/rest/", "/graphql", "/swagger", "/openapi")):
        return True
    stripped = (text or "").lstrip()
    return len(stripped) > 2 and stripped[0] in ("{", "[")


def _is_session_ending_url(url: str, link_text: str | None = None) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        parsed = None
    haystack = " ".join([
        (parsed.path if parsed else url) or "",
        (parsed.query if parsed else "") or "",
        link_text or "",
    ]).lower()
    compact = "".join(ch for ch in haystack if ch.isalnum())
    return any(marker in compact for marker in (
        "logout", "signout", "signoff", "logoff",
        "endsession", "destroysession", "invalidatesession",
    ))


def _same_url_without_fragment(left: str, right: str) -> bool:
    try:
        l = urlparse(left)
        r = urlparse(right)
        return (
            l.scheme.lower(), l.netloc.lower(), l.path.rstrip("/") or "/", l.query,
        ) == (
            r.scheme.lower(), r.netloc.lower(), r.path.rstrip("/") or "/", r.query,
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
):
    response = None
    for attempt in range(2):
        response = await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass
        if not requires_auth or credential is None or not login_url:
            return response
        session_dropped = _response_suggests_session_dropped(response) or await _page_requires_login(page, login_url)
        if not session_dropped:
            return response
        if attempt == 0:
            log.info("Session appears to have dropped for user=%s at %s; re-authenticating and retrying", username, url)
            await _authenticate(page, login_url, credential)
            continue
        log.warning("Session still appears unauthenticated after retry for user=%s at %s", username, url)
        return response
    return response


# ── Authentication ────────────────────────────────────────────────────────────

async def _authenticate(page, login_url: str, credential) -> None:
    """Best-effort form-based login."""
    try:
        await page.goto(login_url, wait_until="domcontentloaded", timeout=15_000)
        try:
            await page.wait_for_selector("input", state="visible", timeout=8_000)
        except Exception:
            log.warning("  _authenticate: no <input> visible at %s", login_url)
        await page.wait_for_timeout(300)

        # Fill username
        username_filled = False
        for sel in [
            "input[autocomplete='username']", "input[autocomplete='email']",
            "input[type='email']", "input[name*='user' i]", "input[name*='email' i]",
            "input[id*='user' i]", "input[id*='email' i]", "input[type='text']",
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
            for sel in ["button:has-text('Next')", "button:has-text('Continue')", "button[type='submit']"]:
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
            "button[type='submit']", "input[type='submit']",
            "button:has-text('Log in')", "button:has-text('Login')",
            "button:has-text('Sign in')", "button:has-text('Submit')",
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
            log.warning("  _authenticate: password field still visible — auth likely failed. page.url=%s", page.url)
        else:
            log.info("  _authenticate: success — login form gone. page.url=%s", page.url)

    except Exception as auth_err:
        log.warning("  _authenticate: exception: %s", auth_err)
