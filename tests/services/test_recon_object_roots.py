from __future__ import annotations

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.models import (
    CrawledPage,
    Credential,
    DiscoveredTarget,
    PageOwaspTest,
    ScanObligation,
    Site,
    TargetAccessObservation,
    TestRun,
    TrafficEntry,
)
from aespa.services.recon_summary import build_recon_summary


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _run(session):
    site = Site(name="shop", base_url="https://shop.test")
    session.add(site)
    session.flush()
    run = TestRun(site_id=site.id, name="shop")
    session.add(run)
    session.flush()
    return run


def _direct(session, run_id, url, actor, result, status):
    target = session.exec(
        select(DiscoveredTarget).where(
            DiscoveredTarget.test_run_id == run_id, DiscoveredTarget.url == url
        )
    ).first()
    if target is None:
        target = DiscoveredTarget(
            test_run_id=run_id, url=url, route_pattern="https://shop.test/orders/{id}"
        )
        session.add(target)
        session.flush()
    traffic = TrafficEntry(
        test_run_id=run_id,
        source="httpx",
        method="GET",
        url=url,
        username="alice" if actor.startswith("credential:") else None,
        status=status,
    )
    session.add(traffic)
    session.flush()
    session.add(
        TargetAccessObservation(
            test_run_id=run_id,
            target_id=target.id,
            method="GET",
            actor_key=actor,
            source_kind="traffic",
            source_id=traffic.id,
            result=result,
        )
    )
    session.flush()
    return target


def test_direct_access_keeps_protected_member_and_evidence_with_public_sibling():
    with _session() as session:
        run = _run(session)
        credential = Credential(
            site_id=run.site_id, username="alice", password="secret"
        )
        session.add(credential)
        session.flush()
        _direct(
            session, run.id, "https://shop.test/orders/101", "anonymous", "reached", 200
        )
        _direct(
            session,
            run.id,
            "https://shop.test/orders/202",
            f"credential:{credential.id}",
            "reached",
            200,
        )
        _direct(
            session,
            run.id,
            "https://shop.test/orders/202",
            "unknown:session",
            "reached",
            200,
        )
        summary = build_recon_summary(run.id, session=session, persist=False)
        route = next(
            row
            for row in summary["routes"]
            if row["canonical_url"] == "https://shop.test/orders/{id}"
        )
        access = route["access"]
        assert access["classification"] == "mixed"
        assert access["needs_anonymous_comparison"] is True
        by_url = {member["url"]: member for member in access["members"]}
        protected = by_url["https://shop.test/orders/202"]
        assert protected["anonymous"] is False
        assert protected["anonymous_observed"] is False
        assert protected["credential_ids"] == [credential.id]
        assert protected["observations"][0]["result"] == "reached"
        assert protected["observations"][0]["source_kind"] == "traffic"
        assert protected["observations"][0]["source_id"] > 0

        _direct(
            session, run.id, "https://shop.test/orders/202", "anonymous", "denied", 403
        )
        after = build_recon_summary(run.id, session=session, persist=False)
        access = next(
            row
            for row in after["routes"]
            if row["canonical_url"] == "https://shop.test/orders/{id}"
        )["access"]
        assert access["needs_anonymous_comparison"] is False
        denied = next(
            member for member in access["members"] if member["url"].endswith("/202")
        )
        assert denied["anonymous"] is False
        assert denied["anonymous_observed"] is True
        assert {item["result"] for item in denied["observations"]} == {
            "reached",
            "denied",
        }


def test_two_pending_children_of_one_visited_page_count_one_remaining_root():
    with _session() as session:
        run = _run(session)
        page = CrawledPage(
            test_run_id=run.id, url="https://shop.test/orders/202", req_auth=True
        )
        session.add(page)
        session.flush()
        cell = PageOwaspTest(
            test_run_id=run.id, page_id=page.id, owasp_category="A01", status="covered"
        )
        session.add(cell)
        session.flush()
        target = DiscoveredTarget(
            test_run_id=run.id,
            url=page.url,
            route_pattern="https://shop.test/orders/{id}",
        )
        session.add(target)
        session.flush()
        for index in range(2):
            session.add(
                ScanObligation(
                    run_kind="web",
                    run_id=run.id,
                    owasp_category="A01",
                    vulnerability_technique="idor",
                    route_template=target.route_pattern,
                    scope_kind="object",
                    target_id=target.id,
                    selection_key=f"check-{index}",
                    parent_page_cell_id=cell.id,
                    status="queued",
                )
            )
        session.flush()
        summary = build_recon_summary(run.id, session=session, persist=False)
        category = next(
            row
            for row in summary["coverage"]["by_category"]
            if row["category"] == "A01"
        )
        assert summary["coverage"]["total"] == 1
        assert len(summary["coverage"]["unresolved_units"]) == 1
        assert category["total"] == 1
        assert category["remaining"] == 1
        assert summary["routes"][0]["coverage"]["remaining_categories"] == ["A01"]
