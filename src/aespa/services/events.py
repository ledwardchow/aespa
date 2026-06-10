"""Pub/sub event bus for SSE streaming.

Crawler and scanner push events here; the SSE endpoint drains them to clients.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

# run_id → list of subscriber queues
_queues: dict[int, list[asyncio.Queue]] = {}

# Ids of runs that emit as API scans.  web TestRun ids and ApiTestRun ids come
# from independent counters and collide, so the shared agent_log / scan_log
# tables need a discriminator written at persist time.  An API run registers
# its id here for the lifetime of the process; persisted rows are tagged "api"
# when their run_id is registered (or the event carries ``_run_kind="api"``),
# and "web" otherwise.
_api_run_ids: set[int] = set()


def register_api_run(run_id: int) -> None:
    """Mark a run id as belonging to an API scan so its persisted log rows are
    tagged ``run_kind='api'``.  Safe to call repeatedly."""
    _api_run_ids.add(run_id)


def _run_kind_for(run_id: int, event: dict) -> str:
    if event.get("_run_kind") == "api" or run_id in _api_run_ids:
        return "api"
    return "web"


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
