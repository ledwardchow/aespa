"""Tests for TestRun CRUD. Does NOT exercise actual crawl (requires Playwright + network)."""

import json

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import get_session
from aespa.models import ScannerSession, TargetIntelItem


def _make_site(client: TestClient, **kw):
    defaults = {
        "name": "Target",
        "base_url": "https://target.local",
        "requires_auth": False,
    }
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


def test_create_run_defaults_to_500_pages(client: TestClient):
    site = _make_site(client)
    response = client.post(f"/api/sites/{site['id']}/test-runs", json={})
    assert response.status_code == 201
    assert response.json()["max_pages"] == 500


def test_create_run_custom_name(client: TestClient):
    site = _make_site(client)
    r = _make_run(client, site["id"], name="Initial recon")
    assert r.status_code == 201
    assert r.json()["name"] == "Initial recon"


def test_create_run_can_enable_interactive_spa_crawler(client: TestClient):
    site = _make_site(client)
    created = _make_run(client, site["id"], crawler_mode="interactive")
    assert created.status_code == 201
    assert created.json()["crawler_mode"] == "interactive"

    updated = client.patch(
        f"/api/test-runs/{created.json()['id']}",
        json={
            "max_depth": 2,
            "max_pages": 10,
            "crawler_mode": "url",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["crawler_mode"] == "url"


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


def test_list_active_jobs_includes_running_dynamic_scan(
    client: TestClient, monkeypatch
):
    from aespa.services import scanner as scanner_svc

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()

    monkeypatch.setattr(
        scanner_svc, "is_thinking_running", lambda run_id: run_id == run["id"]
    )
    monkeypatch.setattr(
        scanner_svc,
        "get_thinking_scan_status",
        lambda run_id: {
            "status": "analysing",
            "findings_count": 1,
        },
    )

    r = client.get("/api/test-runs/active")

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["job_type"] == "Dynamic Scan"
    assert data[0]["status"] == "analysing"
    assert data[0]["findings_count"] == 1


def test_list_active_jobs_includes_one_validation_job_per_run(
    client: TestClient, monkeypatch
):
    from aespa.services import validator as validator_svc

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    monkeypatch.setattr(
        validator_svc, "is_validating", lambda run_id: run_id == run["id"]
    )
    monkeypatch.setattr(
        validator_svc,
        "get_validation_status",
        lambda run_id: {
            "total": 8,
            "validating": 3,
            "unvalidated": 1,
        },
    )

    response = client.get("/api/test-runs/active")

    assert response.status_code == 200
    validation_jobs = [
        job for job in response.json() if job["job_type"] == "Validation"
    ]
    assert len(validation_jobs) == 1
    assert validation_jobs[0]["run_id"] == run["id"]
    assert validation_jobs[0]["pages_done"] == 4
    assert validation_jobs[0]["total_pages"] == 8


def test_get_run(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == run["id"]


def test_get_target_intelligence_returns_counts_and_items(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()

    override = client.app.dependency_overrides[get_session]
    gen = override()
    session = next(gen)
    try:
        session.add(
            TargetIntelItem(
                test_run_id=run["id"],
                kind="endpoint",
                key="/api/accounts",
                value="https://target.local/api/accounts",
                url="https://target.local/dashboard",
                method="GET",
                source="dom_link",
                confidence=0.8,
                evidence="Accounts",
                item_metadata='{"page_url":"https://target.local/dashboard"}',
            )
        )
        session.add(
            TargetIntelItem(
                test_run_id=run["id"],
                kind="input",
                key="account_id",
                value="request_body",
                url="https://target.local/api/transfers",
                method="POST",
                source="api_request",
            )
        )
        session.commit()
    finally:
        session.close()
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.get(f"/api/test-runs/{run['id']}/target-intelligence")

    assert r.status_code == 200
    data = r.json()
    assert data["counts"] == {"endpoint": 1, "input": 1}
    assert {item["kind"] for item in data["items"]} == {"endpoint", "input"}
    endpoint = next(item for item in data["items"] if item["kind"] == "endpoint")
    assert endpoint["item_metadata"]["page_url"] == "https://target.local/dashboard"


def test_import_findings_creates_findings_and_pages(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    payload = [
        {
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
            "evidence_items": [
                {"type": "status", "label": "HTTP status", "value": "200"}
            ],
            "finding_source": "manual_import",
            "validation_status": "confirmed",
            "validation_note": "Imported validated issue.",
        }
    ]

    r = client.post(f"/api/test-runs/{run['id']}/findings/import", json=payload)

    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 1
    finding = data["findings"][0]
    assert finding["title"] == "Imported authorization bypass"
    assert finding["validation_status"] == "confirmed"
    assert finding["finding_source"] == "manual_import"
    assert finding["affected_url"] == "https://target.local/admin"
    assert finding["evidence_items"][0]["type"] == "status"
    run_after = client.get(f"/api/test-runs/{run['id']}").json()
    assert run_after["pages_discovered"] == 1


def _import_one_finding(client: TestClient, run_id: int) -> dict:
    payload = [
        {
            "owasp_category": "A01",
            "severity": "high",
            "title": "Imported authorization bypass",
            "description": "A protected resource is accessible.",
            "affected_url": "https://target.local/admin",
            "validation_status": "confirmed",
        }
    ]
    r = client.post(f"/api/test-runs/{run_id}/findings/import", json=payload)
    assert r.status_code == 200
    return r.json()["findings"][0]


def test_update_finding_edits_status_severity_and_text(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    finding = _import_one_finding(client, run["id"])

    r = client.patch(
        f"/api/test-runs/{run['id']}/findings/{finding['id']}",
        json={
            "validation_status": "unconfirmed",
            "severity": "medium",
            "title": "Edited title",
            "description": "Edited description.",
            "cvss_score": 5.4,
        },
    )

    assert r.status_code == 200
    data = r.json()
    assert data["validation_status"] == "unconfirmed"
    assert data["severity"] == "medium"
    assert data["title"] == "Edited title"
    assert data["description"] == "Edited description."
    assert data["cvss_score"] == 5.4
    # affected_url was not supplied — must be left untouched.
    assert data["affected_url"] == "https://target.local/admin"


def test_update_finding_ignores_invalid_values_and_guards_title(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    finding = _import_one_finding(client, run["id"])

    r = client.patch(
        f"/api/test-runs/{run['id']}/findings/{finding['id']}",
        json={"severity": "bogus", "validation_status": "validating", "title": "   "},
    )

    assert r.status_code == 200
    data = r.json()
    # Invalid severity/status are ignored; blank title is not applied.
    assert data["severity"] == "high"
    assert data["validation_status"] == "confirmed"
    assert data["title"] == "Imported authorization bypass"


def test_update_finding_unknown_id_404(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.patch(
        f"/api/test-runs/{run['id']}/findings/999999",
        json={"severity": "low"},
    )
    assert r.status_code == 404


def test_get_scanner_sessions_redacts_auth_material():
    from aespa.api import test_runs as test_runs_api
    from aespa.models import Site, TestRun

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

            run = TestRun(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)

            session.add(
                ScannerSession(
                    test_run_id=run.id,
                    label="configured_primary",
                    kind="mixed",
                    account_label="Primary administrator",
                    username="alice",
                    credential_id=3,
                    source="test",
                    cookies_json='{"sid":"secret-cookie"}',
                    extra_headers_json='{"Authorization":"Bearer secret-token"}',
                    session_metadata='{"login_url":"https://target.local/login","password":"generated-secret"}',
                    token_hint="secret...token",
                )
            )
            session.commit()

            summary = test_runs_api.get_scanner_sessions(run.id, session=session)

        assert summary.counts["total"] == 1
        item = summary.sessions[0]
        assert item.label == "configured_primary"
        assert item.account_label == "Primary administrator"
        assert item.username == "alice"
        assert item.cookie_names == ["sid"]
        assert item.header_names == ["Authorization"]
        assert item.session_metadata["login_url"] == "https://target.local/login"
        assert item.session_metadata["password"] == "[REDACTED]"
        assert "secret-cookie" not in item.model_dump_json()
        assert "secret-token" not in item.model_dump_json()
        assert "generated-secret" not in item.model_dump_json()
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_update_scanner_session_renames_and_deactivates():
    from aespa.api import test_runs as test_runs_api
    from aespa.models import Site, TestRun
    from aespa.schemas import ScannerSessionUpdate

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

            run = TestRun(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)

            record = ScannerSession(
                test_run_id=run.id,
                label="discovered_token",
                kind="bearer",
                source="test",
                extra_headers_json='{"Authorization":"Bearer secret-token"}',
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            updated = test_runs_api.update_scanner_session(
                run.id,
                record.id,
                ScannerSessionUpdate(label="Forged Admin", is_active=False),
                session=session,
            )

            summary = test_runs_api.get_scanner_sessions(
                run.id, include_inactive=True, session=session
            )

        assert updated.label == "forged_admin"
        assert updated.is_active is False
        assert summary.counts["inactive"] == 1
        assert summary.sessions[0].label == "forged_admin"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_validate_scanner_sessions_route(client: TestClient, monkeypatch):
    from aespa.services import scanner_sessions

    site = _make_site(client, base_url="https://target.local")
    run = _make_run(client, site["id"]).json()
    captured = {}

    async def validate(db, run_id, **kwargs):
        captured.update(run_id=run_id, **kwargs)
        return {
            "checked": 2,
            "valid": 1,
            "evicted": 1,
            "errors": 0,
            "skipped": 0,
            "results": [],
        }

    monkeypatch.setattr(scanner_sessions, "validate_active_sessions", validate)
    response = client.post(
        f"/api/test-runs/{run['id']}/scanner-sessions/validate"
    )

    assert response.status_code == 200
    assert response.json()["evicted"] == 1
    assert captured["run_id"] == run["id"]
    assert captured["run_kind"] == "web"
    assert captured["default_url"].rstrip("/") == "https://target.local"


def test_get_run_not_found(client: TestClient):
    r = client.get("/api/test-runs/9999")
    assert r.status_code == 404


def test_task_graph_routes_are_removed(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()

    assert client.get(f"/api/test-runs/{run['id']}/task-graph").status_code == 404
    assert client.post(f"/api/test-runs/{run['id']}/task-graph/seed").status_code in {
        404,
        405,
    }


def test_delete_run(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.delete(f"/api/test-runs/{run['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/test-runs/{run['id']}").status_code == 404


def test_delete_run_cleans_legacy_task_rows(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()

    override = client.app.dependency_overrides[get_session]
    gen = override()
    session = next(gen)
    try:
        session.exec(
            text("""
            CREATE TABLE pentest_hypothesis (
                id INTEGER PRIMARY KEY,
                test_run_id INTEGER NOT NULL
            )
        """)
        )
        session.exec(
            text("""
            CREATE TABLE pentest_task (
                id INTEGER PRIMARY KEY,
                test_run_id INTEGER NOT NULL,
                hypothesis_id INTEGER
            )
        """)
        )
        session.exec(
            text(
                "INSERT INTO pentest_hypothesis (id, test_run_id) VALUES (1, :run_id)"
            ).bindparams(run_id=run["id"])
        )
        session.exec(
            text(
                "INSERT INTO pentest_task (id, test_run_id, hypothesis_id) "
                "VALUES (1, :run_id, 1)"
            ).bindparams(run_id=run["id"])
        )
        session.commit()
    finally:
        session.close()
        try:
            next(gen)
        except StopIteration:
            pass

    assert client.delete(f"/api/test-runs/{run['id']}").status_code == 204

    gen = override()
    session = next(gen)
    try:
        assert session.exec(text("SELECT count(*) FROM pentest_task")).one()[0] == 0
        assert (
            session.exec(text("SELECT count(*) FROM pentest_hypothesis")).one()[0] == 0
        )
    finally:
        session.close()
        try:
            next(gen)
        except StopIteration:
            pass


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

    monkeypatch.setattr(
        scan_api.validator_svc,
        "request_stop",
        lambda run_id: stopped_runs.append(run_id) or True,
    )
    monkeypatch.setattr(
        scan_api.validator_svc,
        "get_validation_status",
        lambda run_id: {
            "total": 0,
            "confirmed": 0,
            "false_positives": 0,
            "unconfirmed": 0,
            "validating": 0,
            "unvalidated": 0,
            "status": "stopped",
        },
    )

    r = client.post(f"/api/test-runs/{run['id']}/validate/stop")

    assert r.status_code == 200
    assert stopped_runs == [run["id"]]
    assert r.json()["status"] == "stopped"


def test_thinking_scan_start_blocked_when_already_running(
    client: TestClient, monkeypatch
):
    from aespa.api import scan as scan_api

    site = _make_site(client)
    run = _make_run(client, site["id"]).json()

    monkeypatch.setattr(
        scan_api.scanner_svc, "is_thinking_running", lambda run_id: True
    )
    r = client.post(f"/api/test-runs/{run['id']}/thinking-scan/start")
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


def test_get_graph_reports_unauthenticated_access():
    from aespa.api import test_runs as test_runs_api
    from aespa.models import CrawledPage, PageCredentialView, Site, TestRun

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
            run = TestRun(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)
            public_page = CrawledPage(
                test_run_id=run.id,
                url="https://target.local/public",
                accessible_by="[10, 20]",
            )
            private_page = CrawledPage(
                test_run_id=run.id,
                url="https://target.local/private",
                accessible_by="[10, 20]",
            )
            session.add(public_page)
            session.add(private_page)
            session.commit()
            session.refresh(public_page)
            session.add(
                PageCredentialView(
                    test_run_id=run.id,
                    page_id=public_page.id,
                    credential_id=None,
                    username="unauthenticated",
                )
            )
            session.commit()

            graph = test_runs_api.get_graph(run.id, session=session)

        nodes_by_url = {node.url: node for node in graph.nodes}
        assert (
            nodes_by_url["https://target.local/public"].accessible_anonymously is True
        )
        assert (
            nodes_by_url["https://target.local/private"].accessible_anonymously is False
        )
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_list_pages_empty(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    r = client.get(f"/api/test-runs/{run['id']}/pages")
    assert r.status_code == 200
    assert r.json() == []


def test_export_and_import_crawl_into_new_run(client: TestClient):
    site = _make_site(client)
    source = _make_run(client, site["id"]).json()
    target = _make_run(client, site["id"]).json()
    # The finding-import endpoint creates a realistic crawled page without
    # requiring a Playwright crawl in this service-level test.
    created = client.post(
        f"/api/test-runs/{source['id']}/findings/import",
        json=[
            {
                "title": "Imported page seed",
                "affected_url": "https://target.local/account",
            }
        ],
    )
    assert created.status_code == 200

    exported = client.get(f"/api/test-runs/{source['id']}/crawl/export")
    assert exported.status_code == 200
    archive = exported.json()
    assert archive["format"] == "aespa-crawl-export"
    assert archive["crawl"]["pages"][0]["url"] == "https://target.local/account"
    # Simulate the category information emitted by a normal crawl.  Import must
    # restore both the sitemap's per-page flags and the coverage-matrix cells.
    archive["crawl"]["pages"][0]["owasp_applicable_json"] = (
        '{"A01": true, "A02": false}'
    )
    archive["crawl"]["pages"][0]["has_object_ref"] = True
    archive["crawl"]["owasp_categories"] = [
        {
            "page_url": "https://target.local/account",
            "category": "A01",
        }
    ]
    archive["crawl"]["traffic"] = [
        {
            "source": "playwright",
            "method": "GET",
            "url": "https://target.local/account",
            "request_headers": '{"Authorization": "Bearer retained"}',
            "request_body": None,
            "status": 200,
            "response_headers": '{"Set-Cookie": "session=retained"}',
            "response_body": "account page",
            "duration_ms": 12,
            "username": "alice",
        }
    ]
    archive["crawl"]["scanner_sessions"] = [
        {
            "label": "configured_primary",
            "kind": "mixed",
            "username": "alice",
            "credential_username": "alice",
            "source": "crawler",
            "cookies_json": '{"session": "retained"}',
            "extra_headers_json": '{"Authorization": "Bearer retained"}',
            "session_metadata": '{"origin": "crawl"}',
            "token_hint": "retained",
            "is_active": True,
        }
    ]

    imported = client.post(
        f"/api/test-runs/{target['id']}/crawl/import",
        files={"file": ("crawl.json", json.dumps(archive), "application/json")},
    )
    assert imported.status_code == 200
    assert imported.json()["status"] == "complete"
    assert imported.json()["pages_discovered"] == 1
    pages = client.get(f"/api/test-runs/{target['id']}/pages")
    assert [page["url"] for page in pages.json()] == ["https://target.local/account"]
    detail = client.get(f"/api/test-runs/{target['id']}/pages/{pages.json()[0]['id']}")
    assert detail.json()["owasp_applicable"] == {"A01": True, "A02": False}
    sessions = client.get(f"/api/test-runs/{target['id']}/scanner-sessions").json()
    assert sessions["counts"] == {"total": 1, "mixed": 1, "active": 1}
    assert sessions["sessions"][0]["cookie_names"] == ["session"]
    assert sessions["sessions"][0]["header_names"] == ["Authorization"]
    # An imported run has populated crawl timestamps; it must be exportable too.
    assert client.get(f"/api/test-runs/{target['id']}/crawl/export").status_code == 200
    recon = client.get(f"/api/test-runs/{target['id']}/recon-summary")
    assert recon.status_code == 200
    assert recon.json()["schema_version"] == 2
    assert recon.json()["routes"][0]["canonical_url"] == "https://target.local/account"
    assert recon.json()["routes"][0]["access"]["classification"] == "unknown"
    assert {item["type"] for item in recon.json()["signals"]["items"]} == {
        "object_reference"
    }


def test_import_crawl_rejects_another_site(client: TestClient):
    source_site = _make_site(client)
    source = _make_run(client, source_site["id"]).json()
    client.post(
        f"/api/test-runs/{source['id']}/findings/import",
        json=[
            {
                "title": "Imported page seed",
                "affected_url": "https://target.local/account",
            }
        ],
    )
    archive = client.get(f"/api/test-runs/{source['id']}/crawl/export")
    other_site = _make_site(client, name="Other", base_url="https://other.local")
    target = _make_run(client, other_site["id"]).json()

    imported = client.post(
        f"/api/test-runs/{target['id']}/crawl/import",
        files={"file": ("crawl.json", archive.content, "application/json")},
    )
    assert imported.status_code == 400
    assert "different site" in imported.json()["detail"]


def test_clear_crawl_resets_run_without_restarting(monkeypatch):
    from aespa import models as _models  # noqa: F401
    from aespa.main import create_app
    from aespa.models import (
        CrawledPage,
        PageCredentialView,
        PageLink,
        ScanFinding,
        Site,
        TestRun,
        TestRunStatus,
    )
    from aespa.services import crawler as crawler_svc

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    started: list[int] = []

    async def fake_start_crawl(run_id: int) -> None:
        started.append(run_id)

    monkeypatch.setattr(crawler_svc, "start_crawl", fake_start_crawl)

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

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
                pages_discovered=1,
                current_url="https://target.local/account",
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            page = CrawledPage(test_run_id=run.id, url="https://target.local/account")
            session.add(page)
            session.commit()
            session.refresh(page)
            session.add(
                PageLink(
                    test_run_id=run.id,
                    source_page_id=page.id,
                    target_url="https://target.local/next",
                )
            )
            session.add(
                PageCredentialView(
                    test_run_id=run.id, page_id=page.id, username="alice"
                )
            )
            session.add(
                TargetIntelItem(test_run_id=run.id, kind="endpoint", key="/account")
            )
            finding = ScanFinding(
                test_run_id=run.id,
                page_id=page.id,
                owasp_category="A01",
                severity="medium",
                title="Finding",
                description="Desc",
            )
            session.add(finding)
            session.commit()
            run_id = run.id
            finding_id = finding.id

        with TestClient(app, raise_server_exceptions=True) as api_client:
            response = api_client.post(f"/api/test-runs/{run_id}/crawl/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["pages_discovered"] == 0
        assert data["current_url"] is None
        assert started == []

        with Session(engine) as session:
            assert (
                session.exec(
                    select(CrawledPage).where(CrawledPage.test_run_id == run_id)
                ).all()
                == []
            )
            assert (
                session.exec(
                    select(PageLink).where(PageLink.test_run_id == run_id)
                ).all()
                == []
            )
            assert (
                session.exec(
                    select(PageCredentialView).where(
                        PageCredentialView.test_run_id == run_id
                    )
                ).all()
                == []
            )
            assert (
                session.exec(
                    select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)
                ).all()
                == []
            )
            finding_after = session.get(ScanFinding, finding_id)
            assert finding_after is not None
            assert finding_after.page_id is None
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


# ── Cascaded delete when site is deleted ──────────────────────────────────────


def test_deleting_site_cleans_up_runs(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"]).json()
    client.delete(f"/api/sites/{site['id']}")
    r = client.get(f"/api/test-runs/{run['id']}")
    assert r.status_code == 404
