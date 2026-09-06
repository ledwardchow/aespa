from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa import db, db_legacy
from alembic import command


def _upgrade_to(engine, revision: str) -> None:
    command.upgrade(db._get_alembic_config(engine), revision)


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

        db_legacy._ensure_column(engine, "sample", "name", "TEXT")

        with engine.connect() as conn:
            columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(sample)"))
            }

        assert "name" in columns
    finally:
        engine.dispose()


def test_reset_orphaned_running_runs_uses_crawl_message_and_updates_legacy_text():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE test_run ("
                    "id INTEGER PRIMARY KEY, status TEXT, phase TEXT, outcome TEXT, "
                    "terminal_reason TEXT, error_message TEXT, completed_at DATETIME)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO test_run "
                    "(id, status, error_message) VALUES "
                    "(1, 'running', 'old error'), "
                    "(2, 'failed', 'Interrupted by a server restart; mark as failed.')"
                )
            )
            conn.commit()

        db._reset_orphaned_running_runs(engine)

        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, status, phase, outcome, terminal_reason, error_message "
                    "FROM test_run ORDER BY id"
                )
            ).all()

        assert rows[0][1:] == (
            "failed",
            "finished",
            "failed",
            "interrupted",
            "Last crawl interrupted prior to completion",
        )
        assert rows[1][-1] == "Last crawl interrupted prior to completion"
    finally:
        engine.dispose()


def test_reset_orphaned_runs_backfills_sast_restart_message_into_phase_log():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401
        from aespa.models import SastRun, ScanLog

        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            run = SastRun(
                name="Interrupted scan",
                status="failed",
                error_message="Interrupted by a server restart; mark as failed.",
            )
            session.add(run)
            live_run = SastRun(name="Live scan", status="scanning")
            session.add(live_run)
            session.commit()
            session.refresh(run)
            session.refresh(live_run)
            run_id = run.id
            live_run_id = live_run.id

        db._reset_orphaned_running_runs(engine)
        db._reset_orphaned_running_runs(engine)

        with Session(engine) as session:
            logs = session.exec(
                select(ScanLog)
                .where(ScanLog.test_run_id == run_id)
                .where(ScanLog.run_kind == "sast")
                .where(ScanLog.phase == "restart_recovery")
            ).all()
            live_status = session.get(SastRun, live_run_id).status

        assert len(logs) == 1
        assert logs[0].status == "failed"
        assert logs[0].message == "Interrupted by a server restart; mark as failed."
        assert live_status == "scanning"
    finally:
        SQLModel.metadata.drop_all(engine)
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

        db_legacy._backfill_scanner_session_account_labels(engine)
        db_legacy._backfill_scanner_session_account_labels(engine)

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

        db_legacy._normalize_threshold_skipped_findings(engine)

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

        db_legacy._ensure_scan_finding_test_run_id_nullable(engine)

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
        db_legacy._ensure_scan_finding_test_run_id_nullable(engine)
        with engine.connect() as conn:
            count = next(conn.execute(text("SELECT count(*) FROM scan_finding")))[0]
            assert count == 2
    finally:
        engine.dispose()


def test_alembic_migration_creates_version_table_and_stamps_legacy():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        was_pre_alembic = db.run_migrations(engine)

        with engine.connect() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()

        assert "alembic_version" in tables
        assert "site" in tables
        assert "test_run" in tables
        assert was_pre_alembic is False
        # The migration chain now includes replay/session provenance fields.
        assert version == "7a9d3c1e5f20"
    finally:
        engine.dispose()


def test_migrate_skips_legacy_schema_repair_for_versioned_database(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    calls = []
    try:
        monkeypatch.setattr(db, "run_migrations", lambda _engine: False)
        monkeypatch.setattr(
            db_legacy,
            "upgrade_pre_alembic_schema",
            lambda _engine: calls.append("legacy_schema"),
        )
        monkeypatch.setattr(
            db,
            "_reset_orphaned_validating_findings",
            lambda _engine: calls.append("validations"),
        )
        monkeypatch.setattr(
            db,
            "_reset_orphaned_running_runs",
            lambda _engine: calls.append("runs"),
        )
        monkeypatch.setattr(
            db,
            "_cleanup_orphaned_sast_extractions",
            lambda: calls.append("workspaces"),
        )

        db._migrate(engine)

        assert calls == ["validations", "runs", "workspaces"]
    finally:
        engine.dispose()


def test_global_run_identity_migration_remaps_collisions_and_drops_ambiguous_rows():
    """Old shared rows are remapped only when their owner is knowable."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            for statement in (
                "CREATE TABLE site (id INTEGER PRIMARY KEY)",
                "CREATE TABLE api_collection (id INTEGER PRIMARY KEY)",
                "CREATE TABLE test_run (id INTEGER PRIMARY KEY, site_id INTEGER, name TEXT)",
                "CREATE TABLE api_test_run (id INTEGER PRIMARY KEY, collection_id INTEGER, name TEXT)",
                "CREATE TABLE agent_log (id INTEGER PRIMARY KEY, test_run_id INTEGER NOT NULL, run_kind TEXT NOT NULL)",
                "CREATE TABLE traffic_entry (id INTEGER PRIMARY KEY, test_run_id INTEGER NOT NULL, api_test_run_id INTEGER, source TEXT)",
                "CREATE TABLE scan_finding (id INTEGER PRIMARY KEY, test_run_id INTEGER, api_test_run_id INTEGER, title TEXT)",
                "CREATE TABLE crawler_config (id INTEGER PRIMARY KEY)",
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)",
                "INSERT INTO alembic_version VALUES ('d2f9a6b1c340')",
                "INSERT INTO site VALUES (1)",
                "INSERT INTO api_collection VALUES (1)",
                "INSERT INTO test_run VALUES (31, 1, 'Bank of Ed')",
                "INSERT INTO api_test_run VALUES (31, 1, 'Hack This Site')",
                # The default web marker is ambiguous when both old parents
                # exist and must be discarded.
                "INSERT INTO agent_log VALUES (1, 31, 'web')",
                "INSERT INTO agent_log VALUES (2, 31, 'api')",
                "INSERT INTO traffic_entry VALUES (1, 31, 31, 'httpx')",
                "INSERT INTO scan_finding VALUES (1, 31, NULL, 'ambiguous')",
                "INSERT INTO scan_finding VALUES (2, NULL, 31, 'api')",
            ):
                conn.execute(text(statement))
            conn.commit()

        _upgrade_to(engine, "e1a7b9c3d5f0")

        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            identities = conn.execute(
                text("SELECT id, kind, legacy_id FROM run_identity ORDER BY id")
            ).all()
            parents = conn.execute(text("SELECT id, name FROM api_test_run")).all()
            logs = conn.execute(
                text("SELECT test_run_id, run_kind FROM agent_log ORDER BY id")
            ).all()
            traffic = conn.execute(
                text("SELECT test_run_id, api_test_run_id FROM traffic_entry")
            ).all()
            findings = conn.execute(
                text(
                    "SELECT test_run_id, api_test_run_id, title FROM scan_finding ORDER BY id"
                )
            ).all()

        assert identities == [(31, "web", 31), (32, "api", 31)]
        assert parents == [(32, "Hack This Site")]
        assert logs == [(32, "api")]
        assert traffic == [(None, 32)]
        assert findings == [(None, 32, "api")]
    finally:
        engine.dispose()


def test_replay_provenance_repair_migration_handles_existing_c4_database():
    """Databases already at c4 may never have executed the retroactive 1f4 DDL."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            for statement in (
                "CREATE TABLE test_run (id INTEGER PRIMARY KEY)",
                "CREATE TABLE credential (id INTEGER PRIMARY KEY)",
                "CREATE TABLE crawled_page (id INTEGER PRIMARY KEY)",
                "CREATE TABLE traffic_entry (id INTEGER PRIMARY KEY)",
                "CREATE TABLE target_intel_item (id INTEGER PRIMARY KEY)",
                "CREATE TABLE crawler_config (id INTEGER PRIMARY KEY)",
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)",
                "INSERT INTO alembic_version VALUES ('c4e8b7a2d901')",
            ):
                conn.execute(text(statement))
            conn.commit()

        _upgrade_to(engine, "d2f9a6b1c340")

        with engine.connect() as conn:
            columns = {
                table: {
                    row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
                }
                for table in (
                    "test_run",
                    "crawled_page",
                    "traffic_entry",
                    "target_intel_item",
                )
            }
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert {"target_page_ids_json", "target_session_label"} <= columns["test_run"]
        assert "replay_credential_id" in columns["crawled_page"]
        assert {"page_id", "session_label"} <= columns["traffic_entry"]
        assert "page_id" in columns["target_intel_item"]
        assert version == "d2f9a6b1c340"
    finally:
        engine.dispose()


def test_runtime_replay_provenance_backfill_is_idempotent():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            for table in (
                "test_run",
                "crawled_page",
                "traffic_entry",
                "target_intel_item",
            ):
                conn.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            conn.commit()

        db_legacy._ensure_interactive_replay_provenance(engine)
        db_legacy._ensure_interactive_replay_provenance(engine)

        with engine.connect() as conn:
            test_run_columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(test_run)"))
            }
            indexes = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='index'")
                )
            }

        assert {"target_page_ids_json", "target_session_label"} <= test_run_columns
        assert {
            "ix_crawled_page_replay_credential_id",
            "ix_traffic_entry_page_id",
            "ix_traffic_entry_session_label",
            "ix_target_intel_item_page_id",
        } <= indexes
    finally:
        engine.dispose()


def test_migrate_creates_browser_debug_config_for_legacy_db_missing_table():
    """Legacy databases stamped at head still receive newer singleton tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE browser_debug_config"))
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(browser_debug_config)"))
            }

        assert {"id", "browser_engine", "browser_visible", "updated_at"} <= columns
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_legacy_db_with_run_identity_but_no_applications_tables_gets_new_schema():
    """A real legacy DB (run_identity present, no alembic_version, predating
    the Applications/Campaign feature) must still receive every new table.

    Regression for a bug where the legacy stamp always targeted the literal
    Alembic keyword ``"head"``, which silently drifted forward as new
    migrations were added and caused this exact database shape to skip the
    entire Applications/Campaign schema forever.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            for statement in (
                "CREATE TABLE site (id INTEGER PRIMARY KEY, name TEXT)",
                "CREATE TABLE api_collection (id INTEGER PRIMARY KEY, name TEXT)",
                "CREATE TABLE run_identity (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, legacy_id INTEGER, created_at DATETIME)",
                "CREATE TABLE test_run (id INTEGER PRIMARY KEY, site_id INTEGER NOT NULL, name TEXT)",
                "CREATE TABLE api_test_run (id INTEGER PRIMARY KEY, collection_id INTEGER NOT NULL, name TEXT)",
                "CREATE TABLE crawler_config (id INTEGER PRIMARY KEY, test_run_id INTEGER)",
                "CREATE TABLE scanner_policy (id INTEGER PRIMARY KEY)",
                "CREATE TABLE traffic_entry (id INTEGER PRIMARY KEY)",
                "INSERT INTO site VALUES (1, 'legacy site')",
                "INSERT INTO run_identity VALUES (1, 'web', 1, CURRENT_TIMESTAMP)",
                "INSERT INTO test_run VALUES (1, 1, 'legacy run')",
            ):
                conn.execute(text(statement))
            conn.commit()

        with engine.connect() as conn:
            tables_before = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
        assert "application" not in tables_before
        assert "assessment_campaign" not in tables_before

        was_pre_alembic = db.run_migrations(engine)

        with engine.connect() as conn:
            tables_after = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
            campaign_columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(assessment_campaign)"))
            }

        # The full Applications/Campaign schema now exists...
        assert {
            "application",
            "application_component",
            "component_snapshot",
            "application_target",
            "component_target_hint",
            "assessment_campaign",
            "campaign_source_member",
            "campaign_target_member",
            "component_fact",
            "component_connection",
            "lead_target_mapping",
            "campaign_validation_case",
            "scan_lead_component_provenance",
        } <= tables_after
        assert was_pre_alembic is True
        # ...including the follow-up migration's column.
        assert "interrupted_stage" in campaign_columns
        assert version == "7a9d3c1e5f20"
    finally:
        engine.dispose()


def test_current_db_with_applications_tables_stamps_head_without_recreating():
    """A DB already at the current schema (e.g. built via metadata.create_all)
    but missing only the alembic_version bookkeeping row must be recognized
    as already current and not re-run migrations that would try to create
    tables that already exist.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        with engine.connect() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
        assert "alembic_version" not in tables
        assert "assessment_campaign" in tables

        db.run_migrations(engine)

        with engine.connect() as conn:
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()

        assert version == "7a9d3c1e5f20"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_explicit_target_component_migration_adds_nullable_column():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            for statement in (
                "CREATE TABLE application (id INTEGER PRIMARY KEY)",
                "CREATE TABLE application_component ("
                "id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL)",
                "CREATE TABLE application_target ("
                "id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL,"
                "target_type TEXT NOT NULL, target_id INTEGER NOT NULL,"
                "created_at DATETIME NOT NULL)",
                "CREATE TABLE component_target_hint ("
                "id INTEGER PRIMARY KEY, target_id INTEGER NOT NULL "
                "REFERENCES application_target(id))",
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)",
                "INSERT INTO alembic_version VALUES ('cc7896879130')",
            ):
                conn.execute(text(statement))
            conn.commit()

        _upgrade_to(engine, "b8e2f4a6c901")

        with engine.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(application_target)"))
            }
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert "component_id" in columns
        assert version == "b8e2f4a6c901"
    finally:
        engine.dispose()


def test_scope_host_port_migration_backfills_configured_effective_ports():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE site ("
                    "id INTEGER PRIMARY KEY, base_url TEXT NOT NULL, scope_hosts TEXT)"
                )
            )
            conn.execute(
                text(
                    "CREATE TABLE api_collection ("
                    "id INTEGER PRIMARY KEY, base_url TEXT NOT NULL, scope_hosts TEXT)"
                )
            )
            conn.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            conn.execute(text("INSERT INTO alembic_version VALUES ('c7d8e9f0a1b2')"))
            conn.execute(
                text(
                    "INSERT INTO site VALUES "
                    "(1, 'https://app.example.com:8443', :scope_hosts)"
                ),
                {
                    "scope_hosts": (
                        '["app.example.com", "other.example.com:9443", '
                        '"https://secure.example.com"]'
                    )
                },
            )
            conn.execute(
                text(
                    "INSERT INTO api_collection VALUES "
                    "(1, 'http://api.example.com:8080', :scope_hosts)"
                ),
                {"scope_hosts": '["api.example.com"]'},
            )
            conn.commit()

        _upgrade_to(engine, "d4e5f6a7b8c9")

        with engine.connect() as conn:
            site_scope = conn.execute(
                text("SELECT scope_hosts FROM site WHERE id=1")
            ).scalar_one()
            api_scope = conn.execute(
                text("SELECT scope_hosts FROM api_collection WHERE id=1")
            ).scalar_one()
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert site_scope == (
            '["app.example.com:8443", "other.example.com:9443", '
            '"secure.example.com:443"]'
        )
        assert api_scope == '["api.example.com:8080"]'
        assert version == "d4e5f6a7b8c9"
    finally:
        engine.dispose()


@pytest.mark.parametrize("fail_upgrade", [False, True])
def test_legacy_upgrade_restores_foreign_keys_before_recovery(
    monkeypatch, fail_upgrade
):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    engine._aespa_enforce_foreign_keys = True
    calls = []

    def foreign_keys_enabled():
        with engine.connect() as connection:
            return connection.exec_driver_sql("PRAGMA foreign_keys").scalar()

    def migrate(_engine):
        calls.append("alembic")
        return True

    def legacy_upgrade(_engine):
        calls.append("legacy")
        assert foreign_keys_enabled() == 0
        if fail_upgrade:
            raise RuntimeError("legacy upgrade failed")

    def recover(_engine):
        assert foreign_keys_enabled() == 1
        calls.append("recovery")

    monkeypatch.setattr(db, "run_migrations", migrate)
    monkeypatch.setattr(db_legacy, "upgrade_pre_alembic_schema", legacy_upgrade)
    monkeypatch.setattr(db, "_reset_orphaned_validating_findings", recover)
    monkeypatch.setattr(db, "_reset_orphaned_running_runs", lambda _engine: None)
    monkeypatch.setattr(db, "_cleanup_orphaned_sast_extractions", lambda: None)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        if fail_upgrade:
            with pytest.raises(RuntimeError, match="legacy upgrade failed"):
                db._migrate(engine)
            assert calls == ["alembic", "legacy"]
        else:
            db._migrate(engine)
            assert calls == ["alembic", "legacy", "recovery"]
        assert foreign_keys_enabled() == 1
    finally:
        engine.dispose()
