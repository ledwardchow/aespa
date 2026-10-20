from __future__ import annotations

import importlib
import json
from types import SimpleNamespace

import certifi
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from aespa.models import LLMPriceCatalog, SastRun, Site, TestRun, UpstreamProxyConfig
from tests import test_benchmark_transfer as transfer_tests
from tests.test_benchmark_lab import enabled_benchmarking  # noqa: F401
from tests.test_benchmark_transfer import seed

UPLOAD_TOKEN = "aespa_upload_" + "a" * 64
portable = transfer_tests.portable


def modules():
    return importlib.import_module("aespa_external_aespa_benchmarking.publishing")


def test_published_model_includes_daybreak_when_recorded():
    summary = modules().model_summary(
        {
            "model": "gpt-6-sol",
            "provider": "openai_codex",
            "daybreak_programs": ["daybreak_red", "daybreak_blue"],
        },
        include_daybreak=True,
    )
    assert summary["daybreak_programs"] == ["daybreak_blue", "daybreak_red"]
    assert "daybreak_programs" not in modules().model_summary({"model": "unknown"})


def test_graph_export_keeps_only_summary_and_stable_identity(portable):
    models, _, stores = portable
    seed(models, stores[0])
    one = modules().graph_bundle(stores[0])
    two = modules().graph_bundle(stores[0])
    assert one == two
    result = one["results"][0]
    assert result["summary"] == {"full": 1, "partial": 0, "missing": 0}
    assert result["score"] is None
    assert result["category_counts"] is None
    assert result["category_totals"] is None
    assert result["scan_cost_usd"] == 0.42
    assert result["scan_started_at"] is None
    assert result["primary"] == {"model": "scanner", "name": None, "provider": None}
    assert result["scan_type"] == "DAST"
    assert result["tokens"] is None
    assert result["comment"] == ""
    assert "run_name" not in result
    assert result["sast"] == []
    assert len(result["dataset"]["key"]) == 64
    serialized = json.dumps(one)
    assert "saved proof" not in serialized
    assert "SQL injection" not in serialized
    assert "ground_truth" not in result
    assert "findings" not in result


def test_publish_prices_fast_calls_at_normal_rates_and_preserves_comment(
    portable, db_engine
):
    models, _, stores = portable
    seed(models, stores[0])
    with Session(db_engine) as core:
        core.add(Site(name="Bank", base_url="https://bank.test"))
        core.add(
            LLMPriceCatalog(
                provider="openai_chatgpt_plan",
                model="test-model",
                input_price_usd_per_million=1,
            )
        )
        core.commit()
        run = TestRun(
            site_id=1,
            name="Scan",
            token_usage_json=json.dumps(
                {
                    "test-model": {
                        "provider": "openai_chatgpt_plan",
                        "input": 3_000_000,
                        "estimated_cost_available": True,
                        "estimated_total_cost_usd": 3,
                    },
                    "test-model#fast": {
                        "provider": "openai_chatgpt_plan",
                        "model": "test-model",
                        "service_tier": "fast",
                        "input": 1_000_000,
                        "estimated_cost_available": True,
                        "estimated_total_cost_usd": 2,
                    },
                }
            ),
        )
        sast = SastRun(
            name="Source scan",
            token_usage_json=json.dumps(
                {
                    "test-model#fast": {
                        "provider": "openai_chatgpt_plan",
                        "model": "test-model",
                        "service_tier": "fast",
                        "input": 1_000_000,
                        "estimated_cost_available": True,
                        "estimated_total_cost_usd": 4,
                    }
                }
            ),
        )
        core.add_all([run, sast])
        core.commit()
        run_id, sast_id = run.id, sast.id
    with stores[0].session() as session:
        row = session.exec(select(models.ScanResult)).one()
        row.run_id = run_id
        saved = json.loads(row.rows_json)
        saved["scan_models"]["sast"] = [{"run_id": sast_id}]
        saved["scan_cost_usd"] = 9
        saved["scan_cost_breakdown"] = {"complete": True}
        saved["comment"] = "Reviewed by Alice."
        row.rows_json = json.dumps(saved)
        session.add(row)
        session.commit()

    first = modules().graph_bundle(stores[0])["results"][0]
    second = modules().graph_bundle(stores[0])["results"][0]
    assert first == second
    assert first["scan_cost_usd"] == 5
    assert first["comment"] == (
        "Reviewed by Alice.\n\nRun used Fast mode. Estimated scan cost with Fast mode: "
        "$9.00000000. Published scan cost uses Normal mode pricing."
    )
    assert first["comment"].count("Run used Fast mode") == 1


def test_matched_score_weights_full_and_partial_matches():
    result = {
        "ground_truth": {
            "items": [
                {
                    "external_id": str(index),
                    "severity": severity,
                    "category": "A01: Broken Access Control"
                    if index < 3
                    else "A03: Injection",
                }
                for index, severity in enumerate(
                    ("informational", "low", "medium", "high", "critical")
                )
            ]
        },
        "rows": [
            {"external_id": str(index), "disposition": disposition}
            for index, disposition in enumerate(
                ("full", "partial", "full", "partial", "missing")
            )
        ],
    }
    scoring = importlib.import_module("aespa_external_aespa_benchmarking.scoring")
    assert scoring.matched_score(result["ground_truth"], result["rows"]) == 9
    assert scoring.matched_categories(result["ground_truth"], result["rows"]) == {
        "A01: Broken Access Control": 3,
        "A03: Injection": 1,
    }
    assert scoring.ground_truth_category_totals(result["ground_truth"]) == {
        "A01: Broken Access Control": 3,
        "A03: Injection": 2,
    }
    result["rows"][4]["disposition"] = "full"
    assert scoring.matched_score(result["ground_truth"], result["rows"]) == 17
    assert (
        scoring.matched_categories(result["ground_truth"], result["rows"])[
            "A03: Injection"
        ]
        == 2
    )
    result["ground_truth"]["items"][4]["severity"] = "unknown"
    assert scoring.matched_score(result["ground_truth"], result["rows"]) is None


def test_matched_score_doubles_only_high_and_critical_in_selected_categories():
    scoring = importlib.import_module("aespa_external_aespa_benchmarking.scoring")
    items = [
        {"external_id": str(index), "severity": severity, "category": category}
        for index, (severity, category) in enumerate(
            [
                ("high", "A01: Broken Access Control"),
                ("high", "A03: Injection"),
                ("critical", "A04: Insecure Design"),
                ("critical", "A07: Authentication"),
                ("high", "A02: Cryptographic Failures"),
                ("low", "A01: Broken Access Control"),
                ("high", "A01-other"),
            ]
        )
    ]
    rows = [{"external_id": str(index), "disposition": "partial"} for index in range(7)]
    assert scoring.matched_score({"items": items}, rows) == 35


def test_published_tokens_include_linked_sast_run_without_names():
    publishing = modules()
    row = SimpleNamespace(run_kind="site", run_id=1)
    run = SimpleNamespace(
        token_usage_json=json.dumps(
            {
                "scanner": {
                    "input": 120,
                    "output": 30,
                    "cache_read": 40,
                    "cache_write": 10,
                }
            }
        )
    )
    source = SimpleNamespace(
        token_usage_json=json.dumps(
            {"sast": {"input": 50, "output": 20, "cache_read": 5, "cache_write": 0}}
        )
    )

    class Core:
        def get(self, model, run_id):
            return (
                run if model.__name__ == "TestRun" else source if run_id == 2 else None
            )

    assert publishing.token_counts(
        Core(), row, {"sast": [{"run_id": 2, "run_name": "Private source"}]}
    ) == {"input": 170, "output": 50, "cache_read": 45, "cache_write": 10}


@pytest.mark.parametrize(
    "value",
    [
        "http://example.chatgpt.site",
        "https://example.com",
        "https://a.chatgpt.site.example.com",
        "https://a.chatgpt.site/path",
        "https://user:pass@a.chatgpt.site",
        "https://a.chatgpt.site?x=1",
        "http://benchmarks.aespa.app",
        "https://benchmarks.aespa.app.evil.example",
        "https://benchmarks.aespa.app/path",
    ],
)
def test_publishing_rejects_unrelated_destinations(value):
    with pytest.raises(ValueError):
        modules().site_url(value)


def test_benchmark_domain_reuses_native_site_token(portable, db_engine, monkeypatch):
    models, _, stores = portable
    seed(models, stores[0])
    publishing = modules()
    app = FastAPI()
    from fastapi import APIRouter

    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)
    calls = []

    async def fake_post(self, url, **kwargs):
        calls.append((url, kwargs["headers"]))
        return httpx.Response(
            200, json={"received": 1, "stored": 1, "skipped_stale": 0}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    native = "https://aespa-benchmarks.maranthis.chatgpt.site"
    custom = "https://benchmarks.aespa.app"
    token = publishing.connection_token(native, "service-secret", UPLOAD_TOKEN)
    with TestClient(app) as client:
        assert client.get("/publishing").json()["site_url"] == custom
        assert (
            client.put(
                "/publishing", json={"site_url": custom, "token": token}
            ).status_code
            == 200
        )
        assert client.get("/publishing").json()["site_url"] == custom
        assert publishing.decode_connection_token(
            client.post("/publishing/token").json()["token"], native
        ) == ("service-secret", UPLOAD_TOKEN)
        assert client.put("/publishing", json={"site_url": native}).status_code == 200
        assert client.put("/publishing", json={"site_url": custom}).status_code == 200
        assert client.post("/publish").status_code == 200
        assert calls[0][0] == f"{custom}/api/v1/results"
        assert calls[0][1]["OAI-Sites-Authorization"] == "Bearer service-secret"
        assert calls[0][1]["X-AESPA-Upload-Token"] == UPLOAD_TOKEN
        assert (
            client.put(
                "/publishing", json={"site_url": "https://other.chatgpt.site"}
            ).status_code
            == 422
        )
        assert publishing.decode_connection_token(
            publishing.connection_token(custom, "service-secret", UPLOAD_TOKEN), native
        ) == ("service-secret", UPLOAD_TOKEN)


def test_publish_sends_service_header_and_masks_saved_token(
    portable, db_engine, monkeypatch, fake_ssl_context
):
    models, _, stores = portable
    seed(models, stores[0])
    publishing = modules()
    app = FastAPI()
    from fastapi import APIRouter

    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)
    called = []
    client_options = []
    with Session(db_engine) as session:
        session.add(
            UpstreamProxyConfig(
                id=1,
                llm_proxy_url="http://company-proxy.local:8080",
                proxy_llm=True,
                llm_ca_bundle_path=certifi.where(),
            )
        )
        session.commit()

    original_init = httpx.AsyncClient.__init__

    def capture_client_options(self, *args, **kwargs):
        client_options.append(kwargs)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", capture_client_options)

    async def fake_post(self, url, **kwargs):
        called.append((url, kwargs))
        return httpx.Response(
            200, json={"received": 1, "stored": 1, "skipped_stale": 0}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with TestClient(app) as client:
        assert (
            client.put(
                "/publishing",
                json={
                    "site_url": "https://a.chatgpt.site",
                    "service_token": "secret-value",
                    "upload_token": UPLOAD_TOKEN,
                },
            ).status_code
            == 200
        )
        read = client.get("/publishing")
        assert read.json() == {
            "site_url": "https://a.chatgpt.site",
            "token_saved": True,
            "upload_token_saved": True,
        }
        assert "secret-value" not in read.text
        assert UPLOAD_TOKEN not in read.text
        assert (
            client.put(
                "/publishing", json={"site_url": "https://b.chatgpt.site"}
            ).status_code
            == 422
        )
        assert client.post("/publish").json()["stored"] == 1
    assert called[0][0] == "https://a.chatgpt.site/api/v1/results"
    assert client_options[-1]["proxy"] == "http://company-proxy.local:8080"
    assert client_options[-1]["verify"] == fake_ssl_context(certifi.where())
    assert client_options[-1]["trust_env"] is False
    assert called[0][1]["headers"]["OAI-Sites-Authorization"] == "Bearer secret-value"
    assert called[0][1]["headers"]["X-AESPA-Upload-Token"] == UPLOAD_TOKEN
    assert "saved proof" not in called[0][1]["content"].decode()
    assert "run_name" not in called[0][1]["content"].decode()
    assert "tokens" in called[0][1]["content"].decode()


def test_publish_sends_only_selected_ground_truths(portable, monkeypatch):
    models, _, stores = portable
    seed(models, stores[0], name="First")
    seed(models, stores[0], name="Second")
    with stores[0].session() as session:
        first, second = [
            row.id
            for row in session.exec(select(models.Dataset).order_by(models.Dataset.id))
        ]
    publishing = modules()
    every = publishing.graph_bundle(stores[0])["results"]
    keys = {
        row["dataset"]["key"]
        for row in publishing.graph_bundle(stores[0], {second})["results"]
    }
    assert len(every) == 2 and len(keys) == 1
    app = FastAPI()
    from fastapi import APIRouter

    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)
    sent = []

    async def fake_post(self, url, **kwargs):
        batch = json.loads(kwargs["content"])["results"]
        sent.extend(batch)
        return httpx.Response(
            200,
            json={"received": len(batch), "stored": len(batch), "skipped_stale": 0},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with TestClient(app) as client:
        client.put(
            "/publishing",
            json={
                "site_url": "https://a.chatgpt.site",
                "service_token": "secret-value",
                "upload_token": UPLOAD_TOKEN,
            },
        )
        response = client.post("/publish", json={"dataset_ids": [second]})
        assert response.json()["received"] == 1
        assert {row["dataset"]["key"] for row in sent} == keys
        assert client.post("/publish", json={"dataset_ids": []}).status_code == 422
        assert (
            client.post("/publish", json={"dataset_ids": [first, 9999]}).status_code
            == 422
        )
    assert len(sent) == 1


def test_failed_publish_does_not_leak_response_or_credential(portable, monkeypatch):
    models, _, stores = portable
    seed(models, stores[0])
    publishing = modules()
    app = FastAPI()
    from fastapi import APIRouter

    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)

    async def fake_post(self, url, **kwargs):
        return httpx.Response(403, text="secret-value")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with TestClient(app) as client:
        client.put(
            "/publishing",
            json={
                "site_url": "https://a.chatgpt.site",
                "service_token": "secret-value",
                "upload_token": UPLOAD_TOKEN,
            },
        )
        response = client.post("/publish")
        assert response.status_code == 502
        assert "secret-value" not in response.text


def test_reveal_token_is_explicit_and_not_cached(portable):
    _, _, stores = portable
    publishing = modules()
    app = FastAPI()
    from fastapi import APIRouter

    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)
    with TestClient(app) as client:
        assert client.post("/publishing/token").status_code == 404
        client.put(
            "/publishing",
            json={
                "site_url": "https://a.chatgpt.site",
                "service_token": "fixture-secret",
                "upload_token": UPLOAD_TOKEN,
            },
        )
        assert "fixture-secret" not in client.get("/publishing").text
        response = client.post("/publishing/token")
        assert publishing.decode_connection_token(
            response.json()["token"], "https://a.chatgpt.site"
        ) == ("fixture-secret", UPLOAD_TOKEN)
        assert response.headers["cache-control"] == "no-store"
        # A new settings page and a blank update keep the stored token.
        assert (
            client.put(
                "/publishing", json={"site_url": "https://a.chatgpt.site"}
            ).status_code
            == 200
        )
        assert publishing.decode_connection_token(
            client.post("/publishing/token").json()["token"], "https://a.chatgpt.site"
        ) == ("fixture-secret", UPLOAD_TOKEN)


def test_upload_token_required_and_not_reused_for_another_site(portable):
    models, _, stores = portable
    from fastapi import APIRouter

    publishing = modules()
    app = FastAPI()
    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)
    # Existing installations retain the service credential but need an upload token.
    with stores[0].session() as session:
        session.add(
            models.PublishingSettings(
                site_url="https://a.chatgpt.site", service_token="service-secret"
            )
        )
        session.commit()
    with TestClient(app) as client:
        assert client.get("/publishing").json()["upload_token_saved"] is False
        assert client.post("/publish").status_code == 422
        for token in ("", "invalid", "aespa_upload_" + "z" * 64):
            response = client.put(
                "/publishing",
                json={"site_url": "https://a.chatgpt.site", "upload_token": token},
            )
            assert response.status_code == 422
        assert (
            client.put(
                "/publishing",
                json={
                    "site_url": "https://a.chatgpt.site",
                    "upload_token": UPLOAD_TOKEN,
                },
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/publishing",
                json={
                    "site_url": "https://b.chatgpt.site",
                    "service_token": "new-service",
                },
            ).status_code
            == 422
        )
        # A rejected change must not overwrite either saved credential.
        assert publishing.decode_connection_token(
            client.post("/publishing/token").json()["token"], "https://a.chatgpt.site"
        ) == ("service-secret", UPLOAD_TOKEN)
        assert UPLOAD_TOKEN not in client.get("/graph-export").text
        assert (
            client.put(
                "/publishing",
                json={
                    "site_url": "https://b.chatgpt.site",
                    "service_token": "new-service",
                    "upload_token": "aespa_upload_" + "b" * 64,
                },
            ).status_code
            == 200
        )


def test_single_token_saves_and_sends_both_credentials(portable, monkeypatch):
    models, _, stores = portable
    seed(models, stores[0])
    from fastapi import APIRouter

    publishing = modules()
    app = FastAPI()
    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)
    called = []

    async def fake_post(self, url, **kwargs):
        called.append(kwargs)
        return httpx.Response(
            200, json={"received": 1, "stored": 1, "skipped_stale": 0}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    token = publishing.connection_token(
        "https://a.chatgpt.site", "service-secret", UPLOAD_TOKEN
    )
    with TestClient(app) as client:
        assert (
            client.put(
                "/publishing",
                json={"site_url": "https://a.chatgpt.site", "token": token},
            ).status_code
            == 200
        )
        assert token not in client.get("/publishing").text
        assert client.post("/publishing/token").json() == {"token": token}
        assert client.post("/publish").status_code == 200
        assert (
            called[0]["headers"]["OAI-Sites-Authorization"] == "Bearer service-secret"
        )
        assert called[0]["headers"]["X-AESPA-Upload-Token"] == UPLOAD_TOKEN
        response = client.put(
            "/publishing", json={"site_url": "https://b.chatgpt.site", "token": token}
        )
        assert response.status_code == 422
        assert token not in response.text
        assert client.post("/publishing/token").json() == {"token": token}
        assert (
            client.put(
                "/publishing",
                json={
                    "site_url": "https://a.chatgpt.site",
                    "token": token,
                    "service_token": "conflict",
                },
            ).status_code
            == 422
        )


def test_publish_reports_site_edited_results(portable, monkeypatch):
    models, _, stores = portable
    seed(models, stores[0])
    from fastapi import APIRouter

    publishing = modules()
    app = FastAPI()
    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)

    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "received": 1,
                "stored": 0,
                "skipped_stale": 0,
                "skipped_site_edits": 1,
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    token = publishing.connection_token(
        "https://benchmarks.aespa.app", "service-secret", UPLOAD_TOKEN
    )
    with TestClient(app) as client:
        assert (
            client.put(
                "/publishing",
                json={"site_url": "https://benchmarks.aespa.app", "token": token},
            ).status_code
            == 200
        )
        report = client.post("/publish")
        assert report.status_code == 200
        assert report.json()["skipped_site_edits"] == 1
        assert report.json()["skipped_stale"] == 0


def test_publish_reports_locked_results(portable, monkeypatch):
    models, _, stores = portable
    seed(models, stores[0])
    from fastapi import APIRouter

    publishing = modules()
    app = FastAPI()
    router = APIRouter()
    publishing.register_publishing(router, stores[0])
    app.include_router(router)

    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "received": 1,
                "stored": 0,
                "skipped_stale": 0,
                "skipped_site_edits": 0,
                "skipped_locked": 1,
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    token = publishing.connection_token(
        "https://benchmarks.aespa.app", "service-secret", UPLOAD_TOKEN
    )
    with TestClient(app) as client:
        assert (
            client.put(
                "/publishing",
                json={"site_url": "https://benchmarks.aespa.app", "token": token},
            ).status_code
            == 200
        )
        report = client.post("/publish")
        assert report.status_code == 200
        assert report.json()["skipped_locked"] == 1
        assert report.json()["received"] == 1


@pytest.mark.parametrize(
    "value",
    [
        "",
        "raw-service",
        "aespa_publish_v1_!!!!",
        "aespa_publish_v1_e30",
        "aespa_publish_v1_" + "a" * 33000,
    ],
)
def test_rejects_malformed_single_tokens(value):
    with pytest.raises(ValueError):
        modules().decode_connection_token(value, "https://a.chatgpt.site")
