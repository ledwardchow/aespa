from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.models import LLMConfig, SastRun, ScanLead


def _completed_run(db_engine) -> int:
    with Session(db_engine) as session:
        run = SastRun(name="benchmark fixture", status="completed")
        session.add(run)
        session.commit()
        session.refresh(run)
        lead = ScanLead(
            producer_run_type="sast",
            producer_run_id=run.id,
            title="SQL injection in query",
            category="CWE-89",
            location="app.py:42",
            evidence="user input reaches SQL query",
            reportable=True,
        )
        session.add(lead)
        session.commit()
        return run.id


def test_benchmark_lab_config_defaults_off_and_persists(client):
    response = client.get("/api/settings/benchmark-lab")
    assert response.status_code == 200
    assert response.json()["panel_enabled"] is False

    response = client.put(
        "/api/settings/benchmark-lab",
        json={
            "panel_enabled": True,
            "default_match_mode": "deterministic",
            "default_repetitions": 2,
        },
    )
    assert response.status_code == 200
    assert response.json()["panel_enabled"] is True


def test_benchmark_evaluation_matches_without_mutating_sast_run(client, db_engine):
    run_id = _completed_run(db_engine)
    dataset = client.post(
        "/api/benchmark-lab/datasets",
        json={
            "name": "fixture",
            "ground_truth": {
                "schema_version": 1,
                "items": [
                    {
                        "external_id": "GT-1",
                        "title": "SQL injection",
                        "category": "CWE-89",
                        "locations": [{"path": "app.py", "line": 42}],
                        "root_cause": "user input reaches SQL query",
                    }
                ],
            },
        },
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]
    evaluation = client.post(
        "/api/benchmark-lab/evaluations",
        json={
            "name": "run 1",
            "sast_run_id": run_id,
            "dataset_id": dataset_id,
            "match_mode": "deterministic",
        },
    )
    assert evaluation.status_code == 201
    evaluation_id = evaluation.json()["id"]
    result = client.post(f"/api/benchmark-lab/evaluations/{evaluation_id}/run")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "completed"
    assert body["blindness_status"] in {"warning", "valid"}
    assert json.loads(body["metrics_json"])["full_recall"] == 1.0
    assert body["matches"][0]["disposition"] == "full"
    review = client.post(
        f"/api/benchmark-lab/evaluations/{evaluation_id}/matches/{body['matches'][0]['id']}/review",
        json={
            "disposition": "partial",
            "review_note": "Expected evidence is only partly represented.",
        },
    )
    assert review.status_code == 200
    assert len(json.loads(review.json()["review_history_json"])) == 1
    assert (
        client.get(
            f"/api/benchmark-lab/evaluations/{evaluation_id}/export?format=csv"
        ).status_code
        == 200
    )
    with Session(db_engine) as session:
        run = session.get(SastRun, run_id)
        assert run.status == "completed"


def test_assisted_matching_uses_bounded_completed_output_only(
    client, db_engine, monkeypatch
):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        config = LLMConfig(name="benchmark evaluator", model="fake")
        session.add(config)
        session.commit()
        session.refresh(config)
        run = session.get(SastRun, run_id)
        run.llm_config_id = config.id
        session.add(run)
        session.commit()
        lead_id = (
            session.exec(select(ScanLead).where(ScanLead.producer_run_id == run_id))
            .one()
            .id
        )

    captured: dict[str, str] = {}

    async def fake_completion(_config, prompt, *, system_prompt):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        return json.dumps(
            {
                "decisions": [
                    {
                        "ground_truth_external_id": "GT-1",
                        "scan_lead_id": lead_id,
                        "disposition": "partial",
                        "confidence": 0.8,
                        "rationale": "The root cause matches but impact is incomplete.",
                    }
                ]
            }
        )

    from aespa.services import llm

    monkeypatch.setattr(llm, "plain_completion", fake_completion)
    dataset = client.post(
        "/api/benchmark-lab/datasets",
        json={
            "name": "assisted fixture",
            "ground_truth": {
                "items": [
                    {
                        "external_id": "GT-1",
                        "title": "SQL injection",
                        "category": "CWE-89",
                    }
                ]
            },
        },
    ).json()
    evaluation = client.post(
        "/api/benchmark-lab/evaluations",
        json={
            "name": "assisted",
            "sast_run_id": run_id,
            "dataset_id": dataset["id"],
            "match_mode": "assisted",
        },
    ).json()
    result = client.post(f"/api/benchmark-lab/evaluations/{evaluation['id']}/run")

    assert result.status_code == 200, result.text
    body = result.json()
    assert body["matching_version"] == "assisted-v1"
    assert body["matches"][0]["disposition"] == "partial"
    assert "scanner_output" in captured["prompt"]
    assert "deterministic_proposals" in captured["prompt"]
    assert (
        "Repository tools and scanner transcripts are unavailable"
        in captured["system_prompt"]
    )


def test_benchmark_rejects_non_terminal_sast_run(client, db_engine):
    with Session(db_engine) as session:
        run = SastRun(name="active", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    dataset = client.post(
        "/api/benchmark-lab/datasets",
        json={"name": "fixture", "ground_truth": {"items": []}},
    )
    response = client.post(
        "/api/benchmark-lab/evaluations",
        json={
            "name": "invalid",
            "sast_run_id": run_id,
            "dataset_id": dataset.json()["id"],
        },
    )
    assert response.status_code == 409


def test_benchmark_marks_answer_key_inside_source_as_contaminated(
    client, db_engine, tmp_path
):
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("src/app.py", "def app(): return True\n")
        bundle.writestr("VULNERABILITIES.md", "GT-1: SQL injection\n")
    with Session(db_engine) as session:
        run = SastRun(
            name="contaminated fixture",
            status="completed",
            source_archive_path=str(archive),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    dataset = client.post(
        "/api/benchmark-lab/datasets",
        json={
            "name": "fixture",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    evaluation = client.post(
        "/api/benchmark-lab/evaluations",
        json={
            "name": "blindness audit",
            "sast_run_id": run_id,
            "dataset_id": dataset["id"],
            "match_mode": "deterministic",
        },
    ).json()
    result = client.post(
        f"/api/benchmark-lab/evaluations/{evaluation['id']}/run"
    ).json()
    assert result["blindness_status"] == "contaminated"
    assert json.loads(result["metrics_json"])["aggregate_eligible"] is False


def test_benchmark_comparison_reports_range_frequency_and_thresholds(client, db_engine):
    run_id = _completed_run(db_engine)
    dataset = client.post(
        "/api/benchmark-lab/datasets",
        json={
            "name": "repeat fixture",
            "ground_truth": {
                "items": [
                    {
                        "external_id": "GT-1",
                        "title": "SQL injection",
                        "category": "CWE-89",
                        "locations": [{"path": "app.py", "line": 42}],
                        "root_cause": "user input reaches SQL query",
                    }
                ]
            },
        },
    ).json()
    evaluation_ids = []
    for number in (1, 2):
        evaluation = client.post(
            "/api/benchmark-lab/evaluations",
            json={
                "name": f"repeat {number}",
                "sast_run_id": run_id,
                "dataset_id": dataset["id"],
                "match_mode": "deterministic",
            },
        ).json()
        completed = client.post(
            f"/api/benchmark-lab/evaluations/{evaluation['id']}/run"
        ).json()
        evaluation_ids.append(completed["id"])
    response = client.post(
        "/api/benchmark-lab/comparisons",
        json={
            "name": "two repeats",
            "dataset_id": dataset["id"],
            "evaluation_ids": evaluation_ids,
            "thresholds": {"inclusive_recall": {"min": 1.0}},
        },
    )
    assert response.status_code == 201, response.text
    comparison = response.json()
    metrics = json.loads(comparison["metrics_json"])
    assert comparison["status"] == "passed"
    assert metrics["inclusive_recall"] == {
        "median": 1.0,
        "min": 1.0,
        "max": 1.0,
        "values": [1.0, 1.0],
    }
    assert metrics["detection_frequency"]["GT-1"]["frequency"] == 1.0
