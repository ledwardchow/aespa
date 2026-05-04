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


def test_create_run_with_scan_mode(client: TestClient):
    site = _make_site(client)
    r = _make_run(client, site["id"], scan_mode="aggressive")
    assert r.status_code == 201
    data = r.json()
    assert data["scan_mode"] == "aggressive"
    assert data["scanner_policy"]["scan_mode"] == "aggressive"


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


def test_create_run_invalid_scan_mode(client: TestClient):
    site = _make_site(client)
    r = _make_run(client, site["id"], scan_mode="reckless")
    assert r.status_code == 422


def test_run_scan_policy_snapshots_global_defaults(client: TestClient):
    policy = client.get("/api/settings/scanner-policy").json()
    policy["max_probes_per_page"] = 7
    client.put("/api/settings/scanner-policy", json=policy)

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}/scan/policy")
    assert r.status_code == 200
    assert r.json()["source"] == "run_snapshot"
    assert r.json()["max_probes_per_page"] == 7

    policy["max_probes_per_page"] = 30
    client.put("/api/settings/scanner-policy", json=policy)
    r2 = client.get(f"/api/test-runs/{run['id']}/scan/policy")
    assert r2.json()["max_probes_per_page"] == 7


def test_update_run_scan_policy(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    policy = client.get(f"/api/test-runs/{run['id']}/scan/policy").json()
    policy["scan_mode"] = "passive"
    policy["max_probes_per_page"] = 0
    r = client.patch(f"/api/test-runs/{run['id']}/scan/policy", json=policy)
    assert r.status_code == 200
    assert r.json()["scan_mode"] == "passive"
    assert r.json()["max_probes_per_page"] == 0

    run2 = client.get(f"/api/test-runs/{run['id']}").json()
    assert run2["scan_mode"] == "passive"
    assert run2["scanner_policy"]["max_probes_per_page"] == 0


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
        "validating": 0,
        "unvalidated": 0,
        "status": "stopped",
    })

    r = client.post(f"/api/test-runs/{run['id']}/validate/stop")

    assert r.status_code == 200
    assert stopped_runs == [run["id"]]
    assert r.json()["status"] == "stopped"


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
