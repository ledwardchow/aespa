from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

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
            columns = {row[1] for row in conn.execute(text("PRAGMA table_info(sample)"))}

        assert "name" in columns
    finally:
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
            conn.execute(text("""
                CREATE TABLE credential (
                    id INTEGER PRIMARY KEY,
                    site_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    label TEXT
                )
            """))
            conn.execute(text("""
                INSERT INTO credential (id, site_id, username, password, label)
                SELECT id, site_id, username, password, label FROM credential_old
            """))
            conn.execute(text("DROP TABLE credential_old"))
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            columns = {row[1] for row in conn.execute(text("PRAGMA table_info(credential)"))}

        assert "login_url" in columns
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
            conn.execute(text("""
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
            """))
            conn.execute(text("""
                INSERT INTO scan_finding (
                    id, test_run_id, page_id, owasp_category, severity, title,
                    description, evidence, created_at
                )
                VALUES (
                    1, 1, 1, 'A05', 'medium', 'Existing finding',
                    'description', 'evidence', '2026-05-10 00:00:00'
                )
            """))
            conn.execute(text("DROP TABLE scan_finding_old"))
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            columns = {
                row[1]: row
                for row in conn.execute(text("PRAGMA table_info(scan_finding)"))
            }
            conn.execute(text("""
                INSERT INTO scan_finding (
                    id, test_run_id, page_id, owasp_category, severity, title,
                    description, evidence, created_at
                )
                VALUES (
                    2, 1, NULL, 'A05', 'medium', 'Run-level finding',
                    'description', 'evidence', '2026-05-10 00:00:00'
                )
            """))
            conn.commit()

        assert int(columns["page_id"][3]) == 0
        assert {
            "evidence_json",
            "merged_instances",
            "finding_source",
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
            conn.execute(text("""
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
            """))
            conn.execute(text("DROP TABLE scan_finding_old"))
            conn.commit()

        db._migrate(engine)

        with engine.connect() as conn:
            columns = {row[1] for row in conn.execute(text("PRAGMA table_info(scan_finding)"))}

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

        assert {"test_run_id", "kind", "key", "value", "url", "source", "item_metadata"} <= columns
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
            "test_run_id", "label", "kind", "username", "credential_id",
            "cookies_json", "extra_headers_json", "session_metadata", "token_hint", "is_active",
        } <= columns
        assert "ix_scanner_session_test_run_id" in indexes
        assert "ix_scanner_session_label" in indexes
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
