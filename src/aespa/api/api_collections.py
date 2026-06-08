from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel as _BaseModel
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import ApiCollection, ApiCredential, ApiEndpoint
from aespa.schemas import (
    ApiCollectionCreate,
    ApiCollectionDetail,
    ApiCollectionSummary,
    ApiCollectionUpdate,
    ApiCredentialCreate,
    ApiCredentialOut,
    ApiDocumentOut,
    ApiEndpointOut,
)
from aespa.services import api_collections as api_collections_service
from aespa.services import api_documents as api_documents_service
from aespa.services import api_docs as api_docs_service
from aespa.services import api_readiness as api_readiness_service


router = APIRouter(prefix="/api/api-collections", tags=["api-collections"])


def _to_summary(collection: ApiCollection, session: Session) -> ApiCollectionSummary:
    return ApiCollectionSummary(
        id=collection.id,  # type: ignore[arg-type]
        name=collection.name,
        base_url=collection.base_url,
        description=collection.description,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        endpoint_count=api_docs_service.count_endpoints(session, collection.id),
        document_count=api_documents_service.count_documents(session, collection.id),
        servers=json.loads(collection.servers or "[]"),
        scope_hosts=json.loads(collection.scope_hosts or "[]"),
    )


def _to_detail(collection: ApiCollection) -> ApiCollectionDetail:
    return ApiCollectionDetail(
        id=collection.id,  # type: ignore[arg-type]
        name=collection.name,
        base_url=collection.base_url,
        description=collection.description,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        servers=json.loads(collection.servers or "[]"),
        scope_hosts=json.loads(collection.scope_hosts or "[]"),
    )


@router.get("", response_model=list[ApiCollectionSummary])
def list_collections(
    session: Session = Depends(get_session),
) -> list[ApiCollectionSummary]:
    return [
        _to_summary(c, session)
        for c in api_collections_service.list_collections(session)
    ]


@router.post(
    "", response_model=ApiCollectionDetail, status_code=status.HTTP_201_CREATED
)
def create_collection(
    payload: ApiCollectionCreate, session: Session = Depends(get_session)
) -> ApiCollectionDetail:
    try:
        collection = api_collections_service.create_collection(session, payload)
    except api_collections_service.DuplicateApiCollectionName as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _to_detail(collection)


@router.get("/{collection_id}", response_model=ApiCollectionDetail)
def get_collection(
    collection_id: int, session: Session = Depends(get_session)
) -> ApiCollectionDetail:
    try:
        collection = api_collections_service.get_collection(session, collection_id)
    except api_collections_service.ApiCollectionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _to_detail(collection)


@router.put("/{collection_id}", response_model=ApiCollectionDetail)
def update_collection(
    collection_id: int,
    payload: ApiCollectionUpdate,
    session: Session = Depends(get_session),
) -> ApiCollectionDetail:
    try:
        collection = api_collections_service.update_collection(
            session, collection_id, payload
        )
    except api_collections_service.ApiCollectionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except api_collections_service.DuplicateApiCollectionName as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _to_detail(collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int, session: Session = Depends(get_session)
) -> None:
    try:
        api_collections_service.delete_collection(session, collection_id)
    except api_collections_service.ApiCollectionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


class _ScopeHostsPayload(_BaseModel):
    scope_hosts: list[str]


@router.put("/{collection_id}/scope-hosts")
def update_scope_hosts(
    collection_id: int,
    payload: _ScopeHostsPayload,
    session: Session = Depends(get_session),
) -> dict:
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API collection not found"
        )
    collection.scope_hosts = json.dumps(payload.scope_hosts)
    session.add(collection)
    session.commit()
    return {"scope_hosts": payload.scope_hosts}


# ── Documents ────────────────────────────────────────────────────────────────


def _doc_to_out(doc) -> ApiDocumentOut:
    return ApiDocumentOut.model_validate(doc)


@router.get("/{collection_id}/documents", response_model=list[ApiDocumentOut])
def list_documents(
    collection_id: int, session: Session = Depends(get_session)
) -> list[ApiDocumentOut]:
    try:
        docs = api_documents_service.list_documents(session, collection_id)
    except api_documents_service.ApiCollectionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return [_doc_to_out(d) for d in docs]


@router.post(
    "/{collection_id}/documents",
    response_model=list[ApiDocumentOut],
    status_code=status.HTTP_201_CREATED,
)
async def upload_documents(
    collection_id: int,
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
) -> list[ApiDocumentOut]:
    created = []
    for upload in files:
        content = await upload.read()
        try:
            doc = api_documents_service.create_document(
                session,
                collection_id,
                filename=upload.filename or "upload",
                content=content,
                content_type=upload.content_type,
            )
        except api_documents_service.ApiCollectionNotFound as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except (
            api_documents_service.EmptyUpload,
            api_documents_service.UploadTooLarge,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        # Parse immediately using the same session so the response reflects
        # the real status. parse_document catches its own errors internally.
        await api_docs_service.parse_document(session, collection_id, doc.id)
        session.refresh(doc)
        created.append(_doc_to_out(doc))
    return created


@router.post(
    "/{collection_id}/documents/{document_id}/parse",
    response_model=ApiDocumentOut,
)
async def parse_document(
    collection_id: int,
    document_id: int,
    session: Session = Depends(get_session),
) -> ApiDocumentOut:
    """Re-trigger parsing for a single document."""
    try:
        _ = api_documents_service.get_document(session, collection_id, document_id)
    except api_documents_service.ApiDocumentNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await api_docs_service.parse_document(session, collection_id, document_id)
    doc = api_documents_service.get_document(session, collection_id, document_id)
    return _doc_to_out(doc)


@router.get("/{collection_id}/documents/{document_id}/download")
def download_document(
    collection_id: int,
    document_id: int,
    session: Session = Depends(get_session),
) -> Response:
    try:
        doc, content = api_documents_service.read_document_bytes(
            session, collection_id, document_id
        )
    except api_documents_service.ApiDocumentNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    media_type = doc.content_type or "application/octet-stream"
    headers = {
        "Content-Disposition": f'attachment; filename="{doc.filename}"',
    }
    return Response(content=content, media_type=media_type, headers=headers)


@router.delete(
    "/{collection_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    collection_id: int,
    document_id: int,
    session: Session = Depends(get_session),
) -> None:
    try:
        api_documents_service.delete_document(session, collection_id, document_id)
    except api_documents_service.ApiDocumentNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/{collection_id}/endpoints", response_model=list[ApiEndpointOut])
def list_endpoints(
    collection_id: int,
    session: Session = Depends(get_session),
) -> list[ApiEndpointOut]:
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API collection not found")
    endpoints = session.exec(
        select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
    ).all()
    return [ApiEndpointOut.model_validate(ep) for ep in endpoints]


class _ScopePayload(_BaseModel):
    in_scope: bool


@router.patch("/{collection_id}/endpoints/{endpoint_id}/scope", response_model=ApiEndpointOut)
def patch_endpoint_scope(
    collection_id: int,
    endpoint_id: int,
    payload: _ScopePayload,
    session: Session = Depends(get_session),
) -> ApiEndpointOut:
    ep = session.get(ApiEndpoint, endpoint_id)
    if ep is None or ep.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    ep.in_scope = payload.in_scope
    session.add(ep)
    session.commit()
    session.refresh(ep)
    return ApiEndpointOut.model_validate(ep)


# ── Credentials ───────────────────────────────────────────────────────────────


@router.get("/{collection_id}/credentials", response_model=list[ApiCredentialOut])
def list_credentials(
    collection_id: int,
    session: Session = Depends(get_session),
) -> list[ApiCredentialOut]:
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API collection not found")
    creds = session.exec(
        select(ApiCredential).where(ApiCredential.collection_id == collection_id)
    ).all()
    return [ApiCredentialOut.model_validate(c) for c in creds]


@router.post(
    "/{collection_id}/credentials",
    response_model=ApiCredentialOut,
    status_code=status.HTTP_201_CREATED,
)
def create_credential(
    collection_id: int,
    payload: ApiCredentialCreate,
    session: Session = Depends(get_session),
) -> ApiCredentialOut:
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API collection not found")
    cred = ApiCredential(
        collection_id=collection_id,
        scheme=payload.scheme,
        name=payload.name,
        value=payload.value,
        label=payload.label,
        scope=payload.scope,
        endpoint_id=payload.endpoint_id,
        auth_endpoint=payload.auth_endpoint,
    )
    session.add(cred)
    session.commit()
    session.refresh(cred)
    return ApiCredentialOut.model_validate(cred)


@router.delete(
    "/{collection_id}/credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_credential(
    collection_id: int,
    credential_id: int,
    session: Session = Depends(get_session),
) -> None:
    cred = session.get(ApiCredential, credential_id)
    if cred is None or cred.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    session.delete(cred)
    session.commit()


# ── Readiness assessment ────────────────────────────────────────────────────────────────


@router.post("/{collection_id}/readiness", status_code=status.HTTP_200_OK)
async def run_readiness(
    collection_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Run (or re-run) the LLM-driven readiness assessment for this collection."""
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API collection not found"
        )
    try:
        result = await api_readiness_service.assess_readiness(session, collection_id)
    except api_readiness_service.ReadinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return result


@router.get("/{collection_id}/readiness")
def get_readiness(
    collection_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Return the most recent readiness assessment result, or a not-assessed stub."""
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API collection not found"
        )
    result = api_readiness_service.get_readiness(session, collection_id)
    if result is None:
        return {"status": "not_assessed"}
    return result


# ── Purge all parsed data ─────────────────────────────────────────────────────


@router.delete("/{collection_id}/data", status_code=status.HTTP_200_OK)
def purge_collection_data(
    collection_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Delete all endpoints and credentials parsed for this collection.

    Documents and the collection itself are kept.  Use this to clear
    duplicates caused by uploading the same file multiple times, then
    re-parse the documents you want to keep.
    """
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API collection not found"
        )

    endpoints = session.exec(
        select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
    ).all()
    ep_count = len(endpoints)
    for ep in endpoints:
        session.delete(ep)

    credentials = session.exec(
        select(ApiCredential).where(ApiCredential.collection_id == collection_id)
    ).all()
    cred_count = len(credentials)
    for cred in credentials:
        session.delete(cred)

    # Clear persisted readiness too — it's now stale
    collection.readiness_json = None
    session.add(collection)
    session.commit()

    return {
        "endpoints_deleted": ep_count,
        "credentials_deleted": cred_count,
    }
