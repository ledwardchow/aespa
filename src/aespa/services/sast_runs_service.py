"""Create and control SAST runs.

The ``/api`` routes and the API extension both call these functions, so each
request is checked by the same rules. Errors are raised as ``HTTPException`` to
match the other run services.
"""

from __future__ import annotations

import hashlib
import json
import uuid
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from aespa.config import get_settings
from aespa.models import SastRun

# Keep standalone uploads aligned with SAST export/import archives.
MAX_UPLOAD_BYTES = 250 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
ANALYSIS_MODES = {"light", "deep"}


@dataclass(frozen=True)
class StoredArchive:
    path: Path
    original_name: str
    sha256: str


def get_run(session: Session, run_id: int) -> SastRun:
    run = session.get(SastRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="SAST run not found")
    return run


def check_analysis_mode(analysis_mode: str) -> None:
    if analysis_mode not in ANALYSIS_MODES:
        raise HTTPException(
            status_code=422,
            detail="Analysis mode must be either 'light' or 'deep'.",
        )


def _check_profile(session: Session, llm_profile_id: int | None) -> None:
    if llm_profile_id is not None:
        from aespa.services.settings_profiles import get_scan_profile

        get_scan_profile(session, llm_profile_id)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(UPLOAD_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def store_upload(
    read: Callable[[int], Awaitable[bytes]], filename: str | None
) -> StoredArchive:
    """Stream an uploaded ZIP into AESPA's upload folder and check it."""
    original_name = Path(filename or "source.zip").name or "source.zip"
    base = Path(get_settings().data_dir) / "sast_uploads"
    base.mkdir(parents=True, exist_ok=True)
    ext = Path(original_name).suffix or ".zip"
    upload_id = uuid.uuid4().hex
    temp_path = base / f".{upload_id}.upload"
    stored_path = base / f"{upload_id}{ext}"
    bytes_written = 0
    try:
        with temp_path.open("wb") as destination:
            while True:
                chunk = await read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB "
                            "upload limit."
                        ),
                    )
                destination.write(chunk)

        if bytes_written == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if not zipfile.is_zipfile(temp_path):
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid ZIP archive."
            )
        temp_path.replace(stored_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return StoredArchive(stored_path, original_name, file_sha256(stored_path))


def create_from_archive(
    session: Session,
    archive: StoredArchive,
    *,
    name: str | None = None,
    analysis_mode: str = "deep",
    llm_config_id: int | None = None,
    llm_profile_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> SastRun:
    """Create a pending SAST run from a stored upload. Nothing is started."""
    check_analysis_mode(analysis_mode)
    _check_profile(session, llm_profile_id)
    from aespa.services import sast_scanner

    return sast_scanner.create_sast_run(
        collection_id=None,
        name=name or f"SAST – {archive.original_name}",
        source_archive_path=str(archive.path),
        source_filename=archive.original_name,
        source_provider="upload",
        source_locator=archive.original_name,
        source_archive_sha256=archive.sha256,
        source_metadata_json=(
            json.dumps(metadata, ensure_ascii=False) if metadata else None
        ),
        analysis_mode=analysis_mode,
        llm_config_id=llm_config_id,
        llm_profile_id=llm_profile_id,
    )


async def create_from_source(
    session: Session,
    *,
    provider_id: str,
    parameters: dict[str, Any],
    name: str | None = None,
    analysis_mode: str = "deep",
    llm_profile_id: int | None = None,
    start_scan: bool = True,
    metadata: dict[str, Any] | None = None,
) -> SastRun:
    """Create a SAST run whose source is prepared by an extension provider."""
    check_analysis_mode(analysis_mode)
    _check_profile(session, llm_profile_id)

    from aespa.extensions import get_extension_manager
    from aespa.services import sast_scanner, sast_sources

    manager = get_extension_manager()
    manager.ensure_loaded()
    registered = manager.source_providers.get(provider_id)
    if registered is None:
        raise HTTPException(status_code=404, detail="SAST source provider not found")
    availability = await registered.provider.check_availability(
        manager.context_for(registered.extension_id)
    )
    if not availability.available:
        raise HTTPException(status_code=409, detail=availability.message)

    repository = parameters.get("repository")
    default_name = (
        f"SAST - {repository}"
        if isinstance(repository, str) and repository
        else "SAST scan"
    )
    run = sast_scanner.create_sast_run(
        collection_id=None,
        name=(name or "").strip() or default_name,
        source_provider=provider_id,
        source_locator=repository if isinstance(repository, str) else None,
        source_requested_ref=(str(parameters.get("ref") or "").strip() or None),
        source_metadata_json=json.dumps(
            {"request": parameters, **(metadata or {})}, ensure_ascii=False
        ),
        analysis_mode=analysis_mode,
        llm_profile_id=llm_profile_id,
        status="preparing",
    )
    sast_sources.start_source_preparation(
        run.id,
        provider_id,
        parameters,
        auto_start=start_scan,
    )
    return run


async def start(session: Session, run_id: int) -> None:
    run = get_run(session, run_id)
    if run.status == "preparing":
        raise HTTPException(
            status_code=409,
            detail="The source snapshot is still being prepared.",
        )
    if not run.source_archive_path and run.source_provider != "upload":
        raise HTTPException(
            status_code=409,
            detail="The source snapshot is not ready. Resume source preparation first.",
        )
    from aespa.services import sast_scanner

    await sast_scanner.start_sast_scan(run_id)


def can_resume(run: SastRun) -> bool:
    """Whether ``resume`` can continue the run from its saved progress."""
    from aespa.services import run_pause, sast_scanner

    if sast_scanner.is_sast_scan_running(run.id):
        return False
    if run.status == "paused":
        return run_pause.get_pause("sast", run.id) is not None
    return run.status in {
        "completed",
        "failed",
        "cancelled",
    } and sast_scanner.has_resumable_sast_work(run.id)


async def resume(session: Session, run_id: int) -> None:
    """Continue a paused run, or a finished run with unfinished work."""
    from aespa.services import run_pause, sast_scanner

    run = get_run(session, run_id)
    if sast_scanner.is_sast_scan_running(run_id):
        raise HTTPException(status_code=409, detail="SAST scan is already running")
    if not can_resume(run):
        raise HTTPException(
            status_code=409,
            detail="SAST scan has no paused or failed worker work to resume",
        )
    pause = run_pause.get_pause("sast", run_id)
    if pause and pause.reset_at and pause.reset_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=409,
            detail={"message": pause.message, "reset_at": pause.reset_at.isoformat()},
        )
    await sast_scanner.start_sast_scan(run_id, resume=True)
    run_pause.clear_pause("sast", run_id)


async def stop(session: Session, run_id: int) -> bool:
    get_run(session, run_id)
    from aespa.services import sast_scanner, sast_sources

    source_stopped = await sast_sources.stop_source_preparation_and_wait(run_id)
    stopped = await sast_scanner.stop_sast_scan(run_id)
    return bool(stopped or source_stopped)
