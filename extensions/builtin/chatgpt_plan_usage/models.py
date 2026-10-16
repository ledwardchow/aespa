from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import MetaData
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


metadata = MetaData()


class ExtensionModel(SQLModel):
    metadata = metadata


class CounterState(ExtensionModel, table=True):
    """Last cumulative plan counters read from AESPA's usage ledger."""

    __tablename__ = "planusage_counter_state"
    provider: str = Field(primary_key=True)
    model: str = Field(primary_key=True)
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    updated_at: datetime = Field(default_factory=now)


class UsageDelta(ExtensionModel, table=True):
    """Usage added between two samples, stamped with the later sample time."""

    __tablename__ = "planusage_usage_delta"
    id: int | None = Field(default=None, primary_key=True)
    sampled_at: datetime = Field(default_factory=now, index=True)
    provider: str = Field(index=True)
    model: str = Field(index=True)
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


class Reading(ExtensionModel, table=True):
    """A plan usage percentage, typed in by the user or read from Codex."""

    __tablename__ = "planusage_reading"
    id: int | None = Field(default=None, primary_key=True)
    window: str = Field(index=True)
    used_percent: float
    observed_at: datetime = Field(index=True)
    resets_at: datetime | None = None
    note: str = ""
    source: str = "manual"
    created_at: datetime = Field(default_factory=now)


class Meta(ExtensionModel, table=True):
    __tablename__ = "planusage_meta"
    key: str = Field(primary_key=True)
    value: str
