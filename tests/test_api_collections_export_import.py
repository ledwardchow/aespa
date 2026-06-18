"""Round-trip test for export_collection/import_collection — verifies id remapping
across endpoints, credentials, findings, workprogram cells, ALICE chat, and that
uploaded document bytes survive."""
from __future__ import annotations

import json
import types

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa import models as _models  # noqa: F401  (register tables)
from aespa.models import (
    AgentLog,
    AliceChatMessage,
    AliceChatSession,
    ApiCollection,
    ApiCredential,
    ApiDocument,
    ApiEndpoint,
    ApiEndpointTest,
    ApiTestRun,
    SastRun,
    ScanFinding,
    ScanLead,
    ScanLog,
    TrafficEntry,
)
from aespa.services import api_collections as svc


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_roundtrip(session, tmp_path, monkeypatch):
    # Redirect document storage to a temp dir for both the source file and import.
    monkeypatch.setattr(
        "aespa.services.api_documents.get_settings",
        lambda: types.SimpleNamespace(data_dir=tmp_path),
    )

    col = ApiCollection(name="petstore", base_url="http://api.test")
    session.add(col)
    session.flush()

    doc_path = tmp_path / "spec.json"
    doc_path.write_bytes(b'{"openapi":"3.0.0"}')
    doc = ApiDocument(collection_id=col.id, filename="spec.json", doc_type="openapi",
                      stored_path=str(doc_path), size_bytes=doc_path.stat().st_size, status="parsed")
    session.add(doc)
    session.flush()

    ep = ApiEndpoint(collection_id=col.id, source_doc_id=doc.id, method="GET", path="/pets/{id}")
    session.add(ep)
    session.flush()
    # Credential scoped to the endpoint — endpoint_id must remap.
    session.add(ApiCredential(collection_id=col.id, scheme="bearer", name="Authorization",
                              value="tok", scope="endpoint", endpoint_id=ep.id))

    run = ApiTestRun(collection_id=col.id, name="run-1", status="completed", sast_run_id=42)
    session.add(run)
    session.flush()
    finding = ScanFinding(api_test_run_id=run.id, owasp_category="API1", owasp_api_category="API1",
                          severity="high", title="BOLA", description="x")
    session.add(finding)
    session.flush()
    # API traffic uses the sentinel test_run_id=0 (no real TestRun row).
    session.add(TrafficEntry(test_run_id=0, api_test_run_id=run.id, source="httpx",
                             method="GET", url="http://api.test/pets/1"))
    # Cell references both endpoint and finding; 99999 is a stale finding id to drop.
    session.add(ApiEndpointTest(api_test_run_id=run.id, endpoint_id=ep.id, owasp_api_category="API1",
                                status="finding", finding_ids_json=json.dumps([finding.id, 99999])))
    session.add(AgentLog(test_run_id=run.id, run_kind="api", agent_id="lead", role="test_lead", status="active"))
    alice = AliceChatSession(test_run_id=run.id, run_kind="api", session_key="tab-1")
    session.add(alice)
    session.flush()
    session.add(AliceChatMessage(session_id=alice.id, message_key="m1", sender="user", text="hi"))

    # SAST run that produced a lead; the api run back-references it via sast_run_id.
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04zipbytes")
    zip_doc = ApiDocument(collection_id=col.id, filename="src.zip", doc_type="source_zip",
                          stored_path=str(zip_path), size_bytes=zip_path.stat().st_size, status="parsed")
    session.add(zip_doc)
    session.flush()
    sast = SastRun(collection_id=col.id, document_id=zip_doc.id, name="sast-1", status="completed",
                   triggered_by_run_type="api", triggered_by_run_id=run.id)
    session.add(sast)
    session.flush()
    run.sast_run_id = sast.id
    session.add(run)
    session.add(ScanLog(test_run_id=sast.id, run_kind="sast", phase="thinking_step", message="sast scanning"))
    session.add(AgentLog(test_run_id=sast.id, run_kind="sast", agent_id="sast", role="sast", status="done"))
    lead = ScanLead(collection_id=col.id, producer_run_id=sast.id, category="API1", severity="high",
                    title="hardcoded secret", evidence="api_key = 'xxx'  # config.py:10",
                    investigated_by_run_type="api", investigated_by_run_id=run.id,
                    linked_finding_id=finding.id)
    session.add(lead)
    session.commit()

    bundle = svc.export_collection(session, col.id)
    # source_zip bytes are intentionally dropped from the bundle.
    zip_entry = next(d for d in bundle["documents"] if d["doc_type"] == "source_zip")
    assert zip_entry["content_b64"] is None
    new_col = svc.import_collection(session, bundle)
    assert new_col.id != col.id

    new_run = session.exec(select(ApiTestRun).where(ApiTestRun.collection_id == new_col.id)).one()
    assert new_run.llm_config_id is None  # cannot map across installations

    new_ep = session.exec(select(ApiEndpoint).where(ApiEndpoint.collection_id == new_col.id)).one()
    new_doc = session.exec(select(ApiDocument).where(ApiDocument.collection_id == new_col.id)
                           .where(ApiDocument.doc_type == "openapi")).one()
    assert new_ep.source_doc_id == new_doc.id
    # Document bytes survived and live at a fresh path.
    from pathlib import Path
    assert new_doc.stored_path != str(doc_path)
    assert Path(new_doc.stored_path).read_bytes() == b'{"openapi":"3.0.0"}'

    new_cred = session.exec(select(ApiCredential).where(ApiCredential.collection_id == new_col.id)).one()
    assert new_cred.endpoint_id == new_ep.id

    new_finding = session.exec(select(ScanFinding).where(ScanFinding.api_test_run_id == new_run.id)).one()
    assert new_finding.test_run_id is None  # never leaks into the web id-space
    cell = session.exec(select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == new_run.id)).one()
    assert cell.endpoint_id == new_ep.id
    assert json.loads(cell.finding_ids_json) == [new_finding.id]  # stale 99999 dropped

    new_traffic = session.exec(select(TrafficEntry).where(TrafficEntry.api_test_run_id == new_run.id)).one()
    assert new_traffic.test_run_id == 0  # sentinel preserved, not NULL

    assert len(session.exec(select(AgentLog).where(AgentLog.test_run_id == new_run.id)
                            .where(AgentLog.run_kind == "api")).all()) == 1
    new_alice = session.exec(select(AliceChatSession).where(AliceChatSession.test_run_id == new_run.id)).one()
    msgs = session.exec(select(AliceChatMessage).where(AliceChatMessage.session_id == new_alice.id)).all()
    assert len(msgs) == 1 and msgs[0].text == "hi"

    # SAST run + lead survived with every cross-reference remapped.
    new_sast = session.exec(select(SastRun).where(SastRun.collection_id == new_col.id)).one()
    assert new_sast.triggered_by_run_id == new_run.id
    new_zip = session.exec(select(ApiDocument).where(ApiDocument.doc_type == "source_zip")
                           .where(ApiDocument.collection_id == new_col.id)).one()
    assert new_sast.document_id == new_zip.id
    assert new_zip.stored_path == ""  # bytes were dropped → no file written
    assert new_run.sast_run_id == new_sast.id  # back-patched
    # SAST logs travel too, re-keyed onto the new SAST run id.
    assert len(session.exec(select(ScanLog).where(ScanLog.test_run_id == new_sast.id)
                            .where(ScanLog.run_kind == "sast")).all()) == 1
    assert len(session.exec(select(AgentLog).where(AgentLog.test_run_id == new_sast.id)
                            .where(AgentLog.run_kind == "sast")).all()) == 1

    new_lead = session.exec(select(ScanLead).where(ScanLead.collection_id == new_col.id)).one()
    assert new_lead.producer_run_id == new_sast.id
    assert new_lead.investigated_by_run_id == new_run.id
    assert new_lead.linked_finding_id == new_finding.id
    assert new_lead.evidence == "api_key = 'xxx'  # config.py:10"


def test_rejects_non_api_bundle(session):
    with pytest.raises(svc.ApiCollectionServiceError):
        svc.import_collection(session, {"export_version": 1, "kind": "site"})
