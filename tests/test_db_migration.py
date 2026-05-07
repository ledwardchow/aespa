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