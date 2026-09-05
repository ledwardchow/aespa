"""Settings values."""

from __future__ import annotations

import json
from datetime import datetime, timezone

_SINGLETON_ID = 1

AGENT_ROLES: tuple[str, ...] = (
    "crawler",
    "test_lead",
    "specialist",
    "validator",
    "api_scanner",
    "sast",
    "component_mapper",
    "alice",
    "mentor",
)

CONTEXT_WINDOW_FALLBACK = 128_000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _json_dumps(value) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
