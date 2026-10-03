from __future__ import annotations

import importlib
import json
from copy import deepcopy

import pytest
from sqlmodel import Session, select

from aespa.extensions import ExtensionDataStore
from aespa.models import SastRun
from tests.test_benchmark_lab import enabled_benchmarking  # noqa: F401


@pytest.fixture
def portable(client, tmp_path):
    models = importlib.import_module("aespa_external_aespa_benchmarking.models")
    transfer = importlib.import_module("aespa_external_aespa_benchmarking.transfer")
    stores = []
    for name in ("first", "second", "third"):
        store = ExtensionDataStore(
            "aespa.benchmarking", "benchmarking", tmp_path / f"{name}.db"
        )
        store.create_all(models.metadata)
        stores.append(store)
    yield models, transfer, stores
    for store in stores:
        store.dispose()


def seed(models, store, name="Scan", run_kind="site"):
    truth = {
        "schema_version": 1,
        "name": "Fixture",
        "items": [{"external_id": "one", "title": "SQL injection"}],
    }
    with store.session() as session:
        dataset = models.Dataset(
            name="Fixture",
            ground_truth_json=json.dumps(truth),
            ground_truth_digest="old",
        )
        session.add(dataset)
        session.flush()
        session.add(
            models.DatasetLabel(dataset_id=dataset.id, label="Shared application")
        )
        result = models.ScanResult(
            run_kind=run_kind,
            run_id=1,
            target_kind="site",
            target_id=1,
            dataset_id=dataset.id,
            run_name=name,
            target_name="Bank",
            ground_truth_json=json.dumps(truth),
            findings_json=json.dumps(
                [{"id": 1, "title": "SQL injection", "evidence": "saved proof"}]
            ),
            rows_json=json.dumps(
                {
                    "rows": [
                        {
                            "external_id": "one",
                            "disposition": "full",
                            "finding_ids": [1],
                            "reviewed": True,
                        }
                    ],
                    "scan_models": {"primary": {"model": "scanner"}},
                    "scan_cost_usd": 0.42,
                }
            ),
        )
        session.add(result)
        evaluation = models.Evaluation(
            name=name, dataset_id=dataset.id, sast_run_id=1, status="completed"
        )
        session.add(evaluation)
        session.flush()
        session.add(
            models.Match(
                evaluation_id=evaluation.id,
                scan_lead_id=1,
                ground_truth_external_id="one",
                disposition="full",
                human_reviewed=True,
                review_note="Reviewed proof",
            )
        )
        session.add(
            models.Comparison(
                name="Comparison",
                dataset_id=dataset.id,
                evaluation_ids_json=json.dumps([evaluation.id]),
            )
        )
        session.commit()


def export(transfer, store, core):
    with store.session() as session:
        data = transfer.export_bundle(session, core)
        session.commit()
        return data


def merge(transfer, store, core, data):
    with store.session() as session:
        result = transfer.import_bundle(
            session, core, transfer.Bundle.model_validate(data)
        )
        session.commit()
        return result


@pytest.mark.parametrize("run_kind", ["site", "api", "sast"])
def test_multihost_roundtrip_preserves_snapshots_and_remaps_links(
    portable, db_engine, run_kind
):
    models, transfer, (first, second, third) = portable
    seed(models, first, "First host", run_kind)
    seed(models, second, "Second host", run_kind)
    with Session(db_engine) as core:
        core.add(SastRun(name="Unrelated local scan", status="completed"))
        core.commit()
        source = export(transfer, first, core)
        report = merge(transfer, second, core, source)
        assert report == {
            "imported": 3,
            "skipped": 0,
            "conflicts": [],
            "datasets_added": 0,
        }
        assert merge(transfer, second, core, source)["skipped"] == 3
        combined = export(transfer, second, core)
        assert len(combined["datasets"]) == 1
        assert len(combined["results"]) == 2
        assert merge(transfer, third, core, combined)["imported"] == 6
        # Passing through another host keeps the original identity.
        assert (
            merge(transfer, first, core, export(transfer, third, core))["skipped"] == 3
        )
        assert merge(transfer, first, core, source)["skipped"] == 3
    with second.session() as session:
        imported = session.exec(
            select(models.ScanResult).where(models.ScanResult.run_name == "First host")
        ).one()
        assert imported.run_id == 0
        assert imported.target_id is None
        assert json.loads(imported.findings_json)[0]["evidence"] == "saved proof"
        assert json.loads(imported.rows_json)["scan_cost_usd"] == 0.42
        evaluation = session.exec(
            select(models.Evaluation).where(models.Evaluation.name == "First host")
        ).one()
        assert evaluation.sast_run_id == 0
        match = session.exec(
            select(models.Match).where(models.Match.evaluation_id == evaluation.id)
        ).one()
        assert match.review_note == "Reviewed proof"
        comparison = session.exec(
            select(models.Comparison).order_by(models.Comparison.id.desc())
        ).first()
        assert json.loads(comparison.evaluation_ids_json) == [evaluation.id]


def test_roundtrip_preserves_combined_cost_without_local_source_runs(
    portable, db_engine
):
    models, transfer, (first, second, _) = portable
    seed(models, first)
    breakdown = {
        "run_cost_usd": 10,
        "sast": [{"run_id": 273, "cost_usd": 3}],
        "complete": True,
    }
    with first.session() as session:
        row = session.exec(select(models.ScanResult)).one()
        saved = json.loads(row.rows_json)
        saved.update(scan_cost_usd=13, scan_cost_breakdown=breakdown)
        row.rows_json = json.dumps(saved)
        session.add(row)
        session.commit()
    with Session(db_engine) as core:
        merge(transfer, second, core, export(transfer, first, core))
        exported = export(transfer, second, core)
    saved = json.loads(exported["results"][0]["data"]["rows_json"])
    assert saved["scan_cost_usd"] == 13
    assert saved["scan_cost_breakdown"] == breakdown


def test_conflicts_keep_local_reviews_and_skip_dependent_comparisons(
    portable, db_engine
):
    models, transfer, (first, second, _) = portable
    seed(models, first)
    with Session(db_engine) as core:
        source = export(transfer, first, core)
        merge(transfer, second, core, source)
        with second.session() as session:
            match = session.exec(select(models.Match)).first()
            match.review_note = "Local review"
            session.add(match)
            session.commit()
        report = merge(transfer, second, core, source)
        assert [item["kind"] for item in report["conflicts"]] == ["evaluations"]
        assert report["skipped"] == 2
        source["comparisons"][0]["key"] = "87654321-1234-4321-8765-123456789012"
        report = merge(transfer, second, core, source)
        assert [item["kind"] for item in report["conflicts"]] == [
            "evaluations",
            "comparisons",
        ]
    with second.session() as session:
        assert session.exec(select(models.Match)).first().review_note == "Local review"


@pytest.mark.parametrize(
    "damage", ["reference", "dataset", "local_id", "rows", "version", "duplicate"]
)
def test_invalid_bundle_is_atomic(portable, db_engine, damage):
    models, transfer, (first, second, _) = portable
    seed(models, first)
    with Session(db_engine) as core:
        source = deepcopy(export(transfer, first, core))
        if damage == "reference":
            source["comparisons"][0]["evaluations"] = [
                "87654321-1234-4321-8765-123456789012"
            ]
        elif damage == "dataset":
            source["datasets"][0]["data"]["ground_truth_json"] = '{"items": []}'
        elif damage == "local_id":
            source["results"][0]["data"]["run_id"] = 1
        elif damage == "rows":
            source["results"][0]["data"]["rows_json"] = '{"rows": [{}]}'
        elif damage == "version":
            source["version"] = 2
        else:
            source["results"].append(source["results"][0])
        with pytest.raises(ValueError):
            merge(transfer, second, core, source)
    with second.session() as session:
        assert session.exec(select(models.Dataset)).first() is None
        assert session.exec(select(models.ScanResult)).first() is None


def test_transfer_api_rejects_invalid_file_and_exports_download(client):
    base = "/extension/aespa.benchmarking"
    response = client.get(f"{base}/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["format"] == "aespa-benchmark-lab"
    assert client.post(f"{base}/import", json=payload).status_code == 200
    assert client.post(f"{base}/import", json={"version": 99}).status_code == 422


def test_imported_records_are_reviewable_but_never_use_local_scans(
    portable, db_engine, client
):
    models, transfer, (first, _, _) = portable
    seed(models, first)
    base = "/extension/aespa.benchmarking"
    with Session(db_engine) as core:
        core.add(SastRun(name="Unrelated local scan", status="completed"))
        core.commit()
        source = export(transfer, first, core)
    response = client.post(f"{base}/import", json=source)
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 3
    result = client.get(f"{base}/results").json()[0]
    assert result["imported"] is True
    assert result["run_id"] == 0
    assert result["scan_models"]["primary"]["model"] == "scanner"
    assert result["scan_cost_usd"] == 0.42
    evaluation = client.get(f"{base}/evaluations").json()[0]
    assert evaluation["imported"] is True
    assert client.post(f"{base}/evaluations/{evaluation['id']}/run").status_code == 409
    reviewed = client.put(
        f"{base}/results/{result['id']}/review",
        json={
            "external_id": "one",
            "disposition": "partial",
            "finding_ids": [1],
            "note": "Reviewed on receiving host",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["rows"][0]["review_note"] == "Reviewed on receiving host"
    repeated = client.post(f"{base}/import", json=source).json()
    assert [item["kind"] for item in repeated["conflicts"]] == ["results"]
    with Session(db_engine) as core:
        assert [run.name for run in core.exec(select(SastRun))] == [
            "Unrelated local scan"
        ]
    assert client.delete(f"{base}/results/{result['id']}").status_code == 204
    assert client.post(f"{base}/import", json=source).json()["imported"] == 1
    assert len(client.get(f"{base}/results").json()) == 1


def test_invalid_late_record_rolls_back_api_import(portable, db_engine, client):
    models, transfer, (first, _, _) = portable
    seed(models, first)
    with Session(db_engine) as core:
        source = export(transfer, first, core)
    source["comparisons"][0]["data"]["thresholds_json"] = "[]"
    base = "/extension/aespa.benchmarking"
    assert client.post(f"{base}/import", json=source).status_code == 422
    assert client.get(f"{base}/datasets").json() == []
    assert client.get(f"{base}/results").json() == []
