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
    NSModalResponseOK,
    NSOpenPanel,
    NSSavePanel,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSURL, NSMakeRect, NSMakeSize, NSObject, NSURLRequest
from WebKit import WKWebView, WKWebViewConfiguration

# Policy enums (cancel=0, allow=1, download=2). Import where available, else fall
# back to the literals so older pyobjc builds still work.
try:
    from WebKit import (
        WKNavigationActionPolicyAllow,
        WKNavigationActionPolicyDownload,
        WKNavigationResponsePolicyAllow,
        WKNavigationResponsePolicyDownload,
    )
except ImportError:  # pragma: no cover
    WKNavigationActionPolicyAllow = 1
    WKNavigationActionPolicyDownload = 2
    WKNavigationResponsePolicyAllow = 1
    WKNavigationResponsePolicyDownload = 2

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


def _menubar_icon() -> NSImage:
    """The AESPA logo as a monochrome menubar template.

    icon-menubar.png is a high-res alpha trace of the logo artwork. A template
    image is drawn by its alpha only — macOS recolors it to match the menubar,
    so it looks like a native icon in light and dark mode.
    """
    img = NSImage.alloc().initWithContentsOfFile_(
        str(DEFAULT_WEB_DIR / "icon-menubar.png")
    )
    img.setSize_(NSMakeSize(18, 18))
    img.setTemplate_(True)
    return img


class Controller(NSObject):
    def initWithURL_(self, url):
        self = objc.super(Controller, self).init()
        self._url = url
        self._window = None
        return self

    def applicationDidFinishLaunching_(self, _notification):
        bar = NSStatusBar.systemStatusBar()
        self._status = bar.statusItemWithLength_(NSVariableStatusItemLength)
        self._status.button().setImage_(_menubar_icon())

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
            web.setUIDelegate_(self)  # file-open panel (import/upload)
            web.setNavigationDelegate_(self)  # downloads (export)
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

    # --- File import (WKUIDelegate) ---------------------------------------
    def webView_runOpenPanelWithParameters_initiatedByFrame_completionHandler_(
        self, _webView, parameters, _frame, completionHandler
    ):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(parameters.allowsMultipleSelection())
        if panel.runModal() == NSModalResponseOK:
            completionHandler(panel.URLs())
        else:
            completionHandler(None)

    # --- File export (WKNavigationDelegate -> WKDownload) -----------------
    def webView_decidePolicyForNavigationAction_decisionHandler_(
        self, _webView, navigationAction, decisionHandler
    ):
        # <a download> sets shouldPerformDownload on the action.
        if navigationAction.respondsToSelector_("shouldPerformDownload") and (
            navigationAction.shouldPerformDownload()
        ):
            decisionHandler(WKNavigationActionPolicyDownload)
        else:
            decisionHandler(WKNavigationActionPolicyAllow)

    def webView_decidePolicyForNavigationResponse_decisionHandler_(
        self, _webView, navigationResponse, decisionHandler
    ):
        # Endpoints that return Content-Disposition: attachment, or any MIME the
        # web view can't display, become downloads.
        disposition = ""
        resp = navigationResponse.response()
        if resp.respondsToSelector_("allHeaderFields"):
            headers = resp.allHeaderFields()
            disposition = (
                headers.get("Content-Disposition")
                or headers.get("content-disposition")
                or ""
            )
        if (
            not navigationResponse.canShowMIMEType()
            or "attachment" in disposition.lower()
        ):
            decisionHandler(WKNavigationResponsePolicyDownload)
        else:
            decisionHandler(WKNavigationResponsePolicyAllow)

    def webView_navigationAction_didBecomeDownload_(self, _webView, _action, download):
        download.setDelegate_(self)

    def webView_navigationResponse_didBecomeDownload_(
        self, _webView, _response, download
    ):
        download.setDelegate_(self)

    # --- WKDownloadDelegate -----------------------------------------------
    def download_decideDestinationUsingResponse_suggestedFilename_completionHandler_(
        self, _download, _response, suggestedFilename, completionHandler
    ):
        panel = NSSavePanel.savePanel()
        panel.setNameFieldStringValue_(suggestedFilename or "download")
        if panel.runModal() == NSModalResponseOK:
            completionHandler(panel.URL())
        else:
            completionHandler(None)

    def download_didFailWithError_resumeData_(self, _download, _error, _resumeData):
        pass

    def downloadDidFinish_(self, _download):
        pass

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
