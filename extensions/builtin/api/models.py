"""Tables in the API extension's own database."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Engine, MetaData, UniqueConstraint, inspect, text
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


metadata = MetaData()


class ExtensionModel(SQLModel):
    metadata = metadata


class ApiToken(ExtensionModel, table=True):
    """An access token. Requests are matched on the SHA-256 hash."""

    __tablename__ = "integrationapi_token"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    token_hash: str = Field(index=True, unique=True)
    token_prefix: str
    # Kept so the settings page can show the token again. Null for tokens
    # created before AESPA kept them.
    token_value: Optional[str] = None
    scopes_json: str = "[]"
    # "own": only scans this token created. "all": every scan of a kind its
    # scopes allow, including scans started in AESPA.
    scan_access: str = "own"
    webhook_url: Optional[str] = None
    # Kept in clear text because AESPA needs it to sign callbacks.
    webhook_secret: Optional[str] = None
    created_at: datetime = Field(default_factory=now)
    last_used_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None


class ApiScan(ExtensionModel, table=True):
    """A run started through the API and the token that owns it."""

    __tablename__ = "integrationapi_scan"
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(index=True, unique=True)
    kind: str = Field(index=True)  # web | sast
    token_id: int = Field(index=True)
    scan_after_crawl: bool = False
    start_options_json: str = "{}"
    callback_url: Optional[str] = None
    callback_secret: Optional[str] = None
    callback_events_json: str = "[]"
    last_state: Optional[str] = None
    last_phase: Optional[str] = None
    last_percent: Optional[int] = None
    last_progress_sent_at: Optional[datetime] = None
    finished: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=now)


class ApiDelivery(ExtensionModel, table=True):
    """A callback waiting to be sent, sent, or given up on."""

    __tablename__ = "integrationapi_delivery"
    id: Optional[int] = Field(default=None, primary_key=True)
    delivery_id: str = Field(index=True, unique=True)
    scan_id: int = Field(index=True)
    event: str
    url: str
    payload_json: str
    status: str = Field(default="pending", index=True)  # pending|delivered|failed
    attempts: int = 0
    next_attempt_at: datetime = Field(default_factory=now, index=True)
    last_status_code: Optional[int] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=now)
    delivered_at: Optional[datetime] = None


class ApiIdempotency(ExtensionModel, table=True):
    """The saved response for a request sent with an Idempotency-Key."""

    __tablename__ = "integrationapi_idempotency"
    __table_args__ = (UniqueConstraint("token_id", "key"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    token_id: int = Field(index=True)
    key: str
    request_hash: str
    status_code: Optional[int] = None
    response_json: Optional[str] = None
    created_at: datetime = Field(default_factory=now, index=True)


# Columns added after the first release, with the SQL that adds each one to an
# existing database.
_ADDED_COLUMNS = {
    "integrationapi_token": {
        "token_value": "VARCHAR",
        "scan_access": "VARCHAR NOT NULL DEFAULT 'own'",
        "deactivated_at": "DATETIME",
    },
}


def upgrade(engine: Engine) -> None:
    """Bring an existing database up to the current tables. Safe to repeat."""
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                    )
            if "revoked_at" in existing:
                # Revoked tokens from before tokens could be turned back on.
                connection.execute(
                    text(
                        f"UPDATE {table} SET deactivated_at = revoked_at "
                        "WHERE revoked_at IS NOT NULL AND deactivated_at IS NULL"
                    )
                )
