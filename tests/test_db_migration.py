from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa import db


def test_ensure_column_adds_missing_column():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY)"))
            conn.commit()

        db._ensure_column(engine, "sample", "name", "TEXT")

        with engine.connect() as conn:
            columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(sample)"))
            }

        assert "name" in columns
    finally:
        engine.dispose()


def test_backfill_scanner_session_account_labels_replaces_opaque_subjects():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                CREATE TABLE scanner_session (
                    id INTEGER PRIMARY KEY,
                    label TEXT NOT NULL,
                    account_label TEXT,
                    username TEXT
                )
            """)
            )
            conn.execute(
                text("""
                INSERT INTO scanner_session (id, label, username)
                VALUES (1, 'admin_token', 'sub:1'), (2, 'normal', 'alice')
            """)
            )
            conn.commit()

        db._backfill_scanner_session_account_labels(engine)
        db._backfill_scanner_session_account_labels(engine)

        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                SELECT id, account_label, username
                FROM scanner_session ORDER BY id
            """)
            ).all()

        assert rows == [(1, "admin_token", None), (2, None, "alice")]
    finally:
        engine.dispose()


def test_normalize_threshold_skips_does_not_mark_them_unconfirmed():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401
        from aespa.models import ScanFinding

        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            finding = ScanFinding(
                test_run_id=1,
                page_id=None,
                owasp_category="A05",
                severity="info",
                title="Informational finding",
                description="Informational only.",
                validation_status="unconfirmed",
                validation_note=(
                    "Skipped: severity 'info' is below the configured threshold 'low'."
                ),
            )
            session.add(finding)
            session.commit()
            session.refresh(finding)
            finding_id = finding.id

        db._normalize_threshold_skipped_findings(engine)

        with Session(engine) as session:
            normalized = session.get(ScanFinding, finding_id)

        assert normalized.validation_status == "skipped"
        assert normalized.validation_note.startswith("Not validated:")
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_keeps_ensure_column_separate_and_adds_credential_login_url():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)

        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE credential RENAME TO credential_old"))
            conn.execute(
                text("""
                CREATE TABLE credential (
                    id INTEGER PRIMARY KEY,
                    site_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    label TEXT
                )
            """)
            )
            conn.execute(
                text("""
                INSERT INTO credential (id, site_id, username, password, label)
                SELECT id, site_id, username, password, label FROM credential_old
            """)
            )
            conn.execute(
                text(
                    "INSERT INTO credential "
                    "(id, site_id, username, password, label) "
                    "VALUES (987, 1, 'legacy-user', 'legacy-pass', 'Legacy')"
                )
            )
            conn.execute(text("DROP TABLE credential_old"))
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(credential)"))
            }
            preserved = conn.execute(
                text(
                    "SELECT username, password, login_fields_json "
                    "FROM credential ORDER BY id LIMIT 1"
                )
            ).first()

        assert "login_url" in columns
        assert "login_fields_json" in columns
        assert "test_mailbox_url" in columns
        assert preserved == ("legacy-user", "legacy-pass", None)
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_makes_scan_finding_page_id_nullable_and_preserves_new_columns():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE scan_finding RENAME TO scan_finding_old"))
            conn.execute(
                text("""
                CREATE TABLE scan_finding (
                    id INTEGER PRIMARY KEY,
                    test_run_id INTEGER NOT NULL,
                    page_id INTEGER NOT NULL,
                    owasp_category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    impact TEXT NOT NULL DEFAULT '',
                    likelihood TEXT NOT NULL DEFAULT '',
                    recommendation TEXT NOT NULL DEFAULT '',
                    cvss_score REAL NOT NULL DEFAULT 0.0,
                    cvss_vector TEXT NOT NULL DEFAULT '',
                    affected_url TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL,
                    request_evidence TEXT NOT NULL DEFAULT '',
                    response_evidence TEXT NOT NULL DEFAULT '',
                    screenshot_b64 TEXT,
                    validation_status TEXT NOT NULL DEFAULT 'unvalidated',
                    validation_note TEXT,
                    created_at DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text("""
                INSERT INTO scan_finding (
                    id, test_run_id, page_id, owasp_category, severity, title,
                    description, evidence, created_at
                )
                VALUES (
                    1, 1, 1, 'A05', 'medium', 'Existing finding',
                    'description', 'evidence', '2026-05-10 00:00:00'
                )
            """)
            )
            conn.execute(text("DROP TABLE scan_finding_old"))
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            columns = {
                row[1]: row
                for row in conn.execute(text("PRAGMA table_info(scan_finding)"))
            }
            conn.execute(
                text("""
                INSERT INTO scan_finding (
                    id, test_run_id, page_id, owasp_category, severity, title,
                    description, evidence, created_at
                )
                VALUES (
                    2, 1, NULL, 'A05', 'medium', 'Run-level finding',
                    'description', 'evidence', '2026-05-10 00:00:00'
                )
            """)
            )
            conn.commit()

        assert int(columns["page_id"][3]) == 0
        assert {
            "evidence_json",
            "merged_instances",
            "finding_source",
            "poc_command",
            "poc_setup",
        } <= set(columns)
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_adds_scan_finding_evidence_json():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE scan_finding RENAME TO scan_finding_old"))
            conn.execute(
                text("""
                CREATE TABLE scan_finding (
                    id INTEGER PRIMARY KEY,
                    test_run_id INTEGER NOT NULL,
                    page_id INTEGER,
                    owasp_category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    impact TEXT NOT NULL DEFAULT '',
                    likelihood TEXT NOT NULL DEFAULT '',
                    recommendation TEXT NOT NULL DEFAULT '',
                    cvss_score REAL NOT NULL DEFAULT 0.0,
                    cvss_vector TEXT NOT NULL DEFAULT '',
                    affected_url TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL,
                    request_evidence TEXT NOT NULL DEFAULT '',
                    response_evidence TEXT NOT NULL DEFAULT '',
                    screenshot_b64 TEXT,
                    validation_status TEXT NOT NULL DEFAULT 'unvalidated',
                    validation_note TEXT,
                    created_at DATETIME NOT NULL
                )
            """)
            )
            conn.execute(text("DROP TABLE scan_finding_old"))
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(scan_finding)"))
            }

        assert "evidence_json" in columns
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_creates_target_intelligence_table():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        db._migrate(engine)

        with engine.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(target_intel_item)"))
            }
            indexes = {
                row[1]
                for row in conn.execute(text("PRAGMA index_list(target_intel_item)"))
            }

        assert {
            "test_run_id",
            "kind",
            "key",
            "value",
            "url",
            "source",
            "item_metadata",
        } <= columns
        assert "ix_target_intel_item_test_run_id" in indexes
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_creates_scanner_session_table():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        db._migrate(engine)

        with engine.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(scanner_session)"))
            }
            indexes = {
                row[1]
                for row in conn.execute(text("PRAGMA index_list(scanner_session)"))
            }

        assert {
            "test_run_id",
            "label",
            "kind",
            "username",
            "credential_id",
            "cookies_json",
            "extra_headers_json",
            "session_metadata",
            "token_hint",
            "is_active",
        } <= columns
        assert "ix_scanner_session_test_run_id" in indexes
        assert "ix_scanner_session_label" in indexes
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_splits_llm_providers_and_resets_run_profile_overrides():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE llm_config RENAME TO llm_config_new"))
            conn.execute(
                text("""
                CREATE TABLE llm_config (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT 'Default',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    provider TEXT NOT NULL DEFAULT 'anthropic',
                    api_key TEXT,
                    base_url TEXT,
                    model TEXT NOT NULL DEFAULT 'claude-opus-4-5',
                    max_tokens INTEGER NOT NULL DEFAULT 4096,
                    temperature REAL NOT NULL DEFAULT 0.0,
                    use_vision INTEGER NOT NULL DEFAULT 0,
                    updated_at DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text("""
                INSERT INTO llm_config (
                    id, name, is_active, provider, api_key, base_url, model,
                    max_tokens, temperature, use_vision, updated_at
                )
                VALUES (
                    42, 'Old Profile', 1, 'openai_compatible', 'sk-old',
                    'http://localhost:1234/v1', 'llama-3', 4096, 0.0, 0,
                    datetime('now')
                )
            """)
            )
            conn.execute(text("DROP TABLE llm_config_new"))
            conn.execute(
                text("""
                INSERT INTO site (id, name, base_url, requires_auth, created_at, updated_at)
                VALUES (7, 'Site', 'https://target.local', 0, datetime('now'), datetime('now'))
            """)
            )
            conn.execute(
                text("""
                INSERT INTO test_run (
                    id, site_id, name, status, use_screenshots, max_depth, max_pages,
                    scan_mode, scanner_policy_json, pages_discovered, llm_config_id, created_at
                )
                VALUES (9, 7, 'Run', 'pending', 0, 3, 50, 'safe_active', '{}', 0, 42, datetime('now'))
            """)
            )
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            profile = conn.execute(
                text(
                    "SELECT provider_id, provider, api_key, base_url FROM llm_config WHERE id = 42"
                )
            ).first()
            provider = conn.execute(
                text(
                    "SELECT api_format, api_key, base_url, models_json FROM llm_provider_config"
                )
            ).first()
            run = conn.execute(
                text("SELECT llm_config_id FROM test_run WHERE id = 9")
            ).first()

        assert profile[0] is not None
        assert profile[1] == "openai_compatible"
        assert profile[2] is None
        assert profile[3] is None
        assert provider[0] == "openai_compatible"
        assert provider[1] == "sk-old"
        assert provider[2] == "http://localhost:1234/v1"
        assert provider[3] == '["llama-3"]'
        assert run[0] is None
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_preserves_bedrock_provider_format():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(
                text("""
                INSERT INTO llm_config (
                    name, is_active, provider, api_key, base_url, model,
                    max_tokens, temperature, use_vision, force_tool_choice, updated_at
                )
                VALUES (
                    'Bedrock Profile', 1, 'bedrock', NULL, NULL,
                    'global.anthropic.claude-sonnet-4-6', 4096, 0.0, 0, 1,
                    datetime('now')
                )
            """)
            )
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            profile = conn.execute(
                text("SELECT provider FROM llm_config WHERE name = 'Bedrock Profile'")
            ).first()
            provider = conn.execute(
                text("SELECT api_format, api_key, base_url FROM llm_provider_config")
            ).first()

        assert profile[0] == "bedrock"
        assert provider == ("bedrock", None, None)
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_migrate_preserves_legacy_provider_formats():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        legacy_formats = [
            "openai_compatible",
            "openrouter",
            "google",
            "azure_openai",
            "azure_foundry_openai",
            "azure_foundry_anthropic",
        ]
        with engine.connect() as conn:
            for idx, provider in enumerate(legacy_formats, start=1):
                conn.execute(
                    text("""
                    INSERT INTO llm_config (
                        id, name, is_active, provider, api_key, base_url, model,
                        max_tokens, temperature, use_vision, force_tool_choice, updated_at
                    )
                    VALUES (
                        :id, :name, 0, :provider, 'key', 'https://example.test',
                        :model, 4096, 0.0, 0, 1, datetime('now')
                    )
                """),
                    {
                        "id": idx,
                        "name": f"{provider} profile",
                        "provider": provider,
                        "model": f"{provider}-model",
                    },
                )
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            formats = {
                row[0]
                for row in conn.execute(
                    text("SELECT api_format FROM llm_provider_config")
                )
            }
            profile_formats = {
                row[0] for row in conn.execute(text("SELECT provider FROM llm_config"))
            }

        assert set(legacy_formats) <= formats
        assert set(legacy_formats) <= profile_formats
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_ensure_scan_finding_test_run_id_nullable_decouples_api_findings():
    """Legacy DBs stamped the ApiTestRun id into both test_run_id and
    api_test_run_id.  The migration must make test_run_id nullable and clear it
    for every API finding, while leaving genuine web findings untouched."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        # Legacy schema: test_run_id NOT NULL, both FK columns present.
        with engine.connect() as conn:
            conn.execute(
                text("""
                CREATE TABLE scan_finding (
                    id INTEGER PRIMARY KEY,
                    test_run_id INTEGER NOT NULL REFERENCES test_run(id),
                    page_id INTEGER REFERENCES crawled_page(id),
                    owasp_category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    impact TEXT NOT NULL DEFAULT '',
                    likelihood TEXT NOT NULL DEFAULT '',
                    recommendation TEXT NOT NULL DEFAULT '',
                    cvss_score REAL NOT NULL DEFAULT 0.0,
                    cvss_vector TEXT NOT NULL DEFAULT '',
                    affected_url TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL,
                    request_evidence TEXT NOT NULL DEFAULT '',
                    response_evidence TEXT NOT NULL DEFAULT '',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    merged_instances TEXT NOT NULL DEFAULT '[]',
                    poc_command TEXT NOT NULL DEFAULT '',
                    poc_setup TEXT NOT NULL DEFAULT '',
                    screenshot_b64 TEXT,
                    finding_source TEXT NOT NULL DEFAULT 'unknown',
                    validation_status TEXT NOT NULL DEFAULT 'unvalidated',
                    validation_note TEXT,
                    api_test_run_id INTEGER,
                    owasp_api_category TEXT,
                    created_at DATETIME NOT NULL
                )
            """)
            )
            # Web finding (api_test_run_id NULL) and an API finding (both ids set).
            conn.execute(
                text(
                    "INSERT INTO scan_finding "
                    "(id, test_run_id, owasp_category, severity, title, description, "
                    " evidence, api_test_run_id, created_at) VALUES "
                    "(1, 7, 'A01', 'high', 'web', 'd', 'e', NULL, '2024-01-01'),"
                    "(2, 4, 'API1', 'high', 'api', 'd', 'e', 4, '2024-01-01')"
                )
            )
            conn.commit()

        db._ensure_scan_finding_test_run_id_nullable(engine)

        with engine.connect() as conn:
            trn = next(
                r
                for r in conn.execute(text("PRAGMA table_info(scan_finding)"))
                if r[1] == "test_run_id"
            )
            assert int(trn[3]) == 0, "test_run_id should be nullable"

            rows = {
                r[0]: r[1]
                for r in conn.execute(text("SELECT id, test_run_id FROM scan_finding"))
            }
            assert rows[1] == 7, "web finding test_run_id preserved"
            assert rows[2] is None, "API finding test_run_id cleared"

            indexes = {
                r[0]
                for r in conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='index' "
                        "AND tbl_name='scan_finding'"
                    )
                )
            }
            assert "ix_scan_finding_api_test_run_id" in indexes

        # Idempotent: a second pass is a no-op and does not error.
        db._ensure_scan_finding_test_run_id_nullable(engine)
        with engine.connect() as conn:
            count = next(conn.execute(text("SELECT count(*) FROM scan_finding")))[0]
            assert count == 2
    finally:
        engine.dispose()
