"""Regression tests for run-kind-safe SSE routing."""

from __future__ import annotations

import asyncio
import json
import logging

from sqlmodel import Session, select

from aespa.models import ScanLog


def test_event_bus_separates_colliding_run_ids():
    from aespa.services import events

    web_queue: asyncio.Queue = asyncio.Queue()
    sast_queue: asyncio.Queue = asyncio.Queue()
    web_key = ("web", 42)
    sast_key = ("sast", 42)
    events._queues[web_key] = [web_queue]
    events._queues[sast_key] = [sast_queue]
    try:
        with events.run_kind_scope("sast"):
            events.emit(42, {"type": "scanner_phase", "phase": "sast_extract"})

        assert sast_queue.get_nowait()["phase"] == "sast_extract"
        assert web_queue.empty()
    finally:
        events._queues.pop(web_key, None)
        events._queues.pop(sast_key, None)


def test_agent_status_is_mirrored_to_console_activity(caplog, monkeypatch):
    from aespa.services import events

    monkeypatch.setattr(events, "_persist_agent_status_event", lambda *_args: None)
    caplog.set_level(logging.INFO, logger="aespa.agent.activity")

    with events.run_kind_scope("api"):
        events.emit(
            17,
            {
                "type": "agent_status",
                "agent_id": "validator-4",
                "role": "Validator",
                "status": "complete",
                "current_task": "Review finding",
                "outcome": "Confirmed",
            },
        )

    assert caplog.messages == [
        "api run 17  COMPLETE    Validator (validator-4)  Review finding -> Confirmed"
    ]


def test_persist_only_phase_event_is_not_broadcast(monkeypatch):
    from aespa.services import events

    queue: asyncio.Queue = asyncio.Queue()
    key = ("web", 91)
    persisted: list[tuple[int, dict]] = []
    events._queues[key] = [queue]
    monkeypatch.setattr(
        events,
        "_persist_phase_event",
        lambda run_id, event: persisted.append((run_id, event)),
    )
    event = {
        "type": "scanner_phase",
        "phase": "llm_cache",
        "_persist_only": True,
    }
    try:
        events.emit(91, event)
    finally:
        events._queues.pop(key, None)

    assert queue.empty()
    assert persisted == [(91, event)]


def test_sast_phase_events_keep_concurrent_agent_identities(isolated_db_engine):
    from aespa.services import events

    queue: asyncio.Queue = asyncio.Queue()
    key = ("sast", 92)
    events._queues[key] = [queue]

    async def worker(agent_id: str):
        with events.agent_scope(agent_id, "SAST Worker"):
            await asyncio.sleep(0)
            events.emit(
                92,
                {
                    "type": "scanner_phase",
                    "phase": "llm_request",
                    "data": {"step": 1},
                },
            )

    async def run_workers():
        await asyncio.gather(worker("worker-a"), worker("worker-b"))

    try:
        with events.run_kind_scope("sast"):
            asyncio.run(run_workers())
    finally:
        events._queues.pop(key, None)

    live = [queue.get_nowait() for _ in range(2)]
    assert {event["agent_id"] for event in live} == {"worker-a", "worker-b"}
    assert all(event["role"] == "SAST Worker" for event in live)
    with Session(isolated_db_engine) as session:
        rows = session.exec(select(ScanLog).where(ScanLog.test_run_id == 92)).all()
    assert {
        json.loads(row.data_json)["_activity_agent"]["agent_id"] for row in rows
    } == {"worker-a", "worker-b"}
    assert all(json.loads(row.data_json)["step"] == 1 for row in rows)
