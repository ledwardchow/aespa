"""API routes for standalone SAST runs and explicit lead imports."""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.responses import Response as HTTPResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_session
from aespa.models import (
    AgentLog,
    ApiCollection,
    ApiTestRun,
    PhaseCheckpoint,
    SastRun,
    SastWorker,
    ScanFinding,
    ScanLead,
    ScanLog,
    Site,
    TestRun,
)
from aespa.schemas import SastRunSummary, SastRunUpdate, ScanLeadOut
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import run_cleanup, sast_export
from aespa.services.references import ensure_finding_reference, ensure_lead_reference

_UTC = timezone.utc

# Keep standalone uploads aligned with SAST export/import archives.
_MAX_UPLOAD_BYTES = 250 * 1024 * 1024
_UPLOAD_CHUNK_BYTES = 1024 * 1024

router = APIRouter(tags=["sast-runs"])


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_run_or_404(session: Session, run_id: int) -> SastRun:
    run = session.get(SastRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SAST run not found"
        )
    return run


def _to_summary(run: SastRun) -> SastRunSummary:
    summary = SastRunSummary.model_validate(run)
    if run.id is None:
        return summary

    # The task registry is authoritative while a scan is active. A previous
    # terminal DB status can otherwise briefly leak into list/detail responses
    # while a rerun is already in progress.
    from aespa.services import sast_scanner

    if sast_scanner.is_sast_scan_running(run.id):
        return summary.model_copy(update={"status": "scanning"})
    return summary


def _sast_agent_activity(session: Session, run_id: int) -> list[dict]:
    """Return persisted agent events plus lifecycle history for older workers."""
    rows = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "sast")
        .order_by(AgentLog.id)
    ).all()
    entries = [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "role": r.role,
            "status": r.status,
            "current_task": r.current_task,
            "outcome": r.outcome,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    recorded_statuses: dict[str, set[str]] = {}
    for entry in entries:
        recorded_statuses.setdefault(entry["agent_id"], set()).add(entry["status"])

    workers = session.exec(
        select(SastWorker)
        .where(SastWorker.sast_run_id == run_id)
        .order_by(SastWorker.id)
    ).all()
    for worker in workers:
        agent_id = f"sast-worker-{worker.id}"
        statuses = recorded_statuses.get(agent_id, set())
        role = f"SAST {worker.class_group.replace('_', ' ').title()} Worker"
        lifecycle_times = [
            value
            for value in (worker.created_at, worker.started_at, worker.completed_at)
            if value is not None
        ]
        spawned_at = min(lifecycle_times) if lifecycle_times else worker.created_at
        if "spawned" not in statuses:
            entries.append(
                {
                    "id": f"{agent_id}-spawned",
                    "agent_id": agent_id,
                    "role": role,
                    "status": "spawned",
                    "current_task": f"Queued analysis worker {worker.worker_key}",
                    "outcome": None,
                    "created_at": spawned_at,
                }
            )
        if worker.started_at and "active" not in statuses:
            entries.append(
                {
                    "id": f"{agent_id}-active",
                    "agent_id": agent_id,
                    "role": role,
                    "status": "active",
                    "current_task": f"Started analysis worker {worker.worker_key}",
                    "outcome": None,
                    "created_at": min(
                        value
                        for value in (worker.started_at, worker.completed_at)
                        if value is not None
                    ),
                }
            )
        if worker.completed_at and worker.status not in statuses:
            outcome = worker.error_message or worker.summary or None
            entries.append(
                {
                    "id": f"{agent_id}-{worker.status}",
                    "agent_id": agent_id,
                    "role": role,
                    "status": worker.status,
                    "current_task": f"Analysis finished for {worker.worker_key}",
                    "outcome": outcome[:500] if outcome else None,
                    "created_at": worker.completed_at,
                }
            )

    validator_checkpoints = session.exec(
        select(PhaseCheckpoint)
        .where(PhaseCheckpoint.run_kind == "sast")
        .where(PhaseCheckpoint.run_id == run_id)
        .where(PhaseCheckpoint.phase == "validation")
        .order_by(PhaseCheckpoint.id)
    ).all()
    for checkpoint in validator_checkpoints:
        worker_key = checkpoint.idempotency_key.removeprefix("agent:")
        if not worker_key.startswith("validator:"):
            continue
        candidate_id = worker_key.partition(":")[2]
        agent_id = f"sast-validator-{candidate_id}"
        if "complete" in recorded_statuses.get(agent_id, set()):
            continue
        entries.append(
            {
                "id": f"{agent_id}-checkpoint",
                "agent_id": agent_id,
                "role": "SAST Candidate Validator",
                "status": "complete",
                "current_task": f"Validated candidate {candidate_id}",
                "outcome": "Recovered from the saved validator checkpoint",
                "created_at": checkpoint.completed_at,
            }
        )

    status_order = {"spawned": 0, "active": 1}
    entries.sort(
        key=lambda entry: (
            entry["created_at"].isoformat() if entry["created_at"] else "",
            status_order.get(entry["status"], 2),
            str(entry["id"]),
        )
    )
    return entries


# ── Standalone SAST run (upload archive + create, no collection) ──────────────


@router.post(
    "/api/sast-runs",
    response_model=SastRunSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_standalone_sast_run(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    llm_config_id: int | None = Form(default=None),
    llm_profile_id: int | None = Form(default=None),
    session: Session = Depends(get_session),
) -> SastRunSummary:
    """Create a standalone SAST run from an uploaded source archive.

    Not tied to an API collection — used by the SAST screen and consumed by web
    or API test runs, which explicitly import copies of the resulting leads.
    """
    original_name = Path(file.filename or "source.zip").name or "source.zip"
    base = Path(get_settings().data_dir) / "sast_uploads"
    base.mkdir(parents=True, exist_ok=True)
    ext = Path(original_name).suffix or ".zip"
    upload_id = uuid.uuid4().hex
    temp_path = base / f".{upload_id}.upload"
    stored_path = base / f"{upload_id}{ext}"
    bytes_written = 0
    try:
        with temp_path.open("wb") as destination:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > _MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"File exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)} MiB "
                            "upload limit."
                        ),
                    )
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

    from aespa.services import sast_scanner

    if llm_profile_id is not None:
        from aespa.models import LLMProfile

        if session.get(LLMProfile, llm_profile_id) is None:
            raise HTTPException(status_code=404, detail="Scan profile not found")

    run = sast_scanner.create_sast_run(
        collection_id=None,
        name=name or f"SAST – {original_name}",
        source_archive_path=str(stored_path),
        source_filename=original_name,
        llm_config_id=llm_config_id,
        llm_profile_id=llm_profile_id,
    )
    return _to_summary(run)


# ── Global SAST runs list ──────────────────────────────────────────────────────


@router.get("/api/sast-runs", response_model=list[SastRunSummary])
def list_all_sast_runs(session: Session = Depends(get_session)) -> list[SastRunSummary]:
    runs = session.exec(
        select(SastRun).order_by(SastRun.id.desc())  # type: ignore[attr-defined]
    ).all()
    return [_to_summary(r) for r in runs]


@router.get("/api/sast-runs/{run_id}/export")
def export_sast_run(
    run_id: int, session: Session = Depends(get_session)
) -> JSONResponse:
    """Download a complete, portable SAST run bundle."""
    try:
        bundle = sast_export.export_sast_run(session, run_id)
    except sast_export.SastExportError as exc:
        detail = str(exc)
        code = 404 if "does not exist" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc
    name = bundle["sast_run"].get("name") or f"sast-run-{run_id}"
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return JSONResponse(
        content=bundle,
        headers={
            "Content-Disposition": f'attachment; filename="{safe}.aespa-sast.json"'
        },
    )


@router.post(
    "/api/sast-runs/import",
    response_model=SastRunSummary,
    status_code=status.HTTP_201_CREATED,
)
async def import_sast_run(
    request: Request, session: Session = Depends(get_session)
) -> SastRunSummary:
    """Restore a complete SAST run from a bundle produced by the export route."""
    try:
        bundle = json.loads(await request.body())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON body: {exc}",
        ) from exc
    try:
        run = sast_export.import_sast_run(session, bundle)
    except sast_export.SastExportError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return _to_summary(run)


# ── Single SAST run ────────────────────────────────────────────────────────────


@router.get("/api/sast-runs/{run_id}", response_model=SastRunSummary)
def get_sast_run(
    run_id: int, session: Session = Depends(get_session)
) -> SastRunSummary:
    return _to_summary(_get_run_or_404(session, run_id))


@router.patch("/api/sast-runs/{run_id}", response_model=SastRunSummary)
def update_sast_run(
    run_id: int,
    payload: SastRunUpdate,
    session: Session = Depends(get_session),
) -> SastRunSummary:
    """Change the model profile used by the next SAST scan or rerun."""
    run = _get_run_or_404(session, run_id)
    from aespa.services import sast_scanner

    if run.status == "scanning" or sast_scanner.is_sast_scan_running(run_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change the model profile while the SAST scan is running",
        )
    if payload.llm_profile_id is not None:
        from aespa.models import LLMProfile

        if session.get(LLMProfile, payload.llm_profile_id) is None:
            raise HTTPException(status_code=404, detail="Scan profile not found")
    run.llm_profile_id = payload.llm_profile_id
    run.updated_at = datetime.now(_UTC)
    session.add(run)
    session.commit()
    session.refresh(run)
    return _to_summary(run)


def _json_object(value: str | None, default: dict) -> dict:
    try:
        parsed = json.loads(value or "")
    except (TypeError, ValueError):
        return default
    return parsed if isinstance(parsed, dict) else default


@router.get("/api/sast-runs/{run_id}/analysis")
def get_sast_analysis(run_id: int, session: Session = Depends(get_session)) -> dict:
    """Return authoritative phase, coverage, and report state for the UI."""
    run = _get_run_or_404(session, run_id)
    from aespa.services.sast_scanner import _empty_phase_state
    from aespa.services.sast_workprogram import completion_decision

    completion_status, completion_reasons, work_program = completion_decision(run_id)

    return {
        "phases": _json_object(run.phase_state_json, _empty_phase_state()),
        "coverage": _json_object(
            run.coverage_json,
            {"files": [], "summary": {"files_total": 0, "files_reviewed": 0}},
        ),
        "report": _json_object(run.report_json, {}),
        "work_program": work_program,
        "assurance": {
            "status": completion_status,
            "reasons": completion_reasons,
        },
    }


@router.delete("/api/sast-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sast_run(run_id: int, session: Session = Depends(get_session)) -> None:
    _get_run_or_404(session, run_id)
    from aespa.services import campaigns as campaigns_svc
    from aespa.services import sast_scanner

    await campaigns_svc.stop_member_tasks_for_run("sast", run_id)
    if sast_scanner.is_sast_scan_running(run_id):
        await sast_scanner.stop_sast_scan_and_wait(run_id)
    run_cleanup.cascade_delete_sast_run(session, run_id)
    session.commit()


# ── Start / Stop / Status ──────────────────────────────────────────────────────


@router.post("/api/sast-runs/{run_id}/scan/start")
async def start_sast_scan(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import sast_scanner

    await sast_scanner.start_sast_scan(run_id)
    return {"ok": True}


@router.post("/api/sast-runs/{run_id}/scan/stop")
async def stop_sast_scan(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import sast_scanner

    stopped = await sast_scanner.stop_sast_scan(run_id)
    return {"ok": True, "stopped": stopped}


@router.post("/api/sast-runs/{run_id}/scan/pause")
async def pause_sast_scan(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Pause an active SAST scan after its current provider step."""
    _get_run_or_404(session, run_id)
    from aespa.services import sast_scanner

    paused = await sast_scanner.pause_sast_scan_and_wait(run_id)
    if not paused:
        raise HTTPException(status_code=409, detail="SAST scan is not running")
    return {"ok": True, "pause_requested": True}


@router.post("/api/sast-runs/{run_id}/scan/resume")
async def resume_sast_scan(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Resume a user, network, quota, or restart-paused SAST scan."""
    from aespa.services import sast_scanner

    _get_run_or_404(session, run_id)
    from aespa.services import run_pause as run_pause_svc

    run = session.get(SastRun, run_id)
    pause = run_pause_svc.get_pause("sast", run_id)
    if run is None or pause is None or run.status != "paused":
        raise HTTPException(status_code=409, detail="SAST scan is not paused")
    if sast_scanner.is_sast_scan_running(run_id):
        raise HTTPException(status_code=409, detail="SAST scan is already running")
    if pause.reset_at and pause.reset_at > datetime.now(_UTC):
        raise HTTPException(
            status_code=409,
            detail={"message": pause.message, "reset_at": pause.reset_at.isoformat()},
        )
    await sast_scanner.start_sast_scan(run_id, resume=True)
    run_pause_svc.clear_pause("sast", run_id)
    return sast_scanner.get_sast_status(run_id)


@router.get("/api/sast-runs/{run_id}/scan/status")
def sast_scan_status(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import sast_scanner

    return sast_scanner.get_sast_status(run_id)


# ── SSE event stream ───────────────────────────────────────────────────────────


@router.get("/api/sast-runs/{run_id}/events")
def stream_events(
    run_id: int,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    _get_run_or_404(session, run_id)
    return StreamingResponse(
        events_svc.stream(run_id, run_kind="sast"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/api/sast-runs/{run_id}/token-usage")
def get_token_usage(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Return accumulated LLM token usage for this SAST run."""
    _get_run_or_404(session, run_id)
    return llm_svc.get_run_token_usage(run_id, run_kind="sast")


# ── Agent log ─────────────────────────────────────────────────────────────────


@router.get("/api/sast-runs/{run_id}/scan-log")
def get_scan_log(
    run_id: int,
    session: Session = Depends(get_session),
) -> list:
    _get_run_or_404(session, run_id)
    rows = session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.run_kind == "sast")
        .order_by(ScanLog.created_at, ScanLog.id)
    ).all()
    return [
        {
            "id": r.id,
            "phase": r.phase,
            "status": r.status,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/api/sast-runs/{run_id}/agent-log")
def get_agent_log(
    run_id: int,
    session: Session = Depends(get_session),
) -> list:
    _get_run_or_404(session, run_id)
    rows = _sast_agent_activity(session, run_id)
    return [
        {
            **r,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@router.get("/api/sast-runs/{run_id}/agent-log/export")
def export_agent_log(
    run_id: int,
    session: Session = Depends(get_session),
) -> HTTPResponse:
    run = _get_run_or_404(session, run_id)
    rows = _sast_agent_activity(session, run_id)
    exported_at = datetime.now(_UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# Agent Log — SAST Run #{run_id}",
        "",
        f"Run: {run.name}",
        f"Exported: {exported_at}",
        f"Entries: {len(rows)}",
        "",
        "---",
        "",
    ]
    for r in rows:
        created_at = r["created_at"]
        ts = created_at.strftime("%H:%M:%S") if created_at else ""
        lines.append(
            f"### `{ts}` [{(r['status'] or '').upper()}] {r['role']} (`{r['agent_id']}`)"
        )
        lines.append("")
        if r["current_task"]:
            lines.append(f"**Task:** {r['current_task']}")
            lines.append("")
        if r["outcome"]:
            lines.append(f"**Outcome:** {r['outcome']}")
            lines.append("")
        lines.append("---")
        lines.append("")
    md = "\n".join(lines)
    return HTTPResponse(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="agent-log-sast-{run_id}.md"'
        },
    )


# ── Leads ─────────────────────────────────────────────────────────────────────


@router.get("/api/sast-runs/{run_id}/leads", response_model=list[ScanLeadOut])
def get_sast_leads(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[ScanLeadOut]:
    _get_run_or_404(session, run_id)
    leads = session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_id == run_id)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711 — originals only
        .order_by(ScanLead.id)
    ).all()
    finding_ids = {lead.linked_finding_id for lead in leads if lead.linked_finding_id}
    linked_findings = (
        session.exec(select(ScanFinding).where(ScanFinding.id.in_(finding_ids))).all()
        if finding_ids
        else []
    )
    for finding in linked_findings:
        ensure_finding_reference(session, finding)
    finding_refs = {finding.id: finding.reference for finding in linked_findings}
    for lead in leads:
        ensure_lead_reference(session, lead)
    session.commit()
    return [
        ScanLeadOut.model_validate(lead).model_copy(
            update={
                "linked_finding_reference": finding_refs.get(lead.linked_finding_id)
            }
        )
        for lead in leads
    ]


@router.get("/api/sast-runs/{run_id}/handoff-targets")
def get_sast_handoff_targets(
    run_id: int, session: Session = Depends(get_session)
) -> list[dict]:
    """List dynamic runs that can receive a validated static lead."""
    _get_run_or_404(session, run_id)
    targets: list[dict] = []
    web_runs = session.exec(
        select(TestRun).order_by(TestRun.id.desc()).limit(100)
    ).all()  # type: ignore[attr-defined]
    for run in web_runs:
        site = session.get(Site, run.site_id)
        targets.append(
            {
                "run_type": "web",
                "run_id": run.id,
                "name": run.name,
                "target": site.name if site else f"Site #{run.site_id}",
                "status": run.status,
            }
        )
    api_runs = session.exec(
        select(ApiTestRun).order_by(ApiTestRun.id.desc()).limit(100)  # type: ignore[attr-defined]
    ).all()
    for run in api_runs:
        collection = session.get(ApiCollection, run.collection_id)
        targets.append(
            {
                "run_type": "api",
                "run_id": run.id,
                "name": run.name,
                "target": (
                    collection.name
                    if collection
                    else f"API collection #{run.collection_id}"
                ),
                "status": run.status,
            }
        )
    return targets


class SastLeadHandoffRequest(BaseModel):
    run_type: str
    run_id: int


@router.post("/api/sast-runs/{run_id}/leads/{lead_id}/handoff")
def handoff_sast_lead(
    run_id: int,
    lead_id: int,
    body: SastLeadHandoffRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Queue one validated lead into an explicitly selected dynamic run.

    Campaign-owned sources and targets are valid because this only creates an
    independent lead copy; it does not alter the run lifecycle or source lead.
    """
    _get_run_or_404(session, run_id)
    lead = session.get(ScanLead, lead_id)
    if (
        lead is None
        or lead.producer_run_id != run_id
        or lead.imported_into_run_id is not None
    ):
        raise HTTPException(status_code=404, detail="SAST lead not found")
    if not lead.reportable or lead.validation_status != "confirmed":
        raise HTTPException(
            status_code=409,
            detail="Only independently validated reportable leads can be handed off",
        )
    if body.run_type == "web":
        target = session.get(TestRun, body.run_id)
    elif body.run_type == "api":
        target = session.get(ApiTestRun, body.run_id)
    else:
        raise HTTPException(status_code=422, detail="run_type must be web or api")
    if target is None:
        raise HTTPException(status_code=404, detail="Dynamic target run not found")

    from aespa.services.scan_leads import copy_lead_to_run

    copied = copy_lead_to_run(lead_id, body.run_type, body.run_id)
    return {
        "queued": True,
        "lead_id": copied.id,
        "lead_reference": copied.reference,
        "source_reference": lead.reference,
        "run_type": body.run_type,
        "run_id": body.run_id,
    }


@router.get("/api/api-test-runs/{run_id}/leads", response_model=list[ScanLeadOut])
def get_api_run_leads(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[ScanLeadOut]:
    """Return only the SAST-lead copies owned by this API test run."""
    api_run = session.get(ApiTestRun, run_id)
    if api_run is None:
        raise HTTPException(status_code=404, detail="API test run not found")
    leads = session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_type == "api")
        .where(ScanLead.imported_into_run_id == run_id)
        .order_by(ScanLead.id)
    ).all()
    finding_ids = {lead.linked_finding_id for lead in leads if lead.linked_finding_id}
    linked_findings = (
        session.exec(select(ScanFinding).where(ScanFinding.id.in_(finding_ids))).all()
        if finding_ids
        else []
    )
    for finding in linked_findings:
        ensure_finding_reference(session, finding)
    finding_refs = {finding.id: finding.reference for finding in linked_findings}
    for lead in leads:
        ensure_lead_reference(session, lead)
    session.commit()
    return [
        ScanLeadOut.model_validate(lead).model_copy(
            update={
                "linked_finding_reference": finding_refs.get(lead.linked_finding_id)
            }
        )
        for lead in leads
    ]


@router.get("/api/api-test-runs/{run_id}/sast-runs/available")
def list_api_run_available_sast_runs(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[dict]:
    """Completed standalone SAST runs available for explicit lead import."""
    if session.get(ApiTestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="API test run not found")
    runs = session.exec(
        select(SastRun)
        .where(SastRun.status == "completed")
        .where(SastRun.leads_count > 0)
        .order_by(SastRun.id.desc())  # type: ignore[attr-defined]
    ).all()
    return [
        {
            "id": run.id,
            "name": run.name,
            "leads_count": run.leads_count,
            "source_filename": run.source_filename,
            "completed_at": (
                run.completed_at.isoformat() if run.completed_at else None
            ),
        }
        for run in runs
    ]


class ApiImportLeadsRequest(BaseModel):
    sast_run_id: int


@router.post("/api/api-test-runs/{run_id}/import-leads")
def import_api_run_sast_leads(
    run_id: int,
    body: ApiImportLeadsRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Copy one completed SAST run's leads into an API test run.

    Campaign ownership does not block lead copies: the source remains
    immutable and the destination receives separately owned investigation rows.
    """
    if session.get(ApiTestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="API test run not found")
    sast_run = session.get(SastRun, body.sast_run_id)
    if sast_run is None:
        raise HTTPException(status_code=404, detail="SAST run not found")
    if sast_run.status != "completed":
        raise HTTPException(status_code=409, detail="SAST run is not completed")

    from aespa.services.scan_leads import copy_leads_to_run

    imported = copy_leads_to_run(body.sast_run_id, "api", run_id)
    return {"imported": imported}


@router.delete(
    "/api/api-test-runs/{run_id}/leads",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_api_run_leads(
    run_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete all imported leads owned by an API run, preserving originals."""
    if session.get(ApiTestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="API test run not found")
    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_type == "api")
        .where(ScanLead.imported_into_run_id == run_id)
    ).all():
        session.delete(lead)
    session.commit()


@router.delete(
    "/api/api-test-runs/{run_id}/leads/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_api_run_lead(
    run_id: int,
    lead_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete one lead owned by an API run, preserving the SAST original."""
    if session.get(ApiTestRun, run_id) is None:
        raise HTTPException(status_code=404, detail="API test run not found")
    lead = session.get(ScanLead, lead_id)
    if (
        lead is None
        or lead.imported_into_run_type != "api"
        or lead.imported_into_run_id != run_id
    ):
        raise HTTPException(status_code=404, detail="Lead not found for this run")
    session.delete(lead)
    session.commit()
