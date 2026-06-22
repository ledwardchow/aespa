"""Pub/sub event bus for SSE streaming.

Crawler and scanner push events here; the SSE endpoint drains them to clients.
"""
from __future__ import annotations

import asyncio
import contextlib
import contextvars
import json
from typing import AsyncGenerator, Iterator

# run_id → list of subscriber queues
_queues: dict[int, list[asyncio.Queue]] = {}

# web TestRun, ApiTestRun and SastRun ids come from independent counters and
# collide (id 1 can be all three at once), so the shared agent_log / scan_log
# tables need a discriminator written at persist time.  Resolving that
# discriminator from the run id alone is impossible when ids collide, so the
# authoritative — and only — source is ``_run_kind_ctx``: a context variable
# each scan orchestrator sets (via ``run_kind_scope``) for the duration of its
# work.  Because ``asyncio.create_task`` snapshots the current context, every
# event a scan emits — directly or from any child task it spawns — inherits the
# correct kind regardless of id collisions.
#
# INVARIANT: every background-task entry point that can emit ``agent_status`` /
# ``scanner_phase`` MUST run inside a ``run_kind_scope`` (the web/api/sast
# scanners, the crawler, the validator, and ALICE all do).  There is
# deliberately no id-keyed fallback: keying on a colliding run id is what leaked
# events across runs.  An emit that somehow escapes every scope falls back to
# ``'web'`` — deterministic, never routed by stale global state.
_run_kind_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "aespa_run_kind", default=None
)


@contextlib.contextmanager
def run_kind_scope(kind: str) -> Iterator[None]:
    """Tag every event emitted within this context (and any task spawned from
    it) with ``run_kind=kind``.  Nests correctly: a SAST pre-phase awaited
    inside an API scan can open its own ``run_kind_scope('sast')`` and the
    surrounding ``'api'`` scope is restored on exit."""
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
    for q in _queues.get(run_id, []):
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
        from aespa.db import get_engine
        from aespa.models import ScanLog
        from sqlmodel import Session

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
        from aespa.db import get_engine
        from aespa.models import AgentLog
        from sqlmodel import Session

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


async def stream(run_id: int) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings for the given run until the client disconnects."""
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    _queues.setdefault(run_id, []).append(q)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=20.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"  # keep the connection alive
    finally:
        try:
            _queues[run_id].remove(q)
        except (KeyError, ValueError):
            pass
        if run_id in _queues and not _queues[run_id]:
            del _queues[run_id]
