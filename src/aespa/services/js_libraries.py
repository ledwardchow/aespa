"""Deterministic detection of outdated client-side JavaScript libraries.

Library versions are read from script URLs, file names, file contents, and
(for live pages) JavaScript globals, then compared against a bundled list of
known-vulnerable version ranges. The list uses the Retire.js repository
format, so ``data/js_library_signatures.json`` can be replaced with the full
Retire.js repository without code changes.

Both the dynamic scanner (captured script responses) and SAST (vendored
``.js`` files and npm/bower manifests) use this module so a library version is
judged the same way everywhere.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

log = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).with_name("data") / "js_library_signatures.json"
_VERSION_TOKEN = "§§version§§"
_VERSION_PATTERN = r"[0-9][0-9.a-z_\-]+"
_CLEAN_VERSION = re.compile(
    r"\d+(?:\.\d+)*(?:-(?:alpha|beta|rc|pre|b)[0-9.]*)?", re.IGNORECASE
)
_MAX_CONTENT_CHARS = 3_000_000
_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

# Detection methods, most reliable first.
METHOD_RUNTIME = "runtime"
METHOD_CONTENT = "file content"
METHOD_FILENAME = "file name"
METHOD_URI = "URL"
METHOD_MANIFEST = "dependency manifest"


@dataclass(frozen=True)
class Detection:
    library: str
    version: str
    method: str
    source: str
    evidence: str = ""


@dataclass
class LibraryReport:
    """One library version and every place it was seen."""

    library: str
    display: str
    version: str
    detections: list[Detection] = field(default_factory=list)
    vulnerabilities: list[dict[str, Any]] = field(default_factory=list)

    @property
    def severity(self) -> str:
        return max(
            (str(v.get("severity") or "medium").lower() for v in self.vulnerabilities),
            key=lambda s: _SEVERITY_RANK.get(s, 2),
            default="none",
        )

    @property
    def identifiers(self) -> list[str]:
        seen: list[str] = []
        for vuln in self.vulnerabilities:
            for ident in _vuln_identifiers(vuln):
                if ident not in seen:
                    seen.append(ident)
        return seen

    @property
    def fixed_version(self) -> str | None:
        """Lowest version that clears every matched issue, if one exists."""
        bounds = [v.get("below") for v in self.vulnerabilities]
        if not bounds or any(not b for b in bounds):
            return None
        best = max(bounds, key=_version_key)
        # Ranges that never close (e.g. end-of-life major versions) have no fix.
        if any(_no_fixed_release(v) for v in self.vulnerabilities):
            return None
        return str(best)

    @property
    def sources(self) -> list[str]:
        out: list[str] = []
        for det in self.detections:
            if det.source not in out:
                out.append(det.source)
        return out

    @property
    def methods(self) -> list[str]:
        out: list[str] = []
        for det in self.detections:
            if det.method not in out:
                out.append(det.method)
        return out


# ── Repository loading ───────────────────────────────────────────────────────


@lru_cache(maxsize=4)
def load_repository(path: str | None = None) -> dict[str, dict[str, Any]]:
    target = Path(path) if path else _DATA_PATH
    try:
        raw = json.loads(target.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("JS library signatures unavailable (%s): %s", target, exc)
        return {}
    return {
        name: entry
        for name, entry in raw.items()
        if isinstance(entry, dict) and not name.startswith("_")
    }


def _compile(pattern: str) -> re.Pattern[str] | None:
    try:
        return re.compile(pattern.replace(_VERSION_TOKEN, f"(?P<v>{_VERSION_PATTERN})"))
    except re.error:
        # Retire.js patterns are written for JavaScript; skip the rare one that
        # Python cannot compile rather than failing the whole check.
        return None


@lru_cache(maxsize=4)
def _extractors(path: str | None = None) -> dict[str, list[tuple[str, re.Pattern]]]:
    out: dict[str, list[tuple[str, re.Pattern]]] = {
        "filename": [],
        "uri": [],
        "filecontent": [],
    }
    for library, entry in load_repository(path).items():
        extractors = entry.get("extractors") or {}
        for kind in out:
            for pattern in extractors.get(kind) or []:
                if _VERSION_TOKEN not in str(pattern):
                    continue
                compiled = _compile(str(pattern))
                if compiled is not None:
                    out[kind].append((library, compiled))
    return out


def display_name(library: str, path: str | None = None) -> str:
    entry = load_repository(path).get(library) or {}
    return str(entry.get("display") or library)


def library_for_package(package: str, path: str | None = None) -> str | None:
    """Map an npm/bower package name to a library key, if it is tracked."""
    name = str(package or "").strip().casefold()
    if not name:
        return None
    for library, entry in load_repository(path).items():
        if (
            name == library.casefold()
            or name == str(entry.get("npmname") or "").casefold()
        ):
            return library
    return None


def runtime_probes(path: str | None = None) -> list[tuple[str, str]]:
    """JavaScript expressions that return a library's version on a live page."""
    probes = []
    for library, entry in load_repository(path).items():
        for expr in (entry.get("extractors") or {}).get("func") or []:
            if isinstance(expr, str) and expr.strip():
                probes.append((library, expr))
    return probes


# ── Version handling ─────────────────────────────────────────────────────────


def clean_version(value: object) -> str | None:
    """Normalize ``1.12.4.min`` / ``v3.4.1`` / ``^2.2.0`` to a comparable version."""
    match = _CLEAN_VERSION.search(str(value or ""))
    if not match:
        return None
    version = match.group().rstrip(".")
    return version or None


def _version_key(value: object) -> tuple:
    text = str(value or "").strip().lower()
    main, _, pre = text.partition("-")
    numbers = tuple(int(p) if p.isdigit() else 0 for p in main.split(".") if p != "")
    numbers = numbers + (0,) * (6 - len(numbers))
    # A prerelease sorts below the matching release.
    return numbers + ((0, pre) if pre else (1, ""))


def compare_versions(left: object, right: object) -> int:
    a, b = _version_key(left), _version_key(right)
    return (a > b) - (a < b)


def _is_affected(version: str, vuln: dict[str, Any]) -> bool:
    lower = vuln.get("atOrAbove")
    upper = vuln.get("below")
    if lower and compare_versions(version, lower) < 0:
        return False
    if upper and compare_versions(version, upper) >= 0:
        return False
    return bool(lower or upper)


def _no_fixed_release(vuln: dict[str, Any]) -> bool:
    summary = str((vuln.get("identifiers") or {}).get("summary") or "").lower()
    return "no fixed release" in summary or "end of life" in summary


def _vuln_identifiers(vuln: dict[str, Any]) -> list[str]:
    identifiers = vuln.get("identifiers") or {}
    out: list[str] = []
    for key in ("CVE", "GHSA", "githubID", "issue", "bug"):
        value = identifiers.get(key)
        values = value if isinstance(value, list) else [value] if value else []
        out.extend(str(v) for v in values if v)
    return out


def vulnerabilities_for(
    library: str, version: str, path: str | None = None
) -> list[dict[str, Any]]:
    entry = load_repository(path).get(library) or {}
    return [
        vuln
        for vuln in entry.get("vulnerabilities") or []
        if isinstance(vuln, dict) and _is_affected(version, vuln)
    ]


# ── Detection ────────────────────────────────────────────────────────────────


def _match_all(
    kind: str, text: str, method: str, source: str, path: str | None
) -> list[Detection]:
    found: list[Detection] = []
    for library, pattern in _extractors(path)[kind]:
        match = pattern.search(text)
        if not match:
            continue
        version = clean_version(match.group("v"))
        if version:
            found.append(
                Detection(library, version, method, source, match.group(0)[:200])
            )
    return found


def detect_in_url(url: str, path: str | None = None) -> list[Detection]:
    parsed = urlparse(url)
    location = unquote(parsed.path or "")
    with_query = f"{location}?{parsed.query}" if parsed.query else location
    filename = location.rsplit("/", 1)[-1]
    found = _match_all("filename", filename, METHOD_FILENAME, url, path)
    found.extend(_match_all("uri", with_query, METHOD_URI, url, path))
    return found


def detect_in_content(
    content: str, source: str, path: str | None = None
) -> list[Detection]:
    if not content:
        return []
    return _match_all(
        "filecontent", content[:_MAX_CONTENT_CHARS], METHOD_CONTENT, source, path
    )


def detect(
    url: str, content: str | None = None, path: str | None = None
) -> list[Detection]:
    """Detect libraries in one script.

    File content is trusted over the URL: when content names a library, URL
    guesses for that same library are dropped (a ``/1.0/jquery.js`` path may be
    an app release number rather than the jQuery version).
    """
    by_content = detect_in_content(content or "", url, path)
    content_libraries = {d.library for d in by_content}
    by_url = [d for d in detect_in_url(url, path) if d.library not in content_libraries]
    return by_content + by_url


def build_reports(
    detections: list[Detection], path: str | None = None
) -> list[LibraryReport]:
    """Group detections by library and version and attach matched issues."""
    reports: dict[tuple[str, str], LibraryReport] = {}
    for det in detections:
        key = (det.library, det.version)
        report = reports.get(key)
        if report is None:
            report = LibraryReport(
                library=det.library,
                display=display_name(det.library, path),
                version=det.version,
                vulnerabilities=vulnerabilities_for(det.library, det.version, path),
            )
            reports[key] = report
        if det not in report.detections:
            report.detections.append(det)
    return sorted(
        reports.values(),
        key=lambda r: (-_SEVERITY_RANK.get(r.severity, 0), r.display, r.version),
    )


def vulnerable_reports(
    detections: list[Detection], path: str | None = None
) -> list[LibraryReport]:
    return [r for r in build_reports(detections, path) if r.vulnerabilities]


def describe_vulnerabilities(report: LibraryReport) -> list[str]:
    lines = []
    for vuln in report.vulnerabilities:
        identifiers = ", ".join(_vuln_identifiers(vuln)) or "No identifier"
        summary = str((vuln.get("identifiers") or {}).get("summary") or "").strip()
        bounds = []
        if vuln.get("atOrAbove"):
            bounds.append(f">= {vuln['atOrAbove']}")
        if vuln.get("below"):
            bounds.append(f"< {vuln['below']}")
        affected = f" (affects {' and '.join(bounds)})" if bounds else ""
        severity = str(vuln.get("severity") or "medium").lower()
        lines.append(
            f"{identifiers} [{severity}]: {summary or 'Known issue'}{affected}"
        )
    return lines


# ── Source trees (SAST) ──────────────────────────────────────────────────────

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
_MAX_TREE_FILES = 5_000


def scan_source_tree(root: Path, path: str | None = None) -> list[Detection]:
    """Detect vendored browser libraries committed to a source tree.

    ``node_modules`` is skipped: installed packages are covered by lockfiles
    and would otherwise flood the results with transitive copies.
    """
    detections: list[Detection] = []
    seen = 0
    for file_path in sorted(root.rglob("*.js")):
        if seen >= _MAX_TREE_FILES:
            break
        try:
            relative = file_path.relative_to(root)
        except ValueError:
            continue
        if (
            any(part in _SKIP_DIRS for part in relative.parts)
            or not file_path.is_file()
        ):
            continue
        seen += 1
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as handle:
                content = handle.read(_MAX_CONTENT_CHARS)
        except OSError:
            continue
        rel = relative.as_posix()
        by_content = detect_in_content(content, rel, path)
        if by_content:
            detections.extend(by_content)
            continue
        detections.extend(
            _match_all("filename", file_path.name, METHOD_FILENAME, rel, path)
        )
    return detections
