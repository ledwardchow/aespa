from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel as _BaseModel
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import SavedCrawl, Site, TestRun
from aespa.schemas import (
    CredentialIn,
    CredentialOut,
    SavedCrawlOut,
    SavedCrawlUpdate,
    SiteCreate,
    SiteDetail,
    SiteSummary,
    SiteUpdate,
)
from aespa.services import saved_crawls as saved_crawls_svc
from aespa.services import sites as sites_service
from aespa.services.crawl_archives import ArchiveError

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
        scope_hosts=json.loads(site.scope_hosts or "[]"),
    )


def _to_detail(site: Site) -> SiteDetail:
    return SiteDetail(
        id=site.id,  # type: ignore[arg-type]
        name=site.name,
        base_url=site.base_url,
        requires_auth=site.requires_auth,
        login_url=site.login_url,
        notes=site.notes,
        scan_guidance=site.scan_guidance,
        created_at=site.created_at,
        updated_at=site.updated_at,
        credentials=[CredentialOut.model_validate(c) for c in site.credentials],
        scope_hosts=json.loads(site.scope_hosts or "[]"),
    )


@router.get("", response_model=list[SiteSummary])
def list_sites(session: Session = Depends(get_session)) -> list[SiteSummary]:
    return [_to_summary(s) for s in sites_service.list_sites(session)]


@router.post("", response_model=SiteDetail, status_code=status.HTTP_201_CREATED)
def create_site(
    payload: SiteCreate, session: Session = Depends(get_session)
) -> SiteDetail:
    try:
        site = sites_service.create_site(session, payload)
    except sites_service.DuplicateSiteName as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _to_detail(site)


@router.get("/{site_id}", response_model=SiteDetail)
def get_site(site_id: int, session: Session = Depends(get_session)) -> SiteDetail:
    try:
        site = sites_service.get_site(session, site_id)
    except sites_service.SiteNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except sites_service.DuplicateSiteName as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _to_detail(site)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: int, session: Session = Depends(get_session)) -> None:
    try:
        sites_service.delete_site(session, site_id)
    except sites_service.SiteNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except sites_service.SiteReferencedBySystem as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


class _ScopeHostsPayload(_BaseModel):
    scope_hosts: list[str]


@router.put("/{site_id}/scope-hosts")
def update_scope_hosts(
    site_id: int,
    payload: _ScopeHostsPayload,
    session: Session = Depends(get_session),
) -> dict:
    site = session.get(Site, site_id)
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )
    from aespa.services.scope import normalize_scope_entries

    normalized = normalize_scope_entries(payload.scope_hosts, default_url=site.base_url)
    site.scope_hosts = json.dumps(normalized)
    session.add(site)
    session.commit()
    return {"scope_hosts": normalized}


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Export / Import ──────────────────────────────────────────────────────────


@router.get("/{site_id}/export")
def export_site(site_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    """Download a portable JSON bundle for the site and all its data."""
    try:
        bundle = sites_service.export_site(session, site_id)
    except sites_service.SiteNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    site_name = bundle["site"]["name"]
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in site_name)
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}.aespa-site.json"'
    }
    return JSONResponse(content=bundle, headers=headers)


@router.post("/import", response_model=SiteDetail, status_code=status.HTTP_201_CREATED)
async def import_site(
    request: Request, session: Session = Depends(get_session)
) -> SiteDetail:
    """Create a site from a bundle previously produced by the export endpoint."""
    try:
        body = await request.body()
        bundle = json.loads(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON body: {exc}",
        ) from exc
    try:
        site = sites_service.import_site(session, bundle)
    except sites_service.SiteServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return _to_detail(site)


# ── Saved crawls ─────────────────────────────────────────────────────────────


def _site_or_404(session: Session, site_id: int) -> Site:
    site = session.get(Site, site_id)
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )
    return site


def _saved_crawl_out(saved: SavedCrawl, existing_run_ids: set[int]) -> SavedCrawlOut:
    return SavedCrawlOut.model_validate(saved).model_copy(
        update={"source_run_exists": saved.source_run_id in existing_run_ids}
    )


def _site_run_ids(session: Session, site_id: int) -> set[int]:
    return set(session.exec(select(TestRun.id).where(TestRun.site_id == site_id)))


def _saved_crawl_or_error(session: Session, site_id: int, saved_id: int) -> SavedCrawl:
    try:
        return saved_crawls_svc.get_for_site(session, site_id, saved_id)
    except ArchiveError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@router.get("/{site_id}/saved-crawls", response_model=list[SavedCrawlOut])
def list_saved_crawls(
    site_id: int, session: Session = Depends(get_session)
) -> list[SavedCrawlOut]:
    _site_or_404(session, site_id)
    run_ids = _site_run_ids(session, site_id)
    return [
        _saved_crawl_out(saved, run_ids)
        for saved in saved_crawls_svc.list_for_site(session, site_id)
    ]


@router.post(
    "/{site_id}/saved-crawls/upload",
    response_model=SavedCrawlOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_saved_crawl(
    site_id: int,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> SavedCrawlOut:
    """Add an existing crawl export file to the site's saved crawls."""
    site = _site_or_404(session, site_id)
    try:
        payload = json.loads(await file.read())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400, detail="Crawl export must be valid JSON"
        ) from exc
    label = (name or "").strip() or (file.filename or "Uploaded crawl")
    try:
        saved = saved_crawls_svc.save_from_file(
            session, site, payload, label[:200], (notes or "").strip() or None
        )
    except ArchiveError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    return _saved_crawl_out(saved, set())


@router.patch("/{site_id}/saved-crawls/{saved_id}", response_model=SavedCrawlOut)
def update_saved_crawl(
    site_id: int,
    saved_id: int,
    payload: SavedCrawlUpdate,
    session: Session = Depends(get_session),
) -> SavedCrawlOut:
    saved = _saved_crawl_or_error(session, site_id, saved_id)
    saved = saved_crawls_svc.update(
        session, saved, name=payload.name, notes=payload.notes
    )
    return _saved_crawl_out(saved, _site_run_ids(session, site_id))


@router.delete(
    "/{site_id}/saved-crawls/{saved_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_saved_crawl(
    site_id: int, saved_id: int, session: Session = Depends(get_session)
) -> None:
    saved = _saved_crawl_or_error(session, site_id, saved_id)
    saved_crawls_svc.delete(session, saved)


@router.get("/{site_id}/saved-crawls/{saved_id}/export")
def export_saved_crawl(
    site_id: int, saved_id: int, session: Session = Depends(get_session)
) -> JSONResponse:
    saved = _saved_crawl_or_error(session, site_id, saved_id)
    try:
        archive = saved_crawls_svc.archive_payload(saved)
    except ArchiveError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    filename = f"aespa-saved-crawl-{saved.id}.json"
    return JSONResponse(
        archive,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
