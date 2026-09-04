from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.db import set_engine
from aespa.models import ApiCollection, ApiTestRun, CodeExecutionConfig
from aespa.services import mentor


@pytest.fixture(name="db_engine")
def db_engine_fixture():
    from aespa.db import _engine as original_engine

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    set_engine(original_engine)


def _mentor_json() -> str:
    return json.dumps(
        {
            "diagnosis": "The lead repeated the profile probe without changing identity context.",
            "suggested_vectors": [
                {
                    "id": "transfer-idor",
                    "title": "Test transfer ownership",
                    "tool_names": ["http_request"],
                    "route_patterns": ["/api/transfers/{id}"],
                    "owasp_categories": ["API1"],
                    "test_classes": ["idor"],
                    "parameter_names": ["account_id"],
                },
                {
                    "id": "comment-xss",
                    "title": "Test comment rendering",
                    "route_patterns": ["/comments"],
                    "test_classes": ["stored_xss"],
                },
            ],
            "tactical_advice": "Use the second user session against a transfer owned by the first.",
        }
    )


def test_parse_mentor_response_validates_structured_vectors():
    advice = mentor.parse_mentor_response(_mentor_json())

    assert len(advice.suggested_vectors) == 2
    assert advice.suggested_vectors[0].id == "transfer-idor"
    assert advice.suggested_vectors[0].parameter_names == ["account_id"]
    assert "STRATEGY SHIFT CONTRACT" in advice.format_xml_block()


def test_incident_history_keeps_failure_evidence_but_redacts_credentials():
    history = mentor._recent_incident_history(
        [
            {
                "step": 9,
                "method": "BROWSER",
                "url": "https://target.local/checkout",
                "request_headers": {"Authorization": "Bearer top-secret"},
                "request_body": {
                    "steps": [{"op": "click", "selector": "#pay"}],
                    "password": "hunter2",
                },
                "response_body": "click failed: overlay intercepted pointer events",
            }
        ]
    )

    assert history[0]["request"]["headers"]["Authorization"] == "[redacted]"
    assert history[0]["request"]["body"]["password"] == "[redacted]"
    assert history[0]["request"]["body"]["steps"][0]["selector"] == "#pay"
    assert "overlay intercepted" in history[0]["result"]["body"]


def test_parser_rejects_vectors_that_require_an_unavailable_tool():
    payload = json.loads(_mentor_json())
    payload["suggested_vectors"][0]["tool_names"] = ["execute_python"]
    payload["failure_class"] = "tool_limit"
    payload["recovery_kind"] = "execute_python"

    advice = mentor.parse_mentor_response(
        json.dumps(payload), available_tools={"http_request"}
    )

    assert [vector.id for vector in advice.suggested_vectors] == ["comment-xss"]
    assert advice.recovery_kind == "pivot"


def test_malformed_response_does_not_create_an_unenforceable_contract():
    advice = mentor.parse_mentor_response("not json")
    assert advice.suggested_vectors == []
    assert "invalid structured response" in advice.diagnosis


def test_api_run_uses_run_scoped_resolver_and_real_completion(db_engine, monkeypatch):
    with Session(db_engine) as session:
        collection = ApiCollection(name="API", base_url="http://api.local")
        session.add(collection)
        session.commit()
        session.refresh(collection)
        run = ApiTestRun(collection_id=collection.id, name="run")
        session.add(run)
        session.add(
            CodeExecutionConfig(
                id=1,
                enabled=True,
                allowed_roles_json='["test_lead"]',
            )
        )
        session.commit()
        session.refresh(run)
        run_id = run.id

    resolved: list[tuple[object, str]] = []
    emitted: list[dict] = []

    def fake_resolver(_session, run, role):
        resolved.append((run, role))
        return SimpleNamespace(model="mentor-model")

    async def fake_completion(config, prompt, *, system_prompt=None):
        assert config.model == "mentor-model"
        assert system_prompt and "bounded tool-failure debugger" in system_prompt
        incident = json.loads(prompt)
        assert incident["target_url"] == "http://api.local"
        assert "execute_python" in incident["available_tools"]
        assert incident["python_sandbox"]["browser_or_dom_access"] is False
        return _mentor_json()

    monkeypatch.setattr(mentor, "get_llm_config_for_role", fake_resolver)
    monkeypatch.setattr(mentor.llm_svc, "plain_completion", fake_completion)
    monkeypatch.setattr(
        mentor.events_svc,
        "emit",
        lambda _run_id, event: emitted.append(event),
    )

    advice = asyncio.run(
        mentor.run_mentor_adviser(
            run_id=run_id,
            trigger_reason="stagnant",
            target_url="http://api.local",
            history_snippet=[],
            is_api_run=True,
        )
    )

    assert isinstance(resolved[0][0], ApiTestRun)
    assert resolved[0][1] == "mentor"
    assert advice.suggested_vectors[0].id == "transfer-idor"
    statuses = [event["status"] for event in emitted if event["type"] == "agent_status"]
    assert statuses == ["active", "complete"]
    assert all(event["_run_kind"] == "api" for event in emitted)
    guidance = [
        event
        for event in emitted
        if event.get("type") == "scanner_phase"
        and event.get("phase") == "mentor_guidance"
        and event.get("status") == "complete"
    ]
    assert len(guidance) == 1
    assert "Mentor Alternate Instructions" in guidance[0]["message"]
    assert "Test transfer ownership" in guidance[0]["message"]
    assert "Tactical next step" in guidance[0]["message"]
    assert guidance[0]["data"]["emitter"] == "Mentor Agent"
    assert guidance[0]["data"]["suggested_vectors"][0]["id"] == "transfer-idor"


def test_missing_model_still_emits_terminal_event(db_engine, monkeypatch):
    with Session(db_engine) as session:
        collection = ApiCollection(name="API", base_url="http://api.local")
        session.add(collection)
        session.commit()
        session.refresh(collection)
        run = ApiTestRun(collection_id=collection.id, name="run")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    emitted: list[dict] = []
    monkeypatch.setattr(mentor, "get_llm_config_for_role", lambda *_args: None)
    monkeypatch.setattr(
        mentor.events_svc,
        "emit",
        lambda _run_id, event: emitted.append(event),
    )

    asyncio.run(
        mentor.run_mentor_adviser(
            run_id, "stagnant", "http://api.local", [], is_api_run=True
        )
    )
    assert [
        event["status"] for event in emitted if event["type"] == "agent_status"
    ] == [
        "active",
        "warning",
    ]
