from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import (
    CrawledPage,
    PageCredentialView,
    PageLink,
    SastRun,
    ScanFinding,
    ScannerSession,
    Site,
    TargetIntelItem,
    TestRun,
    TestRunStatus,
    TrafficEntry,
)
from aespa.schemas import (
    ActiveJobSummary,
    CrawledPageDetail,
    CrawledPageOut,
    CredentialSummary,
    GraphData,
    PageCredentialViewOut,
    ScanLeadOut,
    ScannerSessionOut,
    ScannerSessionSummary,
    ScannerSessionUpdate,
    ScannerSessionValidationResult,
    ScopeUpdate,
    StartCrawlBody,
    TargetIntelItemOut,
    TargetIntelSummary,
    TestRunCreate,
    TestRunSummary,
    TestRunUpdate,
)
from aespa.services import active_jobs as active_jobs_svc
from aespa.services import crawl_archives, run_cleanup
from aespa.services import crawler as crawler_svc
from aespa.services import recon_summary as recon_summary_svc
from aespa.services import scanner as scanner_svc
from aespa.services import scanner_sessions as scanner_session_svc
from aespa.services import settings as settings_service
from aespa.services import validator as validator_svc
from aespa.services.crawl_archives import _json_dict, _redacted_metadata
from aespa.services.references import ensure_finding_reference, ensure_lead_reference
from aespa.services.run_graph import build_run_graph
from aespa.services.settings import get_llm_config_for_run

router = APIRouter(tags=["test_runs"])

_CRAWL_OWNED_PHASES = {"created", "crawling", "reconciling", "finalizing"}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_run_or_404(session: Session, run_id: int) -> TestRun:
    run = session.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"TestRun {run_id} not found")
    return run


def _run_summary(run: TestRun, session: Session) -> TestRunSummary:
    from aespa.models import Site
    from aespa.services import scanner as scanner_svc

    site = session.get(Site, run.site_id)
    creds = [
        CredentialSummary(
            id=c.id,
            username=c.username,
            label=c.label,
            auth_mode=c.auth_mode or "auto",
            has_totp_seed=bool((c.totp_seed or "").strip()),
        )
        for c in (site.credentials if site else [])
    ]
    s = TestRunSummary.model_validate(run)
    s.credentials = creds
    policy = settings_service.get_run_scanner_policy(session, run)
    s.scanner_policy = policy.model_dump(mode="json")
    s.scan_mode = policy.scan_mode
    import json as _json

    s.scope_hosts = _json.loads(site.scope_hosts or "[]") if site else []
    thinking = scanner_svc.get_thinking_scan_status(run.id)
    s.thinking_status = thinking.get("status", "idle")
    return s


def _get_site_or_404(session: Session, site_id: int):
    from aespa.models import Site

    site = session.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    return site


def _scanner_session_out(record: ScannerSession) -> ScannerSessionOut:
    cookies = _json_dict(record.cookies_json)
    headers = _json_dict(record.extra_headers_json)
    metadata = _redacted_metadata(_json_dict(record.session_metadata))
    return ScannerSessionOut(
        id=record.id,
        test_run_id=record.test_run_id,
        label=record.label,
        kind=record.kind,
        account_label=record.account_label,
        username=record.username,
        credential_id=record.credential_id,
        source=record.source,
        cookie_names=sorted(str(k) for k in cookies.keys()),
        header_names=sorted(str(k) for k in headers.keys()),
        token_hint=record.token_hint,
        lifecycle_state=record.lifecycle_state,
        validation_url=record.validation_url,
        last_status=record.last_status,
        last_validated_at=record.last_validated_at,
        session_metadata=metadata,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _auto_name(session: Session, site_id: int) -> str:
    existing = session.exec(select(TestRun).where(TestRun.site_id == site_id)).all()
    return f"Run #{len(existing) + 1}"


def _clear_crawl_state(session: Session, run: TestRun) -> None:
    run_id = run.id
    if run_id is None:
        return

    for finding in session.exec(
        select(ScanFinding).where(ScanFinding.test_run_id == run_id)
    ).all():
        if finding.page_id is not None:
            finding.page_id = None
            session.add(finding)
    for lnk in session.exec(
        select(PageLink).where(PageLink.test_run_id == run_id)
    ).all():
        session.delete(lnk)
    for view in session.exec(
        select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)
    ).all():
        session.delete(view)
    for item in session.exec(
        select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)
    ).all():
        session.delete(item)
    for entry in session.exec(
        select(TrafficEntry).where(TrafficEntry.test_run_id == run_id)
    ).all():
        session.delete(entry)
    for pg in session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run_id)
    ).all():
        session.delete(pg)

    run.status = TestRunStatus.pending
    run.pages_discovered = 0
    run.started_at = None
    run.completed_at = None
    run.error_message = None
    run.current_url = None
    run.per_user_progress = None
    session.add(run)


# ── Per-site: create / list ───────────────────────────────────────────────────


@router.post(
    "/api/sites/{site_id}/test-runs",
    response_model=TestRunSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_test_run(
    site_id: int,
    payload: TestRunCreate,
    session: Session = Depends(get_session),
) -> TestRunSummary:
    _get_site_or_404(session, site_id)
    if payload.llm_config_id is not None:
        from aespa.models import LLMConfig

        if session.get(LLMConfig, payload.llm_config_id) is None:
            raise HTTPException(status_code=404, detail="LLM model not found")
    if payload.llm_profile_id is not None:
        from aespa.models import LLMProfile

        if session.get(LLMProfile, payload.llm_profile_id) is None:
            raise HTTPException(status_code=404, detail="Scan profile not found")
    name = payload.name or _auto_name(session, site_id)
    policy = settings_service.get_scanner_policy(session)
    run = TestRun(
        site_id=site_id,
        name=name,
        use_screenshots=payload.use_screenshots,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
        crawler_mode=payload.crawler_mode,
        scan_mode=policy.scan_mode,
        scanner_policy_json="{}",
        llm_config_id=payload.llm_config_id,
        llm_profile_id=payload.llm_profile_id,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return _run_summary(run, session)


@router.get("/api/sites/{site_id}/test-runs", response_model=list[TestRunSummary])
def list_test_runs(
    site_id: int,
    session: Session = Depends(get_session),
) -> list[TestRunSummary]:
    _get_site_or_404(session, site_id)
    runs = session.exec(
        select(TestRun)
        .where(TestRun.site_id == site_id)
        .order_by(TestRun.created_at.desc())
    ).all()
    return [_run_summary(r, session) for r in runs]


@router.get("/api/test-runs/active", response_model=list[ActiveJobSummary])
def list_active_jobs(session: Session = Depends(get_session)) -> list[ActiveJobSummary]:
    return active_jobs_svc.list_active_jobs(session)


# ── Single run ────────────────────────────────────────────────────────────────


@router.get("/api/test-runs/{run_id}", response_model=TestRunSummary)
def get_test_run(
    run_id: int, session: Session = Depends(get_session)
) -> TestRunSummary:
    run = _get_run_or_404(session, run_id)
    return _run_summary(run, session)


@router.delete("/api/test-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_run(run_id: int, session: Session = Depends(get_session)) -> None:
    _get_run_or_404(session, run_id)
    from aespa.services import campaigns as campaigns_svc

    await campaigns_svc.stop_member_tasks_for_run("web", run_id)
    # Stop every in-process worker before deleting rows.  The scan can remain
    # active after the crawl has marked the run complete, so checking only the
    # persisted status is not sufficient.
    if crawler_svc.is_running(run_id):
        await crawler_svc.stop_and_wait(run_id)
    if scanner_svc.is_thinking_running(run_id):
        await scanner_svc.stop_thinking_and_wait(run_id)
    if validator_svc.is_validating(run_id):
        await validator_svc.stop_and_wait(run_id)
    from aespa.services import alice_tasks

    await alice_tasks.stop(run_id)
    child_sast_ids = [
        sast_run.id
        for sast_run in session.exec(
            select(SastRun)
            .where(SastRun.triggered_by_run_type == "web")
            .where(SastRun.triggered_by_run_id == run_id)
        ).all()
        if sast_run.id is not None
    ]
    if child_sast_ids:
        from aespa.services import sast_scanner

        for sast_run_id in child_sast_ids:
            await sast_scanner.stop_sast_scan_and_wait(sast_run_id)
    run_cleanup.cascade_delete_web_run(session, run_id)
    session.commit()


# ── SAST leads (web run) ──────────────────────────────────────────────────────


@router.get("/api/test-runs/{run_id}/sast-runs/available")
def list_available_sast_runs(
    run_id: int, session: Session = Depends(get_session)
) -> list[dict]:
    """Completed SAST runs with leads — the dropdown source for importing leads."""
    from aespa.models import SastRun

    _get_run_or_404(session, run_id)
    runs = session.exec(
        select(SastRun)
        .where(SastRun.status == "completed")
        .where(SastRun.leads_count > 0)
        .order_by(SastRun.id.desc())  # type: ignore[attr-defined]
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "leads_count": r.leads_count,
            "source_filename": r.source_filename,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


class ImportLeadsRequest(BaseModel):
    sast_run_id: int


@router.post("/api/test-runs/{run_id}/import-leads")
def import_sast_leads(
    run_id: int,
    body: ImportLeadsRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Copy SAST leads into this web run as independent rows.

    Campaign ownership does not block lead copies: the source remains
    immutable and the destination receives separately owned investigation rows.
    """
    from aespa.models import SastRun
    from aespa.services.scan_leads import copy_leads_to_run

    _get_run_or_404(session, run_id)
    if session.get(SastRun, body.sast_run_id) is None:
        raise HTTPException(status_code=404, detail="SAST run not found")
    imported = copy_leads_to_run(body.sast_run_id, "web", run_id)
    return {"imported": imported}


@router.get("/api/test-runs/{run_id}/leads", response_model=list[ScanLeadOut])
def get_test_run_leads(
    run_id: int, session: Session = Depends(get_session)
) -> list[ScanLeadOut]:
    """Return the SAST leads imported into this web run."""
    from aespa.models import ScanLead

    _get_run_or_404(session, run_id)
    leads = session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_type == "web")
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


@router.delete("/api/test-runs/{run_id}/leads", status_code=status.HTTP_204_NO_CONTENT)
def clear_test_run_leads(run_id: int, session: Session = Depends(get_session)) -> None:
    """Delete all SAST leads imported into this web run (originals are untouched)."""
    from aespa.models import ScanLead

    _get_run_or_404(session, run_id)
    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_type == "web")
        .where(ScanLead.imported_into_run_id == run_id)
    ).all():
        session.delete(lead)
    session.commit()


@router.delete(
    "/api/test-runs/{run_id}/leads/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_test_run_lead(
    run_id: int, lead_id: int, session: Session = Depends(get_session)
) -> None:
    """Delete a single imported lead from this web run.

    Scoped to leads owned by this run so an original SAST lead can never be
    removed through the web-run endpoint.
    """
    from aespa.models import ScanLead

    _get_run_or_404(session, run_id)
    lead = session.get(ScanLead, lead_id)
    if (
        lead is None
        or lead.imported_into_run_type != "web"
        or lead.imported_into_run_id != run_id
    ):
        raise HTTPException(status_code=404, detail="Lead not found for this run")
    session.delete(lead)
    session.commit()


# ── Update run settings ───────────────────────────────────────────────────────


@router.patch("/api/test-runs/{run_id}", response_model=TestRunSummary)
def update_test_run(
    run_id: int,
    payload: TestRunUpdate,
    session: Session = Depends(get_session),
) -> TestRunSummary:
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(
            status_code=409, detail="Cannot edit settings while crawl is running"
        )
    run.max_depth = payload.max_depth
    run.max_pages = payload.max_pages
    run.llm_max_concurrency = (
        payload.llm_max_concurrency
        if payload.llm_max_concurrency and payload.llm_max_concurrency > 0
        else None
    )
    if payload.crawler_mode is not None:
        run.crawler_mode = payload.crawler_mode
    if payload.llm_config_id is not None:
        # Validate the model exists
        from aespa.models import LLMConfig

        if session.get(LLMConfig, payload.llm_config_id) is None:
            raise HTTPException(status_code=404, detail="LLM model not found")
    if payload.llm_profile_id is not None:
        from aespa.models import LLMProfile

        if session.get(LLMProfile, payload.llm_profile_id) is None:
            raise HTTPException(status_code=404, detail="Scan profile not found")
    run.llm_config_id = payload.llm_config_id
    run.llm_profile_id = payload.llm_profile_id
    session.add(run)
    session.commit()
    session.refresh(run)
    return _run_summary(run, session)


# ── Crawl control ─────────────────────────────────────────────────────────────


@router.get("/api/test-runs/{run_id}/crawl/status")
def test_run_crawl_status(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    """Return the crawler task state independently of the overall run phase."""
    _get_run_or_404(session, run_id)
    return {"running": crawler_svc.is_running(run_id)}


@router.post("/api/test-runs/{run_id}/start", response_model=TestRunSummary)
async def start_test_run(
    run_id: int,
    body: StartCrawlBody | None = None,
    session: Session = Depends(get_session),
) -> TestRunSummary:
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Test run is already running")
    if run.status not in (
        TestRunStatus.pending,
        TestRunStatus.stopped,
        TestRunStatus.failed,
        TestRunStatus.complete,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start a run with status '{run.status}'",
        )
    if get_llm_config_for_run(session, run) is None:
        raise HTTPException(
            status_code=400,
            detail="No LLM configuration found. Configure it in Settings first.",
        )
    if body and body.crawl_credential_id is not None:
        from aespa.models import Credential

        cred = session.get(Credential, body.crawl_credential_id)
        if cred is None or cred.site_id != run.site_id:
            raise HTTPException(
                status_code=404,
                detail="Credential not found or does not belong to this site",
            )
        run.crawl_credential_id = body.crawl_credential_id
    else:
        # Reset to "all credentials" if no specific user was requested.
        run.crawl_credential_id = None
    # Clear stale per_user_progress synchronously so the response (and the
    # first poll) never contains data from a previous crawl.
    run.per_user_progress = None
    session.add(run)
    session.commit()
    await crawler_svc.start_crawl(run_id)
    return _run_summary(run, session)


@router.post("/api/test-runs/{run_id}/restart", response_model=TestRunSummary)
async def restart_test_run(
    run_id: int,
    body: StartCrawlBody | None = None,
    session: Session = Depends(get_session),
) -> TestRunSummary:
    """Wipe all crawled pages/links for this run and start a fresh crawl."""
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Stop the run before restarting.")
    if get_llm_config_for_run(session, run) is None:
        raise HTTPException(
            status_code=400,
            detail="No LLM configuration found. Configure it in Settings first.",
        )
    if body and body.crawl_credential_id is not None:
        from aespa.models import Credential

        cred = session.get(Credential, body.crawl_credential_id)
        if cred is None or cred.site_id != run.site_id:
            raise HTTPException(
                status_code=404,
                detail="Credential not found or does not belong to this site",
            )
        run.crawl_credential_id = body.crawl_credential_id
    else:
        run.crawl_credential_id = None
    _clear_crawl_state(session, run)
    session.commit()
    session.refresh(run)
    summary = _run_summary(run, session)
    await crawler_svc.start_crawl(run_id)
    return summary


@router.post("/api/test-runs/{run_id}/crawl/resume", response_model=TestRunSummary)
async def resume_test_run_crawl(
    run_id: int,
    session: Session = Depends(get_session),
) -> TestRunSummary:
    """Resume a quota-paused crawl using its persisted crawl artifacts."""
    run = _get_run_or_404(session, run_id)
    from aespa.services import run_pause as run_pause_svc

    pause = run_pause_svc.get_pause("crawl", run_id)
    if pause is None or run.status != "paused":
        raise HTTPException(status_code=409, detail="Crawl is not paused")
    if pause.reset_at and pause.reset_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=409,
            detail={"message": pause.message, "reset_at": pause.reset_at.isoformat()},
        )
    await crawler_svc.start_crawl(run_id)
    run_pause_svc.clear_pause("crawl", run_id)
    session.refresh(run)
    return _run_summary(run, session)


@router.post("/api/test-runs/{run_id}/crawl/clear", response_model=TestRunSummary)
def clear_test_run_crawl(
    run_id: int,
    session: Session = Depends(get_session),
) -> TestRunSummary:
    """Wipe crawled pages/links for this run without starting a new crawl."""
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(
            status_code=409, detail="Stop the run before clearing crawl data."
        )
    _clear_crawl_state(session, run)
    session.commit()
    session.refresh(run)
    return _run_summary(run, session)


@router.get("/api/test-runs/{run_id}/crawl/export")
def export_test_run_crawl(
    run_id: int, session: Session = Depends(get_session)
) -> JSONResponse:
    """Download crawl artifacts for reuse in a later run against the same site."""
    run = _get_run_or_404(session, run_id)
    if not session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run_id)
    ).first():
        raise HTTPException(status_code=400, detail="There is no crawl data to export")
    try:
        archive = crawl_archives.build_archive(session, run)
    except crawl_archives.ArchiveError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    filename = f"aespa-crawl-run-{run_id}.json"
    return JSONResponse(
        archive,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/test-runs/{run_id}/crawl/import", response_model=TestRunSummary)
async def import_test_run_crawl(
    run_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> TestRunSummary:
    """Populate a new run from an exported crawl without re-running Playwright."""
    run = _get_run_or_404(session, run_id)
    if run.status != TestRunStatus.pending:
        raise HTTPException(
            status_code=409,
            detail="Crawl data can only be imported into a new pending run",
        )
    if session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run_id)
    ).first():
        raise HTTPException(
            status_code=409, detail="Clear this run's crawl data before importing"
        )
    raw = await file.read()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400, detail="Crawl export must be valid JSON"
        ) from exc
    site = _get_site_or_404(session, run.site_id)
    try:
        crawl = crawl_archives.validate_archive(payload, site.base_url)
    except crawl_archives.ArchiveError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc

    try:
        pages_by_url = crawl_archives.restore_archive_records(
            session, run_id, crawl, site
        )
    except crawl_archives.ArchiveError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc

    crawl_archives.finish_archive_import(session, run, crawl, pages_by_url)
    return _run_summary(run, session)


@router.post("/api/test-runs/{run_id}/stop", response_model=TestRunSummary)
def stop_test_run(
    run_id: int, session: Session = Depends(get_session)
) -> TestRunSummary:
    run = _get_run_or_404(session, run_id)
    if not crawler_svc.is_running(run_id):
        raise HTTPException(status_code=409, detail="Crawl is not currently running")
    crawler_svc.request_stop(run_id)
    # The Dynamic Scan can run at the same time as the crawler and owns the
    # shared run status once its phase starts. Stopping the crawler must not
    # overwrite an active or completed scan result.
    if run.phase in _CRAWL_OWNED_PHASES:
        run.status = TestRunStatus.stopped
        session.add(run)
        session.commit()
        session.refresh(run)
    return _run_summary(run, session)


# ── Web workprogram ────────────────────────────────────────────────────────────


@router.get("/api/test-runs/{run_id}/coverage")
def get_web_coverage_matrix(
    run_id: int, session: Session = Depends(get_session)
) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import web_workprogram

    return web_workprogram.get_web_coverage_matrix(run_id)


@router.post("/api/test-runs/{run_id}/coverage/seed")
def seed_web_coverage(run_id: int, session: Session = Depends(get_session)) -> dict:
    _get_run_or_404(session, run_id)
    from aespa.services import web_workprogram

    created = web_workprogram.seed_web_workprogram(run_id)
    return {"ok": True, "created": created}


# ── Pages + graph ─────────────────────────────────────────────────────────────


@router.get("/api/test-runs/{run_id}/pages", response_model=list[CrawledPageOut])
def list_pages(
    run_id: int, session: Session = Depends(get_session)
) -> list[CrawledPageOut]:
    _get_run_or_404(session, run_id)
    pages = session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == run_id)
        .order_by(CrawledPage.depth, CrawledPage.discovered_at)
    ).all()
    return [CrawledPageOut.model_validate(p) for p in pages]


@router.get("/api/test-runs/{run_id}/pages/{page_id}", response_model=CrawledPageDetail)
def get_page(
    run_id: int, page_id: int, session: Session = Depends(get_session)
) -> CrawledPageDetail:
    _get_run_or_404(session, run_id)
    page = session.get(CrawledPage, page_id)
    if page is None or page.test_run_id != run_id:
        raise HTTPException(status_code=404, detail="Page not found")
    detail = CrawledPageDetail.model_validate(page)
    try:
        replay = json.loads(page.replay_steps_json or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        replay = []
    if isinstance(replay, dict):
        root_url = str(replay.get("root_url") or page.url)
        steps = replay.get("steps") or []
    else:
        root_url = page.url
        steps = replay if isinstance(replay, list) else []
    if steps:
        detail.browser_replay = {
            "url": root_url,
            "steps": [{"op": "goto", "url": root_url}]
            + [
                {
                    key: value
                    for key, value in {
                        "op": step.get("kind") or step.get("op") or "click",
                        "selector": step.get("selector"),
                        "testid": step.get("testid"),
                        "role": step.get("role"),
                        "name": step.get("name"),
                        "value": step.get("value"),
                    }.items()
                    if value not in (None, "")
                }
                for step in steps
                if isinstance(step, dict)
            ],
        }
    traffic_rows = session.exec(
        select(TrafficEntry)
        .where(TrafficEntry.test_run_id == run_id)
        .where(TrafficEntry.page_id == page_id)
        .order_by(TrafficEntry.id.desc())
        .limit(100)
    ).all()
    detail.traffic = [
        {
            "id": row.id,
            "source": row.source,
            "method": row.method,
            "url": row.url,
            "status": row.status,
            "duration_ms": row.duration_ms,
            "username": row.username,
            "session_label": row.session_label,
            "interaction_id": row.interaction_id,
        }
        for row in traffic_rows
    ]
    intel_rows = session.exec(
        select(TargetIntelItem)
        .where(TargetIntelItem.test_run_id == run_id)
        .where(TargetIntelItem.page_id == page_id)
        .where(TargetIntelItem.kind == "object_reference")
        .order_by(TargetIntelItem.id.desc())
        .limit(100)
    ).all()
    detail.object_references = [
        {
            "id": row.id,
            "key": row.key,
            "value": row.value,
            "url": row.url,
            "method": row.method,
            "confidence": row.confidence,
            "metadata": _redacted_metadata(_json_dict(row.item_metadata)),
        }
        for row in intel_rows
    ]
    return detail


@router.get(
    "/api/test-runs/{run_id}/pages/{page_id}/views",
    response_model=list[PageCredentialViewOut],
)
def get_page_views(
    run_id: int, page_id: int, session: Session = Depends(get_session)
) -> list[PageCredentialViewOut]:
    _get_run_or_404(session, run_id)
    views = session.exec(
        select(PageCredentialView)
        .where(PageCredentialView.page_id == page_id)
        .where(PageCredentialView.test_run_id == run_id)
    ).all()
    return [PageCredentialViewOut.model_validate(v) for v in views]


@router.get("/api/test-runs/{run_id}/graph", response_model=GraphData)
def get_graph(run_id: int, session: Session = Depends(get_session)) -> GraphData:
    return build_run_graph(session, _get_run_or_404(session, run_id))


@router.delete("/api/test-runs/{run_id}/target-intelligence", status_code=204)
def clear_target_intelligence(
    run_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete all target intelligence items discovered for this run."""
    _get_run_or_404(session, run_id)
    for item in session.exec(
        select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)
    ).all():
        session.delete(item)
    session.commit()


@router.get(
    "/api/test-runs/{run_id}/target-intelligence", response_model=TargetIntelSummary
)
def get_target_intelligence(
    run_id: int,
    kind: str | None = None,
    page_id: int | None = None,
    limit: int = 500,
    session: Session = Depends(get_session),
) -> TargetIntelSummary:
    _get_run_or_404(session, run_id)
    limit = max(1, min(limit, 2000))
    all_items = session.exec(
        select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)
    ).all()
    counts: dict[str, int] = {}
    for item in all_items:
        counts[item.kind] = counts.get(item.kind, 0) + 1

    query = select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)
    if kind:
        query = query.where(TargetIntelItem.kind == kind)
    if page_id is not None:
        query = query.where(TargetIntelItem.page_id == page_id)
    items = session.exec(
        query.order_by(
            TargetIntelItem.kind, TargetIntelItem.discovered_at.desc()
        ).limit(limit)
    ).all()
    return TargetIntelSummary(
        counts=counts,
        items=[TargetIntelItemOut.model_validate(item) for item in items],
    )


@router.get(
    "/api/test-runs/{run_id}/scanner-sessions", response_model=ScannerSessionSummary
)
def get_scanner_sessions(
    run_id: int,
    include_inactive: bool = False,
    session: Session = Depends(get_session),
) -> ScannerSessionSummary:
    _get_run_or_404(session, run_id)
    query = (
        select(ScannerSession)
        .where(ScannerSession.test_run_id == run_id)
        .where(ScannerSession.run_kind == "web")
    )
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


@router.post(
    "/api/test-runs/{run_id}/scanner-sessions/validate",
    response_model=ScannerSessionValidationResult,
)
async def validate_scanner_sessions(
    run_id: int,
    session: Session = Depends(get_session),
) -> ScannerSessionValidationResult:
    run = _get_run_or_404(session, run_id)
    site = session.get(Site, run.site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    pages = session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == run_id)
        .where(CrawledPage.in_scope != False)  # noqa: E712
        .where(CrawledPage.req_auth == True)  # noqa: E712
        .order_by(CrawledPage.depth, CrawledPage.id)
    ).all()
    sessions = session.exec(
        select(ScannerSession)
        .where(ScannerSession.test_run_id == run_id)
        .where(ScannerSession.run_kind == "web")
        .where(ScannerSession.is_active == True)  # noqa: E712
    ).all()
    probe_urls: dict[int, str] = {}
    for record in sessions:
        for page in pages:
            try:
                accessible_by = json.loads(page.accessible_by or "[]")
            except Exception:
                accessible_by = []
            if record.credential_id is None or record.credential_id in accessible_by:
                probe_urls[record.id] = page.url
                break

    return await scanner_session_svc.validate_active_sessions(
        session,
        run_id,
        run_kind="web",
        default_url=site.base_url,
        probe_urls=probe_urls,
    )


@router.patch(
    "/api/test-runs/{run_id}/scanner-sessions/{session_id}",
    response_model=ScannerSessionOut,
)
def update_scanner_session(
    run_id: int,
    session_id: int,
    payload: ScannerSessionUpdate,
    session: Session = Depends(get_session),
) -> ScannerSessionOut:
    _get_run_or_404(session, run_id)
    record = session.get(ScannerSession, session_id)
    if record is None or record.test_run_id != run_id or record.run_kind != "web":
        raise HTTPException(
            status_code=404, detail=f"ScannerSession {session_id} not found"
        )

    if payload.label is not None:
        normalized = scanner_session_svc.stable_label(payload.label)
        if not normalized:
            raise HTTPException(status_code=400, detail="Session label cannot be blank")
        duplicate = session.exec(
            select(ScannerSession)
            .where(ScannerSession.test_run_id == run_id)
            .where(ScannerSession.run_kind == "web")
            .where(ScannerSession.label == normalized)
            .where(ScannerSession.id != session_id)
        ).first()
        if duplicate is not None:
            raise HTTPException(
                status_code=409, detail=f"Session label '{normalized}' already exists"
            )
        record.label = normalized
    if payload.is_active is not None:
        record.is_active = payload.is_active
    from aespa.models import _utcnow

    record.updated_at = _utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    return _scanner_session_out(record)


@router.get("/api/test-runs/{run_id}/recon-summary")
def get_recon_summary(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Return a live attack-surface and workprogram coverage projection."""
    _get_run_or_404(session, run_id)
    has_crawl = session.exec(
        select(CrawledPage.id).where(CrawledPage.test_run_id == run_id)
    ).first()
    if has_crawl is None:
        raise HTTPException(
            status_code=404, detail="Attack surface not yet available for this run."
        )
    # The tab polls while a scan is active. Rebuild from canonical rows so routes,
    # access observations, findings, and coverage never lag behind stored JSON.
    return recon_summary_svc.build_recon_summary(run_id, session=session, persist=False)


# ── Scope management ──────────────────────────────────────────────────────────


@router.patch("/api/test-runs/{run_id}/pages/{page_id}/scope")
def update_page_scope(
    run_id: int,
    page_id: int,
    payload: ScopeUpdate,
    session: Session = Depends(get_session),
) -> dict:
    _get_run_or_404(session, run_id)
    page = session.get(CrawledPage, page_id)
    if page is None or page.test_run_id != run_id:
        raise HTTPException(status_code=404, detail="Page not found")

    if payload.cascade:
        # BFS through PageLinks to collect the page and all its descendants.
        from collections import deque

        visited: set[int] = {page_id}
        queue: deque[int] = deque([page_id])
        while queue:
            pid = queue.popleft()
            children = session.exec(
                select(PageLink.target_page_id)
                .where(PageLink.test_run_id == run_id)
                .where(PageLink.source_page_id == pid)
            ).all()
            for cid in children:
                if cid is not None and cid not in visited:
                    visited.add(cid)
                    queue.append(cid)
        pages_to_update = session.exec(
            select(CrawledPage).where(CrawledPage.id.in_(list(visited)))
        ).all()
        for p in pages_to_update:
            p.in_scope = payload.in_scope
            session.add(p)
        updated = len(pages_to_update)
    else:
        page.in_scope = payload.in_scope
        session.add(page)
        updated = 1

    session.commit()
    return {"updated": updated}


@router.delete("/api/test-runs/{run_id}/pages/{page_id}", status_code=204)
def delete_page(
    run_id: int,
    page_id: int,
    cascade: bool = False,
    session: Session = Depends(get_session),
) -> None:
    _get_run_or_404(session, run_id)
    page = session.get(CrawledPage, page_id)
    if page is None or page.test_run_id != run_id:
        raise HTTPException(status_code=404, detail="Page not found")

    if cascade:
        from collections import deque

        to_delete: set[int] = {page_id}
        queue: deque[int] = deque([page_id])
        while queue:
            pid = queue.popleft()
            children = session.exec(
                select(PageLink.target_page_id)
                .where(PageLink.test_run_id == run_id)
                .where(PageLink.source_page_id == pid)
            ).all()
            for cid in children:
                if cid is not None and cid not in to_delete:
                    to_delete.add(cid)
                    queue.append(cid)
    else:
        to_delete = {page_id}

    # Delete links touching any of the pages being removed, then the pages.
    ids = list(to_delete)
    for link in session.exec(
        select(PageLink).where(
            (PageLink.source_page_id.in_(ids)) | (PageLink.target_page_id.in_(ids))
        )
    ).all():
        session.delete(link)
    for view in session.exec(
        select(PageCredentialView)
        .where(PageCredentialView.test_run_id == run_id)
        .where(PageCredentialView.page_id.in_(ids))
    ).all():
        session.delete(view)
    for p in session.exec(select(CrawledPage).where(CrawledPage.id.in_(ids))).all():
        session.delete(p)
    session.commit()
