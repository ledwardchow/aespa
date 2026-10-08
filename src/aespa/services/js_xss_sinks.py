"""Find JavaScript rendering paths worth checking for XSS.

This is deliberately a lead finder, not a vulnerability detector. It does not
follow data across modules or claim that a field is attacker controlled.
"""

from __future__ import annotations

import re

_HTML_SINK_RE = re.compile(
    r"\.\s*(?:innerHTML|outerHTML)\s*(?:\+?=)|"
    r"\.\s*(?:insertAdjacentHTML|html|append|prepend)\s*\(|"
    r"\bdocument\s*\.\s*write\s*\(",
    re.IGNORECASE,
)
_FIELD_RE = re.compile(r"\b([a-z][\w]*)\s*\.\s*([a-zA-Z_]\w*)\b")
_HANDLER_RE = re.compile(r"\bon[a-z]{3,}\s*=", re.IGNORECASE)
_ESCAPE_RE = re.compile(
    r"(?:escapeHtml|htmlEncode|encodeHtml|DOMPurify\.sanitize|sanitize)\s*\(\s*$",
    re.IGNORECASE,
)
_IGNORED_OBJECTS = {
    "api",
    "console",
    "container",
    "document",
    "element",
    "event",
    "html",
    "json",
    "math",
    "object",
    "response",
    "string",
    "window",
}
_IGNORED_FIELDS = {
    "classList",
    "forEach",
    "innerHTML",
    "length",
    "outerHTML",
    "preventDefault",
    "querySelector",
    "target",
    "textContent",
}
_TEXT_FIELD_RE = re.compile(
    r"(?:name|title|description|comment|content|message|text|label|nickname|"
    r"email|url|src|html|body|value)$",
    re.IGNORECASE,
)


def _render_block(source: str, sink_start: int) -> str:
    """Keep the nearest renderer and its HTML builder, with a fixed size bound."""
    start = max(0, sink_start - 16_000)
    prefix = source[start:sink_start]
    functions = list(re.finditer(r"\bfunction\s*(?:[\w$]+)?\s*\([^)]*\)\s*\{", prefix))
    if functions:
        start += functions[-1].start()
    # A callback inside a renderer can occur after the HTML builder starts.
    # Prefer that builder's declaration so its field references are retained.
    builder = list(re.finditer(r"\b(?:var|let|const)\s+html\s*=", prefix))
    if builder:
        start = max(0, sink_start - 16_000) + builder[-1].start()
    return source[start : min(len(source), sink_start + 300)]


def find_js_xss_sinks(source: str, *, max_candidates: int = 120) -> list[dict]:
    """Return distinct field/rendering-context leads from a JavaScript asset."""
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for sink_index, sink in enumerate(_HTML_SINK_RE.finditer(source[:1_000_000])):
        if sink_index >= 500:
            break
        block = _render_block(source, sink.start())
        # The final assignment often uses an HTML builder variable. Search its
        # surrounding renderer, rather than the 200 bytes beside innerHTML.
        for line in block.splitlines():
            handler = bool(_HANDLER_RE.search(line))
            for match in _FIELD_RE.finditer(line):
                obj, field = match.groups()
                if obj.lower() in _IGNORED_OBJECTS or field in _IGNORED_FIELDS:
                    continue
                if obj[0].isupper() or field.startswith("_"):
                    continue
                before = line[max(0, match.start() - 120) : match.start()]
                escaped = bool(_ESCAPE_RE.search(before)) or bool(
                    re.search(
                        r"(?:escapeHtml|htmlEncode|encodeHtml|DOMPurify\.sanitize|sanitize)\s*\([^)]*$",
                        before,
                        re.IGNORECASE,
                    )
                )
                # HTML escaping protects normal text, but it is insufficient
                # for data embedded in an inline JavaScript event handler.
                if escaped and not handler:
                    continue
                context = "event_handler" if handler else "html"
                key = (field, context)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "field": field,
                        "context": context,
                        "sink": sink.group(0).strip(),
                        "evidence": line[
                            max(0, match.start() - 130) : match.end() + 180
                        ].strip()[:350],
                        "confidence": (
                            0.9
                            if handler and _TEXT_FIELD_RE.search(field)
                            else 0.7
                            if _TEXT_FIELD_RE.search(field)
                            else 0.6
                            if handler
                            else 0.45
                        ),
                    }
                )
                if len(candidates) >= max_candidates:
                    return candidates
    return candidates
