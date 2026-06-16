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
    """Delete a collection and every row that hangs off it.

    Like the run ids, ``ApiCollection`` ids are reused by SQLite, so any child
    left behind (runs, findings, endpoints, uploaded docs, …) would resurface
    under a newly created collection that reuses the freed id.  Cascade through
    every child: API/SAST runs go via the shared ``run_cleanup`` helpers so their
    findings/traffic/logs are cleaned too.
    """
    from pathlib import Path

    from aespa.models import (
        ApiCredential,
        ApiDocument,
        ApiEndpoint,
        ApiTestRun,
        SastRun,
        ScanLead,
    )
    from aespa.services import run_cleanup

    collection = get_collection(session, collection_id)

    for run in session.exec(
        select(ApiTestRun).where(ApiTestRun.collection_id == collection_id)
    ).all():
        run_cleanup.cascade_delete_api_run(session, run.id)
    for run in session.exec(
        select(SastRun).where(SastRun.collection_id == collection_id)
    ).all():
        run_cleanup.cascade_delete_sast_run(session, run.id)
    # Leads carry a collection_id of their own; sweep any not tied to a SAST run.
    for lead in session.exec(
        select(ScanLead).where(ScanLead.collection_id == collection_id)
    ).all():
        session.delete(lead)
    for ep in session.exec(
        select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
    ).all():
        session.delete(ep)
    for cred in session.exec(
        select(ApiCredential).where(ApiCredential.collection_id == collection_id)
    ).all():
        session.delete(cred)
    for doc in session.exec(
        select(ApiDocument).where(ApiDocument.collection_id == collection_id)
    ).all():
        try:
            path = Path(doc.stored_path)
            if path.is_file():
                path.unlink()
        except OSError:
            pass
        session.delete(doc)

    session.delete(collection)
    session.commit()
