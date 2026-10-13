"""Preview and import external scanner reports into web and API runs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool

from aespa.db import get_session
from aespa.services import report_leads

router = APIRouter(tags=["scan-leads"])


async def _import_report(
    run_kind: str, run_id: int, file: UploadFile, preview: bool, session: Session
) -> dict:
    try:
        content = await file.read(report_leads.MAX_REPORT_BYTES + 1)
        return await run_in_threadpool(
            report_leads.import_report,
            session,
            run_kind=run_kind,
            run_id=run_id,
            content=content,
            filename=file.filename or "report",
            preview=preview,
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
    file: UploadFile = File(...),
    preview: bool = Form(default=True),
    session: Session = Depends(get_session),
) -> dict:
    return await _import_report("web", run_id, file, preview, session)


@router.post("/api/api-test-runs/{run_id}/import-report")
async def import_api_report(
    run_id: int,
    file: UploadFile = File(...),
    preview: bool = Form(default=True),
    session: Session = Depends(get_session),
) -> dict:
    return await _import_report("api", run_id, file, preview, session)
