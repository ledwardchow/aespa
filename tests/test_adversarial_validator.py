"""Tests for Phase 3: adversarial validator config, API, and LLM tools."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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


def test_upsert_adversarial_validator_config(client: TestClient):
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


def test_upsert_then_get_round_trip(client: TestClient):
    payload = {
        "enabled": True,
        "max_steps": 35,
        "min_severity": "critical",
        "end_scan_max_concurrent": 6,
        "auto_validate_inline": True,
        "require_concrete_disproof": True,
    }
    client.put("/api/settings/adversarial-validator-config", json=payload)
    resp = client.get("/api/settings/adversarial-validator-config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_steps"] == 35
    assert data["min_severity"] == "critical"
    assert data["end_scan_max_concurrent"] == 6


def test_upsert_is_idempotent(client: TestClient):
    payload = {
        "enabled": True,
        "max_steps": 5,
        "min_severity": "medium",
        "end_scan_max_concurrent": 4,
        "auto_validate_inline": False,
        "require_concrete_disproof": True,
    }
    r1 = client.put("/api/settings/adversarial-validator-config", json=payload)
    r2 = client.put("/api/settings/adversarial-validator-config", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["max_steps"] == 5


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
    # must NOT contain old scanner done values
    assert "summary" not in done_tool["input_schema"]["properties"]


def test_compare_responses_tool_schema():
    ct = next(t for t in VALIDATOR_AGENT_TOOLS if t["name"] == "compare_responses")
    props = ct["input_schema"]["properties"]
    assert "baseline" in props
    assert "test" in props
    assert "baseline" in ct["input_schema"]["required"]
    assert "test" in ct["input_schema"]["required"]


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
