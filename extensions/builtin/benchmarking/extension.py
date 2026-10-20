from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, Table, insert, inspect
from sqlmodel import select

from aespa.db import get_engine

from . import models
from .router import build_router


def _migrate_renamed_database(store) -> None:
    """Copy the former extension database once, keeping its original file intact."""
    old_path = store.path.with_name("aespa.sast-benchmarking.db")
    if not old_path.is_file():
        return
    tables = (
        models.Dataset.__table__,
        models.Evaluation.__table__,
        models.Match.__table__,
        models.Comparison.__table__,
        models.GroundTruthBinding.__table__,
        models.ScanResult.__table__,
    )
    with store.engine.begin() as target:
        if any(target.execute(select(table).limit(1)).first() for table in tables):
            return
        with closing(
            sqlite3.connect(f"{old_path.as_uri()}?mode=ro", uri=True)
        ) as source:
            source.row_factory = sqlite3.Row
            old_tables = {
                row[0]
                for row in source.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            for table in tables:
                old_name = f"sast_{table.name}"
                if old_name not in old_tables:
                    continue
                rows = []
                for row in source.execute(f'SELECT * FROM "{old_name}"'):
                    values = {}
                    for key, value in dict(row).items():
                        column = table.columns.get(key)
                        if column is None:
                            continue
                        is_datetime = isinstance(column.type, DateTime) or isinstance(
                            getattr(column.type, "impl", None), DateTime
                        )
                        if is_datetime and isinstance(value, str):
                            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                            if value.tzinfo is None:
                                value = value.replace(tzinfo=timezone.utc)
                        values[key] = value
                    rows.append(values)
                if rows:
                    target.execute(insert(table), rows)


def _migrate_legacy_data(store) -> None:
    """Read retired core tables without registering them as core ORM models."""
    with store.session() as target:
        if target.exec(select(models.Dataset)).first() is not None:
            return
        engine = get_engine()
        names = (
            "benchmark_dataset",
            "benchmark_evaluation",
            "benchmark_match",
            "benchmark_comparison",
            "benchmark_comparison_evaluation",
        )
        existing = set(inspect(engine).get_table_names())
        if not set(names).issubset(existing):
            return
        metadata = MetaData()
        tables = {name: Table(name, metadata, autoload_with=engine) for name in names}
        with engine.connect() as source:
            rows = {
                name: [
                    {
                        key: (
                            value.replace(tzinfo=timezone.utc)
                            if isinstance(value, datetime) and value.tzinfo is None
                            else value
                        )
                        for key, value in row.items()
                    }
                    for row in source.execute(select(table)).mappings()
                ]
                for name, table in tables.items()
            }
        datasets = rows["benchmark_dataset"]
        evaluations = rows["benchmark_evaluation"]
        matches = rows["benchmark_match"]
        comparisons = rows["benchmark_comparison"]
        links = rows["benchmark_comparison_evaluation"]
        if not datasets and not evaluations and not matches and not comparisons:
            return
        target.add_all(models.Dataset(**row) for row in datasets)
        target.flush()
        target.add_all(models.Evaluation(**row) for row in evaluations)
        target.flush()
        target.add_all(models.Match(**row) for row in matches)
        evaluation_ids = {}
        for link in links:
            evaluation_ids.setdefault(link["comparison_id"], []).append(
                (link["ordinal"], link["evaluation_id"])
            )
        target.add_all(
            models.Comparison(
                **row,
                evaluation_ids_json=json.dumps(
                    [
                        evaluation_id
                        for _ordinal, evaluation_id in sorted(
                            evaluation_ids.get(row["id"], [])
                        )
                    ]
                ),
            )
            for row in comparisons
        )
        target.commit()


class BenchmarkingExtension:
    def register(self, registry) -> None:
        store = registry.data_store(models.metadata)
        _migrate_renamed_database(store)
        _migrate_legacy_data(store)
        registry.register_api_router(build_router(store))


def create_extension():
    return BenchmarkingExtension()
