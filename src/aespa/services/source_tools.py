"""Shared, bounded source archive and file inspection tools for SAST scans."""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import re
import stat
import zipfile
from pathlib import Path

from aespa.models import SastEvidenceReceipt
from aespa.services import events as events_svc
from aespa.services import sast_workprogram as workprogram_svc

log = logging.getLogger(__name__)

_READ_FILE_MAX_CHARS = 20_000
_GREP_MAX_RESULTS = 200
_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_ARCHIVE_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
_MAX_ARCHIVE_ENTRY_BYTES = 50 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 1_000
_MAX_INSPECT_FILE_BYTES = 10 * 1024 * 1024


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
    ".vb": "Visual Basic",
    ".cshtml": "Razor",
    ".razor": "Razor",
    ".aspx": "ASP.NET Web Forms",
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


# Stable public API for other source-analysis services.
safe_unzip = _safe_unzip
jail = _jail
list_files = _tool_list_files
glob_files = _tool_glob
grep = _tool_grep


def read_file(
    root: Path,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    return _tool_read_file(root, path, start_line, end_line)
