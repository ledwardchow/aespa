"""Tests for per-agent-role model mixing: scan profiles, the role resolver, and
auto-migration. Covers both the service layer (resolver) and the API."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.db import _ensure_default_llm_profile, set_engine
from aespa.schemas import LLMConfigIn, LLMProfileIn, LLMProviderConfigIn
from aespa.services import settings as settings_svc

# ── Service-layer fixtures (own engine via set_engine) ────────────────────────

@pytest.fixture(name="db_engine")
def db_engine_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa.db import _engine as original_engine
    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    set_engine(original_engine)


@pytest.fixture(name="db_session")
def db_session_fixture(db_engine):
    with Session(db_engine) as session:
        yield session


def _mk_model(session: Session, name: str, model: str = "m1"):
    prov = settings_svc.create_llm_provider(
        session,
        LLMProviderConfigIn(
            name=f"{name}-prov", api_format="openai",
            base_url="http://x/v1", models=[model], api_key="k",
        ),
    )
    return settings_svc.create_llm_profile(
        session,
        LLMConfigIn(name=name, provider_id=prov.id, model=model, max_tokens=100),
    )


# ── Resolver precedence ───────────────────────────────────────────────────────

def test_role_override_beats_default(db_session: Session):
    cheap = _mk_model(db_session, "cheap")
    smart = _mk_model(db_session, "smart")
    prof = settings_svc.create_scan_profile(
        db_session,
        LLMProfileIn(name="P", default_model_id=smart.id, role_models={"crawler": cheap.id}),
    )
    run = SimpleNamespace(llm_profile_id=prof.id, llm_config_id=None)

    assert settings_svc.get_llm_config_for_role(db_session, run, "crawler").id == cheap.id
    # Unmapped role → default model.
    assert settings_svc.get_llm_config_for_role(db_session, run, "test_lead").id == smart.id
    # Role-agnostic → default model.
    assert settings_svc.get_llm_config_for_run(db_session, run).id == smart.id


def test_no_profile_falls_back_to_legacy_config(db_session: Session):
    legacy = _mk_model(db_session, "legacy")
    run = SimpleNamespace(llm_profile_id=None, llm_config_id=legacy.id)
    assert settings_svc.get_llm_config_for_role(db_session, run, "crawler").id == legacy.id


def test_active_profile_used_when_run_unset(db_session: Session):
    smart = _mk_model(db_session, "smart")
    cheap = _mk_model(db_session, "cheap")
    settings_svc.create_scan_profile(
        db_session,
        LLMProfileIn(name="active", default_model_id=smart.id, role_models={"validator": cheap.id}),
    )  # first profile auto-activates
    run = SimpleNamespace(llm_profile_id=None, llm_config_id=None)
    assert settings_svc.get_llm_config_for_role(db_session, run, "validator").id == cheap.id
    assert settings_svc.get_llm_config_for_role(db_session, run, "crawler").id == smart.id


def test_falls_back_to_active_model_without_profiles(db_session: Session):
    only = _mk_model(db_session, "only")  # first model auto-activates
    run = SimpleNamespace(llm_profile_id=None, llm_config_id=None)
    assert settings_svc.get_active_scan_profile(db_session) is None
    assert settings_svc.get_llm_config_for_role(db_session, run, "crawler").id == only.id


# ── Auto-migration ────────────────────────────────────────────────────────────

def test_auto_default_profile_wraps_active_model(db_session: Session, db_engine):
    active = _mk_model(db_session, "active")
    _mk_model(db_session, "other")  # exists but inactive
    assert settings_svc.list_scan_profiles(db_session) == []

    _ensure_default_llm_profile(db_engine)

    profiles = settings_svc.list_scan_profiles(db_session)
    assert len(profiles) == 1
    assert profiles[0].is_active is True
    assert profiles[0].default_model_id == active.id

    # Idempotent — a second call seeds nothing more.
    _ensure_default_llm_profile(db_engine)
    assert len(settings_svc.list_scan_profiles(db_session)) == 1


# ── Profile CRUD validation (service layer) ───────────────────────────────────

def test_profile_rejects_unknown_model_and_role(db_session: Session):
    good = _mk_model(db_session, "good")

    with pytest.raises(Exception):
        settings_svc.create_scan_profile(
            db_session, LLMProfileIn(name="bad-default", default_model_id=99999)
        )
    with pytest.raises(Exception):
        settings_svc.create_scan_profile(
            db_session,
            LLMProfileIn(name="bad-role", default_model_id=good.id, role_models={"crawler": 99999}),
        )
    with pytest.raises(Exception):
        settings_svc.create_scan_profile(
            db_session,
            LLMProfileIn(name="bad-role-name", default_model_id=good.id, role_models={"nope": good.id}),
        )


def test_single_active_profile(db_session: Session):
    a = _mk_model(db_session, "a")
    p1 = settings_svc.create_scan_profile(db_session, LLMProfileIn(name="p1", default_model_id=a.id))
    p2 = settings_svc.create_scan_profile(db_session, LLMProfileIn(name="p2", default_model_id=a.id))
    assert p1.is_active is True and p2.is_active is False
    settings_svc.activate_scan_profile(db_session, p2.id)
    db_session.refresh(p1)
    db_session.refresh(p2)
    assert p1.is_active is False and p2.is_active is True


# ── API: profile CRUD + run persistence ───────────────────────────────────────

def _make_model(client: TestClient, name: str = "M"):
    prov = client.post("/api/settings/llm/providers", json={
        "name": f"{name}-prov", "api_format": "openai",
        "base_url": "http://x/v1", "models": ["m1"], "api_key": "k",
    }).json()
    return client.post("/api/settings/llm/model-configs", json={
        "name": name, "provider_id": prov["id"], "model": "m1", "max_tokens": 100,
    }).json()


def test_api_profile_crud(client: TestClient):
    m = _make_model(client)
    r = client.post("/api/settings/llm/profiles", json={
        "name": "Cheap crawler", "default_model_id": m["id"],
        "role_models": {"crawler": m["id"]},
    })
    assert r.status_code == 200, r.text
    prof = r.json()
    assert prof["is_active"] is True
    assert prof["default_model_name"] == "M"
    assert prof["role_models"] == {"crawler": m["id"]}

    listing = client.get("/api/settings/llm/profiles").json()
    assert len(listing) == 1


def test_api_profile_rejects_bad_ids(client: TestClient):
    m = _make_model(client)
    assert client.post("/api/settings/llm/profiles", json={
        "name": "x", "default_model_id": 99999,
    }).status_code == 422
    assert client.post("/api/settings/llm/profiles", json={
        "name": "y", "default_model_id": m["id"], "role_models": {"crawler": 99999},
    }).status_code == 422


def test_run_persists_llm_profile_id(client: TestClient):
    m = _make_model(client)
    prof = client.post("/api/settings/llm/profiles", json={
        "name": "P", "default_model_id": m["id"],
    }).json()
    site = client.post("/api/sites", json={
        "name": "T", "base_url": "https://t.local", "requires_auth": False,
    }).json()

    ok = client.post(f"/api/sites/{site['id']}/test-runs", json={
        "max_depth": 2, "max_pages": 10, "llm_profile_id": prof["id"],
    })
    assert ok.status_code == 201, ok.text
    assert ok.json()["llm_profile_id"] == prof["id"]

    bad = client.post(f"/api/sites/{site['id']}/test-runs", json={
        "max_depth": 2, "max_pages": 10, "llm_profile_id": 99999,
    })
    assert bad.status_code == 404
