"""API routes for standalone SAST runs and explicit lead imports."""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response as HTTPResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_session
from aespa.models import (
    AgentLog,
    ApiTestRun,
    SastRun,
    ScanLead,
    ScanLog,
)
from aespa.schemas import SastRunSummary, ScanLeadOut
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import run_cleanup

_UTC = timezone.utc

# 25 MiB cap, matching the API-document upload limit.
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024

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
    return SastRunSummary.model_validate(run)


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
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)} MiB upload limit.",
        )
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a valid ZIP archive."
        )

    original_name = Path(file.filename or "source.zip").name or "source.zip"
    base = Path(get_settings().data_dir) / "sast_uploads"
    base.mkdir(parents=True, exist_ok=True)
    ext = Path(original_name).suffix or ".zip"
    stored_path = base / f"{uuid.uuid4().hex}{ext}"
    stored_path.write_bytes(content)

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


# ── Single SAST run ────────────────────────────────────────────────────────────


@router.get("/api/sast-runs/{run_id}", response_model=SastRunSummary)
def get_sast_run(
    run_id: int, session: Session = Depends(get_session)
) -> SastRunSummary:
    return _to_summary(_get_run_or_404(session, run_id))


@router.delete("/api/sast-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sast_run(run_id: int, session: Session = Depends(get_session)) -> None:
    _get_run_or_404(session, run_id)
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
        events_svc.stream(run_id),
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
        .order_by(ScanLog.id)
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
    rows = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "sast")
        .order_by(AgentLog.id)
    ).all()
    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "role": r.role,
            "status": r.status,
            "current_task": r.current_task,
            "outcome": r.outcome,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/api/sast-runs/{run_id}/agent-log/export")
def export_agent_log(
    run_id: int,
    session: Session = Depends(get_session),
) -> HTTPResponse:
    run = _get_run_or_404(session, run_id)
    rows = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "sast")
        .order_by(AgentLog.id)
    ).all()
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
        ts = r.created_at.strftime("%H:%M:%S") if r.created_at else ""
        lines.append(
            f"### `{ts}` [{(r.status or '').upper()}] {r.role} (`{r.agent_id}`)"
        )
        lines.append("")
        if r.current_task:
            lines.append(f"**Task:** {r.current_task}")
            lines.append("")
        if r.outcome:
            lines.append(f"**Outcome:** {r.outcome}")
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
    return [ScanLeadOut.model_validate(lead) for lead in leads]


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
    return [ScanLeadOut.model_validate(lead) for lead in leads]


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
    """Copy one completed SAST run's leads into an API test run."""
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
