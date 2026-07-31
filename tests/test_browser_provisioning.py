from __future__ import annotations

import asyncio

from aespa import browser


def test_chromium_present_globs_the_browsers_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_BUNDLED", "1")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))

    assert browser.chromium_present() is False  # empty dir → not present
    (tmp_path / "chromium_headless_shell-1223").mkdir()
    assert browser.chromium_present() is True  # any chromium* build → present


def test_chromium_present_true_in_dev(monkeypatch):
    # Unbundled dev run manages its own browsers; never show the indicator.
    monkeypatch.delenv("AESPA_BUNDLED", raising=False)
    assert browser.chromium_present() is True


def test_launch_playwright_browser_defaults_to_playwright_chromium():
    class FakeChromium:
        def __init__(self):
            self.calls = []

        async def launch(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("channel") == "chrome":
                raise RuntimeError("Chrome is unavailable in this test")
            return kwargs

    class FakePlaywright:
        def __init__(self):
            self.chromium = FakeChromium()

    playwright = FakePlaywright()
    result = asyncio.run(
        browser.launch_playwright_browser(
            playwright, headless=True, args=["--proxy-bypass-list=<-loopback>"]
        )
    )

    assert result["channel"] == "chromium"
    assert playwright.chromium.calls == [{
        "channel": "chromium",
        "headless": True,
        "args": ["--proxy-bypass-list=<-loopback>"],
    }]


def test_launch_playwright_browser_can_select_system_chrome(monkeypatch):
    class FakeChromium:
        def __init__(self):
            self.calls = []

        async def launch(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("channel") == "chrome":
                raise RuntimeError("Chrome is unavailable in this test")
            return kwargs

    class FakePlaywright:
        def __init__(self):
            self.chromium = FakeChromium()

    playwright = FakePlaywright()
    monkeypatch.setattr(browser, "_capture_frontmost_application", lambda: None)
    result = asyncio.run(
        browser.launch_playwright_browser(
            playwright, browser_engine="system_chrome", headless=False
        )
    )

    assert result["channel"] == "chromium"
    assert [call["channel"] for call in playwright.chromium.calls] == [
        "chrome",
        "chromium",
    ]


def test_headed_launch_remembers_previous_app_for_focus_protection(monkeypatch):
    class FakeBrowser:
        pass

    class FakeChromium:
        async def launch(self, **kwargs):
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    previous_app = object()
    restored = []
    monkeypatch.setattr(
        browser, "_capture_frontmost_application", lambda: previous_app
    )
    monkeypatch.setattr(
        browser,
        "_restore_frontmost_application",
        lambda application: restored.append(application),
    )

    launched = asyncio.run(
        browser.launch_playwright_browser(
            FakePlaywright(), browser_engine="system_chrome", headless=False
        )
    )

    assert launched in browser._browser_focus_apps
    assert restored == [previous_app]


def test_playwright_user_agent_uses_browser_version_without_headless_token():
    class FakeBrowser:
        version = "150.0.7871.125"

    user_agent = browser.playwright_user_agent(FakeBrowser())

    assert "Chrome/150.0.0.0" in user_agent
    assert "HeadlessChrome" not in user_agent
