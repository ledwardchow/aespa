from __future__ import annotations

import pytest
from sqlmodel import select

from aespa.models import (
    Credential,
    DeepScanCheck,
    DeepScanTask,
    DiscoveredTarget,
    Site,
    TargetAccessObservation,
    TestRun,
    TrafficEntry,
)
from aespa.services.deep_scan import _refresh_campaign_state, seed_deep_tasks
from aespa.services.target_catalog import (
    DiscoverySource,
    record_discoveries,
    record_traffic_response,
)
from aespa.services.web_workprogram import (
    _request_body_identity,
    record_probe_execution,
    select_object_access_check,
)


def test_duplicate_json_keys_keep_raw_request_identity() -> None:
    assert _request_body_identity('{"id":101,"id":202}') != _request_body_identity('{"id":202}')


def test_post_object_check_requires_same_body_as_direct_baseline(db_session) -> None:
    site = Site(name="body", base_url="https://shop.test")
    db_session.add(site)
    db_session.flush()
    run = TestRun(site_id=site.id, name="body")
    owner = Credential(site_id=site.id, username="owner", password="x")
    db_session.add_all([run, owner])
    db_session.commit()
    url = "https://shop.test/api/orders"
    record_discoveries(run.id, [url], source=DiscoverySource(None, None, "anonymous", "dom_link"), session=db_session)
    db_session.commit()
    target = db_session.exec(select(DiscoveredTarget).where(DiscoveredTarget.test_run_id == run.id)).one()
    baseline = TrafficEntry(test_run_id=run.id, source="httpx", method="POST", url=url,
                            request_body='{"order_id":101}', status=200, response_body="order 101", username="owner")
    db_session.add(baseline)
    db_session.commit()
    record_traffic_response(run.id, baseline.id, actor=f"credential:{owner.id}", verified_credential_id=owner.id)
    owner_result_id = db_session.exec(select(TargetAccessObservation.id).where(
        TargetAccessObservation.test_run_id == run.id,
        TargetAccessObservation.source_id == baseline.id,
    )).one()
    check = select_object_access_check(run.id, target.id, baseline_observation_id=owner_result_id,
                                       comparison_actor_key="anonymous", method="POST")
    other = TrafficEntry(test_run_id=run.id, source="httpx", method="POST", url=url,
                         request_body='{"order_id":202}', status=200, response_body="order 202")
    db_session.add(other)
    db_session.commit()
    record_traffic_response(run.id, other.id, actor="anonymous")
    with pytest.raises(ValueError, match="body"):
        record_probe_execution(run.id, check.id, traffic_id=other.id, target_id=target.id,
                               method="POST", url=url, acting_actor_key="anonymous")
    selected = TrafficEntry(test_run_id=run.id, source="httpx", method="POST", url=url,
                            request_body='{"order_id":101}', status=200, response_body="order 101")
    db_session.add(selected)
    db_session.commit()
    record_traffic_response(run.id, selected.id, actor="anonymous")
    execution_id = record_probe_execution(run.id, check.id, traffic_id=selected.id,
                                          target_id=target.id, method="POST", url=url,
                                          acting_actor_key="anonymous")
    assert execution_id > 0


def test_deep_selected_children_keep_exact_targets_and_pending_state(db_session) -> None:
    site = Site(name="deep objects", base_url="https://shop.test")
    db_session.add(site)
    db_session.flush()
    run = TestRun(site_id=site.id, name="deep objects", coverage_mode="deep")
    owner = Credential(site_id=site.id, username="owner", password="x")
    db_session.add_all([run, owner])
    db_session.commit()
    checks = []
    for number in (101, 202):
        url = f"https://shop.test/orders/{number}"
        record_discoveries(run.id, [url], source=DiscoverySource(None, None, "anonymous", "dom_link"), session=db_session)
        db_session.commit()
        target = db_session.exec(select(DiscoveredTarget).where(DiscoveredTarget.url == url)).one()
        baseline = TrafficEntry(test_run_id=run.id, source="httpx", method="GET", url=url,
                                status=200, response_body=f"order {number}", username="owner")
        db_session.add(baseline)
        db_session.commit()
        record_traffic_response(run.id, baseline.id, actor=f"credential:{owner.id}", verified_credential_id=owner.id)
        observation_id = db_session.exec(select(TargetAccessObservation.id).where(
            TargetAccessObservation.test_run_id == run.id,
            TargetAccessObservation.source_id == baseline.id,
        )).one()
        checks.append(select_object_access_check(run.id, target.id,
                      baseline_observation_id=observation_id, comparison_actor_key="anonymous"))
    seed_deep_tasks(run.id)
    tasks = db_session.exec(select(DeepScanTask).where(DeepScanTask.obligation_id.in_([check.id for check in checks]))).all()
    assert {task.target_url for task in tasks} == {f"https://shop.test/orders/{number}" for number in (101, 202)}
    assert len(tasks) == 2
    _refresh_campaign_state(db_session, tasks[0])
    db_session.commit()
    linked = db_session.exec(select(DeepScanCheck).where(DeepScanCheck.task_id == tasks[0].id)).one()
    assert linked.status == "queued"
