"""Focused regression coverage for the SAST Validate scan mode."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from sqlmodel import Session

from aespa.models import ApiCollection, ApiTestRun, ScanLead, Site
from aespa.models import TestRun as WebTestRun
from aespa.services.prompts.test_lead import (
    get_sast_validate_system,
    get_sast_validate_tools,
)
from aespa.services.scan_leads import (
    format_lead_index_for_validation,
    format_leads_for_scan_context,
    get_lead_detail_for_run,
)
from aespa.services.scanner import (
    _do_agentic_thinking_loop,
    _run_thinking_context_tool,
)


def _web_run(
    engine,
    *,
    base_url: str = "https://target.local",
    name: str = "SAST Validate Site",
) -> WebTestRun:
    with Session(engine) as session:
        site = Site(name=name, base_url=base_url)
        session.add(site)
        session.commit()
        session.refresh(site)
        run = WebTestRun(site_id=site.id, name="SAST Validate Web")
        session.add(run)
        session.commit()
        session.refresh(run)
        return run


def _api_run(engine, *, base_url: str = "https://api.local") -> ApiTestRun:
    with Session(engine) as session:
        collection = ApiCollection(name="SAST Validate API", base_url=base_url)
        session.add(collection)
        session.commit()
        session.refresh(collection)
        run = ApiTestRun(
            collection_id=collection.id,
            name="SAST Validate API Run",
            status="pending",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run


def _imported_lead(
    engine,
    *,
    run_type: str,
    run_id: int,
    title: str = "Static issue",
    status: str = "open",
    **fields,
) -> ScanLead:
    values = {
        "producer_run_id": 9001,
        "producer_run_type": "sast",
        "imported_into_run_type": run_type,
        "imported_into_run_id": run_id,
        "title": title,
        "description": "Static description",
        "category": "A03",
        "severity": "high",
        "confidence": 0.95,
        "location": "src/app.py:10",
        "status": status,
        **fields,
    }
    with Session(engine) as session:
        lead = ScanLead(**values)
        session.add(lead)
        session.commit()
        session.refresh(lead)
        return lead


def test_start_endpoints_accept_sast_validate_and_require_open_leads(
    client, isolated_db_engine
):
    web_run = _web_run(isolated_db_engine)
    api_run = _api_run(isolated_db_engine)

    with patch(
        "aespa.services.scanner.start_thinking_scan", new_callable=AsyncMock
    ) as web_start:
        response = client.post(
            f"/api/test-runs/{web_run.id}/thinking-scan/start",
            json={"coverage_mode": "sast_validate"},
        )
    assert response.status_code == 409
    assert "No open imported SAST leads" in response.text
    web_start.assert_not_awaited()

    with patch(
        "aespa.services.api_scanner.start_api_scan", new_callable=AsyncMock
    ) as api_start:
        response = client.post(
            f"/api/api-test-runs/{api_run.id}/scan/start",
            json={"coverage_mode": "sast_validate"},
        )
    assert response.status_code == 409
    assert "No open imported SAST leads" in response.text
    api_start.assert_not_awaited()

    web_lead = _imported_lead(isolated_db_engine, run_type="web", run_id=web_run.id)
    api_lead = _imported_lead(
        isolated_db_engine, run_type="api", run_id=api_run.id, title="API issue"
    )

    with patch("aespa.services.scanner.start_thinking_scan", new_callable=AsyncMock):
        response = client.post(
            f"/api/test-runs/{web_run.id}/thinking-scan/start",
            json={"coverage_mode": "sast_validate"},
        )
    assert response.status_code == 200
    with Session(isolated_db_engine) as session:
        assert session.get(WebTestRun, web_run.id).coverage_mode == "sast_validate"

    with patch("aespa.services.api_scanner.start_api_scan", new_callable=AsyncMock):
        response = client.post(
            f"/api/api-test-runs/{api_run.id}/scan/start",
            json={"coverage_mode": "sast_validate"},
        )
    assert response.status_code == 200
    assert response.json()["coverage_mode"] == "sast_validate"
    assert web_lead.id != api_lead.id or web_run.id != api_run.id


def test_sast_validate_resume_requires_open_leads_and_skips_workprogram(
    client, isolated_db_engine
):
    run = _web_run(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        persisted_run = session.get(WebTestRun, run.id)
        persisted_run.coverage_mode = "sast_validate"
        session.add(persisted_run)
        session.commit()

    with (
        patch(
            "aespa.api.scan.checkpoint_svc.checkpoint_status",
            return_value={"exists": True, "step_count": 4},
        ),
        patch("aespa.api.scan.scanner_svc.start_thinking_scan_resume") as resume,
        patch("aespa.api.scan.scanner_svc.get_thinking_scan_status") as status,
        patch("aespa.services.web_workprogram.seed_web_workprogram") as seed,
    ):
        response = client.post(f"/api/test-runs/{run.id}/thinking-scan/resume")
        assert response.status_code == 409
        resume.assert_not_awaited()
        seed.assert_not_called()

        _imported_lead(isolated_db_engine, run_type="web", run_id=run.id)
        status.return_value = {"status": "running", "run_id": run.id}
        response = client.post(f"/api/test-runs/{run.id}/thinking-scan/resume")
        assert response.status_code == 200
        resume.assert_awaited_once_with(run.id)
        seed.assert_not_called()


def test_scan_start_rejects_invalid_coverage_mode(client, isolated_db_engine):
    web_run = _web_run(isolated_db_engine)
    api_run = _api_run(isolated_db_engine)

    response = client.post(
        f"/api/test-runs/{web_run.id}/thinking-scan/start",
        json={"coverage_mode": "not-a-mode"},
    )
    assert response.status_code == 422

    response = client.post(
        f"/api/api-test-runs/{api_run.id}/scan/start",
        json={"coverage_mode": "not-a-mode"},
    )
    assert response.status_code == 422


def test_validation_index_includes_all_leads_and_dynamic_objective(
    isolated_db_engine,
):
    run = _web_run(isolated_db_engine)
    leads = [
        _imported_lead(
            isolated_db_engine,
            run_type="web",
            run_id=run.id,
            title=f"Lead {index}",
            suggested_endpoint=f"/items/{index}",
            attack_path_json='{"dynamic_test":"validate object %d"}' % index,
        )
        for index in range(25)
    ]

    index = format_lead_index_for_validation("web", run.id)
    assert len(leads) == 25
    assert index.count("context_tool(tool=lead_detail") == 25
    assert "Lead 24" in index
    assert "/items/24" in index
    assert "validate object 24" in index
    assert "static-analysis hypothesis" in index.lower()


def test_quick_scan_context_includes_every_open_lead(isolated_db_engine):
    run = _web_run(isolated_db_engine)
    for index in range(25):
        _imported_lead(
            isolated_db_engine,
            run_type="web",
            run_id=run.id,
            title=f"Quick lead {index}",
        )

    quick_context = format_leads_for_scan_context("web", run.id, "track")
    full_context = format_leads_for_scan_context("web", run.id, "enforce")

    assert quick_context.count("context_tool(tool=lead_detail") == 25
    assert "Quick lead 24" in quick_context
    assert full_context.count("[Lead ") == 20


def test_quick_resume_refreshes_leads_and_blocks_done(isolated_db_engine, monkeypatch):
    run = _api_run(isolated_db_engine)
    lead = _imported_lead(
        isolated_db_engine,
        run_type="api",
        run_id=run.id,
        title="Lead added after checkpoint",
    )
    captured = {}

    async def fake_agentic_loop(_config, **kwargs):
        captured["system_message"] = kwargs["system_message"]
        allowed, feedback = kwargs["done_check"]({}, 5)
        assert allowed is False
        assert "still open" in feedback

        with Session(isolated_db_engine) as session:
            row = session.get(ScanLead, lead.id)
            row.status = "dismissed"
            session.add(row)
            session.commit()

        allowed, feedback = kwargs["done_check"]({}, 6)
        assert allowed is True
        return "done"

    monkeypatch.setattr(
        "aespa.services.scanner.llm_svc.thinking_agentic_loop",
        fake_agentic_loop,
    )
    monkeypatch.setattr(
        "aespa.services.scanner.events_svc.emit", lambda *args, **kwargs: None
    )

    asyncio.run(
        _do_agentic_thinking_loop(
            run_id=run.id,
            is_api_run=True,
            llm_cfg=SimpleNamespace(),
            base_url="https://api.local",
            crawl_context="old context",
            creds_for_llm=[],
            session_vault={},
            pages_snapshot=[],
            findings_snapshot=[],
            first_page_id=None,
            scanner_policy=SimpleNamespace(
                execution_monitor_enabled=False,
                max_consecutive_text_turns=0,
                enforce_full_coverage_obligations=False,
            ),
            hx=SimpleNamespace(),
            browser_ctx=None,
            pw_page=None,
            history=[],
            all_results=[],
            resume_from={
                "messages": [{"role": "user", "content": "checkpoint context"}],
                "step_count": 4,
            },
            system_message_override="API Test Lead",
            tools_override=[],
            coverage_mode="track",
        )
    )

    assert "resumed Quick run" in captured["system_message"]
    assert "Lead added after checkpoint" in captured["system_message"]


def test_lead_detail_returns_full_owned_data_and_rejects_foreign_leads(
    isolated_db_engine,
):
    run = _web_run(isolated_db_engine)
    foreign_run = _web_run(
        isolated_db_engine,
        base_url="https://other.local",
        name="Foreign SAST Validate Site",
    )
    lead = _imported_lead(
        isolated_db_engine,
        run_type="web",
        run_id=run.id,
        suggested_endpoint="/admin/items/7",
        evidence="unique evidence marker",
        source_trace_json='{"source":"source marker"}',
        control_trace_json='["control marker"]',
        sink_trace_json='{"sink":"sink marker"}',
        counterevidence_json='["counter marker"]',
        proof_gaps_json='["gap marker"]',
        validation_status="confirmed",
        validation_reasoning="reasoning marker",
        attack_path_json=(
            '{"nodes":["node marker"],"impact":"impact marker",'
            '"severity_reasoning":"severity marker",'
            '"dynamic_test":"objective marker"}'
        ),
    )

    detail = get_lead_detail_for_run("web", run.id, lead.id)
    assert detail is not None
    assert detail["evidence"] == "unique evidence marker"
    assert detail["suggested_endpoint"] == "/admin/items/7"
    assert detail["source_trace"]["source"] == "source marker"
    assert detail["control_trace"] == ["control marker"]
    assert detail["sink_trace"]["sink"] == "sink marker"
    assert detail["counterevidence"] == ["counter marker"]
    assert detail["proof_gaps"] == ["gap marker"]
    assert detail["validation_reasoning"] == "reasoning marker"
    assert detail["attack_path"]["nodes"] == ["node marker"]
    assert detail["attack_path"]["dynamic_test"] == "objective marker"
    assert get_lead_detail_for_run("web", foreign_run.id, lead.id) is None
    assert get_lead_detail_for_run("api", run.id, lead.id) is None

    context = _run_thinking_context_tool(
        "lead_detail",
        {"lead_id": lead.id},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=run.id,
        base_url="https://target.local",
    )
    assert context["lead"]["evidence"] == "unique evidence marker"

    quoted_context = _run_thinking_context_tool(
        "lead_detail",
        {"lead_id": str(lead.id)},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=run.id,
        base_url="https://target.local",
    )
    assert quoted_context["lead"]["evidence"] == "unique evidence marker"


def test_sast_validate_context_exposes_only_open_leads(isolated_db_engine):
    web_run = _web_run(isolated_db_engine)
    open_lead = _imported_lead(
        isolated_db_engine,
        run_type="web",
        run_id=web_run.id,
        title="Open lead",
    )
    confirmed_lead = _imported_lead(
        isolated_db_engine,
        run_type="web",
        run_id=web_run.id,
        title="Confirmed lead",
        status="confirmed",
    )

    lead_list = _run_thinking_context_tool(
        "lead_list",
        {},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=web_run.id,
        base_url=web_run.name,
        open_leads_only=True,
    )
    assert [lead["id"] for lead in lead_list["leads"]] == [open_lead.id]

    terminal_detail = _run_thinking_context_tool(
        "lead_detail",
        {"lead_id": confirmed_lead.id},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=web_run.id,
        base_url="https://target.local",
        open_leads_only=True,
    )
    assert terminal_detail["error"] == "lead not found or unavailable for this run"

    api_run = _api_run(isolated_db_engine)
    api_open_lead = _imported_lead(
        isolated_db_engine,
        run_type="api",
        run_id=api_run.id,
        title="Open API lead",
    )
    api_confirmed_lead = _imported_lead(
        isolated_db_engine,
        run_type="api",
        run_id=api_run.id,
        title="Confirmed API lead",
        status="confirmed",
    )
    api_lead_list = _run_thinking_context_tool(
        "lead_list",
        {"status": "confirmed"},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=api_run.id,
        api_run_id=api_run.id,
        base_url="https://api.local",
        open_leads_only=True,
    )
    assert [lead["id"] for lead in api_lead_list["leads"]] == [api_open_lead.id]
    api_terminal_detail = _run_thinking_context_tool(
        "lead_detail",
        {"lead_id": api_confirmed_lead.id},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=api_run.id,
        api_run_id=api_run.id,
        base_url="https://api.local",
        open_leads_only=True,
    )
    assert api_terminal_detail["error"] == "lead not found or unavailable for this run"


def test_malformed_lead_detail_is_safe(isolated_db_engine):
    run = _web_run(isolated_db_engine)
    lead = _imported_lead(
        isolated_db_engine,
        run_type="web",
        run_id=run.id,
        source_trace_json="{bad",
        control_trace_json="{bad",
        sink_trace_json="{bad",
        counterevidence_json="{bad",
        proof_gaps_json="{bad",
        attack_path_json="{bad",
    )
    detail = get_lead_detail_for_run("web", run.id, lead.id)
    assert detail["source_trace"] == {}
    assert detail["control_trace"] == []
    assert detail["sink_trace"] == {}
    assert detail["counterevidence"] == []
    assert detail["proof_gaps"] == []
    assert detail["attack_path"] == {}


def test_sast_validate_prompt_and_tools_are_focused():
    web_prompt = get_sast_validate_system(is_api_run=False)
    api_prompt = get_sast_validate_system(is_api_run=True)
    for prompt in (web_prompt, api_prompt):
        assert "lead_detail" in prompt
        assert "attack path" in prompt
        assert "configured" in prompt
        assert "incidental" in prompt
        assert "baseline" in prompt
        assert "binding is stale" in prompt
    assert "browser" in {
        tool["name"] for tool in get_sast_validate_tools(is_api_run=False)
    }
    assert "browser" not in {
        tool["name"] for tool in get_sast_validate_tools(is_api_run=True)
    }
    assert "execute_python" in {
        tool["name"] for tool in get_sast_validate_tools(is_api_run=False)
    }
    assert "execute_python" in {
        tool["name"] for tool in get_sast_validate_tools(is_api_run=True)
    }
    assert "agent_dispatch" not in {
        tool["name"] for tool in get_sast_validate_tools(is_api_run=False)
    }
    assert "coverage_gaps" not in {
        tool["name"] for tool in get_sast_validate_tools(is_api_run=False)
    }
    api_http_tool = next(
        tool
        for tool in get_sast_validate_tools(is_api_run=True)
        if tool["name"] == "http_request"
    )
    assert "store_as" in api_http_tool["input_schema"]["properties"]
    assert "store_as" in api_prompt
    update_tool = next(
        tool
        for tool in get_sast_validate_tools(is_api_run=True)
        if tool["name"] == "update_lead"
    )
    update_schema = update_tool["input_schema"]
    assert "outcome_reason" in update_schema["properties"]
    assert "baseline_evidence" in update_schema["properties"]
    assert "mutated_evidence" in update_schema["properties"]
    from aespa.services.prompts.test_lead import _API_THINKING_AGENT_SYSTEM

    assert "lead_detail" in _API_THINKING_AGENT_SYSTEM


def test_api_login_response_session_is_reused_by_stable_label(
    isolated_db_engine, monkeypatch
):
    run = _api_run(isolated_db_engine)
    from aespa.services.scanner_sessions import load_session_vault, upsert_session

    upsert_session(
        run.id,
        label="configured_primary",
        kind="bearer",
        extra_headers={"Authorization": "Bearer stale-token"},
        run_kind="api",
    )
    session_vault = load_session_vault(run.id, run_kind="api")
    observed_authorization = []
    observed_cookies = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth":
            return httpx.Response(
                200,
                json={"token": "eyJheader.eyJpayload.signature"},
                request=request,
            )
        if request.url.path == "/api/cookie-auth":
            return httpx.Response(
                200,
                json={"ok": True},
                headers={"set-cookie": "sid=fresh-cookie; Path=/; HttpOnly"},
                request=request,
            )
        if request.url.path == "/api/private":
            observed_authorization.append(request.headers.get("authorization"))
        if request.url.path == "/api/cookie-private":
            observed_cookies.append(request.headers.get("cookie"))
        return httpx.Response(200, json={"ok": True}, request=request)

    async def fake_agentic_loop(_config, **kwargs):
        login_result = await kwargs["tool_executor"](
            "http_request",
            {
                "method": "POST",
                "url": "https://api.local/api/auth",
                "body": {"email": "user@example.com", "password": "correct"},
                "use_session": "anonymous",
                "store_as": "configured_primary",
                "owasp_category": "API2",
            },
            1,
        )
        assert "[SESSION STORED]" in login_result
        assert "configured_primary" in session_vault

        protected_result = await kwargs["tool_executor"](
            "http_request",
            {
                "method": "GET",
                "url": "https://api.local/api/private",
                "use_session": "configured_primary",
                "owasp_category": "API2",
            },
            2,
        )
        assert "Status: 200" in protected_result

        cookie_login_result = await kwargs["tool_executor"](
            "http_request",
            {
                "method": "POST",
                "url": "https://api.local/api/cookie-auth",
                "body": {"username": "cookie-user", "password": "correct"},
                "use_session": "anonymous",
                "store_as": "cookie_primary",
                "owasp_category": "API2",
            },
            3,
        )
        assert "[SESSION STORED]" in cookie_login_result
        assert session_vault["cookie_primary"]["kind"] == "cookie"

        cookie_protected_result = await kwargs["tool_executor"](
            "http_request",
            {
                "method": "GET",
                "url": "https://api.local/api/cookie-private",
                "use_session": "cookie_primary",
                "owasp_category": "API2",
            },
            4,
        )
        assert "Status: 200" in cookie_protected_result
        return "done"

    monkeypatch.setattr(
        "aespa.services.scanner.llm_svc.thinking_agentic_loop",
        fake_agentic_loop,
    )
    monkeypatch.setattr(
        "aespa.services.scanner.events_svc.emit", lambda *args, **kwargs: None
    )

    async def run_scan():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await _do_agentic_thinking_loop(
                run_id=run.id,
                is_api_run=True,
                llm_cfg=SimpleNamespace(),
                base_url="https://api.local",
                crawl_context="API context",
                creds_for_llm=[],
                session_vault=session_vault,
                pages_snapshot=[],
                findings_snapshot=[],
                first_page_id=None,
                scanner_policy=SimpleNamespace(
                    execution_monitor_enabled=False,
                    max_consecutive_text_turns=0,
                    enforce_full_coverage_obligations=False,
                    min_delay_s=0,
                    scan_mode="safe_active",
                ),
                hx=client,
                browser_ctx=None,
                pw_page=None,
                history=[],
                all_results=[],
                scope_check_fn=lambda _url: None,
                system_message_override="API Test Lead",
                tools_override=get_sast_validate_tools(is_api_run=True),
                coverage_mode="sast_validate",
            )

    asyncio.run(run_scan())

    assert observed_authorization == ["Bearer eyJheader.eyJpayload.signature"]
    assert observed_cookies == ["sid=fresh-cookie"]
    persisted = load_session_vault(run.id, run_kind="api")
    assert "configured_primary" in persisted
    assert persisted["configured_primary"]["kind"] == "bearer"
    assert persisted["cookie_primary"]["cookies"] == {"sid": "fresh-cookie"}
