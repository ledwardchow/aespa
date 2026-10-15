from __future__ import annotations

import asyncio

from sqlmodel import Session

from aespa.db import get_engine
from aespa.models import Site, TestRun
from aespa.services import crawler as crawler_svc
from aespa.services import events as events_svc
from aespa.services import llm_sign_in_stop


def _running_web_run() -> int:
    with Session(get_engine()) as s:
        site = Site(name="Site", base_url="https://example.test")
        s.add(site)
        s.commit()
        s.refresh(site)
        run = TestRun(site_id=site.id, name="Scan", status="running")
        s.add(run)
        s.commit()
        s.refresh(run)
        return run.id


def test_sign_in_error_stops_web_run_once_and_tells_the_user(monkeypatch):
    run_id = _running_web_run()
    emitted = []
    monkeypatch.setattr(events_svc, "emit", lambda rid, evt: emitted.append((rid, evt)))

    async def scenario():
        crawl = asyncio.create_task(asyncio.sleep(60))
        crawler_svc._active_tasks[run_id] = crawl
        try:
            assert llm_sign_in_stop.schedule_stop("web", run_id, "Sign in again")
            assert not llm_sign_in_stop.schedule_stop("web", run_id, "Sign in again")
            await asyncio.gather(*llm_sign_in_stop._stop_tasks)
        finally:
            crawler_svc._active_tasks.pop(run_id, None)
        return crawl

    crawl = asyncio.run(scenario())

    assert crawl.cancelled()
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        assert run.status == "failed"
        assert run.error_message == "Sign in again"
        assert run.completed_at is not None
    alerts = [evt for rid, evt in emitted if evt["type"] == "llm_sign_in_required"]
    assert alerts == [
        {"type": "llm_sign_in_required", "message": "Sign in again", "_persist": True}
    ]


def test_calls_outside_a_run_do_not_stop_anything():
    assert not llm_sign_in_stop.schedule_stop("web", None, "Sign in again")
    assert not llm_sign_in_stop.schedule_stop(None, 1, "Sign in again")
