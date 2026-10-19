"""Backfill daily LLM usage from dated scan records and single-day SAST runs.

Run without --apply to preview. This is a one-time operation for a database
whose daily ledger is empty. It leaves monthly totals unchanged.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

COUNTERS = (
    "requests",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "ai_credits",
    "factory_credits",
)
INCLUSIVE_INPUT_PROVIDERS = {
    "openai",
    "openai_compatible",
    "openrouter",
    "azure_openai",
    "azure_foundry",
    "azure_foundry_openai",
    "google",
    "google_vertex",
    "openai_codex",
    "openai_chatgpt_plan",
    "google_antigravity",
    "bedrock",
}


def _local_day(timestamp: str) -> str:
    value = datetime.fromisoformat(timestamp)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().date().isoformat()


def _plan(
    connection: sqlite3.Connection, *, include_sast: bool = True
) -> tuple[list[tuple], dict[str, int]]:
    monthly = {}
    tiers = defaultdict(set)
    for row in connection.execute(
        "SELECT month, provider, model, service_tier, requests, input_tokens, "
        "output_tokens, cache_read_tokens, cache_write_tokens, ai_credits, "
        "factory_credits, created_at, updated_at FROM llm_usage_month"
    ):
        key = tuple(row[:4])
        monthly[key] = dict(zip(COUNTERS, row[4:11], strict=True))
        tiers[key[:3]].add(key[3])

    single_day = {}
    for row in connection.execute(
        "SELECT month, provider, model, service_tier, created_at, updated_at "
        "FROM llm_usage_month"
    ):
        month, provider, model, tier, created_at, updated_at = row
        first_day = _local_day(created_at)
        if first_day == _local_day(updated_at) and first_day[:7] == month:
            single_day[(month, provider, model, tier)] = first_day

    grouped = defaultdict(lambda: dict.fromkeys(COUNTERS, 0))
    stats = defaultdict(int)
    for row in connection.execute(
        "SELECT created_at, json_extract(data_json, '$.provider'), "
        "json_extract(data_json, '$.model'), "
        "json_extract(data_json, '$.uncached_input_tokens'), "
        "json_extract(data_json, '$.output_tokens'), "
        "json_extract(data_json, '$.cache_read_tokens') "
        "FROM scan_log WHERE phase = 'llm_cache'"
    ):
        stats["timestamped_calls"] += 1
        timestamp, provider, model, input_tokens, output_tokens, cache_read = row
        if not provider or not model:
            stats["invalid_calls"] += 1
            continue
        try:
            day = _local_day(timestamp)
            counts = [int(input_tokens), int(output_tokens), int(cache_read)]
        except (TypeError, ValueError, OverflowError):
            stats["invalid_calls"] += 1
            continue
        if any(count < 0 for count in counts):
            stats["invalid_calls"] += 1
            continue
        candidate_tiers = tiers.get((day[:7], provider, model), set())
        if len(candidate_tiers) != 1:
            stats["unmatched_or_ambiguous_calls"] += 1
            continue
        tier = next(iter(candidate_tiers))
        if (day[:7], provider, model, tier) in single_day:
            stats["covered_by_same_day_monthly_row_calls"] += 1
            continue
        counters = grouped[(day, provider, model, tier)]
        counters["requests"] += 1
        counters["input_tokens"] += counts[0]
        counters["output_tokens"] += counts[1]
        counters["cache_read_tokens"] += counts[2]

    for key, day in single_day.items():
        grouped[(day, *key[1:])] = monthly[key].copy()
        stats["same_day_monthly_rows"] += 1

    if include_sast:
        logged_sast_runs = {
            run_id
            for (run_id,) in connection.execute(
                "SELECT DISTINCT test_run_id FROM scan_log "
                "WHERE phase = 'llm_cache' AND run_kind = 'sast'"
            )
        }
        sast_groups = defaultdict(lambda: dict.fromkeys(COUNTERS, 0))
        for run_id, created, started, completed, raw in connection.execute(
            "SELECT id, created_at, started_at, completed_at, token_usage_json "
            "FROM sast_run WHERE token_usage_json IS NOT NULL"
        ):
            if not started or not completed or run_id in logged_sast_runs:
                continue
            day = _local_day(started)
            if day != _local_day(created) or day != _local_day(completed):
                continue
            try:
                usage = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(usage, dict):
                continue
            for bucket, counts in usage.items():
                if not isinstance(counts, dict) or not counts.get("provider"):
                    continue
                model = str(counts.get("model") or bucket)
                tier = str(counts.get("service_tier") or "")
                if not tier and "#" in model:
                    name, suffix = model.rsplit("#", 1)
                    if suffix in {"fast", "priority"}:
                        model, tier = name, suffix
                provider = str(counts["provider"])
                month_key = (day[:7], provider, model, tier)
                if month_key not in monthly or month_key in single_day:
                    continue
                try:
                    values = {
                        "requests": max(0, int(counts.get("requests") or 0)),
                        "input_tokens": max(0, int(counts.get("input") or 0)),
                        "output_tokens": max(0, int(counts.get("output") or 0)),
                        "cache_read_tokens": max(0, int(counts.get("cache_read") or 0)),
                        "cache_write_tokens": max(
                            0, int(counts.get("cache_write") or 0)
                        ),
                        "ai_credits": max(0.0, float(counts.get("ai_credits") or 0)),
                        "factory_credits": max(
                            0.0, float(counts.get("factory_credits") or 0)
                        ),
                    }
                except (TypeError, ValueError, OverflowError):
                    continue
                if provider == "bedrock_mantle":
                    includes_cache = not model.lower().startswith(
                        ("anthropic.", "claude-")
                    )
                else:
                    includes_cache = provider in INCLUSIVE_INPUT_PROVIDERS
                if includes_cache:
                    values["input_tokens"] = max(
                        0,
                        values["input_tokens"]
                        - values["cache_read_tokens"]
                        - values["cache_write_tokens"],
                    )
                row = sast_groups[(day, provider, model, tier)]
                for field in COUNTERS:
                    row[field] += values[field]

        sast_by_month = defaultdict(lambda: dict.fromkeys(COUNTERS, 0))
        for (day, provider, model, tier), counts in sast_groups.items():
            total = sast_by_month[(day[:7], provider, model, tier)]
            for field in COUNTERS:
                total[field] += counts[field]
        existing_by_month = defaultdict(lambda: dict.fromkeys(COUNTERS, 0))
        for (day, provider, model, tier), counts in grouped.items():
            total = existing_by_month[(day[:7], provider, model, tier)]
            for field in COUNTERS:
                total[field] += counts[field]
        accepted = {
            key
            for key, counts in sast_by_month.items()
            if all(
                existing_by_month[key][field] + counts[field]
                <= monthly[key][field] + 1e-9
                for field in COUNTERS
            )
        }
        for (day, provider, model, tier), counts in sast_groups.items():
            if (day[:7], provider, model, tier) not in accepted:
                stats["rejected_sast_calls"] += counts["requests"]
                continue
            row = grouped[(day, provider, model, tier)]
            for field in COUNTERS:
                row[field] += counts[field]
            stats["sast_calls"] += counts["requests"]
        stats["sast_rows"] = len(sast_groups)

    by_month = defaultdict(lambda: dict.fromkeys(COUNTERS, 0))
    for (day, provider, model, tier), counts in grouped.items():
        total = by_month[(day[:7], provider, model, tier)]
        for field in COUNTERS:
            total[field] += counts[field]
    rejected = {
        key
        for key, counts in by_month.items()
        if any(counts[field] > monthly[key][field] for field in COUNTERS)
    }
    rows = []
    for key, counts in sorted(grouped.items()):
        if (key[0][:7], *key[1:]) in rejected:
            stats["over_monthly_total_calls"] += counts["requests"]
            continue
        rows.append((*key, *(counts[field] for field in COUNTERS)))
        stats["backfilled_calls"] += counts["requests"]
    stats["daily_rows"] = len(rows)
    stats["rejected_monthly_groups"] = len(rejected)
    return rows, dict(stats)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Path to aespa.db")
    parser.add_argument(
        "--apply", action="store_true", help="Write the planned daily rows"
    )
    args = parser.parse_args()
    database = args.database.resolve(strict=True)
    mode = "rw" if args.apply else "ro"
    connection = sqlite3.connect(f"file:{database}?mode={mode}", uri=True, timeout=30)
    try:
        if args.apply:
            connection.execute("BEGIN IMMEDIATE")
        else:
            connection.execute("PRAGMA query_only=ON")
        base_rows, _ = _plan(connection, include_sast=False)
        rows, stats = _plan(connection)
        existing = list(
            connection.execute(
                "SELECT day, provider, model, service_tier, requests, input_tokens, "
                "output_tokens, cache_read_tokens, cache_write_tokens, "
                "ai_credits, factory_credits FROM llm_usage_day "
                "ORDER BY day, provider, model, service_tier"
            )
        )
        if existing and existing not in (base_rows, rows):
            raise ValueError(
                "Daily usage differs from this plan; refusing to replace it"
            )
        for key, value in sorted(stats.items()):
            print(f"{key}: {value}")
        if existing == rows:
            print("saved: already present")
        elif args.apply:
            connection.executemany(
                "INSERT INTO llm_usage_day "
                "(day, provider, model, service_tier, requests, input_tokens, "
                "output_tokens, cache_read_tokens, cache_write_tokens, "
                "ai_credits, factory_credits, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "ON CONFLICT(day, provider, model, service_tier) DO UPDATE SET "
                "requests=excluded.requests, input_tokens=excluded.input_tokens, "
                "output_tokens=excluded.output_tokens, "
                "cache_read_tokens=excluded.cache_read_tokens, "
                "cache_write_tokens=excluded.cache_write_tokens, "
                "ai_credits=excluded.ai_credits, "
                "factory_credits=excluded.factory_credits, "
                "updated_at=CURRENT_TIMESTAMP",
                rows,
            )
            saved = connection.execute("SELECT COUNT(*) FROM llm_usage_day").fetchone()[
                0
            ]
            if saved != len(rows):
                raise RuntimeError("Daily row count changed while backfilling")
            connection.commit()
            print("saved: yes")
        else:
            print("saved: no (preview)")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
