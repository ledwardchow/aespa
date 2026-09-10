from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone

from sqlmodel import Session

from aespa.models import SastRun, ScanLead


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
        json={"panel_enabled": True, "default_match_mode": "deterministic", "default_repetitions": 2},
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
        json={"name": "run 1", "sast_run_id": run_id, "dataset_id": dataset_id, "match_mode": "deterministic"},
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
    assert client.get(f"/api/benchmark-lab/evaluations/{evaluation_id}/export?format=csv").status_code == 200
    with Session(db_engine) as session:
        run = session.get(SastRun, run_id)
        assert run.status == "completed"


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
        json={"name": "invalid", "sast_run_id": run_id, "dataset_id": dataset.json()["id"]},
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
