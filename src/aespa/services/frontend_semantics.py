"""Small, deterministic semantic extraction for browser-facing JavaScript.

The extractor deliberately works from request behaviour and call relationships.
It does not need a project-specific request helper name.  This keeps the
output useful for source snapshots from different frontend frameworks while
remaining safe to run when a parser/runtime is unavailable.

``extract_frontend_facts`` accepts one source file and returns dictionaries in
the shape consumed by ``ComponentFact`` persistence.  It is intentionally
conservative: values which cannot be resolved are kept as ``None`` or a
template marker rather than guessed from nearby code.
"""

from __future__ import annotations

import ast
import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
_MAX_FUNCTIONS = 500
_MAX_FACTS = 500
_MAX_SOURCE_CHARS = 1_000_000
_MAX_CALLS_PER_SOURCE = 4_000
_MAX_ASSIGNMENTS_PER_SOURCE = 2_000
_MAX_CALLBACK_RANGES = 1_000
_MAX_REPOSITORY_FILES = 4_000

# Calls with these names are common inside event callbacks, but they do not
# identify the callback's application handler.  Keeping the list here avoids
# emitting synthetic UI actions for DOM lookups and built-in helpers such as
# ``Number``.
_NON_HANDLER_NAMES = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "with",
        "return",
        "async",
        "await",
        "new",
        "this",
        "super",
        "typeof",
        "instanceof",
        "in",
        "of",
        "number",
        "string",
        "boolean",
        "bigint",
        "symbol",
        "object",
        "array",
        "date",
        "regexp",
        "error",
        "parseint",
        "parsefloat",
        "isnan",
        "isfinite",
        "decodeuri",
        "decodeuricomponent",
        "encodeuri",
        "encodeuricomponent",
        "math",
        "json",
        "console",
        "settimeout",
        "setinterval",
        "cleartimeout",
        "clearinterval",
        "promise",
        "fetch",
        "axios",
        "xmlhttprequest",
        "resolve",
        "reject",
        "then",
        "finally",
        "closest",
        "getelementbyid",
        "queryselector",
        "queryselectorall",
        "getelementsbyclassname",
        "getelementsbytagname",
        "addeventlistener",
        "removeeventlistener",
        "preventdefault",
        "stoppropagation",
        "click",
        "focus",
        "blur",
        "trim",
        "replace",
        "map",
        "filter",
        "reduce",
        "foreach",
        "find",
        "some",
        "every",
        "includes",
        "push",
        "pop",
        "slice",
        "substring",
        "substr",
        "tostring",
        "valueof",
    }
)


@dataclass(frozen=True)
class _Function:
    name: str
    params: tuple[str, ...]
    body: str
    start: int
    body_start: int
    location: str
    source: str = ""
    relative_path: str = ""


@dataclass(frozen=True)
class _Call:
    callee: str
    args: str
    start: int
    end: int


@dataclass
class _Request:
    method: str | None
    path: str | None
    host: str | None
    location: str
    supporting_locations: set[str] = field(default_factory=set)
    handler_locations: set[str] = field(default_factory=set)
    body_expression: str | None = None
    body_fields: list[str] = field(default_factory=list)


def _line_location(relative_path: str, source: str, position: int) -> str:
    return f"{relative_path}:{source.count(chr(10), 0, max(0, position)) + 1}"


def _matching(source: str, opening: int, left: str = "(", right: str = ")") -> int:
    """Find a matching delimiter, skipping strings and comments."""
    depth = 0
    quote = ""
    escaped = False
    i = opening
    while i < len(source):
        c = source[i]
        if quote:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif quote == "`" and c == "`":
                quote = ""
            elif quote != "`" and c == quote:
                quote = ""
            i += 1
            continue
        if c in "'\"`":
            quote = c
            i += 1
            continue
        if c == "/" and i + 1 < len(source) and source[i + 1] == "/":
            newline = source.find("\n", i + 2)
            i = len(source) if newline < 0 else newline + 1
            continue
        if c == "/" and i + 1 < len(source) and source[i + 1] == "*":
            end = source.find("*/", i + 2)
            i = len(source) if end < 0 else end + 2
            continue
        if c == left:
            depth += 1
        elif c == right:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_args(args: str) -> list[str]:
    parts: list[str] = []
    start = 0
    stack: list[str] = []
    quote = ""
    escaped = False
    pairs = {"(": ")", "[": "]", "{": "}"}
    for i, c in enumerate(args):
        if quote:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == quote:
                quote = ""
            continue
        if c in "'\"`":
            quote = c
        elif c in pairs:
            stack.append(pairs[c])
        elif stack and c == stack[-1]:
            stack.pop()
        elif c == "," and not stack:
            parts.append(args[start:i].strip())
            start = i + 1
    tail = args[start:].strip()
    if tail or parts:
        parts.append(tail)
    return parts


def _variable_assignments(source: str) -> list[tuple[str, str]]:
    """Return simple variable assignments, including multiline objects."""
    assignments: list[tuple[str, str]] = []
    marker = re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*")
    for match in marker.finditer(source):
        if len(assignments) >= _MAX_ASSIGNMENTS_PER_SOURCE:
            break
        start = match.end()
        stack: list[str] = []
        quote = ""
        escaped = False
        end = len(source)
        i = start
        while i < len(source):
            char = source[i]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
                i += 1
                continue
            if char in "'\"`":
                quote = char
            elif char in "([{":
                stack.append({"(": ")", "[": "]", "{": "}"}[char])
            elif stack and char == stack[-1]:
                stack.pop()
            elif char == ";" and not stack:
                end = i
                break
            elif char == "\n" and not stack:
                end = i
                break
            i += 1
        value = source[start:end].strip()
        if value:
            assignments.append((match.group(1), value))
    return assignments


def _calls(source: str, names: str | re.Pattern[str]) -> list[_Call]:
    pattern = re.compile(names) if isinstance(names, str) else names
    found: list[_Call] = []
    for match in pattern.finditer(source):
        if len(found) >= _MAX_CALLS_PER_SOURCE:
            break
        # Call patterns include the opening parenthesis.  Looking after the
        # match would skip it and silently drop every call with arguments.
        opening = source.find("(", max(match.start(), match.end() - 1))
        if opening < 0:
            continue
        closing = _matching(source, opening)
        if closing < 0:
            continue
        callee = match.groupdict().get("callee") or match.group(0).strip()
        found.append(
            _Call(callee, source[opening + 1 : closing], match.start(), closing + 1)
        )
    return found


def _functions(source: str, relative_path: str) -> dict[str, _Function]:
    functions: dict[str, _Function] = {}
    patterns = (
        re.compile(
            r"\b(?:async\s+)?function\s+(?P<name>[\w$]+)\s*\((?P<params>[^)]*)\)\s*\{"
        ),
        re.compile(
            r"\b(?:const|let|var)\s+(?P<name>[\w$]+)\s*=\s*(?:async\s*)?"
            r"(?:\((?P<params>[^)]*)\)|(?P<single>[\w$]+))\s*=>\s*\{"
        ),
        # Class/object methods, including Angular service methods.
        re.compile(r"(?<![\w$])(?P<name>[\w$]+)\s*\((?P<params>[^)]*)\)\s*\{"),
    )
    for pattern in patterns:
        for match in pattern.finditer(source):
            name = match.group("name")
            if name in {"if", "for", "while", "switch", "catch"} or name in functions:
                continue
            opening = source.find("{", match.end() - 1)
            closing = _matching(source, opening, "{", "}")
            if closing < 0:
                continue
            params = (
                match.groupdict().get("params") or match.groupdict().get("single") or ""
            )
            param_names = tuple(
                re.split(r"\s*=", item.strip(), maxsplit=1)[0].strip()
                for item in _split_args(params)
                if item
                and re.match(
                    r"^[\w$]+$",
                    re.split(r"\s*=", item.strip(), maxsplit=1)[0].strip(),
                )
            )
            functions[name] = _Function(
                name=name,
                params=param_names,
                body=source[opening + 1 : closing],
                start=match.start(),
                body_start=opening + 1,
                location=_line_location(relative_path, source, match.start()),
                source=source,
                relative_path=relative_path,
            )
            if len(functions) >= _MAX_FUNCTIONS:
                return functions
    # Expression-bodied arrows have no brace range to scan.  Treat their
    # expression as a compact function body so wrappers such as
    # ``const save = () => request('POST', '/save')`` are summarized too.
    expression_pattern = re.compile(
        r"\b(?:const|let|var)\s+(?P<name>[\w$]+)\s*=\s*(?:async\s*)?"
        r"(?:\((?P<params>[^)]*)\)|(?P<single>[\w$]+))\s*=>\s*(?!\{)(?P<expr>[^;\n]+)"
    )
    for match in expression_pattern.finditer(source):
        name = match.group("name")
        if name in functions:
            continue
        params = match.group("params") or match.group("single") or ""
        param_names = tuple(
            item.strip()
            for item in _split_args(params)
            if re.match(r"^[\w$]+$", item.strip())
        )
        expr_start = match.start("expr")
        functions[name] = _Function(
            name=name,
            params=param_names,
            body=match.group("expr").strip(),
            start=match.start(),
            body_start=expr_start,
            location=_line_location(relative_path, source, match.start()),
            source=source,
            relative_path=relative_path,
        )
        if len(functions) >= _MAX_FUNCTIONS:
            break
    return functions


def _literal(
    expr: str, env: dict[str, str | None], _seen: set[str] | None = None
) -> str | None:
    expr = expr.strip().rstrip(";")
    if not expr:
        return None
    if expr in env:
        value = env[expr]
        if value is None:
            return None
        # Resolve aliases recursively.  This matters when a call site builds
        # ``const path = `/api/quotes/${product}``` before passing ``path`` to
        # a request wrapper.  The guard keeps malformed cyclic aliases safe.
        seen = set() if _seen is None else set(_seen)
        if expr in seen:
            return value
        seen.add(expr)
        resolved = _literal(value, env, seen)
        return value if resolved is None else resolved
    # String literals and template literals.  Dynamic values are represented
    # by a stable parameter marker, so /items/${id} matches /items/{id}.
    if len(expr) >= 2 and expr[0] in "'\"`" and expr[-1] == expr[0]:
        if expr[0] == "`":
            value = expr[1:-1]

            def replace_template_value(match: re.Match[str]) -> str:
                expression = match.group(1).strip()
                resolved = _literal(expression, env, _seen)
                if resolved is not None:
                    return resolved
                return "{" + re.sub(r"[^\w$.-]+", "_", expression) + "}"

            return re.sub(
                r"\$\{\s*([^}]+?)\s*\}",
                replace_template_value,
                value,
            )
        try:
            parsed = ast.literal_eval(expr)
            return parsed if isinstance(parsed, str) else None
        except (SyntaxError, ValueError):
            return expr[1:-1]
    # Concatenation of literals and identifiers is common in hand-written
    # clients.  Do this only when every term can be represented safely.
    terms = re.split(r"\s*\+\s*", expr)
    if len(terms) > 1:
        values = [_literal(term, env, _seen) for term in terms]
        if all(value is not None for value in values):
            return "".join(value or "" for value in values)
    return None


def _normal_path(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    value = value.strip().split("?", 1)[0].split("#", 1)[0]
    value = _normalise_server_template_route(value)
    if not value:
        return None, None
    # A partly evaluated JavaScript expression is not a URL.  Dropping it is
    # safer than persisting a path such as ``/api/type === 'MOTOR'`` and later
    # treating it as route evidence.
    if re.search(r"[\s'\"=<>|]", value):
        return None, None
    host = None
    if value.startswith(("http://", "https://")):
        parsed = urlsplit(value)
        host = parsed.netloc or None
        value = parsed.path or "/"
    if not value.startswith("/"):
        value = "/" + value
    value = re.sub(r"/{2,}", "/", value)
    return value.rstrip("/") or "/", host


def _normalise_server_template_route(value: str) -> str:
    """Strip URL-expression syntax used by server-side view templates.

    Thymeleaf writes form actions as ``@{/claims/{id}/disburse(id=${id})}``.
    The part in parentheses supplies values for the route variables and is
    not part of the route itself.  Preserve the ``{id}`` path marker so it can
    match a backend route template later.
    """
    value = value.strip()
    if not (value.startswith("@{") and value.endswith("}")):
        return value
    expression = value[2:-1].strip()
    brace_depth = 0
    for index, char in enumerate(expression):
        if char == "{":
            brace_depth += 1
        elif char == "}" and brace_depth:
            brace_depth -= 1
        elif char == "(" and brace_depth == 0:
            expression = expression[:index].strip()
            break
    return expression


def _method(value: str | None, default: str | None = None) -> str | None:
    if value:
        value = value.strip().strip("'\"`").upper()
        if value in _HTTP_METHODS:
            return value
    return default


def _object_value(text: str, key: str) -> str | None:
    match = re.search(
        rf"(?:^|[,{{\s]){re.escape(key)}\s*:\s*(?P<value>`[^`]*`|'[^']*'|\"[^\"]*\"|[^,}}\n]+)",
        text,
        re.IGNORECASE,
    )
    return match.group("value").strip() if match else None


def _resolved_object_value(
    text: str, key: str, env: dict[str, str | None]
) -> str | None:
    """Read a property from an inline object or an object held in a local."""
    candidate = _object_value(text, key)
    if candidate is None and re.search(
        rf"[{{,\s]\s*{re.escape(key)}\s*(?:[,}}]|$)", text
    ):
        candidate = key
    if candidate is None and text.strip() in env and env[text.strip()]:
        candidate = _object_value(env[text.strip()] or "", key)
        if candidate is None and re.search(
            rf"[{{,\s]\s*{re.escape(key)}\s*(?:[,}}]|$)", env[text.strip()] or ""
        ):
            candidate = key
    # Object shorthand is represented by the property name itself.
    return candidate


def _body_fields(body: str | None) -> list[str]:
    if not body:
        return []
    if body.startswith("{"):
        return re.findall(r"(?:^|[,\s])([A-Za-z_$][\w$]*)\s*(?::|[,}])", body)
    return []


def _axios_bases(
    source: str, env: dict[str, str | None] | None = None
) -> dict[str, str]:
    """Find ``axios.create`` clients and their base URLs."""
    bases: dict[str, str] = {}
    for match in re.finditer(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*axios\.create\s*\(",
        source,
        re.I,
    ):
        opening = source.find("(", match.end() - 1)
        closing = _matching(source, opening)
        if closing < 0:
            continue
        config = source[opening + 1 : closing]
        value = _object_value(config, "baseURL")
        value = _literal(value or "", env or {})
        if value:
            bases[match.group(1)] = value
            bases[match.group(1).lower()] = value
    return bases


def _request_from_call(
    call: _Call,
    source: str,
    env: dict[str, str | None],
    relative_path: str,
    function: _Function | None,
    axios_bases: dict[str, str] | None = None,
) -> _Request | None:
    args = _split_args(call.args)
    callee = call.callee.lower()
    method: str | None = None
    url_expr: str | None = None
    body_expr: str | None = None
    if callee.endswith(".open") and re.search(
        r"new\s+XMLHttpRequest\s*\(", source, re.I
    ):
        # XMLHttpRequest separates the method/url call from ``send``.  The
        # open call is the useful browser request fact; send's payload is
        # captured when it is a simple literal or local assignment.
        method = _method(_literal(args[0], env) if args else None)
        url_expr = args[1] if len(args) > 1 else None
    elif callee in {"fetch", "window.fetch", "globalthis.fetch"}:
        url_expr = args[0] if args else None
        options = args[1] if len(args) > 1 else ""
        method_expr = _resolved_object_value(options, "method", env)
        method = _method(_literal(method_expr or "", env), "GET")
        body_expr = _resolved_object_value(options, "body", env)
    elif callee.endswith(".request") and (
        "axios" in callee or "http" in callee or "client" in callee
    ):
        config = args[0] if args else ""
        url_expr = _resolved_object_value(config, "url", env)
        method_expr = _resolved_object_value(config, "method", env)
        method = _method(_literal(method_expr or "", env), "GET")
        body_expr = _resolved_object_value(
            config, "data", env
        ) or _resolved_object_value(config, "body", env)
    else:
        member = re.search(r"\.([A-Za-z]+)$", callee)
        if not member or member.group(1).upper() not in _HTTP_METHODS:
            return None
        method = member.group(1).upper()
        url_expr = args[0] if args else None
        body_expr = args[1] if len(args) > 1 else None
        # A random object method named ``get`` is not enough evidence.  These
        # receiver names cover Axios, Angular HttpClient, and usual wrappers.
        receiver = callee.rsplit(".", 1)[0].split(".")[-1]
        receiver_name = receiver.lower()
        known_base_client = bool(
            axios_bases and (receiver in axios_bases or receiver_name in axios_bases)
        )
        if (
            not known_base_client
            and receiver_name
            not in {
                "axios",
                "http",
                "httpclient",
                "client",
                "api",
                "request",
                "$http",
                "service",
                "this",
            }
            and not receiver_name.endswith(("client", "http", "api", "service"))
        ):
            return None
    url = _literal(url_expr or "", env)
    path, host = _normal_path(url)
    if path and axios_bases and callee.count(".") >= 1:
        receiver = callee.rsplit(".", 1)[0].split(".")[-1]
        base = axios_bases.get(receiver) or axios_bases.get(receiver.lower())
        if base:
            base_path, base_host = _normal_path(base)
            if base_path:
                path = f"{base_path.rstrip('/')}/{path.lstrip('/')}"
                host = host or base_host
    location = _line_location(
        relative_path, source, (function.body_start if function else 0) + call.start
    )
    return _Request(
        method=method,
        path=path,
        host=host,
        location=location,
        supporting_locations={location},
        body_expression=_literal(body_expr or "", env) or body_expr,
        body_fields=_body_fields(body_expr),
    )


def _is_ui_handler_name(name: str | None) -> bool:
    return bool(name and name.casefold() not in _NON_HANDLER_NAMES)


def _contains_http_sink(text: str) -> bool:
    """Return whether an inline callback directly contains a request sink."""
    return bool(
        re.search(
            r"\b(?:fetch|axios|XMLHttpRequest)\s*\(|"
            r"\b[A-Za-z_$][\w$]*\s*\.\s*(?:get|post|put|patch|delete|head|options)\s*\(",
            text,
            re.I,
        )
    )


def _state_property_values(
    source: str, env: dict[str, str | None]
) -> dict[str, set[str]]:
    """Collect concrete values assigned to object properties.

    Small browser apps often keep the selected route parameter in state and
    read it later from a different event handler.  Static ``data-*`` values
    provide useful call-site values for assignments such as
    ``state.product = button.dataset.product`` without assuming a framework.
    """
    dataset_values: dict[str, set[str]] = {}
    for match in re.finditer(
        r"\bdata-(?P<key>[A-Za-z0-9_-]+)\s*=\s*['\"](?P<value>[^'\"]+)['\"]",
        source,
        re.I,
    ):
        key = match.group("key").replace("-", "_").casefold()
        dataset_values.setdefault(key, set()).add(match.group("value"))

    assignments = re.finditer(
        r"\b(?P<object>[A-Za-z_$][\w$]*)\.(?P<property>[A-Za-z_$][\w$]*)\s*=\s*"
        r"(?P<value>[^;\n,}]+)",
        source,
    )
    values: dict[str, set[str]] = {}
    pending: list[tuple[str, str]] = []
    for match in assignments:
        key = f"{match.group('object')}.{match.group('property')}"
        expression = match.group("value").strip()
        dataset = re.fullmatch(
            r"[A-Za-z_$][\w$]*\.dataset\.(?P<key>[A-Za-z_$][\w$]*)",
            expression,
        )
        if dataset:
            candidates = dataset_values.get(dataset.group("key").casefold(), set())
            if candidates:
                values.setdefault(key, set()).update(candidates)
            continue
        literal = _literal(expression, env)
        symbolic = re.fullmatch(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*", expression)
        if literal is not None and not symbolic:
            values.setdefault(key, set()).add(literal)
        else:
            pending.append((key, expression))
    for _ in range(len(pending)):
        changed = False
        for key, expression in pending:
            if key in values:
                continue
            candidates = values.get(expression)
            if candidates:
                values[key] = set(candidates)
                changed = True
        if not changed:
            break
    return values


def _state_env_variants(
    env: dict[str, str | None],
    state_values: dict[str, set[str]],
    body: str = "",
) -> list[dict[str, str | None]]:
    """Return bounded environments for concrete state-property values."""
    local_environment_text = " ".join(value for _, value in _variable_assignments(body))
    template_expressions = re.findall(r"\$\{\s*([^}]+?)\s*\}", body)
    relevant = [
        (key, sorted(values))
        for key, values in sorted(state_values.items())
        if values
        and len(values) <= 8
        and (
            key in local_environment_text
            or key in {expression.strip() for expression in template_expressions}
        )
    ]
    if not relevant:
        return [env]
    variants: list[dict[str, str | None]] = []
    for combination in itertools.product(*(item[1] for item in relevant)):
        variant = dict(env)
        for (key, _), value in zip(relevant, combination):
            variant[key] = value
        variants.append(variant)
        if len(variants) >= 24:
            break
    return variants or [env]


def _handler_bindings(source: str, relative_path: str) -> list[dict]:
    bindings: list[dict] = []
    patterns = (
        re.compile(
            r"\bon(?P<event>Click|Submit)\s*=\s*\{\s*(?P<handler>[\w$]+)\s*\}", re.I
        ),
        re.compile(
            r"@(?P<event>click|submit)(?:\.[\w-]+)*\s*=\s*[\"']\s*(?P<handler>[\w$]+)",
            re.I,
        ),
        re.compile(
            r"\((?P<event>click|ngSubmit|submit)\)\s*=\s*[\"']\s*(?P<handler>[\w$]+)\s*\(",
            re.I,
        ),
        re.compile(
            # A listener may receive a named function or an inline callback.
            # Require the named form to end at the argument boundary so
            # ``async event => ...`` is not mistaken for a handler named
            # ``async`` or ``event``.  Inline callbacks are resolved by the
            # listener pass below, which can inspect their call graph.
            r"addEventListener\s*\(\s*[\"'](?P<event>click|submit)[\"']\s*,\s*"
            r"(?P<handler>[\w$]+)\s*(?=\)|,)(?!\s*=>)",
            re.I,
        ),
        re.compile(r"\.(?:onclick|onsubmit)\s*=\s*(?P<handler>[\w$]+)", re.I),
    )
    for pattern in patterns:
        for match in pattern.finditer(source):
            event = match.group("event").lower()
            location = _line_location(relative_path, source, match.start())
            handler = match.group("handler")
            if not _is_ui_handler_name(handler):
                continue
            if pattern is patterns[3] and re.match(r"\s*=>", source[match.end() :]):
                # ``e`` in ``('submit', e => ...)`` is the callback
                # parameter.  Resolve the named call in the listener pass.
                continue
            if pattern in (patterns[1], patterns[2]) and (
                handler in {"fetch", "axios", "XMLHttpRequest"}
                or handler.lower() in {method.lower() for method in _HTTP_METHODS}
            ):
                continue
            label = None
            nearby = source[
                max(0, match.start() - 180) : min(len(source), match.end() + 180)
            ]
            button = re.search(
                r"<button\b[^>]*>([^<]{1,120})</button>", nearby, re.I | re.S
            )
            if button:
                label = " ".join(button.group(1).split())
            bindings.append(
                {
                    "handler": handler,
                    "event": event,
                    "location": location,
                    "label": label or handler,
                }
            )
    # Vanilla listeners frequently use an inline callback.  Resolve the
    # named call inside that callback and retain the listener as the evidence
    # location.  This also handles ``e => { e.preventDefault(); submit(); }``.
    listener_pattern = re.compile(r"(?P<owner>[^;\n]+?)\.addEventListener\s*\(", re.I)
    for match in listener_pattern.finditer(source):
        opening = source.find("(", match.end() - 1)
        closing = _matching(source, opening)
        if closing < 0:
            continue
        args = _split_args(source[opening + 1 : closing])
        if len(args) < 2:
            continue
        event_match = re.match(r"\s*['\"](click|submit)['\"]", args[0], re.I)
        if not event_match:
            continue
        callback = args[1].strip()
        named = re.match(r"^[A-Za-z_$][\w$]*$", callback)
        candidates = (
            [callback] if named else re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", callback)
        )
        candidates = [
            candidate
            for candidate in candidates
            if candidate
            and _is_ui_handler_name(candidate)
            and candidate
            not in {
                "addEventListener",
                "preventDefault",
                "stopPropagation",
                "fetch",
                "XMLHttpRequest",
            }
            and candidate.lower() not in {method.lower() for method in _HTTP_METHODS}
        ]
        if not candidates and not _contains_http_sink(callback):
            continue
        event = event_match.group(1).lower()
        location = _line_location(relative_path, source, match.start())
        callback_offset = opening + 1 + source[opening + 1 : closing].find(args[1])
        handler = (
            candidates[0]
            if candidates
            else f"__event_callback_{source.count(chr(10), 0, match.start()) + 1}"
        )
        label = candidates[0] if candidates else handler
        element_id = None
        id_match = re.search(
            r"getElementById\s*\(\s*['\"]([^'\"]+)", match.group("owner"), re.I
        )
        if id_match:
            element_id = id_match.group(1)
        if element_id:
            markup = re.search(
                rf"<[^>]+\bid\s*=\s*['\"]{re.escape(element_id)}['\"][^>]*>\s*([^<]+)",
                source,
                re.I | re.S,
            )
            if markup:
                label = " ".join(markup.group(1).split())
        if not any(
            item["location"] == location and item["handler"] == handler
            for item in bindings
        ):
            binding = {
                "handler": handler,
                "event": event,
                "location": location,
                "label": label,
            }
            # Keep the callback body even when it already contains a named
            # helper.  The post-pass can then choose a later request owner
            # over an earlier state or validation helper.
            binding.update(
                {"callback_body": callback, "callback_offset": callback_offset}
            )
            bindings.append(binding)
    # Inline callbacks are useful even when they call a named function.
    inline = re.compile(r"\bon(?P<event>Click|Submit)\s*=\s*\{", re.I)
    for match in inline.finditer(source):
        opening = source.find("{", match.end() - 1)
        closing = _matching(source, opening, "{", "}")
        if closing < 0:
            continue
        expression = source[opening + 1 : closing]
        arrow = expression.find("=>")
        body = expression[arrow + 2 :].strip() if arrow >= 0 else expression.strip()
        called_names = re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", body)
        valid_names = [
            name
            for name in called_names
            if _is_ui_handler_name(name)
            and name.lower() not in {method.lower() for method in _HTTP_METHODS}
            and name not in {"fetch", "axios", "XMLHttpRequest"}
        ]
        if valid_names or _contains_http_sink(body):
            handler = valid_names[0] if valid_names else ""
            if not handler:
                handler = (
                    f"__event_callback_{source.count(chr(10), 0, match.start()) + 1}"
                )
            bindings.append(
                {
                    "handler": handler,
                    "event": match.group("event").lower(),
                    "location": _line_location(relative_path, source, match.start()),
                    "label": handler,
                    "callback_body": body,
                    "callback_offset": opening
                    + 1
                    + (expression.find("=>") + 2 if arrow >= 0 else 0),
                }
            )
    # Vue and Angular inline expressions use quoted attributes.  Named calls
    # are retained as handlers; direct sinks receive the same synthetic
    # callback treatment as JSX and vanilla listeners.
    attr_pattern = re.compile(
        r"(?:@(?:click|submit)(?:\.[\w-]+)*|\((?:click|ngSubmit|submit)\))\s*=\s*"
        r"(?P<quote>['\"])(?P<body>.*?)(?P=quote)",
        re.I,
    )
    for match in attr_pattern.finditer(source):
        event = re.search(r"(?:@|\()(click|submit|ngSubmit)", match.group(0), re.I)
        if not event:
            continue
        body = match.group("body").strip()
        called_names = re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", body)
        if not called_names:
            bare = re.match(r"([A-Za-z_$][\w$]*)\b", body)
            if bare:
                called_names = [bare.group(1)]
        valid_names = [
            name
            for name in called_names
            if _is_ui_handler_name(name)
            and name.lower() not in {method.lower() for method in _HTTP_METHODS}
            and name not in {"fetch", "axios", "XMLHttpRequest"}
        ]
        if not valid_names and not _contains_http_sink(body):
            continue
        handler = valid_names[0] if valid_names else ""
        callback_body = body
        if not handler:
            handler = f"__event_callback_{source.count(chr(10), 0, match.start()) + 1}"
        location = _line_location(relative_path, source, match.start())
        if not any(
            item["location"] == location and item["handler"] == handler
            for item in bindings
        ):
            bindings.append(
                {
                    "handler": handler,
                    "event": event.group(1).lower(),
                    "location": location,
                    "label": handler,
                    "callback_body": callback_body,
                    "callback_offset": match.start("body"),
                }
            )
    return bindings


def _function_calls(function: _Function) -> list[_Call]:
    """Return calls in a function body using the shared lightweight scanner."""
    calls = _calls(
        function.body,
        re.compile(r"(?P<callee>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\("),
    )
    callback_ranges = _callback_ranges(function.body)
    return [call for call in calls if not _in_callback(call.start, callback_ranges)]


def _is_request_sink_call(call: _Call) -> bool:
    """Identify request sinks without requiring a resolved URL."""
    callee = call.callee.casefold()
    if callee in {"fetch", "window.fetch", "globalthis.fetch"}:
        return True
    if callee.endswith(".open") or callee in {"xmlhttprequest", "xhr.open"}:
        return True
    member = callee.rsplit(".", 1)[-1]
    if member in {method.casefold() for method in _HTTP_METHODS}:
        receiver = callee.rsplit(".", 1)[0].rsplit(".", 1)[-1]
        return receiver in {
            "axios",
            "http",
            "httpclient",
            "client",
            "api",
            "request",
            "$http",
            "service",
            "this",
        } or receiver.endswith(("client", "http", "api", "service"))
    return False


def _function_request_distance(
    name: str,
    functions: dict[str, _Function],
    memo: dict[str, int | None] | None = None,
    visiting: set[str] | None = None,
) -> int | None:
    """Return the shortest call depth from a function to a request sink.

    This is intentionally a small bounded call-graph walk.  It lets event
    callbacks identify the function that owns a request when the callback also
    performs validation or state updates, as in ``saveStep(); submitQuote()``.
    """
    memo = memo if memo is not None else {}
    visiting = visiting if visiting is not None else set()
    if name in memo:
        return memo[name]
    if name in visiting or name not in functions:
        return None
    visiting.add(name)
    function = functions[name]
    distances: list[int] = []
    for call in _function_calls(function):
        if _is_request_sink_call(call):
            distances.append(1)
        elif call.callee in functions:
            child_distance = _function_request_distance(
                call.callee, functions, memo, visiting
            )
            if child_distance is not None:
                distances.append(child_distance + 1)
    result = min(distances) if distances else None
    visiting.discard(name)
    memo[name] = result
    return result


def _resolve_event_handler_bindings(
    bindings: list[dict], functions: dict[str, _Function]
) -> None:
    """Bind inline callbacks to the request-owning function they invoke.

    A callback often calls a state-saving helper before its final request
    helper.  Choosing the first call makes the browser request appear owned by
    the state helper and leaves the request function without a handler fact.
    Prefer the first function in source order that reaches a request sink.
    """
    memo: dict[str, int | None] = {}
    for binding in bindings:
        callback_body = binding.get("callback_body")
        if not callback_body:
            continue
        candidates = [
            call.callee
            for call in _calls(
                str(callback_body),
                re.compile(r"(?P<callee>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\("),
            )
            if call.callee in functions and _is_ui_handler_name(call.callee)
        ]
        request_candidates = [
            (candidate, distance)
            for candidate in candidates
            if (distance := _function_request_distance(candidate, functions, memo))
            is not None
        ]
        if request_candidates:
            binding["handler"] = min(
                enumerate(request_candidates), key=lambda item: (item[1][1], item[0])
            )[1][0]
            binding.pop("callback_body", None)
            binding.pop("callback_offset", None)


def _callback_ranges(source: str) -> list[tuple[int, int]]:
    """Return callback expression ranges that are separate event roots."""
    ranges: list[tuple[int, int]] = []
    listener_pattern = re.compile(r"\baddEventListener\s*\(", re.I)
    for match in listener_pattern.finditer(source):
        opening = source.find("(", match.end() - 1)
        closing = _matching(source, opening)
        if closing < 0:
            continue
        arrow = source.find("=>", opening, closing)
        if arrow >= 0:
            ranges.append((arrow, closing))
    jsx_pattern = re.compile(r"\bon(?:Click|Submit)\s*=\s*\{", re.I)
    for match in jsx_pattern.finditer(source):
        opening = source.find("{", match.end() - 1)
        closing = _matching(source, opening, "{", "}")
        if closing >= 0:
            arrow = source.find("=>", opening, closing)
            if arrow >= 0:
                ranges.append((arrow, closing))
    # Template strings and render helpers sometimes contain Vue/Angular
    # attributes.  Calls in those expressions belong to the bound action.
    attr_pattern = re.compile(
        r"(?:@(?:click|submit)(?:\.[\w-]+)*|\((?:click|ngSubmit|submit)\))\s*=\s*['\"]",
        re.I,
    )
    for match in attr_pattern.finditer(source):
        end_quote = source.find(source[match.end() - 1], match.end())
        if end_quote >= 0:
            ranges.append((match.end(), end_quote))
    return ranges


def _in_callback(position: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def _route_facts(source: str, relative_path: str) -> list[dict]:
    routes: list[dict] = []
    patterns = (
        re.compile(r"<Route\b[^>]*\bpath\s*=\s*[\"'](?P<path>[^\"']+)", re.I),
        re.compile(r"\bpath\s*:\s*[\"'](?P<path>[^\"']+)[\"']", re.I),
        re.compile(r"\b(?:route|router)\s*\(\s*[\"'](?P<path>/[^\"']*)", re.I),
    )
    seen: set[tuple[str, int]] = set()
    for pattern in patterns:
        for match in pattern.finditer(source):
            path, _ = _normal_path(match.group("path"))
            if not path or (path, match.start()) in seen:
                continue
            seen.add((path, match.start()))
            loc = _line_location(relative_path, source, match.start())
            routes.append(
                {
                    "fact_type": "ui_route",
                    "method": None,
                    "path": path,
                    "host": None,
                    "name": f"UI route {path}",
                    "detail": {"route_kind": "frontend", "supporting_locations": [loc]},
                    "evidence_location": loc,
                }
            )
    return routes


def _form_submissions(source: str, relative_path: str) -> list[dict]:
    submissions: list[dict] = []
    for match in re.finditer(r"<form\b(?P<attrs>[^>]*>)", source, re.I | re.S):
        attrs = match.group("attrs")
        action_match = re.search(r"\baction\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
        if not action_match:
            continue
        method_match = re.search(r"\bmethod\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
        path, host = _normal_path(action_match.group(1))
        if not path:
            continue
        location = _line_location(relative_path, source, match.start())
        handler = f"__form_submit_{source.count(chr(10), 0, match.start()) + 1}"
        submissions.append(
            {
                "handler": handler,
                "location": location,
                "method": _method(
                    method_match.group(1) if method_match else None, "GET"
                ),
                "path": path,
                "host": host,
            }
        )
    return submissions


def _file_route(relative_path: str) -> str | None:
    """Infer common Next-style file routes without requiring a framework."""
    parts = relative_path.replace("\\", "/").split("/")
    suffix = Path(parts[-1]).suffix.lower() if parts else ""
    if suffix not in {".js", ".jsx", ".ts", ".tsx"}:
        return None
    stem = Path(parts[-1]).stem
    if "app" in parts:
        index = len(parts) - 1 - parts[::-1].index("app")
        if stem not in {"page", "index"}:
            return None
        segments = parts[index + 1 : -1]
    elif "pages" in parts:
        index = len(parts) - 1 - parts[::-1].index("pages")
        segments = parts[index + 1 :]
        segments[-1] = stem
    else:
        return None
    segments = [
        ("{" + part[1:-1] + "}")
        if part.startswith("[") and part.endswith("]")
        else part
        for part in segments
        if part
        and not (part.startswith("(") and part.endswith(")"))
        and part not in {"index", "page"}
    ]
    return "/" + "/".join(segments)


def _extract_frontend_facts(
    text: str,
    relative_path: str,
    external_functions: dict[str, _Function] | None = None,
) -> list[dict]:
    """Extract UI routes/actions, handlers, and browser HTTP calls.

    ``relative_path`` is retained in every evidence pointer and also supplies
    the source suffix for callers that pass generated or virtual files.
    """
    if not isinstance(text, str) or not isinstance(relative_path, str):
        raise TypeError("text and relative_path must be strings")
    if len(text) > _MAX_SOURCE_CHARS:
        return []
    suffix = Path(relative_path).suffix.lower()
    if suffix not in {".js", ".jsx", ".ts", ".tsx", ".vue", ".html"}:
        return []
    functions = _functions(text, relative_path)
    if external_functions:
        for name, function in external_functions.items():
            functions.setdefault(name, function)
    bindings = _handler_bindings(text, relative_path)
    form_submissions = _form_submissions(text, relative_path)
    bindings.extend(
        {
            "handler": submission["handler"],
            "event": "submit",
            "location": submission["location"],
            "label": "Submit form",
        }
        for submission in form_submissions
    )
    for binding in bindings:
        callback_body = binding.get("callback_body")
        name = binding["handler"]
        if not callback_body or name in functions:
            continue
        callback_offset = int(binding.get("callback_offset") or 0)
        functions[name] = _Function(
            name=name,
            params=(),
            body=str(callback_body),
            start=callback_offset,
            body_start=callback_offset,
            location=binding["location"],
            source=text,
            relative_path=relative_path,
        )
    for submission in form_submissions:
        name = submission["handler"]
        functions[name] = _Function(
            name=name,
            params=(),
            body="",
            start=0,
            body_start=0,
            location=submission["location"],
            source=text,
            relative_path=relative_path,
        )
    _resolve_event_handler_bindings(bindings, functions)
    routes = _route_facts(text, relative_path)
    inferred_route = _file_route(relative_path)
    if inferred_route and not any(route["path"] == inferred_route for route in routes):
        location = f"{relative_path}:1"
        routes.append(
            {
                "fact_type": "ui_route",
                "method": None,
                "path": inferred_route,
                "host": None,
                "name": f"UI route {inferred_route}",
                "detail": {
                    "route_kind": "file_convention",
                    "supporting_locations": [location],
                },
                "evidence_location": location,
            }
        )
    facts: list[dict] = list(routes)
    handler_locations = {f.name: f.location for f in functions.values()}
    action_locations_by_handler: dict[str, list[str]] = {}
    for binding in bindings:
        action_locations_by_handler.setdefault(binding["handler"], []).append(
            binding["location"]
        )
        detail = {
            "trigger": binding["event"],
            "handler": binding["handler"],
            "handler_locations": [handler_locations[binding["handler"]]]
            if binding["handler"] in handler_locations
            else [],
            "supporting_locations": [binding["location"]],
            "request_role": None,
        }
        facts.append(
            {
                "fact_type": "ui_action",
                "method": None,
                "path": None,
                "host": None,
                "name": binding["label"],
                "detail": detail,
                "evidence_location": binding["location"],
            }
        )

    # Emit direct and nested calls from roots.  Each context carries the
    # handler definition location, which gives correlation an explicit edge.
    called_functions: set[str] = set()
    for function in functions.values():
        callback_ranges = _callback_ranges(function.body)
        for call in _calls(
            function.body,
            re.compile(r"(?P<callee>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\("),
        ):
            if _in_callback(call.start, callback_ranges):
                continue
            if call.callee in functions:
                called_functions.add(call.callee)
    roots = set(functions) - called_functions
    roots.update(
        binding["handler"] for binding in bindings if binding["handler"] in functions
    )
    emitted: dict[tuple[str | None, str | None, str], _Request] = {}
    for submission in form_submissions:
        emitted[(submission["method"], submission["path"], submission["location"])] = (
            _Request(
                method=submission["method"],
                path=submission["path"],
                host=submission["host"],
                location=submission["location"],
                supporting_locations={submission["location"]},
                handler_locations={submission["location"]},
            )
        )
    global_env: dict[str, str | None] = {}
    for name, value in _variable_assignments(text):
        global_env[name] = value
    state_values = _state_property_values(text, global_env)

    def visit(
        function: _Function,
        env: dict[str, str | None],
        root_handler: str | None,
        chain: set[str],
    ) -> None:
        if function.name in chain:
            return
        next_chain = chain | {function.name}
        local_env = dict(env)
        # Preserve object literals and aliases for request option lookup.
        for name, value in _variable_assignments(function.body):
            local_env[name] = value
        variant_envs = _state_env_variants(local_env, state_values, function.body)
        callback_ranges = _callback_ranges(function.body)
        for call in _calls(
            function.body,
            re.compile(r"(?P<callee>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\("),
        ):
            if _in_callback(call.start, callback_ranges):
                continue
            for call_env in variant_envs:
                axios_bases = _axios_bases(function.source or text, call_env)
                req = _request_from_call(
                    call,
                    function.source or text,
                    call_env,
                    function.relative_path or relative_path,
                    function,
                    axios_bases,
                )
                if req:
                    req.handler_locations.add(
                        handler_locations.get(
                            root_handler or function.name, function.location
                        )
                    )
                    req.supporting_locations.add(function.location)
                    key = (req.method, req.path, req.location)
                    if key in emitted:
                        emitted[key].handler_locations.update(req.handler_locations)
                        emitted[key].supporting_locations.update(
                            req.supporting_locations
                        )
                    else:
                        emitted[key] = req
                    continue
                target = functions.get(call.callee)
                if not target:
                    continue
                args = _split_args(call.args)
                child_env = {
                    param: _literal(args[i], call_env) if i < len(args) else None
                    for i, param in enumerate(target.params)
                }
                visit(target, child_env, root_handler or function.name, next_chain)

    for name in sorted(roots):
        visit(
            functions[name],
            dict(global_env),
            name if name in action_locations_by_handler else None,
            set(),
        )
    # Top-level sinks are browser requests even without a named function.
    top_level_variants = _state_env_variants(global_env, state_values, text)
    for call in _calls(
        text,
        re.compile(
            r"(?P<callee>(?:window\.|globalThis\.)?fetch|(?:[A-Za-z_$][\w$]*\.)?(?:request|get|post|put|patch|delete|head|options))\s*\("
        ),
    ):
        if any(
            f.start <= call.start < f.body_start + len(f.body)
            for f in functions.values()
        ):
            continue
        for top_level_env in top_level_variants:
            top_level_bases = _axios_bases(text, top_level_env)
            req = _request_from_call(
                call, text, top_level_env, relative_path, None, top_level_bases
            )
            if req:
                emitted.setdefault((req.method, req.path, req.location), req)

    for req in sorted(
        emitted.values(),
        key=lambda value: (value.location, value.method or "", value.path or ""),
    ):
        detail: dict = {
            "request_role": "browser_request",
            "frontend": True,
            "supporting_locations": sorted(req.supporting_locations),
            "handler_locations": sorted(req.handler_locations),
        }
        if req.body_expression:
            detail["body_expression"] = req.body_expression
        if req.body_fields:
            detail["body_fields"] = sorted(set(req.body_fields))
        facts.append(
            {
                "fact_type": "http_call",
                "method": req.method,
                "path": req.path,
                "host": req.host,
                "name": f"{req.method or 'HTTP'} {req.path or 'dynamic request'}",
                "detail": detail,
                "evidence_location": req.location,
            }
        )

    # Handler facts make the action -> function -> request chain inspectable.
    for name, function in sorted(functions.items(), key=lambda pair: pair[1].location):
        if name not in action_locations_by_handler:
            continue
        facts.append(
            {
                "fact_type": "handler",
                "method": None,
                "path": None,
                "host": None,
                "name": name,
                "detail": {
                    "handler": name,
                    "supporting_locations": sorted(action_locations_by_handler[name]),
                    "request_role": None,
                },
                "evidence_location": function.location,
            }
        )
    return facts[:_MAX_FACTS]


def extract_frontend_facts(text: str, relative_path: str) -> list[dict]:
    """Extract facts from one JavaScript/TypeScript source file."""
    return _extract_frontend_facts(text, relative_path)


def _resolve_module(
    importer: str, specifier: str, sources: dict[str, str]
) -> str | None:
    if not specifier.startswith("."):
        return None
    base = Path(importer).parent / specifier
    candidates = [base]
    if not base.suffix:
        candidates.extend(
            base.with_suffix(suffix)
            for suffix in (".js", ".jsx", ".ts", ".tsx", ".vue")
        )
    normalized = {str(Path(key).as_posix()).lstrip("./"): key for key in sources}
    for candidate in candidates:
        key = candidate.as_posix().lstrip("./")
        if key in normalized:
            return normalized[key]
    # Handle index modules without relying on Path arithmetic with suffixes.
    for suffix in (".js", ".jsx", ".ts", ".tsx", ".vue"):
        key = (base / ("index" + suffix)).as_posix().lstrip("./")
        if key in normalized:
            return normalized[key]
    return None


def _module_exports(text: str, functions: dict[str, _Function]) -> dict[str, _Function]:
    """Map export names to definitions, covering ES modules and CommonJS."""
    exports: dict[str, _Function] = {}
    for name, function in functions.items():
        if re.search(
            rf"\bexport\s+(?:async\s+)?(?:function|const|let|var)\s+{re.escape(name)}\b",
            text,
        ):
            exports[name] = function
    for match in re.finditer(r"\bexport\s*\{(?P<items>[^}]+)\}", text, re.S):
        for item in _split_args(match.group("items")):
            bits = re.split(r"\s+as\s+", item.strip(), maxsplit=1)
            local = bits[0].strip()
            exported = bits[-1].strip()
            if local in functions:
                exports[exported] = functions[local]
    default = re.search(r"\bexport\s+default\s+(?:async\s+)?function\s+([\w$]+)", text)
    if default and default.group(1) in functions:
        exports["default"] = functions[default.group(1)]
    # A plain ``export default handler`` points to an existing definition.
    default_ref = re.search(r"\bexport\s+default\s+([\w$]+)", text)
    if default_ref and default_ref.group(1) in functions:
        exports["default"] = functions[default_ref.group(1)]
    for match in re.finditer(
        r"(?:module\.exports|exports)\s*=\s*\{(?P<items>[^}]+)\}", text, re.S
    ):
        for item in _split_args(match.group("items")):
            bits = item.split(":", 1)
            exported = bits[0].strip()
            local = bits[-1].strip()
            if local in functions:
                exports[exported] = functions[local]
    for match in re.finditer(
        r"\bexports\.(?P<export>[\w$]+)\s*=\s*(?P<local>[\w$]+)", text
    ):
        if match.group("local") in functions:
            exports[match.group("export")] = functions[match.group("local")]
    common_default = re.search(r"module\.exports\s*=\s*([\w$]+)", text)
    if common_default and common_default.group(1) in functions:
        exports["default"] = functions[common_default.group(1)]
    return exports


def _imported_functions(
    text: str,
    relative_path: str,
    modules: dict[str, tuple[dict[str, _Function], dict[str, _Function]]],
    sources: dict[str, str],
) -> dict[str, _Function]:
    imported: dict[str, _Function] = {}

    def add(module_specifier: str, local: str, exported: str) -> None:
        target_path = _resolve_module(relative_path, module_specifier, sources)
        if not target_path or target_path not in modules:
            return
        _, exports = modules[target_path]
        target = exports.get(exported)
        if target:
            imported[local] = target

    # Named/default/namespace ES imports.
    for match in re.finditer(
        r"\bimport\s+(?P<clause>[\s\S]*?)\s+from\s+[\"'](?P<module>[^\"']+)[\"']",
        text,
    ):
        clause = match.group("clause").strip()
        module = match.group("module")
        if clause.startswith("{"):
            items = clause.strip("{} ")
            for item in _split_args(items):
                bits = re.split(r"\s+as\s+", item.strip(), maxsplit=1)
                add(module, bits[-1].strip(), bits[0].strip())
        elif clause.startswith("*"):
            namespace = re.search(r"\bas\s+([\w$]+)", clause)
            target_path = _resolve_module(relative_path, module, sources)
            if namespace and target_path in modules:
                for exported, function in modules[target_path][1].items():
                    imported[f"{namespace.group(1)}.{exported}"] = function
        else:
            default_name = clause.split(",", 1)[0].strip()
            add(module, default_name, "default")
            named = re.search(r"\{(?P<items>[^}]+)\}", clause, re.S)
            if named:
                for item in _split_args(named.group("items")):
                    bits = re.split(r"\s+as\s+", item.strip(), maxsplit=1)
                    add(module, bits[-1].strip(), bits[0].strip())

    # CommonJS destructuring and property aliases.
    for match in re.finditer(
        r"\b(?:const|let|var)\s*\{(?P<items>[^}]+)\}\s*=\s*require\s*\(\s*[\"'](?P<module>[^\"']+)[\"']\s*\)",
        text,
        re.S,
    ):
        for item in _split_args(match.group("items")):
            bits = item.split(":", 1)
            add(match.group("module"), bits[-1].strip(), bits[0].strip())
    for match in re.finditer(
        r"\b(?:const|let|var)\s+(?P<local>[\w$]+)\s*=\s*require\s*\(\s*[\"'](?P<module>[^\"']+)[\"']\s*\)(?:\.(?P<export>[\w$]+))?",
        text,
    ):
        exported = match.group("export")
        if exported:
            add(match.group("module"), match.group("local"), exported)
            continue
        target_path = _resolve_module(relative_path, match.group("module"), sources)
        if target_path in modules:
            for name, function in modules[target_path][1].items():
                imported[f"{match.group('local')}.{name}"] = function
            if "default" in modules[target_path][1]:
                imported[match.group("local")] = modules[target_path][1]["default"]
    return imported


def _merge_fact(existing: dict, incoming: dict) -> None:
    detail = existing.get("detail")
    incoming_detail = incoming.get("detail")
    if not isinstance(detail, dict) or not isinstance(incoming_detail, dict):
        return
    for key, value in incoming_detail.items():
        if isinstance(value, list):
            old = detail.setdefault(key, [])
            if isinstance(old, list):
                detail[key] = sorted(set(old + value))
        elif key not in detail or detail[key] in (None, ""):
            detail[key] = value


def extract_frontend_repository_facts(sources: dict[str, str]) -> list[dict]:
    """Extract frontend facts across files and resolve local module imports."""
    if not isinstance(sources, dict):
        raise TypeError("sources must be a mapping of relative paths to source text")
    normalized = {
        str(Path(path).as_posix()).lstrip("./"): text
        for path, text in sorted(sources.items())[:_MAX_REPOSITORY_FILES]
        if isinstance(path, str)
        and isinstance(text, str)
        and len(text) <= _MAX_SOURCE_CHARS
    }
    modules: dict[str, tuple[dict[str, _Function], dict[str, _Function]]] = {}
    for path, text in normalized.items():
        functions = _functions(text, path)
        modules[path] = (functions, _module_exports(text, functions))

    collected: list[dict] = []
    for path in sorted(normalized):
        text = normalized[path]
        imported = _imported_functions(text, path, modules, normalized)
        collected.extend(_extract_frontend_facts(text, path, imported))

    action_handler_locations: set[str] = set()
    for fact in collected:
        if fact.get("fact_type") != "ui_action":
            continue
        detail = fact.get("detail")
        if isinstance(detail, dict):
            values = detail.get("handler_locations") or []
            if isinstance(values, str):
                values = [values]
            action_handler_locations.update(str(value) for value in values)

    merged: dict[tuple[object, ...], dict] = {}
    for fact in collected:
        if fact.get("fact_type") == "http_call" and not fact.get("path"):
            detail = fact.get("detail")
            handlers = (
                detail.get("handler_locations", []) if isinstance(detail, dict) else []
            )
            if isinstance(handlers, str):
                handlers = [handlers]
            if not action_handler_locations.intersection(
                str(value) for value in handlers
            ):
                continue
        key = (
            fact.get("fact_type"),
            fact.get("method"),
            fact.get("path"),
            fact.get("evidence_location"),
            fact.get("name"),
        )
        if key in merged:
            _merge_fact(merged[key], fact)
        else:
            merged[key] = fact
    return list(merged.values())[:_MAX_FACTS]


__all__ = ["extract_frontend_facts", "extract_frontend_repository_facts"]
