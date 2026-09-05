from __future__ import annotations

import json

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.models import ApiCollection, ApiTestRun, Site, TestRun
from aespa.services import api_scanner, scope


def test_scope_authority_includes_effective_port():
    assert scope.scope_authority("https://Example.com/path") == "example.com:443"
    assert scope.scope_authority("http://example.com:8080/") == "example.com:8080"
    assert (
        scope.scope_authority("example.com", default_scheme="https")
        == "example.com:443"
    )


def test_bare_scope_entry_inherits_nonstandard_base_port():
    default_url = "https://app.example.com:8443"

    assert scope.normalize_scope_entries(
        ["app.example.com"], default_url=default_url
    ) == ["app.example.com:8443"]
    assert scope.authority_is_allowed(
        "https://app.example.com:8443/account",
        ["app.example.com"],
        default_url=default_url,
    )


def test_authority_scope_blocks_same_hostname_on_another_port():
    allowed = ["app.example.com"]

    assert scope.authority_is_allowed(
        "https://app.example.com/account",
        allowed,
        default_url="https://app.example.com",
    )
    assert not scope.authority_is_allowed(
        "https://app.example.com:8443/admin",
        allowed,
        default_url="https://app.example.com",
    )


def test_check_scope_and_auto_registration_are_port_aware(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(scope, "get_engine", lambda: engine)
    monkeypatch.setattr(scope.events_svc, "emit", lambda *args, **kwargs: None)

    with Session(engine) as session:
        site = Site(
            name="Port-aware app",
            base_url="https://app.example.com",
            scope_hosts=json.dumps(["app.example.com:443"]),
        )
        session.add(site)
        session.commit()
        session.refresh(site)
        run = TestRun(site_id=site.id, name="scope-test")
        session.add(run)
        session.commit()
        session.refresh(run)
        site_id = site.id
        run_id = run.id

    assert scope.check_scope("https://app.example.com/home", site_id, run_id) is None
    rejection = scope.check_scope(
        "https://app.example.com:8443/admin", site_id, run_id
    )
    assert rejection is not None
    assert "app.example.com:8443" in rejection
    assert not scope.register_scope_host_for_run(
        run_id, "https://app.example.com:8443/admin"
    )

    with Session(engine) as session:
        saved = session.get(Site, site_id)
        assert json.loads(saved.scope_hosts) == ["app.example.com:443"]


def test_api_scanner_fallback_scope_blocks_another_port(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(api_scanner, "get_engine", lambda: engine)

    with Session(engine) as session:
        collection = ApiCollection(
            name="Port-aware API",
            base_url="https://api.example.com",
            servers="[]",
            scope_hosts="[]",
        )
        session.add(collection)
        session.commit()
        session.refresh(collection)
        run = ApiTestRun(collection_id=collection.id, name="api-scope-test")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    assert api_scanner._api_check_scope(
        "https://api.example.com/v1/users", run_id
    ) is None
    rejection = api_scanner._api_check_scope(
        "https://api.example.com:8443/admin", run_id
    )
    assert rejection is not None
    assert "api.example.com:8443" in rejection
