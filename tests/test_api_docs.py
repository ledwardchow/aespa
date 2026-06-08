"""Tests for Slice 3: document parsing → ApiEndpoint / ApiCredential rows."""
from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from aespa.db import get_session
from aespa.main import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def client(data_dir):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401
    SQLModel.metadata.create_all(engine)

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def _make_collection(client: TestClient, name: str = "Test API") -> int:
    r = client.post(
        "/api/api-collections",
        json={"name": name, "base_url": "https://api.example.com"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _upload(client: TestClient, cid: int, filename: str, content: bytes, content_type: str = "application/octet-stream") -> dict:
    r = client.post(
        f"/api/api-collections/{cid}/documents",
        files={"files": (filename, io.BytesIO(content), content_type)},
    )
    assert r.status_code == 201, r.text
    return r.json()[0]


# ── Unit tests for parsers (no DB, direct service calls) ─────────────────────

OPENAPI_YAML = b"""
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0"
servers:
  - url: https://api.example.com/v1
paths:
  /users:
    get:
      operationId: listUsers
      summary: List users
      tags: [users]
      security: []
      responses:
        "200":
          description: ok
    post:
      operationId: createUser
      summary: Create a user
      tags: [users]
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
            example:
              username: alice
      responses:
        "201":
          description: created
  /users/{id}:
    get:
      operationId: getUser
      summary: Get user by id
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      security:
        - BearerAuth: []
      responses:
        "200":
          description: ok
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""

SWAGGER_JSON = json.dumps({
    "swagger": "2.0",
    "info": {"title": "Petstore", "version": "1.0"},
    "host": "petstore.example.com",
    "basePath": "/v2",
    "schemes": ["https"],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List pets",
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}).encode()

POSTMAN_V21 = json.dumps({
    "info": {"name": "Widgets API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "variable": [{"key": "baseUrl", "value": "https://widgets.example.com"}],
    "auth": {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "super-secret-tok", "type": "string"}],
    },
    "item": [
        {
            "name": "Get widget",
            "request": {
                "method": "GET",
                "url": {"raw": "{{baseUrl}}/widgets/{{id}}", "host": ["{{baseUrl}}"], "path": ["widgets", "{{id}}"]},
                "auth": {"type": "noauth"},
            },
        },
        {
            "name": "Create widget",
            "request": {
                "method": "POST",
                "url": {"raw": "{{baseUrl}}/widgets", "host": ["{{baseUrl}}"], "path": ["widgets"]},
                "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "tok", "type": "string"}]},
                "body": {"mode": "raw", "raw": '{"name": "foo"}'},
            },
        },
    ],
}).encode()

CREDENTIALS_FILE = b"""
# Sample credentials
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMSJ9.abc
X-API-Key: my-secret-key-123
Cookie: session=abc123; csrf=xyz789
curl 'https://api.example.com/v1/me' -H 'Authorization: Bearer curl-token-123' -H 'X-Custom: value'
"""

SOURCE_FASTAPI = b"""
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/items")
def create_item():
    pass

@app.get("/items/{item_id}")
def get_item(item_id: int):
    pass
"""


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ── 3a OpenAPI ───────────────────────────────────────────────────────────────

def test_parse_openapi_yaml_extracts_endpoints(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "openapi.yaml", OPENAPI_YAML, "application/yaml")
    # Trigger explicit re-parse to ensure sync completion in tests
    r = client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    assert r.status_code == 200
    assert r.json()["status"] == "parsed"

    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    methods_paths = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/users") in methods_paths
    assert ("POST", "/users") in methods_paths
    assert ("GET", "/users/{id}") in methods_paths


def test_parse_openapi_auth_required_flag(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "openapi.yaml", OPENAPI_YAML, "application/yaml")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = {e["path"] + ":" + e["method"]: e for e in
           client.get(f"/api/api-collections/{cid}/endpoints").json()}
    # GET /users has security: [] → auth_required False
    assert eps["/users:GET"]["auth_required"] is False
    # POST /users has BearerAuth → auth_required True
    assert eps["/users:POST"]["auth_required"] is True


def test_parse_openapi_sample_request(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "openapi.yaml", OPENAPI_YAML, "application/yaml")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = {e["method"]: e for e in
           client.get(f"/api/api-collections/{cid}/endpoints").json()
           if e["path"] == "/users"}
    sample = json.loads(eps["POST"]["sample_request_json"])
    assert sample.get("username") == "alice"


def test_parse_swagger_json(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "petstore.json", SWAGGER_JSON, "application/json")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    assert any(e["path"] == "/pets" and e["method"] == "GET" for e in eps)


# ── 3b Postman ────────────────────────────────────────────────────────────────

def test_parse_postman_extracts_endpoints(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "widgets.postman_collection.json", POSTMAN_V21, "application/json")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    paths = {e["path"] for e in eps}
    assert "/widgets/{id}" in paths
    assert "/widgets" in paths


def test_parse_postman_extracts_collection_auth_credential(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "widgets.postman_collection.json", POSTMAN_V21, "application/json")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    creds = client.get(f"/api/api-collections/{cid}/credentials").json()
    assert any(c["scheme"] == "bearer" for c in creds)


def test_parse_postman_body_example(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "widgets.postman_collection.json", POSTMAN_V21, "application/json")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = {e["path"]: e for e in client.get(f"/api/api-collections/{cid}/endpoints").json()}
    sample = json.loads(eps["/widgets"]["sample_request_json"])
    assert sample.get("name") == "foo"


# ── 3c Credentials ────────────────────────────────────────────────────────────

def test_parse_credentials_bearer(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "creds.txt", CREDENTIALS_FILE, "text/plain")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    creds = client.get(f"/api/api-collections/{cid}/credentials").json()
    bearer_creds = [c for c in creds if c["scheme"] == "bearer"]
    assert len(bearer_creds) >= 1


def test_parse_credentials_apikey(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "creds.txt", CREDENTIALS_FILE, "text/plain")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    creds = client.get(f"/api/api-collections/{cid}/credentials").json()
    apikey_creds = [c for c in creds if c["scheme"] == "apikey"]
    assert len(apikey_creds) >= 1


def test_parse_credentials_curl_header(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "creds.txt", CREDENTIALS_FILE, "text/plain")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    creds = client.get(f"/api/api-collections/{cid}/credentials").json()
    # curl line should have produced at least one curl-header bearer credential
    curl_bearer = [c for c in creds if c.get("label") == "curl-header" and c["scheme"] == "bearer"]
    assert len(curl_bearer) >= 1


def test_parse_credentials_cookie(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "creds.txt", CREDENTIALS_FILE, "text/plain")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    creds = client.get(f"/api/api-collections/{cid}/credentials").json()
    cookie_creds = [c for c in creds if c["scheme"] == "cookie"]
    assert len(cookie_creds) >= 1


# ── 3e Source zip ─────────────────────────────────────────────────────────────

def test_parse_source_zip_fastapi(client, data_dir):
    zip_bytes = _make_zip({"app/main.py": SOURCE_FASTAPI})
    cid = _make_collection(client)
    doc = _upload(client, cid, "src.zip", zip_bytes, "application/zip")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    paths = {e["path"] for e in eps}
    assert "/health" in paths
    assert "/items" in paths
    assert "/items/{item_id}" in paths


def test_parse_source_zip_rejects_path_traversal(client, data_dir):
    """A zip containing path-traversal entries should not crash and should skip those files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("safe/main.py", SOURCE_FASTAPI.decode())
        # Add traversal entry manually (ZipFile.writestr won't allow .., use lower-level)
    # Build a malicious zip with path traversal filename
    from zipfile import ZipFile, ZipInfo
    buf2 = io.BytesIO()
    with ZipFile(buf2, "w") as zf:
        info = ZipInfo("../../evil.py")
        zf.writestr(info, "import os\nos.system('echo pwned')")
        zf.writestr("safe/main.py", SOURCE_FASTAPI.decode())
    zip_bytes = buf2.getvalue()
    cid = _make_collection(client)
    doc = _upload(client, cid, "traversal.zip", zip_bytes, "application/zip")
    r = client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    assert r.status_code == 200
    # Should still parse the safe file
    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    paths = {e["path"] for e in eps}
    assert "/health" in paths


def test_parse_source_zip_rejects_bomb(client, data_dir):
    """A zip with too many entries should fail gracefully."""
    from aespa.services.api_docs import _safe_unzip, ParseError
    # Build a zip with 5001 tiny entries
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(5001):
            zf.writestr(f"f{i}.py", "x=1")
    with pytest.raises(ParseError, match="Zip has"):
        _safe_unzip(buf.getvalue())


# ── Document status → failed when content is invalid ─────────────────────────

def test_parse_bad_openapi_sets_status_failed(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "bad.yaml", b"this is not yaml: [", "application/yaml")
    r = client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    assert r.status_code == 200
    assert r.json()["status"] == "failed"


# ── Endpoint scope toggle ─────────────────────────────────────────────────────

def test_patch_endpoint_scope(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "openapi.yaml", OPENAPI_YAML, "application/yaml")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    assert len(eps) > 0
    ep = eps[0]
    assert ep["in_scope"] is True
    r = client.patch(f"/api/api-collections/{cid}/endpoints/{ep['id']}/scope", json={"in_scope": False})
    assert r.status_code == 200
    assert r.json()["in_scope"] is False


# ── Credentials CRUD ─────────────────────────────────────────────────────────

def test_create_and_list_credentials(client, data_dir):
    cid = _make_collection(client)
    r = client.post(f"/api/api-collections/{cid}/credentials", json={
        "scheme": "bearer",
        "name": "Authorization",
        "value": "Bearer my-test-token",
        "label": "dev token",
    })
    assert r.status_code == 201
    cred = r.json()
    assert cred["scheme"] == "bearer"
    # value is intentionally excluded from ApiCredentialOut
    assert "value" not in cred

    r2 = client.get(f"/api/api-collections/{cid}/credentials")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_delete_credential(client, data_dir):
    cid = _make_collection(client)
    r = client.post(f"/api/api-collections/{cid}/credentials", json={
        "scheme": "apikey", "name": "X-API-Key", "value": "k", "label": "test"
    })
    cid2 = r.json()["id"]
    r2 = client.delete(f"/api/api-collections/{cid}/credentials/{cid2}")
    assert r2.status_code == 204
    assert client.get(f"/api/api-collections/{cid}/credentials").json() == []


# ── endpoint_count in collection summary ─────────────────────────────────────

def test_collection_summary_endpoint_count(client, data_dir):
    cid = _make_collection(client)
    doc = _upload(client, cid, "openapi.yaml", OPENAPI_YAML, "application/yaml")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    summaries = client.get("/api/api-collections").json()
    s = next(s for s in summaries if s["id"] == cid)
    assert s["endpoint_count"] == 3  # GET /users, POST /users, GET /users/{id}


# ── Reparse idempotency ───────────────────────────────────────────────────────

def test_reparse_replaces_endpoints(client, data_dir):
    """Parsing the same doc twice should not duplicate endpoints."""
    cid = _make_collection(client)
    doc = _upload(client, cid, "openapi.yaml", OPENAPI_YAML, "application/yaml")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")
    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    # Should still have only 3 (not 6)
    assert len(eps) == 3


# ── Migration smoke test ──────────────────────────────────────────────────────

def test_migrate_creates_api_endpoint_and_credential_tables():
    from sqlalchemy import inspect, text
    from sqlmodel import create_engine as _ce, SQLModel
    from aespa import db as _db

    engine = _ce("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    # Drop the new tables to simulate an older schema
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS api_credential"))
        conn.execute(text("DROP TABLE IF EXISTS api_endpoint"))
        conn.commit()

    _db._migrate(engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "api_endpoint" in tables
    assert "api_credential" in tables
