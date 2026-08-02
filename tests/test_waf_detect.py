from __future__ import annotations

import asyncio

from aespa.services import scanner, traffic
from aespa.services.waf_detect import detect_waf


def test_waf_detection_returns_provider_specific_strategies():
    cases = [
        ({"server": "cloudflare"}, "Cloudflare", "browser_page"),
        ({"x-amzn-waf-action": "challenge"}, "AWS WAF", "browser_page"),
        ({"server": "sucuri/cloudproxy"}, "Sucuri CloudProxy", "direct_http"),
    ]

    for headers, provider, transport in cases:
        detection = detect_waf(headers, None)
        assert detection is not None
        assert detection["provider"] == provider
        assert detection["strategy"]["transport"] == transport
        assert detection["strategy"]["summary"]


def test_amazon_request_id_alone_is_not_waf_evidence():
    assert detect_waf({"x-amzn-requestid": "ordinary-aws-response"}, None) is None


class _FakeResponse:
    status_code = 200
    headers = {"content-type": "application/json"}
    text = '{"ok":true}'


class _FakeHttpClient:
    def __init__(self):
        self.called = False

    async def request(self, *args, **kwargs):
        self.called = True
        return _FakeResponse()


class _FakeBrowserContext:
    def __init__(self):
        self.added_cookies: list[dict] = []
        self.extra_headers: dict = {}

    async def clear_cookies(self):
        self.added_cookies = []

    async def add_cookies(self, cookies):
        self.added_cookies.extend(cookies)

    async def set_extra_http_headers(self, headers):
        self.extra_headers = headers


class _FakeBrowserPage:
    def __init__(self):
        self.evaluate_calls = 0
        self.goto_calls = []

    async def evaluate(self, expression, argument=None):
        if expression == "location.origin":
            return "https://target.local"
        self.evaluate_calls += 1
        return {
            "status": 200,
            "url": "https://target.local/api/check",
            "type": "basic",
            "headers": {"content-type": "application/json"},
            "text": '{"ok":true}',
        }

    async def goto(self, url, **kwargs):
        self.goto_calls.append(url)

    async def wait_for_timeout(self, _milliseconds):
        return None


def test_browser_strategy_uses_page_fetch_for_named_sessions():
    traffic._waf_cache.clear()
    detection = detect_waf({"server": "cloudflare"}, None)
    traffic._waf_cache[("web", 91)] = detection

    http_client = _FakeHttpClient()
    browser_context = _FakeBrowserContext()
    browser_page = _FakeBrowserPage()
    response = asyncio.run(
        scanner._dispatch_http_request(
            http_client,
            browser_context,
            91,
            "GET",
            "https://target.local/api/check",
            {"X-Test": "one"},
            None,
            selected_session={
                "cookies": {"other_session": "yes"},
                "extra_headers": {"Authorization": "Bearer other"},
            },
            primary_session={
                "cookies": {"primary_session": "yes"},
                "extra_headers": {"Authorization": "Bearer primary"},
            },
            primary_browser_cookies=[
                {
                    "name": "primary_session",
                    "value": "yes",
                    "url": "https://target.local",
                },
                {
                    "name": "cf_clearance",
                    "value": "clear",
                    "url": "https://target.local",
                },
            ],
            browser_page=browser_page,
        )
    )

    assert response.status_code == 200
    assert browser_page.evaluate_calls == 1
    assert not http_client.called
    cookie_header = response.request.headers["Cookie"]
    assert "other_session=<browser>" in cookie_header
    assert "cf_clearance=<browser>" in cookie_header
    assert "primary_session=<browser>" not in cookie_header
    assert browser_context.extra_headers["Authorization"] == "Bearer other"


def test_direct_strategy_does_not_use_browser_page():
    traffic._waf_cache.clear()
    traffic._waf_cache[("web", 92)] = detect_waf({"server": "sucuri/cloudproxy"}, None)

    http_client = _FakeHttpClient()
    browser_context = _FakeBrowserContext()
    browser_page = _FakeBrowserPage()
    response = asyncio.run(
        scanner._dispatch_http_request(
            http_client,
            browser_context,
            92,
            "GET",
            "https://target.local/",
            {},
            None,
            selected_session=None,
            browser_page=browser_page,
        )
    )

    assert response.status_code == 200
    assert http_client.called
    assert browser_page.evaluate_calls == 0
