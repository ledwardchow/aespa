from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from aespa.services import scanner


def test_alternate_account_must_be_a_different_configured_credential():
    primary = SimpleNamespace(id=1, username="alice")
    alternate = SimpleNamespace(id=2, username="bob")
    credentials = [primary, alternate]

    assert scanner._alternate_configured_credential(credentials, " BOB ") is alternate
    assert scanner._alternate_configured_credential(credentials, "alice") is None
    assert scanner._alternate_configured_credential(credentials, "unknown") is None
    assert (
        scanner._alternate_configured_credential([primary, alternate, alternate], "bob")
        is None
    )


class _Page:
    async def goto(self, *_args, **_kwargs):
        return None


class _Context:
    def __init__(self, cookies):
        self.page = _Page()
        self.saved_cookies = cookies
        self.headers = []
        self.closed = False

    async def new_page(self):
        return self.page

    async def cookies(self):
        return self.saved_cookies

    async def set_extra_http_headers(self, headers):
        self.headers.append(headers)

    async def close(self):
        self.closed = True


class _Browser:
    def __init__(self, context):
        self.context = context
        self.created = 0

    async def new_context(self, **_kwargs):
        self.created += 1
        return self.context


def test_alternate_login_uses_fresh_context_and_keeps_it_for_view(monkeypatch):
    context = _Context([{"name": "sid", "value": "bob-session"}])
    browser = _Browser(context)
    credential = SimpleNamespace(id=2, username="bob")
    logins = []

    async def authenticate(page, login_url, selected, run_id, llm_cfg):
        logins.append((page, login_url, selected, run_id, llm_cfg))

    monkeypatch.setattr("aespa.services.crawler._authenticate", authenticate)
    monkeypatch.setattr(scanner, "protect_playwright_context", lambda *_: None)
    monkeypatch.setattr(scanner, "playwright_user_agent", lambda _: "test-agent")
    monkeypatch.setattr(scanner, "_playwright_proxy", lambda: {})
    monkeypatch.setattr(
        scanner, "_playwright_global_headers", lambda extra=None: extra or {}
    )
    monkeypatch.setattr(
        scanner.traffic_svc, "setup_playwright_logging", lambda *_: None
    )

    async def no_token(_page):
        return None, None

    monkeypatch.setattr(scanner, "_read_browser_auth_token", no_token)
    result_context, result_page = asyncio.run(
        scanner._open_browser_as_configured_account(
            browser,
            credential,
            base_url="https://target.test",
            login_url="https://target.test/login",
            run_id=42,
            llm_cfg=None,
        )
    )

    assert browser.created == 1
    assert logins == [(context.page, "https://target.test/login", credential, 42, None)]
    assert result_context is context
    assert result_page is context.page
    assert context.closed is False


def test_alternate_login_without_auth_closes_context(monkeypatch):
    context = _Context([])
    browser = _Browser(context)

    async def authenticate(*_args, **_kwargs):
        return None

    async def no_token(_page):
        return None, None

    monkeypatch.setattr("aespa.services.crawler._authenticate", authenticate)
    monkeypatch.setattr(scanner, "protect_playwright_context", lambda *_: None)
    monkeypatch.setattr(scanner, "playwright_user_agent", lambda _: "test-agent")
    monkeypatch.setattr(scanner, "_playwright_proxy", lambda: {})
    monkeypatch.setattr(
        scanner, "_playwright_global_headers", lambda extra=None: extra or {}
    )
    monkeypatch.setattr(
        scanner.traffic_svc, "setup_playwright_logging", lambda *_: None
    )
    monkeypatch.setattr(scanner, "_read_browser_auth_token", no_token)

    with pytest.raises(RuntimeError, match="did not produce a browser session"):
        asyncio.run(
            scanner._open_browser_as_configured_account(
                browser,
                SimpleNamespace(id=2, username="bob"),
                base_url="https://target.test",
                login_url="https://target.test/login",
                run_id=42,
                llm_cfg=None,
            )
        )
    assert context.closed is True


def test_alternate_login_does_not_send_primary_auth_headers(monkeypatch):
    context = _Context([])
    browser = _Browser(context)

    async def authenticate(*_args, **_kwargs):
        return None

    async def alternate_token(_page):
        return "alternate-token", "session-token"

    monkeypatch.setattr("aespa.services.crawler._authenticate", authenticate)
    monkeypatch.setattr(scanner, "protect_playwright_context", lambda *_: None)
    monkeypatch.setattr(scanner, "playwright_user_agent", lambda _: "test-agent")
    monkeypatch.setattr(scanner, "_playwright_proxy", lambda: {})
    monkeypatch.setattr(
        scanner,
        "_playwright_global_headers",
        lambda extra=None: {
            "Authorization": "Bearer primary-token",
            "Cookie": "sid=primary",
            "X-Scan": "yes",
            **(extra or {}),
        },
    )
    monkeypatch.setattr(
        scanner.traffic_svc, "setup_playwright_logging", lambda *_: None
    )
    monkeypatch.setattr(scanner, "_read_browser_auth_token", alternate_token)

    asyncio.run(
        scanner._open_browser_as_configured_account(
            browser,
            SimpleNamespace(id=2, username="bob"),
            base_url="https://target.test",
            login_url="https://target.test/login",
            run_id=42,
            llm_cfg=None,
            request_headers={"X-Request": "view", "Cookie": "sid=also-primary"},
        )
    )

    assert context.headers[0] == {"X-Scan": "yes", "X-Request": "view"}
    assert context.headers[1] == {
        "X-Scan": "yes",
        "X-Request": "view",
        "Authorization": "Bearer alternate-token",
    }
