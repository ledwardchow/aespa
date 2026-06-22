"""Tests for Phase 1 recon summary: build_recon_summary and context builder fallback."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.models import CrawledPage, Site, TargetIntelItem
from aespa.models import TestRun as RunModel
from aespa.services import scanner
from aespa.services import task_graph as task_graph_svc


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

def test_build_recon_summary_trust_zones(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id

        # Public page (no req_auth)
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/", req_auth=False, takes_input=False))
        # Auth page (req_auth = True)
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/account", req_auth=True, takes_input=True))
        # Admin page
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/admin/users", req_auth=True, takes_input=False))
        s.commit()

    summary = task_graph_svc.build_recon_summary(run_id)

    assert "https://target.local/" in summary["trust_zones"]["public"]
    assert "https://target.local/account" in summary["trust_zones"]["user"]
    assert "https://target.local/admin/users" in summary["trust_zones"]["admin"]


def test_build_recon_summary_attack_classes_populated(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id

        # Object-reference page → should trigger idor class
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/users/42",
                          req_auth=True, takes_input=False, has_object_ref=True))
        # Business logic page
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/checkout",
                          req_auth=False, takes_input=True, has_business_logic=True))
        # Sensitive response field
        s.add(TargetIntelItem(test_run_id=run_id, kind="response_field", key="secret_token",
                              value="", url="https://target.local/api/user"))
        s.commit()

    summary = task_graph_svc.build_recon_summary(run_id)

    class_ids = [c["id"] for c in summary["attack_classes"]]
    assert "idor" in class_ids
    assert "data_exposure" in class_ids
    assert "business_logic" in class_ids

    # Highest priority class should come first
    priorities = [c["priority"] for c in summary["attack_classes"]]
    assert priorities == sorted(priorities, reverse=True)


def test_build_recon_summary_persists_to_run(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/", req_auth=False, takes_input=False))
        s.commit()

    task_graph_svc.build_recon_summary(run_id)

    with Session(engine) as s:
        run = s.get(RunModel, run_id)
        assert run.recon_summary is not None
        import json
        data = json.loads(run.recon_summary)
        assert "trust_zones" in data
        assert "attack_classes" in data


def test_build_recon_summary_entry_points_deduplicated(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        url = "https://target.local/search"
        s.add(CrawledPage(test_run_id=run_id, url=url, req_auth=False, takes_input=True))
        # Same URL added as intel input — should not double-count
        s.add(TargetIntelItem(test_run_id=run_id, kind="input", key="q", value="", url=url, method="GET"))
        s.commit()

    summary = task_graph_svc.build_recon_summary(run_id)

    # After dedup, only one entry point for this URL+method
    matching = [ep for ep in summary["entry_points"] if ep["url"] == url and ep["method"] == "GET"]
    assert len(matching) == 1


# ── seed_task_graph with summary ───────────────────────────────────────────────

def test_seed_task_graph_from_summary_creates_correct_hypothesis_areas(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/users/1",
                          req_auth=True, takes_input=False, has_object_ref=True))
        s.commit()

    summary = task_graph_svc.build_recon_summary(run_id)
    result = task_graph_svc.seed_task_graph(run_id, summary=summary)

    assert result["hypotheses_created"] > 0
    assert result["tasks_created"] > 0


# ── _build_thinking_context_from_recon_summary ─────────────────────────────────

def test_thinking_context_falls_back_when_no_summary(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

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
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

    import aespa.services.scanner as scanner_mod
    monkeypatch.setattr(scanner_mod, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.add(CrawledPage(test_run_id=run_id, url="https://target.local/users/1",
                          req_auth=True, takes_input=False, has_object_ref=True))
        s.add(TargetIntelItem(test_run_id=run_id, kind="response_field", key="secret_key",
                              value="", url="https://target.local/api/me"))
        s.commit()

    task_graph_svc.build_recon_summary(run_id)

    context = scanner._build_thinking_context_from_recon_summary(
        run_id,
        base_url="https://target.local",
        findings_snapshot=[],
    )
    assert "Attack surface snapshot" in context
    assert "attack_classes" in context.lower() or "idor" in context.lower()


def test_thinking_context_includes_confirmed_findings(monkeypatch):
    engine = _make_engine()
    monkeypatch.setattr(task_graph_svc, "get_engine", lambda: engine)

    import aespa.services.scanner as scanner_mod
    monkeypatch.setattr(scanner_mod, "get_engine", lambda: engine)

    with Session(engine) as s:
        run = _seed_run(s, engine)
        run_id = run.id
        s.commit()

    # Even without a summary, confirmed findings must appear in the fallback
    findings = [{"severity": "high", "owasp": "A01", "title": "Admin bypass", "affected_url": "https://target.local/admin"}]
    context = scanner._build_thinking_context_from_recon_summary(
        run_id,
        base_url="https://target.local",
        findings_snapshot=findings,
    )
    assert "Admin bypass" in context
    assert "do NOT re-test" in context
