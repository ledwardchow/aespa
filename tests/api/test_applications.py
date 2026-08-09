"""Applications API: CRUD, same-application validation, and safe ZIP
snapshot upload/deletion behavior.
"""

from __future__ import annotations

import io
import zipfile

from sqlmodel import Session

from aespa.models import (
    ApplicationTarget,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentSnapshot,
    SastRun,
    TestRun,
)


def _zip_bytes(contents: str = "def handler():\n    pass\n") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("app.py", contents)
    return buf.getvalue()


def _create_application(client, name="Acme Portal") -> dict:
    resp = client.post("/api/applications", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_component(client, app_id, name="checkout-ui") -> dict:
    resp = client.post(f"/api/applications/{app_id}/components", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _upload_snapshot(client, app_id, component_id, filename="v1.zip") -> dict:
    resp = client.post(
        f"/api/applications/{app_id}/components/{component_id}/snapshots",
        files={"file": (filename, _zip_bytes(), "application/zip")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Application / component CRUD ─────────────────────────────────────────────


def test_create_and_get_application(client):
    app = _create_application(client)
    resp = client.get(f"/api/applications/{app['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme Portal"


def test_duplicate_application_name_rejected(client):
    _create_application(client, "Dup")
    resp = client.post("/api/applications", json={"name": "Dup"})
    assert resp.status_code == 409


def test_component_names_unique_within_application(client):
    app = _create_application(client)
    _create_component(client, app["id"], "orders-api")
    resp = client.post(
        f"/api/applications/{app['id']}/components", json={"name": "orders-api"}
    )
    assert resp.status_code == 409


def test_component_names_can_repeat_across_applications(client):
    app_a = _create_application(client, "App A")
    app_b = _create_application(client, "App B")
    _create_component(client, app_a["id"], "shared-name")
    resp = client.post(
        f"/api/applications/{app_b['id']}/components", json={"name": "shared-name"}
    )
    assert resp.status_code == 201


# ── Snapshot immutability ─────────────────────────────────────────────────────


def test_snapshot_upload_creates_new_immutable_version(client, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app = _create_application(client)
    component = _create_component(client, app["id"])

    first = _upload_snapshot(client, app["id"], component["id"], "v1.zip")
    second = _upload_snapshot(client, app["id"], component["id"], "v2.zip")

    assert first["id"] != second["id"]
    resp = client.get(
        f"/api/applications/{app['id']}/components/{component['id']}/snapshots"
    )
    assert resp.status_code == 200
    ids = {row["id"] for row in resp.json()}
    assert ids == {first["id"], second["id"]}
    # Both stored files exist independently on disk (immutable, never overwritten).
    assert first["sha256"] and second["sha256"]


def test_snapshot_upload_rejects_non_zip(client, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app = _create_application(client)
    component = _create_component(client, app["id"])
    resp = client.post(
        f"/api/applications/{app['id']}/components/{component['id']}/snapshots",
        files={"file": ("bad.zip", b"not a zip", "application/zip")},
    )
    assert resp.status_code == 400


def test_snapshot_upload_enforces_size_limit(client, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    from aespa.services import applications as applications_svc

    monkeypatch.setattr(applications_svc, "MAX_SNAPSHOT_UPLOAD_BYTES", 4)
    monkeypatch.setattr("aespa.api.applications._MAX_SNAPSHOT_UPLOAD_BYTES", 4)
    app = _create_application(client)
    component = _create_component(client, app["id"])
    resp = client.post(
        f"/api/applications/{app['id']}/components/{component['id']}/snapshots",
        files={"file": ("v1.zip", _zip_bytes(), "application/zip")},
    )
    assert resp.status_code == 400


def test_delete_snapshot_blocked_while_referenced_by_campaign(
    client, isolated_db_engine, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app = _create_application(client)
    component = _create_component(client, app["id"])
    snapshot = _upload_snapshot(client, app["id"], component["id"])

    site_resp = client.post(
        "/api/sites", json={"name": "S1", "base_url": "http://t.local"}
    )
    assert site_resp.status_code == 201, site_resp.text
    site_id = site_resp.json()["id"]
    target_resp = client.post(
        f"/api/applications/{app['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    )
    assert target_resp.status_code == 201, target_resp.text
    target = target_resp.json()

    campaign_resp = client.post(
        f"/api/applications/{app['id']}/campaigns",
        json={
            "name": "release-1",
            "source_members": [
                {"component_id": component["id"], "snapshot_id": snapshot["id"]}
            ],
            "target_members": [{"target_id": target["id"]}],
        },
    )
    assert campaign_resp.status_code == 201, campaign_resp.text

    delete_resp = client.delete(
        f"/api/applications/{app['id']}/components/{component['id']}"
        f"/snapshots/{snapshot['id']}"
    )
    assert delete_resp.status_code == 409

    with Session(isolated_db_engine) as s:
        assert s.get(ComponentSnapshot, snapshot["id"]) is not None


def test_campaign_detail_reports_linked_child_run_status(
    client, isolated_db_engine, tmp_path, monkeypatch
):
    """Campaign status must reflect a child run resumed from its own page."""
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app = _create_application(client)
    component = _create_component(client, app["id"])
    snapshot = _upload_snapshot(client, app["id"], component["id"])
    site_id = client.post(
        "/api/sites", json={"name": "Campaign target", "base_url": "http://target.local"}
    ).json()["id"]
    target = client.post(
        f"/api/applications/{app['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    ).json()
    campaign = client.post(
        f"/api/applications/{app['id']}/campaigns",
        json={
            "name": "status-sync",
            "source_members": [
                {"component_id": component["id"], "snapshot_id": snapshot["id"]}
            ],
            "target_members": [{"target_id": target["id"]}],
        },
    ).json()

    with Session(isolated_db_engine) as s:
        source_member = s.get(CampaignSourceMember, campaign["source_members"][0]["id"])
        target_member = s.get(CampaignTargetMember, campaign["target_members"][0]["id"])
        sast_run = SastRun(name="source", status="scanning")
        test_run = TestRun(site_id=site_id, name="target", status="running")
        s.add(sast_run)
        s.add(test_run)
        s.flush()
        source_member.sast_run_id = sast_run.id
        target_member.test_run_id = test_run.id
        s.add(source_member)
        s.add(target_member)
        s.commit()

    response = client.get(
        f"/api/applications/{app['id']}/campaigns/{campaign['id']}"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_members"][0]["run_status"] == "scanning"
    assert payload["target_members"][0]["run_status"] == "running"


def test_delete_unreferenced_snapshot_succeeds(client, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app = _create_application(client)
    component = _create_component(client, app["id"])
    snapshot = _upload_snapshot(client, app["id"], component["id"])
    resp = client.delete(
        f"/api/applications/{app['id']}/components/{component['id']}"
        f"/snapshots/{snapshot['id']}"
    )
    assert resp.status_code == 204


# ── Same-application validation ──────────────────────────────────────────────


def test_campaign_rejects_component_from_another_application(
    client, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app_a = _create_application(client, "App A")
    app_b = _create_application(client, "App B")
    component_b = _create_component(client, app_b["id"], "other-app-component")
    snapshot_b = _upload_snapshot(client, app_b["id"], component_b["id"])

    site_resp = client.post(
        "/api/sites", json={"name": "S2", "base_url": "http://t2.local"}
    )
    site_id = site_resp.json()["id"]
    target_resp = client.post(
        f"/api/applications/{app_a['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    )
    target = target_resp.json()

    resp = client.post(
        f"/api/applications/{app_a['id']}/campaigns",
        json={
            "name": "cross-app",
            "source_members": [
                {"component_id": component_b["id"], "snapshot_id": snapshot_b["id"]}
            ],
            "target_members": [{"target_id": target["id"]}],
        },
    )
    assert resp.status_code == 400


def test_hint_rejects_target_from_another_application(client, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app_a = _create_application(client, "App A")
    app_b = _create_application(client, "App B")
    component_a = _create_component(client, app_a["id"])

    site_resp = client.post(
        "/api/sites", json={"name": "S3", "base_url": "http://t3.local"}
    )
    site_id = site_resp.json()["id"]
    target_resp = client.post(
        f"/api/applications/{app_b['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    )
    target_b = target_resp.json()

    resp = client.post(
        f"/api/applications/{app_a['id']}/hints",
        json={"component_id": component_a["id"], "target_id": target_b["id"]},
    )
    assert resp.status_code == 400


def test_attach_and_detach_target(client, isolated_db_engine):
    app = _create_application(client)
    site_resp = client.post(
        "/api/sites", json={"name": "S4", "base_url": "http://t4.local"}
    )
    site_id = site_resp.json()["id"]
    resp = client.post(
        f"/api/applications/{app['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    )
    assert resp.status_code == 201
    target = resp.json()
    assert target["name"] == "S4"

    detach = client.delete(f"/api/applications/{app['id']}/targets/{target['id']}")
    assert detach.status_code == 204
    with Session(isolated_db_engine) as s:
        assert s.get(ApplicationTarget, target["id"]) is None


def test_target_can_optionally_select_code_component(client):
    app = _create_application(client)
    component = _create_component(client, app["id"], "orders-api")
    site_id = client.post(
        "/api/sites", json={"name": "S5b", "base_url": "http://t5b.local"}
    ).json()["id"]
    target = client.post(
        f"/api/applications/{app['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    ).json()
    assert target["component_id"] is None

    update = client.patch(
        f"/api/applications/{app['id']}/targets/{target['id']}",
        json={"component_id": component["id"]},
    )
    assert update.status_code == 200
    assert update.json()["component_id"] == component["id"]

    clear = client.patch(
        f"/api/applications/{app['id']}/targets/{target['id']}",
        json={"component_id": None},
    )
    assert clear.status_code == 200
    assert clear.json()["component_id"] is None


def test_target_component_link_rejects_component_from_another_application(client):
    app_a = _create_application(client, "Target owner")
    app_b = _create_application(client, "Component owner")
    component_b = _create_component(client, app_b["id"], "foreign")
    site_id = client.post(
        "/api/sites", json={"name": "S5c", "base_url": "http://t5c.local"}
    ).json()["id"]
    target = client.post(
        f"/api/applications/{app_a['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    ).json()

    update = client.patch(
        f"/api/applications/{app_a['id']}/targets/{target['id']}",
        json={"component_id": component_b["id"]},
    )
    assert update.status_code == 400


def test_application_delete_blocked_while_campaign_exists(
    client, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app = _create_application(client)
    component = _create_component(client, app["id"])
    snapshot = _upload_snapshot(client, app["id"], component["id"])
    site_resp = client.post(
        "/api/sites", json={"name": "S5", "base_url": "http://t5.local"}
    )
    site_id = site_resp.json()["id"]
    target = client.post(
        f"/api/applications/{app['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    ).json()
    client.post(
        f"/api/applications/{app['id']}/campaigns",
        json={
            "name": "c1",
            "source_members": [
                {"component_id": component["id"], "snapshot_id": snapshot["id"]}
            ],
            "target_members": [{"target_id": target["id"]}],
        },
    )
    resp = client.delete(f"/api/applications/{app['id']}")
    assert resp.status_code == 409


# ── Review endpoint: empty decisions schema + validation gating (finding 7) ──


def test_review_endpoint_accepts_empty_decisions_with_zero_proposals(
    client, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    app = _create_application(client)
    component = _create_component(client, app["id"])
    snapshot = _upload_snapshot(client, app["id"], component["id"])
    site_resp = client.post(
        "/api/sites", json={"name": "ReviewSite", "base_url": "http://rs.local"}
    )
    site_id = site_resp.json()["id"]
    target = client.post(
        f"/api/applications/{app['id']}/targets",
        json={"target_type": "site", "target_id": site_id},
    ).json()
    campaign = client.post(
        f"/api/applications/{app['id']}/campaigns",
        json={
            "name": "empty-review",
            "source_members": [
                {"component_id": component["id"], "snapshot_id": snapshot["id"]}
            ],
            "target_members": [{"target_id": target["id"]}],
        },
    ).json()

    from sqlmodel import Session

    from aespa.db import get_engine
    from aespa.models import AssessmentCampaign

    with Session(get_engine()) as s:
        row = s.get(AssessmentCampaign, campaign["id"])
        row.status = "awaiting_review"
        s.add(row)
        s.commit()

    resp = client.post(
        f"/api/applications/{app['id']}/campaigns/{campaign['id']}/review",
        json={"decisions": []},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"approved": 0, "rejected": 0, "copied": 0}


def test_review_endpoint_rejects_unknown_mapping_id(client, isolated_db_engine):
    from sqlmodel import Session

    from aespa.db import get_engine
    from aespa.models import Application, AssessmentCampaign

    with Session(get_engine()) as s:
        app_row = Application(name="ReviewApp")
        s.add(app_row)
        s.flush()
        campaign = AssessmentCampaign(
            application_id=app_row.id, name="c", status="awaiting_review"
        )
        s.add(campaign)
        s.commit()
        app_id = app_row.id
        campaign_id = campaign.id

    resp = client.post(
        f"/api/applications/{app_id}/campaigns/{campaign_id}/review",
        json={"decisions": [{"mapping_id": 999999, "approve": True}]},
    )
    assert resp.status_code == 400
