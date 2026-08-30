"""Portable export and import for complete SAST runs.

The database keeps the source archive on disk, while the run state and scan
evidence live in SQLite.  A SAST export joins those two parts into one JSON
bundle so a run can be moved to another AESPA installation without losing the
source archive or the state shown in the SAST run view.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.models import (
    AgentLog,
    ApiDocument,
    ComponentFact,
    LLMProfile,
    SastEvidenceReceipt,
    SastPartition,
    SastRun,
    SastSourceFile,
    SastSurfaceItem,
    SastWorker,
    SastWorkItem,
    ScanLead,
    ScanLog,
)

EXPORT_VERSION = 1
EXPORT_KIND = "sast-run"
_MAX_ARCHIVE_BYTES = 250 * 1024 * 1024


class SastExportError(ValueError):
    """Raised when a SAST export is missing data or cannot be imported."""


def _row(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json")


def _parse_datetimes(data: dict[str, Any], *fields: str) -> None:
    for field in fields:
        value = data.get(field)
        if isinstance(value, str):
            data[field] = datetime.fromisoformat(value)


def _archive_for_run(session: Session, run: SastRun) -> tuple[str, bytes] | None:
    """Resolve the archive using the same legacy fallbacks as the scanner."""
    archive_path = run.source_archive_path
    archive_name = run.source_filename or "source.zip"

    document = None
    if run.document_id:
        document = session.get(ApiDocument, run.document_id)
    elif run.collection_id:
        document = session.exec(
            select(ApiDocument)
            .where(ApiDocument.collection_id == run.collection_id)
            .where(ApiDocument.doc_type == "source_zip")
            .order_by(ApiDocument.id.desc())  # type: ignore[attr-defined]
        ).first()
    if document is not None:
        archive_path = document.stored_path
        archive_name = document.filename

    if not archive_path:
        return None
    try:
        content = Path(archive_path).read_bytes()
    except OSError as exc:
        raise SastExportError(
            "The source archive for this SAST run is no longer available."
        ) from exc
    if len(content) > _MAX_ARCHIVE_BYTES:
        raise SastExportError(
            f"The source archive is larger than the {_MAX_ARCHIVE_BYTES // (1024 * 1024)} MiB export limit."
        )
    return Path(archive_name or "source.zip").name or "source.zip", content


def export_sast_run(session: Session, run_id: int) -> dict[str, Any]:
    """Return every persisted row owned by a SAST run plus its source ZIP."""
    run = session.get(SastRun, run_id)
    if run is None:
        raise SastExportError(f"SAST run id={run_id} does not exist")

    archive = _archive_for_run(session, run)
    source_archive = None
    if archive is not None:
        filename, content = archive
        source_archive = {
            "filename": filename,
            "content_b64": base64.b64encode(content).decode("ascii"),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    leads = session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_type == "sast")
        .where(ScanLead.producer_run_id == run_id)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        .order_by(ScanLead.id)
    ).all()
    scan_logs = session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.run_kind == "sast")
        .order_by(ScanLog.id)
    ).all()
    agent_logs = session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "sast")
        .order_by(AgentLog.id)
    ).all()
    component_facts = session.exec(
        select(ComponentFact)
        .where(ComponentFact.sast_run_id == run_id)
        .order_by(ComponentFact.id)
    ).all()
    work_program_models = (
        SastSourceFile,
        SastSurfaceItem,
        SastPartition,
        SastWorker,
        SastWorkItem,
        SastEvidenceReceipt,
    )
    work_program = {
        model.__tablename__: [
            _row(row)
            for row in session.exec(
                select(model).where(model.sast_run_id == run_id).order_by(model.id)
            ).all()
        ]
        for model in work_program_models
    }

    run_data = _row(run)
    # Absolute paths are installation-specific and can disclose local layout.
    run_data.pop("source_archive_path", None)

    return {
        "export_version": EXPORT_VERSION,
        "kind": EXPORT_KIND,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "sast_run": run_data,
        "source_archive": source_archive,
        "scan_leads": [_row(lead) for lead in leads],
        "scan_logs": [_row(log) for log in scan_logs],
        "agent_logs": [_row(log) for log in agent_logs],
        "component_facts": [_row(fact) for fact in component_facts],
        "work_program": work_program,
    }


def _decode_archive(source_archive: Any) -> tuple[str, bytes] | None:
    if source_archive is None:
        return None
    if not isinstance(source_archive, dict):
        raise SastExportError("source_archive must be an object or null")
    filename = Path(str(source_archive.get("filename") or "source.zip")).name
    if not filename:
        filename = "source.zip"
    encoded = source_archive.get("content_b64")
    if encoded is None:
        return None
    if not isinstance(encoded, str):
        raise SastExportError("source_archive.content_b64 must be a string")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SastExportError("source_archive.content_b64 is not valid base64") from exc
    if not content:
        raise SastExportError("The exported source archive is empty")
    if len(content) > _MAX_ARCHIVE_BYTES:
        raise SastExportError(
            f"The source archive is larger than the {_MAX_ARCHIVE_BYTES // (1024 * 1024)} MiB import limit."
        )
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise SastExportError("The exported source archive is not a valid ZIP file")
    expected_sha256 = source_archive.get("sha256")
    if expected_sha256 and hashlib.sha256(content).hexdigest() != expected_sha256:
        raise SastExportError("The source archive checksum does not match the export")
    return filename, content


def _store_archive(filename: str, content: bytes) -> str:
    base = Path(get_settings().data_dir) / "sast_uploads"
    base.mkdir(parents=True, exist_ok=True)
    extension = Path(filename).suffix or ".zip"
    path = base / f"{uuid.uuid4().hex}{extension}"
    path.write_bytes(content)
    return str(path)


def _validate_bundle(bundle: Any) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        raise SastExportError("SAST export must be a JSON object")
    if (
        bundle.get("export_version") != EXPORT_VERSION
        or bundle.get("kind") != EXPORT_KIND
    ):
        raise SastExportError(
            "Unsupported or non-SAST export bundle: "
            f"version={bundle.get('export_version')!r} kind={bundle.get('kind')!r}"
        )
    if not isinstance(bundle.get("sast_run"), dict):
        raise SastExportError("SAST export is missing run data")
    return bundle


def import_sast_run(session: Session, bundle: Any) -> SastRun:
    """Create a standalone SAST run from an export bundle.

    A run export may have come from an API collection or a campaign.  Those
    parent records are intentionally not recreated here; the imported run gets
    its own source archive and keeps all state that the SAST screen displays.
    """
    bundle = _validate_bundle(bundle)
    source_archive = _decode_archive(bundle.get("source_archive"))

    run_data = dict(bundle["sast_run"])
    run_data.pop("id", None)
    run_data.pop("collection_id", None)
    run_data.pop("document_id", None)
    run_data.pop("source_archive_path", None)
    run_data["collection_id"] = None
    run_data["document_id"] = None
    run_data["triggered_by_run_type"] = None
    run_data["triggered_by_run_id"] = None
    # Provider connection IDs belong to the source installation. A local
    # profile can still be selected later from the run settings screen.
    run_data["llm_config_id"] = None
    if (
        run_data.get("llm_profile_id") is not None
        and session.get(LLMProfile, run_data["llm_profile_id"]) is None
    ):
        run_data["llm_profile_id"] = None
    _parse_datetimes(run_data, "created_at", "updated_at", "started_at", "completed_at")
    if source_archive is not None:
        filename, content = source_archive
        run_data["source_filename"] = filename
        run_data["source_archive_path"] = _store_archive(filename, content)
    else:
        run_data["source_archive_path"] = None

    run = SastRun(**run_data)
    session.add(run)
    session.flush()
    new_run_id: int = run.id  # type: ignore[assignment]

    work_program = bundle.get("work_program")
    if work_program is not None and not isinstance(work_program, dict):
        raise SastExportError("work_program must be an object")
    work_program = work_program or {}
    id_maps: dict[str, dict[int, int]] = {
        "source": {},
        "surface": {},
        "partition": {},
        "worker": {},
        "work_item": {},
        "receipt": {},
        "lead": {},
    }
    pending_work_leads: dict[int, int] = {}

    def _import_rows(key: str, model, map_name: str, transform) -> None:
        rows = work_program.get(key, [])
        if not isinstance(rows, list):
            raise SastExportError(f"work_program.{key} must be an array")
        for item in rows:
            if not isinstance(item, dict):
                raise SastExportError(f"work_program.{key} entries must be objects")
            data = dict(item)
            old_id = int(data.pop("id"))
            data["sast_run_id"] = new_run_id
            transform(data, old_id)
            row = model(**data)
            session.add(row)
            session.flush()
            id_maps[map_name][old_id] = int(row.id)

    _import_rows(
        "sast_source_file",
        SastSourceFile,
        "source",
        lambda data, _old_id: _parse_datetimes(data, "created_at"),
    )

    def _surface_transform(data: dict, _old_id: int) -> None:
        source_id = data.get("source_file_id")
        data["source_file_id"] = id_maps["source"].get(source_id)
        _parse_datetimes(data, "created_at")

    _import_rows("sast_surface_item", SastSurfaceItem, "surface", _surface_transform)
    _import_rows(
        "sast_partition",
        SastPartition,
        "partition",
        lambda data, _old_id: _parse_datetimes(
            data, "started_at", "completed_at", "created_at", "updated_at"
        ),
    )

    def _worker_transform(data: dict, _old_id: int) -> None:
        partition_id = data.get("partition_id")
        data["partition_id"] = id_maps["partition"].get(partition_id)
        _parse_datetimes(data, "started_at", "completed_at", "created_at", "updated_at")

    _import_rows("sast_worker", SastWorker, "worker", _worker_transform)

    def _work_item_transform(data: dict, old_id: int) -> None:
        data["partition_id"] = id_maps["partition"].get(data.get("partition_id"))
        data["surface_item_id"] = id_maps["surface"].get(data.get("surface_item_id"))
        data["worker_id"] = id_maps["worker"].get(data.get("worker_id"))
        old_lead_id = data.get("lead_id")
        if old_lead_id is not None:
            pending_work_leads[old_id] = int(old_lead_id)
        data["lead_id"] = None
        _parse_datetimes(data, "created_at", "updated_at")

    _import_rows("sast_work_item", SastWorkItem, "work_item", _work_item_transform)

    def _receipt_transform(data: dict, _old_id: int) -> None:
        data["worker_id"] = id_maps["worker"].get(data.get("worker_id"))
        _parse_datetimes(data, "created_at")

    _import_rows(
        "sast_evidence_receipt",
        SastEvidenceReceipt,
        "receipt",
        _receipt_transform,
    )

    for item in bundle.get("scan_leads", []):
        if not isinstance(item, dict):
            raise SastExportError("scan_leads entries must be objects")
        lead_data = dict(item)
        old_lead_id = lead_data.pop("id", None)
        lead_data["producer_run_type"] = "sast"
        lead_data["producer_run_id"] = new_run_id
        lead_data["collection_id"] = None
        lead_data["imported_into_run_type"] = None
        lead_data["imported_into_run_id"] = None
        lead_data["investigated_by_run_type"] = None
        lead_data["investigated_by_run_id"] = None
        # A linked finding belongs to a dynamic run, not to the SAST run. It
        # cannot be restored safely without exporting that other run as well.
        lead_data["linked_finding_id"] = None
        lead_data["source_work_item_id"] = id_maps["work_item"].get(
            lead_data.get("source_work_item_id")
        )
        _parse_datetimes(lead_data, "created_at", "updated_at")
        lead = ScanLead(**lead_data)
        session.add(lead)
        session.flush()
        if old_lead_id is not None:
            id_maps["lead"][int(old_lead_id)] = int(lead.id)

    for old_work_id, old_lead_id in pending_work_leads.items():
        new_work_id = id_maps["work_item"].get(old_work_id)
        new_lead_id = id_maps["lead"].get(old_lead_id)
        if new_work_id is None or new_lead_id is None:
            continue
        work_item = session.get(SastWorkItem, new_work_id)
        if work_item is not None:
            work_item.lead_id = new_lead_id
            session.add(work_item)

    for item in bundle.get("scan_logs", []):
        if not isinstance(item, dict):
            raise SastExportError("scan_logs entries must be objects")
        log_data = dict(item)
        log_data.pop("id", None)
        log_data["test_run_id"] = new_run_id
        log_data["run_kind"] = "sast"
        _parse_datetimes(log_data, "created_at")
        session.add(ScanLog(**log_data))

    for item in bundle.get("agent_logs", []):
        if not isinstance(item, dict):
            raise SastExportError("agent_logs entries must be objects")
        log_data = dict(item)
        log_data.pop("id", None)
        log_data["test_run_id"] = new_run_id
        log_data["run_kind"] = "sast"
        _parse_datetimes(log_data, "created_at")
        session.add(AgentLog(**log_data))

    for item in bundle.get("component_facts", []):
        if not isinstance(item, dict):
            raise SastExportError("component_facts entries must be objects")
        fact_data = dict(item)
        fact_data.pop("id", None)
        fact_data["sast_run_id"] = new_run_id
        # Component IDs belong to a campaign/application that is not imported.
        fact_data["component_id"] = None
        _parse_datetimes(fact_data, "created_at")
        session.add(ComponentFact(**fact_data))

    session.commit()
    session.refresh(run)
    return run
