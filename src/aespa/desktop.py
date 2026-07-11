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
    NSAlert,
    NSAlertFirstButtonReturn,
    NSAppearance,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSColor,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSModalResponseOK,
    NSOpenPanel,
    NSSavePanel,
    NSStatusBar,
    NSTerminateCancel,
    NSTerminateNow,
    NSTextField,
    NSVariableStatusItemLength,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
    NSWorkspace,
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

from aespa.browser import (
    chromium_present,
    configure_browsers_path,
    download_chromium_if_missing,
)
from aespa.config import DEFAULT_WEB_DIR, _pkg_version

_LATEST_RELEASE_API = "https://api.github.com/repos/ledwardchow/aespa/releases/latest"

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


def _check_for_update() -> str | None:
    """Return the release page URL if GitHub has a newer stable release, else None.

    Best-effort: any failure (offline, rate-limited, unparseable tag) returns None
    so it never blocks or crashes launch. Uses GitHub's /releases/latest, which
    skips prereleases — we only nudge users toward stable builds.
    """
    import json
    import urllib.request

    def _tuple(v: str) -> tuple[int, ...]:
        # Tags/versions are MAJOR.MINOR.YYYYMMDD.REVISION — all numeric.
        return tuple(int(p) for p in v.lstrip("v").split("."))

    try:
        req = urllib.request.Request(
            _LATEST_RELEASE_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AESPA"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
        if _tuple(data["tag_name"]) > _tuple(_pkg_version):
            return data.get("html_url")
    except Exception:
        pass  # ponytail: silent — an update nudge isn't worth a launch failure.
    return None


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


def _install_edit_menu() -> None:
    """Wire ⌘X/⌘C/⌘V/⌘A into the web view.

    WKWebView copy/paste works through the responder chain, which is only
    reachable if a main menu exposes the cut:/copy:/paste:/selectAll: actions.
    A menubar-only app has no main menu by default, so without this the
    keyboard shortcuts are dead. Items have nil targets on purpose — that's
    what makes them route to the first responder (the web view).
    """
    main = NSMenu.alloc().init()

    app_item = NSMenuItem.alloc().init()
    main.addItem_(app_item)
    app_menu = NSMenu.alloc().init()
    app_menu.addItem_(
        NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit AESPA", "terminate:", "q"
        )
    )
    app_item.setSubmenu_(app_menu)

    edit_item = NSMenuItem.alloc().init()
    main.addItem_(edit_item)
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    for title, action, key in (
        ("Undo", "undo:", "z"),
        ("Redo", "redo:", "Z"),
        (None, None, None),
        ("Cut", "cut:", "x"),
        ("Copy", "copy:", "c"),
        ("Paste", "paste:", "v"),
        ("Select All", "selectAll:", "a"),
    ):
        if title is None:
            edit_menu.addItem_(NSMenuItem.separatorItem())
        else:
            edit_menu.addItem_(
                NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    title, action, key
                )
            )
    edit_item.setSubmenu_(edit_menu)

    NSApplication.sharedApplication().setMainMenu_(main)


class Controller(NSObject):
    def initWithURL_(self, url):
        self = objc.super(Controller, self).init()
        self._url = url
        self._window = None
        self._quitting = False
        self._dl_item = None
        self._dl_sep = None
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
        self._menu = menu

        _install_edit_menu()
        self.showWindow_(None)

        # First-run Chromium download can take minutes with no visible sign.
        # Show a disabled "Downloading browser…" item while it runs so the user
        # knows something's happening; the thread always runs (the installer is
        # the authoritative idempotent check), only the indicator is gated.
        if not chromium_present():
            self._dl_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Downloading browser… (first run)", None, ""
            )
            self._dl_sep = NSMenuItem.separatorItem()
            self._menu.insertItem_atIndex_(self._dl_item, 0)
            self._menu.insertItem_atIndex_(self._dl_sep, 1)
        threading.Thread(target=self._downloadBrowser, daemon=True).start()

        # Best-effort GitHub release check off the main thread; on a hit it
        # inserts an "Update available" item at the top of the menubar menu.
        threading.Thread(target=self._checkUpdate, daemon=True).start()

    def _downloadBrowser(self):
        download_chromium_if_missing()
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "browserReady:", None, False
        )

    def browserReady_(self, _):
        if self._dl_item is not None:
            self._menu.removeItem_(self._dl_item)
            self._menu.removeItem_(self._dl_sep)
            self._dl_item = None
            self._dl_sep = None

    def _checkUpdate(self):
        url = _check_for_update()
        if url:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "addUpdateItem:", url, False
            )

    def addUpdateItem_(self, url):
        self._update_url = url
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Update Available — Download…", "openUpdate:", ""
        )
        item.setTarget_(self)
        self._menu.insertItem_atIndex_(item, 0)
        self._menu.insertItem_atIndex_(NSMenuItem.separatorItem(), 1)

    def openUpdate_(self, _sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(self._update_url))

    def _ensureWindow(self):
        if self._window is None:
            rect = NSMakeRect(0, 0, 1280, 820)
            win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, _WINDOW_STYLE, NSBackingStoreBuffered, False
            )
            win.setTitle_("AESPA")
            win.setReleasedWhenClosed_(False)
            win.setDelegate_(self)
            # Match the site theme (manifest theme_color #0b0d12): dark chrome,
            # title bar tinted to the page background so it blends in.
            win.setBackgroundColor_(
                NSColor.colorWithSRGBRed_green_blue_alpha_(
                    11 / 255, 13 / 255, 18 / 255, 1.0
                )
            )
            win.setTitlebarAppearsTransparent_(True)
            win.setAppearance_(
                NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua")
            )
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

    def _presentWindow(self):
        self._ensureWindow()
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        app.unhide_(None)
        app.activateIgnoringOtherApps_(True)
        if self._window.isMiniaturized():
            self._window.deminiaturize_(None)
        self._window.makeKeyAndOrderFront_(None)
        self._window.orderFrontRegardless()

    def showWindow_(self, _sender):
        self._presentWindow()

    def windowShouldClose_(self, sender):
        # Hide instead of close: server + scans keep running. Drop the dock
        # icon so only the menubar host remains.
        sender.orderOut_(None)
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )
        return False

    def applicationShouldHandleReopen_hasVisibleWindows_(
        self, _sender, _hasVisibleWindows
    ):
        # Dock clicks on a running app arrive here. The window may have been
        # hidden into menubar mode, so route reopen through the normal presenter.
        self._presentWindow()
        return True

    def applicationDidBecomeActive_(self, _notification):
        # Some macOS paths (notably Dock activation after the app was hidden or
        # the window was miniaturized) activate the app without sending the
        # narrower reopen callback. If the Dock icon is present, make sure the
        # UI comes back with the activation.
        if (
            self._window is not None
            and NSApplication.sharedApplication().activationPolicy()
            == NSApplicationActivationPolicyRegular
            and (not self._window.isVisible() or self._window.isMiniaturized())
        ):
            self._presentWindow()

    # --- JS dialogs (WKUIDelegate): alert / confirm / prompt --------------
    def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
        self, _webView, message, _frame, completionHandler
    ):
        alert = NSAlert.alloc().init()
        alert.setMessageText_("AESPA")
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        alert.runModal()
        completionHandler()

    def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(  # noqa: E501
        self, _webView, message, _frame, completionHandler
    ):
        alert = NSAlert.alloc().init()
        alert.setMessageText_("AESPA")
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        alert.addButtonWithTitle_("Cancel")
        completionHandler(alert.runModal() == NSAlertFirstButtonReturn)

    def webView_runJavaScriptTextInputPanelWithPrompt_defaultText_initiatedByFrame_completionHandler_(  # noqa: E501
        self, _webView, prompt, defaultText, _frame, completionHandler
    ):
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 280, 24))
        field.setStringValue_(defaultText or "")
        alert = NSAlert.alloc().init()
        alert.setMessageText_("AESPA")
        alert.setInformativeText_(prompt)
        alert.addButtonWithTitle_("OK")
        alert.addButtonWithTitle_("Cancel")
        alert.setAccessoryView_(field)
        if alert.runModal() == NSAlertFirstButtonReturn:
            completionHandler(field.stringValue())
        else:
            completionHandler(None)

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

    def applicationShouldTerminate_(self, _sender):
        # ⌘Q / app-menu Quit hides the window and keeps the server + scans
        # running; only the menubar "Quit AESPA" (which sets _quitting) really
        # exits. Mirrors windowShouldClose_.
        if self._quitting:
            return NSTerminateNow
        if self._window is not None:
            self._window.orderOut_(None)
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )
        return NSTerminateCancel

    def quit_(self, _sender):
        self._quitting = True
        NSApplication.sharedApplication().terminate_(None)


def main() -> None:
    configure_browsers_path()
    # The Controller kicks off the first-run Chromium download once its menubar
    # is up, so the "Downloading browser…" indicator can reflect it.
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
