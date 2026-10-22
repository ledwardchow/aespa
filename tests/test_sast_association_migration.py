from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from aespa import db
from alembic import command
from scripts import check_migration_history


@pytest.mark.parametrize(
    "unsafe_source",
    [
        'with op.batch_alter_table("sast_run") as batch:\n'
        '    batch.add_column(sa.Column("site_id", sa.Integer()))\n',
        'op.batch_alter_table(table_name="sast_run")\n',
        'op.drop_table(table_name="sast_run")\n',
        'op.execute("DROP TABLE sast_run")\n',
        'op.execute("drop table if exists \\"sast_run\\"")\n',
        'op.execute(sa.text("DROP TABLE [sast_run]"))\n',
        'op.execute("DROP TABLE `main`.`sast_run`;")\n',
    ],
)
def test_migration_check_rejects_original_sast_rebuild(
    unsafe_source, tmp_path, monkeypatch, capsys
):
    migration = tmp_path / "alembic/versions/d22.py"
    migration.parent.mkdir(parents=True)
    migration.write_text(unsafe_source)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["check_migration_history.py", "--base", "base"])
    monkeypatch.setattr(
        check_migration_history,
        "_git_lines",
        lambda *args: set() if args[0] == "ls-tree" else {"alembic/versions/d22.py"},
    )
    assert check_migration_history.main() == 1
    assert "alembic/versions/d22.py:1" in capsys.readouterr().out
    migration.write_text(
        'op.add_column("sast_run", sa.Column("site_id", sa.Integer()))\n'
    )
    assert check_migration_history.main() == 0
    migration.write_text('op.execute("DROP TABLE another_table")\n')
    assert check_migration_history.main() == 0


def test_sast_association_migration_preserves_saved_scan_data():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    config = db._get_alembic_config(engine)
    try:
        command.upgrade(config, "4a7c1e9d2b60")
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=ON"))
            connection.execute(
                text(
                    "INSERT INTO run_identity (id, kind, legacy_id) "
                    "VALUES (7, 'sast', 7)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO sast_run "
                    "(id, name, status, leads_count, completion_status, "
                    "created_at, updated_at) VALUES "
                    "(7, 'Saved scan', 'completed', 0, 'full', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO sast_source_file "
                    "(id, sast_run_id, path, created_at) VALUES "
                    "(1, 7, 'src/example.py', CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO sast_code_symbol "
                    "(id, sast_run_id, symbol_key, path, language, name, "
                    "qualname, kind, start_line, end_line, reachability, is_root) "
                    "VALUES (1, 7, 'example', 'src/example.py', 'Python', "
                    "'example', 'example', 'function', 1, 2, 'unknown', 1)"
                )
            )

        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert (
                connection.execute(
                    text("SELECT id FROM sast_source_file WHERE sast_run_id = 7")
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text("SELECT id FROM sast_code_symbol WHERE sast_run_id = 7")
                ).scalar_one()
                == 1
            )
            assert not connection.execute(text("PRAGMA foreign_key_check")).all()

        command.downgrade(config, "4a7c1e9d2b60")
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert (
                connection.execute(
                    text("SELECT id FROM sast_source_file WHERE sast_run_id = 7")
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text("SELECT id FROM sast_code_symbol WHERE sast_run_id = 7")
                ).scalar_one()
                == 1
            )
            assert not connection.execute(text("PRAGMA foreign_key_check")).all()
    finally:
        engine.dispose()


@pytest.mark.parametrize("column_exists", [False, True])
def test_repair_sast_api_association_column(column_exists, monkeypatch):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/c8a61d92e4b7_repair_sast_api_association_column.py"
    )
    spec = importlib.util.spec_from_file_location("sast_association_repair", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE api_collection (id INTEGER PRIMARY KEY)"))
        column = (
            ", associated_collection_id INTEGER REFERENCES api_collection(id)"
            if column_exists
            else ""
        )
        connection.execute(
            text(f"CREATE TABLE sast_run (id INTEGER PRIMARY KEY{column})")
        )
        if column_exists:
            connection.execute(
                text(
                    "CREATE INDEX ix_sast_run_associated_collection_id "
                    "ON sast_run (associated_collection_id)"
                )
            )
        connection.execute(text("INSERT INTO sast_run (id) VALUES (7)"))

        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()

        schema = inspect(connection)
        assert "associated_collection_id" in {
            item["name"] for item in schema.get_columns("sast_run")
        }
        assert "ix_sast_run_associated_collection_id" in {
            item["name"] for item in schema.get_indexes("sast_run")
        }
        assert any(
            item["referred_table"] == "api_collection"
            and item["constrained_columns"] == ["associated_collection_id"]
            for item in schema.get_foreign_keys("sast_run")
        )
        assert connection.execute(text("SELECT id FROM sast_run")).scalar_one() == 7
