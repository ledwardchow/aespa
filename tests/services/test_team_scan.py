from __future__ import annotations

import asyncio

from sqlmodel import select

from aespa.models import PhaseCheckpoint, Site, TestRun
from aespa.services import checkpoint as checkpoint_svc
from aespa.services.team_scan import (
    TEAM_ASSIGNMENTS,
    reset_team_progress,
    run_team_scan,
)


def _team_run(db_session) -> TestRun:
    site = Site(name="Team target", base_url="https://target.local")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    run = TestRun(
        site_id=site.id,
        name="Team run",
        coverage_mode="team",
        scan_mode="aggressive",
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_team_runs_three_fresh_standard_test_leads(db_session, monkeypatch):
    from aespa.services import scanner, team_scan

    run = _team_run(db_session)
    calls = []
    emitted = []

    async def fake_scan(run_id, **kwargs):
        calls.append((run_id, kwargs))
        checkpoint_svc.save_checkpoint(
            run_id,
            messages=[{"role": "assistant", "content": "done"}],
            history=[],
            blocked_urls=set(),
            failed_url_counts={},
            step_count=1,
            progressive_findings_count=0,
            consecutive_context_tools=0,
        )

    monkeypatch.setattr(scanner, "_do_thinking_scan", fake_scan)
    monkeypatch.setattr(
        team_scan.events_svc, "emit", lambda run_id, event: emitted.append(event)
    )

    asyncio.run(run_team_scan(run.id))

    assert [call[1]["team_assignment"]["key"] for call in calls] == [
        "primary",
        "independent",
        "closer",
    ]
    assert all(call[1]["effective_coverage_mode"] == "standard" for call in calls)
    assert [call[1]["team_assignment"]["run_preflight"] for call in calls] == [
        True,
        False,
        False,
    ]
    assert calls[-1][1]["team_assignment"]["final"] is True
    assert checkpoint_svc.checkpoint_status(run.id)["exists"] is False
    coordinator_events = [
        event for event in emitted if event.get("agent_id") == "scanner"
    ]
    assert coordinator_events
    assert all(event["role"] == "Test Co-ordinator" for event in coordinator_events)
    assert all(event["status"] == "active" for event in coordinator_events)
    assert "Perform an independent second look" in next(
        event["current_task"]
        for event in coordinator_events
        if "Pair Tester" in event["current_task"]
    )
    member_events = [
        event for event in emitted if str(event.get("agent_id", "")).startswith("team-")
    ]
    assert [
        (event["agent_id"], event["role"], event["status"]) for event in member_events
    ] == [
        ("team-primary", "Primary Tester", "active"),
        ("team-primary", "Primary Tester", "complete"),
        ("team-independent", "Pair Tester", "active"),
        ("team-independent", "Pair Tester", "complete"),
        ("team-closer", "QA Tester", "active"),
        ("team-closer", "QA Tester", "complete"),
    ]


def test_team_resume_skips_completed_members(db_session, monkeypatch):
    from aespa.services import scanner

    run = _team_run(db_session)
    checkpoint_svc.save_phase_checkpoint(
        run.id,
        "team_scan_member",
        "primary",
        {"label": "Primary Tester"},
        run_kind="web",
    )
    calls = []

    async def fake_scan(run_id, **kwargs):
        calls.append(kwargs["team_assignment"]["key"])

    monkeypatch.setattr(scanner, "_do_thinking_scan", fake_scan)

    asyncio.run(run_team_scan(run.id))

    assert calls == ["independent", "closer"]


def test_reset_team_progress_removes_only_team_markers(db_session):
    run = _team_run(db_session)
    for assignment in TEAM_ASSIGNMENTS:
        checkpoint_svc.save_phase_checkpoint(
            run.id,
            "team_scan_member",
            assignment["key"],
            {},
            run_kind="web",
        )
    checkpoint_svc.save_phase_checkpoint(
        run.id,
        "other_phase",
        "keep",
        {},
        run_kind="web",
    )

    reset_team_progress(run.id)

    remaining = db_session.exec(
        select(PhaseCheckpoint).where(PhaseCheckpoint.run_id == run.id)
    ).all()
    assert [(row.phase, row.idempotency_key) for row in remaining] == [
        ("other_phase", "keep")
    ]


def test_scanner_routes_team_mode_to_team_engine(db_session, monkeypatch):
    from aespa.services import scanner, team_scan

    run = _team_run(db_session)
    called = []

    async def fake_team_scan(run_id):
        called.append(run_id)

    monkeypatch.setattr(team_scan, "run_team_scan", fake_team_scan)

    asyncio.run(scanner._do_thinking_scan(run.id))

    assert called == [run.id]
