from __future__ import annotations

import json

from sqlmodel import Session, select

from aespa.models import (
    Application,
    ApplicationTarget,
    AssessmentCampaign,
    CampaignTargetMember,
    CampaignValidationCase,
    LeadTargetMapping,
    SastRun,
    ScanLead,
    Site,
    TestRun,
)
from aespa.services import campaign_validation_cases as cases_svc
from aespa.services.scan_leads import update_lead


def _seed_web_case(engine, *, path: dict):
    with Session(engine) as session:
        app = Application(name="Insurance")
        site = Site(name="FACE", base_url="https://face.test")
        sast_run = SastRun(name="backend", status="completed")
        session.add(app)
        session.add(site)
        session.add(sast_run)
        session.flush()
        target = ApplicationTarget(
            application_id=app.id,
            target_type="site",
            target_id=site.id,
        )
        campaign = AssessmentCampaign(application_id=app.id, name="validation")
        child_run = TestRun(site_id=site.id, name="FACE validation")
        session.add(target)
        session.add(campaign)
        session.add(child_run)
        session.flush()
        member = CampaignTargetMember(
            campaign_id=campaign.id,
            target_id=target.id,
            target_type="site",
            test_run_id=child_run.id,
        )
        source = ScanLead(
            producer_run_type="sast",
            producer_run_id=sast_run.id,
            title="Quote accepts an invalid age",
            description="The backend does not enforce the age rule.",
            category="business_logic",
            severity="high",
            confidence=0.9,
            location="quotes.py:40",
            fingerprint="quote-age",
            reportable=True,
            attack_path_json=json.dumps(path),
        )
        session.add(member)
        session.add(source)
        session.flush()
        mapping = LeadTargetMapping(
            campaign_id=campaign.id,
            lead_id=source.id,
            target_id=target.id,
            target_type="site",
            score=1.0,
            status="approved",
            path_json=json.dumps(path),
            approved_attack_path_json=json.dumps(path),
            final_attack_path_json=json.dumps(path),
        )
        session.add(mapping)
        session.commit()
        return campaign.id, member.id, child_run.id, mapping.id


def _v3_path() -> dict:
    return {
        "schema_version": 3,
        "perspective": "frontend",
        "source_finding": {"lead_id": 1},
        "frontend_surface": {
            "ui_route": {"kind": "ui_route", "path": "/quotes/motor"},
            "ui_action": {
                "kind": "ui_action",
                "label": "Submit quote",
                "action_kind": "click",
            },
            "browser_request": {
                "kind": "http_call",
                "request_role": "browser_request",
                "method": "POST",
                "path": "/api/quotes/motor",
            },
        },
        "service_hops": [
            {
                "kind": "http_call",
                "request_role": "server_egress",
                "method": "POST",
                "path": "/api/customer/quotes/motor",
            }
        ],
        "vulnerability_anchor": {"location": "quotes.py:40"},
        "static_trace": {"status": "complete", "proof_gaps": []},
        "validation_assertion": {
            "claim": "Invalid ages are accepted",
            "mutation_points": ["age"],
            "secure_outcome": "The quote is rejected",
            "vulnerable_outcome": "The quote is created",
            "prerequisites": [],
        },
    }


def test_unresolved_web_mapping_never_enters_child_queue(isolated_db_engine):
    legacy_server_path = {
        "schema_version": 2,
        "perspective": "frontend",
        "frontend_entrypoint": {
            "method": "POST",
            "path": "/api/customer/quotes/motor",
            "request_role": "server_egress",
        },
    }
    campaign_id, member_id, run_id, _mapping_id = _seed_web_case(
        isolated_db_engine, path=legacy_server_path
    )

    resolution = cases_svc.resolve_cases_for_web_target(
        campaign_id,
        member_id,
        run_id,
        {"crawl_status": "completed", "pages": [], "actions": [], "requests": []},
    )
    compilation = cases_svc.compile_runnable_cases(campaign_id, member_id)

    assert resolution.counts == {"missing_frontend_hop": 1}
    assert compilation.copied_lead_ids == []
    with Session(isolated_db_engine) as session:
        copied = session.exec(
            select(ScanLead).where(ScanLead.imported_into_run_id == run_id)
        ).all()
    assert copied == []


def test_resolved_case_compiles_once_and_records_execution_evidence(
    isolated_db_engine,
):
    campaign_id, member_id, run_id, mapping_id = _seed_web_case(
        isolated_db_engine, path=_v3_path()
    )
    context = {
        "crawl_status": "completed",
        "pages": [{"id": 10, "url": "https://face.test/quotes/motor"}],
        "actions": [
            {
                "id": 20,
                "page_id": 10,
                "label": "Submit quote",
                "action_kind": "click",
                "interaction_id": "submit-1",
            }
        ],
        "requests": [
            {
                "id": 30,
                "page_id": 10,
                "method": "POST",
                "url": "https://face.test/api/quotes/motor",
                "interaction_id": "submit-1",
                "session_label": "configured_primary",
                "fields": ["age"],
            }
        ],
    }

    resolution = cases_svc.resolve_cases_for_web_target(
        campaign_id, member_id, run_id, context
    )
    first = cases_svc.compile_runnable_cases(campaign_id, member_id)
    second = cases_svc.compile_runnable_cases(campaign_id, member_id)

    assert resolution.counts == {"resolved": 1}
    assert len(first.copied_lead_ids) == 1
    assert second.copied_lead_ids == first.copied_lead_ids
    copied_id = first.copied_lead_ids[0]
    updated = update_lead(
        copied_id,
        status="dismissed",
        note="The server rejected an invalid age.",
        owner_run_type="web",
        owner_run_id=run_id,
        outcome_reason="secure_behavior_observed",
        baseline_evidence="A valid quote returned 201.",
        mutated_evidence="An invalid age returned 422.",
    )
    assert updated is not None

    with Session(isolated_db_engine) as session:
        copies = session.exec(
            select(ScanLead).where(ScanLead.imported_into_run_id == run_id)
        ).all()
        case = session.exec(
            select(CampaignValidationCase).where(
                CampaignValidationCase.mapping_id == mapping_id
            )
        ).one()
        compiled_path = json.loads(copies[0].attack_path_json)
        output = cases_svc.case_to_output(session, case)

    assert len(copies) == 1
    assert compiled_path["schema_version"] == 3
    assert compiled_path["validation_case_id"] == case.id
    assert compiled_path["live_binding"]["traffic_id"] == 30
    assert case.execution_status == "dismissed"
    assert case.outcome_reason == "secure_behavior_observed"
    assert json.loads(case.baseline_evidence_json)["summary"].startswith("A valid")
    assert output["source_lead"]["title"] == "Quote accepts an invalid age"


def test_stale_binding_removes_an_unexecuted_child_lead(isolated_db_engine):
    campaign_id, member_id, run_id, _mapping_id = _seed_web_case(
        isolated_db_engine, path=_v3_path()
    )
    matching_context = {
        "crawl_status": "completed",
        "pages": [{"id": 10, "url": "https://face.test/quotes/motor"}],
        "actions": [
            {
                "id": 20,
                "page_id": 10,
                "label": "Submit quote",
                "action_kind": "click",
                "interaction_id": "submit-1",
            }
        ],
        "requests": [
            {
                "id": 30,
                "page_id": 10,
                "method": "POST",
                "url": "https://face.test/api/quotes/motor",
                "interaction_id": "submit-1",
                "fields": ["age"],
            }
        ],
    }
    cases_svc.resolve_cases_for_web_target(
        campaign_id, member_id, run_id, matching_context
    )
    compiled = cases_svc.compile_runnable_cases(campaign_id, member_id)
    assert len(compiled.copied_lead_ids) == 1

    stale = cases_svc.resolve_cases_for_web_target(
        campaign_id,
        member_id,
        run_id,
        {
            "crawl_status": "completed",
            "pages": [{"id": 11, "url": "https://face.test/quotes/motor"}],
            "actions": [],
            "requests": [],
        },
    )

    assert stale.counts == {"static_complete": 1}
    with Session(isolated_db_engine) as session:
        copied = session.exec(
            select(ScanLead).where(ScanLead.imported_into_run_id == run_id)
        ).all()
        case = session.exec(select(CampaignValidationCase)).one()
    assert copied == []
    assert case.copied_lead_id is None
    assert case.execution_status == "not_queued"
