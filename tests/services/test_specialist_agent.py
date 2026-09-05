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
            auto_dispatch_enabled=True,
            max_concurrent=5,
            max_queued=20,
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
            dispatch_file_upload=True,
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
    assert cfg.auto_dispatch_enabled is True
    assert cfg.max_concurrent == 5
    assert cfg.max_queued == 20
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
    assert data["auto_dispatch_enabled"] is True
    assert data["max_concurrent"] == 5
    assert data["max_queued"] == 20
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
        assert name in thinking_names, (
            f"specialist tool {name!r} not in THINKING_AGENT_TOOLS"
        )


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
    assert "priority" in required
    assert "file_upload" in props["attack_class"]["enum"]


def test_attack_class_aliases_are_normalized():
    from aespa.services.specialist_handoffs import normalize_attack_class

    assert normalize_attack_class("SQL Injection") == "sqli"
    assert normalize_attack_class("business-logic") == "business_logic"
    assert normalize_attack_class("file upload") == "file_upload"


def test_automatic_candidate_detects_ssrf_parameter():
    from aespa.services.specialist_handoffs import automatic_candidate

    candidate = automatic_candidate(
        {
            "method": "POST",
            "url": "https://target.test/hooks",
            "body": {"webhook": "https://example.com"},
        },
        response_status=202,
        response_headers={"content-type": "application/json"},
        response_body="accepted",
    )

    assert candidate is not None
    assert candidate["attack_class"] == "ssrf"
    assert candidate["parameter"] == "webhook"


def test_automatic_candidate_requires_database_error_for_sqli():
    from aespa.services.specialist_handoffs import automatic_candidate

    clean = automatic_candidate(
        {
            "method": "GET",
            "url": "https://target.test/search?q=test",
            "test_class": "sqli",
        },
        response_status=200,
        response_headers={},
        response_body="no results",
    )
    error = automatic_candidate(
        {
            "method": "GET",
            "url": "https://target.test/search?q=%27",
            "test_class": "sqli",
        },
        response_status=500,
        response_headers={},
        response_body="SQL syntax error near quote",
    )

    assert clean is None
    assert error is not None
    assert error["attack_class"] == "sqli"


def test_handoff_reserves_scope_and_delivers_completion(isolated_db_engine):
    from sqlmodel import Session

    from aespa.models import RunIdentity
    from aespa.services.specialist_handoffs import (
        consume_feedback,
        create_or_get_handoff,
        find_active_conflict,
        update_handoff,
    )

    with Session(isolated_db_engine) as session:
        identity = RunIdentity(kind="web")
        session.add(identity)
        session.commit()
        session.refresh(identity)
        run_id = identity.id

    handoff, created = create_or_get_handoff(
        run_id=run_id,
        run_kind="web",
        attack_class="SQL Injection",
        target_url="https://target.test/search?q=one",
        parameter="q",
        session_label=None,
        priority=8,
        rationale="Database error",
        dispatch_source="automatic",
        agent_id="specialist-sqli-1",
    )

    assert created is True
    assert (
        find_active_conflict(
            run_id,
            run_kind="web",
            attack_class="sqli",
            target_url="https://target.test/search?q=two",
            parameter="q",
        ).id
        == handoff.id
    )

    update_handoff(handoff.id, status="completed", outcome="No SQL injection found")
    assert consume_feedback(run_id, run_kind="web") == [
        "specialist-sqli-1 finished sqli on https://target.test/search?q=one: No SQL injection found."
    ]
    assert consume_feedback(run_id, run_kind="web") == []


def test_missing_priority_uses_configured_default_and_queues(isolated_db_engine):
    from sqlmodel import Session

    from aespa.models import RunIdentity
    from aespa.services.scanner import (
        _schedule_specialist_agent,
        _specialist_pending,
    )

    with Session(isolated_db_engine) as session:
        identity = RunIdentity(kind="web")
        session.add(identity)
        session.commit()
        session.refresh(identity)
        run_id = identity.id

    config = _SpecialistConfig(max_concurrent=1, min_priority=7)
    _specialist_running[run_id] = 1
    try:
        decision = _schedule_specialist_agent(
            run_id=run_id,
            dispatch={
                "attack_class": "SQL Injection",
                "target_url": "https://target.test/search?q=one",
                "rationale": "Database error",
            },
            session_vault={},
            llm_cfg=None,
            base_url="https://target.test",
            scanner_policy=None,
            specialist_config=config,
            site_id=1,
        )
        assert decision["status"] == "queued"
        assert len(_specialist_pending[run_id]) == 1
    finally:
        _specialist_running.pop(run_id, None)
        _specialist_pending.pop(run_id, None)
