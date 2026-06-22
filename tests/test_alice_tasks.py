"""Tests for ALICE background-task event buffering and reconnect replay."""
import asyncio
import json

from aespa.services import alice_tasks as at


def _task(run_id=1, run_type="site"):
    return at.AliceTask(
        run_id=run_id, tab_id="t", think_msg_id="th", reply_msg_id="re",
        run_type=run_type,
    )


def test_buffer_trim_tracks_dropped_and_keeps_cursor_aligned():
    task = _task()
    total = at.BUFFER_LIMIT + 50
    for i in range(total):
        at._append(task, {"type": "x", "i": i})

    # The buffer is bounded and `dropped` accounts for every evicted event.
    assert len(task.events) <= at.BUFFER_LIMIT
    assert task.dropped == total - len(task.events)
    # The first retained event sits at absolute index == dropped.
    assert task.events[0]["i"] == task.dropped

    # A reconnect cursor inside the retained window maps to the right slice —
    # pre-fix this used the absolute cursor as a buffer index and lost events.
    cursor = total - 10
    start = max(0, cursor - task.dropped)
    assert [e["i"] for e in task.events[start:]] == list(range(cursor, total))


def test_stream_events_replays_exactly_from_cursor_after_trim():
    task = _task(run_id=42)
    total = at.BUFFER_LIMIT + 30
    for i in range(total):
        at._append(task, {"type": "x", "i": i})
    task.done = True
    at._registry[("site", 42)] = task
    try:
        cursor = total - 5

        async def _drain():
            return [
                line async for line in at.stream_events(42, cursor=cursor, run_type="site")
            ]

        got = [json.loads(line[6:]) for line in asyncio.run(_drain())]
        assert [e["i"] for e in got] == list(range(cursor, total))
    finally:
        at._registry.pop(("site", 42), None)
