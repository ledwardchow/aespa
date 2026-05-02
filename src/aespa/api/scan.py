"""Scan API — start/stop/status/findings endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import CrawledPage, ScanFinding, TestRun, TestRunStatus
from aespa.schemas import ScanFindingOut, ScanStatusOut
from aespa.services import scanner as scanner_svc

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
    await scanner_svc.start_scan(run_id)
    return ScanStatusOut(**scanner_svc.get_scan_status(run_id))


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
