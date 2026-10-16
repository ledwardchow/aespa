from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect, text

from aespa import config, db, storage_migration
from aespa.config import Settings


def test_default_and_legacy_env_database_urls_follow_data_dir(tmp_path):
    data_dir = tmp_path / "aespa_data"
    for database_url in (
        None,
        "sqlite:///./aespa.db",
        "sqlite:///./aespa_data/aespa.db",
    ):
        options = {"data_dir": data_dir, "_env_file": None}
        if database_url is not None:
            options["database_url"] = database_url
        settings = Settings(**options)
        assert settings.database_url == f"sqlite:///{data_dir / 'aespa.db'}"

    custom = Settings(
        data_dir=data_dir,
        database_url=f"sqlite:///{tmp_path / 'custom.db'}",
        _env_file=None,
    )
    assert custom.database_url == f"sqlite:///{tmp_path / 'custom.db'}"


def test_fresh_installation_creates_database_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_migration, "_DATA_ROOT", tmp_path)
    settings = Settings(data_dir=tmp_path / "aespa_data", _env_file=None)
    storage_migration.migrate_legacy_storage(settings)
    engine = db._build_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE sample (id INTEGER)"))
        assert (settings.data_dir / "aespa.db").is_file()
    finally:
        engine.dispose()


def test_selected_data_folder_starts_empty_or_uses_existing_database(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(storage_migration, "_DATA_ROOT", tmp_path)
    legacy = tmp_path / "aespa.db"
    with sqlite3.connect(legacy) as connection:
        connection.execute("CREATE TABLE marker (value TEXT)")
        connection.execute("INSERT INTO marker VALUES ('old default')")

    selected = tmp_path / "custom" / "aespa_data"
    settings = Settings(data_dir=selected, _env_file=None)
    storage_migration.migrate_legacy_storage(settings)
    assert selected.is_dir()
    assert not (selected / "aespa.db").exists()
    assert legacy.is_file()

    engine = db._build_engine(settings)
    db.run_migrations(engine)
    assert "site" in inspect(engine).get_table_names()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE marker (value TEXT)"))
        connection.execute(text("INSERT INTO marker VALUES ('selected data')"))
    engine.dispose()
    storage_migration.migrate_legacy_storage(settings)
    with sqlite3.connect(selected / "aespa.db") as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == (
            "selected data"
        )


def test_bundled_settings_file_selects_data_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_bundled", lambda: True)
    monkeypatch.setattr(config, "app_data_dir", lambda: tmp_path / "App Support")
    settings_file = config.settings_env_path()
    settings_file.parent.mkdir()
    selected = tmp_path / "External Data"
    (tmp_path / ".env").write_text("AESPA_DATABASE_URL=sqlite:////old/db.db\n")
    settings_file.write_text(
        f'AESPA_DATA_DIR="{selected}"\n'
        f"AESPA_DATABASE_URL=sqlite:///{selected / 'aespa.db'}\n"
    )

    assert config.get_settings().data_dir == selected
    assert config.get_settings().database_url == f"sqlite:///{selected / 'aespa.db'}"


def test_legacy_databases_copy_with_wal_and_do_not_replace_destination(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(storage_migration, "_DATA_ROOT", tmp_path)
    data_dir = tmp_path / "aespa_data"
    monkeypatch.setattr(storage_migration, "DEFAULT_DATA_DIR", data_dir)
    source = tmp_path / "aespa.db"
    with sqlite3.connect(source) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('from WAL')")
        connection.commit()

        for name in ("logs.db", "aespa_reporting_debug.db"):
            with sqlite3.connect(tmp_path / name) as other:
                other.execute("CREATE TABLE sample (value TEXT)")
                other.execute("INSERT INTO sample VALUES (?)", (name,))

        settings = Settings(data_dir=data_dir, _env_file=None)
        storage_migration.migrate_legacy_storage(settings)

    for name, expected in (
        ("aespa.db", "from WAL"),
        ("logs.db", "logs.db"),
        ("aespa_reporting_debug.db", "aespa_reporting_debug.db"),
    ):
        with sqlite3.connect(data_dir / name) as migrated:
            assert (
                migrated.execute("SELECT value FROM sample").fetchone()[0] == expected
            )
        assert not (tmp_path / name).exists()
        assert (data_dir / "legacy-backups" / name).is_file()

    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('new legacy data')")
    storage_migration.migrate_legacy_storage(settings)
    with sqlite3.connect(data_dir / "aespa.db") as migrated:
        assert migrated.execute("SELECT count(*) FROM sample").fetchone()[0] == 1


def test_copied_data_dir_repairs_absolute_upload_paths(tmp_path, monkeypatch):
    old_data = tmp_path / "old-install" / "Custom Data"
    new_data = tmp_path / "new-install" / "Moved Data"
    relative = Path("api_collections/1/upload.json")
    (new_data / relative).parent.mkdir(parents=True)
    (new_data / relative).write_text("{}")
    snapshot = Path("system_snapshots/2/source.zip")
    (new_data / snapshot).parent.mkdir(parents=True)
    (new_data / snapshot).write_bytes(b"snapshot")
    source_archive = Path("sast_uploads/3.zip")
    (new_data / source_archive).parent.mkdir(parents=True)
    (new_data / source_archive).write_bytes(b"source")
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE api_document (id INTEGER, stored_path TEXT)")
        )
        connection.execute(
            text("CREATE TABLE component_snapshot (id INTEGER, stored_path TEXT)")
        )
        connection.execute(
            text("CREATE TABLE sast_run (id INTEGER, source_archive_path TEXT)")
        )
        connection.execute(
            text("INSERT INTO api_document VALUES (1, :path)"),
            {"path": str(old_data / relative)},
        )
        connection.execute(
            text("INSERT INTO component_snapshot VALUES (2, :path)"),
            {"path": str(old_data / snapshot)},
        )
        connection.execute(
            text("INSERT INTO sast_run VALUES (3, :path)"),
            {"path": str(old_data / source_archive)},
        )
    monkeypatch.setattr(db, "get_settings", lambda: SimpleNamespace(data_dir=new_data))

    db._relocate_stored_paths(engine)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT stored_path FROM api_document WHERE id = 1")
        ).scalar_one() == str(new_data / relative)
        assert connection.execute(
            text("SELECT stored_path FROM component_snapshot WHERE id = 2")
        ).scalar_one() == str(new_data / snapshot)
        assert connection.execute(
            text("SELECT source_archive_path FROM sast_run WHERE id = 3")
        ).scalar_one() == str(new_data / source_archive)
    engine.dispose()
