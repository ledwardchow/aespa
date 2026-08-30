"""SAST scan orchestration.

Provides a first-class agentic static-analysis scan over an uploaded source
archive (``ApiDocument`` with ``doc_type='source_zip'``).  Mirrors the
``api_scanner.py`` background-task lifecycle: task registry, start/stop/status,
SSE events via ``events_svc``, and ``AgentLog`` / ``ScanLog`` persistence.

The scan:
1. Extracts the archive into a deterministic per-run directory
   (``<data_dir>/sast_extract/<id>/``) that a startup sweep can reconcile
   if the process crashes mid-scan.
2. Inventories source files and records deterministic inspection receipts.
3. Runs separate discovery, independent validation, and attack-path agents.
4. Persists structured evidence, explicit proof gaps, and reportability decisions.
"""

from __future__ import annotations

import asyncio
import contextlib
import fnmatch
import json
import logging
import os
import re
import shutil
import stat
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_engine
from aespa.models import (
    ApiCollection,
    ApiDocument,
    ApiEndpoint,
    PhaseCheckpoint,
    SastEvidenceReceipt,
    SastRun,
    SastWorker,
    ScanLead,
)
from aespa.sast_workspace import (
    SastWorkspaceLease,
    try_acquire_sast_workspace_lease,
)
from aespa.services import events as events_svc
from aespa.services import sast_workprogram as workprogram_svc
from aespa.services.scan_leads import (
    CONFIDENCE_THRESHOLD,
    create_lead,
    lead_fingerprint,
)

log = logging.getLogger(__name__)

_UTC = timezone.utc

# ── In-memory state ────────────────────────────────────────────────────────────

_sast_tasks: dict[int, asyncio.Task] = {}
_sast_workspace_leases: dict[int, SastWorkspaceLease] = {}
_sast_stop_requested: set[int] = set()
_sast_pause_requested: set[int] = set()

# Candidates accumulated by write_lead within a single scan task.
# sast_run_id → list of candidate dicts (awaiting filter_lead scoring).
_candidates: dict[int, list[dict]] = {}

# Max characters in a single read_file response.
_READ_FILE_MAX_CHARS = 20_000
# Max grep results.
_GREP_MAX_RESULTS = 200
# Keep archive extraction and source inspection bounded even when the uploaded
# ZIP is small after compression.
_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_ARCHIVE_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
_MAX_ARCHIVE_ENTRY_BYTES = 50 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 1_000
_MAX_INSPECT_FILE_BYTES = 10 * 1024 * 1024
_PHASES = ("scope", "discovery", "validation", "attack_path", "report")
_SAST_VALIDATOR_MAX_CONCURRENT = 4
_SAST_NETWORK_RETRY_DELAYS = (1.0, 2.0, 4.0)


class SastPauseRequested(RuntimeError):
    """The current SAST task reached a safe user-requested pause boundary."""


class SastNetworkPause(RuntimeError):
    """Transient provider connectivity remained unavailable after retries."""


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


def _persist_candidate_state(sast_run_id: int) -> None:
    _save_checkpoint(
        sast_run_id,
        "state",
        "candidates",
        {"candidates": _candidates.get(sast_run_id, [])},
    )


def _restore_candidate_state(sast_run_id: int) -> list[dict]:
    value = _load_checkpoint(sast_run_id, "state", "candidates").get("candidates")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


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


async def _run_checkpointed_agent(
    *,
    sast_run_id: int,
    phase: str,
    worker_key: str,
    config,
    system_message: str,
    initial_user_message: str,
    tool_executor,
    emit_fn,
    stop_check,
    tools: list[dict],
    resume: bool,
    done_check=None,
    termination_check=None,
) -> str:
    """Run one SAST agent with durable turn checkpoints and bounded retries."""
    from aespa.services import llm as llm_svc

    key = _checkpoint_key(worker_key)
    saved = _load_checkpoint(sast_run_id, phase, key) if resume else {}
    last_error: BaseException | None = None
    for attempt in range(len(_SAST_NETWORK_RETRY_DELAYS) + 1):
        messages = saved.get("messages")
        step_count = int(saved.get("step_count") or 0)

        async def _on_checkpoint(new_messages: list[dict], new_step_count: int) -> None:
            nonlocal saved
            saved = {
                "messages": new_messages,
                "step_count": new_step_count,
                "worker_key": worker_key,
            }
            _save_checkpoint(sast_run_id, phase, key, saved)

        try:
            return await llm_svc.thinking_agentic_loop(
                config,
                system_message=system_message,
                initial_user_message=initial_user_message,
                tool_executor=tool_executor,
                emit_fn=emit_fn,
                stop_check=stop_check,
                tools=tools,
                resume_messages=messages if isinstance(messages, list) else None,
                resume_step_count=step_count,
                on_checkpoint=_on_checkpoint,
                done_check=done_check,
                termination_check=termination_check,
            )
        except llm_svc.LLMQuotaPauseError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not _is_transient_provider_error(exc):
                raise
            last_error = exc
            if attempt >= len(_SAST_NETWORK_RETRY_DELAYS):
                break
            delay = _SAST_NETWORK_RETRY_DELAYS[attempt]
            events_svc.emit(
                sast_run_id,
                {
                    "type": "scanner_phase",
                    "phase": "llm_response",
                    "status": "warning",
                    "message": (
                        "The LLM connection was interrupted. Retrying from the "
                        f"last saved step in {delay:g} second(s)."
                    ),
                    "data": {"attempt": attempt + 1, "error": str(exc)},
                },
            )
            await asyncio.sleep(delay)
    raise SastNetworkPause(
        "The LLM provider is still unreachable. The scan was paused at its last "
        f"saved step and can be resumed safely. Last error: {last_error}"
    ) from last_error


def _notify_campaign_source_started(sast_run_id: int) -> None:
    """Keep a campaign child in sync when the SAST page starts its scan."""
    try:
        from aespa.services import campaigns as campaigns_svc

        campaigns_svc.notify_source_run_started(sast_run_id)
    except Exception:  # noqa: BLE001 - a campaign sync must not stop SAST
        log.exception(
            "Could not sync campaign source member for started SAST run %s",
            sast_run_id,
        )


def _notify_campaign_source_finished(sast_run_id: int, status: str) -> None:
    """Keep a campaign child in sync when its SAST task reaches a terminal state."""
    try:
        from aespa.services import campaigns as campaigns_svc

        campaigns_svc.notify_source_run_finished(sast_run_id, status)
    except Exception:  # noqa: BLE001 - a campaign sync must not stop SAST
        log.exception(
            "Could not sync campaign source member for finished SAST run %s",
            sast_run_id,
        )


def _persist_paused_run(
    sast_run_id: int,
    *,
    phase: str,
    reason: str,
    message: str,
    provider: str = "",
    reset_at: datetime | None = None,
    snapshot: dict[str, Any] | None = None,
) -> None:
    from aespa.services import run_pause as run_pause_svc

    with Session(get_engine()) as s:
        run = s.get(SastRun, sast_run_id)
        if run is not None:
            run.status = "paused"
            run.error_message = message[:2000]
            run.completed_at = None
            run.updated_at = datetime.now(_UTC)
            s.add(run)
            s.commit()
    run_pause_svc.save_pause(
        "sast",
        sast_run_id,
        provider=provider,
        message=message,
        reset_at=reset_at,
        snapshot=snapshot,
        resume_stage=phase,
        reason=reason,
    )
    _set_phase(sast_run_id, phase, "paused", message)
    events_svc.emit(
        sast_run_id,
        {
            "type": "scan_paused",
            "reason": reason,
            "message": message,
            "reset_at": reset_at.isoformat() if reset_at else None,
        },
    )


def _empty_phase_state() -> dict[str, dict]:
    return {
        phase: {"status": "pending", "message": "", "data": {}} for phase in _PHASES
    }


def _set_phase(
    sast_run_id: int,
    phase: str,
    status: str,
    message: str,
    data: dict | None = None,
) -> None:
    """Persist and emit authoritative semantic phase state."""
    now = datetime.now(_UTC).isoformat()
    with Session(get_engine()) as s:
        run = s.get(SastRun, sast_run_id)
        if run is not None:
            try:
                state = json.loads(run.phase_state_json or "{}")
            except (TypeError, ValueError):
                state = {}
            if not state:
                state = _empty_phase_state()
            entry = state.setdefault(phase, {})
            entry.update(
                {
                    "status": status,
                    "message": message,
                    "data": data or {},
                    "updated_at": now,
                }
            )
            if status == "running" and not entry.get("started_at"):
                entry["started_at"] = now
            if status in {"complete", "failed", "cancelled"}:
                entry["completed_at"] = now
            run.phase_state_json = json.dumps(state, ensure_ascii=False)
            run.updated_at = datetime.now(_UTC)
            s.add(run)
            s.commit()
    events_svc.emit(
        sast_run_id,
        {
            "type": "scanner_phase",
            "phase": phase,
            "status": status,
            "message": message,
            "data": data or {},
        },
    )


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


# ── Safe archive extraction ────────────────────────────────────────────────────


def _safe_unzip(archive_path: str, target_dir: str) -> None:
    """Extract a zip archive, rejecting any entries that would escape target_dir."""
    target = Path(target_dir).resolve()
    with zipfile.ZipFile(archive_path, "r") as zf:
        members = zf.infolist()
        if len(members) > _MAX_ARCHIVE_ENTRIES:
            raise ValueError(
                f"Archive contains too many entries (maximum {_MAX_ARCHIVE_ENTRIES})."
            )

        total_uncompressed = 0
        for info in members:
            if info.is_dir():
                continue
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                continue
            if info.file_size > _MAX_ARCHIVE_ENTRY_BYTES:
                raise ValueError(
                    f"Archive entry {info.filename!r} exceeds the "
                    f"{_MAX_ARCHIVE_ENTRY_BYTES // (1024 * 1024)} MiB limit."
                )
            total_uncompressed += info.file_size
            if total_uncompressed > _MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ValueError(
                    "Archive exceeds the total uncompressed-size limit of "
                    f"{_MAX_ARCHIVE_UNCOMPRESSED_BYTES // (1024 * 1024)} MiB."
                )
            if (
                info.compress_size > 0
                and info.file_size / info.compress_size > _MAX_COMPRESSION_RATIO
            ):
                raise ValueError(
                    f"Archive entry {info.filename!r} has an unsafe compression ratio."
                )

        seen: set[Path] = set()
        for info in members:
            member = info.filename
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                log.warning("_safe_unzip: skipping symlink entry %r", member)
                continue
            dest = (target / member).resolve()
            # Use is_relative_to rather than string-prefix matching: a prefix
            # check treats ``…/extract/55`` as inside ``…/extract/5`` and lets a
            # crafted entry escape into a sibling directory.
            if dest != target and not dest.is_relative_to(target):
                log.warning("_safe_unzip: skipping path-traversal entry %r", member)
                continue
            if dest in seen:
                log.warning("_safe_unzip: skipping duplicate entry %r", member)
                continue
            seen.add(dest)
            zf.extract(info, target_dir)


# ── Path jail helpers ──────────────────────────────────────────────────────────


def _jail(root: Path, rel: str) -> Path:
    """Resolve *rel* within *root*, raising ValueError if it escapes."""
    if not rel:
        return root
    candidate = (root / rel).resolve()
    # is_relative_to, not a string-prefix check: ``…/extract/55`` must not be
    # treated as living inside ``…/extract/5``.
    if candidate != root and not candidate.is_relative_to(root):
        raise ValueError(f"Path escape attempt: {rel!r}")
    return candidate


# ── File tool implementations ──────────────────────────────────────────────────


def _tool_list_files(root: Path, path: str = "", max_depth: int = 3) -> str:
    try:
        base = _jail(root, path)
    except ValueError as exc:
        return f"Error: {exc}"
    if not base.is_dir():
        return f"Error: not a directory: {path!r}"
    lines: list[str] = []
    try:
        for dirpath, dirnames, filenames in os.walk(base):
            depth = len(Path(dirpath).relative_to(base).parts)
            if depth >= max_depth:
                dirnames.clear()
                continue
            # Sort for determinism.
            dirnames.sort()
            filenames.sort()
            rel_dir = str(Path(dirpath).relative_to(root))
            for fn in filenames:
                lines.append(os.path.join(rel_dir, fn) if rel_dir != "." else fn)
            if depth + 1 < max_depth:
                for dn in dirnames:
                    rel_sub = os.path.join(rel_dir, dn) if rel_dir != "." else dn
                    lines.append(rel_sub + "/")
    except Exception as exc:
        return f"Error listing files: {exc}"
    return "\n".join(lines[:2000]) or "(empty)"


def _tool_glob(root: Path, pattern: str) -> str:
    try:
        matches = sorted(str(p.relative_to(root)) for p in root.rglob(pattern))
    except Exception as exc:
        return f"Error: {exc}"
    return "\n".join(matches[:500]) or "(no matches)"


def _tool_read_file(
    root: Path, path: str, start_line: int | None, end_line: int | None
) -> str:
    try:
        target = _jail(root, path)
    except ValueError as exc:
        return f"Error: {exc}"
    if not target.is_file():
        return f"Error: not a file: {path!r}"
    try:
        if target.stat().st_size > _MAX_INSPECT_FILE_BYTES:
            return (
                f"Error: file exceeds the {_MAX_INSPECT_FILE_BYTES // (1024 * 1024)} "
                "MiB inspection limit. Use a narrower generated artifact or grep."
            )
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Error reading file: {exc}"
    lines = text.splitlines(keepends=True)
    if start_line is not None or end_line is not None:
        s = max(0, (start_line or 1) - 1)
        e = end_line if end_line is not None else len(lines)
        lines = lines[s:e]
    result = "".join(lines)
    if len(result) > _READ_FILE_MAX_CHARS:
        result = result[:_READ_FILE_MAX_CHARS] + "\n[... truncated ...]"
    return result


def _tool_grep(
    root: Path, pattern: str, path: str = "", include_pattern: str = ""
) -> str:
    if len(pattern) > 500 or re.search(r"\([^)]*[+*][^)]*\)[+*]", pattern):
        return "Error: regex is too complex for safe repository scanning."
    if pattern.count(".*") > 4:
        return "Error: regex contains too many unbounded wildcards."
    try:
        base = _jail(root, path)
    except ValueError as exc:
        return f"Error: {exc}"
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"
    results: list[str] = []
    for dirpath, _dirs, filenames in os.walk(base):
        for fn in sorted(filenames):
            if include_pattern and not fnmatch.fnmatch(fn, include_pattern):
                continue
            fp = Path(dirpath) / fn
            try:
                # Skip binary-looking files.
                if fp.stat().st_size > _MAX_INSPECT_FILE_BYTES:
                    continue
                raw = fp.read_bytes()
                if b"\x00" in raw[:512]:
                    continue
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if rx.search(line):
                    rel = str(fp.relative_to(root))
                    results.append(f"{rel}:{i}: {line.rstrip()}")
                    if len(results) >= _GREP_MAX_RESULTS:
                        results.append("[... truncated at 200 results ...]")
                        return "\n".join(results)
    return "\n".join(results) if results else "(no matches)"


def _count_source_files(root: Path) -> int:
    """Count regular source files without following symlinked directories."""
    count = 0
    for _dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        count += sum(
            1
            for filename in filenames
            if (Path(_dirpath) / filename).is_file()
            and not (Path(_dirpath) / filename).is_symlink()
        )
    return count


_LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C/C++",
    ".cc": "C/C++",
    ".cpp": "C/C++",
    ".h": "C/C++",
    ".rs": "Rust",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sql": "SQL",
    ".html": "HTML",
    ".vue": "Vue",
}


def _build_source_inventory(root: Path) -> dict[str, dict]:
    inventory: dict[str, dict] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            inventory[rel] = {
                "path": rel,
                "size": path.stat().st_size,
                "language": _LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Other"),
                "reviewed": False,
                "read_count": 0,
                "phases": [],
            }
    return inventory


def _mark_reviewed(coverage: dict[str, dict], paths: list[str], phase: str) -> None:
    for raw_path in paths:
        path = raw_path.replace("\\", "/")
        item = coverage.get(path)
        if item is None:
            continue
        item["reviewed"] = True
        item["read_count"] += 1
        if phase not in item["phases"]:
            item["phases"].append(phase)


def _run_read_tool(
    sast_run_id: int,
    root: Path,
    coverage: dict[str, dict],
    phase: str,
    tool_name: str,
    tool_input: dict,
    worker_id: int | None = None,
) -> str | None:
    """Execute one shared read-only file tool and record review receipts."""
    if tool_name == "list_files":
        path = tool_input.get("path", "") or "."
        result = _tool_list_files(
            root,
            path=path if path != "." else "",
            max_depth=int(tool_input.get("max_depth", 3)),
        )
    elif tool_name == "glob":
        path = str(tool_input.get("pattern", ""))
        result = _tool_glob(root, path)
    elif tool_name == "read_file":
        path = str(tool_input.get("path", ""))
        result = _tool_read_file(
            root,
            path=path,
            start_line=tool_input.get("start_line"),
            end_line=tool_input.get("end_line"),
        )
        if not result.startswith("Error:"):
            _mark_reviewed(coverage, [path], phase)
            returned_lines = [
                line for line in result.splitlines() if line != "[... truncated ...]"
            ]
            receipt_start = int(tool_input.get("start_line") or 1)
            receipt_end = (
                receipt_start + len(returned_lines) - 1
                if returned_lines
                else receipt_start
            )
            workprogram_svc.record_evidence_receipt(
                SastEvidenceReceipt(
                    sast_run_id=sast_run_id,
                    worker_id=worker_id,
                    phase=phase,
                    tool_name=tool_name,
                    path=path,
                    start_line=receipt_start,
                    end_line=receipt_end,
                    characters_returned=len(result),
                    truncated="truncated" in result.casefold(),
                )
            )
    elif tool_name == "grep":
        pattern = str(tool_input.get("pattern", ""))
        path = str(tool_input.get("path", ""))
        result = _tool_grep(
            root,
            pattern=pattern,
            path=path,
            include_pattern=str(tool_input.get("include_pattern", "")),
        )
        include_pattern = str(tool_input.get("include_pattern", ""))
        try:
            base = _jail(root, path)
            inspected_paths = [
                file.relative_to(root).as_posix()
                for file in base.rglob("*")
                if file.is_file()
                and file.stat().st_size <= _MAX_INSPECT_FILE_BYTES
                and (not include_pattern or fnmatch.fnmatch(file.name, include_pattern))
            ]
        except (OSError, ValueError):
            inspected_paths = []
        matched_paths = sorted(
            {
                line.split(":", 1)[0]
                for line in result.splitlines()
                if re.match(r"^.+:\d+:", line)
            }
        )
        workprogram_svc.record_evidence_receipt(
            SastEvidenceReceipt(
                sast_run_id=sast_run_id,
                worker_id=worker_id,
                phase=phase,
                tool_name=tool_name,
                path=path,
                search_pattern=pattern,
                include_pattern=include_pattern,
                files_in_scope=len(inspected_paths),
                files_with_matches=len(matched_paths),
                matches_returned=sum(
                    bool(re.match(r"^.+:\d+:", line)) for line in result.splitlines()
                ),
                characters_returned=len(result),
                truncated="truncated" in result.casefold(),
                details_json=json.dumps({"matched_paths": matched_paths}),
            )
        )
    else:
        return None
    events_svc.emit(
        sast_run_id,
        {
            "type": "scanner_phase",
            "phase": phase,
            "status": "running",
            "message": f"{tool_name}: {path}",
        },
    )
    return result


# ── Tool executor factory ─────────────────────────────────────────────────────


def _make_tool_executor(
    sast_run_id: int,
    root: Path,
    collection_id: int | None,
    coverage: dict[str, dict] | None = None,
    on_candidate_ready: Callable[[dict], None] | None = None,
    initial_candidates: list[dict] | None = None,
    assigned_worker_id: int | None = None,
):
    """Return an async tool_executor closure for the SAST agentic loop.

    Handles: list_files / glob / read_file / grep / write_lead / filter_lead / done.
    Candidates are stored in _candidates[sast_run_id]; filter_lead records the
    discovery agent's confidence before independent validation.
    """
    if initial_candidates is not None or sast_run_id not in _candidates:
        _candidates[sast_run_id] = list(initial_candidates or [])
    coverage = coverage if coverage is not None else _build_source_inventory(root)
    assigned_items = (
        {
            int(item["work_item_id"])
            for item in workprogram_svc.worker_payload(assigned_worker_id).get(
                "work_items", []
            )
        }
        if assigned_worker_id is not None
        else set()
    )

    async def tool_executor(tool_name: str, tool_input: dict, step: int) -> str:
        if sast_run_id in _sast_stop_requested:
            return "Scan stopped by user."

        read_result = _run_read_tool(
            sast_run_id,
            root,
            coverage,
            "discovery",
            tool_name,
            tool_input,
            assigned_worker_id,
        )
        if read_result is not None:
            return read_result

        if tool_name == "get_work_program":
            if assigned_worker_id is None:
                return "Error: this agent has no assigned work program."
            return json.dumps(
                workprogram_svc.worker_payload(assigned_worker_id),
                ensure_ascii=False,
            )

        if tool_name == "record_disposition":
            work_item_id = int(tool_input.get("work_item_id", -1))
            if work_item_id not in assigned_items:
                return (
                    f"Error: work item {work_item_id} is not assigned to this worker."
                )
            ok, message = workprogram_svc.record_disposition(
                work_item_id,
                status=str(tool_input.get("status", "")),
                reasoning=str(tool_input.get("reasoning", "")),
                trace=_normalize_tool_list(tool_input.get("trace")),
                controls=_normalize_tool_list(tool_input.get("controls")),
                evidence=_normalize_tool_list(tool_input.get("evidence")),
            )
            return message if ok else f"Error: {message}"

        if tool_name == "write_lead":
            work_item_id = int(tool_input.get("work_item_id", -1))
            if assigned_worker_id is not None and work_item_id not in assigned_items:
                return (
                    "Error: write_lead requires a work_item_id assigned to this worker."
                )
            if assigned_worker_id is not None:
                disposition_ok, disposition_message = (
                    workprogram_svc.record_disposition(
                        work_item_id,
                        status="candidate",
                        reasoning=str(
                            tool_input.get("description", "Candidate recorded.")
                        ),
                        trace=[tool_input.get("source_trace") or {}],
                        controls=_normalize_tool_list(tool_input.get("controls")),
                        evidence=[str(tool_input.get("evidence", ""))],
                        candidate_from_lead=True,
                    )
                )
                if not disposition_ok:
                    return f"Error: {disposition_message}"
            title = str(tool_input.get("title", ""))
            category = str(tool_input.get("category", ""))
            location = str(tool_input.get("location", ""))
            fingerprint = lead_fingerprint(
                category=category,
                title=title,
                location=location,
            )
            existing = next(
                (
                    item
                    for item in _candidates[sast_run_id]
                    if item.get("fingerprint") == fingerprint
                    or (
                        item.get("title") == title
                        and item.get("category") == category
                        and item.get("location") == location
                    )
                ),
                None,
            )
            if existing is not None:
                if work_item_id >= 0 and existing.get("lead_id"):
                    workprogram_svc.attach_lead(work_item_id, int(existing["lead_id"]))
                reference = existing.get("reference") or f"#{existing['candidate_id']}"
                return (
                    f"Lead {reference} was already recorded. Reuse it instead of "
                    "creating a duplicate."
                )
            cid = (
                max(
                    (
                        int(item.get("candidate_id", -1))
                        for item in _candidates[sast_run_id]
                    ),
                    default=-1,
                )
                + 1
            )
            candidate = {
                "candidate_id": cid,
                "source_work_item_id": work_item_id if work_item_id >= 0 else None,
                "fingerprint": fingerprint,
                "title": title,
                "category": category,
                "severity": str(tool_input.get("severity", "medium")),
                "location": location,
                "description": str(tool_input.get("description", "")),
                "evidence": str(tool_input.get("evidence", "")),
                "suggested_endpoint": str(tool_input.get("suggested_endpoint", "")),
                "source_trace": tool_input.get("source_trace") or {},
                "controls": tool_input.get("controls") or [],
                "sink_trace": tool_input.get("sink_trace") or {},
                "proof_gaps": tool_input.get("proof_gaps") or [],
                "confidence": None,  # set by filter_lead
                "validation_status": "pending",
                "validation_reasoning": "",
                "counterevidence": [],
                "attack_path": {},
                "reportable": False,
            }
            _candidates[sast_run_id].append(candidate)
            # The Candidates view reads from the database while discovery state
            # lives in memory.  Persist immediately so the UI does not remain
            # empty until the later validation phase completes.
            _sync_candidates_to_db(sast_run_id, collection_id)
            _persist_candidate_state(sast_run_id)
            events_svc.emit(
                sast_run_id,
                {
                    "type": "scanner_phase",
                    "phase": "sast_candidate",
                    "status": "running",
                    "message": f"Candidate: {candidate['title']}",
                },
            )
            reference = candidate.get("reference") or f"#{cid}"
            return f"Lead {reference} recorded. Now call filter_lead with lead_reference={reference}."

        if tool_name == "filter_lead":
            lead_reference = str(tool_input.get("lead_reference") or "").strip()
            try:
                cid = int(tool_input.get("lead_id", -1))
            except (TypeError, ValueError):
                cid = -1
            confidence = float(tool_input.get("confidence", 0.0))
            reasoning = str(tool_input.get("reasoning", ""))
            candidates = _candidates.get(sast_run_id, [])
            match = next(
                (
                    c
                    for c in candidates
                    if (lead_reference and c.get("reference") == lead_reference)
                    or (not lead_reference and c["candidate_id"] == cid)
                ),
                None,
            )
            if match is None:
                return f"Error: no lead {lead_reference or f'#{cid}'} found."
            match["confidence"] = confidence
            match["filter_reasoning"] = reasoning
            _sync_candidates_to_db(sast_run_id, collection_id)
            _persist_candidate_state(sast_run_id)
            kept = confidence >= CONFIDENCE_THRESHOLD
            events_svc.emit(
                sast_run_id,
                {
                    "type": "scanner_phase",
                    "phase": "sast_filter",
                    "status": "running",
                    "message": (
                        f"Discovery {'SUPPORTED' if kept else 'LOW CONFIDENCE'} lead "
                        f"{match.get('reference') or f'#{cid}'}: "
                        f"{match['title']} (confidence={confidence:.0%})"
                    ),
                },
            )
            if on_candidate_ready is not None:
                on_candidate_ready(match)
            outcome = (
                "SUPPORTED for independent validation"
                if kept
                else "flagged as low-confidence for the validator"
            )
            return f"Lead {match.get('reference') or f'#{cid}'}: confidence={confidence:.0%} — {outcome}."

        if tool_name == "done":
            # Persisted by the caller — just return the summary.
            return str(tool_input.get("summary", ""))

        return f"Unknown tool: {tool_name!r}"

    return tool_executor


def _candidate_for_id(sast_run_id: int, candidate_id: int) -> dict | None:
    return next(
        (
            candidate
            for candidate in _candidates.get(sast_run_id, [])
            if candidate["candidate_id"] == candidate_id
        ),
        None,
    )


def _make_review_executor(
    sast_run_id: int,
    root: Path,
    coverage: dict[str, dict],
    phase: str,
    collection_id: int | None = None,
    assigned_candidate_id: int | None = None,
):
    async def tool_executor(tool_name: str, tool_input: dict, step: int) -> str:
        if sast_run_id in _sast_stop_requested:
            return "Scan stopped by user."
        read_result = _run_read_tool(
            sast_run_id, root, coverage, phase, tool_name, tool_input
        )
        if read_result is not None:
            return read_result
        candidate_id = int(tool_input.get("candidate_id", -1))
        candidate = _candidate_for_id(sast_run_id, candidate_id)
        if (
            assigned_candidate_id is not None
            and tool_name
            in {"get_candidate", "validate_candidate", "record_attack_path"}
            and candidate_id != assigned_candidate_id
        ):
            assigned = _candidate_for_id(sast_run_id, assigned_candidate_id)
            assigned_reference = assigned.get("reference") if assigned else None
            candidate_reference = candidate.get("reference") if candidate else None
            return (
                f"Error: this validator is assigned to lead "
                f"{assigned_reference or f'#{assigned_candidate_id}'}, "
                f"not lead {candidate_reference or f'#{candidate_id}'}."
            )
        if tool_name == "get_candidate":
            if candidate is None:
                return f"Error: no lead {candidate.get('reference') if candidate else f'#{candidate_id}'} found."
            return json.dumps(candidate, ensure_ascii=False)
        if candidate is None and tool_name in {
            "validate_candidate",
            "record_attack_path",
        }:
            return f"Error: no lead {candidate.get('reference') if candidate else f'#{candidate_id}'} found."
        if tool_name == "validate_candidate":
            verdict = str(tool_input.get("verdict", "inconclusive"))
            confidence = min(1.0, max(0.0, float(tool_input.get("confidence", 0))))
            candidate.update(
                {
                    "validation_status": verdict,
                    "validation_reasoning": str(tool_input.get("reasoning", "")),
                    "confidence": confidence,
                    "controls": _normalize_tool_list(tool_input.get("controls")),
                    "counterevidence": _normalize_tool_list(
                        tool_input.get("counterevidence")
                    ),
                    "proof_gaps": _normalize_tool_list(tool_input.get("proof_gaps")),
                    "reportable": verdict == "confirmed"
                    and confidence >= CONFIDENCE_THRESHOLD,
                }
            )
            # A verdict completes the validator's research for this candidate.
            # Persist and announce it now instead of waiting for the validator's
            # entire agentic loop to finish so the UI can show progressive results.
            _sync_candidate_to_db(sast_run_id, collection_id, candidate)
            _persist_candidate_state(sast_run_id)
            _persist_coverage(sast_run_id, coverage)
            _emit_validation_result(sast_run_id, candidate)
            return f"Lead {candidate.get('reference') or f'#{candidate_id}'} validation recorded as {verdict}."
        if tool_name == "record_attack_path":
            if not candidate.get("reportable"):
                return f"Error: lead {candidate.get('reference') or f'#{candidate_id}'} is not reportable."
            candidate["attack_path"] = {
                "nodes": _normalize_tool_list(tool_input.get("nodes")),
                "impact": str(tool_input.get("impact", "")),
                "severity_reasoning": str(tool_input.get("severity_reasoning", "")),
                "dynamic_test": str(tool_input.get("dynamic_test", "")),
            }
            _sync_candidate_to_db(sast_run_id, collection_id, candidate)
            _persist_candidate_state(sast_run_id)
            return f"Lead {candidate.get('reference') or f'#{candidate_id}'} attack path recorded."
        if tool_name == "done":
            return str(tool_input.get("summary", ""))
        return f"Unknown tool: {tool_name!r}"

    return tool_executor


def _normalize_tool_list(value: object) -> list:
    """Keep malformed string-valued tool arrays from splitting into characters."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
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


def _sync_candidates_to_db(
    sast_run_id: int, collection_id: int | None
) -> tuple[int, int]:
    """Upsert every candidate and return (candidate_count, reportable_count)."""
    candidates = _candidates.get(sast_run_id, [])
    for candidate in candidates:
        _sync_candidate_to_db(sast_run_id, collection_id, candidate)
    return len(candidates), sum(bool(c.get("reportable")) for c in candidates)


def _sync_candidate_to_db(
    sast_run_id: int, collection_id: int | None, candidate: dict
) -> None:
    """Upsert one candidate so completed review work is visible immediately."""
    title = str(candidate.get("title", ""))
    category = str(candidate.get("category", ""))
    location = str(candidate.get("location", ""))
    lead = create_lead(
        producer_run_id=sast_run_id,
        producer_run_type="sast",
        collection_id=collection_id,
        title=title,
        description=str(candidate.get("description", "")),
        category=category,
        severity=candidate.get("severity", "medium"),
        confidence=float(candidate.get("confidence") or 0.0),
        location=location,
        evidence=candidate.get("evidence", ""),
        source="sast",
        fingerprint=lead_fingerprint(
            category=category,
            title=title,
            location=location,
        ),
        suggested_endpoint=candidate.get("suggested_endpoint", ""),
        source_trace=candidate.get("source_trace") or {},
        controls=candidate.get("controls") or [],
        sink_trace=candidate.get("sink_trace") or {},
        counterevidence=candidate.get("counterevidence") or [],
        proof_gaps=candidate.get("proof_gaps") or [],
        validation_status=candidate.get("validation_status", "inconclusive"),
        validation_reasoning=candidate.get("validation_reasoning", ""),
        attack_path=candidate.get("attack_path") or {},
        reportable=bool(candidate.get("reportable")),
    )
    candidate["reference"] = lead.reference
    candidate["lead_id"] = lead.id
    source_work_item_id = candidate.get("source_work_item_id")
    if lead.id is not None and source_work_item_id:
        with Session(get_engine()) as session:
            persisted_lead = session.get(ScanLead, lead.id)
            if persisted_lead is not None:
                persisted_lead.source_work_item_id = int(source_work_item_id)
                session.add(persisted_lead)
                session.commit()
        workprogram_svc.attach_lead(int(source_work_item_id), lead.id)


# ── SAST scan task ─────────────────────────────────────────────────────────────


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
        "then Phase 3 (write_lead + filter_lead for each candidate). "
        "Call done when finished."
    )
    return "\n".join(lines)


async def _sast_scan_task(sast_run_id: int, *, resume: bool = False) -> None:
    """Core async task: extract archive, run agentic loop, persist leads."""
    from aespa.services import llm as llm_svc
    from aespa.services.prompts.sast import (
        SAST_ATTACK_PATH_PROMPT,
        SAST_ATTACK_PATH_TOOLS,
        SAST_TOOLS,
        SAST_VALIDATION_PROMPT,
        SAST_VALIDATION_TOOLS,
        sast_worker_prompt,
    )
    from aespa.services.settings import get_llm_config_for_role

    _sast_stop_requested.discard(sast_run_id)
    _sast_pause_requested.discard(sast_run_id)
    tmpdir: str | None = None
    lease = _sast_workspace_leases.get(sast_run_id)
    if lease is None:
        lease = try_acquire_sast_workspace_lease(
            Path(get_settings().data_dir), sast_run_id
        )
        if lease is None:
            raise RuntimeError(
                f"SAST workspace for run {sast_run_id} is active in another process."
            )
        _sast_workspace_leases[sast_run_id] = lease
    run: SastRun | None = None  # populated early; used in except blocks
    validation_tasks: list[asyncio.Task] = []
    current_phase = "scope"
    try:
        # ── Load run, collection, document ────────────────────────────────────
        with Session(get_engine(), expire_on_commit=False) as s:
            run = s.get(SastRun, sast_run_id)
            if run is None:
                raise ValueError(f"SastRun {sast_run_id} not found")
            # New SAST runs are standalone. Collection/document linkage remains
            # readable for legacy and imported rows.
            coll = (
                s.get(ApiCollection, run.collection_id) if run.collection_id else None
            )
            # Resolve the source archive. Legacy rows may still use ApiDocument;
            # new standalone runs store the archive path on the run itself.
            doc: ApiDocument | None = None
            if run.document_id:
                doc = s.get(ApiDocument, run.document_id)
            elif run.collection_id:
                # Find the most recent source_zip for this collection.
                doc = s.exec(
                    select(ApiDocument)
                    .where(ApiDocument.collection_id == run.collection_id)
                    .where(ApiDocument.doc_type == "source_zip")
                    .order_by(ApiDocument.id.desc())  # type: ignore[attr-defined]
                ).first()
            if doc is not None:
                archive_path = doc.stored_path
                archive_name = doc.filename
            else:
                archive_path = run.source_archive_path
                archive_name = run.source_filename or "source.zip"
            if not archive_path:
                raise ValueError("No source archive found for this SAST run.")
            llm_cfg_obj = get_llm_config_for_role(s, run, "sast")  # type: ignore[arg-type]
            if llm_cfg_obj is None:
                raise RuntimeError(
                    "No LLM configuration. Configure it in Settings first."
                )
            validator_cfg_obj = (
                get_llm_config_for_role(  # type: ignore[arg-type]
                    s, run, "validator"
                )
                or llm_cfg_obj
            )
            endpoints = (
                list(
                    s.exec(
                        select(ApiEndpoint)
                        .where(ApiEndpoint.collection_id == run.collection_id)
                        .where(ApiEndpoint.in_scope == True)  # noqa: E712
                        .order_by(ApiEndpoint.path, ApiEndpoint.method)
                    ).all()
                )
                if run.collection_id
                else []
            )
            detached: set[int] = set()
            for obj in [run, coll, doc, llm_cfg_obj, validator_cfg_obj]:
                if obj is not None and id(obj) not in detached:
                    s.expunge(obj)
                    detached.add(id(obj))

        # ── Extract archive ────────────────────────────────────────────────────
        # Use a deterministic path under <data_dir>/sast_extract/<id>/ so a
        # startup sweep can reconcile any dirs leaked by a crashed scan
        # (see db._cleanup_orphaned_sast_extractions). A prior interrupted run
        # for the same id may have left files behind — wipe them so we don't
        # mix old artefacts into the new scan.
        extract_root = Path(get_settings().data_dir) / "sast_extract"
        extract_root.mkdir(parents=True, exist_ok=True)
        tmpdir = str(extract_root / str(sast_run_id))
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.makedirs(tmpdir, exist_ok=True)
        _set_phase(
            sast_run_id,
            "scope",
            "running",
            f"Extracting and inventorying source archive: {archive_name}",
        )
        _safe_unzip(archive_path, tmpdir)
        root = Path(tmpdir).resolve()
        coverage = _build_source_inventory(root)
        if resume:
            coverage = _merge_persisted_coverage(coverage, run.coverage_json)
        source_file_count = len(coverage)
        work_program_built = (
            not resume or workprogram_svc.count_rows(sast_run_id, SastWorker) == 0
        )
        if work_program_built:
            atlas_summary = workprogram_svc.build_source_atlas(sast_run_id, root)
        else:
            atlas_summary = workprogram_svc.work_program_summary(sast_run_id)
        _persist_coverage(sast_run_id, coverage)
        _set_phase(
            sast_run_id,
            "scope",
            "complete",
            f"Source scope ready: {source_file_count} regular file(s) inventoried.",
            {
                "files_total": source_file_count,
                "production_files": atlas_summary["files"]["production"],
                "surface": atlas_summary["surface"],
                "work_items": atlas_summary["work_items"]["total"],
            },
        )

        initial_message = _build_initial_message(coll, endpoints, archive_name)

        # ── Configure LLM context tracking ────────────────────────────────────
        llm_svc.set_run_context(
            sast_run_id,
            lambda evt: events_svc.emit(sast_run_id, evt),
            run_kind="sast",
        )

        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "active",
                "current_task": "Starting static analysis…",
                "outcome": None,
                "_persist": True,
            },
        )

        def _stop_check() -> bool:
            return (
                sast_run_id in _sast_stop_requested
                or sast_run_id in _sast_pause_requested
            )

        def _raise_if_stopped() -> None:
            if sast_run_id in _sast_pause_requested:
                raise SastPauseRequested("SAST scan paused by user.")
            if _stop_check():
                raise asyncio.CancelledError

        validation_semaphore = asyncio.Semaphore(_SAST_VALIDATOR_MAX_CONCURRENT)
        validation_scheduled: set[int] = set()
        validation_failures: list[int] = []
        validation_started = False

        async def _validate_candidate(candidate_id: int) -> None:
            async with validation_semaphore:
                candidate = _candidate_for_id(sast_run_id, candidate_id)
                if candidate is None:
                    return
                try:
                    await _run_checkpointed_agent(
                        sast_run_id=sast_run_id,
                        phase="validation",
                        worker_key=f"validator:{candidate_id}",
                        config=validator_cfg_obj,
                        system_message=SAST_VALIDATION_PROMPT,
                        initial_user_message=_candidate_validation_message(candidate),
                        tool_executor=_make_review_executor(
                            sast_run_id,
                            root,
                            coverage,
                            "validation",
                            collection_id=run.collection_id,
                            assigned_candidate_id=candidate_id,
                        ),
                        emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
                        stop_check=_stop_check,
                        tools=SAST_VALIDATION_TOOLS,
                        resume=resume,
                    )
                    _raise_if_stopped()
                except asyncio.CancelledError:
                    raise
                except llm_svc.LLMQuotaPauseError:
                    raise
                except (SastPauseRequested, SastNetworkPause):
                    raise
                except Exception as exc:
                    log.exception(
                        "SAST validator failed: sast_run_id=%s candidate_id=%s",
                        sast_run_id,
                        candidate_id,
                    )
                    candidate = _candidate_for_id(sast_run_id, candidate_id)
                    if candidate is not None:
                        if candidate.get("validation_status") == "pending":
                            candidate.update(
                                {
                                    "validation_status": "inconclusive",
                                    "validation_reasoning": f"Validator failed: {exc}",
                                    "proof_gaps": [
                                        *candidate.get("proof_gaps", []),
                                        "Independent validator failed before closing this candidate.",
                                    ],
                                    "reportable": False,
                                }
                            )
                            _sync_candidate_to_db(
                                sast_run_id, run.collection_id, candidate
                            )
                            _persist_coverage(sast_run_id, coverage)
                            _emit_validation_result(
                                sast_run_id, candidate, error=str(exc)
                            )
                            validation_failures.append(candidate_id)
                    return

                candidate = _candidate_for_id(sast_run_id, candidate_id)
                if candidate is None:
                    return
                if candidate.get("validation_status") == "pending":
                    candidate.update(
                        {
                            "validation_status": "inconclusive",
                            "validation_reasoning": "Validator returned no explicit verdict.",
                            "proof_gaps": [
                                *candidate.get("proof_gaps", []),
                                "Independent validator did not close this candidate.",
                            ],
                            "reportable": False,
                        }
                    )
                    _sync_candidate_to_db(sast_run_id, run.collection_id, candidate)
                    _persist_coverage(sast_run_id, coverage)
                    _emit_validation_result(sast_run_id, candidate)

        def _schedule_candidate_validation(candidate: dict) -> None:
            nonlocal validation_started
            candidate_id = int(candidate["candidate_id"])
            if candidate_id in validation_scheduled:
                return
            validation_scheduled.add(candidate_id)
            if not validation_started:
                validation_started = True
                _set_phase(
                    sast_run_id,
                    "validation",
                    "running",
                    "Validating candidates as discovery completes.",
                    {"candidates": 1, "completed": 0},
                )
                events_svc.emit(
                    sast_run_id,
                    {
                        "type": "agent_status",
                        "agent_id": "sast-validator",
                        "role": "SAST Validator",
                        "status": "active",
                        "current_task": "Validating candidates as they arrive",
                        "outcome": None,
                        "_persist": True,
                    },
                )
            validation_tasks.append(
                asyncio.create_task(
                    _validate_candidate(candidate_id),
                    name=f"sast-validator-{sast_run_id}-{candidate_id}",
                )
            )

        _candidates[sast_run_id] = (
            _restore_candidate_state(sast_run_id) if resume else []
        )

        try:
            saved_phases = json.loads(run.phase_state_json or "{}") if resume else {}
        except (TypeError, ValueError):
            saved_phases = {}

        def _phase_was_complete(phase: str) -> bool:
            entry = saved_phases.get(phase, {})
            return (
                isinstance(entry, dict)
                and entry.get("status") == "complete"
                and not (phase == "discovery" and work_program_built)
            )

        current_phase = "discovery"
        discovery_summary = "Discovery was already complete before resume."
        if not _phase_was_complete("discovery"):
            _set_phase(
                sast_run_id,
                "discovery",
                "running",
                "Tracing entry points and source-to-sink candidate paths.",
                {"files_total": source_file_count},
            )

            worker_semaphore = asyncio.Semaphore(4)

            async def _run_discovery_worker(worker: SastWorker) -> str:
                if worker.id is None:
                    return "Worker has no persisted id."
                if resume and worker.status == "complete":
                    return worker.summary or f"{worker.worker_key} already complete."
                async with worker_semaphore:
                    workprogram_svc.set_worker_status(worker.id, "running")
                    payload = workprogram_svc.worker_payload(worker.id)

                    def _worker_done(_tool_input: dict, _calls: int):
                        unresolved = workprogram_svc.unresolved_for_worker(worker.id)
                        if unresolved:
                            return (
                                False,
                                "Resolve these assigned work items before done: "
                                + ", ".join(str(item) for item in unresolved[:50]),
                            )
                        return True, ""

                    try:
                        summary = await _run_checkpointed_agent(
                            sast_run_id=sast_run_id,
                            phase="discovery",
                            worker_key=worker.worker_key,
                            config=llm_cfg_obj,
                            system_message=sast_worker_prompt(worker.class_group),
                            initial_user_message=(
                                initial_message
                                + "\n\nAssigned work program:\n"
                                + json.dumps(payload, ensure_ascii=False)
                            ),
                            tool_executor=_make_tool_executor(
                                sast_run_id,
                                root,
                                run.collection_id,
                                coverage,
                                on_candidate_ready=_schedule_candidate_validation,
                                assigned_worker_id=worker.id,
                            ),
                            emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
                            stop_check=_stop_check,
                            tools=SAST_TOOLS,
                            resume=resume,
                            done_check=_worker_done,
                        )
                    except (
                        asyncio.CancelledError,
                        llm_svc.LLMQuotaPauseError,
                        SastPauseRequested,
                        SastNetworkPause,
                    ):
                        raise
                    except Exception as exc:
                        workprogram_svc.set_worker_status(
                            worker.id, "failed", error=str(exc)
                        )
                        log.exception(
                            "SAST discovery worker failed: run=%s worker=%s",
                            sast_run_id,
                            worker.worker_key,
                        )
                        return f"{worker.worker_key} failed: {exc}"
                    unresolved = workprogram_svc.unresolved_for_worker(worker.id)
                    workprogram_svc.set_worker_status(
                        worker.id,
                        "complete" if not unresolved else "blocked",
                        summary=summary,
                        error=(
                            f"{len(unresolved)} assigned item(s) unresolved."
                            if unresolved
                            else ""
                        ),
                    )
                    return summary

            worker_summaries = await asyncio.gather(
                *(
                    _run_discovery_worker(worker)
                    for worker in workprogram_svc.worker_rows(sast_run_id)
                )
            )
            discovery_summary = "\n".join(worker_summaries)
            _raise_if_stopped()

        candidates = _candidates.get(sast_run_id, [])
        candidate_count = len(candidates)
        _persist_coverage(sast_run_id, coverage)
        completion_status, completion_reasons, work_program_summary = (
            workprogram_svc.completion_decision(sast_run_id)
        )
        if not _phase_was_complete("discovery"):
            _set_phase(
                sast_run_id,
                "discovery",
                "complete",
                (
                    f"Discovery recorded {candidate_count} candidate(s) with "
                    f"{completion_status} work-program coverage."
                ),
                {
                    "files_total": source_file_count,
                    "candidates": candidate_count,
                    "completion_status": completion_status,
                    "completion_reasons": completion_reasons,
                    "work_program": work_program_summary,
                },
            )

        # ── Complete independent adversarial validation ───────────────────────
        current_phase = "validation"
        if not root.is_dir():
            raise RuntimeError(
                "SAST source workspace disappeared before independent validation."
            )
        if not _phase_was_complete("validation"):
            for candidate in candidates:
                if (
                    candidate.get("validation_status") == "pending"
                    and candidate.get("confidence") is not None
                ):
                    _schedule_candidate_validation(candidate)

            if validation_tasks:
                await asyncio.gather(*validation_tasks)
                _raise_if_stopped()
                validated_count = sum(c.get("reportable", False) for c in candidates)
                validation_summary = (
                    f"Independent validation retained {validated_count} of "
                    f"{candidate_count} candidate(s)."
                )
                if validation_failures:
                    validation_summary += (
                        f" {len(validation_failures)} validator task(s) failed "
                        "and were marked inconclusive."
                    )
            else:
                validated_count = sum(c.get("reportable", False) for c in candidates)
                validation_summary = "No candidates required validation."

            _sync_candidates_to_db(sast_run_id, run.collection_id)
            _persist_candidate_state(sast_run_id)
            _persist_coverage(sast_run_id, coverage)
            _set_phase(
                sast_run_id,
                "validation",
                "complete",
                f"Independent validation retained {validated_count} of {candidate_count} candidate(s).",
                {
                    "candidates": candidate_count,
                    "reportable": validated_count,
                    "validator_tasks": len(validation_tasks),
                    "validator_failures": len(validation_failures),
                },
            )
        else:
            validated_count = sum(c.get("reportable", False) for c in candidates)
            validation_summary = (
                "Independent validation was already complete before resume."
            )
        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-validator",
                "role": "SAST Validator",
                "status": "complete",
                "current_task": "Validation complete",
                "outcome": f"{validated_count} reportable candidate(s)",
                "_persist": True,
            },
        )

        # ── Independent reachability / attack-path analysis ──────────────────
        current_phase = "attack_path"
        attack_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("reportable") and not candidate.get("attack_path")
        ]
        attack_summary = "Attack-path analysis was already complete before resume."
        if not _phase_was_complete("attack_path"):
            _set_phase(
                sast_run_id,
                "attack_path",
                "running",
                f"Tracing reachability for {len(attack_candidates)} validated candidate(s).",
                {"candidates": len(attack_candidates)},
            )
            attack_summary = "No validated candidates required attack-path analysis."
        if (
            not _phase_was_complete("attack_path")
            and attack_candidates
            and not _stop_check()
        ):
            events_svc.emit(
                sast_run_id,
                {
                    "type": "agent_status",
                    "agent_id": "sast-attack-path",
                    "role": "Attack Path Analyst",
                    "status": "active",
                    "current_task": "Tracing external reachability and impact",
                    "outcome": None,
                    "_persist": True,
                },
            )
            attack_summary = await _run_checkpointed_agent(
                sast_run_id=sast_run_id,
                phase="attack_path",
                worker_key="attack_path",
                config=llm_cfg_obj,
                system_message=SAST_ATTACK_PATH_PROMPT,
                initial_user_message=(
                    "Record an attack path for every validated candidate:\n"
                    + _candidate_brief(attack_candidates)
                ),
                tool_executor=_make_review_executor(
                    sast_run_id,
                    root,
                    coverage,
                    "attack_path",
                    collection_id=run.collection_id,
                ),
                emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
                stop_check=_stop_check,
                tools=SAST_ATTACK_PATH_TOOLS,
                resume=resume,
            )
            _raise_if_stopped()
        if not _phase_was_complete("attack_path"):
            for candidate in candidates:
                if candidate.get("reportable") and not candidate.get("attack_path"):
                    candidate["attack_path"] = {
                        "nodes": [],
                        "impact": "",
                        "severity_reasoning": "",
                        "dynamic_test": candidate.get("suggested_endpoint", ""),
                        "proof_gap": "Attack-path analyst returned no ordered path.",
                    }
        _, leads_count = _sync_candidates_to_db(sast_run_id, run.collection_id)
        _persist_candidate_state(sast_run_id)
        _persist_coverage(sast_run_id, coverage)
        if not _phase_was_complete("attack_path"):
            _set_phase(
                sast_run_id,
                "attack_path",
                "complete",
                f"Attack-path analysis completed for {leads_count} reportable lead(s).",
                {"reportable": leads_count, "dynamic_confirmation_required": True},
            )
        if validated_count:
            events_svc.emit(
                sast_run_id,
                {
                    "type": "agent_status",
                    "agent_id": "sast-attack-path",
                    "role": "Attack Path Analyst",
                    "status": "complete",
                    "current_task": "Attack-path analysis complete",
                    "outcome": f"{leads_count} path(s) recorded",
                    "_persist": True,
                },
            )

        # ── Report ────────────────────────────────────────────────────────────
        current_phase = "report"
        if not _phase_was_complete("report"):
            _set_phase(
                sast_run_id,
                "report",
                "running",
                "Building the final candidate and coverage report.",
            )
        report = {
            "candidates": candidate_count,
            "reportable": leads_count,
            "dismissed": sum(
                c.get("validation_status") == "dismissed" for c in candidates
            ),
            "inconclusive": sum(
                c.get("validation_status") == "inconclusive" for c in candidates
            ),
            "discovery_summary": discovery_summary,
            "validation_summary": validation_summary,
            "attack_path_summary": attack_summary,
            "completion_status": completion_status,
            "completion_reasons": completion_reasons,
            "work_program": work_program_summary,
        }
        if not _phase_was_complete("report"):
            with Session(get_engine()) as s:
                persisted_run = s.get(SastRun, sast_run_id)
                if persisted_run is not None:
                    persisted_run.report_json = json.dumps(report, ensure_ascii=False)
                    s.add(persisted_run)
                    s.commit()
            _set_phase(
                sast_run_id,
                "report",
                "complete",
                (
                    f"SAST report complete with {completion_status} coverage: "
                    f"{leads_count} reportable lead(s) from {candidate_count} candidate(s)."
                ),
                report,
            )
        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "complete",
                "current_task": "Analysis complete",
                "outcome": (
                    f"{leads_count} lead(s) recorded, {completion_status} coverage"
                ),
                "_persist": True,
            },
        )

        with Session(get_engine()) as s:
            r = s.get(SastRun, sast_run_id)
            if r is not None and r.status == "scanning":
                r.status = "completed"
                r.completion_status = completion_status
                r.leads_count = leads_count
                r.completed_at = datetime.now(_UTC)
                r.updated_at = datetime.now(_UTC)
                s.add(r)
                s.commit()

        _notify_campaign_source_finished(sast_run_id, "completed")

        # Deterministic, bounded interface-fact extraction (routes, outbound
        # calls, auth boundaries, queues, datastores, framework markers).
        # Runs for every SAST run — component_id stays NULL unless this run
        # belongs to a campaign, so standalone SAST behavior is unchanged.
        if root is not None:
            from aespa.services.component_facts import persist_component_facts

            persist_component_facts(sast_run_id, root)

    except (SastPauseRequested, SastNetworkPause) as exc:
        reason = "network" if isinstance(exc, SastNetworkPause) else "user"
        log.info(
            "SAST scan paused: sast_run_id=%s reason=%s: %s",
            sast_run_id,
            reason,
            exc,
        )
        _persist_candidate_state(sast_run_id)
        _persist_paused_run(
            sast_run_id,
            phase=current_phase,
            reason=reason,
            message=str(exc),
        )
        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "paused",
                "current_task": "Scan paused",
                "outcome": reason,
                "_persist": True,
            },
        )
    except asyncio.CancelledError:
        log.info("SAST scan cancelled: sast_run_id=%s", sast_run_id)
        total = 0
        if run is not None:
            for candidate in _candidates.get(sast_run_id, []):
                if candidate.get("validation_status") == "pending":
                    candidate["validation_status"] = "inconclusive"
                    candidate["validation_reasoning"] = (
                        "Scan stopped before validation completed."
                    )
                    candidate["reportable"] = False
            _, total = _sync_candidates_to_db(sast_run_id, run.collection_id)
            with Session(get_engine()) as s:
                r = s.get(SastRun, sast_run_id)
                if r is not None:
                    r.leads_count = total
                    s.add(r)
                    s.commit()
        _update_sast_run_status(sast_run_id, "cancelled")
        _notify_campaign_source_finished(sast_run_id, "cancelled")
        _set_phase(
            sast_run_id,
            current_phase,
            "cancelled",
            f"SAST scan stopped. {total} reportable lead(s) preserved.",
        )
        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "stopped",
                "current_task": "Scan stopped",
                "outcome": "cancelled",
                "_persist": True,
            },
        )
    except llm_svc.LLMQuotaPauseError as exc:
        log.warning("SAST scan paused: sast_run_id=%s: %s", sast_run_id, exc)
        _persist_candidate_state(sast_run_id)
        _persist_paused_run(
            sast_run_id,
            phase=current_phase,
            reason="quota",
            provider=str(getattr(llm_cfg_obj, "provider", "")),
            message=str(exc),
            reset_at=exc.reset_at,
            snapshot=exc.snapshot,
        )
    except Exception as exc:
        log.exception("SAST scan error: sast_run_id=%s", sast_run_id)
        if run is not None:
            try:
                for candidate in _candidates.get(sast_run_id, []):
                    if candidate.get("validation_status") == "pending":
                        candidate["validation_status"] = "inconclusive"
                        candidate["validation_reasoning"] = (
                            "Scan failed before validation completed."
                        )
                        candidate["reportable"] = False
                _, total = _sync_candidates_to_db(sast_run_id, run.collection_id)
                with Session(get_engine()) as s:
                    r = s.get(SastRun, sast_run_id)
                    if r is not None:
                        r.leads_count = total
                        s.add(r)
                        s.commit()
            except Exception:
                pass
        _update_sast_run_status(sast_run_id, "failed", str(exc))
        _notify_campaign_source_finished(sast_run_id, "failed")
        _set_phase(
            sast_run_id,
            current_phase,
            "failed",
            f"SAST scan failed: {exc}",
        )
        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "failed",
                "current_task": "Scan failed",
                "outcome": str(exc),
                "_persist": True,
            },
        )
    finally:
        for task in validation_tasks:
            if not task.done():
                task.cancel()
        if validation_tasks:
            await asyncio.gather(*validation_tasks, return_exceptions=True)
        _sast_tasks.pop(sast_run_id, None)
        _sast_stop_requested.discard(sast_run_id)
        _sast_pause_requested.discard(sast_run_id)
        _candidates.pop(sast_run_id, None)
        if tmpdir and os.path.isdir(tmpdir):
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
        try:
            from aespa.services import llm as llm_svc

            llm_svc.clear_run_context()
        except Exception:
            pass
        owned_lease = _sast_workspace_leases.pop(sast_run_id, None)
        if owned_lease is not None:
            owned_lease.release()


# ── Public lifecycle API ───────────────────────────────────────────────────────


def create_sast_run(
    *,
    collection_id: int | None = None,
    name: str,
    document_id: int | None = None,
    source_archive_path: str | None = None,
    source_filename: str | None = None,
    llm_config_id: int | None = None,
    llm_profile_id: int | None = None,
    triggered_by_run_type: str | None = None,
    triggered_by_run_id: int | None = None,
) -> SastRun:
    """Create and persist a SastRun row. Does NOT start the scan.

    New runs use ``source_archive_path`` + ``source_filename``. Collection and
    document linkage remains supported for legacy/import compatibility.
    """
    run = SastRun(
        collection_id=collection_id,
        name=name,
        document_id=document_id,
        source_archive_path=source_archive_path,
        source_filename=source_filename,
        llm_config_id=llm_config_id,
        llm_profile_id=llm_profile_id,
        triggered_by_run_type=triggered_by_run_type,
        triggered_by_run_id=triggered_by_run_id,
        status="pending",
        created_at=datetime.now(_UTC),
        updated_at=datetime.now(_UTC),
    )
    with Session(get_engine()) as s:
        s.add(run)
        s.commit()
        s.refresh(run)
    return run


async def start_sast_scan(sast_run_id: int, *, resume: bool = False) -> None:
    """Start a background SAST scan task for an existing SastRun."""
    if sast_run_id in _sast_tasks:
        log.info("start_sast_scan: already running for sast_run_id=%s", sast_run_id)
        return

    log.info("start_sast_scan: sast_run_id=%s", sast_run_id)

    lease = try_acquire_sast_workspace_lease(Path(get_settings().data_dir), sast_run_id)
    if lease is None:
        raise RuntimeError(
            f"SAST run {sast_run_id} is already active in another AESPA process."
        )
    _sast_workspace_leases[sast_run_id] = lease

    # Tag every event this run emits as run_kind='sast'.  The scope is retained
    # as the authoritative surface marker.  This also overrides any
    # surrounding caller scope, since the task created below snapshots this
    # authoritative 'sast' context.
    try:
        with events_svc.run_kind_scope("sast"):
            if not resume:
                _clear_checkpoints(sast_run_id)
            with Session(get_engine()) as s:
                run = s.get(SastRun, sast_run_id)
                if run is None:
                    raise ValueError(f"SastRun {sast_run_id} not found")
                run.status = "scanning"
                run.started_at = run.started_at or datetime.now(_UTC)
                run.completed_at = None
                run.error_message = None
                if not resume:
                    run.leads_count = 0
                    run.completion_status = "pending"
                    run.phase_state_json = json.dumps(_empty_phase_state())
                    run.coverage_json = None
                    run.report_json = None
                run.updated_at = datetime.now(_UTC)
                s.add(run)
                if not resume:
                    for lead in s.exec(
                        select(ScanLead)
                        .where(ScanLead.producer_run_id == sast_run_id)
                        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
                    ).all():
                        lead.reportable = False
                        lead.validation_status = "superseded"
                        lead.status = "inconclusive"
                        lead.updated_at = datetime.now(_UTC)
                        s.add(lead)
                s.commit()

            events_svc.emit(
                sast_run_id,
                {
                    "type": "agent_status",
                    "agent_id": "sast-scanner",
                    "role": "SAST Analyst",
                    "status": "active",
                    "current_task": "SAST scan starting…",
                    "outcome": None,
                    "_persist": True,
                },
            )

            task = asyncio.create_task(
                _sast_scan_task(sast_run_id, resume=resume),
                name=f"sast-scan-{sast_run_id}",
            )
            _sast_tasks[sast_run_id] = task
            _notify_campaign_source_started(sast_run_id)
            if resume:
                from aespa.services import run_pause as run_pause_svc

                run_pause_svc.clear_pause("sast", sast_run_id)
    except Exception:
        _sast_workspace_leases.pop(sast_run_id, None)
        lease.release()
        raise


async def run_sast_scan(sast_run_id: int) -> None:
    """Start and await a SAST scan to completion.

    Safe to call when already running. Task failures are logged and swallowed.
    """
    with Session(get_engine()) as s:
        run = s.get(SastRun, sast_run_id)
        resume = run is not None and run.status == "paused"
    await start_sast_scan(sast_run_id, resume=resume)
    task = _sast_tasks.get(sast_run_id)
    if task is not None:
        try:
            await task
        except (asyncio.CancelledError, Exception) as exc:
            log.warning(
                "run_sast_scan: sast_run_id=%s ended with: %s", sast_run_id, exc
            )


async def stop_sast_scan(sast_run_id: int) -> bool:
    """Cancel an in-progress SAST scan."""
    task = _sast_tasks.get(sast_run_id)
    if task is not None:
        _sast_stop_requested.add(sast_run_id)
        task.cancel()
        _update_sast_run_status(sast_run_id, "cancelled")
        # This runs from an unscoped request handler; without the scope the
        # persisted agent_status row defaults to run_kind='web' and leaks into a
        # colliding web run (events.py has no id-keyed fallback any more).
        with events_svc.run_kind_scope("sast"):
            events_svc.emit(
                sast_run_id,
                {
                    "type": "agent_status",
                    "agent_id": "sast-scanner",
                    "role": "SAST Analyst",
                    "status": "idle",
                    "current_task": "Scan stopped",
                    "outcome": "stopped",
                    "_persist": True,
                },
            )
        return True
    return False


async def pause_sast_scan(sast_run_id: int) -> bool:
    """Request a cooperative pause at the next completed agent step."""
    task = _sast_tasks.get(sast_run_id)
    if task is None or task.done():
        return False
    _sast_pause_requested.add(sast_run_id)
    with events_svc.run_kind_scope("sast"):
        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "pausing",
                "current_task": "Pausing after the current provider step",
                "outcome": None,
                "_persist": True,
            },
        )
    return True


async def pause_sast_scan_and_wait(sast_run_id: int, timeout: float = 30.0) -> bool:
    task = _sast_tasks.get(sast_run_id)
    if task is None or task.done():
        return False
    paused = await pause_sast_scan(sast_run_id)
    with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout)
    return paused


async def stop_sast_scan_and_wait(sast_run_id: int, timeout: float = 5.0) -> bool:
    """Cancel a SAST scan and wait briefly for its cleanup handlers."""
    task = _sast_tasks.get(sast_run_id)
    if task is None or task.done():
        return False
    stopped = await stop_sast_scan(sast_run_id)
    with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout)
    return stopped


def is_sast_scan_running(sast_run_id: int) -> bool:
    return sast_run_id in _sast_tasks and not _sast_tasks[sast_run_id].done()


def get_sast_status(sast_run_id: int) -> dict:
    running = is_sast_scan_running(sast_run_id)
    with Session(get_engine()) as s:
        run = s.get(SastRun, sast_run_id)
        run_status = run.status if run else "unknown"
    return {
        "running": running,
        "status": "running" if running else run_status,
    }


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
