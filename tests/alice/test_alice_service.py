"""Tests for A.L.I.C.E. chat coordinator and scope routing service."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from aespa.db import get_session
from aespa.main import create_app
from aespa.models import CrawledPage, LLMConfig, Site
from aespa.models import TestRun as RunModel
from aespa.services import alice_tasks as at
from aespa.services.alice import run_alice_turn, run_alice_turn_stream


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


def test_alice_tool_set_includes_auth_and_enforce_coverage_tools():
    from aespa.services.alice import _get_alice_tools

    names = {tool["name"] for tool in _get_alice_tools()}
    assert "reauthenticate" in names
    assert "skip_coverage" in names
    assert "rerun_validation" in names
    enforce_names = {
        tool["name"] for tool in _get_alice_tools(exclude={"skip_coverage"})
    }
    assert "reauthenticate" in enforce_names
    assert "skip_coverage" not in enforce_names


def test_alice_run_status_context_reports_crawl_progress(db_session, test_data):
    """ALICE can answer a crawl-status question from AESPA's live run state."""
    from aespa.services.scanner import _run_thinking_context_tool

    run = test_data["run"]
    run.phase = "crawling"
    run.pages_discovered = 3
    run.max_pages = 10
    run.current_url = "http://target.local/account"
    run.per_user_progress = json.dumps(
        {"alice": {"current_url": run.current_url, "pages_visited": 3}}
    )
    db_session.add(
        CrawledPage(
            test_run_id=run.id, url="http://target.local/account", status="crawled"
        )
    )
    db_session.commit()

    result = _run_thinking_context_tool(
        "run_status",
        {},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=run.id,
        base_url="http://target.local",
    )

    assert result["run_kind"] == "web"
    assert result["phase"] == "crawling"
    assert result["crawl"]["status"] == "running"
    assert result["crawl"]["pages_discovered"] == 3
    assert result["crawl"]["max_pages"] == 10
    assert result["crawl"]["current_url"] == "http://target.local/account"
    assert result["crawl"]["per_user_progress"]["alice"]["pages_visited"] == 3


def test_alice_prompt_explains_aespa_operational_questions():
    from aespa.services.prompts.alice import (
        ALICE_OPERATIONAL_SYSTEM_PROMPT,
        ALICE_SYSTEM_PROMPT,
    )

    assert "MANDATORY INTENT ROUTING" in ALICE_SYSTEM_PROMPT
    assert "CURRENT AESPA RUN STATUS" in ALICE_SYSTEM_PROMPT
    assert "context_tool(tool='run_status')" in ALICE_SYSTEM_PROMPT
    assert "do not use http_request, browser" in ALICE_SYSTEM_PROMPT
    assert "operational/support turn" in ALICE_OPERATIONAL_SYSTEM_PROMPT
    assert "The only tools available for this turn are context_tool and done" in (
        ALICE_OPERATIONAL_SYSTEM_PROMPT
    )


def test_alice_operational_question_tool_gate_preserves_explicit_testing():
    from aespa.services.alice import _classify_alice_intent

    assert _classify_alice_intent("What is the progress of the crawl?") == "operational"
    assert (
        _classify_alice_intent("What is the status of this test run?") == "operational"
    )
    assert _classify_alice_intent("Test the crawl for XSS") == "testing"
    assert _classify_alice_intent("Probe the API for IDOR") == "testing"
    assert _classify_alice_intent("Re-run validation for all findings") == "testing"


def test_goal_mode_done_schema_requires_completion_state():
    from aespa.services.alice import _get_alice_tools, _goal_mode_tools

    tools = _goal_mode_tools(_get_alice_tools())
    done = next(tool for tool in tools if tool["name"] == "done")

    assert done["input_schema"]["properties"]["status"]["enum"] == [
        "completed",
        "blocked",
    ]
    assert "remaining_work" in done["input_schema"]["required"]


def test_alice_goal_lifecycle_is_persistent(db_session, test_data):
    from aespa.services import alice_goals

    run = test_data["run"]
    goal = alice_goals.create_goal("web", run.id, "tab-goal", "Test account recovery")
    alice_goals.update_goal(
        goal.id,
        checkpoint={"remaining_work": ["Test email enumeration"]},
        increment_cycle=True,
    )

    loaded = alice_goals.goal_out(alice_goals.get_goal("web", run.id, "tab-goal"))
    assert loaded["status"] == "active"
    assert loaded["cycle_count"] == 1
    assert loaded["checkpoint"]["remaining_work"] == ["Test email enumeration"]

    alice_goals.reconcile_interrupted_goals()
    paused = alice_goals.goal_out(alice_goals.get_goal("web", run.id, "tab-goal"))
    assert paused["status"] == "paused"
    assert "restarted" in paused["pause_reason"]


@pytest.mark.anyio
async def test_goal_mode_rejects_partial_done_then_accepts_verified_completion(
    db_session, test_data
):
    from aespa.services import alice_goals

    run = test_data["run"]
    row = alice_goals.create_goal("web", run.id, "tab-goal", "Test account recovery")
    goal = alice_goals.goal_out(row)
    replies = [
        [
            {
                "type": "tool_use",
                "id": "tool-1",
                "name": "context_tool",
                "input": {"tool": "site_map", "args": {}},
            }
        ],
        [
            {
                "type": "tool_use",
                "id": "done-1",
                "name": "done",
                "input": {
                    "status": "completed",
                    "summary": "Partly checked",
                    "completed_criteria": ["Loaded the route inventory"],
                    "evidence": ["site_map result"],
                    "remaining_work": ["Probe the recovery endpoint"],
                },
            }
        ],
        [
            {
                "type": "tool_use",
                "id": "done-2",
                "name": "done",
                "input": {
                    "status": "completed",
                    "summary": "Recovery behavior verified",
                    "completed_criteria": ["Tested account recovery"],
                    "evidence": ["The recovery probe returned a uniform response"],
                    "remaining_work": [],
                },
            }
        ],
    ]
    calls = 0

    async def mock_call(*args, **kwargs):  # noqa: ARG001
        nonlocal calls
        blocks = replies[calls]
        calls += 1
        return blocks, "tool_use", blocks

    lines = []
    with (
        patch("aespa.services.llm._call_with_tools", side_effect=mock_call),
        patch("aespa.services.alice._execute_alice_tool", new=AsyncMock(return_value="site map evidence")),
        patch("aespa.services.llm.plain_completion", new=AsyncMock(return_value='{"verdict":"completed","reason":"verified","missing_work":[]}')),
        patch("aespa.services.validator.is_validating", return_value=False),
    ):
        async for line in run_alice_turn_stream(
            run.id, "Test account recovery", [], goal=goal
        ):
            lines.append(line)

    events = [json.loads(line[6:].strip()) for line in lines if line.startswith("data: ")]
    assert calls == 3
    assert any(event["type"] == "goal_progress" for event in events)
    assert any(event["type"] == "goal_completed" for event in events)
    completed = alice_goals.get_goal("web", run.id, "tab-goal")
    assert completed.status == "completed"


@pytest.mark.anyio
async def test_goal_mode_requires_repeated_confirmation_of_a_blocker(test_data):
    from aespa.services.alice import _check_goal_completion

    proposal = {
        "status": "blocked",
        "summary": "Testing needs a valid customer account.",
        "completed_criteria": ["Confirmed the route requires authentication"],
        "evidence": ["The endpoint returned 401 for the available session"],
        "remaining_work": ["Test the authenticated customer flow"],
        "blocker": "No valid customer account is available.",
    }
    checkpoint = {}

    with patch(
        "aespa.services.llm.plain_completion",
        new=AsyncMock(
            return_value=(
                '{"verdict":"blocked","reason":"external access is required",'
                '"missing_work":[]}'
            )
        ),
    ):
        results = [
            await _check_goal_completion(
                test_data["llm_cfg"],
                objective="Test the authenticated customer flow",
                proposal=proposal,
                evidence=[{"tool": "http_request", "result": "401"}],
                run_id=test_data["run"].id,
                is_api=True,
                checkpoint=checkpoint,
            )
            for _ in range(3)
        ]

    assert [accepted for accepted, _, _ in results] == [False, False, True]
    assert checkpoint["blocker_confirmations"] == 3


@pytest.mark.anyio
async def test_active_goal_accepts_steering(test_data):
    from aespa.services import alice_goals

    goal = alice_goals.create_goal(
        "web", test_data["run"].id, "tab-goal", "Test account recovery"
    )
    task = at.AliceTask(
        run_id=test_data["run"].id,
        tab_id="tab-goal",
        think_msg_id="think",
        reply_msg_id="reply",
        goal_id=goal.id,
        goal=alice_goals.goal_out(goal),
    )
    at._registry[("site", test_data["run"].id)] = task
    try:
        assert (
            await at.steer_goal(test_data["run"].id, "Focus on the reset token")
            is True
        )
        assert task.steering.get_nowait() == "Focus on the reset token"
        assert task.events[-1]["type"] == "goal_steered"
    finally:
        at._registry.pop(("site", test_data["run"].id), None)


def test_alice_run_status_prefers_live_scan_state(db_session, test_data):
    from aespa.services.scanner import _run_thinking_context_tool

    run = test_data["run"]
    run.status = "stopped"
    run.phase = "scanning"
    db_session.add(run)
    db_session.commit()

    with patch("aespa.services.scanner.is_thinking_running", return_value=True):
        result = _run_thinking_context_tool(
            "run_status",
            {},
            pages_snapshot=[],
            findings_snapshot=[],
            history=[],
            run_id=run.id,
            base_url="http://target.local",
        )

    assert result["status"] == "running"
    assert result["scan"]["status"] == "running"


@pytest.mark.anyio
async def test_alice_rerun_validation_uses_managed_validator(db_session, test_data):
    from aespa.models import ScanFinding
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    first = ScanFinding(
        test_run_id=run.id,
        owasp_category="A01",
        title="Needs validation",
        description="Evidence to re-check.",
        severity="high",
        validation_status="unconfirmed",
    )
    confirmed = ScanFinding(
        test_run_id=run.id,
        owasp_category="A02",
        title="Already confirmed",
        description="Already verified.",
        severity="medium",
        validation_status="confirmed",
    )
    db_session.add(first)
    db_session.add(confirmed)
    db_session.commit()
    db_session.refresh(first)

    with (
        patch("aespa.services.validator.is_validating", return_value=False),
        patch(
            "aespa.services.validator.start_validation", new_callable=AsyncMock
        ) as start_validation,
    ):
        result = json.loads(
            await _execute_alice_tool(
                run.id,
                test_data["llm_cfg"],
                "http://target.local",
                test_data["site"].id,
                "rerun_validation",
                {},
                1,
            )
        )

    assert result["status"] == "started"
    assert result["queued"] == 1
    start_validation.assert_awaited_once_with(run.id, finding_ids=[first.id])


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
async def test_run_alice_turn_executes_loop_for_in_scope_directive(
    db_session, test_data
):
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
async def test_alice_turn_includes_live_status_for_operational_questions(
    db_session, test_data
):
    """The model receives run state before deciding whether a request is a test."""
    run = test_data["run"]
    run.phase = "crawling"
    run.pages_discovered = 4
    run.max_pages = 12
    db_session.add(run)
    db_session.commit()
    captured = {}

    async def mock_call_with_tools(*args, **kwargs):
        captured["calls"] = captured.get("calls", 0) + 1
        captured["system"] = args[1]
        captured.setdefault("initial_message", args[2][-1]["content"])
        captured.setdefault("tools", {tool["name"] for tool in kwargs["tools"]})
        text_block = {"type": "text", "text": "The crawl has found 4 of 12 pages."}
        return [text_block], "end_turn", [text_block]

    with patch("aespa.services.llm._call_with_tools", side_effect=mock_call_with_tools):
        response = await run_alice_turn(
            run.id, "What is the progress of the crawl?", []
        )

    assert response["status"] == "complete"
    assert "operational/support turn" in captured["system"]
    assert "MANDATORY INTENT ROUTING" not in captured["system"]
    assert captured["tools"] <= {"context_tool", "done"}
    assert captured["calls"] == 1
    initial_message = captured["initial_message"]
    assert "CURRENT AESPA RUN STATUS" in initial_message
    assert '"pages_discovered": 4' in initial_message


@pytest.mark.anyio
async def test_alice_operational_answer_with_done_tool_stays_visible(
    db_session, test_data
):
    """A final text answer must not be swallowed when the model also calls done."""
    run = test_data["run"]
    captured = {"calls": 0}

    async def mock_call_with_tools(*args, **kwargs):  # noqa: ARG001
        captured["calls"] += 1
        blocks = [
            {"type": "text", "text": "The crawl is complete."},
            {"type": "tool_use", "id": "done-1", "name": "done", "input": {}},
        ]
        return blocks, "tool_use", blocks

    with patch("aespa.services.llm._call_with_tools", side_effect=mock_call_with_tools):
        response = await run_alice_turn(run.id, "What is the crawl progress?", [])

    assert captured["calls"] == 1
    assert "The crawl is complete." in response["message"]


@pytest.mark.anyio
async def test_alice_operational_reasoning_stays_out_of_visible_answer(
    db_session, test_data
):
    """Structured reasoning stays private while the text block reaches the reply."""
    run = test_data["run"]
    captured = {"calls": 0}

    async def mock_call_with_tools(*args, **kwargs):  # noqa: ARG001
        captured["calls"] += 1
        blocks = [
            {"type": "thinking", "thinking": "The user asked about AESPA status."},
            {"type": "text", "text": "The crawl is complete."},
        ]
        return blocks, "end_turn", blocks

    with patch("aespa.services.llm._call_with_tools", side_effect=mock_call_with_tools):
        response = await run_alice_turn(run.id, "What is the crawl progress?", [])

    assert captured["calls"] == 1
    assert "The crawl is complete." in response["message"]
    assert "AESPA status" not in response["message"]
    assert "AESPA status" in response["thought_process"]


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


@pytest.mark.anyio
async def test_alice_quota_pause_is_emitted_as_warning_and_chat_message(
    db_session, test_data
):
    run = test_data["run"]
    from aespa.services import llm as llm_service

    async def mock_call_with_tools(*args, **kwargs):
        raise llm_service.LLMQuotaPauseError(
            "Codex upstream rate limit persisted; resume after the window resets."
        )

    with patch("aespa.services.llm._call_with_tools", side_effect=mock_call_with_tools):
        chunks = []
        async for line in run_alice_turn_stream(run.id, "Check the target", []):
            if line.startswith("data: "):
                chunks.append(json.loads(line[6:].strip()))

    warnings = [chunk for chunk in chunks if chunk.get("type") == "warning"]
    messages = [chunk for chunk in chunks if chunk.get("type") == "message_chunk"]
    done = [chunk for chunk in chunks if chunk.get("type") == "done"]

    assert len(warnings) == 1
    assert "paused this ALICE turn" in warnings[0]["message"]
    assert any("rate-limit window" in chunk["delta"] for chunk in messages)
    assert len(done) == 1
    assert "paused this ALICE turn" in done[0]["message"]


@pytest.mark.anyio
async def test_run_alice_turn_stream_routes_inline_think_tags_to_trace(
    db_session, test_data
):
    """MiniMax-style <think> blocks should not leak into visible reply chunks."""
    run = test_data["run"]
    reply = "<think>private reasoning\nwith details</think>Visible answer only."

    async def mock_call_with_tools(*args, **kwargs):
        text_block = {"type": "text", "text": reply}
        return [text_block], "end_turn", [text_block]

    with patch("aespa.services.llm._call_with_tools", side_effect=mock_call_with_tools):
        chunks = []
        async for line in run_alice_turn_stream(run.id, "Summarize", []):
            if line.startswith("data: "):
                chunks.append(json.loads(line[6:].strip()))

    thinking_text = "".join(
        c.get("delta", "") for c in chunks if c.get("type") == "thinking_chunk"
    )
    message_text = "".join(
        c.get("delta", "") for c in chunks if c.get("type") == "message_chunk"
    )
    done = [c for c in chunks if c.get("type") == "done"][0]

    assert "private reasoning" in thinking_text
    assert "private reasoning" not in message_text
    assert "Visible answer only." in message_text
    assert "private reasoning" not in done["message"]
    assert "Visible answer only." in done["message"]


def test_alice_chat_api_endpoint(test_client, test_data):
    """Verify that the POST /api/test-runs/{run_id}/alice/run endpoint operates correctly."""
    run = test_data["run"]

    # Test 404 for non-existent run
    r_404 = test_client.post(
        "/api/test-runs/999999/alice/run",
        json={"message": "hello", "think_msg_id": "t1", "reply_msg_id": "r1"},
    )
    assert r_404.status_code == 404

    # Test valid request — alice/run starts a background task and returns {"ok": True}
    with patch("aespa.services.alice_tasks.start") as mock_start:
        mock_start.return_value = None
        r_api = test_client.post(
            f"/api/test-runs/{run.id}/alice/run",
            json={
                "message": "Test message",
                "history": [],
                "tab_id": "tab-test",
                "think_msg_id": "think-1",
                "reply_msg_id": "reply-1",
            },
        )

        assert r_api.status_code == 200
        assert r_api.json() == {"ok": True}
        mock_start.assert_called_once()


def test_alice_sessions_roundtrip_and_run_token(test_client, test_data):
    """GET returns a stable run_created_at token; PUT persists and reloads chats."""
    run = test_data["run"]

    # 404 for a non-existent run.
    assert test_client.get("/api/test-runs/999999/alice/sessions").status_code == 404

    # Fresh run: no chats yet, but the stable run identity token is present.
    r_empty = test_client.get(f"/api/test-runs/{run.id}/alice/sessions")
    assert r_empty.status_code == 200
    empty = r_empty.json()
    assert empty["chats"] == []
    token = empty["run_created_at"]
    assert token == run.created_at.isoformat()

    # Save a chat session, then reload it.
    payload = {
        "chats": [
            {
                "id": "tab-default",
                "title": "Session 1",
                "messages": [
                    {
                        "id": "m1",
                        "sender": "user",
                        "type": "message",
                        "text": "hi",
                        "ts": "10:00",
                    },
                    {
                        "id": "m2",
                        "sender": "alice",
                        "type": "thinking",
                        "text": "[Step 1] Calling LLM...",
                        "ts": "10:01",
                        "stepData": {
                            "1": {
                                "llmMessages": [{"role": "user", "content": "hi"}],
                                "tools": [
                                    {
                                        "tool": "context_tool",
                                        "input": {"tool": "finding_list"},
                                        "result": "{}",
                                    }
                                ],
                            }
                        },
                    },
                ],
            }
        ],
        "active_tab_id": "tab-default",
    }
    r_put = test_client.put(f"/api/test-runs/{run.id}/alice/sessions", json=payload)
    assert r_put.status_code == 200

    loaded = test_client.get(f"/api/test-runs/{run.id}/alice/sessions").json()
    assert loaded["run_created_at"] == token  # token is stable across saves
    assert len(loaded["chats"]) == 1
    assert loaded["chats"][0]["id"] == "tab-default"
    assert [m["text"] for m in loaded["chats"][0]["messages"]] == [
        "hi",
        "[Step 1] Calling LLM...",
    ]
    assert (
        loaded["chats"][0]["messages"][1]["stepData"]["1"]["tools"][0]["tool"]
        == "context_tool"
    )
    assert loaded["updated_at"] is not None


@pytest.mark.anyio
async def test_alice_write_finding_tool_persists(db_session, test_data):
    """Verify that calling write_finding via the agentic loop persists a finding."""

    from aespa.services.alice import _execute_alice_tool

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
    mock_finding = MagicMock()
    mock_finding.id = 42
    with (
        patch(
            "aespa.services.scanner._persist_dynamic_finding", new_callable=AsyncMock
        ) as mock_persist,
        patch(
            "aespa.services.validator.validate_finding_inline", new_callable=AsyncMock
        ) as mock_validate,
    ):
        mock_persist.return_value = mock_finding
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
    mock_validate.assert_called_once()


def _capturing_scanner_client(captured: dict):
    """Return a fake _make_scanner_client that records the cookies/headers it is
    built with and yields a client whose .request returns a canned response."""

    def _factory(*args, **kwargs):
        captured["cookies"] = kwargs.get("cookies")
        captured["headers"] = kwargs.get("headers")

        resp = MagicMock()
        resp.status_code = 200
        resp.text = "ok"
        resp.headers = {}
        resp.cookies = {}

        client = MagicMock()
        client.request = AsyncMock(return_value=resp)
        client.get = AsyncMock(return_value=resp)

        ctx = AsyncMock()
        ctx.__aenter__.return_value = client
        ctx.__aexit__.return_value = False
        return ctx

    return _factory


@pytest.mark.anyio
async def test_alice_http_request_forwards_owasp_category_to_post_probe(
    db_session, test_data
):
    """A probe declaring owasp_category invokes post_probe_fn(url, method, category)."""
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    calls: list = []
    captured: dict = {}
    with patch(
        "aespa.services.scanner._make_scanner_client",
        _capturing_scanner_client(captured),
    ):
        await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="http_request",
            tool_input={
                "url": "http://target.local/v1/products/5",
                "method": "GET",
                "owasp_category": "API1",
            },
            step=1,
            session_vault={},
            post_probe_fn=lambda url, method, cat: calls.append((url, method, cat)),
        )

    assert calls == [("http://target.local/v1/products/5", "GET", "API1")]


@pytest.mark.anyio
async def test_alice_http_request_no_post_probe_without_category(db_session, test_data):
    """A setup request without owasp_category does not invoke post_probe_fn."""
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    calls: list = []
    captured: dict = {}
    with patch(
        "aespa.services.scanner._make_scanner_client",
        _capturing_scanner_client(captured),
    ):
        await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="http_request",
            tool_input={"url": "http://target.local/login", "method": "POST"},
            step=1,
            session_vault={},
            post_probe_fn=lambda *a: calls.append(a),
        )

    assert calls == []


@pytest.mark.anyio
async def test_alice_http_request_uses_stored_primary_session(db_session, test_data):
    """http_request carries the run's stored authenticated session by default."""
    from aespa.services import scanner_sessions as session_svc
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    session_svc.upsert_session(
        run.id,
        label="configured_primary",
        kind="cookie",
        cookies={"SESSION": "abc123"},
        extra_headers={"Authorization": "Bearer tok-xyz"},
    )
    vault = session_svc.load_session_vault(run.id)

    captured: dict = {}
    with patch(
        "aespa.services.scanner._make_scanner_client",
        _capturing_scanner_client(captured),
    ):
        await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="http_request",
            tool_input={"url": "http://target.local/account", "method": "GET"},
            step=1,
            session_vault=vault,
        )

    assert captured["cookies"] == {"SESSION": "abc123"}
    assert captured["headers"]["Authorization"] == "Bearer tok-xyz"


@pytest.mark.anyio
async def test_alice_http_request_use_session_selects_and_anonymous_opts_out(
    db_session, test_data
):
    """use_session selects a specific stored session; "anonymous" sends no creds."""
    from aespa.services import scanner_sessions as session_svc
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    session_svc.upsert_session(
        run.id,
        label="configured_primary",
        kind="cookie",
        cookies={"SESSION": "admin"},
        extra_headers={},
    )
    session_svc.upsert_session(
        run.id,
        label="alice_user_b",
        kind="cookie",
        cookies={"SESSION": "userb"},
        extra_headers={},
    )
    session_svc.ensure_anonymous_session(run.id)
    vault = session_svc.load_session_vault(run.id)

    site_id = test_data["site"].id
    llm_cfg = test_data["llm_cfg"]

    async def _probe(tool_input):
        captured: dict = {}
        with patch(
            "aespa.services.scanner._make_scanner_client",
            _capturing_scanner_client(captured),
        ):
            await _execute_alice_tool(
                run_id=run.id,
                llm_cfg=llm_cfg,
                base_url="http://target.local",
                site_id=site_id,
                tool_name="http_request",
                tool_input=tool_input,
                step=1,
                session_vault=vault,
            )
        return captured

    # Explicit label selects the second identity.
    selected = await _probe(
        {"url": "http://target.local/u/2", "use_session": "alice_user_b"}
    )
    assert selected["cookies"] == {"SESSION": "userb"}

    # "anonymous" opts out of stored credentials entirely.
    anon = await _probe({"url": "http://target.local/u/2", "use_session": "anonymous"})
    assert anon["cookies"] == {}
    assert "Authorization" not in anon["headers"]


@pytest.mark.anyio
async def test_alice_http_request_anonymous_when_vault_empty(db_session, test_data):
    """With no stored sessions, requests fall back to anonymous (no cookies)."""
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    captured: dict = {}
    with patch(
        "aespa.services.scanner._make_scanner_client",
        _capturing_scanner_client(captured),
    ):
        await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="http_request",
            tool_input={"url": "http://target.local/", "method": "GET"},
            step=1,
            session_vault={},
        )

    assert captured["cookies"] == {}
    assert "Authorization" not in captured["headers"]


@pytest.mark.anyio
async def test_alice_browser_captures_session_into_vault(db_session, test_data):
    """The browser tool drives a live page and, with capture_session, persists the
    resulting cookies into the vault + DB so later calls reuse the authenticated session."""
    from aespa.services import scanner_sessions as session_svc
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    vault: dict = {}

    fake_ctx = AsyncMock()
    fake_ctx.cookies = AsyncMock(return_value=[{"name": "sid", "value": "abc123"}])
    fake_page = MagicMock()

    async def fake_get_browser(_run_id, api_run_id=None):
        return fake_page, fake_ctx

    async def fake_run_action(page, action, default_url, scanner_policy):  # noqa: ARG001
        return {
            "body": "Final URL: http://target.local/admin\nLogged in.",
            "url": "http://target.local/admin",
        }

    with (
        patch("aespa.services.alice._get_alice_browser", fake_get_browser),
        patch("aespa.services.scanner._run_thinking_browser_action", fake_run_action),
    ):
        result = await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="browser",
            tool_input={
                "steps": [
                    {"op": "goto", "url": "http://target.local/"},
                    {"op": "click", "selector": "button:has-text('Log in')"},
                    {"op": "fill", "selector": "#user", "value": "admin"},
                    {"op": "click", "selector": "button[type=submit]"},
                ],
                "capture_session": "modal_admin",
                "capture_username": "admin",
            },
            step=1,
            session_vault=vault,
        )

    # Cookies injected into the in-memory vault for the rest of the turn.
    assert vault["modal_admin"]["cookies"] == {"sid": "abc123"}
    assert vault["modal_admin"]["username"] == "admin"
    assert "[Session captured as 'modal_admin'" in result
    # And persisted to the DB so a fresh vault load sees it.
    reloaded = session_svc.load_session_vault(run.id)
    assert reloaded["modal_admin"]["cookies"] == {"sid": "abc123"}
    assert reloaded["modal_admin"]["username"] == "admin"


@pytest.mark.anyio
async def test_alice_browser_blocks_out_of_scope_goto_step(db_session, test_data):
    """A goto step pointing outside scope is rejected before any browser launch."""
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]

    def _boom(_run_id, api_run_id=None):  # pragma: no cover - must never be called
        raise AssertionError("browser must not launch for out-of-scope steps")

    with patch("aespa.services.alice._get_alice_browser", _boom):
        result = await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="browser",
            tool_input={"steps": [{"op": "goto", "url": "http://evil.example/"}]},
            step=1,
            session_vault={},
        )

    assert "[SCOPE BLOCK]" in result


@pytest.mark.anyio
async def test_alice_browser_replays_crawled_state_and_passes_page_provenance(
    db_session, test_data
):
    from aespa.models import CrawledPage
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    page_row = CrawledPage(
        test_run_id=run.id,
        url="http://target.local/app",
        state_kind="interactive",
        replay_steps_json=json.dumps(
            {
                "root_url": "http://target.local/app",
                "steps": [
                    {"kind": "click", "selector": "#open"},
                    {"kind": "fill", "selector": "#search", "value": "alice"},
                ],
            }
        ),
    )
    db_session.add(page_row)
    db_session.commit()
    db_session.refresh(page_row)

    fake_ctx = AsyncMock()
    fake_page = MagicMock()
    captured: dict = {}

    async def fake_get_browser(_run_id, api_run_id=None):
        return fake_page, fake_ctx

    async def fake_run_action(page, action, default_url, scanner_policy):  # noqa: ARG001
        captured.update(action)
        return {
            "body": "interactive state loaded",
            "url": "http://target.local/app",
            "status": 200,
            "headers": {},
        }

    with (
        patch("aespa.services.alice._get_alice_browser", fake_get_browser),
        patch("aespa.services.scanner._run_thinking_browser_action", fake_run_action),
    ):
        result = await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="browser",
            tool_input={"page_id": page_row.id, "replay": True, "steps": []},
            step=1,
            session_vault={},
        )

    assert "interactive state loaded" in result
    assert captured["steps"][:3] == [
        {"op": "goto", "url": "http://target.local/app"},
        {"op": "click", "selector": "#open"},
        {"op": "fill", "selector": "#search", "value": "alice"},
    ]


@pytest.mark.anyio
async def test_alice_skip_coverage_is_gated_to_web_enforce_mode(db_session, test_data):
    from aespa.services.alice import _execute_alice_tool

    run = test_data["run"]
    run.coverage_mode = "track"
    db_session.add(run)
    db_session.commit()
    result = await _execute_alice_tool(
        run_id=run.id,
        llm_cfg=test_data["llm_cfg"],
        base_url="http://target.local",
        site_id=test_data["site"].id,
        tool_name="skip_coverage",
        tool_input={"url": "http://target.local/", "owasp_category": "A01"},
        step=1,
        session_vault={},
    )
    assert "only for web Full mode" in result

    run.coverage_mode = "enforce"
    db_session.add(run)
    db_session.commit()
    with patch(
        "aespa.services.web_workprogram.skip_web_coverage_obligation",
        return_value="blocked with evidence",
    ) as skip:
        result = await _execute_alice_tool(
            run_id=run.id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="skip_coverage",
            tool_input={
                "url": "http://target.local/",
                "owasp_category": "A01",
                "disposition": "blocked",
                "reason": "login flow unavailable",
                "evidence": "HTTP 403",
            },
            step=2,
            session_vault={},
        )
    skip.assert_called_once()
    assert "blocked with evidence" in result


@pytest.mark.anyio
async def test_alice_reauthenticate_refreshes_configured_primary_session(
    db_session, test_data
):
    from aespa.models import Credential
    from aespa.services.alice import _execute_alice_tool

    credential = Credential(
        site_id=test_data["site"].id,
        username="admin",
        password="secret",
        login_url="http://target.local/login",
    )
    db_session.add(credential)
    db_session.commit()

    async def fake_export(**kwargs):  # noqa: ARG001
        return {"sid": "fresh"}, "fresh-token"

    vault: dict = {}
    with patch("aespa.services.scanner._export_cred_session", fake_export):
        result = await _execute_alice_tool(
            run_id=test_data["run"].id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="reauthenticate",
            tool_input={
                "reason": "The primary session returned 403 after a prior 200."
            },
            step=1,
            session_vault=vault,
        )

    assert "succeeded" in result
    assert vault["configured_primary"]["cookies"] == {"sid": "fresh"}
    assert vault["configured_primary"]["extra_headers"] == {
        "Authorization": "Bearer fresh-token"
    }


@pytest.mark.anyio
async def test_alice_web_update_lead_records_web_run_kind(test_data):
    from aespa.services.alice import _execute_alice_tool

    updated = MagicMock(id=12, status="dismissed", note="not reproducible")
    with patch(
        "aespa.services.scan_leads.update_lead", return_value=updated
    ) as update_lead:
        result = await _execute_alice_tool(
            run_id=test_data["run"].id,
            llm_cfg=test_data["llm_cfg"],
            base_url="http://target.local",
            site_id=test_data["site"].id,
            tool_name="update_lead",
            tool_input={
                "lead_id": 12,
                "outcome": "dismissed",
                "note": "not reproducible",
            },
            step=1,
            session_vault={},
        )

    assert json.loads(result)["status"] == "dismissed"
    assert update_lead.call_args.kwargs["investigated_by_run_type"] == "web"


# --- Merged from test_alice_tasks.py ---
def _alice_task(run_id=1, run_type="site"):
    return at.AliceTask(
        run_id=run_id,
        tab_id="t",
        think_msg_id="th",
        reply_msg_id="re",
        run_type=run_type,
    )


def test_buffer_trim_tracks_dropped_and_keeps_cursor_aligned():
    task = _alice_task()
    total = at.BUFFER_LIMIT + 50
    for i in range(total):
        at._append(task, {"type": "x", "i": i})

    # The buffer is bounded and `dropped` accounts for every evicted event.
    assert len(task.events) <= at.BUFFER_LIMIT
    assert task.dropped == total - len(task.events)
    # The first retained event sits at absolute index == dropped.
    assert task.events[0]["i"] == task.dropped

    # A reconnect cursor inside the retained window maps to the right slice —
    # pre-fix this used the absolute cursor as a buffer index and lost events.
    cursor = total - 10
    start = max(0, cursor - task.dropped)
    assert [e["i"] for e in task.events[start:]] == list(range(cursor, total))


def test_stream_events_replays_exactly_from_cursor_after_trim():
    task = _alice_task(run_id=42)
    total = at.BUFFER_LIMIT + 30
    for i in range(total):
        at._append(task, {"type": "x", "i": i})
    task.done = True
    at._registry[("site", 42)] = task
    try:
        cursor = total - 5

        async def _drain():
            return [
                line
                async for line in at.stream_events(42, cursor=cursor, run_type="site")
            ]

        got = [json.loads(line[6:]) for line in asyncio.run(_drain())]
        assert [e["i"] for e in got] == list(range(cursor, total))
    finally:
        at._registry.pop(("site", 42), None)
