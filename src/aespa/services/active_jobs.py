"""Read active job summaries across run types."""

from __future__ import annotations

from sqlmodel import Session, func, select

from aespa.models import ScanFinding, TestRun
from aespa.schemas import ActiveJobSummary


def list_active_jobs(session: Session) -> list[ActiveJobSummary]:
    from aespa.models import Application, AssessmentCampaign, Site
    from aespa.services import crawler as crawler_svc
    from aespa.services import scanner as scanner_svc
    from aespa.services import validator as validator_svc

    runs = session.exec(select(TestRun).order_by(TestRun.created_at.desc())).all()
    jobs: list[ActiveJobSummary] = []
    for run in runs:
        site = session.get(Site, run.site_id)
        site_name = site.name if site else f"Site #{run.site_id}"

        if crawler_svc.is_running(run.id):
            jobs.append(
                ActiveJobSummary(
                    run_id=run.id,
                    site_id=run.site_id,
                    site_name=site_name,
                    run_name=run.name,
                    job_type="Crawl",
                    status="running",
                    pages_done=run.pages_discovered,
                    total_pages=run.max_pages,
                    current_url=run.current_url,
                    started_at=run.started_at,
                    created_at=run.created_at,
                )
            )

        if scanner_svc.is_thinking_running(run.id):
            thinking = scanner_svc.get_thinking_scan_status(run.id)
            jobs.append(
                ActiveJobSummary(
                    run_id=run.id,
                    site_id=run.site_id,
                    site_name=site_name,
                    run_name=run.name,
                    job_type="Dynamic Scan",
                    status=thinking.get("status", "running"),
                    findings_count=thinking.get("findings_count"),
                    started_at=run.started_at,
                    created_at=run.created_at,
                )
            )

        if validator_svc.is_validating(run.id):
            validation = validator_svc.get_validation_status(run.id)
            jobs.append(
                ActiveJobSummary(
                    run_id=run.id,
                    site_id=run.site_id,
                    site_name=site_name,
                    run_name=run.name,
                    job_type="Validation",
                    status="running",
                    pages_done=(
                        validation["total"]
                        - validation["validating"]
                        - validation["unvalidated"]
                    ),
                    total_pages=validation["total"],
                    findings_count=validation["total"],
                    started_at=run.started_at,
                    created_at=run.created_at,
                )
            )

        from aespa.services import alice_tasks

        alice_task = alice_tasks.get(run.id, run_type="site")
        if alice_task is not None and not alice_task.done:
            findings_count = session.exec(
                select(func.count())
                .select_from(ScanFinding)
                .where(ScanFinding.test_run_id == run.id)
            ).one()
            jobs.append(
                ActiveJobSummary(
                    run_id=run.id,
                    site_id=run.site_id,
                    site_name=site_name,
                    run_name=run.name,
                    job_type="A.L.I.C.E.",
                    status="running",
                    findings_count=findings_count,
                    started_at=run.started_at,
                    created_at=run.created_at,
                )
            )

    # ── Campaign orchestrator jobs ───────────────────────────────────────────
    # Campaigns coordinate their own SAST/correlation/live-testing children,
    # so they do not appear in any of the run-specific registries above. Keep
    # the campaign itself visible while its durable stage is active, including
    # short windows where the in-memory orchestrator task is not the source of
    # truth (for example, during correlation or a graceful transition).
    campaigns = session.exec(
        select(AssessmentCampaign)
        .where(
            AssessmentCampaign.status.in_(
                ("sast_running", "correlating", "dast_running")
            )
        )
        .order_by(AssessmentCampaign.created_at.desc())
    ).all()
    for campaign in campaigns:
        application = session.get(Application, campaign.application_id)
        jobs.append(
            ActiveJobSummary(
                run_id=campaign.id,
                run_name=campaign.name,
                job_type="Campaign Scan",
                status=campaign.status,
                started_at=campaign.started_at,
                created_at=campaign.created_at,
                run_type="campaign",
                application_id=campaign.application_id,
                application_name=(
                    application.name
                    if application
                    else f"Application #{campaign.application_id}"
                ),
            )
        )

    # ── API test run jobs ─────────────────────────────────────────────────────
    from aespa.models import ApiCollection, ApiTestRun
    from aespa.services import alice_tasks as alice_tasks_svc
    from aespa.services import api_scanner as api_scanner_svc

    api_runs = session.exec(
        select(ApiTestRun).order_by(ApiTestRun.created_at.desc())
    ).all()
    for api_run in api_runs:
        coll = session.get(ApiCollection, api_run.collection_id)
        coll_name = coll.name if coll else f"Collection #{api_run.collection_id}"

        if api_scanner_svc.is_api_scan_running(api_run.id):
            findings_count = session.exec(
                select(func.count())
                .select_from(ScanFinding)
                .where(ScanFinding.api_test_run_id == api_run.id)
            ).one()
            jobs.append(
                ActiveJobSummary(
                    run_id=api_run.id,
                    run_name=api_run.name,
                    job_type="Dynamic Scan",
                    status="running",
                    findings_count=findings_count,
                    started_at=api_run.started_at,
                    created_at=api_run.created_at,
                    run_type="api",
                    collection_id=api_run.collection_id,
                    collection_name=coll_name,
                )
            )

        api_alice_task = alice_tasks_svc.get(api_run.id, run_type="api")
        if api_alice_task is not None and not api_alice_task.done:
            findings_count = session.exec(
                select(func.count())
                .select_from(ScanFinding)
                .where(ScanFinding.api_test_run_id == api_run.id)
            ).one()
            jobs.append(
                ActiveJobSummary(
                    run_id=api_run.id,
                    run_name=api_run.name,
                    job_type="A.L.I.C.E.",
                    status="running",
                    findings_count=findings_count,
                    started_at=api_run.started_at,
                    created_at=api_run.created_at,
                    run_type="api",
                    collection_id=api_run.collection_id,
                    collection_name=coll_name,
                )
            )

    # ── SAST run jobs ─────────────────────────────────────────────────────────
    from aespa.models import SastRun
    from aespa.services import sast_scanner as sast_scanner_svc

    sast_runs = session.exec(select(SastRun).order_by(SastRun.created_at.desc())).all()
    for sast_run in sast_runs:
        if sast_scanner_svc.is_sast_scan_running(sast_run.id):
            coll = session.get(ApiCollection, sast_run.collection_id)
            coll_name = coll.name if coll else f"Collection #{sast_run.collection_id}"
            jobs.append(
                ActiveJobSummary(
                    run_id=sast_run.id,
                    run_name=sast_run.name,
                    job_type="SAST Scan",
                    status="scanning",
                    started_at=sast_run.started_at,
                    created_at=sast_run.created_at,
                    run_type="sast",
                    collection_id=sast_run.collection_id,
                    collection_name=coll_name,
                )
            )

    return jobs
