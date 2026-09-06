"""Deterministic, bounded extraction of compact interface facts from a SAST
source tree.

Every campaign source repository is scanned separately (see
``services/sast_scanner.py``). Alongside the usual leads, this module derives
a short, structured summary of how the code talks to the outside world:
routes/UI paths it serves, HTTP calls it makes, auth/session boundaries,
message queues/topics, shared datastores, and framework markers - each with a
``file:line`` evidence pointer.

This is intentionally deterministic rather than another LLM turn: it is
cheap and bounded, and it only needs to be "good enough" to seed
cross-repository correlation (``services/correlation.py``), not to replace
the agentic SAST analysis itself. Frontend files use the shared semantic
extractor first, with the older line-oriented patterns as a compatibility
fallback.
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
    ".vue",
    ".html",
    ".htm",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".cs",
}

_FRONTEND_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".vue", ".html", ".htm"}

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

_SPRING_MAPPING_NAMES = {
    "requestmapping": None,
    "getmapping": "GET",
    "postmapping": "POST",
    "putmapping": "PUT",
    "patchmapping": "PATCH",
    "deletemapping": "DELETE",
}
_SPRING_MAPPING_PATTERN = re.compile(
    r"@(?P<name>RequestMapping|GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping)\b",
    re.IGNORECASE,
)


def _balanced_annotation_end(text: str, opening: int) -> int:
    """Return the closing parenthesis for a Java annotation call."""
    depth = 0
    quote = ""
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _spring_annotation(text: str, match: re.Match[str]) -> tuple[str, int]:
    """Return an annotation name and its end offset."""
    end = match.end()
    while end < len(text) and text[end].isspace():
        end += 1
    if end < len(text) and text[end] == "(":
        closing = _balanced_annotation_end(text, end)
        return match.group("name").casefold(), closing if closing >= 0 else end
    return match.group("name").casefold(), end


def _spring_mapping_paths(annotation_body: str) -> list[str]:
    """Extract route values from Spring mapping annotation arguments."""
    value_match = re.search(
        r"\b(?:value|path)\s*=\s*(?P<value>\{[^}]*\}|[\"'][^\"']*[\"'])",
        annotation_body,
        re.IGNORECASE | re.DOTALL,
    )
    if value_match:
        values = re.findall(r"[\"']([^\"']*)[\"']", value_match.group("value"))
    else:
        values = re.findall(r"[\"']([^\"']*)[\"']", annotation_body)
    return [value.strip() or "/" for value in values] or ["/"]


def _spring_mapping_methods(name: str, annotation_body: str) -> list[str | None]:
    fixed = _SPRING_MAPPING_NAMES[name]
    if fixed:
        return [fixed]
    values = re.findall(
        r"RequestMethod\.([A-Z]+)|HttpMethod\.([A-Z]+)",
        annotation_body,
        re.IGNORECASE,
    )
    methods = [first or second for first, second in values]
    return [method.upper() for method in methods] or [None]


def _join_spring_paths(prefix: str, path: str) -> str:
    joined = "/".join((prefix.rstrip("/"), path.lstrip("/"))).strip("/")
    return "/" + joined if joined else "/"


def _spring_route_facts(text: str, relative_path: str) -> list[dict]:
    """Extract Spring MVC method mappings with their class-level prefix."""
    classes: list[tuple[int, int, str]] = []
    class_pattern = re.compile(
        r"(?P<annotations>(?:(?:@[A-Za-z_$][\w$]*(?:\s*\([^)]*\))?)\s*)*)"
        r"(?:public\s+|protected\s+|private\s+|abstract\s+|final\s+)*"
        r"class\s+[A-Za-z_$][\w$]*\s*\{",
        re.DOTALL,
    )
    for class_match in class_pattern.finditer(text):
        opening = text.find("{", class_match.start(), class_match.end())
        if opening < 0:
            continue
        depth = 0
        quote = ""
        escaped = False
        closing = len(text)
        for index in range(opening, len(text)):
            char = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
                continue
            if char in "'\"":
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    closing = index
                    break
        prefix = "/"
        for mapping in _SPRING_MAPPING_PATTERN.finditer(
            class_match.group("annotations")
        ):
            name, end = _spring_annotation(class_match.group("annotations"), mapping)
            body = class_match.group("annotations")[mapping.end() : end]
            values = _spring_mapping_paths(body)
            if values:
                prefix = values[0]
                break
        classes.append((class_match.start(), closing, prefix))

    routes: list[dict] = []
    seen: set[tuple[str | None, str, int]] = set()
    for start, closing, prefix in classes:
        body_start = text.find("{", start, closing) + 1
        for mapping in _SPRING_MAPPING_PATTERN.finditer(text, body_start, closing):
            name, end = _spring_annotation(text, mapping)
            body = text[mapping.end() : end]
            values = _spring_mapping_paths(body)
            methods = _spring_mapping_methods(name, body)
            location = f"{relative_path}:{text.count(chr(10), 0, mapping.start()) + 1}"
            for value in values:
                path = _join_spring_paths(prefix, value)
                for method in methods:
                    identity = (method, path, mapping.start())
                    if identity in seen:
                        continue
                    seen.add(identity)
                    routes.append(
                        {
                            "fact_type": "route",
                            "method": method,
                            "path": path,
                            "host": None,
                            "name": None,
                            "detail": {"request_role": "server_ingress"},
                            "evidence_location": location,
                        }
                    )
    return routes


# ── Outbound HTTP calls ───────────────────────────────────────────────────────
_HTTP_CALL_PATTERNS = [
    re.compile(
        r"\b(?:requests|httpx|http|axios)\.(?P<method>get|post|put|patch|delete)\(\s*"
        r"[\"'](?P<url>https?://[^\"']+|/[^\"']*)[\"']",
        re.IGNORECASE,
    ),
    re.compile(
        r"\baxios\.request\(\s*\{[^}]*?\burl\s*:\s*[\"']"
        r"(?P<url>https?://[^\"']+|/[^\"']*)[\"'][^}]*?"
        r"\bmethod\s*:\s*[\"'](?P<method>\w+)[\"']",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:axios|fetch)\(\s*[\"'](?P<url>https?://[^\"']+|/[^\"']*)[\"']"
        r"(?:\s*,\s*\{[^}]*method\s*:\s*[\"'](?P<method>\w+)[\"'])?",
        re.IGNORECASE,
    ),
]

# Request-bearing facts use this field to keep browser traffic separate from
# calls made by a server.  The field lives in detail_json so existing
# ComponentFact rows remain readable without a schema migration.
REQUEST_ROLES = frozenset({"browser_request", "server_ingress", "server_egress"})


def normalize_request_role(value: object) -> str | None:
    """Return a supported request role, or ``None`` for an unknown role.

    Unknown legacy facts are intentionally left unknown.  A caller can then
    record a proof gap instead of treating a server-to-server URL as a browser
    entry point.
    """
    if value is None:
        return None
    role = str(value).strip().casefold().replace("-", "_")
    aliases = {
        "browser": "browser_request",
        "frontend": "browser_request",
        "client": "browser_request",
        "ingress": "server_ingress",
        "server_in": "server_ingress",
        "egress": "server_egress",
        "server_out": "server_egress",
    }
    role = aliases.get(role, role)
    if role not in REQUEST_ROLES:
        raise ValueError(
            "request_role must be one of browser_request, server_ingress, "
            "or server_egress"
        )
    return role


def request_role_for_fact(
    fact_type: str,
    detail: dict | None = None,
    *,
    source_suffix: str | None = None,
) -> str | None:
    """Resolve a request role from explicit detail and deterministic hints."""
    detail = detail if isinstance(detail, dict) else {}
    if "request_role" in detail:
        return normalize_request_role(detail.get("request_role"))
    if fact_type == "route":
        return "server_ingress"
    if fact_type != "http_call":
        return None
    if detail.get("frontend") or detail.get("ui_route") or detail.get("trigger"):
        return "browser_request"
    if source_suffix and source_suffix.casefold() in _FRONTEND_SUFFIXES:
        return "browser_request"
    if (
        detail.get("handler")
        or detail.get("handler_location")
        or detail.get("handler_locations")
    ):
        return "server_egress"
    return None


_UI_ROUTE_PATTERNS = [
    re.compile(
        r"(?:<Route|route)\s*(?:[^>]*?)path\s*=\s*[\"'](?P<path>/[^\"']*)[\"']",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:createBrowserRouter|createHashRouter)\s*\(\s*\[(?P<body>.*)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpath\s*:\s*[\"'](?P<path>/[^\"']*)[\"']",
        re.IGNORECASE,
    ),
]

_UI_ACTION_PATTERNS = [
    re.compile(r"\bonSubmit\s*=\s*\{?(?P<handler>[\w$]+)", re.IGNORECASE),
    re.compile(r"\bonClick\s*=\s*\{?(?P<handler>[\w$]+)", re.IGNORECASE),
    re.compile(r"<button\b[^>]*>(?P<label>[^<]{1,120})</button>", re.IGNORECASE),
]


def _normalise_frontend_path(value: object) -> str | None:
    """Return a stable path for frontend facts.

    The semantic extractor can see JavaScript template literals while the
    legacy extractor sees only quoted strings.  Keep the parameter shape in
    the fact so the mapper can compare it with a backend route, and strip
    query strings for the same reason as ``interface_fact_fingerprint``.
    """
    if value is None:
        return None
    path = str(value).strip()
    if not path:
        return None
    path = re.sub(r"\$\{\s*([^}]+?)\s*\}", r"{\1}", path)
    path = re.sub(r"\{\s*([^}]+?)\s*\}", r"{\1}", path)
    path = re.sub(r"/:([A-Za-z_$][\w$-]*)", r"/{\1}", path)
    if "?" in path:
        path = path.split("?", 1)[0]
    if "#" in path:
        path = path.split("#", 1)[0]
    return path or "/"


_SERVER_FRONTEND_MARKERS = re.compile(
    r"(?:from|require\s*\()\s*[\"'](?:express|fastify|koa|hapi|@nestjs/)"
    r"|\b(?:express|fastify|koa|hapi)\s*\("
    r"|\b(?:server|app|router)\.(?:listen|use|route|get|post|put|patch|delete)\s*\("
    r"|\b(?:@Controller|@Get|@Post|@Put|@Patch|@Delete)\b",
    re.IGNORECASE,
)
_BROWSER_FRONTEND_MARKERS = re.compile(
    r"\b(?:window|document|globalThis)\b|\.addEventListener\s*\("
    r"|\bon(?:Click|Submit)\s*=|@[\w-]+\s*=|\((?:click|submit|ngSubmit)\)\s*="
    r"|<\s*(?:button|form|input|select|textarea|Route)\b"
    r"|\b(?:useState|useEffect)\b|@Component\b",
    re.IGNORECASE,
)


def _classify_frontend_source(text: str, relative_path: str) -> str:
    """Classify browser/server evidence without trusting a file extension."""
    path_parts = {
        part.casefold() for part in relative_path.replace("\\", "/").split("/")
    }
    stem = Path(relative_path).stem.casefold()
    if _SERVER_FRONTEND_MARKERS.search(text) or path_parts & {
        "server",
        "backend",
        "api",
        "routes",
        "controllers",
    }:
        return "server"
    if (
        _BROWSER_FRONTEND_MARKERS.search(text)
        or stem
        in {
            "ui",
            "frontend",
            "component",
            "page",
            "view",
        }
        or path_parts & {"components", "pages", "views"}
    ):
        return "browser"
    return "unknown"


def _location_source(location: object, source_paths: tuple[str, ...]) -> str | None:
    if not isinstance(location, str):
        return None
    return next(
        (path for path in source_paths if location.startswith(f"{path}:")),
        None,
    )


def _apply_frontend_request_roles(
    facts: list[dict],
    source_roles: dict[str, str],
    source_paths: tuple[str, ...],
) -> None:
    """Apply conservative browser/server roles to semantic facts in place."""
    browser_files = {
        source
        for fact in facts
        if fact.get("fact_type") in {"ui_action", "ui_route"}
        for source in [_location_source(fact.get("evidence_location"), source_paths)]
        if source is not None and source_roles.get(source) != "server"
    }
    for fact in facts:
        if fact.get("fact_type") != "http_call":
            continue
        source = _location_source(fact.get("evidence_location"), source_paths)
        detail = fact.setdefault("detail", {})
        handlers = detail.get("handler_locations") or []
        if isinstance(handlers, str):
            handlers = [handlers]
        handler_sources = {
            handler_source
            for handler_source in (
                _location_source(location, source_paths) for location in handlers
            )
            if handler_source is not None
        }
        if handler_sources & browser_files:
            role = "browser_request"
        elif source_roles.get(source) == "server":
            role = "server_egress"
        elif source_roles.get(source) == "browser":
            role = "browser_request"
        else:
            role = None
        detail["request_role"] = role
        detail["frontend"] = role == "browser_request"


def _frontend_evidence_location(raw: dict, relative_path: str) -> str:
    """Keep semantic evidence tied to the source file being scanned."""
    location = raw.get("evidence_location") or raw.get("location")
    if isinstance(location, int):
        return f"{relative_path}:{max(1, location)}"
    if isinstance(location, str) and location.strip():
        location = location.strip()
        if location.startswith(f"{relative_path}:"):
            # ComponentFact evidence uses file:line.  Preserve a column when
            # the analyzer supplies one only if it is already part of the
            # source pointer; the mapper can still display it verbatim.
            return location
        line_match = re.match(r"[^:]+:(\d+)(?::\d+)?$", location)
        if line_match:
            return f"{relative_path}:{line_match.group(1)}"
    line = raw.get("line")
    if isinstance(line, int):
        return f"{relative_path}:{max(1, line)}"
    return f"{relative_path}:1"


def _extract_semantic_frontend_facts(text: str, relative_path: str) -> list[dict]:
    """Adapt the shared frontend analyzer to the ComponentFact shape.

    This per-file API is a compatibility fallback only. Production extraction
    uses the repository API so imports and aliases can be resolved together.
    Importing lazily keeps extraction usable when an older installation has no
    semantic analyzer module.
    """
    try:
        from aespa.services.frontend_semantics import extract_frontend_facts
    except Exception:
        return []
    try:
        extracted = extract_frontend_facts(text, relative_path)
    except Exception:
        return []
    return _normalise_semantic_frontend_facts(extracted, relative_path)


def _normalise_semantic_frontend_facts(
    extracted: object,
    relative_path: str | None = None,
    source_paths: tuple[str, ...] = (),
) -> list[dict]:
    """Adapt semantic facts from either the file or repository API."""
    if not isinstance(extracted, list):
        return []

    facts: list[dict] = []
    for raw in extracted[:_MAX_FACTS]:
        if not isinstance(raw, dict):
            continue
        fact_type = str(raw.get("fact_type") or "").strip()
        if not fact_type:
            continue
        detail = raw.get("detail")
        if not isinstance(detail, dict):
            detail = {}
        else:
            detail = dict(detail)
        path = _normalise_frontend_path(raw.get("path"))
        name = raw.get("name")
        if fact_type == "ui_action" and detail.get("handler"):
            # Labels are useful display metadata, but handler identity keeps
            # two buttons with different actions from collapsing when their
            # surrounding markup happens to produce the same label.
            detail.setdefault("label", name)
            name = detail["handler"]
        fact_path = relative_path
        if fact_path is None:
            location = raw.get("evidence_location") or raw.get("location")
            if isinstance(location, str):
                fact_path = next(
                    (
                        candidate
                        for candidate in source_paths
                        if location.startswith(f"{candidate}:")
                    ),
                    None,
                )
            fact_path = fact_path or raw.get("relative_path") or raw.get("source_path")
        if not isinstance(fact_path, str) or not fact_path:
            continue
        facts.append(
            {
                "fact_type": fact_type,
                "method": (
                    str(raw["method"]).upper()
                    if raw.get("method") is not None
                    else None
                ),
                "path": path,
                "host": raw.get("host"),
                "name": name,
                "detail": detail,
                "evidence_location": _frontend_evidence_location(raw, fact_path),
            }
        )
    return facts


def _extract_semantic_frontend_repository_facts(
    sources: dict[str, str],
) -> tuple[list[dict], bool]:
    """Run the production repository analyzer once per source tree."""
    try:
        from aespa.services.frontend_semantics import (
            extract_frontend_repository_facts,
        )
    except Exception:
        return [], False
    try:
        extracted = extract_frontend_repository_facts(sources)
    except Exception:
        return [], False
    return _normalise_semantic_frontend_facts(
        extracted,
        source_paths=tuple(sources),
    ), True


_AUTH_MARKERS = re.compile(
    r"login_required|requires?_auth|authenticate|verify_jwt|Depends\("
    r"\s*get_current_user|passport\.authenticate|@PreAuthorize|IsAuthenticated",
    re.IGNORECASE,
)
_SPRING_SECURITY_MATCHER = re.compile(
    r"\.securityMatcher\((?P<args>[^)]*)\)", re.IGNORECASE
)
_SPRING_PERMIT_ALL = re.compile(
    r"\.requestMatchers\((?P<args>[^)]*)\)\.permitAll", re.IGNORECASE
)
_SPRING_ANY_REQUEST_AUTHENTICATED = re.compile(
    r"\.anyRequest\(\)\.authenticated\(\)", re.IGNORECASE
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
    """Fingerprint interface identity without tying it to one evidence line.

    ``name`` and descriptive host text are mapper metadata, not interface
    identity. LLM mapping often gives the same call a different label or
    explains a default host in prose; those variants must still merge.
    """
    raw_path = (path or "").strip().lower()
    if "://" in raw_path:
        raw_path = urlparse(raw_path).path
    raw_path = raw_path.split("?", 1)[0].rstrip("/") or "/"
    raw_path = re.sub(r"\{[^}]+\}", "{}", raw_path)
    raw_path = re.sub(r"/:[\w-]+", "/{}", raw_path)
    raw_host = (host or "").strip().lower()
    if raw_host:
        first_host_token = raw_host.split()[0]
        parsed_host = urlparse(
            first_host_token if "://" in first_host_token else f"//{first_host_token}"
        ).hostname
        raw_host = (parsed_host or "").lower()
    identity_name = name or ""
    if fact_type in {
        "http_call",
        "route",
        "ui_route",
        "auth_flow",
        "rpc_client",
        "rpc_server",
    } and (path or method):
        identity_name = ""
    canonical = "|".join(
        (
            (fact_type or "").strip().lower(),
            (method or "").strip().lower(),
            re.sub(r"\s+", " ", raw_path),
            raw_host,
            identity_name.strip().lower(),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _spring_security_context(text: str) -> dict[str, object]:
    """Extract small, path-aware Spring Security rules from one source file."""
    protected_paths: list[str] = []
    for match in _SPRING_SECURITY_MATCHER.finditer(text):
        protected_paths.extend(re.findall(r"[\"']([^\"']+)[\"']", match.group("args")))

    public_rules: list[dict[str, object]] = []
    for match in _SPRING_PERMIT_ALL.finditer(text):
        args = match.group("args")
        paths = re.findall(r"[\"']([^\"']+)[\"']", args)
        method_match = re.search(r"HttpMethod\.([A-Z]+)", args)
        for path in paths:
            public_rules.append(
                {
                    "path": path,
                    "method": method_match.group(1) if method_match else None,
                }
            )

    return {
        "protected_paths": protected_paths or ["*"],
        "public_rules": public_rules,
        "has_global_auth": bool(_SPRING_ANY_REQUEST_AUTHENTICATED.search(text)),
    }


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

    source_files: list[tuple[Path, str, str]] = []
    for path in _iter_source_files(root):
        if path.suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        source_files.append((path, rel, text))

    frontend_sources = {
        rel: text
        for path, rel, text in source_files
        if path.suffix.lower() in _FRONTEND_SUFFIXES
    }
    source_roles = {
        rel: _classify_frontend_source(text, rel)
        for rel, text in frontend_sources.items()
    }
    semantic_repository_facts, repository_api_available = (
        _extract_semantic_frontend_repository_facts(frontend_sources)
    )
    _apply_frontend_request_roles(
        semantic_repository_facts,
        source_roles,
        tuple(frontend_sources),
    )
    semantic_facts_by_file: dict[str, list[dict]] = {}
    for semantic_fact in semantic_repository_facts:
        location = semantic_fact.get("evidence_location") or ""
        source_file = next(
            (
                rel
                for rel in frontend_sources
                if isinstance(location, str) and location.startswith(f"{rel}:")
            ),
            None,
        )
        if source_file is not None:
            semantic_facts_by_file.setdefault(source_file, []).append(semantic_fact)
        if len(facts) < _MAX_FACTS:
            _add(semantic_fact)

    for path, rel, text in source_files:
        if len(facts) >= _MAX_FACTS:
            break
        spring_security = _spring_security_context(text)
        is_frontend_source = path.suffix.lower() in _FRONTEND_SUFFIXES

        # Spring MVC mappings need the class prefix and method annotation
        # together.  The line-oriented patterns below cannot recover that
        # relationship when ``@RequestMapping("/claims")`` sits above the
        # class and ``@PostMapping("/{id}/paid")`` sits above a method.
        for spring_route in _spring_route_facts(text, rel):
            if len(facts) >= _MAX_FACTS:
                break
            _add(spring_route)

        # The semantic pass follows calls through wrappers and UI bindings.
        # Keep the line-oriented extractors below as a small compatibility
        # fallback for syntax the semantic pass does not understand.  _add()
        # merges equivalent facts by interface identity.
        semantic_frontend_facts = semantic_facts_by_file.get(rel, [])
        if is_frontend_source and not repository_api_available:
            semantic_frontend_facts = _extract_semantic_frontend_facts(text, rel)
            _apply_frontend_request_roles(
                semantic_frontend_facts,
                {rel: source_roles.get(rel, "unknown")},
                (rel,),
            )
            for frontend_fact in semantic_frontend_facts:
                if len(facts) >= _MAX_FACTS:
                    break
                _add(frontend_fact)

        # Next.js file-system routes are concrete browser roots even when no
        # JSX route declaration exists in the file.
        normalized_parts = rel.split("/")
        if path.name in {"page.js", "page.jsx", "page.ts", "page.tsx"} and (
            "app" in normalized_parts
        ):
            route_parts = normalized_parts[:-1]
            if route_parts and route_parts[0] == "src":
                route_parts = route_parts[1:]
            if route_parts and route_parts[0] == "app":
                route_parts = route_parts[1:]
            route = "/" + "/".join(
                part
                for part in route_parts
                if part and not (part.startswith("(") and part.endswith(")"))
            )
            _add(
                {
                    "fact_type": "ui_route",
                    "method": None,
                    "path": route.rstrip("/") or "/",
                    "host": None,
                    "name": "Next.js App Router page",
                    "detail": {
                        "route_kind": "next_app",
                        "trigger": "page_load",
                        "request_role": None,
                    },
                    "evidence_location": f"{rel}:1",
                }
            )
        elif path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx"} and (
            "pages" in normalized_parts
        ):
            page_index = normalized_parts.index("pages")
            route_parts = normalized_parts[page_index + 1 :]
            if route_parts and route_parts[-1].split(".")[0] in {"index"}:
                route_parts = route_parts[:-1]
            else:
                route_parts[-1] = route_parts[-1].rsplit(".", 1)[0]
            route = "/" + "/".join(
                part[1:-1] if part.startswith("[") and part.endswith("]") else part
                for part in route_parts
                if part
            )
            _add(
                {
                    "fact_type": "ui_route",
                    "method": None,
                    "path": route.rstrip("/") or "/",
                    "host": None,
                    "name": "Next.js Pages Router page",
                    "detail": {
                        "route_kind": "next_pages",
                        "trigger": "page_load",
                        "request_role": None,
                    },
                    "evidence_location": f"{rel}:1",
                }
            )

        for line_no, line in enumerate(text.splitlines(), start=1):
            if len(facts) >= _MAX_FACTS:
                break
            location = f"{rel}:{line_no}"

            if is_frontend_source:
                for pattern in _UI_ROUTE_PATTERNS:
                    m = pattern.search(line)
                    if m and m.groupdict().get("path"):
                        _add(
                            {
                                "fact_type": "ui_route",
                                "method": None,
                                "path": m.group("path"),
                                "host": None,
                                "name": "React Router route",
                                "detail": {
                                    "route_kind": "react_router",
                                    "trigger": "page_load",
                                    "request_role": None,
                                },
                                "evidence_location": location,
                            }
                        )
                        break

                for pattern in _UI_ACTION_PATTERNS:
                    m = pattern.search(line)
                    if m:
                        detail = {
                            "action_kind": (
                                "form_submit" if "submit" in line.lower() else "click"
                            ),
                            "handler": m.groupdict().get("handler"),
                            "label": (m.groupdict().get("label") or "").strip() or None,
                        }
                        semantic_action_covered = any(
                            semantic_fact.get("fact_type") == "ui_action"
                            and (
                                semantic_fact.get("evidence_location") == location
                                or (
                                    detail.get("handler")
                                    and semantic_fact.get("detail", {}).get("handler")
                                    == detail.get("handler")
                                )
                                or (
                                    detail.get("label")
                                    and (
                                        semantic_fact.get("name") == detail.get("label")
                                        or semantic_fact.get("detail", {}).get("label")
                                        == detail.get("label")
                                    )
                                )
                            )
                            for semantic_fact in semantic_frontend_facts
                        )
                        if semantic_action_covered:
                            break
                        _add(
                            {
                                "fact_type": "ui_action",
                                "method": None,
                                "path": None,
                                "host": None,
                                "name": detail.get("handler") or detail.get("label"),
                                "detail": detail,
                                "evidence_location": location,
                            }
                        )
                        break

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
                            "detail": {"request_role": "server_ingress"},
                            "evidence_location": location,
                        }
                    )
                    break

            for pattern in _HTTP_CALL_PATTERNS:
                m = pattern.search(line)
                if m:
                    url = m.group("url")
                    method = (m.groupdict().get("method") or "GET").upper()
                    normalized_url = _normalise_frontend_path(url) or url
                    frontend_role = (
                        source_roles.get(rel) if is_frontend_source else "server"
                    )
                    _add(
                        {
                            "fact_type": "http_call",
                            "method": method,
                            "path": normalized_url,
                            "host": _host_from_url(url),
                            "name": None,
                            "detail": {
                                "frontend": frontend_role == "browser",
                                "request_role": (
                                    "browser_request"
                                    if frontend_role == "browser"
                                    else "server_egress"
                                    if frontend_role == "server"
                                    else None
                                ),
                            },
                            "evidence_location": location,
                        }
                    )
                    break

            permit_all = _SPRING_PERMIT_ALL.search(line)
            if permit_all:
                args = permit_all.group("args")
                public_paths = re.findall(r"[\"']([^\"']+)[\"']", args)
                public_method = re.search(r"HttpMethod\.([A-Z]+)", args)
                for public_path in public_paths:
                    _add(
                        {
                            "fact_type": "auth_boundary",
                            "method": public_method.group(1) if public_method else None,
                            "path": public_path,
                            "host": None,
                            "name": "permitAll",
                            "detail": {
                                "scope": "path",
                                "public_paths": [public_path],
                                "public_methods": (
                                    [public_method.group(1)] if public_method else []
                                ),
                            },
                            "evidence_location": location,
                        }
                    )

            auth_marker = _AUTH_MARKERS.search(line)
            if auth_marker:
                is_global_spring_rule = bool(
                    spring_security["has_global_auth"]
                    and _SPRING_ANY_REQUEST_AUTHENTICATED.search(line)
                )
                _add(
                    {
                        "fact_type": "auth_boundary",
                        "method": None,
                        "path": None,
                        "host": None,
                        "name": auth_marker.group(0),
                        "detail": (
                            {
                                "scope": "global",
                                "protected_paths": spring_security["protected_paths"],
                                "rule": "anyRequest.authenticated",
                            }
                            if is_global_spring_rule
                            else {"scope": "local"}
                        ),
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

        existing_by_fingerprint = {row.fingerprint: row for row in existing_rows}
        for row in existing_rows:
            semantic_fingerprint = interface_fact_fingerprint(
                fact_type=row.fact_type,
                method=row.method,
                path=row.path,
                host=row.host,
                name=row.name,
            )
            existing_by_fingerprint.setdefault(semantic_fingerprint, row)

        for existing in existing_rows:
            try:
                detail = json.loads(existing.detail_json or "{}")
            except (TypeError, ValueError):
                detail = {}
            semantic_fingerprint = interface_fact_fingerprint(
                fact_type=existing.fact_type,
                method=existing.method,
                path=existing.path,
                host=existing.host,
                name=existing.name,
            )
            if (
                "llm" not in str(detail.get("origin") or "").lower()
                and existing.fingerprint not in desired
                and semantic_fingerprint not in desired
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
                    existing.fingerprint = fp
                    session.add(existing)
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
