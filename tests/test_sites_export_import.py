"""Round-trip test for export_site/import_site, focused on the run-child tables
that were previously dropped (workprogram, checkpoint, agent logs, ALICE chat)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa import models as _models  # noqa: F401  (register tables)
from aespa.models import (
    AgentLog,
    AliceChatMessage,
    AliceChatSession,
    CrawledPage,
    PageOwaspTest,
    ScanCheckpoint,
    ScanFinding,
    Site,
    TestRun,
)
from aespa.services import sites as sites_service


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_roundtrip_includes_run_children(session):
    site = Site(name="acme", base_url="http://acme.test")
    session.add(site)
    session.flush()
    run = TestRun(site_id=site.id, name="run-1", status="scanned")
    session.add(run)
    session.flush()
    page = CrawledPage(test_run_id=run.id, url="http://acme.test/login")
    session.add(page)
    session.flush()
    finding = ScanFinding(
        test_run_id=run.id, page_id=page.id, owasp_category="A01",
        severity="high", title="IDOR", description="x",
    )
    session.add(finding)
    session.flush()

    session.add(PageOwaspTest(
        test_run_id=run.id, page_id=page.id, owasp_category="A01",
        status="finding", finding_ids_json=json.dumps([finding.id]),
    ))
    session.add(ScanCheckpoint(test_run_id=run.id, step_count=7))
    session.add(AgentLog(test_run_id=run.id, run_kind="web", agent_id="scanner", role="test_lead", status="active"))
    alice = AliceChatSession(test_run_id=run.id, run_kind="web", session_key="tab-1")
    session.add(alice)
    session.flush()
    session.add(AliceChatMessage(session_id=alice.id, message_key="m1", sender="user", text="hi"))
    session.commit()

    bundle = sites_service.export_site(session, site.id)
    new_site = sites_service.import_site(session, bundle)

    new_run = session.exec(select(TestRun).where(TestRun.site_id == new_site.id)).one()
    rid = new_run.id

    owasp = session.exec(select(PageOwaspTest).where(PageOwaspTest.test_run_id == rid)).all()
    assert len(owasp) == 1
    new_finding = session.exec(select(ScanFinding).where(ScanFinding.test_run_id == rid)).one()
    # finding_ids_json must point at the *new* finding id, not the stale one.
    assert json.loads(owasp[0].finding_ids_json) == [new_finding.id]

    assert session.exec(select(ScanCheckpoint).where(ScanCheckpoint.test_run_id == rid)).one().step_count == 7
    assert len(session.exec(select(AgentLog).where(AgentLog.test_run_id == rid)).all()) == 1

    new_alice = session.exec(select(AliceChatSession).where(AliceChatSession.test_run_id == rid)).one()
    msgs = session.exec(select(AliceChatMessage).where(AliceChatMessage.session_id == new_alice.id)).all()
    assert len(msgs) == 1 and msgs[0].text == "hi"
