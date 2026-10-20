from __future__ import annotations

import asyncio

from aespa.services.scanner import _run_thinking_browser_action


class _FormPage:
    """A fake page whose evaluate() mirrors the set_field op's DOM contract.

    It models one <form> with named controls so the test exercises the Python
    handler's argument wiring (name/form/value/create) and its set/created/
    not-found reporting, the same way the other browser-executor tests stand in
    for a real Playwright page.
    """

    url = "https://target.local/checkout"

    def __init__(self, fields: dict[str, str]):
        self.fields = dict(fields)
        self.created: list[str] = []

    def locator(self, _selector):  # pragma: no cover - unused by set_field
        raise AssertionError("set_field must not use locators")

    def on(self, *_args):
        return None

    def remove_listener(self, *_args):
        return None

    async def wait_for_load_state(self, *_args, **_kwargs):
        return None

    async def title(self):
        return "Checkout"

    async def content(self):
        return "<form></form>"

    async def inner_text(self, *_args, **_kwargs):  # pragma: no cover
        return ""

    async def screenshot(self, **_kwargs):
        return b"png"

    async def evaluate(self, _js, arg):
        name = arg.get("name")
        selector = arg.get("selector")
        key = name or selector
        if key not in self.fields:
            if not arg.get("create") or not name:
                return "not-found"
            self.fields[name] = ""
            self.created.append(name)
            outcome = "created"
        else:
            outcome = "set"
        self.fields[key] = arg.get("value") or ""
        return outcome


def _run(page, steps):
    return asyncio.run(
        _run_thinking_browser_action(page, {"steps": steps}, "https://target.local")
    )


def test_set_field_overwrites_a_hidden_control():
    page = _FormPage({"expectedTotal": "71900"})

    result = _run(
        page,
        [{"op": "set_field", "name": "expectedTotal", "form": "form", "value": "1"}],
    )

    assert page.fields["expectedTotal"] == "1"
    assert result["action_log"] == ["set_field [name=expectedTotal] in form=1 -> set"]


def test_set_field_creates_a_missing_field_when_requested():
    page = _FormPage({"expectedTotal": "71900"})

    result = _run(
        page,
        [{"op": "set_field", "name": "pm", "value": "42", "create": True}],
    )

    assert page.created == ["pm"]
    assert page.fields["pm"] == "42"
    assert result["action_log"] == ["set_field [name=pm]=42 -> created"]


def test_set_field_reports_missing_field_without_create():
    page = _FormPage({"expectedTotal": "71900"})

    result = _run(page, [{"op": "set_field", "name": "pm", "value": "42"}])

    assert "pm" not in page.fields
    assert result["action_log"] == ["set_field [name=pm]=42 -> not-found"]


def test_set_field_requires_a_name_or_selector():
    page = _FormPage({"expectedTotal": "71900"})

    result = _run(page, [{"op": "set_field", "value": "1"}])

    assert result["action_log"] == ["set_field skipped: requires selector or name"]
