"""Build campaign findings and mapping responses from stored results."""

from __future__ import annotations

import json

from sqlmodel import Session, select

from aespa.models import (
    ApplicationComponent,
    CampaignSourceMember,
    CampaignTargetMember,
    LeadTargetMapping,
    ScanFinding,
    ScanLead,
    ScanLeadComponentProvenance,
)
from aespa.schemas import CampaignFindingRow, LeadTargetMappingOut
from aespa.services import applications as applications_svc
from aespa.services import scan_leads as scan_leads_svc
from aespa.services.references import (
    ensure_campaign_finding_reference,
    ensure_finding_reference,
    ensure_lead_references,
)


def _component_id_by_sast_run_id(session: Session, campaign_id: int) -> dict[int, int]:
    """One component per frozen SAST child this campaign created."""
    return {
        member.sast_run_id: member.component_id
        for member in session.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.campaign_id == campaign_id
            )
        ).all()
        if member.sast_run_id is not None
    }


def _component_names_by_id(session: Session, component_ids: set[int]) -> dict[int, str]:
    if not component_ids:
        return {}
    return {
        component.id: component.name
        for component in session.exec(
            select(ApplicationComponent).where(
                ApplicationComponent.id.in_(component_ids)
            )
        ).all()
    }


def _cross_repo_finding_group_key(
    finding: ScanFinding,
    finding_lead: ScanLead | None,
    original_lead: ScanLead | None,
    target_member: CampaignTargetMember,
) -> tuple[str, str, int, str, str] | None:
    """Return a root-cause key for a campaign cross-repository finding.

    A single SAST lead can be connected to many equivalent endpoints. The
    endpoint stays in the instance list; the source vulnerability and target
    component define the displayed root cause.
    """
    if (
        finding_lead is None
        or finding_lead.producer_run_type != "campaign"
        or original_lead is None
    ):
        return None
    attack_path = scan_leads_svc.decode_attack_path(original_lead.attack_path_json)
    entrypoint = attack_path.get("frontend_entrypoint")
    backend_route = attack_path.get("backend_route")
    vulnerability = attack_path.get("vulnerability")
    if not (
        isinstance(entrypoint, dict)
        and isinstance(backend_route, dict)
        and isinstance(vulnerability, dict)
    ):
        return None
    target_component_id = backend_route.get("component_id")
    if not isinstance(target_component_id, int):
        return None
    vulnerability_id = vulnerability.get("lead_id") or original_lead.fingerprint
    return (
        "cross-repository",
        str(vulnerability_id),
        target_component_id,
        finding.owasp_category,
        target_member.target_type,
    )


def _finding_instance_payload(row: CampaignFindingRow) -> dict[str, object]:
    """Keep the useful identity of a hidden duplicate in the API response."""
    return {
        "finding_id": row.finding_id,
        "reference": row.reference,
        "run_reference": row.run_reference,
        "target_run_id": row.target_run_id,
        "target_name": row.target_name,
        "affected_url": row.affected_url,
        "title": row.title,
        "status": row.status,
    }


def merge_campaign_finding_rows(
    rows: list[tuple[CampaignFindingRow, tuple[str, str, int, str, str] | None]],
) -> list[CampaignFindingRow]:
    """Return one row per cross-repository root cause plus endpoint instances."""
    grouped: dict[tuple[str, str, int, str, str], list[CampaignFindingRow]] = {}
    for row, key in rows:
        if key is not None:
            grouped.setdefault(key, []).append(row)

    hidden_ids: set[int] = set()
    merged_by_primary: dict[int, str] = {}
    for group in grouped.values():
        group.sort(key=lambda row: (row.target_run_id, row.finding_id))
        if len(group) < 2:
            continue
        primary = group[0]
        try:
            merged = json.loads(primary.merged_instances or "[]")
        except (TypeError, json.JSONDecodeError):
            merged = []
        if not isinstance(merged, list):
            merged = []
        merged.extend(_finding_instance_payload(row) for row in group[1:])
        merged_by_primary[primary.finding_id] = json.dumps(merged)
        hidden_ids.update(row.finding_id for row in group[1:])

    result: list[CampaignFindingRow] = []
    for row, _key in rows:
        if row.finding_id in hidden_ids:
            continue
        if row.finding_id in merged_by_primary:
            row.merged_instances = merged_by_primary[row.finding_id]
        result.append(row)
    return result


def enrich_mappings(
    session: Session, campaign_id: int, mappings: list[LeadTargetMapping]
) -> list[LeadTargetMappingOut]:
    """Attach lead context (title/description/severity/location/producer)
    and contributing component ids/names to each mapping — bounded to a
    handful of queries total regardless of mapping count (no N+1).
    """
    if not mappings:
        return []

    lead_ids = {m.lead_id for m in mappings}
    leads_by_id = {
        lead.id: lead
        for lead in session.exec(
            select(ScanLead).where(ScanLead.id.in_(lead_ids))
        ).all()
    }
    ensure_lead_references(session, leads_by_id.values())

    component_id_by_sast_run_id = _component_id_by_sast_run_id(session, campaign_id)

    campaign_lead_ids = {
        lead_id
        for lead_id, lead in leads_by_id.items()
        if lead.producer_run_type == "campaign"
    }
    provenance_by_lead: dict[int, list[int]] = {}
    if campaign_lead_ids:
        for row in session.exec(
            select(ScanLeadComponentProvenance).where(
                ScanLeadComponentProvenance.scan_lead_id.in_(campaign_lead_ids)
            )
        ).all():
            provenance_by_lead.setdefault(row.scan_lead_id, []).append(row.component_id)

    all_component_ids = set(component_id_by_sast_run_id.values()) | {
        component_id
        for component_ids in provenance_by_lead.values()
        for component_id in component_ids
    }
    component_name_by_id = _component_names_by_id(session, all_component_ids)

    enriched: list[LeadTargetMappingOut] = []
    for mapping in mappings:
        base = LeadTargetMappingOut.model_validate(mapping)
        lead = leads_by_id.get(mapping.lead_id)
        if lead is None:
            enriched.append(base)
            continue
        if lead.producer_run_type == "sast":
            component_id = component_id_by_sast_run_id.get(lead.producer_run_id)
            component_ids = [component_id] if component_id is not None else []
        else:
            component_ids = provenance_by_lead.get(lead.id, [])
        enriched.append(
            base.model_copy(
                update={
                    "lead_reference": lead.reference,
                    "lead_title": lead.title,
                    "lead_description": lead.description,
                    "lead_severity": lead.severity,
                    "lead_location": lead.location,
                    "lead_producer_run_type": lead.producer_run_type,
                    "lead_producer_run_id": lead.producer_run_id,
                    "lead_category": lead.category,
                    "lead_confidence": lead.confidence,
                    "lead_source": lead.source,
                    "lead_fingerprint": lead.fingerprint,
                    "lead_origin_lead_id": lead.origin_lead_id,
                    "lead_origin_reference": lead.origin_reference,
                    "lead_trace_path_key": lead.trace_path_key,
                    "lead_trace_status": lead.trace_status,
                    "lead_trace_confidence": lead.trace_confidence,
                    "lead_suggested_endpoint": lead.suggested_endpoint,
                    "lead_status": lead.status,
                    "lead_validation_status": lead.validation_status,
                    "lead_validation_reasoning": lead.validation_reasoning,
                    "lead_reportable": lead.reportable,
                    "lead_evidence": lead.evidence,
                    "lead_note": lead.note,
                    "lead_source_trace_json": lead.source_trace_json,
                    "lead_control_trace_json": lead.control_trace_json,
                    "lead_sink_trace_json": lead.sink_trace_json,
                    "lead_counterevidence_json": lead.counterevidence_json,
                    "lead_proof_gaps_json": lead.proof_gaps_json,
                    "lead_attack_path_json": lead.attack_path_json,
                    "component_ids": component_ids,
                    "component_names": [
                        component_name_by_id[cid]
                        for cid in component_ids
                        if cid in component_name_by_id
                    ],
                }
            )
        )
    session.commit()
    return enriched


def list_campaign_findings(
    session: Session, application_id: int, campaign_id: int
) -> list[CampaignFindingRow]:
    """Return campaign findings with references and component names."""
    target_members = session.exec(
        select(CampaignTargetMember).where(
            CampaignTargetMember.campaign_id == campaign_id
        )
    ).all()

    findings_by_target: list[tuple[CampaignTargetMember, int, list[ScanFinding]]] = []
    all_findings: list[ScanFinding] = []
    for target_member in target_members:
        run_id = target_member.test_run_id or target_member.api_test_run_id
        if run_id is None:
            continue
        if target_member.test_run_id is not None:
            findings = session.exec(
                select(ScanFinding).where(ScanFinding.test_run_id == run_id)
            ).all()
        else:
            findings = session.exec(
                select(ScanFinding).where(ScanFinding.api_test_run_id == run_id)
            ).all()
        findings_by_target.append((target_member, run_id, findings))
        all_findings.extend(findings)

    finding_ids = {f.id for f in all_findings if f.id is not None}
    lead_by_finding_id: dict[int, ScanLead] = {}
    if finding_ids:
        for lead in session.exec(
            select(ScanLead).where(ScanLead.linked_finding_id.in_(finding_ids))
        ).all():
            if lead.linked_finding_id is not None:
                lead_by_finding_id[lead.linked_finding_id] = lead

    component_id_by_sast_run_id = _component_id_by_sast_run_id(session, campaign_id)

    # Campaign-produced copies need their *original* lead's id (provenance is
    # keyed on the original, not the copy) — resolved by fingerprint, exactly
    # how copy_lead_to_run itself finds an existing copy.
    campaign_copy_fingerprints = {
        lead.fingerprint
        for lead in lead_by_finding_id.values()
        if lead.producer_run_type == "campaign" and lead.fingerprint
    }
    original_id_by_fingerprint: dict[str, int] = {}
    original_by_id: dict[int, ScanLead] = {}
    if campaign_copy_fingerprints:
        for original in session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == campaign_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.fingerprint.in_(campaign_copy_fingerprints))
        ).all():
            original_id_by_fingerprint[original.fingerprint] = original.id
            original_by_id[original.id] = original

    provenance_by_original_lead: dict[int, list[int]] = {}
    if original_id_by_fingerprint:
        original_ids = set(original_id_by_fingerprint.values())
        for row in session.exec(
            select(ScanLeadComponentProvenance).where(
                ScanLeadComponentProvenance.scan_lead_id.in_(original_ids)
            )
        ).all():
            provenance_by_original_lead.setdefault(row.scan_lead_id, []).append(
                row.component_id
            )

    all_component_ids = set(component_id_by_sast_run_id.values()) | {
        component_id
        for component_ids in provenance_by_original_lead.values()
        for component_id in component_ids
    }
    component_name_by_id = _component_names_by_id(session, all_component_ids)

    def _component_ids_for_finding(finding: ScanFinding) -> list[int]:
        lead = lead_by_finding_id.get(finding.id)
        if lead is None:
            return []  # no linked campaign lead — never guessed
        if lead.producer_run_type == "sast":
            component_id = component_id_by_sast_run_id.get(lead.producer_run_id)
            return [component_id] if component_id is not None else []
        if lead.producer_run_type == "campaign":
            original_id = original_id_by_fingerprint.get(lead.fingerprint)
            if original_id is None:
                return []
            return provenance_by_original_lead.get(original_id, [])
        return []

    rows: list[tuple[CampaignFindingRow, tuple[str, str, int, str, str] | None]] = []
    for target_member, run_id, findings in findings_by_target:
        target = applications_svc.get_target(
            session, application_id, target_member.target_id
        )
        target_name = applications_svc.target_display_name(session, target)
        for finding in findings:
            ensure_finding_reference(session, finding)
            campaign_reference = ensure_campaign_finding_reference(
                session,
                campaign_id=campaign_id,
                finding_id=finding.id,
                target_member_id=target_member.id,
            )
            component_ids = _component_ids_for_finding(finding)
            finding_lead = lead_by_finding_id.get(finding.id)
            attack_path = (
                scan_leads_svc.decode_attack_path(finding_lead.attack_path_json)
                if finding_lead is not None
                else {}
            )
            frontend_path = (
                attack_path if attack_path.get("perspective") == "frontend" else None
            )
            backend_path = (
                attack_path.get("origin_attack_path") if frontend_path else attack_path
            )
            component_names = [
                component_name_by_id[cid]
                for cid in component_ids
                if cid in component_name_by_id
            ]
            row = CampaignFindingRow(
                finding_id=finding.id,
                reference=campaign_reference.public_reference,
                run_reference=finding.reference,
                target_type=target_member.target_type,
                target_run_id=run_id,
                component_id=component_ids[0] if component_ids else None,
                component_name=(
                    ", ".join(component_names) if component_names else None
                ),
                component_ids=component_ids,
                component_names=component_names,
                target_name=target_name,
                title=finding.title,
                description=finding.description,
                impact=finding.impact,
                likelihood=finding.likelihood,
                recommendation=finding.recommendation,
                cvss_score=finding.cvss_score,
                cvss_vector=finding.cvss_vector,
                affected_url=finding.affected_url,
                evidence=finding.evidence,
                request_evidence=finding.request_evidence,
                response_evidence=finding.response_evidence,
                evidence_items=finding.evidence_items,
                validation_note=finding.validation_note,
                merged_instances=finding.merged_instances,
                poc_command=finding.poc_command,
                poc_setup=finding.poc_setup,
                finding_source=finding.finding_source,
                origin=finding.origin,
                validated_by=finding.validated_by,
                severity=finding.severity,
                status=finding.validation_status,
                frontend_attack_path=frontend_path,
                backend_attack_path=backend_path
                if isinstance(backend_path, dict)
                else None,
            )
            original_lead = None
            if (
                finding_lead is not None
                and finding_lead.producer_run_type == "campaign"
            ):
                original_id = original_id_by_fingerprint.get(finding_lead.fingerprint)
                if original_id is not None:
                    original_lead = original_by_id.get(original_id)
            rows.append(
                (
                    row,
                    _cross_repo_finding_group_key(
                        finding,
                        finding_lead,
                        original_lead,
                        target_member,
                    ),
                )
            )
    session.commit()
    return merge_campaign_finding_rows(rows)
