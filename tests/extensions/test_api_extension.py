from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import threading
import traceback
import zipfile
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import event
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import SastRun, ScanFinding, ScanLead, Site, TestRun
from aespa.services import events, run_lifecycle, run_progress
from extensions.builtin.api import callbacks as api_callbacks
from extensions.builtin.api.models import ApiDelivery, ApiScan, now

EXTENSION = "aespa.api"
BASE = f"/extension/{EXTENSION}"
SNAPSHOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "aespa_api_v1_openapi.json"
)


@pytest.fixture
def api(client, monkeypatch, tmp_path, data_dir):
    """Enable the API extension with its callback thread held back."""
    from aespa.extensions import get_extension_manager

    manager = get_extension_manager()
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(
            extensions_dir=tmp_path / "user-extensions",
            data_dir=tmp_path / "data",
        ),
    )
    manager.load_extensions()
    with monkeypatch.context() as patch:
        patch.setattr(threading.Thread, "start", lambda self: None)
        manager.set_enabled(EXTENSION, True)
    assert manager.extensions[EXTENSION].status == "loaded", manager.extensions[
        EXTENSION
    ].error

    started = {"crawl": [], "scheduled": [], "sast": []}

    async def fake_start_crawl(run_id):
        started["crawl"].append(run_id)
        return object()

    async def fake_start_sast(run_id, *, resume=False):
        started["sast"].append(run_id)

    from aespa.services import crawl_then_pentest, crawler, sast_scanner

    monkeypatch.setattr(
        "aespa.services.web_runs_service.get_llm_config_for_run", lambda *_: object()
    )
    monkeypatch.setattr(crawler, "start_crawl", fake_start_crawl)
    monkeypatch.setattr(
        crawl_then_pentest,
        "schedule",
        lambda run_id, task: started["scheduled"].append(run_id),
    )
    monkeypatch.setattr(sast_scanner, "start_sast_scan", fake_start_sast)
    yield SimpleNamespace(
        client=client,
        manager=manager,
        store=manager.data_stores[EXTENSION],
        core=manager.core_access_for(EXTENSION),
        started=started,
    )
    manager.set_enabled(EXTENSION, False)


def _token(api, scopes=("sast", "web", "sites"), **extra) -> str:
    response = api.client.post(
        f"{BASE}/admin/tokens",
        json={"name": "CI", "scopes": list(scopes), **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("app.py", "print('hello')\n")
    return buffer.getvalue()


def _site(name="Shop", **extra) -> dict:
    return {
        "name": name,
        "base_url": "https://shop.example.test",
        "requires_auth": True,
        "login_url": "https://shop.example.test/login",
        "scope_hosts": ["api.shop.example.test"],
        "scan_guidance": "Avoid the checkout payment step.",
        "workflow_data": [
            {
                "name": "Order",
                "goal": "Place an order",
                "start_url": "https://shop.example.test/cart",
                "instructions": "Add an item and check out.",
            }
        ],
        "credentials": [
            {"label": "Admin", "username": "admin", "password": "s3cret-pass"},
            {
                "label": "Custom form",
                "auth_mode": "totp",
                "totp_seed": "JBSWY3DPEHPK3PXP",
                "login_fields": [
                    {"key": "account", "label": "Account", "value": "acme"},
                    {
                        "key": "pin",
                        "label": "PIN",
                        "value": "9911",
                        "sensitive": True,
                    },
                ],
            },
        ],
        **extra,
    }


def _upload(api, token, **form):
    return api.client.post(
        f"{BASE}/v1/sast/scans",
        headers=_auth(token) | form.pop("headers", {}),
        files={"file": ("src.zip", _zip(), "application/zip")},
        data=form,
    )


# ── OpenAPI definition ───────────────────────────────────────────────────────


def _refs(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref":
                yield value
            else:
                yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)


def _flat_routes(routes):
    for route in routes:
        original = getattr(route, "original_router", None)
        yield from _flat_routes(original.routes) if original else [route]


def test_openapi_definition_is_published_and_complete(api):
    listed = next(
        item
        for item in api.client.get("/api/extensions").json()
        if item["id"] == EXTENSION
    )
    assert listed["openapi_url"] == f"/api/extensions/{EXTENSION}/openapi.json"
    document = api.client.get(listed["openapi_url"]).json()
    assert document["openapi"] == "3.1.0"
    assert document["servers"] == [{"url": BASE}]
    assert api.client.get(f"{BASE}/v1/openapi.json").json() == document

    schemas = document["components"]["schemas"]
    for ref in set(_refs(document)):
        assert ref.removeprefix("#/components/schemas/") in schemas, ref

    served = {
        (method.upper(), route.path)
        for route in _flat_routes(api.manager.api_app_for(EXTENSION).routes)
        if getattr(route, "include_in_schema", False)
        for method in route.methods
    }
    documented = {
        (method.upper(), path)
        for path, operations in document["paths"].items()
        for method in operations
    }
    assert served == documented
    assert not any(path.startswith("/admin") for path in document["paths"])

    operation_ids = []
    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            operation_ids.append(operation["operationId"])
            assert operation.get("tags"), (method, path)
            assert operation.get("summary"), (method, path)
            assert operation["security"] == [{"bearerAuth": []}]
            assert "401" in operation["responses"]
    assert len(operation_ids) == len(set(operation_ids))

    credential = schemas["CredentialCreate"]["properties"]
    assert credential["password"]["writeOnly"] is True
    assert credential["totp_seed"]["writeOnly"] is True
    assert schemas["LoginFieldIn"]["properties"]["value"]["writeOnly"] is True
    assert set(document["webhooks"]) == {
        "scan.started",
        "scan.phase_changed",
        "scan.progress",
        "scan.needs_action",
        "scan.paused",
        "scan.completed",
        "scan.failed",
        "scan.stopped",
    }
    headers = {
        item["name"]
        for item in document["webhooks"]["scan.completed"]["post"]["parameters"]
    }
    assert {"x-aespa-signature", "x-aespa-delivery", "x-aespa-event"} <= headers


def test_openapi_v1_matches_saved_copy(api):
    """Fails on any change to API v1. Update the saved copy deliberately.

    Run with AESPA_UPDATE_API_SNAPSHOT=1 to rewrite the copy after checking
    that the change does not break existing clients.
    """
    document = api.client.get(f"/api/extensions/{EXTENSION}/openapi.json").json()
    if os.environ.get("AESPA_UPDATE_API_SNAPSHOT") == "1":
        SNAPSHOT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    assert document == json.loads(SNAPSHOT.read_text())


def test_openapi_is_not_published_while_disabled(api):
    api.manager.set_enabled(EXTENSION, False)
    assert (
        api.client.get(f"/api/extensions/{EXTENSION}/openapi.json").status_code == 404
    )
    assert api.client.get(f"{BASE}/v1/openapi.json").status_code == 404
    other = api.client.get("/api/extensions/aespa.githubrepository/openapi.json")
    assert other.status_code == 404


# ── Tokens ───────────────────────────────────────────────────────────────────


def test_tokens_scopes_and_revocation(api):
    token = _token(api, scopes=["sast"])
    assert api.client.get(f"{BASE}/v1/scans").status_code == 401
    assert (
        api.client.get(f"{BASE}/v1/scans", headers=_auth("aespa_wrong")).status_code
        == 401
    )
    assert api.client.get(f"{BASE}/v1/scans", headers=_auth(token)).status_code == 200
    assert api.client.get(f"{BASE}/v1/sites", headers=_auth(token)).status_code == 403

    listed = api.client.get(f"{BASE}/admin/tokens").json()
    assert "token" not in listed[0]
    assert token.startswith(listed[0]["prefix"])
    assert listed[0]["last_used_at"] is not None

    api.client.post(f"{BASE}/admin/tokens/{listed[0]['id']}/revoke")
    assert api.client.get(f"{BASE}/v1/scans", headers=_auth(token)).status_code == 401


def test_token_management_is_local_only(api):
    forwarded = api.client.get(
        f"{BASE}/admin/tokens", headers={"X-Forwarded-For": "203.0.113.5"}
    )
    assert forwarded.status_code == 403
    cross_site = api.client.post(
        f"{BASE}/admin/tokens",
        json={"name": "x", "scopes": ["sast"]},
        headers={"Origin": "https://evil.example"},
    )
    assert cross_site.status_code == 403
    same_site = api.client.post(
        f"{BASE}/admin/tokens",
        json={"name": "x", "scopes": ["sast"]},
        headers={"Origin": "http://testserver"},
    )
    assert same_site.status_code == 201


def test_default_webhook_secret_is_shown_once(api):
    created = api.client.post(
        f"{BASE}/admin/tokens",
        json={
            "name": "Hook",
            "scopes": ["sast"],
            "webhook_url": "https://hooks.example.test/a",
        },
    ).json()
    assert created["webhook_secret"].startswith("whsec_")
    listed = api.client.get(f"{BASE}/admin/tokens").json()[0]
    assert listed["has_webhook_secret"] is True
    assert "webhook_secret" not in listed
    bad = api.client.patch(
        f"{BASE}/admin/tokens/{created['id']}", json={"webhook_url": "not a url"}
    )
    assert bad.status_code == 422


# ── SAST scans ───────────────────────────────────────────────────────────────


def test_sast_upload_creates_and_starts_a_scan(api):
    token = _token(api)
    response = _upload(api, token, name="Repo", analysis_mode="light")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"].startswith("sast-")
    assert body["kind"] == "sast"
    assert body["links"]["sarif"].endswith("/sarif")
    run_id = int(body["id"].split("-")[1])
    assert api.started["sast"] == [run_id]
    with Session(get_engine()) as session:
        run = session.get(SastRun, run_id)
        assert run.analysis_mode == "light"
        assert json.loads(run.source_metadata_json) == {"created_via": EXTENSION}

    assert (
        api.client.get(f"{BASE}/v1/scans/{body['id']}", headers=_auth(token)).json()[
            "name"
        ]
        == "Repo"
    )
    other = _token(api)
    assert (
        api.client.get(
            f"{BASE}/v1/scans/{body['id']}", headers=_auth(other)
        ).status_code
        == 404
    )
    assert api.client.get(f"{BASE}/v1/scans", headers=_auth(other)).json()["total"] == 0


def test_sast_upload_rejects_bad_input(api):
    token = _token(api)
    bad_zip = api.client.post(
        f"{BASE}/v1/sast/scans",
        headers=_auth(token),
        files={"file": ("src.zip", b"not a zip", "application/zip")},
    )
    assert bad_zip.status_code == 400
    bad_callbacks = _upload(api, token, callbacks='{"url": "ftp://x"}')
    assert bad_callbacks.status_code == 422
    assert _upload(api, _token(api, scopes=["web"])).status_code == 403


def test_idempotency_key_returns_the_first_response(api):
    token = _token(api)
    first = _upload(api, token, name="Repo", headers={"Idempotency-Key": "build-7"})
    again = _upload(api, token, name="Repo", headers={"Idempotency-Key": "build-7"})
    assert first.status_code == again.status_code == 201
    assert again.json()["id"] == first.json()["id"]
    assert len(api.started["sast"]) == 1
    with Session(get_engine()) as session:
        assert len(session.exec(select(SastRun)).all()) == 1
    changed = _upload(api, token, name="Other", headers={"Idempotency-Key": "build-7"})
    assert changed.status_code == 422


def test_sast_results_summary_gate_and_sarif(api):
    token = _token(api)
    scan = _upload(api, token).json()
    run_id = int(scan["id"].split("-")[1])
    with Session(get_engine()) as session:
        session.add(
            ScanLead(
                producer_run_id=run_id,
                title="SQL injection",
                severity="high",
                category="A03",
                location="app/db.py:12",
                description="Query built from input.",
            )
        )
        session.add(
            ScanLead(
                producer_run_id=run_id, title="Note", severity="low", status="dismissed"
            )
        )
        run = session.get(SastRun, run_id)
        run.status = "completed"
        session.add(run)
        session.commit()

    findings = api.client.get(
        f"{BASE}/v1/scans/{scan['id']}/findings", headers=_auth(token)
    ).json()
    assert findings["partial"] is False
    assert [item["title"] for item in findings["items"]] == ["SQL injection"]
    assert findings["items"][0]["location"]["file"] == "app/db.py"
    assert findings["items"][0]["location"]["line"] == 12
    all_items = api.client.get(
        f"{BASE}/v1/scans/{scan['id']}/findings?include_dismissed=true",
        headers=_auth(token),
    ).json()
    assert all_items["total"] == 2
    assert (
        api.client.get(
            f"{BASE}/v1/scans/{scan['id']}/findings?severity=urgent",
            headers=_auth(token),
        ).status_code
        == 422
    )

    summary = api.client.get(
        f"{BASE}/v1/scans/{scan['id']}/summary?fail_on=high", headers=_auth(token)
    ).json()
    assert summary["by_severity"]["high"] == 1
    assert summary["gate"] == {
        "fail_on": "high",
        "blocking_findings": 1,
        "passed": False,
    }
    assert (
        api.client.get(
            f"{BASE}/v1/scans/{scan['id']}/summary?fail_on=critical",
            headers=_auth(token),
        ).json()["gate"]["passed"]
        is True
    )

    sarif = api.client.get(f"{BASE}/v1/scans/{scan['id']}/sarif", headers=_auth(token))
    assert sarif.headers["content-type"].startswith("application/sarif+json")
    assert sarif.json()["version"] == "2.1.0"


def test_sast_from_source_uses_the_core_source_service(api, monkeypatch):
    calls = []

    async def fake_create(session, **options):
        calls.append(options)
        run = SastRun(
            name="Repo", status="preparing", source_provider=options["provider_id"]
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run

    monkeypatch.setattr(
        "aespa.services.sast_runs_service.create_from_source", fake_create
    )
    token = _token(api)
    response = api.client.post(
        f"{BASE}/v1/sast/scans/from-source",
        headers=_auth(token),
        json={
            "provider_id": "aespa.githubrepository",
            "parameters": {"repository": "acme/shop", "ref": "main"},
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["state"] == "preparing"
    assert calls[0]["metadata"] == {"created_via": EXTENSION}
    assert calls[0]["start_scan"] is True


# ── Sites and web scans ──────────────────────────────────────────────────────


def test_web_scan_with_inline_site_creates_everything_without_leaking_secrets(api):
    token = _token(api)
    response = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token),
        json={
            "site": _site(),
            "name": "Nightly",
            "max_pages": 50,
            "max_depth": 2,
            "crawler_mode": "interactive",
            "llm_max_concurrency": 3,
            "coverage_mode": "deep",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    run_id = int(body["id"].split("-")[1])
    assert api.started["crawl"] == [run_id]
    assert api.started["scheduled"] == [run_id]
    assert body["scan_after_crawl"] is True
    assert "s3cret-pass" not in response.text

    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        assert (run.max_pages, run.max_depth, run.crawler_mode) == (
            50,
            2,
            "interactive",
        )
        assert run.llm_max_concurrency == 3
        assert run.coverage_mode == "deep"
        site = session.get(Site, run.site_id)
        assert site.scan_guidance == "Avoid the checkout payment step."
        assert "api.shop.example.test:443" in json.loads(site.scope_hosts)
        assert {cred.label for cred in site.credentials} == {"Admin", "Custom form"}

    detail = api.client.get(f"{BASE}/v1/sites/{body['site_id']}", headers=_auth(token))
    assert detail.status_code == 200
    text = detail.text
    assert "s3cret-pass" not in text and "9911" not in text and "JBSWY3DP" not in text
    custom = next(
        c for c in detail.json()["credentials"] if c["label"] == "Custom form"
    )
    assert custom["has_totp_seed"] is True
    assert [f["value"] for f in custom["login_fields"]] == ["acme", None]
    assert len(detail.json()["workflow_data"]) == 1


def test_web_scan_site_rules(api):
    token = _token(api)
    web_only = _token(api, scopes=["web"])
    both = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token),
        json={"site_id": 1, "site": _site()},
    )
    assert both.status_code == 422
    no_sites_scope = api.client.post(
        f"{BASE}/v1/web/scans", headers=_auth(web_only), json={"site": _site()}
    )
    assert no_sites_scope.status_code == 403

    guided = _site(name="Guided")
    guided["credentials"] = [
        {"label": "SSO", "username": "u", "password": "p", "auth_mode": "guided"}
    ]
    rejected = api.client.post(
        f"{BASE}/v1/web/scans", headers=_auth(token), json={"site": guided}
    )
    assert rejected.status_code == 422
    assert "unattended" in rejected.text

    first = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token),
        json={"site": _site(), "start": False},
    )
    assert first.status_code == 201
    assert api.started["crawl"] == []
    duplicate = api.client.post(
        f"{BASE}/v1/web/scans", headers=_auth(token), json={"site": _site()}
    )
    assert duplicate.status_code == 409
    updated = _site(scan_guidance="Updated guidance")
    replaced = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token),
        json={"site": updated, "update_site": True, "start": False},
    )
    assert replaced.status_code == 201
    assert replaced.json()["site_id"] == first.json()["site_id"]
    site = api.client.get(
        f"{BASE}/v1/sites/{first.json()['site_id']}", headers=_auth(token)
    ).json()
    assert site["scan_guidance"] == "Updated guidance"

    by_id = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(web_only),
        json={"site_id": site["id"], "scan_after_crawl": False},
    )
    assert by_id.status_code == 201
    assert api.started["scheduled"] == []


def test_sites_routes(api):
    token = _token(api, scopes=["sites"])
    created = api.client.post(f"{BASE}/v1/sites", headers=_auth(token), json=_site())
    assert created.status_code == 201
    site_id = created.json()["id"]
    assert (
        api.client.post(
            f"{BASE}/v1/sites", headers=_auth(token), json=_site()
        ).status_code
        == 409
    )
    upserted = api.client.post(
        f"{BASE}/v1/sites?upsert=true",
        headers=_auth(token),
        json=_site(notes="Upserted"),
    )
    assert upserted.status_code == 200
    assert upserted.json()["notes"] == "Upserted"

    added = api.client.post(
        f"{BASE}/v1/sites/{site_id}/credentials",
        headers=_auth(token),
        json={"label": "Viewer", "username": "viewer", "password": "pw-viewer"},
    )
    assert added.status_code == 201
    assert "pw-viewer" not in added.text
    assert (
        api.client.delete(
            f"{BASE}/v1/sites/{site_id}/credentials/{added.json()['id']}",
            headers=_auth(token),
        ).status_code
        == 204
    )
    bad = api.client.post(
        f"{BASE}/v1/sites",
        headers=_auth(token),
        json={
            "name": "Bad",
            "base_url": "https://x.example.test",
            "login_url": "https://x.example.test/l",
        },
    )
    assert bad.status_code == 422
    assert (
        api.client.get(f"{BASE}/v1/sites/999999", headers=_auth(token)).status_code
        == 404
    )


def test_web_scan_that_cannot_start_reports_its_id_and_can_be_started(api, monkeypatch):
    token = _token(api)
    monkeypatch.setattr(
        "aespa.services.web_runs_service.get_llm_config_for_run", lambda *_: None
    )
    failed = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token) | {"Idempotency-Key": "k1"},
        json={"site": _site()},
    )
    assert failed.status_code == 400
    scan_id = failed.json()["detail"]["scan_id"]
    again = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token) | {"Idempotency-Key": "k1"},
        json={"site": _site()},
    )
    assert again.status_code == 400
    assert again.json()["detail"]["scan_id"] == scan_id

    monkeypatch.setattr(
        "aespa.services.web_runs_service.get_llm_config_for_run", lambda *_: object()
    )
    started = api.client.post(f"{BASE}/v1/scans/{scan_id}/start", headers=_auth(token))
    assert started.status_code == 200, started.text
    assert api.started["scheduled"] == [int(scan_id.split("-")[1])]


# ── Progress and polling ─────────────────────────────────────────────────────


def _set_web(run_id, **values):
    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        for key, value in values.items():
            setattr(run, key, value)
        session.add(run)
        session.commit()


def test_web_sarif_maps_findings_to_url_results_and_owasp_rules(api):
    token = _token(api)
    scan = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token),
        json={"site": _site(), "start": False},
    ).json()
    assert scan["links"]["sarif"].endswith(f"/scans/{scan['id']}/sarif")
    run_id = int(scan["id"].split("-")[1])
    _set_web(run_id, status="complete", phase="finished", outcome="complete")
    with Session(get_engine()) as session:
        session.add(
            ScanFinding(
                test_run_id=run_id,
                public_reference="F-1",
                owasp_category="A03",
                severity="high",
                title="Reflected XSS in search",
                description="The q parameter is echoed without encoding.",
                recommendation="Encode output.",
                cvss_score=8.1,
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N",
                affected_url="https://shop.example.test/search?q=x",
                evidence="GET /search?q=<script> -> 200",
                merged_instances=json.dumps(
                    [{"affected_url": "https://shop.example.test/find?q=x"}]
                ),
                validation_status="confirmed",
            )
        )
        session.add(
            ScanFinding(
                test_run_id=run_id,
                owasp_category="A03",
                severity="low",
                title="Verbose SQL error",
                description="Error text shows the query.",
                affected_url="https://shop.example.test/item?id=1",
            )
        )
        session.add(
            ScanFinding(
                test_run_id=run_id,
                owasp_category="A05",
                severity="medium",
                title="Missing security headers",
                description="No CSP.",
                affected_url="https://shop.example.test/",
            )
        )
        session.add(
            ScanFinding(
                test_run_id=run_id,
                owasp_category="A01",
                severity="critical",
                title="Not real",
                description="Disproved.",
                affected_url="https://shop.example.test/admin",
                validation_status="false_positive",
                validation_note="Page needs a login.",
            )
        )
        session.commit()

    response = api.client.get(
        f"{BASE}/v1/scans/{scan['id']}/sarif", headers=_auth(token)
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/sarif+json")
    document = response.json()
    assert document["version"] == "2.1.0"
    run = document["runs"][0]
    rules = run["tool"]["driver"]["rules"]
    assert [rule["id"] for rule in rules] == ["AESPA/WEB-A03", "AESPA/WEB-A05"]
    assert rules[0]["name"] == "A03 Injection"
    assert rules[0]["properties"]["security-severity"] == "8.1"
    assert "OWASP-A03" in rules[0]["properties"]["tags"]
    results = run["results"]
    assert [r["message"]["text"] for r in results] == [
        "Reflected XSS in search",
        "Missing security headers",
        "Verbose SQL error",
    ]
    first = results[0]
    assert first["ruleId"] == "AESPA/WEB-A03"
    assert rules[first["ruleIndex"]]["id"] == first["ruleId"]
    assert first["level"] == "error"
    location = first["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "https://shop.example.test/search?q=x"
    assert location["region"]["snippet"]["text"] == "GET /search?q=<script> -> 200"
    related = first["relatedLocations"][0]["physicalLocation"]["artifactLocation"]
    assert related == {"uri": "https://shop.example.test/find?q=x"}
    assert first["properties"]["cvssScore"] == 8.1
    assert first["properties"]["reference"] == "F-1"
    assert "Encode output." in first["message"]["markdown"]
    assert first["partialFingerprints"]["primaryLocationHash"]
    assert results[1]["level"] == "warning"
    assert results[2]["level"] == "note"
    assert run["invocations"][0]["executionSuccessful"] is True
    assert "suppressions" not in json.dumps(results)

    with_dismissed = api.client.get(
        f"{BASE}/v1/scans/{scan['id']}/sarif?include_dismissed=true",
        headers=_auth(token),
    ).json()["runs"][0]
    suppressed = with_dismissed["results"][0]
    assert suppressed["message"]["text"] == "Not real"
    assert suppressed["suppressions"][0]["justification"] == "Page needs a login."
    rule_ids = {rule["id"] for rule in with_dismissed["tool"]["driver"]["rules"]}
    assert "AESPA/WEB-A01" in rule_ids


def test_web_sarif_for_deleted_run_is_not_found(api):
    token = _token(api)
    scan = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token),
        json={"site": _site(), "start": False},
    ).json()
    run_id = int(scan["id"].split("-")[1])
    with Session(get_engine()) as session:
        session.delete(session.get(TestRun, run_id))
        session.commit()
    response = api.client.get(
        f"{BASE}/v1/scans/{scan['id']}/sarif", headers=_auth(token)
    )
    assert response.status_code == 404


def test_web_progress_states(api):
    token = _token(api)
    scan = api.client.post(
        f"{BASE}/v1/web/scans",
        headers=_auth(token),
        json={"site": _site(), "start": False},
    ).json()
    run_id = int(scan["id"].split("-")[1])
    assert scan["state"] == "queued"

    _set_web(run_id, status="complete", phase="crawled")
    status = run_progress.get_progress(run_id, scan_after_crawl=True)
    assert (status["state"], status["phase"]) == ("failed", "crawled")
    assert run_progress.get_progress(run_id)["state"] == "completed"

    _set_web(run_id, status="complete", phase="finished", outcome="complete")
    with Session(get_engine()) as session:
        session.add(
            ScanFinding(
                test_run_id=run_id,
                owasp_category="A03",
                severity="high",
                title="XSS",
                description="Reflected",
                affected_url="https://shop.example.test/q",
            )
        )
        session.commit()
    status = run_progress.get_progress(run_id, scan_after_crawl=True)
    assert status["state"] == "completed"
    assert status["percent"] == 100
    assert status["counts"]["findings"]["high"] == 1

    _set_web(run_id, status="failed", error_message="Browser crashed")
    status = run_progress.get_progress(run_id)
    assert (status["state"], status["error"]) == ("failed", "Browser crashed")
    _set_web(run_id, status="stopped")
    assert run_progress.get_progress(run_id)["state"] == "stopped"


def test_sast_progress_states():
    with Session(get_engine()) as session:
        run = SastRun(name="Repo", status="preparing")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    assert run_progress.get_progress(run_id)["state"] == "preparing"
    for status, state in [
        ("pending", "queued"),
        ("completed", "completed"),
        ("failed", "failed"),
        ("cancelled", "stopped"),
        ("paused", "paused"),
    ]:
        with Session(get_engine()) as session:
            run = session.get(SastRun, run_id)
            run.status = status
            session.add(run)
            session.commit()
        assert run_progress.get_progress(run_id)["state"] == state, status
    assert run_progress.get_progress(987654) is None


def test_polling_supports_etag_and_wait(api):
    token = _token(api)
    scan = _upload(api, token).json()
    url = f"{BASE}/v1/scans/{scan['id']}"
    first = api.client.get(url, headers=_auth(token))
    etag = first.headers["etag"]
    assert first.headers["cache-control"] == "no-store"
    same = api.client.get(url, headers=_auth(token) | {"If-None-Match": etag})
    assert same.status_code == 304
    waited = api.client.get(
        f"{url}?wait=1", headers=_auth(token) | {"If-None-Match": etag}
    )
    assert waited.status_code == 304

    run_id = int(scan["id"].split("-")[1])
    with Session(get_engine()) as session:
        run = session.get(SastRun, run_id)
        run.status = "completed"
        session.add(run)
        session.commit()
    changed = api.client.get(
        f"{url}?wait=5", headers=_auth(token) | {"If-None-Match": etag}
    )
    assert changed.status_code == 200
    assert changed.json()["state"] == "completed"
    assert api.client.get(f"{url}/activity", headers=_auth(token)).json() == {
        "items": [],
        "next_cursor": 0,
    }


def test_stop_scan(api, monkeypatch):
    token = _token(api)
    scan = _upload(api, token).json()
    stopped = []

    async def fake_stop(session, run_id):
        stopped.append(run_id)
        return True

    monkeypatch.setattr("aespa.services.sast_runs_service.stop", fake_stop)
    result = api.client.post(f"{BASE}/v1/scans/{scan['id']}/stop", headers=_auth(token))
    assert result.status_code == 200
    assert result.json()["stopped"] is True
    assert stopped == [int(scan["id"].split("-")[1])]
    assert (
        api.client.post(
            f"{BASE}/v1/scans/{scan['id']}/stop",
            headers=_auth(_token(api, scopes=["web"])),
        ).status_code
        == 404
    )


# ── Callbacks ────────────────────────────────────────────────────────────────


def _scan_with_callbacks(api, token, **callbacks):
    response = _upload(
        api,
        token,
        callbacks=json.dumps({"url": "https://hooks.example.test/aespa", **callbacks}),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete(run_id):
    with Session(get_engine()) as session:
        run = session.get(SastRun, run_id)
        run.status = "completed"
        session.add(run)
        session.commit()


def test_callbacks_are_signed_and_sent_once(api):
    token = _token(api)
    scan = _scan_with_callbacks(api, token)
    secret = scan["callbacks"]["secret"]
    assert secret.startswith("whsec_")
    status = api.client.get(f"{BASE}/v1/scans/{scan['id']}", headers=_auth(token))
    assert status.json()["callbacks"]["secret"] is None
    run_id = int(scan["id"].split("-")[1])

    assert api_callbacks.check_scans(api.store, api.core) == 0
    _complete(run_id)
    assert api_callbacks.check_scans(api.store, api.core) == 2
    assert api_callbacks.check_scans(api.store, api.core) == 0

    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(204)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert api_callbacks.deliver_due(api.store, client) == 2
        assert api_callbacks.deliver_due(api.store, client) == 0

    events_sent = [request.headers["x-aespa-event"] for request in sent]
    assert events_sent == ["scan.started", "scan.completed"]
    request = sent[1]
    timestamp, signature = (
        part.split("=", 1)[1]
        for part in request.headers["x-aespa-signature"].split(",")
    )
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + request.content, hashlib.sha256
    ).hexdigest()
    assert hmac.compare_digest(signature, expected)
    payload = json.loads(request.content)
    assert payload["id"] == request.headers["x-aespa-delivery"]
    assert payload["scan"]["state"] == "completed"
    assert secret not in request.content.decode()

    deliveries = api.client.get(
        f"{BASE}/v1/scans/{scan['id']}/deliveries", headers=_auth(token)
    ).json()
    assert [item["status"] for item in deliveries] == ["delivered", "delivered"]


def test_callbacks_retry_then_fail_and_can_be_redelivered(api):
    token = _token(api)
    scan = _scan_with_callbacks(api, token, events=["scan.completed"])
    _complete(int(scan["id"].split("-")[1]))
    assert api_callbacks.check_scans(api.store, api.core) == 1

    calls = []

    def redirect(request):
        calls.append(request)
        return httpx.Response(
            302, headers={"Location": "https://elsewhere.example.test"}
        )

    at = now()
    with httpx.Client(
        transport=httpx.MockTransport(redirect), follow_redirects=False
    ) as client:
        for delay in (timedelta(0), *api_callbacks.RETRY_DELAYS):
            at += delay
            api_callbacks.deliver_due(api.store, client, at=at)
    assert len(calls) == len(api_callbacks.RETRY_DELAYS) + 1
    with api.store.session() as session:
        delivery = session.exec(select(ApiDelivery)).one()
        assert (delivery.status, delivery.last_status_code) == ("failed", 302)

    redelivered = api.client.post(
        f"{BASE}/v1/deliveries/{delivery.delivery_id}/redeliver", headers=_auth(token)
    )
    assert redelivered.json()["status"] == "pending"
    other = _token(api)
    assert (
        api.client.post(
            f"{BASE}/v1/deliveries/{delivery.delivery_id}/redeliver",
            headers=_auth(other),
        ).status_code
        == 404
    )
    # A redelivery gets a fresh set of retries instead of failing on its
    # first error.
    with httpx.Client(transport=httpx.MockTransport(redirect)) as client:
        assert api_callbacks.deliver_due(api.store, client) == 0
    with api.store.session() as session:
        delivery = session.exec(select(ApiDelivery)).one()
        assert (delivery.status, delivery.attempts) == ("pending", 1)
        delivery.next_attempt_at = now()
        session.add(delivery)
        session.commit()
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200))
    ) as client:
        assert api_callbacks.deliver_due(api.store, client) == 1
    failed = api.client.get(f"{BASE}/admin/deliveries?status=failed").json()
    assert failed == []


def test_events_follow_state_changes():
    row = ApiScan(run_id=1, kind="web", token_id=1)
    at = now()

    def step(state, phase=None, percent=None):
        events_out = api_callbacks.events_for(
            row, {"state": state, "phase": phase, "percent": percent}, at
        )
        row.last_state, row.last_phase = state, phase
        if "scan.progress" in events_out:
            row.last_percent, row.last_progress_sent_at = percent, at
        return events_out

    assert step("queued") == []
    assert step("running", "crawling") == ["scan.started"]
    assert step("running", "scanning", 10) == ["scan.phase_changed", "scan.progress"]
    assert step("running", "scanning", 20) == []  # Less than a minute later.
    assert step("needs_action", "scanning") == ["scan.needs_action"]
    assert step("paused", "scanning") == ["scan.paused"]
    assert step("running", "scanning") == ["scan.phase_changed"]
    assert step("failed", "scanning") == ["scan.failed"]
    assert step("failed", "scanning") == []


def test_started_is_always_sent_first():
    at = now()
    for state, expected in [
        ("paused", ["scan.started", "scan.paused"]),
        ("failed", ["scan.started", "scan.failed"]),
        ("needs_action", ["scan.started", "scan.needs_action"]),
    ]:
        row = ApiScan(run_id=1, kind="web", token_id=1)
        assert (
            api_callbacks.events_for(row, {"state": state, "phase": "x"}, at)
            == expected
        ), state


def test_default_token_webhook_is_used(api):
    created = api.client.post(
        f"{BASE}/admin/tokens",
        json={
            "name": "Hook",
            "scopes": ["sast"],
            "webhook_url": "https://hooks.example.test/a",
        },
    ).json()
    scan = _upload(api, created["token"]).json()
    assert scan["callbacks"]["url"] == "https://hooks.example.test/a"
    with api.store.session() as session:
        row = session.exec(select(ApiScan)).one()
        assert row.callback_secret == created["webhook_secret"]


# ── Core rules ───────────────────────────────────────────────────────────────


def test_run_changes_reach_extension_listeners_until_disabled(api):
    before = len(run_lifecycle._listeners)
    seen = []
    unsubscribe = api.core.on_run_change(
        lambda run_id, kind, reason: seen.append(run_id)
    )
    events.emit(4242, {"type": "run_update", "status": "running"})
    events.emit(4242, {"type": "http"})
    assert seen == [4242]
    unsubscribe()
    assert len(run_lifecycle._listeners) == before
    assert before >= 1  # The extension's own listener.
    api.manager.set_enabled(EXTENSION, False)
    assert len(run_lifecycle._listeners) == before - 1


def test_core_access_requires_declared_capabilities(api):
    from aespa.extensions.core_access import CoreAccess

    limited = CoreAccess(["api.routes"], lambda listener: None)
    with pytest.raises(PermissionError):
        limited.sast
    with pytest.raises(PermissionError):
        limited.web
    assert limited.runs.progress(123456) is None


def test_extension_writes_to_main_database_only_through_core_services(api):
    """Every main-database write made while serving the API passes through core_access."""
    extension_dir = str(
        Path(__file__).resolve().parents[2] / "extensions" / "builtin" / "api"
    )
    violations = []

    def check(conn, cursor, statement, parameters, context, executemany):
        if not statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            return
        files = [frame.filename for frame in traceback.extract_stack()]
        if any(name.startswith(extension_dir) for name in files) and not any(
            name.endswith("aespa/extensions/core_access.py") for name in files
        ):
            violations.append(statement.split("\n")[0])

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", check)
    try:
        token = _token(api)
        scan = _upload(api, token, headers={"Idempotency-Key": "w"}).json()
        api.client.get(f"{BASE}/v1/scans/{scan['id']}", headers=_auth(token))
        api.client.get(f"{BASE}/v1/scans/{scan['id']}/findings", headers=_auth(token))
        api.client.get(f"{BASE}/v1/scans/{scan['id']}/sarif", headers=_auth(token))
        api.client.post(
            f"{BASE}/v1/web/scans",
            headers=_auth(token),
            json={
                "site": _site(),
                "callbacks": {"url": "https://hooks.example.test/a"},
            },
        )
        _complete(int(scan["id"].split("-")[1]))
        api_callbacks.check_scans(api.store, api.core)
    finally:
        event.remove(engine, "before_cursor_execute", check)
    assert violations == []


def test_published_request_examples_are_valid():
    from extensions.builtin.api import examples, schemas

    cases = [
        (schemas.SiteIn, examples.SITE),
        (schemas.CredentialCreate, examples.CREDENTIAL),
        (schemas.WebScanCreate, examples.WEB_SCAN),
        (schemas.SourceScanCreate, examples.SOURCE_SCAN),
    ]
    for model, named in cases:
        for name, example in named.items():
            model.model_validate(example["value"]), name
    schemas.ScanStatus.model_validate(examples.SCAN_STATUS)
    schemas.ScanStatus.model_validate(examples.SAST_SCAN_STATUS)


def test_examples_are_in_the_definition(api):
    document = api.client.get(f"/api/extensions/{EXTENSION}/openapi.json").json()
    body = document["paths"]["/v1/web/scans"]["post"]["requestBody"]["content"]
    assert set(body["application/json"]["examples"]) == {
        "existing_site",
        "new_site",
        "crawl_only",
    }
    assert (
        document["components"]["schemas"]["ScanStatus"]["examples"][0]["id"] == "web-42"
    )
