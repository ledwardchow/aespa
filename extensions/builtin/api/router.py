"""Routes for API v1 and the settings page's token management."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    UploadFile,
)
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import select

from aespa.extensions import ExtensionDataStore, get_extension_manager
from aespa.schemas import StartCrawlBody, TestRunCreate, WebCoverageModeLiteral

from . import examples, scans
from .auth import (
    SCOPES,
    Caller,
    aware,
    hash_token,
    new_secret,
    new_token,
    require_local_admin,
    scope_dependency,
    token_scopes,
)
from .models import ApiDelivery, ApiScan, ApiToken, now
from .schemas import (
    ERRORS,
    SCAN_ID_PATTERN,
    ActivityPage,
    CallbackConfig,
    CredentialCreate,
    CredentialOut,
    Delivery,
    FindingPage,
    LlmProfile,
    ScanList,
    ScanStatus,
    Severity,
    SiteIn,
    SiteOut,
    SourceScanCreate,
    StopResult,
    Summary,
    TokenInfo,
    WebScanCreate,
)

ScanIdPath = Annotated[
    str,
    Path(
        pattern=SCAN_ID_PATTERN,
        description="Scan ID returned when the scan was created, such as web-42.",
        examples=["web-42"],
    ),
]
IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description=(
            "Any unique value. Repeating a request with the same key returns the "
            "first response instead of starting another scan. Kept for 24 hours."
        ),
    ),
]
MAX_WAIT_SECONDS = 60
RUN_OPTION_FIELDS = set(TestRunCreate.model_fields)
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def _scopes(*names: str) -> dict:
    return {"x-aespa-scopes": list(names)}


def _status_model(body: dict[str, Any]) -> dict[str, Any]:
    """Check a response against the public model before sending it."""
    return ScanStatus.model_validate(body).model_dump(mode="json")


class StartFailed(Exception):
    def __init__(self, scan_id: str, error: HTTPException):
        super().__init__(error.detail)
        self.scan_id = scan_id
        self.error = error


def _iso(value: datetime | None) -> str | None:
    value = aware(value)
    return value.isoformat() if value else None


def _delivery(row: ApiDelivery) -> dict[str, Any]:
    return {
        "id": row.delivery_id,
        "event": row.event,
        "url": row.url,
        "status": row.status,
        "attempts": row.attempts,
        "last_status_code": row.last_status_code,
        "last_error": row.last_error,
        "created_at": _iso(row.created_at),
        "delivered_at": _iso(row.delivered_at),
        "next_attempt_at": _iso(row.next_attempt_at)
        if row.status == "pending"
        else None,
    }


class ScanStartBody(BaseModel):
    coverage_mode: WebCoverageModeLiteral | None = Field(
        default=None,
        description="Web scans only. Overrides the mode chosen at creation.",
    )


ScanAccess = Literal["own", "all"]


class TokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[Literal["sast", "web", "sites"]] = Field(min_length=1)
    scan_access: ScanAccess = "own"
    webhook_url: str | None = None


class TokenUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    scopes: list[Literal["sast", "web", "sites"]] | None = None
    scan_access: ScanAccess | None = None
    webhook_url: str | None = Field(
        default=None, description="An empty string removes the default webhook."
    )


def _check_webhook_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(CallbackConfig(url=value).url)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail="Enter a full http or https URL."
        ) from exc


def _token_out(row: ApiToken) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "prefix": row.token_prefix,
        "scopes": token_scopes(row),
        "scan_access": row.scan_access,
        "active": row.deactivated_at is None,
        "can_show_token": bool(row.token_value),
        "webhook_url": row.webhook_url,
        "has_webhook_secret": bool(row.webhook_secret),
        "created_at": _iso(row.created_at),
        "last_used_at": _iso(row.last_used_at),
        "deactivated_at": _iso(row.deactivated_at),
    }


def build_router(store: ExtensionDataStore, core) -> APIRouter:
    router = APIRouter()
    require = scope_dependency(store)

    # ── Helpers that need the store and core ────────────────────────────────

    def status_for(row: ApiScan, created_secret: str | None = None) -> dict[str, Any]:
        body = scans.status_payload(core, row)
        if created_secret and body.get("callbacks"):
            body["callbacks"]["secret"] = created_secret
        return _status_model(body)

    async def run_create(
        caller: Caller,
        key: str | None,
        digest: str,
        create,
        *,
        cleanup=None,
    ) -> JSONResponse:
        saved = scans.claim_key(store, caller, key, digest)
        if saved is not None:
            if cleanup is not None:
                cleanup()
            return JSONResponse(saved[1], status_code=saved[0])
        try:
            body = await create()
        except StartFailed as failure:
            detail = {"message": failure.error.detail, "scan_id": failure.scan_id}
            scans.save_key(
                store, caller, key, failure.error.status_code, {"detail": detail}
            )
            raise HTTPException(
                status_code=failure.error.status_code, detail=detail
            ) from None
        except BaseException:
            scans.release_key(store, caller, key)
            raise
        scans.save_key(store, caller, key, 201, body)
        return JSONResponse(body, status_code=201)

    async def start_web(row: ApiScan) -> None:
        options = scans.start_options(row)
        await core.web.start(
            row.run_id,
            StartCrawlBody(
                crawl_credential_id=options.get("crawl_credential_id"),
                start_pentest_after_crawl=row.scan_after_crawl,
                coverage_mode=options.get("coverage_mode"),
            ),
        )

    # ── OpenAPI definition ──────────────────────────────────────────────────

    @router.get("/v1/openapi.json", include_in_schema=False)
    def openapi_document() -> dict:
        document = get_extension_manager().openapi_for(scans.EXTENSION_ID)
        if document is None:
            raise HTTPException(status_code=404, detail="Not found")
        return document

    # ── Sites ───────────────────────────────────────────────────────────────

    @router.get(
        "/v1/sites",
        response_model=list[SiteOut],
        operation_id="listSites",
        summary="List Sites",
        tags=["Sites"],
        responses=ERRORS,
        openapi_extra=_scopes("sites"),
    )
    def list_sites(caller: Caller = Depends(require("sites"))):
        return core.web.list_sites()

    @router.post(
        "/v1/sites",
        response_model=SiteOut,
        status_code=201,
        operation_id="createSite",
        summary="Create a Site",
        description=(
            "Create a Site with its scope, accounts, workflows, and scan guidance. "
            "With upsert=true, a Site with the same name is replaced instead "
            "(PUT semantics, so send every credential's password again)."
        ),
        tags=["Sites"],
        responses=ERRORS,
        openapi_extra=_scopes("sites"),
    )
    def create_site(
        payload: Annotated[SiteIn, Body(openapi_examples=examples.SITE)],
        upsert: bool = Query(False, description="Replace a Site with the same name."),
        caller: Caller = Depends(require("sites")),
    ):
        existing = core.web.find_site_id(payload.name)
        if existing is not None and upsert:
            return JSONResponse(
                SiteOut.model_validate(
                    core.web.update_site(existing, payload)
                ).model_dump(mode="json"),
                status_code=200,
            )
        return core.web.create_site(payload)

    @router.get(
        "/v1/sites/{site_id}",
        response_model=SiteOut,
        operation_id="getSite",
        summary="Get a Site",
        tags=["Sites"],
        responses=ERRORS,
        openapi_extra=_scopes("sites"),
    )
    def get_site(site_id: int, caller: Caller = Depends(require("sites"))):
        return core.web.get_site(site_id)

    @router.put(
        "/v1/sites/{site_id}",
        response_model=SiteOut,
        operation_id="replaceSite",
        summary="Replace a Site",
        description=(
            "Replace every field. Credentials not listed are removed. Include a "
            "credential's id to keep it; its password must be sent again."
        ),
        tags=["Sites"],
        responses=ERRORS,
        openapi_extra=_scopes("sites"),
    )
    def replace_site(
        site_id: int,
        payload: Annotated[SiteIn, Body(openapi_examples=examples.SITE)],
        caller: Caller = Depends(require("sites")),
    ):
        return core.web.update_site(site_id, payload)

    @router.post(
        "/v1/sites/{site_id}/credentials",
        response_model=CredentialOut,
        status_code=201,
        operation_id="addSiteCredential",
        summary="Add an account to a Site",
        tags=["Sites"],
        responses=ERRORS,
        openapi_extra=_scopes("sites"),
    )
    def add_credential(
        site_id: int,
        payload: Annotated[
            CredentialCreate, Body(openapi_examples=examples.CREDENTIAL)
        ],
        caller: Caller = Depends(require("sites")),
    ):
        return core.web.add_credential(site_id, payload)

    @router.delete(
        "/v1/sites/{site_id}/credentials/{credential_id}",
        status_code=204,
        operation_id="deleteSiteCredential",
        summary="Remove an account from a Site",
        tags=["Sites"],
        responses=ERRORS,
        openapi_extra=_scopes("sites"),
    )
    def delete_credential(
        site_id: int, credential_id: int, caller: Caller = Depends(require("sites"))
    ) -> Response:
        core.web.delete_credential(site_id, credential_id)
        return Response(status_code=204)

    # ── Create scans ────────────────────────────────────────────────────────

    @router.post(
        "/v1/web/scans",
        response_model=ScanStatus,
        status_code=201,
        operation_id="createWebScan",
        summary="Create and start a web scan",
        description=(
            "Uses an existing Site (site_id) or creates one (site). By default the "
            "crawl starts at once and the dynamic scan follows when the crawl "
            "succeeds. If the scan was created but could not start, the error's "
            "detail includes its scan_id; fix the problem and call the start route."
        ),
        tags=["Web scans"],
        responses=ERRORS,
        openapi_extra=_scopes("web"),
    )
    async def create_web_scan(
        payload: Annotated[WebScanCreate, Body(openapi_examples=examples.WEB_SCAN)],
        idempotency_key: IdempotencyKey = None,
        caller: Caller = Depends(require("web")),
    ):
        if (payload.site_id is None) == (payload.site is None):
            raise HTTPException(status_code=422, detail="Send either site_id or site.")
        if payload.site is not None and "sites" not in caller.scopes:
            raise HTTPException(
                status_code=403,
                detail="Creating a Site needs a token with the sites scope.",
            )
        digest = scans.request_hash("web", payload.model_dump(mode="json"))

        def guided(credentials: list[tuple[int | None, str]]) -> None:
            if not payload.unattended:
                return
            people = [
                cred_id
                for cred_id, mode in credentials
                if mode == "guided" and (payload.crawl_credential_id in (None, cred_id))
            ]
            if people:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "This Site has an account that a person must sign in to "
                        "(auth_mode guided). Set unattended to false to allow it, "
                        "and watch for the needs_action state."
                    ),
                )

        async def create() -> dict[str, Any]:
            web = core.web
            if payload.site is not None:
                guided([(None, cred.auth_mode) for cred in payload.site.credentials])
                existing = web.find_site_id(payload.site.name)
                if existing is not None and not payload.update_site:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"A Site named {payload.site.name!r} already exists "
                            f"(id {existing}). Send site_id, or set update_site."
                        ),
                    )
                site = (
                    web.update_site(existing, payload.site)
                    if existing is not None
                    else web.create_site(payload.site)
                )
            else:
                site = web.get_site(payload.site_id)
                guided(
                    [(cred["id"], cred["auth_mode"]) for cred in site["credentials"]]
                )
            run_id = web.create_run(
                site["id"],
                TestRunCreate(**payload.model_dump(include=RUN_OPTION_FIELDS)),
            )
            row, secret = scans.record_scan(
                store,
                caller,
                run_id=run_id,
                kind="web",
                scan_after_crawl=payload.scan_after_crawl,
                callbacks=payload.callbacks,
                start_options={
                    "crawl_credential_id": payload.crawl_credential_id,
                    "coverage_mode": payload.coverage_mode,
                },
            )
            if payload.start:
                try:
                    await start_web(row)
                except HTTPException as exc:
                    raise StartFailed(scans.scan_id("web", run_id), exc) from exc
            return status_for(row, secret)

        return await run_create(caller, idempotency_key, digest, create)

    @router.post(
        "/v1/sast/scans",
        response_model=ScanStatus,
        status_code=201,
        operation_id="createSastScan",
        summary="Create and start a SAST scan from a ZIP file",
        tags=["SAST scans"],
        responses={**ERRORS, **examples.created(examples.SAST_SCAN_STATUS)},
        openapi_extra=_scopes("sast"),
    )
    async def create_sast_scan(
        file: UploadFile = File(
            description="Source code as a ZIP file, up to 250 MiB."
        ),
        name: str | None = Form(default=None),
        analysis_mode: Literal["light", "deep"] = Form(default="deep"),
        llm_config_id: int | None = Form(default=None),
        llm_profile_id: int | None = Form(default=None),
        start: bool = Form(default=True),
        callbacks: str | None = Form(
            default=None,
            description="Callback settings as a JSON object, in the CallbackConfig shape.",
        ),
        idempotency_key: IdempotencyKey = None,
        caller: Caller = Depends(require("sast")),
    ):
        callback_config = None
        if callbacks:
            try:
                callback_config = CallbackConfig.model_validate_json(callbacks)
            except ValidationError as exc:
                raise HTTPException(
                    status_code=422, detail=json.loads(exc.json())
                ) from exc
        sast = core.sast
        sast.check_analysis_mode(analysis_mode)
        archive = await sast.store_upload(file.read, file.filename)
        digest = scans.request_hash(
            "sast",
            archive.sha256,
            name,
            analysis_mode,
            llm_config_id,
            llm_profile_id,
            start,
            callbacks,
        )

        async def create() -> dict[str, Any]:
            run_id = sast.create_from_archive(
                archive,
                name=name,
                analysis_mode=analysis_mode,
                llm_config_id=llm_config_id,
                llm_profile_id=llm_profile_id,
                metadata={"created_via": scans.EXTENSION_ID},
            )
            row, secret = scans.record_scan(
                store,
                caller,
                run_id=run_id,
                kind="sast",
                scan_after_crawl=False,
                callbacks=callback_config,
            )
            if start:
                try:
                    await sast.start(run_id)
                except HTTPException as exc:
                    raise StartFailed(scans.scan_id("sast", run_id), exc) from exc
            return status_for(row, secret)

        return await run_create(
            caller,
            idempotency_key,
            digest,
            create,
            cleanup=lambda: archive.path.unlink(missing_ok=True),
        )

    @router.post(
        "/v1/sast/scans/from-source",
        response_model=ScanStatus,
        status_code=201,
        operation_id="createSastScanFromSource",
        summary="Create a SAST scan from a source provider",
        description=(
            "Prepares source through an enabled SAST source extension, such as "
            "GitHub repository. The scan starts when the source is ready."
        ),
        tags=["SAST scans"],
        responses={**ERRORS, **examples.created(examples.SAST_SCAN_STATUS)},
        openapi_extra=_scopes("sast"),
    )
    async def create_sast_scan_from_source(
        payload: Annotated[
            SourceScanCreate, Body(openapi_examples=examples.SOURCE_SCAN)
        ],
        idempotency_key: IdempotencyKey = None,
        caller: Caller = Depends(require("sast")),
    ):
        digest = scans.request_hash("sast-source", payload.model_dump(mode="json"))

        async def create() -> dict[str, Any]:
            run_id = await core.sast.create_from_source(
                provider_id=payload.provider_id,
                parameters=payload.parameters,
                name=payload.name,
                analysis_mode=payload.analysis_mode,
                llm_profile_id=payload.llm_profile_id,
                start_scan=payload.start,
                metadata={"created_via": scans.EXTENSION_ID},
            )
            row, secret = scans.record_scan(
                store,
                caller,
                run_id=run_id,
                kind="sast",
                scan_after_crawl=False,
                callbacks=payload.callbacks,
            )
            return status_for(row, secret)

        return await run_create(caller, idempotency_key, digest, create)

    # ── The calling token ───────────────────────────────────────────────────

    @router.get(
        "/v1/token",
        response_model=TokenInfo,
        operation_id="getToken",
        summary="Describe the token sending the request",
        description="Shows the token's scopes and which scans it can see.",
        tags=["Tokens"],
        responses=ERRORS,
    )
    def get_token(caller: Caller = Depends(require())):
        with store.session() as session:
            row = session.get(ApiToken, caller.token_id)
        return {
            "name": row.name,
            "prefix": row.token_prefix,
            "scopes": token_scopes(row),
            "scan_access": row.scan_access,
        }

    # ── LLM profiles ────────────────────────────────────────────────────────

    @router.get(
        "/v1/llm-profiles",
        response_model=list[LlmProfile],
        operation_id="listLlmProfiles",
        summary="List scan profiles",
        description=(
            "Scan profiles choose the LLM models AESPA uses. Send a profile's id as "
            "llm_profile_id when creating a scan, or leave it out to use the active "
            "profile."
        ),
        tags=["LLM profiles"],
        responses=ERRORS,
    )
    def list_llm_profiles(caller: Caller = Depends(require())):
        return core.llm.profiles()

    # ── Read and control scans ──────────────────────────────────────────────

    @router.get(
        "/v1/scans",
        response_model=ScanList,
        operation_id="listScans",
        summary="List the scans this token can see",
        description=(
            "Newest first. A token set to its own scans sees only scans it created. "
            "A token set to all scans sees every web or SAST scan its scopes allow, "
            "including scans started in AESPA; those have no callbacks."
        ),
        tags=["Scans"],
        responses=ERRORS,
    )
    def list_scans(
        kind: Literal["web", "sast"] | None = None,
        offset: int = Query(0, ge=0),
        limit: int = Query(25, ge=1, le=100),
        caller: Caller = Depends(require()),
    ):
        rows, total = scans.list_visible(store, core, caller, kind, offset, limit)
        items = []
        for row in rows:
            try:
                items.append(status_for(row))
            except HTTPException:
                continue  # The run was deleted in AESPA.
        return {"items": items, "total": total, "offset": offset, "limit": limit}

    @router.get(
        "/v1/scans/{scan_id}",
        response_model=ScanStatus,
        operation_id="getScan",
        summary="Get a scan's status and progress",
        description=(
            "Responses carry an ETag. Send it as If-None-Match to get 304 when "
            "nothing changed. With wait, the request is held for up to that many "
            "seconds until the status differs from If-None-Match (or from the "
            "status when the request arrived)."
        ),
        tags=["Scans"],
        responses={**ERRORS, 304: {"description": "Not changed"}},
    )
    async def get_scan(
        scan_id: ScanIdPath,
        wait: int = Query(
            0, ge=0, le=MAX_WAIT_SECONDS, description="Seconds to wait for a change."
        ),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
        caller: Caller = Depends(require()),
    ):
        row = scans.get_visible(store, core, caller, scan_id)

        def current() -> tuple[dict[str, Any], str]:
            body = status_for(row)
            digest = hashlib.sha256(
                json.dumps(body, sort_keys=True).encode("utf-8")
            ).hexdigest()[:32]
            return body, f'"{digest}"'

        body, etag = current()
        known = if_none_match or (etag if wait else None)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait
        while (
            wait
            and etag == known
            and body["state"]
            not in {
                "completed",
                "failed",
                "stopped",
            }
        ):
            if loop.time() >= deadline:
                break
            await asyncio.sleep(1)
            body, etag = current()
        if if_none_match and etag == if_none_match:
            return Response(status_code=304, headers={"ETag": etag})
        return JSONResponse(body, headers={"ETag": etag, "Cache-Control": "no-store"})

    @router.post(
        "/v1/scans/{scan_id}/start",
        response_model=ScanStatus,
        operation_id="startScan",
        summary="Start a scan that was created with start=false or failed to start",
        tags=["Scans"],
        responses=ERRORS,
    )
    async def start_scan(
        scan_id: ScanIdPath,
        caller: Caller = Depends(require()),
    ):
        row = scans.get_visible(store, core, caller, scan_id)
        _require_kind_scope(caller, row)
        if row.kind == "web":
            await start_web(row)
        else:
            await core.sast.start(row.run_id)
        return status_for(row)

    @router.post(
        "/v1/web/scans/{scan_id}/scan",
        response_model=ScanStatus,
        operation_id="startWebDynamicScan",
        summary="Start the dynamic scan on a crawled web scan",
        description="For web scans created with scan_after_crawl=false.",
        tags=["Web scans"],
        responses=ERRORS,
        openapi_extra=_scopes("web"),
    )
    async def start_dynamic_scan(
        scan_id: ScanIdPath,
        payload: ScanStartBody | None = Body(
            default=None, openapi_examples=examples.START_SCAN
        ),
        caller: Caller = Depends(require("web")),
    ):
        row = scans.get_visible(store, core, caller, scan_id)
        if row.kind != "web":
            raise HTTPException(status_code=409, detail="This is not a web scan.")
        coverage_mode = (
            payload.coverage_mode if payload else None
        ) or scans.start_options(row).get("coverage_mode")
        await core.web.start_scan(row.run_id, coverage_mode)
        return status_for(row)

    @router.post(
        "/v1/sast/scans/{scan_id}/resume",
        response_model=ScanStatus,
        operation_id="resumeSastScan",
        summary="Resume a paused SAST scan",
        description=(
            "Continues a paused SAST scan, or a finished one with unfinished work, "
            "from its saved progress. Check the scan's resumable field first. "
            "POST /scans/{scan_id}/start starts the scan over instead."
        ),
        tags=["SAST scans"],
        responses=ERRORS,
        openapi_extra=_scopes("sast"),
    )
    async def resume_sast_scan(
        scan_id: ScanIdPath,
        caller: Caller = Depends(require("sast")),
    ):
        row = scans.get_visible(store, core, caller, scan_id)
        if row.kind != "sast":
            raise HTTPException(status_code=409, detail="This is not a SAST scan.")
        await core.sast.resume(row.run_id)
        return status_for(row)

    @router.post(
        "/v1/scans/{scan_id}/stop",
        response_model=StopResult,
        operation_id="stopScan",
        summary="Stop a scan",
        tags=["Scans"],
        responses=ERRORS,
    )
    async def stop_scan(scan_id: ScanIdPath, caller: Caller = Depends(require())):
        row = scans.get_visible(store, core, caller, scan_id)
        _require_kind_scope(caller, row)
        if row.kind == "web":
            stopped = core.web.stop(row.run_id)
        else:
            stopped = await core.sast.stop(row.run_id)
        await asyncio.sleep(0)
        return {"stopped": stopped, "scan": status_for(row)}

    @router.get(
        "/v1/scans/{scan_id}/activity",
        response_model=ActivityPage,
        operation_id="getScanActivity",
        summary="Read the scan's activity log",
        tags=["Scans"],
        responses=ERRORS,
    )
    def get_activity(
        scan_id: ScanIdPath,
        after: int = Query(0, ge=0, description="next_cursor from the previous page."),
        limit: int = Query(100, ge=1, le=500),
        caller: Caller = Depends(require()),
    ):
        row = scans.get_visible(store, core, caller, scan_id)
        items = core.runs.activity(row.run_id, after=after, limit=limit)
        return {
            "items": items,
            "next_cursor": items[-1]["cursor"] if items else after,
        }

    def _findings(row: ApiScan, severity: str | None, include_dismissed: bool):
        wanted = None
        if severity:
            wanted = {
                value.strip().lower() for value in severity.split(",") if value.strip()
            }
            unknown = wanted - set(SEVERITY_ORDER)
            if unknown:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown severity: {', '.join(sorted(unknown))}",
                )
        items = core.runs.findings(
            row.run_id, severities=wanted, include_dismissed=include_dismissed
        )
        if items is None:
            raise HTTPException(
                status_code=404, detail="This scan's run was deleted in AESPA."
            )
        return items

    @router.get(
        "/v1/scans/{scan_id}/findings",
        response_model=FindingPage,
        operation_id="listScanFindings",
        summary="List the scan's findings",
        description="Most severe first. Available while the scan runs (partial=true).",
        tags=["Results"],
        responses=ERRORS,
    )
    def list_findings(
        scan_id: ScanIdPath,
        severity: str | None = Query(
            None, description="Comma-separated severities, for example high,critical."
        ),
        include_dismissed: bool = Query(
            False, description="Include findings marked false positive or dismissed."
        ),
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        caller: Caller = Depends(require()),
    ):
        row = scans.get_visible(store, core, caller, scan_id)
        items = _findings(row, severity, include_dismissed)
        progress = core.runs.progress(row.run_id, scan_after_crawl=row.scan_after_crawl)
        return {
            "scan_id": scan_id,
            "partial": bool(progress)
            and progress["state"] not in {"completed", "failed", "stopped"},
            "items": items[offset : offset + limit],
            "total": len(items),
            "offset": offset,
            "limit": limit,
        }

    @router.get(
        "/v1/scans/{scan_id}/summary",
        response_model=Summary,
        operation_id="getScanSummary",
        summary="Count findings and check a CI gate",
        description="With fail_on, gate.passed is false when any finding is at or above that severity.",
        tags=["Results"],
        responses=ERRORS,
    )
    def get_summary(
        scan_id: ScanIdPath,
        fail_on: Severity | None = None,
        include_dismissed: bool = False,
        caller: Caller = Depends(require()),
    ):
        row = scans.get_visible(store, core, caller, scan_id)
        items = _findings(row, None, include_dismissed)
        status = status_for(row)
        duration = None
        if status["started_at"]:
            started = datetime.fromisoformat(status["started_at"])
            ended = (
                datetime.fromisoformat(status["finished_at"])
                if status["finished_at"]
                else now()
            )
            duration = max(0.0, (ended - started).total_seconds())
        return {
            "scan_id": scan_id,
            "state": status["state"],
            "partial": status["state"] not in {"completed", "failed", "stopped"},
            "duration_seconds": duration,
            **core.runs.summarize(items, fail_on=fail_on),
        }

    @router.get(
        "/v1/scans/{scan_id}/sarif",
        operation_id="getScanSarif",
        summary="Download results as SARIF 2.1.0",
        description=(
            "Returns web or SAST results as a SARIF 2.1.0 document for GitHub "
            "code scanning and other tools. Web results have one rule per OWASP "
            "category and use the affected URL as the location. Web findings "
            "marked as false positives are left out unless include_dismissed is "
            "true, when they are included as suppressed results. SAST results "
            "include reportable findings only."
        ),
        tags=["Results"],
        responses={
            **ERRORS,
            200: {
                "description": "SARIF 2.1.0 document",
                "content": {"application/sarif+json": {"schema": {"type": "object"}}},
            },
        },
    )
    def get_sarif(
        scan_id: ScanIdPath,
        include_dismissed: bool = Query(
            False,
            description=(
                "Web scans only: include findings marked as false positives, "
                "as suppressed results."
            ),
        ),
        caller: Caller = Depends(require()),
    ):
        row = scans.get_visible(store, core, caller, scan_id)
        if row.kind == "web":
            document = core.runs.web_sarif(
                row.run_id, include_false_positives=include_dismissed
            )
        else:
            document = core.runs.sast_sarif(row.run_id)
        if document is None:
            raise HTTPException(
                status_code=404, detail="This scan's run was deleted in AESPA."
            )
        return JSONResponse(document, media_type="application/sarif+json")

    # ── Callback deliveries ─────────────────────────────────────────────────

    @router.get(
        "/v1/scans/{scan_id}/deliveries",
        response_model=list[Delivery],
        operation_id="listScanDeliveries",
        summary="List callbacks sent for a scan",
        tags=["Callbacks"],
        responses=ERRORS,
    )
    def list_deliveries(scan_id: ScanIdPath, caller: Caller = Depends(require())):
        row = scans.get_visible(store, core, caller, scan_id)
        if row.id is None:
            return []
        with store.session() as session:
            rows = session.exec(
                select(ApiDelivery)
                .where(ApiDelivery.scan_id == row.id)
                .order_by(ApiDelivery.id)
            ).all()
        return [_delivery(item) for item in rows]

    @router.post(
        "/v1/deliveries/{delivery_id}/redeliver",
        response_model=Delivery,
        operation_id="redeliverCallback",
        summary="Send a callback again",
        tags=["Callbacks"],
        responses=ERRORS,
    )
    def redeliver(delivery_id: str, caller: Caller = Depends(require())):
        with store.session() as session:
            item = session.exec(
                select(ApiDelivery).where(ApiDelivery.delivery_id == delivery_id)
            ).first()
            owner = session.get(ApiScan, item.scan_id) if item else None
            if item is None or owner is None:
                raise HTTPException(status_code=404, detail="Delivery not found")
            try:
                scans.get_visible(
                    store, core, caller, scans.scan_id(owner.kind, owner.run_id)
                )
            except HTTPException:
                raise HTTPException(
                    status_code=404, detail="Delivery not found"
                ) from None
            item.status = "pending"
            item.attempts = 0
            item.next_attempt_at = now()
            item.last_error = None
            session.add(item)
            session.commit()
            session.refresh(item)
            return _delivery(item)

    def _require_kind_scope(caller: Caller, row: ApiScan) -> None:
        if row.kind not in caller.scopes:
            raise HTTPException(
                status_code=403,
                detail=f"This token does not have the {row.kind} scope.",
            )

    # ── Token management (settings page only) ───────────────────────────────

    admin_only = {
        "include_in_schema": False,
        "dependencies": [Depends(require_local_admin)],
    }

    @router.get("/admin/tokens", **admin_only)
    def admin_list_tokens() -> list[dict]:
        with store.session() as session:
            rows = session.exec(select(ApiToken).order_by(ApiToken.id)).all()
        return [_token_out(row) for row in rows]

    @router.post("/admin/tokens", status_code=201, **admin_only)
    def admin_create_token(payload: TokenCreate) -> dict:
        token = new_token()
        webhook_url = _check_webhook_url(payload.webhook_url)
        secret = new_secret() if webhook_url else None
        row = ApiToken(
            name=payload.name.strip(),
            token_hash=hash_token(token),
            token_prefix=token[:12],
            token_value=token,
            scopes_json=json.dumps(sorted(set(payload.scopes))),
            scan_access=payload.scan_access,
            webhook_url=webhook_url,
            webhook_secret=secret,
        )
        with store.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
        return {**_token_out(row), "token": token, "webhook_secret": secret}

    def _admin_token(session, token_id: int) -> ApiToken:
        row = session.get(ApiToken, token_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Token not found")
        return row

    @router.patch("/admin/tokens/{token_id}", **admin_only)
    def admin_update_token(token_id: int, payload: TokenUpdate) -> dict:
        secret = None
        with store.session() as session:
            row = _admin_token(session, token_id)
            if payload.name is not None:
                row.name = payload.name.strip()
            if payload.scopes is not None:
                if not payload.scopes:
                    raise HTTPException(
                        status_code=422, detail="Choose at least one scope."
                    )
                row.scopes_json = json.dumps(sorted(set(payload.scopes)))
            if payload.scan_access is not None:
                row.scan_access = payload.scan_access
            if payload.webhook_url is not None:
                row.webhook_url = _check_webhook_url(payload.webhook_url)
                if row.webhook_url and not row.webhook_secret:
                    row.webhook_secret = secret = new_secret()
            session.add(row)
            session.commit()
            session.refresh(row)
            return {**_token_out(row), "webhook_secret": secret}

    @router.post("/admin/tokens/{token_id}/webhook-secret", **admin_only)
    def admin_rotate_secret(token_id: int) -> dict:
        with store.session() as session:
            row = _admin_token(session, token_id)
            row.webhook_secret = new_secret()
            session.add(row)
            session.commit()
            return {"webhook_secret": row.webhook_secret}

    def _set_active(token_id: int, active: bool) -> dict:
        with store.session() as session:
            row = _admin_token(session, token_id)
            if active != (row.deactivated_at is None):
                row.deactivated_at = None if active else now()
                session.add(row)
                session.commit()
                session.refresh(row)
            return _token_out(row)

    @router.post("/admin/tokens/{token_id}/deactivate", **admin_only)
    def admin_deactivate_token(token_id: int) -> dict:
        return _set_active(token_id, False)

    @router.post("/admin/tokens/{token_id}/reactivate", **admin_only)
    def admin_reactivate_token(token_id: int) -> dict:
        return _set_active(token_id, True)

    @router.get("/admin/tokens/{token_id}/token", **admin_only)
    def admin_show_token(token_id: int) -> dict:
        with store.session() as session:
            row = _admin_token(session, token_id)
        if not row.token_value:
            raise HTTPException(
                status_code=409,
                detail=(
                    "This token was created before AESPA kept tokens, so it can't "
                    "be shown. Create a new token to replace it."
                ),
            )
        return {"token": row.token_value}

    @router.get("/admin/deliveries", **admin_only)
    def admin_recent_deliveries(
        status: Literal["pending", "delivered", "failed"] | None = None,
        limit: int = Query(20, ge=1, le=100),
    ) -> list[dict]:
        with store.session() as session:
            query = select(ApiDelivery, ApiScan).where(
                ApiDelivery.scan_id == ApiScan.id
            )
            if status:
                query = query.where(ApiDelivery.status == status)
            rows = session.exec(
                query.order_by(ApiDelivery.id.desc()).limit(limit)
            ).all()
        return [
            {**_delivery(item), "scan_id": scans.scan_id(scan.kind, scan.run_id)}
            for item, scan in rows
        ]

    @router.get("/admin/scopes", **admin_only)
    def admin_scopes() -> list[str]:
        return list(SCOPES)

    return router
