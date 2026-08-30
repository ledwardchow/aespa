"""End-to-end backend contract tests for the campaign review UI:

1. GET .../mappings includes enough lead context to review a proposal
   without a second round-trip (title/description/severity/location/
   producer, plus contributing component ids/names for both SAST-produced
   and campaign-produced cross-repo leads).
2. GET .../activity replays persisted campaign AgentLog/ScanLog rows in one
   stable chronological feed, isolated from every other run kind.
3. GET .../findings resolves each finding's contributing component(s)
   through its linked ScanLead — never guessed when there is no link.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from aespa.models import (
    AgentLog,
    ApiCollection,
    ApiTestRun,
    Application,
    ApplicationComponent,
    ApplicationTarget,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentSnapshot,
    LeadTargetMapping,
    ScanFinding,
    ScanLead,
    ScanLeadComponentProvenance,
    ScanLog,
    Site,
    TestRun,
)
from aespa.schemas import CampaignFindingRow

_UTC = timezone.utc


def test_campaign_finding_rows_merge_cross_repo_instances():
    from aespa.api.applications import _merge_campaign_finding_rows

    first = CampaignFindingRow(
        finding_id=10,
        reference="CF-10",
        run_reference="F-10",
        target_type="api_collection",
        target_run_id=101,
        component_id=None,
        component_name=None,
        target_name="orders-api",
        title="Cross-repository authorization issue",
        affected_url="https://api.test/orders/1",
        severity="high",
        status="confirmed",
    )
    second = CampaignFindingRow(
        finding_id=11,
        reference="CF-11",
        run_reference="F-11",
        target_type="api_collection",
        target_run_id=102,
        component_id=None,
        component_name=None,
        target_name="orders-api",
        title="Cross-repository authorization issue",
        affected_url="https://api.test/orders/2",
        severity="high",
        status="confirmed",
    )

    rows = _merge_campaign_finding_rows(
        [
            (first, ("cross-repository", "source-1", 2, "A01", "api_collection")),
            (second, ("cross-repository", "source-1", 2, "A01", "api_collection")),
        ]
    )

    assert len(rows) == 1
    assert rows[0].finding_id == 10
    assert [item["finding_id"] for item in json.loads(rows[0].merged_instances)] == [11]


def _seed_two_component_application(session: Session) -> dict:
    app = Application(name="Acme")
    session.add(app)
    session.flush()

    ui = ApplicationComponent(application_id=app.id, name="checkout-ui")
    api = ApplicationComponent(application_id=app.id, name="orders-api")
    session.add(ui)
    session.add(api)
    session.flush()

    ui_snapshot = ComponentSnapshot(
        component_id=ui.id,
        filename="ui.zip",
        stored_path="/x/ui.zip",
        size_bytes=1,
        sha256="a" * 64,
    )
    api_snapshot = ComponentSnapshot(
        component_id=api.id,
        filename="api.zip",
        stored_path="/x/api.zip",
        size_bytes=1,
        sha256="b" * 64,
    )
    session.add(ui_snapshot)
    session.add(api_snapshot)

    collection = ApiCollection(name="Orders API", base_url="https://api.acme.test")
    session.add(collection)
    session.flush()
    target = ApplicationTarget(
        application_id=app.id, target_type="api_collection", target_id=collection.id
    )
    session.add(target)

    campaign = AssessmentCampaign(application_id=app.id, name="release-1")
    session.add(campaign)
    session.flush()

    ui_sast_run_id = 9001
    api_sast_run_id = 9002
    session.add(
        CampaignSourceMember(
            campaign_id=campaign.id,
            component_id=ui.id,
            snapshot_id=ui_snapshot.id,
            sast_run_id=ui_sast_run_id,
            status="completed",
        )
    )
    session.add(
        CampaignSourceMember(
            campaign_id=campaign.id,
            component_id=api.id,
            snapshot_id=api_snapshot.id,
            sast_run_id=api_sast_run_id,
            status="completed",
        )
    )
    session.add(
        CampaignTargetMember(
            campaign_id=campaign.id, target_id=target.id, target_type="api_collection"
        )
    )
    session.commit()

    return {
        "application_id": app.id,
        "campaign_id": campaign.id,
        "ui_component_id": ui.id,
        "api_component_id": api.id,
        "target_id": target.id,
        "ui_sast_run_id": ui_sast_run_id,
        "api_sast_run_id": api_sast_run_id,
    }


# ── Gap 1: enriched lead-target mappings ─────────────────────────────────────


def test_mappings_endpoint_includes_lead_context_for_sast_lead(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_two_component_application(s)
        lead = ScanLead(
            producer_run_id=ctx["ui_sast_run_id"],
            producer_run_type="sast",
            title="Missing authorization on order creation",
            description="The endpoint does not check ownership before returning data.",
            severity="high",
            location="src/checkout.js:42",
            reportable=True,
        )
        s.add(lead)
        s.flush()
        mapping = LeadTargetMapping(
            campaign_id=ctx["campaign_id"],
            lead_id=lead.id,
            target_id=ctx["target_id"],
            target_type="api_collection",
            score=0.8,
            rationale="Exact method/path match",
        )
        s.add(mapping)
        s.commit()
        app_id, campaign_id = ctx["application_id"], ctx["campaign_id"]

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/mappings")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    row = rows[0]

    # Original mapping fields still present (backward compatible).
    assert row["target_id"] == ctx["target_id"]
    assert row["score"] == 0.8

    # New lead-context fields.
    assert row["lead_title"] == "Missing authorization on order creation"
    assert "ownership" in row["lead_description"]
    assert row["lead_severity"] == "high"
    assert row["lead_location"] == "src/checkout.js:42"
    assert row["lead_producer_run_type"] == "sast"
    assert row["lead_producer_run_id"] == ctx["ui_sast_run_id"]
    assert row["component_ids"] == [ctx["ui_component_id"]]
    assert row["component_names"] == ["checkout-ui"]


def test_mappings_endpoint_includes_all_contributing_components_for_cross_repo_lead(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_two_component_application(s)
        cross_lead = ScanLead(
            producer_run_id=ctx["campaign_id"],
            producer_run_type="campaign",
            title="Cross-repository: unauthenticated order lookup",
            description="checkout-ui reaches orders-api's /orders route directly.",
            severity="high",
            location="src/checkout.js:42 -> src/routes.py:10",
            reportable=True,
        )
        s.add(cross_lead)
        s.flush()
        s.add(
            ScanLeadComponentProvenance(
                scan_lead_id=cross_lead.id,
                component_id=ctx["ui_component_id"],
                role="primary",
            )
        )
        s.add(
            ScanLeadComponentProvenance(
                scan_lead_id=cross_lead.id,
                component_id=ctx["api_component_id"],
                role="contributing",
            )
        )
        mapping = LeadTargetMapping(
            campaign_id=ctx["campaign_id"],
            lead_id=cross_lead.id,
            target_id=ctx["target_id"],
            target_type="api_collection",
            score=0.7,
        )
        s.add(mapping)
        s.commit()
        app_id, campaign_id = ctx["application_id"], ctx["campaign_id"]
        ui_id, api_id = ctx["ui_component_id"], ctx["api_component_id"]

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/mappings")
    assert resp.status_code == 200, resp.text
    row = resp.json()[0]

    assert row["lead_producer_run_type"] == "campaign"
    assert row["lead_producer_run_id"] == ctx["campaign_id"]
    assert set(row["component_ids"]) == {ui_id, api_id}
    assert set(row["component_names"]) == {"checkout-ui", "orders-api"}


def test_mappings_endpoint_is_bounded_query_count_regardless_of_row_count(
    client, isolated_db_engine
):
    """Avoid N+1: a handful of mappings must not multiply query count."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_two_component_application(s)
        for i in range(5):
            lead = ScanLead(
                producer_run_id=ctx["ui_sast_run_id"],
                producer_run_type="sast",
                title=f"Lead {i}",
                location=f"src/checkout.js:{i}",
                reportable=True,
            )
            s.add(lead)
            s.flush()
            s.add(
                LeadTargetMapping(
                    campaign_id=ctx["campaign_id"],
                    lead_id=lead.id,
                    target_id=ctx["target_id"],
                    target_type="api_collection",
                    score=0.5,
                )
            )
        s.commit()
        campaign_id = ctx["campaign_id"]

    from aespa.db import get_engine

    query_count = 0
    real_exec = Session.exec

    def _counting_exec(self, *args, **kwargs):
        nonlocal query_count
        query_count += 1
        return real_exec(self, *args, **kwargs)

    import aespa.api.applications as applications_module  # noqa: F401

    Session.exec = _counting_exec
    try:
        with Session(get_engine()) as s:
            query_count = 0
            resp_rows = applications_module._enrich_mappings(
                s,
                campaign_id,
                s.exec(
                    select(LeadTargetMapping).where(
                        LeadTargetMapping.campaign_id == campaign_id
                    )
                ).all(),
            )
    finally:
        Session.exec = real_exec

    assert len(resp_rows) == 5
    # Bounded regardless of mapping count: leads, source-members,
    # provenance, components — a handful of queries, not one per mapping.
    assert query_count <= 6


# ── Gap 2: persisted campaign activity ───────────────────────────────────────


def test_activity_endpoint_replays_persisted_history_in_order(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as s:
        app = Application(name="ActivityApp")
        s.add(app)
        s.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="c1")
        s.add(campaign)
        s.flush()
        campaign_id = campaign.id
        app_id = app.id

        base = datetime.now(_UTC)
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="campaign",
                created_at=base,
                agent_id="campaign",
                role="Campaign Orchestrator",
                status="active",
                current_task="Starting source-code scans…",
                outcome=None,
            )
        )
        s.add(
            ScanLog(
                test_run_id=campaign_id,
                run_kind="campaign",
                created_at=base + timedelta(seconds=1),
                phase="sast_running",
                status="running",
                message="Scanning checkout-ui",
            )
        )
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="campaign",
                created_at=base + timedelta(seconds=2),
                agent_id="campaign",
                role="Campaign Orchestrator",
                status="idle",
                current_task="Awaiting lead-target review",
                outcome=None,
            )
        )
        s.commit()

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/activity")
    assert resp.status_code == 200, resp.text
    entries = resp.json()
    assert len(entries) == 3

    # Stable chronological order.
    timestamps = [e["timestamp"] for e in entries]
    assert timestamps == sorted(timestamps)

    assert entries[0]["type"] == "agent_status"
    assert entries[0]["role"] == "Campaign Orchestrator"
    assert entries[0]["task"] == "Starting source-code scans…"
    assert entries[0]["status"] == "active"

    assert entries[1]["type"] == "scanner_phase"
    assert entries[1]["phase"] == "sast_running"
    assert entries[1]["message"] == "Scanning checkout-ui"

    assert entries[2]["outcome"] is None
    assert entries[2]["task"] == "Awaiting lead-target review"


def test_activity_endpoint_is_isolated_from_other_run_kinds(client, isolated_db_engine):
    with Session(isolated_db_engine) as s:
        app = Application(name="IsolationApp")
        s.add(app)
        s.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="c1")
        s.add(campaign)
        s.flush()
        campaign_id = campaign.id
        app_id = app.id

        # A genuine campaign-tagged row.
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="campaign",
                agent_id="campaign",
                role="Campaign Orchestrator",
                status="active",
                current_task="real campaign row",
            )
        )
        # Adversarial: rows that share the exact same numeric id but are
        # tagged as a different run kind — must never leak into the
        # campaign's activity feed.
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="web",
                agent_id="scanner",
                role="Test Lead",
                status="active",
                current_task="unrelated web row",
            )
        )
        s.add(
            ScanLog(
                test_run_id=campaign_id,
                run_kind="api",
                phase="thinking_step",
                status="running",
                message="unrelated api row",
            )
        )
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="sast",
                agent_id="sast-scanner",
                role="SAST Analyst",
                status="active",
                current_task="unrelated sast row",
            )
        )
        s.commit()

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/activity")
    assert resp.status_code == 200, resp.text
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["task"] == "real campaign row"


def test_activity_endpoint_returns_empty_list_when_no_history(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as s:
        app = Application(name="EmptyApp")
        s.add(app)
        s.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="c1")
        s.add(campaign)
        s.commit()
        app_id, campaign_id = app.id, campaign.id

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/activity")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Gap 3: findings component provenance ─────────────────────────────────────


def test_findings_resolves_component_for_sast_produced_lead(client, isolated_db_engine):
    with Session(isolated_db_engine) as s:
        ctx = _seed_two_component_application(s)
        api_run = ApiTestRun(collection_id=1, name="orders-api dast run")
        s.add(api_run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == ctx["campaign_id"]
            )
        ).first()
        member.api_test_run_id = api_run.id
        s.add(member)

        finding = ScanFinding(
            api_test_run_id=api_run.id,
            owasp_category="API1",
            severity="high",
            title="Broken object level authorization",
            description="desc",
        )
        s.add(finding)
        s.flush()

        lead = ScanLead(
            producer_run_id=ctx["ui_sast_run_id"],
            producer_run_type="sast",
            title="Missing authorization on order creation",
            location="src/checkout.js:42",
            imported_into_run_type="api",
            imported_into_run_id=api_run.id,
            linked_finding_id=finding.id,
            reportable=True,
        )
        s.add(lead)
        s.commit()
        app_id, campaign_id = ctx["application_id"], ctx["campaign_id"]
        ui_id = ctx["ui_component_id"]

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/findings")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["component_id"] == ui_id
    assert row["component_name"] == "checkout-ui"
    assert row["component_ids"] == [ui_id]
    assert row["component_names"] == ["checkout-ui"]


def test_findings_resolves_components_for_campaign_cross_repo_lead(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_two_component_application(s)
        api_run = ApiTestRun(collection_id=1, name="orders-api dast run")
        s.add(api_run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == ctx["campaign_id"]
            )
        ).first()
        member.api_test_run_id = api_run.id
        s.add(member)

        finding = ScanFinding(
            api_test_run_id=api_run.id,
            owasp_category="API1",
            severity="high",
            title="Cross-repository unauthenticated order lookup",
            description="desc",
        )
        s.add(finding)
        s.flush()

        original = ScanLead(
            producer_run_id=ctx["campaign_id"],
            producer_run_type="campaign",
            title="Cross-repository: unauthenticated order lookup",
            location="src/checkout.js:42 -> src/routes.py:10",
            fingerprint="cross-fp-1",
            reportable=True,
        )
        s.add(original)
        s.flush()
        s.add(
            ScanLeadComponentProvenance(
                scan_lead_id=original.id,
                component_id=ctx["ui_component_id"],
                role="primary",
            )
        )
        s.add(
            ScanLeadComponentProvenance(
                scan_lead_id=original.id,
                component_id=ctx["api_component_id"],
                role="contributing",
            )
        )
        # The copy imported into the dynamic run — this is what
        # linked_finding_id actually points at, mirroring copy_lead_to_run.
        copy = ScanLead(
            producer_run_id=ctx["campaign_id"],
            producer_run_type="campaign",
            title=original.title,
            location=original.location,
            fingerprint="cross-fp-1",
            imported_into_run_type="api",
            imported_into_run_id=api_run.id,
            linked_finding_id=finding.id,
            reportable=True,
        )
        s.add(copy)
        s.commit()
        app_id, campaign_id = ctx["application_id"], ctx["campaign_id"]
        ui_id, api_id = ctx["ui_component_id"], ctx["api_component_id"]

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/findings")
    assert resp.status_code == 200, resp.text
    row = resp.json()[0]
    assert set(row["component_ids"]) == {ui_id, api_id}
    assert set(row["component_names"]) == {"checkout-ui", "orders-api"}
    # Comma-joined single string form stays backward compatible.
    assert "checkout-ui" in row["component_name"]
    assert "orders-api" in row["component_name"]


def test_findings_never_guesses_component_without_a_linked_lead(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as s:
        ctx = _seed_two_component_application(s)
        api_run = ApiTestRun(collection_id=1, name="orders-api dast run")
        s.add(api_run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember).where(
                CampaignTargetMember.campaign_id == ctx["campaign_id"]
            )
        ).first()
        member.api_test_run_id = api_run.id
        s.add(member)

        # A finding discovered independently by the dynamic scan — no
        # ScanLead links to it at all.
        finding = ScanFinding(
            api_test_run_id=api_run.id,
            owasp_category="API1",
            severity="medium",
            title="Verbose error message",
            description="desc",
        )
        s.add(finding)
        s.commit()
        app_id, campaign_id = ctx["application_id"], ctx["campaign_id"]

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/findings")
    assert resp.status_code == 200, resp.text
    row = resp.json()[0]
    assert row["component_id"] is None
    assert row["component_name"] is None
    assert row["component_ids"] == []
    assert row["component_names"] == []


def test_findings_resolves_component_for_web_target_member(client, isolated_db_engine):
    """The same resolution must work for a web (TestRun) target, not just API."""
    with Session(isolated_db_engine) as s:
        ctx = _seed_two_component_application(s)
        site = Site(name="Portal", base_url="http://portal.test")
        s.add(site)
        s.flush()
        web_target = ApplicationTarget(
            application_id=ctx["application_id"], target_type="site", target_id=site.id
        )
        s.add(web_target)
        s.flush()
        s.add(
            CampaignTargetMember(
                campaign_id=ctx["campaign_id"],
                target_id=web_target.id,
                target_type="site",
            )
        )
        web_run = TestRun(site_id=site.id, name="web dast run")
        s.add(web_run)
        s.flush()
        member = s.exec(
            select(CampaignTargetMember)
            .where(CampaignTargetMember.campaign_id == ctx["campaign_id"])
            .where(CampaignTargetMember.target_id == web_target.id)
        ).first()
        member.test_run_id = web_run.id
        s.add(member)

        finding = ScanFinding(
            test_run_id=web_run.id,
            owasp_category="A01",
            severity="high",
            title="IDOR on order page",
            description="desc",
        )
        s.add(finding)
        s.flush()
        lead = ScanLead(
            producer_run_id=ctx["ui_sast_run_id"],
            producer_run_type="sast",
            title="Missing authorization",
            location="src/checkout.js:42",
            imported_into_run_type="web",
            imported_into_run_id=web_run.id,
            linked_finding_id=finding.id,
            reportable=True,
        )
        s.add(lead)
        s.commit()
        app_id, campaign_id = ctx["application_id"], ctx["campaign_id"]
        ui_id = ctx["ui_component_id"]

    resp = client.get(f"/api/applications/{app_id}/campaigns/{campaign_id}/findings")
    assert resp.status_code == 200, resp.text
    web_rows = [r for r in resp.json() if r["target_type"] == "site"]
    assert len(web_rows) == 1
    assert web_rows[0]["component_ids"] == [ui_id]
    assert web_rows[0]["component_names"] == ["checkout-ui"]


# ── Gap 4 (finding 2): cursor-safe activity replay ───────────────────────────


def test_activity_stream_generator_replays_then_follows_without_gap(
    isolated_db_engine,
):
    """The poll-based generator must deliver every persisted row exactly
    once, in order, whether it existed before the stream started or was
    committed while the stream was already running — proving there is no
    fetch→subscribe gap window (there is no subscribe step at all)."""
    import asyncio

    import anyio

    from aespa.api.applications import _stream_campaign_activity

    with Session(isolated_db_engine) as s:
        app = Application(name="StreamApp")
        s.add(app)
        s.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="c1")
        s.add(campaign)
        s.flush()
        campaign_id = campaign.id

        base = datetime.now(_UTC)
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="campaign",
                created_at=base,
                agent_id="campaign",
                role="Campaign Orchestrator",
                status="active",
                current_task="Starting source-code scans…",
                outcome=None,
            )
        )
        s.commit()

    async def _run():
        gen = _stream_campaign_activity(campaign_id, 0, 0, poll_seconds=0.02)
        try:
            # First message: the row that already existed before the stream
            # started (the "replay" half).
            first = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
            assert "id: 1.0" in first
            assert "Starting source-code scans" in first

            # Commit a brand-new row concurrently, simulating a write that
            # happens *after* the stream has already begun polling — this is
            # exactly the moment a fetch→subscribe design could lose an
            # event; a poll-based design cannot, because it never stops
            # re-querying.
            with Session(isolated_db_engine) as s:
                s.add(
                    ScanLog(
                        test_run_id=campaign_id,
                        run_kind="campaign",
                        created_at=datetime.now(_UTC),
                        phase="sast_running",
                        status="running",
                        message="Scanning checkout-ui",
                    )
                )
                s.commit()

            # Keep reading until the new row shows up (skipping heartbeats);
            # bounded so a real regression fails fast instead of hanging.
            second = None
            for _ in range(20):
                candidate = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
                if candidate.strip() != ": heartbeat":
                    second = candidate
                    break
            assert second is not None, "new row was never observed"
            assert "id: 1.1" in second
            assert "Scanning checkout-ui" in second
        finally:
            await gen.aclose()

    anyio.run(_run)


def test_activity_stream_resumes_from_supplied_cursor_without_duplicating(
    isolated_db_engine,
):
    """Reconnecting with a prior ``event_id`` as the cursor must never
    re-deliver rows already seen."""
    import asyncio

    import anyio

    from aespa.api.applications import _stream_campaign_activity

    with Session(isolated_db_engine) as s:
        app = Application(name="StreamApp2")
        s.add(app)
        s.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="c1")
        s.add(campaign)
        s.flush()
        campaign_id = campaign.id

        base = datetime.now(_UTC)
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="campaign",
                created_at=base,
                agent_id="campaign",
                role="Campaign Orchestrator",
                status="active",
                current_task="first",
                outcome=None,
            )
        )
        s.add(
            AgentLog(
                test_run_id=campaign_id,
                run_kind="campaign",
                created_at=base + timedelta(seconds=1),
                agent_id="campaign",
                role="Campaign Orchestrator",
                status="active",
                current_task="second",
                outcome=None,
            )
        )
        s.commit()

    async def _run():
        # Resume as if the client already saw agent_log id=1 ("first").
        gen = _stream_campaign_activity(campaign_id, 1, 0, poll_seconds=0.02)
        try:
            first = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
            assert "second" in first
            assert "first" not in first
        finally:
            await gen.aclose()

    anyio.run(_run)


def test_activity_stream_http_endpoint_404s_for_unknown_campaign(client):
    """The route is registered and wired to campaign lookup before it ever
    starts streaming — an unknown campaign 404s immediately rather than
    hanging on an infinite body."""
    resp = client.get("/api/applications/1/campaigns/999999/activity/stream")
    assert resp.status_code == 404
