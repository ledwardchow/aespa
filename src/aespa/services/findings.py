"""Finding-editing logic shared by the web-scan and API-scan routers.

Keeps the routers thin: both `PATCH .../findings/{id}` endpoints validate the
run/finding ownership and then delegate the actual mutation here so the rules for
what a user may change (and how it is sanitised) live in one place.
"""

from __future__ import annotations

from .. import schemas
from ..models import ScanFinding

ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info"}
# Statuses a user may assign by hand. "validating" is excluded — it is a
# transient state owned by the validator service, not a user-settable label.
USER_SETTABLE_VALIDATION = {
    "unvalidated",
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
