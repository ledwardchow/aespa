"""Startup sweep for leaked SAST extraction directories.

When a SAST scan is interrupted by a hard process crash (SIGKILL, OOM, power
loss, …) the coroutine's ``finally`` block never runs, so the per-run
extraction directory under ``<data_dir>/sast_extract/<id>/`` leaks. On the
next startup ``db._cleanup_orphaned_sast_extractions`` walks that directory
and reconciles the DB:

  * No matching ``SastRun`` row, or the run is in a terminal state
    (``completed`` / ``failed`` / ``cancelled``) → the dir is just deleted.
  * The run is still ``scanning`` → the run is marked ``failed`` with a
    note that the process was interrupted, and the dir is deleted.
  * The run is ``pending`` → the dir is left alone (the user may still
    start the scan). It also should not exist in this case under normal
    operation.
  * Subdirs whose name is not an integer are ignored.
"""

from __future__ import annotations

from datetime import datetime, timezone  # noqa: F401  (datetime used in fixtures below)
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa import db as db_mod
from aespa.config import get_settings
from aespa.db import (
    _cleanup_orphaned_sast_extractions,
    get_engine,
    init_db,
    set_engine,
)
from aespa.models import SastRun

_UTC = timezone.utc


@pytest.fixture(name="engine")
def engine_fixture():
    """A fresh in-memory SQLite engine wired into the db module + a tmp
    data_dir for the on-disk extraction root."""
    prev_engine = db_mod._engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    yield engine
    set_engine(prev_engine)
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def _write_run(status: str, **kwargs) -> int:
    """Persist a minimal SastRun row and return its id."""
    with Session(get_engine()) as s:
        run = SastRun(
            name=kwargs.get("name", f"sast-{status}"),
            status=status,
            **{
                k: v
                for k, v in kwargs.items()
                if k
                not in {
                    "name",
                    "status",
                }
            },
        )
        s.add(run)
        s.commit()
        s.refresh(run)
        return run.id


def _extract_dir(run_id: int) -> Path:
    return Path(get_settings().data_dir) / "sast_extract" / str(run_id)


def _seed_dir(run_id: int, files: tuple[str, ...] = ("a.py", "b/c.py")) -> Path:
    d = _extract_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    for rel in files:
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {rel}\n", encoding="utf-8")
    return d


def test_sweep_removes_orphan_dir_with_no_run(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    d = _seed_dir(run_id=99991)
    assert d.is_dir()

    _cleanup_orphaned_sast_extractions()

    assert not d.exists()


def test_sweep_removes_dir_for_terminal_run(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    for status in ("completed", "failed", "cancelled"):
        run_id = _write_run(status=status)
        d = _seed_dir(run_id=run_id)
        assert d.is_dir()

        _cleanup_orphaned_sast_extractions()

        assert not d.exists(), f"dir leaked for status={status!r}"
        with Session(engine) as s:
            run = s.get(SastRun, run_id)
        assert run.status == status  # terminal status is preserved, not touched


def test_sweep_marks_scanning_run_failed_and_removes_dir(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    run_id = _write_run(status="scanning")
    d = _seed_dir(run_id=run_id)
    assert d.is_dir()

    _cleanup_orphaned_sast_extractions()

    assert not d.exists()
    with Session(engine) as s:
        run = s.get(SastRun, run_id)
    assert run.status == "failed"
    assert "interrupted" in (run.error_message or "").lower()
    assert run.completed_at is not None


def test_sweep_leaves_pending_run_alone(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    run_id = _write_run(status="pending")
    d = _seed_dir(run_id=run_id)
    assert d.is_dir()

    _cleanup_orphaned_sast_extractions()

    # Pending run + dir untouched — user may still start the scan.
    assert d.is_dir()
    with Session(engine) as s:
        run = s.get(SastRun, run_id)
    assert run.status == "pending"
    assert run.error_message is None


def test_sweep_ignores_non_integer_subdirs(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    root = Path(get_settings().data_dir) / "sast_extract"
    (root / "lost+found").mkdir(parents=True)
    (root / "scratch").mkdir(parents=True)
    (root / "123").write_text("not a dir", encoding="utf-8")

    _cleanup_orphaned_sast_extractions()

    assert (root / "lost+found").is_dir()
    assert (root / "scratch").is_dir()
    assert (root / "123").is_file()  # file is not a dir, skipped


def test_sweep_is_noop_when_extract_root_missing(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    # No sast_extract/ dir exists at all.
    _cleanup_orphaned_sast_extractions()  # must not raise


def test_sweep_is_idempotent(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    run_id = _write_run(status="scanning")
    d = _seed_dir(run_id=run_id)

    _cleanup_orphaned_sast_extractions()
    # Second call after the dir is gone must still succeed and leave the run
    # in 'failed' (not re-write the error message).
    _cleanup_orphaned_sast_extractions()
    _cleanup_orphaned_sast_extractions()

    assert not d.exists()
    with Session(engine) as s:
        run = s.get(SastRun, run_id)
    assert run.status == "failed"
    # error_message should not keep being overwritten; the timestamp may
    # change on updated_at, which is fine.


def test_sweep_wired_into_init_db(engine, tmp_path, monkeypatch):
    """Regression: _migrate() must call the sweep on every startup."""
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    run_id = _write_run(status="scanning")
    d = _seed_dir(run_id=run_id)
    assert d.is_dir()

    init_db()

    assert not d.exists()
    with Session(engine) as s:
        run = s.get(SastRun, run_id)
    assert run.status == "failed"
