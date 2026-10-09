"""Crawls saved on a site so later runs can skip the crawl phase."""

from __future__ import annotations

import gzip
import json

from sqlalchemy.orm import defer
from sqlmodel import Session, select

from aespa.models import CrawledPage, SavedCrawl, Site, TestRun, TestRunStatus
from aespa.services import crawl_archives
from aespa.services.crawl_archives import ArchiveError


def _store(
    session: Session,
    site: Site,
    archive: dict,
    *,
    name: str,
    notes: str | None,
    source_run_id: int | None,
    crawler_mode: str,
) -> SavedCrawl:
    blob = gzip.compress(json.dumps(archive).encode("utf-8"))
    saved = SavedCrawl(
        site_id=site.id,  # type: ignore[arg-type]
        name=name,
        notes=notes or None,
        source_run_id=source_run_id,
        crawler_mode=crawler_mode,
        page_count=len(archive.get("crawl", {}).get("pages", [])),
        size_bytes=len(blob),
        archive_gz=blob,
    )
    session.add(saved)
    session.commit()
    session.refresh(saved)
    return saved


def save_from_run(
    session: Session, run: TestRun, name: str, notes: str | None = None
) -> SavedCrawl:
    if run.status == TestRunStatus.running:
        raise ArchiveError(status=409, message="Stop the run before saving its crawl")
    if not session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run.id)
    ).first():
        raise ArchiveError(status=400, message="There is no crawl data to save")
    site = session.get(Site, run.site_id)
    if site is None:
        raise ArchiveError(status=404, message=f"Site {run.site_id} not found")
    archive = crawl_archives.build_archive(session, run)
    return _store(
        session,
        site,
        archive,
        name=name,
        notes=notes,
        source_run_id=run.id,
        crawler_mode=run.crawler_mode,
    )


def save_from_file(
    session: Session, site: Site, payload: object, name: str, notes: str | None = None
) -> SavedCrawl:
    crawl_archives.validate_archive(payload, site.base_url)
    assert isinstance(payload, dict)
    source = payload.get("source") or {}
    crawler_mode = source.get("crawler_mode") if isinstance(source, dict) else None
    if crawler_mode not in ("url", "interactive"):
        crawler_mode = "url"
    return _store(
        session,
        site,
        payload,
        name=name,
        notes=notes,
        source_run_id=None,
        crawler_mode=crawler_mode,
    )


def list_for_site(session: Session, site_id: int) -> list[SavedCrawl]:
    return list(
        session.exec(
            select(SavedCrawl)
            .where(SavedCrawl.site_id == site_id)
            .options(defer(SavedCrawl.archive_gz))  # type: ignore[arg-type]
            .order_by(SavedCrawl.created_at.desc())  # type: ignore[attr-defined]
        )
    )


def get_for_site(session: Session, site_id: int, saved_id: int) -> SavedCrawl:
    saved = session.get(SavedCrawl, saved_id)
    if saved is None or saved.site_id != site_id:
        raise ArchiveError(status=404, message="Saved crawl not found")
    return saved


def update(
    session: Session,
    saved: SavedCrawl,
    *,
    name: str | None = None,
    notes: str | None = None,
) -> SavedCrawl:
    if name is not None:
        saved.name = name
    if notes is not None:
        saved.notes = notes or None
    session.add(saved)
    session.commit()
    session.refresh(saved)
    return saved


def delete(session: Session, saved: SavedCrawl) -> None:
    session.delete(saved)
    session.commit()


def archive_payload(saved: SavedCrawl) -> dict:
    try:
        return json.loads(gzip.decompress(saved.archive_gz))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(
            status=500, message="Saved crawl data is unreadable"
        ) from exc


def load_into_run(session: Session, saved: SavedCrawl, run: TestRun) -> TestRun:
    if saved.site_id != run.site_id:
        raise ArchiveError(
            status=400, message="This saved crawl belongs to a different site"
        )
    site = session.get(Site, run.site_id)
    if site is None:
        raise ArchiveError(status=404, message=f"Site {run.site_id} not found")
    return crawl_archives.import_into_run(session, run, archive_payload(saved), site)
