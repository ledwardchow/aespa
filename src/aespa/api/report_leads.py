"""Preview and import external scanner reports into web and API runs."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool

from aespa.db import get_session
from aespa.services import report_leads

router = APIRouter(tags=["scan-leads"])


async def _import_report(
    run_kind: str,
    run_id: int,
    file: UploadFile,
    preview: bool,
    prepared: str | None,
    request: Request,
    session: Session,
) -> dict:
    try:
        content = await file.read(report_leads.MAX_REPORT_BYTES + 1)
        filename = PurePosixPath((file.filename or "report").replace("\\", "/")).name[
            :255
        ]
        secret = request.app.state.auth.secret
        if report_leads.needs_llm(content, filename):
            if preview:
                (
                    report_format,
                    leads,
                    warnings,
                    skipped,
                ) = await report_leads.normalize_report(
                    session, run_kind, run_id, content, filename
                )
                data = {
                    "run_kind": run_kind,
                    "run_id": run_id,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "filename": filename,
                    "format": report_format,
                    "leads": [asdict(lead) for lead in leads],
                    "warnings": warnings,
                    "skipped": skipped,
                }
                result = await run_in_threadpool(
                    report_leads.import_report,
                    session,
                    run_kind=run_kind,
                    run_id=run_id,
                    content=content,
                    filename=filename,
                    preview=True,
                    prepared=data,
                )
                result["prepared"] = report_leads.sign_prepared(data, secret)
                return result
            if not prepared:
                raise report_leads.ReportImportError(
                    "Preview this report before importing it."
                )
            data = report_leads.verify_prepared(
                prepared, secret, run_kind, run_id, content
            )
            filename = data["filename"]
        else:
            if prepared:
                raise report_leads.ReportImportError("Preview this report again.")
            data = None
        return await run_in_threadpool(
            report_leads.import_report,
            session,
            run_kind=run_kind,
            run_id=run_id,
            content=content,
            filename=filename,
            preview=preview,
            prepared=data,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except report_leads.ReportImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()


@router.post("/api/test-runs/{run_id}/import-report")
async def import_web_report(
    run_id: int,
    request: Request,
    file: UploadFile = File(...),
    preview: bool = Form(default=True),
    prepared: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> dict:
    return await _import_report(
        "web", run_id, file, preview, prepared, request, session
    )


@router.post("/api/api-test-runs/{run_id}/import-report")
async def import_api_report(
    run_id: int,
    request: Request,
    file: UploadFile = File(...),
    preview: bool = Form(default=True),
    prepared: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> dict:
    return await _import_report(
        "api", run_id, file, preview, prepared, request, session
    )
