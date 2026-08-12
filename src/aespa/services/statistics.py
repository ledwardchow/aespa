"""Independent monthly LLM usage statistics and price estimates."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import LLMPriceCatalog, LLMPriceFeed, LLMUsageMonth

PRICE_FEED_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

DEFAULT_CREDIT_PRICES: dict[str, tuple[float, str]] = {
    "github_copilot": (10_000.0, "AI credits per 1,000,000 credits"),
    "factory_droid": (7.0, "Factory credits per 1,000,000 credits"),
}

SUBSCRIPTION_PROVIDERS = {"openai_codex"}

_INCLUSIVE_INPUT_PROVIDERS = {
    "openai",
    "openai_compatible",
    "openrouter",
    "azure_openai",
    "azure_foundry",
    "azure_foundry_openai",
    "bedrock_mantle",
    "google",
    "openai_codex",
}


def local_month(value: datetime | None = None) -> str:
    """Return the operating system's local calendar month for ``value``."""

    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%Y-%m")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _native_credit_defaults(provider: str) -> tuple[float | None, str | None]:
    return DEFAULT_CREDIT_PRICES.get(provider, (None, None))


def _as_price(value: Any) -> float | None:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value * 1_000_000


def _provider_aliases(provider: str) -> set[str]:
    aliases = {
        provider,
        {
            "azure_openai": "openai",
            "azure_foundry": "openai",
            "azure_foundry_openai": "openai",
            "azure_foundry_anthropic": "anthropic",
            "bedrock_mantle": "bedrock",
            "google": "vertex_ai",
            "openrouter": "openrouter",
        }.get(provider, provider),
    }
    return {value.lower() for value in aliases}


def _price_candidates(provider: str, model: str) -> list[str]:
    values = [model, f"{provider}/{model}"]
    if "/" in model:
        values.append(model.split("/", 1)[1])
    return list(
        dict.fromkeys(value.strip().lower() for value in values if value.strip())
    )


def resolve_price(
    provider: str,
    model: str,
    feed: dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve a LiteLLM entry without broad fuzzy matching.

    Exact key matches win. A suffix match is only accepted when it is unique,
    which handles feeds that prefix a model with a provider name while avoiding
    accidental matches between similarly named models.
    """

    candidates = _price_candidates(provider, model)
    lowered = {str(key).lower(): value for key, value in feed.items()}
    selected_key: str | None = None
    selected: Any = None
    confidence = "exact"
    for candidate in candidates:
        if candidate in lowered and isinstance(lowered[candidate], dict):
            selected_key, selected = candidate, lowered[candidate]
            break
    if selected is None:
        suffix_matches = [
            (key, value)
            for key, value in lowered.items()
            if isinstance(value, dict)
            and any(key.endswith("/" + candidate) for candidate in candidates)
        ]
        if len(suffix_matches) == 1:
            selected_key, selected = suffix_matches[0]
            confidence = "alias"
    if selected is None:
        return None

    input_rate = _as_price(selected.get("input_cost_per_token"))
    output_rate = _as_price(selected.get("output_cost_per_token"))
    cache_read_value = selected.get("cache_read_input_token_cost")
    if cache_read_value is None:
        cache_read_value = selected.get("cache_read_input_token_cost_per_token")
    cache_write_value = selected.get("cache_creation_input_token_cost")
    if cache_write_value is None:
        cache_write_value = selected.get("cache_write_input_token_cost")
    cache_read_rate = _as_price(cache_read_value)
    cache_write_rate = _as_price(cache_write_value)
    if input_rate is None and output_rate is None:
        return None
    # A feed without a cache-specific price still gives a useful conservative
    # estimate. The confidence label tells the UI this is an assumption.
    if cache_read_rate is None and input_rate is not None:
        cache_read_rate = input_rate
        confidence = "fallback"
    if cache_write_rate is None and input_rate is not None:
        cache_write_rate = input_rate
        confidence = "fallback"
    return {
        "input_price_usd_per_million": input_rate,
        "output_price_usd_per_million": output_rate,
        "cache_read_price_usd_per_million": cache_read_rate,
        "cache_write_price_usd_per_million": cache_write_rate,
        "price_source": selected_key,
        "price_confidence": confidence,
    }


def _feed(session: Session) -> dict[str, Any]:
    row = session.get(LLMPriceFeed, 1)
    if not row:
        return {}
    try:
        value = json.loads(row.payload_json)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _rates_for(session: Session, provider: str, model: str) -> dict[str, Any]:
    if provider in SUBSCRIPTION_PROVIDERS:
        return {
            "input_price_usd_per_million": None,
            "output_price_usd_per_million": None,
            "cache_read_price_usd_per_million": None,
            "cache_write_price_usd_per_million": None,
            "credit_price_usd_per_million": None,
            "credit_unit": "Included with subscription",
            "price_source": "subscription",
            "price_confidence": "not_applicable",
            "manual_override": False,
        }
    catalog = session.exec(
        select(LLMPriceCatalog).where(
            LLMPriceCatalog.provider == provider,
            LLMPriceCatalog.model == model,
        )
    ).first()
    if catalog:
        rates = {
            key: getattr(catalog, key)
            for key in (
                "input_price_usd_per_million",
                "output_price_usd_per_million",
                "cache_read_price_usd_per_million",
                "cache_write_price_usd_per_million",
                "credit_price_usd_per_million",
                "credit_unit",
                "price_source",
                "price_confidence",
                "manual_override",
            )
        }
        credit_price, credit_unit = _native_credit_defaults(provider)
        rates["credit_price_usd_per_million"] = (
            rates["credit_price_usd_per_million"]
            if rates["credit_price_usd_per_million"] is not None
            else credit_price
        )
        rates["credit_unit"] = rates["credit_unit"] or credit_unit
        return rates
    resolved = resolve_price(provider, model, _feed(session)) or {}
    credit_price, credit_unit = _native_credit_defaults(provider)
    resolved.setdefault("credit_price_usd_per_million", credit_price)
    resolved.setdefault("credit_unit", credit_unit)
    resolved.setdefault("manual_override", False)
    return resolved


def _cost(row: LLMUsageMonth) -> tuple[float, float, float]:
    """Return token, native-credit, and combined cost estimates.

    A missing price means that component cannot be estimated, but it should
    not make the totals for the other components disappear. Treating missing
    prices as zero keeps monthly and lifetime totals useful when a provider's
    price feed does not include every model or credit type.
    """

    token_cost = (
        row.input_tokens * (row.input_price_usd_per_million or 0)
        + row.output_tokens * (row.output_price_usd_per_million or 0)
        + row.cache_read_tokens * (row.cache_read_price_usd_per_million or 0)
        + row.cache_write_tokens * (row.cache_write_price_usd_per_million or 0)
    ) / 1_000_000
    credit_count = (
        row.ai_credits if row.provider == "github_copilot" else row.factory_credits
    )
    credit_cost = credit_count * (row.credit_price_usd_per_million or 0) / 1_000_000
    return token_cost, credit_cost, token_cost + credit_cost


def estimate_usage_cost(
    provider: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    ai_credits: float = 0,
    factory_credits: float = 0,
    rates: dict[str, Any] | None = None,
) -> dict[str, float | bool]:
    """Estimate the cost for one run-usage delta using resolved model rates."""

    if provider in SUBSCRIPTION_PROVIDERS:
        return {
            "estimated_token_cost_usd": 0.0,
            "estimated_credit_cost_usd": 0.0,
            "estimated_total_cost_usd": 0.0,
            "estimated_cost_available": False,
        }

    rates = rates or {}
    billable_input = max(0, int(input_tokens))
    if provider in _INCLUSIVE_INPUT_PROVIDERS:
        billable_input = max(
            0,
            billable_input - max(0, int(cache_read_tokens)) - max(0, int(cache_write_tokens)),
        )
    input_rate = rates.get("input_price_usd_per_million")
    output_rate = rates.get("output_price_usd_per_million")
    cache_read_rate = rates.get("cache_read_price_usd_per_million")
    cache_write_rate = rates.get("cache_write_price_usd_per_million")
    credit_rate = rates.get("credit_price_usd_per_million")
    input_count = billable_input
    output_count = max(0, int(output_tokens))
    cache_read_count = max(0, int(cache_read_tokens))
    cache_write_count = max(0, int(cache_write_tokens))
    credit_count = max(
        0.0,
        float(ai_credits if provider == "github_copilot" else factory_credits),
    )
    cost_available = any(
        count > 0 and rate is not None
        for count, rate in (
            (input_count, input_rate),
            (output_count, output_rate),
            (cache_read_count, cache_read_rate),
            (cache_write_count, cache_write_rate),
            (credit_count, credit_rate),
        )
    )
    token_cost = (
        input_count * (input_rate or 0)
        + output_count * (output_rate or 0)
        + cache_read_count * (cache_read_rate or 0)
        + cache_write_count * (cache_write_rate or 0)
    ) / 1_000_000
    credit_cost = (
        credit_count
        * (credit_rate or 0)
        / 1_000_000
    )
    return {
        "estimated_token_cost_usd": token_cost,
        "estimated_credit_cost_usd": credit_cost,
        "estimated_total_cost_usd": token_cost + credit_cost,
        "estimated_cost_available": cost_available,
    }


def _row_dict(row: LLMUsageMonth) -> dict[str, Any]:
    token_cost, credit_cost, total = _cost(row)
    return {
        "month": row.month,
        "provider": row.provider,
        "model": row.model,
        "base_url": row.base_url,
        "requests": row.requests,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "cache_read_tokens": row.cache_read_tokens,
        "cache_write_tokens": row.cache_write_tokens,
        "ai_credits": row.ai_credits,
        "factory_credits": row.factory_credits,
        "prices": {
            "input_usd_per_million": row.input_price_usd_per_million,
            "output_usd_per_million": row.output_price_usd_per_million,
            "cache_read_usd_per_million": row.cache_read_price_usd_per_million,
            "cache_write_usd_per_million": row.cache_write_price_usd_per_million,
            "credit_usd_per_million": row.credit_price_usd_per_million,
            "credit_unit": row.credit_unit,
            "source": row.price_source,
            "confidence": row.price_confidence,
            "manual_override": row.manual_override,
            "updated_at": row.price_updated_at.isoformat()
            if row.price_updated_at
            else None,
        },
        "estimated_token_cost_usd": token_cost,
        "estimated_credit_cost_usd": credit_cost,
        "estimated_total_cost_usd": total,
    }


def record_usage(
    provider: str,
    model: str,
    *,
    base_url: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    ai_credits: float = 0,
    factory_credits: float = 0,
    requests: int = 1,
    month: str | None = None,
) -> dict[str, Any]:
    """Atomically add one provider usage delta to the local monthly ledger."""

    provider = str(provider or "unknown")
    model = str(model or "unknown")
    base_url = str(base_url).strip() if base_url else None
    month = month or local_month()
    now = _utcnow()
    with Session(get_engine()) as session:
        rates = _rates_for(session, provider, model)
        values = {
            "month": month,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "requests": max(0, int(requests)),
            "input_tokens": max(0, int(input_tokens)),
            "output_tokens": max(0, int(output_tokens)),
            "cache_read_tokens": max(0, int(cache_read_tokens)),
            "cache_write_tokens": max(0, int(cache_write_tokens)),
            "ai_credits": max(0.0, float(ai_credits)),
            "factory_credits": max(0.0, float(factory_credits)),
            **rates,
            "created_at": now,
            "updated_at": now,
            "price_updated_at": now if rates else None,
        }
        stmt = sqlite_insert(LLMUsageMonth).values(**values)
        excluded = stmt.excluded
        table = LLMUsageMonth.__table__.c
        increments = {
            key: table[key] + getattr(excluded, key)
            for key in (
                "requests",
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "ai_credits",
                "factory_credits",
            )
        }
        # Keep the first observed endpoint with the row. Provider settings may
        # change later, but the historical usage row should remain stable.
        increments["base_url"] = func.coalesce(table.base_url, excluded.base_url)
        increments["updated_at"] = excluded.updated_at
        stmt = stmt.on_conflict_do_update(
            index_elements=["month", "provider", "model"],
            set_=increments,
        )
        session.exec(stmt)
        session.commit()
    return rates


def get_statistics(session: Session, month: str | None = None) -> dict[str, Any]:
    selected_month = month or local_month()
    rows = list(
        session.exec(
            select(LLMUsageMonth)
            .where(LLMUsageMonth.month == selected_month)
            .order_by(LLMUsageMonth.provider, LLMUsageMonth.model)
        )
    )
    row_values = [_row_dict(row) for row in rows]
    totals = {
        "requests": sum(row.requests for row in rows),
        "input_tokens": sum(row.input_tokens for row in rows),
        "output_tokens": sum(row.output_tokens for row in rows),
        "cache_read_tokens": sum(row.cache_read_tokens for row in rows),
        "cache_write_tokens": sum(row.cache_write_tokens for row in rows),
        "ai_credits": sum(row.ai_credits for row in rows),
        "factory_credits": sum(row.factory_credits for row in rows),
    }
    costs = [_cost(row) for row in rows]
    totals["estimated_token_cost_usd"] = (
        sum(cost[0] for cost in costs) if costs else None
    )
    totals["estimated_credit_cost_usd"] = (
        sum(cost[1] for cost in costs) if costs else None
    )
    totals["estimated_total_cost_usd"] = (
        sum(cost[2] for cost in costs) if costs else None
    )
    all_rows = list(session.exec(select(LLMUsageMonth)))
    lifetime_costs = [_cost(row) for row in all_rows]
    lifetime_token_cost = (
        sum(cost[0] for cost in lifetime_costs) if lifetime_costs else None
    )
    lifetime_credit_cost = (
        sum(cost[1] for cost in lifetime_costs) if lifetime_costs else None
    )
    lifetime = {
        "months": len({row.month for row in all_rows}),
        "requests": sum(row.requests for row in all_rows),
        "input_tokens": sum(row.input_tokens for row in all_rows),
        "output_tokens": sum(row.output_tokens for row in all_rows),
        "cache_read_tokens": sum(row.cache_read_tokens for row in all_rows),
        "cache_write_tokens": sum(row.cache_write_tokens for row in all_rows),
        "ai_credits": sum(row.ai_credits for row in all_rows),
        "factory_credits": sum(row.factory_credits for row in all_rows),
        "estimated_token_cost_usd": lifetime_token_cost,
        "estimated_credit_cost_usd": lifetime_credit_cost,
    }
    lifetime["estimated_total_cost_usd"] = (
        sum(cost[2] for cost in lifetime_costs) if lifetime_costs else None
    )
    months = list(
        session.exec(
            select(LLMUsageMonth.month).distinct().order_by(LLMUsageMonth.month.desc())
        )
    )
    feed = session.get(LLMPriceFeed, 1)
    return {
        "month": selected_month,
        "available_months": months,
        "totals": totals,
        "lifetime": lifetime,
        "rows": row_values,
        "price_feed": {
            "source": feed.source_url if feed else PRICE_FEED_URL,
            "fetched_at": feed.fetched_at.isoformat() if feed else None,
        },
    }


def refresh_prices(session: Session) -> dict[str, Any]:
    response = httpx.get(PRICE_FEED_URL, timeout=30.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or len(payload) > 100_000:
        raise ValueError("The downloaded price data was not a valid model price map")
    now = _utcnow()
    feed = session.get(LLMPriceFeed, 1)
    if feed:
        feed.source_url = PRICE_FEED_URL
        feed.payload_json = json.dumps(payload, separators=(",", ":"))
        feed.fetched_at = now
    else:
        session.add(
            LLMPriceFeed(
                id=1,
                source_url=PRICE_FEED_URL,
                payload_json=json.dumps(payload, separators=(",", ":")),
                fetched_at=now,
            )
        )
    current_month = local_month()
    updated = 0
    current_rows = list(
        session.exec(select(LLMUsageMonth).where(LLMUsageMonth.month == current_month))
    )
    for row in current_rows:
        if row.manual_override:
            continue
        rates = resolve_price(row.provider, row.model, payload) or {}
        credit_price, credit_unit = _native_credit_defaults(row.provider)
        for key, value in rates.items():
            setattr(row, key, value)
        if row.credit_price_usd_per_million is None:
            row.credit_price_usd_per_million = credit_price
        if row.credit_unit is None:
            row.credit_unit = credit_unit
        row.price_updated_at = now
        row.updated_at = now
        updated += 1
    for catalog in list(session.exec(select(LLMPriceCatalog))):
        if catalog.manual_override:
            continue
        rates = resolve_price(catalog.provider, catalog.model, payload) or {}
        for key, value in rates.items():
            setattr(catalog, key, value)
        catalog.updated_at = now
    session.commit()
    return {
        "updated_rows": updated,
        "fetched_at": now.isoformat(),
        "source": PRICE_FEED_URL,
    }


def set_prices(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    month = str(payload.get("month") or local_month())
    provider = str(payload.get("provider") or "").strip()
    model = str(payload.get("model") or "").strip()
    if not provider or not model or len(month) != 7:
        raise ValueError("month, provider, and model are required")
    allowed = {
        "input_price_usd_per_million",
        "output_price_usd_per_million",
        "cache_read_price_usd_per_million",
        "cache_write_price_usd_per_million",
        "credit_price_usd_per_million",
        "credit_unit",
    }
    values = {key: payload.get(key) for key in allowed if key in payload}
    for key, value in values.items():
        if key != "credit_unit" and value is not None and float(value) < 0:
            raise ValueError("prices cannot be negative")
    now = _utcnow()
    row = session.exec(
        select(LLMUsageMonth).where(
            LLMUsageMonth.month == month,
            LLMUsageMonth.provider == provider,
            LLMUsageMonth.model == model,
        )
    ).first()
    if row is None:
        row = LLMUsageMonth(month=month, provider=provider, model=model)
        session.add(row)
    for key, value in values.items():
        setattr(row, key, value)
    row.manual_override = True
    row.price_confidence = "manual"
    row.price_source = "manual"
    row.price_updated_at = now
    row.updated_at = now
    if payload.get("apply_to_future", True):
        catalog = session.exec(
            select(LLMPriceCatalog).where(
                LLMPriceCatalog.provider == provider,
                LLMPriceCatalog.model == model,
            )
        ).first()
        if catalog is None:
            catalog = LLMPriceCatalog(provider=provider, model=model)
            session.add(catalog)
        for key, value in values.items():
            setattr(catalog, key, value)
        catalog.manual_override = True
        catalog.price_confidence = "manual"
        catalog.price_source = "manual"
        catalog.updated_at = now
    session.commit()
    return _row_dict(row)


def reset_statistics(session: Session) -> None:
    session.exec(LLMUsageMonth.__table__.delete())
    session.commit()
