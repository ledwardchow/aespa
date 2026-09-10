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
    }

    def accepts(self, path: Path) -> bool:
        return path.name.casefold() in self._names

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
        if path.name.casefold() == "package.json":
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
                        "reason": "invalid package.json",
                    }
                )
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


def extract_parser_facts(root: Path) -> AdapterResult:
    combined = AdapterResult()
    adapters: tuple[ParserAdapter, ...] = (
        PythonAstAdapter(),
        EcmaScriptAdapter(),
        ManifestAdapter(),
    )
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
            continue
        parsed = adapter.parse(path, relative)
        combined.facts.extend(parsed.facts)
        combined.edges.extend(parsed.edges)
        combined.warnings.extend(parsed.warnings)
        combined.files_seen += parsed.files_seen
        combined.files_parsed += parsed.files_parsed
    return combined
