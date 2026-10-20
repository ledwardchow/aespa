from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from aespa.config import Settings
from aespa.desktop_console import DesktopConsoleServer
from aespa.local_auth import get_auth


def test_desktop_login_link_uses_the_actual_port_and_fresh_tickets(tmp_path):
    settings = Settings(data_dir=tmp_path, port=8123)
    auth = get_auth(settings)
    console = DesktopConsoleServer.__new__(DesktopConsoleServer)
    console.host = "127.0.0.1"
    console.port = 8123
    console.auth = auth
    first, second = console.login_url(), console.login_url()
    assert first != second
    for url in (first, second):
        parsed = urlsplit(url)
        assert parsed.netloc == "127.0.0.1:8123"
        ticket = parse_qs(parsed.fragment)["aespa-login"][0]
        assert auth.consume_ticket(ticket)
        assert not auth.consume_ticket(ticket)


@pytest.mark.parametrize("authenticated", ["true", "false", None])
def test_windows_reopen_preserves_signed_in_page_and_recovers_sign_in(
    monkeypatch, authenticated
):
    monkeypatch.setitem(sys.modules, "pystray", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "PIL", SimpleNamespace(Image=SimpleNamespace()))
    monkeypatch.delitem(sys.modules, "aespa.desktop_win", raising=False)
    desktop = importlib.import_module("aespa.desktop_win")
    opened = []
    desktop._window = SimpleNamespace(
        show=lambda: opened.append("show"),
        evaluate_js=lambda script: authenticated,
        load_url=lambda url: opened.append(url),
    )
    desktop._console_server = SimpleNamespace(
        login_url=lambda: "http://127.0.0.1:8123/#aespa-login=fresh"
    )
    desktop._on_open(None, None)
    assert opened == (
        ["show", "http://127.0.0.1:8123/#aespa-login=fresh"]
        if authenticated == "false"
        else ["show"]
    )
    monkeypatch.delitem(sys.modules, "aespa.desktop_win")
