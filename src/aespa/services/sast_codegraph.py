"""Tree-sitter code graph for SAST scope.

Parses production source into function definitions and call sites, resolves
calls to definitions by name, and works out which functions can be reached
from entry points. No LLM calls and no network: grammars ship as wheels.

Name resolution is approximate because tree-sitter has no type information.
A call is matched to definitions with the same name, preferring the caller's
own class for ``this``/``self`` receivers, a named class for static calls,
then the same file, then the closest directories. Reachability is therefore
a hint for ordering and grouping work, never a reason to skip code.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

log = logging.getLogger(__name__)

MODULE_SCOPE = "<module>"
_MAX_FILE_BYTES = 1_000_000
_MAX_TARGETS = 3
_MAX_CALL_TEXT = 300
_MAX_PATH_HOPS = 8

REACHABLE = "reachable"
NO_CALLERS = "no_callers"
NOT_REACHED = "not_reached"
UNKNOWN = "unknown"

_SELF_RECEIVERS = {"$this", "this", "self", "static", "self::", "static::", "$self"}


def _load_php() -> Any:
    import tree_sitter_php

    return tree_sitter_php.language_php()


def _load_javascript() -> Any:
    import tree_sitter_javascript

    return tree_sitter_javascript.language()


def _load_typescript() -> Any:
    import tree_sitter_typescript

    return tree_sitter_typescript.language_typescript()


def _load_tsx() -> Any:
    import tree_sitter_typescript

    return tree_sitter_typescript.language_tsx()


def _load_python() -> Any:
    import tree_sitter_python

    return tree_sitter_python.language()


def _load_java() -> Any:
    import tree_sitter_java

    return tree_sitter_java.language()


def _load_go() -> Any:
    import tree_sitter_go

    return tree_sitter_go.language()


def _load_c_sharp() -> Any:
    import tree_sitter_c_sharp

    return tree_sitter_c_sharp.language()


def _load_ruby() -> Any:
    import tree_sitter_ruby

    return tree_sitter_ruby.language()


_JS_DEFS = (
    "function_declaration",
    "generator_function_declaration",
    "method_definition",
    "function_expression",
    "function",
    "generator_function",
    "arrow_function",
)
_JS_CLASSES = ("class_declaration", "class", "abstract_class_declaration")
_JS_CALLS = ("call_expression", "new_expression")
# A function name passed as a value, e.g. `router.add("/x", render)`,
# `{ "/x": render }` or `el.addEventListener("click", this.onClick)`.
_JS_REFS = """
(arguments (identifier) @ref)
(arguments (member_expression property: (property_identifier) @ref))
(pair value: (identifier) @ref)
(array (identifier) @ref)
(object (shorthand_property_identifier) @ref)
"""
_JSX_REFS = _JS_REFS + "(jsx_expression (identifier) @ref)\n"
_PY_REFS = """
(argument_list (identifier) @ref)
(keyword_argument value: (identifier) @ref)
(pair value: (identifier) @ref)
(list (identifier) @ref)
"""


@dataclass(frozen=True)
class _LangSpec:
    name: str
    loader: Callable[[], Any]
    defs: tuple[str, ...]
    classes: tuple[str, ...]
    calls: tuple[str, ...]
    refs: str = ""


_SPECS: dict[str, _LangSpec] = {
    "php": _LangSpec(
        "php",
        _load_php,
        (
            "function_definition",
            "method_declaration",
            "anonymous_function",
            "anonymous_function_creation_expression",
            "arrow_function",
        ),
        (
            "class_declaration",
            "interface_declaration",
            "trait_declaration",
            "enum_declaration",
        ),
        (
            "function_call_expression",
            "member_call_expression",
            "nullsafe_member_call_expression",
            "scoped_call_expression",
            "object_creation_expression",
            "include_expression",
            "include_once_expression",
            "require_expression",
            "require_once_expression",
        ),
    ),
    "javascript": _LangSpec(
        "javascript", _load_javascript, _JS_DEFS, _JS_CLASSES, _JS_CALLS, _JSX_REFS
    ),
    "typescript": _LangSpec(
        "typescript", _load_typescript, _JS_DEFS, _JS_CLASSES, _JS_CALLS, _JS_REFS
    ),
    "tsx": _LangSpec("tsx", _load_tsx, _JS_DEFS, _JS_CLASSES, _JS_CALLS, _JSX_REFS),
    "python": _LangSpec(
        "python",
        _load_python,
        ("function_definition",),
        ("class_definition",),
        ("call",),
        _PY_REFS,
    ),
    "java": _LangSpec(
        "java",
        _load_java,
        ("method_declaration", "constructor_declaration"),
        (
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        ),
        ("method_invocation", "object_creation_expression"),
    ),
    "go": _LangSpec(
        "go",
        _load_go,
        ("function_declaration", "method_declaration"),
        (),
        ("call_expression",),
    ),
    "c_sharp": _LangSpec(
        "c_sharp",
        _load_c_sharp,
        (
            "method_declaration",
            "constructor_declaration",
            "local_function_statement",
        ),
        (
            "class_declaration",
            "interface_declaration",
            "struct_declaration",
            "record_declaration",
        ),
        ("invocation_expression", "object_creation_expression"),
    ),
    "ruby": _LangSpec(
        "ruby",
        _load_ruby,
        ("method", "singleton_method"),
        ("class", "module"),
        ("call",),
    ),
}

_LANGUAGE_BY_SUFFIX = {
    ".php": "php",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".py": "python",
    ".java": "java",
    ".go": "go",
    ".cs": "c_sharp",
    ".rb": "ruby",
}

# Calls only resolve within a family; JS and TS modules import each other.
_FAMILY = {"javascript": "js", "typescript": "js", "tsx": "js"}
# Languages where an unqualified call inside a class usually means `this.`.
_IMPLICIT_THIS = {"java", "c_sharp", "ruby"}


def language_for_path(path: str) -> str | None:
    return _LANGUAGE_BY_SUFFIX.get(PurePosixPath(path).suffix.casefold())


@dataclass
class CodeDef:
    key: str
    path: str
    language: str
    name: str
    qualname: str
    kind: str
    start_line: int
    end_line: int
    start_byte: int = 0
    end_byte: int = 0
    class_name: str = ""

    @property
    def label(self) -> str:
        if self.name == MODULE_SCOPE:
            return f"{self.path} (top level)"
        return f"{self.qualname} ({self.path}:{self.start_line})"


@dataclass
class CodeCall:
    path: str
    line: int
    caller_key: str
    callee_name: str
    receiver: str
    kind: str
    text: str
    targets: list[str] = field(default_factory=list)


@dataclass
class CodeGraph:
    defs: dict[str, CodeDef] = field(default_factory=dict)
    calls: list[CodeCall] = field(default_factory=list)
    parsed_files: dict[str, str] = field(default_factory=dict)
    warnings: list[dict[str, str]] = field(default_factory=list)
    reachability: dict[str, str] = field(default_factory=dict)
    roots: set[str] = field(default_factory=set)
    _parent: dict[str, str | None] = field(default_factory=dict)
    _defs_by_file: dict[str, list[CodeDef]] = field(default_factory=dict)
    _calls_by_line: dict[tuple[str, int], list[CodeCall]] = field(default_factory=dict)

    def is_parsed(self, path: str) -> bool:
        return path in self.parsed_files

    def calls_on_line(self, path: str, line: int) -> list[CodeCall]:
        return self._calls_by_line.get((path, line), [])

    def module_key(self, path: str) -> str:
        return f"{path}::{MODULE_SCOPE}"

    def enclosing_def(self, path: str, line: int) -> CodeDef | None:
        """Innermost function containing ``line``, else the file's top level."""
        best: CodeDef | None = None
        for item in self._defs_by_file.get(path, []):
            if item.name == MODULE_SCOPE:
                continue
            if item.start_line <= line <= item.end_line and (
                best is None
                or item.end_line - item.start_line < best.end_line - best.start_line
            ):
                best = item
        if best is not None:
            return best
        return self.defs.get(self.module_key(path))

    def defs_in_file(self, path: str) -> list[CodeDef]:
        return list(self._defs_by_file.get(path, []))

    def status_for(self, path: str, line: int) -> tuple[str, CodeDef | None]:
        if not self.is_parsed(path):
            return UNKNOWN, None
        item = self.enclosing_def(path, line)
        if item is None:
            return UNKNOWN, None
        return self.reachability.get(item.key, UNKNOWN), item

    def path_to(self, key: str) -> list[str]:
        """Shortest known chain of functions from an entry point to ``key``."""
        chain: list[str] = []
        current: str | None = key
        while current is not None and len(chain) <= _MAX_PATH_HOPS:
            chain.append(current)
            current = self._parent.get(current)
        chain.reverse()
        return chain

    def compute_reachability(self, roots: Iterable[str]) -> None:
        edges: dict[str, set[str]] = defaultdict(set)
        incoming: set[str] = set()
        for call in self.calls:
            for target in call.targets:
                if target == call.caller_key:
                    continue
                edges[call.caller_key].add(target)
                incoming.add(target)
        self.roots = {key for key in roots if key in self.defs}
        self._parent = {key: None for key in self.roots}
        queue = deque(sorted(self.roots))
        while queue:
            current = queue.popleft()
            for target in sorted(edges.get(current, ())):
                if target not in self._parent:
                    self._parent[target] = current
                    queue.append(target)
        self.reachability = {}
        for key in self.defs:
            if key in self._parent:
                self.reachability[key] = REACHABLE
            elif key not in incoming:
                self.reachability[key] = NO_CALLERS
            else:
                self.reachability[key] = NOT_REACHED

    def stats(self) -> dict[str, Any]:
        languages: dict[str, int] = defaultdict(int)
        for language in self.parsed_files.values():
            languages[language] += 1
        functions = [item for item in self.defs.values() if item.name != MODULE_SCOPE]
        statuses: dict[str, int] = defaultdict(int)
        for item in functions:
            statuses[self.reachability.get(item.key, UNKNOWN)] += 1
        direct_calls = [call for call in self.calls if call.kind != "ref"]
        return {
            "files_parsed": len(self.parsed_files),
            "languages": dict(sorted(languages.items())),
            "functions": len(functions),
            "calls": len(direct_calls),
            "resolved_calls": sum(bool(call.targets) for call in direct_calls),
            "function_reachability": dict(statuses),
            "warnings": len(self.warnings),
        }


class _Parsers:
    """Load each grammar once; a grammar that fails is disabled for the run."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, Any, list[str]] | None] = {}

    def get(self, language: str, warnings: list[dict[str, str]]):
        if language in self._cache:
            return self._cache[language]
        spec = _SPECS[language]
        try:
            import tree_sitter as ts

            ts_language = ts.Language(spec.loader())
            groups = []
            for capture, kinds in (
                ("def", spec.defs),
                ("class", spec.classes),
                ("call", spec.calls),
            ):
                known = [
                    kind
                    for kind in kinds
                    if ts_language.id_for_node_kind(kind, True) is not None
                ]
                if known:
                    groups.append(
                        "[" + " ".join(f"({kind})" for kind in known) + "] @" + capture
                    )
            if spec.refs:
                groups.append(spec.refs)
            query = ts.Query(ts_language, "\n".join(groups))
            loaded = (ts.Parser(ts_language), query, [])
        except Exception as exc:  # noqa: BLE001 - any grammar failure disables it
            log.warning("tree-sitter grammar %s unavailable: %s", language, exc)
            warnings.append(
                {"language": language, "reason": f"grammar unavailable: {exc}"}
            )
            loaded = None
        self._cache[language] = loaded
        return loaded


def _text(node: Any) -> str:
    if node is None:
        return ""
    try:
        return node.text.decode("utf-8", errors="replace")
    except AttributeError:
        return ""


def _field(node: Any, name: str) -> Any:
    return node.child_by_field_name(name) if node is not None else None


def _last_name(value: str) -> str:
    for separator in ("\\", "::", "->", "?->", "."):
        value = value.rsplit(separator, 1)[-1]
    return value.strip().lstrip("$")


def _def_name(node: Any) -> str:
    name = _field(node, "name")
    if name is not None:
        return _text(name)
    parent = node.parent
    if parent is None:
        return ""
    if parent.type == "variable_declarator":
        return _text(_field(parent, "name"))
    if parent.type == "pair":
        return _text(_field(parent, "key")).strip("'\"")
    if parent.type in {"assignment_expression", "assignment"}:
        return _last_name(_text(_field(parent, "left")))
    if parent.type in {"public_field_definition", "field_definition"}:
        return _text(_field(parent, "name") or _field(parent, "property"))
    return ""


def _def_span(node: Any) -> Any:
    parent = node.parent
    if parent is not None and parent.type == "decorated_definition":
        return parent
    return node


def _class_name(node: Any) -> str:
    return _text(_field(node, "name"))


def _go_receiver_type(node: Any) -> str:
    receiver = _field(node, "receiver")
    if receiver is None:
        return ""
    text = _text(receiver).strip("() ")
    return text.split()[-1].lstrip("*") if text else ""


def _call_parts(node: Any, language: str) -> tuple[str, str, str]:
    """Return ``(callee_name, receiver, kind)`` for a call-like node."""
    kind = node.type
    if kind in {
        "include_expression",
        "include_once_expression",
        "require_expression",
        "require_once_expression",
    }:
        return "", "", "include"
    if kind in {"object_creation_expression", "new_expression"}:
        target = _field(node, "type") or _field(node, "constructor")
        if target is None:
            target = next(
                (
                    child
                    for child in node.named_children
                    if child.type in {"name", "qualified_name", "identifier"}
                ),
                None,
            )
        return _last_name(_text(target)), "", "new"
    if language == "php":
        if kind == "function_call_expression":
            return _last_name(_text(_field(node, "function"))), "", "call"
        if kind in {"member_call_expression", "nullsafe_member_call_expression"}:
            return (
                _text(_field(node, "name")),
                _text(_field(node, "object")),
                "call",
            )
        if kind == "scoped_call_expression":
            return (
                _text(_field(node, "name")),
                _text(_field(node, "scope")),
                "call",
            )
    if language == "java":
        return _text(_field(node, "name")), _text(_field(node, "object")), "call"
    if language == "ruby":
        return (
            _text(_field(node, "method")),
            _text(_field(node, "receiver")),
            "call",
        )
    function = _field(node, "function")
    if function is None:
        return "", "", "call"
    if function.type in {"member_expression", "attribute", "selector_expression"}:
        obj = (
            _field(function, "object")
            or _field(function, "operand")
            or _field(function, "expression")
        )
        prop = (
            _field(function, "property")
            or _field(function, "attribute")
            or _field(function, "field")
        )
        return _text(prop), _text(obj), "call"
    if function.type == "member_access_expression":
        return (
            _text(_field(function, "name")),
            _text(_field(function, "expression")),
            "call",
        )
    return _last_name(_text(function)), "", "call"


def _callee_line(node: Any) -> int:
    for name in ("name", "function", "method", "constructor", "type"):
        child = _field(node, name)
        if child is not None:
            return child.end_point[0] + 1
    return node.start_point[0] + 1


def _innermost(spans: list[CodeDef], start: int, end: int) -> CodeDef | None:
    best: CodeDef | None = None
    for item in spans:
        if (
            item.start_byte <= start
            and end <= item.end_byte
            and (
                best is None
                or item.end_byte - item.start_byte < best.end_byte - best.start_byte
            )
        ):
            best = item
    return best


def _parse_file(
    graph: CodeGraph, rel: str, raw: bytes, language: str, parser: Any, query: Any
) -> None:
    import tree_sitter as ts

    tree = parser.parse(raw)
    captures = ts.QueryCursor(query).captures(tree.root_node)
    line_count = raw.count(b"\n") + 1
    module = CodeDef(
        key=graph.module_key(rel),
        path=rel,
        language=language,
        name=MODULE_SCOPE,
        qualname=MODULE_SCOPE,
        kind="module",
        start_line=1,
        end_line=line_count,
        start_byte=0,
        end_byte=len(raw),
    )
    file_defs: list[CodeDef] = [module]
    classes = [
        CodeDef(
            key="",
            path=rel,
            language=language,
            name=_class_name(node),
            qualname=_class_name(node),
            kind="class",
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        )
        for node in captures.get("class", [])
    ]
    for node in sorted(captures.get("def", []), key=lambda item: item.start_byte):
        name = _def_name(node)
        if not name:
            continue
        span = _def_span(node)
        owner = _innermost(classes, node.start_byte, node.end_byte)
        class_name = owner.name if owner else ""
        if language == "go" and node.type == "method_declaration":
            class_name = _go_receiver_type(node)
        qualname = f"{class_name}.{name}" if class_name else name
        start_line = span.start_point[0] + 1
        key = f"{rel}::{qualname}@{start_line}"
        file_defs.append(
            CodeDef(
                key=key,
                path=rel,
                language=language,
                name=name,
                qualname=qualname,
                kind="method" if class_name else "function",
                start_line=start_line,
                end_line=span.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                class_name=class_name,
            )
        )
    for item in file_defs:
        graph.defs[item.key] = item
    graph._defs_by_file[rel] = file_defs

    for node in captures.get("call", []):
        callee, receiver, kind = _call_parts(node, language)
        caller = _innermost(file_defs, node.start_byte, node.end_byte) or module
        text = " ".join(_text(node).split())[:_MAX_CALL_TEXT]
        call = CodeCall(
            path=rel,
            line=_callee_line(node),
            caller_key=caller.key,
            callee_name=callee,
            receiver=receiver[:120],
            kind=kind,
            text=text,
        )
        graph.calls.append(call)
        graph._calls_by_line.setdefault((rel, call.line), []).append(call)
    for node in captures.get("ref", []):
        caller = _innermost(file_defs, node.start_byte, node.end_byte) or module
        graph.calls.append(
            CodeCall(
                path=rel,
                line=node.start_point[0] + 1,
                caller_key=caller.key,
                callee_name=_text(node),
                receiver="",
                kind="ref",
                text="",
            )
        )


def _dir_affinity(first: str, second: str) -> int:
    a = PurePosixPath(first).parts[:-1]
    b = PurePosixPath(second).parts[:-1]
    shared = 0
    for left, right in zip(a, b):
        if left != right:
            break
        shared += 1
    return shared


def _resolve(graph: CodeGraph) -> None:
    by_name: dict[tuple[str, str], list[CodeDef]] = defaultdict(list)
    by_class: dict[tuple[str, str], list[CodeDef]] = defaultdict(list)
    for item in graph.defs.values():
        if item.name == MODULE_SCOPE:
            continue
        family = _FAMILY.get(item.language, item.language)
        by_name[(family, item.name)].append(item)
        if item.class_name:
            by_class[(family, item.class_name)].append(item)
    for call in graph.calls:
        caller = graph.defs.get(call.caller_key)
        if caller is None:
            continue
        family = _FAMILY.get(caller.language, caller.language)
        if call.kind == "new":
            candidates = [
                item
                for item in by_class.get((family, call.callee_name), [])
                if item.name in {"__construct", "constructor", "initialize"}
                or item.name == call.callee_name
            ]
        elif call.callee_name:
            candidates = list(by_name.get((family, call.callee_name), []))
        else:
            candidates = []
        if not candidates:
            continue
        receiver = call.receiver.strip()
        if (
            not receiver
            and call.kind == "call"
            and caller.class_name
            and caller.language in _IMPLICIT_THIS
        ):
            receiver = "this"
        if receiver in _SELF_RECEIVERS or receiver in {"parent", "super"}:
            same_class = [
                item for item in candidates if item.class_name == caller.class_name
            ]
            if same_class and receiver not in {"parent", "super"}:
                candidates = same_class
        elif receiver and receiver.lstrip("\\")[:1].isupper():
            owner = _last_name(receiver)
            owned = [item for item in candidates if item.class_name == owner]
            if owned:
                candidates = owned
        same_file = [item for item in candidates if item.path == call.path]
        if same_file:
            candidates = same_file
        if len(candidates) > _MAX_TARGETS:
            candidates.sort(
                key=lambda item: (-_dir_affinity(item.path, call.path), item.key)
            )
            candidates = candidates[:_MAX_TARGETS]
        call.targets = [item.key for item in candidates]
    # References that name no known function are just variables.
    graph.calls = [call for call in graph.calls if call.kind != "ref" or call.targets]


def build_code_graph(files: Iterable[tuple[str, Path]]) -> CodeGraph:
    """Parse ``(relative_path, disk_path)`` pairs into a resolved call graph."""
    graph = CodeGraph()
    parsers = _Parsers()
    for rel, disk_path in files:
        language = language_for_path(rel)
        if language is None:
            continue
        loaded = parsers.get(language, graph.warnings)
        if loaded is None:
            continue
        try:
            if disk_path.stat().st_size > _MAX_FILE_BYTES:
                continue
            raw = disk_path.read_bytes()
        except OSError as exc:
            graph.warnings.append({"path": rel, "reason": str(exc)})
            continue
        if b"\x00" in raw[:512]:
            continue
        parser, query, _ = loaded
        try:
            _parse_file(graph, rel, raw, language, parser, query)
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop a scan
            log.warning("tree-sitter parse failed for %s: %s", rel, exc)
            graph.warnings.append({"path": rel, "reason": f"parse failed: {exc}"})
            continue
        graph.parsed_files[rel] = language
    _resolve(graph)
    return graph
