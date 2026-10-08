from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from aespa.services import llm, sast_scanner, sast_scanner_light
from aespa.services.codex_provider import CodexOpenFileLimitError
from aespa.services.sast_worker_concurrency import (
    AdaptiveWorkerGate,
    gather_workers,
    worker_gate,
)


def test_reduced_gate_queues_new_workers_until_active_sessions_finish():
    async def scenario():
        gate = AdaptiveWorkerGate(4)
        first = await gate.__aenter__()
        second = await gate.__aenter__()
        assert first is gate and second is gate
        assert await gate.reduce() == 2
        assert await gate.reduce() == 1

        entered = asyncio.Event()

        async def next_worker():
            async with gate:
                entered.set()

        task = asyncio.create_task(next_worker())
        await asyncio.sleep(0)
        assert not entered.is_set()
        await gate.__aexit__(None, None, None)
        await asyncio.sleep(0)
        assert not entered.is_set()
        await gate.__aexit__(None, None, None)
        await asyncio.wait_for(task, timeout=1)
        assert entered.is_set()

    asyncio.run(scenario())


def test_failed_discovery_group_cancels_and_awaits_other_workers():
    async def scenario():
        started = asyncio.Event()
        stopped = asyncio.Event()

        async def failing_worker():
            await started.wait()
            raise RuntimeError("worker failed")

        async def waiting_worker():
            started.set()
            try:
                await asyncio.Future()
            finally:
                stopped.set()

        with pytest.raises(RuntimeError, match="worker failed"):
            await gather_workers([failing_worker(), waiting_worker()])
        assert stopped.is_set()

    asyncio.run(scenario())


@pytest.mark.parametrize("scanner", [sast_scanner, sast_scanner_light])
def test_codex_file_limit_retries_saved_worker_at_lower_concurrency(
    scanner, monkeypatch
):
    checkpoints = []
    attempts = []
    monkeypatch.setattr(llm, "_read_run_concurrency_limit", lambda _kind: 4)
    monkeypatch.setattr(scanner, "_load_checkpoint", lambda *_args: {})
    monkeypatch.setattr(
        scanner, "_save_checkpoint", lambda *_args: checkpoints.append(_args[-1])
    )
    monkeypatch.setattr(scanner.events_svc, "emit", lambda *_args: None)
    monkeypatch.setattr(scanner, "_SAST_NETWORK_RETRY_DELAYS", (0, 0, 0))

    async def fake_loop(_config, **kwargs):
        attempts.append(kwargs["resume_step_count"])
        if len(attempts) == 1:
            await kwargs["on_checkpoint"]([{"role": "user", "content": "saved"}], 1)
        if len(attempts) <= 2:
            raise CodexOpenFileLimitError("too many open files")
        return "finished"

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)

    async def scenario():
        result = await scanner._run_checkpointed_agent(
            sast_run_id=1,
            phase="discovery",
            worker_key="route:1",
            config=SimpleNamespace(provider="openai_codex", max_tokens=100),
            system_message="system",
            initial_user_message="start",
            tool_executor=lambda *_args: None,
            emit_fn=lambda *_args: None,
            stop_check=lambda: False,
            tools=[],
            resume=False,
        )
        return result, worker_gate("openai_codex", 4).limit

    result, limit = asyncio.run(scenario())

    assert result == "finished"
    assert attempts == [0, 1, 1]
    assert checkpoints[0]["step_count"] == 1
    assert limit == 1
