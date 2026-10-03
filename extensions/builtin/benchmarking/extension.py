from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime

from sqlalchemy import DateTime, insert
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    BenchmarkComparison,
    BenchmarkComparisonEvaluation,
    BenchmarkDataset,
    BenchmarkEvaluation,
    BenchmarkMatch,
)

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
                        if isinstance(column.type, DateTime) and isinstance(value, str):
                            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        values[key] = value
                    rows.append(values)
                if rows:
                    target.execute(insert(table), rows)


def _migrate_legacy_data(store) -> None:
    """Copy the retired core Benchmark Lab rows once, preserving identifiers."""
    with store.session() as target:
        if target.exec(select(models.Dataset)).first() is not None:
            return
        with Session(get_engine()) as source:
            datasets = list(source.exec(select(BenchmarkDataset)))
            evaluations = list(source.exec(select(BenchmarkEvaluation)))
            matches = list(source.exec(select(BenchmarkMatch)))
            comparisons = list(source.exec(select(BenchmarkComparison)))
            links = list(source.exec(select(BenchmarkComparisonEvaluation)))
        if not datasets and not evaluations and not matches and not comparisons:
            return
        target.add_all(models.Dataset(**row.model_dump()) for row in datasets)
        target.add_all(models.Evaluation(**row.model_dump()) for row in evaluations)
        target.add_all(models.Match(**row.model_dump()) for row in matches)
        evaluation_ids = {}
        for link in links:
            evaluation_ids.setdefault(link.comparison_id, []).append(
                (link.ordinal, link.evaluation_id)
            )
        target.add_all(
            models.Comparison(
                **row.model_dump(),
                evaluation_ids_json=json.dumps(
                    [
                        evaluation_id
                        for _ordinal, evaluation_id in sorted(
                            evaluation_ids.get(row.id, [])
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
