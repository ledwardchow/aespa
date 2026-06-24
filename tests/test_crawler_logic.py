import asyncio

from aespa.services import crawler


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
    assert crawler._is_session_ending_url("https://target.local/account/log-out") is True
    assert crawler._is_session_ending_url("https://target.local/session/end", "Sign out") is True
    assert crawler._is_session_ending_url("https://target.local/profile", "Log out") is True


def test_session_ending_url_detection_ignores_normal_links():
    assert crawler._is_session_ending_url("https://target.local/account") is False
    assert crawler._is_session_ending_url("https://target.local/signature", "Sign document") is False


def test_same_url_without_fragment_ignores_fragment_only():
    assert crawler._same_url_without_fragment(
        "https://target.local/login#next",
        "https://target.local/login",
    ) is True


class _CredWithLogin:
    login_url = "https://target.local/admin/login"


def test_login_url_for_credential_prefers_credential_override():
    assert crawler._login_url_for_credential(
        "https://target.local/login",
        _CredWithLogin(),
    ) == "https://target.local/admin/login"


def test_login_url_for_credential_falls_back_to_site_default():
    assert crawler._login_url_for_credential(
        "https://target.local/login",
        object(),
    ) == "https://target.local/login"


def test_site_base_url_preserves_mounted_app_trailing_slash():
    assert crawler._site_base_url("https://target.local/banking/") == "https://target.local/banking/"


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

    assert crawler._extract_sourcemap_urls("https://target.local/static/app.js", body) == [
        "https://target.local/static/app.js.map"
    ]


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

    assert {route["path"] for route in routes} == {"/admin/audit", "/account/:id/verify"}
    assert {route["category"] for route in routes} == {"admin", "validation"}
    assert crawler._extract_storage_keys_from_js(js) == ["accessToken", "csrfToken"]
    assert {flag["key"] for flag in flags} == {"featurePaymentsV2", "adminDebugPanel"}


def test_mine_asset_text_promotes_typed_js_leads(monkeypatch):
    saved = []
    monkeypatch.setattr(crawler, "_save_intel_item", lambda **kwargs: saved.append(kwargs))
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

    assert any(item["value"] == "https://target.local/api/users/register" and item.get("method") == "POST" for item in endpoints)
    assert any(item["value"] == "https://target.local/admin/reports" and item.get("metadata", {}).get("category") == "admin" for item in endpoints)
    assert {item["key"] for item in inputs} >= {"email", "password"}
    assert any(item["key"] == "auth_token" for item in storage_keys)
    assert any(item["key"] == "featureExports" for item in feature_flags)


def test_page_requires_login_ignores_login_url_without_login_ui():
    page = _FakePage(
        "https://target.local/login",
        "Welcome Alice Account overview Settings",
    )

    assert asyncio.run(crawler._page_requires_login(page, "https://target.local/login")) is False


def test_page_requires_login_detects_visible_password_field():
    page = _FakePage(
        "https://target.local/login",
        "Welcome back",
        password_count=1,
        password_visible=True,
    )

    assert asyncio.run(crawler._page_requires_login(page, "https://target.local/login")) is True


def test_page_requires_login_detects_explicit_login_wall_text():
    page = _FakePage(
        "https://target.local/account",
        "Please sign in to continue",
    )

    assert asyncio.run(crawler._page_requires_login(page, "https://target.local/login")) is True


class _ModalLoginPage:
    """Password field is hidden until a login trigger is clicked (modal login)."""

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
                    return page._form_visible
                return page.clicked is None  # trigger visible until clicked

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


def test_auth_check_matches_similar_post_login_page():
    snapshot = {
        "title": "Dashboard",
        "text": "Welcome Alice Account overview Recent transfers Settings",
    }

    assert crawler._auth_check_matches_snapshot(
        snapshot,
        "Dashboard",
        "Welcome Alice Account overview Recent payments Settings",
    ) is True


def test_auth_recovery_skips_reauth_when_known_good_page_loads(monkeypatch):
    reauth_calls = []

    async def fake_authenticate(*args, **kwargs):  # noqa: ARG001
        reauth_calls.append(True)

    monkeypatch.setattr(crawler, "_authenticate", fake_authenticate)

    response = asyncio.run(crawler._goto_with_auth_recovery(
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
    ))

    assert response.status == 401
    assert reauth_calls == []


def test_auth_recovery_does_not_reauth_api_401_without_snapshot(monkeypatch):
    reauth_calls = []

    async def fake_authenticate(*args, **kwargs):  # noqa: ARG001
        reauth_calls.append(True)

    monkeypatch.setattr(crawler, "_authenticate", fake_authenticate)

    response = asyncio.run(crawler._goto_with_auth_recovery(
        _FakeRecoveryPage(),
        "https://target.local/api/accounts/22",
        requires_auth=True,
        credential=object(),
        login_url="https://target.local/login",
        username="alice",
        auth_check_snapshot=None,
    ))

    assert response.status == 401
    assert reauth_calls == []


def test_auth_recovery_does_not_probe_known_good_page_for_api_401_when_disabled(monkeypatch):
    sanity_calls = []
    reauth_calls = []

    async def fake_sanity_check(*args, **kwargs):  # noqa: ARG001
        sanity_calls.append(True)
        return True

    async def fake_authenticate(*args, **kwargs):  # noqa: ARG001
        reauth_calls.append(True)

    monkeypatch.setattr(crawler, "_auth_check_still_authenticated", fake_sanity_check)
    monkeypatch.setattr(crawler, "_authenticate", fake_authenticate)

    response = asyncio.run(crawler._goto_with_auth_recovery(
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
    ))

    assert response.status == 401
    assert sanity_calls == []
    assert reauth_calls == []


def test_filter_suggested_links_drops_llm_invented_object_url():
    observed = [("https://target.local/banking/#/accounts/1", "Current account 10000001")]
    suggested = ["https://target.local/banking/#/accounts/10000001"]

    assert crawler._filter_suggested_links(suggested, observed, "target.local") == []


def test_filter_suggested_links_keeps_observed_url():
    observed = [("https://target.local/banking/#/accounts/1", "Current account 10000001")]
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
    assert crawler._looks_like_access_failure_text(
        "Account details\nCould not load details\nTry again later"
    ) is True


def test_access_failure_text_ignores_normal_account_details():
    assert crawler._looks_like_access_failure_text(
        "Account details\nBalance GBP 1,204.55\nRecent transactions"
    ) is False


def test_confirm_direct_page_access_rejects_failure_text_without_llm(monkeypatch):
    called = False

    async def fake_judge(*args, **kwargs):  # noqa: ARG001
        nonlocal called
        called = True
        return {"accessible": True, "reasoning": "ok"}

    monkeypatch.setattr(crawler.llm_svc, "judge_page_access", fake_judge)

    accessible, reason = asyncio.run(crawler._confirm_direct_page_access(
        llm_cfg=object(),
        url="https://target.local/banking/#/accounts/1",
        original_title="Account details",
        original_text="Account number 10000001",
        candidate_title="Account details",
        candidate_text="Could not load details",
        candidate_username="bob",
        screenshot_b64=None,
    ))

    assert accessible is False
    assert "access failure" in reason
    assert called is False


def test_confirm_direct_page_access_uses_llm_judgement(monkeypatch):
    async def fake_judge(*args, **kwargs):  # noqa: ARG001
        return {"accessible": True, "reasoning": "Shows equivalent account details for this user."}

    monkeypatch.setattr(crawler.llm_svc, "judge_page_access", fake_judge)

    accessible, reason = asyncio.run(crawler._confirm_direct_page_access(
        llm_cfg=object(),
        url="https://target.local/banking/#/accounts/1",
        original_title="Account details",
        original_text="Account number 10000001",
        candidate_title="Account details",
        candidate_text="Account number 20000002\nBalance GBP 88.10",
        candidate_username="bob",
        screenshot_b64=None,
    ))

    assert accessible is True
    assert "equivalent" in reason


def test_api_response_candidate_detects_fetch_and_json():
    assert crawler._is_api_response_candidate(
        "https://target.local/banking/accounts",
        "fetch",
        "text/html",
    ) is True
    assert crawler._is_api_response_candidate(
        "https://target.local/anything",
        "document",
        "application/json",
    ) is True


def test_api_response_candidate_ignores_document_html():
    assert crawler._is_api_response_candidate(
        "https://target.local/banking/#/dashboard",
        "document",
        "text/html",
    ) is False


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
    assert crawler._url_has_object_ref("https://target.local/api/accounts/10000001") is True
    assert crawler._url_has_object_ref("https://target.local/api/accounts?id=10000001") is True
    assert crawler._url_has_object_ref("https://target.local/api/accounts") is False


def test_analyse_api_call_sends_no_screenshot_to_llm(monkeypatch):
    captured = {}

    async def fake_analyse_page(config, url, title, text, screenshot_b64=None):
        captured.update({
            "config": config,
            "url": url,
            "title": title,
            "text": text,
            "screenshot_b64": screenshot_b64,
        })
        return "Returns account data.", [], {
            "req_auth": None,
            "takes_input": False,
            "has_object_ref": False,
            "has_business_logic": True,
        }

    monkeypatch.setattr(crawler.llm_svc, "analyse_page", fake_analyse_page)

    title, context, categories = asyncio.run(crawler._analyse_api_call(
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
    ))

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

    _title, context, categories = asyncio.run(crawler._analyse_api_call(
        object(),
        {
            "method": "POST",
            "url": "https://target.local/api/payments",
            "status": 201,
            "content_type": "application/json",
            "body": '{}',
        },
        credential_id=None,
    ))

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
