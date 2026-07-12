from __future__ import annotations

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
