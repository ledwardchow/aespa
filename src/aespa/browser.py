"""First-run Chromium provisioning.

We don't bundle Chromium. Instead we point Playwright at a per-user
Application Support directory and download Chromium there on first run.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from weakref import WeakKeyDictionary

log = logging.getLogger("aespa.browser")

# Playwright's headed Chromium can activate its window when a page or context is
# created on macOS. Keep the app that was active before launch so callers can
# restore it after browser windows are created. A weak map avoids retaining
# closed browser objects for the lifetime of the server.
_browser_focus_apps: WeakKeyDictionary = WeakKeyDictionary()


def _bundled() -> bool:
    """True in a packaged (frozen) app, or when AESPA_BUNDLED=1 forces it."""
    return getattr(sys, "frozen", False) or os.environ.get("AESPA_BUNDLED") == "1"


def app_data_dir() -> Path:
    """Per-user, writable, persistent dir for the packaged app (db, uploads…)."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "aespa"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "aespa"
    else:
        xdg = os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
        base = Path(xdg) / "aespa"
    return base


def browsers_dir() -> Path:
    """Where Playwright should keep its browsers (per-user, persistent)."""
    return app_data_dir() / "ms-playwright"


def configure_browsers_path() -> None:
    """Point Playwright at our per-user dir (packaged app only). Fast, no I/O.

    Plain `uv run aespa` is left untouched — devs keep using
    `uv run playwright install chromium` into Playwright's default cache.
    Respects a caller-set PLAYWRIGHT_BROWSERS_PATH. Must run before any
    `playwright` import that launches a browser.
    """
    if _bundled():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers_dir()))


def chromium_present() -> bool:
    """Heuristic: is a Chromium build already downloaded? UI hint only.

    ponytail: a loose glob, deliberately NOT used to decide whether to run the
    installer — that stays authoritative in download_chromium_if_missing (which
    handles Playwright-upgrade revision bumps a glob would miss). Worst case here
    is a missing or needless 'downloading' indicator, never a broken download.
    """
    if not _bundled():
        return True
    target = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", browsers_dir()))
    return any(target.glob("chromium*"))


def playwright_chromium_present() -> bool:
    """Return whether Playwright can resolve an installed Chromium executable."""
    configure_browsers_path()
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executable = Path(playwright.chromium.executable_path)
    except Exception:
        return False
    return executable.is_file()


def download_chromium_if_missing() -> None:
    """Download Chromium into the configured dir if it isn't there. Blocking.

    Safe to run on a background thread. The resolved executable check handles
    Playwright upgrades where an older Chromium directory may still exist.
    """
    configure_browsers_path()
    if playwright_chromium_present():
        return

    if getattr(sys, "frozen", False):
        target = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", browsers_dir()))
        target.mkdir(parents=True, exist_ok=True)
        print(f"[aespa] First run: downloading Chromium into {target} ...", flush=True)
        # Frozen: sys.executable can't run `-m`; invoke Playwright's node driver.
        from playwright._impl._driver import compute_driver_executable, get_driver_env

        exe = compute_driver_executable()
        driver = [exe] if isinstance(exe, str) else list(exe)
        cmd = [*driver, "install", "chromium"]
        subprocess.run(cmd, check=True, env=get_driver_env())
    else:
        print(
            "[aespa] Playwright Chromium is missing; installing it now ...", flush=True
        )
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], check=True
        )


def ensure_chromium() -> None:
    """Configure the browsers path and download Chromium if missing (blocking)."""
    configure_browsers_path()
    download_chromium_if_missing()


def _capture_frontmost_application() -> object | None:
    """Return the macOS app that was active before a headed browser launch."""
    if sys.platform != "darwin":
        return None
    try:
        from AppKit import NSWorkspace

        return NSWorkspace.sharedWorkspace().frontmostApplication()
    except Exception as exc:  # pragma: no cover - depends on the host desktop
        log.debug("Could not capture the macOS frontmost app: %s", exc)
        return None


def _restore_frontmost_application(application: object | None) -> None:
    """Give focus back to the app that was active before AESPA opened Chrome."""
    if application is None:
        return
    try:
        from AppKit import NSApplicationActivateIgnoringOtherApps

        application.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    except Exception as exc:  # pragma: no cover - depends on the host desktop
        log.debug("Could not restore the macOS frontmost app: %s", exc)


def restore_playwright_focus(browser) -> None:
    """Restore the user's previous app after Playwright creates a browser page."""
    _restore_frontmost_application(_browser_focus_apps.get(browser))


def protect_playwright_context(browser, context) -> None:
    """Prevent headed macOS Playwright pages from repeatedly stealing focus.

    Playwright emits a ``page`` event when a context creates a page, including
    pages created by helpers such as authentication and mailbox readers. The
    callback is intentionally a no-op unless ``launch_playwright_browser``
    captured a macOS frontmost app for this browser.
    """
    if browser not in _browser_focus_apps:
        return
    on_page = getattr(context, "on", None)
    if on_page is None:
        return
    on_page("page", lambda _page: restore_playwright_focus(browser))


async def launch_playwright_browser(
    playwright,
    *,
    browser_engine: str = "playwright_chromium",
    headless: bool = True,
    args: list[str] | None = None,
    **kwargs,
):
    """Launch the browser selected in Debug settings.

    The normal mode uses Playwright's regular Chromium channel. The optional
    system Chrome mode uses the installed stable Chrome channel and falls back
    to Playwright Chromium if Chrome is unavailable. The no-channel launch is
    retained as a last-resort compatibility path for older Playwright installs.
    """
    launch_kwargs = {"headless": headless, "args": list(args or []), **kwargs}
    previous_app = _capture_frontmost_application() if not headless else None
    launched_browser = None

    try:
        if browser_engine == "system_chrome":
            try:
                launched_browser = await playwright.chromium.launch(
                    channel="chrome", **launch_kwargs
                )
            except Exception as chrome_error:
                log.warning(
                    "System Chrome is unavailable; falling back to Playwright Chromium: %s",
                    chrome_error,
                )

        if launched_browser is None:
            try:
                launched_browser = await playwright.chromium.launch(
                    channel="chromium", **launch_kwargs
                )
            except Exception as chromium_error:
                log.debug("Playwright Chromium channel unavailable: %s", chromium_error)

        if launched_browser is None:
            # Last-resort compatibility path for installations that only contain
            # the legacy headless shell. The usual install path reaches the
            # regular Chromium channel above.
            launched_browser = await playwright.chromium.launch(**launch_kwargs)

        if previous_app is not None:
            _browser_focus_apps[launched_browser] = previous_app
            restore_playwright_focus(launched_browser)
        return launched_browser
    except Exception:
        # Do not retain a frontmost-app reference if every launch attempt failed.
        if launched_browser is not None:
            _browser_focus_apps.pop(launched_browser, None)
        raise


def playwright_user_agent(browser) -> str:
    """Return a current Chrome-shaped UA for the browser that was launched.

    Chromium's legacy headless shell advertises ``HeadlessChrome`` in its UA,
    even when the browser version and engine are otherwise current. The
    context override below changes only that product token and derives the
    version from the live browser, avoiding a stale hard-coded Chrome version.
    Browser automation signals such as ``navigator.webdriver`` are unchanged.
    """
    version = str(getattr(browser, "version", "") or "0.0.0").split(".", 1)[0]
    if not version.isdigit():
        version = "0"
    if sys.platform == "darwin":
        platform = "Macintosh; Intel Mac OS X 10_15_7"
    elif sys.platform == "win32":
        platform = "Windows NT 10.0; Win64; x64"
    else:
        platform = "X11; Linux x86_64"
    return (
        f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36"
    )
