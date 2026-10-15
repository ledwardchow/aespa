"""Read-only search of SAST scans for explicit dynamic-run lead imports."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlmodel import Session, select

from aespa.models import SastRun, ScanLead
from aespa.services.scan_leads import lead_fingerprint


def search_import_sources(
    session: Session,
    *,
    run_kind: str,
    run_id: int,
    query: str,
    page: int,
    page_size: int,
) -> dict:
    statement = select(SastRun).where(
        SastRun.status == "completed", SastRun.leads_count > 0
    )
    if query.strip():
        term = query.strip().lower()
        source_id = int(term) if term.isdecimal() else 0
        source_id = source_id if source_id <= 2**63 - 1 else 0
        statement = statement.where(
            or_(
                func.lower(SastRun.name).contains(term, autoescape=True),
                func.lower(SastRun.source_filename).contains(term, autoescape=True),
                SastRun.id == source_id if source_id else False,
            )
        )
    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    runs = session.exec(
        statement.order_by(SastRun.completed_at.desc(), SastRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    ids = [run.id for run in runs]
    originals: dict[int, set[str]] = {run.id: set() for run in runs}
    imported: dict[int, set[str]] = {run.id: set() for run in runs}
    if ids:
        for source_id, fingerprint, category, title, location in session.exec(
            select(
                ScanLead.producer_run_id,
                ScanLead.fingerprint,
                ScanLead.category,
                ScanLead.title,
                ScanLead.location,
            ).where(
                ScanLead.producer_run_type == "sast",
                ScanLead.producer_run_id.in_(ids),
                ScanLead.imported_into_run_id.is_(None),
                ScanLead.reportable.is_(True),
            )
        ).all():
            originals[source_id].add(
                fingerprint
                or lead_fingerprint(category=category, title=title, location=location)
            )
        for source_id, fingerprint in session.exec(
            select(ScanLead.producer_run_id, ScanLead.fingerprint).where(
                ScanLead.producer_run_type == "sast",
                ScanLead.producer_run_id.in_(ids),
                ScanLead.imported_into_run_type == run_kind,
                ScanLead.imported_into_run_id == run_id,
            )
        ).all():
            imported[source_id].add(fingerprint)
    return {
        "items": [
            {
                "id": run.id,
                "name": run.name,
                "source_filename": run.source_filename,
                "completed_at": run.completed_at.isoformat()
                if run.completed_at
                else None,
                "leads_count": len(originals[run.id]),
                "imported_count": len(originals[run.id] & imported[run.id]),
                "new_count": len(originals[run.id] - imported[run.id]),
            }
            for run in runs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
