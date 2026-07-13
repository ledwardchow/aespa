"""Tests for ScanLead auto-promotion: confirming a lead must back it with a finding."""
import json

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import set_engine
from aespa.models import (
    ApiCollection,
    ApiEndpoint,
    ApiEndpointTest,
    ScanFinding,
    ScanLead,
)
from aespa.services.scan_leads import (
    copy_leads_to_run,
    format_leads_for_run,
    get_leads_for_run,
    list_leads_for_run,
    update_lead,
)


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
        producer_run_id=overrides.pop("producer_run_id", 10),
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


# ── Copy-into-web-run model ─────────────────────────────────────────────────────

def _make_sast_originals(engine, sast_run_id=10, n=2) -> list[int]:
    ids = []
    for i in range(n):
        ids.append(_make_lead(
            engine,
            collection_id=None,
            producer_run_id=sast_run_id,
            title=f"Lead {i}",
            category="A03",
        ))
    return ids


def test_copy_leads_to_run_copies_and_preserves_originals(engine):
    originals = _make_sast_originals(engine, sast_run_id=10, n=2)

    made = copy_leads_to_run(10, "web", 7)
    assert made == 2

    # Originals untouched: still open, not owned by any run.
    sast_view = list_leads_for_run(10)
    assert len(sast_view) == 2  # copies excluded from the SAST tab
    assert {lead.id for lead in sast_view} == set(originals)
    for lead in sast_view:
        assert lead.imported_into_run_id is None
        assert lead.status == "open"

    # Copies belong to the web run and are fresh/open.
    copies = get_leads_for_run("web", 7)
    assert len(copies) == 2
    for c in copies:
        assert c.imported_into_run_type == "web"
        assert c.imported_into_run_id == 7
        assert c.producer_run_id == 10  # provenance preserved
        assert c.id not in originals
        assert c.status == "open"


def test_copy_leads_to_run_is_idempotent(engine):
    _make_sast_originals(engine, sast_run_id=10, n=2)
    assert copy_leads_to_run(10, "web", 7) == 2
    # Re-import from the same SAST run into the same web run → nothing new.
    assert copy_leads_to_run(10, "web", 7) == 0
    assert len(get_leads_for_run("web", 7)) == 2


def test_explicit_imports_are_fresh_and_independent_for_each_api_run(engine):
    """Explicit imports give every API run a fresh independent lead copy."""
    [original_id] = _make_sast_originals(engine, sast_run_id=10, n=1)

    assert copy_leads_to_run(10, "api", 41) == 1
    first_copy = get_leads_for_run("api", 41)[0]
    update_lead(
        first_copy.id,
        status="dismissed",
        note="not reproducible in run 41",
        investigated_by_run_type="api",
        investigated_by_run_id=41,
    )

    assert get_leads_for_run("api", 41) == []
    assert copy_leads_to_run(10, "api", 42) == 1
    second_copy = get_leads_for_run("api", 42)[0]
    assert second_copy.id != first_copy.id
    assert second_copy.status == "open"
    assert second_copy.note == ""
    assert second_copy.investigated_by_run_id is None
    assert "Lead #" + str(second_copy.id) in format_leads_for_run("api", 42)

    with Session(engine) as s:
        original = s.get(ScanLead, original_id)
        assert original.status == "open"
        assert original.investigated_by_run_id is None
def test_investigating_copy_leaves_original_open(engine):
    [orig_id] = _make_sast_originals(engine, sast_run_id=10, n=1)
    copy_leads_to_run(10, "web", 7)
    copy = get_leads_for_run("web", 7)[0]

    # Dismiss the copy as the web scan would.
    update_lead(
        copy.id,
        status="dismissed",
        investigated_by_run_type="web",
        investigated_by_run_id=7,
    )

    with Session(engine) as s:
        original = s.get(ScanLead, orig_id)
    assert original.status == "open"  # SAST tab original unaffected


def test_web_confirm_promotes_to_test_run_id(engine):
    """A web-investigated lead must key its finding on test_run_id, not api_test_run_id."""
    lead_id = _make_lead(engine, collection_id=None, category="A01", title="SQLi on /search")

    updated = update_lead(
        lead_id,
        status="confirmed",
        investigated_by_run_type="web",
        investigated_by_run_id=42,
    )

    assert updated.linked_finding_id is not None
    with Session(engine) as s:
        finding = s.get(ScanFinding, updated.linked_finding_id)
    assert finding.test_run_id == 42
    assert finding.api_test_run_id is None
    assert finding.owasp_category == "A01"
    assert finding.finding_source == "sast_lead"
