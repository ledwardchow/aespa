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
    ScanLead,
    ScanLeadComponentProvenance,
)
from aespa.services.correlation import (
    apply_review_decisions,
    copy_approved_mappings_for_target,
    copy_explicit_component_leads_for_target,
    correlate_campaign,
    correlate_campaign_with_llm,
)


def _seed_two_component_campaign(engine) -> dict:
    """checkout-ui calls POST /orders; orders-api exposes POST /orders with no
    recorded auth boundary. Both SAST runs are marked completed already."""
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
    assert result["connections"] == 1

    with Session(isolated_db_engine) as s:
        connections = s.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == ctx["campaign_id"]
            )
        ).all()
    assert len(connections) == 1
    connection = connections[0]
    assert connection.match_kind == "deterministic"
    assert connection.confidence >= 0.7
    assert connection.source_component_id == ctx["ui_component_id"]
    assert connection.target_component_id == ctx["api_component_id"]


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

    assert result["connections"] == 1
    with Session(isolated_db_engine) as session:
        connection = session.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == ctx["campaign_id"]
            )
        ).one()
        assert connection.match_kind == "llm_assisted"
        assert connection.confidence == 0.88


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


def test_explicit_target_component_copies_its_own_sast_leads_without_review(
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
    assert own_mapping is None
    copied = copy_explicit_component_leads_for_target(
        ctx["campaign_id"], ctx["target_id"], "api", target_run_id
    )
    assert copied == 1

    with Session(isolated_db_engine) as s:
        copies = s.exec(
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == "api")
            .where(ScanLead.imported_into_run_id == target_run_id)
        ).all()
    assert len(copies) == 1
    assert copies[0].producer_run_id == 9001


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
    ctx = _seed_two_component_campaign(isolated_db_engine)
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
    # Still exactly the one genuine connection from THIS campaign's own
    # facts — the unrelated other-run fact was never considered.
    assert result["connections"] == 1
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
            (l for l in cross_leads if "Arbitrary order price acceptance" in l.title), None
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

