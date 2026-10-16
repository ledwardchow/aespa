from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import select

from aespa.models import (
    Credential,
    DeepScanAttempt,
    DeepScanCheck,
    DeepScanConfig,
    DeepScanTask,
    DeepScanVariant,
    ProbeExecution,
    ScanObligation,
    Site,
    TestRun,
    TrafficEntry,
)
from aespa.services import deep_scan, scanner, scanner_sessions, specialist_handoffs
from aespa.services.target_catalog import (
    DiscoverySource,
    record_discoveries,
    record_traffic_response,
)
from aespa.services.web_workprogram import select_object_access_check


def _selected_check(db_session, *, url="https://target.local/orders/101"):
    site = Site(name="Deep exact", base_url="https://target.local")
    db_session.add(site)
    db_session.flush()
    bob = Credential(site_id=site.id, username="bob", password="test")
    alice = Credential(site_id=site.id, username="alice", password="test")
    db_session.add_all([bob, alice])
    run = TestRun(site_id=site.id, name="Exact objects", coverage_mode="deep")
    db_session.add(run)
    db_session.commit()
    record_discoveries(
        run.id,
        [url],
        source=DiscoverySource(None, None, f"credential:{bob.id}", "test", "baseline"),
    )
    baseline = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="POST",
        url=url,
        request_body='{"item":101}',
        status=200,
        username="bob",
    )
    db_session.add(baseline)
    db_session.commit()
    observation = record_traffic_response(
        run.id,
        baseline.id,
        actor=f"credential:{bob.id}",
        verified_credential_id=bob.id,
        session=db_session,
    )
    db_session.commit()
    check = select_object_access_check(
        run.id,
        observation.target_id,
        baseline_observation_id=observation.id,
        comparison_actor_key=f"credential:{alice.id}",
        method="POST",
    )
    return run, bob, alice, check


def _variant(db_session, run, check):
    task = DeepScanTask(
        run_id=run.id,
        fingerprint="exact-task",
        source="coverage",
        task_kind="operation",
        route_template="/orders/{id}",
        obligation_id=check.id,
        attack_class="business_logic",
        owasp_category="A01",
        target_url="https://target.local/orders/101",
        http_method="POST",
        title="Object comparison",
    )
    db_session.add(task)
    db_session.flush()
    child = DeepScanCheck(
        run_id=run.id,
        task_id=task.id,
        fingerprint="exact-child",
        obligation_id=check.id,
        attack_class="idor",
        owasp_category="A01",
    )
    db_session.add(child)
    db_session.flush()
    variant = DeepScanVariant(
        run_id=run.id,
        task_id=task.id,
        fingerprint="exact-variant",
        purpose="Compare accounts",
        kind="planned",
        status="running",
        worker_id="deep-test",
        check_ids_json=json.dumps([child.id]),
    )
    db_session.add(variant)
    db_session.flush()
    attempt = DeepScanAttempt(
        run_id=run.id,
        task_id=task.id,
        variant_id=variant.id,
        worker_id="deep-test",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(attempt)
    db_session.commit()
    return task, child, variant, attempt


@pytest.mark.parametrize(
    ("url", "body", "actor", "expected"),
    [
        ("https://target.local/orders/101", '{"item":101}', "alice", True),
        ("https://target.local/orders/202", '{"item":101}', "alice", False),
        ("https://target.local/orders/101", '{"item":202}', "alice", False),
        ("https://target.local/orders/101", '{"item":101}', "bob", False),
    ],
)
def test_variant_closes_only_exact_executed_object(
    db_session, url, body, actor, expected
):
    run, bob, alice, check = _selected_check(db_session)
    _, child, variant, attempt = _variant(db_session, run, check)
    credential = alice if actor == "alice" else bob
    traffic = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="POST",
        url=url,
        request_body=body,
        status=200,
        username=actor,
        agent_id="deep-test",
        owasp_category="A01",
    )
    db_session.add(traffic)
    db_session.commit()
    record_traffic_response(
        run.id,
        traffic.id,
        actor=f"credential:{credential.id}",
        verified_credential_id=credential.id,
        session=db_session,
    )
    db_session.commit()

    deep_scan._finish_variant(
        variant.id, attempt.id, status="complete", outcome="Checked"
    )

    db_session.expire_all()
    executions = db_session.exec(
        select(ProbeExecution).where(ProbeExecution.obligation_id == check.id)
    ).all()
    assert len(executions) == int(expected)
    assert db_session.get(DeepScanCheck, child.id).status == (
        "inconclusive" if expected else "queued"
    )
    if expected:
        assert executions[0].target_id == check.target_id
        assert executions[0].acting_actor_key == f"credential:{alice.id}"
        assert executions[0].request_identity


def test_bundled_sibling_stays_pending_without_its_own_request(db_session):
    run, bob, alice, first = _selected_check(db_session)
    second_url = "https://target.local/orders/202"
    record_discoveries(
        run.id,
        [second_url],
        source=DiscoverySource(None, None, f"credential:{bob.id}", "test", "second"),
    )
    baseline = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="POST",
        url=second_url,
        request_body='{"item":101}',
        status=200,
        username="bob",
    )
    db_session.add(baseline)
    db_session.commit()
    observation = record_traffic_response(
        run.id,
        baseline.id,
        actor=f"credential:{bob.id}",
        verified_credential_id=bob.id,
        session=db_session,
    )
    db_session.commit()
    second = select_object_access_check(
        run.id,
        observation.target_id,
        baseline_observation_id=observation.id,
        comparison_actor_key=f"credential:{alice.id}",
        method="POST",
    )
    task, first_child, variant, attempt = _variant(db_session, run, first)
    second_child = DeepScanCheck(
        run_id=run.id,
        task_id=task.id,
        fingerprint="second-child",
        obligation_id=second.id,
        attack_class="idor",
        owasp_category="A01",
    )
    db_session.add(second_child)
    db_session.flush()
    variant.check_ids_json = json.dumps([first_child.id, second_child.id])
    db_session.add(variant)
    traffic = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="POST",
        url="https://target.local/orders/101",
        request_body='{"item":101}',
        status=200,
        username="alice",
        agent_id="deep-test",
        owasp_category="A01",
    )
    db_session.add(traffic)
    db_session.commit()
    record_traffic_response(
        run.id,
        traffic.id,
        actor=f"credential:{alice.id}",
        verified_credential_id=alice.id,
        session=db_session,
    )
    db_session.commit()

    deep_scan._finish_variant(
        variant.id, attempt.id, status="complete", outcome="Compared first object"
    )

    db_session.expire_all()
    execution_ids = db_session.exec(select(ProbeExecution.obligation_id)).all()
    assert execution_ids == [first.id]
    assert db_session.get(DeepScanCheck, first_child.id).status == "inconclusive"
    assert db_session.get(DeepScanCheck, second_child.id).status == "queued"
    assert db_session.get(ScanObligation, second.id).status == "queued"


def test_variant_skips_earlier_wrong_actor_traffic(db_session):
    run, bob, alice, check = _selected_check(db_session)
    _, _, variant, attempt = _variant(db_session, run, check)
    for credential in (bob, alice):
        traffic = TrafficEntry(
            test_run_id=run.id,
            source="httpx",
            method="POST",
            url="https://target.local/orders/101",
            request_body='{"item":101}',
            status=200,
            username=credential.username,
            agent_id="deep-test",
            owasp_category="A01",
        )
        db_session.add(traffic)
        db_session.commit()
        record_traffic_response(
            run.id,
            traffic.id,
            actor=f"credential:{credential.id}",
            verified_credential_id=credential.id,
            session=db_session,
        )
        db_session.commit()
        if credential.id == alice.id:
            alice_traffic_id = traffic.id

    deep_scan._finish_variant(
        variant.id, attempt.id, status="complete", outcome="Compared accounts"
    )

    executions = db_session.exec(
        select(ProbeExecution).where(ProbeExecution.obligation_id == check.id)
    ).all()
    assert [execution.traffic_id for execution in executions] == [alice_traffic_id]


def test_route_check_requires_its_selected_operation(db_session):
    run, _, _, _ = _selected_check(db_session)
    route_check = ScanObligation(
        run_kind="web",
        run_id=run.id,
        owasp_category="A01",
        vulnerability_technique="auth_vs_unauth",
        route_template="/orders/{id}",
        http_method="POST",
    )
    db_session.add(route_check)
    db_session.flush()
    task = DeepScanTask(
        run_id=run.id,
        fingerprint="route-task",
        task_kind="operation",
        source="coverage",
        route_template="/orders/{id}",
        obligation_id=route_check.id,
        attack_class="business_logic",
        owasp_category="A01",
        target_url="https://target.local/orders/101",
        http_method="POST",
    )
    unrelated_url = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="POST",
        url="https://target.local/orders/202",
        status=200,
        owasp_category="A01",
    )
    unrelated_method = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="GET",
        url="https://target.local/orders/101",
        status=200,
        owasp_category="A01",
    )
    exact = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="POST",
        url="https://target.local/orders/101",
        status=200,
        owasp_category="A01",
    )
    assert (
        deep_scan._execution_scope(db_session, task, route_check, unrelated_url) is None
    )
    assert (
        deep_scan._execution_scope(db_session, task, route_check, unrelated_method)
        is None
    )
    assert deep_scan._execution_scope(db_session, task, route_check, exact) == (
        None,
        None,
        None,
    )


@pytest.mark.anyio
async def test_selected_comparison_uses_its_web_session(db_session, monkeypatch):
    run, bob, alice, check = _selected_check(db_session)
    assert check.required_identity_comparison is None
    scanner_sessions.upsert_session(
        run.id,
        label="bob_session",
        kind="cookie",
        credential_id=bob.id,
        username="bob",
        lifecycle_state="active",
    )
    scanner_sessions.upsert_session(
        run.id,
        label="alice_session",
        kind="cookie",
        credential_id=alice.id,
        username="alice",
        lifecycle_state="active",
    )
    db_session.add(
        DeepScanConfig(
            id=1,
            max_tasks=1,
            initial_variants_per_campaign=1,
            max_concurrent_workers=1,
            include_sast_leads=False,
            include_recon_checks=False,
        )
    )
    db_session.commit()

    assert deep_scan.seed_deep_tasks(run.id) == 1
    child = db_session.exec(
        select(DeepScanCheck).where(DeepScanCheck.run_id == run.id)
    ).one()
    task = db_session.get(DeepScanTask, child.task_id)
    assert child.obligation_id == check.id
    assert child.session_label == "alice_session"
    assert "baseline actor credential:" in child.hypothesis
    assert (
        f"comparison actor credential:{alice.id} using session alice_session"
        in child.hypothesis
    )
    assert "baseline request " in task.hypothesis
    assert (
        deep_scan._comparison_session_label(
            db_session, run.id, f"credential:{alice.id}"
        )
        == "alice_session"
    )

    dispatched = []

    async def fake_planner(*_args, **_kwargs):
        raise RuntimeError("use the deterministic plan")

    async def fake_worker(**kwargs):
        handoff = specialist_handoffs.get_handoff(kwargs["handoff_id"])
        dispatched.append(
            (
                kwargs["target_session_label"],
                kwargs["session_vault"],
                handoff,
            )
        )
        specialist_handoffs.update_handoff(
            handoff.id, status="completed", outcome="No finding"
        )

    monkeypatch.setattr(deep_scan, "get_llm_config_for_role", lambda *_: object())
    monkeypatch.setattr(deep_scan.llm_svc, "plain_completion", fake_planner)
    monkeypatch.setattr(scanner, "_run_specialist_agent", fake_worker)
    await deep_scan.run_deep_scan(run.id)

    assert len(dispatched) == 1
    label, vault, handoff = dispatched[0]
    assert label == "alice_session"
    assert set(vault) == {"alice_session"}
    assert handoff.session_label == "alice_session"
    assert handoff.actor_key == f"credential:{bob.id}"
    assert handoff.comparison_actor_key == f"credential:{alice.id}"
    assert handoff.body_identity == check.body_identity
