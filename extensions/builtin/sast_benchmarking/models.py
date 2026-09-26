from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import MetaData
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


metadata = MetaData()


class ExtensionModel(SQLModel):
    metadata = metadata


class Dataset(ExtensionModel, table=True):
    __tablename__ = "sast_benchmarking_dataset"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    schema_version: int = 1
    source_digest: str | None = None
    ground_truth_digest: str
    ground_truth_json: str
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Evaluation(ExtensionModel, table=True):
    __tablename__ = "sast_benchmarking_evaluation"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    sast_run_id: int = Field(index=True)
    dataset_id: int = Field(foreign_key="sast_benchmarking_dataset.id", index=True)
    status: str = "created"
    match_mode: str = "assisted"
    matching_version: str = "deterministic-v1"
    policy_json: str = "{}"
    run_provenance_json: str = "{}"
    blindness_status: str = "pending"
    blindness_checks_json: str = "{}"
    metrics_json: str = "{}"
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Match(ExtensionModel, table=True):
    __tablename__ = "sast_benchmarking_match"
    id: int | None = Field(default=None, primary_key=True)
    evaluation_id: int = Field(
        foreign_key="sast_benchmarking_evaluation.id", index=True
    )
    ground_truth_external_id: str | None = None
    scan_lead_id: int | None = None
    disposition: str = "unreviewed"
    confidence: float = 0.0
    rationale: str = ""
    human_reviewed: bool = False
    review_note: str = ""
    review_history_json: str = "[]"
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Comparison(ExtensionModel, table=True):
    __tablename__ = "sast_benchmarking_comparison"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    dataset_id: int = Field(foreign_key="sast_benchmarking_dataset.id", index=True)
    evaluation_ids_json: str = "[]"
    thresholds_json: str = "{}"
    metrics_json: str = "{}"
    status: str = "created"
    include_contaminated: bool = False
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
