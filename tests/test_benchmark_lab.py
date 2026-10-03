from __future__ import annotations

import asyncio
import importlib
import json
import zipfile
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select

from aespa.models import (
    ApiCollection,
    ApiTestRun,
    LLMConfig,
    LLMProfile,
    SastRun,
    ScanFinding,
    ScanLead,
    Site,
    TestRun,
)

BASE = "/extension/aespa.benchmarking"


@pytest.mark.parametrize("kind", ["site", "api"])
@pytest.mark.parametrize("has_start_time", [True, False])
def test_saved_ground_truth_compares_dast_and_keeps_result_snapshot(
    client, db_engine, monkeypatch, kind, has_start_time
):
    with Session(db_engine) as session:
        model = LLMConfig(name="Benchmark evaluator", model="test-model")
        scan_model = LLMConfig(name="Test Lead", model="scan-model")
        session.add_all([model, scan_model])
        session.commit()
        model_id = model.id
        target = (
            Site(name="Fixture site", base_url="https://example.test")
            if kind == "site"
            else ApiCollection(name="Fixture API", base_url="https://example.test")
        )
        session.add(target)
        session.commit()
        session.refresh(target)
        run = (
            TestRun(site_id=target.id, name="Site scan", status="complete")
            if kind == "site"
            else ApiTestRun(
                collection_id=target.id, name="API scan", status="completed"
            )
        )
        run.created_at = datetime(2026, 9, 30, 7, 0, tzinfo=timezone.utc)
        if has_start_time:
            run.started_at = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)
        run.llm_config_id = scan_model.id
        run.token_usage_json = json.dumps(
            {
                "scan-model": {
                    "input": 100,
                    "output": 200,
                    "provider": "anthropic",
                    "estimated_cost_available": True,
                    "estimated_total_cost_usd": 0.42,
                },
                "other-model": {
                    "input": 250,
                    "output": 1,
                    "requests": 100,
                    "estimated_cost_available": True,
                    "estimated_total_cost_usd": 0.0,
                },
            }
        )
        if kind == "site":
            run.execution_snapshot_json = json.dumps(
                {"model": {"provider": "openai", "model": "scanned-model"}}
            )
        session.add(run)
        session.commit()
        session.refresh(run)
        finding = ScanFinding(
            test_run_id=run.id if kind == "site" else None,
            api_test_run_id=run.id if kind == "api" else None,
            owasp_category="A03",
            owasp_api_category="API8" if kind == "api" else None,
            severity="high",
            title="SQL injection in customer search",
            description="Customer search query accepts SQL injection",
            affected_url="https://example.test/customers/search",
            evidence="SQL injection proved in customer search query",
            validation_status="confirmed",
        )
        ignored = ScanFinding(
            test_run_id=run.id if kind == "site" else None,
            api_test_run_id=run.id if kind == "api" else None,
            owasp_category="A03",
            severity="high",
            title="False finding",
            description="Ignore this",
            validation_status="false_positive",
        )
        session.add_all([finding, ignored])
        session.commit()
        target_id, run_id, finding_id = target.id, run.id, finding.id

    calls = []

    async def answer(_config, prompt, **_kwargs):
        calls.append(json.loads(prompt))
        return json.dumps(
            {
                "decisions": [
                    {
                        "ground_truth_external_id": external_id,
                        "disposition": "missing" if external_id == "GT-3" else "full",
                        "finding_ids": [] if external_id == "GT-3" else [finding_id],
                        "reason": "Model decision",
                    }
                    for external_id in ("GT-1", "GT-2", "GT-3")
                ]
            }
        )

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)

    ground_truth = {
        "items": [
            {
                "external_id": "GT-1",
                "title": "SQL injection in customer search",
                "affected_operation": "/customers/search",
            },
            {
                "external_id": "GT-2",
                "title": "SQL injection in customer search",
                "affected_operation": "/customers/search",
            },
            {"external_id": "GT-3", "title": "Missing authentication logging"},
        ]
    }
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Fixture ground truth",
            "ground_truth": ground_truth,
        },
    ).json()
    assert (
        client.put(
            f"{BASE}/ground-truth/{kind}/{target_id}",
            json={
                "dataset_id": dataset["id"],
            },
        ).status_code
        == 200
    )
    targets = client.get(f"{BASE}/targets").json()
    key = "sites" if kind == "site" else "apis"
    assert targets[key][0]["dataset"]["item_count"] == 3

    response = client.post(
        f"{BASE}/results",
        json={
            "run_kind": kind,
            "run_id": run_id,
            "evaluation_model_id": model_id,
        },
    )
    assert response.status_code == 201, response.text
    assert client.delete(f"{BASE}/datasets/{dataset['id']}").status_code == 409
    result = response.json()
    assert result["comparison"]["method"] == "model"
    expected_hour = "08" if has_start_time else "07"
    assert result["scan_started_at"] == f"2026-09-30T{expected_hour}:00:00+00:00"
    assert result["scan_cost_usd"] == 0.42
    assert result["scan_models"]["primary"] == {
        "id": None,
        "name": "scan-model",
        "model": "scan-model",
        "provider": "anthropic",
    }
    assert result["scan_models"]["sast"] == []
    assert len(calls) == 1
    assert len(calls[0]["scan_findings"]) == 1
    assert len(result["findings"]) == 1
    assert result["summary"] == {"full": 2, "partial": 0, "missing": 1}
    assert result["rows"][0]["finding_ids"] == [finding_id]
    assert result["rows"][1]["finding_ids"] == [finding_id]

    reviewed = client.put(
        f"{BASE}/results/{result['id']}/review",
        json={
            "external_id": "GT-1",
            "disposition": "partial",
            "finding_ids": [finding_id],
            "note": "Only one affected route was tested",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["summary"] == {"full": 1, "partial": 1, "missing": 1}
    replacement = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Replacement",
            "ground_truth": {
                "items": [{"external_id": "NEW", "title": "Another issue"}]
            },
        },
    ).json()
    client.put(
        f"{BASE}/ground-truth/{kind}/{target_id}",
        json={
            "dataset_id": replacement["id"],
        },
    )
    saved = client.get(f"{BASE}/results/{result['id']}").json()
    assert saved["ground_truth"]["items"][0]["external_id"] == "GT-1"
    assert saved["scan_cost_usd"] == 0.42
    assert client.get(f"{BASE}/results").json()[0]["scan_cost_usd"] == 0.42


def test_sast_can_compare_with_saved_site_ground_truth(client, db_engine, monkeypatch):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        model = LLMConfig(name="Benchmark evaluator", model="test-model")
        sast_model = LLMConfig(name="SAST agent", model="sast-model")
        session.add_all([model, sast_model])
        session.commit()
        model_id = model.id
        source_run = session.get(SastRun, run_id)
        source_run.llm_config_id = sast_model.id
        source_run.token_usage_json = json.dumps(
            {"sast-model": {"input": 100, "output": 10, "provider": "anthropic"}}
        )
        session.add(source_run)
        session.commit()
        site = Site(name="Source target", base_url="https://example.test")
        session.add(site)
        session.commit()
        session.refresh(site)
        site_id = site.id

    async def answer(*_args, **_kwargs):
        return json.dumps(
            {
                "decisions": [
                    {
                        "ground_truth_external_id": "GT-1",
                        "disposition": "missing",
                        "finding_ids": [],
                        "reason": "No equivalent lead",
                    }
                ]
            }
        )

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Shared truth",
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
    assert (
        client.put(
            f"{BASE}/ground-truth/site/{site_id}", json={"dataset_id": dataset["id"]}
        ).status_code
        == 200
    )
    result = client.post(
        f"{BASE}/results",
        json={
            "run_kind": "sast",
            "run_id": run_id,
            "dataset_id": dataset["id"],
            "evaluation_model_id": model_id,
        },
    )
    assert result.status_code == 201, result.text
    assert result.json()["run_kind"] == "sast"
    assert result.json()["target_kind"] == "site"
    assert result.json()["target_id"] == site_id
    assert len(result.json()["rows"]) == 1
    assert result.json()["comparison"]["method"] == "model"
    assert result.json()["scan_models"] == {
        "primary": {
            "id": None,
            "name": "sast-model",
            "model": "sast-model",
            "provider": "anthropic",
        },
        "sast": [
            {
                "run_id": run_id,
                "run_name": "benchmark fixture",
                "model": {
                    "id": None,
                    "name": "sast-model",
                    "model": "sast-model",
                    "provider": "anthropic",
                },
            }
        ],
    }


def test_dast_result_lists_sast_models_from_leads_for_the_right_run_kind(
    client, db_engine, monkeypatch
):
    with Session(db_engine) as session:
        evaluator = LLMConfig(name="Evaluator", model="eval-model")
        web_model = LLMConfig(name="Web Test Lead", model="web-model")
        api_model = LLMConfig(name="API Test Lead", model="api-model")
        web_sast_model = LLMConfig(name="Web source SAST", model="web-sast-model")
        api_sast_model = LLMConfig(name="API source SAST", model="api-sast-model")
        session.add_all(
            [evaluator, web_model, api_model, web_sast_model, api_sast_model]
        )
        session.commit()
        evaluator_id = evaluator.id
        web_sast_model_id = web_sast_model.id
        api_sast_model_id = api_sast_model.id
        site = Site(name="Web target", base_url="https://example.test")
        api = ApiCollection(name="API target", base_url="https://example.test")
        session.add_all([site, api])
        session.commit()
        web_run = TestRun(
            site_id=site.id,
            name="Web scan",
            status="complete",
            llm_config_id=web_model.id,
        )
        session.add(web_run)
        session.commit()
        api_run = ApiTestRun(
            collection_id=api.id,
            name="API scan",
            status="completed",
            llm_config_id=api_model.id,
        )
        web_source = SastRun(
            name="Web source", status="completed", llm_config_id=web_sast_model_id
        )
        api_source = SastRun(
            name="API source", status="completed", llm_config_id=api_sast_model_id
        )
        for scan, model, cost in [
            (web_run, "web-model", 1.0),
            (api_run, "api-model", 2.0),
            (web_source, "web-sast-model", 3.0),
            (api_source, "api-sast-model", 4.0),
        ]:
            scan.token_usage_json = json.dumps(
                {
                    model: {
                        "input": 10,
                        "output": 5,
                        "estimated_cost_available": True,
                        "estimated_total_cost_usd": cost,
                    }
                }
            )
        session.add_all([web_run, api_run, web_source, api_source])
        session.commit()
        session.add_all(
            [
                ScanLead(
                    producer_run_type="sast",
                    producer_run_id=web_source.id,
                    imported_into_run_type="web",
                    imported_into_run_id=web_run.id,
                    title="Web SAST lead",
                ),
                ScanLead(
                    producer_run_type="sast",
                    producer_run_id=web_source.id,
                    investigated_by_run_type="web",
                    investigated_by_run_id=web_run.id,
                    title="Another lead from the same SAST run",
                ),
                ScanLead(
                    producer_run_type="sast",
                    producer_run_id=api_source.id,
                    imported_into_run_type="api",
                    imported_into_run_id=api_run.id,
                    title="API SAST lead",
                ),
                ScanLead(
                    producer_run_type="sast",
                    producer_run_id=api_source.id,
                    imported_into_run_type="api",
                    imported_into_run_id=web_run.id,
                    title="Other API run with the Web run's numeric ID",
                ),
                ScanLead(
                    producer_run_type="sast",
                    producer_run_id=web_source.id,
                    imported_into_run_type="web",
                    imported_into_run_id=api_run.id,
                    title="Other Web run with the API run's numeric ID",
                ),
            ]
        )
        session.commit()
        targets = [
            ("site", site.id, web_run.id, "Web source", "web-sast-model"),
            ("api", api.id, api_run.id, "API source", "api-sast-model"),
        ]

    async def answer(*_args, **_kwargs):
        return '{"decisions": []}'

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)
    dataset = client.post(
        f"{BASE}/datasets",
        json={"name": "Fixture", "ground_truth": {"items": []}},
    ).json()
    listed = client.get(f"{BASE}/targets").json()
    for kind, target_id, run_id, source_name, source_model in targets:
        key = "sites" if kind == "site" else "apis"
        listed_run = next(row for row in listed[key][0]["runs"] if row["id"] == run_id)
        assert listed_run["scan_models"]["primary"]["model"] == (
            "web-model" if kind == "site" else "api-model"
        )
        assert len(listed_run["scan_models"]["sast"]) == 1
        assert listed_run["scan_models"]["sast"][0]["model"]["model"] == source_model
        assert (
            client.put(
                f"{BASE}/ground-truth/{kind}/{target_id}",
                json={"dataset_id": dataset["id"]},
            ).status_code
            == 200
        )
        response = client.post(
            f"{BASE}/results",
            json={
                "run_kind": kind,
                "run_id": run_id,
                "evaluation_model_id": evaluator_id,
            },
        )
        assert response.status_code == 201, response.text
        saved = client.get(f"{BASE}/results/{response.json()['id']}").json()
        assert len(saved["scan_models"]["sast"]) == 1
        assert saved["scan_models"]["sast"][0]["run_name"] == source_name
        assert saved["scan_models"]["sast"][0]["model"]["model"] == source_model
        assert response.json()["scan_cost_usd"] == (4.0 if kind == "site" else 6.0)
        assert saved["scan_cost_usd"] == (4.0 if kind == "site" else 6.0)
        assert saved["scan_cost_breakdown"]["complete"] is True
        assert len(saved["scan_cost_breakdown"]["sast"]) == 1


@pytest.mark.parametrize("source_state", ["priced", "unpriced", "deleted"])
def test_existing_result_adds_all_sast_costs_without_changing_saved_data(
    db_engine, source_state
):
    router = importlib.import_module("aespa_external_aespa_benchmarking.router")

    def usage(cost):
        return json.dumps(
            {
                "model": {
                    "estimated_cost_available": True,
                    "estimated_total_cost_usd": cost,
                }
            }
        )

    with Session(db_engine) as core:
        site = Site(name="Cost fixture", base_url="https://example.test")
        core.add(site)
        core.commit()
        run = TestRun(site_id=site.id, name="DAST", token_usage_json=usage(10))
        first = SastRun(name="First source", token_usage_json=usage(3))
        second = SastRun(
            name="Second source",
            token_usage_json=usage(4) if source_state != "unpriced" else None,
        )
        core.add_all([run, first, second])
        core.commit()
        core.add(
            ScanLead(
                producer_run_type="sast",
                producer_run_id=second.id,
                imported_into_run_type="web",
                imported_into_run_id=run.id,
                title="Source linked after the benchmark was saved",
            )
        )
        core.commit()
        second_id = second.id
        # The first source appears twice in the old snapshot.
        row = router.ScanResult(
            run_kind="site",
            run_id=run.id,
            run_name=run.name,
            rows_json=json.dumps(
                {
                    "rows": [],
                    "scan_cost_usd": 10,
                    "scan_models": {
                        "primary": None,
                        "sast": [{"run_id": first.id}, {"run_id": first.id}],
                    },
                }
            ),
        )
        if source_state == "deleted":
            core.delete(second)
            core.commit()
        original = row.rows_json
        result = router.result_out(row, core)
        assert result["scan_cost_usd"] == (17 if source_state == "priced" else None)
        assert result["scan_cost_breakdown"] == {
            "run_cost_usd": 10,
            "sast": [
                {"run_id": first.id, "cost_usd": 3},
                {
                    "run_id": second_id,
                    "cost_usd": 4 if source_state == "priced" else None,
                },
            ],
            "complete": source_state == "priced",
        }
        assert row.rows_json == original
        # New snapshots keep the total if the source data is later removed.
        row.rows_json = json.dumps(
            {
                "rows": [],
                "scan_cost_usd": result["scan_cost_usd"],
                "scan_cost_breakdown": result["scan_cost_breakdown"],
            }
        )
        core.delete(first)
        core.commit()
        assert router.result_out(row, core)["scan_cost_usd"] == result["scan_cost_usd"]


def test_standalone_sast_cost_is_counted_once(db_engine):
    router = importlib.import_module("aespa_external_aespa_benchmarking.router")
    with Session(db_engine) as core:
        run = SastRun(
            name="SAST",
            token_usage_json=json.dumps(
                {
                    "model": {
                        "estimated_cost_available": True,
                        "estimated_total_cost_usd": 3,
                    }
                }
            ),
        )
        core.add(run)
        core.commit()
        row = router.ScanResult(
            run_kind="sast",
            run_id=run.id,
            run_name=run.name,
            rows_json=json.dumps(
                {
                    "rows": [],
                    "scan_models": router.scan_models_snapshot(core, "sast", run),
                }
            ),
        )
        assert router.result_out(row, core)["scan_cost_usd"] == 3


def test_scan_cost_requires_prices_for_every_model():
    router = importlib.import_module("aespa_external_aespa_benchmarking.router")
    run = SastRun(
        name="Partially priced source",
        token_usage_json=json.dumps(
            {
                "priced": {
                    "estimated_cost_available": True,
                    "estimated_total_cost_usd": 3,
                },
                "unpriced": {"input": 1000, "estimated_cost_available": False},
            }
        ),
    )
    assert router.scan_cost(run) is None


def test_historical_result_does_not_use_local_sast_ids(db_engine):
    router = importlib.import_module("aespa_external_aespa_benchmarking.router")
    with Session(db_engine) as core:
        source = SastRun(
            name="Unrelated local source",
            token_usage_json=json.dumps(
                {
                    "model": {
                        "estimated_cost_available": True,
                        "estimated_total_cost_usd": 3,
                    }
                }
            ),
        )
        core.add(source)
        core.commit()
        row = router.ScanResult(
            run_kind="site",
            run_id=-1000000,
            run_name="Historical scan",
            rows_json=json.dumps(
                {
                    "rows": [],
                    "scan_cost_usd": 10,
                    "scan_models": {"primary": None, "sast": [{"run_id": source.id}]},
                }
            ),
        )
        result = router.result_out(row, core)
        assert result["scan_cost_usd"] is None
        assert result["scan_cost_breakdown"]["sast"] == [
            {"run_id": source.id, "cost_usd": None}
        ]


def test_explicit_evaluation_model_is_recorded(client, db_engine, monkeypatch):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        model = LLMConfig(name="Benchmark evaluator", model="test-model")
        session.add(model)
        session.commit()
        session.refresh(model)
        model_id = model.id

    async def answer(*_args, **_kwargs):
        return json.dumps(
            {
                "decisions": [
                    {
                        "ground_truth_external_id": "GT-1",
                        "disposition": "full",
                        "finding_ids": [1],
                        "reason": "The lead names the same SQL injection",
                    }
                ]
            }
        )

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Model fixture",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    result = client.post(
        f"{BASE}/results",
        json={
            "run_kind": "sast",
            "run_id": run_id,
            "dataset_id": dataset["id"],
            "evaluation_model_id": model_id,
        },
    )
    assert result.status_code == 201, result.text
    assert result.json()["comparison"] == {
        "method": "model",
        "model": {"id": model_id, "name": "Benchmark evaluator"},
    }
    assert result.json()["rows"][0]["method"] == "assisted"


def test_default_scan_model_is_used_for_comparison(client, db_engine, monkeypatch):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        model = LLMConfig(name="Scan evaluator", model="scan-model")
        session.add(model)
        session.commit()
        run = session.get(SastRun, run_id)
        run.llm_config_id = model.id
        session.add(run)
        session.commit()
        model_id = model.id

    used_models = []

    async def answer(config, _prompt, **_kwargs):
        used_models.append(config.model)
        return '{"decisions": []}'

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)
    dataset = client.post(
        f"{BASE}/datasets",
        json={"name": "Fixture", "ground_truth": {"items": []}},
    ).json()
    result = client.post(
        f"{BASE}/results",
        json={"run_kind": "sast", "run_id": run_id, "dataset_id": dataset["id"]},
    )
    assert result.status_code == 201, result.text
    assert used_models == ["scan-model"]
    assert result.json()["comparison"]["model"]["id"] == model_id


def test_failed_model_comparison_saves_no_result(client, db_engine, monkeypatch):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        model = LLMConfig(name="Unavailable evaluator", model="test-model")
        session.add(model)
        session.commit()
        session.refresh(model)
        model_id = model.id

    async def fail(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("aespa.services.llm.plain_completion", fail)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Fallback fixture",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    result = client.post(
        f"{BASE}/results",
        json={
            "run_kind": "sast",
            "run_id": run_id,
            "dataset_id": dataset["id"],
            "evaluation_model_id": model_id,
        },
    )
    assert result.status_code == 502, result.text
    assert result.json()["detail"] == "Evaluation model request failed"
    assert client.get(f"{BASE}/results").json() == []


def test_missing_model_and_rules_only_cannot_create_results(client, db_engine):
    run_id = _completed_run(db_engine)
    dataset = client.post(
        f"{BASE}/datasets",
        json={"name": "Fixture", "ground_truth": {"items": []}},
    ).json()
    body = {"run_kind": "sast", "run_id": run_id, "dataset_id": dataset["id"]}
    assert client.post(f"{BASE}/results", json=body).status_code == 409
    assert (
        client.post(f"{BASE}/results", json={**body, "rules_only": True}).status_code
        == 400
    )
    assert client.get(f"{BASE}/results").json() == []


def test_invalid_model_decisions_do_not_save_result(client, db_engine, monkeypatch):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        model = LLMConfig(name="Evaluator", model="test-model")
        session.add(model)
        session.commit()
        model_id = model.id

    async def incomplete(*_args, **_kwargs):
        return '{"decisions": []}'

    monkeypatch.setattr("aespa.services.llm.plain_completion", incomplete)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Fixture",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    response = client.post(
        f"{BASE}/results",
        json={
            "run_kind": "sast",
            "run_id": run_id,
            "dataset_id": dataset["id"],
            "evaluation_model_id": model_id,
        },
    )
    assert response.status_code == 502
    assert client.get(f"{BASE}/results").json() == []


def test_saved_result_can_be_deleted_without_deleting_ground_truth(
    client, db_engine, monkeypatch
):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        model = LLMConfig(name="Evaluator", model="test-model")
        session.add(model)
        session.commit()
        model_id = model.id

    async def answer(*_args, **_kwargs):
        return '{"decisions": []}'

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)
    dataset = client.post(
        f"{BASE}/datasets",
        json={"name": "Fixture", "ground_truth": {"items": []}},
    ).json()
    result = client.post(
        f"{BASE}/results",
        json={
            "run_kind": "sast",
            "run_id": run_id,
            "dataset_id": dataset["id"],
            "evaluation_model_id": model_id,
        },
    )
    assert result.status_code == 201, result.text
    result_id = result.json()["id"]
    assert client.delete(f"{BASE}/results/{result_id}").status_code == 204
    assert client.get(f"{BASE}/results/{result_id}").status_code == 404
    assert client.delete(f"{BASE}/results/{result_id}").status_code == 404
    assert client.get(f"{BASE}/datasets/{dataset['id']}").status_code == 200


@pytest.fixture(autouse=True)
def enabled_benchmarking(client, monkeypatch, tmp_path):
    from aespa.extensions import get_extension_manager

    manager = get_extension_manager()
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "extensions_dir": tmp_path / "extensions",
                "data_dir": tmp_path / "data",
            },
        )(),
    )
    manager.load_extensions()
    response = client.put(
        "/api/extensions/aespa.benchmarking/enabled", json={"enabled": True}
    )
    assert response.status_code == 200
    yield


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


def _stub_legacy_evaluator(db_engine, run_id, monkeypatch):
    with Session(db_engine) as session:
        config = LLMConfig(name="legacy benchmark evaluator", model="fake")
        session.add(config)
        session.commit()
        run = session.get(SastRun, run_id)
        run.llm_config_id = config.id
        session.add(run)
        session.commit()

    async def answer(_config, prompt, **_kwargs):
        data = json.loads(prompt)
        leads = data["scanner_output"]
        return json.dumps(
            {
                "decisions": [
                    {
                        "ground_truth_external_id": item["external_id"],
                        "scan_lead_id": leads[0]["id"] if leads else None,
                        "disposition": "full" if leads else "missed",
                        "confidence": 1.0 if leads else 0.0,
                        "rationale": "Model decision",
                    }
                    for item in data["ground_truth"]
                ]
            }
        )

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)


def test_benchmarking_is_an_extension(client):
    extension = client.get("/api/extensions/aespa.benchmarking").json()
    assert extension["enabled"] is True
    assert extension["api_prefix"] == BASE
    assert extension["data_namespace"] == "benchmarking"


def test_benchmark_evaluation_matches_without_mutating_sast_run(
    client, db_engine, monkeypatch
):
    run_id = _completed_run(db_engine)
    _stub_legacy_evaluator(db_engine, run_id, monkeypatch)
    dataset = client.post(
        f"{BASE}/datasets",
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
        f"{BASE}/evaluations",
        json={
            "name": "run 1",
            "sast_run_id": run_id,
            "dataset_id": dataset_id,
            "match_mode": "assisted",
        },
    )
    assert evaluation.status_code == 201
    evaluation_id = evaluation.json()["id"]
    result = client.post(f"{BASE}/evaluations/{evaluation_id}/run")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "completed"
    assert body["blindness_status"] in {"warning", "valid"}
    assert json.loads(body["metrics_json"])["full_recall"] == 1.0
    assert body["matches"][0]["disposition"] == "full"
    review = client.post(
        f"{BASE}/evaluations/{evaluation_id}/matches/{body['matches'][0]['id']}/review",
        json={
            "disposition": "partial",
            "review_note": "Expected evidence is only partly represented.",
        },
    )
    assert review.status_code == 200
    assert len(json.loads(review.json()["review_history_json"])) == 1
    assert (
        client.get(f"{BASE}/evaluations/{evaluation_id}/export?format=csv").status_code
        == 200
    )
    with Session(db_engine) as session:
        run = session.get(SastRun, run_id)
        assert run.status == "completed"


def test_delete_benchmark_evaluation_and_comparison(client, db_engine, monkeypatch):
    run_id = _completed_run(db_engine)
    _stub_legacy_evaluator(db_engine, run_id, monkeypatch)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "deletion fixture",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    evaluation_ids = []
    for name in ("first", "second"):
        response = client.post(
            f"{BASE}/evaluations",
            json={
                "name": name,
                "sast_run_id": run_id,
                "dataset_id": dataset["id"],
                "match_mode": "assisted",
            },
        )
        assert response.status_code == 201, response.text
        evaluation_id = response.json()["id"]
        evaluation_ids.append(evaluation_id)
        assert client.post(f"{BASE}/evaluations/{evaluation_id}/run").status_code == 200

    comparison = client.post(
        f"{BASE}/comparisons",
        json={
            "name": "two runs",
            "dataset_id": dataset["id"],
            "evaluation_ids": evaluation_ids,
        },
    )
    assert comparison.status_code == 201, comparison.text
    comparison_id = comparison.json()["id"]
    first_id, second_id = evaluation_ids

    blocked = client.delete(f"{BASE}/evaluations/{first_id}")
    assert blocked.status_code == 409
    assert "Delete comparisons" in blocked.json()["detail"]
    assert client.delete(f"{BASE}/comparisons/{comparison_id}").status_code == 204
    assert client.get(f"{BASE}/comparisons/{comparison_id}").status_code == 404
    assert client.delete(f"{BASE}/evaluations/{first_id}").status_code == 204
    assert client.get(f"{BASE}/evaluations/{first_id}").status_code == 404
    assert client.get(f"{BASE}/evaluations/{second_id}").status_code == 200
    assert client.delete(f"{BASE}/evaluations/{first_id}").status_code == 404
    with Session(db_engine) as session:
        assert session.get(SastRun, run_id) is not None


@pytest.mark.parametrize("match_mode", ["deterministic", "human_reviewed"])
def test_legacy_evaluation_rejects_non_model_modes(client, db_engine, match_mode):
    run_id = _completed_run(db_engine)
    dataset = client.post(
        f"{BASE}/datasets",
        json={"name": "Fixture", "ground_truth": {"items": []}},
    ).json()
    response = client.post(
        f"{BASE}/evaluations",
        json={
            "name": "legacy",
            "sast_run_id": run_id,
            "dataset_id": dataset["id"],
            "match_mode": match_mode,
        },
    )
    assert response.status_code == 400
    assert client.get(f"{BASE}/evaluations").json() == []


def test_legacy_evaluation_model_failure_keeps_no_matches(
    client, db_engine, monkeypatch
):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        model = LLMConfig(name="Unavailable evaluator", model="fake")
        session.add(model)
        session.commit()
        run = session.get(SastRun, run_id)
        run.llm_config_id = model.id
        session.add(run)
        session.commit()

    async def fail(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("aespa.services.llm.plain_completion", fail)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Fixture",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    evaluation = client.post(
        f"{BASE}/evaluations",
        json={
            "name": "model comparison",
            "sast_run_id": run_id,
            "dataset_id": dataset["id"],
        },
    ).json()
    response = client.post(f"{BASE}/evaluations/{evaluation['id']}/run")
    assert response.status_code == 502
    saved = client.get(f"{BASE}/evaluations/{evaluation['id']}").json()
    assert saved["status"] == "created"
    assert saved["matches"] == []


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
        f"{BASE}/datasets",
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
        f"{BASE}/evaluations",
        json={
            "name": "assisted",
            "sast_run_id": run_id,
            "dataset_id": dataset["id"],
            "match_mode": "assisted",
        },
    ).json()
    result = client.post(f"{BASE}/evaluations/{evaluation['id']}/run")

    assert result.status_code == 200, result.text
    body = result.json()
    assert body["matching_version"] == "model-v2"
    assert body["matches"][0]["disposition"] == "partial"
    assert "scanner_output" in captured["prompt"]
    assert "deterministic_proposals" not in captured["prompt"]
    assert (
        "Repository tools and scanner transcripts are unavailable"
        in captured["system_prompt"]
    )


def test_assisted_matching_uses_selected_profiles_test_lead_model(
    client, db_engine, monkeypatch
):
    run_id = _completed_run(db_engine)
    with Session(db_engine) as session:
        scan_model = LLMConfig(name="scan model", model="scan-model")
        default_model = LLMConfig(name="profile default", model="default-model")
        test_lead_model = LLMConfig(name="test lead", model="test-lead-model")
        session.add_all([scan_model, default_model, test_lead_model])
        session.commit()
        profile = LLMProfile(
            name="benchmark profile",
            default_model_id=default_model.id,
            role_models_json=json.dumps({"test_lead": test_lead_model.id}),
        )
        session.add(profile)
        run = session.get(SastRun, run_id)
        run.llm_config_id = scan_model.id
        session.add(run)
        session.commit()
        session.refresh(profile)

    used_models = []

    async def fake_completion(config, _prompt, *, system_prompt):
        used_models.append(config.model)
        return '{"decisions": []}'

    from aespa.services import llm

    monkeypatch.setattr(llm, "plain_completion", fake_completion)
    dataset = client.post(
        f"{BASE}/datasets",
        json={"name": "profile fixture", "ground_truth": {"items": []}},
    ).json()
    response = client.post(
        f"{BASE}/evaluations",
        json={
            "name": "selected profile",
            "sast_run_id": run_id,
            "dataset_id": dataset["id"],
            "match_mode": "assisted",
            "llm_profile_id": profile.id,
        },
    )
    assert response.status_code == 201, response.text
    evaluation = response.json()
    assert json.loads(evaluation["policy_json"])["llm_profile_id"] == profile.id
    result = client.post(f"{BASE}/evaluations/{evaluation['id']}/run")
    assert result.status_code == 200, result.text
    assert used_models == ["test-lead-model"]


def test_benchmark_rejects_non_terminal_sast_run(client, db_engine):
    with Session(db_engine) as session:
        run = SastRun(name="active", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    dataset = client.post(
        f"{BASE}/datasets",
        json={"name": "fixture", "ground_truth": {"items": []}},
    )
    response = client.post(
        f"{BASE}/evaluations",
        json={
            "name": "invalid",
            "sast_run_id": run_id,
            "dataset_id": dataset.json()["id"],
        },
    )
    assert response.status_code == 409


def test_benchmark_marks_answer_key_inside_source_as_contaminated(
    client, db_engine, tmp_path, monkeypatch
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
    _stub_legacy_evaluator(db_engine, run_id, monkeypatch)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "fixture",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    evaluation = client.post(
        f"{BASE}/evaluations",
        json={
            "name": "blindness audit",
            "sast_run_id": run_id,
            "dataset_id": dataset["id"],
            "match_mode": "assisted",
        },
    ).json()
    result = client.post(f"{BASE}/evaluations/{evaluation['id']}/run").json()
    assert result["blindness_status"] == "contaminated"
    assert json.loads(result["metrics_json"])["aggregate_eligible"] is False


def test_benchmark_comparison_reports_range_frequency_and_thresholds(
    client, db_engine, monkeypatch
):
    run_id = _completed_run(db_engine)
    _stub_legacy_evaluator(db_engine, run_id, monkeypatch)
    dataset = client.post(
        f"{BASE}/datasets",
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
            f"{BASE}/evaluations",
            json={
                "name": f"repeat {number}",
                "sast_run_id": run_id,
                "dataset_id": dataset["id"],
                "match_mode": "assisted",
            },
        ).json()
        completed = client.post(f"{BASE}/evaluations/{evaluation['id']}/run").json()
        evaluation_ids.append(completed["id"])
    response = client.post(
        f"{BASE}/comparisons",
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


@pytest.mark.parametrize("kind", ["site", "api", "sast"])
def test_bulk_completed_benchmarks_skip_existing_and_retry_failures(
    client, db_engine, monkeypatch, kind
):
    with Session(db_engine) as session:
        model = LLMConfig(name="Bulk evaluator", model="test-model")
        session.add(model)
        target = None
        if kind != "sast":
            target = (
                Site(name="Bulk site", base_url="https://example.test")
                if kind == "site"
                else ApiCollection(name="Bulk API", base_url="https://example.test")
            )
            session.add(target)
        session.commit()
        model_id = model.id

        def make_run(name, status):
            if kind == "site":
                return TestRun(
                    site_id=target.id, name=name, status=status, llm_config_id=model_id
                )
            if kind == "api":
                return ApiTestRun(
                    collection_id=target.id,
                    name=name,
                    status=status,
                    llm_config_id=model_id,
                )
            return SastRun(name=name, status=status, llm_config_id=model_id)

        done = "complete" if kind == "site" else "completed"
        runs = [
            make_run("First scan", done),
            make_run("Second scan", done),
            make_run("Unselected scan", done),
            make_run("Unfinished scan", "running"),
        ]
        session.add_all(runs)
        session.commit()
        run_ids = [run.id for run in runs[:2]]
        unselected_id = runs[2].id
        unfinished_id = runs[3].id
    calls = []
    fail = True
    started = asyncio.Event()

    async def answer(*args, **kwargs):
        calls.append(args)
        call_number = len(calls)
        if fail:
            if call_number == 2:
                started.set()
            await asyncio.wait_for(started.wait(), timeout=2)
        if fail and call_number == 1:
            raise ValueError("fixture model failure")
        return json.dumps(
            {
                "decisions": [
                    {
                        "ground_truth_external_id": "GT-1",
                        "disposition": "missing",
                        "finding_ids": [],
                        "reason": "No findings",
                    }
                ]
            }
        )

    monkeypatch.setattr("aespa.services.llm.plain_completion", answer)
    dataset = client.post(
        f"{BASE}/datasets",
        json={
            "name": "Bulk truth",
            "ground_truth": {
                "items": [{"external_id": "GT-1", "title": "SQL injection"}]
            },
        },
    ).json()
    assert client.get(f"{BASE}/settings").json() == {"default_model_id": None}
    assert (
        client.put(f"{BASE}/settings", json={"default_model_id": 999999}).status_code
        == 404
    )
    assert (
        client.put(f"{BASE}/settings", json={"default_model_id": model_id}).status_code
        == 200
    )
    assert client.get(f"{BASE}/settings").json() == {"default_model_id": model_id}
    body = {
        "evaluation_model_id": 999999,
        "run_kind": kind,
        "dataset_id": dataset["id"],
        "run_ids": run_ids,
    }
    for invalid_ids in ([unfinished_id], [999999], [run_ids[0], unfinished_id]):
        invalid = client.post(
            f"{BASE}/results/benchmark-unbenchmarked",
            json={**body, "run_ids": invalid_ids},
        )
        assert invalid.status_code == 400
    for invalid_ids in ([], [0], [-1]):
        invalid = client.post(
            f"{BASE}/results/benchmark-unbenchmarked",
            json={**body, "run_ids": invalid_ids},
        )
        assert invalid.status_code == 422
    missing = client.post(
        f"{BASE}/results/benchmark-unbenchmarked",
        json={"run_kind": kind, "dataset_id": dataset["id"]},
    )
    assert missing.status_code == 422
    assert calls == []
    response = client.post(f"{BASE}/results/benchmark-unbenchmarked", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["completed"]) == 1
    assert len(result["failures"]) == 1
    assert set(
        result["completed"] + [item["run_id"] for item in result["failures"]]
    ) == set(run_ids)
    assert len(client.get(f"{BASE}/results").json()) == 1
    fail = False
    retry = client.post(f"{BASE}/results/benchmark-unbenchmarked", json=body).json()
    assert retry["completed"] == [result["failures"][0]["run_id"]]
    assert retry["skipped"] == result["completed"]
    assert retry["failures"] == []
    assert len(client.get(f"{BASE}/results").json()) == 2
    skipped = client.post(f"{BASE}/results/benchmark-unbenchmarked", json=body).json()
    assert set(skipped["skipped"]) == set(run_ids)
    assert skipped["completed"] == []
    assert all(call[0].id == model_id for call in calls)
    assert len(calls) == 3
    assert unselected_id not in {
        item["run_id"] for item in client.get(f"{BASE}/results").json()
    }
    duplicate = client.post(
        f"{BASE}/results/benchmark-unbenchmarked",
        json={**body, "run_ids": [unselected_id, unselected_id]},
    ).json()
    assert duplicate["completed"] == [unselected_id]
    assert len(calls) == 4


def test_manage_dataset_labels_assignments_and_delete(client, db_engine):
    with Session(db_engine) as session:
        site = Site(name="App", base_url="http://app.test")
        api = ApiCollection(name="API", base_url="http://api.test")
        session.add_all([site, api])
        session.commit()
        site_id, api_id = site.id, api.id
    dataset = client.post(
        f"{BASE}/datasets", json={"name": "truth.json", "ground_truth": {"items": []}}
    ).json()
    dataset_id = dataset["id"]
    original_digest = dataset["ground_truth_digest"]
    url = f"{BASE}/datasets/{dataset_id}/details"
    response = client.patch(
        url, json={"label": " Bank of Ed ", "target_kind": "site", "target_id": site_id}
    )
    assert response.status_code == 200, response.text
    assert response.json()["label"] == "Bank of Ed"
    saved = client.get(f"{BASE}/datasets").json()[0]
    assert saved["name"] == "truth.json"
    assert saved["ground_truth_digest"] == original_digest
    assert saved["assignments"] == [{"target_kind": "site", "target_id": site_id}]
    assert (
        client.patch(url, json={"target_kind": "api", "target_id": 99999}).status_code
        == 404
    )
    assert client.patch(url, json={"target_kind": "api"}).status_code == 422
    response = client.patch(
        url, json={"label": "API truth", "target_kind": "api", "target_id": api_id}
    )
    assert response.status_code == 200
    targets = client.get(f"{BASE}/targets").json()
    assert targets["sites"][0]["dataset"] is None
    assert targets["apis"][0]["dataset"]["id"] == dataset_id
    assert client.delete(f"{BASE}/datasets/{dataset_id}").status_code == 204
    assert client.get(f"{BASE}/datasets").json() == []
    assert client.get(f"{BASE}/targets").json()["apis"][0]["dataset"] is None


def test_dataset_assignment_replaces_target_dataset(client, db_engine):
    with Session(db_engine) as session:
        site = Site(name="App", base_url="http://app.test")
        session.add(site)
        session.commit()
        site_id = site.id
    ids = [
        client.post(
            f"{BASE}/datasets", json={"name": name, "ground_truth": {"items": []}}
        ).json()["id"]
        for name in ("first.json", "second.json")
    ]
    for dataset_id in ids:
        assert (
            client.patch(
                f"{BASE}/datasets/{dataset_id}/details",
                json={"target_kind": "site", "target_id": site_id},
            ).status_code
            == 200
        )
    saved = {row["id"]: row for row in client.get(f"{BASE}/datasets").json()}
    assert saved[ids[0]]["assignments"] == []
    assert saved[ids[1]]["assignments"] == [
        {"target_kind": "site", "target_id": site_id}
    ]
    assert (
        client.patch(
            f"{BASE}/datasets/{ids[1]}/details", json={"label": "Custom"}
        ).status_code
        == 200
    )
    assert client.get(f"{BASE}/targets").json()["sites"][0]["dataset"] is None


@pytest.mark.parametrize("run_class", [TestRun, ApiTestRun, SastRun])
@pytest.mark.parametrize(
    "usage, expected",
    [
        (
            {
                "lead": {"input": 100, "output": 1},
                "worker": {"input": 20, "output": 200},
            },
            "worker",
        ),
        (
            {
                "lead": {"input": 100, "output": 1, "cache_read": 1000},
                "worker": {"input": 102},
            },
            "worker",
        ),
        ({"z-model": {"input": 10}, "a-model": {"output": 10}}, "a-model"),
        ({"lead": {"input": 0, "output": 0}}, None),
        ({"bad": {"input": "100"}, "broken": [], "valid": {"output": 10}}, "valid"),
        ([], None),
        (None, None),
    ],
)
def test_scan_model_uses_recorded_total_tokens(run_class, usage, expected):
    router = importlib.import_module("aespa_external_aespa_benchmarking.router")
    run = run_class(token_usage_json=json.dumps(usage), llm_config_id=999)
    selected = router.usage_model(run)
    assert (selected["model"] if selected else None) == expected


@pytest.mark.parametrize("kind", ["site", "api", "sast"])
@pytest.mark.parametrize("saved_date", [{}, {"scan_started_at": None}])
def test_older_saved_metadata_is_read_from_run(db_engine, kind, saved_date):
    router = importlib.import_module("aespa_external_aespa_benchmarking.router")
    with Session(db_engine) as core:
        model = {"site": TestRun, "api": ApiTestRun, "sast": SastRun}[kind]
        target_fields = {}
        if kind != "sast":
            target_class = Site if kind == "site" else ApiCollection
            target = target_class(name="Older target", base_url="https://example.test")
            core.add(target)
            core.commit()
            target_fields["site_id" if kind == "site" else "collection_id"] = target.id
        run = model(
            **target_fields,
            name="Older scan",
            created_at=datetime(2026, 9, 30, 7, 0, tzinfo=timezone.utc),
            token_usage_json=json.dumps({"most-used": {"input": 10, "output": 20}}),
        )
        core.add(run)
        core.commit()
        row = router.ScanResult(
            run_kind=kind,
            run_id=run.id,
            run_name=run.name,
            rows_json=json.dumps(
                {
                    **saved_date,
                    "rows": [],
                    "scan_models": {"test_lead": {"model": "old-profile"}, "sast": []},
                }
            ),
        )
        original = row.rows_json
        assert (
            router.result_out(row, core)["scan_models"]["primary"]["model"]
            == "most-used"
        )
        assert (
            router.result_out(row, core)["scan_started_at"]
            == "2026-09-30T07:00:00+00:00"
        )
        assert run.started_at is None
        assert row.rows_json == original
