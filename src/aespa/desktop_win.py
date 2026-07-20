"""Windows desktop launcher.

Runs the AESPA server in a background thread and hosts it in a native window
(Edge WebView2 via pywebview), with a system-tray icon. Closing the window
hides it and leaves the server thread — and any scans in progress — running;
only "Quit" from the tray stops the process. This mirrors the macOS menubar
host in desktop.py.
"""

from __future__ import annotations

import socket
import sys
import threading
import time

import pystray
import webview
from PIL import Image

from aespa.browser import configure_browsers_path, download_chromium_if_missing
from aespa.config import DEFAULT_WEB_DIR

_window = None


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve(port: int) -> None:
    import uvicorn

    uvicorn.Server(
        uvicorn.Config("aespa.main:app", host="127.0.0.1", port=port, log_level="info")
    ).run()


def _wait_port(port: int, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.25):
                return
        except OSError:
            time.sleep(0.1)


def _on_closing() -> bool:
    # Hide instead of close: server + scans keep running, reopen from the tray.
    _window.hide()
    return False


def _on_open(_icon, _item) -> None:
    _window.show()


def _on_quit(icon, _item) -> None:
    icon.stop()
    webview.destroy()


def main() -> None:
    if "--smoke-test" in sys.argv:
        import webview.platforms.winforms

        return

    configure_browsers_path()
    # First-run Chromium download runs in the background so the UI isn't blocked.
    threading.Thread(target=download_chromium_if_missing, daemon=True).start()

    port = _free_port()
    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    _wait_port(port)

    global _window
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
            pystray.MenuItem("Quit AESPA", _on_quit),
        ),
    )
    icon.run_detached()

    webview.start()


if __name__ == "__main__":
    main()
