from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from aespa.db import get_session
from aespa.models import Site
from aespa.schemas import (
    CredentialIn,
    CredentialOut,
    SiteCreate,
    SiteDetail,
    SiteSummary,
    SiteUpdate,
)
from aespa.services import sites as sites_service


router = APIRouter(prefix="/api/sites", tags=["sites"])


def _to_summary(site: Site) -> SiteSummary:
    return SiteSummary(
        id=site.id,  # type: ignore[arg-type]
        name=site.name,
        base_url=site.base_url,
        requires_auth=site.requires_auth,
        login_url=site.login_url,
        notes=site.notes,
        created_at=site.created_at,
        updated_at=site.updated_at,
        credential_count=len(site.credentials),
    )


def _to_detail(site: Site) -> SiteDetail:
    return SiteDetail(
        id=site.id,  # type: ignore[arg-type]
        name=site.name,
        base_url=site.base_url,
        requires_auth=site.requires_auth,
        login_url=site.login_url,
        notes=site.notes,
        created_at=site.created_at,
        updated_at=site.updated_at,
        credentials=[CredentialOut.model_validate(c) for c in site.credentials],
    )


@router.get("", response_model=list[SiteSummary])
def list_sites(session: Session = Depends(get_session)) -> list[SiteSummary]:
    return [_to_summary(s) for s in sites_service.list_sites(session)]


@router.post("", response_model=SiteDetail, status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate, session: Session = Depends(get_session)) -> SiteDetail:
    try:
        site = sites_service.create_site(session, payload)
    except sites_service.DuplicateSiteName as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_detail(site)


@router.get("/{site_id}", response_model=SiteDetail)
def get_site(site_id: int, session: Session = Depends(get_session)) -> SiteDetail:
    try:
        site = sites_service.get_site(session, site_id)
    except sites_service.SiteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_detail(site)


@router.put("/{site_id}", response_model=SiteDetail)
def update_site(
    site_id: int,
    payload: SiteUpdate,
    session: Session = Depends(get_session),
) -> SiteDetail:
    try:
        site = sites_service.update_site(session, site_id, payload)
    except sites_service.SiteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except sites_service.DuplicateSiteName as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_detail(site)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: int, session: Session = Depends(get_session)) -> None:
    try:
        sites_service.delete_site(session, site_id)
    except sites_service.SiteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{site_id}/credentials",
    response_model=CredentialOut,
    status_code=status.HTTP_201_CREATED,
)
def add_credential(
    site_id: int,
    payload: CredentialIn,
    session: Session = Depends(get_session),
) -> CredentialOut:
    try:
        cred = sites_service.add_credential(session, site_id, payload)
    except sites_service.SiteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except sites_service.SiteServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return CredentialOut.model_validate(cred)


@router.delete(
    "/{site_id}/credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_credential(
    site_id: int,
    credential_id: int,
    session: Session = Depends(get_session),
) -> None:
    try:
        sites_service.delete_credential(session, site_id, credential_id)
    except sites_service.CredentialNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
