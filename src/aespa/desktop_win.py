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

import webview

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


def _on_open() -> None:
    _window.show()
    authenticated = _window.evaluate_js(
        "document.documentElement.dataset.aespaAuthenticated"
    )
    if authenticated == "false":
        _window.load_url(_console_server.login_url())


def _on_console() -> None:
    _console_server.open()


def _in_background(action):
    # Tray events arrive on the WinForms UI thread, where pywebview calls such
    # as evaluate_js would deadlock waiting on that same thread.
    def handler(*_args) -> None:
        threading.Thread(target=action, daemon=True).start()

    return handler


def _create_tray() -> None:
    # Runs on the UI thread. pywebview's WinForms backend has already loaded
    # pythonnet and these assemblies.
    from System.Drawing import Bitmap, Icon
    from System.Windows.Forms import (
        ContextMenuStrip,
        MouseButtons,
        NotifyIcon,
        SystemInformation,
    )

    bitmap = Bitmap(
        Bitmap(str(DEFAULT_WEB_DIR / "icon.png")), SystemInformation.SmallIconSize
    )
    tray = NotifyIcon()
    tray.Icon = Icon.FromHandle(bitmap.GetHicon())
    tray.Text = "AESPA"

    def on_quit(*_args) -> None:
        # Dispose first so Windows doesn't leave a dead icon in the tray.
        tray.Visible = False
        tray.Dispose()
        threading.Thread(target=webview.destroy, daemon=True).start()

    def on_click(_sender, args) -> None:
        if args.Button == MouseButtons.Left:
            _in_background(_on_open)()

    menu = ContextMenuStrip()
    menu.Items.Add("Open AESPA").Click += _in_background(_on_open)
    menu.Items.Add("Open Console").Click += _in_background(_on_console)
    menu.Items.Add("Quit AESPA").Click += on_quit
    tray.ContextMenuStrip = menu
    tray.MouseClick += on_click
    tray.Visible = True


def _on_shown() -> None:
    from System import Action

    _window.native.Invoke(Action(_create_tray))


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
        _console_server.login_url(),
        width=1280,
        height=820,
        background_color="#0b0d12",
    )
    _window.events.closing += _on_closing
    _window.events.shown += _on_shown

    webview.start()


if __name__ == "__main__":
    main()
