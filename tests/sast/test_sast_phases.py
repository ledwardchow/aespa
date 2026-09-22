from __future__ import annotations

import asyncio
import json
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlmodel import Session, select

from aespa.models import (
    AgentLog,
    LLMConfig,
    LLMProfile,
    PhaseCheckpoint,
    RunPause,
    SastRun,
    SastWorker,
    ScanLead,
    ScanLog,
    Site,
)
from aespa.models import TestRun as WebTestRun
from aespa.services import events as events_svc
from aespa.services import sast_scanner
from aespa.services.scan_leads import create_lead


@pytest.mark.parametrize(
    "provider",
    ["openai_codex", "github_copilot", "factory_droid", "google_vertex"],
)
def test_semantic_phases_accept_session_authenticated_providers(provider):
    config = SimpleNamespace(provider=provider, api_key=None, base_url=None)

    assert sast_scanner._llm_is_available_for_semantic_phases(config)


def test_light_run_uses_original_scanner_engine(isolated_db_engine, monkeypatch):
    from aespa.services import sast_scanner_light

    with Session(isolated_db_engine) as session:
        run = SastRun(name="light review", analysis_mode="light")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    calls = []

    async def fake_start(sast_run_id: int, *, resume: bool = False):
        calls.append((sast_run_id, resume))

    monkeypatch.setattr(sast_scanner_light, "start_sast_scan", fake_start)

    asyncio.run(sast_scanner.start_sast_scan(run_id, resume=True))

    assert calls == [(run_id, True)]


def _run_with_web_target(engine) -> tuple[int, int]:
    with Session(engine) as session:
        sast_run = SastRun(
            name="review",
            status="completed",
            phase_state_json=json.dumps(
                {
                    "scope": {
                        "status": "complete",
                        "message": "2 files inventoried",
                        "data": {"files_total": 2},
                    }
                }
            ),
            coverage_json=json.dumps(
                {
                    "files": [],
                    "summary": {"files_total": 2, "files_reviewed": 1},
                }
            ),
        )
        site = Site(name="Target", base_url="https://target.test")
        session.add(sast_run)
        session.add(site)
        session.commit()
        session.refresh(sast_run)
        session.refresh(site)
        web_run = WebTestRun(site_id=site.id, name="Live confirmation")
        session.add(web_run)
        session.commit()
        session.refresh(web_run)
        return sast_run.id, web_run.id


def test_analysis_endpoint_returns_persisted_semantic_state(client, isolated_db_engine):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)

    response = client.get(f"/api/sast-runs/{sast_run_id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["phases"]["scope"]["status"] == "complete"
    assert body["coverage"]["summary"] == {
        "files_total": 2,
        "files_reviewed": 1,
    }


def test_agent_log_recovers_fixed_agent_state_from_phase_history(
    client, isolated_db_engine
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        session.add(
            ScanLog(
                test_run_id=sast_run_id,
                run_kind="sast",
                phase="threat_model",
                status="complete",
                message="Threat model ready.",
            )
        )
        session.commit()

    response = client.get(f"/api/sast-runs/{sast_run_id}/agent-log")

    assert response.status_code == 200
    threat = next(
        entry
        for entry in response.json()
        if entry["agent_id"] == "sast-threat-modeller"
    )
    assert threat["status"] == "complete"
    assert threat["display_name"] == "Threat Modeller"
    assert threat["current_task"] == "Threat model ready."


@pytest.mark.parametrize("scanner_module", [sast_scanner, pytest.param(None, id="light")])
def test_running_phase_updates_sast_analyst_status(
    isolated_db_engine, scanner_module
):
    if scanner_module is None:
        from aespa.services import sast_scanner_light

        scanner_module = sast_scanner_light

    with Session(isolated_db_engine) as session:
        run = SastRun(name="live phase status")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    with events_svc.run_kind_scope("sast"):
        scanner_module._set_phase(
            run_id,
            "discovery",
            "running",
            "Reviewing source-to-sink paths.",
        )

    with Session(isolated_db_engine) as session:
        analyst = session.exec(
            select(AgentLog)
            .where(AgentLog.test_run_id == run_id)
            .where(AgentLog.run_kind == "sast")
            .where(AgentLog.agent_id == "sast-scanner")
        ).one()

    assert analyst.status == "active"
    assert analyst.current_task == "Reviewing source-to-sink paths."


@pytest.mark.parametrize(
    "scanner_module", [sast_scanner, pytest.param(None, id="light")]
)
def test_phase_timing_keeps_only_active_resume_intervals(
    isolated_db_engine, scanner_module
):
    if scanner_module is None:
        from aespa.services import sast_scanner_light

        scanner_module = sast_scanner_light

    phase_state = scanner_module._empty_phase_state()
    phase_state["discovery"] = {
        "status": "paused",
        "message": "Paused",
        "data": {},
        "active_elapsed_ms": 1200,
        "started_at": "2026-01-01T00:00:00+00:00",
        "active_intervals": [
            {
                "started_at": "2026-01-01T00:00:00+00:00",
                "ended_at": "2026-01-01T00:00:01.200000+00:00",
            }
        ],
    }
    with Session(isolated_db_engine) as session:
        run = SastRun(name="phase timing", phase_state_json=json.dumps(phase_state))
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    scanner_module._set_phase(run_id, "discovery", "running", "Resumed")
    scanner_module._set_phase(run_id, "discovery", "complete", "Done")

    with Session(isolated_db_engine) as session:
        saved = json.loads(session.get(SastRun, run_id).phase_state_json)

    assert saved["discovery"]["active_elapsed_ms"] >= 1200
    assert saved["discovery"]["active_elapsed_ms"] < 5000
    assert saved["discovery"]["first_started_at"] == "2026-01-01T00:00:00+00:00"
    assert len(saved["discovery"]["active_intervals"]) == 2
    assert saved["discovery"]["completed_at"] >= saved["discovery"]["started_at"]


def test_agent_log_replays_persisted_worker_and_validator_activity(
    client, isolated_db_engine
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    now = datetime.now(timezone.utc)
    with Session(isolated_db_engine) as session:
        worker = SastWorker(
            sast_run_id=sast_run_id,
            worker_key="sink-audit:1",
            class_group="sink",
            status="blocked",
            error_message="2 assigned item(s) unresolved.",
            started_at=now,
            completed_at=now,
        )
        checkpoint = PhaseCheckpoint(
            run_kind="sast",
            run_id=sast_run_id,
            phase="validation",
            idempotency_key="agent:validator:17",
            completed_at=now,
        )
        session.add(worker)
        session.add(checkpoint)
        session.commit()
        session.refresh(worker)

    response = client.get(f"/api/sast-runs/{sast_run_id}/agent-log")

    assert response.status_code == 200
    entries = response.json()
    worker_entries = [
        entry for entry in entries if entry["agent_id"] == f"sast-worker-{worker.id}"
    ]
    assert [entry["status"] for entry in worker_entries] == [
        "spawned",
        "active",
        "blocked",
    ]
    assert all(entry["parent_id"] == "sast-sink-workers" for entry in worker_entries)
    assert all(entry["display_name"] == "sink-audit:1" for entry in worker_entries)
    assert all(entry["class_group"] == "sink" for entry in worker_entries)
    assert any(
        entry["agent_id"] == "sast-validator-17"
        and entry["status"] == "complete"
        and entry["parent_id"] == "sast-validators"
        and entry["display_name"] == "Candidate 17"
        for entry in entries
    )


def test_sast_summaries_prefer_live_scanner_status(
    client, isolated_db_engine, monkeypatch
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        run = session.get(SastRun, sast_run_id)
        run.status = "failed"
        session.add(run)
        session.commit()

    monkeypatch.setattr(
        sast_scanner,
        "is_sast_scan_running",
        lambda run_id: run_id == sast_run_id,
    )

    detail = client.get(f"/api/sast-runs/{sast_run_id}")
    listing = client.get("/api/sast-runs")

    assert detail.status_code == 200
    assert detail.json()["status"] == "scanning"
    assert listing.status_code == 200
    listed_run = next(run for run in listing.json() if run["id"] == sast_run_id)
    assert listed_run["status"] == "scanning"


def test_pause_endpoint_requests_cooperative_pause(
    client, isolated_db_engine, monkeypatch
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)

    async def fake_pause(run_id):
        assert run_id == sast_run_id
        return True

    monkeypatch.setattr(sast_scanner, "pause_sast_scan_and_wait", fake_pause)
    response = client.post(f"/api/sast-runs/{sast_run_id}/scan/pause")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "pause_requested": True}


def test_completed_run_with_failed_worker_can_resume(
    client, isolated_db_engine, monkeypatch
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        session.add(
            SastWorker(
                sast_run_id=sast_run_id,
                worker_key="sink-audit:resume",
                class_group="sink",
                status="failed",
                error_message="maximum context length exceeded",
            )
        )
        session.commit()

    starts = []

    async def fake_start(run_id, *, resume=False):
        starts.append((run_id, resume))

    monkeypatch.setattr(sast_scanner, "start_sast_scan", fake_start)
    monkeypatch.setattr(sast_scanner, "is_sast_scan_running", lambda _run_id: False)
    monkeypatch.setattr(
        sast_scanner,
        "get_sast_status",
        lambda run_id: {"run_id": run_id, "running": True},
    )

    response = client.post(f"/api/sast-runs/{sast_run_id}/scan/resume")

    assert response.status_code == 200
    assert response.json()["running"] is True
    assert starts == [(sast_run_id, True)]


def test_cancelled_run_with_unfinished_validation_can_resume(
    client, isolated_db_engine, monkeypatch
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        run = session.get(SastRun, sast_run_id)
        run.status = "cancelled"
        session.add(run)
        session.add(
            PhaseCheckpoint(
                run_kind="sast",
                run_id=sast_run_id,
                phase="state",
                idempotency_key="candidates",
                data_json=json.dumps(
                    {
                        "candidates": [
                            {
                                "candidate_id": 8,
                                "confidence": 0.91,
                                "validation_status": "inconclusive",
                            }
                        ]
                    }
                ),
            )
        )
        session.commit()

    starts = []

    async def fake_start(run_id, *, resume=False):
        starts.append((run_id, resume))

    monkeypatch.setattr(sast_scanner, "start_sast_scan", fake_start)
    monkeypatch.setattr(sast_scanner, "is_sast_scan_running", lambda _run_id: False)
    monkeypatch.setattr(
        sast_scanner,
        "get_sast_status",
        lambda run_id: {"run_id": run_id, "running": True},
    )

    response = client.post(f"/api/sast-runs/{sast_run_id}/scan/resume")

    assert response.status_code == 200
    assert starts == [(sast_run_id, True)]


def test_checkpointed_agent_retries_from_last_saved_turn(
    isolated_db_engine, monkeypatch
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    attempts: list[dict] = []

    async def fake_loop(_config, **kwargs):
        attempts.append(
            {
                "messages": kwargs.get("resume_messages"),
                "step_count": kwargs.get("resume_step_count"),
            }
        )
        if len(attempts) == 1:
            await kwargs["on_checkpoint"]([{"role": "user", "content": "start"}], 4)
            raise TimeoutError("temporary network loss")
        return "continued"

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(sast_scanner, "_SAST_NETWORK_RETRY_DELAYS", (0.0,))

    result = asyncio.run(
        sast_scanner._run_checkpointed_agent(
            sast_run_id=sast_run_id,
            phase="discovery",
            worker_key="discovery",
            config=object(),
            system_message="system",
            initial_user_message="start",
            tool_executor=lambda *_args: None,
            emit_fn=lambda _event: None,
            stop_check=lambda: False,
            tools=[],
            resume=False,
        )
    )

    assert result == "continued"
    assert attempts == [
        {"messages": None, "step_count": 0},
        {"messages": [{"role": "user", "content": "start"}], "step_count": 4},
    ]
    with Session(isolated_db_engine) as session:
        checkpoint = session.exec(
            select(PhaseCheckpoint)
            .where(PhaseCheckpoint.run_kind == "sast")
            .where(PhaseCheckpoint.run_id == sast_run_id)
        ).one()
    assert checkpoint.idempotency_key == "agent:discovery"


def test_checkpointed_agent_compacts_provider_rejected_context(
    isolated_db_engine, monkeypatch
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    attempts = []
    oversized = [
        {"role": "user", "content": "initial"},
        {"role": "assistant", "content": "x" * 20_000},
        {"role": "user", "content": "continue"},
    ]

    async def fake_loop(_config, **kwargs):
        attempts.append(kwargs.get("resume_messages"))
        if len(attempts) == 1:
            await kwargs["on_checkpoint"](oversized, 7)
            raise RuntimeError("out of memory for context size")
        return "continued after compaction"

    compact_calls = []

    def fake_compact(messages, **kwargs):
        compact_calls.append((messages, kwargs))
        return [messages[0], messages[-1]], {
            "before_chars": 20_100,
            "after_chars": 50,
            "compaction_applied": True,
        }

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(llm, "compact_agentic_messages", fake_compact)
    config = SimpleNamespace(
        max_context_tokens=100_000,
        max_tokens=10_000,
        model="fake-model",
        provider="openai",
    )

    result = asyncio.run(
        sast_scanner._run_checkpointed_agent(
            sast_run_id=sast_run_id,
            phase="discovery",
            worker_key="context-worker",
            config=config,
            system_message="system",
            initial_user_message="start",
            tool_executor=lambda *_args: None,
            emit_fn=lambda _event: None,
            stop_check=lambda: False,
            tools=[],
            resume=False,
        )
    )

    assert result == "continued after compaction"
    assert len(compact_calls) == 1
    assert attempts[1] == [oversized[0], oversized[-1]]
    with Session(isolated_db_engine) as session:
        checkpoint = session.exec(
            select(PhaseCheckpoint)
            .where(PhaseCheckpoint.run_kind == "sast")
            .where(PhaseCheckpoint.run_id == sast_run_id)
            .where(PhaseCheckpoint.idempotency_key == "agent:context-worker")
        ).one()
    assert json.loads(checkpoint.data_json)["context_recovery"]["after_chars"] == 50


def test_resume_start_keeps_existing_leads_and_phase_state(
    isolated_db_engine, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    with Session(isolated_db_engine) as session:
        run = SastRun(
            name="paused review",
            status="paused",
            phase_state_json=json.dumps(
                {"discovery": {"status": "complete", "message": "done", "data": {}}}
            ),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    create_lead(
        producer_run_id=run_id,
        title="Existing lead",
        description="Keep this result",
        confidence=0.9,
        validation_status="confirmed",
        reportable=True,
    )

    async def fake_task(_run_id, *, resume=False):
        assert resume is True

    monkeypatch.setattr(sast_scanner, "_sast_scan_task", fake_task)

    async def start_and_wait():
        await sast_scanner.start_sast_scan(run_id, resume=True)
        await sast_scanner._sast_tasks[run_id]
        sast_scanner._sast_tasks.pop(run_id, None)
        lease = sast_scanner._sast_workspace_leases.pop(run_id, None)
        if lease is not None:
            lease.release()

    asyncio.run(start_and_wait())

    with Session(isolated_db_engine) as session:
        saved_run = session.get(SastRun, run_id)
        lead = session.exec(
            select(ScanLead).where(ScanLead.producer_run_id == run_id)
        ).one()
    assert json.loads(saved_run.phase_state_json)["discovery"]["status"] == "complete"
    assert lead.validation_status == "confirmed"
    assert lead.reportable is True


def test_resume_skips_completed_repository_threat_and_planning_phases(
    isolated_db_engine, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("app.py", "print('hello')\n")

    saved_repository = {"inventory": {"files": []}, "nodes": [], "edges": []}
    saved_threats = {"summary": "Saved threat model", "scenarios": []}
    saved_planning = {
        "obligations": [],
        "workers": [],
        "dependency_analysis": {},
    }
    phase_state = sast_scanner._empty_phase_state()
    for phase, data in (
        ("repository_model", saved_repository),
        ("threat_model", saved_threats),
        ("planning", saved_planning),
    ):
        phase_state[phase] = {
            "status": "complete",
            "message": f"{phase} complete",
            "data": data,
        }

    with Session(isolated_db_engine) as session:
        config = LLMConfig(name="resume-test", is_active=True, model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = SastRun(
            name="paused deep review",
            status="paused",
            source_archive_path=str(archive),
            source_filename="source.zip",
            llm_config_id=config.id,
            phase_state_json=json.dumps(phase_state),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    def unexpected_semantic_rebuild(*_args, **_kwargs):
        raise AssertionError("completed semantic phase was rebuilt")

    async def unexpected_repository_reconciliation(*_args, **_kwargs):
        raise AssertionError("completed repository phase was rerun")

    agent_phases = []

    async def stop_during_discovery(**kwargs):
        agent_phases.append(kwargs["phase"])
        raise sast_scanner.SastPauseRequested("stop regression test")

    from aespa.services import llm, sast_semantic

    monkeypatch.setattr(
        sast_semantic, "build_repository_model", unexpected_semantic_rebuild
    )
    monkeypatch.setattr(
        sast_semantic,
        "reconcile_repository_model_with_llm",
        unexpected_repository_reconciliation,
    )
    monkeypatch.setattr(
        sast_semantic, "build_threat_model", unexpected_semantic_rebuild
    )
    monkeypatch.setattr(
        sast_semantic, "plan_semantic_obligations", unexpected_semantic_rebuild
    )
    monkeypatch.setattr(sast_scanner, "_run_checkpointed_agent", stop_during_discovery)
    monkeypatch.setattr(llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)

    asyncio.run(sast_scanner._sast_scan_task(run_id, resume=True))

    assert agent_phases
    assert set(agent_phases) == {"discovery"}
    with Session(isolated_db_engine) as session:
        saved_run = session.get(SastRun, run_id)
    resumed_phases = json.loads(saved_run.phase_state_json)
    assert resumed_phases["threat_model"]["status"] == "complete"
    assert resumed_phases["threat_model"]["data"] == saved_threats


def test_provider_network_failure_pauses_sast_run(
    isolated_db_engine, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("app.py", "print('ok')\n")
    with Session(isolated_db_engine) as session:
        config = LLMConfig(name="test", is_active=True, model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = SastRun(
            name="network pause",
            status="scanning",
            source_archive_path=str(archive),
            source_filename="source.zip",
            llm_config_id=config.id,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    async def unavailable(_config, **_kwargs):
        raise TimeoutError("network unavailable")

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", unavailable)
    monkeypatch.setattr(llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)
    monkeypatch.setattr(sast_scanner, "_SAST_NETWORK_RETRY_DELAYS", ())

    asyncio.run(sast_scanner._sast_scan_task(run_id))

    with Session(isolated_db_engine) as session:
        saved = session.get(SastRun, run_id)
        pause = session.exec(
            select(RunPause)
            .where(RunPause.run_kind == "sast")
            .where(RunPause.run_id == run_id)
        ).one()
    assert saved.status == "paused"
    assert pause.reason == "network"
    assert "resumed safely" in pause.message


def test_failed_discovery_workers_pause_instead_of_completing(
    isolated_db_engine, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "app.py",
            "def item(request):\n    return db.execute(request.args['id'])\n",
        )
    with Session(isolated_db_engine) as session:
        config = LLMConfig(name="test", is_active=True, model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = SastRun(
            name="worker failure pause",
            status="scanning",
            source_archive_path=str(archive),
            source_filename="source.zip",
            llm_config_id=config.id,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    async def context_failure(_config, **_kwargs):
        raise RuntimeError("maximum context length exceeded")

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", context_failure)
    monkeypatch.setattr(llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)

    asyncio.run(sast_scanner._sast_scan_task(run_id))

    with Session(isolated_db_engine) as session:
        saved = session.get(SastRun, run_id)
        pause = session.exec(
            select(RunPause)
            .where(RunPause.run_kind == "sast")
            .where(RunPause.run_id == run_id)
        ).one()
        workers = session.exec(
            select(SastWorker).where(SastWorker.sast_run_id == run_id)
        ).all()
    assert saved.status == "paused"
    assert saved.completed_at is None
    assert pause.reason == "worker_error"
    assert workers and all(worker.status == "failed" for worker in workers)


def test_sast_usage_context_starts_before_repository_model(
    isolated_db_engine, tmp_path, monkeypatch
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("app.py", "print('ok')\n")
    with Session(isolated_db_engine) as session:
        config = LLMConfig(name="test", is_active=True, model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = SastRun(
            name="usage context",
            status="scanning",
            source_archive_path=str(archive),
            source_filename="source.zip",
            llm_config_id=config.id,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    context_started = False

    def set_context(actual_run_id, _emit_fn, *, run_kind):
        nonlocal context_started
        assert actual_run_id == run_id
        assert run_kind == "sast"
        context_started = True

    def inspect_repository_model(_root):
        assert context_started is True
        raise RuntimeError("stop after checking usage context")

    from aespa.services import llm

    monkeypatch.setattr(llm, "set_run_context", set_context)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)
    monkeypatch.setattr(
        sast_scanner.semantic_svc, "build_repository_model", inspect_repository_model
    )

    asyncio.run(sast_scanner._sast_scan_task(run_id))

    assert context_started is True


@pytest.mark.parametrize(
    ("failure", "expected_reason", "expected_phase"),
    [
        (asyncio.CancelledError(), "interrupted", "discovery"),
        (RuntimeError("source inventory crashed"), "error", "scope"),
    ],
)
def test_sast_task_crashes_pause_for_resume(
    isolated_db_engine,
    tmp_path,
    monkeypatch,
    failure,
    expected_reason,
    expected_phase,
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive = tmp_path / "crashing-source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("app.py", "print('ok')\n")
    with Session(isolated_db_engine) as session:
        config = LLMConfig(name="test", is_active=True, model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = SastRun(
            name="resumable crash",
            status="scanning",
            source_archive_path=str(archive),
            source_filename="crashing-source.zip",
            llm_config_id=config.id,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    async def crash_agent(_config, **_kwargs):
        raise failure

    from aespa.services import llm

    if expected_reason == "interrupted":
        monkeypatch.setattr(llm, "thinking_agentic_loop", crash_agent)
    else:

        def crash_inventory(_root):
            raise failure

        monkeypatch.setattr(sast_scanner, "_build_source_inventory", crash_inventory)
    monkeypatch.setattr(llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)
    monkeypatch.setattr(sast_scanner, "_SAST_NETWORK_RETRY_DELAYS", ())

    asyncio.run(sast_scanner._sast_scan_task(run_id))

    with Session(isolated_db_engine) as session:
        saved = session.get(SastRun, run_id)
        pause = session.exec(
            select(RunPause)
            .where(RunPause.run_kind == "sast")
            .where(RunPause.run_id == run_id)
        ).one()
    assert saved.status == "paused"
    assert saved.completed_at is None
    assert pause.reason == expected_reason
    assert pause.resume_stage == expected_phase
    assert "last saved step" in pause.message


def test_sast_model_profile_can_be_changed_after_creation(client, isolated_db_engine):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        profile = LLMProfile(name="SAST review profile")
        session.add(profile)
        session.commit()
        session.refresh(profile)
        profile_id = profile.id

    updated = client.patch(
        f"/api/sast-runs/{sast_run_id}",
        json={"llm_profile_id": profile_id},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["llm_profile_id"] == profile_id

    cleared = client.patch(
        f"/api/sast-runs/{sast_run_id}",
        json={"llm_profile_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["llm_profile_id"] is None

    missing = client.patch(
        f"/api/sast-runs/{sast_run_id}",
        json={"llm_profile_id": 999999},
    )
    assert missing.status_code == 404


def test_sast_model_profile_cannot_change_while_scanning(client, isolated_db_engine):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        run = session.get(SastRun, sast_run_id)
        run.status = "scanning"
        session.add(run)
        session.commit()

    response = client.patch(
        f"/api/sast-runs/{sast_run_id}",
        json={"llm_profile_id": None},
    )
    assert response.status_code == 409


def test_handoff_requires_validation_and_is_idempotent(client, isolated_db_engine):
    sast_run_id, web_run_id = _run_with_web_target(isolated_db_engine)
    pending = create_lead(
        producer_run_id=sast_run_id,
        title="User input reaches SQL",
        description="Candidate",
        category="A03",
        severity="high",
        confidence=0.9,
        location="app.py:10",
        reportable=False,
        validation_status="pending",
    )
    rejected = client.post(
        f"/api/sast-runs/{sast_run_id}/leads/{pending.id}/handoff",
        json={"run_type": "web", "run_id": web_run_id},
    )
    assert rejected.status_code == 409

    confirmed = create_lead(
        producer_run_id=sast_run_id,
        title="User input reaches SQL",
        description="Validated candidate",
        category="A03",
        severity="high",
        confidence=0.94,
        location="app.py:10",
        reportable=True,
        validation_status="confirmed",
        source_trace={"file": "app.py", "line": 2},
        sink_trace={"file": "app.py", "line": 10},
        attack_path={"nodes": ["HTTP query", "handler", "SQL execute"]},
    )
    assert confirmed.id == pending.id

    first = client.post(
        f"/api/sast-runs/{sast_run_id}/leads/{confirmed.id}/handoff",
        json={"run_type": "web", "run_id": web_run_id},
    )
    second = client.post(
        f"/api/sast-runs/{sast_run_id}/leads/{confirmed.id}/handoff",
        json={"run_type": "web", "run_id": web_run_id},
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["lead_id"] == second.json()["lead_id"]
    with Session(isolated_db_engine) as session:
        copies = session.exec(
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == "web")
            .where(ScanLead.imported_into_run_id == web_run_id)
        ).all()
    assert len(copies) == 1
    assert copies[0].attack_path_json != "{}"


def test_review_executor_records_independent_verdict_and_attack_path(
    tmp_path, isolated_db_engine
):
    root = tmp_path / "source"
    root.mkdir()
    (root / "app.py").write_text("value = request.args['id']\ndb.execute(value)\n")
    coverage = sast_scanner._build_source_inventory(root)
    sast_scanner._candidates[41] = [
        {
            "candidate_id": 0,
            "title": "Injection",
            "location": "app.py:2",
            "reportable": False,
            "validation_status": "pending",
        }
    ]
    executor = sast_scanner._make_review_executor(41, root, coverage, "validation")
    result = asyncio.run(
        executor(
            "validate_candidate",
            {
                "candidate_id": 0,
                "verdict": "confirmed",
                "confidence": 0.91,
                "reasoning": "No parameterization is present.",
                "controls": '["Authentication middleware required"]',
                "counterevidence": "No parameterization found",
                "proof_gaps": [],
            },
            1,
        )
    )
    assert "confirmed" in result
    assert sast_scanner._candidates[41][0]["reportable"] is True
    assert sast_scanner._candidates[41][0]["controls"] == [
        "Authentication middleware required"
    ]
    assert sast_scanner._candidates[41][0]["counterevidence"] == [
        "No parameterization found"
    ]

    attack_executor = sast_scanner._make_review_executor(
        41, root, coverage, "attack_path"
    )
    asyncio.run(
        attack_executor(
            "record_attack_path",
            {
                "candidate_id": 0,
                "nodes": ["query id", "handler", "db.execute"],
                "impact": "Database access",
                "severity_reasoning": "Remote unauthenticated input",
                "dynamic_test": "GET /items?id='",
            },
            1,
        )
    )
    assert sast_scanner._candidates[41][0]["attack_path"]["nodes"][-1] == "db.execute"
    sast_scanner._candidates.pop(41, None)


def test_review_executor_persists_each_verdict_before_next_candidate(
    tmp_path, isolated_db_engine, monkeypatch
):
    root = tmp_path / "source"
    root.mkdir()
    (root / "app.py").write_text("print('hello')\n")
    coverage = sast_scanner._build_source_inventory(root)
    sast_scanner._candidates[42] = [
        {
            "candidate_id": 0,
            "title": "First candidate",
            "description": "First description",
            "category": "A03",
            "location": "app.py:1",
            "validation_status": "pending",
            "reportable": False,
        },
        {
            "candidate_id": 1,
            "title": "Second candidate",
            "description": "Second description",
            "category": "A01",
            "location": "app.py:1",
            "validation_status": "pending",
            "reportable": False,
        },
    ]
    emitted = []
    monkeypatch.setattr(
        sast_scanner.events_svc,
        "emit",
        lambda run_id, event: emitted.append((run_id, event)),
    )
    executor = sast_scanner._make_review_executor(42, root, coverage, "validation")

    asyncio.run(
        executor(
            "validate_candidate",
            {
                "candidate_id": 0,
                "verdict": "confirmed",
                "confidence": 0.91,
                "reasoning": "The first path is exploitable.",
            },
            1,
        )
    )

    with Session(isolated_db_engine) as session:
        leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == 42)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        ).all()
    assert [(lead.title, lead.validation_status) for lead in leads] == [
        ("First candidate", "confirmed")
    ]
    assert any(
        event.get("phase") == "sast_validation_result"
        and event.get("data", {}).get("candidate_id") == 0
        for _, event in emitted
    )

    asyncio.run(
        executor(
            "validate_candidate",
            {
                "candidate_id": 1,
                "verdict": "dismissed",
                "confidence": 0.84,
                "reasoning": "The second path is blocked.",
            },
            2,
        )
    )

    with Session(isolated_db_engine) as session:
        leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == 42)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .order_by(ScanLead.id)
        ).all()
    assert [(lead.title, lead.validation_status) for lead in leads] == [
        ("First candidate", "confirmed"),
        ("Second candidate", "dismissed"),
    ]
    sast_scanner._candidates.pop(42, None)


def test_file_inventory_records_actual_read_receipts(tmp_path, isolated_db_engine):
    root = tmp_path / "source"
    root.mkdir()
    (root / "app.py").write_text("print('hello')\n")
    (root / "notes.txt").write_text("documentation\n")
    coverage = sast_scanner._build_source_inventory(root)
    with Session(isolated_db_engine) as session:
        run = SastRun(name="inventory receipts")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    result = sast_scanner._run_read_tool(
        run_id, root, coverage, "discovery", "read_file", {"path": "app.py"}
    )

    assert "hello" in result
    assert coverage["app.py"]["reviewed"] is True
    assert coverage["app.py"]["phases"] == ["discovery"]
    assert coverage["notes.txt"]["reviewed"] is False


def test_failed_file_reads_do_not_create_coverage_receipts(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "app.py").write_text("print('hello')\n")
    coverage = sast_scanner._build_source_inventory(root)

    result = sast_scanner._run_read_tool(
        53, root, coverage, "validation", "read_file", {"path": "missing.py"}
    )
    listing = sast_scanner._run_read_tool(
        53, root, coverage, "validation", "list_files", {"path": "missing"}
    )

    assert result.startswith("Error: not a file")
    assert listing.startswith("Error: not a directory")
    assert coverage["app.py"]["reviewed"] is False


def test_discovery_candidates_are_persisted_before_validation(
    client, tmp_path, isolated_db_engine
):
    root = tmp_path / "source"
    root.mkdir()
    (root / "app.py").write_text("db.execute(request.args['id'])\n")
    with Session(isolated_db_engine) as session:
        run = SastRun(name="live candidates", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    executor = sast_scanner._make_tool_executor(run_id, root, None)
    candidate_input = {
        "title": "SQL injection",
        "category": "A03",
        "severity": "high",
        "location": "app.py:1",
        "description": "Request input reaches SQL execution.",
        "evidence": "db.execute(request.args['id'])",
        "confidence": 0.81,
        "confidence_reasoning": "A request parameter reaches the SQL sink.",
    }
    asyncio.run(executor("write_lead", candidate_input, 1))
    replay = asyncio.run(executor("write_lead", candidate_input, 1))

    assert "already recorded" in replay
    assert len(sast_scanner._candidates[run_id]) == 1

    with Session(isolated_db_engine) as session:
        lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        ).one()
        assert lead.validation_status == "pending"
        assert lead.confidence == 0.81

    response = client.get(f"/api/sast-runs/{run_id}/leads")
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["SQL injection"]

    asyncio.run(
        executor(
            "filter_lead",
            {"lead_id": 0, "confidence": 0.88, "reasoning": "Concrete path"},
            2,
        )
    )

    with Session(isolated_db_engine) as session:
        lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        ).one()
        assert lead.confidence == 0.88
        assert lead.validation_status == "pending"
    sast_scanner._candidates.pop(run_id, None)


@pytest.mark.parametrize("analysis_mode", ["light", "deep"])
def test_write_lead_requires_atomic_confidence(
    analysis_mode, tmp_path, isolated_db_engine
):
    scanner_module = sast_scanner
    if analysis_mode == "light":
        from aespa.services import sast_scanner_light

        scanner_module = sast_scanner_light

    root = tmp_path / analysis_mode
    root.mkdir()
    with Session(isolated_db_engine) as session:
        run = SastRun(name=f"{analysis_mode} confidence", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    executor = scanner_module._make_tool_executor(run_id, root, None)
    result = asyncio.run(
        executor(
            "write_lead",
            {
                "title": "Unscored lead",
                "category": "A03",
                "severity": "high",
                "location": "app.py:1",
                "description": "Missing a discovery score.",
                "evidence": "db.execute(value)",
            },
            1,
        )
    )

    assert result.startswith("Error: write_lead requires a numeric confidence")
    assert scanner_module._candidates[run_id] == []
    with Session(isolated_db_engine) as session:
        assert (
            session.exec(
                select(ScanLead).where(ScanLead.producer_run_id == run_id)
            ).all()
            == []
        )
    scanner_module._candidates.pop(run_id, None)


@pytest.mark.parametrize("analysis_mode", ["light", "deep"])
def test_unscored_checkpoint_candidates_become_inconclusive(analysis_mode):
    scanner_module = sast_scanner
    if analysis_mode == "light":
        from aespa.services import sast_scanner_light

        scanner_module = sast_scanner_light
    candidates = [
        {
            "candidate_id": 7,
            "confidence": None,
            "validation_status": "pending",
            "proof_gaps": [],
            "reportable": False,
        }
    ]

    assert scanner_module._close_unscored_candidates(candidates) == 1
    assert candidates[0]["validation_status"] == "inconclusive"
    assert "confidence score" in candidates[0]["validation_reasoning"]
    assert scanner_module._pending_candidate_ids(candidates) == []


@pytest.mark.parametrize("analysis_mode", ["light", "deep"])
def test_scored_inconclusive_candidates_still_require_validation(analysis_mode):
    scanner_module = sast_scanner
    if analysis_mode == "light":
        from aespa.services import sast_scanner_light

        scanner_module = sast_scanner_light
    candidates = [
        {
            "candidate_id": 8,
            "confidence": 0.91,
            "validation_status": "inconclusive",
            "reportable": False,
        }
    ]

    assert scanner_module._pending_candidate_ids(candidates) == [8]


@pytest.mark.parametrize("analysis_mode", ["light", "deep"])
def test_stopping_during_validation_checkpoints_pending_candidates(
    analysis_mode, isolated_db_engine
):
    scanner_module = sast_scanner
    if analysis_mode == "light":
        from aespa.services import sast_scanner_light

        scanner_module = sast_scanner_light
    run_id, _ = _run_with_web_target(isolated_db_engine)
    scanner_module._candidates[run_id] = [
        {
            "candidate_id": 8,
            "confidence": 0.91,
            "validation_status": "pending",
            "reportable": False,
        }
    ]
    try:
        saved_count = scanner_module._checkpoint_stopped_validation(
            run_id, "validation"
        )
    finally:
        scanner_module._candidates.pop(run_id, None)

    with Session(isolated_db_engine) as session:
        run = session.get(SastRun, run_id)
        pause = session.exec(
            select(RunPause)
            .where(RunPause.run_kind == "sast")
            .where(RunPause.run_id == run_id)
        ).one()
        checkpoint = session.exec(
            select(PhaseCheckpoint)
            .where(PhaseCheckpoint.run_kind == "sast")
            .where(PhaseCheckpoint.run_id == run_id)
            .where(PhaseCheckpoint.phase == "state")
            .where(PhaseCheckpoint.idempotency_key == "candidates")
        ).one()

    saved_candidates = json.loads(checkpoint.data_json)["candidates"]
    assert saved_count == 1
    assert run.status == "paused"
    assert pause.resume_stage == "validation"
    assert saved_candidates[0]["validation_status"] == "pending"


def test_full_sast_task_executes_discovery_validation_closure_and_attack_path(
    tmp_path, monkeypatch, isolated_db_engine
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "app.py",
            "def item(request):\n    value = request.args['id']\n    return db.execute(value)\n",
        )
    with Session(isolated_db_engine) as session:
        config = LLMConfig(name="test", is_active=True, model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = SastRun(
            name="three-pass",
            status="scanning",
            source_archive_path=str(archive),
            source_filename="source.zip",
            llm_config_id=config.id,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    calls: list[str] = []

    async def fake_loop(_config, **kwargs):
        prompt = kwargs["system_message"]
        execute = kwargs["tool_executor"]
        if "independent adversarial validator" in prompt:
            calls.append("validation")
            await execute(
                "validate_candidate",
                {
                    "candidate_id": 0,
                    "verdict": "confirmed",
                    "confidence": 0.93,
                    "reasoning": "The query is not parameterized.",
                    "controls": [],
                    "counterevidence": [],
                    "proof_gaps": [],
                },
                1,
            )
        elif "attack-path analyst" in prompt:
            calls.append("attack_path")
            await execute(
                "record_attack_path",
                {
                    "candidate_id": 0,
                    "nodes": ["HTTP id", "item", "db.execute"],
                    "impact": "Database compromise",
                    "severity_reasoning": "Remote input reaches SQL",
                    "dynamic_test": "GET /item?id='",
                },
                1,
            )
        elif "semantic closure reviewer" in prompt:
            calls.append("discovery")
        else:
            calls.append("discovery")
            payload = json.loads(await execute("get_work_program", {}, 0))
            work_items = payload["work_items"]
            await execute(
                "read_file", {"path": "app.py", "start_line": 1, "end_line": 3}, 1
            )
            if "assigned focus is injection" in prompt:
                await execute(
                    "write_lead",
                    {
                        "work_item_id": work_items[0]["work_item_id"],
                        "title": "SQL injection in item",
                        "category": "A03",
                        "severity": "high",
                        "location": "app.py:3",
                        "description": "Request id reaches db.execute.",
                        "evidence": "db.execute(value)",
                        "suggested_endpoint": "GET /item?id=",
                        "source_trace": {"file": "app.py", "line": 2},
                        "controls": [],
                        "sink_trace": {"file": "app.py", "line": 3},
                        "proof_gaps": [],
                        "confidence": 0.88,
                        "confidence_reasoning": "Concrete path",
                    },
                    1,
                )
                await execute(
                    "filter_lead",
                    {"lead_id": 0, "confidence": 0.88, "reasoning": "Concrete path"},
                    2,
                )
                work_items = work_items[1:]
            for item in work_items:
                await execute(
                    "record_disposition",
                    {
                        "work_item_id": item["work_item_id"],
                        "status": "no_match",
                        "reasoning": "No issue in this assigned class.",
                    },
                    3,
                )
        return f"{calls[-1]} complete"

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)

    with events_svc.run_kind_scope("sast"):
        asyncio.run(sast_scanner._sast_scan_task(run_id))

    # Four discovery workers plus the semantic closure worker.
    assert calls.count("discovery") == 5
    assert calls.count("validation") == 1
    assert calls[-1] == "attack_path"
    with Session(isolated_db_engine) as session:
        saved_run = session.get(SastRun, run_id)
        saved_lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        ).one()
        agent_rows = session.exec(
            select(AgentLog)
            .where(AgentLog.test_run_id == run_id)
            .where(AgentLog.run_kind == "sast")
        ).all()
    phases = json.loads(saved_run.phase_state_json)
    assert all(phases[key]["status"] == "complete" for key in sast_scanner._PHASES)
    assert saved_run.status == "completed"
    assert saved_run.leads_count == 1
    assert saved_lead.validation_status == "confirmed"
    assert saved_lead.reportable is True
    assert json.loads(saved_lead.attack_path_json)["nodes"][-1] == "db.execute"
    assert json.loads(saved_run.coverage_json)["summary"]["files_reviewed"] == 1
    status_by_agent = {
        row.agent_id: row.status
        for row in agent_rows
        if row.agent_id
        in {
            "sast-repository-modeller",
            "sast-threat-modeller",
            "sast-closure-analyst",
            "sast-attack-path",
        }
    }
    assert status_by_agent == {
        "sast-repository-modeller": "complete",
        "sast-threat-modeller": "complete",
        "sast-closure-analyst": "complete",
        "sast-attack-path": "complete",
    }


def test_sast_validation_starts_after_discovery_reconciliation(
    tmp_path, monkeypatch, isolated_db_engine
):
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "app.py",
            "def item(request):\n    value = request.args['id']\n    return db.execute(value)\n",
        )
    with Session(isolated_db_engine) as session:
        config = LLMConfig(name="test", is_active=True, model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = SastRun(
            name="overlapping-validation",
            status="scanning",
            source_archive_path=str(archive),
            source_filename="source.zip",
            llm_config_id=config.id,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    calls: list[str] = []
    validator_started: list[int] = []
    discovery_observed_validator: list[bool] = []
    visible_candidates_at_validation: list[int] = []
    reconciliation_finished = False
    reconciled_candidate_syncs: list[int] = []

    original_sync_candidates_to_db = sast_scanner._sync_candidates_to_db
    original_reconcile_candidate_ledger = sast_scanner._reconcile_candidate_ledger

    def track_candidate_sync(*args, **kwargs):
        result = original_sync_candidates_to_db(*args, **kwargs)
        if reconciliation_finished:
            reconciled_candidate_syncs.append(result[0])
        return result

    def track_reconciliation(*args, **kwargs):
        nonlocal reconciliation_finished
        result = original_reconcile_candidate_ledger(*args, **kwargs)
        reconciliation_finished = True
        return result

    monkeypatch.setattr(sast_scanner, "_sync_candidates_to_db", track_candidate_sync)
    monkeypatch.setattr(
        sast_scanner, "_reconcile_candidate_ledger", track_reconciliation
    )

    async def fake_loop(_config, **kwargs):
        prompt = kwargs["system_message"]
        execute = kwargs["tool_executor"]
        if "independent adversarial validator" in prompt:
            assert reconciled_candidate_syncs
            assigned = json.loads(
                kwargs["initial_user_message"].split("Assigned candidate:\n", 1)[1]
            )
            candidate_id = assigned["candidate_id"]
            with Session(isolated_db_engine) as session:
                visible_candidates_at_validation.append(
                    len(
                        session.exec(
                            select(ScanLead).where(ScanLead.producer_run_id == run_id)
                        ).all()
                    )
                )
            calls.append("validation")
            validator_started.append(candidate_id)
            await asyncio.sleep(0)
            await execute(
                "validate_candidate",
                {
                    "candidate_id": candidate_id,
                    "verdict": "confirmed",
                    "confidence": 0.93,
                    "reasoning": "The query is not parameterized.",
                    "controls": [],
                    "counterevidence": [],
                    "proof_gaps": [],
                },
                1,
            )
        elif "attack-path analyst" in prompt:
            calls.append("attack_path")
            for candidate_id in (0, 1, 2):
                await execute(
                    "record_attack_path",
                    {
                        "candidate_id": candidate_id,
                        "nodes": ["HTTP id", "item", "db.execute"],
                        "impact": "Database compromise",
                        "severity_reasoning": "Remote input reaches SQL",
                        "dynamic_test": "GET /item?id='",
                    },
                    1,
                )
        elif "semantic closure reviewer" in prompt:
            calls.append("discovery")
        else:
            calls.append("discovery")
            payload = json.loads(await execute("get_work_program", {}, 0))
            work_items = payload["work_items"]
            await execute(
                "read_file", {"path": "app.py", "start_line": 1, "end_line": 3}, 1
            )
            if "assigned focus is injection" not in prompt:
                for item in work_items:
                    await execute(
                        "record_disposition",
                        {
                            "work_item_id": item["work_item_id"],
                            "status": "no_match",
                            "reasoning": "No issue in this assigned class.",
                        },
                        1,
                    )
                return "phase complete"
            for candidate_id in (0, 1):
                await execute(
                    "write_lead",
                    {
                        "work_item_id": work_items[0]["work_item_id"],
                        "title": f"SQL injection in item {candidate_id}",
                        "category": "A03",
                        "severity": "high",
                        "location": f"app.py:{candidate_id + 2}",
                        "description": "Request id reaches db.execute.",
                        "evidence": "db.execute(value)",
                        "suggested_endpoint": "GET /item?id=",
                        "root_causes": (
                            ["Unsafe query construction", "Missing input validation"]
                            if candidate_id == 0
                            else []
                        ),
                        "confidence": 0.88,
                        "confidence_reasoning": "Concrete path",
                    },
                    1,
                )
                await execute(
                    "filter_lead",
                    {
                        "lead_id": candidate_id,
                        "confidence": 0.88,
                        "reasoning": "Concrete path",
                    },
                    2,
                )
                if candidate_id == 0:
                    await asyncio.sleep(0)
                    discovery_observed_validator.append(bool(validator_started))
        return "phase complete"

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)

    asyncio.run(sast_scanner._sast_scan_task(run_id))

    assert discovery_observed_validator == [False]
    assert sorted(validator_started) == [0, 1, 2]
    assert reconciled_candidate_syncs[0] == 3
    assert visible_candidates_at_validation == [3, 3, 3]
    assert calls[0] == "discovery"
    assert calls.count("validation") == 3
    assert calls[-1] == "attack_path"
    with Session(isolated_db_engine) as session:
        saved_run = session.get(SastRun, run_id)
        saved_leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .order_by(ScanLead.id)
        ).all()
    assert saved_run.status == "completed"
    assert saved_run.leads_count == 3
    assert json.loads(saved_run.report_json)["candidates"] == 3
    assert [lead.validation_status for lead in saved_leads] == [
        "confirmed",
        "confirmed",
        "confirmed",
    ]


def test_grep_scope_does_not_count_as_direct_file_review(tmp_path, isolated_db_engine):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "route.py").write_text(
        "@app.get('/items')\ndef items(request):\n    return db.execute(request.args['q'])\n"
    )
    (source_root / "other.py").write_text("def helper():\n    return 1\n")
    with Session(isolated_db_engine) as session:
        run = SastRun(name="receipt-test", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    coverage = sast_scanner._build_source_inventory(source_root)
    from aespa.services import sast_workprogram

    sast_workprogram.build_source_atlas(run_id, source_root)
    result = sast_scanner._run_read_tool(
        run_id,
        source_root,
        coverage,
        "discovery",
        "grep",
        {"pattern": "db\\.execute", "path": ""},
    )

    assert "route.py" in result
    assert not any(item["reviewed"] for item in coverage.values())
    summary = sast_workprogram.work_program_summary(run_id)
    assert summary["files"]["directly_opened"] == 0
    assert summary["files"]["with_search_matches"] == 1
    assert summary["evidence"]["search_calls"] == 1
    worker = sast_workprogram.worker_rows(run_id)[0]
    work_item_id = sast_workprogram.worker_payload(worker.id)["work_items"][0][
        "work_item_id"
    ]
    ok, message = sast_workprogram.record_disposition(
        work_item_id, status="no_match", reasoning="No matching flow."
    )
    assert ok is False
    assert "read_file" in message

    sast_scanner._run_read_tool(
        run_id,
        source_root,
        coverage,
        "discovery",
        "read_file",
        {"path": "route.py", "start_line": 1, "end_line": 3},
        worker.id,
    )
    ok, _ = sast_workprogram.record_disposition(
        work_item_id, status="no_match", reasoning="No matching flow."
    )
    assert ok is True


def test_discovery_worker_budget_scales_with_assigned_work():
    from aespa.services.sast_workprogram import discovery_worker_budget

    payload = {
        "class_group": "access",
        "files": ["app/routes.py"],
        "work_items": [
            {"surface": {"path": f"app/model_{index}.py"}} for index in range(20)
        ],
    }

    budget, basis = discovery_worker_budget(
        payload,
        security_check_count=12,
        budget_mode="adaptive",
        minimum=60,
        maximum=250,
    )

    assert budget == 168
    assert basis["work_items"] == 20
    assert basis["security_checks"] == 12
    assert basis["unique_files"] == 21


def test_discovery_worker_budget_keeps_fixed_mode_exact():
    from aespa.services.sast_workprogram import discovery_worker_budget

    budget, basis = discovery_worker_budget(
        {"class_group": "sink", "work_items": [{}] * 40},
        security_check_count=30,
        budget_mode="fixed",
        minimum=60,
        maximum=250,
    )

    assert budget == 60
    assert basis["calculated"] == 60
