from __future__ import annotations

import base64
import binascii
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, SecretStr
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.services.settings import get_upstream_proxy_config

from .models import Dataset, PublishingSettings, PublishingUploadToken, ScanResult
from .transfer import dataset_key, identity


def site_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".chatgpt.site")
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter an HTTPS Sites URL without a path")
    return f"https://{parsed.hostname}"


def timestamp(value) -> str | None:
    if value is None:
        return None
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    )
    return (
        parsed.replace(tzinfo=timezone.utc).isoformat()
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc).isoformat()
    )


def model_summary(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {
        key: str(value[key]) if value.get(key) is not None else None
        for key in ("model", "name", "provider")
    }


def token_counts(core, row, models: dict) -> dict | None:
    from aespa.models import ApiTestRun, SastRun, TestRun

    if row.run_id <= 0:
        return None
    run_type = {"site": TestRun, "api": ApiTestRun, "sast": SastRun}.get(row.run_kind)
    if run_type is None:
        return None
    runs = [core.get(run_type, row.run_id)]
    if row.run_kind != "sast":
        source_ids = {
            source.get("run_id")
            for source in models.get("sast", [])
            if isinstance(source, dict) and isinstance(source.get("run_id"), int)
        }
        runs.extend(core.get(SastRun, source_id) for source_id in sorted(source_ids))
    totals = {key: 0 for key in ("input", "output", "cache_read", "cache_write")}
    recorded = False
    for run in runs:
        usage = json.loads(run.token_usage_json or "{}") if run else {}
        if not isinstance(usage, dict):
            continue
        for entry in usage.values():
            if not isinstance(entry, dict):
                continue
            for key in totals:
                value = entry.get(key)
                if type(value) is int and value >= 0:
                    totals[key] += value
                    recorded = True
    return totals if recorded else None


def graph_bundle(store) -> dict:
    from .router import result_out

    output = []
    with store.session() as session, Session(get_engine()) as core:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        for row in session.exec(select(ScanResult).order_by(ScanResult.id)):
            result = result_out(row, core)
            dataset = session.get(Dataset, row.dataset_id)
            if dataset is None:
                continue
            models = result.get("scan_models") or {}
            sources = models.get("sast") or []
            output.append(
                {
                    "id": identity(session, "results", row).key,
                    "dataset": {"key": dataset_key(dataset), "name": dataset.name},
                    "scan_type": "SAST"
                    if row.run_kind == "sast"
                    else "DAST with SAST Leads"
                    if sources
                    else "DAST",
                    "primary": model_summary(models.get("primary")),
                    "sast": [
                        {"model": model_summary(source.get("model"))}
                        for source in sources
                    ]
                    if row.run_kind != "sast"
                    else [],
                    "scan_started_at": timestamp(result.get("scan_started_at")),
                    "scan_cost_usd": result.get("scan_cost_usd"),
                    "tokens": token_counts(core, row, models),
                    "summary": result["summary"],
                    "score": result["score"],
                    "category_counts": result["category_counts"],
                    "category_totals": result["category_totals"],
                    "comment": result["comment"],
                    "updated_at": timestamp(row.updated_at),
                }
            )
        session.commit()
    return {"version": 1, "results": output}


CONNECTION_PREFIX = "aespa_publish_v1_"


def connection_token(url: str, service: str, upload: str) -> str:
    value = json.dumps(
        {"site_url": url, "service_token": service, "upload_token": upload},
        separators=(",", ":"),
    )
    return CONNECTION_PREFIX + base64.urlsafe_b64encode(value.encode()).decode().rstrip(
        "="
    )


def decode_connection_token(value: str, url: str) -> tuple[str, str]:
    error = "Enter an upload token generated on the results site"
    if len(value) > 32768 or not value.startswith(CONNECTION_PREFIX):
        raise ValueError(error)
    encoded = value[len(CONNECTION_PREFIX) :]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", encoded):
        raise ValueError(error)
    try:
        data = json.loads(
            base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            )
        )
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise ValueError(error) from None
    if (
        not isinstance(data, dict)
        or set(data) != {"site_url", "service_token", "upload_token"}
        or not all(isinstance(v, str) for v in data.values())
    ):
        raise ValueError(error)
    if data["site_url"] != url:
        raise ValueError("This token was generated for a different site")
    service, upload = data["service_token"], data["upload_token"]
    if not re.fullmatch(r"[\x21-\x7e]{1,8192}", service) or not re.fullmatch(
        r"aespa_upload_[a-f0-9]{64}", upload
    ):
        raise ValueError(error)
    return service, upload


class PublishingIn(BaseModel):
    site_url: str = Field(max_length=300)
    token: SecretStr | None = Field(default=None)
    service_token: SecretStr | None = Field(default=None)
    upload_token: SecretStr | None = Field(default=None)


def register_publishing(router: APIRouter, store) -> None:
    @router.get("/publishing")
    def get_publishing() -> dict:
        with store.session() as session:
            saved = session.get(PublishingSettings, 1)
            return {
                "site_url": saved.site_url if saved else "",
                "token_saved": bool(saved and saved.service_token),
                "upload_token_saved": bool(
                    (upload := session.get(PublishingUploadToken, 1)) and upload.token
                ),
            }

    @router.post("/publishing/token")
    def reveal_publishing_token() -> JSONResponse:
        with store.session() as session:
            saved = session.get(PublishingSettings, 1)
            if not saved or not saved.service_token:
                raise HTTPException(404, "No service token has been saved")
            upload = session.get(PublishingUploadToken, 1)
            if not upload or not upload.token:
                raise HTTPException(404, "No upload token has been saved")
            return JSONResponse(
                {
                    "token": connection_token(
                        saved.site_url, saved.service_token, upload.token
                    )
                },
                headers={"Cache-Control": "no-store"},
            )

    @router.put("/publishing")
    def save_publishing(payload: PublishingIn) -> dict:
        try:
            url = site_url(payload.site_url)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        with store.session() as session:
            saved = session.get(PublishingSettings, 1) or PublishingSettings()
            token = (
                payload.service_token.get_secret_value().strip()
                if payload.service_token is not None
                else None
            )
            upload = session.get(PublishingUploadToken, 1) or PublishingUploadToken()
            upload_token = (
                payload.upload_token.get_secret_value().strip()
                if payload.upload_token is not None
                else None
            )
            if payload.token is not None:
                if (
                    payload.service_token is not None
                    or payload.upload_token is not None
                ):
                    raise HTTPException(422, "Send only the generated upload token")
                try:
                    token, upload_token = decode_connection_token(
                        payload.token.get_secret_value().strip(), url
                    )
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from None
            # Never reuse a site's credential for a different site.
            if saved.site_url and saved.site_url != url and not token:
                raise HTTPException(422, "Enter a token generated for the new site")
            if saved.site_url and saved.site_url != url and not upload_token:
                raise HTTPException(422, "Enter a token generated for the new site")
            if upload_token is not None:
                if not re.fullmatch(r"aespa_upload_[a-f0-9]{64}", upload_token):
                    raise HTTPException(422, "Enter a valid upload token")
                upload.token = upload_token
            if not upload.token:
                raise HTTPException(
                    422, "Create an upload token on the results site and enter it here"
                )
            if token is not None:
                if (
                    not token
                    or len(token) > 8192
                    or any(char.isspace() for char in token)
                ):
                    raise HTTPException(422, "Enter a valid service token")
                saved.service_token = token
            if not saved.service_token:
                raise HTTPException(
                    422, "Enter an upload token generated on the results site"
                )
            saved.site_url = url
            session.add(saved)
            session.add(upload)
            session.commit()
        return {"site_url": url, "token_saved": True, "upload_token_saved": True}

    @router.get("/graph-export")
    def export_graphs() -> dict:
        return graph_bundle(store)

    @router.post("/publish")
    async def publish_graphs() -> dict:
        with store.session() as session:
            saved = session.get(PublishingSettings, 1)
            if not saved or not saved.site_url or not saved.service_token:
                raise HTTPException(422, "Save the site connection first")
            try:
                url = site_url(saved.site_url)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            upload = session.get(PublishingUploadToken, 1)
            if not upload or not upload.token:
                raise HTTPException(
                    422,
                    "Create an upload token on the results site and save it in connection settings",
                )
            token = saved.service_token
            upload_token = upload.token
        results = graph_bundle(store)["results"]
        batches, batch = [], []
        for result in results:
            candidate = [*batch, result]
            if (
                len(candidate) > 100
                or len(
                    json.dumps(
                        {"version": 1, "results": candidate}, ensure_ascii=False
                    ).encode()
                )
                > 262144
            ):
                if batch:
                    batches.append(batch)
                batch = [result]
            else:
                batch = candidate
            if (
                len(
                    json.dumps(
                        {"version": 1, "results": batch}, ensure_ascii=False
                    ).encode()
                )
                > 262144
            ):
                raise HTTPException(422, "A result is too large to publish")
        if batch:
            batches.append(batch)
        stored = skipped = sent = 0
        with Session(get_engine()) as core:
            network = get_upstream_proxy_config(core)
        client_options = {
            "timeout": 30,
            "follow_redirects": False,
            "trust_env": False,
            "verify": network.llm_ca_bundle_path or True,
        }
        if network.proxy_llm and network.llm_proxy_url:
            client_options["proxy"] = network.llm_proxy_url
        try:
            client = httpx.AsyncClient(**client_options)
        except (OSError, ValueError) as exc:
            raise HTTPException(
                502, "The configured CA bundle could not be loaded"
            ) from exc
        async with client:
            for batch in batches:
                try:
                    response = await client.post(
                        f"{url}/api/v1/results",
                        headers={
                            "OAI-Sites-Authorization": f"Bearer {token}",
                            "X-AESPA-Upload-Token": upload_token,
                            "Content-Type": "application/json",
                        },
                        content=json.dumps(
                            {"version": 1, "results": batch},
                            ensure_ascii=False,
                            allow_nan=False,
                        ).encode(),
                    )
                    if response.status_code in (401, 403):
                        raise HTTPException(
                            502,
                            f"Site access was rejected. Check the upload token. If access still fails, generate a new token on the results site. {sent} results sent.",
                        )
                    if not response.is_success:
                        raise HTTPException(
                            502,
                            f"The site rejected the upload (HTTP {response.status_code}). {sent} results sent. You can retry safely.",
                        )
                    report = response.json()
                    if (
                        not isinstance(report, dict)
                        or report.get("received") != len(batch)
                        or not all(
                            isinstance(report.get(key), int) and report[key] >= 0
                            for key in ("stored", "skipped_stale")
                        )
                        or report["stored"] + report["skipped_stale"] != len(batch)
                    ):
                        raise ValueError("Invalid upload receipt")
                except (httpx.HTTPError, ValueError, TypeError) as exc:
                    raise HTTPException(
                        502,
                        f"The upload could not be confirmed. {sent} results sent. You can retry safely.",
                    ) from exc
                sent += len(batch)
                stored += report["stored"]
                skipped += report["skipped_stale"]
        return {
            "received": sent,
            "stored": stored,
            "skipped_stale": skipped,
            "site_url": url,
        }
