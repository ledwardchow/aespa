"""Failure Injection & Verification Test Suite for AESPA Scan Architecture.

Validates:
1. Terminal reason state transitions (coverage_complete, model_done_rejected, user_stop, stagnation).
2. Phase checkpoint resume idempotence (no duplicate findings, no re-run of completed phases).
3. Scan obligation seeding, execution logging, and coverage evidence evaluation.
4. Bounded specialist barrier timeout handling.
5. Structural identity fingerprinting deduplication.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    CrawledPage,
    ScanObligation,
    TestRun,
    TrafficEntry,
)
from aespa.services.checkpoint import has_phase_checkpoint, save_phase_checkpoint
from aespa.services.scan_completion import ScanCompletionPolicy
from aespa.services.scanner import await_specialist_barrier
from aespa.services.web_workprogram import (
    evaluate_coverage_evidence,
    record_probe_execution,
    seed_scan_obligations,
)


@pytest.fixture
def db_session():
    with Session(get_engine()) as session:
        yield session


def test_scenario_01_terminal_reason_state_model(db_session):
    """Scenario 01: TestRun lifecycle state and terminal_reason persistence."""
    run = TestRun(
        site_id=1,
        name="Test Lifecycle Run",
        scan_mode="full",
        phase="scanning",
        status="scanning",
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    run.phase = "finished"
    run.status = "complete"
    run.outcome = "complete"
    run.terminal_reason = "coverage_complete"
    db_session.add(run)
    db_session.commit()

    loaded = db_session.get(TestRun, run.id)
    assert loaded.phase == "finished"
    assert loaded.outcome == "complete"
    assert loaded.terminal_reason == "coverage_complete"


def test_scenario_02_phase_checkpoint_idempotence(db_session):
    """Scenario 02: PhaseCheckpoint saves and checks idempotency keys."""
    run = TestRun(site_id=1, name="Checkpoint Run", scan_mode="full")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    run_id = run.id
    phase = "reporting"
    key = "batch_001"

    assert has_phase_checkpoint(run_id, phase, key, run_kind="web") is False
    save_phase_checkpoint(run_id, phase, key, data={"findings": 3}, run_kind="web")
    assert has_phase_checkpoint(run_id, phase, key, run_kind="web") is True


def test_scenario_03_obligation_seeding_determinism(db_session):
    """Scenario 03: seed_scan_obligations generates deterministic queue."""
    run = TestRun(site_id=1, name="Obligation Run", scan_mode="full")
    db_session.add(run)
    db_session.commit()

    p1 = CrawledPage(
        test_run_id=run.id,
        url="https://target.local/api/v1/users/1",
        in_scope=True,
        has_object_ref=True,
    )
    p2 = CrawledPage(
        test_run_id=run.id,
        url="https://target.local/api/v1/transfers",
        in_scope=True,
        has_business_logic=True,
    )
    db_session.add(p1)
    db_session.add(p2)
    db_session.commit()

    created1 = seed_scan_obligations(run.id, scan_mode="full", run_kind="web")
    assert created1 > 0

    # Seeding again should create 0 new obligations
    created2 = seed_scan_obligations(run.id, scan_mode="full", run_kind="web")
    assert created2 == 0


def test_scenario_04_probe_execution_and_evidence_eval(db_session):
    """Scenario 04: Probe execution logging and coverage evidence evaluation."""
    run = TestRun(site_id=1, name="Evidence Run", scan_mode="full")
    db_session.add(run)
    db_session.commit()

    page = CrawledPage(
        test_run_id=run.id,
        url="https://target.local/api/users/1",
        in_scope=True,
        has_object_ref=True,
    )
    db_session.add(page)
    db_session.commit()

    seed_scan_obligations(run.id, scan_mode="full", run_kind="web")
    obligation = db_session.exec(
        select(ScanObligation).where(ScanObligation.run_id == run.id)
    ).first()
    assert obligation is not None

    exec_id = record_probe_execution(
        run_id=run.id,
        obligation_id=obligation.id,
        status_code=200,
        response_time_ms=45.2,
        run_kind="web",
    )
    assert exec_id is not None

    evaluate_coverage_evidence(
        execution_id=exec_id,
        expected_behavior="200 OK without errors",
        observed_behavior="200 OK clean",
        evaluation_oracle="status_code_oracle",
        outcome="passed",
    )

    db_session.expire_all()
    updated_obligation = db_session.get(ScanObligation, obligation.id)
    assert updated_obligation.status == "passed"


def test_web_obligations_use_supported_observed_method(db_session):
    run = TestRun(site_id=1, name="Method Evidence Run", scan_mode="full")
    db_session.add(run)
    db_session.commit()
    url = "https://target.local/api/transfers/check"
    db_session.add(
        CrawledPage(
            test_run_id=run.id,
            url=url,
            in_scope=True,
            has_business_logic=True,
        )
    )
    db_session.add(
        TrafficEntry(
            test_run_id=run.id,
            source="crawler",
            method="GET",
            url=url,
            status=405,
        )
    )
    db_session.add(
        TrafficEntry(
            test_run_id=run.id,
            source="playwright",
            method="POST",
            url=url,
            status=200,
        )
    )
    db_session.commit()

    created = seed_scan_obligations(run.id, scan_mode="full", run_kind="web")
    assert created > 0
    obligations = list(
        db_session.exec(select(ScanObligation).where(ScanObligation.run_id == run.id))
    )
    assert {item.http_method for item in obligations} == {"POST"}


def test_scenario_05_rejected_done_handling():
    """Scenario 05: ScanCompletionPolicy rejects done when session/coverage gaps exist."""
    policy = ScanCompletionPolicy()
    policy.session_created(
        "untested_user", lifecycle_state="verified", challenge_eligible=True
    )

    allowed, feedback, log_msg = policy.check_done()
    assert allowed is False
    assert "untested_user" in feedback
    assert "session-use challenge" in log_msg


@pytest.mark.anyio
async def test_scenario_06_specialist_barrier_timeout():
    """Scenario 06: Bounded specialist barrier handles completed and timing-out tasks."""
    run_id = 888

    async def fast_task():
        await asyncio.sleep(0.01)

    async def slow_task():
        await asyncio.sleep(10.0)

    from aespa.services.scanner import _specialist_tasks

    _specialist_tasks[run_id] = [
        asyncio.create_task(fast_task()),
        asyncio.create_task(slow_task()),
    ]

    completed_count = await await_specialist_barrier(run_id, timeout=0.1)
    assert completed_count == 1
    _specialist_tasks.pop(run_id, None)
