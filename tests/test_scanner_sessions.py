from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from aespa.services import scanner_sessions


def test_upsert_session_reuses_label_and_loads_vault(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(scanner_sessions, "get_engine", lambda: engine)

        first = scanner_sessions.upsert_session(
            1,
            label="Configured Primary",
            kind="mixed",
            username="alice",
            credential_id=7,
            source="test",
            cookies={"sid": "abc"},
            extra_headers={"Authorization": "Bearer eyJabcdefghi.1234567890.signature"},
            metadata={"login_url": "https://target.local/login"},
        )
        second = scanner_sessions.upsert_session(
            1,
            label="configured_primary",
            kind="bearer",
            username="alice",
            credential_id=7,
            source="updated",
            cookies={},
            extra_headers={"Authorization": "Bearer replacement-token-value"},
        )

        vault = scanner_sessions.load_session_vault(1)

        assert second.id == first.id
        assert list(vault) == ["configured_primary"]
        assert vault["configured_primary"]["kind"] == "bearer"
        assert vault["configured_primary"]["source"] == "updated"
        assert vault["configured_primary"]["username"] == "alice"
        assert vault["configured_primary"]["extra_headers"]["Authorization"] == "Bearer replacement-token-value"

    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_anonymous_session_is_first_class(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(scanner_sessions, "get_engine", lambda: engine)

        scanner_sessions.ensure_anonymous_session(42, source="dynamic_scan")
        vault = scanner_sessions.load_session_vault(42)

        assert vault["anonymous"]["kind"] == "anonymous"
        assert vault["anonymous"]["cookies"] == {}
        assert vault["anonymous"]["extra_headers"] == {}
        assert vault["anonymous"]["source"] == "dynamic_scan"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()