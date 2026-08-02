"""Pub/sub event bus for SSE streaming.

Crawler and scanner push events here; the SSE endpoint drains them to clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import json
from typing import AsyncGenerator, Iterator

# (run_kind, run_id) → list of subscriber queues.  The kind remains part of the
# event-bus key so each surface can keep its own stream and compatibility path.
_queues: dict[tuple[str, int], list[asyncio.Queue]] = {}

# The shared agent_log / scan_log tables retain a discriminator written at
# persist time. The authoritative source is ``_run_kind_ctx``: a context variable
# each scan orchestrator sets (via ``run_kind_scope``) for the duration of its
# work.  Because ``asyncio.create_task`` snapshots the current context, every
# event a scan emits — directly or from any child task it spawns — inherits the
# correct kind regardless of the numeric id.
#
# INVARIANT: every background-task entry point that can emit ``agent_status`` /
# ``scanner_phase`` MUST run inside a ``run_kind_scope`` (the web/api/sast
# scanners, the crawler, the validator, and ALICE all do).  There is
# deliberately no id-keyed fallback: the scope is the explicit routing signal.
# An emit that somehow escapes every scope falls back to
# ``'web'`` — deterministic, never routed by stale global state.
_run_kind_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "aespa_run_kind", default=None
)


@contextlib.contextmanager
def run_kind_scope(kind: str) -> Iterator[None]:
    """Tag every event emitted within this context (and any task spawned from
    it) with ``run_kind=kind``. Nested scopes restore the surrounding kind on
    exit."""
    token = _run_kind_ctx.set(kind)
    try:
        yield
    finally:
        _run_kind_ctx.reset(token)


def _run_kind_for(run_id: int, event: dict) -> str:
    explicit = event.get("_run_kind")
    if explicit:
        return str(explicit)
    return _run_kind_ctx.get() or "web"


def emit(run_id: int, event: dict) -> None:
    """Push an event to all active SSE subscribers for a run (non-blocking).

    scanner_phase events are also persisted to the scan_log table so the
    activity log survives page navigation.
    """
    run_kind = _run_kind_for(run_id, event)
    for q in _queues.get((run_kind, run_id), []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # slow client — drop the event rather than block

    if event.get("type") == "scanner_phase":
        _persist_phase_event(run_id, event)

    if event.get("type") == "agent_status":
        _persist_agent_status_event(run_id, event)


def _persist_phase_event(run_id: int, event: dict) -> None:
    """Write a scanner_phase event to scan_log (best-effort, never raises)."""
    try:
        from sqlmodel import Session

        from aespa.db import get_engine
        from aespa.models import ScanLog

        data = event.get("data")
        entry = ScanLog(
            test_run_id=run_id,
            run_kind=_run_kind_for(run_id, event),
            phase=str(event.get("phase") or ""),
            status=str(event.get("status") or ""),
            message=str(event.get("message") or ""),
            page_url=event.get("page_url") or None,
            data_json=json.dumps(data) if data is not None else None,
        )
        with Session(get_engine()) as s:
            s.add(entry)
            s.commit()
    except Exception:
        pass  # never let persistence failures break the scan


def _persist_agent_status_event(run_id: int, event: dict) -> None:
    """Write an agent_status event to agent_log (best-effort, never raises)."""
    try:
        from sqlmodel import Session

        from aespa.db import get_engine
        from aespa.models import AgentLog

        entry = AgentLog(
            test_run_id=run_id,
            run_kind=_run_kind_for(run_id, event),
            agent_id=str(event.get("agent_id") or ""),
            role=str(event.get("role") or ""),
            status=str(event.get("status") or ""),
            current_task=str(event.get("current_task") or ""),
            outcome=event.get("outcome") or None,
        )
        with Session(get_engine()) as s:
            s.add(entry)
            s.commit()
    except Exception:
        pass  # never let persistence failures break the scan


async def stream(run_id: int, run_kind: str = "web") -> AsyncGenerator[str, None]:
    """Yield events for ``(run_kind, run_id)`` until the client disconnects."""
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    key = (run_kind, run_id)
    _queues.setdefault(key, []).append(q)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=20.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"  # keep the connection alive
    finally:
        try:
            _queues[key].remove(q)
        except (KeyError, ValueError):
            pass
        if key in _queues and not _queues[key]:
            del _queues[key]
