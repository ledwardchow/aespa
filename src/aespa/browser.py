"""First-run Chromium provisioning.

We don't bundle Chromium. Instead we point Playwright at a per-user
Application Support directory and download Chromium there on first run.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _bundled() -> bool:
    """True in a packaged (frozen) app, or when AESPA_BUNDLED=1 forces it."""
    return getattr(sys, "frozen", False) or os.environ.get("AESPA_BUNDLED") == "1"


def browsers_dir() -> Path:
    """Where Playwright should keep its browsers (per-user, persistent)."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "aespa"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "aespa"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "aespa"
    return base / "ms-playwright"


def configure_browsers_path() -> None:
    """Point Playwright at our per-user dir (packaged app only). Fast, no I/O.

    Plain `uv run aespa` is left untouched — devs keep using
    `uv run playwright install chromium` into Playwright's default cache.
    Respects a caller-set PLAYWRIGHT_BROWSERS_PATH. Must run before any
    `playwright` import that launches a browser.
    """
    if _bundled():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers_dir()))


def download_chromium_if_missing() -> None:
    """Download Chromium into the configured dir if it isn't there. Blocking.

    No-op outside a packaged app. Safe to run on a background thread.
    """
    if not _bundled():
        return

    target = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", browsers_dir()))
    if any(target.glob("chromium-*")):  # already installed
        return

    target.mkdir(parents=True, exist_ok=True)
    print(f"[aespa] First run: downloading Chromium into {target} ...", flush=True)
    if getattr(sys, "frozen", False):
        # Frozen: sys.executable can't run `-m`; invoke Playwright's node driver.
        from playwright._impl._driver import compute_driver_executable, get_driver_env

        exe = compute_driver_executable()
        driver = [exe] if isinstance(exe, str) else list(exe)
        subprocess.run([*driver, "install", "chromium"], check=True, env=get_driver_env())
    else:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], check=True
        )


def ensure_chromium() -> None:
    """Configure the browsers path and download Chromium if missing (blocking)."""
    configure_browsers_path()
    download_chromium_if_missing()
