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
from aespa.services.alice import run_alice_turn, run_alice_turn_stream
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
    instruction = "Perform blind SQL Injection on http://google.com/search?q=test"
    
    response = await run_alice_turn(run.id, instruction, [])
    
    assert response["status"] == "warning"
    assert "google.com" in response["message"]
    assert "outside the authorized scope" in response["message"]
    assert "Violation" in response["thought_process"]


@pytest.mark.anyio
async def test_run_alice_turn_executes_loop_for_in_scope_directive(db_session, test_data):
    """Verify that an in-scope instruction runs the stream and returns final reply."""
    run = test_data["run"]
    instruction = "Scan for XSS on http://target.local/api/comments"
    
    mock_thought = "Analyzing comments..."
    mock_reply = "No XSS found."
    
    async def mock_stream(*args, **kwargs):
        yield f"<thinking>{mock_thought}</thinking>"
        yield mock_reply

    with patch("aespa.services.llm.stream_chat_completion", side_effect=mock_stream):
        response = await run_alice_turn(run.id, instruction, [])
        
        assert response["status"] == "complete"
        assert response["message"] == mock_reply
        assert response["thought_process"] == mock_thought


@pytest.mark.anyio
async def test_run_alice_turn_stream_yields_correct_chunks(db_session, test_data):
    """Verify that run_alice_turn_stream yields properly parsed thinking and message chunks."""
    run = test_data["run"]
    instruction = "Check IDOR on http://target.local/users"
    
    async def mock_stream(*args, **kwargs):
        yield "<thinking>Evaluating sitemap</thinking>Let's check the users path."

    with patch("aespa.services.llm.stream_chat_completion", side_effect=mock_stream):
        chunks = []
        async for line in run_alice_turn_stream(run.id, instruction, []):
            if line.startswith("data: "):
                chunks.append(json.loads(line[6:].strip()))
                
        # Must have initial initialization thoughts, evaluation thoughts, and parsed content chunks
        assert len(chunks) >= 3
        
        # Verify tag parsing and state machine output
        thinking_chunks = [c for c in chunks if c.get("type") == "thinking_chunk"]
        message_chunks = [c for c in chunks if c.get("type") == "message_chunk"]
        done_chunks = [c for c in chunks if c.get("type") == "done"]
        
        assert any("Initializing" in c["delta"] for c in thinking_chunks)
        assert any("Evaluating sitemap" in c["delta"] for c in thinking_chunks)
        assert any("Let's check the users path." in c["delta"] for c in message_chunks)
        assert len(done_chunks) == 1
        assert done_chunks[0]["thought"] == "Evaluating sitemap"
        assert done_chunks[0]["message"] == "Let's check the users path."


def test_alice_chat_api_endpoint(test_client, test_data):
    """Verify that the POST /api/test-runs/{run_id}/alice/chat endpoint operates correctly."""
    run = test_data["run"]
    
    # Test 404 for non-existent run
    r_404 = test_client.post(
        "/api/test-runs/999999/alice/chat",
        json={"message": "hello"}
    )
    assert r_404.status_code == 404
    
    # Test valid request (which will hit run_alice_turn_stream)
    async def mock_stream(*args, **kwargs):
        yield "data: {\"type\": \"thinking_chunk\", \"delta\": \"thinking\"}\n\n"
        yield "data: {\"type\": \"done\", \"thought\": \"Thought\", \"message\": \"Reply\"}\n\n"
    
    with patch("aespa.services.alice.run_alice_turn_stream", side_effect=mock_stream) as mock_turn:
        r_api = test_client.post(
            f"/api/test-runs/{run.id}/alice/chat",
            json={"message": "Test message", "history": []}
        )
        
        assert r_api.status_code == 200
        assert r_api.headers["content-type"].startswith("text/event-stream")
        
        # Read streamed content lines
        lines = [line for line in r_api.iter_lines()]
        assert "data: {\"type\": \"thinking_chunk\", \"delta\": \"thinking\"}" in lines
        assert "data: {\"type\": \"done\", \"thought\": \"Thought\", \"message\": \"Reply\"}" in lines
        mock_turn.assert_called_once_with(run.id, "Test message", [])


@pytest.mark.anyio
async def test_execute_alice_tool_calls_with_tags(db_session, test_data):
    """Verify that multiple tool calls inside XML tags are successfully executed and persisted."""
    from aespa.services.alice import _execute_alice_tool_calls
    from aespa.models import ScanFinding
    from sqlmodel import select
    
    run = test_data["run"]
    llm_cfg = test_data["llm_cfg"]
    
    # Thought process containing two XML tool calls: an http_request and a write_finding
    thought = """
    Let me test access first.
    <tool_call>
    {"name": "http_request", "arguments": {"method": "GET", "url": "http://target.local/admin/"}}
    </tool_call>
    
    Now that we found default credentials, let's write a finding:
    <tool_call>
    {
        "name": "write_finding",
        "arguments": {
            "title": "Default Admin Access Enabled",
            "severity": "critical",
            "cvss_score": 9.5,
            "url": "http://target.local/admin/",
            "description": "Default credentials admin/admin123 work.",
            "evidence": "Successful login with admin/admin123",
            "recommendation": "Change the password immediately."
        }
    }
    </tool_call>
    """
    
    # Execute the parser
    await _execute_alice_tool_calls(
        run_id=run.id,
        llm_cfg=llm_cfg,
        base_url="http://target.local",
        thought=thought,
        message="Assessment complete."
    )
    
    # Check that the finding was successfully persisted in the database!
    findings = db_session.exec(select(ScanFinding).where(ScanFinding.test_run_id == run.id)).all()
    assert len(findings) == 1
    finding = findings[0]
    assert finding.title == "Default Admin Access Enabled"
    assert finding.severity == "critical"
    assert finding.affected_url == "http://target.local/admin/"
    assert "admin/admin123" in finding.description
    assert finding.finding_source == "alice"


