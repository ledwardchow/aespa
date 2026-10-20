"""Preview or backfill Daybreak labels in the benchmarking extension database.

Pass the path to aespa.benchmarking.db. The default is a read-only preview.
--apply makes a SQLite backup before updating saved benchmark results.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROVIDERS = {"openai_codex", "openai_chatgpt_plan"}
RED_MODELS = {"gpt-daybreak-red-latest", "gpt-5.6-cyber"}


def historical_program(provider: str, model: str) -> str | None:
    if provider not in PROVIDERS:
        return None
    return "daybreak_red" if model in RED_MODELS else "daybreak_blue"


def changes(saved: dict) -> tuple[dict, bool]:
    models = saved.get("scan_models")
    primary = models.get("primary") if isinstance(models, dict) else None
    if not isinstance(primary, dict) or primary.get("daybreak_programs"):
        return saved, False
    program = historical_program(
        str(primary.get("provider") or ""),
        str(primary.get("model") or primary.get("name") or ""),
    )
    if program is None:
        return saved, False
    primary["daybreak_programs"] = [program]
    return saved, True


def backfill(database: Path, apply: bool = False) -> int:
    database = database.resolve()
    mode = "rw" if apply else "ro"
    connection = sqlite3.connect(f"{database.as_uri()}?mode={mode}", uri=True)
    try:
        rows = connection.execute(
            "SELECT id, rows_json FROM benchmarking_scan_result ORDER BY id"
        ).fetchall()
        updates = []
        for result_id, raw in rows:
            try:
                saved = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(saved, dict):
                continue
            saved, changed = changes(saved)
            if changed:
                program = saved["scan_models"]["primary"]["daybreak_programs"][0]
                print(f"benchmark result #{result_id}: {program}")
                updates.append((json.dumps(saved), result_id))
        if apply and updates:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup_path = database.with_name(f"{database.name}.daybreak-{stamp}.bak")
            with sqlite3.connect(backup_path) as backup:
                connection.backup(backup)
            print(f"Backup: {backup_path}")
            with connection:
                connection.executemany(
                    "UPDATE benchmarking_scan_result SET rows_json = ? WHERE id = ?",
                    updates,
                )
        print(f"{len(updates)} result(s) {'updated' if apply else 'would be updated'}")
        return len(updates)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    backfill(args.database, args.apply)


if __name__ == "__main__":
    main()
