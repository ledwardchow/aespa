"""Bounded frontend-rooted route tracing and crawl-path resolution."""

from __future__ import annotations

import json

import pytest
from sqlmodel import Session, select

from aespa.models import (
    ComponentConnection,
    ComponentFact,
    LeadTargetMapping,
    ScanLead,
)
from aespa.services.correlation import propose_crawl_discovered_paths
from aespa.services.frontend_path_resolver import (
    resolve_approved_path,
    revise_path_with_llm,
)
from aespa.services.route_tracing import attack_path_for_trace, trace_lead_paths


def _seed_trace_graph(engine):
    with Session(engine) as session:
        lead = ScanLead(
            producer_run_type="sast",
            producer_run_id=7002,
            title="Unsafe order price",
            description="The server trusts a client-controlled price.",
            category="A04",
            severity="high",
            confidence=0.9,
            location="api/orders.py:20",
            fingerprint="lead-fp",
            reportable=True,
        )
        route = ComponentFact(
            sast_run_id=7001,
            component_id=1,
            fact_type="ui_route",
            path="/checkout",
            detail_json=json.dumps({"trigger": "page_load"}),
            evidence_location="ui/checkout.tsx:1",
            fingerprint="ui-route",
        )
        call = ComponentFact(
            sast_run_id=7001,
            component_id=1,
            fact_type="http_call",
            method="POST",
            path="/api/orders",
            detail_json=json.dumps(
                {"frontend": True, "body_fields": ["price"], "trigger": "page_load"}
            ),
            evidence_location="ui/checkout.tsx:20",
            fingerprint="ui-call",
        )
        backend_route = ComponentFact(
            sast_run_id=7002,
            component_id=2,
            fact_type="route",
            method="POST",
            path="/api/orders",
            evidence_location="api/orders.py:10",
            fingerprint="api-route",
        )
        handler = ComponentFact(
            sast_run_id=7002,
            component_id=2,
            fact_type="handler",
            name="create_order",
            evidence_location="api/orders.py:20",
            fingerprint="api-handler",
        )
        anchor = ComponentFact(
            sast_run_id=7002,
            component_id=2,
            fact_type="lead_anchor",
            detail_json=json.dumps({"lead_id": 1}),
            evidence_location="api/orders.py:20",
            fingerprint="lead-anchor",
        )
        session.add_all([lead, route, call, backend_route, handler, anchor])
        session.flush()
        anchor.detail_json = json.dumps({"lead_id": lead.id})
        edges = [
            ("triggers", route, call, 0.8),
            ("calls", call, backend_route, 0.7),
            ("dispatches", backend_route, handler, 0.9),
            ("reaches", handler, anchor, 0.85),
        ]
        for kind, source, target, confidence in edges:
            session.add(
                ComponentConnection(
                    campaign_id=1,
                    source_component_id=source.component_id,
                    source_fact_id=source.id,
                    target_component_id=target.component_id,
                    target_fact_id=target.id,
                    source_sast_run_id=source.sast_run_id,
                    target_sast_run_id=target.sast_run_id,
                    edge_kind=kind,
                    path_scope=(
                        "internal"
                        if source.component_id == target.component_id
                        else "cross_component"
                    ),
                    confidence=confidence,
                    evidence_json="{}",
                )
            )
        session.commit()
        return lead.id


def test_trace_lead_paths_resolves_multi_hop_frontend_entry(isolated_db_engine):
    lead_id = _seed_trace_graph(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        lead = session.get(ScanLead, lead_id)
        paths = trace_lead_paths(
            session,
            1,
            lead,
            max_edges=4,
            max_components=3,
            max_paths=10,
            min_confidence=0.5,
        )

    assert len(paths) == 1
    assert paths[0].complete is True
    assert paths[0].confidence == 0.7
    attack_path = attack_path_for_trace(paths[0], lead)
    assert attack_path["perspective"] == "frontend"
    assert attack_path["approved_pre_crawl_path"]["entry"] == "/checkout"
    assert attack_path["request_transition"]["path"] == "/api/orders"
    assert attack_path["mutation_points"] == ["price"]


def test_trace_lead_paths_emits_incomplete_frontend_call(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        lead = ScanLead(
            producer_run_type="sast",
            producer_run_id=7101,
            title="Unsafe request",
            confidence=0.8,
            location="ui/client.ts:3",
            fingerprint="incomplete-lead",
        )
        call = ComponentFact(
            sast_run_id=7101,
            component_id=1,
            fact_type="http_call",
            method="GET",
            path="/api/profile",
            detail_json='{"frontend":true}',
            evidence_location="ui/client.ts:3",
            fingerprint="incomplete-call",
        )
        anchor = ComponentFact(
            sast_run_id=7101,
            component_id=1,
            fact_type="lead_anchor",
            detail_json="{}",
            evidence_location="ui/client.ts:3",
            fingerprint="incomplete-anchor",
        )
        session.add_all([lead, call, anchor])
        session.flush()
        anchor.detail_json = json.dumps({"lead_id": lead.id})
        session.add(
            ComponentConnection(
                campaign_id=1,
                source_component_id=call.component_id,
                source_fact_id=call.id,
                target_component_id=anchor.component_id,
                target_fact_id=anchor.id,
                source_sast_run_id=call.sast_run_id,
                target_sast_run_id=anchor.sast_run_id,
                edge_kind="reaches",
                path_scope="internal",
                confidence=0.7,
            )
        )
        session.commit()
        paths = trace_lead_paths(session, 1, lead)

    assert len(paths) == 1
    assert paths[0].complete is False
    assert "UI root not proven" in paths[0].proof_gaps


def test_resolver_preserves_approved_path_and_uses_only_live_evidence():
    approved = {
        "schema_version": 2,
        "perspective": "frontend",
        "entry": "/checkout",
        "frontend_entrypoint": {
            "route": "/checkout",
            "action": "Submit order",
            "trigger": "form_submit",
        },
        "request_transition": {"method": "POST", "path": "/api/orders"},
        "dynamic_test": "Submit the order form and verify the price issue.",
    }
    final = resolve_approved_path(
        approved,
        {
            "crawl_status": "completed",
            "pages": [
                {"id": 4, "url": "https://app.test/checkout", "route": "/checkout"}
            ],
            "actions": [
                {
                    "id": 8,
                    "page_id": 4,
                    "action_kind": "form_submit",
                    "label": "Submit order",
                }
            ],
            "requests": [
                {
                    "id": 9,
                    "page_id": 4,
                    "method": "POST",
                    "url": "https://app.test/api/orders",
                    "fields": ["price"],
                }
            ],
        },
    )

    assert final["approved_pre_crawl_path"] == approved
    assert final["live_frontend_context"]["resolution_status"] == "matched"
    assert final["live_frontend_context"]["evidence_ids"] == [
        "page:4",
        "traffic:9",
        "action:8",
    ]
    assert final["mutation_points"] == ["price"]


def test_resolver_does_not_attach_crawl_evidence_to_plain_sast_path():
    approved = {
        "dynamic_test": "Use the leaked secret to forge a token.",
        "nodes": ["secret is used by the token provider"],
    }
    live_context = {
        "crawl_status": "completed",
        "pages": [{"id": 1, "url": "https://app.test/", "route": "/"}],
        "actions": [{"id": 2, "page_id": 1, "action_kind": "navigate"}],
        "requests": [
            {"id": 3, "page_id": 1, "method": "GET", "url": "https://app.test/"}
        ],
    }

    assert resolve_approved_path(approved, live_context) == approved


def test_resolver_uses_cross_component_frontend_request_metadata():
    approved = {
        "frontend_entrypoint": {
            "method": "POST",
            "path": "/api/orders/{order_id}",
        },
        "backend_route": {"method": "POST", "path": "/api/orders/{id}"},
    }
    final = resolve_approved_path(
        approved,
        {
            "crawl_status": "completed",
            "pages": [
                {"id": 4, "url": "https://app.test/checkout", "route": "/checkout"}
            ],
            "actions": [],
            "requests": [
                {
                    "id": 9,
                    "page_id": 4,
                    "method": "POST",
                    "url": "https://app.test/api/orders/42",
                },
                {
                    "id": 10,
                    "page_id": 4,
                    "method": "GET",
                    "url": "https://app.test/",
                },
            ],
        },
    )

    assert final["live_frontend_context"]["resolution_status"] == "matched"
    assert final["live_frontend_context"]["route"] == "/checkout"
    assert final["live_frontend_context"]["request"] == {
        "method": "POST",
        "path": "/api/orders/42",
        "evidence_id": "traffic:9",
    }
    assert final["live_frontend_context"]["evidence_ids"] == [
        "page:4",
        "traffic:9",
    ]


@pytest.mark.anyio
async def test_llm_rewrite_skips_plain_sast_path(monkeypatch):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("LLM must not rewrite a non-frontend SAST path")

    monkeypatch.setattr(
        "aespa.services.frontend_path_resolver.llm_svc.plain_completion",
        fail_if_called,
    )
    approved = {"dynamic_test": "Use the SAST evidence."}
    revised, warning = await revise_path_with_llm(approved, approved, object())

    assert revised == approved
    assert warning is None


def test_crawl_discovered_path_is_saved_as_unapproved_proposal(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        lead = ScanLead(
            producer_run_type="campaign",
            producer_run_id=1,
            origin_lead_id=10,
            trace_path_key="approved-path",
            title="Unsafe price",
            description="Trusts price",
            category="A04",
            severity="high",
            confidence=0.8,
            fingerprint="approved-lead",
            attack_path_json=json.dumps(
                {
                    "schema_version": 2,
                    "perspective": "frontend",
                    "entry": "/checkout",
                    "live_frontend_context": {
                        "request": {"method": "POST", "path": "/api/orders"}
                    },
                }
            ),
        )
        session.add(lead)
        session.flush()
        session.add(
            LeadTargetMapping(
                campaign_id=1,
                lead_id=lead.id,
                target_id=9,
                target_type="site",
                status="approved",
                approved_attack_path_json=lead.attack_path_json,
                path_json=lead.attack_path_json,
            )
        )
        session.commit()

    created = propose_crawl_discovered_paths(
        1,
        9,
        context={
            "crawl_status": "completed",
            "pages": [{"id": 2, "url": "https://app.test/cart", "route": "/cart"}],
            "requests": [
                {
                    "id": 3,
                    "page_id": 2,
                    "method": "POST",
                    "url": "https://app.test/api/orders",
                    "fields": ["coupon"],
                }
            ],
            "actions": [],
        },
    )

    assert created == 1
    with Session(isolated_db_engine) as session:
        proposal = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == 1)
            .where(LeadTargetMapping.target_id == 9)
            .where(LeadTargetMapping.status == "proposed")
        ).one()
        assert proposal.copied_lead_id is None


def test_resolver_does_not_call_llm_when_crawl_is_unavailable(monkeypatch):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("LLM must not be called for unavailable crawl evidence")

    monkeypatch.setattr(
        "aespa.services.frontend_path_resolver.llm_svc.plain_completion",
        fail_if_called,
    )
    approved = {"schema_version": 2, "perspective": "frontend", "entry": "/checkout"}
    final = resolve_approved_path(
        approved,
        {"crawl_status": "failed", "pages": [], "actions": [], "requests": []},
    )

    assert final["live_frontend_context"]["resolution_status"] == "unavailable"


@pytest.mark.anyio
async def test_llm_rewrite_rejects_unknown_evidence(monkeypatch):
    async def fake_completion(*_args, **_kwargs):
        return '{"dynamic_test":"Use /invented","evidence_ids":["page:999"]}'

    monkeypatch.setattr(
        "aespa.services.frontend_path_resolver.llm_svc.plain_completion",
        fake_completion,
    )
    approved = {"live_frontend_context": {"evidence_ids": ["page:1"]}}
    final = {
        **approved,
        "live_frontend_context": {
            "evidence_ids": ["page:1"],
            "resolution_status": "matched",
        },
    }
    revised, warning = await revise_path_with_llm(approved, final, object())

    assert revised == final
    assert warning is not None
