from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from aespa.models import CrawledPage, PageCredentialView, TestRun as RunModel, TrafficEntry
from aespa.services import traffic


def test_clear_traffic_preserves_scanner_visible_crawl_state(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    from aespa import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    request_summary = (
        "API endpoint observed during crawl.\n"
        "Method: POST\n"
        "URL: https://target.local/api/accounts/lookup\n"
        "Request Content-Type: application/json\n"
        "HTTP status: 200\n"
        "Response Content-Type: application/json\n\n"
        "Request body excerpt:\n{\"accountId\":\"10000001\"}\n\n"
        "Response body excerpt:\n{\"ok\":true}"
    )

    with Session(engine) as session:
        run = RunModel(site_id=1, name="Run #1")
        session.add(run)
        session.commit()
        session.refresh(run)

        page = CrawledPage(
            test_run_id=run.id,
            url="https://target.local/api/accounts/lookup",
            title="API POST 200 /api/accounts/lookup",
            page_text=request_summary,
            llm_context="[API endpoint]\nRequest body excerpt:\n{\"accountId\":\"10000001\"}",
            has_object_ref=True,
            takes_input=True,
        )
        session.add(page)
        session.commit()
        session.refresh(page)

        view = PageCredentialView(
            page_id=page.id,
            test_run_id=run.id,
            credential_id=7,
            username="alice",
            page_text=request_summary,
            llm_context=page.llm_context,
            has_object_ref=True,
            takes_input=True,
        )
        entry = TrafficEntry(
            test_run_id=run.id,
            source="playwright",
            method="POST",
            url=page.url,
            request_headers='{"content-type":"application/json"}',
            request_body='{"accountId":"10000001"}',
            status=200,
            response_headers='{"content-type":"application/json"}',
            response_body='{"ok":true}',
            duration_ms=12,
            username="alice",
        )
        session.add(view)
        session.add(entry)
        session.commit()
        run_id = run.id
        page_id = page.id
        view_id = view.id

    traffic.clear_traffic(run_id)

    with Session(engine) as session:
        assert session.exec(select(TrafficEntry).where(TrafficEntry.test_run_id == run_id)).all() == []

        page = session.get(CrawledPage, page_id)
        view = session.get(PageCredentialView, view_id)

        assert page is not None
        assert view is not None
        assert '"accountId":"10000001"' in page.page_text
        assert '"accountId":"10000001"' in page.llm_context
        assert page.has_object_ref is True
        assert page.takes_input is True
        assert '"accountId":"10000001"' in view.page_text
        assert '"accountId":"10000001"' in view.llm_context
