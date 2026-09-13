"""Finding-editing logic shared by the web-scan and API-scan routers.

Keeps the routers thin: both `PATCH .../findings/{id}` endpoints validate the
run/finding ownership and then delegate the actual mutation here so the rules for
what a user may change (and how it is sanitised) live in one place.
"""

from __future__ import annotations

import json

from sqlmodel import Session, select

from .. import schemas
from ..models import (
    ApiEndpointTest,
    CampaignFindingReference,
    CampaignValidationCase,
    DeepScanCheck,
    DeepScanClaim,
    DeepScanTask,
    DeepScanTaskFinding,
    PageOwaspTest,
    ScanFinding,
    ScanLead,
    SpecialistHandoff,
)

ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info"}
# Statuses a user may assign by hand. "validating" is excluded — it is a
# transient state owned by the validator service, not a user-settable label.
USER_SETTABLE_VALIDATION = {
    "unvalidated",
    "skipped",
    "confirmed",
    "unconfirmed",
    "false_positive",
}

# Free-text fields copied through verbatim when present.
_TEXT_FIELDS = (
    "description",
    "impact",
    "likelihood",
    "recommendation",
    "cvss_vector",
    "affected_url",
    "evidence",
    "request_evidence",
    "response_evidence",
    "validation_note",
)


def apply_finding_update(
    finding: ScanFinding, payload: schemas.ScanFindingUpdateIn
) -> None:
    """Apply a partial, user-driven edit to *finding* in place.

    Only fields explicitly provided in the payload are touched, so a partial save
    never blanks an unrelated field. Invalid severity/validation values are
    ignored rather than rejected. The caller commits the session.
    """
    data = payload.model_dump(exclude_unset=True)

    if data.get("severity") is not None:
        sev = str(data["severity"]).lower().strip()
        if sev in ALLOWED_SEVERITIES:
            finding.severity = sev

    if data.get("validation_status") is not None:
        status = str(data["validation_status"]).lower().strip()
        if status in USER_SETTABLE_VALIDATION:
            finding.validation_status = status

    if data.get("cvss_score") is not None:
        try:
            finding.cvss_score = float(data["cvss_score"])
        except (TypeError, ValueError):
            pass

    if data.get("title") is not None:
        title = str(data["title"]).strip()
        if title:  # never let an edit blank the title
            finding.title = title

    if data.get("owasp_category") is not None:
        cat = str(data["owasp_category"]).strip()[:32]
        if cat:
            finding.owasp_category = cat

    if data.get("owasp_api_category") is not None:
        api_cat = str(data["owasp_api_category"]).strip()[:32]
        finding.owasp_api_category = api_cat or None

    for field in _TEXT_FIELDS:
        if data.get(field) is not None:
            setattr(finding, field, data[field])


def _replace_finding_ids(value, duplicate_ids: set[int], keeper_id: int):
    if isinstance(value, list):
        replaced = [
            _replace_finding_ids(item, duplicate_ids, keeper_id) for item in value
        ]
        return (
            list(dict.fromkeys(replaced))
            if all(isinstance(v, int) for v in replaced)
            else replaced
        )
    if isinstance(value, dict):
        return {
            key: _replace_finding_ids(item, duplicate_ids, keeper_id)
            for key, item in value.items()
        }
    return keeper_id if isinstance(value, int) and value in duplicate_ids else value


def _replace_finding_ids_json(raw: str, duplicate_ids: set[int], keeper_id: int) -> str:
    try:
        parsed = json.loads(raw or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        return raw
    replaced = _replace_finding_ids(parsed, duplicate_ids, keeper_id)
    return json.dumps(replaced, sort_keys=isinstance(replaced, dict))


def consolidate_findings(
    session: Session,
    keeper: ScanFinding,
    duplicates: list[ScanFinding],
    payload: schemas.ScanFindingUpdateIn,
) -> list[str]:
    """Rewrite one finding and remove duplicates while preserving their links."""
    if keeper.id is None:
        raise ValueError("The retained finding must already be saved.")
    duplicate_ids = {finding.id for finding in duplicates if finding.id is not None}
    duplicate_ids.discard(keeper.id)
    if not duplicate_ids:
        raise ValueError("At least one different duplicate finding is required.")

    apply_finding_update(keeper, payload)
    merged_instances: list[dict] = []
    try:
        existing = json.loads(keeper.merged_instances or "[]")
        if isinstance(existing, list):
            merged_instances.extend(item for item in existing if isinstance(item, dict))
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    for finding in duplicates:
        if finding.id not in duplicate_ids:
            continue
        merged_instances.append(
            {
                "finding_id": finding.id,
                "finding_reference": finding.reference,
                "title": finding.title,
                "severity": finding.severity,
                "affected_url": finding.affected_url,
                "evidence": finding.evidence,
                "request_evidence": finding.request_evidence,
                "response_evidence": finding.response_evidence,
                "validation_status": finding.validation_status,
                "validation_note": finding.validation_note,
            }
        )
    keeper.merged_instances = json.dumps(merged_instances, default=str)
    session.add(keeper)

    for model in (
        CampaignValidationCase,
        SpecialistHandoff,
        DeepScanTask,
        DeepScanCheck,
        DeepScanClaim,
    ):
        for row in session.exec(
            select(model).where(model.finding_id.in_(duplicate_ids))
        ).all():
            row.finding_id = keeper.id
            session.add(row)

    for lead in session.exec(
        select(ScanLead).where(ScanLead.linked_finding_id.in_(duplicate_ids))
    ).all():
        lead.linked_finding_id = keeper.id
        session.add(lead)

    linked_tasks = {
        row.task_id
        for row in session.exec(
            select(DeepScanTaskFinding).where(
                DeepScanTaskFinding.finding_id == keeper.id
            )
        ).all()
    }
    for row in session.exec(
        select(DeepScanTaskFinding).where(
            DeepScanTaskFinding.finding_id.in_(duplicate_ids)
        )
    ).all():
        if row.task_id in linked_tasks:
            session.delete(row)
        else:
            row.finding_id = keeper.id
            linked_tasks.add(row.task_id)
            session.add(row)

    referenced_campaigns = {
        row.campaign_id
        for row in session.exec(
            select(CampaignFindingReference).where(
                CampaignFindingReference.finding_id == keeper.id
            )
        ).all()
    }
    for row in session.exec(
        select(CampaignFindingReference).where(
            CampaignFindingReference.finding_id.in_(duplicate_ids)
        )
    ).all():
        if row.campaign_id in referenced_campaigns:
            session.delete(row)
        else:
            row.finding_id = keeper.id
            referenced_campaigns.add(row.campaign_id)
            session.add(row)

    if keeper.test_run_id is not None:
        for cell in session.exec(
            select(PageOwaspTest).where(PageOwaspTest.test_run_id == keeper.test_run_id)
        ).all():
            cell.finding_ids_json = _replace_finding_ids_json(
                cell.finding_ids_json, duplicate_ids, keeper.id
            )
            cell.test_classes_json = _replace_finding_ids_json(
                cell.test_classes_json, duplicate_ids, keeper.id
            )
            session.add(cell)
    if keeper.api_test_run_id is not None:
        for cell in session.exec(
            select(ApiEndpointTest).where(
                ApiEndpointTest.api_test_run_id == keeper.api_test_run_id
            )
        ).all():
            cell.finding_ids_json = _replace_finding_ids_json(
                cell.finding_ids_json, duplicate_ids, keeper.id
            )
            session.add(cell)

    removed_references = [
        finding.reference for finding in duplicates if finding.id in duplicate_ids
    ]
    for finding in duplicates:
        if finding.id in duplicate_ids:
            session.delete(finding)
    session.commit()
    session.refresh(keeper)
    return removed_references
