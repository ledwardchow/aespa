"""Tests for A.L.I.C.E. chat coordinator and scope routing service."""
from __future__ import annotations

import json
from unittest.mock import patch, AsyncMock, MagicMock
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

    from aespa.db import _engine as original_engine

    SQLModel.metadata.create_all(engine)
    set_engine(engine)

    yield engine

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
    """Verify that an in-scope instruction runs the agentic loop and returns a final reply."""
    run = test_data["run"]
    instruction = "Scan for XSS on http://target.local/api/comments"

    mock_reply = "No XSS found."

    # Mock _call_with_tools to return a text-only (no tools) response that terminates the loop.
    async def mock_call_with_tools(*args, **kwargs):
        text_block = {"type": "text", "text": mock_reply}
        return [text_block], "end_turn", [text_block]

    with patch("aespa.services.llm._call_with_tools", side_effect=mock_call_with_tools):
        response = await run_alice_turn(run.id, instruction, [])

        assert response["status"] == "complete"
        assert mock_reply in response["message"]


@pytest.mark.anyio
async def test_run_alice_turn_stream_yields_correct_chunks(db_session, test_data):
    """Verify that run_alice_turn_stream yields properly structured SSE events."""
    run = test_data["run"]
    instruction = "Check IDOR on http://target.local/users"

    mock_reply = "Let's check the users path."

    # Mock _call_with_tools to emit one text block then end (no tool calls)
    async def mock_call_with_tools(*args, **kwargs):
        text_block = {"type": "text", "text": mock_reply}
        return [text_block], "end_turn", [text_block]

    with patch("aespa.services.llm._call_with_tools", side_effect=mock_call_with_tools):
        chunks = []
        async for line in run_alice_turn_stream(run.id, instruction, []):
            if line.startswith("data: "):
                chunks.append(json.loads(line[6:].strip()))

        assert len(chunks) >= 3

        thinking_chunks = [c for c in chunks if c.get("type") == "thinking_chunk"]
        message_chunks = [c for c in chunks if c.get("type") == "message_chunk"]
        done_chunks = [c for c in chunks if c.get("type") == "done"]

        assert any("Initializing" in c["delta"] for c in thinking_chunks)
        assert any(mock_reply in c["delta"] for c in message_chunks)
        assert len(done_chunks) == 1
        assert mock_reply in done_chunks[0]["message"]


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

        lines = [line for line in r_api.iter_lines()]
        assert "data: {\"type\": \"thinking_chunk\", \"delta\": \"thinking\"}" in lines
        assert "data: {\"type\": \"done\", \"thought\": \"Thought\", \"message\": \"Reply\"}" in lines
        mock_turn.assert_called_once_with(run.id, "Test message", [])


@pytest.mark.anyio
async def test_alice_write_finding_tool_persists(db_session, test_data):
    """Verify that calling write_finding via the agentic loop persists a finding."""
    from aespa.services.alice import _execute_alice_tool
    from aespa.models import ScanFinding
    from sqlmodel import select

    run = test_data["run"]
    llm_cfg = test_data["llm_cfg"]

    finding_input = {
        "title": "Default Admin Access Enabled",
        "severity": "critical",
        "cvss_score": 9.5,
        "affected_url": "http://target.local/admin/",
        "description": "Default credentials admin/admin123 work.",
        "evidence": "Successful login with admin/admin123",
        "recommendation": "Change the password immediately.",
    }

    # Mock _persist_dynamic_finding so it doesn't need full LLM
    with patch("aespa.services.scanner._persist_dynamic_finding", new_callable=AsyncMock) as mock_persist:
        result = await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=llm_cfg,
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="write_finding",
            tool_input=finding_input,
            step=1,
        )

    assert "Default Admin Access Enabled" in result
    assert mock_persist.called
    call_kwargs = mock_persist.call_args.kwargs
    assert call_kwargs["raw"]["finding_source"] == "alice"
    assert call_kwargs["raw"]["title"] == "Default Admin Access Enabled"
