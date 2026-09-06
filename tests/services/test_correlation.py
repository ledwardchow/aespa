"""Deterministic cross-repository correlation: component connections,
lead-target mapping proposals, bounded cross-repo lead generation, and
review approve/reject idempotency.

No network access anywhere — ``correlate_campaign`` is called without an
``llm_match`` callable, exercising only the deterministic path.
"""

from __future__ import annotations

import json

import pytest
from sqlmodel import Session, select

from aespa.models import (
    ApiCollection,
    ApiEndpoint,
    Application,
    ApplicationComponent,
    ApplicationTarget,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentConnection,
    ComponentFact,
    ComponentSnapshot,
    LeadTargetMapping,
    SastRun,
    ScanLead,
    ScanLeadComponentProvenance,
    Site,
)
from aespa.services.correlation import (
    apply_review_decisions,
    copy_approved_mappings_for_target,
    correlate_campaign,
    correlate_campaign_with_llm,
)


def _seed_two_component_campaign(engine, *, public_route: bool = True) -> dict:
    """checkout-ui calls POST /orders; orders-api exposes POST /orders.

    The default fixture records an explicit public-route rule so tests that
    exercise cross-repository generation do not rely on missing evidence being
    interpreted as public. Set ``public_route=False`` for auth-negative cases.
    Both SAST runs are marked completed already.
    """
    with Session(engine) as s:
        app = Application(name="Acme")
        s.add(app)
        s.flush()

        ui = ApplicationComponent(application_id=app.id, name="checkout-ui")
        api = ApplicationComponent(application_id=app.id, name="orders-api")
        s.add(ui)
        s.add(api)
        s.flush()

        ui_snapshot = ComponentSnapshot(
            component_id=ui.id,
            filename="ui.zip",
            stored_path="/tmp/ui.zip",
            size_bytes=10,
            sha256="a" * 64,
        )
        api_snapshot = ComponentSnapshot(
            component_id=api.id,
            filename="api.zip",
            stored_path="/tmp/api.zip",
            size_bytes=10,
            sha256="b" * 64,
        )
        s.add(ui_snapshot)
        s.add(api_snapshot)
        s.flush()

        collection = ApiCollection(name="Orders API", base_url="https://api.acme.test")
        s.add(collection)
        s.flush()
        target = ApplicationTarget(
            application_id=app.id, target_type="api_collection", target_id=collection.id
        )
        s.add(target)
        s.flush()
        endpoint = ApiEndpoint(
            collection_id=collection.id, method="POST", path="/orders"
        )
        s.add(endpoint)

        campaign = AssessmentCampaign(application_id=app.id, name="release-1")
        s.add(campaign)
        s.flush()

        ui_sast_run_id = 9001
        api_sast_run_id = 9002
        ui_member = CampaignSourceMember(
            campaign_id=campaign.id,
            component_id=ui.id,
            snapshot_id=ui_snapshot.id,
            sast_run_id=ui_sast_run_id,
            status="completed",
        )
        api_member = CampaignSourceMember(
            campaign_id=campaign.id,
            component_id=api.id,
            snapshot_id=api_snapshot.id,
            sast_run_id=api_sast_run_id,
            status="completed",
        )
        s.add(ui_member)
        s.add(api_member)
        target_member = CampaignTargetMember(
            campaign_id=campaign.id, target_id=target.id, target_type="api_collection"
        )
        s.add(target_member)
        s.flush()

        call_fact = ComponentFact(
            sast_run_id=ui_sast_run_id,
            component_id=ui.id,
            fact_type="http_call",
            method="POST",
            path="/orders",
            host="api.acme.test",
            evidence_location="src/checkout.js:42",
            fingerprint="call-fp",
        )
        route_fact = ComponentFact(
            sast_run_id=api_sast_run_id,
            component_id=api.id,
            fact_type="route",
            method="POST",
            path="/orders",
            evidence_location="src/routes.py:10",
            fingerprint="route-fp",
        )
        s.add(call_fact)
        s.add(route_fact)
        if public_route:
            s.add(
                ComponentFact(
                    sast_run_id=api_sast_run_id,
                    component_id=api.id,
                    fact_type="auth_boundary",
                    method="POST",
                    path="/orders",
                    name="permitAll",
                    detail_json=json.dumps(
                        {
                            "scope": "path",
                            "public_paths": ["/orders"],
                            "public_methods": ["POST"],
                        }
                    ),
                    evidence_location="src/security.py:8",
                    fingerprint="public-orders-fp",
                )
            )
        s.flush()

        source_lead = ScanLead(
            producer_run_id=ui_sast_run_id,
            producer_run_type="sast",
            title="Missing authorization on order creation",
            category="A01",
            severity="high",
            confidence=0.9,
            location="src/checkout.js:42",
            suggested_endpoint="POST /orders",
            reportable=True,
            validation_status="confirmed",
        )
        s.add(source_lead)
        s.commit()

        return {
            "application_id": app.id,
            "campaign_id": campaign.id,
            "ui_component_id": ui.id,
            "api_component_id": api.id,
            "target_id": target.id,
            "call_fact_id": call_fact.id,
            "route_fact_id": route_fact.id,
            "source_lead_id": source_lead.id,
        }


def test_correlate_campaign_builds_deterministic_connection(isolated_db_engine):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    result = correlate_campaign(ctx["campaign_id"])
    assert result["connections"] == 2  # one internal anchor edge + one API hop

    with Session(isolated_db_engine) as s:
        connections = s.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "calls")
        ).all()
    assert len(connections) == 1
    connection = connections[0]
    assert connection.match_kind == "deterministic"
    assert connection.confidence >= 0.7
    assert connection.source_component_id == ctx["ui_component_id"]
    assert connection.target_component_id == ctx["api_component_id"]


def test_same_component_browser_request_connects_to_matching_server_ingress(
    isolated_db_engine,
):
    """A browser call served by the same component can reach its API route."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        browser_call = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="http_call",
            method="POST",
            path="/api/payment/process",
            host="checkout.acme.test",
            evidence_location="src/payment.js:10",
            detail_json=json.dumps({"request_role": "browser_request"}),
            fingerprint="payment-browser-call",
        )
        ingress = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="route",
            method="POST",
            path="/api/payment/process",
            evidence_location="src/app.py:40",
            fingerprint="payment-ingress",
        )
        unrelated = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="route",
            method="GET",
            path="/api/payment/process",
            evidence_location="src/app.py:41",
            fingerprint="payment-unrelated-method",
        )
        session.add_all([browser_call, ingress, unrelated])
        session.flush()
        browser_call_id = browser_call.id
        ingress_id = ingress.id
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "calls")
            .where(ComponentConnection.source_fact_id == browser_call_id)
        ).all()

    assert len(edges) == 1
    assert edges[0].target_fact_id == ingress_id
    assert edges[0].source_component_id == edges[0].target_component_id
    assert edges[0].confidence >= 0.8
    assert "same-component" in edges[0].rationale


def test_proxy_transit_requires_explicit_ownership_metadata(isolated_db_engine):
    """A route and egress share a proxy edge only when ownership is recorded."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        handler_location = "src/app.py:30"
        owned_route = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="route",
            method="POST",
            path="/api/quotes/motor",
            evidence_location="src/app.py:20",
            detail_json=json.dumps({"handler_locations": [handler_location]}),
            fingerprint="owned-quote-route",
        )
        owned_egress = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="http_call",
            method="POST",
            path="/api/customer/quotes/motor",
            evidence_location="src/client.py:12",
            detail_json=json.dumps(
                {
                    "request_role": "server_egress",
                    "handler_locations": [handler_location],
                }
            ),
            fingerprint="owned-quote-egress",
        )
        unowned_egress = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="http_call",
            method="POST",
            path="/api/customer/quotes/motor",
            evidence_location="src/other.py:12",
            detail_json=json.dumps({"request_role": "server_egress"}),
            fingerprint="unowned-quote-egress",
        )
        session.add_all([owned_route, owned_egress, unowned_egress])
        session.flush()
        owned_route_id = owned_route.id
        owned_egress_id = owned_egress.id
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.source_fact_id == owned_route_id)
            .where(ComponentConnection.edge_kind == "dispatches")
        ).all()

    assert [edge.target_fact_id for edge in edges] == [owned_egress_id]
    assert edges[0].confidence >= 0.75
    assert "ownership metadata" in edges[0].rationale


def test_proxy_transit_binds_each_egress_to_nearest_preceding_route(
    isolated_db_engine,
):
    """Separate handler lines map adjacent routes without cross-route fanout."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    route_specs = (
        ("motor", 262, 264),
        ("home", 270, 272),
        ("contents", 278, 280),
    )
    with Session(isolated_db_engine) as session:
        facts: list[ComponentFact] = []
        for name, route_line, owner_line in route_specs:
            facts.extend(
                [
                    ComponentFact(
                        sast_run_id=9001,
                        component_id=ctx["ui_component_id"],
                        fact_type="route",
                        method="POST",
                        path=f"/api/quotes/{name}",
                        evidence_location=f"app/main.py:{route_line}",
                        fingerprint=f"nearest-route-{name}",
                    ),
                    ComponentFact(
                        sast_run_id=9001,
                        component_id=ctx["ui_component_id"],
                        fact_type="http_call",
                        method="POST",
                        path=f"/api/customer/quotes/{name}",
                        evidence_location=f"app/client.py:{owner_line}",
                        detail_json=json.dumps(
                            {
                                "request_role": "server_egress",
                                "handler_locations": [f"app/main.py:{owner_line}"],
                            }
                        ),
                        fingerprint=f"nearest-egress-{name}",
                    ),
                ]
            )
        # Keep the route and handler locations in the same file while the
        # egress fact's primary location remains its client call site.
        session.add_all(facts)
        session.flush()
        route_ids = {
            fact.path.rsplit("/", 1)[-1]: fact.id
            for fact in facts
            if fact.fact_type == "route"
        }
        egress_ids = {
            fact.path.rsplit("/", 1)[-1]: fact.id
            for fact in facts
            if fact.fact_type == "http_call"
        }
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "dispatches")
            .where(
                ComponentConnection.source_fact_id.in_(
                    [fact_id for fact_id in route_ids.values()]
                )
            )
        ).all()

    assert {(edge.source_fact_id, edge.target_fact_id) for edge in edges} == {
        (route_ids[name], egress_ids[name]) for name, _route, _owner in route_specs
    }


def test_proxy_transit_prefers_exact_adjacent_route_owner_location(
    isolated_db_engine,
):
    """An exact decorator/handler line wins over an earlier route."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    route_specs = (
        ("motor", 262),
        ("home", 268),
        ("contents", 274),
    )
    with Session(isolated_db_engine) as session:
        facts: list[ComponentFact] = []
        for name, line in route_specs:
            owner_location = f"FACE/app.py:{line}"
            facts.extend(
                [
                    ComponentFact(
                        sast_run_id=9001,
                        component_id=ctx["ui_component_id"],
                        fact_type="route",
                        method="POST",
                        path=f"/api/quotes/{name}",
                        evidence_location=owner_location,
                        fingerprint=f"exact-route-{name}",
                    ),
                    ComponentFact(
                        sast_run_id=9001,
                        component_id=ctx["ui_component_id"],
                        fact_type="http_call",
                        method="POST",
                        path=f"/api/customer/quotes/{name}",
                        evidence_location=f"FACE/client.py:{line + 1}",
                        detail_json=json.dumps(
                            {
                                "request_role": "server_egress",
                                "handler_locations": [owner_location],
                            }
                        ),
                        fingerprint=f"exact-egress-{name}",
                    ),
                ]
            )
        session.add_all(facts)
        session.flush()
        route_ids = {
            fact.path.rsplit("/", 1)[-1]: fact.id
            for fact in facts
            if fact.fact_type == "route"
        }
        egress_ids = {
            fact.path.rsplit("/", 1)[-1]: fact.id
            for fact in facts
            if fact.fact_type == "http_call"
        }
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "dispatches")
            .where(
                ComponentConnection.source_fact_id.in_(
                    [fact_id for fact_id in route_ids.values()]
                )
            )
        ).all()

    assert {(edge.source_fact_id, edge.target_fact_id) for edge in edges} == {
        (route_ids[name], egress_ids[name]) for name, _line in route_specs
    }


def test_multistep_quote_anchor_does_not_attach_to_bind_route(
    isolated_db_engine,
):
    """A quote-then-bind lead must retain its quote input route."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    quote_names = ("motor", "home", "contents")
    with Session(isolated_db_engine) as session:
        bind_route = ComponentFact(
            sast_run_id=9002,
            component_id=ctx["api_component_id"],
            fact_type="route",
            method="POST",
            path="/api/customer/policies/{id}/bind",
            evidence_location="goose/CustomerApiController.java:114",
            fingerprint="bind-route-for-quote-leads",
        )
        session.add(bind_route)
        session.flush()
        anchors: list[ComponentFact] = []
        for index, name in enumerate(quote_names):
            lead = ScanLead(
                producer_run_id=9002,
                producer_run_type="sast",
                title=f"Legacy {name} quote bypass",
                category="A04",
                severity="high",
                confidence=0.9,
                location=f"goose/PolicyService.java:{200 + index}",
                suggested_endpoint=(
                    f"POST /api/customer/quotes/{name} then "
                    "POST /api/customer/policies/{id}/bind"
                ),
                reportable=True,
                validation_status="confirmed",
            )
            session.add(lead)
            session.flush()
            anchor = ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="lead_anchor",
                method="POST",
                # The mapper may anchor the finding at the downstream sink
                # even though its suggested endpoint starts at the quote.
                path="/api/customer/policies/{id}/bind",
                evidence_location=f"goose/PolicyService.java:{200 + index}",
                detail_json=json.dumps(
                    {
                        "lead_id": lead.id,
                        "route_locations": [
                            f"goose/CustomerApiController.java:{210 + index * 20}",
                            bind_route.evidence_location,
                        ],
                    }
                ),
                fingerprint=f"quote-anchor-{name}",
            )
            session.add(anchor)
            anchors.append(anchor)
        session.flush()
        bind_route_id = bind_route.id
        anchor_ids = [anchor.id for anchor in anchors]
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        shortcut_edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "reaches")
            .where(ComponentConnection.source_fact_id == bind_route_id)
            .where(ComponentConnection.target_fact_id.in_(anchor_ids))
        ).all()

    assert shortcut_edges == []


def test_single_endpoint_anchor_keeps_explicit_alternate_sink_route(
    isolated_db_engine,
):
    """A single-endpoint lead can name more than one explicit route."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        alternate_route = ComponentFact(
            sast_run_id=9002,
            component_id=ctx["api_component_id"],
            fact_type="route",
            method="POST",
            path="/claims/{id}/review",
            evidence_location="goose/ClaimController.java:144",
            fingerprint="alternate-review-route",
        )
        lead = ScanLead(
            producer_run_id=9002,
            producer_run_type="sast",
            title="Invalid claim transition",
            category="A04",
            severity="high",
            confidence=0.9,
            location="goose/ClaimService.java:115",
            suggested_endpoint="POST /claims/{id}/approve",
            reportable=True,
            validation_status="confirmed",
        )
        session.add_all([alternate_route, lead])
        session.flush()
        anchor = ComponentFact(
            sast_run_id=9002,
            component_id=ctx["api_component_id"],
            fact_type="lead_anchor",
            method="POST",
            path="/claims/{id}/approve",
            evidence_location="goose/ClaimService.java:115",
            detail_json=json.dumps(
                {
                    "lead_id": lead.id,
                    "route_locations": [alternate_route.evidence_location],
                }
            ),
            fingerprint="transition-anchor",
        )
        session.add(anchor)
        session.flush()
        alternate_route_id = alternate_route.id
        anchor_id = anchor.id
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "reaches")
            .where(ComponentConnection.source_fact_id == alternate_route_id)
            .where(ComponentConnection.target_fact_id == anchor_id)
        ).all()

    assert len(edges) == 1


def test_anchor_supporting_location_does_not_attach_unrelated_review_route(
    isolated_db_engine,
):
    """A supporting controller location is context, not route ownership."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        review_route = ComponentFact(
            sast_run_id=9002,
            component_id=ctx["api_component_id"],
            fact_type="route",
            method="POST",
            path="/claims/{id}/review",
            evidence_location="goose/ClaimController.java:144",
            fingerprint="review-route-context",
        )
        lead = ScanLead(
            producer_run_id=9002,
            producer_run_type="sast",
            title="Missing claim note role check",
            category="A01",
            severity="high",
            confidence=0.9,
            location="goose/ClaimController.java:103",
            suggested_endpoint="POST /claims/{id}/note",
            reportable=True,
            validation_status="confirmed",
        )
        session.add_all([review_route, lead])
        session.flush()
        anchor = ComponentFact(
            sast_run_id=9002,
            component_id=ctx["api_component_id"],
            fact_type="lead_anchor",
            method="POST",
            path="/claims/{id}/note",
            evidence_location="goose/ClaimController.java:103",
            detail_json=json.dumps(
                {
                    "lead_id": lead.id,
                    "supporting_locations": [review_route.evidence_location],
                    "route_locations": ["goose/ClaimController.java:103"],
                }
            ),
            fingerprint="note-anchor-with-review-context",
        )
        session.add(anchor)
        session.flush()
        review_route_id = review_route.id
        anchor_id = anchor.id
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "reaches")
            .where(ComponentConnection.source_fact_id == review_route_id)
            .where(ComponentConnection.target_fact_id == anchor_id)
        ).all()

    assert edges == []


def test_face_quote_proxy_facts_infer_egress_and_preserve_one_to_one_hops(
    isolated_db_engine,
):
    """FACE proxy calls without an explicit role still form complete hops."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    quote_names = ("motor", "home", "contents")
    with Session(isolated_db_engine) as session:
        source_facts: list[ComponentFact] = []
        target_facts: list[ComponentFact] = []
        for index, name in enumerate(quote_names):
            route_location = f"FACE/app.py:{260 + index * 6}"
            egress_location = f"FACE/app.py:{263 + index * 6}"
            source_facts.extend(
                [
                    ComponentFact(
                        sast_run_id=9001,
                        component_id=ctx["ui_component_id"],
                        fact_type="route",
                        method="POST",
                        path=f"/api/quotes/{name}",
                        evidence_location=route_location,
                        detail_json=json.dumps(
                            {"supporting_locations": [egress_location]}
                        ),
                        fingerprint=f"face-route-{name}",
                    ),
                    ComponentFact(
                        sast_run_id=9001,
                        component_id=ctx["ui_component_id"],
                        fact_type="http_call",
                        method="POST",
                        path=f"/api/customer/quotes/{name}",
                        evidence_location=egress_location,
                        detail_json=json.dumps(
                            {
                                "supporting_locations": [route_location],
                                "reasoning": f"Outbound proxy call for {name} quote",
                            }
                        ),
                        fingerprint=f"face-egress-{name}",
                    ),
                ]
            )
            target_facts.append(
                ComponentFact(
                    sast_run_id=9002,
                    component_id=ctx["api_component_id"],
                    fact_type="route",
                    method="POST",
                    path=f"/api/customer/quotes/{name}",
                    evidence_location=f"Goose/{name}.java:10",
                    fingerprint=f"goose-route-{name}",
                )
            )
        session.add_all([*source_facts, *target_facts])
        session.flush()
        egress_ids = {
            fact.path.rsplit("/", 1)[-1]: fact.id
            for fact in source_facts
            if fact.fact_type == "http_call"
        }
        route_ids = {
            fact.path.rsplit("/", 1)[-1]: fact.id
            for fact in source_facts
            if fact.fact_type == "route"
        }
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        dispatches = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "dispatches")
            .where(
                ComponentConnection.source_fact_id.in_(
                    [fact_id for fact_id in route_ids.values()]
                )
            )
        ).all()
        egress_facts = session.exec(
            select(ComponentFact).where(
                ComponentFact.id.in_([fact_id for fact_id in egress_ids.values()])
            )
        ).all()
        cross_hops = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "calls")
            .where(
                ComponentConnection.source_fact_id.in_(
                    [fact_id for fact_id in egress_ids.values()]
                )
            )
        ).all()

    assert {(edge.source_fact_id, edge.target_fact_id) for edge in dispatches} == {
        (route_ids[name], egress_ids[name]) for name in quote_names
    }
    assert {
        fact.path.rsplit("/", 1)[-1]
        for fact in egress_facts
        if json.loads(fact.detail_json)["request_role"] == "server_egress"
    } == set(quote_names)
    assert {edge.source_fact_id for edge in cross_hops} == set(egress_ids.values())


def test_semantic_edges_include_late_browser_calls_beyond_legacy_limit(
    isolated_db_engine,
):
    """A call discovered after the old first-20 window remains reachable."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    action_location = "templates/claims/view.html:222"
    late_call_location = "templates/claims/view.html:222"
    with Session(isolated_db_engine) as session:
        action = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="ui_action",
            name="Disburse claim",
            evidence_location=action_location,
            detail_json=json.dumps({"trigger": "submit"}),
            fingerprint="late-form-action",
        )
        session.add(action)
        for index in range(25):
            session.add(
                ComponentFact(
                    sast_run_id=9001,
                    component_id=ctx["ui_component_id"],
                    fact_type="http_call",
                    method="GET",
                    path=f"/noise/{index}",
                    evidence_location=f"templates/noise-{index}.html:1",
                    detail_json=json.dumps({"request_role": "browser_request"}),
                    fingerprint=f"noise-call-{index}",
                )
            )
        late_call = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="http_call",
            method="POST",
            path="/claims/{id}/disburse",
            evidence_location=late_call_location,
            detail_json=json.dumps(
                {
                    "request_role": "browser_request",
                    "handler_locations": [action_location],
                }
            ),
            fingerprint="late-form-call",
        )
        session.add(late_call)
        session.flush()
        late_call_id = late_call.id
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "triggers")
            .where(ComponentConnection.target_fact_id == late_call_id)
        ).all()

    assert len(edges) == 1
    assert edges[0].source_fact_id is not None


def test_ui_action_request_edges_use_handler_ownership_not_shared_supporting_context(
    isolated_db_engine,
):
    """A shared helper location must not bind a request to every action."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        first_action = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="ui_action",
            name="submitMotorQuote",
            evidence_location="ui/form.tsx:10",
            detail_json=json.dumps(
                {"handler_locations": ["ui/app.ts:100"], "trigger": "submit"}
            ),
            fingerprint="motor-action",
        )
        second_action = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="ui_action",
            name="submitResidentialQuote",
            evidence_location="ui/form.tsx:20",
            detail_json=json.dumps(
                {"handler_locations": ["ui/app.ts:200"], "trigger": "submit"}
            ),
            fingerprint="residential-action",
        )
        motor_call = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="http_call",
            method="POST",
            path="/api/quotes/motor",
            evidence_location="ui/app.ts:300",
            detail_json=json.dumps(
                {
                    "request_role": "browser_request",
                    "handler_locations": ["ui/app.ts:100"],
                    "supporting_locations": [
                        "ui/form.tsx:10",
                        # Shared extraction context must not establish a
                        # second action-to-request edge.
                        "ui/form.tsx:20",
                    ],
                }
            ),
            fingerprint="motor-request",
        )
        session.add_all([first_action, second_action, motor_call])
        session.flush()
        first_action_id = first_action.id
        second_action_id = second_action.id
        motor_call_id = motor_call.id
        session.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as session:
        edges = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "triggers")
            .where(ComponentConnection.target_fact_id == motor_call_id)
        ).all()

    assert [edge.source_fact_id for edge in edges] == [first_action_id]
    assert second_action_id not in {edge.source_fact_id for edge in edges}


def test_purge_llm_component_facts_clears_dependent_rows_with_fk_enforcement(
    fk_engine,
):
    ctx = _seed_two_component_campaign(fk_engine)
    from aespa.services.component_mapper import purge_llm_component_facts

    with Session(fk_engine) as session:
        llm_fact = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="handler",
            name="create_order",
            detail_json='{"origin":"llm"}',
            evidence_location="src/checkout.js:50",
            fingerprint="llm-handler-fp",
        )
        session.add(llm_fact)
        session.flush()
        llm_fact_id = llm_fact.id
        session.add(
            ComponentConnection(
                campaign_id=ctx["campaign_id"],
                source_component_id=ctx["ui_component_id"],
                source_fact_id=llm_fact_id,
                target_component_id=ctx["api_component_id"],
                target_fact_id=ctx["route_fact_id"],
                confidence=0.8,
            )
        )
        campaign_lead = ScanLead(
            producer_run_id=ctx["campaign_id"],
            producer_run_type="campaign",
            title="derived lead",
        )
        session.add(campaign_lead)
        session.flush()
        campaign_lead_id = campaign_lead.id
        session.add(
            ScanLeadComponentProvenance(
                scan_lead_id=campaign_lead_id,
                component_id=ctx["ui_component_id"],
                fact_id=llm_fact_id,
            )
        )
        session.commit()

    assert purge_llm_component_facts(9001) == 1

    with Session(fk_engine) as session:
        assert session.get(ComponentFact, llm_fact_id) is None
        assert (
            session.exec(
                select(ComponentConnection).where(
                    ComponentConnection.source_fact_id == llm_fact_id
                )
            ).first()
            is None
        )
        provenance = session.exec(
            select(ScanLeadComponentProvenance).where(
                ScanLeadComponentProvenance.scan_lead_id == campaign_lead_id
            )
        ).one()
        assert provenance.fact_id is None


def test_persist_facts_clears_stale_graph_references_with_fk_enforcement(fk_engine):
    ctx = _seed_two_component_campaign(fk_engine)
    from aespa.services.component_mapper import _persist_facts

    with Session(fk_engine) as session:
        llm_fact = ComponentFact(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            fact_type="handler",
            name="create_order",
            detail_json='{"origin":"llm"}',
            evidence_location="src/checkout.js:50",
            fingerprint="llm-handler-fp",
        )
        session.add(llm_fact)
        session.flush()
        llm_fact_id = llm_fact.id
        session.add(
            ComponentConnection(
                campaign_id=ctx["campaign_id"],
                source_component_id=ctx["ui_component_id"],
                source_fact_id=llm_fact_id,
                target_component_id=ctx["api_component_id"],
                target_fact_id=ctx["route_fact_id"],
                confidence=0.8,
            )
        )
        session.commit()

    assert (
        _persist_facts(
            sast_run_id=9001,
            component_id=ctx["ui_component_id"],
            facts=[],
        )
        == 0
    )

    with Session(fk_engine) as session:
        assert session.get(ComponentFact, llm_fact_id) is None
        assert (
            session.exec(
                select(ComponentConnection).where(
                    ComponentConnection.source_fact_id == llm_fact_id
                )
            ).first()
            is None
        )


@pytest.mark.anyio
async def test_llm_correlation_persists_valid_ambiguous_match(
    isolated_db_engine, monkeypatch
):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as session:
        call = session.get(ComponentFact, ctx["call_fact_id"])
        route = session.get(ComponentFact, ctx["route_fact_id"])
        call.path = "/v1/orders"
        route.path = "/orders"
        session.add(call)
        session.add(route)
        session.commit()

    from aespa.services import component_mapper, llm, settings

    monkeypatch.setattr(settings, "get_llm_config_for_role", lambda *_args: object())

    async def fake_mapper(*_args, **_kwargs):
        return None

    async def fake_completion(*_args, **_kwargs):
        return json.dumps(
            [
                {
                    "call_id": ctx["call_fact_id"],
                    "route_id": ctx["route_fact_id"],
                    "confidence": 0.88,
                    "rationale": "The versioned caller reaches the route service.",
                    "evidence": {"source": "test"},
                }
            ]
        )

    monkeypatch.setattr(component_mapper, "map_campaign_component", fake_mapper)
    monkeypatch.setattr(llm, "plain_completion", fake_completion)
    result = await correlate_campaign_with_llm(ctx["campaign_id"])

    assert result["connections"] == 2  # internal anchor edge plus the LLM hop
    with Session(isolated_db_engine) as session:
        connection = session.exec(
            select(ComponentConnection)
            .where(ComponentConnection.campaign_id == ctx["campaign_id"])
            .where(ComponentConnection.edge_kind == "calls")
        ).one()
        assert connection.match_kind == "llm_assisted"
        assert connection.confidence == 0.88


@pytest.mark.anyio
async def test_llm_correlation_skips_failed_source_scan(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as session:
        app = Application(name="Partial mapping app")
        session.add(app)
        session.flush()
        good_component = ApplicationComponent(
            application_id=app.id, name="good-component"
        )
        failed_component = ApplicationComponent(
            application_id=app.id, name="failed-component"
        )
        session.add(good_component)
        session.add(failed_component)
        session.flush()
        good_snapshot = ComponentSnapshot(
            component_id=good_component.id,
            filename="good.zip",
            stored_path="/tmp/good.zip",
            size_bytes=1,
            sha256="c" * 64,
        )
        failed_snapshot = ComponentSnapshot(
            component_id=failed_component.id,
            filename="failed.zip",
            stored_path="/tmp/failed.zip",
            size_bytes=1,
            sha256="d" * 64,
        )
        good_run = SastRun(name="good", status="completed")
        failed_run = SastRun(name="failed", status="failed")
        session.add(good_snapshot)
        session.add(failed_snapshot)
        session.add(good_run)
        session.add(failed_run)
        session.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="partial")
        session.add(campaign)
        session.flush()
        session.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=good_component.id,
                snapshot_id=good_snapshot.id,
                sast_run_id=good_run.id,
                status="completed",
            )
        )
        session.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=failed_component.id,
                snapshot_id=failed_snapshot.id,
                sast_run_id=failed_run.id,
                status="failed",
            )
        )
        session.commit()
        campaign_id = campaign.id
        good_member_id = (
            session.exec(
                select(CampaignSourceMember)
                .where(CampaignSourceMember.campaign_id == campaign_id)
                .where(CampaignSourceMember.component_id == good_component.id)
            )
            .one()
            .id
        )

    from aespa.services import component_mapper, settings

    monkeypatch.setattr(settings, "get_llm_config_for_role", lambda *_args: object())
    mapped_member_ids: list[int] = []

    async def fake_mapper(_campaign_id, member_id, **_kwargs):
        mapped_member_ids.append(member_id)
        return None

    monkeypatch.setattr(component_mapper, "map_campaign_component", fake_mapper)
    result = await correlate_campaign_with_llm(campaign_id)

    assert result["connections"] == 0
    assert mapped_member_ids == [good_member_id]


def test_correlate_campaign_proposes_lead_target_mapping_via_endpoint_match(
    isolated_db_engine,
):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])

    with Session(isolated_db_engine) as s:
        mappings = s.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == ctx["campaign_id"]
            )
        ).all()
    # This seed's connection is well-evidenced enough to also generate a
    # cross-repo lead (covered by its own tests below), which is itself now
    # proposed for review — so two mappings exist. Assert specifically on
    # the mapping for the original single-component lead.
    mapping = next(m for m in mappings if m.lead_id == ctx["source_lead_id"])
    assert mapping.target_id == ctx["target_id"]
    assert mapping.score > 0
    assert mapping.status == "proposed"


def test_explicit_target_component_creates_approved_mapping_before_copy(
    isolated_db_engine,
):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as s:
        target = s.get(ApplicationTarget, ctx["target_id"])
        target.component_id = ctx["ui_component_id"]
        from aespa.models import ApiTestRun

        target_run = ApiTestRun(collection_id=1, name="target run")
        s.add(target_run)
        s.commit()
        s.refresh(target_run)
        target_run_id = target_run.id

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        own_mapping = s.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == ctx["campaign_id"])
            .where(LeadTargetMapping.lead_id == ctx["source_lead_id"])
        ).first()
    assert own_mapping is not None
    assert own_mapping.status == "approved"
    assert own_mapping.auto_approved is True
    assert own_mapping.copied_lead_id is None

    with Session(isolated_db_engine) as s:
        copies = s.exec(
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == "api")
            .where(ScanLead.imported_into_run_id == target_run_id)
        ).all()
    assert copies == []


def test_correlate_campaign_generates_cross_repo_lead_with_provenance(
    isolated_db_engine,
):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])

    with Session(isolated_db_engine) as s:
        cross_leads = s.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == ctx["campaign_id"])
        ).all()
        assert len(cross_leads) == 1
        lead = cross_leads[0]
        provenance = s.exec(
            select(ScanLeadComponentProvenance).where(
                ScanLeadComponentProvenance.scan_lead_id == lead.id
            )
        ).all()
    component_ids = {p.component_id for p in provenance}
    assert component_ids == {ctx["ui_component_id"], ctx["api_component_id"]}
    roles = {p.role for p in provenance}
    assert roles == {"primary", "contributing"}


def test_correlate_campaign_skips_cross_repo_lead_when_route_has_auth_boundary(
    isolated_db_engine,
):
    ctx = _seed_two_component_campaign(isolated_db_engine, public_route=False)
    with Session(isolated_db_engine) as s:
        s.add(
            ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="auth_boundary",
                name="login_required",
                evidence_location="src/routes.py:10",  # same file as the route
                fingerprint="auth-fp",
            )
        )
        s.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        cross_leads = s.exec(
            select(ScanLead).where(ScanLead.producer_run_type == "campaign")
        ).all()
    assert cross_leads == []


def test_correlate_campaign_does_not_treat_missing_auth_evidence_as_public(
    isolated_db_engine,
):
    ctx = _seed_two_component_campaign(isolated_db_engine, public_route=False)

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        cross_leads = s.exec(
            select(ScanLead).where(ScanLead.producer_run_type == "campaign")
        ).all()
    assert cross_leads == []


def test_correlate_campaign_follows_evidence_backed_authentication_chain(
    isolated_db_engine,
):
    """A public credential flow can make a protected cross-repo route reachable."""
    ctx = _seed_two_component_campaign(isolated_db_engine, public_route=False)
    with Session(isolated_db_engine) as s:
        s.add(
            ComponentFact(
                sast_run_id=9001,
                component_id=ctx["ui_component_id"],
                fact_type="http_call",
                method="POST",
                path="/session",
                host="api.acme.test",
                evidence_location="src/session.js:20",
                fingerprint="session-call-fp",
            )
        )
        s.add(
            ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="route",
                method="POST",
                path="/session",
                evidence_location="src/session_routes.py:5",
                fingerprint="session-route-fp",
            )
        )
        s.add(
            ComponentFact(
                sast_run_id=9001,
                component_id=ctx["ui_component_id"],
                fact_type="auth_flow",
                method="POST",
                path="/session",
                name="bearer token",
                evidence_location="src/session.js:21",
                detail_json=json.dumps(
                    {
                        "origin": "llm",
                        "confidence": 0.9,
                        "credential_kind": "bearer",
                        "acquisition_call_locations": ["src/session.js:20"],
                        "credential_use_locations": ["src/checkout.js:42"],
                    }
                ),
                fingerprint="auth-flow-fp",
            )
        )
        s.add(
            ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="auth_boundary",
                method="POST",
                path="/session",
                detail_json=json.dumps(
                    {
                        "scope": "path",
                        "public_paths": ["/session"],
                        "public_methods": ["POST"],
                    }
                ),
                evidence_location="src/security.py:8",
                fingerprint="public-session-fp",
            )
        )
        s.add(
            ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="auth_boundary",
                detail_json=json.dumps(
                    {"scope": "global", "protected_paths": ["/orders"]}
                ),
                evidence_location="src/security.py:9",
                fingerprint="protected-orders-fp",
            )
        )
        target_lead = ScanLead(
            producer_run_id=9002,
            producer_run_type="sast",
            title="Authorization control failure in order service",
            category="A01",
            severity="high",
            confidence=0.9,
            location="src/order_policy.py:50",
            suggested_endpoint="POST /orders",
            evidence="The order policy trusts an attacker-controlled account.",
            reportable=True,
            validation_status="confirmed",
        )
        s.add(target_lead)
        s.flush()
        s.add(
            ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="lead_anchor",
                method="POST",
                path="/orders",
                name=target_lead.title,
                detail_json=json.dumps(
                    {
                        "origin": "llm",
                        "lead_id": target_lead.id,
                        "route_locations": ["src/routes.py:10"],
                    }
                ),
                evidence_location="src/order_policy.py:50",
                fingerprint="order-policy-anchor-fp",
            )
        )
        s.commit()

    result = correlate_campaign(ctx["campaign_id"], llm_match=lambda _items: [])
    assert result["cross_component_leads"] == 2
    with Session(isolated_db_engine) as s:
        leads = s.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == ctx["campaign_id"])
        ).all()
        assert len(leads) == 2
        for lead in leads:
            attack_path = json.loads(lead.attack_path_json)
            instance = next(
                item
                for item in attack_path["instances"]
                if item["target_path"] == "/orders"
            )
            assert instance["access"] == "authenticated"
            assert instance["authentication"]["credential_kind"] == "bearer"
            assert instance["authentication"]["acquisition"]["path"] == "/session"
        backend = next(
            lead for lead in leads if "Authorization control failure" in lead.title
        )
        assert backend.location == "src/order_policy.py:50"


def test_correlate_campaign_does_not_fabricate_lead_without_connection(
    isolated_db_engine,
):
    """No http_call/route match at all -> no connections, no cross-repo leads."""
    with Session(isolated_db_engine) as s:
        app = Application(name="Lonely App")
        s.add(app)
        s.flush()
        component = ApplicationComponent(application_id=app.id, name="solo")
        s.add(component)
        s.flush()
        snapshot = ComponentSnapshot(
            component_id=component.id,
            filename="solo.zip",
            stored_path="/tmp/solo.zip",
            size_bytes=1,
            sha256="c" * 64,
        )
        s.add(snapshot)
        s.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="solo-campaign")
        s.add(campaign)
        s.flush()
        s.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=component.id,
                snapshot_id=snapshot.id,
                sast_run_id=7001,
                status="completed",
            )
        )
        s.commit()
        campaign_id = campaign.id

    result = correlate_campaign(campaign_id)
    assert result == {
        "connections": 0,
        "cross_component_leads": 0,
        "lead_target_mappings": 0,
    }


# ── Review idempotency / rejection ──────────────────────────────────────────


def test_apply_review_decisions_is_idempotent(isolated_db_engine):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        mapping = s.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == ctx["campaign_id"]
            )
        ).first()
        mapping_id = mapping.id

    result1 = apply_review_decisions(ctx["campaign_id"], [(mapping_id, True)])
    result2 = apply_review_decisions(ctx["campaign_id"], [(mapping_id, True)])
    assert result1["approved"] == 1
    assert result2["approved"] == 0  # already approved — no-op the second time

    with Session(isolated_db_engine) as s:
        mapping = s.get(LeadTargetMapping, mapping_id)
    assert mapping.status == "approved"


def test_rejected_mapping_is_never_copied(isolated_db_engine):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        mapping = s.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == ctx["campaign_id"]
            )
        ).first()
        mapping_id = mapping.id

    apply_review_decisions(ctx["campaign_id"], [(mapping_id, False)])
    with Session(isolated_db_engine) as s:
        api_run_id = 5001
        from aespa.models import ApiTestRun

        run = ApiTestRun(collection_id=1, name="target run", id=api_run_id)
        s.add(run)
        s.commit()

    copied = copy_approved_mappings_for_target(
        ctx["campaign_id"], ctx["target_id"], "api", api_run_id
    )
    assert copied == 0
    with Session(isolated_db_engine) as s:
        mapping = s.get(LeadTargetMapping, mapping_id)
        assert mapping.status == "rejected"
        assert mapping.copied_lead_id is None
        copies = s.exec(
            select(ScanLead).where(ScanLead.imported_into_run_id == api_run_id)
        ).all()
    assert copies == []


def test_copy_approved_mapping_into_exact_child_run_is_idempotent(
    isolated_db_engine,
):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        mapping = s.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == ctx["campaign_id"]
            )
        ).first()
        mapping_id = mapping.id

    apply_review_decisions(ctx["campaign_id"], [(mapping_id, True)])

    with Session(isolated_db_engine) as s:
        from aespa.models import ApiTestRun

        run = ApiTestRun(collection_id=1, name="target run")
        s.add(run)
        s.commit()
        s.refresh(run)
        api_run_id = run.id

    copied_1 = copy_approved_mappings_for_target(
        ctx["campaign_id"], ctx["target_id"], "api", api_run_id
    )
    copied_2 = copy_approved_mappings_for_target(
        ctx["campaign_id"], ctx["target_id"], "api", api_run_id
    )
    assert copied_1 == 1
    assert copied_2 == 1  # copy_lead_to_run itself is idempotent — no duplicate

    with Session(isolated_db_engine) as s:
        copies = s.exec(
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == "api")
            .where(ScanLead.imported_into_run_id == api_run_id)
        ).all()
    assert len(copies) == 1


# ── Regression: facts must be scoped to this campaign's exact sast_run_id ──


def test_correlate_campaign_ignores_facts_from_a_different_sast_run_of_same_component(
    isolated_db_engine,
):
    """A component reused across two campaigns/snapshots has two distinct
    ``sast_run_id``s. Correlating campaign B must never pull in facts that
    belong to campaign A's (different) SastRun for the same component_id."""
    ctx = _seed_two_component_campaign(isolated_db_engine)

    with Session(isolated_db_engine) as s:
        # A duplicate outbound-call fact for the SAME ui component and the
        # SAME method/path as the genuine one, but recorded under a
        # different, unrelated SastRun (e.g. an older campaign's scan of an
        # older snapshot). If facts were scoped by component_id alone this
        # would produce a *second*, spurious ComponentConnection.
        rogue_call_fact = ComponentFact(
            sast_run_id=424242,  # a different, unrelated SastRun
            component_id=ctx["ui_component_id"],
            fact_type="http_call",
            method="POST",
            path="/orders",
            host="api.acme.test",
            evidence_location="src/old_version.js:1",
            fingerprint="rogue-fp",
        )
        s.add(rogue_call_fact)
        s.commit()
        rogue_call_fact_id = rogue_call_fact.id

    result = correlate_campaign(ctx["campaign_id"])
    # The unrelated other-run fact is not considered. The result also includes
    # the internal lead-anchor edge for the genuine fact.
    assert result["connections"] == 2
    with Session(isolated_db_engine) as s:
        connections = s.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == ctx["campaign_id"]
            )
        ).all()
        source_fact_ids = {c.source_fact_id for c in connections}
    assert rogue_call_fact_id not in source_fact_ids
    assert ctx["call_fact_id"] in source_fact_ids


def test_generate_cross_repo_lead_checks_auth_boundary_scoped_to_exact_sast_run(
    isolated_db_engine,
):
    """An auth_boundary fact belonging to a *different* SastRun for the same
    target component must not suppress a genuine cross-repo lead."""
    ctx = _seed_two_component_campaign(isolated_db_engine)

    with Session(isolated_db_engine) as s:
        # Auth boundary recorded under an unrelated sast_run_id, at the SAME
        # file:line as the real route fact. Pre-fix, the component-scoped
        # query would incorrectly treat this as protecting the route.
        s.add(
            ComponentFact(
                sast_run_id=999999,
                component_id=ctx["api_component_id"],
                fact_type="auth_boundary",
                name="login_required",
                evidence_location="src/routes.py:10",
                fingerprint="unrelated-auth-fp",
            )
        )
        s.commit()

    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        cross_leads = s.exec(
            select(ScanLead).where(ScanLead.producer_run_type == "campaign")
        ).all()
    # The lead is still generated — an auth boundary from an unrelated run
    # must not be treated as protecting this campaign's route.
    assert len(cross_leads) == 1


# ── Regression: absolute outbound URLs must normalize to match routes ──────


def test_absolute_outbound_url_matches_relative_route_path(isolated_db_engine):
    with Session(isolated_db_engine) as s:
        app = Application(name="AbsUrlApp")
        s.add(app)
        s.flush()
        ui = ApplicationComponent(application_id=app.id, name="ui")
        api = ApplicationComponent(application_id=app.id, name="api")
        s.add(ui)
        s.add(api)
        s.flush()
        ui_snap = ComponentSnapshot(
            component_id=ui.id,
            filename="ui.zip",
            stored_path="/x/ui.zip",
            size_bytes=1,
            sha256="f" * 64,
        )
        api_snap = ComponentSnapshot(
            component_id=api.id,
            filename="api.zip",
            stored_path="/x/api.zip",
            size_bytes=1,
            sha256="g" * 64,
        )
        s.add(ui_snap)
        s.add(api_snap)
        campaign = AssessmentCampaign(application_id=app.id, name="abs-url")
        s.add(campaign)
        s.flush()
        s.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=ui.id,
                snapshot_id=ui_snap.id,
                sast_run_id=5001,
                status="completed",
            )
        )
        s.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=api.id,
                snapshot_id=api_snap.id,
                sast_run_id=5002,
                status="completed",
            )
        )
        s.flush()
        # The outbound call fact stores a full absolute URL, as the
        # deterministic extractor records it for e.g. requests.post(...).
        s.add(
            ComponentFact(
                sast_run_id=5001,
                component_id=ui.id,
                fact_type="http_call",
                method="POST",
                path="https://api.acme.test/orders?debug=1",
                host="api.acme.test",
                evidence_location="ui.js:1",
                fingerprint="abs-call-fp",
            )
        )
        s.add(
            ComponentFact(
                sast_run_id=5002,
                component_id=api.id,
                fact_type="route",
                method="POST",
                path="/orders",
                evidence_location="routes.py:1",
                fingerprint="abs-route-fp",
            )
        )
        s.commit()
        campaign_id = campaign.id

    result = correlate_campaign(campaign_id)
    assert result["connections"] == 1
    with Session(isolated_db_engine) as s:
        connection = s.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == campaign_id
            )
        ).first()
    assert connection is not None
    assert connection.confidence >= 0.8  # both method AND path matched


# ── Regression: review validation (finding 7) ────────────────────────────────


def test_apply_review_decisions_rejects_unknown_mapping_id(isolated_db_engine):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])

    import pytest

    from aespa.services.correlation import UnknownMappingError

    with pytest.raises(UnknownMappingError):
        apply_review_decisions(ctx["campaign_id"], [(999999, True)])


def test_apply_review_decisions_rejects_mapping_from_another_campaign(
    isolated_db_engine,
):
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        mapping = s.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == ctx["campaign_id"]
            )
        ).first()
        mapping_id = mapping.id

    import pytest

    from aespa.services.correlation import UnknownMappingError

    other_campaign_id = ctx["campaign_id"] + 1000  # never exists
    with pytest.raises(UnknownMappingError):
        apply_review_decisions(other_campaign_id, [(mapping_id, True)])
    # Nothing was applied — the mapping is untouched.
    with Session(isolated_db_engine) as s:
        mapping = s.get(LeadTargetMapping, mapping_id)
        assert mapping.status == "proposed"


def test_apply_review_decisions_all_or_nothing_on_unknown_id(isolated_db_engine):
    """A batch with one valid and one unknown id must apply neither."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        mapping = s.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == ctx["campaign_id"]
            )
        ).first()
        mapping_id = mapping.id

    import pytest

    from aespa.services.correlation import UnknownMappingError

    with pytest.raises(UnknownMappingError):
        apply_review_decisions(
            ctx["campaign_id"], [(mapping_id, True), (999999, False)]
        )
    with Session(isolated_db_engine) as s:
        mapping = s.get(LeadTargetMapping, mapping_id)
        assert mapping.status == "proposed"  # untouched, not partially applied


def test_count_pending_mappings_reflects_review_progress(isolated_db_engine):
    from aespa.services.correlation import count_pending_mappings

    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])
    with Session(isolated_db_engine) as s:
        mapping_ids = [
            m.id
            for m in s.exec(
                select(LeadTargetMapping).where(
                    LeadTargetMapping.campaign_id == ctx["campaign_id"]
                )
            ).all()
        ]
    assert count_pending_mappings(ctx["campaign_id"]) == len(mapping_ids)

    apply_review_decisions(ctx["campaign_id"], [(mapping_ids[0], True)])
    assert count_pending_mappings(ctx["campaign_id"]) == len(mapping_ids) - 1

    apply_review_decisions(ctx["campaign_id"], [(m, True) for m in mapping_ids[1:]])
    assert count_pending_mappings(ctx["campaign_id"]) == 0


# ── Regression: correlate_campaign must not open a nested writing Session ──


def test_correlate_campaign_uses_a_single_session_for_all_writes(
    isolated_db_engine, monkeypatch
):
    """The whole correlate_campaign body — including cross-repo lead
    creation — must run inside the one Session it opens. Previously,
    generating a cross-repo lead called ``create_lead``, which opened and
    committed its own separate ``Session`` mid-transaction."""
    import aespa.services.correlation as correlation_module
    import aespa.services.scan_leads as scan_leads_module

    ctx = _seed_two_component_campaign(isolated_db_engine)

    real_session = Session
    session_instances: list[object] = []

    def _tracking_session(*args, **kwargs):
        instance = real_session(*args, **kwargs)
        session_instances.append(instance)
        return instance

    # Patch every module that could plausibly open its own Session during
    # this call — correlation.py itself, and scan_leads.py (create_lead's
    # home), whose Session it would have used if a nested write reappeared.
    monkeypatch.setattr(correlation_module, "Session", _tracking_session)
    monkeypatch.setattr(scan_leads_module, "Session", _tracking_session)

    correlate_campaign(ctx["campaign_id"])

    # Exactly one Session for this whole call — cross-repo lead creation
    # must reuse it rather than opening (and committing) a second one.
    assert len(session_instances) == 1


def test_correlate_campaign_cross_repo_lead_is_atomic_with_the_rest(
    isolated_db_engine, monkeypatch
):
    """If anything after cross-repo lead generation fails, the lead must not
    have been silently committed by a separate, already-closed Session."""
    import aespa.services.correlation as correlation_module

    ctx = _seed_two_component_campaign(isolated_db_engine)

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure after cross-repo lead creation")

    monkeypatch.setattr(correlation_module, "_propose_lead_target_mappings", _boom)

    import pytest

    with pytest.raises(RuntimeError):
        correlate_campaign(ctx["campaign_id"])

    with Session(isolated_db_engine) as s:
        cross_leads = s.exec(
            select(ScanLead).where(ScanLead.producer_run_type == "campaign")
        ).all()
    # The cross-repo lead created earlier in the same call was rolled back
    # along with everything else — it was never committed independently.
    assert cross_leads == []


# ── Regression: cross-repo leads flow end-to-end through the same pipeline ──


def test_cross_repo_lead_flows_end_to_end_through_mapping_review_and_dast_copy(
    isolated_db_engine,
):
    """A campaign-owned cross-repository lead must be:
    1. proposed as a LeadTargetMapping (not silently excluded),
    2. reviewable via apply_review_decisions,
    3. copied into the exact child run once approved, and
    4. present in that run's leads exactly like any other lead — the whole
    review -> approve -> DAST-copy pipeline, not just correlation output.
    """
    ctx = _seed_two_component_campaign(isolated_db_engine)
    correlate_campaign(ctx["campaign_id"])

    with Session(isolated_db_engine) as s:
        cross_lead = s.exec(
            select(ScanLead).where(ScanLead.producer_run_type == "campaign")
        ).first()
        assert cross_lead is not None
        cross_lead_id = cross_lead.id

        # 1. It must have been proposed for review — not silently dropped.
        mapping = s.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == ctx["campaign_id"])
            .where(LeadTargetMapping.lead_id == cross_lead_id)
        ).first()
        assert mapping is not None
        assert mapping.status == "proposed"
        assert mapping.target_id == ctx["target_id"]
        assert mapping.score > 0
        mapping_id = mapping.id

    # 2. Reviewable.
    result = apply_review_decisions(ctx["campaign_id"], [(mapping_id, True)])
    assert result["approved"] == 1
    with Session(isolated_db_engine) as s:
        mapping = s.get(LeadTargetMapping, mapping_id)
        assert mapping.status == "approved"

    # 3. Copied into the exact child DAST run once approved.
    with Session(isolated_db_engine) as s:
        from aespa.models import ApiTestRun

        run = ApiTestRun(collection_id=1, name="orders-api dast run")
        s.add(run)
        s.commit()
        s.refresh(run)
        api_run_id = run.id

    copied = copy_approved_mappings_for_target(
        ctx["campaign_id"], ctx["target_id"], "api", api_run_id
    )
    assert copied == 1

    with Session(isolated_db_engine) as s:
        mapping = s.get(LeadTargetMapping, mapping_id)
        assert mapping.copied_lead_id is not None

        # 4. The copy is a real ScanLead owned by the DAST run, preserving
        # the cross-repo provenance (producer_run_type/id still point back
        # to the campaign for traceability).
        copy = s.get(ScanLead, mapping.copied_lead_id)
        assert copy is not None
        assert copy.imported_into_run_type == "api"
        assert copy.imported_into_run_id == api_run_id
        assert copy.producer_run_type == "campaign"
        assert copy.producer_run_id == ctx["campaign_id"]
        assert copy.status == "open"

        from aespa.services.scan_leads import get_leads_for_run

    leads_for_run = get_leads_for_run("api", api_run_id)
    assert any(lead.id == mapping.copied_lead_id for lead in leads_for_run)


def test_generate_cross_repo_lead_for_backend_route_vulnerability(isolated_db_engine):
    """When a SAST lead exists on a backend route (Repo B) connected to a frontend call site (Repo A),
    correlate_campaign must generate a cross-repository lead with Repo A as primary provenance,
    populating attack_path_json with structured entrypoint details."""
    ctx = _seed_two_component_campaign(isolated_db_engine)

    with Session(isolated_db_engine) as s:
        target_lead = ScanLead(
            producer_run_id=9002,
            producer_run_type="sast",
            title="Arbitrary order price acceptance",
            category="A01",
            severity="high",
            confidence=0.88,
            location="src/routes.py:10",  # matches route_fact evidence_location
            evidence="Order total is accepted directly from payload without catalog price re-verification.",
            reportable=True,
            validation_status="confirmed",
        )
        s.add(target_lead)
        s.commit()

    res = correlate_campaign(ctx["campaign_id"])
    assert res["cross_component_leads"] >= 1

    with Session(isolated_db_engine) as s:
        cross_leads = s.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == ctx["campaign_id"])
        ).all()

        backend_cross_lead = next(
            (
                lead
                for lead in cross_leads
                if "Arbitrary order price acceptance" in lead.title
            ),
            None,
        )
        assert backend_cross_lead is not None
        assert backend_cross_lead.attack_path_json != "{}"

        attack_path = json.loads(backend_cross_lead.attack_path_json)
        assert "frontend_entrypoint" in attack_path
        assert attack_path["frontend_entrypoint"]["location"] == "src/checkout.js:42"
        assert attack_path["backend_route"]["location"] == "src/routes.py:10"

        provenance = s.exec(
            select(ScanLeadComponentProvenance).where(
                ScanLeadComponentProvenance.scan_lead_id == backend_cross_lead.id
            )
        ).all()

        primary_prov = next((p for p in provenance if p.role == "primary"), None)
        assert primary_prov is not None
        assert primary_prov.component_id == ctx["ui_component_id"]


def test_cross_repo_backend_lead_groups_endpoint_instances(isolated_db_engine):
    """One backend root lead should cover every matched endpoint instance."""
    ctx = _seed_two_component_campaign(isolated_db_engine)
    with Session(isolated_db_engine) as s:
        s.add(
            ComponentFact(
                sast_run_id=9001,
                component_id=ctx["ui_component_id"],
                fact_type="http_call",
                method="POST",
                path="/orders/second",
                host="api.acme.test",
                evidence_location="src/checkout.js:42",
                fingerprint="second-call-fp",
            )
        )
        s.add(
            ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="route",
                method="POST",
                path="/orders/second",
                evidence_location="src/routes.py:10",
                fingerprint="second-route-fp",
            )
        )
        s.add(
            ComponentFact(
                sast_run_id=9002,
                component_id=ctx["api_component_id"],
                fact_type="auth_boundary",
                method="POST",
                path="/orders/second",
                detail_json=json.dumps(
                    {
                        "scope": "path",
                        "public_paths": ["/orders/second"],
                        "public_methods": ["POST"],
                    }
                ),
                evidence_location="src/security.py:9",
                fingerprint="public-second-order-fp",
            )
        )
        s.add(
            ScanLead(
                producer_run_id=9002,
                producer_run_type="sast",
                title="Arbitrary order price acceptance",
                category="A01",
                severity="high",
                confidence=0.88,
                location="src/routes.py:10",
                evidence="Order total is accepted directly from payload.",
                reportable=True,
                validation_status="confirmed",
            )
        )
        s.commit()

    result = correlate_campaign(ctx["campaign_id"])
    assert result["cross_component_leads"] == 2
    with Session(isolated_db_engine) as s:
        leads = s.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == ctx["campaign_id"])
        ).all()
        backend_leads = [
            lead for lead in leads if "Arbitrary order price acceptance" in lead.title
        ]
        assert len(backend_leads) == 1
        path = json.loads(backend_leads[0].attack_path_json)
        assert len(path["instances"]) == 2
        assert {instance["target_path"] for instance in path["instances"]} == {
            "/orders",
            "/orders/second",
        }


def _seed_single_component_frontend_campaign(
    engine, *, include_other_site: bool = False
) -> dict:
    """Create one action with both direct and handler-backed graph variants."""
    with Session(engine) as session:
        app = Application(name="Frontend quality")
        session.add(app)
        session.flush()
        ui = ApplicationComponent(application_id=app.id, name="face-ui")
        other = ApplicationComponent(application_id=app.id, name="other-ui")
        session.add_all([ui, other])
        session.flush()
        snapshot = ComponentSnapshot(
            component_id=ui.id,
            filename="face.zip",
            stored_path="/tmp/face.zip",
            size_bytes=1,
            sha256="f" * 64,
        )
        session.add(snapshot)
        session.flush()
        own_site = Site(name="FACE site", base_url="https://face.example.test")
        session.add(own_site)
        session.flush()
        own_target = ApplicationTarget(
            application_id=app.id,
            target_type="site",
            target_id=own_site.id,
            component_id=ui.id,
        )
        session.add(own_target)
        other_target = None
        if include_other_site:
            other_site = Site(name="Other site", base_url="https://other.example.test")
            session.add(other_site)
            session.flush()
            other_target = ApplicationTarget(
                application_id=app.id,
                target_type="site",
                target_id=other_site.id,
                component_id=other.id,
            )
            session.add(other_target)
        session.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="frontend quality")
        session.add(campaign)
        session.flush()
        session.add(
            CampaignSourceMember(
                campaign_id=campaign.id,
                component_id=ui.id,
                snapshot_id=snapshot.id,
                sast_run_id=9401,
                status="completed",
            )
        )
        session.add(
            CampaignTargetMember(
                campaign_id=campaign.id,
                target_id=own_target.id,
                target_type="site",
            )
        )
        if other_target is not None:
            session.add(
                CampaignTargetMember(
                    campaign_id=campaign.id,
                    target_id=other_target.id,
                    target_type="site",
                )
            )
        lead = ScanLead(
            producer_run_id=9401,
            producer_run_type="sast",
            title="Payment amount is trusted",
            description="The server accepts a client controlled payment amount.",
            category="A04",
            severity="high",
            confidence=0.9,
            location="server/payment.py:40",
            suggested_endpoint="POST /api/payment/process",
            reportable=True,
        )
        session.add(lead)
        session.flush()
        action_location = "ui/payment.js:10"
        handler_location = "ui/payment.js:20"
        call_location = "ui/payment.js:30"
        route_location = "server/payment.py:40"
        session.add_all(
            [
                ComponentFact(
                    sast_run_id=9401,
                    component_id=ui.id,
                    fact_type="ui_action",
                    name="Pay now",
                    evidence_location=action_location,
                    detail_json=json.dumps(
                        {
                            "action_kind": "click",
                            "handler_locations": [handler_location],
                            "supporting_locations": [call_location],
                        }
                    ),
                    fingerprint="frontend-action",
                ),
                ComponentFact(
                    sast_run_id=9401,
                    component_id=ui.id,
                    fact_type="handler",
                    name="processPayment",
                    evidence_location=handler_location,
                    detail_json=json.dumps({"supporting_locations": [call_location]}),
                    fingerprint="frontend-handler",
                ),
                ComponentFact(
                    sast_run_id=9401,
                    component_id=ui.id,
                    fact_type="http_call",
                    method="POST",
                    path="/api/payment/process",
                    evidence_location=call_location,
                    detail_json=json.dumps({"request_role": "browser_request"}),
                    fingerprint="frontend-call",
                ),
                ComponentFact(
                    sast_run_id=9401,
                    component_id=ui.id,
                    fact_type="route",
                    method="POST",
                    path="/api/payment/process",
                    evidence_location=route_location,
                    fingerprint="frontend-route",
                ),
            ]
        )
        session.commit()
        return {
            "campaign_id": campaign.id,
            "own_target_id": own_target.id,
            "other_target_id": other_target.id if other_target else None,
        }


def test_equivalent_handler_and_direct_paths_create_one_campaign_lead(
    isolated_db_engine,
):
    ctx = _seed_single_component_frontend_campaign(isolated_db_engine)

    correlate_campaign(ctx["campaign_id"])

    with Session(isolated_db_engine) as session:
        leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == ctx["campaign_id"])
        ).all()
        assert len(leads) == 1
        path = json.loads(leads[0].attack_path_json)
        assert path["path_status"] == "complete"
        fact_kinds = [fact["kind"] for fact in path["static_trace"]["facts"]]
        assert "handler" in fact_kinds
        assert leads[0].trace_path_key


def test_complete_single_component_path_only_maps_to_owning_site(
    isolated_db_engine,
):
    ctx = _seed_single_component_frontend_campaign(
        isolated_db_engine, include_other_site=True
    )

    correlate_campaign(ctx["campaign_id"])

    with Session(isolated_db_engine) as session:
        campaign_lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == ctx["campaign_id"])
        ).one()
        mappings = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == ctx["campaign_id"])
            .where(LeadTargetMapping.lead_id == campaign_lead.id)
        ).all()

    assert [mapping.target_id for mapping in mappings] == [ctx["own_target_id"]]
    assert mappings[0].status == "approved"
