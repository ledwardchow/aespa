"""Campaign CRUD + the durable multi-repository scan orchestrator.

A campaign coordinates ordinary child ``SastRun``/``TestRun``/``ApiTestRun``
scans for one ``Application`` through:

    draft -> sast_running -> correlating -> awaiting_review -> dast_running
    -> completed | failed | stopped

It never re-implements crawling, dynamic scanning, or SAST analysis — it only
creates the child rows, starts/awaits the existing entry points
(``sast_scanner.run_sast_scan``, ``crawler.start_crawl``,
``scanner.start_thinking_scan``, ``api_scanner.start_api_scan``), and applies
bounded concurrency + sequencing rules on top.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    ApiCollection,
    ApiTestRun,
    ApplicationComponent,
    ApplicationTarget,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentSnapshot,
    SastRun,
    Site,
    TestRun,
)
from aespa.schemas import CampaignCreate
from aespa.services import applications as applications_svc
from aespa.services import correlation as correlation_svc
from aespa.services import events as events_svc

log = logging.getLogger(__name__)

_UTC = timezone.utc

# Background orchestrator tasks + cooperative stop flags, keyed by campaign_id
# — mirrors the pattern used by crawler.py / scanner.py / sast_scanner.py.
_campaign_tasks: dict[int, asyncio.Task] = {}
_campaign_stop_requested: set[int] = set()

_ACTIVE_STATUSES = ("sast_running", "correlating", "dast_running")


class CampaignServiceError(Exception):
    """Base class for service-layer errors."""


class CampaignNotFound(CampaignServiceError):
    pass


class InvalidCampaignState(CampaignServiceError):
    pass


class InvalidReviewDecision(CampaignServiceError):
    """Raised for a malformed review submission: an unknown/foreign mapping
    id, or an empty submission while proposals are still pending."""


def _utcnow() -> datetime:
    return datetime.now(_UTC)


# ── CRUD ──────────────────────────────────────────────────────────────────────


def list_campaigns(session: Session, application_id: int) -> list[AssessmentCampaign]:
    applications_svc.get_application(session, application_id)
    return list(
        session.exec(
            select(AssessmentCampaign)
            .where(AssessmentCampaign.application_id == application_id)
            .order_by(AssessmentCampaign.id.desc())  # type: ignore[attr-defined]
        ).all()
    )


def get_campaign(
    session: Session, application_id: int, campaign_id: int
) -> AssessmentCampaign:
    campaign = session.get(AssessmentCampaign, campaign_id)
    if campaign is None or campaign.application_id != application_id:
        raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
    return campaign


def create_campaign(
    session: Session, application_id: int, payload: CampaignCreate
) -> AssessmentCampaign:
    """Validate and freeze one campaign's component snapshots + live targets.

    Every referenced component/snapshot/target must belong to this exact
    Application — an id from another application is rejected outright.
    """
    applications_svc.get_application(session, application_id)

    seen_components: set[int] = set()
    for source in payload.source_members:
        if source.component_id in seen_components:
            raise InvalidCampaignState(
                "Each component can only be selected once per campaign"
            )
        seen_components.add(source.component_id)
        component = session.get(ApplicationComponent, source.component_id)
        if component is None or component.application_id != application_id:
            raise applications_svc.CrossApplicationReference(
                f"Component id={source.component_id} does not belong to this application"
            )
        snapshot = session.get(ComponentSnapshot, source.snapshot_id)
        if snapshot is None or snapshot.component_id != source.component_id:
            raise applications_svc.CrossApplicationReference(
                f"Snapshot id={source.snapshot_id} does not belong to component "
                f"id={source.component_id}"
            )

    seen_targets: set[int] = set()
    for target_ref in payload.target_members:
        if target_ref.target_id in seen_targets:
            raise InvalidCampaignState(
                "Each target can only be selected once per campaign"
            )
        seen_targets.add(target_ref.target_id)
        target = session.get(ApplicationTarget, target_ref.target_id)
        if target is None or target.application_id != application_id:
            raise applications_svc.CrossApplicationReference(
                f"Target id={target_ref.target_id} does not belong to this application"
            )

    if payload.llm_config_id is not None:
        from aespa.models import LLMConfig

        if session.get(LLMConfig, payload.llm_config_id) is None:
            raise InvalidCampaignState("LLM model not found")
    if payload.llm_profile_id is not None:
        from aespa.models import LLMProfile

        if session.get(LLMProfile, payload.llm_profile_id) is None:
            raise InvalidCampaignState("Scan profile not found")

    campaign = AssessmentCampaign(
        application_id=application_id,
        name=payload.name,
        status="draft",
        max_parallel_sast=payload.max_parallel_sast,
        llm_config_id=payload.llm_config_id,
        llm_profile_id=payload.llm_profile_id,
    )
    session.add(campaign)
    session.flush()

    for source in payload.source_members:
        session.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=source.component_id,
                snapshot_id=source.snapshot_id,
            )
        )
    for target_ref in payload.target_members:
        target = session.get(ApplicationTarget, target_ref.target_id)
        session.add(
            CampaignTargetMember(
                campaign_id=campaign.id,
                target_id=target_ref.target_id,
                target_type=target.target_type,
            )
        )
    session.commit()
    session.refresh(campaign)
    return campaign


def delete_campaign(session: Session, application_id: int, campaign_id: int) -> None:
    campaign = get_campaign(session, application_id, campaign_id)
    if is_campaign_running(campaign_id) or campaign.status in _ACTIVE_STATUSES:
        raise InvalidCampaignState("Stop the campaign before deleting it")
    from aespa.services import run_cleanup

    run_cleanup.cascade_delete_campaign(session, campaign_id)
    session.commit()


def is_campaign_running(campaign_id: int) -> bool:
    task = _campaign_tasks.get(campaign_id)
    return task is not None and not task.done()


def get_campaign_progress(session: Session, campaign_id: int) -> dict:
    campaign = session.get(AssessmentCampaign, campaign_id)
    if campaign is None:
        raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
    source_members = list(
        session.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).all()
    )
    target_members = list(
        session.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).all()
    )
    try:
        warnings = json.loads(campaign.warnings_json or "[]")
    except (TypeError, ValueError):
        warnings = []
    return {
        "status": campaign.status,
        "warnings": warnings,
        "source_members": source_members,
        "target_members": target_members,
    }


# ── Internal state helpers ────────────────────────────────────────────────────


def _set_campaign_status(campaign_id: int, status: str) -> None:
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is not None:
            campaign.status = status
            campaign.updated_at = _utcnow()
            s.add(campaign)
            s.commit()


def _append_campaign_warnings(campaign_id: int, warnings: list[str]) -> None:
    if not warnings:
        return
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            return
        try:
            existing = json.loads(campaign.warnings_json or "[]")
        except (TypeError, ValueError):
            existing = []
        existing.extend(warnings)
        campaign.warnings_json = json.dumps(existing)
        campaign.updated_at = _utcnow()
        s.add(campaign)
        s.commit()


def _finish_campaign(
    campaign_id: int, status: str, *, error: str | None = None
) -> None:
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            return
        campaign.status = status
        campaign.completed_at = _utcnow()
        campaign.updated_at = _utcnow()
        if error:
            campaign.error_message = error
        s.add(campaign)
        s.commit()
    events_svc.emit(
        campaign_id,
        {
            "type": "agent_status",
            "agent_id": "campaign",
            "role": "Campaign Orchestrator",
            "status": "complete" if status == "completed" else status,
            "current_task": f"Campaign {status}",
            "outcome": error,
            "_persist": True,
        },
    )


def _update_source_member_status(member_id: int, status: str) -> None:
    with Session(get_engine()) as s:
        member = s.get(CampaignSourceMember, member_id)
        if member is not None:
            member.status = status
            member.updated_at = _utcnow()
            s.add(member)
            s.commit()


def _update_target_member_status(member_id: int, status: str) -> None:
    with Session(get_engine()) as s:
        member = s.get(CampaignTargetMember, member_id)
        if member is not None:
            member.status = status
            member.updated_at = _utcnow()
            s.add(member)
            s.commit()


def _normalize_running_members_after_stop(campaign_id: int) -> None:
    """Force any member still ``running`` to a terminal state.

    Call only after every child shutdown barrier this coroutine knows how to
    wait for has already completed. A member can still read ``running`` at
    that point because its own per-member coroutine's stop-requested check
    (inside a polling loop, or a bare ``asyncio.CancelledError`` re-raise)
    returns/unwinds without itself recording a terminal status — this makes
    sure a stopped campaign never leaves a member claiming to still be in
    progress, which would otherwise both mislead the UI and make the
    campaign resemble one still safe to auto-complete.
    """
    with Session(get_engine()) as s:
        for member in s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id,
                CampaignSourceMember.status == "running",
            )
        ).all():
            member.status = "skipped"
            member.updated_at = _utcnow()
            s.add(member)
        for member in s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id,
                CampaignTargetMember.status == "running",
            )
        ).all():
            member.status = "skipped"
            member.updated_at = _utcnow()
            s.add(member)
        s.commit()


# ── Start / stop ──────────────────────────────────────────────────────────────


async def start_campaign(campaign_id: int) -> None:
    """Create the frozen SAST child manifest and start the SAST stage."""
    if is_campaign_running(campaign_id):
        return
    with events_svc.run_kind_scope("campaign"):
        with Session(get_engine()) as s:
            campaign = s.get(AssessmentCampaign, campaign_id)
            if campaign is None:
                raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
            if campaign.status != "draft":
                raise InvalidCampaignState(
                    f"Cannot start a campaign with status '{campaign.status}'"
                )
            campaign.status = "sast_running"
            campaign.started_at = _utcnow()
            campaign.completed_at = None
            campaign.error_message = None
            campaign.warnings_json = "[]"
            campaign.updated_at = _utcnow()
            s.add(campaign)

            members = s.exec(
                select(CampaignSourceMember).where(
                    CampaignSourceMember.campaign_id == campaign_id
                )
            ).all()
            for member in members:
                if member.sast_run_id is not None:
                    continue  # already created by a previous start attempt
                snapshot = s.get(ComponentSnapshot, member.snapshot_id)
                component = s.get(ApplicationComponent, member.component_id)
                run = SastRun(
                    name=f"{component.name} — {campaign.name}",
                    source_archive_path=snapshot.stored_path,
                    source_filename=snapshot.filename,
                    llm_config_id=campaign.llm_config_id,
                    llm_profile_id=campaign.llm_profile_id,
                    triggered_by_run_type="campaign",
                    triggered_by_run_id=campaign_id,
                    status="pending",
                )
                s.add(run)
                s.flush()
                member.sast_run_id = run.id
                member.status = "pending"
                s.add(member)
            s.commit()

        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": "campaign",
                "role": "Campaign Orchestrator",
                "status": "active",
                "current_task": "Starting source-code scans…",
                "outcome": None,
                "_persist": True,
            },
        )
        task = asyncio.create_task(
            _run_campaign(campaign_id), name=f"campaign-{campaign_id}"
        )
    _campaign_tasks[campaign_id] = task


async def _run_campaign(campaign_id: int) -> None:
    try:
        await _run_sast_stage(campaign_id)
        if campaign_id in _campaign_stop_requested:
            _finish_campaign(campaign_id, "stopped")
            return
        _set_campaign_status(campaign_id, "correlating")
        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": "campaign",
                "role": "Campaign Orchestrator",
                "status": "active",
                "current_task": "Matching context across components…",
                "outcome": None,
                "_persist": True,
            },
        )
        correlation_svc.correlate_campaign(campaign_id)
        if campaign_id in _campaign_stop_requested:
            _finish_campaign(campaign_id, "stopped")
            return
        _set_campaign_status(campaign_id, "awaiting_review")
        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": "campaign",
                "role": "Campaign Orchestrator",
                "status": "idle",
                "current_task": "Awaiting lead-target review",
                "outcome": None,
                "_persist": True,
            },
        )
    except asyncio.CancelledError:
        _finish_campaign(campaign_id, "stopped")
        raise
    except Exception as exc:
        log.exception("Campaign %s failed during SAST/correlation", campaign_id)
        _finish_campaign(campaign_id, "failed", error=str(exc))
    finally:
        _campaign_stop_requested.discard(campaign_id)


async def _run_sast_stage(campaign_id: int) -> None:
    from aespa.services import sast_scanner as sast_scanner_svc

    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        max_parallel = campaign.max_parallel_sast if campaign else 2
        members = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).all()
        member_refs = [
            (m.id, m.sast_run_id) for m in members if m.sast_run_id is not None
        ]

    semaphore = asyncio.Semaphore(max(1, max_parallel))
    warnings: list[str] = []

    async def _run_one(member_id: int, sast_run_id: int) -> None:
        async with semaphore:
            if campaign_id in _campaign_stop_requested:
                _update_source_member_status(member_id, "skipped")
                return
            with Session(get_engine()) as s:
                member = s.get(CampaignSourceMember, member_id)
                already_terminal = member is not None and member.status in (
                    "completed",
                    "failed",
                )
            if already_terminal:
                # A retry after a restart resumes only the members that were
                # genuinely in flight when the process stopped — one already
                # finished (successfully or not) is never rerun or duplicated.
                return
            _update_source_member_status(member_id, "running")
            try:
                await sast_scanner_svc.run_sast_scan(sast_run_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — isolate one child's failure
                warnings.append(f"A source-code scan failed to run: {exc}")
                _update_source_member_status(member_id, "failed")
                return
            with Session(get_engine()) as s:
                run = s.get(SastRun, sast_run_id)
                completed = run is not None and run.status == "completed"
            _update_source_member_status(
                member_id, "completed" if completed else "failed"
            )
            if not completed:
                warnings.append(
                    "A source-code scan did not finish successfully — matches "
                    "involving that component may be incomplete."
                )

    await asyncio.gather(
        *(_run_one(member_id, run_id) for member_id, run_id in member_refs)
    )
    _append_campaign_warnings(campaign_id, warnings)


async def stop_campaign(campaign_id: int) -> bool:
    """Cancel the orchestrator and propagate the stop to every active child.

    Awaits each child's own ``stop_*_and_wait`` barrier (not just a fire-and-
    forget stop request) and then awaits the orchestrator task itself with a
    bounded timeout, so that by the time this coroutine returns, the campaign
    is genuinely persisted ``stopped`` — never left mid-shutdown claiming an
    active stage, and immediately safe for ``delete_campaign`` to cascade.
    """
    from aespa.services import api_scanner as api_scanner_svc
    from aespa.services import crawler as crawler_svc
    from aespa.services import sast_scanner as sast_scanner_svc
    from aespa.services import scanner as scanner_svc

    _campaign_stop_requested.add(campaign_id)

    with Session(get_engine()) as s:
        source_members = s.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).all()
        target_members = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).all()

    for member in source_members:
        if member.sast_run_id and sast_scanner_svc.is_sast_scan_running(
            member.sast_run_id
        ):
            await sast_scanner_svc.stop_sast_scan_and_wait(member.sast_run_id)
    for member in target_members:
        if member.test_run_id and crawler_svc.is_running(member.test_run_id):
            await crawler_svc.stop_and_wait(member.test_run_id)
        if member.test_run_id and scanner_svc.is_thinking_running(member.test_run_id):
            await scanner_svc.stop_thinking_and_wait(member.test_run_id)
        if member.api_test_run_id and api_scanner_svc.is_api_scan_running(
            member.api_test_run_id
        ):
            await api_scanner_svc.stop_api_scan_and_wait(member.api_test_run_id)

    task = _campaign_tasks.get(campaign_id)
    if task is not None and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), timeout=10.0)
        # Every child barrier above already waited for its own cleanup; the
        # orchestrator's CancelledError handler persists "stopped" as part of
        # unwinding. If it hasn't (e.g. the bounded wait above timed out),
        # force the terminal status now rather than leave the campaign
        # claiming an active stage after this coroutine has returned.
        with Session(get_engine()) as s:
            campaign = s.get(AssessmentCampaign, campaign_id)
            still_active = campaign is not None and campaign.status in _ACTIVE_STATUSES
        if still_active:
            _finish_campaign(campaign_id, "stopped")
    else:
        _finish_campaign(campaign_id, "stopped")
    _normalize_running_members_after_stop(campaign_id)
    return True


# ── Review gate + DAST stage ─────────────────────────────────────────────────


def submit_review(campaign_id: int, decisions: list[tuple[int, bool]]) -> dict:
    """Apply lead-target review decisions and, once nothing is left pending,
    stamp ``review_submitted_at`` so live testing can start.

    An empty ``decisions`` list is only accepted when the campaign genuinely
    has zero proposed mappings — submitting an empty review while proposals
    are still pending is rejected rather than silently accepted as a no-op.
    The gate is stamped only once every proposed mapping (across this and any
    earlier submission) has an approved/rejected decision, so a partial
    review can be submitted more than once before live testing unlocks.
    """
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
        if campaign.status != "awaiting_review":
            raise InvalidCampaignState(
                f"Cannot review a campaign with status '{campaign.status}'"
            )

    pending_before = correlation_svc.count_pending_mappings(campaign_id)
    if not decisions and pending_before > 0:
        raise InvalidReviewDecision(
            f"This campaign has {pending_before} pending lead-target "
            "proposal(s) — submit a decision for each, or wait until it has "
            "zero proposals to submit an empty review."
        )

    try:
        result = correlation_svc.apply_review_decisions(campaign_id, decisions)
    except correlation_svc.UnknownMappingError as exc:
        raise InvalidReviewDecision(str(exc)) from exc

    pending_after = correlation_svc.count_pending_mappings(campaign_id)
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if pending_after == 0 and campaign.review_submitted_at is None:
            campaign.review_submitted_at = _utcnow()
        campaign.updated_at = _utcnow()
        s.add(campaign)
        s.commit()
    return result


async def continue_to_live_testing(campaign_id: int) -> None:
    """Start the DAST stage. Gated on review having been submitted."""
    if is_campaign_running(campaign_id):
        return
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
        if campaign.status != "awaiting_review":
            raise InvalidCampaignState(
                f"Cannot start live testing from status '{campaign.status}'"
            )
        if campaign.review_submitted_at is None:
            raise InvalidCampaignState(
                "Submit the lead-target review before starting live testing"
            )
        campaign.status = "dast_running"
        campaign.updated_at = _utcnow()
        s.add(campaign)
        s.commit()

    with events_svc.run_kind_scope("campaign"):
        task = asyncio.create_task(
            _run_dast_wrapper(campaign_id), name=f"campaign-dast-{campaign_id}"
        )
    _campaign_tasks[campaign_id] = task


async def _run_dast_wrapper(campaign_id: int) -> None:
    try:
        any_target_completed = await _run_dast_stage(campaign_id)
        if campaign_id in _campaign_stop_requested:
            _finish_campaign(campaign_id, "stopped")
        elif any_target_completed:
            _finish_campaign(campaign_id, "completed")
        else:
            # Every live target failed its dynamic scan (or none existed) —
            # reporting "completed" here would be a false success.
            _finish_campaign(
                campaign_id,
                "failed",
                error="No live target completed its dynamic scan.",
            )
    except asyncio.CancelledError:
        _finish_campaign(campaign_id, "stopped")
        raise
    except Exception as exc:
        log.exception("Campaign %s failed during live testing", campaign_id)
        _finish_campaign(campaign_id, "failed", error=str(exc))
    finally:
        _campaign_stop_requested.discard(campaign_id)


async def _run_dast_stage(campaign_id: int) -> bool:
    """Run every campaign target's dynamic scan.

    Returns ``True`` if at least one target's dynamic scan actually reached a
    successful terminal state — the caller uses this to decide whether the
    campaign may report "completed" rather than "failed".
    """
    from aespa.services import api_scanner as api_scanner_svc
    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc

    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        members = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == campaign_id
            )
        ).all()
        prepared: list[tuple[int, str, int, int | None, int | None]] = []
        for member in members:
            target = s.get(ApplicationTarget, member.target_id)
            if target is None:
                continue
            if target.target_type == "site":
                if member.test_run_id is None:
                    site = s.get(Site, target.target_id)
                    run = TestRun(
                        site_id=target.target_id,
                        name=f"{site.name} — {campaign.name}",
                        llm_config_id=campaign.llm_config_id,
                        llm_profile_id=campaign.llm_profile_id,
                    )
                    s.add(run)
                    s.flush()
                    member.test_run_id = run.id
                    s.add(member)
            else:
                if member.api_test_run_id is None:
                    collection = s.get(ApiCollection, target.target_id)
                    run = ApiTestRun(
                        collection_id=target.target_id,
                        name=f"{collection.name} — {campaign.name}",
                        llm_config_id=campaign.llm_config_id,
                        llm_profile_id=campaign.llm_profile_id,
                    )
                    s.add(run)
                    s.flush()
                    member.api_test_run_id = run.id
                    s.add(member)
            prepared.append(
                (
                    member.id,
                    target.target_type,
                    target.id,
                    member.test_run_id,
                    member.api_test_run_id,
                )
            )
        s.commit()

    warnings: list[str] = []
    completed_flags: dict[int, bool] = {}

    async def _run_target(
        member_id: int,
        target_type: str,
        target_id: int,
        test_run_id: int | None,
        api_test_run_id: int | None,
    ) -> None:
        if campaign_id in _campaign_stop_requested:
            _update_target_member_status(member_id, "skipped")
            return
        with Session(get_engine()) as s:
            member = s.get(CampaignTargetMember, member_id)
            already_terminal = member is not None and member.status in (
                "completed",
                "failed",
            )
        if already_terminal:
            # Retry resumes only targets still in flight at interruption —
            # an already-finished target is never rerun or duplicated.
            completed_flags[member_id] = member.status == "completed"
            return
        _update_target_member_status(member_id, "running")
        try:
            if target_type == "site":
                await crawler_svc.start_crawl(test_run_id)
                while crawler_svc.is_running(test_run_id):
                    if campaign_id in _campaign_stop_requested:
                        return
                    await asyncio.sleep(1.0)
                with Session(get_engine()) as s:
                    run = s.get(TestRun, test_run_id)
                    crawl_ok = run is not None and run.phase == "crawled"
                if not crawl_ok:
                    warnings.append(
                        "A web target's crawl did not finish — its dynamic "
                        "scan was skipped."
                    )
                    _update_target_member_status(member_id, "failed")
                    return
                correlation_svc.copy_approved_mappings_for_target(
                    campaign_id, target_id, "web", test_run_id
                )
                await scanner_svc.start_thinking_scan(test_run_id)
                while scanner_svc.is_thinking_running(test_run_id):
                    if campaign_id in _campaign_stop_requested:
                        return
                    await asyncio.sleep(1.0)
                # Reload the run and require its own terminal success status
                # before reporting this member "completed" — the wait loop
                # only tells us the task exited, not that it finished well.
                with Session(get_engine()) as s:
                    run = s.get(TestRun, test_run_id)
                    scan_ok = run is not None and run.status == "complete"
                if scan_ok:
                    _update_target_member_status(member_id, "completed")
                    completed_flags[member_id] = True
                else:
                    warnings.append(
                        "A web target's dynamic scan did not finish "
                        "successfully — its results may be incomplete."
                    )
                    _update_target_member_status(member_id, "failed")
            else:
                correlation_svc.copy_approved_mappings_for_target(
                    campaign_id, target_id, "api", api_test_run_id
                )
                await api_scanner_svc.start_api_scan(api_test_run_id)
                while api_scanner_svc.is_api_scan_running(api_test_run_id):
                    if campaign_id in _campaign_stop_requested:
                        return
                    await asyncio.sleep(1.0)
                # Same terminal-status check for the API scan.
                with Session(get_engine()) as s:
                    run = s.get(ApiTestRun, api_test_run_id)
                    scan_ok = run is not None and run.status == "completed"
                if scan_ok:
                    _update_target_member_status(member_id, "completed")
                    completed_flags[member_id] = True
                else:
                    warnings.append(
                        "An API target's dynamic scan did not finish "
                        "successfully — its results may be incomplete."
                    )
                    _update_target_member_status(member_id, "failed")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — isolate one target's failure
            warnings.append(f"A live-target scan failed: {exc}")
            _update_target_member_status(member_id, "failed")

    await asyncio.gather(*(_run_target(*ref) for ref in prepared))
    _append_campaign_warnings(campaign_id, warnings)
    return any(completed_flags.values())


# ── Restart reconciliation + retry ────────────────────────────────────────────


def reconcile_campaigns() -> list[int]:
    """Best-effort reconciliation for campaigns interrupted by a restart.

    A campaign whose status is still an active stage right after process
    startup cannot have a live orchestrator task (in-memory registries start
    empty), so it was interrupted. Its already-collected results (leads,
    facts, findings) are preserved. Rather than a dead-end ``failed`` status,
    the campaign is moved to ``interrupted`` with ``interrupted_stage`` set to
    the exact stage it was in — ``retry_campaign`` uses that to resume the
    same stage's runner without recreating any child run or duplicating any
    lead. Any member left ``running`` at the moment of interruption is reset
    to ``pending`` so retry re-attempts exactly it (and only it); a member
    that had already reached ``completed``/``failed`` is left untouched.
    """
    reconciled: list[int] = []
    with Session(get_engine()) as s:
        campaigns = s.exec(
            select(AssessmentCampaign).where(
                AssessmentCampaign.status.in_(_ACTIVE_STATUSES)  # type: ignore[attr-defined]
            )
        ).all()
        for campaign in campaigns:
            try:
                warnings = json.loads(campaign.warnings_json or "[]")
            except (TypeError, ValueError):
                warnings = []
            warnings.append(
                "The application restarted while this stage was running. "
                "Results already collected are kept — retry to resume."
            )
            campaign.warnings_json = json.dumps(warnings)
            campaign.interrupted_stage = campaign.status
            campaign.status = "interrupted"
            campaign.error_message = (
                "Interrupted by a server restart. Retry to resume without "
                "duplicating results."
            )
            campaign.updated_at = _utcnow()
            s.add(campaign)
            for member in s.exec(
                select(CampaignSourceMember).where(
                    CampaignSourceMember.campaign_id == campaign.id
                )
            ).all():
                if member.status == "running":
                    member.status = "pending"
                    s.add(member)
            for member in s.exec(
                select(CampaignTargetMember).where(
                    CampaignTargetMember.campaign_id == campaign.id
                )
            ).all():
                if member.status == "running":
                    member.status = "pending"
                    s.add(member)
            reconciled.append(campaign.id)
        s.commit()
    return reconciled


async def retry_campaign(campaign_id: int) -> None:
    """Resume a campaign interrupted by a restart from its recorded stage.

    Reuses every existing child run/lead — ``start_campaign``-created
    ``SastRun`` rows and ``_run_dast_stage``-created ``TestRun``/
    ``ApiTestRun`` rows are only ever created once (member ids stay set), and
    the terminal-status skip in ``_run_sast_stage``/``_run_dast_stage`` means
    an already-finished member is never rerun, so retrying never duplicates a
    child run or a lead.
    """
    if is_campaign_running(campaign_id):
        return
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
        if campaign.status != "interrupted":
            raise InvalidCampaignState(
                f"Cannot retry a campaign with status '{campaign.status}'"
            )
        stage = campaign.interrupted_stage or "sast_running"
        campaign.status = stage
        campaign.interrupted_stage = None
        campaign.error_message = None
        campaign.updated_at = _utcnow()
        s.add(campaign)
        s.commit()

    with events_svc.run_kind_scope("campaign"):
        if stage == "dast_running":
            task = asyncio.create_task(
                _run_dast_wrapper(campaign_id), name=f"campaign-dast-{campaign_id}"
            )
        else:
            # "sast_running" or "correlating" both resume through the same
            # SAST -> correlate -> review pipeline; members already completed
            # are skipped, so this is cheap when only correlation itself was
            # interrupted.
            task = asyncio.create_task(
                _run_campaign(campaign_id), name=f"campaign-{campaign_id}"
            )
    _campaign_tasks[campaign_id] = task
