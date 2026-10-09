"""Bounded parser adapters that emit framework-neutral repository facts.

Adapters describe program structure, never benchmark answers or vulnerability
claims. Unsupported syntax is reported explicitly so semantic closure cannot
mistake a partial model for complete coverage.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

_MAX_FILES = 4_000
_MAX_FILE_BYTES = 2 * 1024 * 1024


@dataclass
class AdapterResult:
    facts: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    files_seen: int = 0
    files_parsed: int = 0


class ParserAdapter(Protocol):
    name: str

    def accepts(self, path: Path) -> bool: ...
    def parse(self, path: Path, relative_path: str) -> AdapterResult: ...


def _fact(kind: str, name: str, path: str, line: int, **detail: Any) -> dict[str, Any]:
    return {
        "fact_type": kind,
        "name": name,
        "path": detail.pop("operation_path", None),
        "source": path,
        "evidence_location": f"{path}:{line}",
        "provenance": "parser",
        "detail": detail,
    }


class PythonAstAdapter:
    name = "python_ast"

    def accepts(self, path: Path) -> bool:
        return path.suffix.casefold() == ".py"

    def parse(self, path: Path, relative_path: str) -> AdapterResult:
        result = AdapterResult(files_seen=1)
        try:
            tree = ast.parse(path.read_text("utf-8", errors="replace"))
        except (OSError, SyntaxError) as exc:
            result.warnings.append(
                {"adapter": self.name, "path": relative_path, "reason": str(exc)[:300]}
            )
            return result
        result.files_parsed = 1
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = [ast.unparse(d) for d in node.decorator_list]
                route = next(
                    (
                        d
                        for d in decorators
                        if re.search(r"\.(get|post|put|patch|delete|route)\s*\(", d)
                    ),
                    None,
                )
                if route:
                    method = re.search(r"\.(get|post|put|patch|delete|route)", route)
                    literal = re.search(r"\(\s*['\"]([^'\"]+)", route)
                    result.facts.append(
                        _fact(
                            "route",
                            node.name,
                            relative_path,
                            node.lineno,
                            method=(method.group(1).upper() if method else ""),
                            operation_path=(literal.group(1) if literal else None),
                            symbol=node.name,
                        )
                    )
                else:
                    result.facts.append(
                        _fact(
                            "callable",
                            node.name,
                            relative_path,
                            node.lineno,
                            symbol=node.name,
                        )
                    )
            elif isinstance(node, ast.Call):
                called = ast.unparse(node.func)
                lower = called.casefold()
                if any(
                    term in lower
                    for term in (
                        "execute",
                        "eval",
                        "exec",
                        "popen",
                        "system",
                        "loads",
                        "open",
                    )
                ):
                    result.facts.append(
                        _fact(
                            "sensitive_operation",
                            called,
                            relative_path,
                            node.lineno,
                            api=called,
                        )
                    )
                if any(
                    term in lower
                    for term in (
                        "authorize",
                        "permission",
                        "authenticate",
                        "login_required",
                    )
                ):
                    result.facts.append(
                        _fact(
                            "auth_boundary",
                            called,
                            relative_path,
                            node.lineno,
                            api=called,
                        )
                    )
        return result


class EcmaScriptAdapter:
    name = "ecmascript_structure"
    _route = re.compile(
        r"\b(?:app|router|server)\.(get|post|put|patch|delete|use)\s*\(\s*['\"]([^'\"]+)",
        re.I,
    )
    _function = re.compile(
        r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\("
    )

    def accepts(self, path: Path) -> bool:
        return path.suffix.casefold() in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    def parse(self, path: Path, relative_path: str) -> AdapterResult:
        result = AdapterResult(files_seen=1)
        try:
            text = path.read_text("utf-8", errors="replace")
        except OSError as exc:
            result.warnings.append(
                {"adapter": self.name, "path": relative_path, "reason": str(exc)[:300]}
            )
            return result
        result.files_parsed = 1
        for line_no, line in enumerate(text.splitlines(), 1):
            for match in self._route.finditer(line):
                result.facts.append(
                    _fact(
                        "route",
                        match.group(2),
                        relative_path,
                        line_no,
                        method=match.group(1).upper(),
                        operation_path=match.group(2),
                    )
                )
            for match in self._function.finditer(line):
                result.facts.append(
                    _fact(
                        "callable",
                        match.group(1) or match.group(2),
                        relative_path,
                        line_no,
                    )
                )
            if re.search(
                r"\b(eval|exec|innerHTML|dangerouslySetInnerHTML|child_process|fetch|axios)\b",
                line,
            ):
                result.facts.append(
                    _fact(
                        "sensitive_operation",
                        line.strip()[:160],
                        relative_path,
                        line_no,
                    )
                )
        return result


def _lockfile_browser_libraries(
    name: str, text: str, yarn_entry: re.Pattern[str]
) -> list[tuple[str, str]]:
    """Resolved versions of tracked browser libraries from an npm/yarn lockfile.

    Lockfiles list every transitive package, so only libraries with known
    vulnerable version data are kept; the rest would crowd out other facts.
    """
    from aespa.services.js_libraries import library_for_package

    found: dict[tuple[str, str], None] = {}
    if name == "yarn.lock":
        for match in yarn_entry.finditer(text):
            if library_for_package(match.group("name")):
                found[(match.group("name"), match.group("version"))] = None
        return list(found)
    try:
        payload = json.loads(text)
    except ValueError:
        return []
    for key, info in (payload.get("packages") or {}).items():
        package = str(key).rsplit("node_modules/", 1)[-1]
        if (
            isinstance(info, dict)
            and info.get("version")
            and library_for_package(package)
        ):
            found[(package, str(info["version"]))] = None

    def _walk(deps: object) -> None:
        if not isinstance(deps, dict):
            return
        for package, info in deps.items():
            if not isinstance(info, dict):
                continue
            if info.get("version") and library_for_package(package):
                found[(package, str(info["version"]))] = None
            _walk(info.get("dependencies"))

    _walk(payload.get("dependencies"))
    return list(found)


class ManifestAdapter:
    name = "manifest"
    _names = {
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "pom.xml",
        "build.gradle",
        "go.mod",
        "cargo.toml",
        "composer.json",
        "gemfile",
        "packages.config",
        "directory.packages.props",
        "bower.json",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
    }
    _yarn_entry = re.compile(
        r'^"?(?P<name>@?[^@\s",]+)@[^\n]*:\s*\n(?:[ \t]+[^\n]*\n)*?[ \t]+version:?\s+"?(?P<version>[^"\s]+)',
        re.MULTILINE,
    )
    _suffixes = {".csproj", ".vbproj", ".fsproj"}
    _nuget_reference = re.compile(
        r"<(?P<tag>PackageReference|PackageVersion)\b(?P<attrs>[^>]*?)(?:/>|>(?P<body>.*?)</(?P=tag)\s*>)",
        re.IGNORECASE | re.DOTALL,
    )
    _nuget_package = re.compile(
        r"<package\b[^>]*?\bid\s*=\s*\"(?P<name>[^\"]+)\"[^>]*?\bversion\s*=\s*\"(?P<version>[^\"]*)\"",
        re.IGNORECASE,
    )

    def accepts(self, path: Path) -> bool:
        return (
            path.name.casefold() in self._names
            or path.suffix.casefold() in self._suffixes
        )

    def parse(self, path: Path, relative_path: str) -> AdapterResult:
        result = AdapterResult(files_seen=1, files_parsed=1)
        try:
            text = path.read_text("utf-8", errors="replace")
        except OSError as exc:
            result.files_parsed = 0
            result.warnings.append(
                {"adapter": self.name, "path": relative_path, "reason": str(exc)[:300]}
            )
            return result
        dependencies: list[tuple[str, str]] = []
        lowered = path.name.casefold()
        if lowered in {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock"}:
            dependencies = _lockfile_browser_libraries(lowered, text, self._yarn_entry)
        elif lowered in {"package.json", "bower.json"}:
            try:
                payload = json.loads(text)
                for group in (
                    "dependencies",
                    "optionalDependencies",
                    "devDependencies",
                ):
                    dependencies.extend(
                        (name, str(version))
                        for name, version in (payload.get(group) or {}).items()
                    )
            except (ValueError, AttributeError):
                result.warnings.append(
                    {
                        "adapter": self.name,
                        "path": relative_path,
                        "reason": f"invalid {path.name}",
                    }
                )
        elif path.suffix.casefold() in self._suffixes or path.name.casefold() in {
            "packages.config",
            "directory.packages.props",
        }:
            for match in self._nuget_reference.finditer(text):
                attrs = match.group("attrs")
                name = re.search(r"\bInclude\s*=\s*\"([^\"]+)\"", attrs, re.I)
                if name is None:
                    continue
                version_attr = re.search(r"\bVersion\s*=\s*\"([^\"]*)\"", attrs, re.I)
                version = version_attr.group(1) if version_attr else ""
                if not version and match.group("body"):
                    nested = re.search(
                        r"<Version>\s*([^<\s]+)\s*</Version>", match.group("body"), re.I
                    )
                    version = nested.group(1) if nested else ""
                dependencies.append((name.group(1), version or "unresolved"))
            for match in self._nuget_package.finditer(text):
                dependencies.append((match.group("name"), match.group("version")))
        elif path.name.casefold() == "requirements.txt":
            for line in text.splitlines():
                match = re.match(
                    r"\s*([A-Za-z0-9_.-]+)\s*(?:==|~=|>=|<=)?\s*([^;#\s]*)", line
                )
                if match and not line.lstrip().startswith("#"):
                    dependencies.append((match.group(1), match.group(2)))
        else:
            dependencies.extend(
                (m.group(1), m.group(2))
                for m in re.finditer(
                    r"['\"]?([A-Za-z0-9_.@/-]{2,})['\"]?\s*[:= ]\s*['\"]?([v~^<>=]*\d+(?:\.\d+){0,3}[^\s,'\"<)]*)",
                    text,
                )
            )
        for name, version in dependencies[:2_000]:
            line = text[: text.find(name)].count("\n") + 1 if name in text else 1
            result.facts.append(
                _fact(
                    "dependency",
                    name,
                    relative_path,
                    line,
                    version=version,
                    manifest=relative_path,
                )
            )
        return result


_TREE_SITTER_SKIP = {
    "vendor",
    "vendors",
    "third_party",
    "third-party",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    "packages",
    "bower_components",
}
_HTTP_VERBS = {"get", "post", "put", "patch", "delete", "options", "head"}
_ROUTE_CALLEES = _HTTP_VERBS | {"any", "all", "match", "route", "use"}
_ALWAYS_ROUTE_CALLEES = {
    "MapGet": "GET",
    "MapPost": "POST",
    "MapPut": "PUT",
    "MapPatch": "PATCH",
    "MapDelete": "DELETE",
    "MapMethods": None,
    "MapFallback": None,
    "HandleFunc": None,
    "Handle": None,
    "addRoute": None,
    "add_route": None,
    "register_rest_route": None,
}
_CLIENT_RECEIVER = re.compile(
    r"(?:^|[^\w$])(?:\$|\$http|http|https|axios|client|\w*Client|fetch|request|requests|superagent|got|ky|api|cache|map|params|headers|session|config|this\.http)$",
    re.IGNORECASE,
)
_FIRST_STRING = re.compile(
    r"^\s*(?:<[^>]*>)?\s*\(?\s*(?:pattern\s*:\s*)?@?(['\"`])(?P<path>[^'\"`]*)\1"
)
_ANNOTATION_AUTH = re.compile(
    r"\[\s*(?P<cs>Authorize|AllowAnonymous)\b[^\]]*\]"
    r"|@(?P<java>PreAuthorize|PostAuthorize|Secured|RolesAllowed|PermitAll|DenyAll)\b"
    r"|#\[(?P<php>IsGranted|Security)\b"
)
_PHP_ROUTE_ATTRIBUTE = re.compile(
    r"#\[\s*Route\s*\(\s*(?:path\s*:\s*)?['\"](?P<path>[^'\"]+)['\"](?P<rest>[^\]]*)\]"
)
_FACT_PRIORITY = {
    "route": 0,
    "auth_boundary": 1,
    "sensitive_operation": 2,
    "dependency": 3,
    "callable": 4,
}


class TreeSitterAdapter:
    """Structure facts for PHP, JavaScript, TypeScript, Java, Go, C#, and Ruby.

    Uses the shared tree-sitter code graph so routes, sensitive calls, and
    authorization checks carry their enclosing function and whether a route
    or entry point reaches them.
    """

    name = "tree_sitter"

    def __init__(self) -> None:
        from aespa.services import sast_codegraph

        self._codegraph = sast_codegraph

    def accepts(self, path: Path) -> bool:
        language = self._codegraph.language_for_path(path.name)
        return language is not None and language != "python"

    def parse_many(
        self, files: list[tuple[str, Path]]
    ) -> tuple[AdapterResult, set[str]]:
        from aespa.services import component_facts
        from aespa.services.sast_workprogram import _PATTERNS, _handler_scope

        codegraph = self._codegraph
        result = AdapterResult(files_seen=len(files))
        graph = codegraph.build_code_graph(files)
        result.files_parsed = len(graph.parsed_files)
        for warning in graph.warnings[:50]:
            result.warnings.append(
                {
                    "adapter": self.name,
                    "path": warning.get("path", ""),
                    "reason": warning.get("reason", "")[:300],
                }
            )
        sink_patterns = [
            item
            for item in _PATTERNS
            if item.kind == "sink" and item.name != "Authorization decision"
        ]
        auth_patterns = [
            item
            for item in _PATTERNS
            if (
                item.kind == "control"
                and item.category in {"authentication", "authorization"}
            )
            or item.name == "Authorization decision"
        ]
        disk_by_rel = dict(files)
        routes: list[tuple[str, int, str | None, str, str]] = []
        roots = {graph.module_key(rel) for rel in graph.parsed_files}
        route_lines: set[tuple[str, int]] = set()
        texts: dict[str, str] = {}
        for rel, language in graph.parsed_files.items():
            try:
                text = disk_by_rel[rel].read_text("utf-8", errors="replace")
            except OSError:
                continue
            texts[rel] = text
            if language == "c_sharp":
                declared = component_facts._aspnet_route_facts(text, rel)
            elif language == "java":
                declared = component_facts._spring_route_facts(text, rel)
            else:
                declared = []
            for fact in declared:
                line = int(str(fact["evidence_location"]).rsplit(":", 1)[1])
                routes.append(
                    (rel, line, fact.get("method"), fact.get("path") or "/", "declared")
                )
            if language == "php":
                for line_no, line_text in enumerate(text.splitlines(), 1):
                    attribute = _PHP_ROUTE_ATTRIBUTE.search(line_text)
                    if attribute:
                        verb = re.search(
                            r"methods\s*:\s*\[\s*['\"](\w+)", attribute.group("rest")
                        )
                        routes.append(
                            (
                                rel,
                                line_no,
                                verb.group(1).upper() if verb else None,
                                attribute.group("path"),
                                "declared",
                            )
                        )
        for call in graph.calls:
            if call.kind == "ref":
                continue
            route = _route_from_call(call, graph.parsed_files.get(call.path, ""))
            if route is not None:
                routes.append((call.path, call.line, route[0], route[1], "registered"))
                route_lines.add((call.path, call.line))
        for rel, line, _method, _path, kind in routes:
            enclosing = graph.enclosing_def(rel, line)
            if enclosing is not None and kind == "declared":
                roots.add(enclosing.key)
        for call in graph.calls:
            if (call.path, call.line) in route_lines:
                roots.update(call.targets)
        for rel in graph.parsed_files:
            if _handler_scope(rel):
                roots.update(item.key for item in graph.defs_in_file(rel))
        graph.compute_reachability(roots)

        def _context(rel: str, line: int) -> dict[str, Any]:
            status, enclosing = graph.status_for(rel, line)
            if enclosing is None:
                return {}
            context: dict[str, Any] = {
                "symbol": enclosing.qualname,
                "function": enclosing.label,
                "reachability": status,
            }
            if status == codegraph.REACHABLE:
                chain = graph.path_to(enclosing.key)
                if len(chain) > 1:
                    context["reached_from"] = [
                        graph.defs[key].label for key in chain if key in graph.defs
                    ][:8]
            return context

        seen_routes: set[tuple[str, int, str | None, str]] = set()
        for rel, line, method, route_path, kind in routes:
            identity = (rel, line, method, route_path)
            if identity in seen_routes:
                continue
            seen_routes.add(identity)
            context = _context(rel, line)
            symbol = context.get("symbol") if kind == "declared" else None
            result.facts.append(
                _fact(
                    "route",
                    symbol or route_path,
                    rel,
                    line,
                    method=(method or "").upper(),
                    operation_path=route_path,
                    route_kind=kind,
                    **context,
                )
            )
        seen_calls: set[tuple[str, int, str]] = set()
        for call in graph.calls:
            if call.kind == "ref" or not call.text:
                continue
            for pattern in sink_patterns:
                if not pattern.regex.search(call.text):
                    continue
                identity = (call.path, call.line, pattern.name)
                if identity in seen_calls:
                    break
                seen_calls.add(identity)
                result.facts.append(
                    _fact(
                        "sensitive_operation",
                        call.text[:160],
                        call.path,
                        call.line,
                        api=call.callee_name,
                        category=pattern.name,
                        **_context(call.path, call.line),
                    )
                )
                break
            for pattern in auth_patterns:
                if not pattern.regex.search(call.text):
                    continue
                identity = (call.path, call.line, "auth")
                if identity in seen_calls:
                    break
                seen_calls.add(identity)
                result.facts.append(
                    _fact(
                        "auth_boundary",
                        call.callee_name or call.text[:120],
                        call.path,
                        call.line,
                        api=call.text[:160],
                        **_context(call.path, call.line),
                    )
                )
                break
        for rel, text in texts.items():
            for line_no, line_text in enumerate(text.splitlines(), 1):
                for match in _ANNOTATION_AUTH.finditer(line_text):
                    marker = (
                        match.group("cs") or match.group("java") or match.group("php")
                    )
                    result.facts.append(
                        _fact(
                            "auth_boundary",
                            match.group(0)[:120],
                            rel,
                            line_no,
                            api=marker,
                            allows_anonymous=marker in {"AllowAnonymous", "PermitAll"},
                            **_context(rel, line_no),
                        )
                    )
        for item in graph.defs.values():
            if item.name == codegraph.MODULE_SCOPE:
                continue
            result.facts.append(
                _fact(
                    "callable",
                    item.qualname,
                    item.path,
                    item.start_line,
                    symbol=item.qualname,
                    reachability=graph.reachability.get(item.key, codegraph.UNKNOWN),
                )
            )
        return result, set(graph.parsed_files)


def _route_from_call(call: Any, language: str) -> tuple[str | None, str] | None:
    callee = call.callee_name
    if callee in _ALWAYS_ROUTE_CALLEES:
        method = _ALWAYS_ROUTE_CALLEES[callee]
    elif callee.casefold() in _ROUTE_CALLEES:
        if not call.receiver:
            if language != "ruby":
                return None
        elif _CLIENT_RECEIVER.search(call.receiver.strip()):
            return None
        method = callee.upper() if callee.casefold() in _HTTP_VERBS else None
    elif (
        language == "ruby" and callee in {"resources", "resource"} and not call.receiver
    ):
        symbol = re.match(r"^\s*\(?\s*:(\w+)", call.text[len(callee) :])
        return (None, f"/{symbol.group(1)}") if symbol else None
    else:
        return None
    start = call.text.find(callee)
    if start < 0:
        return None
    literal = _FIRST_STRING.match(call.text[start + len(callee) :])
    if literal is None:
        return None
    route_path = literal.group("path")
    verb_prefix = re.match(
        r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/.*)$", route_path
    )
    if verb_prefix:
        method, route_path = verb_prefix.group(1), verb_prefix.group(2)
    if not route_path.startswith("/"):
        if language == "ruby" and route_path and "://" not in route_path:
            route_path = "/" + route_path
        elif callee in _ALWAYS_ROUTE_CALLEES and "://" not in route_path:
            route_path = "/" + route_path
        else:
            return None
    return method, route_path


def extract_parser_facts(root: Path) -> AdapterResult:
    combined = AdapterResult()
    ecmascript = EcmaScriptAdapter()
    adapters: tuple[ParserAdapter, ...] = (
        PythonAstAdapter(),
        ManifestAdapter(),
    )
    try:
        tree_sitter: TreeSitterAdapter | None = TreeSitterAdapter()
    except Exception:  # noqa: BLE001 - fall back to the regex adapter
        tree_sitter = None
    structured: list[tuple[str, Path]] = []
    for index, path in enumerate(sorted(root.rglob("*"))):
        if index >= _MAX_FILES:
            combined.warnings.append(
                {
                    "adapter": "inventory",
                    "path": "",
                    "reason": f"parser file cap {_MAX_FILES} reached",
                }
            )
            break
        if not path.is_file() or ".git" in path.parts or "node_modules" in path.parts:
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        adapter = next(
            (candidate for candidate in adapters if candidate.accepts(path)), None
        )
        if adapter is None:
            if tree_sitter is not None and tree_sitter.accepts(path):
                parts = {part.casefold() for part in path.relative_to(root).parts[:-1]}
                if not parts & _TREE_SITTER_SKIP and not (
                    "wwwroot" in parts and "lib" in parts
                ):
                    structured.append((relative, path))
                continue
            if ecmascript.accepts(path):
                _merge(combined, ecmascript.parse(path, relative))
            continue
        _merge(combined, adapter.parse(path, relative))
    if tree_sitter is not None and structured:
        parsed, parsed_paths = tree_sitter.parse_many(structured)
        _merge(combined, parsed)
        for relative, path in structured:
            if relative not in parsed_paths and ecmascript.accepts(path):
                fallback = ecmascript.parse(path, relative)
                fallback.files_seen = 0
                _merge(combined, fallback)
    combined.facts.sort(key=lambda fact: _FACT_PRIORITY.get(fact["fact_type"], 5))
    return combined


def _merge(combined: AdapterResult, parsed: AdapterResult) -> None:
    combined.facts.extend(parsed.facts)
    combined.edges.extend(parsed.edges)
    combined.warnings.extend(parsed.warnings)
    combined.files_seen += parsed.files_seen
    combined.files_parsed += parsed.files_parsed
