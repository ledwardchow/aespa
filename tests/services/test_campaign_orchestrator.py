"""Campaign orchestration: run identity, child sequencing (with scanners
mocked out), stop propagation, partial failure warnings, restart
reconciliation, and cascade-delete cleanup.

The dynamic scanners (crawler/scanner/api_scanner) and the SAST scanner are
monkeypatched to fast, deterministic fakes so these tests never touch
Playwright, an LLM provider, or the network — only the orchestration logic
in ``services/campaigns.py`` is under test.
"""

from __future__ import annotations

import asyncio
import json
import zipfile
from types import SimpleNamespace

import pytest
from sqlmodel import Session, select

from aespa.models import (
    Application,
    ApplicationComponent,
    ApplicationTarget,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    CampaignValidationCase,
    ComponentConnection,
    ComponentFact,
    ComponentSnapshot,
    LeadTargetMapping,
    RunIdentity,
    SastRun,
    ScanLead,
    ScanLeadComponentProvenance,
    Site,
    TestRun,
)
from aespa.schemas import (
    CampaignCreate,
    CampaignSourceMemberCreate,
    CampaignTargetMemberCreate,
)
from aespa.services import campaigns as campaigns_svc


def _seed_application(session: Session) -> dict:
    app = Application(name="Acme")
    session.add(app)
    session.flush()
    component = ApplicationComponent(application_id=app.id, name="checkout-ui")
    session.add(component)
    session.flush()
    snapshot = ComponentSnapshot(
        component_id=component.id,
        filename="ui.zip",
        stored_path="/tmp/ui.zip",
        size_bytes=1,
        sha256="a" * 64,
    )
    session.add(snapshot)
    site = Site(name="Portal", base_url="http://portal.test")
    session.add(site)
    session.flush()
    target = ApplicationTarget(
        application_id=app.id, target_type="site", target_id=site.id
    )
    session.add(target)
    session.commit()
    session.refresh(component)
    session.refresh(snapshot)
    session.refresh(target)
    return {
        "application_id": app.id,
        "component_id": component.id,
        "snapshot_id": snapshot.id,
        "target_id": target.id,
        "site_id": site.id,
    }


def _create_draft_campaign(session: Session, ctx: dict) -> AssessmentCampaign:
    payload = CampaignCreate(
        name="release-1",
        source_members=[
            CampaignSourceMemberCreate(
                component_id=ctx["component_id"], snapshot_id=ctx["snapshot_id"]
            )
        ],
        target_members=[CampaignTargetMemberCreate(target_id=ctx["target_id"])],
    )
    return campaigns_svc.create_campaign(session, ctx["application_id"], payload)


def test_campaign_id_joins_global_run_identity_namespace(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        identity = s.get(RunIdentity, campaign.id)
    assert identity is not None
    assert identity.kind == "campaign"


def test_forward_campaign_status_clears_old_interruption(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "interrupted"
        campaign.interrupted_stage = "sast_running"
        campaign.error_message = "Scan interrupted"
        campaign.warnings_json = json.dumps(
            ["The application restarted while this stage was running. Retry to resume."]
        )
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    campaigns_svc._set_campaign_status(campaign_id, "correlating")

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "correlating"
        assert campaign.interrupted_stage is None
        assert campaign.error_message is None
        assert json.loads(campaign.warnings_json) == []


def test_create_campaign_rejects_duplicate_component_selection(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        payload = CampaignCreate(
            name="dup",
            source_members=[
                CampaignSourceMemberCreate(
                    component_id=ctx["component_id"], snapshot_id=ctx["snapshot_id"]
                ),
                CampaignSourceMemberCreate(
                    component_id=ctx["component_id"], snapshot_id=ctx["snapshot_id"]
                ),
            ],
            target_members=[CampaignTargetMemberCreate(target_id=ctx["target_id"])],
        )
        with pytest.raises(campaigns_svc.InvalidCampaignState):
            campaigns_svc.create_campaign(s, ctx["application_id"], payload)


@pytest.mark.anyio
async def test_start_campaign_creates_frozen_sast_child_and_runs_stage(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, sast_run_id)
            run.status = "completed"
            s.add(run)
            s.commit()

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)

    await campaigns_svc.start_campaign(campaign_id)
    task = campaigns_svc._campaign_tasks.get(campaign_id)
    assert task is not None
    await task

    with Session(isolated_db_engine) as s:
        members = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).all()
        assert len(members) == 1
        assert members[0].sast_run_id is not None
        assert members[0].status == "completed"
        sast_run = s.get(SastRun, members[0].sast_run_id)
        assert sast_run.triggered_by_run_type == "campaign"
        assert sast_run.triggered_by_run_id == campaign_id

        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "awaiting_review"


@pytest.mark.anyio
async def test_partial_sast_failure_produces_warning_but_still_reaches_review(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as s:
        app = Application(name="Acme2")
        s.add(app)
        s.flush()
        good = ApplicationComponent(application_id=app.id, name="good-component")
        bad = ApplicationComponent(application_id=app.id, name="bad-component")
        s.add(good)
        s.add(bad)
        s.flush()
        good_snap = ComponentSnapshot(
            component_id=good.id,
            filename="g.zip",
            stored_path="/tmp/g.zip",
            size_bytes=1,
            sha256="d" * 64,
        )
        bad_snap = ComponentSnapshot(
            component_id=bad.id,
            filename="b.zip",
            stored_path="/tmp/b.zip",
            size_bytes=1,
            sha256="e" * 64,
        )
        s.add(good_snap)
        s.add(bad_snap)
        site = Site(name="P2", base_url="http://p2.test")
        s.add(site)
        s.flush()
        target = ApplicationTarget(
            application_id=app.id, target_type="site", target_id=site.id
        )
        s.add(target)
        s.commit()
        payload = CampaignCreate(
            name="partial",
            source_members=[
                CampaignSourceMemberCreate(
                    component_id=good.id, snapshot_id=good_snap.id
                ),
                CampaignSourceMemberCreate(
                    component_id=bad.id, snapshot_id=bad_snap.id
                ),
            ],
            target_members=[CampaignTargetMemberCreate(target_id=target.id)],
        )
        campaign = campaigns_svc.create_campaign(s, app.id, payload)
        campaign_id = campaign.id
        bad_snapshot_id = bad_snap.id

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, sast_run_id)
            if run.source_filename == "b.zip":
                run.status = "failed"
            else:
                run.status = "completed"
            s.add(run)
            s.commit()

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)

    await campaigns_svc.start_campaign(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "awaiting_review"  # still reaches review
        import json

        warnings = json.loads(campaign.warnings_json)
        assert len(warnings) >= 1

        members = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).all()
        statuses = {m.snapshot_id: m.status for m in members}
        assert statuses[bad_snapshot_id] == "failed"


@pytest.mark.anyio
async def test_child_sast_page_resume_reactivates_failed_campaign(
    isolated_db_engine,
):
    """Starting a campaign child from the SAST page resumes its parent."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        sast_run = SastRun(name="child", status="failed")
        s.add(sast_run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign.id
            )
        ).one()
        member.sast_run_id = sast_run.id
        member.status = "failed"
        campaign.status = "failed"
        campaign.error_message = "SAST run is not completed"
        campaign.warnings_json = (
            '["The application restarted while this stage was running. ", '
            '"A source-code scan did not finish successfully — matches involving '
            'that component may be incomplete.", '
            '"A source-code scan did not finish successfully — matches involving '
            'that component may be incomplete."]'
        )
        s.add(member)
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id
        sast_run_id = sast_run.id

    with Session(isolated_db_engine) as s:
        run = s.get(SastRun, sast_run_id)
        run.status = "scanning"
        s.add(run)
        s.commit()
    campaigns_svc.notify_source_run_started(sast_run_id)

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).one()
        assert campaign.status == "sast_running"
        assert campaign.error_message is None
        assert member.status == "running"
        assert campaign.warnings_json.count("did not finish successfully") == 0
        assert "The application restarted" not in campaign.warnings_json

    with Session(isolated_db_engine) as s:
        run = s.get(SastRun, sast_run_id)
        run.status = "completed"
        s.add(run)
        s.commit()
    campaigns_svc.notify_source_run_finished(sast_run_id, "completed")
    task = campaigns_svc._campaign_tasks[campaign_id]
    await task

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).one()
        assert campaign.status == "awaiting_review"
        assert member.status == "completed"


@pytest.mark.anyio
async def test_resume_source_member_retries_only_selected_child(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        second = ApplicationComponent(
            application_id=ctx["application_id"], name="orders-api"
        )
        s.add(second)
        s.flush()
        second_snapshot = ComponentSnapshot(
            component_id=second.id,
            filename="api.zip",
            stored_path="/tmp/api.zip",
            size_bytes=1,
            sha256="f" * 64,
        )
        s.add(second_snapshot)
        s.commit()
        second_snapshot_id = second_snapshot.id
        campaign = campaigns_svc.create_campaign(
            s,
            ctx["application_id"],
            CampaignCreate(
                name="resume-one",
                source_members=[
                    CampaignSourceMemberCreate(
                        component_id=ctx["component_id"], snapshot_id=ctx["snapshot_id"]
                    ),
                    CampaignSourceMemberCreate(
                        component_id=second.id, snapshot_id=second_snapshot.id
                    ),
                ],
                target_members=[CampaignTargetMemberCreate(target_id=ctx["target_id"])],
            ),
        )
        campaign_id = campaign.id

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, sast_run_id)
            run.status = "completed"
            s.add(run)
            s.commit()

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)
    await campaigns_svc.start_campaign(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    with Session(isolated_db_engine) as s:
        members = list(
            s.exec(
                select(CampaignSourceMember).where(
                    CampaignSourceMember.campaign_id == campaign_id
                )
            ).all()
        )
        selected = next(m for m in members if m.snapshot_id == second_snapshot_id)
        preserved = next(m for m in members if m.snapshot_id == ctx["snapshot_id"])
        selected.status = "failed"
        selected_run = s.get(SastRun, selected.sast_run_id)
        selected_run.status = "failed"
        s.add(selected)
        s.add(selected_run)
        s.commit()
        selected_id = selected.id
        selected_run_id = selected.sast_run_id
        preserved_id = preserved.id

    calls: list[int] = []

    async def _fake_resume(sast_run_id: int) -> None:
        calls.append(sast_run_id)
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, sast_run_id)
            run.status = "completed"
            s.add(run)
            s.commit()

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_resume)
    await campaigns_svc.resume_source_member(campaign_id, selected_id)
    task = campaigns_svc._campaign_member_tasks[(campaign_id, "source", selected_id)]
    await task

    with Session(isolated_db_engine) as s:
        selected = s.get(CampaignSourceMember, selected_id)
        preserved = s.get(CampaignSourceMember, preserved_id)
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert calls == [selected_run_id]
        assert selected.status == "completed"
        assert preserved.status == "completed"
        assert campaign.status == "awaiting_review"


@pytest.mark.anyio
async def test_continue_to_live_testing_gated_until_review_submitted(
    isolated_db_engine,
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "awaiting_review"
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    with pytest.raises(campaigns_svc.InvalidCampaignState):
        await campaigns_svc.continue_to_live_testing(campaign_id)


@pytest.mark.anyio
async def test_continue_to_live_testing_skips_scan_without_runnable_cases(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "awaiting_review"
        campaign.review_submitted_at = campaign.created_at
        campaign.warnings_json = json.dumps(
            [
                "Lead 12: pre-crawl path wording was not rewritten (bad response)",
                "A source-code scan did not finish successfully - matches may be incomplete.",
            ]
        )
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    call_order: list[str] = []

    async def _fake_start_crawl(run_id: int) -> None:
        call_order.append("crawl_start")
        with Session(isolated_db_engine) as s:
            run = s.get(TestRun, run_id)
            run.phase = "crawled"
            run.status = "complete"
            s.add(run)
            s.commit()

    async def _fake_start_thinking_scan(run_id: int) -> None:
        call_order.append("scan_start")

    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc

    monkeypatch.setattr(crawler_svc, "start_crawl", _fake_start_crawl)
    monkeypatch.setattr(crawler_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scanner_svc, "start_thinking_scan", _fake_start_thinking_scan)
    monkeypatch.setattr(scanner_svc, "is_thinking_running", lambda run_id: False)
    await campaigns_svc.continue_to_live_testing(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    assert call_order == ["crawl_start"]

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "completed"
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).first()
        assert member.test_run_id is not None
        assert member.status == "completed"


@pytest.mark.anyio
async def test_stop_campaign_awaits_child_stop_and_wait_barrier(
    isolated_db_engine, monkeypatch
):
    """stop_campaign must use the *_and_wait variant (genuinely awaiting
    child cleanup) rather than a fire-and-forget stop request, and must not
    return until that cleanup has actually finished."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id

    started = asyncio.Event()
    child_cleanup_done = asyncio.Event()

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)
    monkeypatch.setattr(sast_scanner_svc, "is_sast_scan_running", lambda rid: True)

    stop_and_wait_calls: list[int] = []
    stop_fire_and_forget_calls: list[int] = []

    async def _fake_stop_sast_scan_and_wait(
        sast_run_id: int, timeout: float = 5.0
    ) -> bool:
        stop_and_wait_calls.append(sast_run_id)
        await asyncio.sleep(0.05)  # simulate real (bounded) cleanup latency
        child_cleanup_done.set()
        return True

    async def _fake_stop_sast_scan(sast_run_id: int) -> bool:
        # If stop_campaign ever calls this fire-and-forget variant instead of
        # the *_and_wait one, this test must catch it.
        stop_fire_and_forget_calls.append(sast_run_id)
        return True

    monkeypatch.setattr(
        sast_scanner_svc, "stop_sast_scan_and_wait", _fake_stop_sast_scan_and_wait
    )
    monkeypatch.setattr(sast_scanner_svc, "stop_sast_scan", _fake_stop_sast_scan)

    await campaigns_svc.start_campaign(campaign_id)
    await asyncio.wait_for(started.wait(), timeout=2.0)

    with Session(isolated_db_engine) as s:
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        sast_run_id = member.sast_run_id

    await campaigns_svc.stop_campaign(campaign_id)

    assert stop_and_wait_calls == [sast_run_id]
    assert stop_fire_and_forget_calls == []
    # The cleanup coroutine had genuinely finished before stop_campaign
    # returned — not just been scheduled.
    assert child_cleanup_done.is_set()

    # By the time stop_campaign returns, the campaign is already persisted
    # "stopped" and its orchestrator task is done — no extra await needed.
    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "stopped"
    assert not campaigns_svc.is_campaign_running(campaign_id)


@pytest.mark.anyio
async def test_delete_campaign_immediately_after_stop_does_not_race(
    isolated_db_engine, monkeypatch
):
    """A caller that stops then immediately deletes a campaign must not
    race an in-flight child cleanup — stop_campaign has to fully settle
    everything (including the child's own barrier) before returning."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id
        application_id = ctx["application_id"]

    started = asyncio.Event()

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)
    monkeypatch.setattr(sast_scanner_svc, "is_sast_scan_running", lambda rid: True)

    async def _fake_stop_sast_scan_and_wait(
        sast_run_id: int, timeout: float = 5.0
    ) -> bool:
        await asyncio.sleep(0.05)  # a real, bounded cleanup delay
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, sast_run_id)
            if run is not None:
                run.status = "cancelled"
                s.add(run)
                s.commit()
        return True

    monkeypatch.setattr(
        sast_scanner_svc, "stop_sast_scan_and_wait", _fake_stop_sast_scan_and_wait
    )

    await campaigns_svc.start_campaign(campaign_id)
    await asyncio.wait_for(started.wait(), timeout=2.0)

    await campaigns_svc.stop_campaign(campaign_id)
    # No sleep/yield here on purpose — this is exactly the "stop then
    # immediately delete" sequence a UI action would perform.
    with Session(isolated_db_engine) as s:
        campaigns_svc.delete_campaign(s, application_id, campaign_id)

    with Session(isolated_db_engine) as s:
        assert s.get(AssessmentCampaign, campaign_id) is None


def test_reconcile_campaigns_marks_interrupted_stage_resumable(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "sast_running"
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        member.status = "running"
        s.add(member)
        s.commit()

    reconciled = campaigns_svc.reconcile_campaigns()
    assert campaign_id in reconciled

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        # Resumable, not a dead end: distinct status + the exact interrupted
        # stage recorded so retry knows what to resume.
        assert campaign.status == "interrupted"
        assert campaign.interrupted_stage == "sast_running"
        assert campaign.error_message
        # The in-flight member is reset to "pending" (not "failed") so a
        # retry re-attempts exactly it rather than skipping it as terminal.
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        assert member.status == "pending"


def test_reconcile_campaigns_leaves_terminal_campaigns_untouched(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "completed"
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    reconciled = campaigns_svc.reconcile_campaigns()
    assert campaign_id not in reconciled


def test_delete_campaign_cascades_child_runs_and_facts(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id
        sast_run = SastRun(name="child", status="completed")
        s.add(sast_run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        member.sast_run_id = sast_run.id
        s.add(member)
        fact = ComponentFact(
            sast_run_id=sast_run.id,
            component_id=ctx["component_id"],
            fact_type="route",
            path="/x",
            evidence_location="a.py:1",
            fingerprint="fp1",
        )
        s.add(fact)
        lead = ScanLead(
            producer_run_id=campaign_id,
            producer_run_type="campaign",
            title="cross lead",
        )
        s.add(lead)
        s.commit()
        sast_run_id = sast_run.id

    with Session(isolated_db_engine) as s:
        campaigns_svc.delete_campaign(s, ctx["application_id"], campaign_id)

    with Session(isolated_db_engine) as s:
        assert s.get(AssessmentCampaign, campaign_id) is None
        assert s.get(RunIdentity, campaign_id) is None
        assert s.get(SastRun, sast_run_id) is None
        assert (
            s.exec(
                select(ComponentFact).where(ComponentFact.sast_run_id == sast_run_id)
            ).first()
            is None
        )
        assert (
            s.exec(
                select(ScanLead).where(ScanLead.producer_run_type == "campaign")
            ).first()
            is None
        )


def test_delete_campaign_blocked_while_active(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "sast_running"
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    with Session(isolated_db_engine) as s:
        with pytest.raises(campaigns_svc.InvalidCampaignState):
            campaigns_svc.delete_campaign(s, ctx["application_id"], campaign_id)


# ── Regression: cascade_delete_campaign FK order + snapshot ownership ───────
# These use the `fk_engine` fixture (SQLite foreign_keys=ON) so an ordering
# bug that would silently pass with FK enforcement off actually fails here.


def test_cascade_delete_campaign_respects_fk_order(fk_engine, tmp_path):
    """LeadTargetMapping/ComponentConnection/ScanLeadComponentProvenance must
    be gone before the ComponentFact/ScanLead rows they reference are
    deleted, or SQLite raises IntegrityError with FK enforcement on."""
    from aespa.models import (
        ApiCollection,
        ApiEndpoint,
        ComponentConnection,
        LeadTargetMapping,
        ScanLeadComponentProvenance,
    )

    with Session(fk_engine) as s:
        ctx = _seed_application(s)
        # Swap the web target for an API target with a real ApiEndpoint so a
        # LeadTargetMapping can reference it meaningfully.
        collection = ApiCollection(name="Orders API", base_url="http://api.test")
        s.add(collection)
        s.flush()
        s.add(ApiEndpoint(collection_id=collection.id, method="POST", path="/orders"))
        target = ApplicationTarget(
            application_id=ctx["application_id"],
            target_type="api_collection",
            target_id=collection.id,
        )
        s.add(target)
        s.flush()
        ctx["target_id"] = target.id
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id

        sast_run = SastRun(name="child", status="completed")
        s.add(sast_run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        member.sast_run_id = sast_run.id
        s.add(member)

        call_fact = ComponentFact(
            sast_run_id=sast_run.id,
            component_id=ctx["component_id"],
            fact_type="http_call",
            method="POST",
            path="/orders",
            evidence_location="a.py:1",
            fingerprint="call-fp",
        )
        route_fact = ComponentFact(
            sast_run_id=sast_run.id,
            component_id=ctx["component_id"],
            fact_type="route",
            method="POST",
            path="/orders",
            evidence_location="b.py:1",
            fingerprint="route-fp",
        )
        s.add(call_fact)
        s.add(route_fact)
        s.flush()

        s.add(
            ComponentConnection(
                campaign_id=campaign_id,
                source_component_id=ctx["component_id"],
                source_fact_id=call_fact.id,
                target_component_id=ctx["component_id"],
                target_fact_id=route_fact.id,
                confidence=0.9,
            )
        )

        lead = ScanLead(
            producer_run_id=sast_run.id,
            producer_run_type="sast",
            title="lead",
            location="a.py:1",
            reportable=True,
        )
        s.add(lead)
        s.flush()

        s.add(
            LeadTargetMapping(
                campaign_id=campaign_id,
                lead_id=lead.id,
                target_id=target.id,
                target_type="api_collection",
                score=0.8,
            )
        )

        campaign_lead = ScanLead(
            producer_run_id=campaign_id,
            producer_run_type="campaign",
            title="cross-repo lead",
        )
        s.add(campaign_lead)
        s.flush()
        s.add(
            ScanLeadComponentProvenance(
                scan_lead_id=campaign_lead.id,
                component_id=ctx["component_id"],
                role="primary",
                fact_id=call_fact.id,
            )
        )
        s.commit()

    # Must not raise sqlalchemy.exc.IntegrityError with FK enforcement on.
    with Session(fk_engine) as s:
        campaigns_svc.delete_campaign(s, ctx["application_id"], campaign_id)

    with Session(fk_engine) as s:
        assert s.get(AssessmentCampaign, campaign_id) is None
        assert s.exec(select(ComponentConnection)).first() is None
        assert s.exec(select(LeadTargetMapping)).first() is None
        assert s.exec(select(ScanLeadComponentProvenance)).first() is None


def test_cascade_delete_campaign_preserves_shared_snapshot_file(fk_engine, tmp_path):
    """Deleting a campaign must not delete the ComponentSnapshot's ZIP file —
    it is shared, immutable evidence another campaign may still select."""
    snapshot_path = tmp_path / "component.zip"
    snapshot_path.write_bytes(b"PK\x03\x04fake zip contents")

    with Session(fk_engine) as s:
        ctx = _seed_application(s)
        snapshot = s.get(ComponentSnapshot, ctx["snapshot_id"])
        snapshot.stored_path = str(snapshot_path)
        s.add(snapshot)
        s.commit()

        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id
        sast_run = SastRun(
            name="child",
            status="completed",
            source_archive_path=str(snapshot_path),
            source_filename="component.zip",
        )
        s.add(sast_run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        member.sast_run_id = sast_run.id
        s.add(member)
        s.commit()

    with Session(fk_engine) as s:
        campaigns_svc.delete_campaign(s, ctx["application_id"], campaign_id)

    assert snapshot_path.is_file()  # the shared archive survives

    # A second campaign can still select and use the exact same snapshot.
    with Session(fk_engine) as s:
        second = _create_draft_campaign(s, ctx)
        assert second.id != campaign_id


def test_standalone_sast_deletion_still_removes_its_own_upload(
    isolated_db_engine, tmp_path
):
    """A standalone (non-campaign) SAST run's archive is NOT a shared
    snapshot, so its own cascade-delete still removes the file."""
    from aespa.services import run_cleanup

    archive_path = tmp_path / "standalone_upload.zip"
    archive_path.write_bytes(b"PK\x03\x04fake zip contents")

    with Session(isolated_db_engine) as s:
        run = SastRun(
            name="standalone",
            status="completed",
            source_archive_path=str(archive_path),
            source_filename="standalone_upload.zip",
        )
        s.add(run)
        s.commit()
        run_id = run.id

    with Session(isolated_db_engine) as s:
        run_cleanup.cascade_delete_sast_run(s, run_id)
        s.commit()

    assert not archive_path.exists()


# ── Regression: external deletion detaches campaign-owned children ───────────


def test_direct_sast_run_deletion_detaches_campaign_member(
    isolated_db_engine,
):
    from aespa.services import run_cleanup

    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        sast_run = SastRun(name="child", status="completed")
        s.add(sast_run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign.id
            )
        ).first()
        member.sast_run_id = sast_run.id
        s.add(member)
        s.commit()
        campaign_id = campaign.id
        sast_run_id = sast_run.id

    with Session(isolated_db_engine) as s:
        run_cleanup.cascade_delete_sast_run(s, sast_run_id)
        s.commit()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        assert member is not None
        assert member.sast_run_id is None
        assert member.status == "pending"
        assert s.get(SastRun, sast_run_id) is None


def test_direct_web_run_deletion_detaches_campaign_member(
    isolated_db_engine,
):
    from aespa.services import run_cleanup

    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        run = TestRun(site_id=ctx["site_id"], name="child web run")
        s.add(run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign.id
            )
        ).first()
        member.test_run_id = run.id
        s.add(member)
        s.commit()
        campaign_id = campaign.id
        run_id = run.id

    with Session(isolated_db_engine) as s:
        run_cleanup.cascade_delete_web_run(s, run_id)
        s.commit()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).first()
        assert member is not None
        assert member.test_run_id is None
        assert member.status == "pending"
        assert s.get(TestRun, run_id) is None


def test_direct_api_run_deletion_detaches_campaign_member(
    isolated_db_engine,
):
    from aespa.models import ApiCollection, ApiTestRun
    from aespa.services import run_cleanup

    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        collection = ApiCollection(name="Orders API", base_url="http://api.test")
        s.add(collection)
        s.flush()
        target = ApplicationTarget(
            application_id=ctx["application_id"],
            target_type="api_collection",
            target_id=collection.id,
        )
        s.add(target)
        s.flush()
        ctx["target_id"] = target.id
        campaign = _create_draft_campaign(s, ctx)
        run = ApiTestRun(collection_id=collection.id, name="child api run")
        s.add(run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign.id
            )
        ).first()
        member.api_test_run_id = run.id
        s.add(member)
        s.commit()
        campaign_id = campaign.id
        run_id = run.id

    with Session(isolated_db_engine) as s:
        run_cleanup.cascade_delete_api_run(s, run_id)
        s.commit()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).first()
        assert member is not None
        assert member.api_test_run_id is None
        assert member.status == "pending"
        assert s.get(ApiTestRun, run_id) is None


def test_site_deletion_blocked_while_attached_to_application(client):
    site_resp = client.post(
        "/api/sites", json={"name": "S1", "base_url": "http://t.local"}
    )
    site_id = site_resp.json()["id"]
    app_resp = client.post("/api/applications", json={"name": "App1"})
    app_id = app_resp.json()["id"]
    client.post(
        f"/api/applications/{app_id}/targets",
        json={"target_type": "site", "target_id": site_id},
    )
    resp = client.delete(f"/api/sites/{site_id}")
    assert resp.status_code == 409


def test_api_collection_deletion_blocked_while_attached_to_application(client):
    coll_resp = client.post(
        "/api/api-collections",
        json={"name": "Orders", "base_url": "http://api.test"},
    )
    collection_id = coll_resp.json()["id"]
    app_resp = client.post("/api/applications", json={"name": "App2"})
    app_id = app_resp.json()["id"]
    client.post(
        f"/api/applications/{app_id}/targets",
        json={"target_type": "api_collection", "target_id": collection_id},
    )
    resp = client.delete(f"/api/api-collections/{collection_id}")
    assert resp.status_code == 409


def test_direct_test_run_delete_endpoint_detaches_campaign_member(client):
    """The standalone DELETE /api/test-runs/{id} route detaches its campaign row."""
    site_resp = client.post(
        "/api/sites", json={"name": "S-direct", "base_url": "http://sd.local"}
    )
    site_id = site_resp.json()["id"]
    run_resp = client.post(f"/api/sites/{site_id}/test-runs", json={"name": "run"})
    run_id = run_resp.json()["id"]

    app_resp = client.post("/api/applications", json={"name": "AppDirect"})
    app_id = app_resp.json()["id"]
    target_resp = client.post(
        f"/api/applications/{app_id}/targets",
        json={"target_type": "site", "target_id": site_id},
    )
    target_id = target_resp.json()["id"]

    from aespa.db import get_engine
    from aespa.models import CampaignTargetMember

    with Session(get_engine()) as s:
        campaign = AssessmentCampaign(application_id=app_id, name="c")
        s.add(campaign)
        s.flush()
        s.add(
            CampaignTargetMember(
                campaign_id=campaign.id,
                target_id=target_id,
                target_type="site",
                test_run_id=run_id,
            )
        )
        s.commit()

    resp = client.delete(f"/api/test-runs/{run_id}")
    assert resp.status_code == 204


# ── Regression: verifying real terminal status before "completed" ──────────


@pytest.mark.anyio
async def test_dast_stage_marks_target_failed_when_scan_status_is_failed(
    isolated_db_engine, monkeypatch
):
    """The wait loop exiting only means the task is done — a scan that
    actually ended in TestRun.status == 'failed' must not be reported
    'completed'."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "awaiting_review"
        campaign.review_submitted_at = campaign.created_at
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    async def _fake_start_crawl(run_id: int) -> None:
        with Session(isolated_db_engine) as s:
            run = s.get(TestRun, run_id)
            run.phase = "crawled"
            run.status = "complete"
            s.add(run)
            s.commit()

    async def _fake_start_thinking_scan(run_id: int) -> None:
        # Simulate the scan finishing with a real failure status, even
        # though the task itself exits cleanly (no exception raised).
        with Session(isolated_db_engine) as s:
            run = s.get(TestRun, run_id)
            run.status = "failed"
            s.add(run)
            s.commit()

    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc

    monkeypatch.setattr(crawler_svc, "start_crawl", _fake_start_crawl)
    monkeypatch.setattr(crawler_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scanner_svc, "start_thinking_scan", _fake_start_thinking_scan)
    monkeypatch.setattr(scanner_svc, "is_thinking_running", lambda run_id: False)

    # This test exercises scan terminal-state handling. Supply one resolved
    # case so the readiness gate allows the mocked scanner to start.
    monkeypatch.setattr(
        campaigns_svc.validation_cases_svc,
        "resolve_cases_for_web_target",
        lambda *_args, **_kwargs: SimpleNamespace(counts={"resolved": 1}, warnings=[]),
    )
    monkeypatch.setattr(
        campaigns_svc.validation_cases_svc,
        "compile_runnable_cases",
        lambda *_args, **_kwargs: SimpleNamespace(copied_lead_ids=[1], warnings=[]),
    )

    await campaigns_svc.continue_to_live_testing(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        # The only target failed its dynamic scan — the campaign must not
        # falsely report "completed".
        assert campaign.status == "failed"
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).first()
        assert member.status == "failed"
        import json

        warnings = json.loads(campaign.warnings_json)
        assert any("did not finish successfully" in w for w in warnings)


@pytest.mark.anyio
async def test_dast_stage_is_incomplete_when_one_of_two_targets_fails(
    isolated_db_engine, monkeypatch
):
    """A successful target must not hide a failed sibling target."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        collection = None
        from aespa.models import ApiCollection

        collection = ApiCollection(name="Second API", base_url="http://api2.test")
        s.add(collection)
        s.flush()
        target2 = ApplicationTarget(
            application_id=ctx["application_id"],
            target_type="api_collection",
            target_id=collection.id,
        )
        s.add(target2)
        s.commit()

        payload = CampaignCreate(
            name="two-targets",
            source_members=[
                CampaignSourceMemberCreate(
                    component_id=ctx["component_id"],
                    snapshot_id=ctx["snapshot_id"],
                )
            ],
            target_members=[
                CampaignTargetMemberCreate(target_id=ctx["target_id"]),
                CampaignTargetMemberCreate(target_id=target2.id),
            ],
        )
        campaign = campaigns_svc.create_campaign(s, ctx["application_id"], payload)
        campaign.status = "awaiting_review"
        campaign.review_submitted_at = campaign.created_at
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    async def _fake_start_crawl(run_id: int) -> None:
        with Session(isolated_db_engine) as s:
            run = s.get(TestRun, run_id)
            run.phase = "crawled"
            run.status = "complete"
            s.add(run)
            s.commit()

    async def _fake_start_thinking_scan(run_id: int) -> None:
        with Session(isolated_db_engine) as s:
            run = s.get(TestRun, run_id)
            run.status = "complete"  # this target genuinely succeeds
            s.add(run)
            s.commit()

    async def _fake_start_api_scan(run_id: int) -> None:
        from aespa.models import ApiTestRun

        with Session(isolated_db_engine) as s:
            run = s.get(ApiTestRun, run_id)
            run.status = "failed"  # this target genuinely fails
            s.add(run)
            s.commit()

    from aespa.services import api_scanner as api_scanner_svc
    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc

    monkeypatch.setattr(crawler_svc, "start_crawl", _fake_start_crawl)
    monkeypatch.setattr(crawler_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scanner_svc, "start_thinking_scan", _fake_start_thinking_scan)
    monkeypatch.setattr(scanner_svc, "is_thinking_running", lambda run_id: False)
    monkeypatch.setattr(api_scanner_svc, "start_api_scan", _fake_start_api_scan)
    monkeypatch.setattr(api_scanner_svc, "is_api_scan_running", lambda run_id: False)
    monkeypatch.setattr(
        campaigns_svc.validation_cases_svc,
        "resolve_cases_for_web_target",
        lambda *_args, **_kwargs: SimpleNamespace(counts={"resolved": 1}, warnings=[]),
    )
    monkeypatch.setattr(
        campaigns_svc.validation_cases_svc,
        "resolve_cases_for_api_target",
        lambda *_args, **_kwargs: SimpleNamespace(counts={"resolved": 1}, warnings=[]),
    )
    monkeypatch.setattr(
        campaigns_svc.validation_cases_svc,
        "compile_runnable_cases",
        lambda *_args, **_kwargs: SimpleNamespace(copied_lead_ids=[1], warnings=[]),
    )

    await campaigns_svc.continue_to_live_testing(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "incomplete"
        members = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).all()
        statuses = sorted(m.status for m in members)
        assert statuses == ["completed", "failed"]


# ── Regression: retry resumes without duplicating children/leads ───────────


@pytest.mark.anyio
async def test_retry_campaign_resumes_sast_stage_without_duplicating_child(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id
        sast_run = SastRun(name="child", status="scanning")  # left mid-scan
        s.add(sast_run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        member.sast_run_id = sast_run.id
        member.status = "running"
        s.add(member)
        campaign.status = "sast_running"
        s.add(campaign)
        s.commit()
        sast_run_id = sast_run.id

    reconciled = campaigns_svc.reconcile_campaigns()
    assert campaign_id in reconciled
    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "interrupted"
        assert campaign.interrupted_stage == "sast_running"

    run_sast_scan_calls: list[int] = []

    async def _fake_run_sast_scan(run_id: int) -> None:
        run_sast_scan_calls.append(run_id)
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, run_id)
            run.status = "completed"
            s.add(run)
            s.commit()

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)

    await campaigns_svc.retry_campaign(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    # Resumed exactly the interrupted member, exactly once — no new SastRun.
    assert run_sast_scan_calls == [sast_run_id]
    with Session(isolated_db_engine) as s:
        members = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).all()
        assert len(members) == 1  # no duplicate child created
        assert members[0].sast_run_id == sast_run_id
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "awaiting_review"
        assert campaign.interrupted_stage is None


@pytest.mark.anyio
async def test_retry_campaign_skips_already_completed_members(
    isolated_db_engine, monkeypatch
):
    """A component whose scan already finished before the restart must not
    be rescanned on retry."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id
        sast_run = SastRun(name="child", status="completed")
        s.add(sast_run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        member.sast_run_id = sast_run.id
        member.status = "completed"  # already finished before the restart
        s.add(member)
        campaign.status = "interrupted"
        campaign.interrupted_stage = "correlating"
        s.add(campaign)
        s.commit()

    run_sast_scan_calls: list[int] = []

    async def _fake_run_sast_scan(run_id: int) -> None:
        run_sast_scan_calls.append(run_id)

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)

    await campaigns_svc.retry_campaign(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    assert run_sast_scan_calls == []  # never rerun — it already completed
    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "awaiting_review"


@pytest.mark.anyio
async def test_retry_campaign_resumes_dast_stage_without_recreating_child_run(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id
        run = TestRun(site_id=ctx["site_id"], name="web child")
        s.add(run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).first()
        member.test_run_id = run.id
        member.status = "running"
        s.add(member)
        campaign.status = "interrupted"
        campaign.interrupted_stage = "dast_running"
        campaign.review_submitted_at = campaign.created_at
        s.add(campaign)
        s.commit()
        existing_run_id = run.id

    start_crawl_calls: list[int] = []

    async def _fake_start_crawl(run_id: int) -> None:
        start_crawl_calls.append(run_id)
        with Session(isolated_db_engine) as s:
            r = s.get(TestRun, run_id)
            r.phase = "crawled"
            r.status = "complete"
            s.add(r)
            s.commit()

    async def _fake_start_thinking_scan(run_id: int) -> None:
        with Session(isolated_db_engine) as s:
            r = s.get(TestRun, run_id)
            r.status = "complete"
            s.add(r)
            s.commit()

    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc

    monkeypatch.setattr(crawler_svc, "start_crawl", _fake_start_crawl)
    monkeypatch.setattr(crawler_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scanner_svc, "start_thinking_scan", _fake_start_thinking_scan)
    monkeypatch.setattr(scanner_svc, "is_thinking_running", lambda run_id: False)

    await campaigns_svc.retry_campaign(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    assert start_crawl_calls == [existing_run_id]  # reused, not recreated
    with Session(isolated_db_engine) as s:
        members = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).all()
        assert len(members) == 1
        assert members[0].test_run_id == existing_run_id
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "completed"


def test_retry_campaign_rejected_when_not_interrupted(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id

    async def _run():
        with pytest.raises(campaigns_svc.InvalidCampaignState):
            await campaigns_svc.retry_campaign(campaign_id)

    asyncio.run(_run())


@pytest.mark.anyio
async def test_rebuild_context_matching_clears_all_generated_review_data(
    isolated_db_engine, monkeypatch, tmp_path
):
    archive = tmp_path / "ui.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("app.js", "fetch('/api/orders')")

    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        snapshot = s.get(ComponentSnapshot, ctx["snapshot_id"])
        snapshot.stored_path = str(archive)
        s.add(snapshot)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "awaiting_review"
        campaign.review_submitted_at = campaign.created_at
        s.add(campaign)
        s.flush()

        sast_run = SastRun(name="source", status="completed")
        s.add(sast_run)
        s.flush()
        source_member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign.id
            )
        ).one()
        source_member.sast_run_id = sast_run.id
        source_member.status = "completed"
        s.add(source_member)

        call = ComponentFact(
            sast_run_id=sast_run.id,
            component_id=ctx["component_id"],
            fact_type="http_call",
            method="POST",
            path="/api/orders",
            fingerprint="call",
        )
        route = ComponentFact(
            sast_run_id=sast_run.id,
            component_id=ctx["component_id"],
            fact_type="route",
            method="POST",
            path="/api/orders",
            fingerprint="route",
        )
        s.add(call)
        s.add(route)
        s.flush()
        s.add(
            ComponentConnection(
                campaign_id=campaign.id,
                source_component_id=ctx["component_id"],
                source_fact_id=call.id,
                target_component_id=ctx["component_id"],
                target_fact_id=route.id,
            )
        )

        original_lead = ScanLead(
            producer_run_type="sast",
            producer_run_id=sast_run.id,
            title="Original SAST lead",
        )
        generated_lead = ScanLead(
            producer_run_type="campaign",
            producer_run_id=campaign.id,
            source="campaign",
            title="Generated path lead",
        )
        s.add(original_lead)
        s.add(generated_lead)
        s.flush()
        s.add(
            ScanLeadComponentProvenance(
                scan_lead_id=generated_lead.id,
                component_id=ctx["component_id"],
                fact_id=call.id,
            )
        )
        mapping = LeadTargetMapping(
            campaign_id=campaign.id,
            lead_id=generated_lead.id,
            target_id=ctx["target_id"],
            target_type="site",
            status="approved",
            approved=True,
        )
        s.add(mapping)
        s.flush()
        target_member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign.id
            )
        ).one()
        target_member.status = "completed"
        target_member.status_message = "Old result"
        target_member.validation_summary_json = '{"confirmed": 1}'
        s.add(target_member)
        s.add(
            CampaignValidationCase(
                campaign_id=campaign.id,
                mapping_id=mapping.id,
                target_member_id=target_member.id,
                origin_lead_id=generated_lead.id,
            )
        )
        s.commit()
        campaign_id = campaign.id
        original_lead_id = original_lead.id

    refreshed = []
    monkeypatch.setattr(
        campaigns_svc,
        "_refresh_component_facts",
        lambda value: refreshed.append(value),
    )

    async def _fake_correlate(value, *, preserve_downstream):
        assert value == campaign_id
        assert preserve_downstream is False
        with Session(isolated_db_engine) as s:
            assert not s.exec(
                select(ComponentConnection).where(
                    ComponentConnection.campaign_id == campaign_id
                )
            ).all()
            assert not s.exec(
                select(LeadTargetMapping).where(
                    LeadTargetMapping.campaign_id == campaign_id
                )
            ).all()
            assert not s.exec(
                select(CampaignValidationCase).where(
                    CampaignValidationCase.campaign_id == campaign_id
                )
            ).all()
        return {"connections": 0, "cross_component_leads": 0, "lead_target_mappings": 0}

    monkeypatch.setattr(
        campaigns_svc.correlation_svc,
        "correlate_campaign_with_llm",
        _fake_correlate,
    )

    await campaigns_svc.rebuild_campaign_connections(campaign_id)

    assert refreshed == [campaign_id]
    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "awaiting_review"
        assert campaign.review_submitted_at is None
        assert json.loads(campaign.warnings_json) == []
        assert s.get(ScanLead, original_lead_id) is not None
        assert not s.exec(
            select(ScanLead).where(
                ScanLead.producer_run_type == "campaign",
                ScanLead.producer_run_id == campaign_id,
            )
        ).all()
        assert not s.exec(select(ScanLeadComponentProvenance)).all()
        target_member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).one()
        assert target_member.status == "pending"
        assert target_member.status_message is None
        assert target_member.validation_summary_json == "{}"


@pytest.mark.anyio
async def test_rebuild_context_matching_rejects_existing_live_child_run(
    isolated_db_engine,
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "completed"
        s.add(campaign)
        run = TestRun(site_id=ctx["site_id"], name="existing live scan")
        s.add(run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign.id
            )
        ).one()
        member.test_run_id = run.id
        s.add(member)
        s.commit()
        campaign_id = campaign.id

    with pytest.raises(campaigns_svc.InvalidCampaignState, match="live target scans"):
        await campaigns_svc.rebuild_campaign_connections(campaign_id)

    with Session(isolated_db_engine) as s:
        assert s.get(AssessmentCampaign, campaign_id).status == "completed"


def test_refresh_component_facts_uses_frozen_snapshot(isolated_db_engine, tmp_path):
    archive = tmp_path / "ui.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("src/client.js", "fetch('/api/orders', { method: 'POST' })")

    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        snapshot = s.get(ComponentSnapshot, ctx["snapshot_id"])
        snapshot.stored_path = str(archive)
        s.add(snapshot)
        campaign = _create_draft_campaign(s, ctx)
        run = SastRun(name="source", status="completed")
        s.add(run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign.id
            )
        ).one()
        member.sast_run_id = run.id
        member.status = "completed"
        s.add(member)
        s.add(
            ComponentFact(
                sast_run_id=run.id,
                component_id=ctx["component_id"],
                fact_type="http_call",
                path="/old",
                detail_json='{"origin": "llm_mapper"}',
                fingerprint="old-llm",
            )
        )
        s.commit()
        campaign_id = campaign.id
        run_id = run.id

    campaigns_svc._refresh_component_facts(campaign_id)

    with Session(isolated_db_engine) as s:
        facts = s.exec(
            select(ComponentFact).where(ComponentFact.sast_run_id == run_id)
        ).all()
        assert not any(fact.path == "/old" for fact in facts)
        assert any(
            fact.fact_type == "http_call" and fact.path == "/api/orders"
            for fact in facts
        )


# ── Regression: submit_review gating (finding 7) ────────────────────────────


def _seed_campaign_with_one_proposal(session) -> dict:
    """A minimal campaign already past correlation with exactly one
    lead-target proposal pending review."""
    from aespa.models import ApiCollection, ApiEndpoint, ScanLead

    ctx = _seed_application(session)
    collection = ApiCollection(name="Orders API", base_url="http://api.test")
    session.add(collection)
    session.flush()
    session.add(ApiEndpoint(collection_id=collection.id, method="POST", path="/orders"))
    target = ApplicationTarget(
        application_id=ctx["application_id"],
        target_type="api_collection",
        target_id=collection.id,
    )
    session.add(target)
    session.flush()
    ctx["target_id"] = target.id

    campaign = _create_draft_campaign(session, ctx)
    campaign.status = "awaiting_review"
    session.add(campaign)

    sast_run = SastRun(name="child", status="completed")
    session.add(sast_run)
    session.flush()
    member = session.exec(
        select(CampaignSourceMember).where(
            CampaignSourceMember.campaign_id == campaign.id
        )
    ).first()
    member.sast_run_id = sast_run.id
    member.status = "completed"
    session.add(member)

    lead = ScanLead(
        producer_run_id=sast_run.id,
        producer_run_type="sast",
        title="lead",
        location="a.py:1",
        suggested_endpoint="POST /orders",
        reportable=True,
    )
    session.add(lead)
    session.flush()
    session.commit()

    from aespa.services import correlation as correlation_svc

    correlation_svc.correlate_campaign(campaign.id)

    return {"campaign_id": campaign.id}


def test_submit_review_rejects_empty_when_proposals_pending(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_campaign_with_one_proposal(s)

    with pytest.raises(campaigns_svc.InvalidReviewDecision):
        campaigns_svc.submit_review(ctx["campaign_id"], [])


def test_submit_review_allows_empty_when_zero_proposals(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "awaiting_review"
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    result = campaigns_svc.submit_review(campaign_id, [])
    assert result == {"approved": 0, "rejected": 0}
    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.review_submitted_at is not None


def test_submit_review_stamps_gate_only_once_all_proposals_decided(
    isolated_db_engine,
):
    from aespa.models import LeadTargetMapping

    with Session(isolated_db_engine) as s:
        ctx = _seed_campaign_with_one_proposal(s)
        # Force a second, still-pending proposal so one decision is not
        # enough to close the gate.
        mapping = s.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == ctx["campaign_id"]
            )
        ).first()
        extra = LeadTargetMapping(
            campaign_id=ctx["campaign_id"],
            lead_id=mapping.lead_id,
            target_id=mapping.target_id + 10_000,
            target_type="api_collection",
            score=0.4,
        )
        # target_id has no real FK enforcement here (isolated_db_engine has
        # FK off), only used to keep the unique constraint from firing.
        s.add(extra)
        s.commit()
        first_mapping_id = mapping.id
        second_mapping_id = extra.id

    result = campaigns_svc.submit_review(ctx["campaign_id"], [(first_mapping_id, True)])
    assert result["approved"] == 1
    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, ctx["campaign_id"])
        assert campaign.review_submitted_at is None  # one proposal still pending

    campaigns_svc.submit_review(ctx["campaign_id"], [(second_mapping_id, False)])
    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, ctx["campaign_id"])
        assert campaign.review_submitted_at is not None  # now everything is decided


def test_submit_review_rejects_unknown_mapping_as_400_equivalent(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_campaign_with_one_proposal(s)

    with pytest.raises(campaigns_svc.InvalidReviewDecision):
        campaigns_svc.submit_review(ctx["campaign_id"], [(999999, True)])


# ── Regression: members must not stay "running" after stop completes ───────


@pytest.mark.anyio
async def test_stop_campaign_normalizes_running_sast_member_to_terminal_status(
    isolated_db_engine, monkeypatch
):
    """A CampaignSourceMember must never be left ``running`` once
    ``stop_campaign`` returns — the per-member coroutine's own stop-requested
    check can return before it records any terminal status itself, so
    ``stop_campaign`` has to normalize it after every child barrier settles.
    """
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id

    started = asyncio.Event()

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        started.set()
        # Simulate a real scanner: it keeps running until cancelled, and its
        # own cancellation handler does not touch CampaignSourceMember rows
        # at all (that is campaigns.py's job, not the scanner's).
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)
    monkeypatch.setattr(sast_scanner_svc, "is_sast_scan_running", lambda rid: True)

    async def _fake_stop_sast_scan_and_wait(
        sast_run_id: int, timeout: float = 5.0
    ) -> bool:
        await asyncio.sleep(0.05)
        return True

    monkeypatch.setattr(
        sast_scanner_svc, "stop_sast_scan_and_wait", _fake_stop_sast_scan_and_wait
    )

    await campaigns_svc.start_campaign(campaign_id)
    await asyncio.wait_for(started.wait(), timeout=2.0)

    with Session(isolated_db_engine) as s:
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        assert member.status == "running"  # sanity check before stopping

    await campaigns_svc.stop_campaign(campaign_id)

    with Session(isolated_db_engine) as s:
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).first()
        assert member.status != "running"
        assert member.status == "skipped"


@pytest.mark.anyio
async def test_stop_campaign_normalizes_running_web_target_member_to_terminal_status(
    isolated_db_engine, monkeypatch
):
    """Same guarantee for a CampaignTargetMember mid-crawl/scan when a DAST
    stage is stopped."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign.status = "awaiting_review"
        campaign.review_submitted_at = campaign.created_at
        s.add(campaign)
        s.commit()
        campaign_id = campaign.id

    crawl_started = asyncio.Event()

    async def _fake_start_crawl(run_id: int) -> None:
        crawl_started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    from aespa.services import crawler as crawler_svc

    monkeypatch.setattr(crawler_svc, "start_crawl", _fake_start_crawl)
    monkeypatch.setattr(crawler_svc, "is_running", lambda run_id: True)

    async def _fake_stop_and_wait(run_id: int, timeout: float = 5.0) -> bool:
        await asyncio.sleep(0.05)
        return True

    monkeypatch.setattr(crawler_svc, "stop_and_wait", _fake_stop_and_wait)

    await campaigns_svc.continue_to_live_testing(campaign_id)
    await asyncio.wait_for(crawl_started.wait(), timeout=2.0)

    with Session(isolated_db_engine) as s:
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).first()
        assert member.status == "running"  # sanity check before stopping

    await campaigns_svc.stop_campaign(campaign_id)

    with Session(isolated_db_engine) as s:
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).first()
        assert member.status != "running"
        assert member.status == "skipped"
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "stopped"


@pytest.mark.anyio
async def test_resume_campaign_continues_after_explicit_stop(
    isolated_db_engine, monkeypatch
):
    """A stopped campaign resumes the same stage and reuses its child run."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id

    started = asyncio.Event()
    scan_calls: list[int] = []

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        scan_calls.append(sast_run_id)
        started.set()
        if len(scan_calls) == 1:
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                with Session(isolated_db_engine) as s:
                    run = s.get(SastRun, sast_run_id)
                    run.status = "cancelled"
                    s.add(run)
                    s.commit()
                return
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, sast_run_id)
            run.status = "completed"
            s.add(run)
            s.commit()

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)
    monkeypatch.setattr(sast_scanner_svc, "is_sast_scan_running", lambda rid: True)

    async def _fake_stop_sast_scan_and_wait(
        sast_run_id: int, timeout: float = 5.0
    ) -> bool:
        await asyncio.sleep(0.05)
        return True

    monkeypatch.setattr(
        sast_scanner_svc, "stop_sast_scan_and_wait", _fake_stop_sast_scan_and_wait
    )

    await campaigns_svc.start_campaign(campaign_id)
    await asyncio.wait_for(started.wait(), timeout=2.0)
    with Session(isolated_db_engine) as s:
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).one()
        child_run_id = member.sast_run_id
    await campaigns_svc.stop_campaign(campaign_id)

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        assert campaign.status == "stopped"
        assert campaign.interrupted_stage == "sast_running"
        assert "did not finish successfully" not in campaign.warnings_json

    await campaigns_svc.resume_campaign(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).one()
        assert campaign.status == "awaiting_review"
        assert campaign.interrupted_stage is None
        assert member.sast_run_id == child_run_id
    assert scan_calls == [child_run_id, child_run_id]


@pytest.mark.anyio
async def test_resume_repairs_cancelled_source_from_older_stopped_campaign(
    isolated_db_engine, monkeypatch
):
    """Older stopped rows can carry a stale failed member and warning."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_application(s)
        campaign = _create_draft_campaign(s, ctx)
        campaign_id = campaign.id
        run = SastRun(name="cancelled child", status="cancelled")
        s.add(run)
        s.flush()
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).one()
        member.sast_run_id = run.id
        member.status = "failed"
        campaign.status = "awaiting_review"
        campaign.warnings_json = json.dumps(
            [
                "A source-code scan did not finish successfully — matches "
                "involving that component may be incomplete."
            ]
        )
        s.add(member)
        s.add(campaign)
        s.commit()
        child_run_id = run.id

    calls: list[int] = []

    async def _fake_run_sast_scan(sast_run_id: int) -> None:
        calls.append(sast_run_id)
        with Session(isolated_db_engine) as s:
            run = s.get(SastRun, sast_run_id)
            run.status = "completed"
            s.add(run)
            s.commit()

    from aespa.services import sast_scanner as sast_scanner_svc

    monkeypatch.setattr(sast_scanner_svc, "run_sast_scan", _fake_run_sast_scan)

    await campaigns_svc.resume_campaign(campaign_id)
    await campaigns_svc._campaign_tasks[campaign_id]

    with Session(isolated_db_engine) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        member = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).one()
        assert campaign.status == "awaiting_review"
        assert json.loads(campaign.warnings_json) == []
        assert member.status == "completed"
        assert member.sast_run_id == child_run_id
    assert calls == [child_run_id]
