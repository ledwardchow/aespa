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
import re
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
    run_type: str = "site"  # "site" | "api"
    goal_id: int | None = None
    goal: dict[str, Any] | None = None
    steering: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    # All SSE events produced so far (for replay on reconnect).
    events: list[dict] = field(default_factory=list)
    # Number of events dropped off the front of ``events`` by buffer trimming.
    # The client's reconnect cursor is an absolute position in the logical event
    # stream, so the buffer index is ``cursor - dropped``.
    dropped: int = 0
    # One asyncio.Queue per connected SSE client.
    waiters: set[asyncio.Queue] = field(default_factory=set)
    asyncio_task: Optional[asyncio.Task] = None
    done: bool = False
    # Running totals kept in sync so a cancel can emit a valid done event.
    accumulated_thought: str = ""
    accumulated_message: str = ""


# One entry per (run_type, run_id).
_registry: dict[tuple[str, int], AliceTask] = {}


# ── Public API ────────────────────────────────────────────────────────────────


def get(run_id: int, run_type: str = "site") -> Optional[AliceTask]:
    return _registry.get((run_type, run_id))


def status(run_id: int, run_type: str = "site") -> dict[str, Any]:
    from aespa.services import alice_goals

    run_kind = "api" if run_type == "api" else "web"
    t = _registry.get((run_type, run_id))
    if t is None:
        return {
            "running": False,
            "done": False,
            "goal": alice_goals.goal_out(alice_goals.get_goal(run_kind, run_id)),
        }
    return {
        "running": not t.done,
        "done": t.done,
        "tab_id": t.tab_id,
        "think_msg_id": t.think_msg_id,
        "reply_msg_id": t.reply_msg_id,
        "event_count": len(t.events),
        "goal": alice_goals.goal_out(alice_goals.get_goal(run_kind, run_id)),
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
    from aespa.services import alice_goals

    run_kind = "api" if run_type == "api" else "web"
    existing = _registry.get((run_type, run_id))
    command = re.fullmatch(r"/goal(?:\s+(.*))?", message.strip(), re.I | re.S)
    goal: dict[str, Any] | None = None
    control_message: str | None = None

    if command:
        argument = str(command.group(1) or "").strip()
        action = argument.casefold()
        current = alice_goals.get_goal(run_kind, run_id, tab_id)
        if not argument:
            if current is None:
                control_message = "No goal is set for this chat. Use /goal <objective> to start one."
            else:
                current_out = alice_goals.goal_out(current) or {}
                checkpoint = current_out.get("checkpoint") or {}
                control_message = (
                    f"Goal: {current.objective}\n\nStatus: {current.status}."
                    + (f"\n\nCheckpoint: {json.dumps(checkpoint)}" if checkpoint else "")
                )
        elif action == "pause":
            if current is None:
                control_message = "No goal is set for this chat."
            else:
                await stop(run_id, run_type=run_type)
                current = alice_goals.update_goal(
                    current.id, status="paused", pause_reason="Paused by user."
                )
                control_message = "Goal paused."
        elif action == "clear":
            if current is None:
                control_message = "No goal is set for this chat."
            else:
                await stop(run_id, run_type=run_type)
                current = alice_goals.update_goal(current.id, status="cleared")
                control_message = "Goal cleared."
        elif action == "resume":
            if current is None or current.status not in {"paused", "waiting_input"}:
                control_message = "There is no paused goal to resume in this chat."
            else:
                current = alice_goals.update_goal(
                    current.id, status="active", pause_reason="", increment_cycle=True
                )
                goal = alice_goals.goal_out(current)
                message = current.objective
        else:
            if existing and existing.asyncio_task and not existing.asyncio_task.done():
                await stop(run_id, run_type=run_type)
            current = alice_goals.create_goal(run_kind, run_id, tab_id, argument)
            current = alice_goals.update_goal(current.id, increment_cycle=True)
            goal = alice_goals.goal_out(current)
            message = argument

    existing = _registry.get((run_type, run_id))
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
        goal_id=(goal or {}).get("id"),
        goal=goal,
    )
    _registry[(run_type, run_id)] = task
    if control_message is not None:
        task.asyncio_task = asyncio.create_task(
            _run_control(task, control_message),
            name=f"alice-goal-control-{run_type}-{run_id}",
        )
    else:
        task.asyncio_task = asyncio.create_task(
            _run(task, message, history),
            name=f"alice-run-{run_type}-{run_id}",
        )
    return task


async def stop(run_id: int, run_type: str = "site") -> bool:
    """Cancel the running task for this run.  Returns True if one was active."""
    from aespa.services.code_execution import cancel_run_executions

    cancel_run_executions("api" if run_type == "api" else "web", run_id)
    task = _registry.get((run_type, run_id))
    if task is None or task.done:
        return False
    if task.goal_id is not None:
        from aespa.services import alice_goals

        alice_goals.update_goal(
            task.goal_id, status="paused", pause_reason="Paused by user."
        )
    if task.asyncio_task and not task.asyncio_task.done():
        task.asyncio_task.cancel()
        try:
            await task.asyncio_task
        except (asyncio.CancelledError, Exception):
            pass
        return True
    return False


async def steer_goal(run_id: int, message: str, run_type: str = "site") -> bool:
    """Queue user guidance for the next safe boundary in an active goal."""
    task = _registry.get((run_type, run_id))
    if task is None or task.done or task.goal_id is None or not message.strip():
        return False
    from aespa.services import alice_goals

    run_kind = "api" if run_type == "api" else "web"
    current = alice_goals.get_goal(run_kind, run_id, task.tab_id)
    if current is None or current.status != "active":
        return False
    task.goal = alice_goals.goal_out(current)
    await task.steering.put(message.strip())
    _append(
        task,
        {"type": "goal_steered", "message": message.strip(), "goal": task.goal},
    )
    return True


async def stream_events(
    run_id: int, cursor: int = 0, run_type: str = "site"
) -> AsyncGenerator[str, None]:
    """Yield SSE lines: buffered events from *cursor*, then live events."""
    task = _registry.get((run_type, run_id))

    if task is None:
        # No task — send an empty done so the client knows there's nothing.
        yield f"data: {json.dumps({'type': 'done', 'thought': '', 'message': ''})}\n\n"
        return

    # Replay everything the client missed. ``cursor`` is an absolute position in
    # the logical stream; the buffer may have dropped older events, so translate
    # to a buffer index. A cursor older than the retained window resyncs from the
    # buffer start (best effort — those events are gone).
    if cursor < task.dropped:
        yield f"data: {json.dumps({'type': 'state_snapshot', 'thought': task.accumulated_thought, 'message': task.accumulated_message, 'tab_id': task.tab_id, 'think_msg_id': task.think_msg_id, 'reply_msg_id': task.reply_msg_id})}\n\n"
        start = len(task.events)
    else:
        start = cursor - task.dropped
    for event in task.events[start:]:
        yield f"data: {json.dumps(event)}\n\n"

    if task.done:
        return

    # Subscribe to live events.
    q: asyncio.Queue = asyncio.Queue()
    task.waiters.add(q)
    try:
        while True:
            event = await q.get()
            if event is None:  # sentinel — task finished
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                break
    finally:
        task.waiters.discard(q)


# ── Internal ──────────────────────────────────────────────────────────────────


async def _run_control(task: AliceTask, message: str) -> None:
    _append(task, {"type": "message_chunk", "delta": message})
    _append(task, {"type": "done", "thought": "", "message": message})
    task.done = True
    for q in list(task.waiters):
        q.put_nowait(None)
    task.waiters.clear()


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
    elif t == "message_retract":
        task.accumulated_message = str(event.get("message") or "")
        event = {**event, "tab_id": task.tab_id, "msg_id": task.reply_msg_id}
    elif t in ("step_llm_call", "step_tool_call", "step_tool_result"):
        # Route step detail events to the thinking message so the client can
        # build the expandable tool-call / tool-result UI (matches web scans).
        event = {**event, "tab_id": task.tab_id, "msg_id": task.think_msg_id}
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
        keep = task.events[-(BUFFER_LIMIT - 1) :]
        task.dropped += len(task.events) - len(keep)
        task.events = keep
    task.events.append(event)

    for q in list(task.waiters):
        q.put_nowait(event)


async def _run(task: AliceTask, message: str, history: list[dict]) -> None:
    from aespa.services import alice as alice_svc
    from aespa.services import events as events_svc

    # Choose the right streaming function based on whether this is an API run.
    if task.run_type == "api":
        stream_fn = alice_svc.run_api_alice_turn_stream
    else:
        stream_fn = alice_svc.run_alice_turn_stream

    # Tag every event this turn emits with the right run_kind for the lifetime of
    # the stream.  The scope remains authoritative for the surface marker; child
    # tasks spawned during the turn inherit it.
    run_kind = "api" if task.run_type == "api" else "web"

    try:
        if task.goal is not None:
            _append(task, {"type": "goal_started", "goal": task.goal})
        with events_svc.run_kind_scope(run_kind):
            async for sse_line in stream_fn(
                task.run_id,
                message,
                history,
                goal=task.goal,
                steering_queue=task.steering,
            ):
                if sse_line.startswith("data: "):
                    try:
                        _append(task, json.loads(sse_line[6:].strip()))
                    except Exception:
                        pass

            if task.goal_id is not None:
                from aespa.services import alice_goals

                current = alice_goals.get_goal(run_kind, task.run_id, task.tab_id)
                if current is not None and current.status == "active":
                    current = alice_goals.update_goal(
                        task.goal_id,
                        status="paused",
                        pause_reason="ALICE stopped before the goal completion gate passed.",
                    )
                    _append(
                        task,
                        {
                            "type": "goal_paused",
                            "goal": alice_goals.goal_out(current),
                        },
                    )

            # Calibrate all findings for this run when Alice finishes
            is_api = task.run_type == "api"
            from aespa.services.scanner import calibrate_all_findings_for_run

            try:
                calibrate_all_findings_for_run(task.run_id, is_api_run=is_api)
            except Exception as ce:
                log.warning("calibrate_all_findings_for_run failed: %s", ce)
    except asyncio.CancelledError:
        if task.goal_id is not None:
            from aespa.services import alice_goals

            current = alice_goals.update_goal(
                task.goal_id, status="paused", pause_reason="Paused by user."
            )
            _append(
                task,
                {"type": "goal_paused", "goal": alice_goals.goal_out(current)},
            )
        _append(
            task,
            {
                "type": "done",
                "thought": task.accumulated_thought,
                "message": task.accumulated_message or "Stopped by user.",
            },
        )
        raise
    except Exception as exc:
        log.exception("ALICE background task failed for run_id=%s", task.run_id)
        _append(
            task,
            {
                "type": "done",
                "thought": task.accumulated_thought,
                "message": f"Agent encountered an error: {exc}",
            },
        )
        if task.goal_id is not None:
            from aespa.services import alice_goals

            current = alice_goals.update_goal(
                task.goal_id, status="paused", pause_reason=str(exc)
            )
            _append(
                task,
                {"type": "goal_paused", "goal": alice_goals.goal_out(current)},
            )
    finally:
        task.done = True
        for q in list(task.waiters):
            q.put_nowait(None)  # sentinel to close all client streams
        task.waiters.clear()
