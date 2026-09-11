from __future__ import annotations

import asyncio

from aespa.services.scanner import _run_thinking_browser_action


class _Locator:
    def __init__(
        self, *, count: int = 1, text: str = "", attributes=None, dom=None
    ):
        self._count = count
        self._text = text
        self._attributes = attributes or {}
        self._dom = dom or {
            "tag": "button",
            "targetReceivesPointer": True,
            "hitTarget": {"tag": "button", "text": text},
        }
        self.scrolled = False
        self.clicked = False

    @property
    def first(self):
        return self

    async def count(self):
        return self._count

    async def get_attribute(self, name, timeout=None):  # noqa: ARG002
        return self._attributes.get(name)

    async def text_content(self, timeout=None):  # noqa: ARG002
        return self._text

    async def inner_text(self, timeout=None):  # noqa: ARG002
        return self._text

    async def wait_for(self, **_kwargs):
        return None

    async def is_visible(self, **_kwargs):
        return self._count > 0

    async def is_enabled(self, **_kwargs):
        return True

    async def bounding_box(self, **_kwargs):
        return {"x": 10, "y": 20, "width": 100, "height": 30}

    async def evaluate(self, *_args, **_kwargs):
        return self._dom

    async def scroll_into_view_if_needed(self, **_kwargs):
        self.scrolled = True

    async def click(self, **_kwargs):
        self.clicked = True

    async def select_option(self, *, value, timeout=None):  # noqa: ARG002
        self.selected = value


class _Page:
    url = "https://target.local/dashboard"

    def __init__(self):
        class _Keyboard:
            def __init__(self):
                self.keys = []

            async def press(self, key):
                self.keys.append(key)

        self.keyboard = _Keyboard()
        self.cover_type = _Locator()
        self._locators = {
            "#result": _Locator(attributes={"data-aespa-xss": "canary-123"}),
            "body": _Locator(text="Dashboard"),
        }

    def locator(self, selector):
        return self._locators.get(selector, _Locator(count=0))

    def get_by_role(self, role, *, name, exact):  # noqa: ARG002
        if role == "combobox" and name == "Cover type":
            return self.cover_type
        return _Locator(count=0)

    def on(self, *_args):
        return None

    def remove_listener(self, *_args):
        return None

    async def wait_for_load_state(self, *_args, **_kwargs):
        return None

    async def title(self):
        return "Dashboard"

    async def content(self):
        return "<div id='result' data-aespa-xss='canary-123'></div>"

    async def screenshot(self, **_kwargs):
        return b"png"


def test_dom_check_reports_explicit_pass_without_javascript_execution():
    result = asyncio.run(
        _run_thinking_browser_action(
            _Page(),
            {
                "steps": [
                    {
                        "op": "dom_check",
                        "selector": "#result",
                        "attribute": "data-aespa-xss",
                        "equals": "canary-123",
                    }
                ]
            },
            "https://target.local",
        )
    )

    assert result["action_log"] == [
        "dom_check PASS #result @data-aespa-xss expected=canary-123 actual=canary-123"
    ]
    assert "dom_check PASS" in result["response_evidence"]


def test_dom_check_reports_missing_selector_as_failure():
    result = asyncio.run(
        _run_thinking_browser_action(
            _Page(),
            {
                "steps": [
                    {
                        "op": "dom_check",
                        "selector": "#missing",
                        "equals": "canary-123",
                    }
                ]
            },
            "https://target.local",
        )
    )

    assert result["action_log"][0].startswith("dom_check FAIL #missing")


def test_browser_replay_selects_option_by_accessible_role():
    page = _Page()

    result = asyncio.run(
        _run_thinking_browser_action(
            page,
            {
                "steps": [
                    {
                        "op": "select_option",
                        "role": "combobox",
                        "name": "Cover type",
                        "value": "comprehensive",
                    }
                ]
            },
            "https://target.local",
        )
    )

    assert page.cover_type.selected == "comprehensive"
    assert result["action_log"] == ["select_option combobox:Cover type"]


def test_inspect_element_reports_pointer_obstruction_without_mutating_dom():
    page = _Page()
    page._locators["#submit"] = _Locator(
        text="Submit",
        dom={
            "tag": "button",
            "targetReceivesPointer": False,
            "hitTarget": {
                "tag": "div",
                "id": "consent-backdrop",
                "classes": ["modal-backdrop"],
                "text": "Accept cookies",
            },
        },
    )

    result = asyncio.run(
        _run_thinking_browser_action(
            page,
            {"steps": [{"op": "inspect_element", "selector": "#submit"}]},
            "https://target.local",
        )
    )

    diagnostic = result["browser_diagnostics"][0]
    assert diagnostic["targetReceivesPointer"] is False
    assert diagnostic["hitTarget"]["id"] == "consent-backdrop"
    assert "blocked=True" in result["action_log"][0]
    assert page._locators["#submit"].clicked is False


def test_recover_click_scrolls_and_optionally_escapes_without_forcing():
    page = _Page()
    page._locators["#submit"] = _Locator(text="Submit")

    result = asyncio.run(
        _run_thinking_browser_action(
            page,
            {
                "steps": [
                    {
                        "op": "recover_click",
                        "selector": "#submit",
                        "press_escape": True,
                    }
                ]
            },
            "https://target.local",
        )
    )

    assert page._locators["#submit"].scrolled is True
    assert page._locators["#submit"].clicked is True
    assert page.keyboard.keys == ["Escape"]
    assert result["action_log"] == [
        "recover_click #submit: normal click succeeded after Escape"
    ]


class _Policy:
    def __init__(self, *, strict_locator_enforcement: bool):
        self.strict_locator_enforcement = strict_locator_enforcement
        self.request_timeout_s = 10.0


def test_missing_locator_is_a_hard_failure_by_default():
    result = asyncio.run(
        _run_thinking_browser_action(
            _Page(),
            {"steps": [{"op": "click", "value": "no locator hint given"}]},
            "https://target.local",
        )
    )

    assert result["action_log"] == [
        "click failed: missing locator (requires selector, testid, or role+name)"
    ]
    assert "failed:" in result["action_log"][0]


def test_missing_locator_is_a_hard_failure_for_fill_with_explicit_strict_policy():
    result = asyncio.run(
        _run_thinking_browser_action(
            _Page(),
            {"steps": [{"op": "fill", "value": "hello"}]},
            "https://target.local",
            scanner_policy=_Policy(strict_locator_enforcement=True),
        )
    )

    assert result["action_log"] == [
        "fill failed: missing locator (requires selector, testid, or role+name)"
    ]


def test_missing_locator_falls_back_to_skip_when_strict_mode_disabled():
    result = asyncio.run(
        _run_thinking_browser_action(
            _Page(),
            {"steps": [{"op": "click", "value": "no locator hint given"}]},
            "https://target.local",
            scanner_policy=_Policy(strict_locator_enforcement=False),
        )
    )

    assert result["action_log"] == ["click skipped: missing locator"]
