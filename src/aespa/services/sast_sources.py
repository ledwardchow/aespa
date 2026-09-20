"""Prepare immutable SAST source archives through registered extensions."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
import stat
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_engine
from aespa.extensions import get_extension_manager
from aespa.models import SastRun
from aespa.services import events as events_svc

log = logging.getLogger(__name__)
_UTC = timezone.utc
_MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
_MAX_FILES = 10_000
_MAX_FILE_BYTES = 50 * 1024 * 1024
_MAX_TOTAL_BYTES = 250 * 1024 * 1024
_tasks: dict[int, asyncio.Task] = {}


def is_source_preparation_running(run_id: int) -> bool:
    task = _tasks.get(run_id)
    return task is not None and not task.done()


def _emit(run_id: int, status: str, message: str, **details: Any) -> None:
    events_svc.emit(
        run_id,
        {
            "_run_kind": "sast",
            "type": "source_preparation",
            "status": status,
            "message": message,
            **details,
        },
    )


def _archive_tree(source: Path, destination: Path) -> tuple[str, int, int]:
    files: list[Path] = []
    total_bytes = 0
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink() or not path.is_file():
            continue
        size = path.stat().st_size
        if size > _MAX_FILE_BYTES:
            raise ValueError(
                f"Source file {path.relative_to(source).as_posix()!r} exceeds the "
                f"{_MAX_FILE_BYTES // (1024 * 1024)} MiB limit."
            )
        files.append(path)
        total_bytes += size
        if len(files) > _MAX_FILES:
            raise ValueError(f"Source contains more than {_MAX_FILES} files.")
        if total_bytes > _MAX_TOTAL_BYTES:
            raise ValueError(
                f"Source exceeds the {_MAX_TOTAL_BYTES // (1024 * 1024)} MiB limit."
            )

    digest = hashlib.sha256()
    with destination.open("wb") as raw:
        with zipfile.ZipFile(
            raw, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            for path in files:
                relative = path.relative_to(source).as_posix()
                data = path.read_bytes()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                executable = bool(path.stat().st_mode & stat.S_IXUSR)
                info.external_attr = ((0o755 if executable else 0o644) & 0xFFFF) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        raw.flush()
    if not files:
        destination.unlink(missing_ok=True)
        raise ValueError("The prepared source archive contains no regular files.")
    if destination.stat().st_size > _MAX_ARCHIVE_BYTES:
        destination.unlink(missing_ok=True)
        raise ValueError(
            f"Prepared archive exceeds the {_MAX_ARCHIVE_BYTES // (1024 * 1024)} MiB limit."
        )
    with destination.open("rb") as archive_file:
        for chunk in iter(lambda: archive_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), len(files), total_bytes


async def _prepare_source(
    run_id: int,
    provider_id: str,
    parameters: dict[str, Any],
    *,
    auto_start: bool,
) -> None:
    settings = get_settings()
    staging = Path(settings.data_dir) / "sast_source_prepare" / str(run_id)
    uploads = Path(settings.data_dir) / "sast_uploads"
    stored_path: Path | None = None
    try:
        manager = get_extension_manager()
        manager.ensure_loaded()
        registered = manager.source_providers.get(provider_id)
        if registered is None:
            raise RuntimeError(f"SAST source provider {provider_id!r} is not available")
        context = manager.context_for(registered.extension_id)
        availability = await registered.provider.check_availability(context)
        if not availability.available:
            raise RuntimeError(availability.message)

        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        _emit(run_id, "running", "Cloning repository with local CLI credentials.")
        materialized = await registered.provider.materialize(
            parameters, staging, context
        )
        if not materialized.archive_path.is_file():
            raise RuntimeError("The source provider did not create an archive")
        if materialized.archive_path.stat().st_size > _MAX_ARCHIVE_BYTES:
            raise ValueError(
                f"Prepared archive exceeds the {_MAX_ARCHIVE_BYTES // (1024 * 1024)} MiB limit."
            )

        extracted = staging / "extracted"
        extracted.mkdir(parents=True, exist_ok=True)
        from aespa.services.sast_scanner import _safe_unzip

        _safe_unzip(str(materialized.archive_path), str(extracted))
        uploads.mkdir(parents=True, exist_ok=True)
        stored_path = uploads / f"{uuid.uuid4().hex}.zip"
        sha256, file_count, source_bytes = _archive_tree(extracted, stored_path)
        filename = (
            materialized.display_name.replace("/", "-").replace("@", "-") + ".zip"
        )
        metadata = {
            **materialized.metadata,
            "request": parameters,
            "file_count": file_count,
            "source_bytes": source_bytes,
        }
        with Session(get_engine()) as session:
            run = session.get(SastRun, run_id)
            if run is None:
                stored_path.unlink(missing_ok=True)
                return
            run.source_archive_path = str(stored_path)
            run.source_filename = filename
            run.source_locator = materialized.locator
            run.source_requested_ref = materialized.requested_ref
            run.source_revision = materialized.revision
            run.source_archive_sha256 = sha256
            run.source_metadata_json = json.dumps(metadata, ensure_ascii=False)
            run.status = "pending"
            run.error_message = None
            run.updated_at = datetime.now(_UTC)
            session.add(run)
            session.commit()
        _emit(
            run_id,
            "complete",
            "Source snapshot is ready.",
            revision=materialized.revision,
            file_count=file_count,
        )
        if auto_start:
            from aespa.services import sast_scanner

            await sast_scanner.start_sast_scan(run_id)
    except asyncio.CancelledError:
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        with Session(get_engine()) as session:
            run = session.get(SastRun, run_id)
            if run is not None and run.status == "preparing":
                run.status = "cancelled"
                run.error_message = "Source preparation was cancelled."
                run.updated_at = datetime.now(_UTC)
                session.add(run)
                session.commit()
        _emit(run_id, "cancelled", "Source preparation was cancelled.")
        raise
    except Exception as exc:  # noqa: BLE001 - persist provider failures on the run
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        message = str(exc) or type(exc).__name__
        with Session(get_engine()) as session:
            run = session.get(SastRun, run_id)
            if run is not None:
                run.status = "failed"
                run.error_message = message
                run.updated_at = datetime.now(_UTC)
                session.add(run)
                session.commit()
        _emit(run_id, "failed", message)
        log.warning("Source preparation failed for SAST run %s: %s", run_id, message)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        _tasks.pop(run_id, None)


def start_source_preparation(
    run_id: int,
    provider_id: str,
    parameters: dict[str, Any],
    *,
    auto_start: bool,
) -> None:
    if is_source_preparation_running(run_id):
        raise RuntimeError("Source preparation is already running")
    _tasks[run_id] = asyncio.create_task(
        _prepare_source(run_id, provider_id, parameters, auto_start=auto_start),
        name=f"sast-source-{run_id}",
    )


async def stop_source_preparation_and_wait(run_id: int) -> bool:
    task = _tasks.get(run_id)
    if task is None or task.done():
        return False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    return True


def reconcile_interrupted_source_preparations() -> int:
    count = 0
    with Session(get_engine()) as session:
        runs = list(session.exec(select(SastRun).where(SastRun.status == "preparing")))
        for run in runs:
            run.status = "failed"
            run.error_message = "AESPA stopped while preparing the source snapshot. Create the scan again."
            run.updated_at = datetime.now(_UTC)
            session.add(run)
            count += 1
        if count:
            session.commit()
    return count
