"""Tests for Phase 2: Specialist Agent Dispatch."""

# We import the private helpers directly from the scanner module.
# They live at module scope after the 'Specialist agent dispatch' section.
from aespa.services.scanner import (
    _next_specialist_agent_id,
    _should_dispatch_specialist,
    _specialist_at_capacity,
    _specialist_running,
    _specialist_seq,
)

# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class _SpecialistConfig:
    """Minimal stand-in for SpecialistAgentConfigOut."""
    def __init__(self, **kwargs):
        defaults = dict(
            enabled=True,
            max_concurrent=5,
            max_steps=30,
            min_priority=7,
            dispatch_idor=True,
            dispatch_auth_bypass=True,
            dispatch_sqli=True,
            dispatch_xss=True,
            dispatch_business_logic=True,
            dispatch_ssrf=True,
            dispatch_path_traversal=True,
            dispatch_cors=False,
            dispatch_crypto=True,
            dispatch_config=False,
        )
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)



# ---------------------------------------------------------------------------
# _should_dispatch_specialist
# ---------------------------------------------------------------------------

def test_should_dispatch_returns_false_when_disabled():
    cfg = _SpecialistConfig(enabled=False)
    assert _should_dispatch_specialist("idor", 10, cfg) is False


def test_should_dispatch_returns_false_when_class_disabled():
    cfg = _SpecialistConfig(dispatch_idor=False)
    assert _should_dispatch_specialist("idor", 10, cfg) is False


def test_should_dispatch_returns_false_for_cors_when_disabled_by_default():
    cfg = _SpecialistConfig()  # dispatch_cors defaults to False
    assert _should_dispatch_specialist("cors", 10, cfg) is False


def test_should_dispatch_returns_false_priority_too_low():
    cfg = _SpecialistConfig(min_priority=7)
    assert _should_dispatch_specialist("idor", 5, cfg) is False


def test_should_dispatch_returns_false_priority_equal_to_min():
    cfg = _SpecialistConfig(min_priority=7)
    # priority == min_priority should be allowed (>=)
    assert _should_dispatch_specialist("idor", 7, cfg) is True


def test_should_dispatch_returns_true_for_enabled_class():
    cfg = _SpecialistConfig()
    assert _should_dispatch_specialist("xss", 8, cfg) is True


def test_should_dispatch_returns_false_unknown_class():
    cfg = _SpecialistConfig()
    assert _should_dispatch_specialist("not_a_class", 10, cfg) is False


def test_should_dispatch_returns_false_when_max_concurrent_zero():
    cfg = _SpecialistConfig(max_concurrent=0)
    assert _should_dispatch_specialist("idor", 10, cfg) is False


def test_should_dispatch_returns_false_none_config():
    assert _should_dispatch_specialist("idor", 10, None) is False


# ---------------------------------------------------------------------------
# _specialist_at_capacity
# ---------------------------------------------------------------------------

def test_at_capacity_false_when_none_running(tmp_path):
    run_id = 99991
    _specialist_running.pop(run_id, None)
    cfg = _SpecialistConfig(max_concurrent=5)
    assert _specialist_at_capacity(run_id, cfg) is False


def test_at_capacity_true_when_at_limit():
    run_id = 99992
    cfg = _SpecialistConfig(max_concurrent=2)
    _specialist_running[run_id] = 2
    try:
        assert _specialist_at_capacity(run_id, cfg) is True
    finally:
        _specialist_running.pop(run_id, None)


def test_at_capacity_false_below_limit():
    run_id = 99993
    cfg = _SpecialistConfig(max_concurrent=5)
    _specialist_running[run_id] = 3
    try:
        assert _specialist_at_capacity(run_id, cfg) is False
    finally:
        _specialist_running.pop(run_id, None)


# ---------------------------------------------------------------------------
# _next_specialist_agent_id
# ---------------------------------------------------------------------------

def test_next_specialist_agent_id_increments():
    run_id = 99994
    _specialist_seq.pop(run_id, None)
    id1 = _next_specialist_agent_id(run_id, "idor")
    id2 = _next_specialist_agent_id(run_id, "xss")
    assert id1 == "specialist-idor-1"
    assert id2 == "specialist-xss-2"
    _specialist_seq.pop(run_id, None)


def test_next_specialist_agent_id_format():
    run_id = 99995
    _specialist_seq.pop(run_id, None)
    agent_id = _next_specialist_agent_id(run_id, "auth_bypass")
    assert agent_id == "specialist-auth_bypass-1"
    _specialist_seq.pop(run_id, None)


# ---------------------------------------------------------------------------
# SpecialistAgentConfig model defaults
# ---------------------------------------------------------------------------

def test_specialist_config_defaults():
    from aespa.models import SpecialistAgentConfig
    cfg = SpecialistAgentConfig()
    assert cfg.enabled is True
    assert cfg.max_concurrent == 5
    assert cfg.max_steps == 30
    assert cfg.min_priority == 7
    # Core classes default on
    assert cfg.dispatch_idor is True
    assert cfg.dispatch_sqli is True
    assert cfg.dispatch_xss is True
    # Low-signal classes default off
    assert cfg.dispatch_cors is False
    assert cfg.dispatch_config is False


# ---------------------------------------------------------------------------
# Settings API round-trip via TestClient
# ---------------------------------------------------------------------------

def test_specialist_config_api_get_returns_defaults(client):
    resp = client.get("/api/settings/specialist-agent-config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["max_concurrent"] == 5
    assert data["min_priority"] == 7
    assert "dispatch_idor" in data


def test_specialist_config_api_put_persists(client):
    payload = {
        "enabled": True,
        "max_concurrent": 3,
        "max_steps": 20,
        "min_priority": 8,
        "dispatch_idor": True,
        "dispatch_auth_bypass": False,
        "dispatch_sqli": True,
        "dispatch_xss": False,
        "dispatch_business_logic": True,
        "dispatch_ssrf": False,
        "dispatch_path_traversal": True,
        "dispatch_cors": False,
        "dispatch_crypto": False,
        "dispatch_config": False,
    }
    resp = client.put("/api/settings/specialist-agent-config", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_concurrent"] == 3
    assert data["min_priority"] == 8
    assert data["dispatch_auth_bypass"] is False
    assert data["dispatch_xss"] is False

    # Verify persisted — GET should return updated value
    resp2 = client.get("/api/settings/specialist-agent-config")
    assert resp2.json()["max_concurrent"] == 3


def test_specialist_config_api_put_validates_max_concurrent(client):
    payload = {"max_concurrent": 25}  # above max of 20
    resp = client.put("/api/settings/specialist-agent-config", json=payload)
    assert resp.status_code == 422


def test_specialist_config_api_put_validates_min_priority(client):
    payload = {"min_priority": 0}  # below min of 1
    resp = client.put("/api/settings/specialist-agent-config", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# SPECIALIST_AGENT_TOOLS list
# ---------------------------------------------------------------------------

def test_specialist_agent_tools_subset():
    from aespa.services.llm import SPECIALIST_AGENT_TOOLS, THINKING_AGENT_TOOLS
    specialist_names = {t["name"] for t in SPECIALIST_AGENT_TOOLS}
    # Must include core tools
    assert "http_request" in specialist_names
    assert "write_finding" in specialist_names
    assert "done" in specialist_names
    # Must NOT include orchestrator-only tools
    assert "agent_dispatch" not in specialist_names
    assert "forge_jwt" not in specialist_names
    assert "register_account" not in specialist_names
    # All specialist tools must exist in THINKING_AGENT_TOOLS
    thinking_names = {t["name"] for t in THINKING_AGENT_TOOLS}
    for name in specialist_names:
        assert name in thinking_names, f"specialist tool {name!r} not in THINKING_AGENT_TOOLS"


# ---------------------------------------------------------------------------
# agent_dispatch in THINKING_AGENT_TOOLS
# ---------------------------------------------------------------------------

def test_agent_dispatch_in_thinking_tools():
    from aespa.services.llm import THINKING_AGENT_TOOLS
    names = {t["name"] for t in THINKING_AGENT_TOOLS}
    assert "agent_dispatch" in names


def test_agent_dispatch_schema_has_required_properties():
    from aespa.services.llm import THINKING_AGENT_TOOLS
    tool = next(t for t in THINKING_AGENT_TOOLS if t["name"] == "agent_dispatch")
    props = tool["input_schema"].get("properties", {})
    required = tool["input_schema"].get("required", [])
    assert "attack_class" in props
    assert "target_url" in props
    assert "rationale" in props
    assert "attack_class" in required
    assert "target_url" in required
    assert "rationale" in required
