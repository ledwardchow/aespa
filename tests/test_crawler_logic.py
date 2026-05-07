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
