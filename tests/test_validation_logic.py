import asyncio
from types import SimpleNamespace

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.models import AgentLog, CrawledPage, ScanFinding, Site
from aespa.models import TestRun as RunModel
from aespa.services import llm, scanner, validator
from aespa.services.validator import _body_contains_page_evidence, _looks_like_spa_shell


def test_validate_finding_result_without_probe_results_is_false_positive():
    result = asyncio.run(llm.validate_finding_result(
        config=None,
        title="Possible issue",
        description="A finding that could not be reproduced.",
        evidence="REQUEST... RESPONSE...",
        probe_results=[],
    ))

    assert result["verdict"] == "false_positive"
    assert "No validation probes" in result["reasoning"]


def test_access_control_validation_without_credentials_is_unconfirmed():
    finding = ScanFinding(
        test_run_id=1,
        page_id=1,
        owasp_category="A01",
        severity="high",
        title="Authorization bypass",
        description="A protected page may be reachable without the right user.",
        affected_url="https://target.local/admin",
        evidence="",
    )

    result = asyncio.run(validator._deterministic_validate_finding(
        finding,
        cred_sessions={},
        scanner_policy=None,
    ))

    assert result is not None
    verdict, reason, poc_spec = result
    assert verdict == "unconfirmed"
    assert "no alternate user sessions" in reason
    assert poc_spec is None


def test_severity_threshold_skip_is_not_an_unconfirmed_verdict(monkeypatch):
    finding = ScanFinding(
        id=1,
        test_run_id=1,
        page_id=None,
        owasp_category="A05",
        severity="info",
        title="Informational header observation",
        description="Informational finding.",
    )
    persisted = []

    async def fake_persist(*args, **kwargs):
        persisted.append((args, kwargs))

    monkeypatch.setattr(validator, "_persist_verdict", fake_persist)
    monkeypatch.setattr(validator.events_svc, "emit", lambda *_args, **_kwargs: None)

    asyncio.run(validator._validate_one(
        1, finding, None, {}, None, None,
        validator_cfg=SimpleNamespace(min_severity="low", enabled=True),
    ))

    assert persisted[0][0][2] == "skipped"
    assert persisted[0][0][3].startswith("Not validated:")


def test_validation_batch_respects_concurrency_limit():
    active = 0
    peak = 0

    async def fake_validate(_finding):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1

    findings = [
        ScanFinding(
            id=index,
            test_run_id=1,
            page_id=None,
            owasp_category="A05",
            severity="low",
            title=str(index),
            description="test",
        )
        for index in range(8)
    ]
    asyncio.run(validator._run_validation_batch(findings, 3, fake_validate))

    assert peak == 3


def test_resume_interrupted_validations_requeues_only_orphaned_work(monkeypatch):
    from aespa import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        monkeypatch.setattr(validator, "get_engine", lambda: engine)
        with Session(engine) as session:
            session.add(ScanFinding(
                test_run_id=42,
                page_id=None,
                owasp_category="A01",
                severity="high",
                title="Interrupted validation",
                description="A validation task was interrupted.",
                validation_status="unvalidated",
                validation_note=(
                    "Validation was interrupted before a verdict (process restart); "
                    "reset for re-validation."
                ),
            ))
            session.add(ScanFinding(
                test_run_id=42,
                page_id=None,
                owasp_category="A01",
                severity="high",
                title="Ordinary unvalidated finding",
                description="This finding was not interrupted.",
                validation_status="unvalidated",
            ))
            session.commit()

        resumed = []

        async def fake_start_validation(run_id, finding_ids=None):
            resumed.append((run_id, finding_ids))

        monkeypatch.setattr(validator, "start_validation", fake_start_validation)
        asyncio.run(validator.resume_interrupted_validations())

        assert len(resumed) == 1
        assert resumed[0][0] == 42
        assert len(resumed[0][1]) == 1
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_validator_merges_active_primary_with_stored_role_sessions(monkeypatch):
    """Inline validation must not discard crawl-captured alternate roles."""
    primary = {
        "username": "admin",
        "label": "configured_primary",
        "cookies": {"sid": "admin"},
        "extra_headers": {},
    }
    monkeypatch.setattr(validator.scanner_svc, "get_active_sessions", lambda _: {1: primary})

    from aespa.services import scanner_sessions
    monkeypatch.setattr(scanner_sessions, "load_session_vault", lambda _: {
        "recon_2": {
            "label": "recon_2", "kind": "cookie", "username": "viewer",
            "credential_id": 2, "cookies": {"sid": "viewer"}, "extra_headers": {},
        },
    })

    sessions = asyncio.run(validator._get_or_create_sessions(
        1, "https://target.local", None,
        [SimpleNamespace(id=1, username="admin"), SimpleNamespace(id=2, username="viewer")],
        requires_auth=True,
    ))

    assert sessions[1]["username"] == "admin"
    assert sessions[2]["username"] == "viewer"


def test_validator_bootstraps_configured_users_when_auth_flag_is_stale(monkeypatch):
    credential = SimpleNamespace(id=7, username="viewer", label="Viewer")
    monkeypatch.setattr(validator.scanner_svc, "get_active_sessions", lambda _: None)
    from aespa.services import scanner_sessions
    monkeypatch.setattr(scanner_sessions, "load_session_vault", lambda _: {})

    async def export_session(*_args):
        return {"sid": "viewer"}, None

    monkeypatch.setattr(validator.scanner_svc, "_export_cred_session", export_session)

    sessions = asyncio.run(validator._get_or_create_sessions(
        1, "https://target.local", None, [credential], requires_auth=False,
    ))

    assert sessions[7]["cookies"] == {"sid": "viewer"}


def test_persist_verdict_appends_structured_validation_evidence(monkeypatch):
    from aespa import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    try:
        monkeypatch.setattr(validator, "get_engine", lambda: engine)
        emitted = []
        monkeypatch.setattr(validator.events_svc, "emit", lambda run_id, event: emitted.append(event))

        with Session(engine) as session:
            finding = ScanFinding(
                test_run_id=1,
                page_id=None,
                owasp_category="A01",
                severity="high",
                title="Authorization bypass",
                description="Protected resource accessible.",
                affected_url="https://target.local/admin",
                evidence="original evidence",
            )
            session.add(finding)
            session.commit()
            session.refresh(finding)
            finding_id = finding.id

        asyncio.run(validator._persist_verdict(
            1,
            finding_id,
            "confirmed",
            "Replay returned protected content.",
            validation_results=[{
                "desc": "Replay protected resource",
                "url": "https://target.local/admin",
                "status": 200,
                "as_user": "alice",
                "request_evidence": "GET /admin HTTP/1.1\nAuthorization: Bearer secret-token",
                "response_evidence": "HTTP/1.1 200 OK\n\nadmin panel",
                "duration_ms": 35,
                "timing_delta_ms": 900,
                "body_diff": {"added_terms": ["admin", "panel"]},
                "action_outcome": "Replay returned protected content.",
            }],
            source="test_validation",
        ))

        with Session(engine) as session:
            saved = session.get(ScanFinding, finding_id)

        item_types = {item["type"] for item in saved.evidence_items}
        assert {"validation_verdict", "validation_reasoning", "validation_probe", "validation_request", "validation_response", "timing", "timing_delta", "body_diff", "action_outcome"} <= item_types
        assert saved.validation_status == "confirmed"
        assert saved.validation_note == "Replay returned protected content."
        assert "secret-token" not in saved.evidence_json
        update_event = next(e for e in emitted if e.get("type") == "finding_validation_update")
        assert update_event["evidence_items"]
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


class _ScannerCredWithLogin:
    login_url = "https://target.local/customer/login"


def test_scanner_login_url_for_credential_prefers_override():
    assert scanner._login_url_for_credential(
        "https://target.local/login",
        _ScannerCredWithLogin(),
    ) == "https://target.local/customer/login"


def test_dynamic_scan_creates_page_for_findings_without_crawl():
    from aespa import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)

            run = RunModel(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)

            page_id = scanner._find_or_create_dynamic_page(
                session,
                run_id=run.id,
                url="https://target.local/api/accounts/1",
                base_url="https://target.local",
            )
            session.commit()

            page = session.get(CrawledPage, page_id)
            refreshed_run = session.get(RunModel, run.id)

        assert page is not None
        assert page.test_run_id == run.id
        assert page.url == "https://target.local/api/accounts/1"
        assert page.title == "Dynamic Scan target"
        assert refreshed_run.pages_discovered == 1
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_dynamic_scan_task_does_not_write_error_message(monkeypatch):
    from aespa import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    async def fake_do_thinking_scan(run_id: int) -> None:
        scanner._thinking_scan_status[run_id] = "complete"

    try:
        with Session(engine) as session:
            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)

            run = RunModel(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)
            run_id = run.id

        monkeypatch.setattr(scanner, "get_engine", lambda: engine)
        monkeypatch.setattr(scanner, "_do_thinking_scan", fake_do_thinking_scan)
        monkeypatch.setattr(scanner.events_svc, "emit", lambda *args, **kwargs: None)

        scanner._thinking_scan_status.pop(run_id, None)
        asyncio.run(scanner._thinking_scan_task(run_id))

        with Session(engine) as session:
            refreshed_run = session.get(RunModel, run_id)

        assert refreshed_run.error_message is None
    finally:
        scanner._thinking_scan_status.pop(locals().get("run_id", 0), None)
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_dynamic_scan_refusal_is_persisted_on_test_lead_log(monkeypatch):
    from aespa import db as db_module
    from aespa import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    refusal = (
        "LLM provider refused the scan request at step 84: This content was "
        "flagged for possible cybersecurity risk (cyber_policy)"
    )

    async def fake_do_thinking_scan(run_id: int) -> None:
        raise llm.LLMRefusalError(refusal)

    try:
        with Session(engine) as session:
            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)
            run = RunModel(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)
            run_id = run.id

        monkeypatch.setattr(scanner, "get_engine", lambda: engine)
        monkeypatch.setattr(db_module, "get_engine", lambda: engine)
        monkeypatch.setattr(scanner, "_do_thinking_scan", fake_do_thinking_scan)

        scanner._thinking_scan_status.pop(run_id, None)
        asyncio.run(scanner._thinking_scan_task(run_id))

        with Session(engine) as session:
            failure = session.exec(
                select(AgentLog)
                .where(AgentLog.test_run_id == run_id)
                .where(AgentLog.agent_id == "scanner")
                .where(AgentLog.status == "failed")
            ).one()

        assert scanner._thinking_scan_status[run_id] == "failed"
        assert failure.role == "Test Lead"
        assert failure.current_task == "LLM provider refusal"
        assert failure.outcome == refusal
    finally:
        scanner._thinking_scan_status.pop(locals().get("run_id", 0), None)
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_dynamic_scan_page_creation_reuses_existing_page():
    from aespa import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)

            run = RunModel(site_id=site.id, name="Run #1", pages_discovered=1)
            session.add(run)
            session.commit()
            session.refresh(run)

            existing = CrawledPage(
                test_run_id=run.id,
                url="https://target.local/api/accounts/1",
                title="Existing",
            )
            session.add(existing)
            session.commit()
            session.refresh(existing)

            page_id = scanner._find_or_create_dynamic_page(
                session,
                run_id=run.id,
                url="https://target.local/api/accounts/1",
                base_url="https://target.local",
            )
            pages = session.exec(select(CrawledPage)).all()
            refreshed_run = session.get(RunModel, run.id)

        assert page_id == existing.id
        assert len(pages) == 1
        assert refreshed_run.pages_discovered == 1
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_dynamic_finding_write_persists_immediately(monkeypatch):
    from aespa import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(scanner, "get_engine", lambda: engine)

    try:
        with Session(engine) as session:
            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)

            run = RunModel(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)

            page = CrawledPage(
                test_run_id=run.id,
                url="https://target.local/api/login",
                title="API POST /api/login",
                status="crawled",
                in_scope=True,
            )
            session.add(page)
            session.commit()
            session.refresh(page)

            raw = {
                "owasp_category": "A02",
                "title": "Password hash exposed in login API response",
                "description": "The login response exposes password_hash.",
                "impact": "Attackers can use leaked hashes for offline cracking.",
                "likelihood": "Likely for any user who can call the endpoint.",
                "recommendation": "Remove password hashes from API responses.",
                "cvss_score": 7.5,
                "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N",
                "affected_url": page.url,
                "evidence": "password_hash was present in the JSON response.",
                "request_evidence": "POST /api/login",
                "response_evidence": "Status: 200\n{\"password_hash\":\"...\"}",
            }
            result_by_url = {
                page.url: {
                    "url": page.url,
                    "request_evidence": raw["request_evidence"],
                    "response_evidence": raw["response_evidence"],
                }
            }

            saved = asyncio.run(scanner._persist_dynamic_finding(
                run_id=run.id,
                llm_cfg=object(),
                raw=raw,
                base_url="https://target.local",
                pages_snapshot=[{"id": page.id, "url": page.url}],
                first_page_id=page.id,
                result_by_url=result_by_url,
            ))
            duplicate = asyncio.run(scanner._persist_dynamic_finding(
                run_id=run.id,
                llm_cfg=object(),
                raw=raw,
                base_url="https://target.local",
                pages_snapshot=[{"id": page.id, "url": page.url}],
                first_page_id=page.id,
                result_by_url=result_by_url,
            ))

            findings = session.exec(select(ScanFinding)).all()

        assert saved is not None
        assert saved.title == "Password hash exposed in login API response"
        assert duplicate is None
        assert len(findings) == 1
        assert findings[0].validation_status == "unvalidated"
        assert findings[0].validation_note is None
        assert "password_hash" in findings[0].response_evidence
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_followup_log_message_names_signal_and_hypothesis():
    probes = [{
        "type": "http",
        "method": "POST",
        "url": "https://target.local/api/transfers",
        "body": {"amount": 100, "toAccount": "10000001"},
        "interesting_result": "2FA check returned requires_2fa=true",
        "hypothesis": "transfer endpoint may not enforce 2FA server-side",
        "payload_purpose": "omit the 2FA token from the transfer request",
        "desc": "Follow-up: submit transfer without 2FA token.",
    }]

    message = scanner._followup_log_message(probes)

    assert "looked interesting" not in message
    assert "2FA check returned requires_2fa=true" in message
    assert "transfer endpoint may not enforce 2FA" in message
    assert "omit the 2FA token" in message


def test_thinking_jwt_helper_signs_hs256_token():
    token = scanner._sign_hs256_jwt(
        "test-secret",
        {"iss": "BankOfEd", "sub": 1, "jti": "aespa-test"},
    )

    header, payload, signature = token.split(".")

    assert header
    assert payload
    assert signature
    assert token == scanner._sign_hs256_jwt(
        "test-secret",
        {"iss": "BankOfEd", "sub": 1, "jti": "aespa-test"},
    )


def test_credential_check_redacts_passwords():
    redacted = scanner._redact_candidate({
        "username": "admin",
        "password": "admin123",
    })

    assert redacted == {"username": "admin", "password": "***"}


def test_thinking_session_helpers_extract_and_redact_jwt():
    token = scanner._sign_hs256_jwt("secret", {"sub": 1})
    body = f'{{"success":true,"data":{{"token":"{token}"}}}}'

    assert scanner._extract_bearer_token_from_body(body) == token
    assert token not in scanner._redact_sensitive_text(body)
    assert "[REDACTED_JWT]" in scanner._redact_sensitive_text(body)


def test_spa_shell_is_not_treated_as_protected_content():
    body = """
    <!doctype html>
    <html><head><script src="/assets/app.js"></script></head>
    <body><div id="root"></div></body></html>
    """

    assert _looks_like_spa_shell(body, "text/html; charset=utf-8") is True
    assert _body_contains_page_evidence(body, "Admin Dashboard", "Secret invoice data") is False


def test_page_evidence_detection_matches_authorized_content():
    body = "<html><body><h1>Admin Dashboard</h1><p>Quarterly revenue export is ready.</p></body></html>"

    assert _body_contains_page_evidence(
        body,
        "Admin Dashboard",
        "Quarterly revenue export is ready.",
    ) is True


def test_bac_evidence_requires_original_user_content():
    original_text = """
    Account overview
    Statement balance for Alice Example is GBP 1,204.55
    Recent transfer reference ALICE-7781 is pending review
    """
    alternate_body = """
    <html><body>
      <h1>Account overview</h1>
      <p>Statement balance for Bob Example is GBP 88.10</p>
      <p>Recent transfer reference BOB-4412 is pending review</p>
    </body></html>
    """

    assert scanner._body_contains_original_page_evidence(
        alternate_body,
        "Account overview",
        original_text,
    ) is False


def test_bac_evidence_matches_original_user_content():
    original_text = """
    Account overview
    Statement balance for Alice Example is GBP 1,204.55
    Recent transfer reference ALICE-7781 is pending review
    """
    leaked_body = """
    <html><body>
      <h1>Account overview</h1>
      <p>Statement balance for Alice Example is GBP 1,204.55</p>
    </body></html>
    """

    assert scanner._body_contains_original_page_evidence(
        leaked_body,
        "Account overview",
        original_text,
    ) is True


def test_thinking_context_tools_filter_routes_and_history():
    pages = [
        {
            "id": 1,
            "url": "https://target.local/",
            "title": "Home",
            "context": "landing page",
            "page_text": "<html>Home</html>",
            "req_auth": False,
            "takes_input": False,
            "has_object_ref": False,
            "has_business_logic": False,
        },
        {
            "id": 2,
            "url": "https://target.local/api/search?q=test",
            "title": "API GET /api/search",
            "context": "search endpoint",
            "page_text": "GET /api/search?q=test\nHTTP/1.1 200 OK",
            "req_auth": True,
            "takes_input": True,
            "has_object_ref": False,
            "has_business_logic": False,
        },
    ]
    history = [{
        "step": 1,
        "method": "GET",
        "url": "https://target.local/api/search?q=test",
        "note": "Baseline search",
        "request_body": None,
        "response_status": 200,
        "response_headers": {"content-type": "application/json"},
        "response_body": '{"results":[]}',
    }]

    site_map = scanner._run_thinking_context_tool(
        "site_map",
        {"filter": "api takes-input", "flags": ["takes_input"]},
        pages_snapshot=pages,
        findings_snapshot=[],
        history=history,
    )
    detail = scanner._run_thinking_context_tool(
        "page_detail",
        {"page_id": 2, "include": ["context", "page_text"]},
        pages_snapshot=pages,
        findings_snapshot=[],
        history=history,
    )
    history_result = scanner._run_thinking_context_tool(
        "history_search",
        {"query": "Baseline"},
        pages_snapshot=pages,
        findings_snapshot=[],
        history=history,
    )

    assert site_map["count"] == 1
    assert site_map["routes"][0]["page_id"] == 2
    assert detail["context"] == "search endpoint"
    assert "GET /api/search" in detail["page_text"]
    assert history_result["count"] == 1
    assert history_result["matches"][0]["response_status"] == 200


def test_thinking_context_tools_compare_mutate_and_extract():
    history = [
        {
            "step": 1,
            "method": "GET",
            "url": "https://target.local/api/accounts/1?user_id=1",
            "note": "Baseline account",
            "request_body": None,
            "response_status": 200,
            "response_headers": {"content-type": "application/json"},
            "response_body": '{"account_id":1,"owner":"amelia"}',
        },
        {
            "step": 2,
            "method": "GET",
            "url": "https://target.local/api/accounts/2?user_id=2",
            "note": "Mutated account",
            "request_body": None,
            "response_status": 403,
            "response_headers": {"content-type": "application/json"},
            "response_body": '{"error":"forbidden"}',
        },
    ]

    compare = scanner._run_thinking_context_tool(
        "compare_responses",
        {"left_step": 1, "right_step": 2},
        pages_snapshot=[],
        findings_snapshot=[],
        history=history,
    )
    mutate = scanner._run_thinking_context_tool(
        "mutate_request",
        {"step": 1, "mutation": "idor", "limit": 5},
        pages_snapshot=[],
        findings_snapshot=[],
        history=history,
        base_url="https://target.local",
    )
    entities = scanner._run_thinking_context_tool(
        "extract_entities",
        {"step": 1},
        pages_snapshot=[],
        findings_snapshot=[],
        history=history,
    )

    assert compare["status_changed"] is True
    assert compare["right"]["status"] == 403
    assert mutate["count"] > 0
    assert any("IDOR" in probe["desc"] for probe in mutate["probes"])
    assert "1" in entities["entities"]["ids"]


def test_context_tool_checkpoint_allows_reasoned_extension():
    checkpoint = scanner._context_tool_checkpoint_output("site_map", 3)

    assert "checkpoint reached" in checkpoint["error"]
    assert checkpoint["checkpoint"]["checkpoint_interval"] == 3
    assert "context_budget_reason" in checkpoint["checkpoint"]["next_options"][2]
    assert scanner._context_budget_reason({"context_budget_reason": "Need exact IDs."}) == "Need exact IDs."
    assert scanner._context_budget_reason({"note": "no budget reason"}) == ""


def test_request_stop_cancels_running_validation(monkeypatch):
    class FakeTask:
        cancelled = False

        def cancel(self):
            self.cancelled = True

    task = FakeTask()
    reset_calls = []
    monkeypatch.setattr(validator, "_reset_validating_findings", lambda run_id, note: reset_calls.append((run_id, note)))
    validator._validation_tasks[123] = task
    validator._stop_requested.discard(123)

    try:
        assert validator.request_stop(123) is True
        assert task.cancelled is True
        assert 123 in validator._stop_requested
        assert reset_calls == [(123, "Validation stopped by user.")]
    finally:
        validator._validation_tasks.pop(123, None)
        validator._stop_requested.discard(123)


def test_request_stop_noops_when_validation_not_running(monkeypatch):
    reset_calls = []
    monkeypatch.setattr(validator, "_reset_validating_findings", lambda run_id, note: reset_calls.append((run_id, note)))
    validator._validation_tasks.pop(456, None)
    validator._stop_requested.discard(456)

    assert validator.request_stop(456) is False
    assert 456 not in validator._stop_requested
    assert reset_calls == []


def test_static_assets_are_not_protected_endpoints():
    # A .js file whose path contains a sensitive-looking word must not be treated
    # as an auth-protected endpoint (would raise a bogus "unauthenticated access").
    for url in (
        "https://target.local/static/js/user-profile.js",
        "https://target.local/assets/admin.mjs",
        "https://target.local/css/account.css",
        "https://target.local/app.js?v=3",
    ):
        assert scanner._is_static_asset_url(url) is True
        assert scanner._target_requires_auth_or_sensitive({"url": url}) is False


def test_static_asset_check_still_flags_real_endpoints():
    assert scanner._is_static_asset_url("https://target.local/admin/users") is False
    assert scanner._target_requires_auth_or_sensitive(
        {"url": "https://target.local/admin/users"}
    ) is True


def test_deterministic_result_analysis_detects_sql_error():
    findings = scanner._deterministic_findings_from_results(
        run_id=1,
        page_id=2,
        page_url="https://target.local/search?q=test",
        results=[{
            "desc": "SQLi in param 'q': ' OR '1'='1",
            "url": "https://target.local/search?q=%27",
            "status": 500,
            "headers": {"content-type": "text/html"},
            "body": "SQL syntax error near unexpected quote",
            "request_evidence": "GET /search?q='",
            "response_evidence": "HTTP/1.1 500\nSQL syntax error",
        }],
    )

    assert len(findings) == 1
    assert findings[0].title == "SQL injection error disclosure"
    assert findings[0].finding_source == "deterministic_probe"
    assert findings[0].validation_status == "confirmed"


def test_deterministic_result_analysis_detects_reflected_xss():
    payload = '"><img src=x onerror=alert(1)>'
    findings = scanner._deterministic_findings_from_results(
        run_id=1,
        page_id=2,
        page_url="https://target.local/search?q=test",
        results=[{
            "desc": f"XSS in param 'q': {payload}",
            "url": "https://target.local/search?q=x",
            "status": 200,
            "headers": {"content-type": "text/html"},
            "body": f"<html>Results for {payload}</html>",
            "request_evidence": "GET /search?q=payload",
            "response_evidence": f"HTTP/1.1 200\n{payload}",
        }],
    )

    assert len(findings) == 1
    assert findings[0].title == "Reflected cross-site scripting"
    assert findings[0].owasp_category == "A03"


def test_dynamic_deterministic_analysis_persists_findings(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            site = Site(name="Target", base_url="https://target.local")
            session.add(site)
            session.commit()
            session.refresh(site)

            run = RunModel(site_id=site.id, name="Run #1")
            session.add(run)
            session.commit()
            session.refresh(run)

            page = CrawledPage(
                test_run_id=run.id,
                url="https://target.local/search",
                status="crawled",
                in_scope=True,
            )
            session.add(page)
            session.commit()
            session.refresh(page)

            run_id = run.id
            page_id = page.id

        monkeypatch.setattr(scanner, "get_engine", lambda: engine)
        monkeypatch.setattr(scanner.events_svc, "emit", lambda *args, **kwargs: None)

        saved = scanner._run_deterministic_analysis_for_dynamic_results(
            run_id=run_id,
            base_url="https://target.local",
            pages_snapshot=[{"id": page_id, "url": "https://target.local/search"}],
            first_page_id=page_id,
            results=[{
                "desc": "SQLi in param 'q': ' OR '1'='1",
                "url": "https://target.local/search?q=%27",
                "status": 500,
                "headers": {"content-type": "text/html"},
                "body": "SQL syntax error near unexpected quote",
                "request_evidence": "GET /search?q='",
                "response_evidence": "HTTP/1.1 500\nSQL syntax error",
            }],
        )

        with Session(engine) as session:
            findings = session.exec(select(ScanFinding)).all()

        assert saved == 1
        assert len(findings) == 1
        assert findings[0].title == "SQL injection error disclosure"
        assert findings[0].finding_source == "deterministic_probe"
        assert findings[0].page_id == page_id
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_deterministic_sessions_from_vault_merges_non_anonymous_sessions(monkeypatch):
    monkeypatch.setattr(
        scanner,
        "_merge_persisted_sessions",
        lambda run_id, sessions: sessions,
    )

    sessions = scanner._deterministic_sessions_from_vault(
        1,
        {
            "anonymous": {"kind": "anonymous", "cookies": {"a": "1"}},
            "configured_primary": {
                "kind": "cookie",
                "username": "alice",
                "credential_id": 42,
                "cookies": {"sid": "abc"},
                "extra_headers": {},
            },
            "registered_user": {
                "kind": "bearer",
                "username": "bob",
                "extra_headers": {"Authorization": "Bearer token"},
            },
        },
    )

    assert 42 in sessions
    assert sessions[42]["username"] == "alice"
    synthetic = [key for key in sessions if key < 0]
    assert len(synthetic) == 1
    assert sessions[synthetic[0]]["username"] == "bob"


def test_thinking_action_log_message_describes_investigation_and_payload():
    action = {
        "note": "Found something interesting.",
        "observation": "search reflected the q parameter in HTML",
        "hypothesis": "reflected XSS in the search endpoint",
        "payload_purpose": (
            "inject an event-handler payload to test script execution context"
        ),
        "body": {"q": "\" autofocus onfocus=alert(1) x=\""},
    }

    message = scanner._thinking_action_log_message(
        4,
        "POST",
        "https://target.local/search?debug=true",
        action,
    )

    assert "Found something interesting" not in message
    assert "reflected XSS in the search endpoint" in message
    assert "search reflected the q parameter" in message
    assert "event-handler payload" in message
    assert "query payloads: debug=true" in message
    assert "body payload:" in message
