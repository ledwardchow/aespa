"""Thin API router for Applications: components, ZIP snapshots, targets,
code-to-target routing associations, and multi-repository assessment campaigns.

Campaign results are assembled in ``services/campaign_results.py``. This
router also handles HTTP validation, uploads, and activity streams.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
import zipfile
from pathlib import Path
from typing import AsyncGenerator

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_engine, get_session
from aespa.models import (
    AgentLog,
    ApplicationComponent,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentConnection,
    ComponentFact,
    LeadTargetMapping,
    ScanLog,
)
from aespa.schemas import (
    ApplicationComponentCreate,
    ApplicationComponentOut,
    ApplicationComponentUpdate,
    ApplicationCreate,
    ApplicationSummary,
    ApplicationTargetCreate,
    ApplicationTargetOut,
    ApplicationTargetUpdate,
    ApplicationUpdate,
    CampaignActivityEntry,
    CampaignCreate,
    CampaignDetail,
    CampaignFindingRow,
    CampaignProgress,
    CampaignSourceMemberOut,
    CampaignSummary,
    CampaignSupplementalValidationRequest,
    CampaignTargetMemberOut,
    ComponentConnectionOut,
    ComponentSnapshotOut,
    ComponentTargetHintCreate,
    ComponentTargetHintOut,
    LeadTargetMappingEditRequest,
    LeadTargetMappingOut,
    LeadTargetMappingReviewRequest,
    LeadTargetMappingReviewResult,
)
from aespa.services import applications as applications_svc
from aespa.services import campaign_results as campaign_results_svc
from aespa.services import campaigns as campaigns_svc
from aespa.services import correlation as correlation_svc
from aespa.services import events as events_svc

router = APIRouter(prefix="/api/applications", tags=["applications"])

_MAX_SNAPSHOT_UPLOAD_BYTES = applications_svc.MAX_SNAPSHOT_UPLOAD_BYTES
_UPLOAD_CHUNK_BYTES = applications_svc.SNAPSHOT_UPLOAD_CHUNK_BYTES


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


_ACTIVITY_STREAM_POLL_SECONDS = 1.0
_ACTIVITY_CURSOR_RE = re.compile(r"^(\d+)\.(\d+)$")


def _parse_activity_cursor(cursor: str | None) -> tuple[int, int]:
    """Parse an ``event_id``/cursor of the form ``"<agent_id>.<scan_id>"``.

    A missing, empty, or malformed cursor resumes from the very beginning
    (``0, 0``) rather than raising — a stale or garbled ``Last-Event-ID``
    must never wedge a reconnecting client.
    """
    if not cursor:
        return (0, 0)
    match = _ACTIVITY_CURSOR_RE.match(cursor.strip())
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2)))


def _load_campaign_activity_entries(
    session: Session,
    campaign_id: int,
    after_agent_id: int = 0,
    after_scan_id: int = 0,
) -> tuple[list[CampaignActivityEntry], int, int]:
    """Load every persisted campaign activity row strictly after the given
    watermarks, in stable chronological order, and return the new watermarks.

    AgentLog and ScanLog each have their own independent id sequence, so
    "after cursor" is tracked as one watermark per table; ties in
    ``created_at`` are broken by table then id so the merge order never
    depends on incidental query/dict ordering.
    """
    agent_rows = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == campaign_id)
        .where(AgentLog.run_kind == "campaign")
        .where(AgentLog.id > after_agent_id)
    ).all()
    scan_rows = session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == campaign_id)
        .where(ScanLog.run_kind == "campaign")
        .where(ScanLog.id > after_scan_id)
    ).all()

    combined: list[tuple[object, int, str, int]] = [
        (e.created_at, 0, "agent", e.id) for e in agent_rows
    ] + [(e.created_at, 1, "scan", e.id) for e in scan_rows]
    combined.sort(key=lambda row: (row[0], row[1], row[3]))
    by_id = {("agent", e.id): e for e in agent_rows}
    by_id.update({("scan", e.id): e for e in scan_rows})

    entries: list[CampaignActivityEntry] = []
    max_agent, max_scan = after_agent_id, after_scan_id
    for _created_at, _order, kind, row_id in combined:
        row = by_id[(kind, row_id)]
        if kind == "agent":
            max_agent = max(max_agent, row_id)
            entries.append(
                CampaignActivityEntry(
                    event_id=f"{max_agent}.{max_scan}",
                    timestamp=row.created_at,
                    type="agent_status",
                    status=row.status,
                    role=row.role,
                    task=row.current_task,
                    outcome=row.outcome,
                )
            )
        else:
            max_scan = max(max_scan, row_id)
            entries.append(
                CampaignActivityEntry(
                    event_id=f"{max_agent}.{max_scan}",
                    timestamp=row.created_at,
                    type="scanner_phase",
                    status=row.status,
                    phase=row.phase,
                    message=row.message,
                )
            )
    return entries, max_agent, max_scan


def _to_application_summary(session: Session, app) -> ApplicationSummary:
    components = applications_svc.list_components(session, app.id)
    targets = applications_svc.list_targets(session, app.id)
    last_campaign = session.exec(
        select(AssessmentCampaign)
        .where(AssessmentCampaign.application_id == app.id)
        .order_by(AssessmentCampaign.id.desc())  # type: ignore[attr-defined]
    ).first()
    return ApplicationSummary(
        id=app.id,
        name=app.name,
        description=app.description,
        created_at=app.created_at,
        updated_at=app.updated_at,
        component_count=len(components),
        site_count=sum(1 for t in targets if t.target_type == "site"),
        api_collection_count=sum(
            1 for t in targets if t.target_type == "api_collection"
        ),
        last_campaign_status=last_campaign.status if last_campaign else None,
    )


def _to_component_out(
    session: Session, component: ApplicationComponent
) -> ApplicationComponentOut:
    snapshots = applications_svc.list_snapshots(
        session, component.application_id, component.id
    )
    latest = snapshots[0] if snapshots else None
    return ApplicationComponentOut(
        id=component.id,
        application_id=component.application_id,
        name=component.name,
        role=component.role,
        description=component.description,
        created_at=component.created_at,
        updated_at=component.updated_at,
        latest_snapshot=(
            ComponentSnapshotOut.model_validate(latest) if latest else None
        ),
        snapshot_count=len(snapshots),
    )


def _to_target_out(
    session: Session, application_id: int, target
) -> ApplicationTargetOut:
    return ApplicationTargetOut(
        id=target.id,
        application_id=application_id,
        target_type=target.target_type,
        target_id=target.target_id,
        component_id=target.component_id,
        created_at=target.created_at,
        name=applications_svc.target_display_name(session, target),
    )


# ── Application ───────────────────────────────────────────────────────────────


@router.get("", response_model=list[ApplicationSummary])
def list_applications(
    session: Session = Depends(get_session),
) -> list[ApplicationSummary]:
    return [
        _to_application_summary(session, app)
        for app in applications_svc.list_applications(session)
    ]


@router.post("", response_model=ApplicationSummary, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate, session: Session = Depends(get_session)
) -> ApplicationSummary:
    try:
        app = applications_svc.create_application(session, payload)
    except applications_svc.DuplicateApplicationName as exc:
        raise _conflict(exc) from exc
    return _to_application_summary(session, app)


@router.get("/{application_id}", response_model=ApplicationSummary)
def get_application(
    application_id: int, session: Session = Depends(get_session)
) -> ApplicationSummary:
    try:
        app = applications_svc.get_application(session, application_id)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    return _to_application_summary(session, app)


@router.patch("/{application_id}", response_model=ApplicationSummary)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    session: Session = Depends(get_session),
) -> ApplicationSummary:
    try:
        app = applications_svc.update_application(session, application_id, payload)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.DuplicateApplicationName as exc:
        raise _conflict(exc) from exc
    return _to_application_summary(session, app)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int, session: Session = Depends(get_session)
) -> None:
    try:
        applications_svc.delete_application(session, application_id)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.ReferencedByCampaign as exc:
        raise _conflict(exc) from exc


# ── Components ────────────────────────────────────────────────────────────────


@router.get(
    "/{application_id}/components", response_model=list[ApplicationComponentOut]
)
def list_components(
    application_id: int, session: Session = Depends(get_session)
) -> list[ApplicationComponentOut]:
    try:
        components = applications_svc.list_components(session, application_id)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    return [_to_component_out(session, c) for c in components]


@router.post(
    "/{application_id}/components",
    response_model=ApplicationComponentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_component(
    application_id: int,
    payload: ApplicationComponentCreate,
    session: Session = Depends(get_session),
) -> ApplicationComponentOut:
    try:
        component = applications_svc.create_component(session, application_id, payload)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.DuplicateComponentName as exc:
        raise _conflict(exc) from exc
    return _to_component_out(session, component)


@router.patch(
    "/{application_id}/components/{component_id}",
    response_model=ApplicationComponentOut,
)
def update_component(
    application_id: int,
    component_id: int,
    payload: ApplicationComponentUpdate,
    session: Session = Depends(get_session),
) -> ApplicationComponentOut:
    try:
        component = applications_svc.update_component(
            session, application_id, component_id, payload
        )
    except applications_svc.ComponentNotFound as exc:
        raise _not_found(exc) from exc
    return _to_component_out(session, component)


@router.delete(
    "/{application_id}/components/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_component(
    application_id: int, component_id: int, session: Session = Depends(get_session)
) -> None:
    try:
        applications_svc.delete_component(session, application_id, component_id)
    except applications_svc.ComponentNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.ReferencedByCampaign as exc:
        raise _conflict(exc) from exc


# ── ZIP Snapshots ──────────────────────────────────────────────────────────────


@router.get(
    "/{application_id}/components/{component_id}/snapshots",
    response_model=list[ComponentSnapshotOut],
)
def list_snapshots(
    application_id: int, component_id: int, session: Session = Depends(get_session)
) -> list[ComponentSnapshotOut]:
    try:
        snapshots = applications_svc.list_snapshots(
            session, application_id, component_id
        )
    except applications_svc.ComponentNotFound as exc:
        raise _not_found(exc) from exc
    return [ComponentSnapshotOut.model_validate(s) for s in snapshots]


@router.post(
    "/{application_id}/components/{component_id}/snapshots",
    response_model=ComponentSnapshotOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_snapshot(
    application_id: int,
    component_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ComponentSnapshotOut:
    """Upload one immutable ZIP snapshot for a component.

    Reuses the standalone-SAST upload safety rules: a size cap, chunked
    streaming writes, ZIP-format validation, and an atomic rename so a
    half-written file is never visible under its final name.
    """
    try:
        applications_svc.get_component(session, application_id, component_id)
    except applications_svc.ComponentNotFound as exc:
        raise _not_found(exc) from exc

    original_name = Path(file.filename or "source.zip").name or "source.zip"
    base = applications_svc.snapshot_storage_dir(get_settings().data_dir)
    ext = Path(original_name).suffix or ".zip"
    upload_id = uuid.uuid4().hex
    temp_path = base / f".{upload_id}.upload"
    stored_path = base / f"{upload_id}{ext}"
    bytes_written = 0
    digest = hashlib.sha256()
    try:
        with temp_path.open("wb") as destination:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > _MAX_SNAPSHOT_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"File exceeds the "
                            f"{_MAX_SNAPSHOT_UPLOAD_BYTES // (1024 * 1024)} MiB "
                            "upload limit."
                        ),
                    )
                digest.update(chunk)
                destination.write(chunk)

        if bytes_written == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if not zipfile.is_zipfile(temp_path):
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid ZIP archive."
            )
        temp_path.replace(stored_path)
    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    snapshot = applications_svc.create_snapshot(
        session,
        application_id,
        component_id,
        filename=original_name,
        stored_path=str(stored_path),
        size_bytes=bytes_written,
        sha256=digest.hexdigest(),
    )
    return ComponentSnapshotOut.model_validate(snapshot)


@router.delete(
    "/{application_id}/components/{component_id}/snapshots/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_snapshot(
    application_id: int,
    component_id: int,
    snapshot_id: int,
    session: Session = Depends(get_session),
) -> None:
    try:
        applications_svc.delete_snapshot(
            session, application_id, component_id, snapshot_id
        )
    except applications_svc.SnapshotNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.ReferencedByCampaign as exc:
        raise _conflict(exc) from exc


# ── Targets ────────────────────────────────────────────────────────────────────


@router.get("/{application_id}/targets", response_model=list[ApplicationTargetOut])
def list_targets(
    application_id: int, session: Session = Depends(get_session)
) -> list[ApplicationTargetOut]:
    try:
        targets = applications_svc.list_targets(session, application_id)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    return [_to_target_out(session, application_id, t) for t in targets]


@router.post(
    "/{application_id}/targets",
    response_model=ApplicationTargetOut,
    status_code=status.HTTP_201_CREATED,
)
def attach_target(
    application_id: int,
    payload: ApplicationTargetCreate,
    session: Session = Depends(get_session),
) -> ApplicationTargetOut:
    try:
        target = applications_svc.attach_target(session, application_id, payload)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.TargetNotFound as exc:
        raise _not_found(exc) from exc
    return _to_target_out(session, application_id, target)


@router.patch(
    "/{application_id}/targets/{target_id}",
    response_model=ApplicationTargetOut,
)
def update_target(
    application_id: int,
    target_id: int,
    payload: ApplicationTargetUpdate,
    session: Session = Depends(get_session),
) -> ApplicationTargetOut:
    try:
        target = applications_svc.update_target(
            session, application_id, target_id, payload
        )
    except applications_svc.TargetNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.CrossApplicationReference as exc:
        raise _bad_request(exc) from exc
    return _to_target_out(session, application_id, target)


@router.delete(
    "/{application_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT
)
def detach_target(
    application_id: int, target_id: int, session: Session = Depends(get_session)
) -> None:
    try:
        applications_svc.detach_target(session, application_id, target_id)
    except applications_svc.TargetNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.ReferencedByCampaign as exc:
        raise _conflict(exc) from exc


# ── Code-to-target routing associations ────────────────────────────────────────


@router.get("/{application_id}/hints", response_model=list[ComponentTargetHintOut])
def list_hints(
    application_id: int, session: Session = Depends(get_session)
) -> list[ComponentTargetHintOut]:
    try:
        hints = applications_svc.list_hints(session, application_id)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    return [ComponentTargetHintOut.model_validate(h) for h in hints]


@router.post(
    "/{application_id}/hints",
    response_model=ComponentTargetHintOut,
    status_code=status.HTTP_201_CREATED,
)
def create_hint(
    application_id: int,
    payload: ComponentTargetHintCreate,
    session: Session = Depends(get_session),
) -> ComponentTargetHintOut:
    try:
        hint = applications_svc.create_hint(session, application_id, payload)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.CrossApplicationReference as exc:
        raise _bad_request(exc) from exc
    return ComponentTargetHintOut.model_validate(hint)


@router.delete(
    "/{application_id}/hints/{hint_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_hint(
    application_id: int, hint_id: int, session: Session = Depends(get_session)
) -> None:
    try:
        applications_svc.delete_hint(session, application_id, hint_id)
    except applications_svc.HintNotFound as exc:
        raise _not_found(exc) from exc


# ── Campaigns ──────────────────────────────────────────────────────────────────


@router.get("/{application_id}/campaigns", response_model=list[CampaignSummary])
def list_campaigns(
    application_id: int, session: Session = Depends(get_session)
) -> list[CampaignSummary]:
    try:
        campaigns = campaigns_svc.list_campaigns(session, application_id)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    return [CampaignSummary.model_validate(c) for c in campaigns]


@router.post(
    "/{application_id}/campaigns",
    response_model=CampaignDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    application_id: int,
    payload: CampaignCreate,
    session: Session = Depends(get_session),
) -> CampaignDetail:
    try:
        campaign = campaigns_svc.create_campaign(session, application_id, payload)
    except applications_svc.ApplicationNotFound as exc:
        raise _not_found(exc) from exc
    except applications_svc.CrossApplicationReference as exc:
        raise _bad_request(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _bad_request(exc) from exc
    return _to_campaign_detail(session, campaign)


def _to_campaign_detail(session: Session, campaign) -> CampaignDetail:
    source_members = session.exec(
        select(CampaignSourceMember).where(
            CampaignSourceMember.campaign_id == campaign.id
        )
    ).all()
    target_members = session.exec(
        select(CampaignTargetMember).where(
            CampaignTargetMember.campaign_id == campaign.id
        )
    ).all()
    return CampaignDetail(
        **CampaignSummary.model_validate(campaign).model_dump(),
        source_members=[
            _to_campaign_source_member(session, member) for member in source_members
        ],
        target_members=[
            _to_campaign_target_member(session, member) for member in target_members
        ],
    )


def _to_campaign_source_member(session: Session, member) -> CampaignSourceMemberOut:
    result = CampaignSourceMemberOut.model_validate(member)
    return result.model_copy(
        update={
            "run_status": campaigns_svc.get_campaign_member_run_status(session, member)
        }
    )


def _to_campaign_target_member(session: Session, member) -> CampaignTargetMemberOut:
    result = CampaignTargetMemberOut.model_validate(member)
    return result.model_copy(
        update={
            "run_status": campaigns_svc.get_campaign_member_run_status(session, member)
        }
    )


@router.get("/{application_id}/campaigns/{campaign_id}", response_model=CampaignDetail)
def get_campaign(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignDetail:
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    return _to_campaign_detail(session, campaign)


@router.delete(
    "/{application_id}/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_campaign(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> None:
    try:
        campaigns_svc.delete_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc


@router.post(
    "/{application_id}/campaigns/{campaign_id}/start", response_model=CampaignDetail
)
async def start_campaign(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignDetail:
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        await campaigns_svc.start_campaign(campaign.id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.post(
    "/{application_id}/campaigns/{campaign_id}/stop", response_model=CampaignDetail
)
async def stop_campaign(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignDetail:
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    await campaigns_svc.stop_campaign(campaign.id)
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.post(
    "/{application_id}/campaigns/{campaign_id}/resume", response_model=CampaignDetail
)
async def resume_campaign(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignDetail:
    """Resume a stopped campaign without recreating completed work."""
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        await campaigns_svc.resume_campaign(campaign.id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.post(
    "/{application_id}/campaigns/{campaign_id}/retry", response_model=CampaignDetail
)
async def retry_campaign(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignDetail:
    """Backward-compatible route for resuming an interrupted campaign.

    Reuses every child run/lead the campaign already created — never
    recreates a ``SastRun``/``TestRun``/``ApiTestRun`` or duplicates a lead.
    """
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        await campaigns_svc.resume_campaign(campaign.id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.post(
    "/{application_id}/campaigns/{campaign_id}/sources/{member_id}/resume",
    response_model=CampaignDetail,
)
async def resume_campaign_source(
    application_id: int,
    campaign_id: int,
    member_id: int,
    session: Session = Depends(get_session),
) -> CampaignDetail:
    """Retry one campaign-owned SAST child without rerunning other members."""
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        await campaigns_svc.resume_source_member(campaign.id, member_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.post(
    "/{application_id}/campaigns/{campaign_id}/targets/{member_id}/resume",
    response_model=CampaignDetail,
)
async def resume_campaign_target(
    application_id: int,
    campaign_id: int,
    member_id: int,
    session: Session = Depends(get_session),
) -> CampaignDetail:
    """Retry one campaign-owned live-target child without rerunning siblings."""
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        await campaigns_svc.resume_target_member(campaign.id, member_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.get(
    "/{application_id}/campaigns/{campaign_id}/status",
    response_model=CampaignProgress,
)
def campaign_status(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignProgress:
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
        progress = campaigns_svc.get_campaign_progress(session, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    return CampaignProgress(
        status=progress["status"],
        warnings=progress["warnings"],
        source_members=[
            _to_campaign_source_member(session, member)
            for member in progress["source_members"]
        ],
        target_members=[
            _to_campaign_target_member(session, member)
            for member in progress["target_members"]
        ],
    )


@router.get("/{application_id}/campaigns/{campaign_id}/events")
async def campaign_events(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> StreamingResponse:
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    return StreamingResponse(
        events_svc.stream(campaign_id, run_kind="campaign"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/{application_id}/campaigns/{campaign_id}/activity",
    response_model=list[CampaignActivityEntry],
)
def campaign_activity(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> list[CampaignActivityEntry]:
    """Persisted campaign activity, merged into one stable chronological feed.

    Backed by the same ``AgentLog``/``ScanLog`` tables every other run kind
    persists to (filtered to ``run_kind == "campaign"`` and this campaign's
    id) — this is the reload/replay counterpart to the live SSE stream above,
    not a replacement for it. See ``.../activity/stream`` for a cursor-safe
    replay-then-follow feed that never has a fetch→subscribe gap window.
    """
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc

    entries, _, _ = _load_campaign_activity_entries(session, campaign_id)
    return entries


@router.get("/{application_id}/campaigns/{campaign_id}/activity/stream")
async def campaign_activity_stream(
    application_id: int,
    campaign_id: int,
    request: Request,
    cursor: str | None = None,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Cursor-safe persisted replay of campaign activity, then follow new
    entries as they are persisted — with no gap between "catch up on
    history" and "start watching for new events".

    Resumes after ``Last-Event-ID`` (checked first, per the SSE reconnect
    convention) or the ``cursor`` query param (checked second) — either one
    is the opaque ``event_id`` string from a previously received
    ``CampaignActivityEntry``. Omit both to replay full history. Every
    streamed message carries ``id: <event_id>`` so a browser ``EventSource``
    reconnects with the right ``Last-Event-ID`` automatically; a custom
    client can instead track the field itself and pass it as ``cursor``.

    Unlike ``.../events`` (the live pub/sub-only stream), this endpoint never
    subscribes to the in-memory event bus at all — every message it yields,
    including "new" ones, comes from re-querying ``AgentLog``/``ScanLog``
    on a short poll interval. That means there is no window in which an
    event emitted between "fetch persisted history" and "subscribe live"
    could be missed: the next poll always picks up anything committed by
    then, by construction.
    """
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc

    last_event_id = request.headers.get("last-event-id")
    after_agent_id, after_scan_id = _parse_activity_cursor(last_event_id or cursor)

    return StreamingResponse(
        _stream_campaign_activity(campaign_id, after_agent_id, after_scan_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _stream_campaign_activity(
    campaign_id: int,
    after_agent_id: int,
    after_scan_id: int,
    poll_seconds: float = _ACTIVITY_STREAM_POLL_SECONDS,
) -> AsyncGenerator[str, None]:
    """Poll-based SSE body for ``campaign_activity_stream``, factored out so
    it can be driven directly (bypassing the ASGI transport) in tests.

    Every iteration re-queries the persisted tables from the current
    watermark forward — there is no in-memory subscribe step, so there is no
    window in which a concurrently-committed row could be missed between
    "read history" and "start watching for new rows".
    """
    agent_wm, scan_wm = after_agent_id, after_scan_id
    while True:
        with Session(get_engine()) as poll_session:
            entries, agent_wm, scan_wm = _load_campaign_activity_entries(
                poll_session, campaign_id, agent_wm, scan_wm
            )
        if entries:
            for entry in entries:
                yield (
                    f"id: {entry.event_id}\n"
                    f"data: {json.dumps(entry.model_dump(mode='json'))}\n\n"
                )
        else:
            yield ": heartbeat\n\n"
        await asyncio.sleep(poll_seconds)


@router.get(
    "/{application_id}/campaigns/{campaign_id}/connections",
    response_model=list[ComponentConnectionOut],
)
def campaign_connections(
    application_id: int,
    campaign_id: int,
    scope: str = Query(default="cross_component"),
    session: Session = Depends(get_session),
) -> list[ComponentConnectionOut]:
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    stmt = select(ComponentConnection).where(
        ComponentConnection.campaign_id == campaign_id
    )
    if scope != "all":
        stmt = stmt.where(ComponentConnection.path_scope == scope)
    connections = session.exec(stmt).all()
    component_ids = {
        component_id
        for connection in connections
        for component_id in (
            connection.source_component_id,
            connection.target_component_id,
        )
    }
    component_names = {
        component.id: component.name
        for component in session.exec(
            select(ApplicationComponent).where(
                ApplicationComponent.id.in_(component_ids)
            )
        ).all()
    }
    fact_ids = {
        fact_id
        for connection in connections
        for fact_id in (connection.source_fact_id, connection.target_fact_id)
    }
    facts = {
        fact.id: fact
        for fact in session.exec(
            select(ComponentFact).where(ComponentFact.id.in_(fact_ids))
        ).all()
    }

    def fact_summary(fact: ComponentFact | None) -> dict:
        if fact is None:
            return {}
        return {
            "id": fact.id,
            "fact_type": fact.fact_type,
            "method": fact.method,
            "path": fact.path,
            "host": fact.host,
            "name": fact.name,
            "evidence_location": fact.evidence_location,
            "detail_json": fact.detail_json,
        }

    return [
        ComponentConnectionOut.model_validate(connection).model_copy(
            update={
                "source_component_name": component_names.get(
                    connection.source_component_id
                ),
                "target_component_name": component_names.get(
                    connection.target_component_id
                ),
                "source_fact_summary": fact_summary(
                    facts.get(connection.source_fact_id)
                ),
                "target_fact_summary": fact_summary(
                    facts.get(connection.target_fact_id)
                ),
            }
        )
        for connection in connections
    ]


@router.post(
    "/{application_id}/campaigns/{campaign_id}/connections/rebuild",
    response_model=CampaignDetail,
)
async def rebuild_campaign_connections(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignDetail:
    """Rebuild the connection map from immutable snapshots without child scans."""
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        with events_svc.run_kind_scope("campaign"):
            await campaigns_svc.rebuild_campaign_connections(campaign.id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.get(
    "/{application_id}/campaigns/{campaign_id}/mappings",
    response_model=list[LeadTargetMappingOut],
)
def campaign_mappings(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> list[LeadTargetMappingOut]:
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    mappings = session.exec(
        select(LeadTargetMapping).where(LeadTargetMapping.campaign_id == campaign_id)
    ).all()
    return campaign_results_svc.enrich_mappings(session, campaign_id, mappings)


@router.post(
    "/{application_id}/campaigns/{campaign_id}/review",
    response_model=LeadTargetMappingReviewResult,
)
def review_campaign_mappings(
    application_id: int,
    campaign_id: int,
    payload: LeadTargetMappingReviewRequest,
    session: Session = Depends(get_session),
) -> LeadTargetMappingReviewResult:
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
        result = campaigns_svc.submit_review(
            campaign_id,
            [(d.mapping_id, d.approve) for d in payload.decisions],
        )
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    except campaigns_svc.InvalidReviewDecision as exc:
        raise _bad_request(exc) from exc
    return LeadTargetMappingReviewResult(
        approved=result["approved"], rejected=result["rejected"], copied=0
    )


@router.put(
    "/{application_id}/campaigns/{campaign_id}/mappings/{mapping_id}",
    response_model=LeadTargetMappingOut,
)
def edit_campaign_mapping(
    application_id: int,
    campaign_id: int,
    mapping_id: int,
    payload: LeadTargetMappingEditRequest,
    session: Session = Depends(get_session),
) -> LeadTargetMappingOut:
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
        mapping = correlation_svc.edit_mapping_path(
            campaign_id,
            mapping_id,
            payload.path,
            expected_updated_at=payload.expected_updated_at,
        )
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except correlation_svc.UnknownMappingError as exc:
        raise _conflict(exc) from exc
    return campaign_results_svc.enrich_mappings(session, campaign_id, [mapping])[0]


@router.post(
    "/{application_id}/campaigns/{campaign_id}/targets/{target_id}/supplemental-validate",
    response_model=CampaignDetail,
)
async def supplemental_validate_campaign_target(
    application_id: int,
    campaign_id: int,
    target_id: int,
    payload: CampaignSupplementalValidationRequest,
    session: Session = Depends(get_session),
) -> CampaignDetail:
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        await campaigns_svc.supplemental_validate_target(
            campaign_id,
            target_id,
            set(payload.mapping_ids),
        )
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.post(
    "/{application_id}/campaigns/{campaign_id}/continue",
    response_model=CampaignDetail,
)
async def continue_campaign(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> CampaignDetail:
    try:
        campaign = campaigns_svc.get_campaign(session, application_id, campaign_id)
        await campaigns_svc.continue_to_live_testing(campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc
    except campaigns_svc.InvalidCampaignState as exc:
        raise _conflict(exc) from exc
    session.refresh(campaign)
    return _to_campaign_detail(session, campaign)


@router.get(
    "/{application_id}/campaigns/{campaign_id}/findings",
    response_model=list[CampaignFindingRow],
)
def campaign_findings(
    application_id: int, campaign_id: int, session: Session = Depends(get_session)
) -> list[CampaignFindingRow]:
    """Combined findings across every child run this campaign created.

    Component provenance is resolved through the finding's linked ``ScanLead``
    (``ScanLead.linked_finding_id``) — never guessed from target/host
    matching. A SAST-produced lead's component comes from the frozen
    ``CampaignSourceMember`` for its ``producer_run_id`` (the SastRun); a
    campaign-produced cross-repo lead's components come from
    ``ScanLeadComponentProvenance`` on the *original* lead (the finding's
    linked row is itself a copy imported into the dynamic run, so its own id
    is not the provenance key — the copy is matched back to its original by
    fingerprint, the same identity ``copy_lead_to_run`` uses).
    """
    try:
        campaigns_svc.get_campaign(session, application_id, campaign_id)
    except campaigns_svc.CampaignNotFound as exc:
        raise _not_found(exc) from exc

    return campaign_results_svc.list_campaign_findings(
        session, application_id, campaign_id
    )
