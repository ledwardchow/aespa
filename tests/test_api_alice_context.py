"""Tests for API-run A.L.I.C.E. context tool and run routing."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.db import get_session
from aespa.main import create_app

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401
    SQLModel.metadata.create_all(engine)

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def _make_collection_with_endpoints(client: TestClient) -> tuple[int, int]:
    """Return (collection_id, run_id) with a few parsed endpoints."""
    r = client.post("/api/api-collections", json={
        "name": "Widget API",
        "base_url": "https://api.example.com",
    })
    assert r.status_code == 201
    cid = r.json()["id"]

    # Directly insert endpoints via API service so we don't need a real file.
    with Session(create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )) as _:
        pass  # Just illustrating — we'll use DB session override below
    return cid


# ── _run_api_context_tool unit tests ─────────────────────────────────────────

def test_context_tool_collection_info_no_endpoints(db_session):
    """collection_info returns correct metadata even with no endpoints."""
    from aespa.models import ApiCollection, ApiTestRun
    from aespa.services.alice import _run_api_context_tool

    coll = ApiCollection(name="My API", base_url="https://api.example.com")
    db_session.add(coll)
    db_session.commit()
    db_session.refresh(coll)

    run = ApiTestRun(collection_id=coll.id, name="run1")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    # Temporarily patch get_engine to return this in-memory engine
    import aespa.db as db_mod
    orig_engine = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        result = _run_api_context_tool(coll.id, run.id, "collection_info", {})
    finally:
        db_mod._engine = orig_engine

    assert result["tool"] == "collection_info"
    assert result["name"] == "My API"
    assert result["base_url"] == "https://api.example.com"
    assert isinstance(result["credentials"], list)


def test_context_tool_endpoint_list_and_detail(db_session):
    """endpoint_list and endpoint_detail return expected fields."""
    import aespa.db as db_mod
    from aespa.models import ApiCollection, ApiEndpoint, ApiTestRun
    from aespa.services.alice import _run_api_context_tool

    coll = ApiCollection(name="Shop API", base_url="https://shop.example.com")
    db_session.add(coll)
    db_session.commit()
    db_session.refresh(coll)

    ep = ApiEndpoint(
        collection_id=coll.id,
        method="GET",
        path="/v1/products/{id}",
        summary="Get a product",
        auth_required=True,
        parameters_json=json.dumps([{"name": "id", "in": "path", "required": True}]),
        request_body_schema_json="{}",
        response_schema_json="{}",
        security_json=json.dumps([{"BearerAuth": []}]),
        tags_json=json.dumps(["products"]),
        sample_request_json="{}",
        prereq_notes="[]",
        prereq_can_test=True,
        prereq_can_test_auth=True,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)

    run = ApiTestRun(collection_id=coll.id, name="r1")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        # endpoint_list
        lst = _run_api_context_tool(coll.id, run.id, "endpoint_list", {})
        assert lst["tool"] == "endpoint_list"
        assert lst["count"] == 1
        assert lst["endpoints"][0]["method"] == "GET"
        assert lst["endpoints"][0]["path"] == "/v1/products/{id}"
        assert lst["endpoints"][0]["auth_required"] is True

        # endpoint_list method filter
        lst_post = _run_api_context_tool(coll.id, run.id, "endpoint_list", {"method": "POST"})
        assert lst_post["count"] == 0

        # endpoint_list search
        lst_search = _run_api_context_tool(coll.id, run.id, "endpoint_list", {"search": "product"})
        assert lst_search["count"] == 1

        # endpoint_detail by id
        detail = _run_api_context_tool(coll.id, run.id, "endpoint_detail", {"endpoint_id": ep.id})
        assert detail["tool"] == "endpoint_detail"
        assert detail["method"] == "GET"
        assert detail["path"] == "/v1/products/{id}"
        assert isinstance(detail["parameters"], list)
        assert detail["parameters"][0]["name"] == "id"
        assert isinstance(detail["tags"], list)

        # endpoint_detail by method+path
        detail2 = _run_api_context_tool(coll.id, run.id, "endpoint_detail", {"method": "GET", "path": "/v1/products/{id}"})
        assert detail2["id"] == ep.id

        # endpoint_detail not found
        miss = _run_api_context_tool(coll.id, run.id, "endpoint_detail", {"endpoint_id": 9999})
        assert "error" in miss
    finally:
        db_mod._engine = orig


def test_context_tool_unknown_returns_error(db_session):
    """Unknown tool name returns an error dict with available_tools."""
    import aespa.db as db_mod
    from aespa.models import ApiCollection, ApiTestRun
    from aespa.services.alice import _run_api_context_tool

    coll = ApiCollection(name="A", base_url="https://a.example.com")
    db_session.add(coll)
    db_session.commit()
    db_session.refresh(coll)

    run = ApiTestRun(collection_id=coll.id, name="r")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        result = _run_api_context_tool(coll.id, run.id, "site_map", {})
    finally:
        db_mod._engine = orig

    assert result["error"] == "unknown tool"
    assert "endpoint_list" in result["available_tools"]
    assert "set_coverage" in result["available_tools"]
    assert "coverage_matrix" in result["available_tools"]


# ── coverage_matrix / set_coverage ────────────────────────────────────────────

def _make_coverage_fixture(db_session):
    """Create a collection + one in-scope GET endpoint with a path param and a
    seeded coverage matrix. Returns (collection, endpoint, run)."""
    import aespa.db as db_mod
    from aespa.models import ApiCollection, ApiEndpoint, ApiTestRun
    from aespa.services.api_scanner import seed_coverage_matrix

    coll = ApiCollection(name="Cov API", base_url="https://cov.example.com")
    db_session.add(coll)
    db_session.commit()
    db_session.refresh(coll)

    ep = ApiEndpoint(
        collection_id=coll.id,
        method="GET",
        path="/v1/products/{id}",
        summary="Get a product",
        auth_required=True,
        parameters_json=json.dumps([{"name": "id", "in": "path", "required": True}]),
        in_scope=True,
        prereq_can_test=True,
        prereq_can_test_auth=True,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)

    run = ApiTestRun(collection_id=coll.id, name="r")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    # Seed against the same in-memory engine the dispatcher uses.
    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        seed_coverage_matrix(run.id)
    finally:
        db_mod._engine = orig
    return coll, ep, run


def test_set_coverage_marks_cell_and_matrix_reflects_it(db_session):
    """set_coverage upgrades a cell and coverage_matrix reports the new status."""
    import aespa.db as db_mod
    from aespa.services.alice import _run_api_context_tool

    coll, ep, run = _make_coverage_fixture(db_session)

    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        # Cell starts not_started.
        before = _run_api_context_tool(coll.id, run.id, "coverage_matrix", {"endpoint_id": ep.id})
        api1 = next(c for c in before["cells"] if c["owasp_api_category"] == "API1")
        assert api1["status"] == "not_started"

        # Mark it covered.
        res = _run_api_context_tool(coll.id, run.id, "set_coverage", {
            "endpoint_id": ep.id, "owasp_api_category": "API1", "status": "covered",
        })
        assert res["ok"] is True
        assert res["status"] == "covered"
        assert res["downgrade_ignored"] is False

        # Matrix now reflects covered.
        after = _run_api_context_tool(coll.id, run.id, "coverage_matrix", {
            "endpoint_id": ep.id, "status": "covered",
        })
        assert any(c["owasp_api_category"] == "API1" for c in after["cells"])
    finally:
        db_mod._engine = orig


def test_set_coverage_never_downgrades(db_session):
    """A request to lower a cell's status is silently kept at the higher state."""
    import aespa.db as db_mod
    from aespa.services.alice import _run_api_context_tool

    coll, ep, run = _make_coverage_fixture(db_session)

    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        _run_api_context_tool(coll.id, run.id, "set_coverage", {
            "endpoint_id": ep.id, "owasp_api_category": "API2", "status": "finding",
            "finding_id": 7,
        })
        # Try to downgrade to in_progress.
        res = _run_api_context_tool(coll.id, run.id, "set_coverage", {
            "endpoint_id": ep.id, "owasp_api_category": "API2", "status": "in_progress",
        })
        assert res["requested_status"] == "in_progress"
        assert res["status"] == "finding"
        assert res["downgrade_ignored"] is True
    finally:
        db_mod._engine = orig


def test_report_finding_auto_links_coverage_cell(db_session):
    """report_finding flips the matched endpoint × category cell to 'finding'."""
    import aespa.db as db_mod
    from aespa.services.alice import _run_api_context_tool

    coll, ep, run = _make_coverage_fixture(db_session)

    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        res = _run_api_context_tool(coll.id, run.id, "report_finding", {
            "title": "BOLA on product",
            "severity": "high",
            "owasp_api_category": "API1",
            "affected_url": "https://cov.example.com/v1/products/5",
            "description": "swapped id to read another user's product",
        })
        assert res["ok"] is True
        assert res["coverage_cell"] == {"endpoint_id": ep.id, "owasp_api_category": "API1"}

        matrix = _run_api_context_tool(coll.id, run.id, "coverage_matrix", {
            "endpoint_id": ep.id, "status": "finding",
        })
        api1 = [c for c in matrix["cells"] if c["owasp_api_category"] == "API1"]
        assert len(api1) == 1
        assert res["finding_id"] in api1[0]["finding_ids"]
    finally:
        db_mod._engine = orig


def test_report_finding_no_link_when_url_matches_nothing(db_session):
    """A finding whose affected_url matches no endpoint still saves but links no cell."""
    import aespa.db as db_mod
    from aespa.services.alice import _run_api_context_tool

    coll, ep, run = _make_coverage_fixture(db_session)

    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        res = _run_api_context_tool(coll.id, run.id, "report_finding", {
            "title": "Stray finding",
            "severity": "low",
            "owasp_api_category": "API1",
            "affected_url": "https://cov.example.com/nope/unmatched",
        })
        assert res["ok"] is True
        assert res["coverage_cell"] is None
    finally:
        db_mod._engine = orig


def test_set_coverage_validates_inputs(db_session):
    """Invalid status, category, endpoint, and non-applicable category are rejected."""
    import aespa.db as db_mod
    from aespa.services.alice import _run_api_context_tool

    coll, ep, run = _make_coverage_fixture(db_session)

    orig = db_mod._engine
    db_mod._engine = db_session.get_bind()
    try:
        bad_status = _run_api_context_tool(coll.id, run.id, "set_coverage", {
            "endpoint_id": ep.id, "owasp_api_category": "API1", "status": "not_started",
        })
        assert "error" in bad_status

        bad_cat = _run_api_context_tool(coll.id, run.id, "set_coverage", {
            "endpoint_id": ep.id, "owasp_api_category": "API99", "status": "covered",
        })
        assert "error" in bad_cat

        bad_ep = _run_api_context_tool(coll.id, run.id, "set_coverage", {
            "endpoint_id": 9999, "owasp_api_category": "API1", "status": "covered",
        })
        assert "error" in bad_ep

        # API3 only applies to PUT/PATCH — not this GET endpoint.
        not_applicable = _run_api_context_tool(coll.id, run.id, "set_coverage", {
            "endpoint_id": ep.id, "owasp_api_category": "API3", "status": "covered",
        })
        assert "error" in not_applicable
        assert "API3" not in not_applicable.get("applicable_categories", [])
    finally:
        db_mod._engine = orig


# ── _check_api_scope unit tests ────────────────────────────────────────────────

def test_check_api_scope_allows_base_url_host():
    from aespa.services.alice import _check_api_scope

    class _C:
        base_url = "https://api.example.com"
        servers = "[]"
        scope_hosts = "[]"

    assert _check_api_scope("https://api.example.com/v1/foo", _C()) is None


def test_check_api_scope_blocks_out_of_scope():
    from aespa.services.alice import _check_api_scope

    class _C:
        base_url = "https://api.example.com"
        servers = "[]"
        scope_hosts = "[]"

    result = _check_api_scope("https://evil.com/exfil", _C())
    assert result is not None
    assert "evil.com" in result


def test_check_api_scope_respects_explicit_scope_hosts():
    from aespa.services.alice import _check_api_scope

    class _C:
        base_url = "https://api.example.com"
        servers = "[]"
        scope_hosts = json.dumps(["api.example.com", "cdn.example.com"])

    assert _check_api_scope("https://cdn.example.com/image.png", _C()) is None
    result = _check_api_scope("https://other.com/x", _C())
    assert result is not None


def test_check_api_scope_allows_additional_servers():
    from aespa.services.alice import _check_api_scope

    class _C:
        base_url = "https://api.example.com"
        servers = json.dumps(["https://staging.example.com"])
        scope_hosts = "[]"

    assert _check_api_scope("https://staging.example.com/v1/x", _C()) is None


# ── alice_tasks run_type routing ──────────────────────────────────────────────

def test_alice_tasks_start_stores_run_type():
    """start() stores run_type='api' on the created AliceTask."""
    import asyncio

    from aespa.services import alice_tasks

    # Patch out the actual _run coroutine so we don't start a real agent.
    async def _noop_run(task, message, history):
        pass

    import aespa.services.alice_tasks as at_mod
    orig_run = at_mod._run

    async def _fake_run(task, message, history):
        pass

    at_mod._run = _fake_run
    try:
        task = asyncio.run(alice_tasks.start(
            999,
            tab_id="t1",
            think_msg_id="th1",
            reply_msg_id="re1",
            message="hello",
            history=[],
            run_type="api",
        ))
        assert task.run_type == "api"
        assert task.run_id == 999
        # cancel the asyncio task so it doesn't linger
        if task.asyncio_task and not task.asyncio_task.done():
            task.asyncio_task.cancel()
    finally:
        at_mod._run = orig_run
        # Clean up registry
        alice_tasks._registry.pop(999, None)


def test_alice_tasks_start_default_run_type_is_site():
    """start() defaults run_type to 'site' when not specified."""
    import asyncio

    import aespa.services.alice_tasks as at_mod
    from aespa.services import alice_tasks

    async def _fake_run(task, message, history):
        pass

    orig_run = at_mod._run
    at_mod._run = _fake_run
    try:
        task = asyncio.run(alice_tasks.start(
            998,
            tab_id="t",
            think_msg_id="th",
            reply_msg_id="re",
            message="hi",
            history=[],
        ))
        assert task.run_type == "site"
    finally:
        at_mod._run = orig_run
        alice_tasks._registry.pop(998, None)


# ── API endpoint: start_alice_run passes run_type=api ─────────────────────────

def test_start_alice_run_endpoint_uses_api_run_type(client):
    """POST .../alice/run for an ApiTestRun should reach alice_tasks with run_type='api'."""
    import aespa.services.alice_tasks as at_mod

    captured: list[str] = []

    async def _fake_start(run_id, *, tab_id, think_msg_id, reply_msg_id, message, history, run_type="site"):
        captured.append(run_type)
        import asyncio

        from aespa.services.alice_tasks import AliceTask
        task = AliceTask(run_id=run_id, tab_id=tab_id, think_msg_id=think_msg_id,
                        reply_msg_id=reply_msg_id, run_type=run_type)
        task.asyncio_task = asyncio.create_task(asyncio.sleep(0))
        at_mod._registry[run_id] = task
        return task

    orig_start = at_mod.start
    at_mod.start = _fake_start

    try:
        # Create collection + run
        r = client.post("/api/api-collections", json={"name": "Z", "base_url": "https://z.example.com"})
        cid = r.json()["id"]
        run = client.post(f"/api/api-collections/{cid}/test-runs", json={"name": "t"}).json()
        rid = run["id"]

        resp = client.post(f"/api/api-test-runs/{rid}/alice/run", json={
            "message": "test",
            "history": [],
            "tab_id": "tab-default",
            "think_msg_id": "th1",
            "reply_msg_id": "re1",
        })
        assert resp.status_code == 200
        assert captured == ["api"]
    finally:
        at_mod.start = orig_start
        at_mod._registry.pop(rid, None)


# ── ALICE_API_SYSTEM_PROMPT sanity check ──────────────────────────────────────

def test_api_system_prompt_contains_owasp_api_categories():
    from aespa.services.prompts.alice import ALICE_API_SYSTEM_PROMPT
    for category in ["API1", "API2", "API3", "API4", "API5", "API6", "API7", "API8", "API9", "API10"]:
        assert category in ALICE_API_SYSTEM_PROMPT


def test_api_system_prompt_contains_context_tool_commands():
    from aespa.services.prompts.alice import ALICE_API_SYSTEM_PROMPT
    for cmd in ["endpoint_list", "endpoint_detail", "collection_info", "finding_list"]:
        assert cmd in ALICE_API_SYSTEM_PROMPT


def test_api_system_prompt_formats_correctly():
    from aespa.services.prompts.alice import ALICE_API_SYSTEM_PROMPT
    formatted = ALICE_API_SYSTEM_PROMPT.format(
        collection_name="My API",
        base_url="https://api.example.com",
        user_directive="Test everything",
    )
    assert "My API" in formatted
    assert "https://api.example.com" in formatted
    assert "Test everything" in formatted
