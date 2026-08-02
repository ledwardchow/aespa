"""Deterministic, bounded extraction of compact interface facts from a SAST
source tree.

Every campaign source repository is scanned separately (see
``services/sast_scanner.py``). Alongside the usual leads, this module derives
a short, structured summary of how the code talks to the outside world:
routes/UI paths it serves, HTTP calls it makes, auth/session boundaries,
message queues/topics, shared datastores, and framework markers — each with a
``file:line`` evidence pointer.

This is intentionally regex-based rather than another LLM turn: it is cheap,
deterministic, and bounded, and it only needs to be "good enough" to seed
cross-repository correlation (``services/correlation.py``), not to replace
the agentic SAST analysis itself.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

# Bound the total work done per SAST run regardless of repository size.
_MAX_FILES_SCANNED = 4000
_MAX_FILE_BYTES = 1_000_000
_MAX_FACTS = 500

_SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".cs",
}

_FRAMEWORK_MARKERS = {
    "requirements.txt": {
        "flask": "Flask",
        "fastapi": "FastAPI",
        "django": "Django",
    },
    "pyproject.toml": {
        "flask": "Flask",
        "fastapi": "FastAPI",
        "django": "Django",
    },
    "package.json": {
        "express": "Express",
        "next": "Next.js",
        "react": "React",
        "@nestjs/core": "NestJS",
    },
    "go.mod": {
        "gin-gonic/gin": "Gin",
        "labstack/echo": "Echo",
    },
}

# ── Route definitions ────────────────────────────────────────────────────────
_ROUTE_PATTERNS = [
    # Flask/FastAPI/Django-ish decorators: @app.route("/x"), @router.get("/x"),
    # @app.route("/x", methods=["POST"])
    re.compile(
        r"@(?:\w+\.)?(?P<method>get|post|put|patch|delete|route)\(\s*"
        r"[\"'](?P<path>/[^\"']*)[\"']"
        r"(?:[^)]*?methods\s*=\s*\[\s*[\"'](?P<methods_list>\w+)[\"'])?",
        re.IGNORECASE,
    ),
    # Express/Fastify style: app.get('/x', ...), router.post("/x", ...)
    re.compile(
        r"\b\w+\.(?P<method>get|post|put|patch|delete)\(\s*"
        r"[\"'](?P<path>/[^\"']*)[\"']"
    ),
]

# ── Outbound HTTP calls ───────────────────────────────────────────────────────
_HTTP_CALL_PATTERNS = [
    re.compile(
        r"\b(?:requests|httpx|http)\.(?P<method>get|post|put|patch|delete)\(\s*"
        r"[\"'](?P<url>https?://[^\"']+|/[^\"']*)[\"']",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:axios|fetch)\(\s*[\"'](?P<url>https?://[^\"']+|/[^\"']*)[\"']"
        r"(?:\s*,\s*\{[^}]*method\s*:\s*[\"'](?P<method>\w+)[\"'])?",
        re.IGNORECASE,
    ),
]

_AUTH_MARKERS = re.compile(
    r"login_required|requires?_auth|authenticate|verify_jwt|Depends\("
    r"\s*get_current_user|passport\.authenticate|@PreAuthorize|IsAuthenticated",
    re.IGNORECASE,
)

_QUEUE_PATTERNS = [
    re.compile(
        r"\b(?:kafka|pika|amqp|sqs|rabbitmq)\w*"
        r".{0,80}?[\"']([\w./-]+)[\"']",
        re.IGNORECASE | re.DOTALL,
    ),
]

_DATASTORE_PATTERNS = [
    re.compile(r"\bredis\.Redis\(", re.IGNORECASE),
    re.compile(r"\bpsycopg2\.connect\(", re.IGNORECASE),
    re.compile(r"\bpymongo\.MongoClient\(", re.IGNORECASE),
    re.compile(r"\bcreate_engine\(", re.IGNORECASE),
    re.compile(r"\b(DATABASE_URL|MONGO_URI|REDIS_URL)\b"),
]


def _fingerprint(*parts: str) -> str:
    canonical = "|".join(p.strip().lower() for p in parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def interface_fact_fingerprint(
    *,
    fact_type: str,
    method: str | None,
    path: str | None,
    host: str | None,
    name: str | None,
) -> str:
    """Fingerprint interface identity without tying it to one evidence line."""
    raw_path = (path or "").strip().lower()
    if "://" in raw_path:
        raw_path = urlparse(raw_path).path
    raw_path = raw_path.split("?", 1)[0].rstrip("/") or "/"
    raw_path = re.sub(r"\{[^}]+\}", "{}", raw_path)
    raw_path = re.sub(r"/:[\w-]+", "/{}", raw_path)
    canonical = "|".join(
        (
            (fact_type or "").strip().lower(),
            (method or "").strip().lower(),
            re.sub(r"\s+", " ", raw_path),
            (host or "").strip().lower(),
            (name or "").strip().lower(),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _iter_source_files(root: Path):
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for filename in sorted(filenames):
            if scanned >= _MAX_FILES_SCANNED:
                return
            path = Path(dirpath) / filename
            if not path.is_file() or path.is_symlink():
                continue
            scanned += 1
            yield path


def _detect_framework_facts(root: Path) -> list[dict]:
    facts: list[dict] = []
    for marker_file, keywords in _FRAMEWORK_MARKERS.items():
        candidate = root / marker_file
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text.lower()
        for keyword, framework in keywords.items():
            if keyword in lowered:
                facts.append(
                    {
                        "fact_type": "framework",
                        "method": None,
                        "path": None,
                        "host": None,
                        "name": framework,
                        "detail": {"marker_file": marker_file},
                        "evidence_location": marker_file,
                    }
                )
    return facts


def _host_from_url(url: str) -> str | None:
    match = re.match(r"https?://([^/]+)", url)
    return match.group(1) if match else None


def extract_component_facts(root: Path) -> list[dict]:
    """Return a bounded list of deterministic interface facts for a source tree.

    Each fact is a plain dict shaped like the ``ComponentFact`` model's
    writable columns (``fact_type``, ``method``, ``path``, ``host``, ``name``,
    ``detail`` (dict), ``evidence_location``); the caller adds ``sast_run_id``
    / ``component_id`` / ``fingerprint`` before persisting.
    """
    facts: list[dict] = list(_detect_framework_facts(root))
    seen_fingerprints: set[str] = {
        interface_fact_fingerprint(
            fact_type=f["fact_type"],
            method=f.get("method"),
            path=f.get("path"),
            host=f.get("host"),
            name=f.get("name"),
        )
        for f in facts
    }

    def _add(fact: dict) -> None:
        fp = interface_fact_fingerprint(
            fact_type=fact["fact_type"],
            method=fact.get("method"),
            path=fact.get("path"),
            host=fact.get("host"),
            name=fact.get("name"),
        )
        if fp in seen_fingerprints:
            return
        seen_fingerprints.add(fp)
        facts.append(fact)

    for path in _iter_source_files(root):
        if len(facts) >= _MAX_FACTS:
            break
        if path.suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()

        for line_no, line in enumerate(text.splitlines(), start=1):
            if len(facts) >= _MAX_FACTS:
                break
            location = f"{rel}:{line_no}"

            for pattern in _ROUTE_PATTERNS:
                m = pattern.search(line)
                if m:
                    method = (m.group("method") or "route").upper()
                    if method == "ROUTE":
                        methods_list = m.groupdict().get("methods_list")
                        method = methods_list.upper() if methods_list else "GET"
                    _add(
                        {
                            "fact_type": "route",
                            "method": method,
                            "path": m.group("path"),
                            "host": None,
                            "name": None,
                            "detail": {},
                            "evidence_location": location,
                        }
                    )
                    break

            for pattern in _HTTP_CALL_PATTERNS:
                m = pattern.search(line)
                if m:
                    url = m.group("url")
                    method = (m.groupdict().get("method") or "GET").upper()
                    _add(
                        {
                            "fact_type": "http_call",
                            "method": method,
                            "path": url,
                            "host": _host_from_url(url),
                            "name": None,
                            "detail": {},
                            "evidence_location": location,
                        }
                    )
                    break

            if _AUTH_MARKERS.search(line):
                _add(
                    {
                        "fact_type": "auth_boundary",
                        "method": None,
                        "path": None,
                        "host": None,
                        "name": _AUTH_MARKERS.search(line).group(0),
                        "detail": {},
                        "evidence_location": location,
                    }
                )

            for pattern in _QUEUE_PATTERNS:
                m = pattern.search(line)
                if m:
                    _add(
                        {
                            "fact_type": "queue",
                            "method": None,
                            "path": None,
                            "host": None,
                            "name": m.group(1),
                            "detail": {},
                            "evidence_location": location,
                        }
                    )
                    break

            for pattern in _DATASTORE_PATTERNS:
                m = pattern.search(line)
                if m:
                    _add(
                        {
                            "fact_type": "datastore",
                            "method": None,
                            "path": None,
                            "host": None,
                            "name": m.group(0).rstrip("("),
                            "detail": {},
                            "evidence_location": location,
                        }
                    )
                    break

    return facts[:_MAX_FACTS]


def persist_component_facts(sast_run_id: int, root: Path) -> int:
    """Extract and upsert deterministic ``ComponentFact`` rows for one run.

    Looks up the owning ``ApplicationComponent`` via ``CampaignSourceMember``
    (``component_id`` stays ``NULL`` for a standalone SAST run — this never
    requires the run to know about campaigns itself). Idempotent per run: a
    deterministic facts while preserving facts recorded by the LLM mapper.
    Returns the number of deterministic facts persisted. Extraction failures
    remain non-fatal to the vulnerability scan.
    """
    from sqlmodel import Session, select

    from aespa.db import get_engine
    from aespa.models import CampaignSourceMember, ComponentFact

    try:
        raw_facts = extract_component_facts(root)
    except Exception:
        return 0

    with Session(get_engine()) as session:
        membership = session.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.sast_run_id == sast_run_id
            )
        ).first()
        component_id = membership.component_id if membership else None

        existing_rows = list(
            session.exec(
                select(ComponentFact).where(ComponentFact.sast_run_id == sast_run_id)
            ).all()
        )
        existing_by_fingerprint = {row.fingerprint: row for row in existing_rows}
        desired: dict[str, dict] = {}
        for raw in raw_facts:
            fp = interface_fact_fingerprint(
                fact_type=raw["fact_type"],
                method=raw.get("method"),
                path=raw.get("path"),
                host=raw.get("host"),
                name=raw.get("name"),
            )
            desired[fp] = raw

        for existing in existing_rows:
            try:
                detail = json.loads(existing.detail_json or "{}")
            except (TypeError, ValueError):
                detail = {}
            if "llm" not in str(detail.get("origin") or "").lower() and (
                existing.fingerprint not in desired
            ):
                session.delete(existing)

        for fp, raw in desired.items():
            existing = existing_by_fingerprint.get(fp)
            if existing is not None:
                try:
                    detail = json.loads(existing.detail_json or "{}")
                except (TypeError, ValueError):
                    detail = {}
                if "llm" in str(detail.get("origin") or "").lower():
                    continue
                existing.component_id = component_id
                existing.fact_type = raw["fact_type"]
                existing.method = raw.get("method")
                existing.path = raw.get("path")
                existing.host = raw.get("host")
                existing.name = raw.get("name")
                existing.detail_json = json.dumps(
                    {"origin": "deterministic", **(raw.get("detail") or {})}
                )
                existing.evidence_location = raw["evidence_location"]
                existing.fingerprint = fp
                session.add(existing)
                continue
            session.add(
                ComponentFact(
                    sast_run_id=sast_run_id,
                    component_id=component_id,
                    fact_type=raw["fact_type"],
                    method=raw.get("method"),
                    path=raw.get("path"),
                    host=raw.get("host"),
                    name=raw.get("name"),
                    detail_json=json.dumps(
                        {"origin": "deterministic", **(raw.get("detail") or {})}
                    ),
                    evidence_location=raw["evidence_location"],
                    fingerprint=fp,
                )
            )
        session.commit()
    return len(raw_facts)
