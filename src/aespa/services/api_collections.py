"""Service-layer CRUD for API Collections.

Pure functions taking a SQLModel ``Session``, mirroring ``services.sites``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.models import ApiCollection
from aespa.schemas import ApiCollectionCreate, ApiCollectionUpdate


class ApiCollectionServiceError(Exception):
    """Base class for service-layer errors."""


class ApiCollectionNotFound(ApiCollectionServiceError):
    pass


class DuplicateApiCollectionName(ApiCollectionServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_collections(session: Session) -> list[ApiCollection]:
    return list(session.exec(select(ApiCollection).order_by(ApiCollection.name)).all())


def get_collection(session: Session, collection_id: int) -> ApiCollection:
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise ApiCollectionNotFound(f"API collection id={collection_id} does not exist")
    return collection


def get_collection_by_name(session: Session, name: str) -> ApiCollection | None:
    return session.exec(select(ApiCollection).where(ApiCollection.name == name)).first()


def _ensure_unique_name(
    session: Session, name: str, *, ignore_id: int | None = None
) -> None:
    existing = get_collection_by_name(session, name)
    if existing is None:
        return
    if ignore_id is not None and existing.id == ignore_id:
        return
    raise DuplicateApiCollectionName(f"An API collection named {name!r} already exists")


def create_collection(session: Session, payload: ApiCollectionCreate) -> ApiCollection:
    _ensure_unique_name(session, payload.name)

    collection = ApiCollection(
        name=payload.name,
        base_url=str(payload.base_url),
        description=payload.description,
        servers=json.dumps([str(s) for s in payload.servers]),
        scope_hosts=json.dumps(payload.scope_hosts),
    )
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def update_collection(
    session: Session, collection_id: int, payload: ApiCollectionUpdate
) -> ApiCollection:
    collection = get_collection(session, collection_id)
    _ensure_unique_name(session, payload.name, ignore_id=collection.id)

    collection.name = payload.name
    collection.base_url = str(payload.base_url)
    collection.description = payload.description
    collection.servers = json.dumps([str(s) for s in payload.servers])
    collection.scope_hosts = json.dumps(payload.scope_hosts)
    collection.updated_at = _utcnow()

    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def delete_collection(session: Session, collection_id: int) -> None:
    collection = get_collection(session, collection_id)
    session.delete(collection)
    session.commit()
