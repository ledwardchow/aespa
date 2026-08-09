from __future__ import annotations

import re

from sqlmodel import Session

from aespa.models import ScanFinding, ScanLead
from aespa.services.references import (
    ensure_campaign_finding_reference,
    ensure_finding_reference,
    ensure_lead_reference,
    inherit_lead_reference,
)


def test_run_references_share_a_namespace_and_keep_sast_origin(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        original = ScanLead(
            producer_run_type="sast",
            producer_run_id=10,
            title="Unsafe query",
            fingerprint="unsafe-query",
        )
        session.add(original)
        session.flush()
        original_reference = ensure_lead_reference(session, original)

        imported = ScanLead(
            producer_run_type="sast",
            producer_run_id=10,
            imported_into_run_type="web",
            imported_into_run_id=20,
            origin_lead_id=original.id,
            origin_reference=original_reference,
            title=original.title,
            fingerprint=original.fingerprint,
        )
        session.add(imported)
        session.flush()
        imported_reference = ensure_lead_reference(session, imported)

        finding = ScanFinding(
            test_run_id=20,
            owasp_category="A03",
            severity="high",
            title="Unsafe query",
            description="A query can be injected.",
        )
        session.add(finding)
        session.flush()
        inherit_lead_reference(session, finding, imported)
        session.commit()

        assert re.fullmatch(r"[A-Z]{4}-001", original_reference)
        assert re.fullmatch(r"[A-Z]{4}-001", imported_reference)
        assert original_reference != imported_reference
        assert finding.reference == imported_reference
        assert finding.origin == {
            "type": "sast",
            "label": "SAST",
            "run_type": "sast",
            "run_id": 10,
            "lead_id": original.id,
            "reference": original_reference,
        }

        second_finding = ScanFinding(
            test_run_id=20,
            owasp_category="A01",
            severity="medium",
            title="Another issue",
            description="Another issue.",
        )
        session.add(second_finding)
        session.flush()
        assert ensure_finding_reference(session, second_finding).endswith("-002")


def test_campaign_alias_is_stable_and_has_its_own_namespace(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        finding = ScanFinding(
            test_run_id=30,
            owasp_category="A05",
            severity="low",
            title="Missing header",
            description="A security header is absent.",
        )
        session.add(finding)
        session.flush()
        ensure_finding_reference(session, finding)

        first = ensure_campaign_finding_reference(
            session,
            campaign_id=40,
            finding_id=finding.id,
            target_member_id=50,
        )
        second = ensure_campaign_finding_reference(
            session,
            campaign_id=40,
            finding_id=finding.id,
            target_member_id=50,
        )

        assert first.id == second.id
        assert re.fullmatch(r"[A-Z]{4}-001", first.public_reference)
        assert first.public_reference != finding.reference
