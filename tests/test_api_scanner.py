"""Slice 6 tests: API scanner service + findings/traffic alias routes.

Tests:
  1. seed_sessions_from_credentials populates ScannerSession for each ApiCredential
  2. report_finding context-tool sub-command writes a ScanFinding with api_test_run_id
  3. GET /api/api-test-runs/{id}/findings returns findings keyed by api_test_run_id
  4. GET /api/api-test-runs/{id}/traffic returns traffic keyed by test_run_id
  5. POST /api/api-test-runs/{id}/scan/start fires alice_tasks.start (mocked)
  6. POST /api/api-test-runs/{id}/scan/stop fires alice_tasks.stop (mocked)
  7. GET /api/api-test-runs/{id}/scan/status returns status dict
  8. report_finding validates severity; defaults to "info"
  9. report_finding sets finding_source = "alice_api"
  10. ScanFinding schema includes api_test_run_id + owasp_api_category fields
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import set_engine
from aespa.models import (
    ApiCollection,
    ApiCredential,
    ApiTestRun,
    ScanFinding,
    TrafficEntry,
)

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
    coll = ApiCollection(name="TestAPI", base_url="http://api.local")
    db_session.add(coll)
    db_session.commit()
    db_session.refresh(coll)
    return coll


@pytest.fixture(name="api_run")
def api_run_fixture(db_session, collection):
    run = ApiTestRun(
        collection_id=collection.id,
        name="Test Run 1",
        status="pending",
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


@pytest.fixture(name="bearer_cred")
def bearer_cred_fixture(db_session, collection):
    cred = ApiCredential(
        collection_id=collection.id,
        scheme="bearer",
        name="Authorization",
        value="tok_test_abc123",
        label="admin_token",
    )
    db_session.add(cred)
    db_session.commit()
    db_session.refresh(cred)
    return cred


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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_collection(client):
    r = client.post("/api/api-collections", json={"name": "ScanAPI", "base_url": "http://target.api"})
    assert r.status_code == 201
    return r.json()


def _make_run(client, coll_id):
    r = client.post(f"/api/api-collections/{coll_id}/test-runs", json={"name": "run1"})
    assert r.status_code == 201
    return r.json()


# ── Tests: seed_sessions_from_credentials ─────────────────────────────────────

def test_seed_sessions_creates_anonymous_and_configured(db_engine, collection, api_run, bearer_cred):
    """seed_sessions_from_credentials should create anonymous + bearer sessions."""
    from aespa.services.api_scanner import seed_sessions_from_credentials
    from aespa.services.scanner_sessions import list_run_sessions

    count = seed_sessions_from_credentials(api_run.id)

    sessions = list_run_sessions(api_run.id, run_kind="api")
    labels = {s.label for s in sessions}

    assert count >= 2  # anonymous + at least the bearer cred
    assert "anonymous" in labels
    assert any("admin_token" in lbl or "bearer" in lbl for lbl in labels)


def test_seed_sessions_bearer_sets_extra_header(db_engine, collection, api_run, bearer_cred):
    """Bearer credentials should populate extra_headers_json with Authorization."""
    from aespa.services.api_scanner import seed_sessions_from_credentials
    from aespa.services.scanner_sessions import list_run_sessions

    seed_sessions_from_credentials(api_run.id)
    sessions = list_run_sessions(api_run.id, run_kind="api")

    bearer_session = next((s for s in sessions if "admin_token" in s.label or s.kind == "bearer"), None)
    assert bearer_session is not None

    extra = json.loads(bearer_session.extra_headers_json or "{}")
    assert "Authorization" in extra
    assert "tok_test_abc123" in extra["Authorization"]


def test_seed_sessions_no_creds_only_anonymous(db_engine, collection, api_run):
    """If no credentials exist, only the anonymous session is created."""
    from aespa.services.api_scanner import seed_sessions_from_credentials
    from aespa.services.scanner_sessions import list_run_sessions

    count = seed_sessions_from_credentials(api_run.id)
    sessions = list_run_sessions(api_run.id, run_kind="api")

    assert count == 1
    assert sessions[0].label == "anonymous"


# ── Tests: report_finding via context tool ────────────────────────────────────

def test_report_finding_persists_scan_finding(db_engine, collection, api_run):
    """report_finding should write a ScanFinding with api_test_run_id set."""
    from aespa.services.alice import _run_api_context_tool

    result = _run_api_context_tool(
        collection.id,
        api_run.id,
        "report_finding",
        {
            "title": "SQL Injection in /users endpoint",
            "severity": "high",
            "owasp_api_category": "API8",
            "description": "The /users endpoint is vulnerable to SQL injection.",
            "affected_url": "http://api.local/users?id=1",
            "evidence": "Response: 500 Internal Server Error with DB error",
        },
    )

    assert result["ok"] is True
    assert result["severity"] == "high"
    assert result["title"] == "SQL Injection in /users endpoint"
    assert "finding_id" in result

    with Session(db_engine) as s:
        finding = s.get(ScanFinding, result["finding_id"])
    assert finding is not None
    assert finding.api_test_run_id == api_run.id
    assert finding.owasp_api_category == "API8"
    assert finding.severity == "high"
    assert finding.finding_source == "alice_api"


def test_report_finding_defaults_severity_to_info(db_engine, collection, api_run):
    """report_finding with invalid severity should default to 'info'."""
    from aespa.services.alice import _run_api_context_tool

    result = _run_api_context_tool(
        collection.id,
        api_run.id,
        "report_finding",
        {"title": "Minor issue", "severity": "extreme"},
    )

    assert result["ok"] is True
    assert result["severity"] == "info"


def test_report_finding_sets_finding_source(db_engine, collection, api_run):
    """report_finding should set finding_source to 'alice_api'."""
    from aespa.services.alice import _run_api_context_tool

    result = _run_api_context_tool(
        collection.id, api_run.id, "report_finding",
        {"title": "Auth bypass", "severity": "critical"},
    )

    with Session(db_engine) as s:
        finding = s.get(ScanFinding, result["finding_id"])
    assert finding.finding_source == "alice_api"


# ── Tests: API findings route ──────────────────────────────────────────────────

def test_get_api_findings_returns_findings_for_run(client, db_engine):
    """GET /api/api-test-runs/{id}/findings should return findings with api_test_run_id."""
    coll = _make_collection(client)
    run = _make_run(client, coll["id"])
    run_id = run["id"]

    # Insert a finding directly
    with Session(db_engine) as s:
        f = ScanFinding(
            test_run_id=run_id,
            api_test_run_id=run_id,
            owasp_category="A01",
            severity="high",
            title="Test Finding",
            description="desc",
            affected_url="http://target.api/endpoint",
            evidence="",
        )
        s.add(f)
        s.commit()

    r = client.get(f"/api/api-test-runs/{run_id}/findings")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Finding"
    assert data[0]["api_test_run_id"] == run_id


def test_get_api_findings_excludes_other_run_findings(client, db_engine):
    """Findings for a different api_test_run_id should not appear."""
    coll = _make_collection(client)
    run1 = _make_run(client, coll["id"])
    run2 = _make_run(client, coll["id"])

    with Session(db_engine) as s:
        f = ScanFinding(
            test_run_id=run1["id"],
            api_test_run_id=run1["id"],
            owasp_category="A01",
            severity="low",
            title="Run1 Finding",
            description="",
            affected_url="",
            evidence="",
        )
        s.add(f)
        s.commit()

    r = client.get(f"/api/api-test-runs/{run2['id']}/findings")
    assert r.status_code == 200
    assert r.json() == []


def test_get_api_findings_404_for_unknown_run(client):
    r = client.get("/api/api-test-runs/99999/findings")
    assert r.status_code == 404


# ── Tests: API traffic route ───────────────────────────────────────────────────

def test_get_api_traffic_returns_entries(client, db_engine):
    """GET /api/api-test-runs/{id}/traffic should return traffic for the run."""
    coll = _make_collection(client)
    run = _make_run(client, coll["id"])
    run_id = run["id"]

    with Session(db_engine) as s:
        entry = TrafficEntry(
            test_run_id=0,
            api_test_run_id=run_id,
            source="httpx",
            method="GET",
            url="http://target.api/health",
            request_headers="{}",
            status=200,
        )
        s.add(entry)
        s.commit()

    r = client.get(f"/api/api-test-runs/{run_id}/traffic")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["url"] == "http://target.api/health"


def test_get_api_traffic_count(client, db_engine):
    coll = _make_collection(client)
    run = _make_run(client, coll["id"])
    run_id = run["id"]

    with Session(db_engine) as s:
        for i in range(3):
            s.add(TrafficEntry(
                test_run_id=0, api_test_run_id=run_id, source="httpx",
                method="POST", url=f"http://target.api/ep{i}",
                request_headers="{}", status=201,
            ))
        s.commit()

    r = client.get(f"/api/api-test-runs/{run_id}/traffic/count")
    assert r.status_code == 200
    assert r.json()["count"] == 3


# ── Tests: scan start/stop/status routes ──────────────────────────────────────

def test_scan_start_creates_task(client):
    """POST /scan/start should create an asyncio task and return ok=True."""
    coll = _make_collection(client)
    run = _make_run(client, coll["id"])
    run_id = run["id"]

    # The route schedules the scan as a background task, but TestClient's event loop
    # closes right after the request — the coroutine would never run and would leak a
    # "never awaited" warning. Stub create_task to close the coroutine and hand back a
    # done-looking task; the route only needs the registry entry + ok=True here.
    def _fake_create_task(coro, **kwargs):
        coro.close()
        t = MagicMock()
        t.done.return_value = True
        return t

    target = "aespa.services.api_scanner.asyncio.create_task"
    with patch(target, side_effect=_fake_create_task):
        r = client.post(f"/api/api-test-runs/{run_id}/scan/start")

    assert r.status_code == 200
    assert r.json()["ok"] is True

    from aespa.services import api_scanner
    api_scanner._scan_tasks.pop(run_id, None)


def test_scan_stop_returns_ok(client):
    """POST /scan/stop should return ok=True (even when no scan running)."""
    coll = _make_collection(client)
    run = _make_run(client, coll["id"])
    run_id = run["id"]

    r = client.post(f"/api/api-test-runs/{run_id}/scan/stop")

    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_scan_status_returns_dict(client):
    """GET /scan/status should return a dict with 'running' and 'status' keys."""
    coll = _make_collection(client)
    run = _make_run(client, coll["id"])
    run_id = run["id"]

    r = client.get(f"/api/api-test-runs/{run_id}/scan/status")
    assert r.status_code == 200
    data = r.json()
    assert "running" in data
    assert "status" in data


def test_scan_start_404_for_unknown_run(client):
    r = client.post("/api/api-test-runs/99999/scan/start")
    assert r.status_code == 404


# ── Tests: ScanFinding schema ──────────────────────────────────────────────────

def test_scan_finding_schema_includes_api_fields():
    """ScanFindingOut schema should include api_test_run_id and owasp_api_category."""
    from aespa.schemas import ScanFindingOut
    fields = ScanFindingOut.model_fields
    assert "api_test_run_id" in fields
    assert "owasp_api_category" in fields


def test_scan_finding_model_has_api_columns(db_engine):
    """ScanFinding model should have api_test_run_id column after migration."""
    from aespa.db import _migrate
    _migrate(db_engine)

    with Session(db_engine) as s:
        f = ScanFinding(
            test_run_id=999,
            api_test_run_id=999,
            owasp_category="A00",
            owasp_api_category="API1",
            severity="info",
            title="Test",
            description="",
            affected_url="",
            evidence="",
        )
        s.add(f)
        s.commit()
        s.refresh(f)
        assert f.api_test_run_id == 999
        assert f.owasp_api_category == "API1"


# ── Tests: discovered-credential persistence (regression) ─────────────────────

def test_discovered_credential_saved_to_collection_not_site(db_engine, collection, api_run):
    """A credential discovered during an API scan must be saved as an ApiCredential
    on the collection — never as a site Credential.

    Regression: the shared loop previously called _maybe_persist_discovered_credential,
    which resolves run_id as a TestRun id and writes a site Credential. Because
    test_run/api_test_run ids overlap, that attached the credential to an unrelated site.
    """
    from aespa.models import ApiCredential, Credential, Site, TestRun
    from aespa.services.api_scanner import _make_persist_credential_fn

    # Seed a Site + TestRun whose id collides with the ApiTestRun id, to prove the
    # hook does not touch the site even when a colliding TestRun exists.
    with Session(db_engine) as s:
        site = Site(name="Unrelated Site", base_url="http://unrelated.local")
        s.add(site)
        s.commit()
        s.refresh(site)
        tr = TestRun(id=api_run.id, site_id=site.id, name="unrelated run", status="completed")
        s.add(tr)
        s.commit()

    persist = _make_persist_credential_fn(collection.id, api_run.id)
    persist(username="alice@example.com", password="hunter2", login_url="/api/auth/login")

    with Session(db_engine) as s:
        api_creds = list(s.exec(
            select(ApiCredential).where(ApiCredential.collection_id == collection.id)
        ).all())
        site_creds = list(s.exec(select(Credential)).all())

    assert len(site_creds) == 0, "discovered cred must not be written to a site"
    assert len(api_creds) == 1
    cred = api_creds[0]
    assert cred.scheme == "login"
    assert cred.value == "alice@example.com:hunter2"
    assert cred.label == "alice@example.com"
    assert cred.auth_endpoint == "/api/auth/login"


def test_discovered_credential_dedup(db_engine, collection, api_run):
    """Persisting the same discovered credential twice creates only one ApiCredential."""
    from aespa.models import ApiCredential
    from aespa.services.api_scanner import _make_persist_credential_fn

    persist = _make_persist_credential_fn(collection.id, api_run.id)
    persist(username="bob", password="pw", login_url=None)
    persist(username="bob", password="pw", login_url=None)

    with Session(db_engine) as s:
        api_creds = list(s.exec(
            select(ApiCredential).where(ApiCredential.collection_id == collection.id)
        ).all())
    assert len(api_creds) == 1
