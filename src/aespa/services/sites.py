"""Service-layer CRUD for Sites + Credentials.

Pure functions taking a SQLModel ``Session``. The upcoming crawler can import
these helpers directly without going through HTTP.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.models import Credential, Site
from aespa.schemas import CredentialIn, SiteCreate, SiteUpdate


class SiteServiceError(Exception):
    """Base class for service-layer errors."""


class SiteNotFound(SiteServiceError):
    pass


class CredentialNotFound(SiteServiceError):
    pass


class DuplicateSiteName(SiteServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_sites(session: Session) -> list[Site]:
    return list(session.exec(select(Site).order_by(Site.name)).all())


def get_site(session: Session, site_id: int) -> Site:
    site = session.get(Site, site_id)
    if site is None:
        raise SiteNotFound(f"Site id={site_id} does not exist")
    # touch credentials so callers can read them outside the session if needed
    _ = site.credentials
    return site


def get_site_by_name(session: Session, name: str) -> Site | None:
    return session.exec(select(Site).where(Site.name == name)).first()


def _ensure_unique_name(session: Session, name: str, *, ignore_id: int | None = None) -> None:
    existing = get_site_by_name(session, name)
    if existing is None:
        return
    if ignore_id is not None and existing.id == ignore_id:
        return
    raise DuplicateSiteName(f"A site named {name!r} already exists")


def create_site(session: Session, payload: SiteCreate) -> Site:
    _ensure_unique_name(session, payload.name)

    site = Site(
        name=payload.name,
        base_url=str(payload.base_url),
        requires_auth=payload.requires_auth,
        login_url=str(payload.login_url) if payload.login_url else None,
        notes=payload.notes,
    )
    for cred in payload.credentials:
        site.credentials.append(
            Credential(username=cred.username, password=cred.password, label=cred.label)
        )

    session.add(site)
    session.commit()
    session.refresh(site)
    _ = site.credentials
    return site


def update_site(session: Session, site_id: int, payload: SiteUpdate) -> Site:
    site = get_site(session, site_id)
    _ensure_unique_name(session, payload.name, ignore_id=site.id)

    site.name = payload.name
    site.base_url = str(payload.base_url)
    site.requires_auth = payload.requires_auth
    site.login_url = str(payload.login_url) if payload.login_url else None
    site.notes = payload.notes
    site.updated_at = _utcnow()

    # Replace credentials list wholesale.
    site.credentials.clear()
    session.flush()
    for cred in payload.credentials:
        site.credentials.append(
            Credential(username=cred.username, password=cred.password, label=cred.label)
        )

    session.add(site)
    session.commit()
    session.refresh(site)
    _ = site.credentials
    return site


def delete_site(session: Session, site_id: int) -> None:
    from aespa.models import CrawledPage, PageLink, TestRun

    site = get_site(session, site_id)
    # Manually cascade to test runs and their children (SQLite FK off by default)
    runs = session.exec(select(TestRun).where(TestRun.site_id == site_id)).all()
    for run in runs:
        links = session.exec(select(PageLink).where(PageLink.test_run_id == run.id)).all()
        for lnk in links:
            session.delete(lnk)
        pages = session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run.id)).all()
        for pg in pages:
            session.delete(pg)
        session.delete(run)
    session.delete(site)
    session.commit()


def add_credential(session: Session, site_id: int, payload: CredentialIn) -> Credential:
    site = get_site(session, site_id)
    if not site.requires_auth:
        raise SiteServiceError("Cannot add credentials to a site that does not require auth")
    cred = Credential(
        site_id=site.id,
        username=payload.username,
        password=payload.password,
        label=payload.label,
    )
    site.updated_at = _utcnow()
    session.add(cred)
    session.add(site)
    session.commit()
    session.refresh(cred)
    return cred


def delete_credential(session: Session, site_id: int, credential_id: int) -> None:
    cred = session.get(Credential, credential_id)
    if cred is None or cred.site_id != site_id:
        raise CredentialNotFound(
            f"Credential id={credential_id} not found for site {site_id}"
        )
    session.delete(cred)
    session.commit()
