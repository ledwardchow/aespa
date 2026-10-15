from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import LLMPriceCatalog
from aespa.services import statistics
from extensions.builtin.chatgpt_plan_usage import codex, extension, scans, usage
from extensions.builtin.chatgpt_plan_usage.models import Reading, UsageDelta

EXTENSION = "aespa.chatgptplanusage"
T0 = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def store(monkeypatch, tmp_path):
    from aespa.extensions.runtime import ExtensionDataStore
    from extensions.builtin.chatgpt_plan_usage import models

    data = ExtensionDataStore(EXTENSION, "planusage", tmp_path / "usage.db")
    data.create_all(models.metadata)
    yield data
    data.dispose()


def _price(
    model="gpt-6.1-sol", input=4.0, output=20.0, cache=0.4, provider=usage.CHATGPT_PLAN
):
    with Session(get_engine()) as session:
        session.add(
            LLMPriceCatalog(
                provider=provider,
                model=model,
                input_price_usd_per_million=input,
                output_price_usd_per_million=output,
                cache_read_price_usd_per_million=cache,
                cache_write_price_usd_per_million=input,
                manual_override=True,
            )
        )
        session.commit()


def _use(input=0, output=0, cache=0, model="gpt-6.1-sol", provider=usage.CHATGPT_PLAN):
    statistics.record_usage(
        provider,
        model,
        input_tokens=input,
        output_tokens=output,
        cache_read_tokens=cache,
    )


def _read(store, window, percent, at, resets_at=None):
    with store.session() as session:
        session.add(
            Reading(
                window=window,
                used_percent=percent,
                observed_at=at,
                resets_at=resets_at,
            )
        )
        session.commit()


def _deltas(store):
    with store.session() as session:
        return list(session.exec(select(UsageDelta).order_by(UsageDelta.id)))


def test_first_sample_is_a_baseline_and_later_samples_store_increases(store):
    _use(input=500, output=50)
    _use(input=999, model="other", provider="openai")
    assert usage.sample(store, at=T0) == 0

    _use(input=1_000, output=100, cache=300)
    assert usage.sample(store, at=T0 + timedelta(minutes=1)) == 1
    assert usage.sample(store, at=T0 + timedelta(minutes=2)) == 0
    [row] = _deltas(store)
    assert (row.input_tokens, row.output_tokens, row.cache_read_tokens) == (
        1_000,
        100,
        300,
    )
    assert row.requests == 1


def test_reset_statistics_counts_new_usage_from_zero(store):
    _use(input=5_000)
    usage.sample(store, at=T0)
    with Session(get_engine()) as session:
        statistics.reset_statistics(session)
    _use(input=700)
    usage.sample(store, at=T0 + timedelta(minutes=1))
    _use(input=300)
    usage.sample(store, at=T0 + timedelta(minutes=2))
    assert [row.input_tokens for row in _deltas(store)] == [700, 300]


def test_window_start_and_readings_give_cost_per_percent(store):
    _price()
    usage.sample(store, at=T0)
    reset = T0 + timedelta(hours=6)  # The window started at T0 + 1h.
    # $4 of input before the window start must not count.
    _use(input=1_000_000)
    usage.sample(store, at=T0 + timedelta(minutes=30))
    # $20 of output inside the window, then a 10% reading.
    _use(output=1_000_000)
    usage.sample(store, at=T0 + timedelta(hours=2))
    _read(store, "five_hour", 10, T0 + timedelta(hours=2), reset)
    # Another $10 takes the window to 15%.
    _use(input=2_500_000)
    usage.sample(store, at=T0 + timedelta(hours=3))
    _read(store, "five_hour", 15, T0 + timedelta(hours=3))

    result = usage.summary(store, "five_hour", at=T0 + timedelta(hours=3, minutes=30))

    first, second = reversed(result["segments"])
    assert first["from_window_start"] is True
    assert first["usage"]["cost_usd"] == pytest.approx(20)
    assert first["usd_per_percent"] == pytest.approx(2)
    assert second["percent_change"] == 5
    assert second["usd_per_percent"] == pytest.approx(2)
    assert result["estimate"]["usd_per_percent"] == pytest.approx(2)
    assert result["estimate"]["usd_for_full_window"] == pytest.approx(200)
    assert result["estimate"]["tokens_per_percent"]["output_tokens"] == 66_667
    current = result["timeline"]["current"]
    assert current["used_percent"] == 15
    assert current["estimated_percent_now"] == 15
    assert result["unpriced_models"] == []


def test_window_start_before_sampling_began_is_not_used(store):
    _price()
    usage.sample(store, at=T0)
    _use(output=1_000_000)
    usage.sample(store, at=T0 + timedelta(hours=1))
    # The window began an hour before sampling, so its usage is incomplete.
    _read(store, "five_hour", 10, T0 + timedelta(hours=1), T0 + timedelta(hours=4))

    result = usage.summary(store, "five_hour", at=T0 + timedelta(hours=1))

    assert result["segments"] == []
    assert result["estimate"] is None


def test_lower_reading_starts_a_new_window(store):
    _price()
    usage.sample(store, at=T0)
    _use(output=500_000)
    usage.sample(store, at=T0 + timedelta(hours=1))
    _read(store, "weekly", 40, T0 + timedelta(hours=1))
    _use(output=500_000)
    usage.sample(store, at=T0 + timedelta(hours=2))
    _read(store, "weekly", 2, T0 + timedelta(hours=2))

    result = usage.summary(store, "weekly", at=T0 + timedelta(hours=2))

    assert result["segments"] == []


def test_unpriced_models_are_reported_without_a_cost(store):
    usage.sample(store, at=T0)
    _use(output=1_000)
    usage.sample(store, at=T0 + timedelta(minutes=10))
    _read(store, "five_hour", 1, T0 + timedelta(minutes=5))
    _read(store, "five_hour", 3, T0 + timedelta(minutes=10))

    result = usage.summary(store, "five_hour", at=T0 + timedelta(minutes=10))

    assert result["unpriced_models"] == ["gpt-6.1-sol (ChatGPT plan)"]
    assert result["segments"][0]["usage"]["cost_usd"] is None
    assert result["estimate"]["usd_per_percent"] is None
    assert result["estimate"]["tokens_per_percent"]["output_tokens"] == 500


def test_codex_cli_usage_counts_toward_the_estimate(store):
    _price()
    _price(model="gpt-5.6-sol", provider=usage.CODEX)
    usage.sample(store, at=T0)
    _use(output=500_000)  # $10 through the ChatGPT plan provider.
    _use(output=250_000, model="gpt-5.6-sol", provider=usage.CODEX)  # $5.
    usage.sample(store, at=T0 + timedelta(hours=1))
    _read(store, "weekly", 10, T0 + timedelta(minutes=30))
    _read(store, "weekly", 13, T0 + timedelta(hours=1))

    both = usage.summary(store, "weekly", at=T0 + timedelta(hours=1))
    codex_only = usage.summary(
        store, "weekly", at=T0 + timedelta(hours=1), providers=(usage.CODEX,)
    )

    assert both["estimate"]["usd_per_percent"] == pytest.approx(5)
    assert codex_only["estimate"]["usd_per_percent"] == pytest.approx(5 / 3)
    assert codex_only["providers"] == ["Codex CLI"]


def _codex_result(percent=12, reset=1_792_472_310, email="me@example.com"):
    return {
        "account": {"account": {"type": "chatgpt", "email": email}},
        "rate_limits": {
            "rateLimits": {"limitId": "other"},
            "rateLimitsByLimitId": {
                "codex": {
                    "limitId": "codex",
                    "planType": "plus",
                    "primary": {
                        "usedPercent": percent,
                        "windowDurationMins": 300,
                        "resetsAt": reset - 6 * 86_400,
                    },
                    "secondary": {
                        "usedPercent": 40,
                        "windowDurationMins": 10080,
                        "resetsAt": reset,
                    },
                },
                "codex_spark": {"primary": {"usedPercent": 99}},
            },
        },
    }


def test_codex_limits_are_parsed_by_window_length():
    parsed = codex.parse(_codex_result())

    assert parsed["email"] == "me@example.com"
    assert parsed["limit_id"] == "codex"
    assert parsed["plan_type"] == "plus"
    assert [(item["window"], item["used_percent"]) for item in parsed["windows"]] == [
        ("five_hour", 12.0),
        ("weekly", 40.0),
    ]
    assert parsed["windows"][1]["resets_at"] == datetime.fromtimestamp(
        1_792_472_310, timezone.utc
    )
    assert codex.parse({})["windows"] == []


def _poll(store, monkeypatch, results, plan_email="me@example.com"):
    from aespa.services import chatgpt_plan, codex_provider

    queue = list(results)

    async def fake_read(_path=None):
        value = queue.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(codex_provider, "read_account_usage", fake_read)
    monkeypatch.setattr(
        chatgpt_plan,
        "status",
        lambda: {
            "accounts": [{"email": plan_email, "active": True}] if plan_email else []
        },
    )
    return [codex.poll(store) for _ in results]


def _codex_readings(store):
    with store.session() as session:
        return list(
            session.exec(
                select(Reading).where(Reading.source == "codex").order_by(Reading.id)
            )
        )


def test_codex_readings_are_saved_only_when_usage_changes(store, monkeypatch):
    first, same, changed = _poll(
        store,
        monkeypatch,
        [_codex_result(12), _codex_result(12), _codex_result(15)],
    )

    assert (first["added"], same["added"], changed["added"]) == (2, 0, 1)
    assert first["same_account"] is True
    readings = _codex_readings(store)
    assert [(row.window, row.used_percent) for row in readings] == [
        ("five_hour", 12),
        ("weekly", 40),
        ("five_hour", 15),
    ]
    assert codex.status(store)["windows"][0]["used_percent"] == 15


def test_codex_on_another_account_keeps_only_codex_cli_usage(store, monkeypatch):
    [result] = _poll(
        store, monkeypatch, [_codex_result()], plan_email="other@example.com"
    )

    assert result["same_account"] is False
    assert len(_codex_readings(store)) == 2


def test_codex_failure_is_reported_without_readings(store, monkeypatch):
    from aespa.services.codex_provider import CodexUnavailableError

    [result] = _poll(
        store, monkeypatch, [CodexUnavailableError("Codex CLI is not installed")]
    )

    assert result["ok"] is False
    assert result["error"] == "Codex CLI is not installed"
    assert _codex_readings(store) == []
    assert codex.status(store)["error"] == "Codex CLI is not installed"


def test_fit_recovers_token_weights():
    weights = {"input_tokens": 2.0, "output_tokens": 10.0, "cache_read_tokens": 0.2}
    mixes = [
        (1_000_000, 100_000, 3_000_000),
        (200_000, 400_000, 1_000_000),
        (3_000_000, 50_000, 0),
        (500_000, 500_000, 6_000_000),
    ]
    items = [
        {
            "percent_change": (
                i * weights["input_tokens"]
                + o * weights["output_tokens"]
                + c * weights["cache_read_tokens"]
            )
            / 1_000_000,
            "usage": {
                "input_tokens": i,
                "output_tokens": o,
                "cache_read_tokens": c,
                "cache_write_tokens": 0,
            },
        }
        for i, o, c in mixes
    ]

    result = usage.fit(items)

    for key, value in weights.items():
        assert result["percent_per_million"][key] == pytest.approx(value, rel=1e-6)
    assert result["millions_for_full_window"]["output_tokens"] == pytest.approx(10)
    assert result["fit_quality"] == pytest.approx(1)
    assert usage.fit(items[:3]) is None


def test_extension_api_records_and_deletes_readings(client, monkeypatch, tmp_path):
    from aespa.extensions import get_extension_manager

    manager = get_extension_manager()
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(
            extensions_dir=tmp_path / "user-extensions",
            data_dir=tmp_path / "data",
        ),
    )
    manager.load_extensions()
    assert manager.extensions[EXTENSION].status == "disabled"
    base = f"/extension/{EXTENSION}"
    try:
        enabled = client.put(
            f"/api/extensions/{EXTENSION}/enabled", json={"enabled": True}
        )
        assert enabled.json()["api_prefix"] == base

        empty = client.get(f"{base}/summary?window=weekly").json()
        assert empty["readings"] == [] and empty["coverage_since"]
        assert empty["codex"] is None
        assert empty["providers"] == ["ChatGPT plan", "Codex CLI"]
        codex._save_status(
            manager.data_stores[EXTENSION], {"ok": True, "same_account": False}
        )
        mismatched = client.get(f"{base}/summary?window=weekly").json()
        assert mismatched["providers"] == ["Codex CLI"]
        assert mismatched["codex"]["same_account"] is False

        created = client.post(
            f"{base}/readings",
            json={"window": "weekly", "used_percent": 12.5, "note": " start "},
        )
        assert created.status_code == 201
        reading = created.json()
        assert reading["note"] == "start"
        listed = client.get(f"{base}/summary?window=weekly").json()["readings"]
        assert [row["id"] for row in listed] == [reading["id"]]

        late_reset = client.post(
            f"{base}/readings",
            json={
                "window": "five_hour",
                "used_percent": 5,
                "resets_at": "2099-01-01T00:00:00Z",
            },
        )
        assert late_reset.status_code == 422
        assert (
            client.post(
                f"{base}/readings", json={"window": "daily", "used_percent": 5}
            ).status_code
            == 422
        )

        assert client.delete(f"{base}/readings/{reading['id']}").status_code == 204
        assert client.delete(f"{base}/readings/{reading['id']}").status_code == 404
    finally:
        client.put(f"/api/extensions/{EXTENSION}/enabled", json={"enabled": False})
    assert client.get(f"{base}/summary").status_code == 404


def test_scan_watcher_reports_started_and_ended_scans():
    watcher = scans.ScanWatcher()
    crawl = scans.Scan(("web", 1, "Crawl"), "Crawl 'Shop'")
    scan = scans.Scan(("api", 1, "Dynamic Scan"), "Dynamic Scan 'Orders'")

    assert watcher.check({crawl.key: crawl}) == ([crawl], [])
    assert watcher.check({crawl.key: crawl, scan.key: scan}) == ([scan], [])
    assert watcher.check({scan.key: scan}) == ([], [crawl])
    assert watcher.check({}) == ([], [scan])


def test_only_runs_using_plan_providers_are_watched(monkeypatch):
    from aespa.models import LLMConfig, LLMProfile
    from aespa.schemas import ActiveJobSummary

    with Session(get_engine()) as session:
        plain = LLMConfig(name="API", provider="openai", model="gpt-5.4")
        codex_model = LLMConfig(name="Codex", provider="openai_codex", model="gpt-5.6")
        session.add_all([plain, codex_model])
        session.flush()
        mixed = LLMProfile(
            name="Mixed",
            default_model_id=plain.id,
            role_models_json=json.dumps({"specialist": codex_model.id}),
        )
        api_only = LLMProfile(name="API only", default_model_id=plain.id)
        session.add_all([mixed, api_only])
        session.commit()
        profiles = {"Shop": mixed.id, "Blog": api_only.id}

    runs = {
        1: SimpleNamespace(llm_profile_id=profiles["Shop"], llm_config_id=None),
        2: SimpleNamespace(llm_profile_id=profiles["Blog"], llm_config_id=None),
    }
    jobs = [
        ActiveJobSummary(
            run_id=run_id,
            run_name=name,
            job_type="Dynamic Scan",
            status="running",
            created_at=T0,
        )
        for run_id, name in ((1, "Shop"), (2, "Blog"))
    ]
    monkeypatch.setattr(
        "aespa.services.active_jobs.list_active_jobs", lambda session: jobs
    )
    monkeypatch.setattr(scans, "_run", lambda session, kind, run_id: runs[run_id])

    assert list(scans.active_plan_scans().values()) == [
        scans.Scan(("web", 1, "Dynamic Scan"), "Dynamic Scan 'Shop'")
    ]


def test_codex_readings_follow_scans(monkeypatch):
    calls = []
    current = {}
    monkeypatch.setattr(scans, "active_plan_scans", lambda: dict(current))
    monkeypatch.setattr(
        codex, "poll", lambda store, note="", force=False: calls.append((note, force))
    )
    watcher = scans.ScanWatcher()
    settings = {"codex_poll_minutes": 10, "scan_poll_minutes": 2}
    step = extension.codex_step

    # Idle: check on the normal interval.
    due = step("store", watcher, settings, 0, now=0)
    assert (calls, due) == ([("", False)], 600)
    assert step("store", watcher, settings, due, now=60) == 600

    # A scan starts: read at once, then every 2 minutes while it runs.
    scan = scans.Scan(("web", 3, "Crawl"), "Crawl 'Shop'")
    current[scan.key] = scan
    due = step("store", watcher, settings, due, now=90)
    assert calls[-1] == ("Crawl 'Shop' started", True) and due == 210
    assert step("store", watcher, settings, due, now=150) == 210
    due = step("store", watcher, settings, due, now=210)
    assert calls[-1] == ("", False) and due == 330

    # The scan ends: read at once, then return to the normal interval.
    current.clear()
    due = step("store", watcher, settings, due, now=240)
    assert calls[-1] == ("Crawl 'Shop' ended", True) and due == 840
    assert len(calls) == 4

    # Turning Codex readings off stops all checks.
    assert step("store", watcher, {"codex_readings": False}, 0, now=900) == 0
    assert len(calls) == 4


def test_forced_codex_readings_are_saved_with_a_note(store, monkeypatch):
    _poll(store, monkeypatch, [_codex_result(12)])
    from aespa.services import codex_provider

    async def fake_read(_path=None):
        return _codex_result(12)

    monkeypatch.setattr(codex_provider, "read_account_usage", fake_read)
    result = codex.poll(store, note="Crawl 'Shop' started", force=True)

    assert result["added"] == 2
    assert [row.note for row in _codex_readings(store)][-2:] == [
        "Crawl 'Shop' started",
        "Crawl 'Shop' started",
    ]
