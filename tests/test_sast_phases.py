from __future__ import annotations

import asyncio
import json
import zipfile

from sqlmodel import Session, select

from aespa.models import LLMConfig, LLMProfile, SastRun, ScanLead, Site
from aespa.models import TestRun as WebTestRun
from aespa.services import sast_scanner
from aespa.services.scan_leads import create_lead


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


def test_analysis_endpoint_returns_persisted_semantic_state(
    client, isolated_db_engine
):
    sast_run_id, _ = _run_with_web_target(isolated_db_engine)

    response = client.get(f"/api/sast-runs/{sast_run_id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["phases"]["scope"]["status"] == "complete"
    assert body["coverage"]["summary"] == {
        "files_total": 2,
        "files_reviewed": 1,
    }


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


def test_sast_model_profile_can_be_changed_after_creation(
    client, isolated_db_engine
):
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


def test_sast_model_profile_cannot_change_while_scanning(
    client, isolated_db_engine
):
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
    executor = sast_scanner._make_review_executor(
        41, root, coverage, "validation"
    )
    result = asyncio.run(
        executor(
            "validate_candidate",
            {
                "candidate_id": 0,
                "verdict": "confirmed",
                "confidence": 0.91,
                "reasoning": "No parameterization is present.",
                "controls": [],
                "counterevidence": [],
                "proof_gaps": [],
            },
            1,
        )
    )
    assert "confirmed" in result
    assert sast_scanner._candidates[41][0]["reportable"] is True

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


def test_file_inventory_records_actual_read_receipts(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "app.py").write_text("print('hello')\n")
    (root / "notes.txt").write_text("documentation\n")
    coverage = sast_scanner._build_source_inventory(root)

    result = sast_scanner._run_read_tool(
        52, root, coverage, "discovery", "read_file", {"path": "app.py"}
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
    asyncio.run(
        executor(
            "write_lead",
            {
                "title": "SQL injection",
                "category": "A03",
                "severity": "high",
                "location": "app.py:1",
                "description": "Request input reaches SQL execution.",
                "evidence": "db.execute(request.args['id'])",
            },
            1,
        )
    )

    with Session(isolated_db_engine) as session:
        lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        ).one()
        assert lead.validation_status == "pending"
        assert lead.confidence == 0.0

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


def test_full_sast_task_executes_three_real_phase_loops(
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
        else:
            calls.append("discovery")
            await execute(
                "read_file", {"path": "app.py", "start_line": 1, "end_line": 3}, 1
            )
            await execute(
                "write_lead",
                {
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
                },
                1,
            )
            await execute(
                "filter_lead",
                {"lead_id": 0, "confidence": 0.88, "reasoning": "Concrete path"},
                2,
            )
        return f"{calls[-1]} complete"

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    monkeypatch.setattr(llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm, "clear_run_context", lambda: None)

    asyncio.run(sast_scanner._sast_scan_task(run_id))

    assert calls == ["discovery", "validation", "attack_path"]
    with Session(isolated_db_engine) as session:
        saved_run = session.get(SastRun, run_id)
        saved_lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        ).one()
    phases = json.loads(saved_run.phase_state_json)
    assert all(phases[key]["status"] == "complete" for key in sast_scanner._PHASES)
    assert saved_run.status == "completed"
    assert saved_run.leads_count == 1
    assert saved_lead.validation_status == "confirmed"
    assert saved_lead.reportable is True
    assert json.loads(saved_lead.attack_path_json)["nodes"][-1] == "db.execute"
    assert json.loads(saved_run.coverage_json)["summary"]["files_reviewed"] == 1


def test_sast_validation_starts_before_discovery_finishes(
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

    async def fake_loop(_config, **kwargs):
        prompt = kwargs["system_message"]
        execute = kwargs["tool_executor"]
        if "independent adversarial validator" in prompt:
            candidate_id = 0 if "candidate #0" in kwargs["initial_user_message"] else 1
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
            for candidate_id in (0, 1):
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
        else:
            calls.append("discovery")
            for candidate_id in (0, 1):
                await execute(
                    "write_lead",
                    {
                        "title": f"SQL injection in item {candidate_id}",
                        "category": "A03",
                        "severity": "high",
                        "location": f"app.py:{candidate_id + 2}",
                        "description": "Request id reaches db.execute.",
                        "evidence": "db.execute(value)",
                        "suggested_endpoint": "GET /item?id=",
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

    assert discovery_observed_validator == [True]
    assert sorted(validator_started) == [0, 1]
    assert calls[0] == "discovery"
    assert calls.count("validation") == 2
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
    assert saved_run.leads_count == 2
    assert [lead.validation_status for lead in saved_leads] == [
        "confirmed",
        "confirmed",
    ]
