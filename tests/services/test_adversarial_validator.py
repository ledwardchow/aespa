"""Tests for Phase 3: adversarial validator config, API, and LLM tools."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from aespa.services import validator
from aespa.services.llm import (
    _ADVERSARIAL_VALIDATOR_SYSTEM,
    _DISPROOF_HINTS,
    VALIDATOR_AGENT_TOOLS,
    _disproof_hints_for_finding,
    severity_meets_threshold,
)

# ── Config defaults ────────────────────────────────────────────────────────────


def test_adversarial_validator_config_defaults(client: TestClient):
    resp = client.get("/api/settings/adversarial-validator-config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["max_steps"] == 20
    assert data["min_severity"] == "low"
    assert data["end_scan_max_concurrent"] == 4
    assert data["auto_validate_inline"] is True
    assert data["require_concrete_disproof"] is True
    assert "updated_at" in data


# ── API round-trip ─────────────────────────────────────────────────────────────


def test_adversarial_validator_config_update_round_trip(client: TestClient):
    payload = {
        "enabled": False,
        "max_steps": 10,
        "min_severity": "high",
        "end_scan_max_concurrent": 3,
        "auto_validate_inline": False,
        "require_concrete_disproof": False,
    }
    resp = client.put("/api/settings/adversarial-validator-config", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["max_steps"] == 10
    assert data["min_severity"] == "high"
    assert data["end_scan_max_concurrent"] == 3
    assert data["auto_validate_inline"] is False
    assert data["require_concrete_disproof"] is False

    stored = client.get("/api/settings/adversarial-validator-config").json()
    assert {key: stored[key] for key in payload} == payload

    replacement = {
        "enabled": True,
        "max_steps": 5,
        "min_severity": "medium",
        "end_scan_max_concurrent": 4,
        "auto_validate_inline": False,
        "require_concrete_disproof": True,
    }
    second = client.put("/api/settings/adversarial-validator-config", json=replacement)
    assert second.status_code == 200
    assert (
        client.get("/api/settings/adversarial-validator-config").json()["max_steps"]
        == 5
    )


# ── Validation ────────────────────────────────────────────────────────────────


def test_min_severity_rejects_invalid(client: TestClient):
    payload = {
        "enabled": True,
        "max_steps": 20,
        "min_severity": "extreme",
        "auto_validate_inline": True,
        "require_concrete_disproof": True,
    }
    resp = client.put("/api/settings/adversarial-validator-config", json=payload)
    assert resp.status_code == 422


def test_max_steps_rejects_zero(client: TestClient):
    payload = {
        "enabled": True,
        "max_steps": 0,
        "min_severity": "low",
        "auto_validate_inline": True,
        "require_concrete_disproof": True,
    }
    resp = client.put("/api/settings/adversarial-validator-config", json=payload)
    assert resp.status_code == 422


def test_max_steps_rejects_above_50(client: TestClient):
    payload = {
        "enabled": True,
        "max_steps": 51,
        "min_severity": "low",
        "auto_validate_inline": True,
        "require_concrete_disproof": True,
    }
    resp = client.put("/api/settings/adversarial-validator-config", json=payload)
    assert resp.status_code == 422


@pytest.mark.parametrize("value", [0, 9])
def test_end_scan_concurrency_rejects_out_of_range(client: TestClient, value: int):
    payload = {
        "enabled": True,
        "max_steps": 20,
        "min_severity": "low",
        "end_scan_max_concurrent": value,
        "auto_validate_inline": True,
        "require_concrete_disproof": True,
    }
    resp = client.put("/api/settings/adversarial-validator-config", json=payload)
    assert resp.status_code == 422


# ── LLM tool list ─────────────────────────────────────────────────────────────


def test_validator_agent_tools_contains_required_tools():
    names = {t["name"] for t in VALIDATOR_AGENT_TOOLS}
    assert "http_request" in names
    assert "compare_responses" in names
    assert "context_tool" in names
    assert "done" in names


def test_validator_agent_tools_excludes_scanner_tools():
    names = {t["name"] for t in VALIDATOR_AGENT_TOOLS}
    assert "agent_dispatch" not in names
    assert "write_finding" not in names
    assert "decode_jwt" not in names
    assert "register_account" not in names
    assert "credential_check" not in names


def test_validator_done_tool_schema():
    done_tool = next(t for t in VALIDATOR_AGENT_TOOLS if t["name"] == "done")
    schema = done_tool["input_schema"]
    props = schema["properties"]
    assert "verdict" in props
    assert "reasoning" in props
    assert "confidence" in props
    assert "verdict" in schema["required"]
    assert "reasoning" in schema["required"]
    # confidence is optional
    assert "confidence" not in schema["required"]


def test_validator_done_tool_verdict_enum():
    done_tool = next(t for t in VALIDATOR_AGENT_TOOLS if t["name"] == "done")
    verdict_enum = done_tool["input_schema"]["properties"]["verdict"]["enum"]
    assert "confirmed" in verdict_enum
    assert "false_positive" in verdict_enum
    assert "unconfirmed" in verdict_enum
    # must NOT contain old scanner done values
    assert "summary" not in done_tool["input_schema"]["properties"]


def test_compare_responses_tool_schema():
    ct = next(t for t in VALIDATOR_AGENT_TOOLS if t["name"] == "compare_responses")
    props = ct["input_schema"]["properties"]
    assert "baseline" in props
    assert "test" in props
    assert "baseline" in ct["input_schema"]["required"]
    assert "test" in ct["input_schema"]["required"]


def test_validator_http_tool_documents_anonymous_default():
    tool = next(t for t in VALIDATOR_AGENT_TOOLS if t["name"] == "http_request")
    description = tool["input_schema"]["properties"]["use_session"]["description"]
    assert "anonymous" in description
    assert "omit" in description.lower()


def test_validator_http_request_does_not_inherit_primary_session(monkeypatch):
    captured = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.default_headers = kwargs["headers"]
            self.default_cookies = kwargs["cookies"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def build_request(self, method, url, content=None, headers=None):
            merged = {**self.default_headers, **(headers or {})}
            return httpx.Request(method, url, content=content, headers=merged)

        async def send(self, request):
            captured.append((dict(request.headers), self.default_cookies))
            return httpx.Response(401, text="unauthorized", request=request)

    from aespa.services import traffic

    monkeypatch.setattr(traffic, "LoggingAsyncClient", FakeClient)
    primary = {
        "cookies": {"session": "primary-secret"},
        "extra_headers": {"Authorization": "Bearer primary-secret"},
    }
    policy = type("Policy", (), {"follow_redirects": True})()

    asyncio.run(
        validator._validator_http_request(
            {"method": "GET", "url": "https://target.local/private"},
            primary,
            {"primary": primary},
            policy,
            run_id=1,
        )
    )

    sent_headers, sent_cookies = captured[0]
    assert "authorization" not in sent_headers
    assert sent_cookies == {}


# ── Disproof hints ────────────────────────────────────────────────────────────


def test_disproof_hints_a01():
    hints = _disproof_hints_for_finding("A01")
    assert hints
    assert "access control" in hints.lower() or "idor" in hints.lower()


def test_disproof_hints_a03():
    hints = _disproof_hints_for_finding("A03")
    assert hints
    assert (
        "xss" in hints.lower()
        or "sqli" in hints.lower()
        or "injection" in hints.lower()
    )


def test_disproof_hints_with_year_suffix():
    # "A01:2021" should match the A01 entry
    hints = _disproof_hints_for_finding("A01:2021")
    assert hints


def test_disproof_hints_unknown_category_returns_empty():
    hints = _disproof_hints_for_finding("A99")
    assert hints == ""


def test_disproof_hints_empty_string():
    hints = _disproof_hints_for_finding("")
    assert hints == ""


def test_disproof_hints_none():
    hints = _disproof_hints_for_finding(None)
    assert hints == ""


def test_all_disproof_hint_keys_are_valid_owasp_prefixes():
    for key in _DISPROOF_HINTS:
        assert key.startswith("A"), f"Key {key!r} does not start with 'A'"
        assert len(key) == 3, f"Key {key!r} is not 3 characters"


# ── System prompt ─────────────────────────────────────────────────────────────


def test_adversarial_validator_system_prompt_contains_key_concepts():
    prompt = _ADVERSARIAL_VALIDATOR_SYSTEM.lower()
    assert "disprove" in prompt
    assert "false_positive" in prompt or "false positive" in prompt
    assert "confirmed" in prompt
    assert "done" in prompt


def test_validator_prompt_includes_linked_sast_attack_path(monkeypatch):
    captured = {}

    async def fake_loop(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        validator,
        "_static_attack_path_for_finding",
        lambda _: {
            "nodes": ["route", "service", "database"],
            "dynamic_test": "Try a foreign object id.",
        },
    )
    monkeypatch.setattr(validator.llm_svc, "thinking_agentic_loop", fake_loop)

    asyncio.run(
        validator._run_adversarial_validator_loop(
            run_id=1,
            finding=SimpleNamespace(
                id=9,
                title="BOLA",
                owasp_category="A01",
                severity="high",
                affected_url="https://target.test/orders/2",
                description="Object access is not restricted.",
                evidence="The response returned another user's order.",
            ),
            validator_cfg=SimpleNamespace(max_steps=2, require_concrete_disproof=False),
            llm_cfg=object(),
            cred_sessions={},
            scanner_policy=SimpleNamespace(),
        )
    )

    prompt = captured["initial_user_message"]
    assert "Static attack path from SAST" in prompt
    assert "route → service → database" in prompt
    assert "Try a foreign object id." in prompt
    assert "not runtime proof" in prompt


def test_validator_prompt_lists_sessions_without_secrets(monkeypatch):
    captured = {}

    async def fake_loop(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(validator, "_static_attack_path_for_finding", lambda _: {})
    monkeypatch.setattr(validator.llm_svc, "thinking_agentic_loop", fake_loop)

    asyncio.run(
        validator._run_adversarial_validator_loop(
            run_id=1,
            finding=SimpleNamespace(
                id=9,
                title="SQL injection",
                owasp_category="A03",
                severity="high",
                affected_url="https://target.test/admin/customers",
                description="The search parameter reaches a SQL query.",
                evidence="A quote produced SQLSTATE[42000].",
            ),
            validator_cfg=SimpleNamespace(max_steps=5, require_concrete_disproof=False),
            llm_cfg=object(),
            cred_sessions={
                1: {
                    "username": "admin",
                    "label": "Administrator",
                    "cookies": {"session": "cookie-secret"},
                    "extra_headers": {"Authorization": "Bearer token-secret"},
                }
            },
            scanner_policy=SimpleNamespace(),
        )
    )

    prompt = captured["initial_user_message"]
    assert "Available authenticated sessions" in prompt
    assert "`admin` (Administrator)" in prompt
    assert "`use_session`" in prompt
    assert "cookie-secret" not in prompt


def test_validator_done_payload_is_recorded_as_the_verdict(monkeypatch):
    loop_calls = 0

    async def fake_loop(**kwargs):
        nonlocal loop_calls
        loop_calls += 1
        accepted, feedback = kwargs["done_check"](
            {
                "verdict": "confirmed",
                "reasoning": "The disproof probes failed and the issue reproduced.",
                "confidence": "high",
            },
            3,
        )
        assert accepted is True
        assert feedback == ""

    monkeypatch.setattr(validator, "_static_attack_path_for_finding", lambda _: {})
    monkeypatch.setattr(validator.llm_svc, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(validator.events_svc, "emit", lambda *args, **kwargs: None)

    result = asyncio.run(
        validator._run_adversarial_validator_loop(
            run_id=1,
            finding=SimpleNamespace(
                id=9,
                title="BOLA",
                owasp_category="A01",
                severity="high",
                affected_url="https://target.test/orders/2",
                description="Object access is not restricted.",
                evidence="Another user's order was returned.",
            ),
            validator_cfg=SimpleNamespace(max_steps=5, require_concrete_disproof=False),
            llm_cfg=object(),
            cred_sessions={},
            scanner_policy=SimpleNamespace(),
        )
    )

    assert result[:3] == (
        "confirmed",
        "The disproof probes failed and the issue reproduced.",
        "high",
    )
    assert loop_calls == 1


def test_validator_reserves_verdict_turn_after_probe_budget(monkeypatch):
    calls = []
    request_calls = 0

    async def fake_http_request(*args, **kwargs):
        nonlocal request_calls
        request_calls += 1
        return {
            "status": 500,
            "body": "SQLSTATE[42000] PDO->query()",
            "headers": {},
        }

    async def fake_loop(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            await kwargs["tool_executor"](
                "http_request",
                {
                    "method": "GET",
                    "url": "https://target.test/admin/customers?search=normal",
                    "use_session": "admin",
                },
                1,
            )
            decisive = await kwargs["tool_executor"](
                "http_request",
                {
                    "method": "GET",
                    "url": "https://target.test/admin/customers?search=%27",
                    "use_session": "admin",
                },
                2,
            )
            await kwargs["on_checkpoint"](
                [
                    {"role": "user", "content": "finding"},
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "probe-2",
                                "name": "http_request",
                                "input": {},
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "probe-2",
                                "content": str(decisive),
                            }
                        ],
                    },
                ],
                2,
            )
            return

        assert [tool["name"] for tool in kwargs["tools"]] == ["done"]
        assert "SQLSTATE[42000]" in str(kwargs["resume_messages"])
        assert not any(
            left.get("role") == right.get("role") == "user"
            for left, right in zip(
                kwargs["resume_messages"], kwargs["resume_messages"][1:]
            )
        )
        rejected = await kwargs["tool_executor"](
            "http_request",
            {"method": "GET", "url": "https://target.test/extra-probe"},
            3,
        )
        assert "error" in rejected
        assert kwargs["stop_check"]() is False
        accepted, feedback = kwargs["done_check"](
            {
                "verdict": "confirmed",
                "reasoning": (
                    "The authenticated quote probe produced a payload-dependent "
                    "database syntax error from PDO->query()."
                ),
                "confidence": "high",
            },
            3,
        )
        assert accepted is True
        assert feedback == ""

    monkeypatch.setattr(validator, "_static_attack_path_for_finding", lambda _: {})
    monkeypatch.setattr(validator, "_validator_http_request", fake_http_request)
    monkeypatch.setattr(validator.llm_svc, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(validator.events_svc, "emit", lambda *args, **kwargs: None)

    result = asyncio.run(
        validator._run_adversarial_validator_loop(
            run_id=1,
            finding=SimpleNamespace(
                id=9,
                public_reference="TEST-001",
                reference="TEST-001",
                page_id=None,
                title="SQL injection",
                owasp_category="A03",
                severity="high",
                affected_url="https://target.test/admin/customers",
                description="The search parameter reaches a SQL query.",
                evidence="A quote produced SQLSTATE[42000].",
            ),
            validator_cfg=SimpleNamespace(max_steps=2, require_concrete_disproof=True),
            llm_cfg=object(),
            cred_sessions={
                1: {
                    "username": "admin",
                    "cookies": {},
                    "extra_headers": {"Authorization": "Bearer secret"},
                }
            },
            scanner_policy=SimpleNamespace(),
        )
    )

    assert len(calls) == 2
    assert request_calls == 2
    assert result[:3] == (
        "confirmed",
        (
            "The authenticated quote probe produced a payload-dependent "
            "database syntax error from PDO->query()."
        ),
        "high",
    )


def test_validator_final_turn_can_return_unconfirmed(monkeypatch):
    call_count = 0

    async def fake_loop(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await kwargs["tool_executor"]("context_tool", {"action": "get_finding"}, 1)
            await kwargs["on_checkpoint"](
                [{"role": "user", "content": "insufficient evidence"}],
                1,
            )
            return
        kwargs["done_check"](
            {
                "verdict": "unconfirmed",
                "reasoning": "The required authenticated session was unavailable.",
                "confidence": "low",
            },
            2,
        )

    monkeypatch.setattr(validator, "_static_attack_path_for_finding", lambda _: {})
    monkeypatch.setattr(validator.llm_svc, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(validator.events_svc, "emit", lambda *args, **kwargs: None)

    result = asyncio.run(
        validator._run_adversarial_validator_loop(
            run_id=1,
            finding=SimpleNamespace(
                id=9,
                title="SQL injection",
                owasp_category="A03",
                severity="high",
                affected_url="https://target.test/admin/customers",
                description="The search parameter may reach a SQL query.",
                evidence="The endpoint requires authentication.",
            ),
            validator_cfg=SimpleNamespace(max_steps=1, require_concrete_disproof=True),
            llm_cfg=object(),
            cred_sessions={},
            scanner_policy=SimpleNamespace(),
        )
    )

    assert result[:3] == (
        "unconfirmed",
        "The required authenticated session was unavailable.",
        "low",
    )


# ── Severity threshold ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "severity,threshold,expected",
    [
        ("critical", "low", True),
        ("high", "low", True),
        ("medium", "low", True),
        ("low", "low", True),
        ("info", "low", False),
        ("info", "info", True),
        ("low", "high", False),
        ("high", "high", True),
        ("critical", "critical", True),
        ("high", "critical", False),
    ],
)
def test_severity_meets_threshold(severity, threshold, expected):
    assert severity_meets_threshold(severity, threshold) == expected
