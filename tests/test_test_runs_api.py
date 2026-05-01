"""Tests for TestRun CRUD. Does NOT exercise actual crawl (requires Playwright + network)."""
from fastapi.testclient import TestClient


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
