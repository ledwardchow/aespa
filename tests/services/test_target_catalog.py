from __future__ import annotations

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from aespa.models import (
    CrawledPage,
    Credential,
    DiscoveredTarget,
    ScanObligation,
    Site,
    TargetAccessObservation,
    TestRun,
    TrafficEntry,
)
from aespa.services.route_sampling import RouteSampler
from aespa.services.scanner import _auth_matrix_targets
from aespa.services.target_catalog import (
    DiscoverySource,
    assign_route_patterns,
    list_targets,
    record_discoveries,
    record_traffic_response,
)


def _run(session) -> TestRun:
    site = Site(name="Catalog fixture", base_url="https://shop.test")
    session.add(site)
    session.flush()
    run = TestRun(site_id=site.id, name="Catalog fixture run")
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def test_all_discovered_members_survive_sampling_and_cursor_search(
    db_session, client
) -> None:
    run = _run(db_session)
    source = CrawledPage(
        test_run_id=run.id, url="https://shop.test/orders", status="crawled"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    urls = [f"https://shop.test/orders?id={i}" for i in range(1200)]
    record_discoveries(
        run.id,
        urls,
        source=DiscoverySource(source.id, None, "anonymous", "dom_link"),
        session=db_session,
    )
    db_session.commit()
    sampler = RouteSampler()
    admitted = sampler.offer([{"url": url} for url in urls[:200]], "anonymous")
    assert len(admitted) < 200
    assert (
        len(
            db_session.exec(
                select(DiscoveredTarget).where(DiscoveredTarget.test_run_id == run.id)
            ).all()
        )
        == 1200
    )
    assign_route_patterns(
        run.id,
        [{"url": urls[0], "route_pattern": "https://shop.test/orders?id={value}"}],
    )
    assert (
        list_targets(
            run.id, route_pattern_filter="https://shop.test/orders?id={value}"
        )["total"]
        == 1
    )

    response = client.get(
        f"/api/test-runs/{run.id}/discovered-targets",
        params={"search": "id=1101", "limit": 1},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["url"].endswith("id=1101")
    first = client.get(
        f"/api/test-runs/{run.id}/discovered-targets", params={"limit": 50}
    ).json()
    assert first["total"] == 1200
    second = client.get(
        f"/api/test-runs/{run.id}/discovered-targets",
        params={"limit": 50, "cursor": first["next_cursor"]},
    ).json()
    assert first["items"][-1]["id"] < second["items"][0]["id"]
    assert second["items"][0]["seen_by"][0]["label"] == "Anonymous"
    assert (
        client.get(
            f"/api/test-runs/{run.id}/discovered-targets", params={"cursor": "bad"}
        ).status_code
        == 400
    )


def test_exact_url_state_and_source_sightings_are_distinct(db_session) -> None:
    run = _run(db_session)
    urls = [
        "https://shop.test/a?id=1&id=2",
        "https://shop.test/a?id=2&id=1",
        "https://shop.test/a/?id=1&id=2",
        "https://shop.test/a?id=1&id=2#details",
    ]
    source = DiscoverySource(None, None, "unknown:archive", "archive")
    record_discoveries(run.id, urls, source=source, session=db_session)
    record_discoveries(
        run.id, [urls[0]], source=source, state_key="modal", session=db_session
    )
    db_session.commit()
    assert list_targets(run.id, limit=10, session=db_session)["total"] == 5
    record_discoveries(run.id, urls, source=source, session=db_session)
    db_session.commit()
    assert list_targets(run.id, limit=10, session=db_session)["total"] == 5


def test_account_search_filters_before_cursor_and_total(db_session) -> None:
    run = _run(db_session)
    credential = Credential(
        site_id=run.site_id, username="bob@example.test", password="x", label="Bob"
    )
    db_session.add(credential)
    db_session.commit()
    record_discoveries(
        run.id,
        ["https://shop.test/orders/1", "https://shop.test/orders/2"],
        source=DiscoverySource(None, None, f"credential:{credential.id}", "dom_link"),
        session=db_session,
    )
    record_discoveries(
        run.id,
        ["https://shop.test/orders/3"],
        source=DiscoverySource(None, None, "anonymous", "dom_link"),
        session=db_session,
    )
    db_session.commit()
    first = list_targets(run.id, search="Bob", limit=1)
    second = list_targets(run.id, search="Bob", limit=1, cursor=first["next_cursor"])
    assert first["total"] == second["total"] == 2
    assert [first["items"][0]["url"], second["items"][0]["url"]] == [
        "https://shop.test/orders/1",
        "https://shop.test/orders/2",
    ]


def test_auth_matrix_includes_unsampled_links_without_invented_access(
    db_session,
) -> None:
    run = _run(db_session)
    credential = Credential(site_id=run.site_id, username="owner", password="x")
    db_session.add(credential)
    db_session.commit()
    url = "https://shop.test/orders/297"
    record_discoveries(
        run.id,
        [url],
        source=DiscoverySource(None, None, f"credential:{credential.id}", "dom_link"),
        session=db_session,
    )
    db_session.commit()
    item = next(
        item
        for item in _auth_matrix_targets(run.id, "https://shop.test")
        if item["url"] == url
    )
    assert item["source"] == "discovered_target"
    assert item["accessible_by"] == []
    traffic = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="GET",
        url=url,
        username="owner",
        status=200,
        response_body="order",
    )
    db_session.add(traffic)
    db_session.commit()
    record_traffic_response(
        run.id,
        traffic.id,
        actor=f"credential:{credential.id}",
        verified_credential_id=credential.id,
    )
    item = next(
        item
        for item in _auth_matrix_targets(run.id, "https://shop.test")
        if item["url"] == url
    )
    assert item["accessible_by"] == [credential.id]


@pytest.mark.parametrize("scope_kind", [False, True])
def test_unknown_access_and_scope_states_cannot_be_saved(db_session, scope_kind):
    run = _run(db_session)
    if scope_kind:
        statement = insert(ScanObligation).values(
            run_kind="web",
            run_id=run.id,
            owasp_category="A01",
            vulnerability_technique="idor",
            route_template="https://shop.test/orders/{id}",
            scope_kind="unsupported",
        )
        constraint = "ck_scan_obligation_scope_kind"
    else:
        target = DiscoveredTarget(
            test_run_id=run.id,
            url="https://shop.test/orders/1",
            state_identity="[null]",
            route_pattern="/orders/{id}",
        )
        db_session.add(target)
        db_session.commit()
        statement = insert(TargetAccessObservation).values(
            test_run_id=run.id,
            target_id=target.id,
            source_kind="traffic",
            source_id=1,
            result="unsupported",
        )
        constraint = "ck_target_access_result"
    with pytest.raises(IntegrityError, match=constraint):
        db_session.execute(statement)
    db_session.rollback()


def test_direct_observation_remains_readable_after_its_session_closes(db_session):
    run = _run(db_session)
    traffic = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="GET",
        url="https://shop.test/orders/1",
        request_headers="{}",
        status=403,
        response_body="Access denied",
    )
    db_session.add(traffic)
    db_session.commit()
    observation = record_traffic_response(run.id, traffic.id, actor="anonymous")
    assert observation.id is not None
    assert observation.target_id is not None
    assert observation.method == "GET"
    assert observation.result == "denied"
    assert observation.actor_key == "anonymous"
