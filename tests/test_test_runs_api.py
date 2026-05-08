"""Tests for TestRun CRUD. Does NOT exercise actual crawl (requires Playwright + network)."""
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


def _make_site(client: TestClient, **kw):
    defaults = {"name": "Target", "base_url": "https://target.local", "requires_auth": False}
    return client.post("/api/sites", json={**defaults, **kw}).json()


def _make_run(client: TestClient, site_id: int, **kw):
    defaults = {"max_depth": 2, "max_pages": 10}
    return client.post(f"/api/sites/{site_id}/test-runs", json={**defaults, **kw})


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_create_run_default_name(client: TestClient):
    site = _make_site(client)
    r = _make_run(client, site["id"])
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Run #1"
    assert data["status"] == "pending"
    assert data["pages_discovered"] == 0


def test_create_run_custom_name(client: TestClient):
    site = _make_site(client)
    r = _make_run(client, site["id"], name="Initial recon")
    assert r.status_code == 201
    assert r.json()["name"] == "Initial recon"


def test_create_run_uses_global_scan_policy(client: TestClient):
    policy = client.get("/api/settings/scanner-policy").json()
    policy["scan_mode"] = "aggressive"
    policy["max_probes_per_page"] = 7
    policy["thinking_max_steps"] = 140
    client.put("/api/settings/scanner-policy", json=policy)

    site = _make_site(client)
    r = _make_run(client, site["id"])
    assert r.status_code == 201
    data = r.json()
    assert data["scan_mode"] == "aggressive"
    assert data["scanner_policy"]["scan_mode"] == "aggressive"
    assert data["scanner_policy"]["max_probes_per_page"] == 7
    assert data["scanner_policy"]["thinking_max_steps"] == 140


def test_create_run_auto_increments(client: TestClient):
    site = _make_site(client)
    _make_run(client, site["id"])
    r2 = _make_run(client, site["id"])
    assert r2.json()["name"] == "Run #2"


def test_list_runs(client: TestClient):
    site = _make_site(client)
    _make_run(client, site["id"])
    _make_run(client, site["id"])
    r = client.get(f"/api/sites/{site['id']}/test-runs")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_runs_unknown_site(client: TestClient):
    r = client.get("/api/sites/9999/test-runs")
    assert r.status_code == 404


def test_get_run(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == run["id"]


def test_run_summary_prefers_live_scan_status(monkeypatch):
    from aespa import models as _models  # noqa: F401
    from aespa.api import test_runs as test_runs_api
    from aespa.models import Site, TestRun, TestRunStatus

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            from aespa.services import scanner as scanner_svc

            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)

            run = TestRun(
                site_id=site.id,
                name="Run #1",
                status=TestRunStatus.complete,
                error_message="scan:complete",
            )
            session.add(run)
            session.commit()
            session.refresh(run)

            monkeypatch.setattr(scanner_svc, "is_running", lambda run_id: run_id == run.id)

            summary = test_runs_api._run_summary(run, session)

        assert summary.scan_status == "running"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_run_summary_ignores_non_live_running_scan_marker(monkeypatch):
    from aespa import models as _models  # noqa: F401
    from aespa.api import test_runs as test_runs_api
    from aespa.models import Site, TestRun, TestRunStatus
    from aespa.services import scanner as scanner_svc

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)

            run = TestRun(
                site_id=site.id,
                name="Run #1",
                status=TestRunStatus.complete,
                error_message="scan:running",
            )
            session.add(run)
            session.commit()
            session.refresh(run)

            monkeypatch.setattr(scanner_svc, "is_running", lambda run_id: False)

            summary = test_runs_api._run_summary(run, session)

        assert summary.scan_status == "idle"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_get_run_not_found(client: TestClient):
    r = client.get("/api/test-runs/9999")
    assert r.status_code == 404


def test_delete_run(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.delete(f"/api/test-runs/{run['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/test-runs/{run['id']}").status_code == 404


def test_create_run_invalid_max_depth(client: TestClient):
    site = _make_site(client)
    r = _make_run(client, site["id"], max_depth=99)
    assert r.status_code == 422


def test_create_run_invalid_max_pages(client: TestClient):
    site = _make_site(client)
    r = _make_run(client, site["id"], max_pages=1)
    assert r.status_code == 422


def test_run_scan_policy_tracks_global_defaults(client: TestClient):
    policy = client.get("/api/settings/scanner-policy").json()
    policy["max_probes_per_page"] = 7
    policy["thinking_max_steps"] = 90
    client.put("/api/settings/scanner-policy", json=policy)

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    assert run["scanner_policy"]["source"] == "global_default"
    assert run["scanner_policy"]["max_probes_per_page"] == 7
    assert run["scanner_policy"]["thinking_max_steps"] == 90

    policy["max_probes_per_page"] = 30
    policy["scan_mode"] = "passive"
    client.put("/api/settings/scanner-policy", json=policy)
    run2 = client.get(f"/api/test-runs/{run['id']}").json()
    assert run2["scan_mode"] == "passive"
    assert run2["scanner_policy"]["source"] == "global_default"
    assert run2["scanner_policy"]["max_probes_per_page"] == 30


def test_run_scan_policy_endpoint_removed(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}/scan/policy")
    assert r.status_code == 404


# ── Start without LLM config ──────────────────────────────────────────────────

def test_start_run_requires_llm_config(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.post(f"/api/test-runs/{run['id']}/start")
    assert r.status_code == 400
    assert "LLM" in r.json()["detail"]


# ── Stop a non-running run ────────────────────────────────────────────────────

def test_stop_pending_run_rejected(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.post(f"/api/test-runs/{run['id']}/stop")
    assert r.status_code == 409


def test_stop_validation_endpoint_accepts_post(client: TestClient, monkeypatch):
    from aespa.api import scan as scan_api

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    stopped_runs = []

    monkeypatch.setattr(scan_api.validator_svc, "request_stop", lambda run_id: stopped_runs.append(run_id) or True)
    monkeypatch.setattr(scan_api.validator_svc, "get_validation_status", lambda run_id: {
        "total": 0,
        "confirmed": 0,
        "false_positives": 0,
        "unconfirmed": 0,
        "validating": 0,
        "unvalidated": 0,
        "status": "stopped",
    })

    r = client.post(f"/api/test-runs/{run['id']}/validate/stop")

    assert r.status_code == 200
    assert stopped_runs == [run["id"]]
    assert r.json()["status"] == "stopped"


def test_normal_scan_start_does_not_start_thinking_scan(client: TestClient, monkeypatch):
    from aespa.api import scan as scan_api

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    calls = {"normal": [], "thinking": []}

    async def fake_start_scan(run_id, page_ids=None):
        calls["normal"].append((run_id, page_ids))

    async def fake_start_thinking_scan(run_id):
        calls["thinking"].append(run_id)

    monkeypatch.setattr(scan_api.scanner_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scan_api.scanner_svc, "is_thinking_running", lambda run_id: False)
    monkeypatch.setattr(scan_api.scanner_svc, "start_scan", fake_start_scan)
    monkeypatch.setattr(scan_api.scanner_svc, "start_thinking_scan", fake_start_thinking_scan)
    monkeypatch.setattr(scan_api.scanner_svc, "get_scan_status", lambda run_id: {
        "total_pages": 0,
        "pages_done": 0,
        "findings_count": 0,
        "status": "running",
    })

    r = client.post(f"/api/test-runs/{run['id']}/scan/start")

    assert r.status_code == 200
    assert calls["normal"] == [(run["id"], None)]
    assert calls["thinking"] == []
    assert r.json()["status"] == "running"


def test_thinking_scan_start_does_not_start_normal_scan(client: TestClient, monkeypatch):
    from aespa.api import scan as scan_api

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    calls = {"normal": [], "thinking": []}

    async def fake_start_scan(run_id, page_ids=None):
        calls["normal"].append((run_id, page_ids))

    async def fake_start_thinking_scan(run_id):
        calls["thinking"].append(run_id)

    monkeypatch.setattr(scan_api.scanner_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scan_api.scanner_svc, "is_thinking_running", lambda run_id: False)
    monkeypatch.setattr(scan_api.scanner_svc, "start_scan", fake_start_scan)
    monkeypatch.setattr(scan_api.scanner_svc, "start_thinking_scan", fake_start_thinking_scan)
    monkeypatch.setattr(scan_api.scanner_svc, "get_thinking_scan_status", lambda run_id: {
        "status": "running",
    })

    r = client.post(f"/api/test-runs/{run['id']}/thinking-scan/start")

    assert r.status_code == 200
    assert calls["normal"] == []
    assert calls["thinking"] == [run["id"]]
    assert r.json()["status"] == "running"


def test_scan_modes_block_each_other(client: TestClient, monkeypatch):
    from aespa.api import scan as scan_api

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()

    monkeypatch.setattr(scan_api.scanner_svc, "is_running", lambda run_id: True)
    monkeypatch.setattr(scan_api.scanner_svc, "is_thinking_running", lambda run_id: False)
    r = client.post(f"/api/test-runs/{run['id']}/thinking-scan/start")
    assert r.status_code == 409
    assert r.json()["detail"] == "Scan already running"

    monkeypatch.setattr(scan_api.scanner_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scan_api.scanner_svc, "is_thinking_running", lambda run_id: True)
    r = client.post(f"/api/test-runs/{run['id']}/scan/start")
    assert r.status_code == 409
    assert r.json()["detail"] == "Dynamic Scan already running"


# ── Graph / pages on empty run ────────────────────────────────────────────────

def test_get_graph_empty(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}/graph")
    assert r.status_code == 200
    data = r.json()
    assert data["nodes"] == []
    assert data["links"] == []


def test_list_pages_empty(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}/pages")
    assert r.status_code == 200
    assert r.json() == []


# ── Cascaded delete when site is deleted ──────────────────────────────────────

def test_deleting_site_cleans_up_runs(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    client.delete(f"/api/sites/{site['id']}")
    r = client.get(f"/api/test-runs/{run['id']}")
    assert r.status_code == 404
