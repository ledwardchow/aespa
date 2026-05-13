from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from aespa.config import Settings, get_settings

_engine: Engine | None = None


def _build_engine(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, echo=False, connect_args=connect_args)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine(get_settings())
    return _engine


def set_engine(engine: Engine) -> None:
    """Override the engine (used by tests)."""
    global _engine
    _engine = engine


def init_db() -> None:
    # Importing models registers them with SQLModel.metadata.
    from aespa import models  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _migrate(engine)


def _migrate(engine: Engine) -> None:
    """Apply any missing columns that were added after the initial schema creation."""
    _ensure_column(engine, "llm_config", "name", "TEXT NOT NULL DEFAULT 'Default'")
    _ensure_column(engine, "llm_config", "is_active", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "llm_config", "use_vision", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(engine, "test_run", "current_url", "TEXT")
    _ensure_column(engine, "test_run", "per_user_progress", "TEXT")
    _ensure_column(engine, "test_run", "scan_mode", "TEXT NOT NULL DEFAULT 'safe_active'")
    _ensure_column(engine, "test_run", "scanner_policy_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(engine, "credential", "login_url", "TEXT")
    _ensure_column(engine, "crawled_page", "error_message", "TEXT")
    _ensure_column(engine, "crawled_page", "in_scope", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "crawled_page", "scan_status", "TEXT NOT NULL DEFAULT 'pending'")
    _ensure_column(engine, "crawled_page", "req_auth", "INTEGER")
    _ensure_column(engine, "crawled_page", "takes_input", "INTEGER")
    _ensure_column(engine, "crawled_page", "has_object_ref", "INTEGER")
    _ensure_column(engine, "crawled_page", "has_business_logic", "INTEGER")
    _ensure_column(engine, "scan_finding", "affected_url", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "impact", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "likelihood", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "recommendation", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "cvss_score", "REAL NOT NULL DEFAULT 0.0")
    _ensure_column(engine, "scan_finding", "cvss_vector", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "request_evidence", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "response_evidence", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "screenshot_b64", "TEXT")
    _ensure_column(engine, "scan_finding", "validation_status", "TEXT NOT NULL DEFAULT 'unvalidated'")
    _ensure_column(engine, "scan_finding", "validation_note", "TEXT")
    _ensure_scan_finding_page_id_nullable(engine)
    _ensure_column(engine, "test_run", "llm_config_id", "INTEGER")
    _ensure_column(engine, "crawled_page", "accessible_by", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(engine, "traffic_entry", "username", "TEXT")
    _ensure_column(engine, "scanner_policy", "thinking_max_steps", "INTEGER NOT NULL DEFAULT 120")
    # page_credential_view — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS page_credential_view (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER NOT NULL,
                test_run_id INTEGER NOT NULL,
                credential_id INTEGER,
                username TEXT,
                screenshot_b64 TEXT,
                llm_context TEXT,
                page_text TEXT,
                req_auth INTEGER,
                takes_input INTEGER,
                has_object_ref INTEGER,
                has_business_logic INTEGER
            )
        """))
        conn.execute(__import__("sqlalchemy").text("""
            DELETE FROM page_credential_view
            WHERE NOT EXISTS (
                SELECT 1
                FROM crawled_page
                WHERE crawled_page.id = page_credential_view.page_id
                  AND crawled_page.test_run_id = page_credential_view.test_run_id
            )
        """))
        conn.commit()
    # scan_log — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_run_id INTEGER NOT NULL REFERENCES test_run(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                phase TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                page_url TEXT,
                data_json TEXT
            )
        """))
        conn.commit()
    # target_intel_item — normalized crawl/recon inventory used by the UI and scanners.
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS target_intel_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_run_id INTEGER NOT NULL REFERENCES test_run(id),
                kind TEXT NOT NULL,
                key TEXT NOT NULL DEFAULT '',
                value TEXT NOT NULL DEFAULT '',
                url TEXT,
                method TEXT,
                source TEXT NOT NULL DEFAULT 'crawler',
                confidence REAL NOT NULL DEFAULT 1.0,
                evidence TEXT NOT NULL DEFAULT '',
                item_metadata TEXT NOT NULL DEFAULT '{}',
                discovered_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_target_intel_item_test_run_id "
            "ON target_intel_item (test_run_id)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_target_intel_item_kind "
            "ON target_intel_item (kind)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_target_intel_item_key "
            "ON target_intel_item (key)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_target_intel_item_url "
            "ON target_intel_item (url)"
        ))
        conn.commit()


def _ensure_column(engine: Engine, table: str, column: str, col_def: str) -> None:
    """Add *column* to *table* if it does not already exist (SQLite safe)."""
    with engine.connect() as conn:
        result = conn.execute(
            __import__("sqlalchemy").text(f"PRAGMA table_info({table})")
        )
        existing = {row[1] for row in result}
        if column not in existing:
            conn.execute(
                __import__("sqlalchemy").text(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"
                )
            )
            conn.commit()


def _ensure_scan_finding_page_id_nullable(engine: Engine) -> None:
    """Allow findings to be saved when no specific crawled page applies."""
    if engine.dialect.name != "sqlite":
        return

    sql = __import__("sqlalchemy").text
    columns = [
        "id",
        "test_run_id",
        "page_id",
        "owasp_category",
        "severity",
        "title",
        "description",
        "impact",
        "likelihood",
        "recommendation",
        "cvss_score",
        "cvss_vector",
        "affected_url",
        "evidence",
        "request_evidence",
        "response_evidence",
        "screenshot_b64",
        "validation_status",
        "validation_note",
        "created_at",
    ]
    column_list = ", ".join(columns)
    with engine.connect() as conn:
        rows = list(conn.execute(sql("PRAGMA table_info(scan_finding)")))
        page_id_row = next((row for row in rows if row[1] == "page_id"), None)
        if page_id_row is None or int(page_id_row[3] or 0) == 0:
            return

        conn.execute(sql("DROP TABLE IF EXISTS scan_finding_nullable_migration"))
        conn.execute(sql("""
            CREATE TABLE scan_finding_nullable_migration (
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
                screenshot_b64 TEXT,
                validation_status TEXT NOT NULL DEFAULT 'unvalidated',
                validation_note TEXT,
                created_at DATETIME NOT NULL
            )
        """))
        conn.execute(sql(f"""
            INSERT INTO scan_finding_nullable_migration ({column_list})
            SELECT {column_list}
            FROM scan_finding
        """))
        conn.execute(sql("DROP TABLE scan_finding"))
        conn.execute(sql(
            "ALTER TABLE scan_finding_nullable_migration RENAME TO scan_finding"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_scan_finding_test_run_id "
            "ON scan_finding (test_run_id)"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_scan_finding_page_id "
            "ON scan_finding (page_id)"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_scan_finding_owasp_category "
            "ON scan_finding (owasp_category)"
        ))
        conn.commit()


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
