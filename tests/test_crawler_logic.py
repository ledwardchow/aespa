import asyncio

from aespa.services import crawler


def test_page_function_label_removes_credential_possessive():
    assert (
        crawler._page_function_label("Zoe's Accounts Overview") == "Accounts Overview"
    )
    assert (
        crawler._page_function_label("Admin User Management") == "Admin User Management"
    )


class _FakeLocator:
    def __init__(self, count=0, visible=False):
        self._count = count
        self._visible = visible

    async def count(self):
        return self._count

    async def is_visible(self):
        return self._visible


class _FakeLocatorRoot:
    def __init__(self, locator):
        self.first = locator


class _IndexedLocatorRoot:
    def __init__(self, locators):
        self._locators = locators
        self.first = locators[0]

    async def count(self):
        return len(self._locators)

    def nth(self, index):
        return self._locators[index]


def test_visible_locator_skips_hidden_first_match():
    hidden = _FakeLocator(count=1, visible=False)
    visible = _FakeLocator(count=1, visible=True)

    class _Page:
        def locator(self, selector):  # noqa: ARG002
            return _IndexedLocatorRoot([hidden, visible])

    assert asyncio.run(crawler._visible_locator(_Page(), "input")) is visible


class _FakePage:
    def __init__(self, url, text, password_count=0, password_visible=False):
        self.url = url
        self._text = text
        self._locator = _FakeLocator(password_count, password_visible)

    def locator(self, selector):  # noqa: ARG002
        return _FakeLocatorRoot(self._locator)

    async def evaluate(self, script):  # noqa: ARG002
        return self._text


class _FakeResponse:
    def __init__(self, status):
        self.status = status


class _FakeAuthCheckPage:
    url = "https://target.local/dashboard"

    async def goto(self, url, **kwargs):  # noqa: ARG002
        self.url = url
        return _FakeResponse(200)

    async def wait_for_load_state(self, *args, **kwargs):  # noqa: ARG002
        return None

    async def title(self):
        return "Dashboard"

    async def evaluate(self, script):  # noqa: ARG002
        return "Welcome Alice Account overview Recent transfers Settings"

    def locator(self, selector):  # noqa: ARG002
        return _FakeLocatorRoot(_FakeLocator(0, False))

    async def close(self):
        return None


class _FakeContext:
    async def new_page(self):
        return _FakeAuthCheckPage()


class _FakeRecoveryPage:
    context = _FakeContext()

    async def goto(self, url, **kwargs):  # noqa: ARG002
        return _FakeResponse(401)

    async def wait_for_load_state(self, *args, **kwargs):  # noqa: ARG002
        return None


class _TimeoutAfterNavigationPage:
    def __init__(self, url):
        self.url = url

    async def goto(self, url, **kwargs):  # noqa: ARG002
        self.url = url
        raise TimeoutError("Page.goto: Timeout 20000ms exceeded.")


class _HardTimeoutPage:
    url = "about:blank"

    async def goto(self, url, **kwargs):  # noqa: ARG002
        raise TimeoutError("Page.goto: Timeout 20000ms exceeded.")


def test_session_ending_url_detection_matches_logout_variants():
    assert crawler._is_session_ending_url("https://target.local/logout") is True
    assert (
        crawler._is_session_ending_url("https://target.local/account/log-out") is True
    )
    assert (
        crawler._is_session_ending_url("https://target.local/session/end", "Sign out")
        is True
    )
    assert (
        crawler._is_session_ending_url("https://target.local/profile", "Log out")
        is True
    )


def test_session_ending_url_detection_ignores_normal_links():
    assert crawler._is_session_ending_url("https://target.local/account") is False
    assert (
        crawler._is_session_ending_url(
            "https://target.local/signature", "Sign document"
        )
        is False
    )


def test_same_url_without_fragment_ignores_fragment_only():
    assert (
        crawler._same_url_without_fragment(
            "https://target.local/login#next",
            "https://target.local/login",
        )
        is True
    )


class _CredWithLogin:
    login_url = "https://target.local/admin/login"


def test_login_url_for_credential_prefers_credential_override():
    assert (
        crawler._login_url_for_credential(
            "https://target.local/login",
            _CredWithLogin(),
        )
        == "https://target.local/admin/login"
    )


def test_login_url_for_credential_falls_back_to_site_default():
    assert (
        crawler._login_url_for_credential(
            "https://target.local/login",
            object(),
        )
        == "https://target.local/login"
    )


def test_site_base_url_preserves_mounted_app_trailing_slash():
    assert (
        crawler._site_base_url("https://target.local/banking/")
        == "https://target.local/banking/"
    )


def test_goto_lenient_continues_when_timeout_reached_target():
    page = _TimeoutAfterNavigationPage("about:blank")

    response = asyncio.run(crawler._goto_lenient(page, "https://target.local/banking/"))

    assert response is None
    assert page.url == "https://target.local/banking/"


def test_goto_lenient_raises_when_timeout_did_not_reach_target():
    page = _HardTimeoutPage()

    try:
        asyncio.run(crawler._goto_lenient(page, "https://target.local/banking/"))
    except TimeoutError:
        pass
    else:
        raise AssertionError("Expected timeout to be re-raised")


def test_public_asset_candidates_include_origin_and_app_prefix():
    urls = crawler._public_asset_candidates("https://target.local/banking/")

    assert "https://target.local/robots.txt" in urls
    assert "https://target.local/banking/robots.txt" in urls
    assert "https://target.local/openapi.json" in urls
    assert "https://target.local/banking/openapi.json" in urls


def test_extract_sitemap_locations():
    xml = "<urlset><url><loc>https://target.local/admin</loc></url></urlset>"

    assert crawler._extract_sitemap_locations(xml) == ["https://target.local/admin"]


def test_extract_robots_paths_resolves_directives():
    body = """
    User-agent: *
    Disallow: /admin
    Allow: /api/status
    Sitemap: https://target.local/sitemap.xml
    """

    assert crawler._extract_robots_paths("https://target.local/robots.txt", body) == [
        "https://target.local/admin",
        "https://target.local/api/status",
        "https://target.local/sitemap.xml",
    ]


def test_extract_sourcemap_urls_resolves_relative_reference():
    body = "//# sourceMappingURL=app.js.map"

    assert crawler._extract_sourcemap_urls(
        "https://target.local/static/app.js", body
    ) == ["https://target.local/static/app.js.map"]


def test_extract_js_api_calls_captures_fetch_and_axios_methods():
    js = """
    fetch('/api/users', { method: 'POST', body: JSON.stringify({email, password}) })
    axios.delete('/api/admin/users/7')
    axios({ url: '/api/orders/42/verify', method: 'PATCH', data: { otpCode: code } })
    """

    calls = crawler._extract_js_api_calls(js)
    by_url = {call["url"]: call for call in calls}

    assert by_url["/api/users"]["method"] == "POST"
    assert {"email", "password"} <= set(by_url["/api/users"]["body_fields"])
    assert by_url["/api/admin/users/7"]["method"] == "DELETE"
    assert by_url["/api/orders/42/verify"]["method"] == "PATCH"


def test_extract_js_routes_storage_and_feature_flags():
    js = """
    const routes = [{ path: '/admin/audit' }, { path: '/account/:id/verify' }];
    localStorage.getItem('accessToken');
    sessionStorage.setItem('csrfToken', token);
    window.flags = { 'featurePaymentsV2': true, 'adminDebugPanel': false };
    """

    routes = crawler._extract_js_route_paths(js)
    flags = crawler._extract_feature_flags(js)

    assert {route["path"] for route in routes} == {
        "/admin/audit",
        "/account/:id/verify",
    }
    assert {route["category"] for route in routes} == {"admin", "validation"}
    assert crawler._extract_storage_keys_from_js(js) == ["accessToken", "csrfToken"]
    assert {flag["key"] for flag in flags} == {"featurePaymentsV2", "adminDebugPanel"}


def test_mine_asset_text_promotes_typed_js_leads(monkeypatch):
    saved = []
    monkeypatch.setattr(
        crawler, "_save_intel_item", lambda **kwargs: saved.append(kwargs)
    )
    js = """
    fetch('/api/users/register', { method: 'POST', body: JSON.stringify({email, password}) })
    const route = { path: '/admin/reports' };
    localStorage.getItem('auth_token');
    const flags = { 'featureExports': true };
    """

    crawler._mine_asset_text(
        run_id=1,
        asset_url="https://target.local/static/app.js",
        body=js,
        source="js_asset",
        page_url="https://target.local/",
    )

    endpoints = [item for item in saved if item["kind"] == "endpoint"]
    inputs = [item for item in saved if item["kind"] == "input"]
    storage_keys = [item for item in saved if item["kind"] == "storage_key"]
    feature_flags = [item for item in saved if item["kind"] == "feature_flag"]

    assert any(
        item["value"] == "https://target.local/api/users/register"
        and item.get("method") == "POST"
        for item in endpoints
    )
    assert any(
        item["value"] == "https://target.local/admin/reports"
        and item.get("metadata", {}).get("category") == "admin"
        for item in endpoints
    )
    assert {item["key"] for item in inputs} >= {"email", "password"}
    assert any(item["key"] == "auth_token" for item in storage_keys)
    assert any(item["key"] == "featureExports" for item in feature_flags)


def test_page_requires_login_ignores_login_url_without_login_ui():
    page = _FakePage(
        "https://target.local/login",
        "Welcome Alice Account overview Settings",
    )

    assert (
        asyncio.run(crawler._page_requires_login(page, "https://target.local/login"))
        is False
    )


def test_page_requires_login_detects_visible_password_field():
    page = _FakePage(
        "https://target.local/login",
        "Welcome back",
        password_count=1,
        password_visible=True,
    )

    assert (
        asyncio.run(crawler._page_requires_login(page, "https://target.local/login"))
        is True
    )


def test_page_requires_login_detects_explicit_login_wall_text():
    page = _FakePage(
        "https://target.local/account",
        "Please sign in to continue",
    )

    assert (
        asyncio.run(crawler._page_requires_login(page, "https://target.local/login"))
        is True
    )


class _ModalLoginPage:
    """Playwright-visible password field beneath a closed modal backdrop."""

    def __init__(self):
        self._form_visible = False
        self.clicked = None

    def locator(self, selector):
        page = self

        class _Loc:
            async def count(self):
                if selector == "input[type='password']":
                    return 1
                return 1  # any trigger selector "exists"

            async def is_visible(self):
                if selector == "input[type='password']":
                    # Playwright considers opacity-zero descendants visible when
                    # they retain layout dimensions.
                    return True
                return page.clicked is None  # trigger visible until clicked

            async def evaluate(self, script, actionable):  # noqa: ARG002
                if selector == "input[type='password']":
                    return page._form_visible
                return page.clicked is None

            async def click(self):
                page.clicked = selector
                page._form_visible = True

        return _FakeLocatorRoot(_Loc())

    async def wait_for_timeout(self, ms):  # noqa: ARG002
        return None


def test_reveal_login_form_clicks_trigger_when_no_form_visible():
    page = _ModalLoginPage()
    asyncio.run(crawler._reveal_login_form(page))
    assert page.clicked is not None
    assert page._form_visible is True


def test_reveal_login_form_noop_when_form_already_visible():
    page = _ModalLoginPage()
    page._form_visible = True
    asyncio.run(crawler._reveal_login_form(page))
    assert page.clicked is None


def test_page_requires_login_ignores_password_inside_closed_modal():
    page = _ModalLoginPage()

    assert (
        asyncio.run(crawler._page_requires_login(page, "https://target.local/"))
        is False
    )


class _InteractiveControlsPage:
    def __init__(self):
        self.script = ""

    async def evaluate(self, script):
        self.script = script
        return [
            {
                "tag": "a",
                "role": "link",
                "name": "Open account",
                "testid": None,
                "id": None,
            }
        ]


def test_interactive_controls_include_replayable_non_navigation_links():
    page = _InteractiveControlsPage()

    controls = asyncio.run(crawler._interactive_controls(page))

    assert 'a[href="#"]' in page.script
    assert controls == [
        {
            "role": "link",
            "name": "Open account",
            "testid": None,
            "element_id": None,
            "selector": "",
        }
    ]


def test_crawl_seed_urls_preserve_same_scope_authenticated_landing():
    assert crawler._crawl_seed_urls(
        "https://target.local/app/",
        "https://target.local/app/account",
        "target.local",
        "/app/",
    ) == [
        "https://target.local/app/account",
        "https://target.local/app/",
    ]


def test_crawl_seed_urls_reject_external_authenticated_landing():
    assert crawler._crawl_seed_urls(
        "https://target.local/app/",
        "https://identity.example/callback",
        "target.local",
        "/app/",
    ) == ["https://target.local/app/"]


def test_auth_check_matches_similar_post_login_page():
    snapshot = {
        "title": "Dashboard",
        "text": "Welcome Alice Account overview Recent transfers Settings",
    }

    assert (
        crawler._auth_check_matches_snapshot(
            snapshot,
            "Dashboard",
            "Welcome Alice Account overview Recent payments Settings",
        )
        is True
    )


def test_auth_recovery_skips_reauth_when_known_good_page_loads(monkeypatch):
    reauth_calls = []

    async def fake_authenticate(*args, **kwargs):  # noqa: ARG001
        reauth_calls.append(True)

    monkeypatch.setattr(crawler, "_authenticate", fake_authenticate)

    response = asyncio.run(
        crawler._goto_with_auth_recovery(
            _FakeRecoveryPage(),
            "https://target.local/admin",
            requires_auth=True,
            credential=object(),
            login_url="https://target.local/login",
            username="alice",
            auth_check_snapshot={
                "url": "https://target.local/dashboard",
                "title": "Dashboard",
                "text": "Welcome Alice Account overview Recent transfers Settings",
            },
        )
    )

    assert response.status == 401
    assert reauth_calls == []


def test_auth_recovery_does_not_reauth_api_401_without_snapshot(monkeypatch):
    reauth_calls = []

    async def fake_authenticate(*args, **kwargs):  # noqa: ARG001
        reauth_calls.append(True)

    monkeypatch.setattr(crawler, "_authenticate", fake_authenticate)

    response = asyncio.run(
        crawler._goto_with_auth_recovery(
            _FakeRecoveryPage(),
            "https://target.local/api/accounts/22",
            requires_auth=True,
            credential=object(),
            login_url="https://target.local/login",
            username="alice",
            auth_check_snapshot=None,
        )
    )

    assert response.status == 401
    assert reauth_calls == []


def test_auth_recovery_does_not_probe_known_good_page_for_api_401_when_disabled(
    monkeypatch,
):
    sanity_calls = []
    reauth_calls = []

    async def fake_sanity_check(*args, **kwargs):  # noqa: ARG001
        sanity_calls.append(True)
        return True

    async def fake_authenticate(*args, **kwargs):  # noqa: ARG001
        reauth_calls.append(True)

    monkeypatch.setattr(crawler, "_auth_check_still_authenticated", fake_sanity_check)
    monkeypatch.setattr(crawler, "_authenticate", fake_authenticate)

    response = asyncio.run(
        crawler._goto_with_auth_recovery(
            _FakeRecoveryPage(),
            "https://target.local/api/accounts/22",
            requires_auth=True,
            credential=object(),
            login_url="https://target.local/login",
            username="alice",
            auth_check_snapshot={
                "url": "https://target.local/dashboard",
                "title": "Dashboard",
                "text": "Welcome Alice Account overview Recent transfers Settings",
            },
            recover_api_auth=False,
        )
    )

    assert response.status == 401
    assert sanity_calls == []
    assert reauth_calls == []


def test_filter_suggested_links_drops_llm_invented_object_url():
    observed = [
        ("https://target.local/banking/#/accounts/1", "Current account 10000001")
    ]
    suggested = ["https://target.local/banking/#/accounts/10000001"]

    assert crawler._filter_suggested_links(suggested, observed, "target.local") == []


def test_filter_suggested_links_keeps_observed_url():
    observed = [
        ("https://target.local/banking/#/accounts/1", "Current account 10000001")
    ]
    suggested = ["https://target.local/banking/#/accounts/1"]

    assert crawler._filter_suggested_links(suggested, observed, "target.local") == [
        "https://target.local/banking/#/accounts/1"
    ]


def test_same_domain_ignores_explicit_default_port():
    # https with an explicit :443 (and vice-versa) must still be same-domain.
    assert crawler._same_domain("https://target.local:443/x", "target.local") is True
    assert crawler._same_domain("https://target.local/x", "target.local:443") is True
    assert crawler._same_domain("http://target.local:80/x", "target.local") is True


def test_same_domain_rejects_different_host_or_nondefault_port():
    assert crawler._same_domain("https://evil.local/x", "target.local") is False
    # A non-default explicit port is a different origin and must not match.
    assert crawler._same_domain("https://target.local:8443/x", "target.local") is False
    # Non-http(s) schemes are never same-domain.
    assert crawler._same_domain("ftp://target.local/x", "target.local") is False


def test_norm_netloc_strips_default_port_keeps_custom():
    assert crawler._norm_netloc("target.local:443", "https") == "target.local"
    assert crawler._norm_netloc("target.local:80", "http") == "target.local"
    assert crawler._norm_netloc("target.local:8443", "https") == "target.local:8443"
    assert crawler._norm_netloc("user:pass@target.local:443", "https") == "target.local"
    # IPv6 literal without a port must be left intact (tail is not numeric).
    assert crawler._norm_netloc("[::1]", "https") == "[::1]"


def test_access_failure_text_detects_could_not_load_details():
    assert (
        crawler._looks_like_access_failure_text(
            "Account details\nCould not load details\nTry again later"
        )
        is True
    )


def test_access_failure_text_ignores_normal_account_details():
    assert (
        crawler._looks_like_access_failure_text(
            "Account details\nBalance GBP 1,204.55\nRecent transactions"
        )
        is False
    )


def test_confirm_direct_page_access_rejects_failure_text_without_llm(monkeypatch):
    called = False

    async def fake_judge(*args, **kwargs):  # noqa: ARG001
        nonlocal called
        called = True
        return {"accessible": True, "reasoning": "ok"}

    monkeypatch.setattr(crawler.llm_svc, "judge_page_access", fake_judge)

    accessible, reason = asyncio.run(
        crawler._confirm_direct_page_access(
            llm_cfg=object(),
            url="https://target.local/banking/#/accounts/1",
            original_title="Account details",
            original_text="Account number 10000001",
            candidate_title="Account details",
            candidate_text="Could not load details",
            candidate_username="bob",
            screenshot_b64=None,
        )
    )

    assert accessible is False
    assert "access failure" in reason
    assert called is False


def test_confirm_direct_page_access_uses_llm_judgement(monkeypatch):
    async def fake_judge(*args, **kwargs):  # noqa: ARG001
        return {
            "accessible": True,
            "reasoning": "Shows equivalent account details for this user.",
        }

    monkeypatch.setattr(crawler.llm_svc, "judge_page_access", fake_judge)

    accessible, reason = asyncio.run(
        crawler._confirm_direct_page_access(
            llm_cfg=object(),
            url="https://target.local/banking/#/accounts/1",
            original_title="Account details",
            original_text="Account number 10000001",
            candidate_title="Account details",
            candidate_text="Account number 20000002\nBalance GBP 88.10",
            candidate_username="bob",
            screenshot_b64=None,
        )
    )

    assert accessible is True
    assert "equivalent" in reason


def test_api_response_candidate_detects_fetch_and_json():
    assert (
        crawler._is_api_response_candidate(
            "https://target.local/banking/accounts",
            "fetch",
            "text/html",
        )
        is True
    )
    assert (
        crawler._is_api_response_candidate(
            "https://target.local/anything",
            "document",
            "application/json",
        )
        is True
    )


def test_api_response_candidate_ignores_document_html():
    assert (
        crawler._is_api_response_candidate(
            "https://target.local/banking/#/dashboard",
            "document",
            "text/html",
        )
        is False
    )


def test_dedupe_api_calls_uses_method_and_normalized_url():
    calls = [
        {"method": "GET", "url": "https://target.local/api/accounts/1"},
        {"method": "GET", "url": "https://target.local/api/accounts/1/"},
        {"method": "POST", "url": "https://target.local/api/accounts/1"},
    ]

    deduped = crawler._dedupe_api_calls(calls)

    assert len(deduped) == 2
    assert [call["method"] for call in deduped] == ["GET", "POST"]


def test_url_has_object_ref_detects_path_and_query_ids():
    assert (
        crawler._url_has_object_ref("https://target.local/api/accounts/10000001")
        is True
    )
    assert (
        crawler._url_has_object_ref("https://target.local/api/accounts?id=10000001")
        is True
    )
    assert crawler._url_has_object_ref("https://target.local/api/accounts") is False


def test_analyse_api_call_sends_no_screenshot_to_llm(monkeypatch):
    captured = {}

    async def fake_analyse_page(config, url, title, text, screenshot_b64=None):
        captured.update(
            {
                "config": config,
                "url": url,
                "title": title,
                "text": text,
                "screenshot_b64": screenshot_b64,
            }
        )
        return (
            "Returns account data.",
            [],
            {
                "req_auth": None,
                "takes_input": False,
                "has_object_ref": False,
                "has_business_logic": True,
            },
        )

    monkeypatch.setattr(crawler.llm_svc, "analyse_page", fake_analyse_page)

    title, context, categories = asyncio.run(
        crawler._analyse_api_call(
            object(),
            {
                "method": "GET",
                "url": "https://target.local/api/accounts/10000001",
                "request_headers": {"content-type": "application/json"},
                "request_body": '{"accountId":"10000001"}',
                "status": 200,
                "content_type": "application/json",
                "body": '{"accountNumber":"10000001"}',
            },
            credential_id=7,
        )
    )

    assert captured["screenshot_b64"] is None
    assert "REQUEST" in captured["text"]
    assert '"accountId":"10000001"' in captured["text"]
    assert "RESPONSE" in captured["text"]
    assert title.startswith("API GET 200")
    assert "Returns account data" in context
    assert categories["req_auth"] is True
    assert categories["has_object_ref"] is True
    assert categories["has_business_logic"] is True


def test_analyse_api_call_falls_back_when_llm_fails(monkeypatch):
    async def fake_analyse_page(*args, **kwargs):  # noqa: ARG001
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(crawler.llm_svc, "analyse_page", fake_analyse_page)

    _title, context, categories = asyncio.run(
        crawler._analyse_api_call(
            object(),
            {
                "method": "POST",
                "url": "https://target.local/api/payments",
                "status": 201,
                "content_type": "application/json",
                "body": "{}",
            },
            credential_id=None,
        )
    )

    assert "[API endpoint]" in context
    assert categories["takes_input"] is True


def test_api_categories_detects_object_ref_in_request_body():
    categories = crawler._api_categories(
        {
            "method": "POST",
            "url": "https://target.local/api/accounts/lookup",
            "request_body": '{"account":{"id":"10000001"}}',
        },
        credential_id=7,
    )

    assert categories["takes_input"] is True
    assert categories["has_object_ref"] is True


# ── LLM-driven adaptive login fallback ────────────────────────────────────────


class _SmartCred:
    id = 1
    username = "alice"
    password = "s3cr3t-pw"
    auth_mode = "auto"


class _SmartLoginLocator:
    def __init__(self, page, selector):
        self._page = page
        self._selector = selector
        self.first = self

    async def count(self):
        if self._selector == "input[type='password']":
            return 0 if self._page.logged_in else 1
        # Action targets always resolve.
        return 1

    async def is_visible(self):
        if self._selector == "input[type='password']":
            return not self._page.logged_in
        return True

    async def fill(self, value):
        self._page.fills.append((self._selector, value))

    async def click(self, **kwargs):  # noqa: ARG002
        self._page.clicks.append(self._selector)
        if self._selector == "#submit":
            self._page.logged_in = True

    async def press(self, key):
        self._page.presses.append((self._selector, key))


class _SmartLoginPage:
    """Fake Playwright page that flips to logged-in after the submit click."""

    def __init__(self):
        self.url = "https://target.local/"
        self.logged_in = False
        self.fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []
        self.presses: list[tuple[str, str]] = []

    def locator(self, selector):
        return _SmartLoginLocator(self, selector)

    def get_by_text(self, text, exact=False):  # noqa: ARG002
        return _SmartLoginLocator(self, f"text={text}")

    async def evaluate(self, script):
        if "document.body.innerText" in script:
            return (
                "Welcome alice — your dashboard" if self.logged_in else "Please log in"
            )
        if "storage_keys" in script:  # _extract_dom_intelligence
            return {
                "scripts": [],
                "assets": [],
                "forms": [
                    {
                        "selector": "form#login",
                        "fields": [
                            {"selector": "#user", "type": "text", "name": "user"},
                            {"selector": "#pass", "type": "password", "name": "pass"},
                        ],
                    }
                ],
                "storage_keys": [],
            }
        if "role='button'" in script:  # clickable controls query
            return [
                {
                    "tag": "button",
                    "text": "Sign in",
                    "id": "login-trigger",
                    "sel": "#login-trigger",
                }
            ]
        return []

    async def wait_for_timeout(self, *args, **kwargs):  # noqa: ARG002
        return None


def test_authenticate_smart_completes_login_and_substitutes_credentials(monkeypatch):
    page = _SmartLoginPage()
    cred = _SmartCred()

    scripted = [
        {"action": "click", "selector": "#login-trigger", "reason": "reveal modal"},
        {
            "action": "fill",
            "selector": "#user",
            "value": "{{username}}",
            "reason": "username",
        },
        {
            "action": "fill",
            "selector": "#pass",
            "value": "{{password}}",
            "reason": "password",
        },
        {"action": "click", "selector": "#submit", "reason": "submit"},
    ]
    seen_payloads: list[dict] = []

    async def _fake_decide(config, **kwargs):  # noqa: ARG001
        seen_payloads.append(kwargs)
        return scripted.pop(0)

    monkeypatch.setattr(crawler.llm_svc, "decide_login_action", _fake_decide)

    class _LLMCfg:
        use_vision = False

    asyncio.run(
        crawler._authenticate_smart(
            page, "https://target.local/login", cred, 1, _LLMCfg()
        )
    )

    # Login succeeded and the real credentials were typed (placeholders resolved).
    assert page.logged_in is True
    assert ("#user", "alice") in page.fills
    assert ("#pass", "s3cr3t-pw") in page.fills
    # The real password is never leaked into anything sent to the LLM.
    for payload in seen_payloads:
        blob = repr(payload)
        assert "s3cr3t-pw" not in blob


def test_crawl_log_emits_scanner_phase_event(monkeypatch):
    captured: list[tuple[int, dict]] = []
    monkeypatch.setattr(
        crawler.events_svc, "emit", lambda rid, evt: captured.append((rid, evt))
    )

    crawler._crawl_log(
        7, "crawl", "start", "Crawl started", page_url="https://t.local/"
    )

    assert len(captured) == 1
    run_id, evt = captured[0]
    assert run_id == 7
    assert evt["type"] == "scanner_phase"
    assert evt["phase"] == "crawl"
    assert evt["status"] == "start"
    assert evt["message"] == "Crawl started"
    assert evt["page_url"] == "https://t.local/"


def test_crawl_log_noop_for_zero_run_id(monkeypatch):
    captured: list = []
    monkeypatch.setattr(
        crawler.events_svc, "emit", lambda rid, evt: captured.append((rid, evt))
    )

    crawler._crawl_log(0, "auth", "info", "should not emit")

    assert captured == []


def test_authenticate_skips_smart_fallback_without_llm_cfg(monkeypatch):
    """Back-compat: with llm_cfg=None the LLM fallback must never be invoked."""
    called = {"smart": False}

    async def _noop_auto(*args, **kwargs):  # noqa: ARG001
        return None

    async def _flag_smart(*args, **kwargs):  # noqa: ARG001
        called["smart"] = True

    monkeypatch.setattr(crawler, "_authenticate_auto", _noop_auto)
    monkeypatch.setattr(crawler, "_authenticate_smart", _flag_smart)

    asyncio.run(
        crawler._authenticate(
            _SmartLoginPage(), "https://target.local/login", _SmartCred()
        )
    )

    assert called["smart"] is False


def test_authenticate_routes_entra_id_mode(monkeypatch):
    called = {"entra": False, "auto": False}

    class _Cred(_SmartCred):
        id = 42
        auth_mode = "entra_id"

    async def _flag_entra(*args, **kwargs):  # noqa: ARG001
        called["entra"] = True

    async def _flag_auto(*args, **kwargs):  # noqa: ARG001
        called["auto"] = True

    monkeypatch.setattr(crawler, "_authenticate_entra_id", _flag_entra)
    monkeypatch.setattr(crawler, "_authenticate_auto", _flag_auto)

    asyncio.run(
        crawler._authenticate(
            _SmartLoginPage(), "https://target.local/login", _Cred(), run_id=1
        )
    )

    assert called == {"entra": True, "auto": False}


def test_authenticate_does_not_reuse_unconfirmed_entra_session(monkeypatch):
    called = {"entra": False}

    class _Cred(_SmartCred):
        id = 42
        auth_mode = "entra_id"

    async def _flag_entra(*args, **kwargs):  # noqa: ARG001
        called["entra"] = True

    crawler._guided_session_cache[(12, 42)] = {
        "cookies": {"AppSession": "stale"},
        "provider": "entra_id",
        "completed": False,
    }
    monkeypatch.setattr(crawler, "_authenticate_entra_id", _flag_entra)

    asyncio.run(
        crawler._authenticate(
            _SmartLoginPage(), "https://target.local/login", _Cred(), run_id=12
        )
    )

    assert called["entra"] is True
    assert (12, 42) not in crawler._guided_session_cache


def test_login_url_for_entra_credential_prefers_site_login_before_provider():
    class _Cred:
        auth_mode = "entra_id"
        login_url = "https://login.microsoftonline.com/"

    assert (
        crawler._login_url_for_credential("https://target.local/login", _Cred())
        == "https://target.local/login"
    )


def test_login_url_for_entra_credential_keeps_provider_without_site_login():
    class _Cred:
        auth_mode = "entra_id"
        login_url = "https://login.microsoftonline.com/"

    assert (
        crawler._login_url_for_credential("", _Cred())
        == "https://login.microsoftonline.com/"
    )


class _EntraContext:
    def __init__(self):
        self.handlers = {}

    def on(self, name, handler):
        self.handlers[name] = handler

    async def cookies(self):
        return [{"name": "AppSession", "value": "abc123"}]

    async def set_extra_http_headers(self, headers):  # noqa: ARG002
        return None


class _EntraLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector
        self.first = self

    async def count(self):
        return 1 if self.page.is_selector_visible(self.selector) else 0

    async def is_visible(self):
        return self.page.is_selector_visible(self.selector)

    async def fill(self, value):
        self.page.fills.append((self.selector, value))
        if "email" in self.selector or "loginfmt" in self.selector:
            self.page.email_filled = True
        if "password" in self.selector or "passwd" in self.selector:
            self.page.password_filled = True

    async def click(self):
        self.page.clicks.append(self.selector)
        if self.page.state == "email" and self.page.email_filled:
            self.page.state = "password"
        elif self.page.state == "password" and self.page.password_filled:
            self.page.state = "stay_signed_in"
        elif self.page.state == "stay_signed_in":
            self.page.state = "done"
            self.page.url = "https://target.local/dashboard"


class _EntraPage:
    def __init__(self):
        self.context = _EntraContext()
        self.url = "about:blank"
        self.state = "email"
        self.email_filled = False
        self.password_filled = False
        self.fills = []
        self.clicks = []

    async def goto(self, url, **kwargs):  # noqa: ARG002
        self.url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"

    async def wait_for_load_state(self, *args, **kwargs):  # noqa: ARG002
        return None

    async def wait_for_timeout(self, *args, **kwargs):  # noqa: ARG002
        return None

    def locator(self, selector):
        return _EntraLocator(self, selector)

    def is_selector_visible(self, selector):
        if self.state == "email":
            return "email" in selector or "loginfmt" in selector or "idSIButton9" in selector
        if self.state == "password":
            return "password" in selector or "passwd" in selector or "idSIButton9" in selector
        if self.state == "stay_signed_in":
            return "idSIButton9" in selector or "Yes" in selector
        return False

    async def evaluate(self, script, *args):  # noqa: ARG002
        if "localStorage" in script:
            return {"access_token": "eyJ.access.token"}
        if "sessionStorage" in script:
            return {}
        if "document.body" in script:
            return {
                "email": "Sign in Enter your email",
                "password": "Enter password",
                "stay_signed_in": "Stay signed in?",
                "done": "Dashboard Account overview",
            }[self.state]
        return "Dashboard Account overview"


class _EntraCred:
    id = 9
    username = "alice@example.com"
    password = "s3cr3t"
    label = "alice"
    auth_mode = "entra_id"


def test_authenticate_entra_id_completes_and_persists_session(monkeypatch):
    captured = {}

    def _fake_upsert(run_id, **kwargs):
        captured["run_id"] = run_id
        captured.update(kwargs)

    monkeypatch.setattr(
        "aespa.services.scanner_sessions.upsert_session", _fake_upsert
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: None)

    page = _EntraPage()
    asyncio.run(
        crawler._authenticate_entra_id(
            page, "https://target.local/login", _EntraCred(), run_id=77
        )
    )

    assert page.url == "https://target.local/dashboard"
    assert ("input[type='email']", "alice@example.com") in page.fills
    assert ("input[type='password']", "s3cr3t") in page.fills
    assert captured["run_id"] == 77
    assert captured["label"] == "entra_9"
    assert captured["source"] == "entra_id_login"
    assert captured["cookies"] == {"AppSession": "abc123"}
    assert captured["extra_headers"]["Authorization"] == "Bearer eyJ.access.token"
    assert captured["metadata"]["auth_provider"] == "entra_id"
    assert captured["metadata"]["completed"] is True


class _EntraTotpPage(_EntraPage):
    def is_selector_visible(self, selector):
        if self.state == "totp":
            return (
                "one-time-code" in selector
                or "SAOTCC" in selector
                or "otc" in selector
                or "code" in selector
                or "idSIButton9" in selector
            )
        return super().is_selector_visible(selector)

    async def evaluate(self, script, *args):  # noqa: ARG002
        if "localStorage" in script:
            return {"access_token": "eyJ.access.token"}
        if "sessionStorage" in script:
            return {}
        if "document.body" in script:
            return {
                "email": "Sign in Enter your email",
                "password": "Enter password",
                "totp": "Enter code from your authenticator app",
                "done": "Dashboard Account overview",
            }[self.state]
        return "Dashboard Account overview"


class _EntraTotpLocator(_EntraLocator):
    async def fill(self, value):
        await super().fill(value)
        if self.page.state == "totp":
            self.page.totp_filled = True

    async def click(self):
        self.page.clicks.append(self.selector)
        if self.page.state == "email" and self.page.email_filled:
            self.page.state = "password"
        elif self.page.state == "password" and self.page.password_filled:
            self.page.state = "totp"
        elif self.page.state == "totp" and getattr(self.page, "totp_filled", False):
            self.page.state = "done"
            self.page.url = "https://target.local/dashboard"


class _EntraTotpPageWithLocator(_EntraTotpPage):
    def __init__(self):
        super().__init__()
        self.totp_filled = False

    def locator(self, selector):
        return _EntraTotpLocator(self, selector)


class _EntraCredWithTotp(_EntraCred):
    totp_seed = "JBSWY3DPEHPK3PXP"


def test_authenticate_entra_id_uses_totp_seed_for_other_app_code(monkeypatch):
    captured = {}

    def _fake_upsert(run_id, **kwargs):
        captured["run_id"] = run_id
        captured.update(kwargs)

    monkeypatch.setattr(
        "aespa.services.scanner_sessions.upsert_session", _fake_upsert
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: None)

    page = _EntraTotpPageWithLocator()
    asyncio.run(
        crawler._authenticate_entra_id(
            page, "https://target.local/login", _EntraCredWithTotp(), run_id=78
        )
    )

    totp_fills = [
        value
        for selector, value in page.fills
        if "one-time-code" in selector or "SAOTCC" in selector
    ]
    assert page.url == "https://target.local/dashboard"
    assert len(totp_fills) == 1
    assert totp_fills[0].isdigit()
    assert len(totp_fills[0]) == 6
    assert captured["metadata"]["completed"] is True


def test_entra_notification_prompt_event_contains_number(monkeypatch):
    captured = []
    monkeypatch.setattr(
        crawler.events_svc, "emit", lambda run_id, event: captured.append((run_id, event))
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: None)

    crawler._emit_entra_notification_prompt(12, 34, "alice@example.com", "42")

    assert captured == [
        (
            12,
            {
                "type": "entra_authenticator_prompt",
                "credential_id": 34,
                "username": "alice@example.com",
                "number": "42",
                "message": "Attempting Entra login as alice@example.com - open Authenticator and enter 42",
            },
        )
    ]


def test_entra_notification_prompt_event_allows_pending_approval(monkeypatch):
    captured = []
    logs = []
    monkeypatch.setattr(
        crawler.events_svc, "emit", lambda run_id, event: captured.append((run_id, event))
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: logs.append(args))

    crawler._emit_entra_notification_prompt(12, 34, "alice@example.com", None)

    assert captured == [
        (
            12,
            {
                "type": "entra_authenticator_prompt",
                "credential_id": 34,
                "username": "alice@example.com",
                "number": None,
                "message": "Attempting Entra login as alice@example.com - open Authenticator and approve the sign-in request",
            },
        )
    ]
    assert logs


def test_entra_authenticator_status_event_reports_success_and_timeout(monkeypatch):
    captured = []
    logs = []
    monkeypatch.setattr(
        crawler.events_svc, "emit", lambda run_id, event: captured.append((run_id, event))
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: logs.append(args))

    crawler._emit_entra_authenticator_status(
        12, 34, "alice@example.com", "success", "42"
    )
    crawler._emit_entra_authenticator_status(
        12, 34, "alice@example.com", "timeout", "42"
    )

    assert captured[0] == (
        12,
        {
            "type": "entra_authenticator_status",
            "credential_id": 34,
            "username": "alice@example.com",
            "number": "42",
            "status": "success",
            "message": "Entra login confirmed for alice@example.com.",
        },
    )
    assert captured[1][1]["status"] == "timeout"
    assert "Timed out waiting for Entra Authenticator approval" in captured[1][1]["message"]
    assert [entry[2] for entry in logs] == ["complete", "error"]


def test_entra_notification_number_detects_number_matching_prompt():
    text = "approve sign in request open authenticator and enter the number 42"
    assert crawler._entra_notification_number(text) == "42"


def test_entra_notification_number_detects_displayed_number_prompt():
    text = "open microsoft authenticator enter the code displayed in your browser 42"
    assert crawler._entra_notification_number(text) == "42"


def test_entra_sso_provider_detection_ignores_bare_sso_app_text():
    text = "dashboard settings authenticated user sso configuration audit logs"
    assert crawler._entra_text_offers_sso_provider(text) is False


def test_entra_sso_provider_detection_keeps_azure_ad_choice():
    text = "choose a login method azure ad one-time pin"
    assert crawler._entra_text_offers_sso_provider(text) is True


def test_entra_detects_retryable_authenticator_failure():
    text = "Your sign in request was denied. Select Try again to send another request."
    assert crawler._entra_text_has_retryable_authenticator_failure(text) is True
    assert crawler._entra_page_kind(text, "https://login.microsoftonline.com/common/SAS") == "authenticator_retry"


class _EntraNotificationPage(_EntraPage):
    def __init__(self):
        super().__init__()
        self.number_was_shown = False

    async def wait_for_timeout(self, *args, **kwargs):  # noqa: ARG002
        if self.state == "number_prompt" and self.number_was_shown:
            self.state = "done"
            self.url = "https://target.local/dashboard"
        return None

    def is_selector_visible(self, selector):
        if self.state == "notification_choice":
            return "Approve a request" in selector or "Microsoft Authenticator" in selector
        if self.state == "number_prompt":
            return False
        return super().is_selector_visible(selector)

    async def evaluate(self, script, *args):  # noqa: ARG002
        if "localStorage" in script:
            return {"access_token": "eyJ.access.token"}
        if "sessionStorage" in script:
            return {}
        if "document.body" in script:
            value = {
                "email": "Sign in Enter your email",
                "password": "Enter password",
                "notification_choice": "Approve a request on my Microsoft Authenticator app",
                "number_prompt": "Open your Authenticator app and enter the number shown below 42 to sign in",
                "done": "Dashboard Account overview",
            }[self.state]
            if self.state == "number_prompt":
                self.number_was_shown = True
            return value
        return "Dashboard Account overview"


class _EntraNotificationLocator(_EntraLocator):
    async def click(self):
        self.page.clicks.append(self.selector)
        if self.page.state == "email" and self.page.email_filled:
            self.page.state = "password"
        elif self.page.state == "password" and self.page.password_filled:
            self.page.state = "notification_choice"
        elif self.page.state == "notification_choice":
            self.page.state = "number_prompt"


class _EntraNotificationPageWithLocator(_EntraNotificationPage):
    def locator(self, selector):
        return _EntraNotificationLocator(self, selector)


class _EntraRetryPage(_EntraPage):
    def __init__(self):
        super().__init__()
        self.state = "retry"

    def is_selector_visible(self, selector):
        if self.state == "retry":
            return "Try again" in selector
        return False


def test_entra_authenticator_retry_waits_for_ui_and_clicks_retry(monkeypatch):
    emitted = []
    monkeypatch.setattr(crawler.events_svc, "emit", lambda *args: emitted.append(args))
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: None)
    page = _EntraRetryPage()

    async def _run():
        task = asyncio.create_task(
            crawler._wait_for_entra_authenticator_retry(
                page, 81, 9, "alice@example.com", "89"
            )
        )
        await asyncio.sleep(0)
        crawler._entra_retry_registry[(81, 9)].set()
        return await task

    assert asyncio.run(_run()) is True
    assert any("Try again" in selector for selector in page.clicks)
    assert emitted[0][1]["type"] == "entra_authenticator_status"
    assert emitted[0][1]["status"] == "retry_required"


class _EntraRetryThenNumberPage(_EntraPage):
    def __init__(self):
        super().__init__()
        self.state = "retry"
        self.retry_clicked = False
        self.body_reads_after_retry = 0
        self.number_was_shown = False

    def is_selector_visible(self, selector):
        if self.state == "retry":
            return "Try again" in selector
        return False

    async def wait_for_timeout(self, *args, **kwargs):  # noqa: ARG002
        if self.number_was_shown:
            self.state = "done"
            self.url = "https://target.local/dashboard"
        return None

    async def evaluate(self, script, *args):  # noqa: ARG002
        if "localStorage" in script:
            return {"access_token": "eyJ.access.token"}
        if "sessionStorage" in script:
            return {}
        if "document.body" in script:
            if self.state == "done":
                return "Dashboard Account overview"
            if self.retry_clicked:
                self.body_reads_after_retry += 1
                if self.body_reads_after_retry > 3:
                    self.number_was_shown = True
                    return "Open Authenticator and enter the number shown below 55"
            return "Your sign in request was denied. Try again to send another request."
        return "Dashboard Account overview"


class _EntraRetryThenNumberLocator(_EntraLocator):
    async def click(self):
        self.page.clicks.append(self.selector)
        if self.page.state == "retry":
            self.page.retry_clicked = True
            return
        await super().click()


class _EntraRetryThenNumberPageWithLocator(_EntraRetryThenNumberPage):
    def locator(self, selector):
        return _EntraRetryThenNumberLocator(self, selector)


def test_authenticate_entra_retry_does_not_immediately_reprompt_failure(monkeypatch):
    emitted = []
    logs = []
    monkeypatch.setattr(
        crawler.events_svc,
        "emit",
        lambda run_id, event: emitted.append((run_id, event)),
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: logs.append(args))
    monkeypatch.setattr(
        "aespa.services.scanner_sessions.upsert_session",
        lambda *args, **kwargs: None,
    )

    page = _EntraRetryThenNumberPageWithLocator()

    async def _run():
        task = asyncio.create_task(
            crawler._authenticate_entra_id(
                page, "https://target.local/login", _EntraCred(), run_id=82
            )
        )
        await asyncio.sleep(0)
        crawler._entra_retry_registry[(82, 9)].set()
        await task

    asyncio.run(_run())

    retry_required = [
        event
        for _run_id, event in emitted
        if event["type"] == "entra_authenticator_status"
        and event["status"] == "retry_required"
    ]
    assert len(retry_required) == 1
    assert any(
        event["type"] == "entra_authenticator_prompt" and event["number"] == "55"
        for _run_id, event in emitted
    )
    assert page.url == "https://target.local/dashboard"


class _EntraCloudflarePage(_EntraPage):
    def __init__(self):
        super().__init__()
        self.state = "sso_choice"

    async def goto(self, url, **kwargs):  # noqa: ARG002
        self.url = "https://target.local/cdn-cgi/access/login"

    def is_selector_visible(self, selector):
        if self.state == "sso_choice":
            return "Azure AD" in selector
        return super().is_selector_visible(selector)

    async def evaluate(self, script, *args):  # noqa: ARG002
        if "localStorage" in script:
            return {"access_token": "eyJ.access.token"}
        if "sessionStorage" in script:
            return {}
        if "document.body" in script:
            return {
                "sso_choice": "Access protected application Azure AD One-time PIN",
                "email": "Sign in Enter your email",
                "password": "Enter password",
                "stay_signed_in": "Stay signed in?",
                "done": "Dashboard Account overview",
            }[self.state]
        return "Dashboard Account overview"


class _EntraCloudflareLocator(_EntraLocator):
    async def click(self):
        self.page.clicks.append(self.selector)
        if self.page.state == "sso_choice":
            self.page.state = "email"
            self.page.url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
            return
        await super().click()


class _EntraCloudflarePageWithLocator(_EntraCloudflarePage):
    def locator(self, selector):
        return _EntraCloudflareLocator(self, selector)


def test_authenticate_entra_id_clicks_upstream_sso_provider(monkeypatch):
    logs = []
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: logs.append(args))
    monkeypatch.setattr(crawler.events_svc, "emit", lambda *args, **kwargs: None)

    captured = {}

    def _fake_upsert(run_id, **kwargs):
        captured["run_id"] = run_id
        captured.update(kwargs)

    monkeypatch.setattr(
        "aespa.services.scanner_sessions.upsert_session", _fake_upsert
    )

    page = _EntraCloudflarePageWithLocator()
    asyncio.run(
        crawler._authenticate_entra_id(
            page, "https://target.local/cdn-cgi/access/login", _EntraCred(), run_id=80
        )
    )

    assert any("Azure AD" in selector for selector in page.clicks)
    assert page.url == "https://target.local/dashboard"
    assert any("Selected upstream Microsoft/Entra SSO provider" in args[3] for args in logs)
    assert captured["metadata"]["completed"] is True


class _EntraPostLoginSsoTextPage(_EntraPage):
    def __init__(self):
        super().__init__()
        self.state = "done"
        self.url = "https://target.local/dashboard"

    async def goto(self, url, **kwargs):  # noqa: ARG002
        self.url = "https://target.local/dashboard"

    async def evaluate(self, script, *args):  # noqa: ARG002
        if "localStorage" in script:
            return {"access_token": "eyJ.access.token"}
        if "sessionStorage" in script:
            return {}
        if "document.body" in script:
            return "Dashboard Settings Azure AD single sign-on audit logs"
        return "Dashboard Settings Azure AD single sign-on audit logs"

    def is_selector_visible(self, selector):
        return False


def test_authenticate_entra_id_accepts_target_app_with_sso_text(monkeypatch):
    emitted = []
    captured = {}
    monkeypatch.setattr(
        crawler.events_svc,
        "emit",
        lambda run_id, event: emitted.append((run_id, event)),
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: None)

    def _fake_upsert(run_id, **kwargs):
        captured["run_id"] = run_id
        captured.update(kwargs)

    monkeypatch.setattr(
        "aespa.services.scanner_sessions.upsert_session", _fake_upsert
    )

    page = _EntraPostLoginSsoTextPage()
    asyncio.run(
        crawler._authenticate_entra_id(
            page, "https://target.local/login", _EntraCred(), run_id=83
        )
    )

    assert captured["metadata"]["completed"] is True
    assert captured["metadata"]["landing_url"] == "https://target.local/dashboard"
    assert not any(
        event["type"] == "entra_authenticator_status" and event["status"] == "timeout"
        for _run_id, event in emitted
    )


def test_authenticate_entra_id_selects_notification_and_emits_number(monkeypatch):
    emitted = []

    monkeypatch.setattr(
        crawler.events_svc,
        "emit",
        lambda run_id, event: emitted.append((run_id, event)),
    )
    monkeypatch.setattr(crawler, "_crawl_log", lambda *args, **kwargs: None)

    page = _EntraNotificationPageWithLocator()
    asyncio.run(
        crawler._authenticate_entra_id(
            page, "https://target.local/login", _EntraCred(), run_id=79
        )
    )

    assert any("Approve a request" in selector for selector in page.clicks)
    assert (
        79,
        {
            "type": "entra_authenticator_prompt",
            "credential_id": 9,
            "username": "alice@example.com",
            "number": None,
            "message": "Attempting Entra login as alice@example.com - open Authenticator and approve the sign-in request",
        },
    ) in emitted
    assert (
        79,
        {
            "type": "entra_authenticator_prompt",
            "credential_id": 9,
            "username": "alice@example.com",
            "number": "42",
            "message": "Attempting Entra login as alice@example.com - open Authenticator and enter 42",
        },
    ) in emitted
    assert (
        79,
        {
            "type": "entra_authenticator_status",
            "credential_id": 9,
            "username": "alice@example.com",
            "number": "42",
            "status": "success",
            "message": "Entra login confirmed for alice@example.com.",
        },
    ) in emitted
