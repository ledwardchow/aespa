import json
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, func, select

from aespa.models import (
    LLMConfig,
    LLMPriceCatalog,
    LLMUsageDay,
    LLMUsageMonth,
    Site,
    TestRun,
)
from aespa.services import llm, statistics


def test_provider_usage_is_isolated_without_requesting_a_database_fixture():
    from aespa.db import get_engine

    engine = get_engine()
    assert engine.url.database == ":memory:"
    llm._record_usage("isolation-test-model", 10, 5, provider="unknown")
    with Session(engine) as session:
        row = session.exec(select(LLMUsageMonth)).one()
        assert row.model == "isolation-test-model"
        assert row.requests == 1


def test_explicit_free_price_remains_zero():
    row = LLMUsageMonth(
        month="2026-09",
        provider="openai",
        model="free-model",
        input_tokens=100,
        input_price_usd_per_million=0,
    )
    assert statistics._row_dict(row)["estimated_total_cost_usd"] == 0


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
        row = session.exec(select(LLMUsageMonth)).one()
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
        row = session.exec(select(LLMUsageMonth)).one()
        assert row.input_tokens == 1000


def test_bedrock_run_cost_uses_uncached_input():
    cost = statistics.estimate_usage_cost(
        "bedrock",
        input_tokens=450,
        cache_read_tokens=300,
        cache_write_tokens=50,
        rates={
            "input_price_usd_per_million": 1.0,
            "cache_read_price_usd_per_million": 0.1,
            "cache_write_price_usd_per_million": 2.0,
        },
    )
    assert cost["estimated_token_cost_usd"] == pytest.approx(230 / 1_000_000)


def test_copilot_cost_uses_credits_even_when_model_has_token_prices(
    client, isolated_db_engine, monkeypatch
):
    monkeypatch.setattr(
        statistics,
        "_feed",
        lambda session: {
            "gpt-test": {
                "input_cost_per_token": 0.000002,
                "output_cost_per_token": 0.000004,
            }
        },
    )
    rates = statistics.record_usage(
        "github_copilot",
        "gpt-test",
        input_tokens=1_000_000,
        output_tokens=500_000,
        ai_credits=2.5,
        month="2026-08",
    )

    assert rates["credit_price_usd_per_million"] == 10_000
    run_cost = statistics.estimate_usage_cost(
        "github_copilot",
        input_tokens=1_000_000,
        output_tokens=500_000,
        ai_credits=2.5,
        rates=rates,
    )
    assert run_cost["estimated_token_cost_usd"] == 0
    assert run_cost["estimated_credit_cost_usd"] == 0.025
    assert run_cost["estimated_total_cost_usd"] == 0.025

    stats = client.get("/api/statistics/llm?month=2026-08").json()
    assert stats["rows"][0]["estimated_token_cost_usd"] == 0
    assert stats["rows"][0]["estimated_total_cost_usd"] == 0.025
    assert stats["totals"]["estimated_total_cost_usd"] == 0.025
    assert stats["lifetime"]["estimated_total_cost_usd"] == 0.025


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
        row = session.exec(select(LLMUsageMonth)).one()
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
        assert (
            session.exec(select(LLMPriceCatalog)).one().credit_price_usd_per_million
            == 9
        )
        statistics.reset_statistics(session)
        assert session.exec(select(func.count()).select_from(LLMUsageMonth)).one() == 0
        assert (
            session.exec(select(func.count()).select_from(LLMPriceCatalog)).one() == 1
        )


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


def test_date_views_use_daily_usage_and_monthly_prices(client, isolated_db_engine):
    statistics.record_usage(
        "openai", "dated-model", input_tokens=100, day="2026-10-18", service_tier="fast"
    )
    statistics.record_usage(
        "openai", "dated-model", input_tokens=200, day="2026-10-19", service_tier="fast"
    )
    statistics.record_usage("openai", "dated-model", input_tokens=300, day="2026-10-26")
    with Session(isolated_db_engine) as session:
        statistics.set_prices(
            session,
            {
                "month": "2026-10",
                "provider": "openai",
                "model": "dated-model",
                "input_price_usd_per_million": 2,
            },
        )
        statistics.set_prices(
            session,
            {
                "month": "2026-10",
                "provider": "openai",
                "model": "dated-model",
                "service_tier": "fast",
                "input_price_usd_per_million": 4,
            },
        )
        assert len(list(session.exec(select(LLMUsageDay)))) == 3
    response = client.get("/api/statistics/llm?view=daily&date=2026-10-19")
    assert response.status_code == 200, response.json()
    daily = response.json()
    assert daily["totals"]["input_tokens"] == 200
    assert daily["rows"][0]["month"] == "2026-10"
    assert daily["rows"][0]["service_tier"] == "fast"
    assert daily["totals"]["estimated_total_cost_usd"] == pytest.approx(0.0008)
    weekly = client.get("/api/statistics/llm?view=weekly&date=2026-10-19").json()
    assert weekly["start"] == "2026-10-19"
    assert weekly["end"] == "2026-10-25"
    assert weekly["totals"]["input_tokens"] == 200
    custom = client.get(
        "/api/statistics/llm?view=custom&start=2026-10-18&end=2026-10-19"
    ).json()
    assert custom["totals"]["input_tokens"] == 300
    all_time = client.get("/api/statistics/llm?view=all_time").json()
    assert all_time["totals"]["input_tokens"] == 600
    assert all_time["totals"]["estimated_total_cost_usd"] == pytest.approx(0.0018)


def test_date_view_reports_older_monthly_usage_without_guessing_dates(
    client, isolated_db_engine
):
    statistics.record_usage("openai", "older", input_tokens=500, month="2026-08")
    with Session(isolated_db_engine) as session:
        assert session.exec(select(func.count()).select_from(LLMUsageDay)).one() == 0
    response = client.get(
        "/api/statistics/llm?view=custom&start=2026-08-01&end=2026-08-31"
    ).json()
    assert response["rows"] == []
    assert response["legacy_months"] == ["2026-08"]
    assert (
        client.get("/api/statistics/llm?month=2026-08").json()["totals"]["input_tokens"]
        == 500
    )


def test_invalid_custom_date_range_and_reset_daily_ledger(client, isolated_db_engine):
    assert (
        client.get("/api/statistics/llm?view=custom&start=2026-10-19").status_code
        == 422
    )
    assert (
        client.get(
            "/api/statistics/llm?view=custom&start=2026-10-20&end=2026-10-19"
        ).status_code
        == 422
    )
    statistics.record_usage("openai", "reset", day="2026-10-19")
    assert client.delete("/api/statistics/llm").status_code == 200
    with Session(isolated_db_engine) as session:
        assert session.exec(select(func.count()).select_from(LLMUsageDay)).one() == 0


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
    assert rows["unpriced-model"]["estimated_total_cost_usd"] is None
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
            price = session.exec(select(LLMPriceCatalog)).one()
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


def _add_standard_price(session, model):
    session.add(
        LLMPriceCatalog(
            provider="openai_chatgpt_plan",
            model=model,
            input_price_usd_per_million=1,
            output_price_usd_per_million=2,
        )
    )
    session.commit()


def test_fast_usage_gets_its_own_row_priced_above_standard(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        _add_standard_price(session, "gpt-fast-test")
    for tier in ("", "fast"):
        statistics.record_usage(
            "openai_chatgpt_plan",
            "gpt-fast-test",
            service_tier=tier,
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            month="2026-10",
        )
    with Session(isolated_db_engine) as session:
        rows = {
            row["service_tier"]: row
            for row in statistics.get_statistics(session, "2026-10")["rows"]
        }
    assert rows[""]["requests"] == rows["fast"]["requests"] == 1
    assert rows[""]["estimated_total_cost_usd"] == 3
    assert rows["fast"]["estimated_total_cost_usd"] == 6
    assert rows["fast"]["prices"]["confidence"] == "fallback"


def test_fast_price_comes_from_feed_priority_prices():
    feed = {
        "gpt-test": {
            "input_cost_per_token": 0.000001,
            "output_cost_per_token": 0.000002,
            "input_cost_per_token_priority": 0.0000025,
            "output_cost_per_token_priority": 0.000005,
        }
    }
    rates = statistics.resolve_price("openai", "gpt-test", feed, "fast")
    assert rates["input_price_usd_per_million"] == 2.5
    assert rates["output_price_usd_per_million"] == 5


def test_fast_manual_price_does_not_change_standard_price(isolated_db_engine):
    statistics.record_usage(
        "openai_chatgpt_plan", "gpt-manual", service_tier="fast", month="2026-10"
    )
    with Session(isolated_db_engine) as session:
        statistics.set_prices(
            session,
            {
                "month": "2026-10",
                "provider": "openai_chatgpt_plan",
                "model": "gpt-manual",
                "service_tier": "fast",
                "input_price_usd_per_million": 7,
            },
        )
        fast = statistics._rates_for(
            session, "openai_chatgpt_plan", "gpt-manual", "fast"
        )
        standard = statistics._rates_for(session, "openai_chatgpt_plan", "gpt-manual")
    assert fast["input_price_usd_per_million"] == 7
    assert standard.get("input_price_usd_per_million") is None


def test_run_usage_lists_fast_models_separately(isolated_db_engine):
    model = "gpt-run-fast"
    with Session(isolated_db_engine) as session:
        _add_standard_price(session, model)
    run_id = 991010
    key = ("web", run_id)
    llm.set_run_context(run_id, emit_fn=None)
    try:
        for tier in ("", "fast"):
            llm._record_usage(
                model,
                input_tokens=1_000_000,
                output_tokens=0,
                provider="openai_chatgpt_plan",
                service_tier=tier,
            )
        usage = llm.get_run_token_usage(run_id)
    finally:
        llm.clear_run_context()
        llm._run_token_usage.pop(key, None)
        llm._run_token_seeded.discard(key)

    assert set(usage["by_model"]) == set(usage["by_model_fast"]) == {model}
    assert usage["by_model"][model]["estimated_total_cost_usd"] == 1
    assert usage["by_model_fast"][model]["estimated_total_cost_usd"] == 2
    assert usage["by_model_fast"][model]["service_tier"] == "fast"
    assert usage["total_input"] == 2_000_000
    assert usage["estimated_total_cost_usd"] == 3
