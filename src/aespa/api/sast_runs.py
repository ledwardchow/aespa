"""API routes for SAST runs: /api/sast-runs/* and /api/api-collections/{id}/sast-runs."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response as HTTPResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import AgentLog, ApiCollection, ApiDocument, SastRun, ScanLead, ScanLog
from aespa.schemas import SastRunSummary, ScanLeadOut
from aespa.services import events as events_svc

_UTC = timezone.utc

router = APIRouter(tags=["sast-runs"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_run_or_404(session: Session, run_id: int) -> SastRun:
    run = session.get(SastRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SAST run not found")
    return run


def _to_summary(run: SastRun) -> SastRunSummary:
    return SastRunSummary.model_validate(run)


# ── Create a SAST run under a collection ──────────────────────────────────────

class SastRunCreate(BaseModel):
    name: str | None = None
    document_id: int | None = None
    llm_config_id: int | None = None


@router.post(
    "/api/api-collections/{collection_id}/sast-runs",
    response_model=SastRunSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_sast_run(
    collection_id: int,
    body: SastRunCreate | None = None,
    session: Session = Depends(get_session),
) -> SastRunSummary:
    coll = session.get(ApiCollection, collection_id)
    if coll is None:
        raise HTTPException(status_code=404, detail="API collection not found")

    body = body or SastRunCreate()
    name = body.name or f"SAST – {coll.name}"

    # Resolve document_id: use supplied, else find most recent source_zip.
    doc_id: int | None = body.document_id
    if doc_id is None:
        doc = session.exec(
            select(ApiDocument)
            .where(ApiDocument.collection_id == collection_id)
            .where(ApiDocument.doc_type == "source_zip")
            .order_by(ApiDocument.id.desc())  # type: ignore[attr-defined]
        ).first()
        if doc is None:
            raise HTTPException(
                status_code=400,
                detail="No source_zip document found for this collection. Upload one first.",
            )
        doc_id = doc.id

    run = SastRun(
        collection_id=collection_id,
        document_id=doc_id,
        name=name,
        llm_config_id=body.llm_config_id,
        status="pending",
        created_at=datetime.now(_UTC),
        updated_at=datetime.now(_UTC),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return _to_summary(run)


@router.get(
    "/api/api-collections/{collection_id}/sast-runs",
    response_model=list[SastRunSummary],
)
def list_sast_runs(
    collection_id: int,
    session: Session = Depends(get_session),
) -> list[SastRunSummary]:
    coll = session.get(ApiCollection, collection_id)
    if coll is None:
        raise HTTPException(status_code=404, detail="API collection not found")
    runs = session.exec(
        select(SastRun)
        .where(SastRun.collection_id == collection_id)
        .order_by(SastRun.id.desc())  # type: ignore[attr-defined]
    ).all()
    return [_to_summary(r) for r in runs]


# ── Global SAST runs list ──────────────────────────────────────────────────────

@router.get("/api/sast-runs", response_model=list[SastRunSummary])
def list_all_sast_runs(session: Session = Depends(get_session)) -> list[SastRunSummary]:
    runs = session.exec(
        select(SastRun).order_by(SastRun.id.desc())  # type: ignore[attr-defined]
    ).all()
    return [_to_summary(r) for r in runs]


# ── Single SAST run ────────────────────────────────────────────────────────────

@router.get("/api/sast-runs/{run_id}", response_model=SastRunSummary)
def get_sast_run(run_id: int, session: Session = Depends(get_session)) -> SastRunSummary:
    return _to_summary(_get_run_or_404(session, run_id))


@router.delete("/api/sast-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sast_run(run_id: int, session: Session = Depends(get_session)) -> None:
    run = _get_run_or_404(session, run_id)
    for lead in session.exec(
        select(ScanLead).where(ScanLead.producer_run_id == run_id)
    ).all():
        session.delete(lead)
    for log_entry in session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "sast")
    ).all():
        session.delete(log_entry)
    session.delete(run)
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
        lines.append(f"### `{ts}` [{(r.status or '').upper()}] {r.role} (`{r.agent_id}`)")
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
        headers={"Content-Disposition": f'attachment; filename="agent-log-sast-{run_id}.md"'},
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
        .order_by(ScanLead.id)
    ).all()
    return [ScanLeadOut.model_validate(lead) for lead in leads]


@router.get("/api/api-test-runs/{run_id}/leads", response_model=list[ScanLeadOut])
def get_api_run_leads(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[ScanLeadOut]:
    """Return open ScanLeads for the collection associated with an API test run."""
    from aespa.models import ApiTestRun
    api_run = session.get(ApiTestRun, run_id)
    if api_run is None:
        raise HTTPException(status_code=404, detail="API test run not found")
    leads = session.exec(
        select(ScanLead)
        .where(ScanLead.collection_id == api_run.collection_id)
        .order_by(ScanLead.id)
    ).all()
    return [ScanLeadOut.model_validate(lead) for lead in leads]
