"""Slice 7 tests: coverage matrix seeding, tracking, and the coverage route.

Tests:
  1.  seed_coverage_matrix creates ApiEndpointTest rows for each in-scope endpoint × applicable categories
  2.  seed_coverage_matrix is idempotent (re-seeding does not duplicate rows)
  3.  update_coverage_cell creates a new cell if it does not exist
  4.  update_coverage_cell updates an existing cell's status
  5.  update_coverage_cell appends finding_id to finding_ids_json
  6.  mark_all_cells_covered flips not_started/in_progress → covered; leaves finding/skipped alone
  7.  GET /api/api-test-runs/{id}/coverage returns the matrix shape
  8.  GET /coverage returns empty-ish matrix when no endpoints exist
  9.  _applicable_categories returns API2 (Broken Auth) for every endpoint
  10. _applicable_categories returns API1 (BOLA) for endpoints with path params
  11. _applicable_categories returns API3 (BOPLA) for PUT/PATCH
  12. _match_endpoint_for_url matches exact path
  13. _match_endpoint_for_url matches parameterized path
  14. _match_endpoint_for_url returns None for no match
  15. get_coverage_matrix totals match actual cell counts
  16. _make_post_finding_fn updates coverage cell when finding is saved
  17. Start-scan endpoint triggers seed_coverage_matrix
  18. _make_post_probe_fn marks only the declared OWASP category in_progress (per-category granularity)
  19. _make_post_probe_fn is a no-op when the URL matches no endpoint
"""
from __future__ import annotations

import asyncio
import json
from datetime import timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import _migrate, set_engine
from aespa.models import (
    ApiCollection,
    ApiEndpoint,
    ApiEndpointTest,
    ApiTestRun,
    ScanFinding,
)
from aespa.services.api_scanner import (
    _applicable_categories,
    _build_enforce_directive,
    _enforce_coverage_loop,
    _make_enforce_prober,
    _match_endpoint_for_url,
    _uncovered_cells,
    get_coverage_matrix,
    mark_all_cells_covered,
    seed_coverage_matrix,
    update_coverage_cell,
)

_UTC = timezone.utc


def _fake_create_task(coro, **kwargs):
    """create_task stub: close the scan coroutine (TestClient's loop never runs it,
    which would leak a 'never awaited' warning) and return a done-looking task."""
    coro.close()
    t = MagicMock()
    t.done.return_value = True
    return t


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
    _migrate(engine)  # ensure api_endpoint_test table is created
    set_engine(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    set_engine(original_engine)


@pytest.fixture(name="db_session")
def db_session_fixture(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture(name="collection")
def collection_fixture(db_session):
    coll = ApiCollection(name="CovAPI", base_url="http://api.local")
    db_session.add(coll)
    db_session.commit()
    db_session.refresh(coll)
    return coll


@pytest.fixture(name="endpoint_simple")
def endpoint_simple_fixture(db_session, collection):
    ep = ApiEndpoint(
        collection_id=collection.id,
        method="GET",
        path="/health",
        in_scope=True,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    return ep


@pytest.fixture(name="endpoint_with_param")
def endpoint_with_param_fixture(db_session, collection):
    ep = ApiEndpoint(
        collection_id=collection.id,
        method="GET",
        path="/users/{id}",
        in_scope=True,
        auth_required=True,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    return ep


@pytest.fixture(name="endpoint_patch")
def endpoint_patch_fixture(db_session, collection):
    ep = ApiEndpoint(
        collection_id=collection.id,
        method="PATCH",
        path="/users/{id}/profile",
        in_scope=True,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    return ep


@pytest.fixture(name="api_run")
def api_run_fixture(db_session, collection):
    run = ApiTestRun(
        collection_id=collection.id,
        name="Cov Run 1",
        status="pending",
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


# ── HTTP client fixture ────────────────────────────────────────────────────────

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


def _make_collection_and_run(client) -> tuple[dict, dict]:
    coll = client.post("/api/api-collections", json={"name": "CovHTTP", "base_url": "http://target.api"}).json()
    run = client.post(f"/api/api-collections/{coll['id']}/test-runs", json={}).json()
    return coll, run


# ── 1. seed_coverage_matrix creates rows ──────────────────────────────────────

def test_seed_creates_cells(db_engine, db_session, collection, endpoint_simple, endpoint_with_param, api_run):
    count = seed_coverage_matrix(api_run.id)
    assert count > 0
    cells = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()
    assert len(cells) == count
    # Every cell should start as not_started
    assert all(c.status == "not_started" for c in cells)
    # All cells should reference one of the two endpoints
    endpoint_ids = {endpoint_simple.id, endpoint_with_param.id}
    assert all(c.endpoint_id in endpoint_ids for c in cells)


# ── 2. seed_coverage_matrix is idempotent ─────────────────────────────────────

def test_seed_idempotent(db_engine, db_session, collection, endpoint_simple, api_run):
    first = seed_coverage_matrix(api_run.id)
    second = seed_coverage_matrix(api_run.id)
    assert second == 0  # nothing new to create
    total = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()
    assert len(total) == first


# ── 3. update_coverage_cell creates new cell ──────────────────────────────────

def test_update_cell_creates(db_engine, db_session, collection, endpoint_simple, api_run):
    update_coverage_cell(api_run.id, endpoint_simple.id, "API2", "in_progress")
    cell = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_simple.id)
        .where(ApiEndpointTest.owasp_api_category == "API2")
    ).first()
    assert cell is not None
    assert cell.status == "in_progress"


# ── 4. update_coverage_cell updates status ────────────────────────────────────

def test_update_cell_updates_status(db_engine, db_session, collection, endpoint_simple, api_run):
    seed_coverage_matrix(api_run.id)
    update_coverage_cell(api_run.id, endpoint_simple.id, "API2", "covered")
    db_session.expire_all()
    cell = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_simple.id)
        .where(ApiEndpointTest.owasp_api_category == "API2")
    ).first()
    assert cell.status == "covered"


def test_update_cell_no_downgrade(db_engine, db_session, collection, endpoint_simple, api_run):
    """A higher-ranked status must not be overwritten by a lower-ranked one."""
    update_coverage_cell(api_run.id, endpoint_simple.id, "API2", "finding", finding_id=1)
    # Attempt to downgrade back to in_progress — should be silently ignored.
    update_coverage_cell(api_run.id, endpoint_simple.id, "API2", "in_progress")
    db_session.expire_all()
    cell = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_simple.id)
        .where(ApiEndpointTest.owasp_api_category == "API2")
    ).first()
    assert cell.status == "finding"  # still finding, not downgraded


# ── 5. update_coverage_cell appends finding_id ────────────────────────────────

def test_update_cell_appends_finding(db_engine, db_session, collection, endpoint_simple, api_run):
    update_coverage_cell(api_run.id, endpoint_simple.id, "API2", "finding", finding_id=42)
    db_session.expire_all()
    cell = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_simple.id)
        .where(ApiEndpointTest.owasp_api_category == "API2")
    ).first()
    assert cell.status == "finding"
    assert 42 in json.loads(cell.finding_ids_json)

    # Second call with a different finding_id appends it
    update_coverage_cell(api_run.id, endpoint_simple.id, "API2", "finding", finding_id=99)
    db_session.expire_all()
    cell2 = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_simple.id)
        .where(ApiEndpointTest.owasp_api_category == "API2")
    ).first()
    fids = json.loads(cell2.finding_ids_json)
    assert 42 in fids and 99 in fids


# ── 6. mark_all_cells_covered leaves finding/skipped alone ────────────────────

def test_mark_all_cells_covered(db_engine, db_session, collection, endpoint_simple, endpoint_with_param, api_run):
    seed_coverage_matrix(api_run.id)
    cells = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()

    # Flip some cells to in_progress (simulating traffic hits), one to finding, one to skipped.
    finding_id = cells[0].id
    skipped_id = cells[1].id

    cells[0].status = "finding"
    cells[1].status = "skipped"
    for c in cells[2:]:
        c.status = "in_progress"
    for c in cells:
        db_session.add(c)
    db_session.commit()

    mark_all_cells_covered(api_run.id)
    db_session.expire_all()

    updated = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()
    for c in updated:
        if c.id == finding_id:
            assert c.status == "finding"       # not downgraded
        elif c.id == skipped_id:
            assert c.status == "skipped"       # not downgraded
        else:
            assert c.status == "covered"       # in_progress → covered


def test_mark_cells_covered_leaves_not_started(db_engine, db_session, collection, endpoint_simple, api_run):
    """not_started cells (never hit by the scanner) must NOT become covered."""
    seed_coverage_matrix(api_run.id)
    mark_all_cells_covered(api_run.id)
    db_session.expire_all()

    cells = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()
    # All cells started as not_started and were never touched → should remain not_started.
    assert all(c.status == "not_started" for c in cells)


# ── 7. GET /coverage returns matrix shape ─────────────────────────────────────

def test_get_coverage_route(client, db_engine, db_session):
    coll, run = _make_collection_and_run(client)
    # Add an endpoint directly
    ep = ApiEndpoint(
        collection_id=coll["id"],
        method="POST",
        path="/items",
        in_scope=True,
    )
    db_session.add(ep)
    db_session.commit()
    seed_coverage_matrix(run["id"])

    r = client.get(f"/api/api-test-runs/{run['id']}/coverage")
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == run["id"]
    assert "categories" in data
    assert "endpoints" in data
    assert "totals" in data
    assert len(data["endpoints"]) == 1
    assert data["endpoints"][0]["method"] == "POST"
    assert data["endpoints"][0]["path"] == "/items"
    assert "API2" in data["endpoints"][0]["cells"]


# ── 8. GET /coverage with no endpoints ────────────────────────────────────────

def test_get_coverage_no_endpoints(client):
    coll, run = _make_collection_and_run(client)
    r = client.get(f"/api/api-test-runs/{run['id']}/coverage")
    assert r.status_code == 200
    data = r.json()
    assert data["endpoints"] == []


# ── 9. _applicable_categories — API2 always present ──────────────────────────

def test_applicable_categories_api2_always(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/ping", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API2" in cats


# ── 10. _applicable_categories — API1 for path params ─────────────────────────

def test_applicable_categories_api1_path_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users/{id}", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API1" in cats


def test_applicable_categories_no_api1_without_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API1" not in cats


# ── 11. _applicable_categories — API3 for PUT/PATCH ──────────────────────────

def test_applicable_categories_api3_patch(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="PATCH", path="/users/{id}", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API3" in cats


def test_applicable_categories_no_api3_get(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users/{id}", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API3" not in cats


# ── 12. _match_endpoint_for_url — exact path ──────────────────────────────────

def test_match_endpoint_exact(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/health", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    matched = _match_endpoint_for_url("http://api.local/health", [ep], "http://api.local")
    assert matched is not None
    assert matched.id == ep.id


# ── 13. _match_endpoint_for_url — parameterized path ─────────────────────────

def test_match_endpoint_path_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users/{id}", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    matched = _match_endpoint_for_url("http://api.local/users/42", [ep], "http://api.local")
    assert matched is not None
    assert matched.id == ep.id


def test_match_endpoint_nested_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="PATCH", path="/users/{uid}/posts/{pid}", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    matched = _match_endpoint_for_url("http://api.local/users/10/posts/200", [ep], "http://api.local")
    assert matched is not None
    assert matched.id == ep.id


# ── 14. _match_endpoint_for_url — no match ────────────────────────────────────

def test_match_endpoint_no_match(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/health", in_scope=True)
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    matched = _match_endpoint_for_url("http://api.local/foobar/baz", [ep], "http://api.local")
    assert matched is None


# ── 15. get_coverage_matrix totals ────────────────────────────────────────────

def test_get_coverage_matrix_totals(db_engine, db_session, collection, endpoint_simple, api_run):
    seed_coverage_matrix(api_run.id)
    mat = get_coverage_matrix(api_run.id)
    totals = mat["totals"]
    expected_total = sum(totals.values())
    # All seeded cells start as not_started
    assert totals.get("not_started", 0) == expected_total


# ── 16. post_finding_fn updates coverage cell ─────────────────────────────────

def test_post_finding_fn_updates_cell(db_engine, db_session, collection, endpoint_with_param, api_run):
    seed_coverage_matrix(api_run.id)

    from aespa.services.api_scanner import _make_post_finding_fn

    # Seed a finding
    finding = ScanFinding(
        test_run_id=api_run.id,
        page_id=None,
        owasp_category="API1",
        owasp_api_category="API1",
        severity="high",
        title="BOLA test finding",
        description="BOLA test finding description",
        affected_url="http://api.local/users/42",
    )
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)

    fn = _make_post_finding_fn(api_run.id)
    fn(finding)
    db_session.expire_all()

    # The API1 cell for endpoint_with_param should now be "finding"
    cell = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_with_param.id)
        .where(ApiEndpointTest.owasp_api_category == "API1")
    ).first()
    assert cell is not None
    assert cell.status == "finding"
    assert finding.id in json.loads(cell.finding_ids_json)


# ── 17. start-scan seeds matrix ───────────────────────────────────────────────

def test_start_scan_seeds_matrix(client, db_engine, db_session):
    coll, run = _make_collection_and_run(client)
    ep = ApiEndpoint(
        collection_id=coll["id"],
        method="GET",
        path="/items/{id}",
        in_scope=True,
    )
    db_session.add(ep)
    db_session.commit()

    with (
        patch("aespa.services.api_scanner._do_api_thinking_scan", new_callable=AsyncMock),
        patch("asyncio.create_task", side_effect=_fake_create_task),
    ):
        r = client.post(f"/api/api-test-runs/{run['id']}/scan/start")
    assert r.status_code == 200

    cells = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == run["id"])
    ).all()
    assert len(cells) > 0


# ── 18. _make_post_probe_fn — marks only the declared category in_progress ────

def test_post_probe_fn_marks_single_category(db_engine, db_session, collection, endpoint_with_param, api_run):
    """Calling the post_probe_fn with owasp_category=API1 should flip the API1
    cell to in_progress while leaving other categories untouched."""
    from aespa.services.api_scanner import _make_post_probe_fn

    seed_coverage_matrix(api_run.id)

    # Confirm API1 is applicable for this endpoint (has a path param)
    cats = _applicable_categories(endpoint_with_param)
    assert "API1" in cats

    # Populate the endpoint cache so _make_post_probe_fn can match the URL.
    from aespa.services.api_scanner import _endpoint_cache
    _endpoint_cache[api_run.id] = (collection.id, [endpoint_with_param])

    fn = _make_post_probe_fn(api_run.id)
    fn("http://api.local/users/99", "GET", "API1")
    db_session.expire_all()

    # API1 cell must be in_progress
    api1_cell = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_with_param.id)
        .where(ApiEndpointTest.owasp_api_category == "API1")
    ).first()
    assert api1_cell is not None
    assert api1_cell.status == "in_progress"

    # All other cells for this endpoint must remain not_started
    other_cells = db_session.exec(
        select(ApiEndpointTest)
        .where(ApiEndpointTest.api_test_run_id == api_run.id)
        .where(ApiEndpointTest.endpoint_id == endpoint_with_param.id)
        .where(ApiEndpointTest.owasp_api_category != "API1")
    ).all()
    for cell in other_cells:
        assert cell.status == "not_started", (
            f"Expected not_started for {cell.owasp_api_category}, got {cell.status}"
        )

    # Clean up cache
    _endpoint_cache.pop(api_run.id, None)


def test_post_probe_fn_no_match_is_noop(db_engine, db_session, collection, endpoint_with_param, api_run):
    """When the URL doesn't match any endpoint, the probe fn should silently do nothing."""
    from aespa.services.api_scanner import _endpoint_cache, _make_post_probe_fn

    seed_coverage_matrix(api_run.id)
    _endpoint_cache[api_run.id] = (collection.id, [endpoint_with_param])

    fn = _make_post_probe_fn(api_run.id)
    fn("http://api.local/completely/unknown/route/99", "GET", "API1")  # no match
    db_session.expire_all()

    all_cells = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()
    for cell in all_cells:
        assert cell.status == "not_started"

    _endpoint_cache.pop(api_run.id, None)


# ── Slice 8: Enforce coverage mode ────────────────────────────────────────────

def _all_cells(db_session, api_run_id):
    return db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run_id)
    ).all()


# ── _uncovered_cells returns only non-terminal cells ──────────────────────────

def test_uncovered_cells_excludes_terminal(db_engine, db_session, collection, endpoint_simple, api_run):
    seed_coverage_matrix(api_run.id)
    # Flip one cell to covered (terminal) — it should drop out of the uncovered list.
    update_coverage_cell(api_run.id, endpoint_simple.id, "API2", "covered")
    uncovered = _uncovered_cells(api_run.id)
    cats = {cat for _ep, cat, _status in uncovered}
    assert "API2" not in cats
    # The remaining applicable categories are still uncovered.
    assert "API4" in cats


# ── enforce loop drives every cell to a terminal state ────────────────────────

def test_enforce_loop_covers_all_cells(db_engine, db_session, collection, endpoint_simple, endpoint_with_param, api_run):
    seed_coverage_matrix(api_run.id)

    async def prober(ep, cat, status):
        return ("covered", None)

    stats = asyncio.run(_enforce_coverage_loop(api_run.id, prober, max_attempts=999, time_budget_s=999))

    db_session.expire_all()
    cells = _all_cells(db_session, api_run.id)
    assert cells
    assert all(c.status == "covered" for c in cells)
    assert stats["covered"] == len(cells)
    assert _uncovered_cells(api_run.id) == []


# ── enforce loop records skip reasons ─────────────────────────────────────────

def test_enforce_loop_records_skip_reasons(db_engine, db_session, collection, endpoint_simple, api_run):
    seed_coverage_matrix(api_run.id)

    async def prober(ep, cat, status):
        return ("skipped", f"not applicable: {cat}")

    stats = asyncio.run(_enforce_coverage_loop(api_run.id, prober, max_attempts=999, time_budget_s=999))

    db_session.expire_all()
    cells = _all_cells(db_session, api_run.id)
    assert all(c.status == "skipped" for c in cells)
    assert all(c.skip_reason and c.skip_reason.startswith("not applicable") for c in cells)
    assert stats["skipped"] == len(cells)


# ── enforce loop respects the attempt budget ──────────────────────────────────

def test_enforce_loop_respects_budget(db_engine, db_session, collection, endpoint_simple, endpoint_with_param, api_run):
    seed_coverage_matrix(api_run.id)
    total = len(_all_cells(db_session, api_run.id))
    assert total > 2  # need headroom so the budget actually bites

    async def prober(ep, cat, status):
        return ("covered", None)

    stats = asyncio.run(_enforce_coverage_loop(api_run.id, prober, max_attempts=2, time_budget_s=999))

    assert stats["attempted"] == 2
    assert stats["covered"] == 2
    assert stats["budget_exhausted"] is True

    db_session.expire_all()
    cells = _all_cells(db_session, api_run.id)
    covered = [c for c in cells if c.status == "covered"]
    skipped = [c for c in cells if c.status == "skipped"]
    assert len(covered) == 2
    assert len(skipped) == total - 2
    # Cells not reached within budget are skipped with a clear reason.
    assert all(c.skip_reason == "coverage budget exhausted" for c in skipped)
    # No cell is left dangling.
    assert _uncovered_cells(api_run.id) == []


# ── enforce loop halts on stop_check ──────────────────────────────────────────

def test_enforce_loop_stop_check_halts(db_engine, db_session, collection, endpoint_simple, endpoint_with_param, api_run):
    seed_coverage_matrix(api_run.id)
    calls = {"n": 0}

    async def prober(ep, cat, status):
        calls["n"] += 1
        return ("covered", None)

    # Stop after the first attempt completes.
    stats = asyncio.run(
        _enforce_coverage_loop(
            api_run.id, prober,
            max_attempts=999, time_budget_s=999,
            stop_check=lambda: calls["n"] >= 1,
        )
    )
    assert stats["attempted"] == 1
    assert stats["budget_exhausted"] is True
    # Everything else is closed out as budget-exhausted.
    assert _uncovered_cells(api_run.id) == []


# ── default prober: in_progress cells are promoted to covered (no LLM) ─────────

def test_enforce_prober_promotes_in_progress(db_engine, db_session, collection, endpoint_simple, api_run):
    prober = _make_enforce_prober(api_run.id, llm_cfg=None, base_url="")
    status, reason = asyncio.run(prober(endpoint_simple, "API2", "in_progress"))
    assert status == "covered"
    assert reason is None


# ── default prober: not_started cells classified N/A via the LLM ──────────────

def test_enforce_prober_classifies_not_applicable(db_engine, db_session, collection, endpoint_simple, api_run):
    import aespa.services.llm as llm_mod

    fake = AsyncMock(return_value='{"API2": {"applicable": false, "reason": "no auth required"}}')
    with patch.object(llm_mod, "plain_completion", new=fake):
        prober = _make_enforce_prober(api_run.id, llm_cfg=object(), base_url="")
        status, reason = asyncio.run(prober(endpoint_simple, "API2", "not_started"))

    assert status == "skipped"
    assert "not applicable" in reason
    assert "no auth required" in reason


# ── enforce directive lists endpoints + categories ───────────────────────────

def test_build_enforce_directive_lists_checklist(db_engine, db_session, collection, endpoint_simple, api_run):
    seed_coverage_matrix(api_run.id)
    text = _build_enforce_directive(api_run.id)
    assert "ENFORCE COVERAGE MODE" in text
    assert "/health" in text
    assert "API2" in text


def test_build_enforce_directive_empty_when_nothing_uncovered(db_engine, db_session, collection, endpoint_simple, api_run):
    seed_coverage_matrix(api_run.id)
    # Cover every cell so there is nothing left to enforce.
    for ep, cat, _status in _uncovered_cells(api_run.id):
        update_coverage_cell(api_run.id, ep.id, cat, "covered")
    assert _build_enforce_directive(api_run.id) == ""


# ── scan-start accepts a coverage_mode override ───────────────────────────────

def test_scan_start_overrides_coverage_mode(client, db_engine, db_session):
    coll, run = _make_collection_and_run(client)  # defaults to track
    with (
        patch("aespa.services.api_scanner._do_api_thinking_scan", new_callable=AsyncMock),
        patch("asyncio.create_task", side_effect=_fake_create_task),
    ):
        r = client.post(f"/api/api-test-runs/{run['id']}/scan/start", json={"coverage_mode": "enforce"})
    assert r.status_code == 200
    assert r.json()["coverage_mode"] == "enforce"

    db_session.expire_all()
    refreshed = db_session.get(ApiTestRun, run["id"])
    assert refreshed.coverage_mode == "enforce"
