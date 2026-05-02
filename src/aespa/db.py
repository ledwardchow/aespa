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
    _ensure_column(engine, "llm_config", "use_vision", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(engine, "test_run", "current_url", "TEXT")
    _ensure_column(engine, "crawled_page", "error_message", "TEXT")
    _ensure_column(engine, "crawled_page", "in_scope", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "crawled_page", "scan_status", "TEXT NOT NULL DEFAULT 'pending'")
    _ensure_column(engine, "crawled_page", "req_auth", "INTEGER")
    _ensure_column(engine, "crawled_page", "takes_input", "INTEGER")
    _ensure_column(engine, "crawled_page", "has_object_ref", "INTEGER")
    _ensure_column(engine, "crawled_page", "has_business_logic", "INTEGER")
    _ensure_column(engine, "scan_finding", "affected_url", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "screenshot_b64", "TEXT")
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


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
