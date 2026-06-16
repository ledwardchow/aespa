"""Tests for the web workprogram coverage matrix.

Tests:
  1.  seed_web_workprogram creates PageOwaspTest rows for applicable page × category pairs
  2.  seed_web_workprogram is idempotent (re-seeding does not duplicate rows)
  3.  update_web_coverage_cell creates a new cell if it does not exist
  4.  update_web_coverage_cell updates an existing cell's status
  5.  update_web_coverage_cell never downgrades status (no-downgrade rule)
  6.  update_web_coverage_cell appends finding_id to finding_ids_json
  7.  update_web_coverage_cell records skip_reason
  8.  mark_in_progress_to_covered promotes in_progress → covered; leaves finding/skipped/not_started
  9.  _make_web_post_probe_fn: probe with owasp_category flips matching page cell to in_progress
  10. _make_web_post_probe_fn: no-op when category is blank
  11. _make_web_post_finding_fn: finding flips matching page cell to finding
  12. get_web_coverage_matrix returns seeded=False when no cells exist
  13. get_web_coverage_matrix returns persisted status for cells
  14. get_web_coverage_matrix returns coverage_mode from run
  15. _enforce_web_coverage_loop drives all uncovered cells to terminal state
  16. _enforce_web_coverage_loop respects stop_check
  17. start-scan endpoint persists coverage_mode on the run
"""
from __future__ import annotations

import asyncio
import json
from datetime import timezone
from unittest.mock import patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import _migrate, set_engine
from aespa.models import (
    CrawledPage,
    PageOwaspTest,
    Site,
    TestRun,
)
from aespa.services.web_workprogram import (
    _enforce_web_coverage_loop,
    _make_web_post_finding_fn,
    _make_web_post_probe_fn,
    _uncovered_web_cells,
    get_web_coverage_matrix,
    mark_in_progress_to_covered,
    seed_web_workprogram,
    update_web_coverage_cell,
)

_UTC = timezone.utc


# ── DB fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(name="db_engine")
def db_engine_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa.db import _engine as original_engine
    SQLModel.metadata.create_all(engine)
    _migrate(engine)
    set_engine(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    set_engine(original_engine)


@pytest.fixture(name="db_session")
def db_session_fixture(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture(name="site")
def site_fixture(db_session):
    s = Site(name="TestSite", base_url="http://example.com")
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture(name="run")
def run_fixture(db_session, site):
    r = TestRun(site_id=site.id, name="Run 1")
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


def _make_page(db_session, run, url: str, applicable_cats: list[str] | None = None) -> CrawledPage:
    """Helper: create an in-scope CrawledPage with the given OWASP applicable categories."""
    owasp_json = json.dumps({cat: True for cat in (applicable_cats or [])})
    p = CrawledPage(
        test_run_id=run.id,
        url=url,
        page_text="",
        in_scope=True,
        owasp_applicable_json=owasp_json,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture(name="client")
def client_fixture(db_engine):
    from fastapi.testclient import TestClient

    from aespa.db import get_session as gs
    from aespa.main import create_app

    def _override_session():
        with Session(db_engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[gs] = _override_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── 1. seed_web_workprogram creates rows ──────────────────────────────────────

def test_seed_creates_cells(db_engine, db_session, run):
    _make_page(db_session, run, "http://example.com/login", ["A01", "A03"])
    _make_page(db_session, run, "http://example.com/profile", ["A01"])

    count = seed_web_workprogram(run.id)
    assert count == 3  # 2 + 1

    cells = db_session.exec(
        select(PageOwaspTest).where(PageOwaspTest.test_run_id == run.id)
    ).all()
    assert len(cells) == 3
    assert all(c.status == "not_started" for c in cells)


# ── 2. seed_web_workprogram is idempotent ─────────────────────────────────────

def test_seed_idempotent(db_engine, db_session, run):
    _make_page(db_session, run, "http://example.com/", ["A01"])
    first = seed_web_workprogram(run.id)
    second = seed_web_workprogram(run.id)
    assert first == 1
    assert second == 0


# ── 3. update_web_coverage_cell creates new cell ──────────────────────────────

def test_update_cell_creates(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/api", ["A01"])
    update_web_coverage_cell(run.id, page.id, "A01", "in_progress")
    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A01")
    ).first()
    assert cell is not None
    assert cell.status == "in_progress"


# ── 4. update_web_coverage_cell updates status ────────────────────────────────

def test_update_cell_updates_status(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/api", ["A01"])
    seed_web_workprogram(run.id)
    update_web_coverage_cell(run.id, page.id, "A01", "covered")
    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A01")
    ).first()
    assert cell.status == "covered"


# ── 5. update_web_coverage_cell never downgrades ──────────────────────────────

def test_update_cell_no_downgrade(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/api", ["A01"])
    update_web_coverage_cell(run.id, page.id, "A01", "finding", finding_id=1)
    # Attempt downgrade — should be silently ignored.
    update_web_coverage_cell(run.id, page.id, "A01", "in_progress")
    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A01")
    ).first()
    assert cell.status == "finding"


# ── 6. update_web_coverage_cell appends finding_id ───────────────────────────

def test_update_cell_appends_finding(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/api", ["A03"])
    update_web_coverage_cell(run.id, page.id, "A03", "finding", finding_id=42)
    update_web_coverage_cell(run.id, page.id, "A03", "finding", finding_id=99)
    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A03")
    ).first()
    fids = json.loads(cell.finding_ids_json)
    assert 42 in fids and 99 in fids


# ── 7. update_web_coverage_cell records skip_reason ──────────────────────────

def test_update_cell_skip_reason(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/api", ["A06"])
    update_web_coverage_cell(run.id, page.id, "A06", "skipped", skip_reason="not applicable")
    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A06")
    ).first()
    assert cell.status == "skipped"
    assert cell.skip_reason == "not applicable"


# ── 8. mark_in_progress_to_covered ───────────────────────────────────────────

def test_mark_in_progress_to_covered(db_engine, db_session, run):
    _make_page(db_session, run, "http://example.com/", ["A01", "A03"])
    seed_web_workprogram(run.id)
    cells = db_session.exec(
        select(PageOwaspTest).where(PageOwaspTest.test_run_id == run.id)
    ).all()
    assert len(cells) == 2

    # Mark first as in_progress, second as finding.
    cells[0].status = "in_progress"
    cells[1].status = "finding"
    for c in cells:
        db_session.add(c)
    db_session.commit()

    mark_in_progress_to_covered(run.id)
    db_session.expire_all()

    updated = db_session.exec(
        select(PageOwaspTest).where(PageOwaspTest.test_run_id == run.id)
    ).all()
    by_cat = {c.owasp_category: c for c in updated}
    assert by_cat[cells[0].owasp_category].status == "covered"   # in_progress → covered
    assert by_cat[cells[1].owasp_category].status == "finding"   # finding not downgraded


def test_mark_in_progress_leaves_not_started(db_engine, db_session, run):
    _make_page(db_session, run, "http://example.com/", ["A01"])
    seed_web_workprogram(run.id)
    mark_in_progress_to_covered(run.id)
    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest).where(PageOwaspTest.test_run_id == run.id)
    ).first()
    assert cell.status == "not_started"   # never touched; left alone


# ── 9. _make_web_post_probe_fn flips cell to in_progress ─────────────────────

def test_post_probe_fn_flips_in_progress(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/login", ["A07"])
    seed_web_workprogram(run.id)

    fn = _make_web_post_probe_fn(run.id)
    fn("http://example.com/login", "POST", "A07")

    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A07")
    ).first()
    assert cell.status == "in_progress"


# ── 10. _make_web_post_probe_fn is a no-op for blank category ─────────────────

def test_post_probe_fn_noop_blank_category(db_engine, db_session, run):
    _make_page(db_session, run, "http://example.com/", ["A01"])
    seed_web_workprogram(run.id)

    fn = _make_web_post_probe_fn(run.id)
    fn("http://example.com/", "GET", "")  # blank category — should be a no-op

    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest).where(PageOwaspTest.test_run_id == run.id)
    ).first()
    assert cell.status == "not_started"


# ── 10b. _make_web_post_probe_fn creates a page + cell for unknown URLs ────────

def test_post_probe_fn_creates_page_for_unknown_url(db_engine, db_session, run):
    """If the scan probes a URL not yet in the crawl, a placeholder page is created."""
    fn = _make_web_post_probe_fn(run.id)
    fn("http://example.com/new-page", "POST", "A03")

    db_session.expire_all()
    page = db_session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == run.id)
        .where(CrawledPage.url == "http://example.com/new-page")
    ).first()
    assert page is not None
    assert page.in_scope is True

    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A03")
    ).first()
    assert cell is not None
    assert cell.status == "in_progress"


# ── 11. _make_web_post_finding_fn flips cell to finding ──────────────────────

def test_post_finding_fn_flips_finding(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/transfer", ["A01"])
    seed_web_workprogram(run.id)

    class _FakeFinding:
        id = 77
        page_id = page.id
        affected_url = "http://example.com/transfer"
        owasp_category = "A01"

    fn = _make_web_post_finding_fn(run.id)
    fn(_FakeFinding())

    db_session.expire_all()
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A01")
    ).first()
    assert cell.status == "finding"
    assert 77 in json.loads(cell.finding_ids_json)


# ── 11b. _make_web_post_finding_fn uses affected_url, not page_id ─────────────

def test_post_finding_fn_uses_affected_url(db_engine, db_session, run):
    """Finding on /api/admin/customers must NOT land on the root page row."""
    root = _make_page(db_session, run, "http://example.com/", ["A03"])
    api_page = _make_page(db_session, run, "http://example.com/api/admin/customers", ["A03"])
    seed_web_workprogram(run.id)

    class _FakeFinding:
        id = 99
        page_id = root.id          # scanner set page_id = root (wrong)
        affected_url = "http://example.com/api/admin/customers"
        owasp_category = "A03"

    fn = _make_web_post_finding_fn(run.id)
    fn(_FakeFinding())

    db_session.expire_all()
    root_cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == root.id)
        .where(PageOwaspTest.owasp_category == "A03")
    ).first()
    api_cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == api_page.id)
        .where(PageOwaspTest.owasp_category == "A03")
    ).first()
    # finding must land on the api page, not the root
    assert api_cell.status == "finding"
    assert root_cell.status == "not_started"


# ── 11c. _make_web_post_finding_fn creates page for unknown affected_url ───────

def test_post_finding_fn_creates_page_for_unknown_url(db_engine, db_session, run):
    """Finding at a URL not in the crawl gets a placeholder page + cell."""
    class _FakeFinding:
        id = 42
        page_id = None
        affected_url = "http://example.com/api/health"
        owasp_category = "A05"

    fn = _make_web_post_finding_fn(run.id)
    fn(_FakeFinding())

    db_session.expire_all()
    page = db_session.exec(
        select(CrawledPage)
        .where(CrawledPage.test_run_id == run.id)
        .where(CrawledPage.url == "http://example.com/api/health")
    ).first()
    assert page is not None
    cell = db_session.exec(
        select(PageOwaspTest)
        .where(PageOwaspTest.test_run_id == run.id)
        .where(PageOwaspTest.page_id == page.id)
        .where(PageOwaspTest.owasp_category == "A05")
    ).first()
    assert cell is not None
    assert cell.status == "finding"


# ── 11d. _match_page_for_url does not swallow sub-paths into root ──────────────

def test_match_page_does_not_match_root_to_subpath(db_engine, db_session, run):
    """http://example.com/ must NOT match http://example.com/api/health."""
    from aespa.services.web_workprogram import _match_page_for_url
    root = _make_page(db_session, run, "http://example.com/", ["A01"])
    pages = [db_session.get(CrawledPage, root.id)]
    result = _match_page_for_url("http://example.com/api/health", pages)
    assert result is None   # no match — should create a new placeholder


# ── 12. get_web_coverage_matrix returns seeded=False when no cells ────────────

def test_matrix_empty(db_engine, db_session, run):
    matrix = get_web_coverage_matrix(run.id)
    assert matrix["seeded"] is False
    assert matrix["pages"] == []


# ── 13. get_web_coverage_matrix returns persisted status ─────────────────────

def test_matrix_returns_persisted_status(db_engine, db_session, run):
    page = _make_page(db_session, run, "http://example.com/", ["A01"])
    seed_web_workprogram(run.id)
    update_web_coverage_cell(run.id, page.id, "A01", "covered")

    matrix = get_web_coverage_matrix(run.id)
    assert matrix["seeded"] is True
    assert len(matrix["pages"]) == 1
    assert matrix["pages"][0]["cells"]["A01"]["status"] == "covered"


# ── 14. get_web_coverage_matrix returns coverage_mode from run ───────────────

def test_matrix_returns_coverage_mode(db_engine, db_session, run, site):
    # Set coverage_mode on the run
    run.coverage_mode = "enforce"
    db_session.add(run)
    db_session.commit()
    _make_page(db_session, run, "http://example.com/", ["A01"])
    seed_web_workprogram(run.id)

    matrix = get_web_coverage_matrix(run.id)
    assert matrix["coverage_mode"] == "enforce"


# ── 15. _enforce_web_coverage_loop drives cells to terminal ──────────────────

def test_enforce_loop_drives_to_terminal(db_engine, db_session, run):
    _make_page(db_session, run, "http://example.com/", ["A01", "A03"])
    seed_web_workprogram(run.id)

    # Prober: flip A01 cells to covered, A03 to skipped.
    async def _prober(page_obj, category, current_status):
        if category == "A01":
            return ("covered", None)
        return ("skipped", "not applicable for this page")

    stats = asyncio.run(_enforce_web_coverage_loop(run.id, _prober))
    assert stats["covered"] + stats["skipped"] == 2
    assert stats["budget_exhausted"] is False

    # Verify all cells are now terminal.
    remaining = _uncovered_web_cells(run.id)
    assert remaining == []


# ── 16. _enforce_web_coverage_loop respects stop_check ───────────────────────

def test_enforce_loop_respects_stop(db_engine, db_session, run):
    _make_page(db_session, run, "http://example.com/", ["A01", "A03", "A07"])
    seed_web_workprogram(run.id)

    call_count = [0]

    async def _prober(page_obj, category, current_status):
        call_count[0] += 1
        return ("covered", None)

    # Stop immediately.
    stats = asyncio.run(_enforce_web_coverage_loop(
        run.id, _prober, stop_check=lambda: True
    ))
    # Stop was checked before the first call, so 0 cells processed via the loop.
    assert call_count[0] == 0
    assert stats["budget_exhausted"] is True


# ── 17. start-scan endpoint persists coverage_mode ───────────────────────────

def test_start_scan_persists_coverage_mode(client, db_engine, db_session):
    with patch("aespa.services.scanner.start_thinking_scan", return_value=None), \
         patch("aespa.services.scanner.get_thinking_scan_status", return_value={"status": "running", "run_id": 1}):
        # Create a site + run via API.
        site_r = client.post("/api/sites", json={"name": "S", "base_url": "http://t.com"}).json()
        run_r = client.post(f"/api/sites/{site_r['id']}/test-runs", json={"name": "R"}).json()
        run_id = run_r["id"]

        resp = client.post(
            f"/api/test-runs/{run_id}/thinking-scan/start",
            json={"coverage_mode": "enforce"},
        )
        assert resp.status_code == 200

        # Verify the run now has coverage_mode=enforce.
        db_session.expire_all()
        run = db_session.get(TestRun, run_id)
        assert run.coverage_mode == "enforce"
