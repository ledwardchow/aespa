"""Tests for Slice 5: ApiTestRun CRUD and alias endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from aespa.db import get_session
from aespa.main import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401
    SQLModel.metadata.create_all(engine)

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_collection(client: TestClient, name: str = "Test API") -> int:
    r = client.post("/api/api-collections", json={"name": name, "base_url": "https://example.com"})
    assert r.status_code == 201
    return r.json()["id"]


def _make_run(client: TestClient, collection_id: int, name: str = "Run 1") -> dict:
    r = client.post(f"/api/api-collections/{collection_id}/test-runs", json={"name": name})
    assert r.status_code == 201
    return r.json()


# ── List / Create ──────────────────────────────────────────────────────────────

def test_list_runs_empty(client):
    cid = _make_collection(client)
    r = client.get(f"/api/api-collections/{cid}/test-runs")
    assert r.status_code == 200
    assert r.json() == []


def test_create_run_basic(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    assert run["id"] is not None
    assert run["collection_id"] == cid
    assert run["status"] == "pending"
    assert run["coverage_mode"] == "track"
    assert run["name"] == "Run 1"


def test_create_run_auto_name(client):
    cid = _make_collection(client)
    r = client.post(f"/api/api-collections/{cid}/test-runs", json={})
    assert r.status_code == 201
    data = r.json()
    assert data["name"]  # auto-generated


def test_create_run_coverage_mode(client):
    cid = _make_collection(client)
    r = client.post(
        f"/api/api-collections/{cid}/test-runs",
        json={"name": "Enforce run", "coverage_mode": "enforce"},
    )
    assert r.status_code == 201
    assert r.json()["coverage_mode"] == "enforce"


def test_list_runs_returns_newest_first(client):
    cid = _make_collection(client)
    _make_run(client, cid, "First")
    _make_run(client, cid, "Second")
    r = client.get(f"/api/api-collections/{cid}/test-runs")
    assert r.status_code == 200
    names = [x["name"] for x in r.json()]
    assert names[0] == "Second"
    assert names[1] == "First"


def test_create_run_404_collection(client):
    r = client.post("/api/api-collections/9999/test-runs", json={"name": "x"})
    assert r.status_code == 404


# ── Get / Delete ───────────────────────────────────────────────────────────────

def test_get_run(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    r = client.get(f"/api/api-test-runs/{run['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == run["id"]


def test_get_run_404(client):
    r = client.get("/api/api-test-runs/9999")
    assert r.status_code == 404


def test_delete_run(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    r = client.delete(f"/api/api-test-runs/{run['id']}")
    assert r.status_code == 204
    r = client.get(f"/api/api-test-runs/{run['id']}")
    assert r.status_code == 404


def test_delete_run_404(client):
    r = client.delete("/api/api-test-runs/9999")
    assert r.status_code == 404


# ── Alice alias endpoints (session persistence) ────────────────────────────────

def test_alice_sessions_get_empty(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    r = client.get(f"/api/api-test-runs/{run['id']}/alice/sessions")
    assert r.status_code == 200
    body = r.json()
    assert "chats" in body
    assert isinstance(body["chats"], list)


def test_alice_sessions_save_and_reload(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    rid = run["id"]

    payload = {
        "chats": [
            {
                "id": "tab-default",
                "title": "Session 1",
                "messages": [{"id": "m1", "sender": "user", "type": "message", "text": "hello", "ts": "12:00"}],
            }
        ],
        "active_tab_id": "tab-default",
    }
    r = client.put(f"/api/api-test-runs/{rid}/alice/sessions", json=payload)
    assert r.status_code == 200

    r2 = client.get(f"/api/api-test-runs/{rid}/alice/sessions")
    assert r2.status_code == 200
    body = r2.json()
    assert len(body["chats"]) == 1
    assert body["chats"][0]["messages"][0]["text"] == "hello"


def test_alice_sessions_404(client):
    r = client.get("/api/api-test-runs/9999/alice/sessions")
    assert r.status_code == 404


def test_alice_status_endpoint(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    r = client.get(f"/api/api-test-runs/{run['id']}/alice/status")
    assert r.status_code == 200


# ── Agent log alias ────────────────────────────────────────────────────────────

def test_agent_log_empty(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    r = client.get(f"/api/api-test-runs/{run['id']}/agent-log")
    assert r.status_code == 200
    assert r.json() == []


def test_agent_log_404(client):
    r = client.get("/api/api-test-runs/9999/agent-log")
    assert r.status_code == 404


# ── Events alias (streaming) ───────────────────────────────────────────────────

def test_events_endpoint_404(client):
    r = client.get("/api/api-test-runs/9999/events")
    assert r.status_code == 404


# ── Regression: API and web findings must not cross the shared id space ─────────

def test_api_and_web_findings_do_not_cross():
    """ApiTestRun.id and TestRun.id are independent autoincrement sequences, so
    the first run of each kind both get id=1.  Findings must stay attached to
    their own run kind: web findings key on test_run_id, API findings on
    api_test_run_id (with test_run_id left NULL).  Regression for API findings
    leaking into the web run of the same integer id."""
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, Session, create_engine
    from aespa import models
    from aespa.db import get_session
    from aespa.main import create_app

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        site = models.Site(name="S", base_url="https://example.com")
        s.add(site); s.commit(); s.refresh(site)
        web_run = models.TestRun(site_id=site.id, name="web")
        s.add(web_run); s.commit(); s.refresh(web_run)

        coll = models.ApiCollection(name="C", base_url="https://example.com")
        s.add(coll); s.commit(); s.refresh(coll)
        api_run = models.ApiTestRun(collection_id=coll.id, name="api")
        s.add(api_run); s.commit(); s.refresh(api_run)

        web_run_id, api_run_id = web_run.id, api_run.id
        # The collision that used to cause the leak.
        assert web_run_id == api_run_id == 1

        s.add(models.ScanFinding(
            test_run_id=web_run_id, owasp_category="A01", severity="high",
            title="WEB FINDING", description="d", evidence="e",
        ))
        s.add(models.ScanFinding(
            api_test_run_id=api_run_id, owasp_category="API1", severity="high",
            title="API FINDING", description="d", evidence="e",
        ))
        s.commit()

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        web = c.get(f"/api/test-runs/{web_run_id}/findings")
        api = c.get(f"/api/api-test-runs/{api_run_id}/findings")
        assert web.status_code == 200
        assert api.status_code == 200
        assert [f["title"] for f in web.json()] == ["WEB FINDING"]
        assert [f["title"] for f in api.json()] == ["API FINDING"]
        # The API finding serialises fine even with a NULL test_run_id.
        assert api.json()[0]["test_run_id"] is None

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


# ── Regression: API log rows must not be mis-tagged when ids collide ─────────────

def test_run_kind_scope_overrides_colliding_registration():
    """Core of issue #169.  Run ids collide across web / api / sast (independent
    counters), so the id-keyed fallback is ambiguous — when id 1 is registered as
    both sast and api, the fallback wrongly resolves 'sast', which made the API
    Status page's Test Lead history and Log tab come back empty.  The
    ``run_kind_scope`` set by the running scan is authoritative and collision-proof."""
    from aespa.services import events as events_svc

    events_svc.register_sast_run(1)
    events_svc.register_api_run(1)
    try:
        # Ambiguous id-only fallback (the bug): sast is checked first and wins.
        assert events_svc._run_kind_for(1, {}) == "sast"
        # The API scan's scope makes the tag authoritative.
        with events_svc.run_kind_scope("api"):
            assert events_svc._run_kind_for(1, {}) == "api"
        # Nested scope — a SAST pre-phase awaited inside an API scan — restores.
        with events_svc.run_kind_scope("api"):
            with events_svc.run_kind_scope("sast"):
                assert events_svc._run_kind_for(1, {}) == "sast"
            assert events_svc._run_kind_for(1, {}) == "api"
        # An explicit per-event tag still wins over everything.
        with events_svc.run_kind_scope("sast"):
            assert events_svc._run_kind_for(1, {"_run_kind": "api"}) == "api"
    finally:
        events_svc._api_run_ids.discard(1)
        events_svc._sast_run_ids.discard(1)


def test_run_kind_scope_snapshotted_by_child_task():
    """start_api_scan opens run_kind_scope('api') and create_task()s the scan,
    then returns (closing the scope) while the task keeps running.  This verifies
    the asyncio.create_task context snapshot the fix relies on: the child task
    stays tagged 'api' after the parent leaves the scope."""
    import asyncio
    from aespa.services import events as events_svc

    events_svc.register_sast_run(1)
    events_svc.register_api_run(1)
    captured: dict[str, str] = {}

    async def _child() -> None:
        await asyncio.sleep(0)  # force a real suspension/resume
        captured["kind"] = events_svc._run_kind_for(1, {})

    async def _main() -> None:
        with events_svc.run_kind_scope("api"):
            task = asyncio.create_task(_child())
        # Scope is closed in this frame, but the task snapshotted it at creation.
        await task

    try:
        asyncio.run(_main())
        assert captured["kind"] == "api"
    finally:
        events_svc._api_run_ids.discard(1)
        events_svc._sast_run_ids.discard(1)


def test_api_agent_and_scan_log_tagged_api_despite_sast_collision():
    """End-to-end persistence regression for issue #169.  An API run whose id
    collides with a registered SAST run must still have its agent_log / scan_log
    rows written with run_kind='api', so the API agent-log endpoint returns them."""
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, Session, create_engine, select
    from aespa import models
    from aespa import db as db_mod
    from aespa.db import get_session, set_engine
    from aespa.main import create_app
    from aespa.services import events as events_svc

    prev_engine = db_mod._engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    set_engine(engine)  # events persistence uses get_engine() directly

    with Session(engine) as s:
        coll = models.ApiCollection(name="C", base_url="https://example.com")
        s.add(coll); s.commit(); s.refresh(coll)
        api_run = models.ApiTestRun(collection_id=coll.id, name="api")
        s.add(api_run); s.commit(); s.refresh(api_run)
        api_run_id = api_run.id

    # The collision: id 1 was also registered as a SAST run in this process.
    events_svc.register_sast_run(api_run_id)
    events_svc.register_api_run(api_run_id)

    try:
        with events_svc.run_kind_scope("api"):
            events_svc.emit(api_run_id, {
                "type": "agent_status", "agent_id": "scanner", "role": "Test Lead",
                "status": "active", "current_task": "Step 1: GET /api/x", "outcome": None,
            })
            events_svc.emit(api_run_id, {
                "type": "scanner_phase", "phase": "thinking_step",
                "status": "deciding", "message": "reasoning", "data": {"step": 1},
            })

        with Session(engine) as s:
            agent_rows = s.exec(
                select(models.AgentLog).where(models.AgentLog.test_run_id == api_run_id)
            ).all()
            scan_rows = s.exec(
                select(models.ScanLog).where(models.ScanLog.test_run_id == api_run_id)
            ).all()
        assert [r.run_kind for r in agent_rows] == ["api"]
        assert [r.run_kind for r in scan_rows] == ["api"]

        # The API agent-log endpoint (filters run_kind='api') now returns the row.
        def _override_session():
            with Session(engine) as session:
                yield session

        app = create_app()
        app.dependency_overrides[get_session] = _override_session
        with TestClient(app, raise_server_exceptions=True) as c:
            r = c.get(f"/api/api-test-runs/{api_run_id}/agent-log")
            assert r.status_code == 200
            assert [row["current_task"] for row in r.json()] == ["Step 1: GET /api/x"]
    finally:
        events_svc._api_run_ids.discard(api_run_id)
        events_svc._sast_run_ids.discard(api_run_id)
        set_engine(prev_engine)
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
