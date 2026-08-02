"""Shared path-jailed source inspection helpers.

The SAST scanner owns the bounded implementations today.  This module provides
the stable interface used by other source-analysis agents without duplicating
the security-sensitive limits and path checks.
"""

from __future__ import annotations

from pathlib import Path


def safe_unzip(archive_path: str, target_dir: str) -> None:
    """Extract an archive using the SAST scanner's safe extraction policy."""
    from aespa.services.sast_scanner import _safe_unzip

    _safe_unzip(archive_path, target_dir)


def jail(root: Path, relative_path: str) -> Path:
    """Resolve a relative path below ``root`` or raise ``ValueError``."""
    from aespa.services.sast_scanner import _jail

    return _jail(root, relative_path)


def list_files(root: Path, path: str = "", max_depth: int = 3) -> str:
    from aespa.services.sast_scanner import _tool_list_files

    return _tool_list_files(root, path=path, max_depth=max_depth)


def glob_files(root: Path, pattern: str) -> str:
    from aespa.services.sast_scanner import _tool_glob

    return _tool_glob(root, pattern)


def read_file(
    root: Path,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    from aespa.services.sast_scanner import _tool_read_file

    return _tool_read_file(root, path, start_line, end_line)


def grep(
    root: Path,
    pattern: str,
    path: str = "",
    include_pattern: str = "",
) -> str:
    from aespa.services.sast_scanner import _tool_grep

    return _tool_grep(root, pattern, path=path, include_pattern=include_pattern)
