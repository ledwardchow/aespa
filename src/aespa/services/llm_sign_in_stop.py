"""Stop a run when its LLM provider needs the user to sign in again.

A rejected sign-in cannot recover by retrying, so the run that hit it is
stopped, marked failed with a message saying what to do, and the UI is told
once. Later calls from the same run are ignored while the stop is in progress.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime

from sqlmodel import Session

from aespa.db import get_engine
from aespa.models import ApiTestRun, SastRun, TestRun, TestRunStatus
from aespa.services import events as events_svc

log = logging.getLogger(__name__)

EVENT_TYPE = "llm_sign_in_required"

_stopping: set[tuple[str, int]] = set()
_stop_tasks: set[asyncio.Task] = set()


def schedule_stop(run_kind: str | None, run_id: int | None, message: str) -> bool:
    """Stop the run in a separate task; return False when nothing was started.

    The caller is usually running inside the task being stopped, so the stop
    runs on its own task and the caller simply re-raises its error.
    """
    if run_id is None or run_kind not in {"web", "api", "sast"}:
        return False
    key = (run_kind, run_id)
    if key in _stopping:
        return False
    _stopping.add(key)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _stopping.discard(key)
        return False
    task = loop.create_task(_stop(run_kind, run_id, message))
    _stop_tasks.add(task)
    task.add_done_callback(_stop_tasks.discard)
    return True


async def _stop(run_kind: str, run_id: int, message: str) -> None:
    log.warning("Stopping %s run %s: %s", run_kind, run_id, message)
    try:
        with contextlib.suppress(Exception):
            await _stop_workers(run_kind, run_id)
        _mark_failed(run_kind, run_id, message)
        with events_svc.run_kind_scope(run_kind):
            events_svc.emit(
                run_id,
                {
                    "type": EVENT_TYPE,
                    "message": message,
                    "_persist": True,
                },
            )
            events_svc.emit(
                run_id,
                {"type": "run_update", "status": "failed", "error_message": message},
            )
    except Exception:
        log.exception("Could not stop %s run %s after sign-in error", run_kind, run_id)
    finally:
        _stopping.discard((run_kind, run_id))


async def _stop_workers(run_kind: str, run_id: int) -> None:
    if run_kind == "web":
        from aespa.services import crawl_then_pentest
        from aespa.services import crawler as crawler_svc
        from aespa.services import scanner as scanner_svc
        from aespa.services import validator as validator_svc

        # A finished crawl must not start a pentest that would fail the same way.
        crawl_then_pentest.cancel(run_id)
        if crawler_svc.is_running(run_id):
            await crawler_svc.stop_and_wait(run_id)
        if scanner_svc.is_thinking_running(run_id):
            await scanner_svc.stop_thinking_and_wait(run_id)
        if validator_svc.is_validating(run_id):
            await validator_svc.stop_and_wait(run_id)
    elif run_kind == "api":
        from aespa.services import api_scanner

        await api_scanner.stop_api_scan_and_wait(run_id)
    elif run_kind == "sast":
        from aespa.services import sast_scanner, sast_scanner_light

        if run_id in sast_scanner._sast_tasks:
            await sast_scanner.stop_sast_scan_and_wait(run_id)
        if run_id in sast_scanner_light._sast_tasks:
            await sast_scanner_light.stop_sast_scan_and_wait(run_id)


def _mark_failed(run_kind: str, run_id: int, message: str) -> None:
    model = {"web": TestRun, "api": ApiTestRun, "sast": SastRun}[run_kind]
    with Session(get_engine()) as s:
        run = s.get(model, run_id)
        if run is None:
            return
        run.status = TestRunStatus.failed.value
        run.error_message = message
        run.completed_at = run.completed_at or datetime.now(UTC)
        s.add(run)
        s.commit()
