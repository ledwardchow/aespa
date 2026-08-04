"""Tests for Slice 4: readiness assessment."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

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


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_collection(client: TestClient, name: str = "Test API") -> int:
    r = client.post(
        "/api/api-collections",
        json={"name": name, "base_url": "https://api.example.com"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _upload(
    client: TestClient,
    cid: int,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> dict:
    r = client.post(
        f"/api/api-collections/{cid}/documents",
        files=[("files", (filename, content, content_type))],
    )
    assert r.status_code == 201, r.text
    return r.json()[0]


# Minimal valid OpenAPI spec with a BearerAuth security scheme
OPENAPI_WITH_AUTH = b"""
openapi: "3.0.0"
info:
  title: Auth API
  version: "1.0"
paths:
  /users:
    get:
      summary: List users
      security:
        - BearerAuth: []
      responses:
        "200":
          description: ok
  /health:
    get:
      summary: Health check
      responses:
        "200":
          description: ok
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""

# Canned LLM response — fully ready
CANNED_READY = {
    "overall": {
        "ready_to_test": True,
        "score": 85,
        "summary": "Good coverage with bearer credentials available.",
        "auth_method_understood": True,
        "has_credentials": True,
        "has_sufficient_test_data": True,
        "blocking_gaps": [],
        "recommendations": [],
    },
    "endpoints": [],  # populated dynamically in tests that need per-ep data
}

# Canned LLM response — no credentials
CANNED_NO_CREDS = {
    "overall": {
        "ready_to_test": False,
        "score": 30,
        "summary": "No credentials found for BearerAuth scheme.",
        "auth_method_understood": True,
        "has_credentials": False,
        "has_sufficient_test_data": True,
        "blocking_gaps": ["No bearer token available for BearerAuth endpoints"],
        "recommendations": ["Upload a credentials file containing a bearer token"],
    },
    "endpoints": [],
}


def _mock_assess(monkeypatch, canned_response: dict):
    """Monkeypatch _parse_freetext_llm-style: patch plain_completion in the readiness module."""
    import aespa.services.api_readiness as readiness_mod

    async def _fake_assess(session, collection_id):
        import json
        from datetime import datetime, timezone

        from sqlmodel import select

        from aespa.models import ApiEndpoint

        endpoints = session.exec(
            select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
        ).all()

        result = dict(canned_response)
        result["collection_id"] = collection_id
        result["assessed_at"] = datetime.now(timezone.utc).isoformat()

        # Fill per-endpoint results if the canned response has none
        if not result["endpoints"] and endpoints:
            result["endpoints"] = [
                {
                    "endpoint_id": ep.id,
                    "can_test": True,
                    "can_test_auth": canned_response["overall"]["has_credentials"]
                    or not ep.auth_required,
                    "notes": []
                    if (
                        canned_response["overall"]["has_credentials"]
                        or not ep.auth_required
                    )
                    else ["No credentials for required auth"],
                }
                for ep in endpoints
            ]

        from aespa.models import ApiCollection

        collection = session.get(ApiCollection, collection_id)
        collection.readiness_json = json.dumps(result)
        session.add(collection)

        overall_has_creds = result["overall"]["has_credentials"]
        for ep in endpoints:
            ep_result = next(
                (r for r in result["endpoints"] if r["endpoint_id"] == ep.id), None
            )
            if ep_result:
                ep.prereq_can_test = ep_result["can_test"]
                ep.prereq_can_test_auth = ep_result["can_test_auth"]
                ep.prereq_notes = json.dumps(ep_result["notes"])
            else:
                ep.prereq_can_test = True
                ep.prereq_can_test_auth = not ep.auth_required or overall_has_creds
                ep.prereq_notes = json.dumps(
                    []
                    if ep.prereq_can_test_auth
                    else ["No credentials for required auth"]
                )
            session.add(ep)

        session.commit()
        return result

    monkeypatch.setattr(readiness_mod, "assess_readiness", _fake_assess)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_get_readiness_not_assessed(client):
    """GET /readiness before any assessment returns {status: not_assessed}."""
    cid = _make_collection(client)
    r = client.get(f"/api/api-collections/{cid}/readiness")
    assert r.status_code == 200
    assert r.json()["status"] == "not_assessed"


def test_readiness_404_on_missing_collection(client):
    r = client.post("/api/api-collections/9999/readiness")
    assert r.status_code == 404


def test_run_readiness_with_mock_llm(client, monkeypatch):
    """POST /readiness with mocked LLM returns structured result and persists."""
    _mock_assess(monkeypatch, CANNED_READY)

    cid = _make_collection(client)
    r = client.post(f"/api/api-collections/{cid}/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["overall"]["score"] == 85
    assert data["overall"]["ready_to_test"] is True
    assert "assessed_at" in data
    assert data["collection_id"] == cid


def test_get_readiness_after_assessment(client, monkeypatch):
    """GET /readiness after an assessment returns the stored result."""
    _mock_assess(monkeypatch, CANNED_READY)
    cid = _make_collection(client)
    client.post(f"/api/api-collections/{cid}/readiness")
    r = client.get(f"/api/api-collections/{cid}/readiness")
    assert r.status_code == 200
    assert r.json()["overall"]["score"] == 85


def test_readiness_no_credentials_flags_gap(client, monkeypatch):
    """When no credentials are available the overall.has_credentials should be False."""
    _mock_assess(monkeypatch, CANNED_NO_CREDS)
    cid = _make_collection(client)
    # Upload an OpenAPI spec (parses with real parser — OpenAPI, no LLM needed)
    import aespa.services.api_docs as api_docs_mod

    async def _no_parse(session, cid_, doc_id):
        pass

    monkeypatch.setattr(api_docs_mod, "parse_document", _no_parse)
    r = client.post(f"/api/api-collections/{cid}/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["overall"]["has_credentials"] is False
    assert len(data["overall"]["blocking_gaps"]) >= 1
    assert len(data["overall"]["recommendations"]) >= 1


def test_readiness_no_llm_config_returns_400(client):
    """Without a configured LLM, the endpoint should return 400."""
    cid = _make_collection(client)
    # No LLM config in the test DB → ReadinessError → 400
    r = client.post(f"/api/api-collections/{cid}/readiness")
    assert r.status_code == 400
    assert "LLM" in r.json()["detail"]


def test_prereq_columns_on_endpoints_updated_after_assessment(client, monkeypatch):
    """After assessment, endpoint prereq_* fields are updated."""
    _mock_assess(monkeypatch, CANNED_NO_CREDS)
    cid = _make_collection(client)

    # Upload the OpenAPI spec, then explicitly parse it (upload no longer auto-parses)
    doc = _upload(client, cid, "api.yaml", OPENAPI_WITH_AUTH, "application/yaml")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")

    # Run readiness
    client.post(f"/api/api-collections/{cid}/readiness")

    # Check endpoints
    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    assert len(eps) >= 1

    auth_eps = [ep for ep in eps if ep["auth_required"]]
    unauth_eps = [ep for ep in eps if not ep["auth_required"]]

    # Auth-required endpoints should have can_test_auth=False (no creds)
    for ep in auth_eps:
        assert ep["prereq_can_test"] is True
        assert ep["prereq_can_test_auth"] is False
        notes = json.loads(ep["prereq_notes"])
        assert len(notes) >= 1

    # Unauthenticated endpoints should be fully ready
    for ep in unauth_eps:
        assert ep["prereq_can_test_auth"] is True
        assert json.loads(ep["prereq_notes"]) == []


def test_prereq_columns_green_with_credentials(client, monkeypatch):
    """With credentials present, all endpoints should show can_test_auth=True."""
    _mock_assess(monkeypatch, CANNED_READY)
    cid = _make_collection(client)
    doc = _upload(client, cid, "api.yaml", OPENAPI_WITH_AUTH, "application/yaml")
    client.post(f"/api/api-collections/{cid}/documents/{doc['id']}/parse")

    # Add a bearer credential
    cr = client.post(
        f"/api/api-collections/{cid}/credentials",
        json={
            "scheme": "bearer",
            "name": "Authorization",
            "value": "Bearer test-token",
            "label": "test",
        },
    )
    assert cr.status_code == 201

    client.post(f"/api/api-collections/{cid}/readiness")

    eps = client.get(f"/api/api-collections/{cid}/endpoints").json()
    for ep in eps:
        assert ep["prereq_can_test"] is True
        assert ep["prereq_can_test_auth"] is True


def test_readiness_score_in_summary_response(client, monkeypatch):
    """The collection summary endpoint_count is unaffected; readiness assessed_at is in GET."""
    _mock_assess(monkeypatch, CANNED_READY)
    cid = _make_collection(client)
    client.post(f"/api/api-collections/{cid}/readiness")

    r = client.get(f"/api/api-collections/{cid}/readiness")
    assert r.status_code == 200
    d = r.json()
    assert d["overall"]["score"] == 85
    assert "assessed_at" in d


def test_reassessment_overwrites_previous(client, monkeypatch):
    """A second POST /readiness replaces the previous result."""
    _mock_assess(monkeypatch, CANNED_READY)
    cid = _make_collection(client)
    client.post(f"/api/api-collections/{cid}/readiness")

    _mock_assess(monkeypatch, CANNED_NO_CREDS)
    client.post(f"/api/api-collections/{cid}/readiness")

    r = client.get(f"/api/api-collections/{cid}/readiness")
    assert r.json()["overall"]["score"] == 30  # second result


def test_readiness_db_migration(tmp_path, monkeypatch):
    """_migrate adds the readiness/auth_summary/prereq columns idempotently."""
    import sqlalchemy as sa

    from aespa.db import _migrate

    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    engine = sa.create_engine(f"sqlite:///{tmp_path}/test.db")

    from aespa import models as _m  # noqa: F401

    SQLModel.metadata.create_all(engine)

    # Run twice — must not raise
    _migrate(engine)
    _migrate(engine)

    inspector = sa.inspect(engine)
    col_names = {c["name"] for c in inspector.get_columns("api_endpoint")}
    assert "prereq_can_test" in col_names
    assert "prereq_can_test_auth" in col_names
    assert "prereq_notes" in col_names

    coll_cols = {c["name"] for c in inspector.get_columns("api_collection")}
    assert "readiness_json" in coll_cols
    assert "auth_summary_json" in coll_cols
