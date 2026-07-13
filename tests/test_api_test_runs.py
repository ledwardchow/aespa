"""Tests for Slice 5: ApiTestRun CRUD and alias endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

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


def _import_finding(client: TestClient, run_id: int, title: str = "Leaky finding") -> None:
    r = client.post(
        f"/api/api-test-runs/{run_id}/findings/import",
        json=[{"title": title, "severity": "high", "owasp_api_category": "API1"}],
    )
    assert r.status_code == 200, r.text


def test_delete_run_cleans_up_findings_so_reused_id_is_clean(client):
    """Regression for #173: deleting an API run must remove its findings, or a new
    run that reuses the freed (SQLite-recycled) id inherits them."""
    cid = _make_collection(client)
    run1 = _make_run(client, cid, "Run 1")
    _import_finding(client, run1["id"])

    # The run owns the finding before deletion.
    r = client.get(f"/api/api-test-runs/{run1['id']}/findings")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Delete the run; a freshly created run reuses the same integer id.
    assert client.delete(f"/api/api-test-runs/{run1['id']}").status_code == 204
    run2 = _make_run(client, cid, "Run 2")
    assert run2["id"] == run1["id"], "expected SQLite to recycle the freed id"

    # The new run must NOT see the deleted run's finding.
    r = client.get(f"/api/api-test-runs/{run2['id']}/findings")
    assert r.status_code == 200
    assert r.json() == []


def test_update_api_finding_edits_status_severity_and_text(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    _import_finding(client, run["id"])
    finding = client.get(f"/api/api-test-runs/{run['id']}/findings").json()[0]

    r = client.patch(
        f"/api/api-test-runs/{run['id']}/findings/{finding['id']}",
        json={
            "validation_status": "unconfirmed",
            "severity": "low",
            "title": "Edited API finding",
            "owasp_api_category": "API5",
        },
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["validation_status"] == "unconfirmed"
    assert data["severity"] == "low"
    assert data["title"] == "Edited API finding"
    assert data["owasp_api_category"] == "API5"


def test_update_api_finding_unknown_id_404(client):
    cid = _make_collection(client)
    run = _make_run(client, cid)
    r = client.patch(
        f"/api/api-test-runs/{run['id']}/findings/999999",
        json={"severity": "low"},
    )
    assert r.status_code == 404


def test_delete_collection_cascades_runs_and_findings(client):
    """Deleting a collection must remove its runs (and their findings), or a new
    collection reusing the freed id inherits the orphaned runs."""
    cid = _make_collection(client, "App A")
    run = _make_run(client, cid, "Run 1")
    _import_finding(client, run["id"])

    assert client.delete(f"/api/api-collections/{cid}").status_code == 204

    # New collection reuses the freed id; it must start with no runs.
    cid2 = _make_collection(client, "App B")
    assert cid2 == cid, "expected SQLite to recycle the freed collection id"
    r = client.get(f"/api/api-collections/{cid2}/test-runs")
    assert r.status_code == 200
    assert r.json() == []


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
                "messages": [
                    {"id": "m1", "sender": "user", "type": "message", "text": "hello", "ts": "12:00"},
                    {
                        "id": "m2",
                        "sender": "alice",
                        "type": "thinking",
                        "text": "[Step 1] Executing tool: context_tool",
                        "ts": "12:01",
                        "stepData": {
                            "1": {
                                "llmMessages": [],
                                "tools": [{"tool": "context_tool", "input": {"tool": "finding_list"}, "result": "{\"count\":0}"}],
                            }
                        },
                    },
                ],
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
    assert body["chats"][0]["messages"][1]["stepData"]["1"]["tools"][0]["result"] == "{\"count\":0}"


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
    from sqlmodel import Session, SQLModel, create_engine

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
        s.add(site)
        s.commit()
        s.refresh(site)
        web_run = models.TestRun(site_id=site.id, name="web")
        s.add(web_run)
        s.commit()
        s.refresh(web_run)

        coll = models.ApiCollection(name="C", base_url="https://example.com")
        s.add(coll)
        s.commit()
        s.refresh(coll)
        api_run = models.ApiTestRun(collection_id=coll.id, name="api")
        s.add(api_run)
        s.commit()
        s.refresh(api_run)

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

def test_run_kind_is_resolved_by_scope_only():
    """Run ids collide across web / api / sast (independent counters), so the
    run_kind cannot be inferred from the id.  ``run_kind_scope`` is the sole,
    authoritative source; with no scope the tag deterministically defaults to
    'web' (never routed by stale per-id global state, which is what leaked events
    across runs — issue #169)."""
    from aespa.services import events as events_svc

    # No scope → deterministic 'web' default, regardless of the id.
    assert events_svc._run_kind_for(1, {}) == "web"
    # The running scan's scope makes the tag authoritative.
    with events_svc.run_kind_scope("api"):
        assert events_svc._run_kind_for(1, {}) == "api"
    with events_svc.run_kind_scope("sast"):
        assert events_svc._run_kind_for(1, {}) == "sast"
    # Nested scopes restore the outer API kind.
    with events_svc.run_kind_scope("api"):
        with events_svc.run_kind_scope("sast"):
            assert events_svc._run_kind_for(1, {}) == "sast"
        assert events_svc._run_kind_for(1, {}) == "api"
    # An explicit per-event tag still wins over everything.
    with events_svc.run_kind_scope("sast"):
        assert events_svc._run_kind_for(1, {"_run_kind": "api"}) == "api"


def test_run_kind_scope_snapshotted_by_child_task():
    """start_api_scan opens run_kind_scope('api') and create_task()s the scan,
    then returns (closing the scope) while the task keeps running.  This verifies
    the asyncio.create_task context snapshot the fix relies on: the child task
    stays tagged 'api' after the parent leaves the scope."""
    import asyncio

    from aespa.services import events as events_svc

    captured: dict[str, str] = {}

    async def _child() -> None:
        await asyncio.sleep(0)  # force a real suspension/resume
        captured["kind"] = events_svc._run_kind_for(1, {})

    async def _main() -> None:
        with events_svc.run_kind_scope("api"):
            task = asyncio.create_task(_child())
        # Scope is closed in this frame, but the task snapshotted it at creation.
        await task

    asyncio.run(_main())
    assert captured["kind"] == "api"


def test_api_agent_and_scan_log_tagged_api_despite_sast_collision():
    """End-to-end persistence regression for issue #169.  An API run whose id
    collides with a SAST run must still have its agent_log / scan_log rows written
    with run_kind='api' (driven by run_kind_scope('api')), so the API agent-log
    endpoint returns them."""
    from sqlalchemy.pool import StaticPool
    from sqlmodel import Session, SQLModel, create_engine, select

    from aespa import db as db_mod
    from aespa import models
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
        s.add(coll)
        s.commit()
        s.refresh(coll)
        api_run = models.ApiTestRun(collection_id=coll.id, name="api")
        s.add(api_run)
        s.commit()
        s.refresh(api_run)
        api_run_id = api_run.id

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
        set_engine(prev_engine)
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


# ── ALICE Collision isolation tests ──────────────────────────────────────────

def test_alice_sessions_do_not_cross_colliding_ids():
    """Verify that ALICE sessions for web and API scans with colliding IDs do not overlap."""
    from sqlalchemy.pool import StaticPool
    from sqlmodel import Session, SQLModel, create_engine, select

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
        s.add(site)
        s.commit()
        s.refresh(site)
        web_run = models.TestRun(site_id=site.id, name="web")
        s.add(web_run)
        s.commit()
        s.refresh(web_run)

        coll = models.ApiCollection(name="C", base_url="https://example.com")
        s.add(coll)
        s.commit()
        s.refresh(coll)
        api_run = models.ApiTestRun(collection_id=coll.id, name="api")
        s.add(api_run)
        s.commit()
        s.refresh(api_run)

        web_run_id, api_run_id = web_run.id, api_run.id
        assert web_run_id == api_run_id == 1

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        # PUT web scan Alice session
        web_payload = {
            "chats": [{
                "id": "tab-web",
                "title": "WEB SESSION",
                "messages": [{"id": "m1", "sender": "user", "type": "message", "text": "hello web", "ts": "12:00"}],
            }],
            "active_tab_id": "tab-web",
        }
        r_web_put = c.put(f"/api/test-runs/{web_run_id}/alice/sessions", json=web_payload)
        assert r_web_put.status_code == 200

        # PUT API scan Alice session
        api_payload = {
            "chats": [{
                "id": "tab-api",
                "title": "API SESSION",
                "messages": [{"id": "m2", "sender": "user", "type": "message", "text": "hello api", "ts": "12:01"}],
            }],
            "active_tab_id": "tab-api",
        }
        r_api_put = c.put(f"/api/api-test-runs/{api_run_id}/alice/sessions", json=api_payload)
        assert r_api_put.status_code == 200

        # GET web scan Alice session and verify it is not overwritten
        r_web_get = c.get(f"/api/test-runs/{web_run_id}/alice/sessions")
        assert r_web_get.status_code == 200
        web_chats = r_web_get.json()["chats"]
        assert len(web_chats) == 1
        assert web_chats[0]["title"] == "WEB SESSION"

        # GET API scan Alice session and verify it is isolated
        r_api_get = c.get(f"/api/api-test-runs/{api_run_id}/alice/sessions")
        assert r_api_get.status_code == 200
        api_chats = r_api_get.json()["chats"]
        assert len(api_chats) == 1
        assert api_chats[0]["title"] == "API SESSION"

        # Delete API test run and verify web sessions remain, but API sessions are deleted
        r_api_del = c.delete(f"/api/api-test-runs/{api_run_id}")
        assert r_api_del.status_code == 204

        r_web_get2 = c.get(f"/api/test-runs/{web_run_id}/alice/sessions")
        assert r_web_get2.status_code == 200
        assert len(r_web_get2.json()["chats"]) == 1

        r_api_get2 = c.get(f"/api/api-test-runs/{api_run_id}/alice/sessions")
        assert r_api_get2.status_code == 404

        # Delete Web test run and verify web sessions are deleted
        r_web_del = c.delete(f"/api/test-runs/{web_run_id}")
        assert r_web_del.status_code == 204

        # Verify both are empty now (or deleted)
        with Session(engine) as s:
            assert s.exec(select(models.AliceChatSession)).all() == []

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def test_alice_tasks_do_not_cross_colliding_ids():
    """Verify that background tasks for web and API scans with colliding IDs do not overlap in registry."""
    import asyncio

    from aespa.services import alice_tasks

    # Patch out the actual _run coroutine
    async def _fake_run(task, message, history):
        pass

    import aespa.services.alice_tasks as at_mod
    orig_run = at_mod._run
    at_mod._run = _fake_run

    try:
        web_task = asyncio.run(alice_tasks.start(
            1,
            tab_id="tab-web",
            think_msg_id="th-web",
            reply_msg_id="re-web",
            message="hello web",
            history=[],
            run_type="site",
        ))
        api_task = asyncio.run(alice_tasks.start(
            1,
            tab_id="tab-api",
            think_msg_id="th-api",
            reply_msg_id="re-api",
            message="hello api",
            history=[],
            run_type="api",
        ))

        # Check they both exist in registry concurrently without overwriting each other
        assert alice_tasks.get(1, run_type="site") is web_task
        assert alice_tasks.get(1, run_type="api") is api_task
        assert alice_tasks.status(1, run_type="site")["tab_id"] == "tab-web"
        assert alice_tasks.status(1, run_type="api")["tab_id"] == "tab-api"

        # Cancel both tasks to clean up registry
        asyncio.run(alice_tasks.stop(1, run_type="site"))
        asyncio.run(alice_tasks.stop(1, run_type="api"))
    finally:
        at_mod._run = orig_run
        alice_tasks._registry.pop(("site", 1), None)
        alice_tasks._registry.pop(("api", 1), None)
