"""Candidate and coverage helpers shared by Light and Deep SAST scans."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import ApiCollection, ApiEndpoint, PhaseCheckpoint, SastRun
from aespa.services import events as events_svc

_UTC = timezone.utc


def _merge_persisted_coverage(
    fresh: dict[str, dict], persisted_json: str | None
) -> dict[str, dict]:
    try:
        persisted = json.loads(persisted_json or "{}").get("files", [])
    except (TypeError, ValueError, AttributeError):
        persisted = []
    for item in persisted if isinstance(persisted, list) else []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        if path in fresh:
            fresh[path]["reviewed"] = bool(item.get("reviewed"))
            fresh[path]["read_count"] = int(item.get("read_count") or 0)
            fresh[path]["phases"] = list(item.get("phases") or [])
    return fresh


def _is_transient_provider_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    try:
        import httpx

        if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
            return True
    except Exception:  # pragma: no cover - httpx is a runtime dependency
        pass
    status_code = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    status_code = status_code or getattr(response, "status_code", None)
    if status_code in {408, 409, 425, 429, 500, 502, 503, 504}:
        return True
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    return any(
        marker in name or marker in text
        for marker in (
            "connectionerror",
            "connecterror",
            "apiconnectionerror",
            "timeout",
            "temporarily unavailable",
            "connection reset",
            "connection refused",
            "network is unreachable",
            "name resolution",
            "dns",
        )
    )


def _normalize_tool_list(value: object) -> list:
    """Keep malformed string-valued tool arrays from splitting into characters."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        character_count = 0
        while (
            character_count < len(value)
            and isinstance(value[character_count], str)
            and len(value[character_count]) <= 1
        ):
            character_count += 1
        if character_count >= 8:
            text = "".join(value[:character_count])
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                decoded = text
            return [
                *(decoded if isinstance(decoded, list) else [decoded]),
                *value[character_count:],
            ]
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return decoded if isinstance(decoded, list) else [decoded]
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _close_unscored_candidates(candidates: list[dict]) -> int:
    """Give legacy candidates without an atomic discovery score a final state."""
    closed = 0
    proof_gap = "Discovery ended before a confidence score was recorded."
    for candidate in candidates:
        if (
            candidate.get("validation_status") == "pending"
            and candidate.get("confidence") is None
        ):
            candidate["validation_status"] = "inconclusive"
            candidate["validation_reasoning"] = proof_gap
            candidate["proof_gaps"] = list(
                dict.fromkeys(
                    [*_normalize_tool_list(candidate.get("proof_gaps")), proof_gap]
                )
            )
            candidate["reportable"] = False
            closed += 1
    return closed


def _validation_incomplete(candidate: dict) -> bool:
    """Tell unfinished validation apart from a validator's inconclusive verdict."""
    if candidate.get("validation_status") != "inconclusive":
        return False
    if candidate.get("validation_retry_pending"):
        return True
    # Candidates saved before the retry flag existed.
    reasoning = str(candidate.get("validation_reasoning") or "")
    return reasoning.startswith("Validator failed:") or reasoning in {
        "Validator returned no explicit verdict.",
        "Scan stopped before validation completed.",
    }


_VALIDATION_FAILED_GAPS = {
    "Independent validator failed before closing this candidate.",
    "Independent validator did not close this candidate.",
}


def _reset_incomplete_validation(candidate: dict) -> None:
    candidate.pop("validation_retry_pending", None)
    candidate["validation_status"] = "pending"
    candidate["validation_reasoning"] = ""
    candidate["reportable"] = False
    candidate["proof_gaps"] = [
        gap
        for gap in _normalize_tool_list(candidate.get("proof_gaps"))
        if gap not in _VALIDATION_FAILED_GAPS
    ]


def _pending_candidate_ids(candidates: list[dict]) -> list[int]:
    return [
        int(candidate["candidate_id"])
        for candidate in candidates
        if (
            candidate.get("validation_status") == "pending"
            or _validation_incomplete(candidate)
        )
        and candidate.get("confidence") is not None
        and not candidate.get("reconciled_duplicate")
    ]


def _candidate_brief(candidates: list[dict], *, reportable_only: bool = False) -> str:
    selected = (
        [c for c in candidates if c.get("reportable")]
        if reportable_only
        else candidates
    )
    return json.dumps(
        [
            {
                # The numeric key is private validator bookkeeping. Public
                # output and lead references use ``reference``.
                "candidate_id": c["candidate_id"],
                "reference": c.get("reference"),
                "title": c["title"],
                "category": c.get("category", ""),
                "severity": c.get("severity", "medium"),
                "location": c.get("location", ""),
                "description": c.get("description", ""),
                "discovery_confidence": c.get("confidence"),
                "validation_status": c.get("validation_status"),
            }
            for c in selected
        ],
        ensure_ascii=False,
        indent=2,
    )


def _candidate_validation_message(candidate: dict) -> str:
    candidate_id = int(candidate["candidate_id"])
    reference = candidate.get("reference") or f"#{candidate_id}"
    return (
        f"Validate only lead {reference} (internal candidate #{candidate_id}). "
        "Do not validate any other "
        "lead in the run. Call get_candidate for this candidate, inspect "
        "the relevant source with the read-only file tools, then call "
        "validate_candidate exactly once followed by done.\n\n"
        "Assigned candidate:\n" + json.dumps(candidate, ensure_ascii=False, indent=2)
    )


def _checkpoint_key(worker_key: str) -> str:
    return f"agent:{worker_key}"


def _save_checkpoint(
    sast_run_id: int,
    phase: str,
    key: str,
    data: dict[str, Any],
) -> None:
    from aespa.services.checkpoint import save_phase_checkpoint

    save_phase_checkpoint(
        sast_run_id,
        phase,
        key,
        data=data,
        run_kind="sast",
    )


def _load_checkpoint(sast_run_id: int, phase: str, key: str) -> dict[str, Any]:
    with Session(get_engine()) as s:
        row = s.exec(
            select(PhaseCheckpoint)
            .where(PhaseCheckpoint.run_kind == "sast")
            .where(PhaseCheckpoint.run_id == sast_run_id)
            .where(PhaseCheckpoint.phase == phase)
            .where(PhaseCheckpoint.idempotency_key == key)
        ).first()
    if row is None:
        return {}
    try:
        value = json.loads(row.data_json or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _clear_checkpoints(sast_run_id: int) -> None:
    with Session(get_engine()) as s:
        for row in s.exec(
            select(PhaseCheckpoint)
            .where(PhaseCheckpoint.run_kind == "sast")
            .where(PhaseCheckpoint.run_id == sast_run_id)
        ).all():
            s.delete(row)
        s.commit()


def _emit_agent_activity(
    sast_run_id: int,
    *,
    agent_id: str,
    role: str,
    status: str,
    current_task: str,
    outcome: str | None = None,
) -> None:
    """Persist and stream one SAST child-agent lifecycle event."""
    events_svc.emit(
        sast_run_id,
        {
            "type": "agent_status",
            "agent_id": agent_id,
            "role": role,
            "status": status,
            "current_task": current_task,
            "outcome": outcome,
            "_persist": True,
        },
    )


def _emit_validation_result(
    sast_run_id: int, candidate: dict, *, error: str | None = None
) -> None:
    candidate_id = int(candidate["candidate_id"])
    reference = candidate.get("reference") or f"#{candidate_id}"
    validation_status = str(candidate.get("validation_status") or "inconclusive")
    title = candidate.get("title", "")
    message = (
        f"Lead {reference} validation failed and was marked inconclusive: {title}"
        if error
        else f"Lead {reference} validated as {validation_status}: {title}"
    )
    data = {
        "candidate_id": candidate_id,
        "lead_reference": reference,
        "validation_status": validation_status,
        "confidence": float(candidate.get("confidence") or 0.0),
        "reportable": bool(candidate.get("reportable")),
    }
    if error:
        data["error"] = error
    events_svc.emit(
        sast_run_id,
        {
            "type": "scanner_phase",
            "phase": "sast_validation_result",
            "status": "complete",
            "message": message,
            "data": data,
        },
    )


def _build_initial_message(
    collection: ApiCollection | None,
    endpoints: list[ApiEndpoint],
    zip_filename: str,
) -> str:
    lines = [f"Source archive: {zip_filename}"]
    if collection is not None:
        lines.append(f"API collection: {collection.name}")
        lines.append(f"Base URL: {collection.base_url}")
    else:
        lines.append(
            "This is a standalone source review (no API collection or known "
            "endpoints). Discover the application's entry points yourself."
        )
    lines += [
        "",
        "You have read-only access to the extracted source tree via the file tools "
        "(list_files, glob, read_file, grep). Start by exploring the project "
        "structure, then systematically trace data flow from each of the following "
        "entry-point routes to identify high-confidence security vulnerabilities.",
        "",
    ]
    if endpoints:
        lines.append(f"Known entry points ({len(endpoints)} endpoints):")
        for ep in endpoints[:60]:
            auth_note = " [auth]" if ep.auth_required else ""
            summary_note = f" — {ep.summary}" if ep.summary else ""
            lines.append(f"  [{ep.method}] {ep.path}{auth_note}{summary_note}")
        if len(endpoints) > 60:
            lines.append(
                f"  … and {len(endpoints) - 60} more (discover via file tools)"
            )
    else:
        lines.append(
            "No pre-extracted endpoints are available. Use glob/grep to discover "
            "route definitions."
        )
    lines.append("")
    lines.append(
        "Begin with Phase 1 (project structure), then Phase 2 (trace each entry point), "
        "then Phase 3 (write_lead with confidence for each candidate). "
        "Call done when finished."
    )
    return "\n".join(lines)


def _persist_coverage(sast_run_id: int, coverage: dict[str, dict]) -> None:
    files = [coverage[path] for path in sorted(coverage)]
    languages: dict[str, dict[str, int]] = {}
    for item in files:
        row = languages.setdefault(item["language"], {"total": 0, "reviewed": 0})
        row["total"] += 1
        row["reviewed"] += int(bool(item["reviewed"]))
    payload = {
        "files": files,
        "summary": {
            "files_total": len(files),
            "files_reviewed": sum(bool(item["reviewed"]) for item in files),
            "bytes_total": sum(item["size"] for item in files),
            "languages": languages,
        },
    }
    with Session(get_engine()) as s:
        run = s.get(SastRun, sast_run_id)
        if run is not None:
            run.coverage_json = json.dumps(payload, ensure_ascii=False)
            run.updated_at = datetime.now(_UTC)
            s.add(run)
            s.commit()


def _update_sast_run_status(
    sast_run_id: int, status: str, error: str | None = None
) -> None:
    with Session(get_engine()) as s:
        r = s.get(SastRun, sast_run_id)
        if r is not None:
            r.status = status
            r.updated_at = datetime.now(_UTC)
            if error:
                r.error_message = error
            if status in ("completed", "failed", "cancelled"):
                r.completed_at = r.completed_at or datetime.now(_UTC)
            s.add(r)
            s.commit()
