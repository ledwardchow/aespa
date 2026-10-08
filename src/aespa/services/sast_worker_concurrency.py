"""Queue Codex SAST workers and lower concurrency after file-limit errors."""

from __future__ import annotations

import asyncio
import weakref
from collections.abc import Awaitable, Iterable
from typing import TypeVar

_T = TypeVar("_T")


class AdaptiveWorkerGate:
    def __init__(self, limit: int) -> None:
        self.limit = max(1, limit)
        self.active = 0
        self._condition = asyncio.Condition()

    async def __aenter__(self) -> AdaptiveWorkerGate:
        async with self._condition:
            while self.active >= self.limit:
                await self._condition.wait()
            self.active += 1
        return self

    async def __aexit__(self, *_exc: object) -> None:
        async with self._condition:
            self.active -= 1
            self._condition.notify_all()

    async def reduce(self) -> int:
        async with self._condition:
            self.limit = max(1, self.limit // 2)
            self._condition.notify_all()
            return self.limit


_codex_gates: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, AdaptiveWorkerGate
] = weakref.WeakKeyDictionary()


def worker_gate(provider: str, limit: int) -> AdaptiveWorkerGate | asyncio.Semaphore:
    """Share the Codex limit across SAST runs in this server process."""
    if str(provider) != "openai_codex":
        return asyncio.Semaphore(max(1, limit))
    loop = asyncio.get_running_loop()
    gate = _codex_gates.get(loop)
    if gate is None:
        gate = AdaptiveWorkerGate(limit)
        _codex_gates[loop] = gate
    else:
        gate.limit = min(gate.limit, max(1, limit))
    return gate


async def gather_workers(workers: Iterable[Awaitable[_T]]) -> list[_T]:
    """Stop sibling workers before leaving a failed discovery group."""
    tasks = [asyncio.create_task(worker) for worker in workers]
    try:
        return list(await asyncio.gather(*tasks))
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
