"""Tests for A.L.I.C.E. chat coordinator and scope routing service."""
from __future__ import annotations

import json
from unittest.mock import patch, AsyncMock
from urllib.parse import urlparse

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient

from aespa.db import set_engine, get_engine
from aespa.models import Site, TestRun as RunModel, LLMConfig, CrawledPage, ScanFinding
from aespa.services.alice import run_alice_turn
from aespa.services import llm as llm_svc
from aespa.main import create_app
from aespa.db import get_session


@pytest.fixture(name="db_engine")
def db_engine_fixture():
    """Create an in-memory database engine for testing, and set it globally."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Save the original engine to restore it later
    from aespa.db import _engine as original_engine
    
    # Ensure all tables are created
    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    
    yield engine
    
    # Clean up and restore original engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    set_engine(original_engine)


@pytest.fixture(name="db_session")
def db_session_fixture(db_engine):
    """Provide a database Session for populating test data."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture(name="test_data")
def test_data_fixture(db_session):
    """Seed the database with necessary records: Site, TestRun, LLMConfig."""
    site = Site(
        name="Target App",
        base_url="http://target.local",
        scope_hosts=json.dumps(["target.local"]),
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    llm_cfg = LLMConfig(
        name="Default LLM Profile",
        is_active=True,
        provider="anthropic",
        model="claude-opus-4-5",
    )
    db_session.add(llm_cfg)
    db_session.commit()
    db_session.refresh(llm_cfg)

    run = RunModel(
        site_id=site.id,
        name="Pentest Run #1",
        status="running",
        llm_config_id=llm_cfg.id,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    return {
        "site": site,
        "run": run,
        "llm_cfg": llm_cfg,
    }


@pytest.fixture(name="test_client")
def test_client_fixture(db_engine):
    """FastAPI TestClient bound to the overridden test database session."""
    def _override_session():
        with Session(db_engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.mark.anyio
async def test_run_alice_turn_rejects_out_of_scope_directive(db_session, test_data):
    """Verify that an out-of-scope domain in the user's message is immediately blocked."""
    run = test_data["run"]
    
    # Instruction directing the agent to target google.com (out-of-scope) with http:// scheme
    instruction = "Perform blind SQL Injection on http://google.com/search?q=test"
    
    response = await run_alice_turn(run.id, instruction, [])
    
    assert response["status"] == "warning"
    assert "google.com" in response["message"]
    assert "outside the authorized scope" in response["message"]
    assert "Violation" in response["thought_process"]


@pytest.mark.anyio
async def test_run_alice_turn_executes_loop_for_in_scope_directive(db_session, test_data):
    """Verify that an in-scope instruction runs the agentic loop and returns final reply."""
    run = test_data["run"]
    instruction = "Scan for XSS on http://target.local/api/comments"
    
    mock_final_reply = "I have successfully tested target.local/api/comments and found no vulnerabilities."
    
    with patch("aespa.services.llm.thinking_agentic_loop", new_callable=AsyncMock) as mock_loop:
        mock_loop.return_value = mock_final_reply
        
        response = await run_alice_turn(run.id, instruction, [])
        
        mock_loop.assert_called_once()
        assert response["status"] == "complete"
        assert response["message"] == mock_final_reply
        assert "target.local" in response["thought_process"]


@pytest.mark.anyio
async def test_run_alice_turn_tool_executor_enforces_scope(db_session, test_data):
    """Verify that the tool executor inside ALICE's loop validates target URLs against scope."""
    run = test_data["run"]
    instruction = "Scan for IDORs on our profile endpoint"
    
    captured_executor = None
    
    async def mock_agentic_loop(config, *, system_message, initial_user_message, tool_executor, **kwargs):
        nonlocal captured_executor
        captured_executor = tool_executor
        return "Done"
        
    with patch("aespa.services.llm.thinking_agentic_loop", side_effect=mock_agentic_loop):
        await run_alice_turn(run.id, instruction, [])
        
    assert captured_executor is not None
    
    # Call tool executor with an in-scope URL
    in_scope_res_str = await captured_executor(
        tool_name="http_request",
        tool_input={"url": "http://target.local/api/profile", "note": "Get profile"},
        step=1
    )
    in_scope_res = json.loads(in_scope_res_str)
    assert in_scope_res["status"] == "success"
    
    # Call tool executor with an out-of-scope URL
    out_of_scope_res_str = await captured_executor(
        tool_name="http_request",
        tool_input={"url": "http://malicious.com/exploit", "note": "Send payload"},
        step=2
    )
    out_of_scope_res = json.loads(out_of_scope_res_str)
    assert "error" in out_of_scope_res
    assert "blocked" in out_of_scope_res["error"]
    assert out_of_scope_res["status"] == 403


def test_alice_chat_api_endpoint(test_client, test_data):
    """Verify that the POST /api/test-runs/{run_id}/alice/chat endpoint operates correctly."""
    run = test_data["run"]
    
    # Test 404 for non-existent run
    r_404 = test_client.post(
        "/api/test-runs/999999/alice/chat",
        json={"message": "hello"}
    )
    assert r_404.status_code == 404
    
    # Test valid request (which will hit run_alice_turn)
    # We patch run_alice_turn to return a mock response
    mock_res = {
        "thought_process": "Thought process",
        "message": "Hello tester!",
        "status": "complete"
    }
    
    with patch("aespa.services.alice.run_alice_turn", new_callable=AsyncMock) as mock_turn:
        mock_turn.return_value = mock_res
        
        r_api = test_client.post(
            f"/api/test-runs/{run.id}/alice/chat",
            json={"message": "Test message", "history": []}
        )
        
        assert r_api.status_code == 200
        assert r_api.json() == mock_res
        mock_turn.assert_called_once_with(run.id, "Test message", [])
