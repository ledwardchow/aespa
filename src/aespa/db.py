from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from alembic.config import Config
from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine, select

from aespa import db_legacy
from aespa.config import Settings, get_settings
from alembic import command

_engine: Engine | None = None

# The revision immediately before the Applications/Campaign schema
# (`00c6c82b48b7`'s own ``down_revision``). Fixed on purpose — unlike the
# symbolic ``"head"``, this never silently drifts forward as new migrations
# are added; see ``_stamp_legacy_db_if_needed``.
_LAST_PRE_APPLICATIONS_REVISION = "3d4e5f6a7b8c"


def _build_engine(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {}
    is_sqlite = settings.database_url.startswith("sqlite")
    if is_sqlite:
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30
    engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)
    if is_sqlite:
        engine._aespa_enforce_foreign_keys = True  # type: ignore[attr-defined]

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                # Child run records point at the global identity row.  Keep
                # SQLite's FK enforcement on for every runtime connection;
                # the identity migration temporarily disables it while it
                # rebuilds legacy tables.
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=30000")
            finally:
                cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine(get_settings())
    return _engine


def set_engine(engine: Engine) -> None:
    """Override the engine (used by tests)."""
    global _engine
    _engine = engine


def _get_alembic_config(engine: Engine) -> Config:
    import sys

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        repo_root = Path(sys._MEIPASS)
    else:
        repo_root = Path(__file__).resolve().parents[2]
    ini_path = repo_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.attributes["connection"] = engine
    # The application owns process-wide logging. Alembic's default fileConfig
    # call would replace the interactive console handler during startup.
    cfg.attributes["configure_logging"] = False
    return cfg


def _stamp_legacy_db_if_needed(engine: Engine, alembic_cfg: Config) -> bool:
    """Give an unversioned database a safe starting point.

    A pre-Alembic database (has tables, no ``alembic_version`` row) needs a
    stamp so ``command.upgrade(..., "head")`` right after this knows which
    migrations to replay versus which already happened. Its exact position in
    the migration graph is picked from *actual table presence*, never a fixed
    "this must already be current" assumption — the previous version of this
    function stamped any DB with ``run_identity`` present straight at literal
    ``"head"``, which was correct the day it was written but silently started
    skipping every migration added since (including the entire Applications/
    Campaign schema) for a genuine legacy database that has ``run_identity``
    but predates that feature.

    Three cases, from oldest to newest:
      * No ``run_identity`` at all — pre the global-run-identity migration.
        Stamp immediately before it so ids/child rows get remapped for real
        instead of silently skipped.
      * ``run_identity`` present but not yet ``assessment_campaign`` (or any
        other Applications/Campaign table) — a genuine legacy database that
        predates that feature. Stamp at ``_LAST_PRE_APPLICATIONS_REVISION``
        (immediately before it) so those migrations replay for real.
      * Every Applications/Campaign table already present — e.g. a dev/test
        database built via ``metadata.create_all()`` with current models, so
        it is genuinely at head already. Stamp there directly; replaying
        those migrations would try to create tables that already exist.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    is_pre_alembic = (
        "site" in tables or "test_run" in tables
    ) and "alembic_version" not in tables
    if not is_pre_alembic:
        return False

    if "run_identity" not in tables:
        command.stamp(alembic_cfg, "d2f9a6b1c340")
    elif "assessment_campaign" in tables:
        command.stamp(alembic_cfg, "head")
    else:
        command.stamp(alembic_cfg, _LAST_PRE_APPLICATIONS_REVISION)
    return True


def run_migrations(engine: Engine | None = None) -> bool:
    """Upgrade with Alembic and report whether this was a pre-Alembic database."""
    if engine is None:
        engine = get_engine()
    alembic_cfg = _get_alembic_config(engine)
    is_pre_alembic = _stamp_legacy_db_if_needed(engine, alembic_cfg)
    command.upgrade(alembic_cfg, "head")
    if engine.dialect.name == "sqlite" and getattr(
        engine, "_aespa_enforce_foreign_keys", False
    ):
        # The migration temporarily turns FK enforcement off while SQLite
        # rebuilds tables.  Alembic may return the same pooled connection, so
        # restore the runtime setting explicitly after its transaction ends.
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            conn.commit()
    return is_pre_alembic


def init_db() -> None:
    # Importing models registers them with SQLModel.metadata.
    from aespa import models  # noqa: F401

    engine = get_engine()
    _migrate(engine)


def _reset_orphaned_validating_findings(engine: Engine) -> None:
    """Reset findings left stuck in ``validation_status='validating'``.

    Validation runs entirely as in-memory asyncio tasks, so a fresh process can
    have nothing in flight.  Any finding still marked ``validating`` at startup is
    therefore an orphan from a previous process that was interrupted (restart,
    crash, or a mis-wired validation that never reached a verdict — e.g. the old
    ALICE-on-API path).  Flip it back to ``unvalidated`` so it can be re-validated
    instead of showing a perpetual spinner.  Idempotent and best-effort.
    """
    from sqlalchemy import text as _text

    try:
        with engine.connect() as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    _text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            if "scan_finding" not in tables:
                return
            conn.execute(
                _text(
                    "UPDATE scan_finding "
                    "SET validation_status='unvalidated', "
                    "    validation_note='Validation was interrupted before a verdict "
                    "(process restart); reset for re-validation.' "
                    "WHERE validation_status='validating'"
                )
            )
            conn.commit()
    except Exception:
        pass  # never block startup on a best-effort cleanup


def _reset_orphaned_running_runs(engine: Engine) -> None:
    """Fail out crawl/scan runs left stuck in a "running" state.

    ``TestRun.status`` and ``ApiTestRun.status`` are only
    ever driven to a running value by an in-memory asyncio task (crawler,
    thinking-scan, api-scanner, sast-scanner). A fresh process has none of
    those tasks yet, so any run still showing "running" at startup
    is an orphan from a previous process that was killed or crashed mid-run —
    never a run that is genuinely resuming. Left alone, the UI polls the
    stale status forever and looks like the crawl/scan restarted itself on
    every ``uv run aespa``. Idempotent and best-effort.
    """
    from sqlalchemy import text as _text

    try:
        with engine.connect() as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    _text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            crawl_note = "Last crawl interrupted prior to completion"
            legacy_crawl_note = "Interrupted by a server restart; mark as failed."
            scan_note = legacy_crawl_note
            if "test_run" in tables:
                conn.execute(
                    _text(
                        "UPDATE test_run "
                        "SET status='failed', phase='finished', outcome='failed', "
                        "    terminal_reason='interrupted', "
                        "    error_message=:note, completed_at=CURRENT_TIMESTAMP "
                        "WHERE status='running'"
                    ),
                    {"note": crawl_note},
                )
                conn.execute(
                    _text(
                        "UPDATE test_run SET error_message=:crawl_note "
                        "WHERE error_message=:legacy_crawl_note"
                    ),
                    {
                        "crawl_note": crawl_note,
                        "legacy_crawl_note": legacy_crawl_note,
                    },
                )
            if "api_test_run" in tables:
                conn.execute(
                    _text(
                        "UPDATE api_test_run "
                        "SET status='failed', phase='finished', outcome='failed', "
                        "    terminal_reason='interrupted', "
                        "    error_message=:note, completed_at=CURRENT_TIMESTAMP "
                        "WHERE status='running'"
                    ),
                    {"note": scan_note},
                )
            if "scan_log" in tables and "test_run" in tables:
                conn.execute(
                    _text(
                        "INSERT INTO scan_log "
                        "(test_run_id, run_kind, created_at, phase, status, message) "
                        "SELECT id, 'web', COALESCE(completed_at, CURRENT_TIMESTAMP), "
                        "       'restart_recovery', 'failed', error_message "
                        "FROM test_run AS interrupted "
                        "WHERE error_message=:note "
                        "  AND NOT EXISTS ("
                        "    SELECT 1 FROM scan_log AS logged "
                        "    WHERE logged.test_run_id=interrupted.id "
                        "      AND logged.run_kind='web' "
                        "      AND logged.phase='restart_recovery'"
                        "  )"
                    ),
                    {"note": crawl_note},
                )
            if "scan_log" in tables and "api_test_run" in tables:
                conn.execute(
                    _text(
                        "INSERT INTO scan_log "
                        "(test_run_id, run_kind, created_at, phase, status, message) "
                        "SELECT id, 'api', COALESCE(completed_at, CURRENT_TIMESTAMP), "
                        "       'restart_recovery', 'failed', error_message "
                        "FROM api_test_run AS interrupted "
                        "WHERE error_message=:note "
                        "  AND NOT EXISTS ("
                        "    SELECT 1 FROM scan_log AS logged "
                        "    WHERE logged.test_run_id=interrupted.id "
                        "      AND logged.run_kind='api' "
                        "      AND logged.phase='restart_recovery'"
                        "  )"
                    ),
                    {"note": scan_note},
                )
            if "scan_log" in tables and "sast_run" in tables:
                # Backfill the old failure marker so historical SAST runs show
                # why they stopped. New SAST interruptions are handled below by
                # the workspace-lease-aware cleanup, which pauses resumably.
                conn.execute(
                    _text(
                        "INSERT INTO scan_log "
                        "(test_run_id, run_kind, created_at, phase, status, message) "
                        "SELECT id, 'sast', COALESCE(completed_at, CURRENT_TIMESTAMP), "
                        "       'restart_recovery', 'failed', error_message "
                        "FROM sast_run AS interrupted "
                        "WHERE error_message=:note "
                        "  AND NOT EXISTS ("
                        "    SELECT 1 FROM scan_log AS logged "
                        "    WHERE logged.test_run_id=interrupted.id "
                        "      AND logged.run_kind='sast' "
                        "      AND logged.phase='restart_recovery'"
                        "  )"
                    ),
                    {"note": scan_note},
                )
            conn.commit()
    except Exception:
        pass  # never block startup on a best-effort cleanup


def _cleanup_orphaned_sast_extractions() -> None:
    """Reconcile leaked ``<data_dir>/sast_extract/<id>/`` dirs from crashed scans.

    SAST scans extract the uploaded archive into a deterministic per-run path
    under ``<data_dir>/sast_extract/<id>/`` and hold a cross-process workspace
    lease while it is live. On a hard process crash the lease is released by
    the OS but the coroutine's ``finally`` block does not run, so the dir leaks.
    A workspace whose lease can be acquired is therefore safe to reconcile;
    one owned by another process must not be touched.

    For each numeric subdir of ``<data_dir>/sast_extract/``:
      * no matching ``SastRun``                              → delete the dir
      * run in a terminal state (completed/failed/cancelled) → delete the dir
      * run is ``scanning``                                  → mark the run
        ``paused`` with a resumable interruption note and phase-log entry,
        then delete the dir
      * run is ``pending``                                   → leave alone
        (the user may still start it)
      * subdir name is not an integer                        → leave alone
        (e.g. ``lost+found`` or manual artefacts)

    Idempotent and best-effort: any exception is swallowed so startup is
    never blocked. Runs out of an in-memory engine context — touches the DB
    only to flip ``SastRun.status`` for ``scanning`` orphans.
    """
    import logging
    import shutil
    from datetime import datetime, timezone
    from pathlib import Path

    from sqlmodel import Session

    from aespa.config import get_settings
    from aespa.models import RunPause, SastRun, ScanLog
    from aespa.sast_workspace import try_acquire_sast_workspace_lease

    _UTC = timezone.utc
    log = logging.getLogger(__name__)

    try:
        extract_root = Path(get_settings().data_dir) / "sast_extract"
        engine = get_engine()
        terminal = {"completed", "failed", "cancelled"}
        seen_run_ids: set[int] = set()

        def _mark_interrupted_paused(session: Session, run: SastRun) -> None:
            run.status = "paused"
            run.error_message = (
                "Process was interrupted while the SAST scan was running; "
                "the temporary source workspace was cleaned up on startup. "
                "Resume the scan to continue from its last saved step."
            )
            run.completed_at = None
            run.updated_at = datetime.now(_UTC)
            session.add(run)
            pause = session.exec(
                select(RunPause)
                .where(RunPause.run_kind == "sast")
                .where(RunPause.run_id == run.id)
            ).first()
            if pause is None:
                pause = RunPause(run_kind="sast", run_id=run.id)
            pause.provider = ""
            pause.reason = "interrupted"
            pause.message = run.error_message
            pause.reset_at = None
            pause.snapshot_json = "{}"
            pause.resume_stage = None
            pause.paused_at = datetime.now(_UTC)
            session.add(pause)
            session.add(
                ScanLog(
                    test_run_id=run.id,
                    run_kind="sast",
                    phase="restart_recovery",
                    status="paused",
                    message=run.error_message,
                )
            )
            session.commit()

        entries = extract_root.iterdir() if extract_root.is_dir() else []
        for entry in entries:
            if not entry.is_dir():
                continue
            try:
                run_id = int(entry.name)
            except ValueError:
                continue  # non-numeric subdir (e.g. lost+found) — leave alone
            seen_run_ids.add(run_id)
            lease = try_acquire_sast_workspace_lease(
                Path(get_settings().data_dir), run_id
            )
            if lease is None:
                log.info(
                    "sast_extract sweep: left live workspace %s untouched "
                    "(run id=%s is owned by another process)",
                    entry,
                    run_id,
                )
                continue
            try:
                with Session(engine) as s:
                    run = s.get(SastRun, run_id)
                    if run is None or run.status in terminal:
                        shutil.rmtree(entry, ignore_errors=True)
                        log.info(
                            "sast_extract sweep: removed orphan dir %s "
                            "(run id=%s status=%r)",
                            entry,
                            run_id,
                            None if run is None else run.status,
                        )
                        continue
                    if run.status == "scanning":
                        _mark_interrupted_paused(s, run)
                        shutil.rmtree(entry, ignore_errors=True)
                        log.warning(
                            "sast_extract sweep: marked run id=%s 'paused' and removed %s "
                            "(process was interrupted mid-scan)",
                            run_id,
                            entry,
                        )
                        continue
                    # status == 'pending' — user may still start the scan, leave the
                    # dir alone (and it should not exist yet anyway).
            finally:
                lease.release()

        # A crash can occur after the DB status changes but before extraction
        # creates its directory. Reconcile those rows too. The workspace lease
        # keeps this safe if another AESPA process still owns the run.
        with Session(engine) as s:
            orphan_ids = [
                run.id
                for run in s.exec(
                    select(SastRun).where(SastRun.status == "scanning")
                ).all()
                if run.id is not None and run.id not in seen_run_ids
            ]
        for run_id in orphan_ids:
            lease = try_acquire_sast_workspace_lease(
                Path(get_settings().data_dir), run_id
            )
            if lease is None:
                continue
            try:
                with Session(engine) as s:
                    run = s.get(SastRun, run_id)
                    if run is not None and run.status == "scanning":
                        _mark_interrupted_paused(s, run)
                        log.warning(
                            "sast_extract sweep: marked run id=%s 'paused' "
                            "without an extraction directory",
                            run_id,
                        )
            finally:
                lease.release()
    except Exception:
        pass  # never block startup on a best-effort cleanup


def _migrate(engine: Engine) -> None:
    """Apply Alembic migrations, then reconcile state left by an interrupted run."""
    is_pre_alembic = run_migrations(engine)
    enforce_foreign_keys = engine.dialect.name == "sqlite" and getattr(
        engine, "_aespa_enforce_foreign_keys", False
    )
    if is_pre_alembic:
        if enforce_foreign_keys:
            with engine.connect() as conn:
                conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
                conn.commit()
        try:
            db_legacy.upgrade_pre_alembic_schema(engine)
        finally:
            if enforce_foreign_keys:
                with engine.connect() as conn:
                    conn.exec_driver_sql("PRAGMA foreign_keys=ON")
                    conn.commit()

    _reset_orphaned_validating_findings(engine)
    _reset_orphaned_running_runs(engine)
    _cleanup_orphaned_sast_extractions()


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
