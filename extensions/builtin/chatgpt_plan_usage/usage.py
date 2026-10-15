"""Relate ChatGPT plan usage percentages to AESPA's token usage and API prices.

Readings come from the Codex CLI or are copied from ChatGPT's usage settings.
Both the ChatGPT plan provider and the Codex CLI provider use the plan's
limits, so usage from either counts. AESPA's usage ledger only keeps monthly
totals, so this extension samples those totals and stores the increase between
samples. Usage between two readings of the same window, divided by the change
in percentage, gives the API-price equivalent of 1% of that window.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import LLMUsageMonth
from aespa.services import statistics as statistics_service

from .models import CounterState, Meta, Reading, UsageDelta, now

CHATGPT_PLAN = "openai_chatgpt_plan"
CODEX = "openai_codex"
PROVIDERS = (CHATGPT_PLAN, CODEX)
PROVIDER_LABELS = {CHATGPT_PLAN: "ChatGPT plan", CODEX: "Codex CLI"}
WINDOWS: dict[str, timedelta] = {
    "five_hour": timedelta(hours=5),
    "weekly": timedelta(days=7),
}
RESET_TOLERANCE = timedelta(minutes=15)
PERCENT_TOLERANCE = 0.5
TIMELINE_SPAN = {"five_hour": timedelta(hours=24), "weekly": timedelta(days=14)}
BUCKET_SIZE = {"five_hour": timedelta(minutes=30), "weekly": timedelta(hours=6)}
COUNTERS = (
    "requests",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)
TOKENS = COUNTERS[1:]


def utc(value: datetime | None) -> datetime | None:
    """Return an aware UTC time; a time without a zone is taken as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return None if value is None else utc(value).isoformat()


def read_ledger(core: Session) -> dict[tuple[str, str], dict[str, int]]:
    """Read lifetime plan totals per provider and model from the usage ledger."""
    columns = [
        func.coalesce(func.sum(getattr(LLMUsageMonth, key)), 0) for key in COUNTERS
    ]
    rows = core.exec(
        select(LLMUsageMonth.provider, LLMUsageMonth.model, *columns)
        .where(LLMUsageMonth.provider.in_(PROVIDERS))
        .group_by(LLMUsageMonth.provider, LLMUsageMonth.model)
    ).all()
    return {
        (str(row[0]), str(row[1])): {
            key: int(value or 0) for key, value in zip(COUNTERS, row[2:])
        }
        for row in rows
    }


def sample(store, at: datetime | None = None) -> int:
    """Store usage added since the last sample. Returns the number of rows added."""
    at = utc(at) or now()
    with Session(get_engine()) as core:
        totals = read_ledger(core)
    zeros = dict.fromkeys(COUNTERS, 0)
    added = 0
    with store.session() as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        states = {
            (row.provider, row.model): row for row in session.exec(select(CounterState))
        }
        first = session.get(Meta, "coverage_since") is None
        for key in sorted(set(totals) | set(states)):
            provider, model = key
            current = totals.get(key, zeros)
            state = states.get(key)
            if state is None:
                state = CounterState(provider=provider, model=model)
                previous = current if first else zeros
            else:
                previous = {key: getattr(state, key) for key in COUNTERS}
            if any(current[key] < previous[key] for key in COUNTERS):
                previous = zeros
            delta = {name: current[name] - previous[name] for name in COUNTERS}
            if any(delta.values()):
                session.add(
                    UsageDelta(sampled_at=at, provider=provider, model=model, **delta)
                )
                added += 1
            if key not in states or any(
                getattr(state, name) != current[name] for name in COUNTERS
            ):
                for name in COUNTERS:
                    setattr(state, name, current[name])
                state.updated_at = at
                session.add(state)
        if first:
            session.add(Meta(key="coverage_since", value=at.isoformat()))
        session.commit()
    return added


def coverage_since(session: Session) -> datetime | None:
    row = session.get(Meta, "coverage_since")
    return utc(datetime.fromisoformat(row.value)) if row else None


def model_rates(core: Session, provider: str, model: str) -> dict[str, float] | None:
    """API prices per million tokens, or None when no usable price is known."""
    row = core.exec(
        select(LLMUsageMonth)
        .where(LLMUsageMonth.provider == provider, LLMUsageMonth.model == model)
        .order_by(LLMUsageMonth.month.desc())
    ).first()
    if row is not None and (
        row.input_price_usd_per_million is not None
        or row.output_price_usd_per_million is not None
    ):
        values = {
            "input": row.input_price_usd_per_million,
            "output": row.output_price_usd_per_million,
            "cache_read": row.cache_read_price_usd_per_million,
            "cache_write": row.cache_write_price_usd_per_million,
        }
    else:
        rates = statistics_service._rates_for(core, provider, model)
        values = {
            "input": rates.get("input_price_usd_per_million"),
            "output": rates.get("output_price_usd_per_million"),
            "cache_read": rates.get("cache_read_price_usd_per_million"),
            "cache_write": rates.get("cache_write_price_usd_per_million"),
        }
    if values["input"] is None and values["output"] is None:
        return None
    for key in ("cache_read", "cache_write"):
        if values[key] is None:
            values[key] = values["input"]
    return {key: float(value or 0) for key, value in values.items()}


def delta_cost(row: UsageDelta, rates: dict[str, float]) -> float:
    return (
        row.input_tokens * rates["input"]
        + row.output_tokens * rates["output"]
        + row.cache_read_tokens * rates["cache_read"]
        + row.cache_write_tokens * rates["cache_write"]
    ) / 1_000_000


@dataclass
class Totals:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    unpriced_models: set[str] = field(default_factory=set)

    def add(self, row: UsageDelta, rates: dict[str, float] | None) -> None:
        for key in COUNTERS:
            setattr(self, key, getattr(self, key) + getattr(row, key))
        if rates is None:
            self.unpriced_models.add(model_label(row.provider, row.model))
        else:
            self.cost_usd += delta_cost(row, rates)

    @property
    def priced(self) -> bool:
        return not self.unpriced_models

    def as_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "cost_usd": round(self.cost_usd, 6) if self.priced else None,
            "unpriced_models": sorted(self.unpriced_models),
        }


class Usage:
    """Usage deltas in time order with cached prices."""

    def __init__(self, deltas: list[UsageDelta], rates: dict[str, dict | None]):
        self.deltas = sorted(deltas, key=lambda row: row.sampled_at)
        self.rates = rates

    def between(self, start: datetime, end: datetime) -> Totals:
        totals = Totals()
        for row in self.deltas:
            if start < row.sampled_at <= end:
                totals.add(row, self.rates.get((row.provider, row.model)))
        return totals


def model_label(provider: str, model: str) -> str:
    return f"{model} ({PROVIDER_LABELS.get(provider, provider)})"


def load_usage(
    session: Session,
    core: Session,
    since: datetime | None,
    providers: tuple[str, ...] = PROVIDERS,
) -> Usage:
    query = select(UsageDelta).where(UsageDelta.provider.in_(providers))
    if since is not None:
        query = query.where(UsageDelta.sampled_at > since)
    deltas = list(session.exec(query))
    keys = {(row.provider, row.model) for row in deltas}
    return Usage(deltas, {key: model_rates(core, *key) for key in keys})


@dataclass
class Period:
    """Readings that belong to one usage window, in time order."""

    readings: list[Reading]

    @property
    def resets_at(self) -> datetime | None:
        return next((row.resets_at for row in self.readings if row.resets_at), None)

    def start(self, length: timedelta) -> datetime | None:
        reset = self.resets_at
        return reset - length if reset else None

    def accepts(self, reading: Reading, length: timedelta) -> bool:
        last = self.readings[-1]
        if reading.used_percent < last.used_percent - PERCENT_TOLERANCE:
            return False
        reset = self.resets_at
        if reset and reading.resets_at:
            return abs(reading.resets_at - reset) <= RESET_TOLERANCE
        reset = reset or reading.resets_at
        if reset:
            return all(
                reset - length - RESET_TOLERANCE <= row.observed_at <= reset
                for row in [*self.readings, reading]
            )
        return reading.observed_at - self.readings[0].observed_at < length


def periods(readings: list[Reading], length: timedelta) -> list[Period]:
    result: list[Period] = []
    for reading in sorted(readings, key=lambda row: row.observed_at):
        if result and result[-1].accepts(reading, length):
            result[-1].readings.append(reading)
        else:
            result.append(Period([reading]))
    return result


def anchors(
    period: Period, length: timedelta, covered_from: datetime | None
) -> list[tuple[datetime, float, int | None]]:
    """Points with a known percentage: the readings, plus 0% at the window start."""
    points = [(row.observed_at, row.used_percent, row.id) for row in period.readings]
    start = period.start(length)
    if (
        start is not None
        and covered_from is not None
        and covered_from <= start <= points[0][0]
    ):
        points.insert(0, (start, 0.0, None))
    return points


def segments(
    readings: list[Reading],
    length: timedelta,
    covered_from: datetime | None,
    usage: Usage,
) -> list[dict[str, Any]]:
    result = []
    for period in periods(readings, length):
        points = anchors(period, length, covered_from)
        for (start, before, start_id), (end, after, end_id) in itertools.pairwise(
            points
        ):
            if covered_from is None or start < covered_from or end <= start:
                continue
            totals = usage.between(start, end)
            change = round(after - before, 4)
            if change != 0 and not any(getattr(totals, key) for key in TOKENS):
                # The plan was used outside AESPA, so the change says nothing
                # about AESPA's tokens.
                continue
            result.append(
                {
                    "start": iso(start),
                    "end": iso(end),
                    "from_reading_id": start_id,
                    "to_reading_id": end_id,
                    "from_window_start": start_id is None,
                    "percent_change": change,
                    "usage": totals.as_dict(),
                    "usd_per_percent": (
                        round(totals.cost_usd / change, 6)
                        if totals.priced and change > 0
                        else None
                    ),
                }
            )
    return result


def estimate(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Combine segments as a ratio of sums, which handles rounded readings."""
    if not items:
        return None
    total_percent = sum(item["percent_change"] for item in items)
    if total_percent <= 0:
        return None
    priced = [item for item in items if item["usage"]["cost_usd"] is not None]
    priced_percent = sum(item["percent_change"] for item in priced)
    priced_cost = sum(item["usage"]["cost_usd"] for item in priced)
    usd_per_percent = priced_cost / priced_percent if priced_percent > 0 else None
    return {
        "segments": len(items),
        "percent_measured": round(total_percent, 4),
        "usd_measured": round(priced_cost, 6) if priced else None,
        "usd_per_percent": (
            round(usd_per_percent, 6) if usd_per_percent is not None else None
        ),
        "usd_for_full_window": (
            round(usd_per_percent * 100, 4) if usd_per_percent is not None else None
        ),
        "tokens_per_percent": {
            key: round(sum(item["usage"][key] for item in items) / total_percent)
            for key in TOKENS
        },
        "unpriced_segments": len(items) - len(priced),
    }


def timeline(
    window: str,
    readings: list[Reading],
    covered_from: datetime | None,
    usage: Usage,
    usd_per_percent: float | None,
    at: datetime,
) -> dict[str, Any]:
    length = WINDOWS[window]
    span_start = at - TIMELINE_SPAN[window]
    bucket = BUCKET_SIZE[window]
    buckets = []
    cursor = span_start
    while cursor < at:
        end = min(cursor + bucket, at)
        totals = usage.between(cursor, end)
        buckets.append({"start": iso(cursor), "end": iso(end), **totals.as_dict()})
        cursor = end

    lines: list[list[dict[str, Any]]] = []
    current = None
    for period in periods(readings, length):
        points = anchors(period, length, covered_from)
        reset = period.resets_at
        window_end = reset or (period.readings[0].observed_at + length)
        for index, (start, percent, reading_id) in enumerate(points):
            until = points[index + 1][0] if index + 1 < len(points) else window_end
            until = min(until, at)
            line = [{"t": iso(start), "percent": percent, "estimated": False}]
            spent = 0.0
            priced = True
            for row in usage.deltas:
                if start < row.sampled_at <= until:
                    rates = usage.rates.get((row.provider, row.model))
                    if rates is None:
                        priced = False
                        break
                    spent += delta_cost(row, rates)
                    if usd_per_percent:
                        line.append(
                            {
                                "t": iso(row.sampled_at),
                                "percent": round(percent + spent / usd_per_percent, 3),
                                "estimated": True,
                            }
                        )
            if usd_per_percent and priced and until > start:
                line.append(
                    {
                        "t": iso(until),
                        "percent": round(percent + spent / usd_per_percent, 3),
                        "estimated": True,
                    }
                )
            if until >= span_start:
                lines.append(line)
            is_last = index + 1 == len(points)
            if is_last and at < window_end:
                since = usage.between(start, at)
                current = {
                    "reading_id": reading_id,
                    "observed_at": iso(start),
                    "used_percent": percent,
                    "resets_at": iso(reset),
                    "window_ends_at": iso(window_end),
                    "usage_since_reading": since.as_dict(),
                    "estimated_percent_now": (
                        round(percent + since.cost_usd / usd_per_percent, 2)
                        if usd_per_percent and since.priced
                        else None
                    ),
                }
    return {
        "start": iso(span_start),
        "end": iso(at),
        "buckets": buckets,
        "lines": lines,
        "current": current,
    }


def _no_tokens(totals: Totals) -> bool:
    return not any(getattr(totals, key) for key in TOKENS)


def prune_readings(store) -> int:
    """Delete readings taken while only something outside AESPA used the plan.

    A reading is removed when AESPA used no tokens since the previous reading
    or before the next one, and the percentage changed on either side. Each
    remaining reading still marks the edge of every interval with AESPA usage,
    so removing these does not change the estimate. The first and last reading
    of each window are kept.
    """
    removed = 0
    with store.session() as session, Session(get_engine()) as core:
        covered_from = coverage_since(session)
        if covered_from is None:
            return 0
        readings = list(session.exec(select(Reading).order_by(Reading.observed_at)))
        if not readings:
            return 0
        usage = load_usage(session, core, None)
        for window, length in WINDOWS.items():
            rows = [row for row in readings if row.window == window]
            for period in periods(rows, length):
                kept = [period.readings[0]]
                items = period.readings[1:]
                for index, row in enumerate(items[:-1]):
                    before, after = kept[-1], items[index + 1]
                    if (
                        before.observed_at >= covered_from
                        and _no_tokens(
                            usage.between(before.observed_at, row.observed_at)
                        )
                        and _no_tokens(
                            usage.between(row.observed_at, after.observed_at)
                        )
                        and (
                            row.used_percent != before.used_percent
                            or after.used_percent != row.used_percent
                        )
                    ):
                        session.delete(row)
                        removed += 1
                    else:
                        kept.append(row)
        session.commit()
    return removed


def reading_out(row: Reading) -> dict[str, Any]:
    return {
        "id": row.id,
        "window": row.window,
        "used_percent": row.used_percent,
        "observed_at": iso(row.observed_at),
        "resets_at": iso(row.resets_at),
        "note": row.note,
        "source": row.source,
        "created_at": iso(row.created_at),
    }


def summary(
    store,
    window: str,
    at: datetime | None = None,
    providers: tuple[str, ...] = PROVIDERS,
) -> dict[str, Any]:
    at = utc(at) or now()
    length = WINDOWS[window]
    with store.session() as session, Session(get_engine()) as core:
        covered_from = coverage_since(session)
        readings = list(
            session.exec(
                select(Reading)
                .where(Reading.window == window)
                .order_by(Reading.observed_at)
            )
        )
        earliest = [at - TIMELINE_SPAN[window]]
        if readings:
            earliest.append(readings[0].observed_at - length)
        usage = load_usage(session, core, min(earliest), providers)
    items = segments(readings, length, covered_from, usage)
    result = estimate(items)
    usd_per_percent = result["usd_per_percent"] if result else None
    unpriced = sorted(
        model_label(*key) for key, rates in usage.rates.items() if rates is None
    )
    return {
        "window": window,
        "window_seconds": int(length.total_seconds()),
        "now": iso(at),
        "coverage_since": iso(covered_from),
        "readings": [reading_out(row) for row in reversed(readings)],
        "segments": list(reversed(items)),
        "estimate": result,
        "timeline": timeline(
            window, readings, covered_from, usage, usd_per_percent, at
        ),
        "unpriced_models": unpriced,
        "providers": [PROVIDER_LABELS[provider] for provider in providers],
    }
