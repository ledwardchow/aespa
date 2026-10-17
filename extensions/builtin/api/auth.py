"""Access tokens and request checks."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select

from aespa.extensions import ExtensionDataStore

from .models import ApiToken, now

SCOPES = ("sast", "web", "sites")
TOKEN_PREFIX = "aespa_"
_LAST_USED_INTERVAL = timedelta(minutes=1)
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_FORWARDING_HEADERS = ("x-forwarded-for", "forwarded", "x-real-ip", "cf-connecting-ip")

bearer = HTTPBearer(
    auto_error=False,
    scheme_name="bearerAuth",
    description="An API token created on the API extension's settings page.",
)


@dataclass(frozen=True)
class Caller:
    token_id: int
    scopes: frozenset[str]
    sees_all_scans: bool = False


def aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def new_secret() -> str:
    return "whsec_" + secrets.token_urlsafe(32)


def token_scopes(row: ApiToken) -> list[str]:
    try:
        values = json.loads(row.scopes_json or "[]")
    except (TypeError, ValueError):
        return []
    return [value for value in values if value in SCOPES]


def authenticate(store: ExtensionDataStore, token: str | None) -> Caller:
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Send an API token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with store.session() as session:
        row = session.exec(
            select(ApiToken).where(ApiToken.token_hash == hash_token(token))
        ).first()
        if row is None or row.deactivated_at is not None:
            raise HTTPException(
                status_code=401,
                detail="The API token is not valid or has been turned off.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        current = now()
        last_used = aware(row.last_used_at)
        if last_used is None or current - last_used > _LAST_USED_INTERVAL:
            row.last_used_at = current
            session.add(row)
            session.commit()
        return Caller(row.id, frozenset(token_scopes(row)), row.scan_access == "all")


def scope_dependency(store: ExtensionDataStore):
    """Build ``require(*scopes)`` for routes that need a token."""

    def require(*scopes: str):
        def check(
            credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        ) -> Caller:
            caller = authenticate(
                store, credentials.credentials if credentials else None
            )
            missing = [scope for scope in scopes if scope not in caller.scopes]
            if missing:
                raise HTTPException(
                    status_code=403,
                    detail=f"This token does not have the {', '.join(missing)} scope.",
                )
            return caller

        return check

    return require


def require_local_admin(request: Request) -> None:
    """Allow token management only from AESPA's own page on this computer.

    A reverse proxy or tunnel that forwards the API adds forwarding headers or
    connects from elsewhere, so token management stays unavailable through it.
    """
    client = request.client.host if request.client else ""
    if client not in _LOCAL_HOSTS or any(
        request.headers.get(name) for name in _FORWARDING_HEADERS
    ):
        raise HTTPException(
            status_code=403,
            detail="Manage API tokens from AESPA on this computer.",
        )
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != f"{request.url.scheme}://{request.url.netloc}":
        raise HTTPException(
            status_code=403, detail="Cross-site requests are not allowed."
        )
