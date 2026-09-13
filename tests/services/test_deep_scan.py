from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import ValidationError
from sqlmodel import Session, select

from aespa.models import (
    CrawledPage,
    DeepScanAttempt,
    DeepScanConfig,
    DeepScanTask,
    PageOwaspTest,
    ScanLead,
    ScanObligation,
    Site,
    TestRun,
)
from aespa.services.deep_scan import get_queue, seed_deep_tasks


def _run_with_page(db_session) -> TestRun:
    site = Site(name="Deep target", base_url="https://target.local")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    run = TestRun(
        site_id=site.id,
        name="Deep run",
        coverage_mode="deep",
        scan_mode="aggressive",
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    db_session.add(
        CrawledPage(
            test_run_id=run.id,
            url="https://target.local/api/accounts/1",
            in_scope=True,
            req_auth=True,
            takes_input=True,
            has_object_ref=True,
            has_business_logic=True,
            state_kind="interactive",
            state_label="Transfer form",
        )
    )
    db_session.commit()
    return run


def test_deep_task_seeding_is_idempotent_and_includes_recon(db_session):
    run = _run_with_page(db_session)

    first = seed_deep_tasks(run.id)
    second = seed_deep_tasks(run.id)

    assert first > 0
    assert second == 0
    queue = get_queue(run.id)
    assert queue["total"] == first
    assert queue["counts"]["queued"] == first
    assert {task["source"] for task in queue["tasks"]} >= {
        "coverage",
        "recon",
        "workflow_recon",
    }
    assert any(
        check["attack_class"] == "idor"
        for task in queue["tasks"]
        for check in task["checks"]
    )
    assert queue["checks_total"] >= queue["total"]


def test_deep_queue_reports_the_number_of_findings_from_a_task(db_session):
    run = _run_with_page(db_session)
    db_session.add(
        DeepScanTask(
            run_id=run.id,
            fingerprint="finding-count",
            attack_class="sqli",
            target_url="https://target.local/api/accounts",
            status="finding",
            outcome="2 new findings",
        )
    )
    db_session.commit()

    task = get_queue(run.id)["tasks"][0]

    assert task["finding_count"] == 2


def test_deep_groups_vulnerability_and_parameter_checks_by_operation(db_session):
    run = _run_with_page(db_session)
    for technique, parameter in (("sqli", "search"), ("reflected_xss", "search")):
        db_session.add(
            ScanObligation(
                run_kind="web",
                run_id=run.id,
                scan_mode="full",
                owasp_catalog="web_2025",
                owasp_category="A03",
                vulnerability_technique=technique,
                route_template="https://target.local/api/accounts/1",
                http_method="GET",
                parameter=parameter,
            )
        )
    db_session.commit()

    seed_deep_tasks(run.id)
    operation_tasks = [
        task for task in get_queue(run.id)["tasks"] if task["task_kind"] == "operation"
    ]

    assert len(operation_tasks) == 1
    classes = {check["attack_class"] for check in operation_tasks[0]["checks"]}
    assert {"sqli", "xss"}.issubset(classes)
    assert operation_tasks[0]["inputs"] == ["search"]


def test_worker_step_description_prefers_the_hypothesis_over_a_raw_request():
    from aespa.services.scanner import _infer_step_note

    description = _infer_step_note(
        "http_request",
        {
            "method": "GET",
            "url": "https://target.local/api/accounts/1",
            "hypothesis": "Compare another user's account response to verify ownership checks.",
        },
        4,
    )

    assert description == (
        "Compare another user's account response to verify ownership checks."
    )


def test_worker_step_description_has_plain_fallbacks():
    from aespa.services.scanner import _infer_step_note

    assert (
        _infer_step_note("context_tool", {"tool": "traffic_search", "args": {}}, 5)
        == "Look up traffic search"
    )
    assert (
        _infer_step_note("execute_python", {"purpose": "Compare response sizes"}, 6)
        == "Compare response sizes"
    )


def test_deep_mode_is_web_only():
    from aespa.api.scan import _StartScanBody
    from aespa.schemas import ApiTestRunCreate

    assert _StartScanBody(coverage_mode="deep").coverage_mode == "deep"
    with pytest.raises(ValidationError):
        ApiTestRunCreate(coverage_mode="deep")


def test_deep_is_a_web_only_scan_mode():
    from aespa.api.scan import _StartScanBody
    from aespa.schemas import ApiTestRunCreate

    assert _StartScanBody(coverage_mode="deep").coverage_mode == "deep"
    with pytest.raises(ValidationError):
        ApiTestRunCreate(coverage_mode="deep")


def test_deep_task_seeding_preserves_imported_sast_leads(db_session):
    run = _run_with_page(db_session)
    lead = ScanLead(
        producer_run_id=999,
        title="SQL injection in account lookup",
        category="A03",
        severity="high",
        confidence=0.9,
        suggested_endpoint="/api/accounts/1",
        imported_into_run_type="web",
        imported_into_run_id=run.id,
        public_reference="SL-1",
    )
    db_session.add(lead)
    db_session.commit()

    seed_deep_tasks(run.id)
    db_session.expire_all()
    task = db_session.exec(
        select(DeepScanTask).where(DeepScanTask.lead_id == lead.id)
    ).one()

    assert task.source == "sast_lead"
    assert task.attack_class == "sqli"
    assert task.priority == 9
    assert "SL-1" in task.hypothesis


def test_deep_task_cap_does_not_change_other_scan_modes(db_session):
    run = _run_with_page(db_session)
    db_session.add(
        DeepScanConfig(
            id=1,
            max_tasks=2,
            max_concurrent_workers=3,
            max_steps_per_task=10,
        )
    )
    db_session.commit()

    seed_deep_tasks(run.id)

    assert get_queue(run.id)["total"] == 2
    assert any(
        task["task_kind"] == "operation" for task in get_queue(run.id)["tasks"]
    )
    ordinary = TestRun(
        site_id=run.site_id,
        name="Quick run",
        coverage_mode="track",
        scan_mode="aggressive",
    )
    db_session.add(ordinary)
    db_session.commit()
    assert ordinary.coverage_mode == "track"


@pytest.mark.anyio
async def test_scanner_routes_only_deep_mode_to_deep_engine(db_session, monkeypatch):
    from aespa.services import deep_scan, scanner

    run = _run_with_page(db_session)
    called = []

    async def fake_deep(run_id: int):
        called.append(run_id)

    monkeypatch.setattr(deep_scan, "run_deep_scan", fake_deep)
    await scanner._do_thinking_scan(run.id)

    assert called == [run.id]


@pytest.mark.anyio
async def test_deep_worker_pool_uses_configured_concurrency(db_session, monkeypatch):
    from aespa.services import deep_scan, scanner

    run = _run_with_page(db_session)
    db_session.add(
        DeepScanConfig(
            id=1,
            max_tasks=4,
            max_concurrent_workers=3,
            max_steps_per_task=5,
            include_sast_leads=False,
            include_recon_checks=True,
        )
    )
    db_session.commit()
    active = 0
    high_water = 0
    worker_roles = []

    async def fake_worker(**kwargs):
        nonlocal active, high_water
        worker_roles.append(kwargs["agent_role"])
        active += 1
        high_water = max(high_water, active)
        await asyncio.sleep(0.01)
        active -= 1
        from aespa.services import specialist_handoffs

        specialist_handoffs.update_handoff(
            kwargs["handoff_id"], status="completed", outcome="No confirmed finding"
        )

    monkeypatch.setattr(deep_scan, "get_llm_config_for_role", lambda *_: object())
    monkeypatch.setattr(scanner, "_run_specialist_agent", fake_worker)

    await deep_scan.run_deep_scan(run.id)

    queue = get_queue(run.id)
    assert high_water == 3
    assert all(role and role != "Deep Attack Worker" for role in worker_roles)
    assert queue["total"] == 4
    assert queue["counts"]["inconclusive"] == 4


@pytest.mark.anyio
async def test_deep_worker_probes_update_web_workprogram(db_session, monkeypatch):
    from aespa.services import deep_scan, scanner

    run = _run_with_page(db_session)
    db_session.add(
        DeepScanConfig(
            id=1,
            max_tasks=1,
            max_concurrent_workers=1,
            max_steps_per_task=5,
            include_sast_leads=False,
            include_recon_checks=False,
        )
    )
    db_session.commit()
    observed_statuses = []

    async def fake_worker(**kwargs):
        kwargs["post_probe_fn"](
            kwargs["target_url"],
            "GET",
            "",
            None,
            200,
            kwargs["target_page_id"],
        )
        with Session(db_session.get_bind()) as session:
            cell = session.exec(
                select(PageOwaspTest)
                .where(PageOwaspTest.test_run_id == run.id)
                .where(PageOwaspTest.page_id == kwargs["target_page_id"])
            ).one()
            observed_statuses.append(cell.status)

        from aespa.services import specialist_handoffs

        specialist_handoffs.update_handoff(
            kwargs["handoff_id"], status="completed", outcome="No confirmed finding"
        )

    monkeypatch.setattr(deep_scan, "get_llm_config_for_role", lambda *_: object())
    monkeypatch.setattr(scanner, "_run_specialist_agent", fake_worker)

    await deep_scan.run_deep_scan(run.id)

    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.status == "covered")
    ).one()
    task = db_session.exec(
        select(DeepScanTask).where(DeepScanTask.run_id == run.id)
    ).one()

    assert observed_statuses == ["in_progress"]
    assert cell.page_id == task.page_id
    assert cell.owasp_category == task.owasp_category
    assert scanner._finding_hooks.get(run.id) is None


@pytest.mark.anyio
async def test_deep_worker_usage_is_saved_on_the_web_run(db_session, monkeypatch):
    from aespa.services import deep_scan, llm, scanner

    run = _run_with_page(db_session)
    db_session.add(
        DeepScanConfig(
            id=1,
            max_tasks=1,
            max_concurrent_workers=1,
            max_steps_per_task=5,
            include_sast_leads=False,
            include_recon_checks=True,
        )
    )
    db_session.commit()
    usage_key = ("web", run.id)
    llm._run_token_usage.pop(usage_key, None)
    llm._run_token_seeded.discard(usage_key)

    async def fake_worker(**kwargs):
        assert llm._capture_usage_context().run_id == run.id
        llm._record_usage("deep-test-model", 11, 7, provider="unknown")
        from aespa.services import specialist_handoffs

        specialist_handoffs.update_handoff(
            kwargs["handoff_id"], status="completed", outcome="No confirmed finding"
        )

    monkeypatch.setattr(deep_scan, "get_llm_config_for_role", lambda *_: object())
    monkeypatch.setattr(scanner, "_run_specialist_agent", fake_worker)

    try:
        await deep_scan.run_deep_scan(run.id)
        db_session.expire_all()
        usage = json.loads(db_session.get(TestRun, run.id).token_usage_json)

        assert usage["deep-test-model"]["input"] == 11
        assert usage["deep-test-model"]["output"] == 7
        assert llm._capture_usage_context().run_id is None
    finally:
        llm._run_token_usage.pop(usage_key, None)
        llm._run_token_seeded.discard(usage_key)


@pytest.mark.anyio
async def test_stopping_deep_scan_requeues_in_flight_task(db_session, monkeypatch):
    from aespa.services import deep_scan, scanner

    run = _run_with_page(db_session)
    db_session.add(
        DeepScanConfig(
            id=1,
            max_tasks=1,
            max_concurrent_workers=1,
            max_steps_per_task=5,
            include_sast_leads=False,
            include_recon_checks=True,
        )
    )
    db_session.commit()
    worker_started = asyncio.Event()

    async def waiting_worker(**_kwargs):
        worker_started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(deep_scan, "get_llm_config_for_role", lambda *_: object())
    monkeypatch.setattr(scanner, "_run_specialist_agent", waiting_worker)

    scan_task = asyncio.create_task(deep_scan.run_deep_scan(run.id))
    await asyncio.wait_for(worker_started.wait(), timeout=1)
    scan_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await scan_task

    db_session.expire_all()
    queued_task = db_session.exec(
        select(DeepScanTask).where(DeepScanTask.run_id == run.id)
    ).one()
    cancelled_attempt = db_session.exec(
        select(DeepScanAttempt).where(DeepScanAttempt.task_id == queued_task.id)
    ).one()

    assert queued_task.status == "queued"
    assert queued_task.attempt_count == 0
    assert queued_task.worker_id is None
    assert cancelled_attempt.status == "cancelled"

    async def completing_worker(**kwargs):
        from aespa.services import specialist_handoffs

        specialist_handoffs.update_handoff(
            kwargs["handoff_id"], status="completed", outcome="No confirmed finding"
        )

    monkeypatch.setattr(scanner, "_run_specialist_agent", completing_worker)
    await deep_scan.run_deep_scan(run.id)

    queue = get_queue(run.id)
    assert queue["counts"]["inconclusive"] == 1
    assert queue["tasks"][0]["attempt_count"] == 1
    attempts = list(
        db_session.exec(
            select(DeepScanAttempt)
            .where(DeepScanAttempt.run_id == run.id)
            .order_by(DeepScanAttempt.id)
        ).all()
    )
    assert [attempt.status for attempt in attempts] == ["cancelled", "inconclusive"]
    assert [attempt.attempt_number for attempt in attempts] == [1, 2]


def test_web_run_cleanup_removes_deep_queue_with_foreign_keys(fk_engine):
    from aespa.services.run_cleanup import cascade_delete_web_run

    with Session(fk_engine) as session:
        run = _run_with_page(session)
        task = DeepScanTask(
            run_id=run.id,
            fingerprint="cleanup-task",
            attack_class="config",
            target_url="https://target.local",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.add(
            DeepScanAttempt(run_id=run.id, task_id=task.id, worker_id="deep-worker-1")
        )
        session.commit()

        cascade_delete_web_run(session, run.id)
        session.commit()

        assert session.get(DeepScanTask, task.id) is None


def test_resume_recovers_tasks_cancelled_by_older_deep_scans(db_session):
    from aespa.services.deep_scan import _recover_queue

    run = _run_with_page(db_session)
    task = DeepScanTask(
        run_id=run.id,
        fingerprint="legacy-cancelled-task",
        attack_class="config",
        target_url="https://target.local",
        status="cancelled",
        attempt_count=1,
        max_attempts=1,
        worker_id="deep-worker-1-task-1",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    _recover_queue(run.id)
    db_session.expire_all()
    recovered = db_session.get(DeepScanTask, task.id)

    assert recovered.status == "queued"
    assert recovered.attempt_count == 0
    assert recovered.worker_id is None
