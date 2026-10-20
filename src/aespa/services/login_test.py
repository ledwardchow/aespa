"""Try one site credential's login outside a crawl.

The site form uses this to check an account before a crawl starts. It runs the
crawler's own login code against the values in the form, so a passing test
means a crawl will log in the same way. Nothing is written to the database.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Literal

from sqlmodel import Session

from aespa.browser import (
    launch_playwright_browser,
    playwright_user_agent,
    protect_playwright_context,
)
from aespa.db import get_engine
from aespa.models import AuthMode, Credential
from aespa.schemas import CredentialIn
from aespa.services import crawler
from aespa.services import llm as llm_svc
from aespa.services.settings import (
    get_browser_debug_config,
    get_global_http_header_config,
    get_llm_config_for_role,
    get_upstream_proxy_config,
)

log = logging.getLogger("aespa.login_test")

LOGIN_TEST_TIMEOUT_S = 120

_PAGE_MESSAGE_SELECTORS = (
    "[role='alert']",
    "[aria-live='assertive']",
    ".error",
    ".alert",
    ".invalid-feedback",
    ".error-message",
    ".mat-error",
    "mat-error",
)


class LoginTestError(ValueError):
    """The request cannot be tested, for a reason the user can fix."""


@dataclass
class LoginTestResult:
    status: Literal["logged_in", "failed"]
    message: str
    login_url: str
    final_url: str | None = None
    page_message: str | None = None
    screenshot: str | None = None
    duration_ms: int = 0


def _credential_for_test(
    credential: CredentialIn, site_id: int | None
) -> SimpleNamespace:
    totp_seed = credential.totp_seed
    if not totp_seed and credential.id and site_id:
        # The seed is write-only, so the form never has it for a saved account.
        with Session(get_engine()) as s:
            saved = s.get(Credential, credential.id)
            if saved is not None and saved.site_id == site_id:
                totp_seed = saved.totp_seed
    fields = [field.model_dump() for field in credential.login_fields]
    return SimpleNamespace(
        id=credential.id or 0,
        username=credential.username or "",
        password=credential.password or "",
        login_fields_json=json.dumps(fields) if fields else None,
        label=credential.label,
        login_url=str(credential.login_url) if credential.login_url else None,
        auth_mode=credential.auth_mode or AuthMode.auto,
        totp_seed=totp_seed,
        test_mailbox_url=(
            str(credential.test_mailbox_url) if credential.test_mailbox_url else None
        ),
    )


async def _page_message(page) -> str | None:
    for selector in _PAGE_MESSAGE_SELECTORS:
        try:
            items = page.locator(f"{selector}:visible")
            for index in range(min(await items.count(), 5)):
                text = " ".join((await items.nth(index).inner_text()).split())
                if text:
                    return text[:300]
        except Exception:
            continue
    return None


async def _screenshot(page) -> str | None:
    try:
        data = await page.screenshot(type="jpeg", quality=60)
    except Exception:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


async def run_login_test(
    *,
    base_url: str,
    login_url: str | None,
    credential: CredentialIn,
    site_id: int | None = None,
) -> LoginTestResult:
    if credential.auth_mode == AuthMode.guided:
        raise LoginTestError(
            "Accounts that use 'Log in myself in a browser' are checked when a crawl starts."
        )
    cred = _credential_for_test(credential, site_id)
    target = crawler._login_url_for_credential(login_url or "", cred) or base_url
    with Session(get_engine()) as s:
        llm_cfg = get_llm_config_for_role(
            s, SimpleNamespace(llm_profile_id=None, llm_config_id=None), "crawler"
        )
        upstream = get_upstream_proxy_config(s)
        browser_cfg = get_browser_debug_config(s)
        headers = {
            h.header_name: h.header_value
            for h in get_global_http_header_config(s).headers
        }
    proxy_url = upstream.scanner_proxy_url if upstream.proxy_scanner else None
    pw_proxy = {"proxy": {"server": proxy_url}} if proxy_url else {}
    started = time.monotonic()

    from playwright.async_api import async_playwright

    with llm_svc.llm_transport_scope(
        upstream.llm_proxy_url if upstream.proxy_llm else None,
        upstream.llm_ca_bundle_path,
    ):
        async with async_playwright() as p:
            browser = await launch_playwright_browser(
                p,
                browser_engine=browser_cfg.browser_engine,
                headless=True,
                args=["--proxy-bypass-list=<-loopback>"] if pw_proxy else [],
            )
            try:
                ctx = await browser.new_context(
                    user_agent=playwright_user_agent(browser),
                    ignore_https_errors=True,
                    **pw_proxy,
                )
                protect_playwright_context(browser, ctx)
                if headers:
                    await ctx.set_extra_http_headers(headers)
                page = await ctx.new_page()
                try:
                    await asyncio.wait_for(
                        crawler._authenticate(page, target, cred, 0, llm_cfg),
                        timeout=LOGIN_TEST_TIMEOUT_S,
                    )
                    blocked = await crawler._page_requires_login(
                        page, target, settle_ms=1_500
                    )
                    message = (
                        "Still on the login page."
                        if blocked
                        else "Logged in. The login form is gone."
                    )
                except TimeoutError:
                    blocked = True
                    message = f"The login did not finish within {LOGIN_TEST_TIMEOUT_S} seconds."
                except Exception as exc:
                    log.warning("login test failed for %s: %s", target, exc)
                    blocked = True
                    message = f"The login stopped with an error: {exc}"
                return LoginTestResult(
                    status="failed" if blocked else "logged_in",
                    message=message,
                    login_url=target,
                    final_url=page.url or None,
                    page_message=await _page_message(page) if blocked else None,
                    screenshot=await _screenshot(page),
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
            finally:
                await browser.close()
