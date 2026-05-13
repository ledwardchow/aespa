from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import (
    CrawledPage,
    PageCredentialView,
    PageLink,
    ScannerSession,
    TargetIntelItem,
    TestRun,
    TestRunStatus,
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
    ScopeUpdate,
    ScannerSessionOut,
    ScannerSessionSummary,
    ScannerSessionUpdate,
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
from aespa.services.settings import get_llm_config

router = APIRouter(tags=["test_runs"])


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
    scan_pages = session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == run.id)
        .where(CrawledPage.in_scope != False)  # noqa: E712
    ).all()
    s.scan_total_pages = len(scan_pages)
    s.scan_pages_done = sum(1 for p in scan_pages if p.scan_status == "complete")
    em = run.error_message or ""
    if scanner_svc.is_running(run.id):
        s.scan_status = "running"
    elif em.startswith("scan:"):
        parts = em.split(":", 2)
        s.scan_status = parts[1] if len(parts) > 1 else "idle"
        if s.scan_status == "running":
            s.scan_status = "idle"
        s.error_message = (
            f"Scan failed: {parts[2]}"
            if s.scan_status == "failed" and len(parts) > 2
            else None
        )
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

        if scanner_svc.is_running(run.id):
            scan = scanner_svc.get_scan_status(run.id)
            jobs.append(
                ActiveJobSummary(
                    run_id=run.id,
                    site_id=run.site_id,
                    site_name=site_name,
                    run_name=run.name,
                    job_type="Structured Scan",
                    status=scan.get("status", "running"),
                    pages_done=scan.get("pages_done"),
                    total_pages=scan.get("total_pages"),
                    findings_count=scan.get("findings_count"),
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
    for l in links:
        session.delete(l)
    views = session.exec(select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)).all()
    for v in views:
        session.delete(v)
    intel = session.exec(select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)).all()
    for item in intel:
        session.delete(item)
    pages = session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
    for p in pages:
        session.delete(p)
    session.delete(run)
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
        # Validate the profile exists
        from aespa.models import LLMConfig
        if session.get(LLMConfig, payload.llm_config_id) is None:
            raise HTTPException(status_code=404, detail="LLM profile not found")
    run.llm_config_id = payload.llm_config_id
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
    if get_llm_config(session) is None:
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
    if get_llm_config(session) is None:
        raise HTTPException(
            status_code=400,
            detail="No LLM configuration found. Configure it in Settings first.",
        )
    # Wipe existing results
    for lnk in session.exec(select(PageLink).where(PageLink.test_run_id == run_id)).all():
        session.delete(lnk)
    for view in session.exec(select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)).all():
        session.delete(view)
    for item in session.exec(select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)).all():
        session.delete(item)
    for pg in session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all():
        session.delete(pg)
    # Reset run state
    run.status = TestRunStatus.pending
    run.pages_discovered = 0
    run.started_at = None
    run.completed_at = None
    run.error_message = None
    run.current_url = None
    run.per_user_progress = None
    session.add(run)
    session.commit()
    session.refresh(run)
    summary = _run_summary(run, session)
    await crawler_svc.start_crawl(run_id)
    return summary


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
        GraphLink(source=l.source_page_id, target=l.target_page_id, link_text=l.link_text)
        for l in links
        if l.target_page_id is not None
        and l.source_page_id in page_ids
        and l.target_page_id in page_ids
    ]
    return GraphData(nodes=nodes, links=edges)


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


@router.patch("/api/test-runs/{run_id}/scanner-sessions/{session_id}", response_model=ScannerSessionOut)
def update_scanner_session(
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
