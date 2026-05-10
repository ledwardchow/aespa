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


def test_list_active_jobs_includes_running_structured_scan(client: TestClient, monkeypatch):
    from aespa.services import scanner as scanner_svc

    site = _make_site(client)
    run = _make_run(client, site["id"], name="Live scan").json()

    monkeypatch.setattr(scanner_svc, "is_running", lambda run_id: run_id == run["id"])
    monkeypatch.setattr(scanner_svc, "is_thinking_running", lambda run_id: False)
    monkeypatch.setattr(scanner_svc, "get_scan_status", lambda run_id: {
        "total_pages": 4,
        "pages_done": 2,
        "findings_count": 3,
        "status": "running",
    })

    r = client.get("/api/test-runs/active")

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["run_id"] == run["id"]
    assert data[0]["site_name"] == site["name"]
    assert data[0]["run_name"] == "Live scan"
    assert data[0]["job_type"] == "Structured Scan"
    assert data[0]["status"] == "running"
    assert data[0]["pages_done"] == 2
    assert data[0]["total_pages"] == 4
    assert data[0]["findings_count"] == 3


def test_list_active_jobs_includes_running_dynamic_scan(client: TestClient, monkeypatch):
    from aespa.services import scanner as scanner_svc

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()

    monkeypatch.setattr(scanner_svc, "is_running", lambda run_id: False)
    monkeypatch.setattr(scanner_svc, "is_thinking_running", lambda run_id: run_id == run["id"])
    monkeypatch.setattr(scanner_svc, "get_thinking_scan_status", lambda run_id: {
        "status": "analysing",
        "findings_count": 1,
    })

    r = client.get("/api/test-runs/active")

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["job_type"] == "Dynamic Scan"
    assert data[0]["status"] == "analysing"
    assert data[0]["findings_count"] == 1


def test_get_run(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == run["id"]


def test_import_findings_creates_findings_and_pages(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    payload = [{
        "owasp_category": "A01",
        "severity": "high",
        "title": "Imported authorization bypass",
        "description": "A protected resource is accessible.",
        "impact": "Unauthorized data access.",
        "likelihood": "Likely",
        "recommendation": "Enforce authorization checks.",
        "cvss_score": 8.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N",
        "affected_url": "https://target.local/admin",
        "evidence": "GET /admin returned 200",
        "request_evidence": "GET /admin",
        "response_evidence": "Status: 200",
        "validation_status": "confirmed",
        "validation_note": "Imported validated issue.",
    }]

    r = client.post(f"/api/test-runs/{run['id']}/findings/import", json=payload)

    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 1
    finding = data["findings"][0]
    assert finding["title"] == "Imported authorization bypass"
    assert finding["validation_status"] == "confirmed"
    assert finding["affected_url"] == "https://target.local/admin"
    run_after = client.get(f"/api/test-runs/{run['id']}").json()
    assert run_after["pages_discovered"] == 1


def test_deduplicate_findings_removes_substantially_same_targets(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    other_run = _make_run(client, site["id"]).json()

    duplicate_payload = [
        {
            "owasp_category": "A01",
            "severity": "high",
            "title": "Broken object level authorization exposes account records",
            "description": (
                "The account details endpoint returns private account data "
                "for object reference 123."
            ),
            "impact": "An attacker can read another user's account data.",
            "recommendation": "Enforce object-level authorization checks.",
            "affected_url": "https://target.local/api/accounts/123",
        },
        {
            "owasp_category": "A01",
            "severity": "medium",
            "title": "Broken object-level authorization exposes account records",
            "description": (
                "The account details endpoint returns private account data "
                "for object reference 456."
            ),
            "impact": "An attacker can read another user's account data.",
            "recommendation": "Enforce object-level authorization checks.",
            "affected_url": "https://target.local/api/accounts/456",
            "validation_status": "confirmed",
        },
        {
            "owasp_category": "A01",
            "severity": "high",
            "title": "Broken object level authorization exposes order records",
            "description": (
                "The order details endpoint returns private order data "
                "for object reference 123."
            ),
            "impact": "An attacker can read another user's order data.",
            "recommendation": "Enforce object-level authorization checks.",
            "affected_url": "https://target.local/api/orders/123",
        },
    ]

    imported = client.post(
        f"/api/test-runs/{run['id']}/findings/import",
        json=duplicate_payload,
    ).json()["findings"]
    other_imported = client.post(
        f"/api/test-runs/{other_run['id']}/findings/import",
        json=[duplicate_payload[0]],
    ).json()["findings"][0]

    r = client.post(f"/api/test-runs/{run['id']}/findings/deduplicate")

    assert r.status_code == 200
    data = r.json()
    assert data["total_before"] == 3
    assert data["total_after"] == 2
    assert data["removed"] == 1
    assert data["groups"][0]["kept_id"] == imported[1]["id"]
    assert data["groups"][0]["removed_ids"] == [imported[0]["id"]]

    findings = client.get(f"/api/test-runs/{run['id']}/findings").json()
    assert {f["id"] for f in findings} == {imported[1]["id"], imported[2]["id"]}
    other_findings = client.get(f"/api/test-runs/{other_run['id']}/findings").json()
    assert other_findings[0]["id"] == other_imported["id"]


def test_deduplicate_findings_unknown_run(client: TestClient):
    r = client.post("/api/test-runs/9999/findings/deduplicate")
    assert r.status_code == 404


def test_deduplicate_findings_uses_llm_for_semantic_matches(
    client: TestClient,
    monkeypatch,
):
    from aespa.api import scan as scan_api

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    payload = [
        {
            "owasp_category": "A01",
            "severity": "high",
            "title": "Invoice export exposes arbitrary tenant documents",
            "description": (
                "The export workflow returns files for invoice 111 when "
                "requested by another tenant."
            ),
            "impact": "Confidential documents can be disclosed.",
            "recommendation": "Scope export access to tenant ownership.",
            "affected_url": "https://target.local/api/invoices/111/export",
        },
        {
            "owasp_category": "A01",
            "severity": "high",
            "title": "Missing authorization check in download workflow",
            "description": (
                "A user can fetch document 222 from the download route despite "
                "not owning it."
            ),
            "impact": "Sensitive files from another organization can be retrieved.",
            "recommendation": "Verify ownership before serving files.",
            "affected_url": "https://target.local/api/invoices/222/export",
        },
    ]
    imported = client.post(
        f"/api/test-runs/{run['id']}/findings/import",
        json=payload,
    ).json()["findings"]
    calls = []

    async def fake_llm_dedupe(config, *, target, findings):  # noqa: ARG001
        calls.append({"target": target, "findings": findings})
        return [[imported[0]["id"], imported[1]["id"]]]

    monkeypatch.setattr(scan_api, "get_llm_config_for_run", lambda session, run: object())
    monkeypatch.setattr(
        scan_api.findings_svc.llm_svc,
        "deduplicate_finding_groups",
        fake_llm_dedupe,
    )

    r = client.post(f"/api/test-runs/{run['id']}/findings/deduplicate")

    assert r.status_code == 200
    data = r.json()
    assert data["llm_used"] is True
    assert data["removed"] == 1
    assert calls
    assert len(client.get(f"/api/test-runs/{run['id']}/findings").json()) == 1


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
