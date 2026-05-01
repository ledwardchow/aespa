from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import CrawledPage, PageLink, TestRun, TestRunStatus
from aespa.schemas import (
    CrawledPageDetail,
    CrawledPageOut,
    GraphData,
    GraphLink,
    GraphNode,
    ScopeUpdate,
    TestRunCreate,
    TestRunSummary,
)
from aespa.services import crawler as crawler_svc
from aespa.services.settings import get_llm_config

router = APIRouter(tags=["test_runs"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_run_or_404(session: Session, run_id: int) -> TestRun:
    run = session.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"TestRun {run_id} not found")
    return run


def _get_site_or_404(session: Session, site_id: int):
    from aespa.models import Site
    site = session.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    return site


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
    run = TestRun(
        site_id=site_id,
        name=name,
        use_screenshots=payload.use_screenshots,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return TestRunSummary.model_validate(run)


@router.get("/api/sites/{site_id}/test-runs", response_model=list[TestRunSummary])
def list_test_runs(
    site_id: int,
    session: Session = Depends(get_session),
) -> list[TestRunSummary]:
    _get_site_or_404(session, site_id)
    runs = session.exec(
        select(TestRun).where(TestRun.site_id == site_id).order_by(TestRun.created_at.desc())
    ).all()
    return [TestRunSummary.model_validate(r) for r in runs]


# ── Single run ────────────────────────────────────────────────────────────────

@router.get("/api/test-runs/{run_id}", response_model=TestRunSummary)
def get_test_run(run_id: int, session: Session = Depends(get_session)) -> TestRunSummary:
    run = _get_run_or_404(session, run_id)
    return TestRunSummary.model_validate(run)


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
    pages = session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
    for p in pages:
        session.delete(p)
    session.delete(run)
    session.commit()


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
    await crawler_svc.start_crawl(run_id)
    # Return immediately; the background task updates status in DB and the
    # frontend poll will reflect it within a few seconds.
    return TestRunSummary.model_validate(run)


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
    for pg in session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all():
        session.delete(pg)
    # Reset run state
    run.status = TestRunStatus.pending
    run.pages_discovered = 0
    run.started_at = None
    run.completed_at = None
    run.error_message = None
    run.current_url = None
    session.add(run)
    session.commit()
    session.refresh(run)
    # Capture summary before the await to avoid session-boundary issues
    summary = TestRunSummary.model_validate(run)
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
    return TestRunSummary.model_validate(run)


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
