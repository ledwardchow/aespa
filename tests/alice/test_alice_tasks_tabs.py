from __future__ import annotations

import asyncio

import aespa.services.alice_tasks as alice_tasks


def test_chat_tabs_on_same_run_work_concurrently(monkeypatch):
    """A message in one chat tab must not cancel ALICE work in another tab."""
    release = asyncio.Event

    async def scenario():
        gate = release()

        async def _slow_run(task, message, history):
            try:
                await gate.wait()
            finally:
                task.done = True

        monkeypatch.setattr(alice_tasks, "_run", _slow_run)
        try:
            first = await alice_tasks.start(
                4242,
                tab_id="tab-a",
                think_msg_id="th-a",
                reply_msg_id="re-a",
                message="test login",
                history=[],
            )
            second = await alice_tasks.start(
                4242,
                tab_id="tab-b",
                think_msg_id="th-b",
                reply_msg_id="re-b",
                message="test search",
                history=[],
            )
            await asyncio.sleep(0)

            assert not first.asyncio_task.done()
            assert not second.asyncio_task.done()
            assert alice_tasks.get(4242, tab_id="tab-a") is first
            assert alice_tasks.get(4242, tab_id="tab-b") is second
            assert alice_tasks.is_running(4242)

            # Stopping one tab leaves the other running.
            assert await alice_tasks.stop(4242, tab_id="tab-a") is True
            assert first.asyncio_task.done()
            assert not second.asyncio_task.done()
            assert alice_tasks.status(4242, tab_id="tab-b")["running"] is True

            # Stopping the run as a whole stops every tab.
            assert await alice_tasks.stop(4242) is True
            assert second.asyncio_task.done()
            assert not alice_tasks.is_running(4242)
        finally:
            gate.set()
            for key in [k for k in alice_tasks._registry if k[1] == 4242]:
                alice_tasks._registry.pop(key, None)

    asyncio.run(scenario())


def test_finding_hook_stays_until_last_alice_turn_finishes():
    """Overlapping turns share the workprogram hook; finish order doesn't matter."""
    from aespa.services import alice
    from aespa.services.scanner import _finding_hooks

    run_id = 4243
    try:
        alice._acquire_alice_finding_hook(run_id)  # tab A starts
        hook = _finding_hooks[run_id]
        alice._acquire_alice_finding_hook(run_id)  # tab B starts
        assert _finding_hooks[run_id] is hook

        alice._release_alice_finding_hook(run_id)  # tab B finishes first
        assert _finding_hooks.get(run_id) is hook

        alice._release_alice_finding_hook(run_id)  # tab A finishes
        assert run_id not in _finding_hooks
        assert run_id not in alice._alice_finding_hooks
    finally:
        _finding_hooks.pop(run_id, None)
        alice._alice_finding_hooks.pop(run_id, None)


def test_finding_hook_release_keeps_hook_installed_by_another_component():
    from aespa.services import alice
    from aespa.services.scanner import _finding_hooks

    run_id = 4244

    def scanner_hook(finding):
        return None

    try:
        alice._acquire_alice_finding_hook(run_id)
        _finding_hooks[run_id] = scanner_hook  # e.g. a scan started afterwards
        alice._release_alice_finding_hook(run_id)
        assert _finding_hooks[run_id] is scanner_hook
    finally:
        _finding_hooks.pop(run_id, None)
        alice._alice_finding_hooks.pop(run_id, None)
