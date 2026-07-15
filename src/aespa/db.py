from __future__ import annotations

import json
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


def _backfill_run_kind(engine: Engine) -> None:
    """Tag historical agent_log / scan_log rows that unambiguously belong to an
    API run.  A row whose test_run_id exists in api_test_run but NOT in test_run
    can only have come from an API scan, so flip it to ``run_kind='api'``.
    Rows whose id collides (present in both tables) are left as the default
    ``'web'`` — they cannot be disambiguated after the fact, and new runs are
    tagged correctly at write time.  Idempotent and best-effort.
    """
    from sqlalchemy import text as _text

    try:
        with engine.connect() as conn:
            # Skip cleanly on fresh DBs where api_test_run may not exist yet.
            tables = {
                r[0]
                for r in conn.execute(
                    _text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            if "api_test_run" not in tables:
                return
            api_only = (
                "SELECT id FROM api_test_run "
                "WHERE id NOT IN (SELECT id FROM test_run)"
            )
            for table in ("agent_log", "scan_log", "alice_chat_session", "scanner_session"):
                if table not in tables:
                    continue
                conn.execute(
                    _text(
                        f"UPDATE {table} SET run_kind='api' "
                        f"WHERE run_kind='web' AND test_run_id IN ({api_only})"
                    )
                )
            conn.commit()
    except Exception:
        pass  # never block startup on a best-effort backfill


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


def _normalize_threshold_skipped_findings(engine: Engine) -> None:
    """Correct historical threshold skips that were mislabeled unconfirmed."""
    from sqlalchemy import text as _text

    try:
        with engine.connect() as conn:
            conn.execute(
                _text(
                    "UPDATE scan_finding "
                    "SET validation_status='skipped', "
                    "    validation_note=REPLACE(validation_note, 'Skipped:', 'Not validated:') "
                    "WHERE validation_status='unconfirmed' "
                    "  AND validation_note LIKE 'Skipped: severity % is below the configured threshold %'"
                )
            )
            conn.commit()
    except Exception:
        pass  # never block startup on a best-effort cleanup


def _cleanup_orphaned_sast_extractions() -> None:
    """Reconcile leaked ``<data_dir>/sast_extract/<id>/`` dirs from crashed scans.

    SAST scans extract the uploaded archive into a deterministic per-run path
    under ``<data_dir>/sast_extract/<id>/``. On a hard process crash the
    coroutine's ``finally`` block does not run, so the dir leaks. The in-memory
    task registry (``services.sast_scanner._sast_tasks``) is empty on a fresh
    process, so any dir that survived a restart is orphaned.

    For each numeric subdir of ``<data_dir>/sast_extract/``:
      * no matching ``SastRun``                              → delete the dir
      * run in a terminal state (completed/failed/cancelled) → delete the dir
      * run is ``scanning``                                  → mark the run
        ``failed`` (with a note that the process was interrupted), then delete
        the dir
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
    from aespa.models import SastRun

    _UTC = timezone.utc
    log = logging.getLogger(__name__)

    try:
        extract_root = Path(get_settings().data_dir) / "sast_extract"
        if not extract_root.is_dir():
            return
        engine = get_engine()
        terminal = {"completed", "failed", "cancelled"}
        for entry in extract_root.iterdir():
            if not entry.is_dir():
                continue
            try:
                run_id = int(entry.name)
            except ValueError:
                continue  # non-numeric subdir (e.g. lost+found) — leave alone
            with Session(engine) as s:
                run = s.get(SastRun, run_id)
                if run is None or run.status in terminal:
                    shutil.rmtree(entry, ignore_errors=True)
                    log.info(
                        "sast_extract sweep: removed orphan dir %s "
                        "(run id=%s status=%r)",
                        entry, run_id, None if run is None else run.status,
                    )
                    continue
                if run.status == "scanning":
                    run.status = "failed"
                    run.error_message = (
                        "Process was interrupted while the SAST scan was running; "
                        "extracted source tree has been cleaned up on startup. "
                        "Re-start the scan to retry."
                    )
                    run.completed_at = run.completed_at or datetime.now(_UTC)
                    run.updated_at = datetime.now(_UTC)
                    s.add(run)
                    s.commit()
                    shutil.rmtree(entry, ignore_errors=True)
                    log.warning(
                        "sast_extract sweep: marked run id=%s 'failed' and removed %s "
                        "(process was interrupted mid-scan)",
                        run_id, entry,
                    )
                    continue
                # status == 'pending' — user may still start the scan, leave the
                # dir alone (and it should not exist yet anyway).
    except Exception:
        pass  # never block startup on a best-effort cleanup


def _migrate(engine: Engine) -> None:
    """Apply any missing columns that were added after the initial schema creation."""
    _ensure_column(engine, "site", "scope_hosts", "TEXT")
    _ensure_column(engine, "site", "scan_guidance", "TEXT")
    _ensure_column(engine, "llm_config", "name", "TEXT NOT NULL DEFAULT 'Default'")
    _ensure_column(engine, "llm_config", "is_active", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "llm_config", "provider_id", "INTEGER")
    _ensure_column(engine, "llm_config", "use_vision", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(engine, "llm_config", "force_tool_choice", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "llm_config", "project_id", "TEXT")
    _ensure_column(engine, "test_run", "current_url", "TEXT")
    _ensure_column(engine, "test_run", "per_user_progress", "TEXT")
    _ensure_column(engine, "test_run", "scan_mode", "TEXT NOT NULL DEFAULT 'aggressive'")
    _ensure_column(engine, "test_run", "scanner_policy_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(engine, "test_run", "crawler_mode", "TEXT NOT NULL DEFAULT 'url'")
    _ensure_column(engine, "credential", "login_url", "TEXT")
    _ensure_column(engine, "credential", "auth_mode", "TEXT NOT NULL DEFAULT 'auto'")
    _ensure_column(engine, "credential", "totp_seed", "TEXT")
    _ensure_column(engine, "crawled_page", "error_message", "TEXT")
    _ensure_column(engine, "crawled_page", "in_scope", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "crawled_page", "scan_status", "TEXT NOT NULL DEFAULT 'pending'")
    _ensure_column(engine, "crawled_page", "req_auth", "INTEGER")
    _ensure_column(engine, "crawled_page", "takes_input", "INTEGER")
    _ensure_column(engine, "crawled_page", "has_object_ref", "INTEGER")
    _ensure_column(engine, "crawled_page", "has_business_logic", "INTEGER")
    _ensure_column(engine, "crawled_page", "state_key", "TEXT")
    _ensure_column(engine, "crawled_page", "state_label", "TEXT")
    _ensure_column(engine, "crawled_page", "state_kind", "TEXT NOT NULL DEFAULT 'url'")
    _ensure_column(engine, "crawled_page", "replay_steps_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(engine, "page_link", "action_kind", "TEXT NOT NULL DEFAULT 'navigate'")
    _ensure_column(engine, "page_link", "action_data_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(engine, "scan_finding", "affected_url", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "impact", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "likelihood", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "recommendation", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "cvss_score", "REAL NOT NULL DEFAULT 0.0")
    _ensure_column(engine, "scan_finding", "cvss_vector", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "request_evidence", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "response_evidence", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "evidence_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(engine, "scan_finding", "screenshot_b64", "TEXT")
    _ensure_column(engine, "scan_finding", "finding_source", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(engine, "scan_finding", "validation_status", "TEXT NOT NULL DEFAULT 'unvalidated'")
    _ensure_column(engine, "scan_finding", "validation_note", "TEXT")
    _ensure_column(engine, "scan_finding", "merged_instances", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(engine, "scan_finding", "poc_command", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "scan_finding", "poc_setup", "TEXT NOT NULL DEFAULT ''")
    _ensure_scan_finding_page_id_nullable(engine)
    # Slice 6 — API test run attribution for findings
    _ensure_column(engine, "scan_finding", "api_test_run_id", "INTEGER")
    _ensure_column(engine, "scan_finding", "owasp_api_category", "TEXT")
    # Both scan_finding FK columns now exist — decouple the id spaces: make
    # test_run_id nullable and clear it on findings that belong to an API run.
    _ensure_scan_finding_test_run_id_nullable(engine)
    _ensure_column(engine, "test_run", "llm_config_id", "INTEGER")
    _ensure_column(engine, "test_run", "recon_summary", "TEXT")
    _ensure_column(engine, "test_run", "token_usage_json", "TEXT")
    _ensure_llm_provider_config_migration(engine)
    _ensure_llm_config_temperature_nullable(engine)
    _ensure_column(engine, "crawled_page", "accessible_by", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(engine, "crawled_page", "owasp_applicable_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(engine, "page_credential_view", "owasp_applicable_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(engine, "traffic_entry", "username", "TEXT")
    _ensure_column(engine, "traffic_entry", "api_test_run_id", "INTEGER")
    _ensure_column(engine, "scanner_policy", "thinking_max_steps", "INTEGER NOT NULL DEFAULT 120")
    _ensure_column(engine, "scan_checkpoint", "completion_state_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(engine, "llm_provider_config", "max_tpm", "INTEGER")
    _ensure_column(engine, "llm_provider_config", "max_rpm", "INTEGER")
    _ensure_column(engine, "llm_provider_config", "project_id", "TEXT")
    # agent_log / scan_log share the test_run_id column between web TestRuns and
    # ApiTestRuns, whose ids come from independent counters and collide.  Tag each
    # row with the run kind so the two panels stop reading each other's rows.
    _ensure_column(engine, "agent_log", "run_kind", "TEXT NOT NULL DEFAULT 'web'")
    _ensure_column(engine, "scan_log", "run_kind", "TEXT NOT NULL DEFAULT 'web'")
    _ensure_column(engine, "alice_chat_session", "run_kind", "TEXT NOT NULL DEFAULT 'web'")
    _ensure_column(engine, "scanner_session", "run_kind", "TEXT NOT NULL DEFAULT 'web'")
    _backfill_run_kind(engine)
    _reset_orphaned_validating_findings(engine)
    _normalize_threshold_skipped_findings(engine)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS page_owasp_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_run_id INTEGER NOT NULL REFERENCES test_run(id),
                page_id INTEGER NOT NULL REFERENCES crawled_page(id),
                owasp_category TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_page_owasp_test_test_run_id ON page_owasp_test (test_run_id)"
        ))
        conn.commit()
    _ensure_column(engine, "page_owasp_test", "status", "TEXT NOT NULL DEFAULT 'not_started'")
    _ensure_column(engine, "page_owasp_test", "skip_reason", "TEXT")
    _ensure_column(engine, "page_owasp_test", "finding_ids_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(engine, "page_owasp_test", "last_updated", "DATETIME")  # nullable for existing rows; new rows use model default_factory
    _ensure_column(engine, "test_run", "coverage_mode", "TEXT NOT NULL DEFAULT 'track'")
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS reporting_debug_config (
                id INTEGER PRIMARY KEY,
                capture_enabled INTEGER NOT NULL DEFAULT 0,
                panel_enabled INTEGER NOT NULL DEFAULT 0,
                batch_max_concurrent INTEGER NOT NULL DEFAULT 4,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()
    _ensure_column(engine, "reporting_debug_config", "batch_max_concurrent", "INTEGER NOT NULL DEFAULT 4")
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS upstream_proxy_config (
                id INTEGER PRIMARY KEY,
                proxy_url TEXT,
                proxy_scanner INTEGER NOT NULL DEFAULT 0,
                proxy_llm INTEGER NOT NULL DEFAULT 0,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS burp_mcp_config (
                id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                server_url TEXT NOT NULL DEFAULT 'http://127.0.0.1:9876/sse',
                transport TEXT NOT NULL DEFAULT 'sse',
                send_http1_tool TEXT NOT NULL DEFAULT 'send_http1_request',
                scanner_issues_tool TEXT NOT NULL DEFAULT 'get_scanner_issues',
                active_scan_tool TEXT,
                seed_limit INTEGER NOT NULL DEFAULT 200,
                issue_poll_retries INTEGER NOT NULL DEFAULT 6,
                issue_poll_interval_s REAL NOT NULL DEFAULT 5.0,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS burp_rest_api_config (
                id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                api_url TEXT NOT NULL DEFAULT 'http://127.0.0.1:1337',
                api_key TEXT,
                scan_configuration_name TEXT DEFAULT 'Audit checks - all except time-based detection methods',
                scan_sqli INTEGER NOT NULL DEFAULT 1,
                scan_xss INTEGER NOT NULL DEFAULT 1,
                scan_command_injection INTEGER NOT NULL DEFAULT 1,
                scan_path_traversal INTEGER NOT NULL DEFAULT 1,
                scan_ssrf INTEGER NOT NULL DEFAULT 1,
                scan_xxe INTEGER NOT NULL DEFAULT 1,
                scan_ssti INTEGER NOT NULL DEFAULT 1,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()
    _ensure_column(
        engine,
        "burp_rest_api_config",
        "scan_configuration_name",
        "TEXT DEFAULT 'Audit checks - all except time-based detection methods'",
    )
    _ensure_column(engine, "burp_rest_api_config", "scan_command_injection", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "burp_rest_api_config", "scan_path_traversal", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "burp_rest_api_config", "scan_ssrf", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "burp_rest_api_config", "scan_xxe", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "burp_rest_api_config", "scan_ssti", "INTEGER NOT NULL DEFAULT 1")
    # api_collection — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS api_collection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                description TEXT,
                servers TEXT,
                scope_hosts TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_api_collection_name "
            "ON api_collection (name)"
        ))
        conn.commit()
    # api_document — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS api_document (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL REFERENCES api_collection(id),
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL DEFAULT 'unknown',
                content_type TEXT,
                stored_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'uploaded',
                error_message TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_api_document_collection_id "
            "ON api_document (collection_id)"
        ))
        conn.commit()
    # api_endpoint — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS api_endpoint (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL REFERENCES api_collection(id),
                source_doc_id INTEGER REFERENCES api_document(id),
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                base_url TEXT,
                operation_id TEXT,
                summary TEXT,
                parameters_json TEXT NOT NULL DEFAULT '[]',
                request_body_schema_json TEXT NOT NULL DEFAULT '{}',
                response_schema_json TEXT NOT NULL DEFAULT '{}',
                security_json TEXT NOT NULL DEFAULT '[]',
                auth_required INTEGER NOT NULL DEFAULT 0,
                tags_json TEXT NOT NULL DEFAULT '[]',
                sample_request_json TEXT NOT NULL DEFAULT '{}',
                in_scope INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_api_endpoint_collection_id "
            "ON api_endpoint (collection_id)"
        ))
        conn.commit()
    # api_credential — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS api_credential (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL REFERENCES api_collection(id),
                scheme TEXT NOT NULL DEFAULT 'bearer',
                name TEXT NOT NULL DEFAULT 'Authorization',
                value TEXT NOT NULL,
                label TEXT,
                scope TEXT NOT NULL DEFAULT 'global',
                endpoint_id INTEGER REFERENCES api_endpoint(id),
                created_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_api_credential_collection_id "
            "ON api_credential (collection_id)"
        ))
        conn.commit()
    # Slice 4 — readiness assessment columns (idempotent via _ensure_column)
    _ensure_column(engine, "api_collection", "auth_summary_json", "TEXT")
    _ensure_column(engine, "api_collection", "readiness_json", "TEXT")
    _ensure_column(engine, "api_endpoint", "prereq_can_test", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "api_endpoint", "prereq_can_test_auth", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(engine, "api_endpoint", "prereq_notes", "TEXT NOT NULL DEFAULT '[]'")
    # login-flow credential support
    _ensure_column(engine, "api_credential", "auth_endpoint", "TEXT")
    # api_test_run — created as a full table (not an ALTER)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS api_test_run (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL REFERENCES api_collection(id),
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                llm_config_id INTEGER REFERENCES llm_config(id),
                coverage_mode TEXT NOT NULL DEFAULT 'track',
                started_at DATETIME,
                completed_at DATETIME,
                error_message TEXT,
                recon_summary_json TEXT,
                token_usage_json TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_api_test_run_collection_id "
            "ON api_test_run (collection_id)"
        ))
        conn.commit()
    # Slice 7 — api_endpoint_test (coverage matrix cells)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS api_endpoint_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_test_run_id INTEGER NOT NULL REFERENCES api_test_run(id),
                endpoint_id INTEGER NOT NULL REFERENCES api_endpoint(id),
                owasp_api_category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'not_started',
                skip_reason TEXT,
                finding_ids_json TEXT NOT NULL DEFAULT '[]',
                last_updated DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_api_endpoint_test_run_id "
            "ON api_endpoint_test (api_test_run_id)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_api_endpoint_test_endpoint_id "
            "ON api_endpoint_test (endpoint_id)"
        ))
        conn.commit()
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
    # scanner_session — durable scanner auth/session material with stable labels.
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS scanner_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_run_id INTEGER NOT NULL REFERENCES test_run(id),
                run_kind TEXT NOT NULL DEFAULT 'web',
                label TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'cookie',
                username TEXT,
                credential_id INTEGER REFERENCES credential(id),
                source TEXT NOT NULL DEFAULT 'scanner',
                cookies_json TEXT NOT NULL DEFAULT '{}',
                extra_headers_json TEXT NOT NULL DEFAULT '{}',
                session_metadata TEXT NOT NULL DEFAULT '{}',
                token_hint TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        for column in ("test_run_id", "run_kind", "label", "kind", "username", "credential_id", "is_active"):
            conn.execute(__import__("sqlalchemy").text(
                f"CREATE INDEX IF NOT EXISTS ix_scanner_session_{column} "
                f"ON scanner_session ({column})"
            ))
        conn.commit()
    # specialist_agent_config — singleton settings for specialist agent dispatch.
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS specialist_agent_config (
                id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                max_concurrent INTEGER NOT NULL DEFAULT 5,
                max_steps INTEGER NOT NULL DEFAULT 30,
                min_priority INTEGER NOT NULL DEFAULT 7,
                dispatch_idor INTEGER NOT NULL DEFAULT 1,
                dispatch_auth_bypass INTEGER NOT NULL DEFAULT 1,
                dispatch_sqli INTEGER NOT NULL DEFAULT 1,
                dispatch_xss INTEGER NOT NULL DEFAULT 1,
                dispatch_business_logic INTEGER NOT NULL DEFAULT 1,
                dispatch_ssrf INTEGER NOT NULL DEFAULT 1,
                dispatch_path_traversal INTEGER NOT NULL DEFAULT 1,
                dispatch_cors INTEGER NOT NULL DEFAULT 0,
                dispatch_crypto INTEGER NOT NULL DEFAULT 1,
                dispatch_config INTEGER NOT NULL DEFAULT 0,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()

    # adversarial_validator_config — singleton settings for the adversarial validator.
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS adversarial_validator_config (
                id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                max_steps INTEGER NOT NULL DEFAULT 20,
                min_severity TEXT NOT NULL DEFAULT 'low',
                end_scan_max_concurrent INTEGER NOT NULL DEFAULT 4,
                auto_validate_inline INTEGER NOT NULL DEFAULT 1,
                require_concrete_disproof INTEGER NOT NULL DEFAULT 1,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()
    _ensure_column(
        engine,
        "specialist_agent_config",
        "trigger_specialist_on_burp",
        "INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        engine,
        "adversarial_validator_config",
        "end_scan_max_concurrent",
        "INTEGER NOT NULL DEFAULT 4",
    )
    _ensure_column(
        engine,
        "specialist_agent_config",
        "dispatch_file_upload",
        "INTEGER NOT NULL DEFAULT 1",
    )
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS alice_chat_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_run_id INTEGER NOT NULL REFERENCES test_run(id),
                session_key TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'Session 1',
                position INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_alice_chat_session_test_run_id "
            "ON alice_chat_session (test_run_id)"
        ))
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS alice_chat_message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES alice_chat_session(id),
                message_key TEXT NOT NULL,
                sender TEXT NOT NULL DEFAULT 'alice',
                type TEXT NOT NULL DEFAULT 'message',
                text TEXT NOT NULL DEFAULT '',
                step_data_json TEXT NOT NULL DEFAULT '{}',
                ts TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL DEFAULT 0,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_alice_chat_message_session_id "
            "ON alice_chat_message (session_id)"
        ))
        conn.commit()
    _ensure_column(engine, "alice_chat_message", "step_data_json", "TEXT NOT NULL DEFAULT '{}'")
    # SAST: sast_run and scan_lead tables
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS sast_run (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL REFERENCES api_collection(id),
                document_id INTEGER,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                triggered_by_run_type TEXT,
                triggered_by_run_id INTEGER,
                llm_config_id INTEGER REFERENCES llm_config(id),
                leads_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                token_usage_json TEXT,
                started_at DATETIME,
                completed_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_sast_run_collection_id ON sast_run (collection_id)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_sast_run_triggered_by_run_id ON sast_run (triggered_by_run_id)"
        ))
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS scan_lead (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER,
                producer_run_type TEXT NOT NULL DEFAULT 'sast',
                producer_run_id INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'sast',
                category TEXT NOT NULL DEFAULT '',
                severity TEXT NOT NULL DEFAULT 'medium',
                confidence REAL NOT NULL DEFAULT 0.0,
                title TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                evidence TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                investigated_by_run_type TEXT,
                investigated_by_run_id INTEGER,
                linked_finding_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_scan_lead_collection_id ON scan_lead (collection_id)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_scan_lead_producer_run_id ON scan_lead (producer_run_id)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_scan_lead_status ON scan_lead (status)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_scan_lead_producer_run_type ON scan_lead (producer_run_type)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_scan_lead_source ON scan_lead (source)"
        ))
        conn.commit()
    # SAST: back-reference on api_test_run
    _ensure_column(engine, "api_test_run", "sast_run_id", "INTEGER")
    # SAST web support — additive columns (idempotent).
    _ensure_column(engine, "sast_run", "source_archive_path", "TEXT")
    _ensure_column(engine, "sast_run", "source_filename", "TEXT")
    _ensure_column(engine, "scan_lead", "imported_into_run_type", "TEXT")
    _ensure_column(engine, "scan_lead", "imported_into_run_id", "INTEGER")
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_scan_lead_imported_into_run_id "
            "ON scan_lead (imported_into_run_id)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_scan_lead_imported_into_run_type "
            "ON scan_lead (imported_into_run_type)"
        ))
        conn.commit()
    # Standalone SAST runs have no collection — drop the NOT NULL on collection_id.
    _ensure_sast_run_collection_id_nullable(engine)
    # LLM model-mixing profiles (per-agent-role model assignment). Placed here so
    # all referenced run tables already exist. Profiles map an agent role to an
    # LLMConfig ("Model"); a run selects a profile via *.llm_profile_id.
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS llm_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Default',
                is_active INTEGER NOT NULL DEFAULT 0,
                default_model_id INTEGER REFERENCES llm_config(id),
                role_models_json TEXT NOT NULL DEFAULT '{}',
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_llm_profile_name ON llm_profile (name)"
        ))
        conn.execute(__import__("sqlalchemy").text(
            "CREATE INDEX IF NOT EXISTS ix_llm_profile_is_active ON llm_profile (is_active)"
        ))
        conn.commit()
    _ensure_column(engine, "test_run", "llm_profile_id", "INTEGER")
    _ensure_column(engine, "api_test_run", "llm_profile_id", "INTEGER")
    _ensure_column(engine, "sast_run", "llm_profile_id", "INTEGER")
    _ensure_default_llm_profile(engine)
    # Cloudflare Access: optional AUD to verify on the proxy-injected JWT.
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS cloudflare_access_config (
                id INTEGER PRIMARY KEY,
                audience TEXT,
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()

    # Orphan-extraction sweep last: it queries SastRun via the ORM, so it must
    # run only after every SastRun column above has been added — otherwise the
    # first post-upgrade startup raises "no such column" and silently skips.
    _cleanup_orphaned_sast_extractions()


def _ensure_llm_provider_config_migration(engine: Engine) -> None:
    sql = __import__("sqlalchemy").text
    with engine.connect() as conn:
        conn.execute(sql("""
            CREATE TABLE IF NOT EXISTS llm_provider_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                api_format TEXT NOT NULL DEFAULT 'anthropic',
                api_key TEXT,
                base_url TEXT,
                models_json TEXT NOT NULL DEFAULT '[]',
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(sql("""
            CREATE TABLE IF NOT EXISTS aespa_migration_state (
                key TEXT PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()

        applied = conn.execute(
            sql("SELECT 1 FROM aespa_migration_state WHERE key = 'llm_provider_split_v1'")
        ).first()
        if applied is not None:
            return

        profiles = conn.execute(sql("""
            SELECT id, name, provider, api_key, base_url, model, updated_at
            FROM llm_config
            WHERE provider_id IS NULL
            ORDER BY id ASC
        """)).mappings().all()
        provider_by_key: dict[tuple[str, str | None, str | None], int] = {}
        legacy_provider_formats = {
            "anthropic",
            "openai",
            "openai_compatible",
            "openrouter",
            "google",
            "bedrock",
            "bedrock_mantle",
            "azure_openai",
            "azure_foundry",
            "azure_foundry_openai",
            "azure_foundry_anthropic",
        }
        for profile in profiles:
            api_format = (
                profile["provider"]
                if profile["provider"] in legacy_provider_formats
                else "openai"
            )
            base_url = profile["base_url"]
            api_key = profile["api_key"]
            key = (api_format, base_url, api_key)
            provider_id = provider_by_key.get(key)
            if provider_id is None:
                label = {
                    "anthropic": "Anthropic",
                    "openai": "OpenAI",
                    "openai_compatible": "OpenAI-compatible",
                    "openrouter": "OpenRouter",
                    "google": "Google",
                    "bedrock": "Bedrock",
                    "bedrock_mantle": "Bedrock Mantle",
                    "azure_openai": "Azure OpenAI",
                    "azure_foundry": "Azure Foundry",
                    "azure_foundry_openai": "Azure Foundry OpenAI",
                    "azure_foundry_anthropic": "Azure Foundry Anthropic",
                }.get(api_format, "OpenAI")
                provider_name = f"{profile['name']} {label} Provider".strip()
                result = conn.execute(sql("""
                    INSERT INTO llm_provider_config (name, api_format, api_key, base_url, models_json, updated_at)
                    VALUES (:name, :api_format, :api_key, :base_url, :models_json, COALESCE(:updated_at, datetime('now')))
                """), {
                    "name": provider_name,
                    "api_format": api_format,
                    "api_key": api_key,
                    "base_url": base_url,
                    "models_json": json.dumps([profile["model"]]),
                    "updated_at": profile["updated_at"],
                })
                provider_id = int(result.lastrowid)
                provider_by_key[key] = provider_id
            else:
                row = conn.execute(
                    sql("SELECT models_json FROM llm_provider_config WHERE id = :id"),
                    {"id": provider_id},
                ).first()
                models = json.loads(row[0] or "[]") if row is not None else []
                if profile["model"] not in models:
                    models.append(profile["model"])
                    conn.execute(
                        sql("UPDATE llm_provider_config SET models_json = :models_json WHERE id = :id"),
                        {"id": provider_id, "models_json": json.dumps(models)},
                    )

            conn.execute(sql("""
                UPDATE llm_config
                SET provider_id = :provider_id,
                    provider = :api_format,
                    api_key = NULL,
                    base_url = NULL
                WHERE id = :profile_id
            """), {"provider_id": provider_id, "api_format": api_format, "profile_id": profile["id"]})

        # Existing historical runs that selected a profile should now fall back
        # to the system default profile, as requested for this schema change.
        conn.execute(sql("UPDATE test_run SET llm_config_id = NULL WHERE llm_config_id IS NOT NULL"))
        conn.execute(sql("INSERT INTO aespa_migration_state (key) VALUES ('llm_provider_split_v1')"))
        conn.commit()


def _ensure_default_llm_profile(engine: Engine) -> None:
    """Seed a default active ``LLMProfile`` when Models exist but no Profile does.

    Keeps existing installs working after the model-mixing upgrade: a scan that
    doesn't pick a profile resolves through the active profile's default model,
    which here wraps the previously-active ``LLMConfig``.  Idempotent and
    best-effort — never blocks startup.
    """
    sql = __import__("sqlalchemy").text
    try:
        with engine.connect() as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    sql("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            if "llm_profile" not in tables or "llm_config" not in tables:
                return
            if conn.execute(sql("SELECT 1 FROM llm_profile LIMIT 1")).first() is not None:
                return  # profiles already exist — don't seed
            row = conn.execute(
                sql(
                    "SELECT id FROM llm_config "
                    "ORDER BY is_active DESC, updated_at DESC LIMIT 1"
                )
            ).first()
            if row is None:
                return  # no Models yet; nothing to wrap (a fresh install)
            conn.execute(
                sql(
                    "INSERT INTO llm_profile "
                    "(name, is_active, default_model_id, role_models_json, updated_at) "
                    "VALUES ('Default', 1, :mid, '{}', datetime('now'))"
                ),
                {"mid": int(row[0])},
            )
            conn.commit()
    except Exception:
        pass  # never block startup on a best-effort seed


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
        "evidence_json",
        "merged_instances",
        "poc_command",
        "poc_setup",
        "screenshot_b64",
        "finding_source",
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
                evidence_json TEXT NOT NULL DEFAULT '[]',
                merged_instances TEXT NOT NULL DEFAULT '[]',
                poc_command TEXT NOT NULL DEFAULT '',
                poc_setup TEXT NOT NULL DEFAULT '',
                screenshot_b64 TEXT,
                finding_source TEXT NOT NULL DEFAULT 'unknown',
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


def _ensure_scan_finding_test_run_id_nullable(engine: Engine) -> None:
    """Decouple API findings from the web TestRun id space.

    ``test_run_id`` and ``api_test_run_id`` are FKs into independent
    autoincrement sequences.  API scans used to stamp the ApiTestRun id into
    ``test_run_id`` as well, so an API finding leaked into the web run that
    happened to share that integer id.  Make ``test_run_id`` nullable and null
    it out for every finding that already belongs to an API run.  SQLite cannot
    drop a NOT NULL constraint in place, so rebuild the table (same approach as
    ``_ensure_scan_finding_page_id_nullable``).  Idempotent and best-effort.

    Must run AFTER every scan_finding column has been ensured, since the rebuild
    must carry the full current column set.
    """
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
        "evidence_json",
        "merged_instances",
        "poc_command",
        "poc_setup",
        "screenshot_b64",
        "finding_source",
        "validation_status",
        "validation_note",
        "api_test_run_id",
        "owasp_api_category",
        "created_at",
    ]
    column_list = ", ".join(columns)
    # On copy, drop test_run_id for anything that belongs to an API run.
    select_list = ", ".join(
        "CASE WHEN api_test_run_id IS NOT NULL THEN NULL ELSE test_run_id END "
        "AS test_run_id"
        if c == "test_run_id"
        else c
        for c in columns
    )
    with engine.connect() as conn:
        rows = list(conn.execute(sql("PRAGMA table_info(scan_finding)")))
        if not rows:
            return  # table not created yet (fresh DB handled by create_all)
        test_run_id_row = next((row for row in rows if row[1] == "test_run_id"), None)
        # row[3] == notnull flag; already nullable means this migration has run.
        if test_run_id_row is None or int(test_run_id_row[3] or 0) == 0:
            return

        conn.execute(sql("DROP TABLE IF EXISTS scan_finding_trn_migration"))
        conn.execute(sql("""
            CREATE TABLE scan_finding_trn_migration (
                id INTEGER PRIMARY KEY,
                test_run_id INTEGER REFERENCES test_run(id),
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
                evidence_json TEXT NOT NULL DEFAULT '[]',
                merged_instances TEXT NOT NULL DEFAULT '[]',
                poc_command TEXT NOT NULL DEFAULT '',
                poc_setup TEXT NOT NULL DEFAULT '',
                screenshot_b64 TEXT,
                finding_source TEXT NOT NULL DEFAULT 'unknown',
                validation_status TEXT NOT NULL DEFAULT 'unvalidated',
                validation_note TEXT,
                api_test_run_id INTEGER,
                owasp_api_category TEXT,
                created_at DATETIME NOT NULL
            )
        """))
        conn.execute(sql(f"""
            INSERT INTO scan_finding_trn_migration ({column_list})
            SELECT {select_list}
            FROM scan_finding
        """))
        conn.execute(sql("DROP TABLE scan_finding"))
        conn.execute(sql(
            "ALTER TABLE scan_finding_trn_migration RENAME TO scan_finding"
        ))
        for col in ("test_run_id", "page_id", "owasp_category", "api_test_run_id"):
            conn.execute(sql(
                f"CREATE INDEX IF NOT EXISTS ix_scan_finding_{col} "
                f"ON scan_finding ({col})"
            ))
        conn.commit()


def _ensure_sast_run_collection_id_nullable(engine: Engine) -> None:
    """Make sast_run.collection_id nullable for standalone (web) SAST runs.

    The original table created collection_id as ``NOT NULL REFERENCES
    api_collection(id)``. Standalone runs have no collection, so rebuild the
    table to drop the NOT NULL (SQLite cannot alter a constraint in place).
    Must run AFTER source_archive_path / source_filename are ensured so the
    rebuild carries the full current column set. Idempotent and best-effort.
    """
    if engine.dialect.name != "sqlite":
        return

    sql = __import__("sqlalchemy").text
    columns = [
        "id",
        "collection_id",
        "document_id",
        "source_archive_path",
        "source_filename",
        "name",
        "status",
        "triggered_by_run_type",
        "triggered_by_run_id",
        "llm_config_id",
        "leads_count",
        "error_message",
        "token_usage_json",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]
    column_list = ", ".join(columns)
    with engine.connect() as conn:
        rows = list(conn.execute(sql("PRAGMA table_info(sast_run)")))
        if not rows:
            return  # table not created yet (fresh DB handled by create_all)
        coll_row = next((row for row in rows if row[1] == "collection_id"), None)
        # row[3] == notnull flag; already nullable means this migration has run.
        if coll_row is None or int(coll_row[3] or 0) == 0:
            return

        conn.execute(sql("DROP TABLE IF EXISTS sast_run_coll_migration"))
        conn.execute(sql("""
            CREATE TABLE sast_run_coll_migration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER REFERENCES api_collection(id),
                document_id INTEGER,
                source_archive_path TEXT,
                source_filename TEXT,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                triggered_by_run_type TEXT,
                triggered_by_run_id INTEGER,
                llm_config_id INTEGER REFERENCES llm_config(id),
                leads_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                token_usage_json TEXT,
                started_at DATETIME,
                completed_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.execute(sql(f"""
            INSERT INTO sast_run_coll_migration ({column_list})
            SELECT {column_list}
            FROM sast_run
        """))
        conn.execute(sql("DROP TABLE sast_run"))
        conn.execute(sql(
            "ALTER TABLE sast_run_coll_migration RENAME TO sast_run"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_sast_run_collection_id "
            "ON sast_run (collection_id)"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_sast_run_triggered_by_run_id "
            "ON sast_run (triggered_by_run_id)"
        ))
        conn.commit()


def _ensure_llm_config_temperature_nullable(engine: Engine) -> None:
    """Make the temperature column in llm_config nullable (SQLite table rebuild)."""
    if engine.dialect.name != "sqlite":
        return

    sql = __import__("sqlalchemy").text
    with engine.connect() as conn:
        rows = list(conn.execute(sql("PRAGMA table_info(llm_config)")))
        temp_row = next((row for row in rows if row[1] == "temperature"), None)
        if temp_row is None or int(temp_row[3] or 0) == 0:
            # Column is already nullable (notnull == 0) or doesn't exist
            return

        # Build a dynamic CREATE TABLE, making only temperature nullable
        col_defs = []
        for row in rows:
            cid, name, col_type, notnull, dflt_value, pk = row
            if pk:
                col_defs.append(f"{name} {col_type} PRIMARY KEY")
            elif name == "temperature":
                col_defs.append(f"{name} {col_type}")  # nullable, no default
            else:
                parts = [f"{name} {col_type}"]
                if notnull:
                    parts.append("NOT NULL")
                if dflt_value is not None:
                    parts.append(f"DEFAULT {dflt_value}")
                col_defs.append(" ".join(parts))

        column_list = ", ".join(row[1] for row in rows)
        create_sql = (
            "CREATE TABLE llm_config_temp_nullable_migration (\n    "
            + ",\n    ".join(col_defs)
            + "\n)"
        )

        conn.execute(sql("DROP TABLE IF EXISTS llm_config_temp_nullable_migration"))
        conn.execute(sql(create_sql))
        conn.execute(sql(f"""
            INSERT INTO llm_config_temp_nullable_migration ({column_list})
            SELECT {column_list}
            FROM llm_config
        """))
        conn.execute(sql("DROP TABLE llm_config"))
        conn.execute(sql(
            "ALTER TABLE llm_config_temp_nullable_migration RENAME TO llm_config"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_llm_config_name ON llm_config (name)"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_llm_config_is_active ON llm_config (is_active)"
        ))
        conn.execute(sql(
            "CREATE INDEX IF NOT EXISTS ix_llm_config_provider_id ON llm_config (provider_id)"
        ))
        conn.commit()


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
