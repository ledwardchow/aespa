"""Deterministic, framework-neutral SAST attack-surface and work-program state."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    SastEvidenceReceipt,
    SastPartition,
    SastSourceFile,
    SastSurfaceItem,
    SastWorker,
    SastWorkItem,
)

_UTC = timezone.utc
CLASS_GROUPS = ("injection", "access", "logic")
TERMINAL_WORK_STATUSES = {
    "safe",
    "no_match",
    "candidate",
    "design_intent",
    "not_applicable",
}
_MAX_ATLAS_FILE_BYTES = 1_000_000
_MAX_SURFACE_ITEMS = 12_000
_PARTITION_INPUT_LIMIT = 20
_SINK_WORK_LIMIT = 40

_LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C/C++",
    ".cc": "C/C++",
    ".cpp": "C/C++",
    ".h": "C/C++",
    ".hpp": "C/C++",
    ".rs": "Rust",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".graphql": "GraphQL",
    ".proto": "Protocol Buffers",
    ".yaml": "Configuration",
    ".yml": "Configuration",
    ".json": "Configuration",
    ".toml": "Configuration",
    ".xml": "Configuration",
}
_SOURCE_LANGUAGES = {
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Kotlin",
    "Go",
    "Ruby",
    "PHP",
    "C#",
    "C/C++",
    "Rust",
    "Swift",
    "Scala",
    "HTML",
    "Vue",
    "Svelte",
    "Protocol Buffers",
}
_EXCLUDED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "vendors",
    "third_party",
    "third-party",
    "external",
    "deps",
    "dist",
    "build",
    "coverage",
    "target",
    "__pycache__",
    ".venv",
    "venv",
}
_TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__", "fixtures"}
_GENERATED_PARTS = {"generated", "gen", "autogen", "codegen"}
_ASSET_SUFFIXES = {
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".map",
    ".min.js",
    ".min.css",
}
_DOC_SUFFIXES = {".md", ".rst", ".txt", ".adoc"}


@dataclass(frozen=True)
class _Pattern:
    kind: str
    category: str
    name: str
    regex: re.Pattern[str]


def _rx(value: str) -> re.Pattern[str]:
    return re.compile(value, re.IGNORECASE)


_PATTERNS = (
    _Pattern(
        "entrypoint",
        "http",
        "HTTP route",
        _rx(
            r"(?:@\w+\.(?:get|post|put|patch|delete|route)|\b(?:app|router|server)\.(?:get|post|put|patch|delete|use)\s*\()"
        ),
    ),
    _Pattern(
        "entrypoint",
        "http",
        "Annotated HTTP handler",
        _rx(
            r"@(?:RequestMapping|GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|Path)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "http",
        "HTTP handler registration",
        _rx(
            r"\b(?:HandleFunc|handle\s*\(|add_route|register_route|register_rest_route)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "rpc",
        "RPC service method",
        _rx(r"\b(?:grpc|thrift|rpc)\b.*\b(?:handler|service|method|server)\b"),
    ),
    _Pattern(
        "entrypoint",
        "queue",
        "Message consumer",
        _rx(
            r"\b(?:consumer|subscribe|on_message|message_handler|KafkaListener|SqsListener|RabbitListener)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "websocket",
        "WebSocket handler",
        _rx(r"\b(?:websocket|WebSocket|socket\.on|onmessage)\b"),
    ),
    _Pattern(
        "entrypoint",
        "cli",
        "CLI command",
        _rx(
            r"\b(?:argparse|add_argument|process\.argv|cobra\.Command|flag\.(?:String|Int|Bool)|CommandLine\.Command)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "serverless",
        "Serverless handler",
        _rx(
            r"\b(?:lambda_handler|APIGatewayProxyHandler|CloudFunction|FunctionsFramework|event\.Records)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "file",
        "File processor",
        _rx(r"\b(?:multipart|upload|FileUpload|watchdog|fs\.watch|inotify)\b"),
    ),
    _Pattern(
        "entrypoint",
        "job",
        "Scheduled job",
        _rx(r"\b(?:cron|schedule|Scheduled|Celery|sidekiq|background_job)\b"),
    ),
    _Pattern(
        "input",
        "request",
        "Request value",
        _rx(
            r"\b(?:req\.(?:params|query|body|headers|cookies)|request\.(?:args|form|json|headers|cookies|files)|r\.(?:URL\.Query|FormValue|Header\.Get)|RequestParam|PathVariable|RequestBody)\b"
        ),
    ),
    _Pattern(
        "input",
        "event",
        "Event or message value",
        _rx(
            r"\b(?:event|message|record|payload)\.(?:body|data|value|headers|attributes|Records)\b"
        ),
    ),
    _Pattern(
        "input",
        "cli",
        "CLI input",
        _rx(
            r"\b(?:process\.argv|sys\.argv|add_argument|flag\.(?:String|Int|Bool)|stdin)\b"
        ),
    ),
    _Pattern(
        "input",
        "config",
        "Runtime configuration",
        _rx(
            r"\b(?:getenv|environ\[|process\.env|System\.getenv|Environment\.GetEnvironmentVariable)\b"
        ),
    ),
    _Pattern(
        "input",
        "file",
        "Uploaded or external file",
        _rx(
            r"\b(?:filename|originalname|content_type|mimetype|multipart|UploadedFile|FileStorage)\b"
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Database query",
        _rx(
            r"\b(?:execute|executemany|rawQuery|createQuery|query|prepareStatement|\$wpdb->query)\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Command execution",
        _rx(
            r"\b(?:system|popen|exec|spawn|subprocess\.|ProcessBuilder|Runtime\.getRuntime\(\)\.exec|Command::new)\b"
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Filesystem operation",
        _rx(
            r"\b(?:open|readFile|writeFile|unlink|remove|FileInputStream|FileOutputStream|Path\.of|fs\.)\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Outbound request",
        _rx(
            r"\b(?:fetch|axios|requests\.(?:get|post|put|patch|delete|request)|httpx\.|HttpClient|RestTemplate|WebClient|wp_remote_)\b"
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Code or template evaluation",
        _rx(
            r"\b(?:eval|Function|exec|compile|render_template_string|Template\(|ScriptingEngine)\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "HTML output",
        _rx(
            r"\b(?:innerHTML|outerHTML|dangerouslySetInnerHTML|document\.write|v-html|render\(|html\(|echo\s)\b"
        ),
    ),
    _Pattern(
        "sink",
        "access",
        "Redirect or navigation",
        _rx(
            r"\b(?:redirect|sendRedirect|Location|window\.location|location\.(?:href|assign|replace)|window\.open)\b"
        ),
    ),
    _Pattern(
        "sink",
        "access",
        "Authorization decision",
        _rx(
            r"\b(?:authorize|permission|isAllowed|hasRole|hasPermission|checkAccess|ownership|owner_id|tenant_id)\b"
        ),
    ),
    _Pattern(
        "sink",
        "logic",
        "Deserialization",
        _rx(
            r"\b(?:pickle\.loads|yaml\.load|ObjectInputStream|unserialize|BinaryFormatter|readObject)\b"
        ),
    ),
    _Pattern(
        "sink",
        "logic",
        "Cryptographic operation",
        _rx(
            r"\b(?:md5|sha1|DES|RC4|Cipher|getInstance|createCipher|sign|verify|encrypt|decrypt|Math\.random|random\.)\b"
        ),
    ),
    _Pattern(
        "sink",
        "logic",
        "Sensitive logging",
        _rx(r"\b(?:log|logger|console)\.(?:debug|info|warn|error|log)\s*\("),
    ),
    _Pattern(
        "sink",
        "logic",
        "Concurrent state operation",
        _rx(
            r"\b(?:create_task|executor\.submit|CompletableFuture|go\s+func|setImmediate|ThreadPoolExecutor)\b"
        ),
    ),
    _Pattern(
        "control",
        "authentication",
        "Authentication control",
        _rx(
            r"\b(?:authenticate|login_required|requireAuth|verify_jwt|verifyToken|get_current_user|PreAuthorize)\b"
        ),
    ),
    _Pattern(
        "control",
        "authorization",
        "Authorization control",
        _rx(
            r"\b(?:authorize|checkAccess|hasPermission|hasRole|current_user_can|ownership|owner_id\s*==|tenant_id\s*==)\b"
        ),
    ),
    _Pattern(
        "control",
        "validation",
        "Input validation",
        _rx(
            r"\b(?:validate|validator|schema\.parse|safeParse|isValid|sanitize|escape|parameterized|prepareStatement|nonce|csrf)\b"
        ),
    ),
)


def _file_classification(path: Path, rel: str) -> tuple[str, bool, str]:
    parts = {part.casefold() for part in Path(rel).parts}
    name = path.name.casefold()
    suffixes = "".join(path.suffixes[-2:]).casefold()
    if parts & _EXCLUDED_PARTS:
        return "dependency_or_build", False, "dependency, build output, or VCS data"
    if parts & _TEST_PARTS or re.search(r"(?:^test_|_test\.|\.test\.|\.spec\.)", name):
        return "test", False, "test or fixture code"
    if parts & _GENERATED_PARTS or ".generated." in name or name.endswith(".pb.go"):
        return "generated", False, "generated source"
    if path.suffix.casefold() in _DOC_SUFFIXES:
        return "documentation", False, "documentation"
    if path.suffix.casefold() in _ASSET_SUFFIXES or suffixes in _ASSET_SUFFIXES:
        return "asset", False, "static or minified asset"
    language = _LANGUAGE_BY_SUFFIX.get(path.suffix.casefold(), "Other")
    if language == "Configuration":
        return "configuration", True, "runtime or deployment configuration"
    if language in _SOURCE_LANGUAGES:
        return "production", True, "first-party source candidate"
    return "other", False, "unsupported non-source file"


def _fingerprint(*parts: object) -> str:
    value = "|".join(str(part or "").strip().casefold() for part in parts)
    return hashlib.sha256(value.encode()).hexdigest()


def _partition_base(path: str) -> str:
    parts = Path(path).parts
    if len(parts) <= 1:
        return "root"
    source_markers = {"src", "app", "apps", "lib", "libs", "cmd", "pkg", "server"}
    for index, part in enumerate(parts[:-1]):
        if part.casefold() in source_markers and index + 1 < len(parts) - 1:
            return "/".join(parts[: index + 2])
    return "/".join(parts[: min(2, len(parts) - 1)]) or "root"


def reset_work_program(sast_run_id: int) -> None:
    """Remove work-program rows for a fresh scan without touching leads/logs."""
    with Session(get_engine()) as session:
        for model in (
            SastEvidenceReceipt,
            SastWorkItem,
            SastWorker,
            SastPartition,
            SastSurfaceItem,
            SastSourceFile,
        ):
            session.exec(delete(model).where(model.sast_run_id == sast_run_id))
        session.commit()


def build_source_atlas(sast_run_id: int, root: Path) -> dict[str, Any]:
    """Inventory production scope and seed durable source/sink obligations."""
    reset_work_program(sast_run_id)
    file_rows: list[SastSourceFile] = []
    path_to_disk: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            classification, relevant, reason = _file_classification(path, rel)
            try:
                raw = path.read_bytes()
                file_stat = path.stat()
            except OSError:
                continue
            digest = hashlib.sha256(raw).hexdigest()
            file_rows.append(
                SastSourceFile(
                    sast_run_id=sast_run_id,
                    path=rel,
                    language=_LANGUAGE_BY_SUFFIX.get(path.suffix.casefold(), "Other"),
                    size=file_stat.st_size,
                    sha256=digest,
                    classification=classification,
                    production_relevant=relevant,
                    classification_reason=reason,
                )
            )
            path_to_disk[rel] = path

    with Session(get_engine(), expire_on_commit=False) as session:
        session.add_all(file_rows)
        session.commit()
        persisted_files = session.exec(
            select(SastSourceFile).where(SastSourceFile.sast_run_id == sast_run_id)
        ).all()
        surface_rows: list[SastSurfaceItem] = []
        for row in persisted_files:
            if not row.production_relevant or len(surface_rows) >= _MAX_SURFACE_ITEMS:
                continue
            path = path_to_disk[row.path]
            if row.size > _MAX_ATLAS_FILE_BYTES:
                continue
            try:
                raw = path.read_bytes()
                if b"\x00" in raw[:512]:
                    continue
                lines = raw.decode("utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line_number, line in enumerate(lines, start=1):
                for pattern in _PATTERNS:
                    match = pattern.regex.search(line)
                    if not match:
                        continue
                    snippet = line.strip()[:500]
                    surface_rows.append(
                        SastSurfaceItem(
                            sast_run_id=sast_run_id,
                            source_file_id=row.id,
                            kind=pattern.kind,
                            category=pattern.category,
                            name=pattern.name,
                            path=row.path,
                            line=line_number,
                            symbol=snippet[:160],
                            details_json=json.dumps({"snippet": snippet}),
                            fingerprint=_fingerprint(
                                pattern.kind,
                                pattern.category,
                                row.path,
                                line_number,
                                pattern.name,
                            ),
                        )
                    )
                    if len(surface_rows) >= _MAX_SURFACE_ITEMS:
                        break
                if len(surface_rows) >= _MAX_SURFACE_ITEMS:
                    break
        session.add_all(surface_rows)
        session.commit()

        surfaces = session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == sast_run_id)
        ).all()
        entrypoints = [item for item in surfaces if item.kind == "entrypoint"]
        inputs = [item for item in surfaces if item.kind == "input"]
        sinks = [item for item in surfaces if item.kind == "sink"]

        if not inputs:
            seeds = (
                entrypoints
                or [
                    SastSurfaceItem(
                        sast_run_id=sast_run_id,
                        source_file_id=row.id,
                        kind="input",
                        category="repository_surface",
                        name="Production source scope",
                        path=row.path,
                        line=1,
                        symbol="No framework-specific input was detected; review this source scope.",
                        details_json="{}",
                        provenance="fallback",
                        fingerprint=_fingerprint("fallback-input", row.path),
                    )
                    for row in persisted_files
                    if row.production_relevant
                ][:200]
            )
            for seed in seeds:
                if seed.kind == "input":
                    session.add(seed)
                else:
                    session.add(
                        SastSurfaceItem(
                            sast_run_id=sast_run_id,
                            source_file_id=seed.source_file_id,
                            kind="input",
                            category="no_input_entrypoint",
                            name=f"Entrypoint review: {seed.name}",
                            path=seed.path,
                            line=seed.line,
                            symbol=seed.symbol,
                            details_json=json.dumps({"entrypoint_id": seed.id}),
                            provenance="reconciliation",
                            fingerprint=_fingerprint(
                                "entrypoint-input", seed.fingerprint
                            ),
                        )
                    )
            session.commit()
            surfaces = session.exec(
                select(SastSurfaceItem).where(
                    SastSurfaceItem.sast_run_id == sast_run_id
                )
            ).all()
            inputs = [item for item in surfaces if item.kind == "input"]

        grouped: dict[str, list[SastSurfaceItem]] = defaultdict(list)
        for item in inputs:
            grouped[_partition_base(item.path)].append(item)
        partition_rows: list[SastPartition] = []
        for base, items in sorted(grouped.items()):
            for offset in range(0, len(items), _PARTITION_INPUT_LIMIT):
                chunk = items[offset : offset + _PARTITION_INPUT_LIMIT]
                key = f"{base}:{offset // _PARTITION_INPUT_LIMIT + 1}"
                partition_rows.append(
                    SastPartition(
                        sast_run_id=sast_run_id,
                        partition_key=key,
                        name=f"{base} part {offset // _PARTITION_INPUT_LIMIT + 1}",
                        file_paths_json=json.dumps(
                            sorted({item.path for item in chunk})
                        ),
                    )
                )
        session.add_all(partition_rows)
        session.commit()

        partitions = session.exec(
            select(SastPartition).where(SastPartition.sast_run_id == sast_run_id)
        ).all()
        partition_for_path: dict[str, SastPartition] = {}
        for partition in partitions:
            for path in json.loads(partition.file_paths_json):
                partition_for_path.setdefault(path, partition)

        workers: dict[tuple[int | None, str], SastWorker] = {}
        for partition in partitions:
            for class_group in CLASS_GROUPS:
                worker = SastWorker(
                    sast_run_id=sast_run_id,
                    partition_id=partition.id,
                    worker_key=f"{partition.partition_key}:{class_group}",
                    class_group=class_group,
                )
                session.add(worker)
                workers[(partition.id, class_group)] = worker
        sink_workers: list[SastWorker] = []
        for offset in range(0, len(sinks), _SINK_WORK_LIMIT):
            sink_worker = SastWorker(
                sast_run_id=sast_run_id,
                partition_id=None,
                worker_key=f"sink-audit:{offset // _SINK_WORK_LIMIT + 1}",
                class_group="sink",
            )
            session.add(sink_worker)
            sink_workers.append(sink_worker)
        session.commit()

        for item in inputs:
            partition = partition_for_path.get(item.path)
            if partition is None:
                continue
            for class_group in CLASS_GROUPS:
                worker = workers[(partition.id, class_group)]
                session.add(
                    SastWorkItem(
                        sast_run_id=sast_run_id,
                        partition_id=partition.id,
                        surface_item_id=item.id,
                        worker_id=worker.id,
                        work_key=f"input:{item.id}:{class_group}",
                        work_type="input",
                        class_group=class_group,
                    )
                )
        for offset in range(0, len(sinks), _SINK_WORK_LIMIT):
            worker = sink_workers[offset // _SINK_WORK_LIMIT]
            for sink in sinks[offset : offset + _SINK_WORK_LIMIT]:
                session.add(
                    SastWorkItem(
                        sast_run_id=sast_run_id,
                        partition_id=(
                            partition_for_path.get(sink.path).id
                            if partition_for_path.get(sink.path)
                            else None
                        ),
                        surface_item_id=sink.id,
                        worker_id=worker.id,
                        work_key=f"sink:{sink.id}",
                        work_type="sink",
                        class_group="sink",
                    )
                )
        session.commit()

    return work_program_summary(sast_run_id)


def work_program_summary(sast_run_id: int) -> dict[str, Any]:
    with Session(get_engine()) as session:
        files = session.exec(
            select(SastSourceFile).where(SastSourceFile.sast_run_id == sast_run_id)
        ).all()
        surfaces = session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == sast_run_id)
        ).all()
        partitions = session.exec(
            select(SastPartition).where(SastPartition.sast_run_id == sast_run_id)
        ).all()
        workers = session.exec(
            select(SastWorker).where(SastWorker.sast_run_id == sast_run_id)
        ).all()
        work_items = session.exec(
            select(SastWorkItem).where(SastWorkItem.sast_run_id == sast_run_id)
        ).all()
        receipts = session.exec(
            select(SastEvidenceReceipt).where(
                SastEvidenceReceipt.sast_run_id == sast_run_id
            )
        ).all()

    surface_counts: dict[str, int] = defaultdict(int)
    for item in surfaces:
        surface_counts[item.kind] += 1
    work_counts: dict[str, int] = defaultdict(int)
    for item in work_items:
        work_counts[item.status] += 1
    worker_counts: dict[str, int] = defaultdict(int)
    for worker in workers:
        worker_counts[worker.status] += 1
    direct_paths = {
        receipt.path for receipt in receipts if receipt.tool_name == "read_file"
    }
    matched_paths: set[str] = set()
    for receipt in receipts:
        try:
            matched_paths.update(
                json.loads(receipt.details_json).get("matched_paths", [])
            )
        except (TypeError, ValueError, AttributeError):
            continue
    unresolved = sum(
        count
        for status, count in work_counts.items()
        if status not in TERMINAL_WORK_STATUSES
    )
    return {
        "files": {
            "total": len(files),
            "production": sum(row.production_relevant for row in files),
            "directly_opened": len(direct_paths),
            "with_search_matches": len(matched_paths),
        },
        "surface": dict(surface_counts),
        "partitions": {
            "total": len(partitions),
            "complete": sum(row.status == "complete" for row in partitions),
        },
        "workers": {"total": len(workers), **dict(worker_counts)},
        "work_items": {
            "total": len(work_items),
            "resolved": len(work_items) - unresolved,
            "unresolved": unresolved,
            "statuses": dict(work_counts),
        },
        "evidence": {
            "receipts": len(receipts),
            "read_calls": sum(r.tool_name == "read_file" for r in receipts),
            "search_calls": sum(r.tool_name == "grep" for r in receipts),
            "characters_returned": sum(r.characters_returned for r in receipts),
            "truncated": sum(r.truncated for r in receipts),
        },
    }


def worker_payload(worker_id: int) -> dict[str, Any]:
    with Session(get_engine()) as session:
        worker = session.get(SastWorker, worker_id)
        if worker is None:
            return {}
        partition = (
            session.get(SastPartition, worker.partition_id)
            if worker.partition_id
            else None
        )
        work_items = session.exec(
            select(SastWorkItem)
            .where(SastWorkItem.worker_id == worker_id)
            .order_by(SastWorkItem.id)
        ).all()
        result = []
        for work_item in work_items:
            surface = session.get(SastSurfaceItem, work_item.surface_item_id)
            if surface is None:
                continue
            result.append(
                {
                    "work_item_id": work_item.id,
                    "work_type": work_item.work_type,
                    "class_group": work_item.class_group,
                    "status": work_item.status,
                    "surface": {
                        "kind": surface.kind,
                        "category": surface.category,
                        "name": surface.name,
                        "path": surface.path,
                        "line": surface.line,
                        "symbol": surface.symbol,
                        "trust_level": surface.trust_level,
                    },
                }
            )
        return {
            "worker_id": worker.id,
            "worker_key": worker.worker_key,
            "class_group": worker.class_group,
            "partition": partition.partition_key if partition else "global",
            "files": json.loads(partition.file_paths_json) if partition else [],
            "work_items": result,
        }


def set_worker_status(
    worker_id: int, status: str, *, summary: str = "", error: str = ""
) -> None:
    with Session(get_engine()) as session:
        worker = session.get(SastWorker, worker_id)
        if worker is None:
            return
        now = datetime.now(_UTC)
        worker.status = status
        worker.summary = summary[:4000]
        worker.error_message = error[:4000]
        worker.updated_at = now
        if status == "running" and worker.started_at is None:
            worker.started_at = now
        if status in {"complete", "failed", "blocked"}:
            worker.completed_at = now
        session.add(worker)
        session.flush()
        if worker.partition_id:
            partition = session.get(SastPartition, worker.partition_id)
            if partition is not None:
                sibling_statuses = session.exec(
                    select(SastWorker.status).where(
                        SastWorker.partition_id == partition.id
                    )
                ).all()
                statuses = list(sibling_statuses)
                if all(value == "complete" for value in statuses):
                    partition.status = "complete"
                    partition.completed_at = now
                elif any(value in {"failed", "blocked"} for value in statuses):
                    partition.status = "partial"
                elif any(value == "running" for value in statuses):
                    partition.status = "running"
                    partition.started_at = partition.started_at or now
                partition.updated_at = now
                session.add(partition)
        session.commit()


def unresolved_for_worker(worker_id: int) -> list[int]:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(SastWorkItem).where(SastWorkItem.worker_id == worker_id)
        ).all()
    return [row.id for row in rows if row.status not in TERMINAL_WORK_STATUSES]


def record_disposition(
    work_item_id: int,
    *,
    status: str,
    reasoning: str,
    trace: list[Any] | None = None,
    controls: list[Any] | None = None,
    evidence: list[Any] | None = None,
    candidate_from_lead: bool = False,
) -> tuple[bool, str]:
    if status not in TERMINAL_WORK_STATUSES:
        return False, f"Invalid terminal disposition: {status}"
    if not reasoning.strip():
        return False, "A concrete disposition reason is required."
    if status == "candidate" and not candidate_from_lead:
        return False, "Use write_lead to record a candidate disposition."
    with Session(get_engine()) as session:
        item = session.get(SastWorkItem, work_item_id)
        if item is None:
            return False, f"Unknown work item {work_item_id}."
        if item.status == "candidate" and status != "candidate":
            return False, "A candidate work item cannot be replaced by a safe result."
        surface = (
            session.get(SastSurfaceItem, item.surface_item_id)
            if item.surface_item_id
            else None
        )
        receipts = session.exec(
            select(SastEvidenceReceipt)
            .where(SastEvidenceReceipt.worker_id == item.worker_id)
            .where(SastEvidenceReceipt.tool_name == "read_file")
        ).all()
        has_direct_evidence = surface is not None and any(
            receipt.path == surface.path
            and (
                surface.line is None
                or (
                    (receipt.start_line is None or receipt.start_line <= surface.line)
                    and (receipt.end_line is None or receipt.end_line >= surface.line)
                )
            )
            for receipt in receipts
        )
        if not has_direct_evidence:
            location = surface.path if surface is not None else "the assigned source"
            return (
                False,
                f"Open {location} with read_file before closing this work item.",
            )
        item.status = status
        item.disposition = status
        item.reasoning = reasoning[:8000]
        item.trace_json = json.dumps(trace or [], ensure_ascii=False)
        item.controls_json = json.dumps(controls or [], ensure_ascii=False)
        item.evidence_json = json.dumps(evidence or [], ensure_ascii=False)
        item.updated_at = datetime.now(_UTC)
        session.add(item)
        session.commit()
    return True, f"Work item {work_item_id} recorded as {status}."


def attach_lead(work_item_id: int | None, lead_id: int) -> None:
    if not work_item_id:
        return
    with Session(get_engine()) as session:
        item = session.get(SastWorkItem, work_item_id)
        if item is None:
            return
        item.lead_id = lead_id
        item.status = "candidate"
        item.disposition = "candidate"
        item.updated_at = datetime.now(_UTC)
        session.add(item)
        session.commit()


def record_evidence_receipt(receipt: SastEvidenceReceipt) -> None:
    with Session(get_engine()) as session:
        session.add(receipt)
        session.commit()


def completion_decision(sast_run_id: int) -> tuple[str, list[str], dict[str, Any]]:
    summary = work_program_summary(sast_run_id)
    reasons: list[str] = []
    if summary["files"]["production"] and not summary["surface"].get("entrypoint"):
        reasons.append("No production entry point was identified for reconciliation.")
    if summary["files"]["production"] and not summary["surface"].get("sink"):
        reasons.append("No security-sensitive sink was identified for the sink pass.")
    if sum(summary["surface"].values()) >= _MAX_SURFACE_ITEMS:
        reasons.append("The deterministic source atlas reached its item limit.")
    if summary["work_items"]["total"] == 0:
        reasons.append("No auditable source or sink obligations were created.")
    if summary["work_items"]["unresolved"]:
        reasons.append(
            f"{summary['work_items']['unresolved']} work item(s) remain unresolved."
        )
    failed_workers = summary["workers"].get("failed", 0) + summary["workers"].get(
        "blocked", 0
    )
    if failed_workers:
        reasons.append(f"{failed_workers} worker(s) failed or were blocked.")
    pending_workers = summary["workers"].get("pending", 0) + summary["workers"].get(
        "running", 0
    )
    if pending_workers:
        reasons.append(f"{pending_workers} worker(s) did not complete.")
    return ("full" if not reasons else "partial", reasons, summary)


def worker_rows(sast_run_id: int) -> list[SastWorker]:
    with Session(get_engine(), expire_on_commit=False) as session:
        return list(
            session.exec(
                select(SastWorker)
                .where(SastWorker.sast_run_id == sast_run_id)
                .order_by(SastWorker.id)
            ).all()
        )


def count_rows(sast_run_id: int, model) -> int:
    with Session(get_engine()) as session:
        return int(
            session.exec(
                select(func.count())
                .select_from(model)
                .where(model.sast_run_id == sast_run_id)
            ).one()
        )
