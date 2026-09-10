from __future__ import annotations

from sqlmodel import Session, select

from aespa.models import (
    SastCoverageObligation,
    SastDiscoveryTelemetry,
    SastEvidenceReceipt,
    SastObligationLead,
    SastPartition,
    SastRun,
    SastSourceFile,
    SastSurfaceEdge,
    SastSurfaceItem,
    SastThreatModel,
    SastThreatScenario,
    SastWorker,
    SastWorkItem,
    ScanLead,
)
from aespa.services import run_cleanup, sast_workprogram
from aespa.services.sast_semantic import (
    build_repository_model,
    build_threat_model,
    closure_assurance,
    deterministic_dependency_analysis,
    finalize_agent_threat_model,
    persist_semantic_state,
    plan_semantic_obligations,
    reconcile_candidates,
    record_agent_model_fact,
    record_agent_threat_scenario,
    record_obligation_disposition,
)


def _seed_relational_semantic_state(engine) -> tuple[int, int]:
    with Session(engine) as session:
        run = SastRun(name="semantic cleanup", status="paused")
        session.add(run)
        session.flush()
        source = SastSourceFile(sast_run_id=run.id, path="app.py", language="Python")
        session.add(source)
        session.flush()
        first = SastSurfaceItem(
            sast_run_id=run.id,
            source_file_id=source.id,
            kind="entrypoint",
            fingerprint="entry",
        )
        second = SastSurfaceItem(
            sast_run_id=run.id,
            source_file_id=source.id,
            kind="sink",
            fingerprint="sink",
        )
        partition = SastPartition(
            sast_run_id=run.id, partition_key="app", name="app"
        )
        session.add(first)
        session.add(second)
        session.add(partition)
        session.flush()
        worker = SastWorker(
            sast_run_id=run.id,
            partition_id=partition.id,
            worker_key="app:injection",
            class_group="injection",
        )
        scenario = SastThreatScenario(sast_run_id=run.id, scenario_key="scenario")
        session.add(worker)
        session.add(scenario)
        session.flush()
        obligation = SastCoverageObligation(
            sast_run_id=run.id,
            obligation_key="obligation",
            obligation_type="threat_scenario",
            source_scenario_id=scenario.id,
            assigned_worker_id=worker.id,
        )
        lead = ScanLead(
            producer_run_id=run.id,
            producer_run_type="sast",
            source="sast",
            title="Candidate",
            description="Candidate description",
            confidence=0.8,
        )
        session.add(obligation)
        session.add(lead)
        session.add(
            SastWorkItem(
                sast_run_id=run.id,
                partition_id=partition.id,
                surface_item_id=first.id,
                worker_id=worker.id,
                work_key="work",
                class_group="injection",
            )
        )
        session.add(
            SastEvidenceReceipt(
                sast_run_id=run.id,
                worker_id=worker.id,
                tool_name="read_file",
            )
        )
        session.add(
            SastSurfaceEdge(
                sast_run_id=run.id,
                source_surface_id=first.id,
                target_surface_id=second.id,
                edge_kind="flow",
                fingerprint="edge",
            )
        )
        session.add(SastThreatModel(sast_run_id=run.id))
        session.add(SastDiscoveryTelemetry(sast_run_id=run.id, phase="discovery"))
        session.flush()
        session.add(
            SastObligationLead(
                sast_run_id=run.id,
                obligation_id=obligation.id,
                lead_id=lead.id,
            )
        )
        session.commit()
        return run.id, lead.id


def test_reset_work_program_clears_semantic_rows_in_foreign_key_order(fk_engine):
    run_id, lead_id = _seed_relational_semantic_state(fk_engine)

    sast_workprogram.reset_work_program(run_id)

    with Session(fk_engine) as session:
        assert session.get(SastRun, run_id) is not None
        assert session.get(ScanLead, lead_id) is not None
        assert not session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == run_id)
        ).first()
        assert not session.exec(
            select(SastCoverageObligation).where(
                SastCoverageObligation.sast_run_id == run_id
            )
        ).first()


def test_delete_sast_run_clears_semantic_rows_in_foreign_key_order(fk_engine):
    run_id, lead_id = _seed_relational_semantic_state(fk_engine)

    with Session(fk_engine) as session:
        run_cleanup.cascade_delete_sast_run(session, run_id)
        session.commit()

    with Session(fk_engine) as session:
        assert session.get(SastRun, run_id) is None
        assert session.get(ScanLead, lead_id) is None


def test_repository_model_and_threat_plan_are_source_backed(tmp_path):
    (tmp_path / "app.py").write_text(
        "@app.get('/orders')\n"
        "def orders(request):\n"
        "    return db.query(request.args['id'])\n"
    )
    model = build_repository_model(tmp_path)
    assert model["stats"]["operations"] >= 1
    threat_model = build_threat_model(model)
    planning = plan_semantic_obligations(model, threat_model)
    assert threat_model["scenarios"]
    assert planning["obligations"]
    assert planning["obligations"][0]["status"] == "pending"


def test_php_sql_repository_maps_stores_and_assets(tmp_path):
    (tmp_path / "Database.php").write_text(
        "<?php\n$db = new PDO('mysql:host=db;dbname=bank', $user, $pass);\n"
    )
    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE users (id INT, password_hash TEXT);\n"
        "CREATE TABLE accounts (id INT, balance DECIMAL(10,2));\n"
        "CREATE TABLE transactions (id INT, amount DECIMAL(10,2));\n"
    )

    model = build_repository_model(tmp_path)
    threat_model = build_threat_model(model)

    assert model["stats"]["stores"] >= 1
    assert model["stats"]["assets"] >= 3
    assert {asset["name"] for asset in threat_model["assets"]} >= {
        "users data",
        "accounts data",
        "transactions data",
    }
    assert threat_model["stores"]


def test_agent_facts_require_directly_opened_valid_evidence(tmp_path):
    source = tmp_path / "accounts.php"
    source.write_text("<?php\nfunction balance() { return 10; }\n")
    model = build_repository_model(tmp_path, facts=[])
    proposal = {
        "kind": "asset",
        "name": "Account balances",
        "description": "Customer account balances must retain integrity.",
        "evidence": ["accounts.php:2"],
    }

    ok, message, node_id = record_agent_model_fact(
        tmp_path, model, proposal, set()
    )
    assert not ok
    assert "opened" in message
    assert node_id is None

    ok, _message, node_id = record_agent_model_fact(
        tmp_path, model, proposal, {"accounts.php"}
    )
    assert ok
    assert node_id
    assert any(node["id"] == node_id for node in model["nodes"])


def test_hybrid_threat_model_links_assets_and_reports_quality(tmp_path):
    (tmp_path / "schema.sql").write_text("CREATE TABLE accounts (balance INT);\n")
    model = build_repository_model(tmp_path)
    threat_model = build_threat_model(model)
    asset_id = next(node["id"] for node in model["nodes"] if node["kind"] == "asset")
    ok, message = record_agent_threat_scenario(
        model,
        threat_model,
        {
            "title": "Unauthorized balance change",
            "actor": "authenticated customer",
            "asset_surface_ids": [asset_id],
            "security_objective": "preserve account balance integrity",
            "capability_gain": "change another account balance",
            "impact": "financial loss",
            "priority": "high",
        },
    )
    assert ok, message

    ok, message = finalize_agent_threat_model(
        model,
        threat_model,
        {
            "summary": "Banking data and account operations require authorization.",
            "security_objectives": ["Protect account balances"],
            "open_questions": [],
        },
        files_reviewed=1,
    )
    assert ok, message
    assert threat_model["finalized"] is True
    assert threat_model["assets"]
    assert threat_model["stores"]
    assert threat_model["quality"]["status"] in {"full", "partial"}


def test_persist_semantic_state_coalesces_duplicate_keys(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        run = SastRun(name="duplicate semantic keys")
        session.add(run)
        session.commit()
        run_id = int(run.id)

    scenario_key = "same-scenario"
    obligation_key = "same-obligation"
    result = persist_semantic_state(
        run_id,
        {"nodes": [], "edges": []},
        {
            "scenarios": [
                {"scenario_key": scenario_key, "title": "First title"},
                {"scenario_key": scenario_key, "title": "Updated title"},
            ]
        },
        {
            "obligations": [
                {
                    "obligation_key": obligation_key,
                    "obligation_type": "threat_scenario",
                    "source_scenario_key": scenario_key,
                    "title": "First question",
                },
                {
                    "obligation_key": obligation_key,
                    "obligation_type": "threat_scenario",
                    "source_scenario_key": scenario_key,
                    "title": "Updated question",
                },
            ]
        },
    )

    with Session(isolated_db_engine) as session:
        scenarios = list(
            session.exec(
                select(SastThreatScenario).where(
                    SastThreatScenario.sast_run_id == run_id
                )
            )
        )
        obligations = list(
            session.exec(
                select(SastCoverageObligation).where(
                    SastCoverageObligation.sast_run_id == run_id
                )
            )
        )

    assert result["scenarios"] == 1
    assert result["obligations"] == 1
    assert scenarios[0].title == "Updated title"
    assert len(scenarios) == 1
    assert obligations[0].title == "Updated question"
    assert len(obligations) == 1


def test_reconciliation_retains_locations_and_provenance():
    candidates = [
        {
            "candidate_id": 3,
            "category": "A03",
            "title": "Query injection",
            "location": "app.py:10",
            "description": "request input reaches db query",
            "source_trace": {"path": "app.py"},
            "sink_trace": {"path": "app.py"},
            "evidence": "first evidence",
        },
        {
            "candidate_id": 8,
            "category": "A03",
            "title": "Unsafe query",
            "location": "app.py:11",
            "description": "request input reaches db query",
            "source_trace": {"path": "app.py"},
            "sink_trace": {"path": "app.py"},
            "evidence": "second evidence",
        },
    ]
    merged, stats = reconcile_candidates(candidates)
    assert stats == {"input": 2, "unique": 1, "merged": 1}
    assert merged[0]["locations"] == ["app.py:10", "app.py:11"]


def test_closure_does_not_call_file_reads_coverage():
    result = closure_assurance(
        {"warnings": []},
        {"scenarios": []},
        {"obligations": []},
        [],
    )
    assert result["status"] == "full"
    assert result["coverage_basis"] == "semantic_obligations_and_threat_scenarios"


def test_semantic_obligation_requires_an_evidence_backed_disposition():
    planning = {
        "obligations": [
            {"obligation_key": "authz-1", "status": "pending", "evidence": []}
        ]
    }
    ok, _ = record_obligation_disposition(
        planning,
        "authz-1",
        status="assessed_safe",
        reasoning="Ownership is checked before the record is returned.",
        evidence=["services/orders.py:41"],
        controls=["require_owner"],
    )
    assert ok is True
    assert planning["obligations"][0]["status"] == "assessed_safe"
    assert planning["obligations"][0]["evidence"] == ["services/orders.py:41"]

    closure = closure_assurance({"warnings": []}, {"scenarios": []}, planning, [])
    assert closure["status"] == "full"


def test_dependency_analysis_matches_only_resolved_affected_versions(tmp_path):
    (tmp_path / "requirements.txt").write_text("example-lib==1.2.3\n", encoding="utf-8")
    model = build_repository_model(tmp_path)
    analysis = deterministic_dependency_analysis(
        model,
        {
            "updated_at": "2026-09-10T00:00:00Z",
            "advisories": [
                {
                    "id": "ADV-1",
                    "package": "example-lib",
                    "affected": "<1.3.0",
                    "severity": "high",
                },
                {
                    "id": "ADV-2",
                    "package": "example-lib",
                    "affected": ">=2.0.0",
                    "severity": "high",
                },
            ],
        },
    )
    assert [match["advisory_id"] for match in analysis["matches"]] == ["ADV-1"]
