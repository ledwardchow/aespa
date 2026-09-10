"""Post-run SAST benchmark evaluation.

This module deliberately has no dependency on the SAST scanner.  Ground truth
is read only after a completed run has been selected and is never passed to a
scanner prompt, checkpoint, or source tool.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from aespa.models import (
    BenchmarkDataset,
    BenchmarkEvaluation,
    BenchmarkMatch,
    SastEvidenceReceipt,
    SastRun,
    ScanLead,
)
from aespa.schemas import (
    BenchmarkDatasetIn,
    BenchmarkDatasetOut,
    BenchmarkEvaluationIn,
    BenchmarkEvaluationOut,
    BenchmarkGroundTruth,
    BenchmarkGroundTruthItem,
    BenchmarkMatchOut,
    BenchmarkMatchReviewIn,
)

_UTC = timezone.utc
MATCHING_VERSION = "deterministic-v1"
_TOKEN_RE = re.compile(r"[a-z0-9_]{3,}")
_TERMINAL_RUN_STATUS = "completed"
_MAX_GROUND_TRUTH_BYTES = 10 * 1024 * 1024
_MAX_BLINDNESS_TEXT_BYTES = 10 * 1024 * 1024
_DISPOSITIONS = {
    "full",
    "partial",
    "missed",
    "additional_valid",
    "false_positive",
    "duplicate",
    "unreviewed",
}


def _now() -> datetime:
    return datetime.now(_UTC)


def _dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _load_json(raw: str | None, fallback: Any) -> Any:
    try:
        value = json.loads(raw or "")
    except (TypeError, ValueError):
        return fallback
    return value


def _canonical_ground_truth(payload: BenchmarkDatasetIn) -> BenchmarkGroundTruth:
    if payload.ground_truth is not None:
        gt = payload.ground_truth
    else:
        raw = payload.ground_truth_json
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError as exc:
                raise ValueError("ground_truth_json must contain valid JSON") from exc
        if isinstance(raw, list):
            raw = {"schema_version": payload.schema_version, "items": raw}
        if not isinstance(raw, dict):
            raise ValueError("ground_truth must be an object or array")
        gt = BenchmarkGroundTruth.model_validate(raw)
    if gt.schema_version != payload.schema_version:
        # The dataset envelope is authoritative while retaining the item's
        # shape; this makes old clients that send only schema_version work.
        gt = gt.model_copy(update={"schema_version": payload.schema_version})
    return gt


def _gt_json(gt: BenchmarkGroundTruth) -> str:
    raw = _dumps(gt.model_dump(mode="json"))
    if len(raw.encode("utf-8")) > _MAX_GROUND_TRUTH_BYTES:
        raise ValueError("ground-truth dataset exceeds the 10 MiB limit")
    return raw


def dataset_out(dataset: BenchmarkDataset) -> BenchmarkDatasetOut:
    parsed = _load_json(dataset.ground_truth_json, {})
    items = parsed.get("items", []) if isinstance(parsed, dict) else []
    ground_truth = None
    try:
        ground_truth = BenchmarkGroundTruth.model_validate(parsed)
    except Exception:
        # A legacy/partially imported dataset can still be listed with its
        # digest and count; only the canonical detail includes the payload.
        pass
    return BenchmarkDatasetOut(
        id=dataset.id,
        name=dataset.name,
        schema_version=dataset.schema_version,
        source_digest=dataset.source_digest,
        ground_truth_digest=dataset.ground_truth_digest,
        item_count=len(items) if isinstance(items, list) else 0,
        ground_truth=ground_truth,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


# Kept as a compatibility alias for early callers of the first Benchmark Lab
# slice; new API code should use the public helper above.
_dataset_out = dataset_out


def create_dataset(session: Session, payload: BenchmarkDatasetIn) -> BenchmarkDataset:
    gt = _canonical_ground_truth(payload)
    raw = _gt_json(gt)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    dataset = BenchmarkDataset(
        name=payload.name,
        schema_version=payload.schema_version,
        source_digest=payload.source_digest or gt.source_digest,
        ground_truth_json=raw,
        ground_truth_digest=f"sha256:{digest}",
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def update_dataset(
    session: Session, dataset: BenchmarkDataset, payload: BenchmarkDatasetIn
) -> BenchmarkDataset:
    gt = _canonical_ground_truth(payload)
    raw = _gt_json(gt)
    dataset.name = payload.name
    dataset.schema_version = payload.schema_version
    dataset.source_digest = payload.source_digest or gt.source_digest
    dataset.ground_truth_json = raw
    dataset.ground_truth_digest = f"sha256:{hashlib.sha256(raw.encode()).hexdigest()}"
    dataset.updated_at = _now()
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def list_datasets(session: Session) -> list[BenchmarkDataset]:
    return list(session.exec(select(BenchmarkDataset).order_by(BenchmarkDataset.id.desc())))


def dataset_ground_truth(dataset: BenchmarkDataset) -> BenchmarkGroundTruth:
    return BenchmarkGroundTruth.model_validate(_load_json(dataset.ground_truth_json, {}))


def create_evaluation(
    session: Session, payload: BenchmarkEvaluationIn
) -> BenchmarkEvaluation:
    run = session.get(SastRun, payload.sast_run_id)
    if run is None:
        raise LookupError("SAST run not found")
    if run.status != _TERMINAL_RUN_STATUS:
        raise ValueError("Benchmark evaluations require a completed SAST run")
    if session.get(BenchmarkDataset, payload.dataset_id) is None:
        raise LookupError("Benchmark dataset not found")
    now = _now()
    evaluation = BenchmarkEvaluation(
        name=payload.name,
        sast_run_id=payload.sast_run_id,
        dataset_id=payload.dataset_id,
        status="created",
        match_mode=payload.match_mode,
        matching_version=MATCHING_VERSION,
        policy_json=_dumps({**payload.policy, **({"notes": payload.notes} if payload.notes else {})}),
        run_provenance_json=_run_provenance(run),
        created_at=now,
        updated_at=now,
    )
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    return evaluation


def _run_provenance(run: SastRun) -> str:
    """Return safe provenance; do not serialize prompts, evidence, or secrets."""
    return _dumps(
        {
            "sast_run_id": run.id,
            "name": run.name,
            "source_filename": run.source_filename,
            "source_archive_digest": _source_digest(run),
            "status": run.status,
            "completion_status": run.completion_status,
            "completion_assurance": run.completion_status,
            "collection_id": run.collection_id,
            "document_id": run.document_id,
            "llm_config_id": run.llm_config_id,
            "llm_profile_id": run.llm_profile_id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }
    )


def _tokens(*values: str) -> set[str]:
    return set(_TOKEN_RE.findall(" ".join(v or "" for v in values).lower()))


def _location_paths(location: str) -> set[str]:
    return {
        part.strip().split(":", 1)[0]
        for part in re.split(r"[,\s]+", location or "")
        if "/" in part or "\\" in part or ".py" in part or ".js" in part
    }


def _match_score(
    item: BenchmarkGroundTruthItem, lead: ScanLead, policy: dict[str, Any]
) -> tuple[float, str]:
    expected_paths = {loc.path for loc in item.locations}
    lead_paths = _location_paths(lead.location)
    location_tolerance = policy.get("location_tolerance", "file_and_line")
    path_score = 1.0 if expected_paths & lead_paths else 0.0
    if location_tolerance == "operation" and item.affected_operation:
        operation_terms = _tokens(item.affected_operation)
        lead_operation_terms = _tokens(lead.suggested_endpoint or "")
        path_score = max(
            path_score,
            len(operation_terms & lead_operation_terms) / max(1, len(operation_terms)),
        )
    category_score = 1.0 if item.category and item.category.lower() in (lead.category or "").lower() else 0.0
    expected_terms = _tokens(item.title, item.description, item.root_cause, item.affected_operation)
    lead_terms = _tokens(lead.title, lead.description, lead.evidence, lead.suggested_endpoint)
    term_score = len(expected_terms & lead_terms) / max(1, len(expected_terms))
    # Location and category identify a candidate; root-cause terms distinguish
    # adjacent issues.  Scores are intentionally stable and explainable.
    score = min(1.0, path_score * 0.45 + category_score * 0.2 + term_score * 0.35)
    if path_score and term_score >= 0.25:
        rationale = "location and normalized root-cause evidence agree"
    elif path_score:
        rationale = "source location agrees"
    elif category_score and term_score >= 0.35:
        rationale = "category and normalized evidence agree"
    else:
        rationale = "no deterministic evidence threshold met"
    return score, rationale


def _source_digest(run: SastRun) -> str | None:
    path = Path(run.source_archive_path) if run.source_archive_path else None
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _blindness_checks(session: Session, run: SastRun, dataset: BenchmarkDataset) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    completed_at = run.completed_at
    if completed_at and completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=_UTC)
    dataset_created_at = dataset.created_at
    if dataset_created_at.tzinfo is None:
        dataset_created_at = dataset_created_at.replace(tzinfo=_UTC)
    if completed_at and dataset_created_at > completed_at:
        checks["dataset_timing"] = {"status": "valid"}
    else:
        # A dataset that predates the run is not provably blind in this
        # database-only first slice.  Keep the result inspectable, but exclude
        # it from aggregate scorecards until the operator adjudicates it.
        checks["dataset_timing"] = {
            "status": "warning",
            "reason": "dataset predates run completion or run completion time is unavailable",
        }
    actual_digest = _source_digest(run)
    expected_digest = dataset.source_digest
    if not expected_digest:
        checks["source_digest"] = {"status": "warning", "reason": "dataset has no source digest"}
    elif not actual_digest:
        checks["source_digest"] = {"status": "warning", "reason": "source archive is unavailable"}
    elif actual_digest != expected_digest:
        checks["source_digest"] = {"status": "contaminated", "expected": expected_digest, "actual": actual_digest}
    else:
        checks["source_digest"] = {"status": "valid"}

    archive_answer_key = False
    content_match = False
    archive_path = Path(run.source_archive_path) if run.source_archive_path else None
    if archive_path and archive_path.is_file():
        try:
            with zipfile.ZipFile(archive_path) as archive:
                answer_key_names = (
                    "ground_truth",
                    "ground-truth",
                    "answer_key",
                    "answer-key",
                    "benchmark",
                    "vulnerabilities",
                    "expected-results",
                    "expected_results",
                    "security_scan_report",
                )
                archive_answer_key = any(any(term in name.lower() for term in answer_key_names) for name in archive.namelist())
                # Catch renamed answer keys without copying their contents into
                # evaluation output.  Only distinctive IDs and sufficiently
                # long titles are compared, with strict caps on files/bytes.
                gt = dataset_ground_truth(dataset)
                needles = {
                    value.casefold()
                    for item in gt.items
                    for value in (item.external_id, item.title)
                    if len(value.strip()) >= 8
                }
                hits: set[str] = set()
                inspected = 0
                inspected_bytes = 0
                for info in archive.infolist():
                    suffix = Path(info.filename).suffix.casefold()
                    if suffix not in {".md", ".txt", ".json", ".yaml", ".yml", ".sarif"}:
                        continue
                    if (
                        info.file_size > 2 * 1024 * 1024
                        or inspected >= 100
                        or inspected_bytes + info.file_size
                        > _MAX_BLINDNESS_TEXT_BYTES
                    ):
                        continue
                    inspected += 1
                    inspected_bytes += info.file_size
                    try:
                        text = archive.read(info).decode("utf-8", errors="ignore").casefold()
                    except (OSError, RuntimeError, zipfile.BadZipFile):
                        continue
                    hits.update(needle for needle in needles if needle in text)
                threshold = min(3, len(needles))
                content_match = bool(threshold and len(hits) >= threshold)
        except (OSError, zipfile.BadZipFile):
            checks["source_archive"] = {"status": "warning", "reason": "source archive could not be inspected"}
    checks["ground_truth_in_source"] = {
        "status": "contaminated" if archive_answer_key or content_match else "valid",
        "reason": (
            "source archive contains a likely answer-key filename"
            if archive_answer_key
            else "source archive content overlaps distinctive ground-truth identifiers"
            if content_match
            else "no answer-key indicators found"
        ),
    }

    receipts = session.exec(select(SastEvidenceReceipt).where(SastEvidenceReceipt.sast_run_id == run.id)).all()
    evaluator_path = any(
        re.search(r"ground[_-]?truth|answer[_-]?key|benchmark", receipt.path or "", re.I)
        for receipt in receipts
    )
    checks["evaluator_path_access"] = {"status": "contaminated" if evaluator_path else "valid"}
    checkpoint_text = " ".join((run.phase_state_json or "", run.coverage_json or "", run.report_json or ""))
    checkpoint_access = bool(re.search(r"ground[_-]?truth|answer[_-]?key", checkpoint_text, re.I))
    checks["checkpoint_access"] = {"status": "contaminated" if checkpoint_access else "valid"}
    return checks


def _blindness_status(checks: dict[str, Any]) -> str:
    statuses = {value.get("status") for value in checks.values() if isinstance(value, dict)}
    if "contaminated" in statuses:
        return "contaminated"
    if "warning" in statuses:
        return "warning"
    return "valid"


def _metrics(matches: list[BenchmarkMatch], item_count: int, lead_count: int) -> dict[str, Any]:
    counts = {disposition: sum(m.disposition == disposition for m in matches) for disposition in _DISPOSITIONS}
    full = counts["full"]
    partial = counts["partial"]
    adjudicated = counts["full"] + counts["partial"] + counts["additional_valid"] + counts["false_positive"] + counts["duplicate"]
    true_positive = full + partial + counts["additional_valid"]
    return {
        "full_recall": full / item_count if item_count else 0.0,
        "inclusive_recall": (full + partial) / item_count if item_count else 0.0,
        "precision": true_positive / adjudicated if adjudicated else 0.0,
        "duplicate_rate": counts["duplicate"] / lead_count if lead_count else 0.0,
        "unique_validated_root_causes": true_positive,
        "partial_count": partial,
        "unresolved_count": counts["unreviewed"],
        "item_count": item_count,
        "reportable_lead_count": lead_count,
        "disposition_counts": counts,
    }


def run_evaluation(session: Session, evaluation: BenchmarkEvaluation) -> BenchmarkEvaluation:
    run = session.get(SastRun, evaluation.sast_run_id)
    dataset = session.get(BenchmarkDataset, evaluation.dataset_id)
    if run is None or dataset is None:
        raise LookupError("evaluation source is no longer available")
    if run.status != _TERMINAL_RUN_STATUS:
        raise ValueError("Benchmark evaluations require a completed SAST run")
    gt = dataset_ground_truth(dataset)
    policy = _load_json(evaluation.policy_json, {})
    items = [
        item
        for item in gt.items
        if (
            policy.get("include_conditional", True)
            or item.classification.casefold() != "conditional"
        )
        and (
            policy.get("include_hardening", False)
            or item.classification.casefold()
            not in {"hardening", "defense_in_depth", "defence_in_depth"}
        )
    ]
    evaluation.status = "running"
    evaluation.started_at = _now()
    evaluation.updated_at = _now()
    session.add(evaluation)
    session.commit()
    # Evaluation rows are rebuilt only for this evaluation.  Existing scan
    # leads and run lifecycle fields are never modified.
    old_matches = session.exec(select(BenchmarkMatch).where(BenchmarkMatch.evaluation_id == evaluation.id)).all()
    for old in old_matches:
        session.delete(old)
    session.flush()
    leads = list(
        session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.producer_run_id == run.id)
            .where(ScanLead.imported_into_run_id.is_(None))
            .where(ScanLead.reportable.is_(True))
            .order_by(ScanLead.id)
        )
    )
    used_leads: set[int] = set()
    matches: list[BenchmarkMatch] = []
    for item in items:
        candidates = sorted(
            (
                (_match_score(item, lead, policy), lead)
                for lead in leads
                if lead.id not in used_leads
            ),
            key=lambda pair: (-pair[0][0], pair[1].id or 0),
        )
        (score, rationale), lead = candidates[0] if candidates else ((0.0, "no candidate"), None)
        if lead is None or score < 0.35:
            disposition = "missed"
            lead_id = None
        else:
            disposition = "full" if score >= 0.65 else "partial"
            lead_id = lead.id
            if lead.id is not None:
                used_leads.add(lead.id)
        matches.append(BenchmarkMatch(
            evaluation_id=evaluation.id,
            ground_truth_external_id=item.external_id,
            scan_lead_id=lead_id,
            disposition=disposition,
            confidence=round(score, 4),
            rationale=rationale,
            created_at=_now(),
            updated_at=_now(),
        ))
    for lead in leads:
        if lead.id not in used_leads:
            matches.append(BenchmarkMatch(
                evaluation_id=evaluation.id,
                scan_lead_id=lead.id,
                disposition="unreviewed",
                confidence=0.0,
                rationale="reportable scanner lead had no deterministic ground-truth match",
                created_at=_now(),
                updated_at=_now(),
            ))
    session.add_all(matches)
    session.flush()
    checks = _blindness_checks(session, run, dataset)
    evaluation.blindness_checks_json = _dumps(checks)
    evaluation.blindness_status = _blindness_status(checks)
    metrics = _metrics(matches, len(items), len(leads))
    match_by_external_id = {
        match.ground_truth_external_id: match
        for match in matches
        if match.ground_truth_external_id
    }

    def _recall_breakdown(attribute: str) -> dict[str, dict[str, float | int]]:
        grouped: dict[str, list[BenchmarkGroundTruthItem]] = {}
        for item in items:
            key = str(getattr(item, attribute) or "unspecified")
            grouped.setdefault(key, []).append(item)
        result: dict[str, dict[str, float | int]] = {}
        for key, group_items in grouped.items():
            dispositions = [
                match_by_external_id[item.external_id].disposition
                for item in group_items
                if item.external_id in match_by_external_id
            ]
            full = dispositions.count("full")
            partial = dispositions.count("partial")
            result[key] = {
                "items": len(group_items),
                "full_recall": full / len(group_items),
                "inclusive_recall": (full + partial) / len(group_items),
            }
        return result

    metrics["recall_by_family"] = _recall_breakdown("category")
    metrics["recall_by_classification"] = _recall_breakdown("classification")
    metrics["completion_status"] = run.completion_status
    if run.started_at and run.completed_at:
        metrics["runtime_seconds"] = max(
            0.0, (run.completed_at - run.started_at).total_seconds()
        )
    usage = _load_json(run.token_usage_json, {})
    if isinstance(usage, dict):
        metrics["token_usage"] = {
            key: usage[key]
            for key in ("requests", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "estimated_cost")
            if key in usage
        }
        metrics.update(metrics["token_usage"])
    root_causes = metrics["unique_validated_root_causes"]
    if root_causes:
        if "requests" in metrics:
            metrics["requests_per_unique_true_positive"] = (
                metrics["requests"] / root_causes
            )
        if "estimated_cost" in metrics:
            metrics["cost_per_unique_true_positive"] = (
                metrics["estimated_cost"] / root_causes
            )
    metrics["aggregate_eligible"] = evaluation.blindness_status != "contaminated"
    evaluation.metrics_json = _dumps(metrics)
    evaluation.status = "completed"
    evaluation.completed_at = _now()
    evaluation.updated_at = _now()
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    return evaluation


def evaluation_matches(session: Session, evaluation_id: int) -> list[BenchmarkMatch]:
    return list(session.exec(select(BenchmarkMatch).where(BenchmarkMatch.evaluation_id == evaluation_id).order_by(BenchmarkMatch.id)))


def evaluation_out(session: Session, evaluation: BenchmarkEvaluation) -> BenchmarkEvaluationOut:
    run = session.get(SastRun, evaluation.sast_run_id)
    report = _load_json(run.report_json, {}) if run is not None else {}
    semantic = report.get("semantic", {}) if isinstance(report, dict) else {}
    completion_reasons = (
        report.get("completion_reasons", []) if isinstance(report, dict) else []
    )
    return BenchmarkEvaluationOut(
        **evaluation.model_dump(),
        semantic_coverage=semantic if isinstance(semantic, dict) else {},
        partial_coverage_reasons=(
            completion_reasons if isinstance(completion_reasons, list) else []
        ),
        matches=[BenchmarkMatchOut.model_validate(match) for match in evaluation_matches(session, evaluation.id)],
    )


def review_match(session: Session, match: BenchmarkMatch, payload: BenchmarkMatchReviewIn) -> BenchmarkMatch:
    if payload.disposition not in _DISPOSITIONS:
        raise ValueError("invalid benchmark disposition")
    history = _load_json(match.review_history_json, [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "reviewed_at": _now().isoformat(),
            "previous": {
                "disposition": match.disposition,
                "confidence": match.confidence,
                "rationale": match.rationale,
                "review_note": match.review_note,
            },
            "updated": {
                "disposition": payload.disposition,
                "confidence": payload.confidence,
                "rationale": payload.rationale,
                "review_note": payload.review_note,
            },
        }
    )
    match.review_history_json = _dumps(history[-100:])
    match.disposition = payload.disposition
    match.human_reviewed = True
    match.review_note = payload.review_note
    if payload.rationale is not None:
        match.rationale = payload.rationale
    if payload.confidence is not None:
        match.confidence = payload.confidence
    match.updated_at = _now()
    session.add(match)
    evaluation = session.get(BenchmarkEvaluation, match.evaluation_id)
    if evaluation is not None:
        rows = evaluation_matches(session, evaluation.id)
        previous_metrics = _load_json(evaluation.metrics_json, {})
        metrics = _metrics(
            rows,
            sum(row.ground_truth_external_id is not None for row in rows),
            sum(row.scan_lead_id is not None for row in rows),
        )
        if isinstance(previous_metrics, dict):
            for key in ("completion_status", "runtime_seconds", "token_usage", "aggregate_eligible"):
                if key in previous_metrics:
                    metrics[key] = previous_metrics[key]
        evaluation.metrics_json = _dumps(metrics)
        evaluation.updated_at = _now()
        session.add(evaluation)
    session.commit()
    session.refresh(match)
    return match


def export_evaluation(session: Session, evaluation: BenchmarkEvaluation, fmt: str) -> tuple[bytes, str, str]:
    rows = evaluation_matches(session, evaluation.id)
    if fmt == "json":
        payload = evaluation_out(session, evaluation).model_dump(mode="json")
        return _dumps(payload).encode(), "application/json", f"benchmark-evaluation-{evaluation.id}.json"
    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["match_id", "ground_truth_external_id", "scan_lead_id", "disposition", "confidence", "rationale", "human_reviewed", "review_note"])
        writer.writerows([
            [row.id, row.ground_truth_external_id or "", row.scan_lead_id or "", row.disposition, row.confidence, row.rationale, row.human_reviewed, row.review_note]
            for row in rows
        ])
        return output.getvalue().encode(), "text/csv; charset=utf-8", f"benchmark-evaluation-{evaluation.id}.csv"
    if fmt == "markdown":
        metrics = _load_json(evaluation.metrics_json, {})
        lines = [f"# Benchmark Evaluation: {evaluation.name}", "", f"- Status: **{evaluation.status}**", f"- Blindness: **{evaluation.blindness_status}**", "", "## Metrics", "", "| Metric | Value |", "| --- | ---: |"]
        for key in ("full_recall", "inclusive_recall", "precision", "duplicate_rate", "unique_validated_root_causes", "partial_count", "unresolved_count"):
            if key in metrics:
                lines.append(f"| {key.replace('_', ' ').title()} | {metrics[key]} |")
        lines += ["", "## Matches", "", "| Ground truth | Lead | Disposition | Confidence |", "| --- | ---: | --- | ---: |"]
        lines.extend(f"| {row.ground_truth_external_id or '—'} | {row.scan_lead_id or '—'} | {row.disposition} | {row.confidence:.2f} |" for row in rows)
        return "\n".join(lines).encode(), "text/markdown; charset=utf-8", f"benchmark-evaluation-{evaluation.id}.md"
    raise ValueError("format must be json, csv, or markdown")
