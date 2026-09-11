"""Campaign child runs remain usable through their ordinary run endpoints.

Campaign lead handoff/import operations and read-only endpoint behavior remain
covered here alongside lifecycle, settings, scan-control, and destructive
mutations.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session

from aespa.models import (
    ApiCollection,
    ApiTestRun,
    Application,
    ApplicationComponent,
    ApplicationTarget,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentSnapshot,
    CrawledPage,
    SastRun,
    ScanFinding,
    ScanLead,
    Site,
    TestRun,
)


def _seed_campaign_owned_runs(engine) -> dict:
    """One campaign owning one SastRun, one TestRun, and one ApiTestRun."""
    with Session(engine) as s:
        app = Application(name="Acme")
        s.add(app)
        s.flush()
        component = ApplicationComponent(application_id=app.id, name="checkout-ui")
        s.add(component)
        s.flush()
        snapshot = ComponentSnapshot(
            component_id=component.id,
            filename="ui.zip",
            stored_path="/x/ui.zip",
            size_bytes=1,
            sha256="a" * 64,
        )
        s.add(snapshot)

        site = Site(name="Portal", base_url="http://portal.test")
        s.add(site)
        s.flush()
        site_target = ApplicationTarget(
            application_id=app.id, target_type="site", target_id=site.id
        )
        s.add(site_target)

        collection = ApiCollection(name="Orders API", base_url="http://api.test")
        s.add(collection)
        s.flush()
        api_target = ApplicationTarget(
            application_id=app.id, target_type="api_collection", target_id=collection.id
        )
        s.add(api_target)
        s.flush()

        campaign = AssessmentCampaign(application_id=app.id, name="release-1")
        s.add(campaign)
        s.flush()

        sast_run = SastRun(name="child sast", status="completed")
        s.add(sast_run)
        s.flush()
        s.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=component.id,
                snapshot_id=snapshot.id,
                sast_run_id=sast_run.id,
                status="completed",
            )
        )

        web_run = TestRun(site_id=site.id, name="child web run")
        s.add(web_run)
        s.flush()
        s.add(
            CampaignTargetMember(
                campaign_id=campaign.id,
                target_id=site_target.id,
                target_type="site",
                test_run_id=web_run.id,
            )
        )
        page = CrawledPage(test_run_id=web_run.id, url="http://portal.test/login")
        s.add(page)
        s.flush()
        finding = ScanFinding(
            test_run_id=web_run.id,
            page_id=page.id,
            owasp_category="A01",
            severity="high",
            title="Broken access control",
            description="seeded finding",
        )
        s.add(finding)
        s.flush()

        api_run = ApiTestRun(collection_id=collection.id, name="child api run")
        s.add(api_run)
        s.flush()
        s.add(
            CampaignTargetMember(
                campaign_id=campaign.id,
                target_id=api_target.id,
                target_type="api_collection",
                api_test_run_id=api_run.id,
            )
        )
        s.commit()

        return {
            "sast_run_id": sast_run.id,
            "web_run_id": web_run.id,
            "web_page_id": page.id,
            "web_finding_id": finding.id,
            "api_run_id": api_run.id,
        }


def _seed_standalone_runs(engine) -> dict:
    """Ordinary standalone runs — none of these are campaign-owned."""
    with Session(engine) as s:
        sast_run = SastRun(name="standalone sast", status="completed")
        s.add(sast_run)
        site = Site(name="StandaloneSite", base_url="http://standalone.test")
        s.add(site)
        s.flush()
        web_run = TestRun(site_id=site.id, name="standalone web run")
        s.add(web_run)
        collection = ApiCollection(name="Standalone API", base_url="http://sapi.test")
        s.add(collection)
        s.flush()
        api_run = ApiTestRun(collection_id=collection.id, name="standalone api run")
        s.add(api_run)
        s.commit()
        return {
            "sast_run_id": sast_run.id,
            "web_run_id": web_run.id,
            "api_run_id": api_run.id,
        }


def _seed_reportable_sast_lead(engine, sast_run_id: int) -> int:
    """Add one validated original lead to a completed SAST run."""
    with Session(engine) as s:
        run = s.get(SastRun, sast_run_id)
        assert run is not None
        run.leads_count = 1
        lead = ScanLead(
            producer_run_type="sast",
            producer_run_id=sast_run_id,
            title="Validated static lead",
            description="A campaign lead that may be dynamically investigated.",
            category="A01",
            severity="high",
            confidence=0.95,
            location="app.py:10",
            reportable=True,
            validation_status="confirmed",
            status="open",
        )
        s.add(lead)
        s.commit()
        s.refresh(lead)
        return lead.id


# ── SAST mutation endpoints ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs", "expected_status"),
    [
        (
            "PATCH",
            "/api/sast-runs/{sast_run_id}",
            {"json": {"llm_profile_id": None}},
            200,
        ),
        ("POST", "/api/sast-runs/{sast_run_id}/scan/start", {}, 200),
        ("POST", "/api/sast-runs/{sast_run_id}/scan/stop", {}, 200),
    ],
    ids=["update-profile", "start-scan", "stop-scan"],
)
def test_campaign_owned_sast_runs_use_standard_endpoints(
    client,
    isolated_db_engine,
    method,
    path,
    request_kwargs,
    expected_status,
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    response = client.request(method, path.format(**ctx), **request_kwargs)
    assert response.status_code == expected_status


def test_sast_lead_handoff_allowed_for_campaign_owned_source(
    client, isolated_db_engine
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    standalone = _seed_standalone_runs(isolated_db_engine)
    lead_id = _seed_reportable_sast_lead(isolated_db_engine, ctx["sast_run_id"])
    resp = client.post(
        f"/api/sast-runs/{ctx['sast_run_id']}/leads/{lead_id}/handoff",
        json={"run_type": "web", "run_id": standalone["web_run_id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["queued"] is True


def test_api_import_leads_allowed_for_campaign_owned_target(client, isolated_db_engine):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    standalone = _seed_standalone_runs(isolated_db_engine)
    _seed_reportable_sast_lead(isolated_db_engine, standalone["sast_run_id"])
    resp = client.post(
        f"/api/api-test-runs/{ctx['api_run_id']}/import-leads",
        json={"sast_run_id": standalone["sast_run_id"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"imported": 1}


def test_api_import_leads_allowed_for_campaign_owned_source(client, isolated_db_engine):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    standalone = _seed_standalone_runs(isolated_db_engine)
    _seed_reportable_sast_lead(isolated_db_engine, ctx["sast_run_id"])
    resp = client.post(
        f"/api/api-test-runs/{standalone['api_run_id']}/import-leads",
        json={"sast_run_id": ctx["sast_run_id"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"imported": 1}


def test_clear_and_delete_api_run_leads_blocked_for_campaign_owned_run(
    client, isolated_db_engine
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    assert (
        client.delete(f"/api/api-test-runs/{ctx['api_run_id']}/leads").status_code
        != 409
    )
    assert (
        client.delete(f"/api/api-test-runs/{ctx['api_run_id']}/leads/1").status_code
        != 409
    )


# ── Web mutation endpoints ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs", "expected_status"),
    [
        (
            "PATCH",
            "/api/test-runs/{web_run_id}",
            {"json": {"max_depth": 3, "max_pages": 50}},
            200,
        ),
        ("POST", "/api/test-runs/{web_run_id}/start", {}, 400),
        ("POST", "/api/test-runs/{web_run_id}/restart", {}, 400),
        ("POST", "/api/test-runs/{web_run_id}/crawl/clear", {}, 200),
        (
            "POST",
            "/api/test-runs/{web_run_id}/crawl/import",
            {"files": {"file": ("crawl.json", b"{}", "application/json")}},
            409,
        ),
        ("POST", "/api/test-runs/{web_run_id}/stop", {}, 409),
    ],
    ids=["update-settings", "start", "restart", "clear", "import", "stop"],
)
def test_campaign_owned_web_runs_use_standard_endpoints(
    client,
    isolated_db_engine,
    method,
    path,
    request_kwargs,
    expected_status,
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    response = client.request(method, path.format(**ctx), **request_kwargs)
    assert response.status_code == expected_status
    assert "campaign" not in response.json().get("detail", "").lower()


def test_web_import_leads_allowed_for_campaign_owned_target(client, isolated_db_engine):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    standalone = _seed_standalone_runs(isolated_db_engine)
    _seed_reportable_sast_lead(isolated_db_engine, standalone["sast_run_id"])
    resp = client.post(
        f"/api/test-runs/{ctx['web_run_id']}/import-leads",
        json={"sast_run_id": standalone["sast_run_id"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"imported": 1}


def test_web_import_leads_allowed_for_campaign_owned_source(client, isolated_db_engine):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    standalone = _seed_standalone_runs(isolated_db_engine)
    _seed_reportable_sast_lead(isolated_db_engine, ctx["sast_run_id"])
    resp = client.post(
        f"/api/test-runs/{standalone['web_run_id']}/import-leads",
        json={"sast_run_id": ctx["sast_run_id"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"imported": 1}


def test_clear_and_delete_web_run_leads_blocked_for_campaign_owned_run(
    client, isolated_db_engine
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    assert client.delete(f"/api/test-runs/{ctx['web_run_id']}/leads").status_code != 409
    assert (
        client.delete(f"/api/test-runs/{ctx['web_run_id']}/leads/1").status_code != 409
    )


# ── Thinking-scan mutation endpoints ─────────────────────────────────────────


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/api/test-runs/{web_run_id}/thinking-scan/start", 200),
        ("/api/test-runs/{web_run_id}/thinking-scan/stop", 200),
        ("/api/test-runs/{web_run_id}/thinking-scan/resume", 404),
        ("/api/test-runs/{web_run_id}/pages/{web_page_id}/test", 200),
    ],
    ids=["start", "stop", "resume-without-checkpoint", "focused-page"],
)
def test_campaign_owned_web_scan_controls_use_standard_endpoints(
    client, isolated_db_engine, path, expected_status
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    response = client.post(path.format(**ctx))
    assert response.status_code == expected_status


def test_finding_mutations_blocked_for_campaign_owned_run(client, isolated_db_engine):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    web_run_id = ctx["web_run_id"]
    finding_id = ctx["web_finding_id"]

    assert (
        client.delete(f"/api/test-runs/{web_run_id}/findings/{finding_id}").status_code
        != 409
    )
    assert (
        client.patch(
            f"/api/test-runs/{web_run_id}/findings/{finding_id}",
            json={"severity": "low"},
        ).status_code
        != 409
    )
    assert client.delete(f"/api/test-runs/{web_run_id}/findings").status_code != 409
    assert (
        client.post(
            f"/api/test-runs/{web_run_id}/findings/import",
            json=[
                {
                    "title": "x",
                    "description": "y",
                    "severity": "low",
                    "validation_status": "unvalidated",
                }
            ],
        ).status_code
        != 409
    )


def test_validation_endpoints_blocked_for_campaign_owned_run(
    client, isolated_db_engine
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    web_run_id = ctx["web_run_id"]
    finding_id = ctx["web_finding_id"]

    assert client.post(f"/api/test-runs/{web_run_id}/validate").status_code != 409
    assert client.post(f"/api/test-runs/{web_run_id}/validate/stop").status_code != 409
    assert (
        client.post(
            f"/api/test-runs/{web_run_id}/findings/{finding_id}/validate"
        ).status_code
        != 409
    )


def test_log_clearing_blocked_for_campaign_owned_run(client, isolated_db_engine):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    web_run_id = ctx["web_run_id"]

    assert client.delete(f"/api/test-runs/{web_run_id}/scan-log").status_code != 409
    assert client.delete(f"/api/test-runs/{web_run_id}/agent-log").status_code != 409


# ── API mutation endpoints ───────────────────────────────────────────────────


@pytest.mark.parametrize("action", ["start", "stop"])
def test_campaign_owned_api_scan_controls_use_standard_endpoints(
    client, isolated_db_engine, action
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)
    response = client.post(f"/api/api-test-runs/{ctx['api_run_id']}/scan/{action}")
    assert response.status_code == 200


# ── Read-only endpoints must still work for a campaign-owned run ────────────


def test_read_only_endpoints_not_blocked_for_campaign_owned_runs(
    client, isolated_db_engine
):
    ctx = _seed_campaign_owned_runs(isolated_db_engine)

    assert client.get(f"/api/sast-runs/{ctx['sast_run_id']}").status_code == 200
    assert (
        client.get(f"/api/sast-runs/{ctx['sast_run_id']}/analysis").status_code == 200
    )
    assert (
        client.get(f"/api/sast-runs/{ctx['sast_run_id']}/scan/status").status_code
        == 200
    )

    assert client.get(f"/api/test-runs/{ctx['web_run_id']}").status_code == 200
    assert client.get(f"/api/test-runs/{ctx['web_run_id']}/leads").status_code == 200
    assert (
        client.get(
            f"/api/test-runs/{ctx['web_run_id']}/thinking-scan/status"
        ).status_code
        == 200
    )
    assert client.get(f"/api/test-runs/{ctx['web_run_id']}/findings").status_code == 200
    assert client.get(f"/api/test-runs/{ctx['web_run_id']}/scan-log").status_code == 200
    assert (
        client.get(f"/api/test-runs/{ctx['web_run_id']}/agent-log").status_code == 200
    )
    assert (
        client.get(f"/api/test-runs/{ctx['web_run_id']}/validate/status").status_code
        == 200
    )

    assert client.get(f"/api/api-test-runs/{ctx['api_run_id']}").status_code == 200
    assert (
        client.get(f"/api/api-test-runs/{ctx['api_run_id']}/scan/status").status_code
        == 200
    )


# ── Standalone (non-campaign) runs remain fully usable ──────────────────────


def test_standalone_runs_are_never_blocked(client, isolated_db_engine):
    standalone = _seed_standalone_runs(isolated_db_engine)

    assert (
        client.post(
            f"/api/sast-runs/{standalone['sast_run_id']}/scan/start"
        ).status_code
        != 409
    )
    assert (
        client.patch(
            f"/api/test-runs/{standalone['web_run_id']}",
            json={"max_depth": 3, "max_pages": 50},
        ).status_code
        != 409
    )
    assert (
        client.post(
            f"/api/api-test-runs/{standalone['api_run_id']}/scan/start"
        ).status_code
        != 409
    )
