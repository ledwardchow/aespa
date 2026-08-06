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
from urllib.parse import urlparse

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
    ComponentMapperConfig,
    ComponentSnapshot,
    CrawledPage,
    LeadTargetMapping,
    PageLink,
    SastRun,
    Site,
    TestRun,
    TrafficEntry,
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
# Independent member retries are tracked separately from the campaign
# orchestrator so a single failed child can be retried without restarting the
# stage (or any completed sibling).
_campaign_member_tasks: dict[tuple[int, str, int], asyncio.Task] = {}
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


def _crawl_frontend_context(
    session: Session, test_run_id: int, *, crawl_ok: bool
) -> dict:
    """Return bounded, secret-free live evidence for a copied web lead."""
    pages = session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == test_run_id)
        .where(CrawledPage.status == "crawled")
        .order_by(CrawledPage.id)
        .limit(40)
    ).all()
    traffic = session.exec(
        select(TrafficEntry)
        .where(TrafficEntry.test_run_id == test_run_id)
        .order_by(TrafficEntry.id)
        .limit(80)
    ).all()
    links = session.exec(
        select(PageLink)
        .where(PageLink.test_run_id == test_run_id)
        .order_by(PageLink.id)
        .limit(80)
    ).all()
    status = (
        "completed" if crawl_ok else ("partial" if pages or traffic else "unavailable")
    )

    def _replay_steps(page: CrawledPage) -> list:
        try:
            value = json.loads(page.replay_steps_json or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        return value if isinstance(value, list) else []

    def _action_data(link: PageLink) -> dict:
        try:
            value = json.loads(link.action_data_json or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _request_fields(entry: TrafficEntry) -> list[str]:
        fields: list[str] = []
        try:
            body = json.loads(entry.request_body or "")
        except (TypeError, json.JSONDecodeError):
            body = None
        if isinstance(body, dict):
            fields.extend(str(key)[:100] for key in body if str(key).strip())
        if entry.url:
            query = urlparse(entry.url).query
            fields.extend(
                key[:100]
                for key in (part.split("=", 1)[0] for part in query.split("&") if part)
                if key
            )
        return list(dict.fromkeys(fields))[:30]

    return {
        "resolution_status": status,
        "crawl_status": "completed" if crawl_ok else "failed",
        "pages": [
            {
                "id": page.id,
                "url": page.url,
                "route": urlparse(page.url).path if page.url else "",
                "title": page.title,
                "state_label": page.state_label,
                "replay_steps": _replay_steps(page),
            }
            for page in pages
        ],
        "requests": [
            {
                "id": entry.id,
                "method": entry.method,
                "url": entry.url,
                "status": entry.status,
                "page_id": entry.page_id,
                "session_label": entry.session_label,
                "fields": _request_fields(entry),
            }
            for entry in traffic
        ],
        "actions": [
            {
                "id": link.id,
                "page_id": link.source_page_id,
                "target_url": link.target_url,
                "action_kind": link.action_kind,
                "label": link.link_text,
                "action_data": _action_data(link),
            }
            for link in links
        ],
        "evidence_ids": [
            *[f"page:{page.id}" for page in pages if page.id is not None],
            *[f"traffic:{entry.id}" for entry in traffic if entry.id is not None],
            *[f"action:{link.id}" for link in links if link.id is not None],
        ],
    }


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

    mapper_config = session.get(ComponentMapperConfig, 1)
    campaign = AssessmentCampaign(
        application_id=application_id,
        name=payload.name,
        status="draft",
        max_parallel_sast=payload.max_parallel_sast,
        llm_config_id=payload.llm_config_id,
        llm_profile_id=payload.llm_profile_id,
        max_trace_edges=(
            payload.max_trace_edges
            if payload.max_trace_edges is not None
            else (mapper_config.max_trace_edges if mapper_config else 8)
        ),
        max_trace_components=(
            payload.max_trace_components
            if payload.max_trace_components is not None
            else (mapper_config.max_trace_components if mapper_config else 6)
        ),
        max_paths_per_lead=(
            payload.max_paths_per_lead
            if payload.max_paths_per_lead is not None
            else (mapper_config.max_paths_per_lead if mapper_config else 10)
        ),
        min_trace_confidence=(
            payload.min_trace_confidence
            if payload.min_trace_confidence is not None
            else (mapper_config.min_trace_confidence if mapper_config else 0.50)
        ),
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
    if task is not None and not task.done():
        return True
    return any(
        key[0] == campaign_id and not task.done()
        for key, task in _campaign_member_tasks.items()
    )


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
        campaign.error_message = error if error else None
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


def _interrupt_campaign(campaign_id: int, *, error: str) -> None:
    """Persist a retryable correlation interruption without losing results."""
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            return
        campaign.status = "interrupted"
        campaign.interrupted_stage = "correlating"
        campaign.completed_at = None
        campaign.error_message = error
        campaign.updated_at = _utcnow()
        s.add(campaign)
        s.commit()
    events_svc.emit(
        campaign_id,
        {
            "type": "agent_status",
            "agent_id": "campaign",
            "role": "Campaign Orchestrator",
            "status": "interrupted",
            "current_task": "Correlation interrupted; retry is available",
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


async def rebuild_campaign_connections(campaign_id: int) -> dict:
    """Re-map immutable source snapshots without rerunning child scans."""
    if is_campaign_running(campaign_id):
        raise InvalidCampaignState(
            "Cannot rebuild connections while another campaign action is running"
        )
    with Session(get_engine()) as session:
        campaign = session.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
        if campaign.status in _ACTIVE_STATUSES:
            raise InvalidCampaignState(
                f"Cannot rebuild connections while campaign is '{campaign.status}'"
            )
        preserve_downstream = campaign.status in {
            "awaiting_review",
            "completed",
            "stopped",
        }
        if not preserve_downstream:
            campaign.status = "correlating"
            campaign.error_message = None
            campaign.updated_at = _utcnow()
            session.add(campaign)
            session.commit()

    try:
        result = await correlation_svc.correlate_campaign_with_llm(
            campaign_id,
            preserve_downstream=preserve_downstream,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        from aespa.services.component_mapper import CorrelationTransientError

        if isinstance(exc, CorrelationTransientError):
            _interrupt_campaign(campaign_id, error=str(exc))
        else:
            _finish_campaign(campaign_id, "failed", error=str(exc))
        raise

    if not preserve_downstream:
        _set_campaign_status(campaign_id, "awaiting_review")
    return result


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
        await correlation_svc.correlate_campaign_with_llm(
            campaign_id,
            stop_check=lambda: campaign_id in _campaign_stop_requested,
        )
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
        from aespa.services.component_mapper import CorrelationTransientError

        if isinstance(exc, CorrelationTransientError):
            _interrupt_campaign(campaign_id, error=str(exc))
        else:
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


async def _resume_source_member_task(
    campaign_id: int, member_id: int, sast_run_id: int
) -> None:
    from aespa.services import sast_scanner as sast_scanner_svc

    try:
        if campaign_id in _campaign_stop_requested:
            _update_source_member_status(member_id, "skipped")
            return
        await sast_scanner_svc.run_sast_scan(sast_run_id)
        with Session(get_engine()) as s:
            member = s.get(CampaignSourceMember, member_id)
            run = s.get(SastRun, sast_run_id)
            if member is None:
                return
            if campaign_id in _campaign_stop_requested:
                member.status = "skipped"
            else:
                member.status = (
                    "completed"
                    if run is not None and run.status == "completed"
                    else "failed"
                )
            member.updated_at = _utcnow()
            s.add(member)
            s.commit()
            completed = member.status == "completed"
        if not completed:
            _append_campaign_warnings(
                campaign_id,
                [
                    "A resumed source-code scan did not finish successfully — "
                    "matches involving that component may be incomplete."
                ],
            )
    except asyncio.CancelledError:
        with Session(get_engine()) as s:
            member = s.get(CampaignSourceMember, member_id)
            if member is not None and member.status == "running":
                member.status = "skipped"
                member.updated_at = _utcnow()
                s.add(member)
                s.commit()
        raise
    except Exception as exc:  # noqa: BLE001 — isolate one child retry
        log.exception(
            "Campaign %s source member %s resume failed", campaign_id, member_id
        )
        _update_source_member_status(member_id, "failed")
        _append_campaign_warnings(
            campaign_id, [f"A resumed source-code scan failed to run: {exc}"]
        )
    finally:
        _campaign_member_tasks.pop((campaign_id, "source", member_id), None)


async def resume_source_member(campaign_id: int, member_id: int) -> None:
    """Retry one failed/pending campaign SAST child without touching siblings."""
    from aespa.services import sast_scanner as sast_scanner_svc

    key = (campaign_id, "source", member_id)
    if key in _campaign_member_tasks and not _campaign_member_tasks[key].done():
        return
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
        if campaign.status in _ACTIVE_STATUSES or is_campaign_running(campaign_id):
            raise InvalidCampaignState(
                "Wait for the campaign's current stage to finish before resuming "
                "an individual action"
            )
        member = s.get(CampaignSourceMember, member_id)
        if member is None or member.campaign_id != campaign_id:
            raise CampaignNotFound(
                f"Source member id={member_id} does not belong to this campaign"
            )
        if member.sast_run_id is None:
            snapshot = s.get(ComponentSnapshot, member.snapshot_id)
            component = s.get(ApplicationComponent, member.component_id)
            if snapshot is None or component is None:
                raise InvalidCampaignState(
                    "This source member no longer has a valid component snapshot"
                )
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
        if member.status == "completed":
            raise InvalidCampaignState("This source-code scan is already completed")
        if sast_scanner_svc.is_sast_scan_running(member.sast_run_id):
            raise InvalidCampaignState("This source-code scan is already running")
        member.status = "running"
        member.updated_at = _utcnow()
        campaign.updated_at = _utcnow()
        s.add(member)
        s.add(campaign)
        s.commit()
        sast_run_id = member.sast_run_id

    with events_svc.run_kind_scope("campaign"):
        task = asyncio.create_task(
            _resume_source_member_task(campaign_id, member_id, sast_run_id),
            name=f"campaign-{campaign_id}-source-{member_id}",
        )
    _campaign_member_tasks[key] = task


async def _execute_target_member(
    campaign_id: int,
    member_id: int,
    target_type: str,
    target_id: int,
    test_run_id: int | None,
    api_test_run_id: int | None,
) -> tuple[bool, str | None]:
    """Run one target child and return (completed, warning)."""
    from aespa.services import api_scanner as api_scanner_svc
    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc

    if campaign_id in _campaign_stop_requested:
        _update_target_member_status(member_id, "skipped")
        return False, None
    with Session(get_engine()) as s:
        member = s.get(CampaignTargetMember, member_id)
        already_terminal = member is not None and member.status in (
            "completed",
            "failed",
        )
    if already_terminal:
        return member.status == "completed", None
    _update_target_member_status(member_id, "running")
    try:
        if target_type == "site":
            if test_run_id is None:
                raise ValueError("Web target has no child test run")
            await crawler_svc.start_crawl(test_run_id)
            while crawler_svc.is_running(test_run_id):
                if campaign_id in _campaign_stop_requested:
                    return False, None
                await asyncio.sleep(1.0)
            if campaign_id in _campaign_stop_requested:
                return False, None
            with Session(get_engine()) as s:
                run = s.get(TestRun, test_run_id)
                crawl_ok = run is not None and run.phase == "crawled"
            if not crawl_ok:
                with Session(get_engine()) as s:
                    approved_count = len(
                        s.exec(
                            select(LeadTargetMapping.id)
                            .where(LeadTargetMapping.campaign_id == campaign_id)
                            .where(LeadTargetMapping.target_id == target_id)
                            .where(LeadTargetMapping.status == "approved")
                        ).all()
                    )
                if approved_count == 0:
                    warning = (
                        "A web target's crawl did not finish and no approved SAST "
                        "paths were available — its dynamic scan was skipped."
                    )
                    _update_target_member_status(member_id, "failed")
                    return False, warning
                warning = (
                    "A web target's crawl did not finish; dynamic testing continued "
                    "with approved pre-crawl SAST paths and partial evidence."
                )
                # A failed crawl must not be reported as successful, but the
                # campaign fallback is now an active web scan rather than a
                # terminally failed run.
                with Session(get_engine()) as s:
                    run = s.get(TestRun, test_run_id)
                    if run is not None:
                        run.status = "running"
                        run.phase = "scanning"
                        run.outcome = None
                        run.terminal_reason = None
                        s.add(run)
                        s.commit()
            else:
                warning = None
            with Session(get_engine()) as s:
                live_context = _crawl_frontend_context(
                    s, test_run_id, crawl_ok=crawl_ok
                )
                campaign = s.get(AssessmentCampaign, campaign_id)
                from aespa.services.settings import get_llm_config_for_role

                path_llm_config = (
                    get_llm_config_for_role(s, campaign, "test_lead")
                    if campaign is not None
                    else None
                )
            discovered_paths = correlation_svc.propose_crawl_discovered_paths(
                campaign_id,
                target_id,
                context=live_context,
            )
            if discovered_paths:
                _append_campaign_warnings(
                    campaign_id,
                    [
                        f"{discovered_paths} crawl-discovered frontend path proposal(s) "
                        "were saved for review and were not added to the active scan."
                    ],
                )
            correlation_svc.copy_explicit_component_leads_for_target(
                campaign_id, target_id, "web", test_run_id
            )
            correlation_svc.copy_approved_mappings_for_target(
                campaign_id, target_id, "web", test_run_id
            )
            (
                _,
                rewrite_warnings,
            ) = await correlation_svc.enrich_copied_web_leads_for_target_with_llm(
                campaign_id,
                target_id,
                test_run_id,
                context=live_context,
                warning=warning,
                llm_config=path_llm_config,
            )
            if rewrite_warnings:
                _append_campaign_warnings(campaign_id, rewrite_warnings)
            await scanner_svc.start_thinking_scan(test_run_id)
            while scanner_svc.is_thinking_running(test_run_id):
                if campaign_id in _campaign_stop_requested:
                    return False, None
                await asyncio.sleep(1.0)
            if campaign_id in _campaign_stop_requested:
                return False, None
            with Session(get_engine()) as s:
                run = s.get(TestRun, test_run_id)
                scan_ok = run is not None and run.status == "complete"
            if scan_ok:
                _update_target_member_status(member_id, "completed")
                return True, warning
            warning = (
                "A web target's dynamic scan did not finish successfully — its "
                "results may be incomplete."
            )
            _update_target_member_status(member_id, "failed")
            return False, warning

        if api_test_run_id is None:
            raise ValueError("API target has no child test run")
        correlation_svc.copy_explicit_component_leads_for_target(
            campaign_id, target_id, "api", api_test_run_id
        )
        correlation_svc.copy_approved_mappings_for_target(
            campaign_id, target_id, "api", api_test_run_id
        )
        await api_scanner_svc.start_api_scan(api_test_run_id)
        while api_scanner_svc.is_api_scan_running(api_test_run_id):
            if campaign_id in _campaign_stop_requested:
                return False, None
            await asyncio.sleep(1.0)
        if campaign_id in _campaign_stop_requested:
            return False, None
        with Session(get_engine()) as s:
            run = s.get(ApiTestRun, api_test_run_id)
            scan_ok = run is not None and run.status == "completed"
        if scan_ok:
            _update_target_member_status(member_id, "completed")
            return True, None
        warning = (
            "An API target's dynamic scan did not finish successfully — its "
            "results may be incomplete."
        )
        _update_target_member_status(member_id, "failed")
        return False, warning
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — isolate one target
        _update_target_member_status(member_id, "failed")
        return False, f"A live-target scan failed: {exc}"


async def _resume_target_member_task(
    campaign_id: int,
    member_id: int,
    target_type: str,
    target_id: int,
    test_run_id: int | None,
    api_test_run_id: int | None,
) -> None:
    try:
        completed, warning = await _execute_target_member(
            campaign_id,
            member_id,
            target_type,
            target_id,
            test_run_id,
            api_test_run_id,
        )
        if warning:
            _append_campaign_warnings(campaign_id, [warning])
        if completed:
            with Session(get_engine()) as s:
                campaign = s.get(AssessmentCampaign, campaign_id)
                if (
                    campaign is not None
                    and campaign.status == "failed"
                    and campaign.error_message
                    == "No live target completed its dynamic scan."
                ):
                    campaign.status = "completed"
                    campaign.error_message = None
                    campaign.completed_at = _utcnow()
                    campaign.updated_at = _utcnow()
                    s.add(campaign)
                    s.commit()
        if not completed and campaign_id in _campaign_stop_requested:
            _update_target_member_status(member_id, "skipped")
    except asyncio.CancelledError:
        with Session(get_engine()) as s:
            member = s.get(CampaignTargetMember, member_id)
            if member is not None and member.status == "running":
                member.status = "skipped"
                member.updated_at = _utcnow()
                s.add(member)
                s.commit()
        raise
    finally:
        _campaign_member_tasks.pop((campaign_id, "target", member_id), None)


async def resume_target_member(campaign_id: int, member_id: int) -> None:
    """Retry one failed/pending campaign target child without touching siblings."""
    from aespa.services import api_scanner as api_scanner_svc
    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc

    key = (campaign_id, "target", member_id)
    if key in _campaign_member_tasks and not _campaign_member_tasks[key].done():
        return
    with Session(get_engine()) as s:
        campaign = s.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFound(f"Campaign id={campaign_id} does not exist")
        if campaign.status in _ACTIVE_STATUSES or is_campaign_running(campaign_id):
            raise InvalidCampaignState(
                "Wait for the campaign's current stage to finish before resuming "
                "an individual action"
            )
        member = s.get(CampaignTargetMember, member_id)
        if member is None or member.campaign_id != campaign_id:
            raise CampaignNotFound(
                f"Target member id={member_id} does not belong to this campaign"
            )
        if member.status == "completed":
            raise InvalidCampaignState("This target scan is already completed")
        target = s.get(ApplicationTarget, member.target_id)
        if target is None:
            raise InvalidCampaignState("This target no longer exists")
        if member.target_type == "site":
            if member.test_run_id is None:
                site = s.get(Site, target.target_id)
                if site is None:
                    raise InvalidCampaignState("This site target no longer exists")
                run = TestRun(
                    site_id=target.target_id,
                    name=f"{site.name} — {campaign.name}",
                    llm_config_id=campaign.llm_config_id,
                    llm_profile_id=campaign.llm_profile_id,
                )
                s.add(run)
                s.flush()
                member.test_run_id = run.id
            if member.test_run_id is None:
                raise InvalidCampaignState("This web target has no run to resume")
            if crawler_svc.is_running(
                member.test_run_id
            ) or scanner_svc.is_thinking_running(member.test_run_id):
                raise InvalidCampaignState("This web target scan is already running")
        else:
            if member.api_test_run_id is None:
                collection = s.get(ApiCollection, target.target_id)
                if collection is None:
                    raise InvalidCampaignState("This API target no longer exists")
                run = ApiTestRun(
                    collection_id=target.target_id,
                    name=f"{collection.name} — {campaign.name}",
                    llm_config_id=campaign.llm_config_id,
                    llm_profile_id=campaign.llm_profile_id,
                )
                s.add(run)
                s.flush()
                member.api_test_run_id = run.id
            if member.api_test_run_id is None:
                raise InvalidCampaignState("This API target has no run to resume")
            if api_scanner_svc.is_api_scan_running(member.api_test_run_id):
                raise InvalidCampaignState("This API target scan is already running")
        member.status = "running"
        member.updated_at = _utcnow()
        campaign.updated_at = _utcnow()
        s.add(member)
        s.add(campaign)
        s.commit()
        target_ref = (
            member.id,
            member.target_type,
            member.target_id,
            member.test_run_id,
            member.api_test_run_id,
        )

    with events_svc.run_kind_scope("campaign"):
        task = asyncio.create_task(
            _resume_target_member_task(campaign_id, *target_ref),
            name=f"campaign-{campaign_id}-target-{member_id}",
        )
    _campaign_member_tasks[key] = task


async def supplemental_validate_target(
    campaign_id: int,
    target_id: int,
    mapping_ids: set[int],
) -> None:
    """Validate newly approved crawl paths on an existing web run only."""
    from aespa.services import scanner as scanner_svc

    if not mapping_ids:
        raise InvalidCampaignState("Select at least one approved frontend path")
    with Session(get_engine()) as session:
        campaign = session.get(AssessmentCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFound(f"Campaign {campaign_id} does not exist")
        if campaign.status in _ACTIVE_STATUSES or is_campaign_running(campaign_id):
            raise InvalidCampaignState(
                "Supplemental validation is unavailable while the campaign is active"
            )
        member = session.exec(
            select(CampaignTargetMember)
            .where(CampaignTargetMember.campaign_id == campaign_id)
            .where(CampaignTargetMember.target_id == target_id)
            .where(CampaignTargetMember.target_type == "site")
        ).first()
        if member is None or member.test_run_id is None:
            raise InvalidCampaignState("The selected target has no existing web run")
        run = session.get(TestRun, member.test_run_id)
        if run is None:
            raise InvalidCampaignState("The selected target web run no longer exists")
        if scanner_svc.is_thinking_running(run.id):
            raise InvalidCampaignState("The target scanner is already active")
        crawl_ok = run.phase == "crawled"
        mappings = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == campaign_id)
            .where(LeadTargetMapping.target_id == target_id)
            .where(LeadTargetMapping.id.in_(mapping_ids))
        ).all()
        if len(mappings) != len(mapping_ids) or any(
            mapping.status != "approved" for mapping in mappings
        ):
            raise InvalidCampaignState(
                "Supplemental validation requires approved mappings from this target"
            )
        run.coverage_mode = "sast_validate"
        run.status = "running"
        run.phase = "scanning"
        run.outcome = None
        run.terminal_reason = None
        run.completed_at = None
        member.status = "running"
        member.updated_at = _utcnow()
        session.add(run)
        session.add(member)
        session.commit()
        test_run_id = run.id
        target_member_id = member.id

        live_context = _crawl_frontend_context(
            session, test_run_id, crawl_ok=crawl_ok
        )

    correlation_svc.copy_approved_mappings_for_target(
        campaign_id,
        target_id,
        "web",
        test_run_id,
        mapping_ids=mapping_ids,
    )
    correlation_svc.enrich_copied_web_leads_for_target(
        campaign_id,
        target_id,
        test_run_id,
        context=live_context,
    )
    with events_svc.run_kind_scope("campaign"):
        events_svc.emit(
            campaign_id,
            {
                "type": "scanner_phase",
                "phase": "supplemental_sast_validate",
                "status": "running",
                "message": (
                    f"Validating {len(mapping_ids)} newly approved frontend path(s)."
                ),
                "data": {"target_id": target_id, "mapping_ids": sorted(mapping_ids)},
                "_persist": True,
            },
        )
    await scanner_svc.start_thinking_scan(test_run_id)
    while scanner_svc.is_thinking_running(test_run_id):
        if campaign_id in _campaign_stop_requested:
            return
        await asyncio.sleep(1.0)
    with Session(get_engine()) as session:
        run = session.get(TestRun, test_run_id)
        member = session.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.id == target_member_id
            )
        ).one()
        succeeded = run is not None and run.status == "complete"
        member.status = "completed" if succeeded else "failed"
        member.updated_at = _utcnow()
        session.add(member)
        session.commit()
    if not succeeded:
        raise InvalidCampaignState(
            "Supplemental frontend path validation did not finish successfully"
        )


async def stop_member_tasks_for_run(run_kind: str, run_id: int) -> None:
    """Cancel any independent campaign retry currently using a child run."""
    with Session(get_engine()) as s:
        if run_kind == "sast":
            member_ids = set(
                s.exec(
                    select(CampaignSourceMember.id).where(
                        CampaignSourceMember.sast_run_id == run_id
                    )
                ).all()
            )
        elif run_kind == "web":
            member_ids = set(
                s.exec(
                    select(CampaignTargetMember.id).where(
                        CampaignTargetMember.test_run_id == run_id
                    )
                ).all()
            )
        elif run_kind == "api":
            member_ids = set(
                s.exec(
                    select(CampaignTargetMember.id).where(
                        CampaignTargetMember.api_test_run_id == run_id
                    )
                ).all()
            )
        else:
            raise ValueError(f"Unknown run_kind: {run_kind!r}")

    member_tasks = [
        task
        for (campaign_id, task_kind, member_id), task in _campaign_member_tasks.items()
        if task_kind in ({"sast"} if run_kind == "sast" else {"target"})
        and member_id in member_ids
        and not task.done()
    ]
    for task in member_tasks:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)


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

    member_tasks = [
        task
        for (task_campaign_id, _, _), task in _campaign_member_tasks.items()
        if task_campaign_id == campaign_id and not task.done()
    ]
    for member_task in member_tasks:
        with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(member_task), timeout=10.0)

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
        if campaign.status not in {"awaiting_review", "completed"}:
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
        if (
            campaign.status == "awaiting_review"
            and pending_after == 0
            and campaign.review_submitted_at is None
        ):
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
        completed, warning = await _execute_target_member(
            campaign_id,
            member_id,
            target_type,
            target_id,
            test_run_id,
            api_test_run_id,
        )
        if completed:
            completed_flags[member_id] = True
        if warning:
            warnings.append(warning)

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
