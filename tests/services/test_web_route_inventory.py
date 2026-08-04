"""Dynamic route classification and workprogram enrichment tests."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import _migrate, set_engine
from aespa.models import CrawledPage, PageOwaspTest, Site, TestRun
from aespa.services.web_route_inventory import (
    classify_http_exchange,
    enrich_dynamic_route,
    merge_route_categories,
)
from aespa.services.web_workprogram import _make_web_post_probe_fn


@pytest.fixture(name="db_engine")
def db_engine_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa.db import _engine as original_engine

    SQLModel.metadata.create_all(engine)
    _migrate(engine)
    set_engine(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    set_engine(original_engine)


@pytest.fixture(name="run")
def run_fixture(db_engine):
    with Session(db_engine) as session:
        site = Site(name="Dynamic target", base_url="https://target.local")
        session.add(site)
        session.commit()
        session.refresh(site)
        run = TestRun(site_id=site.id, name="Dynamic run")
        session.add(run)
        session.commit()
        session.refresh(run)
        session.expunge(run)
        return run


def test_classify_http_exchange_finds_route_obligations():
    categories = classify_http_exchange(
        {
            "method": "POST",
            "url": "https://target.local/api/accounts/42/import?url=https://example.test",
            "request_body": '{"customer_id": 7, "name": "new"}',
        },
        authenticated=True,
    )

    assert categories["req_auth"] is True
    assert categories["takes_input"] is True
    assert categories["has_object_ref"] is True
    assert categories["has_business_logic"] is True
    assert categories["owasp_applicable"]["A01"] is True
    assert categories["owasp_applicable"]["A03"] is True
    assert categories["owasp_applicable"]["A10"] is True


def test_merge_route_categories_never_erases_prior_true_values():
    merged = merge_route_categories(
        {
            "takes_input": True,
            "has_object_ref": None,
            "owasp_applicable": {"A03": True, "A10": False},
        },
        {
            "takes_input": False,
            "has_object_ref": True,
            "owasp_applicable": {"A03": False, "A10": True},
        },
    )

    assert merged["takes_input"] is True
    assert merged["has_object_ref"] is True
    assert merged["owasp_applicable"]["A03"] is True
    assert merged["owasp_applicable"]["A10"] is True


def test_missing_guessed_route_is_not_added_to_workprogram(db_engine, run):
    post_probe = _make_web_post_probe_fn(run.id)

    post_probe(
        "https://target.local/definitely-missing",
        "GET",
        "A05",
        None,
        404,
    )

    with Session(db_engine) as session:
        assert not list(
            session.exec(
                select(CrawledPage).where(CrawledPage.test_run_id == run.id)
            ).all()
        )
        assert not list(
            session.exec(
                select(PageOwaspTest).where(PageOwaspTest.test_run_id == run.id)
            ).all()
        )


def test_dynamic_route_enrichment_classifies_and_seeds_all_categories(db_engine, run):
    llm_categories = {
        "req_auth": False,
        "takes_input": True,
        "has_object_ref": False,
        "has_business_logic": True,
        "owasp_applicable": {"A02": True, "A06": True},
    }
    analyse = AsyncMock(
        return_value=("Imports remote account data.", [], llm_categories)
    )

    with patch("aespa.services.web_route_inventory.llm_svc.analyse_page", analyse):
        page_id = asyncio.run(
            enrich_dynamic_route(
                run_id=run.id,
                llm_cfg=object(),
                url="https://target.local/api/accounts/42/import",
                method="POST",
                request_body='{"url": "https://example.test/feed"}',
                response_status=200,
                response_headers={"content-type": "application/json"},
                response_body='{"accepted": true}',
                authenticated=True,
            )
        )

    assert page_id is not None
    with Session(db_engine) as session:
        page = session.get(CrawledPage, page_id)
        assert page is not None
        assert page.state_kind == "api"
        assert page.takes_input is True
        assert page.has_object_ref is True
        assert page.has_business_logic is True
        applicable = json.loads(page.owasp_applicable_json)
        assert applicable["A01"] is True
        assert applicable["A02"] is True
        assert applicable["A03"] is True
        assert applicable["A06"] is True
        assert applicable["A10"] is True

        cells = list(
            session.exec(
                select(PageOwaspTest).where(PageOwaspTest.page_id == page_id)
            ).all()
        )
        assert {cell.owasp_category for cell in cells} == {
            category for category, enabled in applicable.items() if enabled
        }
        assert all(cell.status == "not_started" for cell in cells)


def test_dynamic_route_enrichment_reuses_existing_page_and_llm_analysis(db_engine, run):
    with Session(db_engine) as session:
        page = CrawledPage(
            test_run_id=run.id,
            url="https://target.local/api/users/1",
            in_scope=True,
            owasp_applicable_json=json.dumps({"A01": True}),
        )
        session.add(page)
        session.commit()
        session.refresh(page)
        original_page_id = page.id

    analyse = AsyncMock()
    with patch("aespa.services.web_route_inventory.llm_svc.analyse_page", analyse):
        page_id = asyncio.run(
            enrich_dynamic_route(
                run_id=run.id,
                llm_cfg=object(),
                url="https://target.local/api/users/2?view=full",
                method="GET",
                response_status=200,
                response_body='{"id": 2}',
                authenticated=True,
            )
        )

    assert page_id == original_page_id
    analyse.assert_not_awaited()
    with Session(db_engine) as session:
        pages = list(
            session.exec(
                select(CrawledPage).where(CrawledPage.test_run_id == run.id)
            ).all()
        )
        assert len(pages) == 1
        applicable = json.loads(pages[0].owasp_applicable_json)
        assert applicable["A01"] is True
        assert applicable["A05"] is True
        assert applicable["A07"] is True
