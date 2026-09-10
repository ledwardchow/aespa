from __future__ import annotations

from aespa.services.sast_semantic import (
    build_repository_model,
    build_threat_model,
    closure_assurance,
    deterministic_dependency_analysis,
    plan_semantic_obligations,
    reconcile_candidates,
    record_obligation_disposition,
)


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
