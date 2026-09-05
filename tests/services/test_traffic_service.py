from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.models import CrawledPage, PageCredentialView, TrafficEntry
from aespa.models import TestRun as RunModel
from aespa.schemas import PageCredentialViewOut
from aespa.services import traffic
from aespa.services.traffic import LoggingAsyncClient, setup_playwright_logging


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
        'Request body excerpt:\n{"accountId":"10000001"}\n\n'
        'Response body excerpt:\n{"ok":true}'
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
            llm_context='[API endpoint]\nRequest body excerpt:\n{"accountId":"10000001"}',
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
        assert (
            session.exec(
                select(TrafficEntry).where(TrafficEntry.test_run_id == run_id)
            ).all()
            == []
        )

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


def test_page_credential_view_out_includes_api_transcript_text():
    view = PageCredentialView(
        id=1,
        page_id=2,
        test_run_id=3,
        credential_id=7,
        username="alice",
        page_text=(
            "=== HTTP exchange observed during crawl ===\n"
            "\nREQUEST\nPOST https://target.local/api/accounts/lookup\n"
            '\nBody:\n{"accountId":"10000001"}\n'
            '\nRESPONSE\nStatus: 200\n\nBody:\n{"ok":true}'
        ),
        llm_context="[API endpoint] Observed POST request during crawl.",
    )

    payload = PageCredentialViewOut.model_validate(view).model_dump()

    assert payload["page_text"].startswith(
        "=== HTTP exchange observed during crawl ==="
    )
    assert '"accountId":"10000001"' in payload["page_text"]


@pytest.mark.anyio
async def test_logging_async_client_success(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    # Mock the underlying super().send to return a valid response
    mock_resp = httpx.Response(
        status_code=200,
        headers={"Content-Type": "text/html"},
        text="Success Body",
        request=httpx.Request("GET", "https://target.local/test"),
    )

    # We monkeypatch the superclass's send method
    monkeypatch.setattr(httpx.AsyncClient, "send", AsyncMock(return_value=mock_resp))

    async with LoggingAsyncClient(run_id=42, username="test_user") as client:
        req = httpx.Request("GET", "https://target.local/test")
        resp = await client.send(req)
        assert resp.status_code == 200

    with Session(engine) as session:
        entries = session.exec(select(TrafficEntry)).all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.test_run_id == 42
        assert entry.method == "GET"
        assert entry.url == "https://target.local/test"
        assert entry.status == 200
        assert entry.response_body == "Success Body"
        assert entry.username == "test_user"


@pytest.mark.anyio
async def test_python_traffic_keeps_execution_and_body_provenance(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)
    mock_resp = httpx.Response(
        status_code=201,
        headers={"Content-Type": "application/octet-stream"},
        content=b"\x00\xffresult",
        request=httpx.Request("POST", "https://target.local/test"),
    )
    monkeypatch.setattr(httpx.AsyncClient, "send", AsyncMock(return_value=mock_resp))

    async with LoggingAsyncClient(
        run_id=42,
        source="python",
        provenance={
            "code_execution_id": 7,
            "batch_id": "batch-1",
            "batch_index": 2,
            "agent_id": "specialist-1",
            "agent_step": 4,
            "owasp_category": "A03",
            "test_class": "sqli",
        },
    ) as client:
        request = httpx.Request(
            "POST",
            "https://target.local/test",
            content=b"\x00\x01payload",
            headers={"Content-Type": "application/octet-stream"},
        )
        await client.send(request)

    with Session(engine) as session:
        entry = session.exec(select(TrafficEntry)).one()
        assert entry.source == "python"
        assert entry.code_execution_id == 7
        assert entry.batch_id == "batch-1"
        assert entry.batch_index == 2
        assert entry.agent_id == "specialist-1"
        assert entry.agent_step == 4
        assert entry.owasp_category == "A03"
        assert entry.test_class == "sqli"
        assert entry.request_body_encoding == "base64"
        assert entry.request_body_size == 9
        assert entry.request_body_sha256
        assert entry.response_body_encoding == "base64"
        assert entry.response_body_size == 8
        assert entry.response_body_sha256


@pytest.mark.anyio
async def test_logging_async_client_failure(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    # Mock the underlying super().send to raise a ConnectTimeout exception
    monkeypatch.setattr(
        httpx.AsyncClient,
        "send",
        AsyncMock(side_effect=httpx.ConnectTimeout("Connection timed out")),
    )

    async with LoggingAsyncClient(run_id=42, username="test_user") as client:
        req = httpx.Request(
            "POST", "https://target.local/timeout", content=b"Request Data"
        )
        with pytest.raises(httpx.ConnectTimeout):
            await client.send(req)

    with Session(engine) as session:
        entries = session.exec(select(TrafficEntry)).all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.test_run_id == 42
        assert entry.method == "POST"
        assert entry.url == "https://target.local/timeout"
        assert entry.status is None
        assert (
            "[Request Failed: ConnectTimeout - Connection timed out]"
            in entry.response_body
        )
        assert entry.username == "test_user"
        assert entry.request_body == "Request Data"


@pytest.mark.anyio
async def test_playwright_logging_request_failed(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    # Mock Playwright objects
    mock_ctx = MagicMock()

    # We will capture the listeners registered on the context
    listeners = {}

    def on_event(event_name, handler):
        listeners[event_name] = handler

    mock_ctx.on = on_event

    setup_playwright_logging(mock_ctx, run_id=100, username="pw_user")

    # Verify that the listener is registered
    assert "requestfailed" in listeners
    assert "request" in listeners

    # Mock request object
    mock_req = MagicMock()
    mock_req.method = "GET"
    mock_req.url = "https://target.local/fail"
    mock_req.resource_type = "document"
    mock_req.post_data = None
    mock_req.post_data_json = None
    mock_req.failure = "net::ERR_CONNECTION_REFUSED"

    async def mock_all_headers():
        return {"Host": "target.local"}

    mock_req.all_headers = mock_all_headers
    mock_req.headers = {"Host": "target.local"}

    # Trigger request then requestfailed
    await listeners["request"](mock_req)
    await listeners["requestfailed"](mock_req)

    # Verify log entry in DB
    with Session(engine) as session:
        entries = session.exec(select(TrafficEntry)).all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.test_run_id == 100
        assert entry.source == "playwright"
        assert entry.method == "GET"
        assert entry.url == "https://target.local/fail"
        assert entry.status is None
        assert (
            "[Browser Request Failed: net::ERR_CONNECTION_REFUSED]"
            in entry.response_body
        )
        assert entry.username == "pw_user"


@pytest.mark.anyio
async def test_playwright_logging_skips_noisy_resource_types(monkeypatch):
    """Image/font/media requests are not logged — and (the bug being fixed) the
    request handler must not retain per-request state for them, since the response
    handler returns before cleaning it up."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    listeners = {}
    mock_ctx = MagicMock()
    mock_ctx.on = lambda name, handler: listeners.__setitem__(name, handler)
    setup_playwright_logging(mock_ctx, run_id=101)

    mock_req = MagicMock()
    mock_req.method = "GET"
    mock_req.url = "https://target.local/logo.png"
    mock_req.resource_type = "image"  # in SKIP_RESOURCE_TYPES
    mock_req.post_data = None
    mock_req.post_data_json = None

    mock_resp = MagicMock()
    mock_resp.request = mock_req
    mock_resp.url = mock_req.url
    mock_resp.status = 200

    # A skipped request/response pair must produce no traffic entry.
    await listeners["request"](mock_req)
    await listeners["response"](mock_resp)

    with Session(engine) as session:
        assert session.exec(select(TrafficEntry)).all() == []


@pytest.mark.anyio
async def test_playwright_logging_handles_binary_post_data_decode_error(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    listeners = {}
    mock_ctx = MagicMock()
    mock_ctx.on = lambda name, handler: listeners.__setitem__(name, handler)
    setup_playwright_logging(mock_ctx, run_id=102, username="pw_user")

    class MockBinaryRequest:
        method = "POST"
        url = "https://target.local/upload"
        resource_type = "xhr"
        headers = {"Content-Type": "application/octet-stream"}
        failure = None

        @property
        def post_data(self):
            raise UnicodeDecodeError("utf-8", b"\x1f\x8b", 1, 2, "invalid start byte")

        @property
        def post_data_json(self):
            return None

        @property
        def post_data_buffer(self):
            return b"\x1f\x8b\x08\x00"

        async def all_headers(self):
            return {"Content-Type": "application/octet-stream"}

    mock_req = MockBinaryRequest()

    mock_resp = MagicMock()
    mock_resp.request = mock_req
    mock_resp.url = mock_req.url
    mock_resp.status = 200
    mock_resp.headers = {"content-type": "application/json"}

    async def mock_body():
        return b'{"ok":true}'

    async def mock_all_headers():
        return {"content-type": "application/json"}

    mock_resp.body = mock_body
    mock_resp.all_headers = mock_all_headers

    await listeners["request"](mock_req)
    await listeners["response"](mock_resp)

    with Session(engine) as session:
        entries = session.exec(select(TrafficEntry)).all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.test_run_id == 102
        assert entry.method == "POST"
        assert entry.url == "https://target.local/upload"
        assert entry.request_body == "[binary, 4 bytes]"


@pytest.mark.anyio
async def test_make_httpx_hooks_keys_api_runs_on_api_column(monkeypatch):
    """ALICE/API traffic must land on api_test_run_id (not test_run_id) so it
    shows in the API traffic panel and doesn't collide with web run ids."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    hooks = traffic.make_httpx_hooks(None, username="alice", api_run_id=7)
    req = httpx.Request("GET", "https://api.target.local/v1/users")
    resp = httpx.Response(
        200, headers={"Content-Type": "application/json"}, text="[]", request=req
    )
    for h in hooks["request"]:
        await h(req)
    for h in hooks["response"]:
        await h(resp)

    with Session(engine) as session:
        entry = session.exec(select(TrafficEntry)).one()
        assert entry.api_test_run_id == 7
        assert entry.test_run_id is None  # API traffic has no web-run owner
        assert entry.username == "alice"

    # API traffic panel query (api_run_id) sees it; web query does not.
    assert len(traffic.get_traffic(0, api_run_id=7)) == 1
    assert traffic.get_traffic(7) == []


def test_maybe_record_waf_ignores_out_of_scope_traffic(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)
    traffic._waf_cache.clear()

    from aespa.models import Site

    with Session(engine) as session:
        site = Site(id=1, name="Target Site", base_url="https://target.local")
        run = RunModel(id=50, site_id=site.id, name="Run #50")
        session.add(site)
        session.add(run)
        session.commit()

    # Out of scope CDN request returning Cloudflare header
    traffic._write(
        run_id=50,
        source="playwright",
        method="GET",
        url="https://cdn.tailwindcss.com/3.4.17",
        request_headers={},
        request_body=None,
        status=200,
        response_headers={"server": "cloudflare"},
        response_body=None,
        duration_ms=50,
    )

    with Session(engine) as session:
        run_db = session.get(RunModel, 50)
        assert run_db.waf_provider is None


def test_maybe_record_waf_records_in_scope_traffic(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)
    traffic._waf_cache.clear()

    from aespa.models import Site

    with Session(engine) as session:
        site = Site(id=2, name="Target Site 2", base_url="https://target.local")
        run = RunModel(id=51, site_id=site.id, name="Run #51")
        session.add(site)
        session.add(run)
        session.commit()

    # In scope request returning Cloudflare header
    traffic._write(
        run_id=51,
        source="playwright",
        method="GET",
        url="https://target.local/login",
        request_headers={},
        request_body=None,
        status=200,
        response_headers={"server": "cloudflare"},
        response_body=None,
        duration_ms=50,
    )

    with Session(engine) as session:
        run_db = session.get(RunModel, 51)
        assert run_db.waf_provider == "Cloudflare"
        assert run_db.waf_confidence == "high"
        assert run_db.waf_evidence == "server: cloudflare"


def test_write_emits_structured_testing_traffic_for_console(monkeypatch, caplog):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(traffic, "get_engine", lambda: engine)

    with Session(engine) as session:
        run = RunModel(site_id=1, name="Run #52")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    caplog.set_level("INFO", logger="aespa.testing.traffic")
    traffic._write(
        run_id=run_id,
        source="httpx",
        method="POST",
        url="https://target.local/login",
        request_headers={"content-type": "application/json"},
        request_body='{"user":"alice"}',
        status=401,
        response_headers={"content-type": "application/json"},
        response_body='{"error":"denied"}',
        duration_ms=42,
        username="alice",
        session_label="configured_alice",
    )

    record = next(
        item for item in caplog.records if item.name == "aespa.testing.traffic"
    )
    assert record.aespa_testing_run_kind == "web"
    assert record.aespa_testing_run_id == run_id
    assert record.aespa_testing_method == "POST"
    assert record.aespa_testing_status == 401
    assert record.aespa_testing_request_body == '{"user":"alice"}'
    assert record.aespa_testing_response_body == '{"error":"denied"}'
