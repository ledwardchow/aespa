"""Deletes stay valid with SQLite foreign-key enforcement on, as in production.

The default test engine leaves ``PRAGMA foreign_keys`` off, which hides
ordering bugs.  These tests use ``fk_engine`` so a delete that leaves a
restrictive reference behind fails here the same way it fails for users.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from aespa import schemas
from aespa.db import get_session
from aespa.main import create_app
from aespa.models import (
    ApiCollection,
    ApiCredential,
    ApiDocument,
    ApiEndpoint,
    ApiEndpointTest,
    ApiTestRun,
    AssessmentCampaign,
    CampaignFindingReference,
    CampaignTargetMember,
    CrawledPage,
    Credential,
    DeepScanProbeOutcome,
    DeepScanTask,
    DiscoveredTarget,
    ProbeExecution,
    ScanFinding,
    ScannerSession,
    ScanObligation,
    Site,
    System,
    SystemTarget,
    TargetDiscovery,
    TestRun,
    TrafficEntry,
    WorkflowCoverageItem,
    WorkflowTargetReservation,
)
from aespa.services import findings as findings_svc
from aespa.services import run_cleanup
from tests.auth import authenticate_client


@pytest.fixture
def fk_client(fk_engine):
    def _override_session():
        with Session(fk_engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    with TestClient(app, raise_server_exceptions=True) as client:
        authenticate_client(client, app)
        yield client


def _web_run(s: Session) -> TestRun:
    site = Site(name="Site", base_url="http://target.local")
    s.add(site)
    s.flush()
    run = TestRun(site_id=site.id, name="Run")
    s.add(run)
    s.flush()
    return run


def _page(s: Session, run_id: int, path: str = "/a") -> CrawledPage:
    page = CrawledPage(test_run_id=run_id, url=f"http://target.local{path}")
    s.add(page)
    s.flush()
    return page


def _finding(s: Session, *, test_run_id=None, api_test_run_id=None, title="Bug"):
    finding = ScanFinding(
        test_run_id=test_run_id,
        api_test_run_id=api_test_run_id,
        title=title,
        severity="low",
        owasp_category="A01",
        description="d",
    )
    s.add(finding)
    s.flush()
    return finding


def _workflow_item(s: Session, run_id: int, *, page_id=None, finding_id=None, key="k"):
    item = WorkflowCoverageItem(
        test_run_id=run_id,
        workflow_key=key,
        name="Checkout",
        test_kind="access",
        owasp_category="A01",
        reached_page_id=page_id,
        finding_id=finding_id,
    )
    s.add(item)
    s.flush()
    return item


def _campaign_reference(s: Session, finding: ScanFinding, run: TestRun):
    system = System(name="App")
    s.add(system)
    s.flush()
    target = SystemTarget(
        system_id=system.id, target_type="site", target_id=run.site_id
    )
    s.add(target)
    s.flush()
    campaign = AssessmentCampaign(system_id=system.id, name="Campaign")
    s.add(campaign)
    s.flush()
    member = CampaignTargetMember(
        campaign_id=campaign.id,
        target_id=target.id,
        target_type="site",
        test_run_id=run.id,
    )
    s.add(member)
    s.flush()
    reference = CampaignFindingReference(
        campaign_id=campaign.id,
        finding_id=finding.id,
        target_member_id=member.id,
        public_reference="CF-001",
    )
    s.add(reference)
    s.flush()
    return campaign, reference


def test_web_run_delete_with_workflow_and_campaign_references(fk_engine):
    with Session(fk_engine) as s:
        run = _web_run(s)
        page = _page(s, run.id)
        finding = _finding(s, test_run_id=run.id)
        _workflow_item(s, run.id, page_id=page.id, finding_id=finding.id)
        _campaign_reference(s, finding, run)
        s.add(
            WorkflowTargetReservation(
                test_run_id=run.id,
                owner_key="crawl:edit",
                target_url=page.url,
                route_pattern="/a",
                example_url=page.url,
            )
        )
        s.commit()
        run_id = run.id

        run_cleanup.cascade_delete_web_run(s, run_id)
        s.commit()

        assert s.get(TestRun, run_id) is None
        assert s.exec(select(WorkflowCoverageItem)).all() == []
        assert s.exec(select(WorkflowTargetReservation)).all() == []
        assert s.exec(select(CampaignFindingReference)).all() == []


def test_campaign_delete_removes_finding_references(fk_engine):
    with Session(fk_engine) as s:
        run = _web_run(s)
        finding = _finding(s, test_run_id=run.id)
        campaign, _ = _campaign_reference(s, finding, run)
        s.commit()
        campaign_id = campaign.id

        run_cleanup.cascade_delete_campaign(s, campaign_id)
        s.commit()

        assert s.get(AssessmentCampaign, campaign_id) is None
        assert s.exec(select(CampaignFindingReference)).all() == []


def test_delete_web_finding_clears_references(fk_engine, fk_client):
    with Session(fk_engine) as s:
        run = _web_run(s)
        finding = _finding(s, test_run_id=run.id)
        item = _workflow_item(s, run.id, finding_id=finding.id)
        _campaign_reference(s, finding, run)
        s.commit()
        run_id, finding_id, item_id = run.id, finding.id, item.id

    res = fk_client.delete(f"/api/test-runs/{run_id}/findings/{finding_id}")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(ScanFinding, finding_id) is None
        assert s.get(WorkflowCoverageItem, item_id).finding_id is None
        assert s.exec(select(CampaignFindingReference)).all() == []


def test_clear_web_findings_clears_references(fk_engine, fk_client):
    with Session(fk_engine) as s:
        run = _web_run(s)
        finding = _finding(s, test_run_id=run.id)
        item = _workflow_item(s, run.id, finding_id=finding.id)
        s.commit()
        run_id, item_id = run.id, item.id

    res = fk_client.delete(f"/api/test-runs/{run_id}/findings")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(WorkflowCoverageItem, item_id).finding_id is None


def test_delete_api_finding_clears_campaign_reference(fk_engine, fk_client):
    with Session(fk_engine) as s:
        web_run = _web_run(s)
        collection = ApiCollection(name="API", base_url="http://api.local")
        s.add(collection)
        s.flush()
        api_run = ApiTestRun(collection_id=collection.id, name="API run")
        s.add(api_run)
        s.flush()
        finding = _finding(s, api_test_run_id=api_run.id)
        _campaign_reference(s, finding, web_run)
        s.commit()
        api_run_id, finding_id = api_run.id, finding.id

    res = fk_client.delete(f"/api/api-test-runs/{api_run_id}/findings/{finding_id}")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(ScanFinding, finding_id) is None
        assert s.exec(select(CampaignFindingReference)).all() == []


def test_consolidate_moves_workflow_link_to_kept_finding(fk_engine):
    with Session(fk_engine) as s:
        run = _web_run(s)
        keeper = _finding(s, test_run_id=run.id, title="Keep")
        duplicate = _finding(s, test_run_id=run.id, title="Duplicate")
        item = _workflow_item(s, run.id, finding_id=duplicate.id)
        s.commit()

        findings_svc.consolidate_findings(
            s, keeper, [duplicate], schemas.ScanFindingUpdateIn()
        )

        assert s.get(ScanFinding, duplicate.id) is None
        assert s.get(WorkflowCoverageItem, item.id).finding_id == keeper.id


def test_delete_page_clears_page_references(fk_engine, fk_client):
    with Session(fk_engine) as s:
        run = _web_run(s)
        page = _page(s, run.id)
        item = _workflow_item(s, run.id, page_id=page.id)
        s.add(
            WorkflowTargetReservation(
                test_run_id=run.id,
                owner_key="crawl:edit",
                target_url=page.url,
                route_pattern="/a",
                example_url=page.url,
            )
        )
        target = DiscoveredTarget(
            test_run_id=run.id, url="http://target.local/a", route_pattern="/a"
        )
        s.add(target)
        s.flush()
        discovery = TargetDiscovery(
            test_run_id=run.id,
            target_id=target.id,
            source_key="link",
            source_page_id=page.id,
        )
        s.add(discovery)
        s.commit()
        run_id, page_id = run.id, page.id
        item_id, discovery_id = item.id, discovery.id

    res = fk_client.delete(f"/api/test-runs/{run_id}/pages/{page_id}")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(CrawledPage, page_id) is None
        assert s.get(WorkflowCoverageItem, item_id).reached_page_id is None
        assert s.get(TargetDiscovery, discovery_id).source_page_id is None


def test_clear_crawl_state_with_workflow_page_link(fk_engine):
    from aespa.api.test_runs import _clear_crawl_state

    with Session(fk_engine) as s:
        run = _web_run(s)
        page = _page(s, run.id)
        item = _workflow_item(s, run.id, page_id=page.id)
        s.commit()

        _clear_crawl_state(s, run)
        s.commit()

        assert s.exec(select(CrawledPage)).all() == []
        assert s.exec(select(WorkflowTargetReservation)).all() == []
        assert s.get(WorkflowCoverageItem, item.id).reached_page_id is None


def test_delete_document_keeps_endpoints_and_removes_file(
    fk_engine, fk_client, tmp_path
):
    stored = tmp_path / "spec.json"
    stored.write_text("{}")
    with Session(fk_engine) as s:
        collection = ApiCollection(name="API", base_url="http://api.local")
        s.add(collection)
        s.flush()
        doc = ApiDocument(
            collection_id=collection.id,
            filename="spec.json",
            doc_type="openapi",
            stored_path=str(stored),
        )
        s.add(doc)
        s.flush()
        endpoint = ApiEndpoint(
            collection_id=collection.id,
            method="GET",
            path="/users",
            source_doc_id=doc.id,
        )
        s.add(endpoint)
        s.commit()
        collection_id, doc_id, endpoint_id = collection.id, doc.id, endpoint.id

    res = fk_client.delete(f"/api/api-collections/{collection_id}/documents/{doc_id}")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(ApiDocument, doc_id) is None
        assert s.get(ApiEndpoint, endpoint_id).source_doc_id is None
    assert not stored.exists()


def _run_with_credential(
    s: Session,
) -> tuple[TestRun, Credential, CrawledPage, ScannerSession]:
    run = _web_run(s)
    cred = Credential(site_id=run.site_id, username="alice", password="pw")
    s.add(cred)
    s.flush()
    run.crawl_credential_id = cred.id
    page = _page(s, run.id)
    page.replay_credential_id = cred.id
    scanner_session = ScannerSession(
        test_run_id=run.id, label="alice", credential_id=cred.id
    )
    s.add_all([run, page, scanner_session])
    s.commit()
    return run, cred, page, scanner_session


def test_delete_used_site_credential_clears_references(fk_engine, fk_client):
    with Session(fk_engine) as s:
        run, cred, page, scanner_session = _run_with_credential(s)
        ids = (run.site_id, run.id, cred.id, page.id, scanner_session.id)
    site_id, run_id, cred_id, page_id, scanner_session_id = ids

    res = fk_client.delete(f"/api/sites/{site_id}/credentials/{cred_id}")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(Credential, cred_id) is None
        assert s.get(TestRun, run_id).crawl_credential_id is None
        assert s.get(CrawledPage, page_id).replay_credential_id is None
        assert s.get(ScannerSession, scanner_session_id).credential_id is None


def test_update_site_removing_used_credential_clears_references(fk_engine):
    from aespa.services import sites as sites_svc

    with Session(fk_engine) as s:
        run, cred, _, _ = _run_with_credential(s)
        site_id, run_id, cred_id = run.site_id, run.id, cred.id

    with Session(fk_engine) as s:
        sites_svc.update_site(
            s,
            site_id,
            schemas.SiteUpdate(
                name="Site", base_url="http://target.local", credentials=[]
            ),
        )

    with Session(fk_engine) as s:
        assert s.get(Credential, cred_id) is None
        assert s.get(TestRun, run_id).crawl_credential_id is None


def _scanned_collection(s: Session) -> tuple[int, int]:
    collection = ApiCollection(name="API", base_url="http://api.local")
    s.add(collection)
    s.flush()
    endpoint = ApiEndpoint(collection_id=collection.id, method="GET", path="/users")
    s.add(endpoint)
    s.flush()
    run = ApiTestRun(collection_id=collection.id, name="Run")
    s.add(run)
    s.flush()
    s.add(
        ApiCredential(
            collection_id=collection.id,
            value="token",
            scope="endpoint",
            endpoint_id=endpoint.id,
        )
    )
    s.add(
        ApiEndpointTest(
            api_test_run_id=run.id, endpoint_id=endpoint.id, owasp_api_category="API1"
        )
    )
    s.commit()
    return collection.id, endpoint.id


def test_purge_collection_data_with_scanned_endpoints(fk_engine, fk_client):
    with Session(fk_engine) as s:
        collection_id, _ = _scanned_collection(s)

    res = fk_client.delete(f"/api/api-collections/{collection_id}/data")
    assert res.status_code == 200
    assert res.json() == {"endpoints_deleted": 1, "credentials_deleted": 1}

    with Session(fk_engine) as s:
        assert s.exec(select(ApiEndpoint)).all() == []
        assert s.exec(select(ApiCredential)).all() == []
        assert s.exec(select(ApiEndpointTest)).all() == []


def test_create_api_credential_rejects_endpoint_from_other_collection(
    fk_engine, fk_client
):
    with Session(fk_engine) as s:
        _, other_endpoint_id = _scanned_collection(s)
        collection = ApiCollection(name="Other", base_url="http://other.local")
        s.add(collection)
        s.commit()
        collection_id = collection.id

    for endpoint_id in (other_endpoint_id, 999999):
        res = fk_client.post(
            f"/api/api-collections/{collection_id}/credentials",
            json={"value": "token", "scope": "endpoint", "endpoint_id": endpoint_id},
        )
        assert res.status_code == 404


def _traffic_with_probe_links(
    s: Session, *, run_id: int, api: bool
) -> tuple[int, int, int]:
    traffic = TrafficEntry(
        test_run_id=None if api else run_id,
        api_test_run_id=run_id if api else None,
        source="probe",
        method="GET",
        url="http://target.local/a",
    )
    task = DeepScanTask(
        run_id=run_id,
        fingerprint="f",
        attack_class="xss",
        target_url="http://target.local/a",
    )
    obligation = ScanObligation(
        run_id=run_id,
        owasp_category="A03",
        vulnerability_technique="xss",
        route_template="/a",
    )
    s.add_all([traffic, task, obligation])
    s.flush()
    outcome = DeepScanProbeOutcome(
        run_id=run_id, task_id=task.id, fingerprint="f", traffic_id=traffic.id
    )
    execution = ProbeExecution(
        run_id=run_id, obligation_id=obligation.id, traffic_id=traffic.id
    )
    s.add_all([outcome, execution])
    s.commit()
    return traffic.id, outcome.id, execution.id


def test_clear_web_traffic_clears_probe_links(fk_engine, fk_client):
    with Session(fk_engine) as s:
        run = _web_run(s)
        run_id = run.id
        traffic_id, outcome_id, execution_id = _traffic_with_probe_links(
            s, run_id=run_id, api=False
        )

    res = fk_client.delete(f"/api/test-runs/{run_id}/traffic")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(TrafficEntry, traffic_id) is None
        assert s.get(DeepScanProbeOutcome, outcome_id).traffic_id is None
        assert s.get(ProbeExecution, execution_id).traffic_id is None


def test_clear_api_traffic_removes_only_that_runs_traffic(fk_engine, fk_client):
    with Session(fk_engine) as s:
        collection = ApiCollection(name="API", base_url="http://api.local")
        s.add(collection)
        s.flush()
        api_run = ApiTestRun(collection_id=collection.id, name="Run")
        s.add(api_run)
        s.flush()
        api_run_id = api_run.id
        traffic_id, _, execution_id = _traffic_with_probe_links(
            s, run_id=api_run_id, api=True
        )
        web_run = _web_run(s)
        web_traffic = TrafficEntry(
            test_run_id=web_run.id, source="crawl", method="GET", url="http://t/"
        )
        s.add(web_traffic)
        s.commit()
        web_traffic_id = web_traffic.id

    res = fk_client.delete(f"/api/api-test-runs/{api_run_id}/traffic")
    assert res.status_code == 204

    with Session(fk_engine) as s:
        assert s.get(TrafficEntry, traffic_id) is None
        assert s.get(ProbeExecution, execution_id).traffic_id is None
        assert s.get(TrafficEntry, web_traffic_id) is not None
