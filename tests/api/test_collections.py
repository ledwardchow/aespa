from __future__ import annotations

import json
import types

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine, select

from aespa import db
from aespa import models as _models  # noqa: F401
from aespa.models import (
    AgentLog,
    AliceChatMessage,
    AliceChatSession,
    ApiCollection,
    ApiCredential,
    ApiDocument,
    ApiEndpoint,
    ApiEndpointTest,
    ApiTestRun,
    SastRun,
    ScanFinding,
    ScanLead,
    ScanLog,
    TrafficEntry,
)
from aespa.services import api_collections as svc


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Isolate uploaded-file storage to a temp dir for the test."""
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    return tmp_path


# ---- helpers ----------------------------------------------------------------


def make_collection(client: TestClient, **kwargs):
    defaults = {
        "name": "Payments API",
        "base_url": "https://api.example.com",
    }
    return client.post("/api/api-collections", json={**defaults, **kwargs})


# ---- create -----------------------------------------------------------------


def test_create_collection(client):
    r = make_collection(client)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Payments API"
    assert data["base_url"] == "https://api.example.com/"
    assert data["description"] is None
    assert data["servers"] == []
    assert data["scope_hosts"] == []


def test_create_collection_with_optional_fields(client):
    r = make_collection(
        client,
        name="Orders API",
        description="Order management endpoints",
        servers=["https://eu.api.example.com"],
        scope_hosts=["api.example.com"],
    )
    assert r.status_code == 201
    data = r.json()
    assert data["description"] == "Order management endpoints"
    assert data["servers"] == ["https://eu.api.example.com"]
    assert data["scope_hosts"] == ["api.example.com:443"]


def test_create_collection_duplicate_name_conflicts(client):
    assert make_collection(client).status_code == 201
    r = make_collection(client)
    assert r.status_code == 409


def test_create_collection_requires_valid_url(client):
    r = make_collection(client, base_url="not-a-url")
    assert r.status_code == 422


# ---- list / get -------------------------------------------------------------


def test_list_collections(client):
    make_collection(client, name="A")
    make_collection(client, name="B")
    r = client.get("/api/api-collections")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert names == ["A", "B"]
    assert all(c["endpoint_count"] == 0 for c in r.json())
    assert all(c["document_count"] == 0 for c in r.json())


def test_get_collection(client):
    cid = make_collection(client).json()["id"]
    r = client.get(f"/api/api-collections/{cid}")
    assert r.status_code == 200
    assert r.json()["id"] == cid


def test_get_missing_collection_404(client):
    r = client.get("/api/api-collections/999")
    assert r.status_code == 404


# ---- update -----------------------------------------------------------------


def test_update_collection(client):
    cid = make_collection(client).json()["id"]
    r = client.put(
        f"/api/api-collections/{cid}",
        json={
            "name": "Renamed API",
            "base_url": "https://v2.api.example.com",
            "description": "Updated",
            "scope_hosts": ["v2.api.example.com"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Renamed API"
    assert data["base_url"] == "https://v2.api.example.com/"
    assert data["description"] == "Updated"
    assert data["scope_hosts"] == ["v2.api.example.com:443"]


def test_update_duplicate_name_conflicts(client):
    make_collection(client, name="First")
    second = make_collection(client, name="Second").json()
    r = client.put(
        f"/api/api-collections/{second['id']}",
        json={"name": "First", "base_url": "https://api.example.com"},
    )
    assert r.status_code == 409


def test_update_missing_collection_404(client):
    r = client.put(
        "/api/api-collections/999",
        json={"name": "X", "base_url": "https://api.example.com"},
    )
    assert r.status_code == 404


# ---- scope hosts ------------------------------------------------------------


def test_update_scope_hosts(client):
    cid = make_collection(client).json()["id"]
    r = client.put(
        f"/api/api-collections/{cid}/scope-hosts",
        json={"scope_hosts": ["api.example.com", "eu.api.example.com"]},
    )
    assert r.status_code == 200
    assert r.json()["scope_hosts"] == [
        "api.example.com:443",
        "eu.api.example.com:443",
    ]
    detail = client.get(f"/api/api-collections/{cid}").json()
    assert detail["scope_hosts"] == [
        "api.example.com:443",
        "eu.api.example.com:443",
    ]


# ---- delete -----------------------------------------------------------------


def test_delete_collection(client):
    cid = make_collection(client).json()["id"]
    assert client.delete(f"/api/api-collections/{cid}").status_code == 204
    assert client.get(f"/api/api-collections/{cid}").status_code == 404


def test_delete_missing_collection_404(client):
    assert client.delete("/api/api-collections/999").status_code == 404


# ---- documents --------------------------------------------------------------


def test_list_documents_empty(client, data_dir):
    cid = make_collection(client).json()["id"]
    r = client.get(f"/api/api-collections/{cid}/documents")
    assert r.status_code == 200
    assert r.json() == []


def test_list_documents_missing_collection_404(client, data_dir):
    r = client.get("/api/api-collections/999/documents")
    assert r.status_code == 404


def test_upload_and_list_documents(client, data_dir):
    cid = make_collection(client).json()["id"]
    r = client.post(
        f"/api/api-collections/{cid}/documents",
        files=[
            (
                "files",
                ("spec.yaml", b"openapi: 3.0.0\npaths: {}\n", "application/yaml"),
            ),
            ("files", ("notes.txt", b"GET /widgets returns widgets", "text/plain")),
        ],
    )
    assert r.status_code == 201
    created = r.json()
    assert len(created) == 2
    assert created[0]["filename"] == "spec.yaml"
    assert created[0]["doc_type"] == "openapi"
    assert created[0]["status"] == "uploaded"  # parse no longer runs inline on upload
    assert created[0]["size_bytes"] > 0
    assert created[1]["doc_type"] == "freetext"

    listed = client.get(f"/api/api-collections/{cid}/documents").json()
    assert len(listed) == 2

    # document_count reflected in the collection summary
    summary = next(
        c for c in client.get("/api/api-collections").json() if c["id"] == cid
    )
    assert summary["document_count"] == 2


def test_upload_sniffs_zip(client, data_dir):
    cid = make_collection(client).json()["id"]
    # Minimal zip magic bytes.
    r = client.post(
        f"/api/api-collections/{cid}/documents",
        files=[("files", ("src.zip", b"PK\x03\x04rest-of-zip", "application/zip"))],
    )
    assert r.status_code == 201
    assert r.json()[0]["doc_type"] == "source_zip"


def test_upload_rejects_empty_file(client, data_dir):
    cid = make_collection(client).json()["id"]
    r = client.post(
        f"/api/api-collections/{cid}/documents",
        files=[("files", ("empty.txt", b"", "text/plain"))],
    )
    assert r.status_code == 400


def test_upload_missing_collection_404(client, data_dir):
    r = client.post(
        "/api/api-collections/999/documents",
        files=[("files", ("spec.yaml", b"openapi: 3.0.0", "application/yaml"))],
    )
    assert r.status_code == 404


def test_download_document_returns_original_bytes(client, data_dir):
    cid = make_collection(client).json()["id"]
    payload = b"openapi: 3.0.0\npaths:\n  /ping: {}\n"
    doc = client.post(
        f"/api/api-collections/{cid}/documents",
        files=[("files", ("spec.yaml", payload, "application/yaml"))],
    ).json()[0]
    r = client.get(f"/api/api-collections/{cid}/documents/{doc['id']}/download")
    assert r.status_code == 200
    assert r.content == payload
    assert "spec.yaml" in r.headers["content-disposition"]


def test_download_missing_document_404(client, data_dir):
    cid = make_collection(client).json()["id"]
    r = client.get(f"/api/api-collections/{cid}/documents/999/download")
    assert r.status_code == 404


def test_delete_document(client, data_dir):
    cid = make_collection(client).json()["id"]
    doc = client.post(
        f"/api/api-collections/{cid}/documents",
        files=[("files", ("spec.yaml", b"openapi: 3.0.0", "application/yaml"))],
    ).json()[0]
    assert (
        client.delete(f"/api/api-collections/{cid}/documents/{doc['id']}").status_code
        == 204
    )
    assert client.get(f"/api/api-collections/{cid}/documents").json() == []
    # File removed from disk too.
    assert list((data_dir / "api_collections" / str(cid)).glob("*")) == []


def test_uploaded_file_stored_with_generated_name(client, data_dir):
    """User-supplied filename must not be used to build the on-disk path."""
    cid = make_collection(client).json()["id"]
    client.post(
        f"/api/api-collections/{cid}/documents",
        files=[("files", ("../../evil.yaml", b"openapi: 3.0.0", "application/yaml"))],
    )
    stored = list((data_dir / "api_collections" / str(cid)).glob("*"))
    assert len(stored) == 1
    # Stored name is a generated uuid + extension, not the traversal path.
    assert stored[0].name != "evil.yaml"
    assert ".." not in stored[0].name
    assert stored[0].suffix == ".yaml"


# ---- migration --------------------------------------------------------------


def test_migrate_creates_api_collection_table_on_old_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)

        # Simulate an old DB that predates the api_collection/api_document tables.
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE api_collection"))
            conn.execute(text("DROP TABLE api_document"))
            conn.commit()
            tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            assert "api_collection" not in tables
            assert "api_document" not in tables

        db._migrate(engine)

        with engine.connect() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            assert "api_collection" in tables
            assert "api_document" in tables
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(api_collection)"))
            }
            doc_columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(api_document)"))
            }
        assert {
            "id",
            "name",
            "base_url",
            "description",
            "servers",
            "scope_hosts",
        } <= columns
        assert {
            "id",
            "collection_id",
            "filename",
            "doc_type",
            "stored_path",
            "size_bytes",
            "status",
        } <= doc_columns
    finally:
        engine.dispose()


# --- Merged from test_api_collections_export_import.py ---
@pytest.fixture
def session(db_session):
    return db_session


def test_roundtrip(session, tmp_path, monkeypatch):
    # Redirect document storage to a temp dir for both the source file and import.
    monkeypatch.setattr(
        "aespa.services.api_documents.get_settings",
        lambda: types.SimpleNamespace(data_dir=tmp_path),
    )

    col = ApiCollection(name="petstore", base_url="http://api.test")
    session.add(col)
    session.flush()

    doc_path = tmp_path / "spec.json"
    doc_path.write_bytes(b'{"openapi":"3.0.0"}')
    doc = ApiDocument(
        collection_id=col.id,
        filename="spec.json",
        doc_type="openapi",
        stored_path=str(doc_path),
        size_bytes=doc_path.stat().st_size,
        status="parsed",
    )
    session.add(doc)
    session.flush()

    ep = ApiEndpoint(
        collection_id=col.id, source_doc_id=doc.id, method="GET", path="/pets/{id}"
    )
    session.add(ep)
    session.flush()
    # Credential scoped to the endpoint — endpoint_id must remap.
    session.add(
        ApiCredential(
            collection_id=col.id,
            scheme="bearer",
            name="Authorization",
            value="tok",
            scope="endpoint",
            endpoint_id=ep.id,
        )
    )

    run = ApiTestRun(
        collection_id=col.id, name="run-1", status="completed", sast_run_id=42
    )
    session.add(run)
    session.flush()
    finding = ScanFinding(
        api_test_run_id=run.id,
        owasp_category="API1",
        owasp_api_category="API1",
        severity="high",
        title="BOLA",
        description="x",
    )
    session.add(finding)
    session.flush()
    # API traffic has no web-run owner.
    session.add(
        TrafficEntry(
            test_run_id=0,
            api_test_run_id=run.id,
            source="httpx",
            method="GET",
            url="http://api.test/pets/1",
        )
    )
    # Cell references both endpoint and finding; 99999 is a stale finding id to drop.
    session.add(
        ApiEndpointTest(
            api_test_run_id=run.id,
            endpoint_id=ep.id,
            owasp_api_category="API1",
            status="finding",
            finding_ids_json=json.dumps([finding.id, 99999]),
        )
    )
    session.add(
        AgentLog(
            test_run_id=run.id,
            run_kind="api",
            agent_id="lead",
            role="test_lead",
            status="active",
        )
    )
    alice = AliceChatSession(test_run_id=run.id, run_kind="api", session_key="tab-1")
    session.add(alice)
    session.flush()
    session.add(
        AliceChatMessage(
            session_id=alice.id, message_key="m1", sender="user", text="hi"
        )
    )

    # SAST run that produced a lead; the api run back-references it via sast_run_id.
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04zipbytes")
    zip_doc = ApiDocument(
        collection_id=col.id,
        filename="src.zip",
        doc_type="source_zip",
        stored_path=str(zip_path),
        size_bytes=zip_path.stat().st_size,
        status="parsed",
    )
    session.add(zip_doc)
    session.flush()
    sast = SastRun(
        collection_id=col.id,
        document_id=zip_doc.id,
        name="sast-1",
        status="completed",
        triggered_by_run_type="api",
        triggered_by_run_id=run.id,
    )
    session.add(sast)
    session.flush()
    run.sast_run_id = sast.id
    session.add(run)
    session.add(
        ScanLog(
            test_run_id=sast.id,
            run_kind="sast",
            phase="thinking_step",
            message="sast scanning",
        )
    )
    session.add(
        AgentLog(
            test_run_id=sast.id,
            run_kind="sast",
            agent_id="sast",
            role="sast",
            status="done",
        )
    )
    lead = ScanLead(
        collection_id=col.id,
        producer_run_id=sast.id,
        category="API1",
        severity="high",
        title="hardcoded secret",
        evidence="api_key = 'xxx'  # config.py:10",
        investigated_by_run_type="api",
        investigated_by_run_id=run.id,
        linked_finding_id=finding.id,
    )
    session.add(lead)
    session.commit()

    bundle = svc.export_collection(session, col.id)
    # source_zip bytes are intentionally dropped from the bundle.
    zip_entry = next(d for d in bundle["documents"] if d["doc_type"] == "source_zip")
    assert zip_entry["content_b64"] is None
    new_col = svc.import_collection(session, bundle)
    assert new_col.id != col.id

    new_run = session.exec(
        select(ApiTestRun).where(ApiTestRun.collection_id == new_col.id)
    ).one()
    assert new_run.llm_config_id is None  # cannot map across installations

    new_ep = session.exec(
        select(ApiEndpoint).where(ApiEndpoint.collection_id == new_col.id)
    ).one()
    new_doc = session.exec(
        select(ApiDocument)
        .where(ApiDocument.collection_id == new_col.id)
        .where(ApiDocument.doc_type == "openapi")
    ).one()
    assert new_ep.source_doc_id == new_doc.id
    # Document bytes survived and live at a fresh path.
    from pathlib import Path

    assert new_doc.stored_path != str(doc_path)
    assert Path(new_doc.stored_path).read_bytes() == b'{"openapi":"3.0.0"}'

    new_cred = session.exec(
        select(ApiCredential).where(ApiCredential.collection_id == new_col.id)
    ).one()
    assert new_cred.endpoint_id == new_ep.id

    new_finding = session.exec(
        select(ScanFinding).where(ScanFinding.api_test_run_id == new_run.id)
    ).one()
    assert new_finding.test_run_id is None  # never leaks into the web id-space
    cell = session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == new_run.id)
    ).one()
    assert cell.endpoint_id == new_ep.id
    assert json.loads(cell.finding_ids_json) == [new_finding.id]  # stale 99999 dropped

    new_traffic = session.exec(
        select(TrafficEntry).where(TrafficEntry.api_test_run_id == new_run.id)
    ).one()
    assert new_traffic.test_run_id is None

    assert (
        len(
            session.exec(
                select(AgentLog)
                .where(AgentLog.test_run_id == new_run.id)
                .where(AgentLog.run_kind == "api")
            ).all()
        )
        == 1
    )
    new_alice = session.exec(
        select(AliceChatSession).where(AliceChatSession.test_run_id == new_run.id)
    ).one()
    msgs = session.exec(
        select(AliceChatMessage).where(AliceChatMessage.session_id == new_alice.id)
    ).all()
    assert len(msgs) == 1 and msgs[0].text == "hi"

    # SAST run + lead survived with every cross-reference remapped.
    new_sast = session.exec(
        select(SastRun).where(SastRun.collection_id == new_col.id)
    ).one()
    assert new_sast.triggered_by_run_id == new_run.id
    new_zip = session.exec(
        select(ApiDocument)
        .where(ApiDocument.doc_type == "source_zip")
        .where(ApiDocument.collection_id == new_col.id)
    ).one()
    assert new_sast.document_id == new_zip.id
    assert new_zip.stored_path == ""  # bytes were dropped → no file written
    assert new_run.sast_run_id == new_sast.id  # back-patched
    # SAST logs travel too, re-keyed onto the new SAST run id.
    assert (
        len(
            session.exec(
                select(ScanLog)
                .where(ScanLog.test_run_id == new_sast.id)
                .where(ScanLog.run_kind == "sast")
            ).all()
        )
        == 1
    )
    assert (
        len(
            session.exec(
                select(AgentLog)
                .where(AgentLog.test_run_id == new_sast.id)
                .where(AgentLog.run_kind == "sast")
            ).all()
        )
        == 1
    )

    new_lead = session.exec(
        select(ScanLead).where(ScanLead.collection_id == new_col.id)
    ).one()
    assert new_lead.producer_run_id == new_sast.id
    assert new_lead.investigated_by_run_id == new_run.id
    assert new_lead.linked_finding_id == new_finding.id
    assert new_lead.evidence == "api_key = 'xxx'  # config.py:10"


def test_rejects_non_api_bundle(session):
    with pytest.raises(svc.ApiCollectionServiceError):
        svc.import_collection(session, {"export_version": 1, "kind": "site"})
