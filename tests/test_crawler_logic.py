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
