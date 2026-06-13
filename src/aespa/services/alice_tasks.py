"""Server-side registry of ALICE background tasks.

Each TestRun can have at most one active ALICE task.  Tasks are fully
decoupled from HTTP connections — the agent loop keeps running even when the
browser refreshes or navigates away.

Clients reconnect via GET /api/test-runs/{id}/alice/stream?cursor=N which
replays buffered events from position N and then streams live events as they
arrive.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

log = logging.getLogger(__name__)

# Max events kept per task.  Oldest events are trimmed so memory stays bounded.
BUFFER_LIMIT = 2000


@dataclass
class AliceTask:
    run_id: int
    tab_id: str
    think_msg_id: str
    reply_msg_id: str
    run_type: str = "site"           # "site" | "api"
    # All SSE events produced so far (for replay on reconnect).
    events: list[dict] = field(default_factory=list)
    # One asyncio.Queue per connected SSE client.
    waiters: set[asyncio.Queue] = field(default_factory=set)
    asyncio_task: Optional[asyncio.Task] = None
    done: bool = False
    # Running totals kept in sync so a cancel can emit a valid done event.
    accumulated_thought: str = ""
    accumulated_message: str = ""


# One entry per run_id.
_registry: dict[int, AliceTask] = {}


# ── Public API ────────────────────────────────────────────────────────────────

def get(run_id: int) -> Optional[AliceTask]:
    return _registry.get(run_id)


def status(run_id: int) -> dict[str, Any]:
    t = _registry.get(run_id)
    if t is None:
        return {"running": False, "done": False}
    return {
        "running": not t.done,
        "done": t.done,
        "tab_id": t.tab_id,
        "think_msg_id": t.think_msg_id,
        "reply_msg_id": t.reply_msg_id,
        "event_count": len(t.events),
    }


async def start(
    run_id: int,
    *,
    tab_id: str,
    think_msg_id: str,
    reply_msg_id: str,
    message: str,
    history: list[dict],
    run_type: str = "site",
) -> AliceTask:
    """Start a new ALICE background task, cancelling any existing one first."""
    existing = _registry.get(run_id)
    if existing and existing.asyncio_task and not existing.asyncio_task.done():
        existing.asyncio_task.cancel()
        try:
            await existing.asyncio_task
        except (asyncio.CancelledError, Exception):
            pass

    task = AliceTask(
        run_id=run_id,
        tab_id=tab_id,
        think_msg_id=think_msg_id,
        reply_msg_id=reply_msg_id,
        run_type=run_type,
    )
    _registry[run_id] = task
    task.asyncio_task = asyncio.create_task(
        _run(task, message, history),
        name=f"alice-run-{run_id}",
    )
    return task


async def stop(run_id: int) -> bool:
    """Cancel the running task for this run.  Returns True if one was active."""
    task = _registry.get(run_id)
    if task is None or task.done:
        return False
    if task.asyncio_task and not task.asyncio_task.done():
        task.asyncio_task.cancel()
        return True
    return False


async def stream_events(run_id: int, cursor: int = 0) -> AsyncGenerator[str, None]:
    """Yield SSE lines: buffered events from *cursor*, then live events."""
    task = _registry.get(run_id)

    if task is None:
        # No task — send an empty done so the client knows there's nothing.
        yield f"data: {json.dumps({'type': 'done', 'thought': '', 'message': ''})}\n\n"
        return

    # Replay everything the client missed.
    for event in task.events[cursor:]:
        yield f"data: {json.dumps(event)}\n\n"

    if task.done:
        return

    # Subscribe to live events.
    q: asyncio.Queue = asyncio.Queue()
    task.waiters.add(q)
    try:
        while True:
            event = await q.get()
            if event is None:           # sentinel — task finished
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                break
    finally:
        task.waiters.discard(q)


# ── Internal ──────────────────────────────────────────────────────────────────

def _append(task: AliceTask, event: dict) -> None:
    """Add an event to the buffer and push to all connected clients."""
    t = event.get("type")
    if t == "thinking_chunk" and event.get("delta"):
        task.accumulated_thought += event["delta"]
        # Inject routing context so reconnecting clients can match the right message.
        event = {**event, "tab_id": task.tab_id, "msg_id": task.think_msg_id}
    elif t == "message_chunk" and event.get("delta"):
        task.accumulated_message += event["delta"]
        event = {**event, "tab_id": task.tab_id, "msg_id": task.reply_msg_id}
    elif t == "done":
        if event.get("thought"):
            task.accumulated_thought = event["thought"]
        if event.get("message"):
            task.accumulated_message = event["message"]
        event = {
            **event,
            "tab_id": task.tab_id,
            "think_msg_id": task.think_msg_id,
            "reply_msg_id": task.reply_msg_id,
        }

    if len(task.events) >= BUFFER_LIMIT:
        task.events = task.events[-(BUFFER_LIMIT - 1):]
    task.events.append(event)

    for q in list(task.waiters):
        q.put_nowait(event)


async def _run(task: AliceTask, message: str, history: list[dict]) -> None:
    from aespa.services import alice as alice_svc

    # Choose the right streaming function based on whether this is an API run.
    if task.run_type == "api":
        stream_fn = alice_svc.run_api_alice_turn_stream
    else:
        stream_fn = alice_svc.run_alice_turn_stream

    try:
        async for sse_line in stream_fn(task.run_id, message, history):
            if sse_line.startswith("data: "):
                try:
                    _append(task, json.loads(sse_line[6:].strip()))
                except Exception:
                    pass
    except asyncio.CancelledError:
        _append(task, {
            "type": "done",
            "thought": task.accumulated_thought,
            "message": task.accumulated_message or "Stopped by user.",
        })
        raise
    except Exception as exc:
        log.exception("ALICE background task failed for run_id=%s", task.run_id)
        _append(task, {
            "type": "done",
            "thought": task.accumulated_thought,
            "message": f"Agent encountered an error: {exc}",
        })
    finally:
        task.done = True
        for q in list(task.waiters):
            q.put_nowait(None)      # sentinel to close all client streams
        task.waiters.clear()
