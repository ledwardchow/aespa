"""Playwright-based BFS web crawler with LLM page analysis."""
from __future__ import annotations

import asyncio
import base64
from collections import deque
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, PageLink, TestRun, TestRunStatus
from aespa.services import llm as llm_svc
from aespa.services.settings import get_llm_config

# ── In-memory state ───────────────────────────────────────────────────────────

_stop_requested: set[int] = set()
_active_tasks: dict[int, asyncio.Task] = {}  # run_id → Task


def request_stop(run_id: int) -> None:
    _stop_requested.add(run_id)


def is_running(run_id: int) -> bool:
    return run_id in _active_tasks


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Public entry point ────────────────────────────────────────────────────────

async def start_crawl(run_id: int) -> None:
    """Schedule a background crawl task (idempotent — no-op if already running)."""
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


# ── Core crawler ──────────────────────────────────────────────────────────────

async def _do_crawl(run_id: int) -> None:
    from playwright.async_api import async_playwright

    # Load everything we need from DB, then expunge all objects so that
    # their attributes remain accessible after the session closes.
    # (SQLAlchemy's session.close() expires every attribute on all objects
    # still attached to the session — expunge() prevents that.)
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        from aespa.models import Site
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config(s)
        creds = list(site.credentials)   # force-load the relationship

        if llm_cfg is None:
            raise RuntimeError("No LLM configuration found. Configure it in Settings first.")

        # Expunge before the session closes to keep loaded attribute values.
        for cred in creds:
            s.expunge(cred)
        s.expunge(site)
        s.expunge(llm_cfg)
        s.expunge(run)

    # Extract all needed primitive values from the expunged ORM objects so
    # we never touch SQLAlchemy state again outside a session block.
    base_url      = site.base_url.rstrip("/")
    login_url     = site.login_url
    requires_auth = site.requires_auth
    max_depth     = run.max_depth
    max_pages     = run.max_pages
    _parsed_base  = urlparse(base_url)
    base_netloc   = _parsed_base.netloc
    # Scope crawl to the base URL's path prefix (e.g. "/banking/").
    # Links that escape to a different path root are ignored.
    _bp = _parsed_base.path
    base_path: str = (_bp if _bp.endswith("/") else _bp + "/") if _bp else "/"

    # Load existing pages so we can append instead of wiping.
    # prev_visited maps normalised URL → CrawledPage.id for all already-crawled pages.
    with Session(get_engine()) as s:
        existing = s.exec(
            select(CrawledPage).where(CrawledPage.test_run_id == run_id)
        ).all()
        for ep in existing:
            s.expunge(ep)

    prev_visited: dict[str, Optional[int]] = {_norm(ep.url): ep.id for ep in existing}
    pages_done = len(existing)
    # crawled_norms tracks every final URL crawled this session (including prior
    # runs loaded above) so redirect-loop duplicates are never re-indexed.
    crawled_norms: dict[str, int] = dict(prev_visited)

    _update_run(
        run_id,
        status=TestRunStatus.running,
        started_at=_utcnow(),
        completed_at=None,
        error_message=None,
        pages_discovered=pages_done,
        current_url=base_url,
    )

    # `queued` deduplicates queue entries (like `visited` in a normal BFS).
    # prev_visited URLs are allowed into the queue so we can fast-traverse them
    # and discover links to pages that weren't crawled in earlier runs.
    queued: set[str] = set()
    queue: deque[tuple[str, int, Optional[int]]] = deque()
    queued.add(_norm(base_url))
    queue.append((base_url, 0, None))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
        )
        page = await ctx.new_page()

        if requires_auth and creds:
            await _authenticate(page, login_url, creds[0])

        while queue and max_pages > pages_done:
            if _stop_requested.issuperset({run_id}):
                break

            url, depth, parent_id = queue.popleft()
            norm = _norm(url)

            if norm in prev_visited:
                # Already crawled in a prior run. Fast-traverse: navigate to
                # extract outgoing links and enqueue any that are new.
                if depth < max_depth:
                    existing_id = prev_visited[norm]
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=5_000)
                        except Exception:
                            pass
                        hrefs: list[str] = await page.evaluate(
                            "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
                        )
                        for href in hrefs:
                            n = _norm(href)
                            if n not in queued and _same_domain(href, base_netloc, base_path):
                                queued.add(n)
                                queue.append((href, depth + 1, existing_id))
                    except Exception:
                        pass
                continue

            if depth > max_depth:
                continue

            _update_run(run_id, current_url=url)

            page_id, final_url, is_new = await _process_page(
                page=page,
                url=url,
                depth=depth,
                parent_id=parent_id,
                run_id=run_id,
                llm_cfg=llm_cfg,
                base_netloc=base_netloc,
                base_path=base_path,
                crawled_norms=crawled_norms,
            )
            queued.add(_norm(final_url))

            if not is_new:
                # Redirect landed on an already-crawled page — don't count it
                # or enqueue its children again.
                continue

            crawled_norms[_norm(final_url)] = page_id
            pages_done += 1
            _update_run(run_id, pages_discovered=pages_done)

            page_links, suggested = _get_queued_links(page_id, run_id)
            for link_url in reversed(suggested):
                n = _norm(link_url)
                if n not in queued and _same_domain(link_url, base_netloc, base_path):
                    queued.add(n)
                    queue.appendleft((link_url, depth + 1, page_id))
            for link_url in page_links:
                n = _norm(link_url)
                if n not in queued and _same_domain(link_url, base_netloc, base_path):
                    queued.add(n)
                    queue.append((link_url, depth + 1, page_id))

        await browser.close()

    final_status = (
        TestRunStatus.stopped if run_id in _stop_requested else TestRunStatus.complete
    )
    _update_run(run_id, status=final_status, completed_at=_utcnow(), current_url=None)


# ── Page processing ───────────────────────────────────────────────────────────

def _is_api_page(url: str, text: str) -> bool:
    """Return True if the page looks like an API / JSON endpoint."""
    path = urlparse(url).path.lower()
    if any(pat in path for pat in ("/api/", "/v1/", "/v2/", "/v3/", "/rest/", "/graphql", "/swagger", "/openapi")):
        return True
    stripped = (text or "").lstrip()
    return len(stripped) > 2 and stripped[0] in ("{", "[")


async def _process_page(
    *,
    page,
    url: str,
    depth: int,
    parent_id: Optional[int],
    run_id: int,
    llm_cfg,
    base_netloc: str,
    base_path: str,
    crawled_norms: dict,
) -> tuple[Optional[int], str, bool]:
    """Navigate, extract, analyse, persist.
    Returns (page_id, final_url, is_new).
    is_new=False when final_url was already crawled (redirect loop) — no new
    CrawledPage is created; a link to the existing page is recorded instead."""
    # Navigate
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        # Skip 4xx/5xx responses — don't add them to the sitemap at all.
        if resp is not None and resp.status >= 400:
            return None, url, True
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass  # networkidle timeout is fine; page may have long-polling
    except Exception as nav_err:
        cp = _save_page(run_id, url=url, depth=depth, status="failed",
                        error_message=str(nav_err)[:500])
        _save_link(run_id, parent_id, cp.id, url)
        return cp.id, url, True

    raw_final = page.url
    # Guard against SPA routers that rewrite the URL outside the base scope
    # via history.pushState after networkidle (e.g. /banking/#/dashboard →
    # /dashboard).  When that happens, keep the URL we actually navigated to.
    if (
        base_path != "/"
        and urlparse(raw_final).netloc.lower() == base_netloc.lower()
        and not _same_domain(raw_final, base_netloc, base_path)
    ):
        final_url = url
    else:
        final_url = raw_final

    # Redirect-loop guard: if we've already crawled this URL (possibly via a
    # different entry URL that resolved to the same final destination), link to
    # the existing page rather than creating a duplicate node.
    norm_final = _norm(final_url)
    if norm_final in crawled_norms:
        existing_id = crawled_norms[norm_final]
        _save_link(run_id, parent_id, existing_id, final_url)
        return existing_id, final_url, False

    title = await page.title()

    # Text content
    try:
        text = await page.evaluate("() => document.body.innerText")
    except Exception:
        text = ""

    # Brief pause so the UI can finish rendering before we screenshot.
    try:
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    # Screenshot (always captured; sent to LLM only if use_vision is on)
    screenshot_b64: Optional[str] = None
    try:
        raw = await page.screenshot(type="png", full_page=False)
        screenshot_b64 = base64.b64encode(raw).decode()
    except Exception:
        pass

    # Extract same-domain links
    try:
        raw_links: list[dict] = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                href: a.href,
                text: (a.textContent || '').trim().slice(0, 80)
            }))"""
        )
    except Exception:
        raw_links = []

    same_domain = [
        (r["href"], r["text"])
        for r in raw_links
        if _same_domain(r["href"], base_netloc, base_path)
    ]

    # LLM analysis — skipped for API / JSON endpoints
    if _is_api_page(final_url, text):
        context = "[API endpoint — LLM analysis skipped]"
        suggested: list[str] = []
    else:
        try:
            context, suggested = await llm_svc.analyse_page(
                llm_cfg, final_url, title, text[:8000], screenshot_b64,
            )
        except Exception as llm_err:
            context = f"[LLM analysis failed: {llm_err}]"
            suggested = []

    # Persist
    cp = _save_page(
        run_id, url=final_url, title=title,
        page_text=text[:10_000], screenshot_b64=screenshot_b64,
        llm_context=context, depth=depth, status="crawled",
    )
    _save_link(run_id, parent_id, cp.id, final_url)

    _store_extracted_links(cp.id, same_domain, suggested)
    return cp.id, final_url, True


# ── Helpers ───────────────────────────────────────────────────────────────────

# Temporary in-memory store for per-page extracted links (avoid re-querying DB)
_page_links_cache: dict[int, tuple[list[str], list[str]]] = {}


def _store_extracted_links(page_id: int, links: list[tuple[str, str]], suggested: list[str]) -> None:
    _page_links_cache[page_id] = ([l[0] for l in links], suggested)


def _get_queued_links(page_id: int, run_id: int) -> tuple[list[str], list[str]]:
    return _page_links_cache.pop(page_id, ([], []))


def _save_page(run_id: int, **kwargs) -> CrawledPage:
    with Session(get_engine()) as s:
        cp = CrawledPage(test_run_id=run_id, **kwargs)
        s.add(cp)
        s.commit()
        s.refresh(cp)
        # Expunge so attributes (esp. cp.id) survive session.close().
        s.expunge(cp)
        return cp


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


def _clear_pages(run_id: int) -> None:
    with Session(get_engine()) as s:
        links = s.exec(select(PageLink).where(PageLink.test_run_id == run_id)).all()
        for l in links:
            s.delete(l)
        pages = s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
        for p in pages:
            s.delete(p)
        s.commit()


# ── URL utilities ─────────────────────────────────────────────────────────────

def _norm(url: str) -> str:
    """Normalise URL for deduplication.
    - Lowercases scheme + host.
    - Collapses trailing path slashes so '/banking/' == '/banking'.
    - Strips plain anchors (#section) but preserves SPA hash-routes (#/path)
      because those identify distinct pages in hash-router SPAs."""
    try:
        p = urlparse(url)
        path = p.path.rstrip("/") or "/"
        # Keep '#/...' fragments (SPA routes); discard plain anchors like '#top'
        frag = p.fragment if p.fragment.startswith("/") else ""
        return urlunparse((p.scheme.lower(), p.netloc.lower(), path, p.params, p.query, frag))
    except Exception:
        return url


def _same_domain(url: str, base_netloc: str, base_path: str = "/") -> bool:
    """Return True when *url* is on the same host and under the same path scope."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.netloc.lower() != base_netloc.lower():
            return False
        # Enforce path prefix when the base URL is deployed under a sub-path.
        if base_path != "/":
            p = parsed.path
            if not (p.startswith(base_path) or p == base_path.rstrip("/")):
                return False
        return True
    except Exception:
        return False


# ── Authentication ────────────────────────────────────────────────────────────

async def _authenticate(page, login_url: str, credential) -> None:
    """Best-effort form-based login. Fills username first, then password."""
    try:
        await page.goto(login_url, wait_until="domcontentloaded", timeout=15_000)
        await page.wait_for_timeout(800)  # let JS initialise the form

        # ── Step 1: fill username ─────────────────────────────────────────────
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
            return  # can't locate username field; abort

        # ── Step 2: some forms hide the password until Next is clicked ────────
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

        # ── Step 3: fill password ─────────────────────────────────────────────
        try:
            pass_loc = page.locator("input[type='password']").first
            if await pass_loc.count() > 0 and await pass_loc.is_visible():
                await pass_loc.fill(credential.password)
        except Exception:
            pass

        # ── Step 4: submit ────────────────────────────────────────────────────
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
                    break
            except Exception:
                pass

        await page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass  # best-effort; crawl continues unauthenticated
