"""Core-owned run services offered to extensions.

Extensions must not write to AESPA's main database. Extensions that declare
``core.sast_runs`` or ``core.web_runs`` may instead ask AESPA to create, start,
and stop runs (and, for web runs, Sites and credentials) through these classes.
AESPA code makes and checks every change, using the same services as the
``/api`` routes. Read methods are available to every extension.

Errors are raised as ``fastapi.HTTPException`` with the same status codes and
messages as the matching ``/api`` routes.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import Credential, LLMProfile, SastRun, Site, TestRun
from aespa.schemas import (
    CredentialIn,
    SiteCreate,
    SiteUpdate,
    StartCrawlBody,
    TestRunCreate,
)
from aespa.services import run_lifecycle, run_progress, run_results, settings_profiles
from aespa.services import sast_runs_service as sast_runs
from aespa.services import sites as sites_service
from aespa.services import web_runs_service as web_runs


def _session() -> Session:
    return Session(get_engine())


def credential_dict(cred: Credential) -> dict[str, Any]:
    """Describe a credential without passwords, TOTP seeds, or sensitive values."""
    try:
        fields = json.loads(cred.login_fields_json or "[]")
    except (TypeError, ValueError):
        fields = []
    return {
        "id": cred.id,
        "label": cred.label,
        "username": cred.username or None,
        "login_url": cred.login_url,
        "auth_mode": cred.auth_mode or "auto",
        "test_mailbox_url": cred.test_mailbox_url,
        "has_password": bool(cred.password),
        "has_totp_seed": bool((cred.totp_seed or "").strip()),
        "login_fields": [
            {
                "key": field.get("key"),
                "label": field.get("label"),
                "sensitive": bool(field.get("sensitive")),
                "selector": field.get("selector"),
                "value": None if field.get("sensitive") else field.get("value"),
            }
            for field in fields
            if isinstance(field, dict)
        ],
    }


def site_dict(site: Site) -> dict[str, Any]:
    return {
        "id": site.id,
        "name": site.name,
        "base_url": site.base_url,
        "requires_auth": site.requires_auth,
        "login_url": site.login_url,
        "notes": site.notes,
        "scan_guidance": site.scan_guidance,
        "workflow_data": sites_service.workflow_data_for_site(site),
        "scope_hosts": json.loads(site.scope_hosts or "[]"),
        "credentials": [credential_dict(cred) for cred in site.credentials],
        "created_at": run_results._iso(site.created_at),
        "updated_at": run_results._iso(site.updated_at),
    }


def _site_errors(action: Callable[[], Any]) -> Any:
    try:
        return action()
    except sites_service.SiteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except sites_service.CredentialNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except sites_service.DuplicateSiteName as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except sites_service.SiteServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class SastRunAccess:
    """Create and control SAST runs. Requires ``core.sast_runs``."""

    async def store_upload(
        self, read: Callable[[int], Awaitable[bytes]], filename: str | None
    ) -> sast_runs.StoredArchive:
        return await sast_runs.store_upload(read, filename)

    def check_analysis_mode(self, analysis_mode: str) -> None:
        sast_runs.check_analysis_mode(analysis_mode)

    def create_from_archive(
        self, archive: sast_runs.StoredArchive, **options: Any
    ) -> int:
        with _session() as session:
            return sast_runs.create_from_archive(session, archive, **options).id

    async def create_from_source(self, **options: Any) -> int:
        with _session() as session:
            run = await sast_runs.create_from_source(session, **options)
            return run.id

    async def start(self, run_id: int) -> None:
        with _session() as session:
            await sast_runs.start(session, run_id)

    async def stop(self, run_id: int) -> bool:
        with _session() as session:
            return await sast_runs.stop(session, run_id)

    async def sources(self) -> list[dict[str, Any]]:
        """SAST source providers from enabled extensions, for create_from_source."""
        from aespa.extensions import get_extension_manager

        return await get_extension_manager().describe_source_providers()

    async def resume(self, run_id: int) -> None:
        with _session() as session:
            await sast_runs.resume(session, run_id)


class WebRunAccess:
    """Create Sites and control web runs. Requires ``core.web_runs``."""

    def list_sites(self) -> list[dict[str, Any]]:
        with _session() as session:
            return [site_dict(site) for site in sites_service.list_sites(session)]

    def get_site(self, site_id: int) -> dict[str, Any]:
        with _session() as session:
            return site_dict(
                _site_errors(lambda: sites_service.get_site(session, site_id))
            )

    def find_site_id(self, name: str) -> int | None:
        with _session() as session:
            site = sites_service.get_site_by_name(session, name)
            return site.id if site else None

    def create_site(self, payload: SiteCreate) -> dict[str, Any]:
        with _session() as session:
            return site_dict(
                _site_errors(lambda: sites_service.create_site(session, payload))
            )

    def update_site(self, site_id: int, payload: SiteUpdate) -> dict[str, Any]:
        with _session() as session:
            return site_dict(
                _site_errors(
                    lambda: sites_service.update_site(session, site_id, payload)
                )
            )

    def add_credential(self, site_id: int, payload: CredentialIn) -> dict[str, Any]:
        with _session() as session:
            return credential_dict(
                _site_errors(
                    lambda: sites_service.add_credential(session, site_id, payload)
                )
            )

    def delete_credential(self, site_id: int, credential_id: int) -> None:
        with _session() as session:
            _site_errors(
                lambda: sites_service.delete_credential(session, site_id, credential_id)
            )

    def create_run(self, site_id: int, payload: TestRunCreate) -> int:
        with _session() as session:
            return web_runs.create_run(session, site_id, payload).id

    async def start(self, run_id: int, body: StartCrawlBody | None = None) -> None:
        with _session() as session:
            await web_runs.start(session, run_id, body)

    async def start_scan(self, run_id: int, coverage_mode: str | None = None) -> None:
        with _session() as session:
            await web_runs.start_scan(session, run_id, coverage_mode=coverage_mode)

    async def resume(self, run_id: int, *, scan_after_crawl: bool = False) -> None:
        with _session() as session:
            await web_runs.resume(
                session, run_id, scan_after_crawl=scan_after_crawl
            )

    def stop(self, run_id: int) -> bool:
        with _session() as session:
            return web_runs.stop(session, run_id)

    def site_id_for_run(self, run_id: int) -> int | None:
        with _session() as session:
            run = session.get(TestRun, run_id)
            return run.site_id if run else None


RUN_TABLES = (("web", TestRun), ("sast", SastRun))


class RunReadAccess:
    """Read progress and results for web and SAST runs."""

    def kind(self, run_id: int) -> str | None:
        with _session() as session:
            return run_progress.run_kind(session, run_id)

    def progress(
        self, run_id: int, *, scan_after_crawl: bool = False
    ) -> dict[str, Any] | None:
        return run_progress.get_progress(run_id, scan_after_crawl=scan_after_crawl)

    def activity(
        self, run_id: int, *, after: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        return run_progress.list_activity(run_id, after=after, limit=limit)

    def findings(
        self,
        run_id: int,
        *,
        severities: set[str] | None = None,
        include_dismissed: bool = False,
    ) -> list[dict[str, Any]] | None:
        with _session() as session:
            return run_results.list_findings(
                session,
                run_id,
                severities=severities,
                include_dismissed=include_dismissed,
            )

    def summarize(
        self, findings: list[dict[str, Any]], *, fail_on: str | None = None
    ) -> dict[str, Any]:
        return run_results.summarize(findings, fail_on=fail_on)

    def sast_sarif(self, run_id: int) -> dict[str, Any] | None:
        with _session() as session:
            return run_results.sast_sarif(session, run_id)

    def web_sarif(
        self, run_id: int, *, include_false_positives: bool = False
    ) -> dict[str, Any] | None:
        with _session() as session:
            return run_results.web_sarif(
                session, run_id, include_false_positives=include_false_positives
            )

    def list_runs(
        self, kinds: set[str], *, offset: int = 0, limit: int = 25
    ) -> tuple[list[tuple[str, int]], int]:
        """Web and SAST runs of the given kinds, newest first, with the total."""
        tables = [(kind, table) for kind, table in RUN_TABLES if kind in kinds]
        with _session() as session:
            runs = [
                (created_at, run_id, kind)
                for kind, table in tables
                for run_id, created_at in session.exec(
                    select(table.id, table.created_at)
                ).all()
            ]
        runs.sort(key=lambda item: (item[0], item[1]), reverse=True)
        page = [(kind, run_id) for _, run_id, kind in runs[offset : offset + limit]]
        return page, len(runs)

    def sast_run_exists(self, run_id: int) -> bool:
        with _session() as session:
            return session.get(SastRun, run_id) is not None


class LlmReadAccess:
    """Read the scan profiles a run can use. Available to every extension."""

    def profiles(self) -> list[dict[str, Any]]:
        """Scan profiles, most recently changed first. Never writes."""
        with _session() as session:
            available = settings_profiles.extension_profile_items()
            rows = session.exec(
                select(LLMProfile).order_by(LLMProfile.updated_at.desc())
            ).all()
            return [
                {
                    "id": out.id,
                    "name": out.name,
                    "active": out.is_active,
                    "default_model": out.default_model_name,
                }
                for out in (
                    settings_profiles.llm_profile_out(session, row)
                    for row in rows
                    if row.extension_ref is None or row.extension_ref in available
                )
            ]


class CoreAccess:
    """What ``registry.core`` returns. Missing capabilities raise on access."""

    def __init__(self, capabilities: list[str], subscribe: Callable[..., Any]):
        self._capabilities = set(capabilities)
        self._subscribe = subscribe
        self.runs = RunReadAccess()
        self.llm = LlmReadAccess()

    @property
    def sast(self) -> SastRunAccess:
        if "core.sast_runs" not in self._capabilities:
            raise PermissionError("core.sast_runs is missing from extension.toml")
        return SastRunAccess()

    @property
    def web(self) -> WebRunAccess:
        if "core.web_runs" not in self._capabilities:
            raise PermissionError("core.web_runs is missing from extension.toml")
        return WebRunAccess()

    def on_run_change(self, listener: run_lifecycle.Listener) -> Callable[[], None]:
        """Call ``listener(run_id, run_kind, reason)`` when a run may have changed.

        AESPA removes the listener when the extension is disabled or reloaded.
        """
        return self._subscribe(listener)
