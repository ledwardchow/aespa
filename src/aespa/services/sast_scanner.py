"""SAST scan orchestration.

Provides a first-class agentic static-analysis scan over an uploaded source
archive (``ApiDocument`` with ``doc_type='source_zip'``).  Mirrors the
``api_scanner.py`` background-task lifecycle: task registry, start/stop/status,
SSE events via ``events_svc``, and ``AgentLog`` / ``ScanLog`` persistence.

The scan:
1. Extracts the archive into a deterministic per-run directory
   (``<data_dir>/sast_extract/<id>/``) that a startup sweep can reconcile
   if the process crashes mid-scan.
2. Builds an initial context from the collection's extracted ApiEndpoint rows.
3. Drives ``llm.thinking_agentic_loop`` with read-only file tools + write_lead /
   filter_lead / done.
4. Persists high-confidence (≥ CONFIDENCE_THRESHOLD) candidates as ScanLead rows.
"""
from __future__ import annotations

import asyncio
import fnmatch
import logging
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_engine
from aespa.models import ApiCollection, ApiDocument, ApiEndpoint, SastRun
from aespa.services import events as events_svc
from aespa.services.scan_leads import CONFIDENCE_THRESHOLD, create_lead

log = logging.getLogger(__name__)

_UTC = timezone.utc

# ── In-memory state ────────────────────────────────────────────────────────────

_sast_tasks: dict[int, asyncio.Task] = {}
_sast_stop_requested: set[int] = set()

# Candidates accumulated by write_lead within a single scan task.
# sast_run_id → list of candidate dicts (awaiting filter_lead scoring).
_candidates: dict[int, list[dict]] = {}
# IDs already persisted as ScanLead rows (per run), to avoid double-write.
_persisted: dict[int, set[int]] = {}

# Max characters in a single read_file response.
_READ_FILE_MAX_CHARS = 20_000
# Max grep results.
_GREP_MAX_RESULTS = 200


# ── Safe archive extraction ────────────────────────────────────────────────────

def _safe_unzip(archive_path: str, target_dir: str) -> None:
    """Extract a zip archive, rejecting any entries that would escape target_dir."""
    target = Path(target_dir).resolve()
    with zipfile.ZipFile(archive_path, "r") as zf:
        for member in zf.namelist():
            dest = (target / member).resolve()
            # Use is_relative_to rather than string-prefix matching: a prefix
            # check treats ``…/extract/55`` as inside ``…/extract/5`` and lets a
            # crafted entry escape into a sibling directory.
            if dest != target and not dest.is_relative_to(target):
                log.warning("_safe_unzip: skipping path-traversal entry %r", member)
                continue
            zf.extract(member, target_dir)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _increment_sast_leads_count(sast_run_id: int) -> None:
    """Increment SastRun.leads_count by 1 (best-effort, never raises)."""
    try:
        with Session(get_engine()) as s:
            r = s.get(SastRun, sast_run_id)
            if r is not None:
                r.leads_count = (r.leads_count or 0) + 1
                r.updated_at = datetime.now(_UTC)
                s.add(r)
                s.commit()
    except Exception:
        pass


def _count_persisted_leads(sast_run_id: int) -> int:
    """Return the number of ScanLead rows already persisted for this run."""
    try:
        from sqlmodel import func
        with Session(get_engine()) as s:
            from aespa.models import ScanLead
            return s.exec(
                select(func.count()).select_from(ScanLead)
                .where(ScanLead.producer_run_id == sast_run_id)
            ).one()
    except Exception:
        return 0


def _flush_unfiltered_candidates(sast_run_id: int, collection_id: int) -> int:
    """Persist any write_lead candidates that never received a filter_lead call.

    Returns the count of newly persisted leads.
    """
    candidates = _candidates.get(sast_run_id, [])
    flushed = 0
    for c in candidates:
        cid = c["candidate_id"]
        if cid in _persisted.get(sast_run_id, set()):
            continue
        if c.get("confidence") is not None and c["confidence"] < CONFIDENCE_THRESHOLD:
            continue  # explicitly scored and rejected — don't save
        # Unscored (filter_lead never called): save with confidence=0 so it's
        # visible but clearly marked as unscored.
        try:
            create_lead(
                producer_run_id=sast_run_id,
                producer_run_type="sast",
                collection_id=collection_id,
                title=c["title"],
                description=c["description"],
                category=c.get("category", ""),
                severity=c.get("severity", "medium"),
                confidence=float(c.get("confidence") or 0.0),
                location=c.get("location", ""),
                evidence=c.get("evidence", ""),
                source="sast",
            )
            _persisted.setdefault(sast_run_id, set()).add(cid)
            flushed += 1
        except Exception as exc:
            log.warning("_flush_unfiltered_candidates: failed to persist: %s", exc)
    return flushed


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


def _tool_read_file(root: Path, path: str, start_line: int | None, end_line: int | None) -> str:
    try:
        target = _jail(root, path)
    except ValueError as exc:
        return f"Error: {exc}"
    if not target.is_file():
        return f"Error: not a file: {path!r}"
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
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


# ── Tool executor factory ─────────────────────────────────────────────────────

def _make_tool_executor(sast_run_id: int, root: Path, collection_id: int):
    """Return an async tool_executor closure for the SAST agentic loop.

    Handles: list_files / glob / read_file / grep / write_lead / filter_lead / done.
    Candidates are stored in _candidates[sast_run_id]; filter_lead updates
    confidence and immediately persists high-confidence leads.
    """
    _candidates[sast_run_id] = []
    _persisted[sast_run_id] = set()
    next_candidate_id: list[int] = [0]  # mutable int in closure

    async def tool_executor(tool_name: str, tool_input: dict, step: int) -> str:
        if sast_run_id in _sast_stop_requested:
            return "Scan stopped by user."

        if tool_name == "list_files":
            path = tool_input.get("path", "") or "."
            events_svc.emit(sast_run_id, {
                "type": "scanner_phase",
                "phase": "sast_tool",
                "status": "running",
                "message": f"list_files: {path}",
            })
            return _tool_list_files(
                root,
                path=path if path != "." else "",
                max_depth=int(tool_input.get("max_depth", 3)),
            )

        if tool_name == "glob":
            pattern = tool_input.get("pattern", "")
            events_svc.emit(sast_run_id, {
                "type": "scanner_phase",
                "phase": "sast_tool",
                "status": "running",
                "message": f"glob: {pattern}",
            })
            return _tool_glob(root, pattern)

        if tool_name == "read_file":
            path = str(tool_input.get("path", ""))
            sl = tool_input.get("start_line")
            el = tool_input.get("end_line")
            line_note = f" (lines {sl}–{el})" if sl or el else ""
            events_svc.emit(sast_run_id, {
                "type": "scanner_phase",
                "phase": "sast_tool",
                "status": "running",
                "message": f"read_file: {path}{line_note}",
            })
            return _tool_read_file(root, path=path, start_line=sl, end_line=el)

        if tool_name == "grep":
            pattern = str(tool_input.get("pattern", ""))
            path = str(tool_input.get("path", "")) or "."
            inc = str(tool_input.get("include_pattern", ""))
            inc_note = f" [{inc}]" if inc else ""
            events_svc.emit(sast_run_id, {
                "type": "scanner_phase",
                "phase": "sast_tool",
                "status": "running",
                "message": f"grep: {pattern!r} in {path}{inc_note}",
            })
            return _tool_grep(
                root,
                pattern=pattern,
                path=str(tool_input.get("path", "")),
                include_pattern=str(tool_input.get("include_pattern", "")),
            )

        if tool_name == "write_lead":
            cid = next_candidate_id[0]
            next_candidate_id[0] += 1
            candidate = {
                "candidate_id": cid,
                "title": str(tool_input.get("title", "")),
                "category": str(tool_input.get("category", "")),
                "severity": str(tool_input.get("severity", "medium")),
                "location": str(tool_input.get("location", "")),
                "description": str(tool_input.get("description", "")),
                "evidence": str(tool_input.get("evidence", "")),
                "suggested_endpoint": str(tool_input.get("suggested_endpoint", "")),
                "confidence": None,  # set by filter_lead
            }
            _candidates[sast_run_id].append(candidate)
            events_svc.emit(sast_run_id, {
                "type": "scanner_phase",
                "phase": "sast_candidate",
                "status": "running",
                "message": f"Candidate: {candidate['title']}",
            })
            return f"Candidate #{cid} recorded. Now call filter_lead with lead_id={cid}."

        if tool_name == "filter_lead":
            cid = int(tool_input.get("lead_id", -1))
            confidence = float(tool_input.get("confidence", 0.0))
            reasoning = str(tool_input.get("reasoning", ""))
            candidates = _candidates.get(sast_run_id, [])
            match = next((c for c in candidates if c["candidate_id"] == cid), None)
            if match is None:
                return f"Error: no candidate #{cid} found."
            match["confidence"] = confidence
            match["filter_reasoning"] = reasoning
            kept = confidence >= CONFIDENCE_THRESHOLD
            # Persist immediately so leads survive early termination.
            if kept and cid not in _persisted[sast_run_id]:
                try:
                    create_lead(
                        producer_run_id=sast_run_id,
                        producer_run_type="sast",
                        collection_id=collection_id,
                        title=match["title"],
                        description=match["description"],
                        category=match.get("category", ""),
                        severity=match.get("severity", "medium"),
                        confidence=confidence,
                        location=match.get("location", ""),
                        evidence=match.get("evidence", ""),
                        source="sast",
                    )
                    _persisted[sast_run_id].add(cid)
                    # Keep the SastRun leads_count in sync.
                    _increment_sast_leads_count(sast_run_id)
                except Exception as persist_exc:
                    log.warning("filter_lead: failed to persist lead: %s", persist_exc)
            events_svc.emit(sast_run_id, {
                "type": "scanner_phase",
                "phase": "sast_filter",
                "status": "running",
                "message": (
                    f"{'KEPT' if kept else 'DISCARDED'} candidate #{cid}: "
                    f"{match['title']} (confidence={confidence:.0%})"
                ),
            })
            return (
                f"Candidate #{cid}: confidence={confidence:.0%} — "
                f"{'KEPT (will become a ScanLead)' if kept else 'DISCARDED (below threshold)'}."
            )

        if tool_name == "done":
            # Persisted by the caller — just return the summary.
            return str(tool_input.get("summary", ""))

        return f"Unknown tool: {tool_name!r}"

    return tool_executor


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
            lines.append(f"  … and {len(endpoints) - 60} more (discover via file tools)")
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


async def _sast_scan_task(sast_run_id: int) -> None:
    """Core async task: extract archive, run agentic loop, persist leads."""
    from aespa.services import llm as llm_svc
    from aespa.services.prompts.sast import SAST_SYSTEM_PROMPT, SAST_TOOLS
    from aespa.services.settings import get_llm_config_for_role

    _sast_stop_requested.discard(sast_run_id)
    tmpdir: str | None = None
    run: SastRun | None = None  # populated early; used in except blocks
    try:
        # ── Load run, collection, document ────────────────────────────────────
        with Session(get_engine(), expire_on_commit=False) as s:
            run = s.get(SastRun, sast_run_id)
            if run is None:
                raise ValueError(f"SastRun {sast_run_id} not found")
            # Collection is optional: API SAST runs key on a collection; standalone
            # (web-oriented) runs have none and carry their own uploaded archive.
            coll = s.get(ApiCollection, run.collection_id) if run.collection_id else None
            # Resolve the source archive. Prefer the ApiDocument (the API path);
            # fall back to the standalone archive stored on the run itself.
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
                raise RuntimeError("No LLM configuration. Configure it in Settings first.")
            endpoints = list(s.exec(
                select(ApiEndpoint)
                .where(ApiEndpoint.collection_id == run.collection_id)
                .where(ApiEndpoint.in_scope == True)  # noqa: E712
                .order_by(ApiEndpoint.path, ApiEndpoint.method)
            ).all()) if run.collection_id else []
            for obj in [run, coll, doc, llm_cfg_obj]:
                if obj is not None:
                    s.expunge(obj)

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
        events_svc.emit(sast_run_id, {
            "type": "scanner_phase",
            "phase": "sast_extract",
            "status": "start",
            "message": f"Extracting source archive: {archive_name}",
        })
        _safe_unzip(archive_path, tmpdir)
        root = Path(tmpdir).resolve()

        # ── Build tool executor ────────────────────────────────────────────────
        tool_executor = _make_tool_executor(sast_run_id, root, run.collection_id)
        initial_message = _build_initial_message(coll, endpoints, archive_name)

        # ── Configure LLM context tracking ────────────────────────────────────
        llm_svc.set_run_context(
            sast_run_id,
            lambda evt: events_svc.emit(sast_run_id, evt),
        )

        events_svc.emit(sast_run_id, {
            "type": "agent_status",
            "agent_id": "sast-scanner",
            "role": "SAST Analyst",
            "status": "active",
            "current_task": "Starting static analysis…",
            "outcome": None,
            "_persist": True,
        })

        def _stop_check() -> bool:
            return sast_run_id in _sast_stop_requested

        # ── Run the agentic exploration loop ──────────────────────────────────
        summary = await llm_svc.thinking_agentic_loop(
            llm_cfg_obj,
            system_message=SAST_SYSTEM_PROMPT,
            initial_user_message=initial_message,
            tool_executor=tool_executor,
            emit_fn=lambda evt: events_svc.emit(sast_run_id, evt),
            stop_check=_stop_check,
            tools=SAST_TOOLS,
        )

        # ── Leads already persisted inline during filter_lead calls. ─────────
        # Count what's now in the DB for this run (source of truth).
        leads_count = _count_persisted_leads(sast_run_id)
        events_svc.emit(sast_run_id, {
            "type": "scanner_phase",
            "phase": "sast_complete",
            "status": "complete",
            "message": (
                f"SAST analysis complete. {leads_count} lead(s) recorded "
                f"({len(_candidates.get(sast_run_id, [])) - leads_count} discarded). {summary}"
            ),
        })
        events_svc.emit(sast_run_id, {
            "type": "agent_status",
            "agent_id": "sast-scanner",
            "role": "SAST Analyst",
            "status": "complete",
            "current_task": "Analysis complete",
            "outcome": f"{leads_count} lead(s) recorded",
            "_persist": True,
        })

        with Session(get_engine()) as s:
            r = s.get(SastRun, sast_run_id)
            if r is not None and r.status == "scanning":
                r.status = "completed"
                r.leads_count = leads_count
                r.completed_at = datetime.now(_UTC)
                r.updated_at = datetime.now(_UTC)
                s.add(r)
                s.commit()

    except asyncio.CancelledError:
        log.info("SAST scan cancelled: sast_run_id=%s", sast_run_id)
        # Flush any write_lead candidates that never got a filter_lead call.
        if run is not None:
            flushed = _flush_unfiltered_candidates(sast_run_id, run.collection_id)
            total = _count_persisted_leads(sast_run_id)
            with Session(get_engine()) as s:
                r = s.get(SastRun, sast_run_id)
                if r is not None:
                    r.leads_count = total
                    s.add(r)
                    s.commit()
        else:
            flushed, total = 0, 0
        _update_sast_run_status(sast_run_id, "cancelled")
        events_svc.emit(sast_run_id, {
            "type": "scanner_phase",
            "phase": "sast_stopped",
            "status": "warning",
            "message": f"SAST scan stopped. {total} lead(s) preserved ({flushed} unscored).",
        })
        events_svc.emit(sast_run_id, {
            "type": "agent_status",
            "agent_id": "sast-scanner",
            "role": "SAST Analyst",
            "status": "stopped",
            "current_task": "Scan stopped",
            "outcome": "cancelled",
            "_persist": True,
        })
    except Exception as exc:
        log.exception("SAST scan error: sast_run_id=%s", sast_run_id)
        # Flush any candidates recorded before the failure.
        if run is not None:
            try:
                flushed = _flush_unfiltered_candidates(sast_run_id, run.collection_id)
                total = _count_persisted_leads(sast_run_id)
                with Session(get_engine()) as s:
                    r = s.get(SastRun, sast_run_id)
                    if r is not None:
                        r.leads_count = total
                        s.add(r)
                        s.commit()
            except Exception:
                pass
        _update_sast_run_status(sast_run_id, "failed", str(exc))
        events_svc.emit(sast_run_id, {
            "type": "scanner_phase",
            "phase": "sast_stopped",
            "status": "error",
            "message": f"SAST scan failed: {exc}",
        })
        events_svc.emit(sast_run_id, {
            "type": "agent_status",
            "agent_id": "sast-scanner",
            "role": "SAST Analyst",
            "status": "failed",
            "current_task": "Scan failed",
            "outcome": str(exc),
            "_persist": True,
        })
    finally:
        _sast_tasks.pop(sast_run_id, None)
        _sast_stop_requested.discard(sast_run_id)
        _candidates.pop(sast_run_id, None)
        _persisted.pop(sast_run_id, None)
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

    Pass ``collection_id`` + ``document_id`` for an API-style run, or
    ``source_archive_path`` + ``source_filename`` for a standalone run.
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


async def start_sast_scan(sast_run_id: int) -> None:
    """Start a background SAST scan task for an existing SastRun."""
    if sast_run_id in _sast_tasks:
        log.info("start_sast_scan: already running for sast_run_id=%s", sast_run_id)
        return

    log.info("start_sast_scan: sast_run_id=%s", sast_run_id)

    # Tag every event this run emits as run_kind='sast'.  Run ids collide across
    # web / api / sast, so the scope is authoritative.  This also overrides any
    # surrounding 'api' scope when run as an API scan's SAST pre-phase, since the
    # task created below snapshots this 'sast' context.
    with events_svc.run_kind_scope("sast"):
        with Session(get_engine()) as s:
            run = s.get(SastRun, sast_run_id)
            if run is None:
                raise ValueError(f"SastRun {sast_run_id} not found")
            run.status = "scanning"
            run.started_at = run.started_at or datetime.now(_UTC)
            run.updated_at = datetime.now(_UTC)
            s.add(run)
            s.commit()

        events_svc.emit(sast_run_id, {
            "type": "agent_status",
            "agent_id": "sast-scanner",
            "role": "SAST Analyst",
            "status": "active",
            "current_task": "SAST scan starting…",
            "outcome": None,
            "_persist": True,
        })

        task = asyncio.create_task(
            _sast_scan_task(sast_run_id),
            name=f"sast-scan-{sast_run_id}",
        )
        _sast_tasks[sast_run_id] = task


async def run_sast_scan(sast_run_id: int) -> None:
    """Start and AWAIT the SAST scan to completion.

    Used by the API scan pre-phase — the caller awaits this directly so leads
    are ready before the dynamic loop starts.  Failures are swallowed so the
    dynamic scan always proceeds regardless.
    """
    await start_sast_scan(sast_run_id)
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
            events_svc.emit(sast_run_id, {
                "type": "agent_status",
                "agent_id": "sast-scanner",
                "role": "SAST Analyst",
                "status": "idle",
                "current_task": "Scan stopped",
                "outcome": "stopped",
                "_persist": True,
            })
        return True
    return False


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
