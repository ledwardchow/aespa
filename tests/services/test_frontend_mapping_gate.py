"""Regression tests for evidence-backed frontend mapping."""

from __future__ import annotations

import json

from sqlmodel import Session, select

from aespa.models import (
    Application,
    ApplicationComponent,
    AssessmentCampaign,
    CampaignSourceMember,
    ComponentConnection,
    ComponentFact,
    ComponentSnapshot,
    ScanLead,
)
from aespa.services.correlation import _build_component_connections, _has_frontend_trace
from aespa.services.route_tracing import trace_lead_paths


def _seed_source_members(session: Session) -> tuple[int, list[CampaignSourceMember]]:
    app = Application(name="Mapping gate")
    session.add(app)
    session.flush()
    ui = ApplicationComponent(application_id=app.id, name="checkout-ui")
    api = ApplicationComponent(application_id=app.id, name="orders-api")
    session.add_all([ui, api])
    session.flush()
    ui_snapshot = ComponentSnapshot(
        component_id=ui.id,
        filename="ui.zip",
        stored_path="/tmp/ui.zip",
        size_bytes=1,
        sha256="a" * 64,
    )
    api_snapshot = ComponentSnapshot(
        component_id=api.id,
        filename="api.zip",
        stored_path="/tmp/api.zip",
        size_bytes=1,
        sha256="b" * 64,
    )
    session.add_all([ui_snapshot, api_snapshot])
    session.flush()
    campaign = AssessmentCampaign(application_id=app.id, name="mapping")
    session.add(campaign)
    session.flush()
    members = [
        CampaignSourceMember(
            campaign_id=campaign.id,
            component_id=ui.id,
            snapshot_id=ui_snapshot.id,
            sast_run_id=9101,
            status="completed",
        ),
        CampaignSourceMember(
            campaign_id=campaign.id,
            component_id=api.id,
            snapshot_id=api_snapshot.id,
            sast_run_id=9102,
            status="completed",
        ),
    ]
    session.add_all(members)
    session.flush()
    return campaign.id, members


def _fact(
    *,
    run_id: int,
    component_id: int,
    fact_type: str,
    location: str,
    fingerprint: str,
    name: str | None = None,
    method: str | None = None,
    path: str | None = None,
    detail: dict | None = None,
) -> ComponentFact:
    return ComponentFact(
        sast_run_id=run_id,
        component_id=component_id,
        fact_type=fact_type,
        method=method,
        path=path,
        name=name,
        detail_json=json.dumps(detail or {}),
        evidence_location=location,
        fingerprint=fingerprint,
    )


def _seed_backend_lead(session: Session) -> ScanLead:
    lead = ScanLead(
        producer_run_id=9102,
        producer_run_type="sast",
        title="Unsafe order price",
        category="A04",
        severity="high",
        confidence=0.9,
        location="api/orders.py:20",
        suggested_endpoint="POST /api/orders",
        reportable=True,
    )
    session.add(lead)
    session.flush()
    return lead


def test_wrapper_derived_frontend_path_requires_semantic_edges(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        campaign_id, members = _seed_source_members(session)
        ui_component = members[0].component_id
        api_component = members[1].component_id
        lead = _seed_backend_lead(session)
        session.add_all(
            [
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_route",
                    path="/checkout",
                    location="ui/routes.tsx:1",
                    fingerprint="route",
                    detail={"trigger_locations": ["ui/checkout.tsx:12"]},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_action",
                    name="Submit order",
                    location="ui/checkout.tsx:12",
                    fingerprint="action",
                    detail={"handler_locations": ["ui/checkout.tsx:20"]},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="handler",
                    name="submitOrder",
                    location="ui/checkout.tsx:20",
                    fingerprint="handler",
                    detail={"trigger_locations": ["ui/checkout.tsx:35"]},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="http_call",
                    method="POST",
                    path="/api/orders",
                    location="ui/checkout.tsx:35",
                    fingerprint="browser-call",
                    detail={"request_role": "browser_request"},
                ),
                _fact(
                    run_id=9102,
                    component_id=api_component,
                    fact_type="route",
                    method="POST",
                    path="/api/orders",
                    location="api/routes.py:10",
                    fingerprint="server-route",
                ),
            ]
        )
        session.flush()
        _build_component_connections(session, campaign_id, members, None)
        edges = session.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == campaign_id
            )
        ).all()
        paths = trace_lead_paths(session, campaign_id, lead, max_edges=8)

    assert {edge.edge_kind for edge in edges} == {
        "contains",
        "triggers",
        "dispatches",
        "calls",
        "reaches",
    }
    assert len(paths) == 1
    assert paths[0].complete is True
    assert [fact.fact_type for fact in paths[0].facts] == [
        "ui_action",
        "handler",
        "http_call",
        "route",
        "lead_anchor",
    ]


def test_action_root_only_schema_v3_trace_is_a_frontend_mapping():
    assert _has_frontend_trace(
        {
            "schema_version": 3,
            "perspective": "frontend",
            "frontend_surface": {
                "ui_route": None,
                "ui_action": {"kind": "ui_action"},
                "browser_request": {"kind": "http_call"},
            },
        }
    )


def test_same_file_co_location_does_not_create_frontend_mapping(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        campaign_id, members = _seed_source_members(session)
        ui_component = members[0].component_id
        api_component = members[1].component_id
        lead = _seed_backend_lead(session)
        session.add_all(
            [
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_route",
                    path="/checkout",
                    location="ui/checkout.tsx:1",
                    fingerprint="co-located-route",
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_action",
                    name="Submit order",
                    location="ui/checkout.tsx:12",
                    fingerprint="co-located-action",
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="handler",
                    name="submitOrder",
                    location="ui/checkout.tsx:20",
                    fingerprint="co-located-handler",
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="http_call",
                    method="POST",
                    path="/api/orders",
                    location="ui/checkout.tsx:35",
                    fingerprint="co-located-call",
                    detail={"request_role": "browser_request"},
                ),
                _fact(
                    run_id=9102,
                    component_id=api_component,
                    fact_type="route",
                    method="POST",
                    path="/api/orders",
                    location="api/routes.py:10",
                    fingerprint="co-located-server-route",
                ),
            ]
        )
        session.flush()
        _build_component_connections(session, campaign_id, members, None)
        edges = session.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == campaign_id
            )
        ).all()
        paths = trace_lead_paths(session, campaign_id, lead, max_edges=8)

    assert not any(
        edge.edge_kind in {"contains", "triggers", "dispatches"} for edge in edges
    )
    assert all(not path.complete for path in paths)


def test_inline_callback_direct_request_forms_complete_action_root_trace(
    isolated_db_engine,
):
    with Session(isolated_db_engine) as session:
        campaign_id, members = _seed_source_members(session)
        ui_component = members[0].component_id
        api_component = members[1].component_id
        lead = _seed_backend_lead(session)
        session.add_all(
            [
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_action",
                    name="Place order",
                    location="ui/page.js:4",
                    fingerprint="inline-action",
                    detail={"trigger": "click"},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="http_call",
                    method="POST",
                    path="/api/orders",
                    location="ui/page.js:4",
                    fingerprint="inline-request",
                    detail={
                        "request_role": "browser_request",
                        "supporting_locations": ["ui/page.js:4"],
                    },
                ),
                _fact(
                    run_id=9102,
                    component_id=api_component,
                    fact_type="route",
                    method="POST",
                    path="/api/orders",
                    location="api/routes.py:10",
                    fingerprint="inline-server-route",
                ),
            ]
        )
        session.flush()
        _build_component_connections(session, campaign_id, members, None)
        paths = trace_lead_paths(session, campaign_id, lead, max_edges=8)

    assert len(paths) == 1
    assert paths[0].complete is True
    assert paths[0].facts[0].fact_type == "ui_action"
    assert paths[0].facts[1].fact_type == "http_call"


def test_multiple_routes_and_actions_do_not_form_cartesian_edges(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        campaign_id, members = _seed_source_members(session)
        ui_component = members[0].component_id
        session.add_all(
            [
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_route",
                    path="/orders",
                    location="ui/routes.jsx:1",
                    fingerprint="orders-route",
                    detail={"supporting_locations": ["ui/routes.jsx:1"]},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_route",
                    path="/profile",
                    location="ui/routes.jsx:2",
                    fingerprint="profile-route",
                    detail={"supporting_locations": ["ui/routes.jsx:2"]},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_action",
                    name="Load orders",
                    location="ui/routes.jsx:4",
                    fingerprint="orders-action",
                    detail={
                        "handler_locations": ["ui/routes.jsx:6"],
                        "route_locations": ["ui/routes.jsx:1", "ui/routes.jsx:2"],
                    },
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_action",
                    name="Load profile",
                    location="ui/routes.jsx:5",
                    fingerprint="profile-action",
                    detail={
                        "handler_locations": ["ui/routes.jsx:7"],
                        "route_locations": ["ui/routes.jsx:1", "ui/routes.jsx:2"],
                    },
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="handler",
                    name="loadOrders",
                    location="ui/routes.jsx:6",
                    fingerprint="orders-handler",
                    detail={"trigger_locations": ["ui/routes.jsx:8"]},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="handler",
                    name="loadProfile",
                    location="ui/routes.jsx:7",
                    fingerprint="profile-handler",
                    detail={"trigger_locations": ["ui/routes.jsx:9"]},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="http_call",
                    method="GET",
                    path="/api/orders",
                    location="ui/routes.jsx:8",
                    fingerprint="orders-call",
                    detail={
                        "request_role": "browser_request",
                        "handler_locations": ["ui/routes.jsx:6"],
                    },
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="http_call",
                    method="GET",
                    path="/api/profile",
                    location="ui/routes.jsx:9",
                    fingerprint="profile-call",
                    detail={
                        "request_role": "browser_request",
                        "handler_locations": ["ui/routes.jsx:7"],
                    },
                ),
            ]
        )
        session.flush()
        _build_component_connections(session, campaign_id, members, None)
        edges = session.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == campaign_id,
                ComponentConnection.edge_kind == "contains",
            )
        ).all()

    assert edges == []


def test_native_html_form_action_can_form_complete_trace(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        campaign_id, members = _seed_source_members(session)
        ui_component = members[0].component_id
        api_component = members[1].component_id
        lead = _seed_backend_lead(session)
        session.add_all(
            [
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="ui_action",
                    name="Place order",
                    location="ui/order.html:2",
                    fingerprint="form-action",
                    detail={"trigger": "submit", "form_action": "/api/orders"},
                ),
                _fact(
                    run_id=9101,
                    component_id=ui_component,
                    fact_type="http_call",
                    method="POST",
                    path="/api/orders",
                    location="ui/order.html:2",
                    fingerprint="form-request",
                    detail={
                        "request_role": "browser_request",
                        "supporting_locations": ["ui/order.html:2"],
                    },
                ),
                _fact(
                    run_id=9102,
                    component_id=api_component,
                    fact_type="route",
                    method="POST",
                    path="/api/orders",
                    location="api/routes.py:10",
                    fingerprint="form-server-route",
                ),
            ]
        )
        session.flush()
        _build_component_connections(session, campaign_id, members, None)
        paths = trace_lead_paths(session, campaign_id, lead, max_edges=8)

    assert len(paths) == 1
    assert paths[0].complete is True
    assert paths[0].facts[0].fact_type == "ui_action"


def test_node_server_side_fetch_cannot_form_frontend_path(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        campaign_id, members = _seed_source_members(session)
        api_component = members[1].component_id
        lead = _seed_backend_lead(session)
        session.add(
            _fact(
                run_id=9102,
                component_id=api_component,
                fact_type="http_call",
                method="POST",
                path="/api/orders",
                location="server/index.js:4",
                fingerprint="node-server-fetch",
                detail={"request_role": "server_egress"},
            )
        )
        session.add(
            _fact(
                run_id=9102,
                component_id=api_component,
                fact_type="route",
                method="POST",
                path="/api/orders",
                location="api/routes.py:10",
                fingerprint="node-ingress",
            )
        )
        session.flush()
        _build_component_connections(session, campaign_id, members, None)
        paths = trace_lead_paths(session, campaign_id, lead, max_edges=8)

    assert paths == []
