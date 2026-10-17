"""Create and control web (Site) runs.

The ``/api`` routes and the API extension both call these functions, so each
request is checked by the same rules. Errors are raised as ``HTTPException`` to
match the other run services.
"""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlmodel import Session, select

from aespa.models import CrawledPage, Credential, Site, TestRun, TestRunStatus
from aespa.schemas import StartCrawlBody, TestRunCreate
from aespa.services import crawl_then_pentest
from aespa.services import crawler as crawler_svc
from aespa.services import scanner as scanner_svc
from aespa.services import settings as settings_service
from aespa.services.settings import get_llm_config_for_run

CRAWL_OWNED_PHASES = {"created", "crawling", "reconciling", "finalizing"}
STARTABLE_STATUSES = (
    TestRunStatus.pending,
    TestRunStatus.stopped,
    TestRunStatus.failed,
    TestRunStatus.complete,
)


def get_run(session: Session, run_id: int) -> TestRun:
    run = session.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"TestRun {run_id} not found")
    return run


def validate_page_selection(crawler_mode: str, page_selection: str) -> None:
    if crawler_mode != "url" and page_selection != "each_url":
        raise HTTPException(
            status_code=422,
            detail="Group similar pages is available only with URL crawl",
        )


def _auto_name(session: Session, site_id: int) -> str:
    existing = session.exec(select(TestRun).where(TestRun.site_id == site_id)).all()
    return f"Run #{len(existing) + 1}"


def create_run(session: Session, site_id: int, payload: TestRunCreate) -> TestRun:
    """Create a pending web run for a site. Nothing is started."""
    if session.get(Site, site_id) is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    validate_page_selection(payload.crawler_mode, payload.page_selection)
    if payload.llm_config_id is not None:
        from aespa.models import LLMConfig

        if session.get(LLMConfig, payload.llm_config_id) is None:
            raise HTTPException(status_code=404, detail="LLM model not found")
    if payload.llm_profile_id is not None:
        from aespa.services.settings_profiles import get_scan_profile

        get_scan_profile(session, payload.llm_profile_id)
    policy = settings_service.get_scanner_policy(session)
    run = TestRun(
        site_id=site_id,
        name=payload.name or _auto_name(session, site_id),
        use_screenshots=payload.use_screenshots,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
        llm_max_concurrency=payload.llm_max_concurrency,
        crawler_mode=payload.crawler_mode,
        page_selection=payload.page_selection,
        scan_mode=policy.scan_mode,
        scanner_policy_json="{}",
        llm_config_id=payload.llm_config_id,
        llm_profile_id=payload.llm_profile_id,
        llm_budget_usd=payload.llm_budget_usd,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def reject_resume_over_budget(run: TestRun) -> None:
    """Refuse to resume a run whose estimated LLM spend is at its budget."""
    if run.llm_budget_usd is None:
        return
    from aespa.services import llm as llm_svc

    spend = llm_svc.run_llm_spend_usd(run.id)
    if spend >= run.llm_budget_usd:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This run has spent ${spend:.2f} of its ${run.llm_budget_usd:.2f} "
                "LLM budget. Raise the budget to resume."
            ),
        )


def _scan_mode_group(coverage_mode: str) -> str:
    return coverage_mode if coverage_mode in {"deep", "team"} else "standard"


def reject_incompatible_scan_mode(
    session: Session, run: TestRun, requested_mode: str
) -> None:
    if not scanner_svc.is_scan_mode_locked(session, run):
        return
    if _scan_mode_group(run.coverage_mode) == _scan_mode_group(requested_mode):
        return
    saved_label = {
        "deep": "Deep",
        "team": "Team",
    }.get(run.coverage_mode, "Quick, Standard, Full, or SAST Validate")
    requested_label = {
        "deep": "Deep",
        "team": "Team",
    }.get(requested_mode, "Quick, Standard, Full, or SAST Validate")
    raise HTTPException(
        status_code=409,
        detail=(
            f"This run already started in {saved_label} mode and cannot switch "
            f"to {requested_label}. Create a new run to use the other mode."
        ),
    )


def _require_sast_leads(run_id: int) -> None:
    from aespa.services.scan_leads import get_leads_for_run

    if not get_leads_for_run("web", run_id):
        raise HTTPException(
            status_code=409,
            detail="No open imported SAST leads are available to validate",
        )


async def start(
    session: Session, run_id: int, body: StartCrawlBody | None = None
) -> TestRun:
    """Start the crawl, and optionally the dynamic scan once it succeeds."""
    run = get_run(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Test run is already running")
    if run.status not in STARTABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start a run with status '{run.status}'",
        )
    if get_llm_config_for_run(session, run) is None:
        raise HTTPException(
            status_code=400,
            detail="No LLM configuration found. Configure it in Settings first.",
        )
    next_crawler_mode = (
        body.crawler_mode if body and body.crawler_mode else run.crawler_mode
    )
    next_page_selection = (
        body.page_selection if body and body.page_selection else run.page_selection
    )
    validate_page_selection(next_crawler_mode, next_page_selection)
    if run.crawl_started_once and (
        next_crawler_mode != run.crawler_mode
        or next_page_selection != run.page_selection
    ):
        raise HTTPException(
            status_code=409,
            detail="Clear or restart the crawl to change its mode or page selection",
        )
    if body and body.start_pentest_after_crawl:
        if scanner_svc.is_thinking_running(run_id):
            raise HTTPException(status_code=409, detail="Dynamic Scan already running")
        if body.coverage_mode is not None:
            reject_incompatible_scan_mode(session, run, body.coverage_mode)
            run.coverage_mode = body.coverage_mode
        if run.coverage_mode == "sast_validate":
            _require_sast_leads(run_id)
    if body and body.crawl_credential_id is not None:
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
    run.crawler_mode = next_crawler_mode
    run.page_selection = next_page_selection
    run.crawl_started_once = True
    session.add(run)
    session.commit()
    crawl_task = await crawler_svc.start_crawl(run_id)
    if body and body.start_pentest_after_crawl:
        crawl_then_pentest.schedule(run_id, crawl_task)
    session.refresh(run)
    return run


async def start_scan(
    session: Session,
    run_id: int,
    *,
    coverage_mode: str | None = None,
    target_page_ids: list[int] | None = None,
    use_session: str | None = None,
    update_targets: bool = False,
) -> dict:
    """Start the dynamic scan on a crawled run."""
    run = get_run(session, run_id)
    if crawler_svc.is_running(run_id):
        raise HTTPException(
            status_code=409, detail="Crawl is still running — wait for it to finish"
        )
    if scanner_svc.is_thinking_running(run_id):
        raise HTTPException(status_code=409, detail="Dynamic Scan already running")
    if coverage_mode is not None:
        reject_incompatible_scan_mode(session, run, coverage_mode)
        run.coverage_mode = coverage_mode
    if update_targets or coverage_mode is not None:
        if target_page_ids is not None:
            pages = session.exec(
                select(CrawledPage)
                .where(CrawledPage.test_run_id == run_id)
                .where(CrawledPage.id.in_(target_page_ids))
            ).all()
            if len(pages) != len(set(target_page_ids)):
                raise HTTPException(status_code=404, detail="Target page not found")
            run.target_page_ids_json = json.dumps(sorted(set(target_page_ids)))
            run.target_session_label = use_session or None
        session.add(run)
        session.commit()
    if run.coverage_mode != "sast_validate":
        # Seed workprogram synchronously so it's populated before the response returns.
        try:
            from aespa.services.web_workprogram import seed_web_workprogram

            seed_web_workprogram(run_id)
        except Exception:
            pass  # non-fatal
    if run.coverage_mode == "sast_validate":
        _require_sast_leads(run_id)
    await scanner_svc.start_thinking_scan(run_id)
    return scanner_svc.get_thinking_scan_status(run_id)


def stop(session: Session, run_id: int) -> bool:
    """Stop whatever part of the run is active. Returns False if nothing was."""
    run = get_run(session, run_id)
    stopped = False
    if crawl_then_pentest.is_pending(run_id):
        crawl_then_pentest.cancel(run_id)
        stopped = True
    if crawler_svc.is_running(run_id):
        crawler_svc.request_stop(run_id)
        if run.phase in CRAWL_OWNED_PHASES:
            run.status = TestRunStatus.stopped
            session.add(run)
            session.commit()
        stopped = True
    if scanner_svc.is_thinking_running(run_id):
        scanner_svc.request_thinking_stop(run_id)
        stopped = True
    return stopped
