"""Pub/sub event bus for SSE streaming.

Crawler and scanner push events here; the SSE endpoint drains them to clients.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

# run_id → list of subscriber queues
_queues: dict[int, list[asyncio.Queue]] = {}


def emit(run_id: int, event: dict) -> None:
    """Push an event to all active SSE subscribers for a run (non-blocking)."""
    for q in _queues.get(run_id, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # slow client — drop the event rather than block


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
