from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

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
    candidate_evidence,
    candidate_reconciliation_key,
    closure_assurance,
    deterministic_dependency_analysis,
    finalize_agent_threat_model,
    find_existing_candidate,
    persist_semantic_state,
    plan_semantic_obligations,
    reconcile_ambiguous_candidates,
    reconcile_candidate_ledger,
    reconcile_candidates,
    reconcile_validated_candidates,
    record_agent_model_fact,
    record_agent_threat_scenario,
    record_obligation_disposition,
)


def test_discovery_registry_joins_shared_issue_and_keeps_separate_cause():
    from aespa.services.sast_semantic import absorb_candidate_observation

    first = {
        "candidate_id": 1,
        "category": "A03",
        "title": "SQL injection in customer search",
        "location": "app.py:10",
        "suggested_endpoint": "GET /customers?sort=",
        "source_trace": {"file": "app.py", "symbol": "search"},
        "sink_trace": {"file": "app.py", "symbol": "execute"},
        "evidence": "first trace",
        "confidence": 0.8,
        "provenance": [1],
        "source_work_item_ids": [11],
        "locations": ["app.py:10"],
    }
    second = {
        **first,
        "candidate_id": 2,
        "title": "Unsafe SQL query in customer search",
        "location": "app.py:12",
        "evidence": "second trace",
        "confidence": 0.9,
        "provenance": [2],
        "source_work_item_ids": [12],
        "locations": ["app.py:12"],
    }
    assert find_existing_candidate([first], second) is first
    absorb_candidate_observation(first, second)
    assert first["source_work_item_ids"] == [11, 12]
    assert first["provenance"] == [1, 2]
    assert first["locations"] == ["app.py:10", "app.py:12"]
    assert first["confidence"] == 0.9
    assert "second trace" in first["evidence"]

    distinct = {**second, "root_causes": ["Missing authorization check"]}
    assert find_existing_candidate([first], distinct) is None
    other_input = {
        **second,
        "suggested_endpoint": "GET /customers?filter=",
        "source_trace": {"file": "app.py", "symbol": "search", "input": "filter"},
        "sink_trace": {"file": "app.py", "symbol": "execute_other"},
    }
    assert find_existing_candidate([first], other_input) is None


def test_final_reconciliation_keeps_both_validator_results():
    candidates = [
        {
            "candidate_id": 1,
            "category": "A03",
            "title": "SQL injection in customer search",
            "location": "app.py:10",
            "source_trace": {"file": "app.py", "symbol": "search"},
            "sink_trace": {"file": "app.py", "symbol": "execute"},
            "evidence": "first trace",
            "validation_status": "confirmed",
            "validation_reasoning": "First validator confirmed the flow.",
            "reportable": True,
        },
        {
            "candidate_id": 2,
            "category": "A03",
            "title": "Unsafe SQL query in customer search",
            "location": "app.py:12",
            "source_trace": {"file": "app.py", "symbol": "search"},
            "sink_trace": {"file": "app.py", "symbol": "execute"},
            "evidence": "second trace",
            "validation_status": "confirmed",
            "validation_reasoning": "Second validator confirmed the flow.",
            "reportable": True,
        },
    ]
    assert reconcile_validated_candidates(candidates) == 1
    assert reconcile_validated_candidates(candidates) == 0
    assert candidates[0]["reportable"] is True
    assert "Second validator" in candidates[0]["validation_reasoning"]
    assert candidates[1]["reconciled_into_candidate_id"] == 1
    assert candidates[1]["reportable"] is False


def test_final_reconciliation_respects_distinct_validator_causes():
    common = {
        "category": "A03",
        "title": "SQL injection in customer search",
        "location": "app.py:10",
        "source_trace": {"file": "app.py", "symbol": "search"},
        "sink_trace": {"file": "app.py", "symbol": "execute"},
        "validation_status": "confirmed",
        "reportable": True,
    }
    candidates = [
        {**common, "candidate_id": 1, "validated_root_cause": "Unsafe sort column"},
        {**common, "candidate_id": 2, "validated_root_cause": "Unsafe filter value"},
    ]
    assert reconcile_validated_candidates(candidates) == 0
    assert all(candidate["reportable"] for candidate in candidates)

    candidates[1]["validated_root_cause"] = candidates[0]["validated_root_cause"]
    candidates[0]["fix_location"] = "app.py:10"
    candidates[1]["fix_location"] = "app.py:25"
    assert reconcile_validated_candidates(candidates) == 0


def test_final_reconciliation_uses_matching_validator_anchors():
    common = {
        "category": "A03",
        "location": "app.py:10",
        "suggested_endpoint": "GET /customers",
        "source_trace": {"file": "app.py", "symbol": "search"},
        "sink_trace": {"file": "db.py", "line": 42, "symbol": "execute"},
        "validation_status": "confirmed",
        "reportable": True,
        "validated_root_cause": "Unescaped sort identifier",
        "fix_location": "db.py:38",
    }
    candidates = [
        {**common, "candidate_id": 1, "title": "SQL injection in customer search"},
        {**common, "candidate_id": 2, "title": "Unsafe dynamic query order"},
    ]
    assert reconcile_validated_candidates(candidates) == 1
    assert candidates[1]["reconciled_into_candidate_id"] == 1
    assert "Unescaped sort identifier" in candidate_evidence(candidates[0])


def test_semantic_prevalidation_merges_only_supported_shared_fixes():
    candidates = [
        {
            "candidate_id": index,
            "category": "A03",
            "title": title,
            "location": f"routes_{index}.py:5",
            "source_trace": {"file": f"routes_{index}.py", "line": 5},
            "sink_trace": {"file": "helpers/query.py", "line": 10},
            "validation_status": "pending",
            "evidence": f"trace {index}",
        }
        for index, title in enumerate(
            ["SQL injection in customer lookup", "Unsafe SQL in account lookup"], 1
        )
    ]

    class FakeLLM:
        calls = 0

        async def plain_completion(self, _config, prompt, *, system_prompt):
            self.calls += 1
            assert len(json.loads(prompt)["pairs"]) == 1
            assert len(json.loads(prompt)["candidates"]) == 2
            assert "one specific code fix" in system_prompt
            return json.dumps(
                {
                    "decisions": [
                        {
                            "first_id": 1,
                            "second_id": 2,
                            "same_fix": True,
                            "fix_location": "helpers/query.py:10",
                            "reason": "Both routes call the same unsafe query builder.",
                        }
                    ]
                }
            )

    llm = FakeLLM()
    result = asyncio.run(reconcile_ambiguous_candidates(candidates, llm, object()))
    assert result["merged"] == 1
    assert llm.calls == 1
    assert candidates[1]["reconciled_into_candidate_id"] == 1
    assert "same unsafe query builder" in candidate_evidence(candidates[0])

    candidates[1].pop("reconciled_duplicate")
    candidates[1].pop("reconciled_into_candidate_id")
    candidates[1]["validation_status"] = "pending"
    candidates[0]["merge_decisions"] = []
    candidates[0]["merged_candidate_ids"] = []

    async def unsupported_fix(*_args, **_kwargs):
        return json.dumps(
            {
                "decisions": [
                    {
                        "first_id": 1,
                        "second_id": 2,
                        "same_fix": True,
                        "fix_location": "unrelated.py:4",
                        "reason": "The model guessed an unrelated fix location.",
                    }
                ]
            }
        )

    result = asyncio.run(
        reconcile_ambiguous_candidates(
            candidates, SimpleNamespace(plain_completion=unsupported_fix), object()
        )
    )
    assert result["merged"] == 0

    async def unavailable(*_args, **_kwargs):
        raise TimeoutError("dedup model unavailable")

    result = asyncio.run(
        reconcile_ambiguous_candidates(
            candidates, SimpleNamespace(plain_completion=unavailable), object()
        )
    )
    assert result["status"] == "model_unavailable"
    assert result["merged"] == 0
    assert candidates[1]["validation_status"] == "pending"


def test_semantic_prevalidation_can_review_a_shared_missing_control(tmp_path):
    middleware = tmp_path / "auth/middleware.py"
    middleware.parent.mkdir()
    middleware.write_text("# shared guard\n" * 20)
    candidates = [
        {
            "candidate_id": index,
            "category": "A07",
            "title": f"Missing rate limit on route {index}",
            "location": f"routes_{index}.py:5",
            "source_trace": {"file": "auth/middleware.py", "symbol": "login_guard"},
            "sink_trace": {},
            "root_causes": ["No attempt limit in shared login guard"],
            "validation_status": "pending",
        }
        for index in (1, 2)
    ]

    async def shared_fix(*_args, **_kwargs):
        return json.dumps(
            {
                "decisions": [
                    {
                        "first_id": 1,
                        "second_id": 2,
                        "same_fix": True,
                        "fix_location": "auth/middleware.py:20",
                        "reason": "Both routes use the same guard without an attempt limit.",
                    }
                ]
            }
        )

    result = asyncio.run(
        reconcile_ambiguous_candidates(
            candidates,
            SimpleNamespace(plain_completion=shared_fix),
            object(),
            root=tmp_path,
        )
    )
    assert result["merged"] == 1


def test_new_evidence_is_not_absorbed_by_a_dismissed_lead():
    previous = {
        "candidate_id": 1,
        "category": "A03",
        "title": "SQL injection in customer search",
        "location": "app.py:10",
        "source_trace": {"file": "app.py", "symbol": "search"},
        "sink_trace": {"file": "app.py", "symbol": "execute"},
        "validation_status": "dismissed",
        "validation_reasoning": "Validator found parameter binding.",
        "reportable": False,
    }
    later = {
        **previous,
        "candidate_id": 2,
        "title": "Unsafe SQL query in customer search",
        "location": "app.py:12",
        "validation_status": "pending",
        "validation_reasoning": "",
    }
    assert find_existing_candidate([previous], later) is None
    assert reconcile_candidate_ledger([previous, later])["unique"] == 2
    assert later["validation_status"] == "pending"


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
        partition = SastPartition(sast_run_id=run.id, partition_key="app", name="app")
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

    ok, message, node_id = record_agent_model_fact(tmp_path, model, proposal, set())
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


def test_persist_semantic_state_coalesces_duplicate_edges(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        run = SastRun(name="duplicate semantic edges")
        session.add(run)
        session.commit()
        run_id = int(run.id)

    source_id = "source-node"
    target_id = "target-node"
    edge_id = "same-edge"
    result = persist_semantic_state(
        run_id,
        {
            "nodes": [
                {"id": source_id, "fingerprint": source_id, "kind": "input"},
                {"id": target_id, "fingerprint": target_id, "kind": "sink"},
            ],
            "edges": [
                {
                    "id": edge_id,
                    "source": source_id,
                    "target": target_id,
                    "kind": "related",
                },
                {
                    "id": edge_id,
                    "source": source_id,
                    "target": target_id,
                    "kind": "related",
                    "provenance": "llm_reconciliation",
                },
            ],
        },
        {"scenarios": []},
        {"obligations": []},
    )

    with Session(isolated_db_engine) as session:
        edges = list(
            session.exec(
                select(SastSurfaceEdge).where(SastSurfaceEdge.sast_run_id == run_id)
            )
        )

    assert result["edges"] == 1
    assert len(edges) == 1
    assert edges[0].fingerprint == edge_id


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


def test_candidate_ledger_merges_wording_and_line_variants_before_validation():
    candidates = [
        {
            "candidate_id": 3,
            "category": "A03",
            "title": "SQL injection in user search",
            "location": "app.py:10",
            "description": "Input reaches a raw query.",
            "suggested_endpoint": "GET /users",
            "source_trace": {"file": "app.py", "symbol": "search_users"},
            "sink_trace": {"file": "app.py", "symbol": "execute_search"},
            "evidence": "first trace",
            "confidence": 0.8,
            "validation_status": "pending",
            "provenance": [1],
        },
        {
            "candidate_id": 8,
            "category": "A03",
            "title": "Unsafe SQL query in search",
            "location": "app.py:13",
            "description": "The request changes SQL syntax.",
            "suggested_endpoint": "GET /users",
            "source_trace": {"file": "app.py", "symbol": "search_users"},
            "sink_trace": {"file": "app.py", "symbol": "execute_search"},
            "evidence": "second trace",
            "confidence": 0.9,
            "validation_status": "pending",
            "provenance": [2],
        },
    ]

    assert candidate_reconciliation_key(candidates[0]) == candidate_reconciliation_key(
        candidates[1]
    )
    stats = reconcile_candidate_ledger(candidates)
    assert stats == {"input": 2, "unique": 1, "merged": 1}
    assert candidates[0]["candidate_id"] == 3
    assert candidates[0]["locations"] == ["app.py:10", "app.py:13"]
    assert candidates[0]["provenance"] == [1, 2]
    assert candidates[0]["confidence"] == 0.9
    assert "second trace" in candidate_evidence(candidates[0])
    assert "app.py:13" in candidate_evidence(candidates[0])
    assert candidates[1]["reconciled_into_candidate_id"] == 3
    assert candidates[1]["validation_status"] == "dismissed"
    assert reconcile_candidate_ledger(candidates) == stats
    assert candidates[0]["evidence"] == "first trace\n\nsecond trace"


def test_candidate_ledger_merges_same_route_parameter_and_nearby_sink():
    base = {
        "category": "A03",
        "location": "src/Controllers/AdminUserController.php:22-33",
        "suggested_endpoint": "GET /api/admin/customers?search=",
        "validation_status": "pending",
    }
    candidates = [
        {
            **base,
            "candidate_id": 1,
            "title": "SQL injection in admin customer search",
            "source_trace": {
                "file": "src/Controllers/AdminUserController.php",
                "symbol": "$_GET['search']",
            },
            "sink_trace": {
                "file": "src/Controllers/AdminUserController.php",
                "line": 27,
                "symbol": "$db->query($countSql)",
            },
        },
        {
            **base,
            "candidate_id": 2,
            "title": "SQL injection in admin customer search endpoint",
            "source_trace": {
                "file": "src/AdminRouter.php",
                "symbol": "AdminUserController::index",
            },
            "sink_trace": {
                "file": "src/Controllers/AdminUserController.php",
                "line": 29,
                "symbol": "PDO::query",
            },
        },
    ]
    assert reconcile_candidate_ledger(candidates) == {
        "input": 2,
        "unique": 1,
        "merged": 1,
    }


def test_candidate_ledger_keeps_other_parameters_and_distant_sinks():
    base = {
        "category": "A03",
        "title": "SQL injection in customer search",
        "location": "src/Controllers/AdminUserController.php:20",
        "source_trace": {"file": "src/Controllers/AdminUserController.php"},
        "validation_status": "pending",
    }
    candidates = [
        {
            **base,
            "candidate_id": 1,
            "suggested_endpoint": "GET /api/admin/customers?search=",
            "sink_trace": {
                "file": "src/Controllers/AdminUserController.php",
                "line": 27,
                "symbol": "$db->query($searchSql)",
            },
        },
        {
            **base,
            "candidate_id": 2,
            "suggested_endpoint": "GET /api/admin/customers?sort=",
            "sink_trace": {
                "file": "src/Controllers/AdminUserController.php",
                "line": 29,
                "symbol": "$db->query($sortSql)",
            },
        },
        {
            **base,
            "candidate_id": 3,
            "suggested_endpoint": "GET /api/admin/customers?search=",
            "sink_trace": {
                "file": "src/Controllers/AdminUserController.php",
                "line": 50,
                "symbol": "$db->query($auditSql)",
            },
        },
    ]
    assert reconcile_candidate_ledger(candidates) == {
        "input": 3,
        "unique": 3,
        "merged": 0,
    }


def test_candidate_ledger_merges_same_operation_with_different_agent_labels():
    candidates = [
        {
            "candidate_id": 1,
            "category": "A10",
            "title": "SSRF in document import URL fetch",
            "location": "src/handlers/import.py:70",
            "suggested_endpoint": "POST /documents/import",
            "source_trace": {"file": "src/handlers/import.py"},
            "sink_trace": {
                "file": "src/handlers/import.py",
                "line": 70,
                "symbol": "fetch_url",
            },
        },
        {
            "candidate_id": 2,
            "category": "A10",
            "title": "SSRF via URL fetch in document import",
            "location": "src/handlers/import.py:74",
            "suggested_endpoint": "POST /documents/import",
            "source_trace": {"file": "src/handlers/import.py"},
            "sink_trace": {
                "file": "src/handlers/import.py",
                "line": 74,
                "symbol": "requests.get",
            },
        },
    ]
    assert reconcile_candidate_ledger(candidates)["unique"] == 1


def test_candidate_ledger_merges_same_output_sink_across_callers():
    candidates = [
        {
            "candidate_id": 1,
            "category": "A03",
            "title": "Stored XSS from unescaped comment body in document view",
            "location": "web/view.js:72",
            "suggested_endpoint": "POST /comments",
            "source_trace": {"file": "api/comments.py"},
            "sink_trace": {"file": "web/view.js", "line": 72, "symbol": "innerHTML"},
        },
        {
            "candidate_id": 2,
            "category": "A03",
            "title": "Stored XSS via unescaped comment body in document view",
            "location": "web/view.js:72",
            "suggested_endpoint": "GET /documents/{id}",
            "source_trace": {"file": "api/documents.py"},
            "sink_trace": {
                "file": "web/view.js",
                "line": 72,
                "symbol": "renderComments",
            },
        },
    ]
    assert reconcile_candidate_ledger(candidates)["unique"] == 1


def test_candidate_ledger_merges_shared_middleware_sink_across_routes():
    candidates = [
        {
            "candidate_id": 1,
            "category": "A07",
            "title": "Token signature validation bypass in shared decoder",
            "location": "src/auth/decode.py:48",
            "suggested_endpoint": "GET /accounts",
            "source_trace": {"file": "src/middleware/auth.py"},
            "sink_trace": {
                "file": "src/auth/decode.py",
                "line": 48,
                "symbol": "decode",
            },
        },
        {
            "candidate_id": 2,
            "category": "A07",
            "title": "Token signature not validated in shared decoder",
            "location": "src/auth/decode.py:52",
            "suggested_endpoint": "GET /profile",
            "source_trace": {"file": "src/middleware/auth.py"},
            "sink_trace": {
                "file": "src/auth/decode.py",
                "line": 52,
                "symbol": "parseClaims",
            },
        },
    ]
    assert reconcile_candidate_ledger(candidates)["unique"] == 1


def test_candidate_ledger_does_not_merge_different_methods_and_sinks():
    candidates = [
        {
            "candidate_id": 1,
            "category": "A03",
            "title": "SQL injection in customer query",
            "location": "api/customer.py:20",
            "suggested_endpoint": "GET /customers",
            "source_trace": {"file": "api/customer.py"},
            "sink_trace": {"file": "api/customer.py", "line": 20, "symbol": "search"},
        },
        {
            "candidate_id": 2,
            "category": "A03",
            "title": "SQL injection in customer query",
            "location": "api/customer.py:25",
            "suggested_endpoint": "POST /customers",
            "source_trace": {"file": "api/customer.py"},
            "sink_trace": {"file": "api/customer.py", "line": 25, "symbol": "create"},
        },
    ]
    assert reconcile_candidate_ledger(candidates)["unique"] == 2


def test_candidate_ledger_does_not_fold_combined_issues_into_one_cause():
    base = {
        "category": "A03",
        "location": "api/import.py:40",
        "suggested_endpoint": "POST /import",
        "source_trace": {"file": "api/import.py"},
        "sink_trace": {"file": "api/import.py", "line": 40},
    }
    candidates = [
        {**base, "candidate_id": 1, "title": "SQL injection in import handler"},
        {
            **base,
            "candidate_id": 2,
            "title": "SQL injection and path traversal in import handler",
        },
    ]
    assert reconcile_candidate_ledger(candidates)["unique"] == 2


def test_candidate_ledger_uses_route_and_affected_object_for_access_reports():
    base = {
        "suggested_endpoint": "GET /orders/{id}",
        "location": "api/orders.py:40",
        "source_trace": {"file": "api/orders.py"},
    }
    candidates = [
        {
            **base,
            "candidate_id": 1,
            "category": "A01",
            "title": "IDOR: order detail exposes another user's order",
            "sink_trace": {"file": "models/order.py", "line": 10},
        },
        {
            **base,
            "candidate_id": 2,
            "category": "API1",
            "title": "BOLA: order detail lacks ownership check",
            "sink_trace": {"file": "api/orders.py", "line": 42},
        },
        {
            **base,
            "candidate_id": 3,
            "category": "A01",
            "title": "IDOR: invoice attachment exposes another user's invoice",
            "sink_trace": {"file": "models/invoice.py", "line": 12},
        },
    ]
    stats = reconcile_candidate_ledger(candidates)
    assert stats == {"input": 3, "unique": 2, "merged": 1}
    assert candidates[1]["reconciled_into_candidate_id"] == 1
    assert candidates[2].get("reconciled_duplicate") is None


def test_candidate_ledger_keeps_distinct_weaknesses_and_operations():
    base = {
        "category": "A03",
        "location": "app.py:10",
        "suggested_endpoint": "GET /users",
        "source_trace": {"file": "app.py", "symbol": "search_users"},
        "sink_trace": {"file": "app.py", "symbol": "execute_search"},
        "validation_status": "pending",
    }
    candidates = [
        {**base, "candidate_id": 1, "title": "SQL injection in search"},
        {**base, "candidate_id": 2, "title": "Command injection in search"},
        {
            **base,
            "candidate_id": 3,
            "title": "SQL injection in export",
            "sink_trace": {"file": "app.py", "symbol": "execute_export"},
        },
    ]

    assert reconcile_candidate_ledger(candidates)["unique"] == 3
    assert all(item["validation_status"] == "pending" for item in candidates)


def test_candidate_ledger_respects_distinct_root_causes_in_one_operation():
    base = {
        "category": "A03",
        "location": "app.py:10",
        "suggested_endpoint": "GET /users",
        "source_trace": {"file": "app.py", "symbol": "search_users"},
        "sink_trace": {"file": "app.py", "symbol": "execute_search"},
        "validation_status": "pending",
    }
    candidates = [
        {
            **base,
            "candidate_id": 1,
            "title": "SQL injection in name filter",
            "root_causes": ["Name filter is concatenated into SQL"],
        },
        {
            **base,
            "candidate_id": 2,
            "title": "SQL injection in sort filter",
            "root_causes": ["Sort filter is concatenated into SQL"],
        },
    ]

    assert reconcile_candidate_ledger(candidates)["unique"] == 2


def test_candidate_ledger_merges_same_line_without_structured_trace():
    candidates = [
        {
            "candidate_id": 1,
            "category": "A03",
            "title": "SQL injection in lookup",
            "location": "app.py:10",
            "description": "Untrusted name reaches SQL.",
            "validation_status": "pending",
        },
        {
            "candidate_id": 2,
            "category": "A03",
            "title": "Unparameterized query in lookup",
            "location": "app.py:10",
            "description": "The lookup concatenates the name.",
            "validation_status": "pending",
        },
    ]

    assert reconcile_candidate_ledger(candidates)["merged"] == 1


def test_candidate_ledger_merges_same_disclosure_across_categories_and_locations():
    candidates = [
        {
            "candidate_id": 1,
            "category": "A01",
            "title": "Public health route discloses signing secret and DB credentials",
            "location": "src/Router.php:22-34",
            "description": "Health response includes sensitive configuration.",
            "validation_status": "pending",
        },
        {
            "candidate_id": 2,
            "category": "A05",
            "title": "Health endpoint leaks signing secret and DB credentials",
            "location": "src/Router.php:86 (route registration)",
            "suggested_endpoint": "GET /api/health",
            "description": "The unauthenticated response returns configuration.",
            "validation_status": "pending",
        },
    ]

    assert reconcile_candidate_ledger(candidates)["merged"] == 1
    assert candidates[1]["reconciled_into_candidate_id"] == 1


def test_candidate_ledger_keeps_different_secret_assets_and_cors_controls():
    candidates = [
        {
            "candidate_id": 1,
            "title": "Hardcoded default JWT signing secret",
            "location": "config/app.php:21",
            "validation_status": "pending",
        },
        {
            "candidate_id": 2,
            "title": "Hardcoded default machine token",
            "location": "config/app.php:21",
            "validation_status": "pending",
        },
        {
            "candidate_id": 3,
            "title": "CORS wildcard origin allows any site",
            "location": "config/app.php:32",
            "validation_status": "pending",
        },
        {
            "candidate_id": 4,
            "title": "CORS reflected Origin with credentials",
            "location": "config/app.php:32",
            "validation_status": "pending",
        },
    ]

    assert reconcile_candidate_ledger(candidates)["unique"] == 4


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
