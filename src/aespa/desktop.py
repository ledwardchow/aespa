"""macOS desktop launcher.

Runs the AESPA server in a background thread and hosts it from a menubar
(NSStatusItem) icon. A WKWebView window is the optional UI: closing it hides
the window and drops the dock icon, but the server thread — and any scans in
progress — keep running. Only "Quit" from the menubar stops the process.
"""

from __future__ import annotations

import socket
import threading
import time

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSURL, NSURLRequest, NSMakeRect, NSObject
from WebKit import WKWebView, WKWebViewConfiguration

from aespa.browser import configure_browsers_path, download_chromium_if_missing
from aespa.config import DEFAULT_WEB_DIR

_WINDOW_STYLE = (
    NSWindowStyleMaskTitled
    | NSWindowStyleMaskClosable
    | NSWindowStyleMaskResizable
    | NSWindowStyleMaskMiniaturizable
)
_VIEW_SIZABLE = 2 | 16  # NSViewWidthSizable | NSViewHeightSizable


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


class Controller(NSObject):
    def initWithURL_(self, url):
        self = objc.super(Controller, self).init()
        self._url = url
        self._window = None
        return self

    def applicationDidFinishLaunching_(self, _notification):
        bar = NSStatusBar.systemStatusBar()
        self._status = bar.statusItemWithLength_(NSVariableStatusItemLength)
        icon = NSImage.alloc().initWithContentsOfFile_(str(DEFAULT_WEB_DIR / "icon-sm.png"))
        if icon is not None:
            icon.setSize_((18, 18))
            self._status.button().setImage_(icon)
        else:
            self._status.button().setTitle_("A")

        menu = NSMenu.alloc().init()
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open AESPA", "showWindow:", ""
        )
        open_item.setTarget_(self)
        menu.addItem_(open_item)
        menu.addItem_(NSMenuItem.separatorItem())
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit AESPA", "quit:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)
        self._status.setMenu_(menu)

        self.showWindow_(None)

    def showWindow_(self, _sender):
        if self._window is None:
            rect = NSMakeRect(0, 0, 1280, 820)
            win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, _WINDOW_STYLE, NSBackingStoreBuffered, False
            )
            win.setTitle_("AESPA")
            win.setReleasedWhenClosed_(False)
            win.setDelegate_(self)
            web = WKWebView.alloc().initWithFrame_configuration_(
                rect, WKWebViewConfiguration.alloc().init()
            )
            web.setAutoresizingMask_(_VIEW_SIZABLE)
            win.contentView().addSubview_(web)
            web.loadRequest_(NSURLRequest.requestWithURL_(self._url))
            win.center()
            self._window = win

        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        app.activateIgnoringOtherApps_(True)
        self._window.makeKeyAndOrderFront_(None)

    def windowShouldClose_(self, sender):
        # Hide instead of close: server + scans keep running. Drop the dock
        # icon so only the menubar host remains.
        sender.orderOut_(None)
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )
        return False

    def applicationShouldTerminateAfterLastWindowClosed_(self, _sender):
        return False

    def quit_(self, _sender):
        NSApplication.sharedApplication().terminate_(None)


def main() -> None:
    configure_browsers_path()
    # First-run Chromium download runs in the background so the UI isn't blocked.
    # ponytail: a scan started before this finishes will fail until it lands;
    # upgrade path is surfacing download progress in the UI.
    threading.Thread(target=download_chromium_if_missing, daemon=True).start()

    port = _free_port()
    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    _wait_port(port)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    url = NSURL.URLWithString_(f"http://127.0.0.1:{port}/")
    controller = Controller.alloc().initWithURL_(url)
    app.setDelegate_(controller)
    app.run()


if __name__ == "__main__":
    main()
