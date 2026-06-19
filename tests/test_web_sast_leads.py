"""Integration tests for SAST on web scans.

Covers the standalone SAST upload endpoint and the web-run lead-import flow
(available SAST runs → import a copy → list imported leads). Also guards that
the API-style SAST run shape (collection_id + document_id) still constructs.
"""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa import db as db_mod
from aespa.db import get_session, set_engine
from aespa.main import create_app
from aespa.models import SastRun, ScanLead, Site
from aespa.models import TestRun as WebTestRun

_UTC = timezone.utc


@pytest.fixture(name="env")
def env_fixture():
    """Engine wired into both the get_session dependency and get_engine()."""
    prev_engine = db_mod._engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    set_engine(engine)  # service layer uses get_engine() directly

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, engine

    set_engine(prev_engine)
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("app.py", "def handler(req):\n    return db.query(req['id'])\n")
    return buf.getvalue()


def _make_completed_sast_run_with_leads(engine, n=2) -> int:
    with Session(engine) as s:
        run = SastRun(
            collection_id=None,
            name="standalone",
            source_filename="src.zip",
            status="completed",
            leads_count=n,
            completed_at=datetime.now(_UTC),
        )
        s.add(run)
        s.commit()
        s.refresh(run)
        for i in range(n):
            s.add(ScanLead(
                producer_run_id=run.id,
                producer_run_type="sast",
                collection_id=None,
                title=f"Lead {i}",
                category="A03",
                severity="high",
                confidence=0.9,
                status="open",
            ))
        s.commit()
        return run.id


def _make_web_run(engine) -> int:
    with Session(engine) as s:
        site = Site(name="S", base_url="http://t.local")
        s.add(site)
        s.commit()
        s.refresh(site)
        run = WebTestRun(site_id=site.id, name="web run")
        s.add(run)
        s.commit()
        s.refresh(run)
        return run.id


def test_standalone_sast_upload_creates_collectionless_run(env, tmp_path, monkeypatch):
    client, engine = env
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))

    resp = client.post(
        "/api/sast-runs",
        files={"file": ("mysrc.zip", _zip_bytes(), "application/zip")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["collection_id"] is None
    assert body["source_filename"] == "mysrc.zip"

    with Session(engine) as s:
        run = s.get(SastRun, body["id"])
    assert run.collection_id is None
    assert run.source_archive_path  # archive was stored
    assert run.status == "pending"


def test_standalone_sast_upload_rejects_non_zip(env, tmp_path, monkeypatch):
    client, _ = env
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    resp = client.post(
        "/api/sast-runs",
        files={"file": ("notes.txt", b"not a zip", "text/plain")},
    )
    assert resp.status_code == 400


def test_web_run_import_leads_flow(env):
    client, engine = env
    sast_run_id = _make_completed_sast_run_with_leads(engine, n=2)
    web_run_id = _make_web_run(engine)

    # The completed SAST run shows up as available.
    avail = client.get(f"/api/test-runs/{web_run_id}/sast-runs/available").json()
    assert any(r["id"] == sast_run_id and r["leads_count"] == 2 for r in avail)

    # Import copies the leads in.
    r = client.post(
        f"/api/test-runs/{web_run_id}/import-leads",
        json={"sast_run_id": sast_run_id},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 2

    # The web run now lists 2 imported leads, owned by the run.
    leads = client.get(f"/api/test-runs/{web_run_id}/leads").json()
    assert len(leads) == 2
    for ld in leads:
        assert ld["imported_into_run_type"] == "web"
        assert ld["imported_into_run_id"] == web_run_id

    # The SAST run's own leads endpoint still shows only the 2 originals.
    originals = client.get(f"/api/sast-runs/{sast_run_id}/leads").json()
    assert len(originals) == 2
    assert all(o["imported_into_run_id"] is None for o in originals)

    # Re-import is idempotent.
    r2 = client.post(
        f"/api/test-runs/{web_run_id}/import-leads",
        json={"sast_run_id": sast_run_id},
    )
    assert r2.json()["imported"] == 0


def test_clear_and_delete_imported_leads(env):
    client, engine = env
    sast_run_id = _make_completed_sast_run_with_leads(engine, n=3)
    web_run_id = _make_web_run(engine)
    client.post(
        f"/api/test-runs/{web_run_id}/import-leads",
        json={"sast_run_id": sast_run_id},
    )
    leads = client.get(f"/api/test-runs/{web_run_id}/leads").json()
    assert len(leads) == 3

    # Delete a single row.
    r = client.delete(f"/api/test-runs/{web_run_id}/leads/{leads[0]['id']}")
    assert r.status_code == 204
    assert len(client.get(f"/api/test-runs/{web_run_id}/leads").json()) == 2

    # Deleting an original (not owned by this run) via the web endpoint is rejected.
    original_id = client.get(f"/api/sast-runs/{sast_run_id}/leads").json()[0]["id"]
    r = client.delete(f"/api/test-runs/{web_run_id}/leads/{original_id}")
    assert r.status_code == 404

    # Clear all removes the rest; originals on the SAST run survive.
    r = client.delete(f"/api/test-runs/{web_run_id}/leads")
    assert r.status_code == 204
    assert client.get(f"/api/test-runs/{web_run_id}/leads").json() == []
    assert len(client.get(f"/api/sast-runs/{sast_run_id}/leads").json()) == 3


def test_import_leads_unknown_sast_run_404(env):
    client, engine = env
    web_run_id = _make_web_run(engine)
    r = client.post(
        f"/api/test-runs/{web_run_id}/import-leads",
        json={"sast_run_id": 9999},
    )
    assert r.status_code == 404


def test_api_style_sast_run_still_constructs(env):
    """Regression: the API SAST shape (collection_id + document_id) is unaffected."""
    client, engine = env
    from aespa.services import sast_scanner
    run = sast_scanner.create_sast_run(
        collection_id=1,
        name="SAST for API run #1",
        document_id=5,
        triggered_by_run_type="api",
        triggered_by_run_id=1,
    )
    with Session(engine) as s:
        loaded = s.get(SastRun, run.id)
    assert loaded.collection_id == 1
    assert loaded.document_id == 5
    assert loaded.triggered_by_run_type == "api"
