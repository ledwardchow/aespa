from __future__ import annotations

import json
import sqlite3

from scripts.backfill_daybreak_programs import backfill, changes, historical_program


def test_historical_program_labels_subscription_models():
    for model in ("gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.6-terra", "unknown"):
        assert historical_program("openai_codex", model) == "daybreak_blue"
        assert historical_program("openai_chatgpt_plan", model) == "daybreak_blue"
    for model in ("gpt-daybreak-red-latest", "gpt-5.6-cyber"):
        assert historical_program("openai_codex", model) == "daybreak_red"
    assert historical_program("openai", "gpt-5.6-sol") is None


def test_changes_preserves_nonempty_metadata():
    saved = {
        "scan_models": {
            "primary": {
                "provider": "openai_codex",
                "model": "gpt-5.6-sol",
                "daybreak_programs": ["daybreak_red"],
            }
        }
    }
    assert changes(saved) == (saved, False)


def test_backfill_extension_results_dry_run_backup_and_idempotence(tmp_path):
    database = tmp_path / "aespa.benchmarking.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE benchmarking_scan_result "
            "(id INTEGER PRIMARY KEY, run_id INTEGER, rows_json TEXT)"
        )
        for result_id, run_id, provider, model, programs in (
            (111, -7, "openai_codex", "gpt-5.6-sol", None),
            (112, 0, "openai_chatgpt_plan", "gpt-5.6-luna", None),
            (113, 42, "openai_codex", "gpt-5.6-cyber", None),
            (114, 43, "openai", "gpt-5.6-terra", None),
            (115, 44, "openai_codex", "gpt-6-sol", ["daybreak_red"]),
        ):
            primary = {"provider": provider, "model": model}
            if programs is not None:
                primary["daybreak_programs"] = programs
            connection.execute(
                "INSERT INTO benchmarking_scan_result VALUES (?, ?, ?)",
                (result_id, run_id, json.dumps({"scan_models": {"primary": primary}})),
            )
    assert backfill(database) == 3
    assert not list(tmp_path.glob("*.bak"))
    with sqlite3.connect(database) as connection:
        assert (
            "daybreak_programs"
            not in json.loads(
                connection.execute(
                    "SELECT rows_json FROM benchmarking_scan_result WHERE id = 111"
                ).fetchone()[0]
            )["scan_models"]["primary"]
        )
    assert backfill(database, apply=True) == 3
    backups = list(tmp_path.glob("*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert (
            "daybreak_programs"
            not in json.loads(
                connection.execute(
                    "SELECT rows_json FROM benchmarking_scan_result WHERE id = 111"
                ).fetchone()[0]
            )["scan_models"]["primary"]
        )
    with sqlite3.connect(database) as connection:
        rows = dict(
            connection.execute("SELECT id, rows_json FROM benchmarking_scan_result")
        )
    assert json.loads(rows[111])["scan_models"]["primary"]["daybreak_programs"] == [
        "daybreak_blue"
    ]
    assert json.loads(rows[112])["scan_models"]["primary"]["daybreak_programs"] == [
        "daybreak_blue"
    ]
    assert json.loads(rows[113])["scan_models"]["primary"]["daybreak_programs"] == [
        "daybreak_red"
    ]
    assert "daybreak_programs" not in json.loads(rows[114])["scan_models"]["primary"]
    assert json.loads(rows[115])["scan_models"]["primary"]["daybreak_programs"] == [
        "daybreak_red"
    ]
    assert backfill(database, apply=True) == 0
    assert len(list(tmp_path.glob("*.bak"))) == 1
