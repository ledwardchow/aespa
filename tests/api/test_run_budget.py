from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from sqlmodel import Session

from aespa.models import Site, TestRun
from aespa.services import llm, scanner
from aespa.services import run_pause as run_pause_svc


@pytest.fixture(autouse=True)
def _clean_usage():
    llm._run_token_usage.clear()
    llm._run_concurrency_gates.clear()
    yield
    llm._run_token_usage.clear()
    llm._run_concurrency_gates.clear()


def _run(engine, **fields) -> int:
    with Session(engine) as session:
        site = Site(name="Target", base_url="https://target.local")
        session.add(site)
        session.commit()
        session.refresh(site)
        run = TestRun(site_id=site.id, name="Run #1", **fields)
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def _spend(run_id: int, usd: float) -> None:
    llm._run_token_usage[("web", run_id)] = {
        "model-a": {
            "input": 1000,
            "output": 100,
            "provider": "anthropic",
            "estimated_cost_available": True,
            "estimated_total_cost_usd": usd,
        }
    }
    llm._run_token_seeded.add(("web", run_id))


async def _one_llm_call(run_id: int) -> None:
    llm.set_run_context(run_id, emit_fn=None)
    try:
        async with llm._run_concurrency_slot():
            pass
    finally:
        llm.clear_run_context()


def test_create_and_patch_budget(client, isolated_db_engine):
    site_id = client.post(
        "/api/sites", json={"name": "Target", "base_url": "https://target.local"}
    ).json()["id"]
    created = client.post(
        f"/api/sites/{site_id}/test-runs", json={"llm_budget_usd": 10}
    ).json()
    assert created["llm_budget_usd"] == 10

    run_id = created["id"]
    raised = client.patch(
        f"/api/test-runs/{run_id}/budget", json={"llm_budget_usd": 25}
    )
    assert raised.json()["llm_budget_usd"] == 25

    cleared = client.patch(
        f"/api/test-runs/{run_id}/budget", json={"llm_budget_usd": None}
    )
    assert cleared.json()["llm_budget_usd"] is None

    rejected = client.patch(
        f"/api/test-runs/{run_id}/budget", json={"llm_budget_usd": 0}
    )
    assert rejected.status_code == 422


def test_llm_calls_stop_once_spend_reaches_budget(engine):
    run_id = _run(engine, llm_budget_usd=5.0)

    _spend(run_id, 4.99)
    asyncio.run(_one_llm_call(run_id))

    _spend(run_id, 5.0)
    with pytest.raises(llm.LLMBudgetPauseError):
        asyncio.run(_one_llm_call(run_id))


def test_runs_without_budget_are_never_paused(engine):
    run_id = _run(engine)
    _spend(run_id, 10_000.0)
    asyncio.run(_one_llm_call(run_id))


def test_raising_budget_lets_calls_continue(client, engine):
    run_id = _run(engine, llm_budget_usd=5.0)
    _spend(run_id, 6.0)
    with pytest.raises(llm.LLMBudgetPauseError):
        asyncio.run(_one_llm_call(run_id))

    client.patch(f"/api/test-runs/{run_id}/budget", json={"llm_budget_usd": 20})
    asyncio.run(_one_llm_call(run_id))


def test_scan_pauses_with_budget_reason(monkeypatch, engine):
    run_id = _run(engine, llm_budget_usd=5.0, status="running", phase="scanning")
    _spend(run_id, 5.5)
    events = []

    async def fake_do_thinking_scan(run_id: int) -> None:
        await _one_llm_call(run_id)

    monkeypatch.setattr(scanner, "_do_thinking_scan", fake_do_thinking_scan)
    monkeypatch.setattr(
        scanner.events_svc, "emit", lambda _rid, evt: events.append(evt)
    )
    try:
        asyncio.run(scanner._thinking_scan_task(run_id))
    finally:
        scanner._thinking_scan_status.pop(run_id, None)

    with Session(engine) as session:
        run = session.get(TestRun, run_id)
    assert run.status == "paused"
    assert run.terminal_reason == "budget_reached"
    assert run_pause_svc.get_pause("web", run_id).reason == "budget"
    assert any(
        evt.get("type") == "scan_paused" and evt.get("reason") == "budget"
        for evt in events
    )


def test_resume_refused_until_budget_is_raised(client, engine):
    run_id = _run(engine, llm_budget_usd=5.0, status="paused", phase="scanning")
    _spend(run_id, 5.5)

    with (
        patch(
            "aespa.api.scan.checkpoint_svc.checkpoint_status",
            return_value={"exists": True, "step_count": 4},
        ),
        patch("aespa.api.scan.scanner_svc.start_thinking_scan_resume") as resume,
        patch(
            "aespa.api.scan.scanner_svc.get_thinking_scan_status",
            return_value={"status": "running", "run_id": run_id},
        ),
        patch("aespa.services.web_workprogram.seed_web_workprogram"),
    ):
        refused = client.post(f"/api/test-runs/{run_id}/thinking-scan/resume")
        assert refused.status_code == 409
        assert "Raise the budget" in refused.json()["detail"]
        resume.assert_not_awaited()

        client.patch(f"/api/test-runs/{run_id}/budget", json={"llm_budget_usd": 20})
        resumed = client.post(f"/api/test-runs/{run_id}/thinking-scan/resume")
        assert resumed.status_code == 200
        resume.assert_awaited_once_with(run_id)
