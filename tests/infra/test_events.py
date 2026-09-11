"""Regression tests for run-kind-safe SSE routing."""

from __future__ import annotations

import asyncio
import logging


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
