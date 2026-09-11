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
    SastCoverageObligation,
    SastEvidenceReceipt,
    SastObligationLead,
    SastRun,
    SastWorker,
    ScanLead,
)
from aespa.sast_workspace import (
    SastWorkspaceLease,
    try_acquire_sast_workspace_lease,
)
from aespa.services import events as events_svc
from aespa.services import sast_semantic as semantic_svc
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
_PHASES = (
    "scope",
    "repository_model",
    "threat_model",
    "planning",
    "discovery",
    "reconciliation",
    "validation",
    "closure",
    "attack_path",
    "report",
)
_SAST_VALIDATOR_MAX_CONCURRENT = 4
_SAST_NETWORK_RETRY_DELAYS = (1.0, 2.0, 4.0)
_SESSION_AUTHENTICATED_LLM_PROVIDERS = {
    "codex",
    "openai_codex",
    "github_copilot",
    "factory_droid",
    "google_antigravity",
    "bedrock",
    "bedrock_mantle",
    "azure_openai",
    "azure_foundry",
}


class SastPauseRequested(RuntimeError):
    """The current SAST task reached a safe user-requested pause boundary."""


class SastNetworkPause(RuntimeError):
    """Transient provider connectivity remained unavailable after retries."""


def _llm_is_available_for_semantic_phases(config: Any) -> bool:
    """Return whether semantic model calls have an available auth path."""
    return bool(
        config.api_key
        or config.base_url
        or str(config.provider) in _SESSION_AUTHENTICATED_LLM_PROVIDERS
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
    max_tool_calls: int | None = None,
) -> str:
    """Run one SAST agent with durable turn checkpoints and bounded retries."""
    from aespa.services import llm as llm_svc

    key = _checkpoint_key(worker_key)
    saved = _load_checkpoint(sast_run_id, phase, key) if resume else {}
    last_error: BaseException | None = None
    for attempt in range(len(_SAST_NETWORK_RETRY_DELAYS) + 1):
        messages = saved.get("messages")
        step_count = int(saved.get("step_count") or 0)
        observed_step_count = step_count

        async def _on_checkpoint(new_messages: list[dict], new_step_count: int) -> None:
            nonlocal saved, observed_step_count
            observed_step_count = new_step_count
            saved = {
                "messages": new_messages,
                "step_count": new_step_count,
                "worker_key": worker_key,
            }
            _save_checkpoint(sast_run_id, phase, key, saved)

        try:

            def _bounded_termination_check():
                if max_tool_calls is not None and observed_step_count >= max_tool_calls:
                    return f"phase tool-call budget of {max_tool_calls} reached"
                return termination_check() if termination_check else None

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
                termination_check=_bounded_termination_check,
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
    if status == "running":
        _emit_agent_activity(
            sast_run_id,
            agent_id="sast-scanner",
            role="SAST Analyst",
            status="active",
            current_task=message,
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
    semantic_planning: dict[str, Any] | None = None,
    semantic_obligation_keys: set[str] | None = None,
    discovery_strategy: str = "threat_directed",
    min_confidence: float = CONFIDENCE_THRESHOLD,
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
    assigned_semantic = set(semantic_obligation_keys or set())

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

        if tool_name == "record_semantic_disposition":
            obligation_key = str(tool_input.get("obligation_key", ""))
            if semantic_planning is None or obligation_key not in assigned_semantic:
                return "Error: security check is not assigned to this worker."
            ok, message = semantic_svc.record_obligation_disposition(
                semantic_planning,
                obligation_key,
                status=str(tool_input.get("status", "")),
                reasoning=str(tool_input.get("reasoning", "")),
                evidence=_normalize_tool_list(tool_input.get("evidence")),
                controls=_normalize_tool_list(tool_input.get("controls")),
            )
            if ok:
                _set_phase(
                    sast_run_id,
                    "planning",
                    "complete",
                    "Semantic coverage plan is being resolved by discovery workers.",
                    semantic_planning,
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
            source_trace = tool_input.get("source_trace") or {}
            sink_trace = tool_input.get("sink_trace") or {}
            reconciliation_key = semantic_svc.fingerprint(
                category,
                source_trace.get("path") or location,
                sink_trace.get("path") or location,
                " ".join(
                    sorted(semantic_svc._tokens(tool_input.get("description", "")))
                ),
            )
            existing = next(
                (
                    item
                    for item in _candidates[sast_run_id]
                    if item.get("fingerprint") == fingerprint
                    or item.get("reconciliation_key") == reconciliation_key
                    or (
                        item.get("title") == title
                        and item.get("category") == category
                        and item.get("location") == location
                    )
                ),
                None,
            )
            if existing is not None:
                existing["evidence"] = "\n\n".join(
                    dict.fromkeys(
                        filter(
                            None,
                            [existing.get("evidence"), tool_input.get("evidence")],
                        )
                    )
                )[:12000]
                existing["locations"] = list(
                    dict.fromkeys(
                        existing.get("locations", []) + ([location] if location else [])
                    )
                )[:20]
                existing["provenance"] = list(
                    dict.fromkeys(
                        existing.get("provenance", [])
                        + ([assigned_worker_id] if assigned_worker_id else [])
                    )
                )
                existing["proof_gaps"] = list(
                    dict.fromkeys(
                        existing.get("proof_gaps", [])
                        + _normalize_tool_list(tool_input.get("proof_gaps"))
                    )
                )[:20]
                if work_item_id >= 0 and existing.get("lead_id"):
                    workprogram_svc.attach_lead(work_item_id, int(existing["lead_id"]))
                _persist_candidate_state(sast_run_id)
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
                "semantic_obligation_keys": [
                    str(key)
                    for key in _normalize_tool_list(tool_input.get("obligation_keys"))
                    if str(key) in assigned_semantic
                ],
                "fingerprint": fingerprint,
                "title": title,
                "category": category,
                "severity": str(tool_input.get("severity", "medium")),
                "classification": str(tool_input.get("classification", "exploitable")),
                "root_causes": _normalize_tool_list(tool_input.get("root_causes")),
                "discovery_strategy": discovery_strategy,
                "location": location,
                "description": str(tool_input.get("description", "")),
                "evidence": str(tool_input.get("evidence", "")),
                "suggested_endpoint": str(tool_input.get("suggested_endpoint", "")),
                "source_trace": source_trace,
                "controls": tool_input.get("controls") or [],
                "sink_trace": sink_trace,
                "proof_gaps": tool_input.get("proof_gaps") or [],
                "reconciliation_key": reconciliation_key,
                "provenance": [assigned_worker_id] if assigned_worker_id else [],
                "locations": [location] if location else [],
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
            kept = confidence >= min_confidence
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


def _make_threat_model_executor(
    sast_run_id: int,
    root: Path,
    coverage: dict[str, dict],
    semantic_model: dict[str, Any],
    threat_model: dict[str, Any],
):
    """Build the constrained source and recording tools for threat analysis."""

    async def tool_executor(tool_name: str, tool_input: dict, step: int) -> str:
        if sast_run_id in _sast_stop_requested:
            return "Scan stopped by user."
        read_result = _run_read_tool(
            sast_run_id,
            root,
            coverage,
            "threat_model",
            tool_name,
            tool_input,
        )
        if read_result is not None:
            _persist_coverage(sast_run_id, coverage)
            return read_result

        reviewed_paths = {
            path
            for path, item in coverage.items()
            if "threat_model" in item.get("phases", [])
        }
        if tool_name == "record_model_fact":
            ok, message, _node_id = semantic_svc.record_agent_model_fact(
                root, semantic_model, tool_input, reviewed_paths
            )
        elif tool_name == "record_threat_scenario":
            ok, message = semantic_svc.record_agent_threat_scenario(
                semantic_model, threat_model, tool_input
            )
        elif tool_name == "finalize_threat_model":
            ok, message = semantic_svc.finalize_agent_threat_model(
                semantic_model,
                threat_model,
                tool_input,
                files_reviewed=len(reviewed_paths),
            )
        else:
            return f"Error: unknown threat-model tool {tool_name!r}."
        if ok:
            _save_checkpoint(
                sast_run_id,
                "threat_model",
                "hybrid-state",
                {"model": semantic_model, "threat_model": threat_model},
            )
        return message if ok else f"Error: {message}"

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


def _reconcile_candidate_ledger(sast_run_id: int) -> dict[str, int]:
    """Annotate candidates with semantic clusters while preserving IDs.

    Validator checkpoints and legacy exports refer to candidate IDs, so the
    reconciliation receipt deliberately keeps those IDs stable. Duplicate
    suppression occurs at creation; this pass retains every contributing
    location/provenance for reporting and closure.
    """

    candidates = _candidates.get(sast_run_id, [])
    for candidate in list(candidates):
        roots = [
            str(root).strip()
            for root in candidate.get("root_causes", [])
            if str(root).strip()
        ]
        if len(roots) <= 1 or candidate.get("split_materialized"):
            continue
        candidate["root_causes"] = [roots[0]]
        candidate["split_materialized"] = True
        for root_cause in roots[1:]:
            split = dict(candidate)
            split["candidate_id"] = (
                max(
                    (int(item.get("candidate_id", -1)) for item in candidates),
                    default=-1,
                )
                + 1
            )
            split["root_causes"] = [root_cause]
            split["split_from_candidate_id"] = candidate.get("candidate_id")
            split["description"] = (
                f"{candidate.get('description', '')}\n\nDistinct root cause: {root_cause}".strip()
            )
            split["fingerprint"] = lead_fingerprint(
                category=str(split.get("category") or ""),
                title=f"{split.get('title')} — {root_cause[:80]}",
                location=str(split.get("location") or ""),
            )
            split["title"] = f"{split.get('title')} — {root_cause[:80]}"
            split["reconciliation_key"] = semantic_svc.fingerprint(
                split.get("category"), split.get("location"), root_cause
            )
            candidates.append(split)
    reconciled, stats = semantic_svc.reconcile_candidates(candidates)
    stats["split"] = sum(
        bool(candidate.get("split_from_candidate_id") is not None)
        for candidate in candidates
    )
    clusters = {
        item.get("reconciliation_key"): item
        for item in reconciled
        if item.get("reconciliation_key")
    }
    canonical_by_key: dict[str, dict] = {}
    for candidate in candidates:
        trace = candidate.get("source_trace") or {}
        sink = candidate.get("sink_trace") or {}
        key = semantic_svc.fingerprint(
            candidate.get("category"),
            trace.get("path") or candidate.get("location"),
            sink.get("path") or candidate.get("location"),
            " ".join(sorted(semantic_svc._tokens(candidate.get("description")))),
        )
        cluster = clusters.get(key)
        candidate["reconciliation_key"] = key
        if cluster is not None:
            candidate["provenance"] = cluster.get("provenance", [])
            candidate["locations"] = cluster.get("locations", [])
            candidate["merged_candidate_ids"] = cluster.get("merged_candidate_ids", [])
        canonical = canonical_by_key.get(key)
        if canonical is None:
            canonical_by_key[key] = candidate
        else:
            candidate.update(
                {
                    "reconciled_duplicate": True,
                    "reconciled_into_candidate_id": canonical.get("candidate_id"),
                    "validation_status": "dismissed",
                    "validation_reasoning": (
                        "Merged into an equivalent root-cause hypothesis before validation."
                    ),
                    "reportable": False,
                }
            )
            canonical["evidence"] = "\n\n".join(
                dict.fromkeys(
                    filter(None, [canonical.get("evidence"), candidate.get("evidence")])
                )
            )[:12000]
    _persist_candidate_state(sast_run_id)
    return {key: int(value) for key, value in stats.items()}


def _make_review_executor(
    sast_run_id: int,
    root: Path,
    coverage: dict[str, dict],
    phase: str,
    collection_id: int | None = None,
    assigned_candidate_id: int | None = None,
    min_confidence: float = CONFIDENCE_THRESHOLD,
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
            in {
                "get_candidate",
                "validate_candidate",
                "record_attack_path",
                "record_adjacent_concern",
            }
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
            "record_adjacent_concern",
        }:
            return f"Error: no lead {candidate.get('reference') if candidate else f'#{candidate_id}'} found."
        if tool_name == "record_adjacent_concern":
            concern = {
                "title": str(tool_input.get("title", "Adjacent concern"))[:500],
                "description": str(tool_input.get("description", ""))[:4000],
                "location": str(tool_input.get("location", ""))[:240],
                "proof_gap": str(tool_input.get("proof_gap", ""))[:1000],
                "candidate_id": candidate_id,
                "status": "pending_closure",
            }
            concerns = candidate.setdefault("adjacent_concerns", [])
            if concern not in concerns:
                concerns.append(concern)
            _persist_candidate_state(sast_run_id)
            return (
                f"Adjacent concern queued for lead "
                f"{candidate.get('reference') or f'#{candidate_id}'}; it is not a finding."
            )
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
                    and confidence >= min_confidence,
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


def _apply_sast_policy(candidate: dict[str, Any], policy: Any) -> None:
    """Apply user-selected reporting classes after independent validation."""

    severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    reasons: list[str] = []
    if severity_rank.get(
        str(candidate.get("severity") or "low"), 1
    ) < severity_rank.get(policy.sast_min_severity, 1):
        reasons.append(f"severity is below policy minimum {policy.sast_min_severity}")
    if float(candidate.get("confidence") or 0) < policy.sast_min_confidence:
        reasons.append(
            f"confidence is below policy minimum {policy.sast_min_confidence:.2f}"
        )
    classification = str(candidate.get("classification") or "exploitable").casefold()
    if (
        classification in {"defense_in_depth", "defence_in_depth"}
        and not policy.sast_defense_in_depth_findings
    ):
        reasons.append("defense-in-depth findings are disabled")
    text = " ".join(
        str(candidate.get(key) or "") for key in ("title", "category", "description")
    ).casefold()
    controls = (
        ("rate", policy.sast_rate_limit_findings, ("rate limit", "brute force")),
        (
            "race",
            policy.sast_race_condition_findings,
            ("race condition", "concurrency", "toctou"),
        ),
        (
            "audit",
            policy.sast_audit_logging_findings,
            ("audit log", "monitoring", "detection"),
        ),
        (
            "dependency",
            policy.sast_dependency_findings,
            ("dependency", "cve-", "vulnerable package"),
        ),
    )
    for label, enabled, terms in controls:
        if not enabled and any(term in text for term in terms):
            reasons.append(f"{label} findings are disabled")
    if reasons:
        candidate["reportable"] = False
        candidate["policy_exclusion_reasons"] = reasons


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
    if lead.id is not None:
        with Session(get_engine()) as session:
            persisted_lead = session.get(ScanLead, lead.id)
            if persisted_lead is not None:
                if source_work_item_id:
                    persisted_lead.source_work_item_id = int(source_work_item_id)
                persisted_lead.classification = str(
                    candidate.get("classification") or "exploitable"
                )
                persisted_lead.discovery_strategy = str(
                    candidate.get("discovery_strategy") or ""
                )
                persisted_lead.provenance_json = json.dumps(
                    candidate.get("provenance") or []
                )
                session.add(persisted_lead)
                session.commit()
        if source_work_item_id:
            workprogram_svc.attach_lead(int(source_work_item_id), lead.id)
    if lead.id is not None and candidate.get("semantic_obligation_keys"):
        with Session(get_engine()) as session:
            obligations = list(
                session.exec(
                    select(SastCoverageObligation)
                    .where(SastCoverageObligation.sast_run_id == sast_run_id)
                    .where(
                        SastCoverageObligation.obligation_key.in_(
                            candidate["semantic_obligation_keys"]
                        )
                    )
                )
            )
            existing = {
                (row.obligation_id, row.lead_id, row.relationship)
                for row in session.exec(
                    select(SastObligationLead).where(
                        SastObligationLead.sast_run_id == sast_run_id
                    )
                )
            }
            for obligation in obligations:
                key = (obligation.id, lead.id, "primary")
                if key not in existing:
                    session.add(
                        SastObligationLead(
                            sast_run_id=sast_run_id,
                            obligation_id=obligation.id,
                            lead_id=lead.id,
                            relationship="primary",
                        )
                    )
            session.commit()


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
        SAST_CLOSURE_PROMPT,
        SAST_REPOSITORY_MODEL_PROMPT,
        SAST_THREAT_MODEL_PROMPT,
        SAST_THREAT_MODEL_TOOLS,
        SAST_TOOLS,
        SAST_VALIDATION_PROMPT,
        SAST_VALIDATION_TOOLS,
        sast_worker_prompt,
    )
    from aespa.services.settings import get_llm_config_for_role
    from aespa.services.settings_integrations import get_scanner_policy

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
    llm_cfg_obj = None
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
            scanner_policy = get_scanner_policy(s)
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
            for obj in [run, coll, doc]:
                if obj is not None and id(obj) not in detached:
                    s.expunge(obj)
                    detached.add(id(obj))

        # Start usage tracking before the repository and threat-model phases.
        # Both phases can call the configured SAST model and belong to this run.
        llm_svc.set_run_context(
            sast_run_id,
            lambda evt: events_svc.emit(sast_run_id, evt),
            run_kind="sast",
        )

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

        def _completed_phase_data(phase: str) -> dict[str, Any] | None:
            if not _phase_was_complete(phase):
                return None
            data = saved_phases.get(phase, {}).get("data")
            return data if isinstance(data, dict) and data else None

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

        # Completed semantic phases carry the data needed by later phases, so a
        # resumed scan can reuse them. Incomplete phases are rebuilt against the
        # freshly extracted immutable archive.
        current_phase = "repository_model"
        semantic_model = _completed_phase_data("repository_model")
        llm_ready_for_semantic = _llm_is_available_for_semantic_phases(llm_cfg_obj)
        if semantic_model is None:
            _set_phase(
                sast_run_id,
                "repository_model",
                "running",
                "Normalizing repository components, operations, controls, and dependencies.",
            )
            _emit_agent_activity(
                sast_run_id,
                agent_id="sast-repository-modeller",
                role="Repository Modeller",
                status="active",
                current_task="Modelling repository components and dependencies",
            )
            semantic_model = semantic_svc.build_repository_model(root)
            try:
                if not llm_ready_for_semantic:
                    raise RuntimeError(
                        "configured provider has no available credentials"
                    )
                semantic_model = await semantic_svc.reconcile_repository_model_with_llm(
                    llm_svc, llm_cfg_obj, semantic_model, SAST_REPOSITORY_MODEL_PROMPT
                )
            except Exception as exc:
                semantic_model["reconciliation"] = {
                    "status": "failed",
                    "warning": str(exc)[:500],
                }
            _set_phase(
                sast_run_id,
                "repository_model",
                "complete",
                "Repository model ready.",
                semantic_model,
            )
            reconciliation = semantic_model.get("reconciliation", {})
            _emit_agent_activity(
                sast_run_id,
                agent_id="sast-repository-modeller",
                role="Repository Modeller",
                status="complete",
                current_task="Repository model complete",
                outcome=(
                    str(reconciliation.get("warning"))[:500]
                    if reconciliation.get("status") == "failed"
                    else "Repository facts and dependencies recorded"
                ),
            )

        current_phase = "threat_model"
        semantic_threat_model = _completed_phase_data("threat_model")
        if semantic_threat_model is None:
            _set_phase(
                sast_run_id,
                "threat_model",
                "running",
                "Deriving source-backed actors, assets, boundaries, and threat scenarios.",
            )
            _emit_agent_activity(
                sast_run_id,
                agent_id="sast-threat-modeller",
                role="Threat Modeller",
                status="active",
                current_task="Reviewing assets, actors, boundaries, and threat scenarios",
            )
            semantic_threat_model = semantic_svc.build_threat_model(semantic_model)
            try:
                if not llm_ready_for_semantic:
                    raise RuntimeError(
                        "configured provider has no available credentials"
                    )
                saved_hybrid = (
                    _load_checkpoint(sast_run_id, "threat_model", "hybrid-state")
                    if resume
                    else {}
                )
                if isinstance(saved_hybrid.get("model"), dict):
                    semantic_model = saved_hybrid["model"]
                if isinstance(saved_hybrid.get("threat_model"), dict):
                    semantic_threat_model = saved_hybrid["threat_model"]
                ranked_files = [
                    item
                    for item in semantic_model.get("inventory", {}).get("files", [])
                    if item.get("readable")
                    and item.get("classification") != "deprioritized"
                ][:120]

                def _threat_done(_tool_input: dict, _calls: int):
                    if not semantic_threat_model.get("finalized"):
                        return False, "Call finalize_threat_model before finishing."
                    return True, ""

                await _run_checkpointed_agent(
                    sast_run_id=sast_run_id,
                    phase="threat_model",
                    worker_key="hybrid-threat-analyst",
                    config=llm_cfg_obj,
                    system_message=SAST_THREAT_MODEL_PROMPT,
                    initial_user_message=(
                        "Inspect representative source files and build the application threat model. "
                        "Deterministic facts are navigation hints, not a complete model. Keep assets "
                        "separate from stores. Record important assets, actors, identities, boundaries, "
                        "operations, controls, and scenarios with tool calls. Do not record secret values.\n\n"
                        "Ranked source inventory:\n"
                        + json.dumps(ranked_files, ensure_ascii=False)
                        + "\n\nDeterministic repository hints:\n"
                        + json.dumps(
                            semantic_model.get("nodes", [])[:500], ensure_ascii=False
                        )
                    ),
                    tool_executor=_make_threat_model_executor(
                        sast_run_id,
                        root,
                        coverage,
                        semantic_model,
                        semantic_threat_model,
                    ),
                    emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
                    stop_check=lambda: (
                        sast_run_id in _sast_stop_requested
                        or sast_run_id in _sast_pause_requested
                    ),
                    tools=SAST_THREAT_MODEL_TOOLS,
                    resume=resume,
                    done_check=_threat_done,
                    max_tool_calls=100,
                )
            except (SastNetworkPause, llm_svc.LLMQuotaPauseError):
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-threat-modeller",
                    role="Threat Modeller",
                    status="paused",
                    current_task="Threat modelling paused",
                )
                raise
            except asyncio.CancelledError:
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-threat-modeller",
                    role="Threat Modeller",
                    status="cancelled",
                    current_task="Threat modelling stopped",
                )
                raise
            except Exception as exc:
                semantic_threat_model["llm_status"] = "failed"
                semantic_threat_model["quality"] = {
                    "status": "reduced",
                    "reasons": [f"Agent-led threat review failed: {str(exc)[:300]}"],
                }
                semantic_threat_model.setdefault("open_questions", []).append(
                    f"Threat-model reconciliation failed: {str(exc)[:300]}"
                )
            _set_phase(
                sast_run_id,
                "threat_model",
                "complete",
                semantic_threat_model.get("summary", "Threat model ready."),
                semantic_threat_model,
            )
            _emit_agent_activity(
                sast_run_id,
                agent_id="sast-threat-modeller",
                role="Threat Modeller",
                status="complete",
                current_task="Threat model complete",
                outcome=semantic_threat_model.get(
                    "summary", "Threat scenarios recorded."
                ),
            )

        current_phase = "planning"
        semantic_planning = _completed_phase_data("planning")
        if semantic_planning is None:
            _set_phase(
                sast_run_id,
                "planning",
                "running",
                "Creating required security checks and analysis batches.",
            )
            semantic_planning = semantic_svc.plan_semantic_obligations(
                semantic_model, semantic_threat_model
            )
            semantic_planning["legacy_work_program_projection"] = (
                workprogram_svc.semantic_obligation_summary(semantic_planning)
            )
            semantic_planning["dependency_analysis"] = (
                semantic_svc.deterministic_dependency_analysis(semantic_model)
            )
            semantic_planning["relational_projection"] = (
                semantic_svc.persist_semantic_state(
                    sast_run_id,
                    semantic_model,
                    semantic_threat_model,
                    semantic_planning,
                )
            )
            _set_phase(
                sast_run_id,
                "planning",
                "complete",
                "Semantic coverage plan ready.",
                semantic_planning,
            )

        initial_message = _build_initial_message(coll, endpoints, archive_name)

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
            agent_id = f"sast-validator-{candidate_id}"
            role = "SAST Candidate Validator"
            async with validation_semaphore:
                candidate = _candidate_for_id(sast_run_id, candidate_id)
                if candidate is None:
                    _emit_agent_activity(
                        sast_run_id,
                        agent_id=agent_id,
                        role=role,
                        status="skipped",
                        current_task=f"Candidate {candidate_id} is no longer available",
                    )
                    return
                _emit_agent_activity(
                    sast_run_id,
                    agent_id=agent_id,
                    role=role,
                    status="active",
                    current_task=f"Validating candidate {candidate_id}: {candidate.get('title') or 'Untitled candidate'}",
                )
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
                            min_confidence=scanner_policy.sast_min_confidence,
                        ),
                        emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
                        stop_check=_stop_check,
                        tools=SAST_VALIDATION_TOOLS,
                        resume=resume,
                        max_tool_calls=scanner_policy.sast_validator_budget,
                    )
                    _raise_if_stopped()
                except asyncio.CancelledError:
                    _emit_agent_activity(
                        sast_run_id,
                        agent_id=agent_id,
                        role=role,
                        status="cancelled",
                        current_task=f"Validation stopped for candidate {candidate_id}",
                    )
                    raise
                except llm_svc.LLMQuotaPauseError:
                    _emit_agent_activity(
                        sast_run_id,
                        agent_id=agent_id,
                        role=role,
                        status="paused",
                        current_task=f"Validation paused for candidate {candidate_id}",
                        outcome="LLM quota unavailable",
                    )
                    raise
                except (SastPauseRequested, SastNetworkPause):
                    _emit_agent_activity(
                        sast_run_id,
                        agent_id=agent_id,
                        role=role,
                        status="paused",
                        current_task=f"Validation paused for candidate {candidate_id}",
                    )
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
                    _emit_agent_activity(
                        sast_run_id,
                        agent_id=agent_id,
                        role=role,
                        status="failed",
                        current_task=f"Validation failed for candidate {candidate_id}",
                        outcome=str(exc),
                    )
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
                _emit_agent_activity(
                    sast_run_id,
                    agent_id=agent_id,
                    role=role,
                    status="complete",
                    current_task=f"Validated candidate {candidate_id}",
                    outcome=str(candidate.get("validation_status") or "inconclusive"),
                )

        def _schedule_candidate_validation(candidate: dict) -> None:
            nonlocal validation_started
            candidate_id = int(candidate["candidate_id"])
            if candidate_id in validation_scheduled:
                return
            validation_scheduled.add(candidate_id)
            _emit_agent_activity(
                sast_run_id,
                agent_id=f"sast-validator-{candidate_id}",
                role="SAST Candidate Validator",
                status="spawned",
                current_task=f"Queued validation for candidate {candidate_id}: {candidate.get('title') or 'Untitled candidate'}",
            )
            if not validation_started:
                validation_started = True
                _set_phase(
                    sast_run_id,
                    "validation",
                    "running",
                    "Validating reconciled candidates.",
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

        if resume:
            saved_planning = (
                saved_phases.get("planning", {}).get("data", {})
                if isinstance(saved_phases, dict)
                else {}
            )
            saved_obligations = {
                item.get("obligation_key"): item
                for item in saved_planning.get("obligations", [])
                if isinstance(item, dict) and item.get("obligation_key")
            }
            for obligation in semantic_planning.get("obligations", []):
                previous = saved_obligations.get(obligation.get("obligation_key"))
                if previous is not None:
                    for key in (
                        "status",
                        "disposition",
                        "reasoning",
                        "evidence",
                        "controls",
                    ):
                        if key in previous:
                            obligation[key] = previous[key]

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
            discovery_workers = workprogram_svc.worker_rows(sast_run_id)
            semantic_assignments: dict[int, set[str]] = {
                int(worker.id): set()
                for worker in discovery_workers
                if worker.id is not None
            }
            assignment_ids = list(semantic_assignments)
            baseline_worker_id = assignment_ids[0] if len(assignment_ids) > 1 else None
            threat_worker_ids = [
                worker_id
                for worker_id in assignment_ids
                if worker_id != baseline_worker_id
            ] or assignment_ids
            if threat_worker_ids:
                for index, packet in enumerate(semantic_planning.get("workers", [])):
                    worker_id = threat_worker_ids[index % len(threat_worker_ids)]
                    semantic_assignments[worker_id].update(
                        str(key) for key in packet.get("obligation_keys", [])
                    )

            async def _run_discovery_worker(worker: SastWorker) -> str:
                if worker.id is None:
                    return "Worker has no persisted id."
                if resume and worker.status == "complete":
                    return worker.summary or f"{worker.worker_key} already complete."
                agent_id = f"sast-worker-{worker.id}"
                role = f"SAST {worker.class_group.replace('_', ' ').title()} Worker"
                _emit_agent_activity(
                    sast_run_id,
                    agent_id=agent_id,
                    role=role,
                    status="spawned",
                    current_task=f"Queued analysis worker {worker.worker_key}",
                )
                async with worker_semaphore:
                    workprogram_svc.set_worker_status(worker.id, "running")
                    payload = workprogram_svc.worker_payload(worker.id)
                    semantic_keys = semantic_assignments.get(worker.id, set())
                    semantic_payload = semantic_svc.obligation_payload(
                        semantic_planning, semantic_keys
                    )
                    if worker.id == baseline_worker_id:
                        semantic_payload = {
                            "strategy": "independent_baseline",
                            "obligations": [],
                            "instructions": (
                                "Perform an open-ended security review without access to "
                                "the generated threat scenarios. Follow concrete source "
                                "evidence and the assigned source work program."
                            ),
                        }
                    assigned_count = len(payload.get("work_items") or [])
                    _emit_agent_activity(
                        sast_run_id,
                        agent_id=agent_id,
                        role=role,
                        status="active",
                        current_task=(
                            f"{worker.worker_key}: reviewing {assigned_count} assigned "
                            f"item{'s' if assigned_count != 1 else ''}"
                        ),
                    )

                    def _worker_done(_tool_input: dict, _calls: int):
                        unresolved = workprogram_svc.unresolved_for_worker(worker.id)
                        if unresolved:
                            return (
                                False,
                                "Resolve these assigned work items before done: "
                                + ", ".join(str(item) for item in unresolved[:50]),
                            )
                        unresolved_semantic = [
                            item.get("obligation_key", "")
                            for item in semantic_payload.get("obligations", [])
                            if item.get("status")
                            in {"pending", "in_review", "unreviewed"}
                        ]
                        if unresolved_semantic:
                            return (
                                False,
                                "Resolve these security checks before finishing: "
                                + ", ".join(unresolved_semantic[:50]),
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
                                + "\n\nAssigned threat-based security checks:\n"
                                + json.dumps(semantic_payload, ensure_ascii=False)
                            ),
                            tool_executor=_make_tool_executor(
                                sast_run_id,
                                root,
                                run.collection_id,
                                coverage,
                                # Validation starts after the global reconciliation
                                # pass so duplicate hypotheses do not consume
                                # independent validator calls.
                                on_candidate_ready=None,
                                assigned_worker_id=worker.id,
                                semantic_planning=semantic_planning,
                                semantic_obligation_keys=semantic_keys,
                                discovery_strategy=str(
                                    semantic_payload.get("strategy")
                                    or "threat_directed"
                                ),
                                min_confidence=scanner_policy.sast_min_confidence,
                            ),
                            emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
                            stop_check=_stop_check,
                            tools=SAST_TOOLS,
                            resume=resume,
                            done_check=_worker_done,
                            max_tool_calls=(
                                scanner_policy.sast_baseline_budget
                                if worker.id == baseline_worker_id
                                else scanner_policy.sast_threat_budget
                            ),
                        )
                    except (
                        llm_svc.LLMQuotaPauseError,
                        SastPauseRequested,
                        SastNetworkPause,
                    ):
                        _emit_agent_activity(
                            sast_run_id,
                            agent_id=agent_id,
                            role=role,
                            status="paused",
                            current_task=f"Analysis paused for {worker.worker_key}",
                        )
                        raise
                    except asyncio.CancelledError:
                        _emit_agent_activity(
                            sast_run_id,
                            agent_id=agent_id,
                            role=role,
                            status="cancelled",
                            current_task=f"Analysis stopped for {worker.worker_key}",
                        )
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
                        _emit_agent_activity(
                            sast_run_id,
                            agent_id=agent_id,
                            role=role,
                            status="failed",
                            current_task=f"Analysis failed for {worker.worker_key}",
                            outcome=str(exc),
                        )
                        return f"{worker.worker_key} failed: {exc}"
                    unresolved = workprogram_svc.unresolved_for_worker(worker.id)
                    unresolved_semantic = [
                        item
                        for item in semantic_payload.get("obligations", [])
                        if item.get("status")
                        in {"pending", "in_review", "unreviewed", "blocked"}
                    ]
                    final_status = (
                        "complete"
                        if not unresolved and not unresolved_semantic
                        else "blocked"
                    )
                    workprogram_svc.set_worker_status(
                        worker.id,
                        final_status,
                        summary=summary,
                        error=(
                            f"{len(unresolved)} source and {len(unresolved_semantic)} semantic item(s) unresolved."
                            if unresolved or unresolved_semantic
                            else ""
                        ),
                    )
                    _emit_agent_activity(
                        sast_run_id,
                        agent_id=agent_id,
                        role=role,
                        status=final_status,
                        current_task=f"Analysis finished for {worker.worker_key}",
                        outcome=(
                            f"{len(unresolved)} source and {len(unresolved_semantic)} semantic item(s) unresolved"
                            if unresolved or unresolved_semantic
                            else summary
                        ),
                    )
                    return summary

            worker_summaries = await asyncio.gather(
                *(_run_discovery_worker(worker) for worker in discovery_workers)
            )
            discovery_summary = "\n".join(worker_summaries)
            _raise_if_stopped()

            if not scanner_policy.disable_deterministic_checks:
                deterministic_candidates = (
                    semantic_svc.deterministic_security_candidates(root)
                )
                if scanner_policy.sast_dependency_findings:
                    deterministic_candidates.extend(
                        semantic_svc.dependency_match_candidates(
                            semantic_planning.get("dependency_analysis", {})
                        )
                    )
                for candidate in deterministic_candidates:
                    fingerprint = lead_fingerprint(
                        category=candidate["category"],
                        title=candidate["title"],
                        location=candidate["location"],
                    )
                    if any(
                        item.get("fingerprint") == fingerprint
                        for item in _candidates[sast_run_id]
                    ):
                        continue
                    candidate["candidate_id"] = (
                        max(
                            (
                                int(item.get("candidate_id", -1))
                                for item in _candidates[sast_run_id]
                            ),
                            default=-1,
                        )
                        + 1
                    )
                    candidate["fingerprint"] = fingerprint
                    candidate["reconciliation_key"] = semantic_svc.fingerprint(
                        candidate["category"],
                        candidate["location"],
                        candidate["location"],
                        " ".join(
                            sorted(semantic_svc._tokens(candidate["description"]))
                        ),
                    )
                    candidate["source_work_item_id"] = None
                    candidate["semantic_obligation_keys"] = []
                    _candidates[sast_run_id].append(candidate)
                _sync_candidates_to_db(sast_run_id, run.collection_id)

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

        _set_phase(
            sast_run_id,
            "reconciliation",
            "running",
            "Reconciling candidate hypotheses and preserving contributing evidence.",
            {"candidates": candidate_count},
        )
        reconciliation_stats = _reconcile_candidate_ledger(sast_run_id)
        _sync_candidates_to_db(sast_run_id, run.collection_id)
        _persist_candidate_state(sast_run_id)
        _set_phase(
            sast_run_id,
            "reconciliation",
            "complete",
            "Candidate reconciliation complete.",
            reconciliation_stats,
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
                    and not candidate.get("reconciled_duplicate")
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

        current_phase = "closure"
        _set_phase(
            sast_run_id,
            "closure",
            "running",
            "Checking threat scenarios, model warnings, and adjacent concerns for closure.",
        )
        _emit_agent_activity(
            sast_run_id,
            agent_id="sast-closure-analyst",
            role="Closure Analyst",
            status="active",
            current_task="Checking unresolved security gaps and adjacent concerns",
        )
        closure_agent_failed = False
        unresolved_closure_keys = {
            str(item.get("obligation_key"))
            for item in semantic_planning.get("obligations", [])
            if item.get("status") in {"pending", "in_review", "blocked", "unreviewed"}
        }
        adjacent_for_closure = [
            concern
            for candidate in candidates
            for concern in candidate.get("adjacent_concerns", [])
            if isinstance(concern, dict) and concern.get("status") != "resolved"
        ]
        candidates_before_closure = len(candidates)
        if unresolved_closure_keys or adjacent_for_closure:
            closure_payload = {
                "repository_warnings": semantic_model.get("warnings", []),
                "threat_scenarios": semantic_threat_model.get("scenarios", []),
                "obligations": [
                    item
                    for item in semantic_planning.get("obligations", [])
                    if item.get("obligation_key") in unresolved_closure_keys
                ],
                "adjacent_concerns": adjacent_for_closure,
                "candidate_summary": [
                    {
                        "candidate_id": item.get("candidate_id"),
                        "title": item.get("title"),
                        "location": item.get("location"),
                        "validation_status": item.get("validation_status"),
                    }
                    for item in candidates
                ],
            }
            try:
                await _run_checkpointed_agent(
                    sast_run_id=sast_run_id,
                    phase="closure",
                    worker_key="semantic-closure",
                    config=llm_cfg_obj,
                    system_message=SAST_CLOSURE_PROMPT,
                    initial_user_message=(
                        "Review the bounded closure queue below. Use source tools to verify it. "
                        "Call record_semantic_disposition for every security check. If source evidence "
                        "supports a new distinct vulnerability, call write_lead then filter_lead; "
                        "it will be independently validated. Do not call get_work_program.\n\n"
                        + json.dumps(closure_payload, ensure_ascii=False)
                    ),
                    tool_executor=_make_tool_executor(
                        sast_run_id,
                        root,
                        run.collection_id,
                        coverage,
                        assigned_worker_id=None,
                        semantic_planning=semantic_planning,
                        semantic_obligation_keys=unresolved_closure_keys,
                        discovery_strategy="closure",
                        min_confidence=scanner_policy.sast_min_confidence,
                    ),
                    emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
                    stop_check=_stop_check,
                    tools=SAST_TOOLS,
                    resume=resume,
                    max_tool_calls=scanner_policy.sast_closure_budget,
                )
            except (llm_svc.LLMQuotaPauseError, SastPauseRequested, SastNetworkPause):
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-closure-analyst",
                    role="Closure Analyst",
                    status="paused",
                    current_task="Closure review paused",
                )
                raise
            except asyncio.CancelledError:
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-closure-analyst",
                    role="Closure Analyst",
                    status="cancelled",
                    current_task="Closure review stopped",
                )
                raise
            except Exception as exc:
                closure_agent_failed = True
                semantic_planning.setdefault("closure_warnings", []).append(
                    str(exc)[:500]
                )
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-closure-analyst",
                    role="Closure Analyst",
                    status="failed",
                    current_task="Closure review failed",
                    outcome=str(exc)[:500],
                )

        if len(candidates) > candidates_before_closure:
            closure_reconciliation = _reconcile_candidate_ledger(sast_run_id)
            for candidate in candidates:
                if candidate.get(
                    "validation_status"
                ) == "pending" and not candidate.get("reconciled_duplicate"):
                    candidate.setdefault("discovery_strategy", "closure")
                    _schedule_candidate_validation(candidate)
            if validation_tasks:
                await asyncio.gather(*validation_tasks)
        else:
            closure_reconciliation = {
                "input": len(candidates),
                "unique": len(candidates),
                "merged": 0,
                "split": 0,
            }

        resolved_model_warning_keys = {
            question
            for item in semantic_planning.get("obligations", [])
            if item.get("obligation_type") == "model_completeness"
            and item.get("status") in {"assessed_safe", "candidate", "not_applicable"}
            for question in item.get("open_questions", [])
        }
        for warning in semantic_model.get("warnings", []):
            if warning.get("key") in resolved_model_warning_keys:
                warning["status"] = "resolved"
        semantic_closure = semantic_svc.closure_assurance(
            semantic_model,
            semantic_threat_model,
            semantic_planning,
            candidates,
        )
        semantic_closure["closure_candidates_created"] = max(
            0, len(candidates) - candidates_before_closure
        )
        semantic_closure["reconciliation"] = closure_reconciliation
        semantic_svc.persist_semantic_state(
            sast_run_id, semantic_model, semantic_threat_model, semantic_planning
        )
        for candidate in candidates:
            _apply_sast_policy(candidate, scanner_policy)
        _sync_candidates_to_db(sast_run_id, run.collection_id)
        _set_phase(
            sast_run_id,
            "closure",
            "complete",
            f"Semantic closure is {semantic_closure['status']}.",
            semantic_closure,
        )
        if not closure_agent_failed:
            _emit_agent_activity(
                sast_run_id,
                agent_id="sast-closure-analyst",
                role="Closure Analyst",
                status="complete",
                current_task="Closure review complete",
                outcome=f"Coverage assurance is {semantic_closure['status']}",
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
            try:
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
            except (llm_svc.LLMQuotaPauseError, SastPauseRequested, SastNetworkPause):
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-attack-path",
                    role="Attack Path Analyst",
                    status="paused",
                    current_task="Attack-path analysis paused",
                )
                raise
            except asyncio.CancelledError:
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-attack-path",
                    role="Attack Path Analyst",
                    status="cancelled",
                    current_task="Attack-path analysis stopped",
                )
                raise
            except Exception as exc:
                _emit_agent_activity(
                    sast_run_id,
                    agent_id="sast-attack-path",
                    role="Attack Path Analyst",
                    status="failed",
                    current_task="Attack-path analysis failed",
                    outcome=str(exc)[:500],
                )
                raise
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
        completion_status = (
            "partial"
            if completion_status != "full" or semantic_closure["status"] != "full"
            else "full"
        )
        completion_reasons = list(
            dict.fromkeys(completion_reasons + semantic_closure["reasons"])
        )
        if not _phase_was_complete("report"):
            _set_phase(
                sast_run_id,
                "report",
                "running",
                "Building the final candidate and coverage report.",
            )
        with Session(get_engine()) as telemetry_session:
            telemetry_run = telemetry_session.get(SastRun, sast_run_id)
            try:
                telemetry_phase_state = (
                    json.loads(telemetry_run.phase_state_json or "{}")
                    if telemetry_run
                    else {}
                )
            except (TypeError, ValueError):
                telemetry_phase_state = {}
        efficiency_telemetry = semantic_svc.persist_scan_telemetry(
            sast_run_id, telemetry_phase_state, semantic_planning, candidates
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
            "efficiency_telemetry": efficiency_telemetry,
            "semantic": {
                "repository_model": semantic_model,
                "threat_model": semantic_threat_model,
                "planning": semantic_planning,
                "reconciliation": reconciliation_stats,
                "closure": semantic_closure,
            },
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
        if sast_run_id not in _sast_stop_requested:
            message = (
                "The SAST task was interrupted while running. Resume the scan "
                "to continue from its last saved step."
            )
            log.info("SAST scan interrupted: sast_run_id=%s", sast_run_id)
            _persist_candidate_state(sast_run_id)
            _persist_paused_run(
                sast_run_id,
                phase=current_phase,
                reason="interrupted",
                provider=str(getattr(llm_cfg_obj, "provider", "")),
                message=message,
            )
            events_svc.emit(
                sast_run_id,
                {
                    "type": "agent_status",
                    "agent_id": "sast-scanner",
                    "role": "SAST Analyst",
                    "status": "paused",
                    "current_task": "Scan interrupted",
                    "outcome": "resumable",
                    "_persist": True,
                },
            )
        else:
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
        message = (
            f"The SAST task stopped after an error: {exc}. Resume the scan to "
            "continue from its last saved step."
        )
        _persist_candidate_state(sast_run_id)
        _persist_paused_run(
            sast_run_id,
            phase=current_phase,
            reason="error",
            provider=str(getattr(llm_cfg_obj, "provider", "")),
            message=message,
            snapshot={"error_type": type(exc).__name__},
        )
        events_svc.emit(
            sast_run_id,
            {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "paused",
                "current_task": "Scan paused after an error",
                "outcome": "resumable",
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


def _is_light_run(sast_run_id: int) -> bool:
    with Session(get_engine()) as session:
        run = session.get(SastRun, sast_run_id)
        return run is not None and run.analysis_mode == "light"


def create_sast_run(
    *,
    collection_id: int | None = None,
    name: str,
    document_id: int | None = None,
    source_archive_path: str | None = None,
    source_filename: str | None = None,
    llm_config_id: int | None = None,
    llm_profile_id: int | None = None,
    analysis_mode: str = "deep",
    triggered_by_run_type: str | None = None,
    triggered_by_run_id: int | None = None,
) -> SastRun:
    """Create and persist a SastRun row. Does NOT start the scan.

    New runs use ``source_archive_path`` + ``source_filename``. Collection and
    document linkage remains supported for legacy/import compatibility.
    """
    if analysis_mode not in {"light", "deep"}:
        raise ValueError("analysis_mode must be either 'light' or 'deep'")
    run = SastRun(
        collection_id=collection_id,
        name=name,
        document_id=document_id,
        source_archive_path=source_archive_path,
        source_filename=source_filename,
        llm_config_id=llm_config_id,
        llm_profile_id=llm_profile_id,
        analysis_mode=analysis_mode,
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
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        await sast_scanner_light.start_sast_scan(sast_run_id, resume=resume)
        return
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
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        await sast_scanner_light.run_sast_scan(sast_run_id)
        return
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
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        return await sast_scanner_light.stop_sast_scan(sast_run_id)
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
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        return await sast_scanner_light.pause_sast_scan(sast_run_id)
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
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        return await sast_scanner_light.pause_sast_scan_and_wait(sast_run_id, timeout)
    task = _sast_tasks.get(sast_run_id)
    if task is None or task.done():
        return False
    paused = await pause_sast_scan(sast_run_id)
    with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout)
    return paused


async def stop_sast_scan_and_wait(sast_run_id: int, timeout: float = 5.0) -> bool:
    """Cancel a SAST scan and wait briefly for its cleanup handlers."""
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        return await sast_scanner_light.stop_sast_scan_and_wait(sast_run_id, timeout)
    task = _sast_tasks.get(sast_run_id)
    if task is None or task.done():
        return False
    stopped = await stop_sast_scan(sast_run_id)
    with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout)
    return stopped


def is_sast_scan_running(sast_run_id: int) -> bool:
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        return sast_scanner_light.is_sast_scan_running(sast_run_id)
    return sast_run_id in _sast_tasks and not _sast_tasks[sast_run_id].done()


def get_sast_status(sast_run_id: int) -> dict:
    if _is_light_run(sast_run_id):
        from aespa.services import sast_scanner_light

        return sast_scanner_light.get_sast_status(sast_run_id)
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
