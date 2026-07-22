import asyncio

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

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
        assert (
            vault["configured_primary"]["extra_headers"]["Authorization"]
            == "Bearer replacement-token-value"
        )

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
    redacted = scanner._redacted_account_body(
        account["body"], account["password_field"]
    )

    assert account["username"] == "aespa_abc12345"
    assert account["email"] == "aespa_abc12345@example.invalid"
    assert account["password"] == "Aespa-abc12345-Test!23"
    assert redacted["password"] == "***"


def test_validate_active_sessions_evicts_only_explicit_rejections(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(scanner_sessions, "get_engine", lambda: engine)
        valid = scanner_sessions.upsert_session(
            12,
            label="valid_token",
            kind="bearer",
            extra_headers={"Authorization": "Bearer valid"},
        )
        invalid = scanner_sessions.upsert_session(
            12,
            label="expired_cookie",
            kind="cookie",
            cookies={"sid": "expired"},
        )
        restricted = scanner_sessions.upsert_session(
            12,
            label="restricted_token",
            kind="bearer",
            extra_headers={"Authorization": "Bearer restricted"},
        )
        scanner_sessions.ensure_anonymous_session(12)
        scanner_sessions.upsert_session(
            12,
            label="api_collision",
            kind="bearer",
            extra_headers={"Authorization": "Bearer api"},
            run_kind="api",
        )

        calls = []

        async def request(url, headers, cookies):
            calls.append((url, headers, cookies))
            if cookies.get("sid") == "expired":
                return 401
            if headers.get("Authorization") == "Bearer restricted":
                return 403
            return 200

        with Session(engine) as db:
            result = asyncio.run(
                scanner_sessions.validate_active_sessions(
                    db,
                    12,
                    run_kind="web",
                    default_url="https://target.local/account",
                    request_fn=request,
                )
            )
            db.expire_all()
            assert db.get(_models.ScannerSession, valid.id).is_active is True
            assert db.get(_models.ScannerSession, invalid.id).is_active is False
            restricted_row = db.get(_models.ScannerSession, restricted.id)
            assert restricted_row.is_active is True
            assert restricted_row.lifecycle_state == "verified"

        assert result.checked == 3
        assert result.valid == 2
        assert result.evicted == 1
        assert result.errors == 0
        assert result.skipped == 1
        assert len(calls) == 3
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_upsert_session_deduplicates_the_same_bearer_token(monkeypatch):
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
            21,
            label="http_token",
            kind="bearer",
            extra_headers={"Authorization": "Bearer same-token"},
        )
        second = scanner_sessions.upsert_session(
            21,
            label="http_token_2",
            kind="bearer",
            extra_headers={"Authorization": "Bearer same-token"},
        )

        assert first.id == second.id
        assert len(scanner_sessions.list_run_sessions(21)) == 1
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_validate_active_sessions_preserves_tokens_on_transport_error(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(scanner_sessions, "get_engine", lambda: engine)
        record = scanner_sessions.upsert_session(
            8,
            label="unreachable_target",
            kind="bearer",
            extra_headers={"Authorization": "Bearer keep-me"},
        )

        async def request(url, headers, cookies):
            raise TimeoutError("target timed out")

        with Session(engine) as db:
            result = asyncio.run(
                scanner_sessions.validate_active_sessions(
                    db,
                    8,
                    run_kind="web",
                    default_url="https://target.local",
                    request_fn=request,
                )
            )
            assert db.get(_models.ScannerSession, record.id).is_active is True

        assert result.checked == 1
        assert result.errors == 1
        assert result.evicted == 0
        assert result.results[0].error == "target timed out"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
