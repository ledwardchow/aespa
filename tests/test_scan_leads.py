"""Tests for ScanLead auto-promotion: confirming a lead must back it with a finding."""
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import json

from aespa.db import set_engine
from aespa.models import (
    ApiCollection,
    ApiEndpoint,
    ApiEndpointTest,
    ScanFinding,
    ScanLead,
)
from aespa.services.scan_leads import update_lead


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    from aespa.db import _engine as original

    set_engine(engine)
    yield engine
    set_engine(original)
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def _make_lead(engine, **overrides) -> int:
    lead = ScanLead(
        collection_id=overrides.pop("collection_id", 1),
        producer_run_id=10,
        category=overrides.pop("category", "API1"),
        severity=overrides.pop("severity", "high"),
        title=overrides.pop("title", "IDOR on /orders/{id}"),
        description=overrides.pop("description", "SAST hypothesis: object id not authorised."),
        location=overrides.pop("location", "api/orders.py:42"),
        evidence="order = db.get(id)  # no owner check",
        **overrides,
    )
    with Session(engine) as s:
        s.add(lead)
        s.commit()
        s.refresh(lead)
        return lead.id


def test_confirm_without_finding_auto_promotes(engine):
    lead_id = _make_lead(engine)

    updated = update_lead(
        lead_id,
        status="confirmed",
        note="Reproduced: fetched another user's order.",
        investigated_by_run_type="api",
        investigated_by_run_id=99,
    )

    assert updated is not None
    assert updated.status == "confirmed"
    assert updated.linked_finding_id is not None

    with Session(engine) as s:
        finding = s.get(ScanFinding, updated.linked_finding_id)
    assert finding is not None
    # API run → keyed on api_test_run_id only.
    assert finding.api_test_run_id == 99
    assert finding.test_run_id is None
    assert finding.owasp_api_category == "API1"
    assert finding.severity == "high"
    assert finding.title == "IDOR on /orders/{id}"
    assert finding.finding_source == "sast_lead"


def test_confirm_links_existing_finding_no_duplicate(engine):
    """If the agent already recorded a finding for this run, link it — don't duplicate."""
    lead_id = _make_lead(engine, title="SSRF on webhook param")
    with Session(engine) as s:
        existing = ScanFinding(
            api_test_run_id=99,
            owasp_category="A00",
            owasp_api_category="API7",
            severity="high",
            title="SSRF on webhook param",
            description="already recorded by agent",
            finding_source="alice_api",
        )
        s.add(existing)
        s.commit()
        s.refresh(existing)
        existing_id = existing.id

    updated = update_lead(
        lead_id,
        status="confirmed",
        investigated_by_run_type="api",
        investigated_by_run_id=99,
    )

    assert updated.linked_finding_id == existing_id
    with Session(engine) as s:
        count = len(s.exec(select(ScanFinding).where(ScanFinding.api_test_run_id == 99)).all())
    assert count == 1


def test_explicit_finding_id_skips_promotion(engine):
    lead_id = _make_lead(engine)

    updated = update_lead(
        lead_id,
        status="confirmed",
        investigated_by_run_type="api",
        investigated_by_run_id=99,
        linked_finding_id=555,
    )

    assert updated.linked_finding_id == 555
    with Session(engine) as s:
        count = len(s.exec(select(ScanFinding)).all())
    assert count == 0  # no synthetic finding created


def test_dismissed_lead_creates_no_finding(engine):
    lead_id = _make_lead(engine)

    updated = update_lead(
        lead_id,
        status="dismissed",
        investigated_by_run_type="api",
        investigated_by_run_id=99,
    )

    assert updated.linked_finding_id is None
    with Session(engine) as s:
        count = len(s.exec(select(ScanFinding)).all())
    assert count == 0


def _make_collection_with_endpoint(engine, path="/users/{id}") -> tuple[int, int]:
    with Session(engine) as s:
        coll = ApiCollection(name="API", base_url="http://api.local")
        s.add(coll)
        s.commit()
        s.refresh(coll)
        ep = ApiEndpoint(
            collection_id=coll.id, method="GET", path=path, in_scope=True,
        )
        s.add(ep)
        s.commit()
        s.refresh(ep)
        return coll.id, ep.id


def test_confirm_flips_work_program_cell(engine):
    collection_id, endpoint_id = _make_collection_with_endpoint(engine)
    # Lead text references the route path so the coverage hook can match it.
    lead_id = _make_lead(
        engine,
        collection_id=collection_id,
        category="API1",
        title="BOLA on /users/{id}",
    )

    updated = update_lead(
        lead_id,
        status="confirmed",
        investigated_by_run_type="api",
        investigated_by_run_id=99,
    )

    with Session(engine) as s:
        cell = s.exec(
            select(ApiEndpointTest)
            .where(ApiEndpointTest.api_test_run_id == 99)
            .where(ApiEndpointTest.endpoint_id == endpoint_id)
            .where(ApiEndpointTest.owasp_api_category == "API1")
        ).first()
    assert cell is not None
    assert cell.status == "finding"
    assert updated.linked_finding_id in json.loads(cell.finding_ids_json)


def test_confirm_no_cell_when_no_endpoint_match(engine):
    """A confirmed lead with no matchable endpoint still raises the finding, just no cell."""
    collection_id, _ = _make_collection_with_endpoint(engine, path="/orders/{id}")
    lead_id = _make_lead(
        engine,
        collection_id=collection_id,
        category="API1",
        title="BOLA somewhere",
        location="src/auth.py:88",  # code site, no route path
    )

    updated = update_lead(
        lead_id,
        status="confirmed",
        investigated_by_run_type="api",
        investigated_by_run_id=99,
    )

    assert updated.linked_finding_id is not None  # finding still raised
    with Session(engine) as s:
        cells = s.exec(select(ApiEndpointTest)).all()
    assert len(cells) == 0  # nothing fabricated


def test_confirm_without_run_id_does_not_promote(engine):
    """No run to attribute the finding to → don't create an orphan."""
    lead_id = _make_lead(engine)

    updated = update_lead(lead_id, status="confirmed")

    assert updated.status == "confirmed"
    assert updated.linked_finding_id is None
    with Session(engine) as s:
        count = len(s.exec(select(ScanFinding)).all())
    assert count == 0
