from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from aespa.services import scanner, scanner_sessions


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
            account_label="Production admin",
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
        assert vault["configured_primary"]["account_label"] == "Production admin"
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


def test_upsert_without_identity_preserves_originating_account(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(scanner_sessions, "get_engine", lambda: engine)

        scanner_sessions.upsert_session(
            1,
            label="admin_session",
            kind="cookie",
            username="admin@example.test",
            credential_id=9,
            cookies={"sid": "first"},
        )
        refreshed = scanner_sessions.upsert_session(
            1,
            label="admin_session",
            kind="cookie",
            cookies={"sid": "refreshed"},
        )

        assert refreshed.username == "admin@example.test"
        assert refreshed.credential_id == 9
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_persisted_disposable_session_merges_for_deterministic_modules(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(scanner_sessions, "get_engine", lambda: engine)

        scanner_sessions.upsert_session(
            7,
            label="disposable_user_a",
            kind="bearer",
            username="aespa_user",
            source="dynamic_scan_register_account",
            extra_headers={"Authorization": "Bearer disposable-token"},
            metadata={"registration_url": "https://target.local/register"},
        )

        merged = scanner._merge_persisted_sessions(7, {})

        assert -1 in merged
        assert merged[-1]["label"] == "disposable_user_a"
        assert merged[-1]["username"] == "aespa_user"
        assert merged[-1]["extra_headers"]["Authorization"] == "Bearer disposable-token"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_disposable_account_payload_redacts_password(monkeypatch):
    monkeypatch.setattr(scanner.secrets, "token_hex", lambda n: "abc12345")

    account = scanner._disposable_account_fields({}, base_url="https://target.local")
    redacted = scanner._redacted_account_body(account["body"], account["password_field"])

    assert account["username"] == "aespa_abc12345"
    assert account["email"] == "aespa_abc12345@example.invalid"
    assert account["password"] == "Aespa-abc12345-Test!23"
    assert redacted["password"] == "***"
