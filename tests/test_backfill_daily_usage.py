from __future__ import annotations

import json
import sqlite3

from scripts.backfill_daily_usage import _plan


def test_backfill_uses_exact_logs_and_same_day_monthly_rows():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE llm_usage_month (
            month TEXT, provider TEXT, model TEXT, service_tier TEXT,
            requests INTEGER, input_tokens INTEGER, output_tokens INTEGER,
            cache_read_tokens INTEGER, cache_write_tokens INTEGER,
            ai_credits REAL, factory_credits REAL,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE scan_log (
            created_at TEXT, phase TEXT, data_json TEXT,
            run_kind TEXT, test_run_id INTEGER
        );
        CREATE TABLE sast_run (
            id INTEGER, created_at TEXT, started_at TEXT,
            completed_at TEXT, token_usage_json TEXT
        );
        """
    )
    connection.executemany(
        "INSERT INTO llm_usage_month VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "2026-10",
                "openai",
                "same-day",
                "",
                3,
                300,
                30,
                0,
                0,
                0,
                0,
                "2026-10-18 01:00:00",
                "2026-10-18 02:00:00",
            ),
            (
                "2026-10",
                "openai",
                "dated",
                "",
                3,
                300,
                30,
                0,
                0,
                0,
                0,
                "2026-10-17 01:00:00",
                "2026-10-19 02:00:00",
            ),
            (
                "2026-10",
                "openai",
                "tiered",
                "",
                3,
                300,
                30,
                0,
                0,
                0,
                0,
                "2026-10-17 01:00:00",
                "2026-10-19 02:00:00",
            ),
            (
                "2026-10",
                "openai",
                "tiered",
                "fast",
                2,
                200,
                20,
                0,
                0,
                0,
                0,
                "2026-10-17 01:00:00",
                "2026-10-19 02:00:00",
            ),
            (
                "2026-10",
                "openai",
                "over-month",
                "",
                1,
                50,
                5,
                0,
                0,
                0,
                0,
                "2026-10-17 01:00:00",
                "2026-10-19 02:00:00",
            ),
            (
                "2026-10",
                "openai",
                "sast-only",
                "",
                2,
                100,
                20,
                50,
                0,
                0,
                0,
                "2026-10-17 01:00:00",
                "2026-10-19 02:00:00",
            ),
        ],
    )
    for model, day in [
        ("same-day", "2026-10-18"),
        ("dated", "2026-10-17"),
        ("tiered", "2026-10-17"),
        ("over-month", "2026-10-17"),
    ]:
        connection.execute(
            "INSERT INTO scan_log VALUES (?,?,?,?,?)",
            (
                f"{day} 02:00:00",
                "llm_cache",
                json.dumps(
                    {
                        "provider": "openai",
                        "model": model,
                        "uncached_input_tokens": 100,
                        "output_tokens": 10,
                        "cache_read_tokens": 0,
                    }
                ),
                "web",
                1,
            ),
        )
    connection.execute(
        "INSERT INTO sast_run VALUES (?,?,?,?,?)",
        (
            42,
            "2026-10-18 01:00:00",
            "2026-10-18 02:00:00",
            "2026-10-18 03:00:00",
            json.dumps(
                {
                    "sast-only": {
                        "provider": "openai",
                        "requests": 2,
                        "input": 150,
                        "output": 20,
                        "cache_read": 50,
                    }
                }
            ),
        ),
    )

    rows, stats = _plan(connection)
    by_model = {row[2]: row for row in rows}
    assert by_model["same-day"][4:7] == (3, 300, 30)
    assert by_model["dated"][4:7] == (1, 100, 10)
    assert by_model["sast-only"][4:9] == (2, 100, 20, 50, 0)
    assert "tiered" not in by_model
    assert "over-month" not in by_model
    assert stats["backfilled_calls"] == 6
    assert stats["sast_calls"] == 2
    assert stats["unmatched_or_ambiguous_calls"] == 1
    assert stats["rejected_monthly_groups"] == 1
    base_rows, _ = _plan(connection, include_sast=False)
    assert not any(row[2] == "sast-only" for row in base_rows)
