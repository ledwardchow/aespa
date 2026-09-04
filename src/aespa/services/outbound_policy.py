"""Server-side policy checks for model-directed outbound HTTP requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlsplit

_ALWAYS_RESERVED_HEADERS = {
    "authorization",
    "connection",
    "content-length",
    "cookie",
    "host",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


def validate_request(
    *,
    method: str,
    url: str,
    headers: dict[str, Any],
    body_size: int,
    scanner_policy,
    scope_check: Callable[[str], str | None],
) -> PolicyDecision:
    """Validate an outbound request without performing network I/O."""
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        return PolicyDecision(False, f"invalid URL: {exc}")
    if parsed.username is not None or parsed.password is not None:
        return PolicyDecision(False, "credentials embedded in URLs are not allowed")
    if not parsed.scheme or not parsed.hostname:
        return PolicyDecision(False, "URL must include a scheme and host")
    allowed_schemes = {
        str(value).lower()
        for value in getattr(scanner_policy, "allowed_schemes", ["http", "https"])
    }
    if parsed.scheme.lower() not in allowed_schemes or parsed.scheme.lower() not in {
        "http",
        "https",
    }:
        return PolicyDecision(False, f"URL scheme {parsed.scheme!r} is not allowed")

    try:
        scope_error = scope_check(url)
    except Exception as exc:
        return PolicyDecision(False, f"scope check failed: {exc}")
    if scope_error:
        return PolicyDecision(False, scope_error)

    normalized_method = method.strip().upper()
    scan_mode = str(getattr(scanner_policy, "scan_mode", "aggressive"))
    methods_by_mode = getattr(scanner_policy, "methods_by_mode", {}) or {}
    allowed_methods = {
        str(value).upper() for value in methods_by_mode.get(scan_mode, [])
    }
    if normalized_method not in allowed_methods:
        return PolicyDecision(
            False,
            f"HTTP method {normalized_method!r} is not allowed in {scan_mode!r} mode",
        )
    if scan_mode == "destructive" and getattr(
        scanner_policy, "require_approval_for_destructive", True
    ):
        return PolicyDecision(
            False,
            "destructive requests require an explicit run approval; no approval grant is active",
        )

    blocked = {
        str(value).lower() for value in getattr(scanner_policy, "blocked_headers", [])
    } | _ALWAYS_RESERVED_HEADERS
    supplied_blocked = sorted(
        str(name) for name in headers if str(name).strip().lower() in blocked
    )
    if supplied_blocked:
        return PolicyDecision(
            False,
            "reserved request header(s): " + ", ".join(supplied_blocked),
        )

    limit = int(getattr(scanner_policy, "max_request_body_bytes", 65536))
    if body_size > limit:
        return PolicyDecision(
            False, f"request body is {body_size} bytes; policy limit is {limit} bytes"
        )
    return PolicyDecision(True)
