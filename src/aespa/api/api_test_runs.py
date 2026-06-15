"""Slice 5: /api/api-test-runs/{id}/* — standalone + alias routes for ApiTestRun.

The ``ApiTestRun`` uses the same integer id space as ``TestRun``.
Alice, events, and agent-log endpoints already key on ``test_run_id`` in
``AliceChatSession``, ``AgentLog``, etc.  We add thin alias routes here so the
frontend can call the same alice/events/agent-log URLs against an ApiTestRun id
without any changes to the underlying services.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response as HTTPResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import (
    AgentLog,
    AliceChatMessage,
    AliceChatSession,
    ApiTestRun,
    ScanFinding,
    ScannerSession,
    TrafficEntry,
)
from aespa.schemas import (
    ApiTestRunSummary,
    ScanFindingImportIn,
    ScanFindingImportResult,
    ScanFindingOut,
    ScannerSessionOut,
    ScannerSessionSummary,
    ScannerSessionUpdate,
)
from aespa.services import alice_tasks
from aespa.services import scanner_sessions as scanner_session_svc

_UTC = timezone.utc

router = APIRouter(prefix="/api/api-test-runs", tags=["api-test-runs"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_run_or_404(session: Session, run_id: int) -> ApiTestRun:
    run = session.get(ApiTestRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API test run not found")
    return run


def _to_summary(run: ApiTestRun) -> ApiTestRunSummary:
    return ApiTestRunSummary.model_validate(run)


# ── Single run ─────────────────────────────────────────────────────────────────

@router.get("/{run_id}", response_model=ApiTestRunSummary)
def get_api_test_run(
    run_id: int, session: Session = Depends(get_session)
) -> ApiTestRunSummary:
    return _to_summary(_get_run_or_404(session, run_id))


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_test_run(run_id: int, session: Session = Depends(get_session)) -> None:
    run = _get_run_or_404(session, run_id)
    for sess in session.exec(select(AliceChatSession).where(AliceChatSession.test_run_id == run_id)).all():
        for msg in session.exec(select(AliceChatMessage).where(AliceChatMessage.session_id == sess.id)).all():
            session.delete(msg)
        session.delete(sess)
    for log in session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "api")
    ).all():
        session.delete(log)
    session.delete(run)
    session.commit()


# ── Alice helper: build sessions payload from DB ──────────────────────────────

def _load_api_sessions(run_id: int, run: ApiTestRun, session: Session) -> dict:
    run_token = run.created_at.isoformat() if run.created_at else None

    sess_rows = session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .order_by(AliceChatSession.position, AliceChatSession.id)
    ).all()

    chats = []
    for s in sess_rows:
        msg_rows = session.exec(
            select(AliceChatMessage)
            .where(AliceChatMessage.session_id == s.id)
            .order_by(AliceChatMessage.position, AliceChatMessage.id)
        ).all()
        chats.append({
            "id": s.session_key,
            "title": s.title,
            "messages": [
                {"id": m.message_key, "sender": m.sender,
                 "type": m.type, "text": m.text, "ts": m.ts}
                for m in msg_rows
            ],
        })

    active = next((s for s in sess_rows if s.is_active), sess_rows[0] if sess_rows else None)
    latest_updated = max((s.updated_at for s in sess_rows), default=None)
    return {
        "chats": chats,
        "active_tab_id": active.session_key if active else "tab-default",
        "updated_at": latest_updated.isoformat() if latest_updated else None,
        "run_created_at": run_token,
    }


class AliceSessionsRequest(BaseModel):
    chats: list[dict]
    active_tab_id: str = "tab-default"


class AliceRunRequest(BaseModel):
    message: str
    history: list[dict] = []
    tab_id: str = "tab-default"
    think_msg_id: str
    reply_msg_id: str


def _save_api_sessions(run_id: int, req: AliceSessionsRequest, session: Session) -> None:
    from aespa.api.alice import AliceSessionsRequest as _AReq, _save_sessions
    # Delegate to the canonical implementation — same DB tables, same logic.
    _save_sessions(run_id, req, session)  # type: ignore[arg-type]


# ── Alice alias routes ─────────────────────────────────────────────────────────

@router.get("/{run_id}/alice/sessions")
def get_alice_sessions(run_id: int, session: Session = Depends(get_session)) -> dict:
    run = _get_run_or_404(session, run_id)
    return _load_api_sessions(run_id, run, session)


@router.put("/{run_id}/alice/sessions")
def save_alice_sessions(
    run_id: int, req: AliceSessionsRequest, session: Session = Depends(get_session)
) -> dict:
    _get_run_or_404(session, run_id)
    _save_api_sessions(run_id, req, session)
    return {"ok": True}


@router.post("/{run_id}/alice/run")
async def start_alice_run(
    run_id: int, req: AliceRunRequest, session: Session = Depends(get_session)
) -> dict:
    _get_run_or_404(session, run_id)
    await alice_tasks.start(
        run_id,
        tab_id=req.tab_id,
        think_msg_id=req.think_msg_id,
        reply_msg_id=req.reply_msg_id,
        message=req.message,
        history=req.history,
        run_type="api",
    )
    return {"ok": True}


@router.get("/{run_id}/alice/stream")
async def alice_stream(
    run_id: int,
    cursor: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    _get_run_or_404(session, run_id)
    return StreamingResponse(
        alice_tasks.stream_events(run_id, cursor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.delete("/{run_id}/alice/run")
async def stop_alice_run(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    stopped = await alice_tasks.stop(run_id)
    return {"ok": True, "stopped": stopped}


@router.get("/{run_id}/alice/status")
def alice_status(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    return alice_tasks.status(run_id)


# ── Events alias ───────────────────────────────────────────────────────────────

@router.get("/{run_id}/events")
def stream_events(run_id: int, session: Session = Depends(get_session)) -> StreamingResponse:
    _get_run_or_404(session, run_id)
    from aespa.services import events as events_svc
    return StreamingResponse(
        events_svc.stream(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ── Agent log alias ────────────────────────────────────────────────────────────

@router.get("/{run_id}/agent-log")
def get_agent_log(run_id: int, session: Session = Depends(get_session)) -> list:
    _get_run_or_404(session, run_id)
    rows = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "api")
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


@router.delete("/{run_id}/agent-log", status_code=204)
def clear_api_agent_log(run_id: int, session: Session = Depends(get_session)) -> None:
    """Delete all persisted agent log entries for this API test run."""
    _get_run_or_404(session, run_id)
    for entry in session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "api")
    ).all():
        session.delete(entry)
    session.commit()


@router.get("/{run_id}/agent-log/export")
def export_api_agent_log(run_id: int, session: Session = Depends(get_session)) -> HTTPResponse:
    """Download the agent activity log for this API test run as a markdown file."""
    run = _get_run_or_404(session, run_id)
    rows = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "api")
        .order_by(AgentLog.id)
    ).all()
    exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# Agent Log — API Test Run #{run_id}",
        "",
        f"Run: {run.name or f'Run #{run_id}'}",
        f"Exported: {exported_at}",
        f"Entries: {len(rows)}",
        "",
        "---",
        "",
    ]
    for r in rows:
        ts = r.created_at.strftime("%H:%M:%S") if r.created_at else ""
        status_upper = (r.status or "").upper()
        lines.append(f"### `{ts}` [{status_upper}] {r.role} (`{r.agent_id}`)")
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
    filename = f"agent-log-api-run-{run_id}.md"
    return HTTPResponse(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Scan start / stop ──────────────────────────────────────────────────────────

class ScanStartIn(BaseModel):
    coverage_mode: str | None = None  # "track" | "enforce"; overrides the run setting


@router.post("/{run_id}/scan/start")
async def start_api_scan(
    run_id: int,
    body: ScanStartIn | None = None,
    session: Session = Depends(get_session),
) -> dict:
    run = _get_run_or_404(session, run_id)
    # Allow the scan-start control to override the run's coverage mode.
    if body and body.coverage_mode in ("track", "enforce"):
        run.coverage_mode = body.coverage_mode
        run.updated_at = datetime.now(timezone.utc)
        session.add(run)
        session.commit()
    from aespa.services import api_scanner
    await api_scanner.start_api_scan(run_id)
    return {"ok": True, "coverage_mode": run.coverage_mode}


@router.post("/{run_id}/scan/stop")
async def stop_api_scan(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import api_scanner
    stopped = await api_scanner.stop_api_scan(run_id)
    return {"ok": True, "stopped": stopped}


@router.get("/{run_id}/scan/status")
def api_scan_status(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import api_scanner
    return api_scanner.get_scan_status(run_id)


# ── Findings alias ─────────────────────────────────────────────────────────────

@router.get("/{run_id}/findings", response_model=list[ScanFindingOut])
def get_api_findings(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[ScanFindingOut]:
    _get_run_or_404(session, run_id)
    findings = session.exec(
        select(ScanFinding).where(ScanFinding.api_test_run_id == run_id)
    ).all()
    _order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings = sorted(findings, key=lambda f: _order.get(f.severity, 5))
    return [ScanFindingOut.model_validate(f) for f in findings]


@router.delete("/{run_id}/findings/{finding_id}", status_code=204)
def delete_api_finding(
    run_id: int,
    finding_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete a single finding belonging to this API test run."""
    _get_run_or_404(session, run_id)
    finding = session.get(ScanFinding, finding_id)
    if finding is None or finding.api_test_run_id != run_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    session.delete(finding)
    session.commit()


@router.delete("/{run_id}/findings", status_code=204)
def clear_api_findings(
    run_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete all findings for this API test run."""
    _get_run_or_404(session, run_id)
    for f in session.exec(
        select(ScanFinding).where(ScanFinding.api_test_run_id == run_id)
    ).all():
        session.delete(f)
    session.commit()


@router.post("/{run_id}/findings/import", response_model=ScanFindingImportResult)
def import_api_findings(
    run_id: int,
    payload: list[ScanFindingImportIn],
    session: Session = Depends(get_session),
) -> ScanFindingImportResult:
    """Import a list of findings into an API test run."""
    run = _get_run_or_404(session, run_id)
    if not payload:
        raise HTTPException(status_code=400, detail="No findings to import")
    allowed_severities = {"critical", "high", "medium", "low", "info"}
    allowed_validation = {"unvalidated", "validating", "confirmed", "unconfirmed", "false_positive"}
    imported: list[ScanFinding] = []
    for item in payload:
        severity = item.severity.lower().strip()
        validation_status = item.validation_status.lower().strip()
        import_validation_status = (
            validation_status
            if validation_status in allowed_validation and validation_status != "validating"
            else "unvalidated"
        )
        finding = ScanFinding(
            test_run_id=None,  # API findings key on api_test_run_id only (see ScanFinding model)
            api_test_run_id=run.id,
            page_id=None,
            owasp_category=(item.owasp_category or "A00").strip()[:32],
            severity=severity if severity in allowed_severities else "info",
            title=item.title.strip() or "Imported finding",
            description=item.description,
            impact=item.impact,
            likelihood=item.likelihood,
            recommendation=item.recommendation,
            cvss_score=item.cvss_score,
            cvss_vector=item.cvss_vector,
            affected_url=item.affected_url,
            evidence=item.evidence,
            request_evidence=item.request_evidence,
            response_evidence=item.response_evidence,
            evidence_json=json.dumps(item.evidence_items),
            finding_source=(item.finding_source or "manual_import").strip()[:64],
            validation_status=import_validation_status,
            validation_note=item.validation_note,
            merged_instances=item.merged_instances,
            poc_command=item.poc_command,
            poc_setup=item.poc_setup,
        )
        session.add(finding)
        session.flush()
        imported.append(finding)
    session.commit()
    for f in imported:
        session.refresh(f)
    return ScanFindingImportResult(
        imported=len(imported),
        findings=[ScanFindingOut.model_validate(f) for f in imported],
    )


# ── Traffic alias ──────────────────────────────────────────────────────────────

@router.get("/{run_id}/traffic")
def get_api_traffic(
    run_id: int,
    since_id: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[dict]:
    _get_run_or_404(session, run_id)
    from aespa.services import traffic as traffic_svc
    return traffic_svc.get_traffic(0, since_id, api_run_id=run_id)


@router.get("/{run_id}/traffic/count")
def get_api_traffic_count(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    _get_run_or_404(session, run_id)
    from aespa.services import traffic as traffic_svc
    return {"count": traffic_svc.count_traffic(0, api_run_id=run_id)}


# ── Coverage matrix ────────────────────────────────────────────────────────────

@router.get("/{run_id}/coverage")
def get_api_coverage_matrix(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import api_scanner
    return api_scanner.get_coverage_matrix(run_id)


# ── Scanner sessions alias ─────────────────────────────────────────────────────

import json as _json  # noqa: E402 — placed after other imports to avoid reorder


def _json_dict(value: str | None) -> dict:
    try:
        parsed = _json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _redacted_metadata(value: dict) -> dict:
    sensitive_terms = ("password", "secret", "token", "cookie", "authorization")
    redacted: dict = {}
    for key, raw in value.items():
        if any(term in str(key).lower() for term in sensitive_terms):
            redacted[key] = "[REDACTED]"
        elif isinstance(raw, dict):
            redacted[key] = _redacted_metadata(raw)
        else:
            redacted[key] = raw
    return redacted


def _scanner_session_out(record: ScannerSession) -> ScannerSessionOut:
    cookies = _json_dict(record.cookies_json)
    headers = _json_dict(record.extra_headers_json)
    metadata = _redacted_metadata(_json_dict(record.session_metadata))
    return ScannerSessionOut(
        id=record.id,
        test_run_id=record.test_run_id,
        label=record.label,
        kind=record.kind,
        username=record.username,
        credential_id=record.credential_id,
        source=record.source,
        cookie_names=sorted(str(k) for k in cookies.keys()),
        header_names=sorted(str(k) for k in headers.keys()),
        token_hint=record.token_hint,
        session_metadata=metadata,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/{run_id}/scanner-sessions", response_model=ScannerSessionSummary)
def get_api_scanner_sessions(
    run_id: int,
    include_inactive: bool = False,
    session: Session = Depends(get_session),
) -> ScannerSessionSummary:
    _get_run_or_404(session, run_id)
    query = select(ScannerSession).where(ScannerSession.test_run_id == run_id)
    if not include_inactive:
        query = query.where(ScannerSession.is_active == True)  # noqa: E712
    records = session.exec(query.order_by(ScannerSession.label)).all()
    counts: dict[str, int] = {"total": len(records)}
    for record in records:
        counts[record.kind] = counts.get(record.kind, 0) + 1
        if record.is_active:
            counts["active"] = counts.get("active", 0) + 1
        else:
            counts["inactive"] = counts.get("inactive", 0) + 1
    return ScannerSessionSummary(
        counts=counts,
        sessions=[_scanner_session_out(record) for record in records],
    )


@router.patch("/{run_id}/scanner-sessions/{session_id}", response_model=ScannerSessionOut)
def update_api_scanner_session(
    run_id: int,
    session_id: int,
    payload: ScannerSessionUpdate,
    session: Session = Depends(get_session),
) -> ScannerSessionOut:
    _get_run_or_404(session, run_id)
    record = session.get(ScannerSession, session_id)
    if record is None or record.test_run_id != run_id:
        raise HTTPException(status_code=404, detail=f"ScannerSession {session_id} not found")

    if payload.label is not None:
        normalized = scanner_session_svc.stable_label(payload.label)
        if not normalized:
            raise HTTPException(status_code=400, detail="Session label cannot be blank")
        duplicate = session.exec(
            select(ScannerSession)
            .where(ScannerSession.test_run_id == run_id)
            .where(ScannerSession.label == normalized)
            .where(ScannerSession.id != session_id)
        ).first()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail=f"Session label '{normalized}' already exists")
        record.label = normalized
    if payload.is_active is not None:
        record.is_active = payload.is_active
    from aespa.models import _utcnow
    record.updated_at = _utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    return _scanner_session_out(record)
