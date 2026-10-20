from __future__ import annotations

import pytest
from sqlmodel import select

from aespa.models import (
    CrawledPage,
    Credential,
    DiscoveredTarget,
    PageOwaspTest,
    Site,
    TargetAccessObservation,
    TestRun,
    TrafficEntry,
)
from aespa.services.specialist_handoffs import create_or_get_handoff
from aespa.services.target_catalog import (
    DiscoverySource,
    list_targets,
    record_discoveries,
    record_traffic_response,
)
from aespa.services.web_workprogram import (
    record_object_check_result,
    record_probe_execution,
    select_object_access_check,
    web_completion,
)

BASE = "https://shop.test"


def _run(session, *, name: str = "first") -> tuple[TestRun, Credential, Credential]:
    site = Site(name=name, base_url=BASE)
    session.add(site)
    session.flush()
    run = TestRun(site_id=site.id, name=name, page_selection="group_similar")
    owner = Credential(
        site_id=site.id, username="same@example.test", password="one", label="Owner"
    )
    other = Credential(
        site_id=site.id, username="same@example.test", password="two", label="Other"
    )
    session.add_all([run, owner, other])
    session.commit()
    for row in (run, owner, other):
        session.refresh(row)
    return run, owner, other


def _target(session, run: TestRun, url: str) -> DiscoveredTarget:
    record_discoveries(
        run.id,
        [url],
        source=DiscoverySource(None, None, "anonymous", "dom_link"),
        session=session,
    )
    session.commit()
    return session.exec(
        select(DiscoveredTarget).where(
            DiscoveredTarget.test_run_id == run.id, DiscoveredTarget.url == url
        )
    ).one()


def _traffic(
    session,
    run: TestRun,
    url: str,
    *,
    status: int = 200,
    actor: Credential | None = None,
    method: str = "GET",
    body: str = "order",
) -> TrafficEntry:
    row = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method=method,
        url=url,
        status=status,
        response_body=body,
        username=actor.username if actor else None,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _observation(
    session,
    run: TestRun,
    url: str,
    *,
    actor: Credential | None,
    status: int = 200,
    method: str = "GET",
    body: str = "order",
) -> TargetAccessObservation:
    traffic = _traffic(
        session, run, url, status=status, actor=actor, method=method, body=body
    )
    record_traffic_response(
        run.id,
        traffic.id,
        actor=f"credential:{actor.id}" if actor else "anonymous",
        verified_credential_id=actor.id if actor else None,
    )
    session.expire_all()
    return session.exec(
        select(TargetAccessObservation).where(
            TargetAccessObservation.test_run_id == run.id,
            TargetAccessObservation.source_kind == "traffic",
            TargetAccessObservation.source_id == traffic.id,
        )
    ).one()


def _claim(run: TestRun, url: str, **overrides):
    kwargs = {
        "run_id": run.id,
        "run_kind": "web",
        "attack_class": "idor",
        "target_url": url,
        "page_id": None,
        "parameter": "id",
        "session_label": None,
        "priority": 8,
        "rationale": "Cross-account access to this order",
        "dispatch_source": "test_lead",
        "agent_id": "specialist-1",
        "actor_key": "anonymous",
    }
    kwargs.update(overrides)
    return create_or_get_handoff(**kwargs)


def test_grouped_pages_count_separately_for_standard_completion(db_session) -> None:
    run, _, _ = _run(db_session)
    pages = [
        CrawledPage(test_run_id=run.id, url=f"{BASE}/orders/{number}", status="crawled")
        for number in (101, 202)
    ]
    db_session.add_all(pages)
    db_session.flush()
    db_session.add_all(
        [
            PageOwaspTest(
                test_run_id=run.id,
                page_id=pages[0].id,
                owasp_category="A01",
                status="covered",
            ),
            PageOwaspTest(
                test_run_id=run.id,
                page_id=pages[1].id,
                owasp_category="A01",
                status="not_started",
            ),
        ]
    )
    db_session.commit()

    progress = web_completion(run.id, target_percent=60)
    assert (
        progress["exercised_units"],
        progress["applicable_units"],
        progress["percent"],
    ) == (1, 2, 50.0)
    assert progress["target_met"] is False


def test_selected_uncrawled_object_is_its_own_unit_without_a_page(db_session) -> None:
    run, owner, _ = _run(db_session)
    source = CrawledPage(test_run_id=run.id, url=f"{BASE}/orders/101", status="crawled")
    db_session.add(source)
    db_session.flush()
    db_session.add(
        PageOwaspTest(
            test_run_id=run.id,
            page_id=source.id,
            owasp_category="A01",
            status="covered",
        )
    )
    db_session.commit()
    selected_url = f"{BASE}/orders/202"
    target = _target(db_session, run, selected_url)
    baseline = _observation(db_session, run, selected_url, actor=owner)

    check = select_object_access_check(
        run.id,
        target.id,
        baseline_observation_id=baseline.id,
        comparison_actor_key="anonymous",
    )

    assert check.parent_page_cell_id is None
    assert db_session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run.id)
    ).all() == [source]
    progress = web_completion(run.id)
    assert (
        progress["exercised_units"],
        progress["applicable_units"],
        progress["percent"],
    ) == (1, 2, 50.0)
    item = next(
        item for item in list_targets(run.id)["items"] if item["id"] == target.id
    )
    assert item["crawled"] is False
    assert item["selected_checks"][0]["status"] == "queued"


def test_selected_child_stays_pending_when_its_page_was_previously_covered(
    db_session,
) -> None:
    run, owner, _ = _run(db_session)
    url = f"{BASE}/orders/101"
    page = CrawledPage(test_run_id=run.id, url=url, status="crawled")
    db_session.add(page)
    db_session.flush()
    cell = PageOwaspTest(
        test_run_id=run.id, page_id=page.id, owasp_category="A01", status="covered"
    )
    db_session.add(cell)
    db_session.commit()
    target = _target(db_session, run, url)
    baseline = _observation(db_session, run, url, actor=owner)

    check = select_object_access_check(
        run.id,
        target.id,
        baseline_observation_id=baseline.id,
        comparison_actor_key="anonymous",
    )

    assert check.parent_page_cell_id == cell.id
    progress = web_completion(run.id)
    assert (
        progress["exercised_units"],
        progress["applicable_units"],
        progress["percent"],
    ) == (0, 1, 0.0)
    assert progress["resolved_units"] == 0


@pytest.mark.parametrize(
    "baseline_status,baseline_body", [(403, "forbidden"), (200, 'type="password"')]
)
def test_selection_requires_a_reached_direct_baseline(
    db_session, baseline_status, baseline_body
) -> None:
    run, owner, _ = _run(db_session)
    url = f"{BASE}/orders/101"
    target = _target(db_session, run, url)
    baseline = _observation(
        db_session, run, url, actor=owner, status=baseline_status, body=baseline_body
    )
    assert baseline.result != "reached"

    with pytest.raises(ValueError, match="baseline"):
        select_object_access_check(
            run.id,
            target.id,
            baseline_observation_id=baseline.id,
            comparison_actor_key="anonymous",
        )


def test_duplicate_usernames_do_not_merge_credential_actors(db_session) -> None:
    run, owner, other = _run(db_session)
    url = f"{BASE}/orders/101"
    _target(db_session, run, url)
    traffic = _traffic(db_session, run, url, actor=owner)
    with pytest.raises(ValueError, match="credential selected"):
        record_traffic_response(
            run.id,
            traffic.id,
            actor=f"credential:{other.id}",
            verified_credential_id=owner.id,
        )
    record_traffic_response(
        run.id,
        traffic.id,
        actor=f"credential:{owner.id}",
        verified_credential_id=owner.id,
    )
    second = _observation(db_session, run, url, actor=other)
    assert second.actor_key == f"credential:{other.id}"
    actors = {item["actor_key"] for item in list_targets(run.id)["items"][0]["access"]}
    assert actors == {f"credential:{owner.id}", f"credential:{other.id}"}


def test_result_and_block_need_evidence_for_exact_run_target_and_actor(
    db_session,
) -> None:
    run, owner, other = _run(db_session)
    other_run, other_owner, _ = _run(db_session, name="second")
    url = f"{BASE}/orders/101"
    another_url = f"{BASE}/orders/202"
    target = _target(db_session, run, url)
    _target(db_session, run, another_url)
    _target(db_session, other_run, url)
    baseline = _observation(db_session, run, url, actor=owner)
    check = select_object_access_check(
        run.id,
        target.id,
        baseline_observation_id=baseline.id,
        comparison_actor_key="anonymous",
    )
    wrong_run = _observation(db_session, other_run, url, actor=None, status=403)
    wrong_target = _observation(db_session, run, another_url, actor=None, status=403)
    wrong_actor = _observation(db_session, run, url, actor=other, status=403)
    valid_block = _observation(db_session, run, url, actor=None, status=403)
    assert other_owner.id != owner.id

    for evidence in (wrong_run, wrong_target, wrong_actor):
        with pytest.raises(ValueError, match="evidence"):
            record_object_check_result(
                run.id,
                check.id,
                blocked_reason="Comparison could not reach the object",
                blocked_evidence_id=evidence.id,
            )
    assert valid_block.result == "denied"
    wrong_run_traffic = _traffic(db_session, other_run, url)
    wrong_target_traffic = _traffic(db_session, run, another_url)
    valid_traffic = _traffic(db_session, run, url)
    for traffic in (wrong_run_traffic, wrong_target_traffic):
        with pytest.raises(ValueError, match="selected object|probe traffic"):
            record_probe_execution(
                run.id,
                check.id,
                traffic.id,
                method="GET",
                url=url,
                target_id=target.id,
                acting_actor_key="anonymous",
            )
    with pytest.raises(ValueError, match="selected object"):
        record_probe_execution(
            run.id,
            check.id,
            valid_traffic.id,
            method="GET",
            url=url,
            target_id=target.id,
            acting_actor_key=f"credential:{other.id}",
        )
    assert web_completion(run.id)["exercised_units"] == 0
    assert (
        record_object_check_result(
            run.id,
            check.id,
            blocked_reason="Comparison could not reach the object",
            blocked_evidence_id=valid_block.id,
        ).status
        == "blocked"
    )


def test_handoffs_keep_exact_query_method_and_actor_scope(db_session) -> None:
    run, owner, other = _run(db_session)
    first, created = _claim(
        run, f"{BASE}/orders?id=101", actor_key=f"credential:{owner.id}"
    )
    assert created is True
    repeat, created = _claim(
        run, f"{BASE}/orders?id=101", actor_key=f"credential:{owner.id}"
    )
    assert (repeat.id, created) == (first.id, False)

    variants = [
        {"target_url": f"{BASE}/orders?id=202", "actor_key": f"credential:{owner.id}"},
        {
            "target_url": f"{BASE}/orders?id=101",
            "method": "POST",
            "actor_key": f"credential:{owner.id}",
        },
        {"target_url": f"{BASE}/orders?id=101", "actor_key": f"credential:{other.id}"},
        {
            "target_url": f"{BASE}/orders?id=101",
            "actor_key": f"credential:{owner.id}",
            "comparison_actor_key": f"credential:{other.id}",
        },
    ]
    distinct = [
        _claim(run, f"{BASE}/orders?id=101", **variant)[0] for variant in variants
    ]
    assert len({first.id, *(row.id for row in distinct)}) == 5
    assert all(row.status == "queued" for row in distinct)


def test_new_access_outcome_is_deferred_while_same_evidence_deduplicates(
    db_session,
) -> None:
    run, owner, _ = _run(db_session)
    url = f"{BASE}/orders?id=101"
    _target(db_session, run, url)
    reached = _observation(db_session, run, url, actor=owner)
    claim_args = {
        "actor_key": f"credential:{owner.id}",
        "evidence_observation_ids": (reached.id,),
    }
    active, created = _claim(run, url, **claim_args)
    assert (active.status, created) == ("queued", True)
    same, created = _claim(run, url, **claim_args)
    assert (same.id, created) == (active.id, False)

    repeated_response = _observation(db_session, run, url, actor=owner)
    repeated, created = _claim(
        run,
        url,
        actor_key=f"credential:{owner.id}",
        evidence_observation_ids=(repeated_response.id,),
    )
    assert (repeated.id, created) == (active.id, False)

    denied = _observation(db_session, run, url, actor=owner, status=403)
    follow_up, created = _claim(
        run,
        url,
        actor_key=f"credential:{owner.id}",
        evidence_observation_ids=(denied.id,),
    )
    assert follow_up.id != active.id
    assert (follow_up.status, created) == ("deferred", False)
