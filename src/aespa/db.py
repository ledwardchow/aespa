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
    _ensure_column(engine, "test_run", "llm_config_id", "INTEGER")
    _ensure_column(engine, "crawled_page", "accessible_by", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(engine, "traffic_entry", "username", "TEXT")
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
    # llm_call_log — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS llm_call_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                test_run_id INTEGER,
                provider TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                call_type TEXT NOT NULL DEFAULT '',
                duration_ms INTEGER,
                prompt TEXT,
                response TEXT,
                error TEXT
            )
        """))
        conn.commit()
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


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
