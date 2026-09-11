"""Archive persistence can be exercised without HTTP or browser execution."""

from __future__ import annotations

import pytest
from sqlmodel import select

from aespa.models import CrawledPage, Site, TestRun
from aespa.services.crawl_archives import (
    ArchiveError,
    restore_archive_records,
    validate_archive,
)
from aespa.services.run_graph import build_run_graph


def test_archive_record_failure_rolls_back_partial_import(db_session):
    site = Site(name="Fixture", base_url="https://example.test")
    db_session.add(site)
    db_session.commit()
    run = TestRun(site_id=site.id, name="Fixture")
    db_session.add(run)
    db_session.commit()
    run_id = run.id
    with pytest.raises(ArchiveError, match="page URL missing"):
        restore_archive_records(
            db_session,
            run_id,
            {"pages": [{"url": "https://example.test/page"}, {"title": "Missing URL"}]},
            site,
        )
    assert (
        db_session.exec(
            select(CrawledPage).where(CrawledPage.test_run_id == run_id)
        ).all()
        == []
    )
    assert db_session.get(TestRun, run_id) is not None
    assert build_run_graph(db_session, run).nodes == []


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "Not an AESPA"),
        ({"format": "aespa-crawl-export", "version": 99}, "Unsupported"),
        ({"format": "aespa-crawl-export", "version": 1}, "missing page data"),
    ],
)
def test_archive_validation_reports_service_errors(payload, message):
    with pytest.raises(ArchiveError, match=message) as error:
        validate_archive(payload, "https://example.test")
    assert error.value.status == 400
