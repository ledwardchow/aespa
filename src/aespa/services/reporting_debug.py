from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from aespa.config import DEFAULT_DB_PATH, get_settings
from aespa.db import get_engine
from aespa.models import LLMConfig
from aespa.services.prompts.reporting import _ANALYSE_PROMPT, _WRITEUP_REPLAY_PROMPT

PROMPT_KEY_ANALYSE = "reporting.analyse"
PROMPT_KEY_WRITEUP = "reporting.writeup"
PROMPT_DEFAULTS = {
    PROMPT_KEY_ANALYSE: _ANALYSE_PROMPT,
    PROMPT_KEY_WRITEUP: _WRITEUP_REPLAY_PROMPT,
}
REPLAY_CAPTURE_SCHEMA = "aespa.reporting.replay.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def debug_db_path() -> Path:
    url = make_url(get_settings().database_url)
    raw_path = url.database
    if url.drivername.startswith("sqlite") and raw_path and raw_path != ":memory:":
        base = Path(raw_path)
    else:
        base = DEFAULT_DB_PATH
    if not base.is_absolute():
        base = Path.cwd() / base
    suffix = base.suffix or ".db"
    return base.with_name(f"{base.stem}_reporting_debug{suffix}")


def _connect() -> sqlite3.Connection:
    path = debug_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _init(conn)
    return conn


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS prompt_override (
            key TEXT PRIMARY KEY,
            prompt_text TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS prompt_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reporting_capture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL DEFAULT 'analyse_probe_batch',
            created_at TEXT NOT NULL,
            run_id INTEGER,
            url TEXT NOT NULL,
            result_texts_json TEXT NOT NULL,
            prompt TEXT NOT NULL,
            prompt_sha256 TEXT NOT NULL,
            llm_json TEXT NOT NULL,
            raw_response TEXT NOT NULL,
            findings_json TEXT NOT NULL,
            parse_error TEXT,
            source TEXT,
            base_url TEXT,
            finding_json TEXT,
            evidence_json TEXT
        );
        CREATE TABLE IF NOT EXISTS reporting_replay (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capture_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            progress_message TEXT NOT NULL,
            prompt TEXT,
            prompt_sha256 TEXT,
            prompt_version_id INTEGER,
            prompt_version_name TEXT,
            raw_response TEXT,
            findings_json TEXT NOT NULL DEFAULT '[]',
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_reporting_capture_created_at
            ON reporting_capture (created_at);
        CREATE INDEX IF NOT EXISTS ix_reporting_replay_started_at
            ON reporting_replay (started_at);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_prompt_version_key_name
            ON prompt_version (key, name);
        """
    )
    _ensure_column(conn, "reporting_capture", "kind", "TEXT NOT NULL DEFAULT 'analyse_probe_batch'")
    _ensure_column(conn, "reporting_capture", "source", "TEXT")
    _ensure_column(conn, "reporting_capture", "base_url", "TEXT")
    _ensure_column(conn, "reporting_capture", "finding_json", "TEXT")
    _ensure_column(conn, "reporting_capture", "evidence_json", "TEXT")
    _ensure_column(conn, "reporting_replay", "prompt_version_id", "INTEGER")
    _ensure_column(conn, "reporting_replay", "prompt_version_name", "TEXT")
    _ensure_builtin_prompt_versions(conn)
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _ensure_builtin_prompt_versions(conn: sqlite3.Connection) -> None:
    for key in PROMPT_DEFAULTS:
        row = conn.execute(
            "SELECT id FROM prompt_version WHERE key = ? AND is_builtin = 1",
            (key,),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO prompt_version (
                    key, name, prompt_text, is_builtin, created_at, updated_at
                )
                VALUES (?, 'Default', ?, 1, ?, ?)
                """,
                (key, _default_prompt(key), _now(), _now()),
            )


def is_capture_enabled() -> bool:
    try:
        from sqlalchemy import text

        with get_engine().connect() as conn:
            row = conn.execute(
                text("SELECT capture_enabled FROM reporting_debug_config WHERE id = 1")
            ).first()
        return bool(row and row[0])
    except Exception:
        return False


def _default_prompt(key: str) -> str:
    if key not in PROMPT_DEFAULTS:
        raise KeyError(key)
    return PROMPT_DEFAULTS[key]


def list_prompts() -> list[dict[str, Any]]:
    return [get_prompt(key) for key in (PROMPT_KEY_ANALYSE, PROMPT_KEY_WRITEUP)]


def _prompt_version_from_row(row: sqlite3.Row) -> dict[str, Any]:
    key = row["key"]
    is_builtin = bool(row["is_builtin"])
    return {
        "id": row["id"],
        "key": key,
        "name": row["name"],
        "prompt_text": _default_prompt(key) if is_builtin else row["prompt_text"],
        "is_builtin": is_builtin,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_prompt_versions(key: str = PROMPT_KEY_ANALYSE) -> list[dict[str, Any]]:
    _default_prompt(key)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM prompt_version
            WHERE key = ?
            ORDER BY is_builtin DESC, datetime(updated_at) DESC, id DESC
            """,
            (key,),
        ).fetchall()
    return [_prompt_version_from_row(row) for row in rows]


def get_prompt_version(version_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM prompt_version WHERE id = ?",
            (version_id,),
        ).fetchone()
    return _prompt_version_from_row(row) if row else None


def get_builtin_prompt_version(key: str) -> dict[str, Any]:
    _default_prompt(key)
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM prompt_version WHERE key = ? AND is_builtin = 1",
            (key,),
        ).fetchone()
    if row is None:
        raise RuntimeError(f"missing builtin prompt version for {key}")
    return _prompt_version_from_row(row)


def create_prompt_version(
    *,
    key: str,
    name: str,
    prompt_text: str | None = None,
) -> dict[str, Any]:
    default_text = _default_prompt(key)
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Prompt version name is required")
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO prompt_version (
                key, name, prompt_text, is_builtin, created_at, updated_at
            )
            VALUES (?, ?, ?, 0, ?, ?)
            """,
            (key, clean_name, prompt_text or default_text, now, now),
        )
        conn.commit()
        version_id = int(cur.lastrowid)
    version = get_prompt_version(version_id)
    if version is None:
        raise RuntimeError("failed to create prompt version")
    return version


def update_prompt_version(
    version_id: int,
    *,
    name: str | None = None,
    prompt_text: str | None = None,
) -> dict[str, Any]:
    version = get_prompt_version(version_id)
    if version is None:
        raise KeyError(version_id)
    if version["is_builtin"]:
        raise PermissionError("Default prompt versions cannot be edited")
    updates: dict[str, Any] = {"updated_at": _now()}
    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Prompt version name is required")
        updates["name"] = clean_name
    if prompt_text is not None:
        if not prompt_text.strip():
            raise ValueError("Prompt text is required")
        updates["prompt_text"] = prompt_text
    columns = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [version_id]
    with _connect() as conn:
        conn.execute(f"UPDATE prompt_version SET {columns} WHERE id = ?", values)
        conn.commit()
    updated = get_prompt_version(version_id)
    if updated is None:
        raise RuntimeError("failed to update prompt version")
    return updated


def delete_prompt_version(version_id: int) -> None:
    version = get_prompt_version(version_id)
    if version is None:
        raise KeyError(version_id)
    if version["is_builtin"]:
        raise PermissionError("Default prompt versions cannot be deleted")
    with _connect() as conn:
        conn.execute("DELETE FROM prompt_version WHERE id = ?", (version_id,))
        conn.commit()


def get_prompt(key: str = PROMPT_KEY_ANALYSE) -> dict[str, Any]:
    _default_prompt(key)
    with _connect() as conn:
        row = conn.execute(
            "SELECT prompt_text, updated_at FROM prompt_override WHERE key = ?",
            (key,),
        ).fetchone()
    if row:
        return {
            "key": key,
            "prompt_text": row["prompt_text"],
            "is_default": False,
            "updated_at": row["updated_at"],
        }
    return {
        "key": key,
        "prompt_text": _default_prompt(key),
        "is_default": True,
        "updated_at": None,
    }


def save_prompt(prompt_text: str, key: str = PROMPT_KEY_ANALYSE) -> dict[str, Any]:
    _default_prompt(key)
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO prompt_override (key, prompt_text, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                prompt_text = excluded.prompt_text,
                updated_at = excluded.updated_at
            """,
            (key, prompt_text, now),
        )
        conn.commit()
    return get_prompt(key)


def reset_prompt(key: str = PROMPT_KEY_ANALYSE) -> dict[str, Any]:
    _default_prompt(key)
    with _connect() as conn:
        conn.execute("DELETE FROM prompt_override WHERE key = ?", (key,))
        conn.commit()
    return get_prompt(key)


def capture_reporting_batch(
    *,
    run_id: int | None,
    url: str,
    result_texts: list[str],
    prompt: str,
    prompt_sha256: str,
    llm: dict[str, Any],
    raw_response: str,
    findings: list[dict],
    parse_error: str | None = None,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO reporting_capture (
                kind, created_at, run_id, url, result_texts_json, prompt, prompt_sha256,
                llm_json, raw_response, findings_json, parse_error
            )
            VALUES ('analyse_probe_batch', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                run_id,
                url,
                json.dumps(result_texts, ensure_ascii=False),
                prompt,
                prompt_sha256,
                json.dumps(llm, ensure_ascii=False),
                raw_response,
                json.dumps(findings, ensure_ascii=False),
                parse_error,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def capture_writeup(
    *,
    run_id: int,
    source: str,
    base_url: str,
    url: str,
    finding: dict[str, Any],
    evidence: dict[str, Any],
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO reporting_capture (
                kind, created_at, run_id, url, result_texts_json, prompt, prompt_sha256,
                llm_json, raw_response, findings_json, parse_error, source, base_url,
                finding_json, evidence_json
            )
            VALUES (
                'writeup', ?, ?, ?, '[]', '', '', '{}', '', ?, NULL, ?, ?, ?, ?
            )
            """,
            (
                _now(),
                run_id,
                url,
                json.dumps([finding], ensure_ascii=False, default=str),
                source,
                base_url,
                json.dumps(finding, ensure_ascii=False, default=str),
                json.dumps(evidence, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def _capture_from_row(row: sqlite3.Row, *, include_payload: bool = False) -> dict[str, Any]:
    item = {
        "id": row["id"],
        "kind": row["kind"],
        "created_at": row["created_at"],
        "run_id": row["run_id"],
        "url": row["url"],
        "prompt_sha256": row["prompt_sha256"],
        "llm": json.loads(row["llm_json"] or "{}"),
        "finding_count": len(json.loads(row["findings_json"] or "[]")),
        "parse_error": row["parse_error"],
        "source": row["source"],
    }
    if include_payload:
        item.update(
            {
                "schema": REPLAY_CAPTURE_SCHEMA,
                "capture_id": row["id"],
                "kind": row["kind"],
                "result_texts": json.loads(row["result_texts_json"] or "[]"),
                "prompt": row["prompt"],
                "raw_response": row["raw_response"],
                "findings": json.loads(row["findings_json"] or "[]"),
                "source": row["source"],
                "base_url": row["base_url"],
                "finding": json.loads(row["finding_json"] or "{}"),
                "evidence": json.loads(row["evidence_json"] or "{}"),
            }
        )
    return item


def list_captures(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM reporting_capture
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_capture_from_row(row) for row in rows]


def get_capture(capture_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM reporting_capture WHERE id = ?",
            (capture_id,),
        ).fetchone()
    return _capture_from_row(row, include_payload=True) if row else None


def _prompt_key_for_capture(capture: dict[str, Any]) -> str:
    return (
        PROMPT_KEY_ANALYSE
        if str(capture.get("kind") or "analyse_probe_batch") == "analyse_probe_batch"
        else PROMPT_KEY_WRITEUP
    )


def create_replay(capture_id: int, prompt_version_id: int | None = None) -> dict[str, Any]:
    capture = get_capture(capture_id)
    if capture is None:
        raise KeyError(capture_id)
    expected_key = _prompt_key_for_capture(capture)
    if prompt_version_id is None:
        prompt_version = get_builtin_prompt_version(expected_key)
    else:
        prompt_version = get_prompt_version(prompt_version_id)
        if prompt_version is None:
            raise KeyError(prompt_version_id)
        if prompt_version["key"] != expected_key:
            raise ValueError("Prompt version is not compatible with this capture type")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO reporting_replay (
                capture_id, status, started_at, progress_message, prompt_version_id,
                prompt_version_name, findings_json
            )
            VALUES (?, 'queued', ?, 'Queued', ?, ?, '[]')
            """,
            (
                capture_id,
                _now(),
                prompt_version["id"],
                prompt_version["name"],
            ),
        )
        conn.commit()
        replay_id = int(cur.lastrowid)
    replay = get_replay(replay_id)
    if replay is None:
        raise RuntimeError("failed to create replay")
    return replay


def get_replay(replay_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM reporting_replay WHERE id = ?",
            (replay_id,),
        ).fetchone()
    return _replay_from_row(row) if row else None


def list_replays(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM reporting_replay
            ORDER BY datetime(started_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_replay_from_row(row) for row in rows]


def _replay_from_row(row: sqlite3.Row) -> dict[str, Any]:
    findings = json.loads(row["findings_json"] or "[]")
    return {
        "id": row["id"],
        "capture_id": row["capture_id"],
        "status": row["status"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "progress_message": row["progress_message"],
        "prompt_sha256": row["prompt_sha256"],
        "prompt_version_id": row["prompt_version_id"],
        "prompt_version_name": row["prompt_version_name"],
        "error": row["error"],
        "finding_count": len(findings),
        "findings": findings,
    }


def _update_replay(replay_id: int, **fields: Any) -> None:
    if not fields:
        return
    columns = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [replay_id]
    with _connect() as conn:
        conn.execute(f"UPDATE reporting_replay SET {columns} WHERE id = ?", values)
        conn.commit()


async def run_replay(replay_id: int, config: LLMConfig) -> None:
    replay = get_replay(replay_id)
    if replay is None:
        return
    capture = get_capture(int(replay["capture_id"]))
    if capture is None:
        _update_replay(
            replay_id,
            status="failed",
            completed_at=_now(),
            progress_message="Capture no longer exists",
            error="Capture no longer exists",
        )
        return
    try:
        _update_replay(
            replay_id,
            status="running",
            progress_message="Building reporting prompt",
        )
        capture_kind = str(capture.get("kind") or "analyse_probe_batch")
        prompt_version_id = replay.get("prompt_version_id")
        prompt_version = (
            get_prompt_version(int(prompt_version_id))
            if prompt_version_id is not None
            else get_builtin_prompt_version(_prompt_key_for_capture(capture))
        )
        if prompt_version is None:
            raise RuntimeError("Prompt version no longer exists")
        prompt_template = str(prompt_version["prompt_text"])
        from aespa.services import llm as llm_svc

        _update_replay(replay_id, progress_message="Calling LLM")
        if capture_kind == "analyse_probe_batch":
            result = await llm_svc.replay_reporting_capture(
                config,
                capture,
                prompt_template=prompt_template,
            )
        else:
            result = await llm_svc.replay_reporting_writeup_capture(
                config,
                capture,
                prompt_template=prompt_template,
            )
        findings = result.get("findings") or []
        _update_replay(
            replay_id,
            status="complete",
            completed_at=_now(),
            progress_message=f"Complete: parsed {len(findings)} finding(s)",
            prompt=result.get("prompt"),
            prompt_sha256=result.get("prompt_sha256"),
            prompt_version_name=prompt_version["name"],
            raw_response=result.get("raw_response"),
            findings_json=json.dumps(findings, ensure_ascii=False),
            error=None,
        )
    except Exception as exc:
        _update_replay(
            replay_id,
            status="failed",
            completed_at=_now(),
            progress_message="Replay failed",
            error=str(exc),
        )
