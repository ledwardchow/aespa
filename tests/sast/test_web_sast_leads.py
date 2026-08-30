"""Integration tests for SAST on web scans.

Covers the standalone SAST upload endpoint and the web-run lead-import flow
(available SAST runs → import a copy → list imported leads). Also guards that
the API-style SAST run shape (collection_id + document_id) still constructs.
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa import db as db_mod
from aespa.db import get_session, set_engine
from aespa.main import create_app
from aespa.models import AgentLog, ComponentFact, SastRun, ScanLead, ScanLog, Site
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
            s.add(
                ScanLead(
                    producer_run_id=run.id,
                    producer_run_type="sast",
                    collection_id=None,
                    title=f"Lead {i}",
                    category="A03",
                    severity="high",
                    confidence=0.9,
                    status="open",
                )
            )
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


def test_sast_run_export_import_round_trip_preserves_run_state_and_archive(
    env, tmp_path, monkeypatch
):
    client, engine = env
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive_bytes = _zip_bytes()
    archive_path = tmp_path / "source.zip"
    archive_path.write_bytes(archive_bytes)

    with Session(engine) as session:
        original = SastRun(
            name="Complete source review",
            source_filename="source.zip",
            source_archive_path=str(archive_path),
            status="completed",
            leads_count=1,
            phase_state_json=json.dumps(
                {"scope": {"status": "complete", "message": "1 file reviewed"}}
            ),
            coverage_json=json.dumps(
                {
                    "files": [{"path": "app.py", "reviewed": True}],
                    "summary": {"files_total": 1},
                }
            ),
            report_json=json.dumps({"reportable": 1, "confirmed": 1}),
            token_usage_json=json.dumps({"input_tokens": 12, "output_tokens": 34}),
        )
        session.add(original)
        session.commit()
        session.refresh(original)
        session.add(
            ScanLead(
                producer_run_type="sast",
                producer_run_id=original.id,
                title="SQL injection candidate",
                description="A request value reaches a query builder.",
                category="A03",
                severity="high",
                confidence=0.91,
                location="app.py:10",
                evidence="request.id -> query()",
                fingerprint="lead-fingerprint",
                validation_status="confirmed",
                validation_reasoning="The source and sink were independently confirmed.",
                reportable=True,
                public_reference="TEST-001",
            )
        )
        session.add(
            ScanLog(
                test_run_id=original.id,
                run_kind="sast",
                phase="report",
                status="complete",
                message="Report finished",
                data_json='{"confirmed": 1}',
            )
        )
        session.add(
            AgentLog(
                test_run_id=original.id,
                run_kind="sast",
                agent_id="sast",
                role="SAST",
                status="complete",
                current_task="Review source",
                outcome="Finished",
            )
        )
        session.add(
            ComponentFact(
                sast_run_id=original.id,
                fact_type="route",
                method="GET",
                path="/users/{id}",
                evidence_location="app.py:2",
                fingerprint="fact-fingerprint",
            )
        )
        session.commit()
        original_id = original.id

    exported = client.get(f"/api/sast-runs/{original_id}/export")
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-disposition"].endswith(
        '"Complete_source_review.aespa-sast.json"'
    )
    bundle = exported.json()
    assert bundle["kind"] == "sast-run"
    assert base64.b64decode(bundle["source_archive"]["content_b64"]) == archive_bytes
    assert len(bundle["scan_leads"]) == 1
    assert len(bundle["scan_logs"]) == 1
    assert len(bundle["agent_logs"]) == 1
    assert len(bundle["component_facts"]) == 1

    imported = client.post(
        "/api/sast-runs/import",
        content=json.dumps(bundle),
        headers={"Content-Type": "application/json"},
    )
    assert imported.status_code == 201, imported.text
    imported_id = imported.json()["id"]
    assert imported_id != original_id
    assert imported.json()["name"] == "Complete source review"
    assert imported.json()["status"] == "completed"

    with Session(engine) as session:
        restored = session.get(SastRun, imported_id)
        assert restored is not None
        assert restored.collection_id is None
        assert restored.document_id is None
        assert restored.phase_state_json == bundle["sast_run"]["phase_state_json"]
        assert restored.coverage_json == bundle["sast_run"]["coverage_json"]
        assert restored.report_json == bundle["sast_run"]["report_json"]
        assert restored.token_usage_json == bundle["sast_run"]["token_usage_json"]
        assert restored.source_archive_path is not None
        assert Path(restored.source_archive_path).read_bytes() == archive_bytes

        leads = session.exec(
            select(ScanLead).where(
                ScanLead.producer_run_type == "sast",
                ScanLead.producer_run_id == imported_id,
            )
        ).all()
        assert len(leads) == 1
        assert leads[0].title == "SQL injection candidate"
        assert leads[0].validation_status == "confirmed"
        assert leads[0].public_reference == "TEST-001"
        assert (
            len(
                session.exec(
                    select(ScanLog).where(
                        ScanLog.test_run_id == imported_id,
                        ScanLog.run_kind == "sast",
                    )
                ).all()
            )
            == 1
        )
        assert (
            len(
                session.exec(
                    select(AgentLog).where(
                        AgentLog.test_run_id == imported_id,
                        AgentLog.run_kind == "sast",
                    )
                ).all()
            )
            == 1
        )
        facts = session.exec(
            select(ComponentFact).where(ComponentFact.sast_run_id == imported_id)
        ).all()
        assert len(facts) == 1
        assert facts[0].path == "/users/{id}"


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


def test_jail_rejects_sibling_dir_with_shared_prefix(tmp_path):
    """The path jail must not treat a sibling whose name shares a prefix (…/5x)
    as living inside the run root (…/5) — a string-prefix check would."""
    from aespa.services.sast_scanner import _jail

    root = tmp_path / "5"
    root.mkdir()
    (tmp_path / "5x").mkdir()  # sibling sharing the "5" prefix
    (tmp_path / "5x" / "secret.txt").write_text("nope")

    # Inside the jail is fine.
    assert _jail(root, "ok.txt") == (root / "ok.txt")
    # Escaping into the prefixed sibling is rejected.
    with pytest.raises(ValueError):
        _jail(root, "../5x/secret.txt")
    with pytest.raises(ValueError):
        _jail(root, "../../etc/passwd")


def test_safe_unzip_skips_prefixed_sibling_escape(tmp_path):
    """A crafted entry resolving to a prefixed sibling must not be extracted."""
    from aespa.services.sast_scanner import _safe_unzip

    target = tmp_path / "5"
    target.mkdir()
    (tmp_path / "5x").mkdir()

    archive = tmp_path / "src.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("good.py", "print(1)")
        zf.writestr("../5x/evil.py", "pwned")

    _safe_unzip(str(archive), str(target))

    assert (target / "good.py").exists()
    assert not (tmp_path / "5x" / "evil.py").exists()  # escape blocked


def test_safe_unzip_rejects_oversized_entry(tmp_path, monkeypatch):
    from aespa.services import sast_scanner

    target = tmp_path / "extract"
    target.mkdir()
    archive = tmp_path / "src.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("large.py", "123456")

    monkeypatch.setattr(sast_scanner, "_MAX_ARCHIVE_ENTRY_BYTES", 5)
    with pytest.raises(ValueError, match="exceeds"):
        sast_scanner._safe_unzip(str(archive), str(target))


def test_standalone_sast_upload_streams_and_enforces_limit(env, tmp_path, monkeypatch):
    client, _ = env
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    from aespa.api import sast_runs as sast_api

    assert sast_api._MAX_UPLOAD_BYTES == 250 * 1024 * 1024
    monkeypatch.setattr(sast_api, "_MAX_UPLOAD_BYTES", 4)
    resp = client.post(
        "/api/sast-runs",
        files={"file": ("src.zip", b"12345", "application/zip")},
    )
    assert resp.status_code == 400
    assert "upload limit" in resp.text
