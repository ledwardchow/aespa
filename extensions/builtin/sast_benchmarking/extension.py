from __future__ import annotations

import json

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


class SastBenchmarkingExtension:
    def register(self, registry) -> None:
        store = registry.data_store(models.metadata)
        _migrate_legacy_data(store)
        registry.register_api_router(build_router(store))


def create_extension():
    return SastBenchmarkingExtension()
