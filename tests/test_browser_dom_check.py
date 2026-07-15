from __future__ import annotations

import asyncio

from aespa.services.scanner import _run_thinking_browser_action


class _Locator:
    def __init__(self, *, count: int = 1, text: str = "", attributes=None):
        self._count = count
        self._text = text
        self._attributes = attributes or {}

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


class _Page:
    url = "https://target.local/dashboard"

    def __init__(self):
        self._locators = {
            "#result": _Locator(attributes={"data-aespa-xss": "canary-123"}),
            "body": _Locator(text="Dashboard"),
        }

    def locator(self, selector):
        return self._locators.get(selector, _Locator(count=0))

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
