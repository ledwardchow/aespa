"""Deterministic detection of outdated client-side JavaScript libraries.

Library versions are read from script URLs, file names, file contents, file
hashes, and (for live pages) JavaScript globals, then compared against the
Retire.js vulnerable-library list (see ``services/retire_repository.py`` for
where that list comes from).

Both the dynamic scanner (captured script responses) and SAST (vendored
``.js`` files and npm/bower manifests) use this module so a library version is
judged the same way everywhere.

Retire.js ``ast`` extractors need a JavaScript parser and are not used; every
library also has pattern-based extractors.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from aespa.services import retire_repository

log = logging.getLogger(__name__)

_VERSION_TOKEN = "§§version§§"
_VERSION_PATTERN = r"[0-9][0-9.a-z_\-]+"
_CLEAN_VERSION = re.compile(
    r"\d+(?:\.\d+)*(?:-(?:alpha|beta|rc|pre|b)[0-9.]*)?", re.IGNORECASE
)
_MAX_CONTENT_CHARS = 3_000_000
_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
# Retire.js marks ranges with no fixed release with a "below" like 999.999.999.
_NO_FIX_MAJOR = 999
_SKIPPED_ENTRIES = {"retire-example", "dont check"}
_NODE_ONLY_FUNC = re.compile(r"\brequire\s*\(|\bmodule\.")

# Friendlier names for finding titles. Unlisted libraries use the Retire.js key.
_DISPLAY_NAMES = {
    "jquery": "jQuery",
    "jquery-migrate": "jQuery Migrate",
    "jquery-validation": "jQuery Validation",
    "jquery-mobile": "jQuery Mobile",
    "jquery-ui": "jQuery UI",
    "jquery-ui-dialog": "jQuery UI",
    "jquery-ui-autocomplete": "jQuery UI",
    "jquery-ui-tooltip": "jQuery UI",
    "jquery.datatables": "DataTables",
    "angularjs": "AngularJS",
    "@angular/core": "Angular",
    "backbone.js": "Backbone.js",
    "bootstrap": "Bootstrap",
    "bootstrap-select": "bootstrap-select",
    "ckeditor": "CKEditor",
    "ckeditor5": "CKEditor 5",
    "dojo": "Dojo",
    "ember": "Ember",
    "handlebars": "Handlebars",
    "highcharts": "Highcharts",
    "knockout": "Knockout",
    "lodash": "Lodash",
    "moment.js": "Moment.js",
    "mustache.js": "Mustache.js",
    "nextjs": "Next.js",
    "prototypejs": "Prototype",
    "react": "React",
    "react-dom": "React DOM",
    "select2": "Select2",
    "tinyMCE": "TinyMCE",
    "underscore.js": "Underscore.js",
    "vue": "Vue.js",
}

# Detection methods, most reliable first.
METHOD_RUNTIME = "runtime"
METHOD_HASH = "file hash"
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
class Repository:
    """A loaded Retire.js list with its patterns compiled once."""

    path: str
    libraries: dict[str, dict[str, Any]]
    patterns: dict[str, list[tuple[str, re.Pattern[str]]]]
    replacers: list[tuple[str, re.Pattern[str], str]]
    hashes: dict[str, tuple[str, str]]
    ignored_uris: list[re.Pattern[str]]
    skipped_patterns: int = 0
    total_patterns: int = 0

    def family(self, library: str) -> str:
        """Libraries that ship in one package (jQuery UI widgets) share a family."""
        npm = _names(self.libraries.get(library, {}).get("npmname"))
        return npm[0].casefold() if npm else library.casefold()


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
        if not bounds or any(not b or _no_fixed_release(b) for b in bounds):
            return None
        return str(max(bounds, key=_version_key))

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

_cache: dict[tuple[str, int], Repository] = {}


def _names(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)] if value else []


def _compile(pattern: str, *, named: bool = True) -> re.Pattern[str] | None:
    group = f"(?P<v>{_VERSION_PATTERN})" if named else f"({_VERSION_PATTERN})"
    try:
        return re.compile(pattern.replace(_VERSION_TOKEN, group))
    except re.error:
        # Retire.js patterns are written for JavaScript; skip the rare one that
        # Python cannot compile rather than failing the whole check.
        return None


def _parse_replacer(spec: str) -> tuple[re.Pattern[str], str] | None:
    """Parse a ``/regex/replacement/`` filecontentreplace entry."""
    if not spec.startswith("/") or not spec.endswith("/") or len(spec) < 3:
        return None
    body = spec[1:-1]
    pattern, sep, replacement = body.rpartition("/")
    if not sep:
        return None
    compiled = _compile(pattern, named=False)
    return (compiled, replacement) if compiled else None


def _build(path: Path) -> Repository:
    try:
        raw = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("Retire.js list unavailable (%s): %s", path, exc)
        raw = {}
    repo = Repository(
        path=str(path),
        libraries={},
        patterns={"filename": [], "uri": [], "filecontent": []},
        replacers=[],
        hashes={},
        ignored_uris=[],
    )
    for name, entry in raw.items():
        if not isinstance(entry, dict) or name.startswith("_"):
            continue
        extractors = entry.get("extractors") or {}
        if name == "dont check":
            for pattern in extractors.get("uri") or []:
                with_version = _compile(str(pattern))
                if with_version is not None:
                    repo.ignored_uris.append(with_version)
            continue
        if name in _SKIPPED_ENTRIES:
            continue
        repo.libraries[name] = entry
        for kind in repo.patterns:
            for pattern in extractors.get(kind) or []:
                if _VERSION_TOKEN not in str(pattern):
                    continue
                repo.total_patterns += 1
                compiled = _compile(str(pattern))
                if compiled is None:
                    repo.skipped_patterns += 1
                else:
                    repo.patterns[kind].append((name, compiled))
        for spec in extractors.get("filecontentreplace") or []:
            repo.total_patterns += 1
            parsed = _parse_replacer(str(spec))
            if parsed is None:
                repo.skipped_patterns += 1
            else:
                repo.replacers.append((name, *parsed))
        for digest, version in (extractors.get("hashes") or {}).items():
            repo.hashes[str(digest).lower()] = (name, str(version))
    return repo


def get_repository(path: str | Path | None = None) -> Repository:
    """Load (and cache) a repository; reloads when the file changes."""
    target = Path(path) if path else retire_repository.active_path()
    try:
        stamp = target.stat().st_mtime_ns
    except OSError:
        stamp = -1
    key = (str(target), stamp)
    repo = _cache.get(key)
    if repo is None:
        _cache.clear()
        repo = _cache[key] = _build(target)
    return repo


def load_repository(path: str | None = None) -> dict[str, dict[str, Any]]:
    return get_repository(path).libraries


def display_name(library: str, path: str | None = None) -> str:
    return _DISPLAY_NAMES.get(library, library)


def libraries_for_package(package: str, path: str | None = None) -> list[str]:
    """Map an npm/bower package name to every tracked library it contains.

    The ``jquery-ui`` package maps to jQuery UI and its separately tracked
    widgets, so their issues are reported together.
    """
    name = str(package or "").strip().casefold()
    if not name:
        return []
    exact: list[str] = []
    by_npm: list[str] = []
    by_bower: list[str] = []
    for library, entry in get_repository(path).libraries.items():
        if name == library.casefold():
            exact.append(library)
        elif name in (n.casefold() for n in _names(entry.get("npmname"))):
            by_npm.append(library)
        elif name in (n.casefold() for n in _names(entry.get("bowername"))):
            by_bower.append(library)
    found = exact + by_npm
    return found or by_bower


def library_for_package(package: str, path: str | None = None) -> str | None:
    found = libraries_for_package(package, path)
    return found[0] if found else None


def runtime_probes(path: str | None = None) -> list[tuple[str, str]]:
    """JavaScript expressions that return a library's version on a live page."""
    probes = []
    for library, entry in get_repository(path).libraries.items():
        for expr in (entry.get("extractors") or {}).get("func") or []:
            if (
                isinstance(expr, str)
                and expr.strip()
                and not _NODE_ONLY_FUNC.search(expr)
            ):
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


def _no_fixed_release(below: object) -> bool:
    return _version_key(below)[0] >= _NO_FIX_MAJOR


def _is_affected(version: str, vuln: dict[str, Any]) -> bool:
    if version in _names(vuln.get("excludes")):
        return False
    lower = vuln.get("atOrAbove")
    upper = vuln.get("below")
    if lower and compare_versions(version, lower) < 0:
        return False
    if upper and compare_versions(version, upper) >= 0:
        return False
    return bool(lower or upper)


def _vuln_identifiers(vuln: dict[str, Any]) -> list[str]:
    identifiers = vuln.get("identifiers") or {}
    out: list[str] = []
    for key in ("CVE", "GHSA", "githubID", "issue", "bug", "retid"):
        for value in _names(identifiers.get(key)):
            label = f"issue {value}" if key in {"issue", "bug", "retid"} else value
            if label not in out:
                out.append(label)
    return out


def vulnerabilities_for(
    library: str, version: str, path: str | None = None
) -> list[dict[str, Any]]:
    entry = get_repository(path).libraries.get(library) or {}
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
    for library, pattern in get_repository(path).patterns[kind]:
        match = pattern.search(text)
        if not match:
            continue
        version = clean_version(match.group("v"))
        if version:
            found.append(
                Detection(library, version, method, source, match.group(0)[:200])
            )
    return found


def _match_replacers(text: str, source: str, path: str | None) -> list[Detection]:
    found: list[Detection] = []
    for library, pattern, template in get_repository(path).replacers:
        match = pattern.search(text)
        if not match:
            continue

        def _group(ref: re.Match[str]) -> str:
            index = int(ref.group(1))
            return (match.group(index) or "") if index <= pattern.groups else ""

        version = clean_version(re.sub(r"\$(\d+)", _group, template))
        if version:
            found.append(
                Detection(
                    library, version, METHOD_CONTENT, source, match.group(0)[:200]
                )
            )
    return found


def is_ignored(url: str, path: str | None = None) -> bool:
    return any(p.search(url) for p in get_repository(path).ignored_uris)


def detect_in_url(url: str, path: str | None = None) -> list[Detection]:
    if is_ignored(url, path):
        return []
    parsed = urlparse(url)
    location = unquote(parsed.path or "")
    with_query = f"{location}?{parsed.query}" if parsed.query else location
    filename = location.rsplit("/", 1)[-1]
    found = _match_all("filename", filename, METHOD_FILENAME, url, path)
    found.extend(_match_all("uri", with_query, METHOD_URI, url, path))
    return found


def detect_in_content(
    content: str,
    source: str,
    path: str | None = None,
    *,
    raw: bytes | None = None,
) -> list[Detection]:
    """Detect libraries in file content.

    ``raw`` is the complete file; it enables exact hash matches and should be
    passed only when the whole file was read.
    """
    found: list[Detection] = []
    if raw:
        digest = hashlib.sha1(raw).hexdigest()  # noqa: S324 - Retire.js uses SHA-1
        hit = get_repository(path).hashes.get(digest)
        if hit:
            found.append(Detection(hit[0], hit[1], METHOD_HASH, source, digest))
    if content:
        text = content[:_MAX_CONTENT_CHARS]
        found.extend(_match_all("filecontent", text, METHOD_CONTENT, source, path))
        found.extend(_match_replacers(text, source, path))
    return found


def detect(
    url: str, content: str | None = None, path: str | None = None
) -> list[Detection]:
    """Detect libraries in one script.

    File content is trusted over the URL: when content names a library, URL
    guesses for that same library are dropped (a ``/1.0/jquery.js`` path may be
    an app release number rather than the jQuery version).
    """
    if is_ignored(url, path):
        return []
    by_content = detect_in_content(content or "", url, path)
    content_libraries = {d.library for d in by_content}
    by_url = [d for d in detect_in_url(url, path) if d.library not in content_libraries]
    return by_content + by_url


def _dedupe_vulnerabilities(vulns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple] = set()
    out: list[dict[str, Any]] = []
    for vuln in vulns:
        key = tuple(_vuln_identifiers(vuln)) or (
            str((vuln.get("identifiers") or {}).get("summary") or ""),
            vuln.get("atOrAbove"),
            vuln.get("below"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(vuln)
    return out


def build_reports(
    detections: list[Detection], path: str | None = None
) -> list[LibraryReport]:
    """Group detections by library family and version and attach issues."""
    repo = get_repository(path)
    reports: dict[tuple[str, str], LibraryReport] = {}
    members: dict[tuple[str, str], set[str]] = {}
    for det in detections:
        key = (repo.family(det.library), det.version)
        report = reports.get(key)
        if report is None:
            report = LibraryReport(
                library=det.library,
                display=display_name(det.library, path),
                version=det.version,
            )
            reports[key] = report
            members[key] = set()
        if det.library not in members[key]:
            members[key].add(det.library)
            report.vulnerabilities = _dedupe_vulnerabilities(
                report.vulnerabilities
                + vulnerabilities_for(det.library, det.version, path)
            )
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
        if vuln.get("below") and not _no_fixed_release(vuln["below"]):
            bounds.append(f"< {vuln['below']}")
        affected = f" (affects {' and '.join(bounds)})" if bounds else ""
        if vuln.get("below") and _no_fixed_release(vuln["below"]):
            affected += " (no fixed release)"
        severity = str(vuln.get("severity") or "medium").lower()
        lines.append(
            f"{identifiers} [{severity}]: {summary or 'Known issue'}{affected}"
        )
    return lines


def list_status() -> dict[str, Any]:
    """Which Retire.js copy is in use and how much of it is usable."""
    repo = get_repository()
    return {
        **retire_repository.info(),
        "libraries": len(repo.libraries),
        "vulnerabilities": sum(
            len(entry.get("vulnerabilities") or []) for entry in repo.libraries.values()
        ),
        "patterns": repo.total_patterns,
        "skipped_patterns": repo.skipped_patterns,
    }


def source_label() -> str:
    """Which Retire.js copy results came from, for messages and findings."""
    return retire_repository.describe()


# ── Source trees (SAST) ──────────────────────────────────────────────────────

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
_MAX_TREE_FILES = 5_000
TREE_TIME_BUDGET_S = 120.0


def scan_source_tree(
    root: Path, path: str | None = None, *, time_budget_s: float = TREE_TIME_BUDGET_S
) -> list[Detection]:
    """Detect vendored browser libraries committed to a source tree.

    ``node_modules`` is skipped: installed packages are covered by lockfiles
    and would otherwise flood the results with transitive copies. The check
    stops early when it runs past ``time_budget_s``.
    """
    detections: list[Detection] = []
    seen = 0
    deadline = time.monotonic() + time_budget_s
    for file_path in sorted(root.rglob("*.js")):
        if seen >= _MAX_TREE_FILES:
            break
        if time.monotonic() > deadline:
            log.warning(
                "JavaScript library check stopped after %d files (time limit)", seen
            )
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
            with file_path.open("rb") as handle:
                raw = handle.read(_MAX_CONTENT_CHARS + 1)
        except OSError:
            continue
        complete = len(raw) <= _MAX_CONTENT_CHARS
        rel = relative.as_posix()
        by_content = detect_in_content(
            raw.decode("utf-8", errors="replace"),
            rel,
            path,
            raw=raw if complete else None,
        )
        if by_content:
            detections.extend(by_content)
            continue
        detections.extend(
            _match_all("filename", file_path.name, METHOD_FILENAME, rel, path)
        )
    return detections
