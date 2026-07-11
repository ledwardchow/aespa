from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, func, select

from aespa.db import get_session
from aespa.models import (
    AgentLog,
    CrawledPage,
    PageCredentialView,
    PageLink,
    PageOwaspTest,
    PentestHypothesis,
    PentestTask,
    ScanCheckpoint,
    ScanFinding,
    ScanLog,
    ScannerSession,
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
    GraphLink,
    GraphNode,
    PageCredentialViewOut,
    PentestTaskGraphOut,
    ScanLeadOut,
    ScannerSessionOut,
    ScannerSessionSummary,
    ScannerSessionUpdate,
    ScopeUpdate,
    TargetIntelItemOut,
    TargetIntelSummary,
    TestRunCreate,
    TestRunSummary,
    TestRunUpdate,
)
from aespa.services import crawler as crawler_svc
from aespa.services import scanner_sessions as scanner_session_svc
from aespa.services import settings as settings_service
from aespa.services import task_graph as task_graph_svc
from aespa.services.settings import get_llm_config_for_run

router = APIRouter(tags=["test_runs"])

_CRAWL_ARCHIVE_FORMAT = "aespa-crawl-export"
_CRAWL_ARCHIVE_VERSION = 1
_SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "proxy-authorization", "x-api-key"}


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
    creds = [CredentialSummary.model_validate(c) for c in (site.credentials if site else [])]
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


def _json_dict(value: str | None) -> dict:
    try:
        parsed = json.loads(value or "{}")
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


def _normalise_base_url(url: str) -> str:
    """Compare target origins without treating a trailing slash as a mismatch."""
    parts = urlsplit(url.strip())
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/')}"


def _redact_headers(raw: str | None) -> str:
    """Keep request shape useful while preventing session secrets entering an archive."""
    headers = _json_dict(raw)
    for key in list(headers):
        if key.lower() in _SENSITIVE_HEADER_NAMES:
            headers[key] = "[REDACTED]"
    return json.dumps(headers)


def _crawl_archive(session: Session, run: TestRun) -> dict:
    """Create a portable, intentionally credential-free crawl snapshot."""
    site = _get_site_or_404(session, run.site_id)
    pages = list(session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run.id)))
    page_urls = {page.id: page.url for page in pages}
    credentials = {cred.id: cred.username for cred in site.credentials}
    page_fields = (
        "url", "title", "page_text", "screenshot_b64", "llm_context", "depth", "status",
        "error_message", "in_scope", "scan_status", "req_auth", "takes_input",
        "has_object_ref", "has_business_logic", "accessible_by", "owasp_applicable_json",
    )
    return {
        "format": _CRAWL_ARCHIVE_FORMAT,
        "version": _CRAWL_ARCHIVE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": {"site_base_url": site.base_url, "run_id": run.id, "run_name": run.name},
        "crawl": {
            "pages": [{field: getattr(page, field) for field in page_fields} for page in pages],
            "links": [
                {
                    "source_url": page_urls.get(link.source_page_id),
                    "target_url": link.target_url,
                    "link_text": link.link_text,
                }
                for link in session.exec(select(PageLink).where(PageLink.test_run_id == run.id))
                if page_urls.get(link.source_page_id)
            ],
            "credential_views": [
                {
                    "page_url": page_urls.get(view.page_id),
                    "username": credentials.get(view.credential_id, view.username),
                    "screenshot_b64": view.screenshot_b64,
                    "llm_context": view.llm_context,
                    "page_text": view.page_text,
                    "req_auth": view.req_auth,
                    "takes_input": view.takes_input,
                    "has_object_ref": view.has_object_ref,
                    "has_business_logic": view.has_business_logic,
                    "owasp_applicable_json": view.owasp_applicable_json,
                }
                for view in session.exec(select(PageCredentialView).where(PageCredentialView.test_run_id == run.id))
                if page_urls.get(view.page_id)
            ],
            "target_intelligence": [
                {
                    field: getattr(item, field)
                    for field in ("kind", "key", "value", "url", "method", "source", "confidence", "evidence", "item_metadata")
                }
                for item in session.exec(select(TargetIntelItem).where(TargetIntelItem.test_run_id == run.id))
            ],
            # Traffic gives the test lead useful API observations, but authentication
            # headers are redacted so importing never restores an old session.
            "traffic": [
                {
                    "source": entry.source, "method": entry.method, "url": entry.url,
                    "request_headers": _redact_headers(entry.request_headers),
                    "request_body": entry.request_body, "status": entry.status,
                    "response_headers": _redact_headers(entry.response_headers), "response_body": entry.response_body,
                    "duration_ms": entry.duration_ms, "username": entry.username,
                }
                for entry in session.exec(select(TrafficEntry).where(TrafficEntry.test_run_id == run.id))
            ],
        },
    }


def _validate_crawl_archive(payload: object, site_base_url: str) -> dict:
    if not isinstance(payload, dict) or payload.get("format") != _CRAWL_ARCHIVE_FORMAT:
        raise HTTPException(status_code=400, detail="Not an AESPA crawl export file")
    if payload.get("version") != _CRAWL_ARCHIVE_VERSION:
        raise HTTPException(status_code=400, detail="Unsupported crawl export version")
    source = payload.get("source")
    crawl = payload.get("crawl")
    if not isinstance(source, dict) or not isinstance(crawl, dict) or not isinstance(crawl.get("pages"), list):
        raise HTTPException(status_code=400, detail="Crawl export is missing page data")
    source_url = source.get("site_base_url")
    if not isinstance(source_url, str) or _normalise_base_url(source_url) != _normalise_base_url(site_base_url):
        raise HTTPException(status_code=400, detail="This crawl export belongs to a different site URL")
    return crawl


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


def _auto_name(session: Session, site_id: int) -> str:
    existing = session.exec(
        select(TestRun).where(TestRun.site_id == site_id)
    ).all()
    return f"Run #{len(existing) + 1}"


def _clear_crawl_state(session: Session, run: TestRun) -> None:
    run_id = run.id
    if run_id is None:
        return

    for finding in session.exec(select(ScanFinding).where(ScanFinding.test_run_id == run_id)).all():
        if finding.page_id is not None:
            finding.page_id = None
            session.add(finding)
    for lnk in session.exec(select(PageLink).where(PageLink.test_run_id == run_id)).all():
        session.delete(lnk)
    for view in session.exec(select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)).all():
        session.delete(view)
    for item in session.exec(select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)).all():
        session.delete(item)
    for entry in session.exec(select(TrafficEntry).where(TrafficEntry.test_run_id == run_id)).all():
        session.delete(entry)
    for pg in session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all():
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
        select(TestRun).where(TestRun.site_id == site_id).order_by(TestRun.created_at.desc())
    ).all()
    return [_run_summary(r, session) for r in runs]


@router.get("/api/test-runs/active", response_model=list[ActiveJobSummary])
def list_active_jobs(session: Session = Depends(get_session)) -> list[ActiveJobSummary]:
    from aespa.models import Site
    from aespa.services import scanner as scanner_svc

    runs = session.exec(select(TestRun).order_by(TestRun.created_at.desc())).all()
    jobs: list[ActiveJobSummary] = []
    for run in runs:
        site = session.get(Site, run.site_id)
        site_name = site.name if site else f"Site #{run.site_id}"

        if run.status == TestRunStatus.running:
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

        from aespa.services import alice_tasks
        alice_task = alice_tasks.get(run.id, run_type="site")
        if alice_task is not None and not alice_task.done:
            findings_count = session.exec(
                select(func.count()).select_from(ScanFinding).where(ScanFinding.test_run_id == run.id)
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

    # ── API test run jobs ─────────────────────────────────────────────────────
    from aespa.models import ApiCollection, ApiTestRun
    from aespa.services import alice_tasks as alice_tasks_svc
    from aespa.services import api_scanner as api_scanner_svc

    api_runs = session.exec(select(ApiTestRun).order_by(ApiTestRun.created_at.desc())).all()
    for api_run in api_runs:
        coll = session.get(ApiCollection, api_run.collection_id)
        coll_name = coll.name if coll else f"Collection #{api_run.collection_id}"

        if api_scanner_svc.is_api_scan_running(api_run.id):
            findings_count = session.exec(
                select(func.count()).select_from(ScanFinding).where(ScanFinding.api_test_run_id == api_run.id)
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
                select(func.count()).select_from(ScanFinding).where(ScanFinding.api_test_run_id == api_run.id)
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


# ── Single run ────────────────────────────────────────────────────────────────

@router.get("/api/test-runs/{run_id}", response_model=TestRunSummary)
def get_test_run(run_id: int, session: Session = Depends(get_session)) -> TestRunSummary:
    run = _get_run_or_404(session, run_id)
    return _run_summary(run, session)


@router.delete("/api/test-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_run(run_id: int, session: Session = Depends(get_session)) -> None:
    run = _get_run_or_404(session, run_id)
    # Stop if running
    if run.status == TestRunStatus.running:
        crawler_svc.request_stop(run_id)
    # Cascade-delete pages + links manually (SQLite FK off by default)
    links = session.exec(select(PageLink).where(PageLink.test_run_id == run_id)).all()
    for link in links:
        session.delete(link)
    views = session.exec(select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)).all()
    for v in views:
        session.delete(v)
    intel = session.exec(select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)).all()
    for item in intel:
        session.delete(item)
    for entry in session.exec(select(TrafficEntry).where(TrafficEntry.test_run_id == run_id)).all():
        session.delete(entry)
    pages = session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
    for p in pages:
        session.delete(p)
    for finding in session.exec(select(ScanFinding).where(ScanFinding.test_run_id == run_id)).all():
        session.delete(finding)
    # SAST leads imported (copied) into this web run belong to it — remove them so
    # they don't leak into a reused run id. Originals on the SAST run are untouched.
    from aespa.models import ScanLead
    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_type == "web")
        .where(ScanLead.imported_into_run_id == run_id)
    ).all():
        session.delete(lead)
    for log_entry in session.exec(
        select(ScanLog).where(ScanLog.test_run_id == run_id).where(ScanLog.run_kind == "web")
    ).all():
        session.delete(log_entry)
    for ckpt in session.exec(select(ScanCheckpoint).where(ScanCheckpoint.test_run_id == run_id)).all():
        session.delete(ckpt)
    for ss in session.exec(
        select(ScannerSession)
        .where(ScannerSession.test_run_id == run_id)
        .where(ScannerSession.run_kind == "web")
    ).all():
        session.delete(ss)
    for cell in session.exec(select(PageOwaspTest).where(PageOwaspTest.test_run_id == run_id)).all():
        session.delete(cell)
    for hyp in session.exec(select(PentestHypothesis).where(PentestHypothesis.test_run_id == run_id)).all():
        session.delete(hyp)
    for task in session.exec(select(PentestTask).where(PentestTask.test_run_id == run_id)).all():
        session.delete(task)
    for log_entry in session.exec(
        select(AgentLog).where(AgentLog.test_run_id == run_id).where(AgentLog.run_kind == "web")
    ).all():
        session.delete(log_entry)
    from aespa.models import AliceChatMessage, AliceChatSession
    for sess in session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .where(AliceChatSession.run_kind == "web")
    ).all():
        for msg in session.exec(select(AliceChatMessage).where(AliceChatMessage.session_id == sess.id)).all():
            session.delete(msg)
        session.delete(sess)
    session.delete(run)
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
    """Copy a SAST run's leads into this web run as independent rows."""
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
    return [ScanLeadOut.model_validate(lead) for lead in leads]


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
        raise HTTPException(status_code=409, detail="Cannot edit settings while crawl is running")
    run.max_depth = payload.max_depth
    run.max_pages = payload.max_pages
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

@router.post("/api/test-runs/{run_id}/start", response_model=TestRunSummary)
async def start_test_run(
    run_id: int,
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
    _clear_crawl_state(session, run)
    session.commit()
    session.refresh(run)
    summary = _run_summary(run, session)
    await crawler_svc.start_crawl(run_id)
    return summary


@router.post("/api/test-runs/{run_id}/crawl/clear", response_model=TestRunSummary)
def clear_test_run_crawl(
    run_id: int,
    session: Session = Depends(get_session),
) -> TestRunSummary:
    """Wipe crawled pages/links for this run without starting a new crawl."""
    run = _get_run_or_404(session, run_id)
    if run.status == TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Stop the run before clearing crawl data.")
    _clear_crawl_state(session, run)
    session.commit()
    session.refresh(run)
    return _run_summary(run, session)


@router.get("/api/test-runs/{run_id}/crawl/export")
def export_test_run_crawl(run_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    """Download crawl artifacts for reuse in a later run against the same site."""
    run = _get_run_or_404(session, run_id)
    if not session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).first():
        raise HTTPException(status_code=400, detail="There is no crawl data to export")
    archive = _crawl_archive(session, run)
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
        raise HTTPException(status_code=409, detail="Crawl data can only be imported into a new pending run")
    if session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).first():
        raise HTTPException(status_code=409, detail="Clear this run's crawl data before importing")
    raw = await file.read()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Crawl export must be valid JSON") from exc
    site = _get_site_or_404(session, run.site_id)
    crawl = _validate_crawl_archive(payload, site.base_url)

    pages_by_url: dict[str, CrawledPage] = {}
    allowed_page_fields = {
        "url", "title", "page_text", "screenshot_b64", "llm_context", "depth", "status",
        "error_message", "in_scope", "scan_status", "req_auth", "takes_input",
        "has_object_ref", "has_business_logic", "accessible_by", "owasp_applicable_json",
    }
    try:
        for item in crawl["pages"]:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str) or not item["url"]:
                raise ValueError("page URL missing")
            if item["url"] in pages_by_url:
                continue
            page = CrawledPage(
                test_run_id=run_id,
                **{key: value for key, value in item.items() if key in allowed_page_fields},
            )
            session.add(page)
            session.flush()
            pages_by_url[page.url] = page

        for item in crawl.get("links", []):
            if not isinstance(item, dict) or item.get("source_url") not in pages_by_url or not isinstance(item.get("target_url"), str):
                continue
            target = pages_by_url.get(item["target_url"])
            session.add(PageLink(
                test_run_id=run_id, source_page_id=pages_by_url[item["source_url"]].id,
                target_page_id=target.id if target else None, target_url=item["target_url"],
                link_text=item.get("link_text"),
            ))

        credential_ids = {credential.username: credential.id for credential in site.credentials}
        for item in crawl.get("credential_views", []):
            if not isinstance(item, dict) or item.get("page_url") not in pages_by_url:
                continue
            username = item.get("username") if isinstance(item.get("username"), str) else None
            session.add(PageCredentialView(
                test_run_id=run_id, page_id=pages_by_url[item["page_url"]].id,
                credential_id=credential_ids.get(username), username=username,
                **{key: item.get(key) for key in ("screenshot_b64", "llm_context", "page_text", "req_auth", "takes_input", "has_object_ref", "has_business_logic", "owasp_applicable_json")},
            ))

        for item in crawl.get("target_intelligence", []):
            if not isinstance(item, dict) or not isinstance(item.get("kind"), str):
                continue
            session.add(TargetIntelItem(
                test_run_id=run_id,
                **{key: item.get(key) for key in ("kind", "key", "value", "url", "method", "source", "confidence", "evidence", "item_metadata")},
            ))
        for item in crawl.get("traffic", []):
            if not isinstance(item, dict) or not isinstance(item.get("method"), str) or not isinstance(item.get("url"), str):
                continue
            session.add(TrafficEntry(
                test_run_id=run_id,
                **{key: item.get(key) for key in ("source", "method", "url", "request_headers", "request_body", "status", "response_headers", "response_body", "duration_ms", "username")},
            ))
    except (TypeError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid crawl export data: {exc}") from exc

    # Imported crawl data is ready for scanning. Seed a fresh workprogram, never
    # copy progress/results from the source run.
    for page in pages_by_url.values():
        try:
            applicable = json.loads(page.owasp_applicable_json or "{}")
        except (TypeError, json.JSONDecodeError):
            applicable = {}
        for category, is_applicable in applicable.items():
            if is_applicable and isinstance(category, str):
                session.add(PageOwaspTest(test_run_id=run_id, page_id=page.id, owasp_category=category))
    now = datetime.now(timezone.utc)
    run.status = TestRunStatus.complete
    run.pages_discovered = len(pages_by_url)
    run.started_at = now
    run.completed_at = now
    run.current_url = None
    run.per_user_progress = None
    run.error_message = None
    run.recon_summary = None
    session.add(run)
    session.commit()
    session.refresh(run)
    return _run_summary(run, session)


@router.post("/api/test-runs/{run_id}/stop", response_model=TestRunSummary)
def stop_test_run(run_id: int, session: Session = Depends(get_session)) -> TestRunSummary:
    run = _get_run_or_404(session, run_id)
    if run.status != TestRunStatus.running:
        raise HTTPException(status_code=409, detail="Test run is not currently running")
    crawler_svc.request_stop(run_id)
    run.status = TestRunStatus.stopped
    session.add(run)
    session.commit()
    session.refresh(run)
    return _run_summary(run, session)


# ── Web workprogram ────────────────────────────────────────────────────────────

@router.get("/api/test-runs/{run_id}/coverage")
def get_web_coverage_matrix(run_id: int, session: Session = Depends(get_session)) -> dict:
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
def list_pages(run_id: int, session: Session = Depends(get_session)) -> list[CrawledPageOut]:
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
    return CrawledPageDetail.model_validate(page)


@router.get("/api/test-runs/{run_id}/pages/{page_id}/views", response_model=list[PageCredentialViewOut])
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
    _get_run_or_404(session, run_id)
    pages = session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run_id)
    ).all()
    links = session.exec(
        select(PageLink).where(PageLink.test_run_id == run_id)
    ).all()

    nodes = [
        GraphNode(
            id=p.id,
            url=p.url,
            title=p.title,
            depth=p.depth,
            status=p.status,
            context=p.llm_context,
            in_scope=p.in_scope,
            scan_status=p.scan_status,
            accessible_by=json.loads(p.accessible_by or "[]"),
        )
        for p in pages
    ]
    page_ids = {p.id for p in pages}
    edges = [
        GraphLink(source=link.source_page_id, target=link.target_page_id, link_text=link.link_text)
        for link in links
        if link.target_page_id is not None
        and link.source_page_id in page_ids
        and link.target_page_id in page_ids
    ]
    return GraphData(nodes=nodes, links=edges)


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


@router.get("/api/test-runs/{run_id}/target-intelligence", response_model=TargetIntelSummary)
def get_target_intelligence(
    run_id: int,
    kind: str | None = None,
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
    items = session.exec(
        query.order_by(TargetIntelItem.kind, TargetIntelItem.discovered_at.desc()).limit(limit)
    ).all()
    return TargetIntelSummary(
        counts=counts,
        items=[TargetIntelItemOut.model_validate(item) for item in items],
    )


@router.get("/api/test-runs/{run_id}/scanner-sessions", response_model=ScannerSessionSummary)
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


@router.patch("/api/test-runs/{run_id}/scanner-sessions/{session_id}", response_model=ScannerSessionOut)
def update_scanner_session(
    run_id: int,
    session_id: int,
    payload: ScannerSessionUpdate,
    session: Session = Depends(get_session),
) -> ScannerSessionOut:
    _get_run_or_404(session, run_id)
    record = session.get(ScannerSession, session_id)
    if record is None or record.test_run_id != run_id or record.run_kind != "web":
        raise HTTPException(status_code=404, detail=f"ScannerSession {session_id} not found")

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


@router.delete("/api/test-runs/{run_id}/task-graph", status_code=204)
def clear_task_graph(
    run_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete all hypotheses and tasks for this run."""
    _get_run_or_404(session, run_id)
    for task in session.exec(
        select(PentestTask).where(PentestTask.test_run_id == run_id)
    ).all():
        session.delete(task)
    for hyp in session.exec(
        select(PentestHypothesis).where(PentestHypothesis.test_run_id == run_id)
    ).all():
        session.delete(hyp)
    session.commit()


@router.get("/api/test-runs/{run_id}/task-graph", response_model=PentestTaskGraphOut)
def get_task_graph(
    run_id: int,
    session: Session = Depends(get_session),
) -> PentestTaskGraphOut:
    _get_run_or_404(session, run_id)
    return task_graph_svc.get_task_graph(run_id, session=session)


@router.post("/api/test-runs/{run_id}/task-graph/seed", response_model=PentestTaskGraphOut)
def seed_task_graph(
    run_id: int,
    session: Session = Depends(get_session),
) -> PentestTaskGraphOut:
    _get_run_or_404(session, run_id)
    result = task_graph_svc.seed_task_graph(run_id, session=session)
    if result.get("hypotheses_created") or result.get("tasks_created"):
        from aespa.services import events as events_svc
        events_svc.emit(run_id, {
            "type": "task_graph_update",
            "reason": "seeded",
            "data": result,
        })
    return task_graph_svc.get_task_graph(run_id, session=session)


@router.get("/api/test-runs/{run_id}/recon-summary")
def get_recon_summary(
    run_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Return the stored attack-surface summary for this run, or 404 if not yet built."""
    run = _get_run_or_404(session, run_id)
    if not run.recon_summary:
        raise HTTPException(status_code=404, detail="Recon summary not yet available for this run.")
    import json as _json
    return _json.loads(run.recon_summary)


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
