"""Security scanner service.

Two-phase LLM-directed probe execution:
  1. plan_probes()  → LLM returns a list of HTTP / form probes for the page
  2. execute probes → httpx (url/header/idor) or Playwright (form injection)
  3. analyse_probes() → LLM interprets results, returns ScanFinding rows

Auth bootstrap: re-uses _authenticate() from crawler, then exports cookies +
JS storage tokens so httpx carries a live authenticated session.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, ScanFinding, Site, TestRun, TestRunStatus
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import traffic as traffic_svc
from aespa.services.settings import get_llm_config

log = logging.getLogger("aespa.scanner")

# ── In-memory state ───────────────────────────────────────────────────────────

_stop_requested: set[int] = set()
_active_tasks: dict[int, asyncio.Task] = {}

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

MAX_PROBES_PER_PAGE = 50
REQUEST_TIMEOUT = 10.0
BODY_READ_LIMIT = 512 * 1024  # 512 KB
MIN_DELAY = 0.2               # ~5 req/s


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Public entry points ───────────────────────────────────────────────────────

def request_stop(run_id: int) -> None:
    _stop_requested.add(run_id)


def is_running(run_id: int) -> bool:
    return run_id in _active_tasks


async def start_scan(run_id: int, page_ids: list[int] | None = None) -> None:
    """Start a scan. Pass page_ids to scan only specific pages; omit to scan all in-scope pages."""
    if run_id in _active_tasks:
        return
    task = asyncio.create_task(
        _scan_task(run_id, page_ids=page_ids),
        name=f"scan-{run_id}",
    )
    _active_tasks[run_id] = task
    task.add_done_callback(lambda _: _active_tasks.pop(run_id, None))


# ── Task wrapper ──────────────────────────────────────────────────────────────

async def _scan_task(run_id: int, page_ids: list[int] | None = None) -> None:
    try:
        await _do_scan(run_id, page_ids=page_ids)
    except Exception as exc:
        log.exception("Scan task failed for run_id=%s", run_id)
        _mark_run(run_id, scan_status="failed", error=str(exc)[:2000])
    finally:
        _stop_requested.discard(run_id)


# ── Core scan ─────────────────────────────────────────────────────────────────

async def _do_scan(run_id: int, page_ids: list[int] | None = None) -> None:
    from playwright.async_api import async_playwright

    # Load site, credentials, and LLM config (expunge before session closes).
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config(s)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration. Configure it in Settings first.")
        creds = list(site.credentials)
        for obj in [*creds, site, llm_cfg, run]:
            s.expunge(obj)

    base_url      = site.base_url.rstrip("/")
    login_url     = site.login_url
    requires_auth = site.requires_auth

    log.info("=== Scan start: run_id=%s base_url=%s ===", run_id, base_url)

    # Mark target pages as scan_status=pending; clear their existing findings.
    with Session(get_engine()) as s:
        q = (
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)   # noqa: E712
            .where(CrawledPage.status == "crawled") # skip failed navigations
            .where(CrawledPage.page_text != None)   # noqa: E711  skip content-less pages
            .where(CrawledPage.page_text != "")
        )
        if page_ids:
            q = q.where(CrawledPage.id.in_(page_ids))
        pages = s.exec(q).all()
        target_ids = [p.id for p in pages]
        for p in pages:
            p.scan_status = "pending"
            s.add(p)
        # Clear existing findings only for the pages we're about to scan.
        old = s.exec(
            select(ScanFinding)
            .where(ScanFinding.test_run_id == run_id)
            .where(ScanFinding.page_id.in_(target_ids))
        ).all()
        for f in old:
            s.delete(f)
        s.commit()
        page_ids = target_ids  # use resolved list from here on

    if not page_ids:
        log.info("No in-scope pages to scan.")
        _mark_run(run_id, scan_status="complete")
        return

    _mark_run(run_id, scan_status="running")

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
        traffic_svc.setup_playwright_logging(ctx, run_id)
        pw_page = await ctx.new_page()

        # ── Auth bootstrap ────────────────────────────────────────────────────
        # Pre-load base URL, then authenticate to get a live session.
        try:
            await pw_page.goto(base_url, wait_until="domcontentloaded", timeout=20_000)
        except Exception as e:
            log.warning("Pre-load failed: %s", e)

        if requires_auth and creds:
            from aespa.services.crawler import _authenticate
            log.info("Authenticating at %s", login_url)
            await _authenticate(pw_page, login_url, creds[0])
            log.info("Auth done. page.url=%s", pw_page.url)

        # ── Export auth state for httpx ───────────────────────────────────────
        raw_cookies = await ctx.cookies()
        cookie_jar: dict[str, str] = {c["name"]: c["value"] for c in raw_cookies}

        # Check for JWT/Bearer tokens in JS storage.
        auth_token: Optional[str] = None
        try:
            for key in ["access_token", "token", "jwt", "auth_token", "id_token",
                        "authToken", "accessToken"]:
                val = await pw_page.evaluate(
                    f"() => localStorage.getItem('{key}') || sessionStorage.getItem('{key}')"
                )
                if val:
                    auth_token = val
                    log.info("Found JS storage token under key '%s'", key)
                    break
        except Exception as e:
            log.warning("JS storage token extraction failed: %s", e)

        extra_headers: dict[str, str] = {}
        if auth_token:
            extra_headers["Authorization"] = f"Bearer {auth_token}"

        # Build httpx client with exported auth state.
        async with httpx.AsyncClient(
            cookies=cookie_jar,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                **extra_headers,
            },
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(run_id, username=creds[0].username if creds else None),
        ) as hx:
            # ── Per-page scanning ─────────────────────────────────────────────
            for page_id in page_ids:
                if run_id in _stop_requested:
                    log.info("Stop requested — aborting scan.")
                    break
                await _scan_page(run_id, page_id, hx, pw_page, llm_cfg, base_url)

    stopped = run_id in _stop_requested
    _mark_run(run_id, scan_status="stopped" if stopped else "complete")
    _emit_scan_update(run_id)
    log.info("=== Scan %s: run_id=%s ===", "stopped" if stopped else "complete", run_id)


# ── Per-page scan ─────────────────────────────────────────────────────────────

async def _scan_page(
    run_id: int,
    page_id: int,
    hx: httpx.AsyncClient,
    pw_page,
    llm_cfg,
    base_url: str,
) -> None:
    # Load page details.
    with Session(get_engine()) as s:
        page = s.get(CrawledPage, page_id)
        if page is None:
            return
        page_url    = page.url
        page_title  = page.title or ""
        page_ctx    = page.llm_context or ""
        categories  = {
            "req_auth":          page.req_auth,
            "takes_input":       page.takes_input,
            "has_object_ref":    page.has_object_ref,
            "has_business_logic": page.has_business_logic,
        }
        page.scan_status = "running"
        s.add(page)
        s.commit()

    events_svc.emit(run_id, {"type": "node_scan_status", "page_id": page_id, "scan_status": "running"})
    log.info("Scanning page: %s", page_url)

    # Determine applicable OWASP checks based on page categories.
    applicable = _applicable_checks(categories)

    # Phase 1: LLM plans probes.
    try:
        probes = await llm_svc.plan_probes(
            llm_cfg, page_url, page_title, page_ctx, categories, applicable
        )
    except Exception as e:
        log.warning("plan_probes failed for %s: %s", page_url, e)
        probes = []

    # Inject hard-coded probes before the LLM probes so they always run.
    deterministic: list[dict] = []
    if categories.get("has_object_ref"):
        idor = _idor_probes(page_url)
        log.info("  IDOR probes generated: %d", len(idor))
        deterministic.extend(idor)
    if categories.get("takes_input"):
        iv = _input_validation_probes(page_url)
        log.info("  Input-validation probes generated: %d", len(iv))
        deterministic.extend(iv)

    # Combine: deterministic first, then LLM probes, capped at MAX_PROBES_PER_PAGE.
    all_probes = deterministic + probes
    all_probes = all_probes[:MAX_PROBES_PER_PAGE]
    log.info("  %d total probes for %s (%d deterministic, %d llm)",
             len(all_probes), page_url, len(deterministic), len(probes))

    # Phase 2: Execute probes.
    results: list[dict] = []

    # Always run passive checks regardless of LLM probes.
    passive = await _passive_checks(hx, page_url, base_url)
    results.extend(passive)

    for probe in all_probes:
        if run_id in _stop_requested:
            break
        try:
            if probe.get("type") == "form":
                result = await _run_form_probe(pw_page, probe, page_url)
            else:
                result = await _run_http_probe(hx, probe, page_url)
            if result:
                results.append(result)
        except Exception as e:
            log.debug("Probe error (%s): %s", probe.get("desc", "?"), e)
        await asyncio.sleep(MIN_DELAY)

    # Phase 3: LLM analyses results and produces findings.
    try:
        raw_findings = await llm_svc.analyse_probes(llm_cfg, page_url, results)
    except Exception as e:
        log.warning("analyse_probes failed for %s: %s", page_url, e)
        raw_findings = []

    log.info("  %d findings for %s", len(raw_findings), page_url)

    # Build a URL→result lookup so we can attach evidence + screenshot to each finding.
    result_by_url: dict[str, dict] = {}
    for r in results:
        if r.get("url"):
            result_by_url[r["url"]] = r

    probe_urls = list(result_by_url.keys())  # ordered list of actually-probed URLs

    # Persist findings and mark page complete.
    with Session(get_engine()) as s:
        for f in raw_findings:
            llm_url = (f.get("affected_url") or "").strip()
            if llm_url and llm_url != page_url:
                # LLM returned a specific probe URL — use it directly.
                affected_url = llm_url
            elif probe_urls:
                # LLM returned the page URL or nothing; prefer the first probe URL
                # whose evidence string or URL appears in the finding description.
                desc = (f.get("description", "") + " " + f.get("title", "")).lower()
                match = next((u for u in probe_urls if u.lower() in desc), probe_urls[0])
                affected_url = match
            else:
                affected_url = page_url
            matched = result_by_url.get(affected_url, {})
            # Use the pre-built evidence from the probe result if available;
            # fall back to what the LLM wrote.
            evidence = matched.get("evidence") or f.get("evidence", "")
            screenshot = matched.get("screenshot_b64")
            finding = ScanFinding(
                test_run_id=run_id,
                page_id=page_id,
                owasp_category=f.get("owasp_category", "A00"),
                severity=f.get("severity", "info"),
                title=f.get("title", "Untitled finding"),
                description=f.get("description", ""),
                affected_url=affected_url,
                evidence=evidence[:4000],
                screenshot_b64=screenshot,
                created_at=_utcnow(),
            )
            s.add(finding)
        pg = s.get(CrawledPage, page_id)
        if pg:
            pg.scan_status = "complete"
            s.add(pg)
        s.commit()

    events_svc.emit(run_id, {"type": "node_scan_status", "page_id": page_id, "scan_status": "complete"})


# ── Passive checks ────────────────────────────────────────────────────────────

async def _passive_checks(
    hx: httpx.AsyncClient,
    url: str,
    base_url: str,
) -> list[dict]:
    """Fire a single GET to the page and check response headers / cookies."""
    results = []
    try:
        resp = await hx.get(url, timeout=REQUEST_TIMEOUT)
        headers = dict(resp.headers)
        body = resp.text[:500]
        status = resp.status_code

        # Check security headers.
        security_headers = {
            "strict-transport-security": "HSTS",
            "content-security-policy": "Content-Security-Policy",
            "x-frame-options": "X-Frame-Options",
            "x-content-type-options": "X-Content-Type-Options",
            "referrer-policy": "Referrer-Policy",
            "permissions-policy": "Permissions-Policy",
        }
        missing = [
            label for hdr, label in security_headers.items()
            if hdr not in {k.lower() for k in headers}
        ]

        # Auth bypass: same request without cookies.
        auth_bypass_status: Optional[int] = None
        try:
            anon = await hx.get(url, timeout=REQUEST_TIMEOUT,
                                headers={"Cookie": "", "Authorization": ""})
            auth_bypass_status = anon.status_code
        except Exception:
            pass

        headers_text = "\n".join(f"{k}: {v}" for k, v in headers.items())
        evidence = (
            f"REQUEST:\nGET {url} HTTP/1.1\n\n"
            f"RESPONSE:\nHTTP/1.1 {status}\n{headers_text}\n\n{body}"
            + (f"\n\nMISSING SECURITY HEADERS: {', '.join(missing)}" if missing else "")
            + (f"\n\nANON REQUEST STATUS: {auth_bypass_status}" if auth_bypass_status else "")
        )
        results.append({
            "desc": "Passive: headers + auth-bypass check",
            "url": url,
            "status": status,
            "headers": headers,
            "body": body,
            "evidence": evidence,
            "screenshot_b64": None,
            "missing_security_headers": missing,
            "auth_bypass_status": auth_bypass_status,
        })

        # Check cookies for Secure / HttpOnly flags.
        if resp.cookies:
            cookie_issues = []
            for raw in resp.headers.get_list("set-cookie"):
                name = raw.split("=")[0].strip()
                flags = raw.lower()
                issues = []
                if "secure" not in flags:
                    issues.append("missing Secure flag")
                if "httponly" not in flags:
                    issues.append("missing HttpOnly flag")
                if "samesite" not in flags:
                    issues.append("missing SameSite attribute")
                if issues:
                    cookie_issues.append(f"{name}: {', '.join(issues)}")
            if cookie_issues:
                issue_text = " | ".join(cookie_issues)
                results.append({
                    "desc": "Passive: cookie attribute check",
                    "url": url,
                    "status": status,
                    "headers": {},
                    "body": issue_text,
                    "evidence": f"REQUEST:\nGET {url}\n\nCOOKIE ISSUES:\n{issue_text}",
                    "screenshot_b64": None,
                })

    except Exception as e:
        log.debug("Passive check failed for %s: %s", url, e)

    return results


# ── HTTP probe execution ──────────────────────────────────────────────────────

async def _run_http_probe(
    hx: httpx.AsyncClient,
    probe: dict,
    page_url: str,
) -> Optional[dict]:
    method       = probe.get("method", "GET").upper()
    url          = probe.get("url") or page_url
    params       = probe.get("params") or {}
    body         = probe.get("body")
    extra_hdrs   = probe.get("headers") or {}
    desc         = probe.get("desc", url)

    try:
        req = hx.build_request(
            method, url,
            params=params,
            content=body.encode() if isinstance(body, str) else body,
            headers=extra_hdrs,
        )
        resp = await hx.send(req, follow_redirects=True)
        resp_body = resp.text[:1000]

        # Build a readable request/response block for evidence.
        req_headers_text = "\n".join(f"{k}: {v}" for k, v in req.headers.items()
                                     if k.lower() not in ("cookie",))  # omit cookie value
        resp_headers_text = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
        evidence = (
            f"REQUEST:\n{method} {req.url} HTTP/1.1\n{req_headers_text}\n"
            + (f"\n{body[:200]}" if body else "")
            + f"\n\nRESPONSE:\nHTTP/1.1 {resp.status_code}\n{resp_headers_text}\n\n{resp_body}"
        )

        return {
            "desc": desc,
            "url": str(resp.url),
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp_body,
            "evidence": evidence,
            "screenshot_b64": None,
        }
    except Exception as e:
        return {"desc": desc, "url": url, "status": None, "headers": {}, "body": str(e),
                "evidence": f"REQUEST ERROR: {e}", "screenshot_b64": None}


# ── Playwright form probe execution ───────────────────────────────────────────

async def _run_form_probe(pw_page, probe: dict, page_url: str) -> Optional[dict]:
    url      = probe.get("url") or page_url
    selector = probe.get("selector", "input")
    payload  = probe.get("payload", "")
    submit   = probe.get("submit_selector", "button[type=submit]")
    desc     = probe.get("desc", selector)

    try:
        await pw_page.goto(url, wait_until="domcontentloaded", timeout=15_000)
        await pw_page.wait_for_selector(selector, state="visible", timeout=5_000)

        field = pw_page.locator(selector).first
        await field.fill("")
        await field.type(payload, delay=20)

        # Capture the network response on submit.
        response_body = ""
        response_status: Optional[int] = None
        try:
            async with pw_page.expect_response(
                lambda r: r.url.startswith(url.split("?")[0]),
                timeout=8_000,
            ) as resp_info:
                sub_btn = pw_page.locator(submit).first
                if await sub_btn.count() > 0:
                    await sub_btn.click()
                else:
                    await field.press("Enter")
            resp = await resp_info.value
            response_status = resp.status
            try:
                response_body = (await resp.text())[:500]
            except Exception:
                pass
        except Exception:
            # If we can't intercept a response, capture the resulting page HTML.
            try:
                await pw_page.wait_for_load_state("networkidle", timeout=6_000)
            except Exception:
                pass
            response_body = (await pw_page.content())[:500]

        # Always take a screenshot so findings can show visual proof.
        screenshot_b64: Optional[str] = None
        try:
            raw_png = await pw_page.screenshot(full_page=False)
            import base64 as _b64
            screenshot_b64 = _b64.b64encode(raw_png).decode()
        except Exception:
            pass

        evidence = (
            f"FORM PROBE:\nURL: {url}\nField selector: {selector}\n"
            f"Payload: {payload}\n\n"
            f"RESPONSE STATUS: {response_status}\n\n"
            f"RESPONSE BODY (truncated):\n{response_body}"
        )

        return {
            "desc": desc,
            "url": url,
            "payload": payload,
            "status": response_status,
            "headers": {},
            "body": response_body,
            "evidence": evidence,
            "screenshot_b64": screenshot_b64,
        }
    except Exception as e:
        log.debug("Form probe error (%s): %s", desc, e)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _idor_probes(url: str) -> list[dict]:
    """Generate IDOR probes by extracting numeric IDs from the URL path and query string."""
    probes: list[dict] = []
    parsed = urlparse(url)

    # ── Path segments ──────────────────────────────────────────────────────────
    parts = parsed.path.split("/")
    for i, part in enumerate(parts):
        if not re.match(r"^\d+$", part):
            continue
        orig = int(part)
        candidates = sorted({0, 1, max(0, orig - 1), orig + 1, 9999, 99999} - {orig})
        for cid in candidates[:6]:
            new_parts = parts.copy()
            new_parts[i] = str(cid)
            test_url = urlunparse(parsed._replace(path="/".join(new_parts)))
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {}, "body": None,
                "desc": f"IDOR: path /{part} → /{cid}",
            })
            # Also test without auth cookies to check access control.
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {"Cookie": "", "Authorization": ""}, "body": None,
                "desc": f"IDOR+auth-bypass: path /{part} → /{cid} (no auth)",
            })

    # ── Query parameters ───────────────────────────────────────────────────────
    qs = parse_qs(parsed.query, keep_blank_values=True)
    for param, vals in qs.items():
        if not (vals and re.match(r"^\d+$", vals[0])):
            continue
        orig = int(vals[0])
        base_params = {k: v[0] for k, v in qs.items()}
        candidates = sorted({0, 1, max(0, orig - 1), orig + 1, 9999} - {orig})
        for cid in candidates[:5]:
            np = dict(base_params)
            np[param] = str(cid)
            test_url = urlunparse(parsed._replace(query=urlencode(np)))
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {}, "body": None,
                "desc": f"IDOR: ?{param}={vals[0]} → {cid}",
            })

    return probes[:20]  # cap to avoid flooding


# Common injection payloads used for takes_input pages.
_SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1'--",
    "1 AND SLEEP(0)--",
    "1; SELECT 1--",
    "' UNION SELECT NULL--",
    "1' ORDER BY 999--",
]
_XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(1)",
    "'><svg onload=alert(1)>",
    "<details open ontoggle=alert(1)>",
]
_SSTI_PAYLOADS = ["{{7*7}}", "${7*7}", "<%= 7*7 %>", "#{7*7}"]
_PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "....//....//etc/passwd",
]
_SSRF_PAYLOADS = [
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.1/",
    "http://[::1]/",
]
_CMD_PAYLOADS = ["; echo aespa_probe", "| echo aespa_probe", "$(echo aespa_probe)"]


def _input_validation_probes(url: str) -> list[dict]:
    """Generate HTTP-level input validation probes for every query parameter."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if not qs:
        return []

    probes: list[dict] = []
    all_payloads = (
        [(p, "SQLi")  for p in _SQLI_PAYLOADS]
        + [(p, "XSS")   for p in _XSS_PAYLOADS]
        + [(p, "SSTI")  for p in _SSTI_PAYLOADS]
        + [(p, "Path")  for p in _PATH_TRAVERSAL_PAYLOADS]
        + [(p, "SSRF")  for p in _SSRF_PAYLOADS]
        + [(p, "CMDi")  for p in _CMD_PAYLOADS]
    )
    base_params = {k: v[0] for k, v in qs.items()}
    for param in list(qs.keys())[:3]:       # test up to 3 params
        for payload, label in all_payloads:
            np = dict(base_params)
            np[param] = payload
            test_url = urlunparse(parsed._replace(query=urlencode(np)))
            probes.append({
                "type": "http", "method": "GET", "url": test_url,
                "params": {}, "headers": {}, "body": None,
                "desc": f"{label} in param '{param}': {payload[:40]}",
            })
    return probes[:30]


def _applicable_checks(categories: dict) -> list[str]:
    checks = ["A02", "A05", "A06", "A08", "A09"]  # always-on
    if categories.get("req_auth"):
        checks += ["A01", "A07"]
    if categories.get("takes_input"):
        checks += ["A03", "A10"]
    if categories.get("has_object_ref"):
        checks.append("A01")
    if categories.get("has_business_logic"):
        checks.append("A04")
    return sorted(set(checks))


def _emit_scan_update(run_id: int) -> None:
    status = get_scan_status(run_id)
    events_svc.emit(run_id, {"type": "scan_update", **status})


def _mark_run(run_id: int, scan_status: str, error: str = "") -> None:
    """Persist scan_status on the TestRun (stored in the error_message field prefix)."""
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return
        # We persist scan status as a prefixed error_message so no schema change is needed.
        run.error_message = f"scan:{scan_status}" if not error else f"scan:{scan_status}:{error}"
        s.add(run)
        s.commit()


def get_scan_status(run_id: int) -> dict:
    with Session(get_engine()) as s:
        pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
        ).all()
        total = len(pages)
        done  = sum(1 for p in pages if p.scan_status == "complete")
        findings_count = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all().__len__()

        run = s.get(TestRun, run_id)
        em = (run.error_message or "") if run else ""
        if em.startswith("scan:"):
            parts = em.split(":", 2)
            status = parts[1] if len(parts) > 1 else "idle"
        elif is_running(run_id):
            status = "running"
        else:
            status = "idle"

    return {
        "total_pages": total,
        "pages_done": done,
        "findings_count": findings_count,
        "status": status,
    }
