"""One-time Daybreak labels for historical ChatGPT subscription run usage.

Run with a database path to preview changes. Add --apply to write them after
reviewing the preview. This script does not run during AESPA startup.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

PROVIDERS = {"openai_codex", "openai_chatgpt_plan"}
BLUE_MODELS = {
    "gpt-6-sol",
    "gpt-6-luna",
    "gpt-6.1-sol",
    "gpt-6-astra",
    "gpt-daybreak-blue-latest",
}
RED_MODELS = {"gpt-daybreak-red-latest", "gpt-5.6-cyber"}
TABLES = ("test_run", "api_test_run", "sast_run")


def historical_program(provider: str, model: str) -> str | None:
    if provider not in PROVIDERS:
        return None
    if model in RED_MODELS:
        return "daybreak_red"
    if model in BLUE_MODELS:
        return "daybreak_blue"
    return None


def changes(usage: dict) -> tuple[dict, bool]:
    changed = False
    for key, counts in usage.items():
        if not isinstance(counts, dict):
            continue
        model = counts.get("model") or key.split("::", 1)[0]
        program = historical_program(str(counts.get("provider") or ""), str(model))
        if not program or "daybreak_programs" in counts:
            continue
        if not (counts.get("input", 0) or counts.get("output", 0)):
            continue
        counts["daybreak_programs"] = [program]
        changed = True
    return usage, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    mode = "rw" if args.apply else "ro"
    connection = sqlite3.connect(
        f"file:{args.database.resolve()}?mode={mode}", uri=True
    )
    try:
        for table in TABLES:
            for run_id, raw in connection.execute(
                f"SELECT id, token_usage_json FROM {table} WHERE token_usage_json IS NOT NULL"
            ):
                try:
                    usage = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                if not isinstance(usage, dict):
                    continue
                updated, changed = changes(usage)
                if not changed:
                    continue
                print(
                    f"{table} #{run_id}: {[(key, value['daybreak_programs']) for key, value in updated.items() if isinstance(value, dict) and value.get('daybreak_programs')]}"
                )
                if args.apply:
                    connection.execute(
                        f"UPDATE {table} SET token_usage_json = ? WHERE id = ?",
                        (json.dumps(updated), run_id),
                    )
        if args.apply:
            connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
