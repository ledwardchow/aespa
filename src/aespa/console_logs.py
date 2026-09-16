"""Optional SQLite persistence for terminal console logs."""

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class ConsoleLogStore:
    """Write complete console log records to an independent SQLite database."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self.last_error = ""
        self.enabled = self._read_enabled_setting()

    def _read_enabled_setting(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            connection = sqlite3.connect(
                f"file:{self.path}?mode=ro", uri=True, timeout=1
            )
            try:
                row = connection.execute(
                    "SELECT value FROM console_log_settings WHERE key = 'enabled'"
                ).fetchone()
            finally:
                connection.close()
        except sqlite3.Error:
            return False
        return bool(row and row[0] == "1")

    def set_enabled(self, enabled: bool) -> bool:
        """Persist the setting and return whether it was applied."""
        with self._lock:
            try:
                if enabled:
                    connection = self._open_connection()
                elif self.path.exists():
                    connection = self._open_connection()
                else:
                    self.enabled = False
                    self.last_error = ""
                    return True
                connection.execute(
                    """
                    INSERT INTO console_log_settings (key, value)
                    VALUES ('enabled', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    ("1" if enabled else "0",),
                )
                connection.commit()
                self.enabled = enabled
                self.last_error = ""
                if not enabled:
                    self._close_connection()
                return True
            except (OSError, sqlite3.Error) as exc:
                self.last_error = str(exc)
                self.enabled = False
                self._close_connection()
                return False

    def append(self, record: logging.LogRecord, view: str) -> None:
        """Save one record. Failures are retained for the settings screen."""
        if not self.enabled:
            return
        exception = None
        if record.exc_info:
            exception = logging.Formatter().formatException(record.exc_info)
        try:
            run_id = getattr(record, "aespa_llm_run_id", None)
            with self._lock:
                connection = self._open_connection()
                connection.execute(
                    """
                    INSERT INTO console_logs (
                        created_at, view, logger, level, message, exception,
                        llm_call_id, llm_direction, llm_operation, llm_kind,
                        llm_context, llm_payload, run_kind, run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.fromtimestamp(
                            record.created, timezone.utc
                        ).isoformat(),
                        view,
                        record.name,
                        record.levelname,
                        record.getMessage(),
                        exception,
                        getattr(record, "aespa_llm_call_id", None),
                        getattr(record, "aespa_llm_direction", None),
                        getattr(record, "aespa_llm_operation", None),
                        getattr(record, "aespa_llm_kind", None),
                        getattr(record, "aespa_llm_context", None),
                        getattr(record, "aespa_llm_payload", None),
                        getattr(record, "aespa_llm_run_kind", None),
                        int(run_id) if run_id is not None else None,
                    ),
                )
                connection.commit()
                self.last_error = ""
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            with self._lock:
                self.last_error = str(exc)
                self.enabled = False
                self._close_connection()

    def close(self) -> None:
        with self._lock:
            self._close_connection()

    def _open_connection(self) -> sqlite3.Connection:
        if self._connection is not None:
            return self._connection
        self.path.parent.mkdir(parents=True, exist_ok=True)
        created = not self.path.exists()
        connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS console_log_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS console_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    view TEXT NOT NULL,
                    logger TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    exception TEXT,
                    llm_call_id INTEGER,
                    llm_direction TEXT,
                    llm_operation TEXT,
                    llm_kind TEXT,
                    llm_context TEXT,
                    llm_payload TEXT,
                    run_kind TEXT,
                    run_id INTEGER
                );

                CREATE INDEX IF NOT EXISTS ix_console_logs_created_at
                    ON console_logs (created_at);
                CREATE INDEX IF NOT EXISTS ix_console_logs_view
                    ON console_logs (view);
                CREATE INDEX IF NOT EXISTS ix_console_logs_llm_call_id
                    ON console_logs (llm_call_id);
                """
            )
            connection.commit()
        except Exception:
            connection.close()
            raise
        if created:
            with contextlib.suppress(OSError):
                os.chmod(self.path, 0o600)
        self._connection = connection
        return connection

    def _close_connection(self) -> None:
        if self._connection is None:
            return
        self._connection.close()
        self._connection = None
