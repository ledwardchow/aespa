"""Move AESPA-owned SQLite data into the portable data directory."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from sqlalchemy.engine import make_url

from aespa.config import _DATA_ROOT, DEFAULT_DATA_DIR, Settings


def migrate_legacy_storage(settings: Settings) -> None:
    """Copy legacy databases before any new connection opens them.

    SQLite's backup API includes committed WAL data. Archive the originals
    inside data_dir, and never replace a database already present there.
    """
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    if data_dir.resolve() != DEFAULT_DATA_DIR.resolve():
        return
    url = make_url(settings.database_url)
    if url.drivername.startswith("sqlite") and url.database:
        database_path = Path(url.database).resolve()
        if database_path == (data_dir / "aespa.db").resolve():
            _migrate_database(_DATA_ROOT / "aespa.db", database_path, data_dir)
            _migrate_database(
                _DATA_ROOT / "aespa_reporting_debug.db",
                data_dir / "aespa_reporting_debug.db",
                data_dir,
            )
    _migrate_database(_DATA_ROOT / "logs.db", data_dir / "logs.db", data_dir)


def _migrate_database(source: Path, destination: Path, data_dir: Path) -> None:
    if source.resolve() == destination.resolve() or not source.is_file():
        return
    _copy_database(source, destination)
    _archive_legacy_database(source, data_dir)


def _copy_database(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with closing(sqlite3.connect(source, timeout=30)) as original:
            with closing(sqlite3.connect(temporary)) as copy:
                original.backup(copy)
                if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise sqlite3.DatabaseError(f"Invalid SQLite backup: {source}")
        # Linking in the same directory publishes the copy atomically without
        # replacing a database another process may have already installed.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            pass
    finally:
        temporary.unlink(missing_ok=True)


def _archive_legacy_database(source: Path, data_dir: Path) -> None:
    archive_dir = data_dir / "legacy-backups"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = archive_dir / source.name
    number = 1
    while archived.exists():
        archived = archive_dir / f"{source.name}.{number}"
        number += 1
    shutil.move(str(source), str(archived))
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = source.with_name(source.name + suffix)
        if sidecar.exists():
            shutil.move(str(sidecar), str(archive_dir / (archived.name + suffix)))
