"""Windows desktop launcher.

Runs the AESPA server in a background thread and hosts it in a native window
(Edge WebView2 via pywebview), with a system-tray icon. Closing the window
hides it and leaves the server thread — and any scans in progress — running;
only "Quit" from the tray stops the process. This mirrors the macOS menubar
host in desktop.py.
"""

from __future__ import annotations

import sys
import threading
from importlib import import_module

import pystray
import webview
from PIL import Image

from aespa.browser import configure_browsers_path, download_chromium_if_missing
from aespa.config import DEFAULT_WEB_DIR
from aespa.desktop_console import (
    DesktopConsoleServer,
)
from aespa.desktop_console import (
    main as console_client_main,
)
from aespa.desktop_server import start_local_server

_window = None
_console_server = None


def _on_closing() -> bool:
    # Hide instead of close: server + scans keep running, reopen from the tray.
    _window.hide()
    return False


def _on_open(_icon, _item) -> None:
    _window.show()


def _on_quit(icon, _item) -> None:
    icon.stop()
    webview.destroy()


def _on_console(_icon, _item) -> None:
    _console_server.open()


def main() -> None:
    if "--desktop-console" in sys.argv:
        console_client_main()
        return
    if "--smoke-test" in sys.argv:
        import_module("webview.platforms.winforms")
        return

    configure_browsers_path()
    # First-run Chromium download runs in the background so the UI isn't blocked.
    threading.Thread(target=download_chromium_if_missing, daemon=True).start()

    try:
        port = start_local_server()
    except Exception as exc:
        print(f"[AESPA Startup Error] {exc}", file=sys.stderr)
        sys.exit(1)

    global _console_server, _window
    _console_server = DesktopConsoleServer(host="127.0.0.1", port=port)
    _window = webview.create_window(
        "AESPA",
        f"http://127.0.0.1:{port}/",
        width=1280,
        height=820,
        background_color="#0b0d12",
    )
    _window.events.closing += _on_closing

    icon = pystray.Icon(
        "aespa",
        Image.open(DEFAULT_WEB_DIR / "icon.png"),
        "AESPA",
        menu=pystray.Menu(
            pystray.MenuItem("Open AESPA", _on_open, default=True),
            pystray.MenuItem("Open Console", _on_console),
            pystray.MenuItem("Quit AESPA", _on_quit),
        ),
    )
    icon.run_detached()

    webview.start()


if __name__ == "__main__":
    main()
