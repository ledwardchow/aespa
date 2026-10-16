"""Portable benchmark snapshots. Core scan IDs are never imported as local links."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from .models import (
    Comparison,
    Dataset,
    DatasetLabel,
    Evaluation,
    Match,
    ScanResult,
    TransferIdentity,
)
from .schemas import BenchmarkGroundTruth

MODELS = {"results": ScanResult, "evaluations": Evaluation, "comparisons": Comparison}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: UUID
    dataset: str
    origin: dict = Field(default_factory=dict)
    data: dict
    matches: list[dict] = Field(default_factory=list)
    evaluations: list[UUID] = Field(default_factory=list)


class PortableDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    data: dict
    label: str = Field(default="", max_length=200)


class Bundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["aespa-benchmark-lab"]
    version: Literal[1]
    datasets: list[PortableDataset] = Field(max_length=10000)
    results: list[Entry] = Field(default_factory=list, max_length=100000)
    evaluations: list[Entry] = Field(default_factory=list, max_length=100000)
    comparisons: list[Entry] = Field(default_factory=list, max_length=100000)


def dataset_key(row: Dataset) -> str:
    return digest(
        {
            "ground_truth": json.loads(row.ground_truth_json),
            "source_digest": row.source_digest,
            "schema_version": row.schema_version,
        }
    )


def identity(session: Session, kind: str, row) -> TransferIdentity:
    saved = session.exec(
        select(TransferIdentity).where(
            TransferIdentity.kind == kind, TransferIdentity.local_id == row.id
        )
    ).first()
    if saved is None:
        origin = {}
        if kind == "results":
            origin = {
                name: getattr(row, name)
                for name in (
                    "run_kind",
                    "run_id",
                    "target_kind",
                    "target_id",
                    "target_name",
                )
            }
        elif kind == "evaluations":
            origin = {"run_kind": "sast", "run_id": row.sast_run_id}
        saved = TransferIdentity(
            key=str(uuid4()),
            kind=kind,
            local_id=row.id,
            origin_json=canonical(origin),
        )
        session.add(saved)
        session.flush()
    return saved


def export_bundle(session: Session, core: Session) -> dict:
    from .router import result_out

    output = {"format": "aespa-benchmark-lab", "version": 1, "datasets": []}
    datasets = {}
    for row in session.exec(select(Dataset).order_by(Dataset.id)):
        key = dataset_key(row)
        datasets[row.id] = key
        label = session.get(DatasetLabel, row.id)
        if not any(item["key"] == key for item in output["datasets"]):
            output["datasets"].append(
                {
                    "key": key,
                    "data": row.model_dump(mode="json", exclude={"id"}),
                    "label": label.label if label else "",
                }
            )
    evaluation_keys = {}
    for kind, model in MODELS.items():
        output[kind] = []
        for row in session.exec(select(model).order_by(model.id)):
            saved = identity(session, kind, row)
            data = row.model_dump(mode="json", exclude={"id", "dataset_id"})
            entry = {
                "key": saved.key,
                "dataset": datasets[row.dataset_id],
                "origin": json.loads(saved.origin_json),
                "data": data,
                "matches": [],
                "evaluations": [],
            }
            if kind == "results":
                snapshot = result_out(row, core)
                data["rows_json"] = canonical(
                    {
                        key: snapshot[key]
                        for key in (
                            "rows",
                            "comparison",
                            "scan_models",
                            "scan_cost_usd",
                            "scan_cost_breakdown",
                            "scan_started_at",
                        )
                    }
                )
                for name in ("run_id", "target_id", "target_kind"):
                    data.pop(name)
            elif kind == "evaluations":
                evaluation_keys[row.id] = saved.key
                data.pop("sast_run_id")
                entry["matches"] = [
                    match.model_dump(mode="json", exclude={"id", "evaluation_id"})
                    for match in session.exec(
                        select(Match)
                        .where(Match.evaluation_id == row.id)
                        .order_by(Match.id)
                    )
                ]
            else:
                entry["evaluations"] = [
                    evaluation_keys[value]
                    for value in json.loads(data.pop("evaluation_ids_json"))
                ]
            output[kind].append(entry)
    return output


def validate_data(model, data: dict, excluded: set[str], **local):
    if set(data) - (set(model.model_fields) - excluded):
        raise ValueError(f"Unknown or local-only fields in {model.__name__}")
    row = model.model_validate({**data, **local})
    for name in model.model_fields:
        if name.endswith("_json"):
            value = json.loads(getattr(row, name))
            expected = (
                list
                if name
                in {"findings_json", "review_history_json", "evaluation_ids_json"}
                else dict
            )
            if not isinstance(value, expected):
                raise ValueError(f"Invalid {name}: expected {expected.__name__}")
            canonical(value)  # Reject non-finite JSON numbers before writing anything.
    return row


def import_bundle(session: Session, core: Session, bundle: Bundle) -> dict:
    """Validate first, then merge in one transaction owned by the caller."""
    prepared = {}
    for item in bundle.datasets:
        row = validate_data(Dataset, item.data, {"id"})
        BenchmarkGroundTruth.model_validate_json(row.ground_truth_json)
        if dataset_key(row) != item.key or item.key in prepared:
            raise ValueError("Invalid or duplicate dataset key")
        # Never trust a supplied digest for identity or later comparisons.
        row.ground_truth_digest = "sha256:" + digest(json.loads(row.ground_truth_json))
        prepared[item.key] = row

    entries = {}
    validated = {}
    for kind, model in MODELS.items():
        for item in getattr(bundle, kind):
            key = str(item.key)
            if key in entries or item.dataset not in prepared:
                raise ValueError("Duplicate record key or missing dataset")
            excluded = {"id", "dataset_id"}
            local = {"dataset_id": 0}
            if kind == "results":
                excluded |= {"run_id", "target_id", "target_kind"}
                local.update(run_id=0, target_id=None, target_kind=None)
            elif kind == "evaluations":
                excluded.add("sast_run_id")
                local["sast_run_id"] = 0
            else:
                excluded.add("evaluation_ids_json")
            row = validate_data(model, item.data, excluded, **local)
            if kind == "results":
                snapshot = json.loads(row.rows_json)
                if row.run_kind not in {"site", "api", "sast"} or not isinstance(
                    snapshot, dict
                ):
                    raise ValueError("Invalid saved scan result")
                BenchmarkGroundTruth.model_validate_json(row.ground_truth_json)
                findings = json.loads(row.findings_json)
                if not isinstance(findings, list) or any(
                    not isinstance(f, dict) or "id" not in f for f in findings
                ):
                    raise ValueError("Invalid finding snapshots")
                if any(type(f["id"]) is not int or f["id"] <= 0 for f in findings):
                    raise ValueError("Invalid finding identifier")
                finding_ids = {f["id"] for f in findings}
                if len(finding_ids) != len(findings):
                    raise ValueError("Duplicate finding identifier")
                cost = snapshot.get("scan_cost_usd")
                if cost is not None and (
                    type(cost) not in (int, float)
                    or not math.isfinite(cost)
                    or cost < 0
                ):
                    raise ValueError("Invalid scan cost")
                if snapshot.get("scan_models") is not None and not isinstance(
                    snapshot["scan_models"], dict
                ):
                    raise ValueError("Invalid scan models")
                if not isinstance(snapshot.get("comparison", {}), dict):
                    raise ValueError("Invalid comparison details")
                if not isinstance(snapshot.get("rows"), list):
                    raise ValueError("Invalid result rows")
                for result in snapshot["rows"]:
                    if (
                        not isinstance(result, dict)
                        or not result.get("external_id")
                        or result.get("disposition")
                        not in {"full", "partial", "missing"}
                        or not isinstance(result.get("finding_ids", []), list)
                        or any(
                            value not in finding_ids
                            for value in result.get("finding_ids", [])
                        )
                    ):
                        raise ValueError("Invalid result row or finding reference")
            if kind != "evaluations" and item.matches:
                raise ValueError("Only evaluations can contain matches")
            if kind != "comparisons" and item.evaluations:
                raise ValueError("Only comparisons can reference evaluations")
            match_rows = [
                validate_data(Match, match, {"id", "evaluation_id"}, evaluation_id=0)
                for match in item.matches
            ]
            for match in match_rows:
                if (
                    match.disposition
                    not in {
                        "full",
                        "partial",
                        "missed",
                        "additional_valid",
                        "false_positive",
                        "duplicate",
                        "unreviewed",
                    }
                    or not 0 <= match.confidence <= 1
                ):
                    raise ValueError("Invalid match disposition or confidence")
            entries[key] = (kind, item)
            validated[key] = (row, match_rows)
    for kind, item in entries.values():
        if kind == "comparisons":
            if len(item.evaluations) != len(set(item.evaluations)):
                raise ValueError("Duplicate comparison evaluation")
            for ref in item.evaluations:
                linked = entries.get(str(ref))
                if (
                    not linked
                    or linked[0] != "evaluations"
                    or linked[1].dataset != item.dataset
                ):
                    raise ValueError(
                        "Comparison references an unavailable or different dataset evaluation"
                    )

    current = export_bundle(session, core)
    existing = {item["key"]: (kind, item) for kind in MODELS for item in current[kind]}
    report = {"imported": 0, "skipped": 0, "conflicts": [], "datasets_added": 0}
    dataset_ids = {dataset_key(row): row.id for row in session.exec(select(Dataset))}
    for item in bundle.datasets:
        if item.key not in dataset_ids:
            row = prepared[item.key]
            session.add(row)
            session.flush()
            dataset_ids[item.key] = row.id
            session.add(DatasetLabel(dataset_id=row.id, label=item.label))
            report["datasets_added"] += 1
    local_ids = {}
    for kind in MODELS:
        for item in getattr(bundle, kind):
            key = str(item.key)
            previous = existing.get(key)
            if previous:
                if previous[0] != kind:
                    raise ValueError(
                        "Record key is already used by another record type"
                    )
                saved = session.get(TransferIdentity, key)
                local_ids[key] = saved.local_id
                if canonical(previous[1]) == canonical(item.model_dump(mode="json")):
                    report["skipped"] += 1
                else:
                    report["conflicts"].append(
                        {
                            "kind": kind,
                            "key": key,
                            "name": item.data.get(
                                "name", item.data.get("run_name", "")
                            ),
                        }
                    )
                continue
            row, match_rows = validated[key]
            row.dataset_id = dataset_ids[item.dataset]
            if kind == "comparisons":
                # A changed evaluation must not silently change the meaning of an imported comparison.
                conflict_keys = {conflict["key"] for conflict in report["conflicts"]}
                if any(str(ref) in conflict_keys for ref in item.evaluations):
                    report["conflicts"].append(
                        {"kind": kind, "key": key, "name": row.name}
                    )
                    continue
                row.evaluation_ids_json = canonical(
                    [local_ids[str(ref)] for ref in item.evaluations]
                )
            # Remove a stale identity if a deleted row's SQLite ID was reused.
            stale = session.get(TransferIdentity, key)
            if stale:
                session.delete(stale)
                session.flush()
            session.add(row)
            session.flush()
            old = session.exec(
                select(TransferIdentity).where(
                    TransferIdentity.kind == kind, TransferIdentity.local_id == row.id
                )
            ).first()
            if old:
                session.delete(old)
                session.flush()
            session.add(
                TransferIdentity(
                    key=key,
                    kind=kind,
                    local_id=row.id,
                    origin_json=canonical(item.origin),
                )
            )
            local_ids[key] = row.id
            for match in match_rows:
                match.evaluation_id = row.id
                session.add(match)
            report["imported"] += 1
    session.flush()
    return report
