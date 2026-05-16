"""Scan API — start/stop/status/findings/validation endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response as HTTPResponse
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import CrawledPage, ScanFinding, ScanLog, TestRun, TestRunStatus
from aespa.schemas import (
    ScanFindingDeduplicationResult,
    ScanFindingImportIn,
    ScanFindingImportResult,
    ScanFindingOut,
    ScanStatusOut,
    ValidationStatusOut,
)
from aespa.services import findings as findings_svc
from aespa.services import scanner as scanner_svc
from aespa.services import validator as validator_svc
from aespa.services.settings import get_llm_config_for_run

router = APIRouter(tags=["scan"])


def _get_run_or_404(session: Session, run_id: int) -> TestRun:
    run = session.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return run


@router.post("/api/test-runs/{run_id}/scan/start", response_model=ScanStatusOut)
async def start_scan(run_id: int, session: Session = Depends(get_session)) -> ScanStatusOut:
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Crawl is still running — wait for it to finish")
    if scanner_svc.is_running(run_id):
        raise HTTPException(status_code=409, detail="Scan already running")
    if scanner_svc.is_thinking_running(run_id):
        raise HTTPException(status_code=409, detail="Dynamic Scan already running")
    await scanner_svc.start_scan(run_id)
    return ScanStatusOut(**scanner_svc.get_scan_status(run_id))


@router.post("/api/test-runs/{run_id}/thinking-scan/start")
async def start_thinking_scan(run_id: int, session: Session = Depends(get_session)) -> dict:
    """Start an LLM-directed scan that dynamically chooses what to test next."""
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Crawl is still running — wait for it to finish")
    if scanner_svc.is_running(run_id):
        raise HTTPException(status_code=409, detail="Scan already running")
    if scanner_svc.is_thinking_running(run_id):
        raise HTTPException(status_code=409, detail="Dynamic Scan already running")
    await scanner_svc.start_thinking_scan(run_id)
    return scanner_svc.get_thinking_scan_status(run_id)


@router.post("/api/test-runs/{run_id}/thinking-scan/stop")
def stop_thinking_scan(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    scanner_svc.request_thinking_stop(run_id)
    return scanner_svc.get_thinking_scan_status(run_id)


@router.get("/api/test-runs/{run_id}/thinking-scan/status")
def thinking_scan_status(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    return scanner_svc.get_thinking_scan_status(run_id)


@router.post("/api/test-runs/{run_id}/pages/{page_id}/scan", response_model=ScanStatusOut)
async def scan_single_page(
    run_id: int,
    page_id: int,
    session: Session = Depends(get_session),
) -> ScanStatusOut:
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Crawl is still running")
    if scanner_svc.is_running(run_id):
        raise HTTPException(status_code=409, detail="Scan already running")
    if scanner_svc.is_thinking_running(run_id):
        raise HTTPException(status_code=409, detail="Dynamic Scan already running")
    page = session.get(CrawledPage, page_id)
    if page is None or page.test_run_id != run_id:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.in_scope is False:
        raise HTTPException(status_code=409, detail="Page is out of scope")
    await scanner_svc.start_scan(run_id, page_ids=[page_id])
    return ScanStatusOut(**scanner_svc.get_scan_status(run_id))


@router.post("/api/test-runs/{run_id}/scan/stop", response_model=ScanStatusOut)
def stop_scan(run_id: int, session: Session = Depends(get_session)) -> ScanStatusOut:
    _get_run_or_404(session, run_id)
    scanner_svc.request_stop(run_id)
    return ScanStatusOut(**scanner_svc.get_scan_status(run_id))


@router.get("/api/test-runs/{run_id}/scan/status", response_model=ScanStatusOut)
def scan_status(run_id: int, session: Session = Depends(get_session)) -> ScanStatusOut:
    _get_run_or_404(session, run_id)
    return ScanStatusOut(**scanner_svc.get_scan_status(run_id))


@router.delete("/api/test-runs/{run_id}/findings/{finding_id}", status_code=204)
def delete_finding(
    run_id: int,
    finding_id: int,
    session: Session = Depends(get_session),
) -> None:
    _get_run_or_404(session, run_id)
    finding = session.get(ScanFinding, finding_id)
    if finding is None or finding.test_run_id != run_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    session.delete(finding)
    session.commit()


@router.delete("/api/test-runs/{run_id}/findings", status_code=204)
def delete_findings_group(
    run_id: int,
    title: str | None = Query(default=None, description="Delete all findings with this title. Omit to clear ALL findings."),
    session: Session = Depends(get_session),
) -> None:
    """Delete findings for this run.  If *title* is supplied, only that group is
    removed.  If omitted, **all** findings are deleted and every page's
    scan_status is reset to 'pending' so the scanner can re-run from scratch."""
    _get_run_or_404(session, run_id)
    if title is not None:
        findings = session.exec(
            select(ScanFinding)
            .where(ScanFinding.test_run_id == run_id)
            .where(ScanFinding.title == title)
        ).all()
    else:
        findings = session.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all()
        # Reset pages so the scanner can run again cleanly.
        for page in session.exec(
            select(CrawledPage).where(CrawledPage.test_run_id == run_id)
        ).all():
            page.scan_status = "pending"
            session.add(page)
    for f in findings:
        session.delete(f)
    session.commit()


@router.get("/api/test-runs/{run_id}/findings", response_model=list[ScanFindingOut])
def get_findings(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[ScanFindingOut]:
    _get_run_or_404(session, run_id)
    findings = session.exec(
        select(ScanFinding).where(ScanFinding.test_run_id == run_id)
    ).all()
    # Sort: critical → high → medium → low → info
    _order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings = sorted(findings, key=lambda f: _order.get(f.severity, 5))
    return [ScanFindingOut.model_validate(f) for f in findings]


@router.post(
    "/api/test-runs/{run_id}/findings/deduplicate",
    response_model=ScanFindingDeduplicationResult,
)
async def deduplicate_findings(
    run_id: int,
    session: Session = Depends(get_session),
) -> ScanFindingDeduplicationResult:
    run = _get_run_or_404(session, run_id)
    llm_cfg = get_llm_config_for_run(session, run)
    result = await findings_svc.deduplicate_findings(session, run_id, llm_cfg)
    return ScanFindingDeduplicationResult(
        total_before=result.total_before,
        total_after=result.total_after,
        removed=result.removed,
        llm_used=result.llm_used,
        groups=[group.__dict__ for group in result.groups],
    )


def _page_for_imported_finding(
    session: Session,
    run: TestRun,
    affected_url: str,
) -> CrawledPage:
    page_url = (affected_url or "").strip() or f"imported-finding://run/{run.id}"
    page = session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == run.id)
        .where(CrawledPage.url == page_url)
    ).first()
    if page:
        return page

    page = CrawledPage(
        test_run_id=run.id,
        url=page_url,
        title="Imported issue target",
        llm_context="Created during issue import.",
        depth=0,
        status="crawled",
        in_scope=True,
        scan_status="complete",
    )
    session.add(page)
    session.flush()
    run.pages_discovered = (run.pages_discovered or 0) + 1
    session.add(run)
    return page


@router.post(
    "/api/test-runs/{run_id}/findings/import",
    response_model=ScanFindingImportResult,
)
def import_findings(
    run_id: int,
    payload: list[ScanFindingImportIn],
    session: Session = Depends(get_session),
) -> ScanFindingImportResult:
    run = _get_run_or_404(session, run_id)
    if not payload:
        raise HTTPException(status_code=400, detail="No findings to import")

    allowed_severities = {"critical", "high", "medium", "low", "info"}
    allowed_validation = {
        "unvalidated",
        "validating",
        "confirmed",
        "unconfirmed",
        "false_positive",
    }
    imported: list[ScanFinding] = []
    for item in payload:
        severity = item.severity.lower().strip()
        validation_status = item.validation_status.lower().strip()
        keep_validation = (
            validation_status in allowed_validation
            and validation_status != "validating"
        )
        import_validation_status = (
            validation_status
            if keep_validation
            else "unvalidated"
        )
        page = _page_for_imported_finding(session, run, item.affected_url)
        finding = ScanFinding(
            test_run_id=run.id,
            page_id=page.id,
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
        )
        session.add(finding)
        session.flush()
        imported.append(finding)

    session.commit()
    for finding in imported:
        session.refresh(finding)
    return ScanFindingImportResult(
        imported=len(imported),
        findings=[ScanFindingOut.model_validate(f) for f in imported],
    )


# ── Validation endpoints ──────────────────────────────────────────────────────

@router.post("/api/test-runs/{run_id}/validate", response_model=ValidationStatusOut)
async def start_validation(
    run_id: int,
    session: Session = Depends(get_session),
) -> ValidationStatusOut:
    """Start background validation of all unvalidated findings for this run."""
    _get_run_or_404(session, run_id)
    if validator_svc.is_validating(run_id):
        raise HTTPException(status_code=409, detail="Validation already running")
    await validator_svc.start_validation(run_id)
    return ValidationStatusOut(**validator_svc.get_validation_status(run_id))


@router.post("/api/test-runs/{run_id}/validate/stop", response_model=ValidationStatusOut)
def stop_validation(
    run_id: int,
    session: Session = Depends(get_session),
) -> ValidationStatusOut:
    """Stop background validation for this run."""
    _get_run_or_404(session, run_id)
    validator_svc.request_stop(run_id)
    return ValidationStatusOut(**validator_svc.get_validation_status(run_id))


@router.post(
    "/api/test-runs/{run_id}/findings/{finding_id}/validate",
    response_model=ScanFindingOut,
)
async def validate_single_finding(
    run_id: int,
    finding_id: int,
    session: Session = Depends(get_session),
) -> ScanFindingOut:
    """Start background validation of a single finding. Returns immediately with status 'validating'."""
    _get_run_or_404(session, run_id)
    finding = session.get(ScanFinding, finding_id)
    if finding is None or finding.test_run_id != run_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    if validator_svc.is_validating(run_id):
        raise HTTPException(status_code=409, detail="Validation already running for this run")
    # Mark as validating immediately so the UI updates before the task starts.
    finding.validation_status = "validating"
    finding.validation_note = None
    session.add(finding)
    session.commit()
    session.refresh(finding)
    await validator_svc.start_validation(run_id, finding_ids=[finding_id])
    return ScanFindingOut.model_validate(finding)


@router.get("/api/test-runs/{run_id}/validate/status", response_model=ValidationStatusOut)
def get_validation_status(
    run_id: int,
    session: Session = Depends(get_session),
) -> ValidationStatusOut:
    _get_run_or_404(session, run_id)
    return ValidationStatusOut(**validator_svc.get_validation_status(run_id))


@router.delete("/api/test-runs/{run_id}/scan-log", status_code=204)
def clear_scan_log(
    run_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete all persisted activity log entries for this run."""
    _get_run_or_404(session, run_id)
    for entry in session.exec(
        select(ScanLog).where(ScanLog.test_run_id == run_id)
    ).all():
        session.delete(entry)
    session.commit()


@router.get("/api/test-runs/{run_id}/scan-log")
def get_scan_log(
    run_id: int,
    session: Session = Depends(get_session),
) -> list[dict]:
    _get_run_or_404(session, run_id)
    entries = session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .order_by(ScanLog.id)
    ).all()
    return [
        {
            "type": "scanner_phase",
            "phase": e.phase,
            "status": e.status,
            "message": e.message,
            "page_url": e.page_url,
            "data": json.loads(e.data_json) if e.data_json else None,
            "_persisted_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


def _build_thinking_log_markdown(run_id: int, entries: list[ScanLog]) -> str:
    """Format thinking-scan ScanLog entries as a readable markdown document."""
    # Group events by step number so each step becomes one section.
    steps: dict[int, list[tuple[ScanLog, dict]]] = {}
    preamble: list[tuple[ScanLog, dict]] = []  # non-step events (warnings, etc.)
    for e in entries:
        data = json.loads(e.data_json) if e.data_json else {}
        step_num = data.get("step")
        if step_num is not None:
            steps.setdefault(int(step_num), []).append((e, data))
        else:
            preamble.append((e, data))

    exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_steps = len(steps)
    lines: list[str] = [
        f"# Thinking Scan Log — Run #{run_id}",
        f"",
        f"Exported: {exported_at}  ",
        f"Steps logged: {total_steps}",
        f"",
        "---",
        "",
    ]

    # Non-step preamble events (e.g. credential warnings injected before loop start).
    for e, data in preamble:
        ts = e.created_at.strftime("%H:%M:%S") if e.created_at else ""
        lines += [f"> `{ts}` **{e.status.upper()}** {e.message}", ""]

    for step_num in sorted(steps.keys()):
        evts = steps[step_num]

        # Pick the most informative event in order: running → complete → deciding.
        def _pick(status: str):
            return next(((e, d) for e, d in evts if e.status == status), None)

        main = _pick("running") or _pick("complete") or evts[0]
        main_e, main_d = main

        # Collect response status from the complete event.
        complete_d = next((d for e, d in evts if e.status == "complete"), {})
        resp_status = complete_d.get("status", "")

        method       = main_d.get("method", "")
        url          = main_d.get("url", "")
        tool         = main_d.get("tool", "")
        note         = main_d.get("note") or complete_d.get("note") or ""
        observation  = main_d.get("observation", "")
        hypothesis   = main_d.get("hypothesis", "")
        payload_purp = main_d.get("payload_purpose", "")
        payload_sum  = main_d.get("payload_summary", "")
        finding_id   = complete_d.get("finding_id")
        affected_url = complete_d.get("affected_url", "")
        ts = main_e.created_at.strftime("%H:%M:%S") if main_e.created_at else ""

        max_steps = next((d.get("max_steps") for _, d in evts if d.get("max_steps")), "?")

        if tool:
            heading = f"### `{ts}` Step {step_num}/{max_steps} — tool `{tool}`"
        elif finding_id:
            heading = f"### `{ts}` Step {step_num}/{max_steps} — **FINDING** {note}"
        elif method and url:
            status_suffix = f" → `{resp_status}`" if resp_status else ""
            heading = f"### `{ts}` Step {step_num}/{max_steps} — `{method}` {url}{status_suffix}"
        else:
            heading = f"### `{ts}` Step {step_num}/{max_steps}"

        lines.append(heading)
        lines.append("")

        if note and not finding_id:
            lines += [f"**Note:** {note}", ""]
        if observation:
            lines += [f"**Observation:** {observation}", ""]
        if hypothesis:
            lines += [f"**Hypothesis:** {hypothesis}", ""]
        if payload_purp:
            lines += [f"**Payload purpose:** {payload_purp}", ""]
        if payload_sum:
            lines += ["**Payload:**", f"```", payload_sum, "```", ""]
        if finding_id and affected_url:
            lines += [f"**Affected URL:** {affected_url}  ", f"**Finding ID:** {finding_id}", ""]

        lines += ["---", ""]

    return "\n".join(lines)


@router.get("/api/test-runs/{run_id}/thinking-log/export")
def export_thinking_log(
    run_id: int,
    session: Session = Depends(get_session),
) -> HTTPResponse:
    """Download the thinking scan activity log as a markdown file."""
    _get_run_or_404(session, run_id)
    entries = session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.phase == "thinking_step")
        .order_by(ScanLog.id)
    ).all()
    md = _build_thinking_log_markdown(run_id, list(entries))
    filename = f"thinking-log-run-{run_id}.md"
    return HTTPResponse(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
