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
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import set_engine, get_engine, _migrate
from aespa.models import (
    ApiCollection,
    ApiCredential,
    ApiEndpoint,
    ApiEndpointTest,
    ApiTestRun,
    ScanFinding,
)
from aespa.services.api_scanner import (
    _applicable_categories,
    _match_endpoint_for_url,
    get_coverage_matrix,
    mark_all_cells_covered,
    seed_coverage_matrix,
    update_coverage_cell,
    OWASP_API_CATEGORIES,
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
    from aespa.main import create_app
    from aespa.db import get_session as gs

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
    # Manually set one cell to finding, one to skipped
    cells = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()
    cells[0].status = "finding"
    cells[1].status = "skipped"
    db_session.add(cells[0])
    db_session.add(cells[1])
    db_session.commit()

    mark_all_cells_covered(api_run.id)
    db_session.expire_all()

    updated = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == api_run.id)
    ).all()
    for c in updated:
        if c.id in (cells[0].id, cells[1].id):
            # These should be unchanged
            assert c.status in ("finding", "skipped")
        else:
            assert c.status == "covered"


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
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API2" in cats


# ── 10. _applicable_categories — API1 for path params ─────────────────────────

def test_applicable_categories_api1_path_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users/{id}", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API1" in cats


def test_applicable_categories_no_api1_without_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API1" not in cats


# ── 11. _applicable_categories — API3 for PUT/PATCH ──────────────────────────

def test_applicable_categories_api3_patch(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="PATCH", path="/users/{id}", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API3" in cats


def test_applicable_categories_no_api3_get(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users/{id}", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    cats = _applicable_categories(ep)
    assert "API3" not in cats


# ── 12. _match_endpoint_for_url — exact path ──────────────────────────────────

def test_match_endpoint_exact(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/health", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    matched = _match_endpoint_for_url("http://api.local/health", [ep], "http://api.local")
    assert matched is not None
    assert matched.id == ep.id


# ── 13. _match_endpoint_for_url — parameterized path ─────────────────────────

def test_match_endpoint_path_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/users/{id}", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    matched = _match_endpoint_for_url("http://api.local/users/42", [ep], "http://api.local")
    assert matched is not None
    assert matched.id == ep.id


def test_match_endpoint_nested_param(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="PATCH", path="/users/{uid}/posts/{pid}", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
    matched = _match_endpoint_for_url("http://api.local/users/10/posts/200", [ep], "http://api.local")
    assert matched is not None
    assert matched.id == ep.id


# ── 14. _match_endpoint_for_url — no match ────────────────────────────────────

def test_match_endpoint_no_match(db_engine, db_session, collection):
    ep = ApiEndpoint(collection_id=collection.id, method="GET", path="/health", in_scope=True)
    db_session.add(ep); db_session.commit(); db_session.refresh(ep)
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
        patch("asyncio.create_task") as mock_task,
    ):
        mock_task.return_value = AsyncMock()
        r = client.post(f"/api/api-test-runs/{run['id']}/scan/start")
    assert r.status_code == 200

    cells = db_session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == run["id"])
    ).all()
    assert len(cells) > 0
