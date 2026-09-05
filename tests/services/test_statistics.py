import json
from datetime import datetime, timezone

from sqlmodel import Session

from aespa.models import LLMConfig, LLMPriceCatalog, LLMUsageMonth, Site, TestRun
from aespa.services import llm, statistics


def test_records_all_calls_without_run_context(isolated_db_engine, monkeypatch):
    monkeypatch.setattr(statistics, "local_month", lambda: "2026-08")
    llm._record_usage(
        "gpt-test",
        1000,
        200,
        cache_read_tokens=300,
        provider="openai",
        base_url="https://api.openai.com/v1",
    )
    with Session(isolated_db_engine) as session:
        row = session.query(LLMUsageMonth).one()
        assert row.input_tokens == 700
        assert row.output_tokens == 200
        assert row.cache_read_tokens == 300
        assert row.base_url == "https://api.openai.com/v1"
        assert row.requests == 1


def test_provider_specific_cache_normalization_contract():
    feed = {
        "gpt-test": {
            "input_cost_per_token": 0.000001,
            "output_cost_per_token": 0.000002,
        }
    }
    assert (
        statistics.resolve_price("openai", "gpt-test", feed)[
            "input_price_usd_per_million"
        ]
        == 1
    )
    # Bedrock and Anthropic report uncached input separately; their adapters
    # therefore pass the raw input value through to the ledger.
    assert statistics.local_month(datetime(2026, 8, 1, tzinfo=timezone.utc))


def test_codex_daybreak_uses_official_gpt_5_6_sol_prices(isolated_db_engine):
    rates = statistics.record_usage(
        "openai_codex",
        "gpt-daybreak-blue-latest",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
        month="2026-08",
    )

    assert rates["input_price_usd_per_million"] == 4
    assert rates["output_price_usd_per_million"] == 20
    assert rates["cache_read_price_usd_per_million"] == 0.4
    assert rates["cache_write_price_usd_per_million"] == 5
    assert rates["price_source"].endswith("/gpt-5.6-sol")
    assert rates["price_confidence"] == "alias"


def test_codex_known_models_use_their_official_openai_prices(isolated_db_engine):
    rates = statistics.record_usage(
        "openai_codex",
        "gpt-5.6-terra",
        input_tokens=1,
        month="2026-08",
    )

    assert rates["input_price_usd_per_million"] == 2
    assert rates["output_price_usd_per_million"] == 12
    assert rates["cache_read_price_usd_per_million"] == 0.2
    assert rates["cache_write_price_usd_per_million"] == 2.5
    assert rates["price_confidence"] == "exact"


def test_codex_run_counter_uses_official_api_equivalent_cost(isolated_db_engine):
    run_id = 991000
    key = ("web", run_id)
    llm.set_run_context(run_id, emit_fn=None)
    try:
        llm._record_usage(
            "gpt-daybreak-blue-latest",
            input_tokens=3_000_000,
            output_tokens=1_000_000,
            cache_read_tokens=1_000_000,
            cache_write_tokens=1_000_000,
            provider="openai_codex",
        )
        usage = llm.get_run_token_usage(run_id)
    finally:
        llm.clear_run_context()
        llm._run_token_usage.pop(key, None)
        llm._run_token_seeded.discard(key)

    assert usage["estimated_cost_available"] is True
    assert usage["estimated_total_cost_usd"] == 29.4


def test_openrouter_compatible_profile_is_labelled_openrouter():
    config = LLMConfig(
        provider="openai",
        base_url="https://openrouter.ai/api/v1",
        model="minimax/minimax-m2",
    )
    assert llm._usage_provider(config) == "openrouter"
    assert llm._usage_base_url(config) == "https://openrouter.ai/api/v1"


def test_bedrock_input_is_not_subtracted(isolated_db_engine):
    statistics.record_usage(
        "bedrock",
        "anthropic.claude-test",
        input_tokens=1000,
        cache_read_tokens=300,
        cache_write_tokens=100,
        month="2026-08",
    )
    with Session(isolated_db_engine) as session:
        row = session.query(LLMUsageMonth).one()
        assert row.input_tokens == 1000


def test_usage_keeps_first_observed_base_url(isolated_db_engine):
    statistics.record_usage(
        "openai_compatible",
        "test-model",
        base_url="https://first.example/v1",
        month="2026-08",
    )
    statistics.record_usage(
        "openai_compatible",
        "test-model",
        base_url="https://changed.example/v1",
        month="2026-08",
    )
    with Session(isolated_db_engine) as session:
        row = session.query(LLMUsageMonth).one()
        assert row.base_url == "https://first.example/v1"


def test_monthly_price_override_and_reset_keep_catalog(isolated_db_engine):
    statistics.record_usage(
        "factory_droid", "test-model", factory_credits=1_000_000, month="2026-08"
    )
    with Session(isolated_db_engine) as session:
        statistics.set_prices(
            session,
            {
                "month": "2026-08",
                "provider": "factory_droid",
                "model": "test-model",
                "credit_price_usd_per_million": 9,
                "credit_unit": "Factory credits per 1M",
                "apply_to_future": True,
            },
        )
        assert session.query(LLMPriceCatalog).one().credit_price_usd_per_million == 9
        statistics.reset_statistics(session)
        assert session.query(LLMUsageMonth).count() == 0
        assert session.query(LLMPriceCatalog).count() == 1


def test_statistics_api_is_independent_and_reset_is_explicit(client):
    statistics.record_usage(
        "anthropic", "claude-test", input_tokens=12, month="2026-08"
    )
    response = client.get("/api/statistics/llm?month=2026-08")
    assert response.status_code == 200
    assert response.json()["totals"]["input_tokens"] == 12
    reset = client.delete("/api/statistics/llm")
    assert reset.status_code == 200
    assert client.get("/api/statistics/llm?month=2026-08").json()["rows"] == []


def test_statistics_api_includes_lifetime_cost(client):
    statistics.record_usage(
        "factory_droid", "droid-test", factory_credits=1_000_000, month="2026-07"
    )
    statistics.record_usage(
        "factory_droid", "droid-test", factory_credits=500_000, month="2026-08"
    )
    lifetime = client.get("/api/statistics/llm?month=2026-08").json()["lifetime"]
    assert lifetime["months"] == 2
    assert lifetime["factory_credits"] == 1_500_000
    assert lifetime["estimated_total_cost_usd"] == 10.5


def test_missing_prices_count_as_zero_in_monthly_and_lifetime_costs(
    client, isolated_db_engine
):
    statistics.record_usage(
        "openai",
        "priced-model",
        input_tokens=1_000_000,
        month="2026-08",
    )
    statistics.record_usage(
        "openai",
        "unpriced-model",
        input_tokens=1_000_000,
        month="2026-08",
    )
    with Session(isolated_db_engine) as session:
        statistics.set_prices(
            session,
            {
                "month": "2026-08",
                "provider": "openai",
                "model": "priced-model",
                "input_price_usd_per_million": 2,
                "output_price_usd_per_million": 0,
                "cache_read_price_usd_per_million": 0,
                "cache_write_price_usd_per_million": 0,
            },
        )
    stats = client.get("/api/statistics/llm?month=2026-08").json()
    rows = {row["model"]: row for row in stats["rows"]}
    assert rows["priced-model"]["estimated_credit_cost_usd"] == 0
    assert rows["unpriced-model"]["estimated_token_cost_usd"] == 0
    assert rows["unpriced-model"]["estimated_total_cost_usd"] == 0
    assert stats["totals"]["estimated_token_cost_usd"] == 2
    assert stats["totals"]["estimated_credit_cost_usd"] == 0
    assert stats["totals"]["estimated_total_cost_usd"] == 2
    assert stats["lifetime"]["estimated_token_cost_usd"] == 2
    assert stats["lifetime"]["estimated_credit_cost_usd"] == 0
    assert stats["lifetime"]["estimated_total_cost_usd"] == 2


def test_run_token_usage_includes_cache_aware_estimated_cost(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        session.add(
            LLMPriceCatalog(
                provider="openai",
                model="gpt-cost-test",
                input_price_usd_per_million=2,
                output_price_usd_per_million=4,
                cache_read_price_usd_per_million=0.2,
                cache_write_price_usd_per_million=0.4,
            )
        )
        session.commit()

    run_id = 991001
    llm.set_run_context(run_id, emit_fn=None)
    try:
        llm._record_usage(
            "gpt-cost-test",
            input_tokens=1_000_000,
            output_tokens=500_000,
            cache_read_tokens=100_000,
            provider="openai",
        )
    finally:
        llm.clear_run_context()

    usage = llm.get_run_token_usage(run_id)
    assert usage["estimated_token_cost_usd"] == 3.82
    assert usage["estimated_credit_cost_usd"] == 0
    assert usage["estimated_total_cost_usd"] == 3.82
    assert usage["estimated_cost_available"] is True
    assert usage["by_model"]["gpt-cost-test"]["estimated_total_cost_usd"] == 3.82


def test_run_cost_is_recalculated_from_totals_on_each_usage_update(
    isolated_db_engine,
):
    model = "gpt-repriced"
    with Session(isolated_db_engine) as session:
        session.add(
            LLMPriceCatalog(
                provider="openai",
                model=model,
                input_price_usd_per_million=1,
                output_price_usd_per_million=2,
            )
        )
        session.commit()

    run_id = 991002
    key = ("web", run_id)
    llm.set_run_context(run_id, emit_fn=None)
    try:
        llm._record_usage(
            model,
            input_tokens=1_000_000,
            output_tokens=500_000,
            provider="openai",
        )
        with Session(isolated_db_engine) as session:
            price = session.query(LLMPriceCatalog).one()
            price.input_price_usd_per_million = 2
            price.output_price_usd_per_million = 4
            session.add(price)
            session.commit()
        llm._record_usage(
            model,
            input_tokens=1_000_000,
            output_tokens=500_000,
            provider="openai",
        )
        usage = llm.get_run_token_usage(run_id)
    finally:
        llm.clear_run_context()
        llm._run_token_usage.pop(key, None)
        llm._run_token_seeded.discard(key)

    model_usage = usage["by_model"][model]
    assert model_usage["estimated_cost_available"] is True
    assert model_usage["estimated_total_cost_usd"] == 8


def test_existing_run_token_usage_is_backfilled_and_persisted(isolated_db_engine):
    model = "minimax/minimax-m3"
    old_bucket = {
        model: {
            "input": 1_000_000,
            "output": 100_000,
            "cache_read": 200_000,
            "cache_write": 0,
            "ai_credits": 0,
            "factory_credits": 0,
            "premium_requests": 0,
            "requests": 0,
            "provider": "openrouter",
            "estimated_cost_available": True,
            "estimated_token_cost_usd": 0.09,
            "estimated_credit_cost_usd": 0,
            "estimated_total_cost_usd": 0.09,
        }
    }
    with Session(isolated_db_engine) as session:
        site = Site(name="Backfill target", base_url="https://target.test")
        session.add(site)
        session.flush()
        run = TestRun(
            site_id=site.id,
            name="Existing scan",
            status="complete",
            execution_snapshot_json=json.dumps(
                {"model": {"model": model, "provider": "openai"}}
            ),
            token_usage_json=json.dumps(old_bucket),
        )
        session.add(run)
        session.add(LLMUsageMonth(month="2026-08", provider="openrouter", model=model))
        session.add(
            LLMPriceCatalog(
                provider="openrouter",
                model=model,
                input_price_usd_per_million=2,
                output_price_usd_per_million=3,
                cache_read_price_usd_per_million=0.2,
                cache_write_price_usd_per_million=0.4,
            )
        )
        session.commit()
        run_id = run.id

    key = ("web", run_id)
    llm._run_token_usage[key] = old_bucket
    try:
        usage = llm.get_run_token_usage(run_id)
    finally:
        llm._run_token_usage.pop(key, None)
        llm._run_token_seeded.discard(key)

    assert usage["by_model"][model]["provider"] == "openrouter"
    assert usage["estimated_cost_available"] is True
    assert usage["estimated_total_cost_usd"] == 1.94
    with Session(isolated_db_engine) as session:
        saved = json.loads(session.get(TestRun, run_id).token_usage_json)
    assert saved[model]["estimated_total_cost_usd"] == 1.94
