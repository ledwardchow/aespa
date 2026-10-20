"""Request and ground-truth schemas owned by the Benchmark Lab extension."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BenchmarkLocation(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    line: int | None = Field(default=None, ge=1)


class BenchmarkGroundTruthItem(BaseModel):
    external_id: str = Field(min_length=1, max_length=200)
    title: str = Field(default="", max_length=1000)
    description: str = Field(default="", max_length=10000)
    category: str = Field(default="", max_length=200)
    severity: str = Field(default="medium", max_length=32)
    locations: list[BenchmarkLocation] = Field(default_factory=list, max_length=100)
    root_cause: str = Field(default="", max_length=10000)
    affected_operation: str = Field(default="", max_length=2000)
    expected_evidence: list[str] = Field(default_factory=list, max_length=100)
    classification: str = Field(default="exploitable", max_length=100)


class BenchmarkGroundTruth(BaseModel):
    schema_version: int = Field(default=1, ge=1)
    name: str = Field(default="", max_length=500)
    source_digest: str | None = Field(default=None, max_length=200)
    items: list[BenchmarkGroundTruthItem] = Field(max_length=10000)

    @model_validator(mode="after")
    def _unique_external_ids(self) -> "BenchmarkGroundTruth":
        ids = [item.external_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("ground-truth external_id values must be unique")
        return self


class BenchmarkDatasetIn(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    schema_version: int = Field(default=1, ge=1)
    source_digest: str | None = Field(default=None, max_length=200)
    ground_truth: BenchmarkGroundTruth | None = None
    ground_truth_json: dict | str | None = None

    @model_validator(mode="after")
    def _require_ground_truth(self) -> "BenchmarkDatasetIn":
        if self.ground_truth is None and self.ground_truth_json is None:
            raise ValueError("ground_truth is required")
        return self


class BenchmarkDatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    schema_version: int
    source_digest: str | None
    ground_truth_digest: str
    item_count: int = 0
    ground_truth: BenchmarkGroundTruth | None = None
    created_at: datetime
    updated_at: datetime


class BenchmarkEvaluationIn(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    sast_run_id: int = Field(gt=0)
    dataset_id: int = Field(gt=0)
    match_mode: Literal["deterministic", "assisted", "human_reviewed"] = "assisted"
    llm_profile_id: int | None = Field(default=None, gt=0)
    policy: dict = Field(default_factory=dict)
    notes: str = Field(default="", max_length=10000)


class BenchmarkMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    evaluation_id: int
    ground_truth_external_id: str | None
    scan_lead_id: int | None
    disposition: str
    confidence: float
    rationale: str
    human_reviewed: bool
    review_note: str
    review_history_json: str
    created_at: datetime
    updated_at: datetime


class BenchmarkMatchReviewIn(BaseModel):
    disposition: Literal[
        "full",
        "partial",
        "missed",
        "additional_valid",
        "false_positive",
        "duplicate",
        "unreviewed",
    ]
    review_note: str = Field(default="", max_length=10000)
    rationale: str | None = Field(default=None, max_length=10000)
    confidence: float | None = Field(default=None, ge=0, le=1)


class BenchmarkEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sast_run_id: int
    dataset_id: int
    status: str
    match_mode: str
    matching_version: str
    policy_json: str
    run_provenance_json: str
    blindness_status: str
    blindness_checks_json: str
    metrics_json: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    semantic_coverage: dict = Field(default_factory=dict)
    partial_coverage_reasons: list = Field(default_factory=list)
    matches: list[BenchmarkMatchOut] = Field(default_factory=list)


class BenchmarkComparisonIn(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    dataset_id: int = Field(gt=0)
    evaluation_ids: list[int] = Field(min_length=2, max_length=100)
    thresholds: dict = Field(default_factory=dict)
    include_contaminated: bool = False

    @field_validator("evaluation_ids")
    @classmethod
    def _unique_evaluations(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("evaluation_ids must be unique")
        return value


class BenchmarkComparisonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    dataset_id: int
    evaluation_ids: list[int] = Field(default_factory=list)
    thresholds_json: str
    metrics_json: str
    status: str
    include_contaminated: bool
    created_at: datetime
    updated_at: datetime
