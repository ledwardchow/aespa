"""Tests for Phase 1 recon summary: build_recon_summary and context builder fallback."""

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.models import (
    CrawledPage,
    Credential,
    PageCredentialView,
    PageOwaspTest,
    Site,
    TargetIntelItem,
)
from aespa.models import TestRun as RunModel
from aespa.services import recon_summary as recon_summary_svc
from aespa.services import scanner


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _seed_run(session, engine):
    """Create a minimal Site + TestRun and return the run."""
    site = Site(name="test-site", base_url="https://target.local")
    session.add(site)
    session.flush()
    run = RunModel(site_id=site.id, name="test-run")
    session.add(run)
    session.flush()
    return run


# ── build_recon_summary ────────────────────────────────────────────────────────


def test_build_recon_summary_access_observations(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id

        credential = Credential(
            site_id=run.site_id, username="alice", password="secret", label="Customer"
        )
        s.add(credential)
        s.flush()
        public = CrawledPage(
            test_run_id=run_id,
            url="https://target.local/",
            req_auth=False,
            takes_input=False,
        )
        account = CrawledPage(
            test_run_id=run_id,
            url="https://target.local/account",
            req_auth=True,
            takes_input=True,
            accessible_by=f"[{credential.id}]",
        )
        mixed = CrawledPage(
            test_run_id=run_id,
            url="https://target.local/profile",
            req_auth=False,
            accessible_by=f"[{credential.id}]",
        )
        s.add(public)
        s.add(account)
        s.add(mixed)
        s.flush()
        s.add(
            PageCredentialView(
                page_id=account.id,
                test_run_id=run_id,
                credential_id=credential.id,
                username="alice",
                req_auth=True,
            )
        )
        s.commit()

    summary = recon_summary_svc.build_recon_summary(run_id)

    routes = {route["canonical_url"]: route for route in summary["routes"]}
    assert routes["https://target.local/"]["access"]["classification"] == "anonymous"
    assert (
        routes["https://target.local/account"]["access"]["classification"]
        == "authenticated"
    )
    assert routes["https://target.local/profile"]["access"]["classification"] == "mixed"
    assert routes["https://target.local/account"]["access"]["labels"] == ["Customer"]
    assert summary["access"]["profiles"][0]["username"] == "alice"


def test_build_recon_summary_evidence_signals(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id

        # Object-reference page → should trigger idor class
        s.add(
            CrawledPage(
                test_run_id=run_id,
                url="https://target.local/users/42",
                req_auth=True,
                takes_input=False,
                has_object_ref=True,
            )
        )
        # Business logic page
        s.add(
            CrawledPage(
                test_run_id=run_id,
                url="https://target.local/checkout",
                req_auth=False,
                takes_input=True,
                has_business_logic=True,
            )
        )
        # Sensitive response field
        s.add(
            TargetIntelItem(
                test_run_id=run_id,
                kind="response_field",
                key="secret_token",
                value="",
                url="https://target.local/api/user",
            )
        )
        s.commit()

    summary = recon_summary_svc.build_recon_summary(run_id)

    signal_types = {item["type"] for item in summary["signals"]["items"]}
    assert signal_types == {"object_reference", "business_logic", "sensitive_field"}
    assert all("priority" not in item for item in summary["signals"]["items"])


def test_build_recon_summary_persists_to_run(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.add(
            CrawledPage(
                test_run_id=run_id,
                url="https://target.local/",
                req_auth=False,
                takes_input=False,
            )
        )
        s.commit()

    recon_summary_svc.build_recon_summary(run_id)

    with Session(engine) as s:
        run = s.get(RunModel, run_id)
        assert run.recon_summary is not None
        import json

        data = json.loads(run.recon_summary)
        assert data["schema_version"] == 2
        assert "routes" in data
        assert "coverage" in data


def test_build_recon_summary_routes_deduplicated_and_parameters_retained(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        url = "https://target.local/search"
        s.add(
            CrawledPage(test_run_id=run_id, url=url, req_auth=False, takes_input=True)
        )
        # Same URL added as intel input — should not double-count
        s.add(
            TargetIntelItem(
                test_run_id=run_id,
                kind="input",
                key="q",
                value="",
                url=url,
                method="GET",
            )
        )
        s.commit()

    summary = recon_summary_svc.build_recon_summary(run_id)

    matching = [route for route in summary["routes"] if route["canonical_url"] == url]
    assert len(matching) == 1
    assert matching[0]["parameters"] == ["q"]


def test_build_recon_summary_uses_endpoint_destination_not_source_asset(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.add(
            CrawledPage(
                test_run_id=run_id, url="https://target.local/dashboard", req_auth=False
            )
        )
        s.add(
            TargetIntelItem(
                test_run_id=run_id,
                kind="endpoint",
                key="/api/transfers/check",
                value="https://target.local/api/transfers/check",
                url="https://target.local/assets/api.js",
                method="POST",
                source="public_asset",
                item_metadata='{"page_url":"https://target.local/dashboard"}',
            )
        )
        s.add(
            TargetIntelItem(
                test_run_id=run_id,
                kind="input",
                key="account_id",
                value="js_request_body",
                url="https://target.local/api/transfers/check",
                method="POST",
                source="public_asset",
            )
        )
        s.commit()

    summary = recon_summary_svc.build_recon_summary(run_id)
    route = next(
        route
        for route in summary["routes"]
        if route["canonical_url"].endswith("/api/transfers/check")
    )
    assert route["methods"] == ["POST"]
    assert route["parameters"] == ["account_id"]
    assert route["source_urls"] == [
        "https://target.local/assets/api.js",
        "https://target.local/dashboard",
    ]
    assert not any(
        route["canonical_url"].endswith("api.js") for route in summary["routes"]
    )


def test_build_recon_summary_coverage_is_live_workprogram_projection(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        page = CrawledPage(
            test_run_id=run_id, url="https://target.local/users/42", req_auth=False
        )
        s.add(page)
        s.flush()
        s.add(
            PageOwaspTest(
                test_run_id=run_id,
                page_id=page.id,
                owasp_category="A01",
                status="finding",
            )
        )
        s.add(
            PageOwaspTest(
                test_run_id=run_id,
                page_id=page.id,
                owasp_category="A03",
                status="not_started",
            )
        )
        s.commit()

    summary = recon_summary_svc.build_recon_summary(run_id)
    assert summary["coverage"]["statuses"]["finding"] == 1
    assert summary["coverage"]["statuses"]["not_started"] == 1
    assert summary["coverage"]["completion_percent"] == 50
    assert summary["coverage"]["by_category"][0]["category"] == "A03"
    route = summary["routes"][0]
    assert route["canonical_url"] == "https://target.local/users/{id}"
    assert route["coverage"]["statuses"] == {"finding": 1, "not_started": 1}
    assert route["coverage"]["remaining_categories"] == ["A03"]


# ── _build_thinking_context_from_recon_summary ─────────────────────────────────


def test_thinking_context_falls_back_when_no_summary(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    # Patch scanner's get_engine too so DB reads work
    import aespa.services.scanner as scanner_mod

    monkeypatch.setattr(scanner_mod, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.commit()

    # No recon_summary saved yet — should return fallback compact context
    context = scanner._build_thinking_context_from_recon_summary(
        run_id,
        base_url="https://target.local",
        findings_snapshot=[],
    )
    assert "https://target.local" in context


def test_thinking_context_uses_summary_when_present(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    import aespa.services.scanner as scanner_mod

    monkeypatch.setattr(scanner_mod, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.add(
            CrawledPage(
                test_run_id=run_id,
                url="https://target.local/users/1",
                req_auth=True,
                takes_input=False,
                has_object_ref=True,
            )
        )
        s.add(
            TargetIntelItem(
                test_run_id=run_id,
                kind="response_field",
                key="secret_key",
                value="",
                url="https://target.local/api/me",
            )
        )
        s.commit()

    recon_summary_svc.build_recon_summary(run_id)

    context = scanner._build_thinking_context_from_recon_summary(
        run_id,
        base_url="https://target.local",
        findings_snapshot=[],
    )
    assert "Recon brief" in context
    assert "Actionable route sample" in context
    assert "priority order" not in context


def test_thinking_context_includes_confirmed_findings(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(recon_summary_svc, "get_engine", lambda: engine)

    import aespa.services.scanner as scanner_mod

    monkeypatch.setattr(scanner_mod, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.commit()

    # Even without a summary, confirmed findings must appear in the fallback
    findings = [
        {
            "severity": "high",
            "owasp": "A01",
            "title": "Admin bypass",
            "affected_url": "https://target.local/admin",
        }
    ]
    context = scanner._build_thinking_context_from_recon_summary(
        run_id,
        base_url="https://target.local",
        findings_snapshot=findings,
    )
    assert "Admin bypass" in context
    assert "do NOT re-test" in context
