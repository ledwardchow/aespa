from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

import pytest

from aespa import db


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
    assert data["scope_hosts"] == ["api.example.com"]


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
    assert data["scope_hosts"] == ["v2.api.example.com"]


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
    assert r.json()["scope_hosts"] == ["api.example.com", "eu.api.example.com"]
    detail = client.get(f"/api/api-collections/{cid}").json()
    assert detail["scope_hosts"] == ["api.example.com", "eu.api.example.com"]


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
            ("files", ("spec.yaml", b"openapi: 3.0.0\npaths: {}\n", "application/yaml")),
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
    summary = next(c for c in client.get("/api/api-collections").json() if c["id"] == cid)
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
    assert client.delete(f"/api/api-collections/{cid}/documents/{doc['id']}").status_code == 204
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
                row[1]
                for row in conn.execute(text("PRAGMA table_info(api_document)"))
            }
        assert {"id", "name", "base_url", "description", "servers", "scope_hosts"} <= columns
        assert {"id", "collection_id", "filename", "doc_type", "stored_path",
                "size_bytes", "status"} <= doc_columns
    finally:
        engine.dispose()
