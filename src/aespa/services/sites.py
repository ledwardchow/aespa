"""Service-layer CRUD for Sites + Credentials.

Pure functions taking a SQLModel ``Session``. The upcoming crawler can import
these helpers directly without going through HTTP.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _parse_datetimes(data: dict, *fields: str) -> dict:
    """Return *data* with ISO-string values for *fields* converted to datetime objects.

    JSON serialisation turns datetime → str; SQLite requires real datetime objects
    when inserting via SQLAlchemy, so we convert them back here at import time.
    ``None`` values are left as-is; strings are parsed with ``datetime.fromisoformat``.
    """
    for field in fields:
        value = data.get(field)
        if isinstance(value, str):
            data[field] = datetime.fromisoformat(value)
    return data

from sqlmodel import Session, select

from aespa.models import Credential, PageCredentialView, Site
from aespa.schemas import CredentialIn, SiteCreate, SiteUpdate


class SiteServiceError(Exception):
    """Base class for service-layer errors."""


class SiteNotFound(SiteServiceError):
    pass


class CredentialNotFound(SiteServiceError):
    pass


class DuplicateSiteName(SiteServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_sites(session: Session) -> list[Site]:
    return list(session.exec(select(Site).order_by(Site.name)).all())


def get_site(session: Session, site_id: int) -> Site:
    site = session.get(Site, site_id)
    if site is None:
        raise SiteNotFound(f"Site id={site_id} does not exist")
    # touch credentials so callers can read them outside the session if needed
    _ = site.credentials
    return site


def get_site_by_name(session: Session, name: str) -> Site | None:
    return session.exec(select(Site).where(Site.name == name)).first()


def _ensure_unique_name(session: Session, name: str, *, ignore_id: int | None = None) -> None:
    existing = get_site_by_name(session, name)
    if existing is None:
        return
    if ignore_id is not None and existing.id == ignore_id:
        return
    raise DuplicateSiteName(f"A site named {name!r} already exists")


def create_site(session: Session, payload: SiteCreate) -> Site:
    _ensure_unique_name(session, payload.name)

    site = Site(
        name=payload.name,
        base_url=str(payload.base_url),
        requires_auth=payload.requires_auth,
        login_url=str(payload.login_url) if payload.login_url else None,
        notes=payload.notes,
    )
    for cred in payload.credentials:
        site.credentials.append(
            Credential(
                username=cred.username,
                password=cred.password,
                label=cred.label,
                login_url=str(cred.login_url) if cred.login_url else None,
                auth_mode=cred.auth_mode,
                totp_seed=cred.totp_seed,
            )
        )

    session.add(site)
    session.commit()
    session.refresh(site)
    _ = site.credentials
    return site


def update_site(session: Session, site_id: int, payload: SiteUpdate) -> Site:
    site = get_site(session, site_id)
    _ensure_unique_name(session, payload.name, ignore_id=site.id)

    site.name = payload.name
    site.base_url = str(payload.base_url)
    site.requires_auth = payload.requires_auth
    site.login_url = str(payload.login_url) if payload.login_url else None
    site.notes = payload.notes
    site.updated_at = _utcnow()

    # Replace credentials list wholesale.
    site.credentials.clear()
    session.flush()
    for cred in payload.credentials:
        site.credentials.append(
            Credential(
                username=cred.username,
                password=cred.password,
                label=cred.label,
                login_url=str(cred.login_url) if cred.login_url else None,
                auth_mode=cred.auth_mode,
                totp_seed=cred.totp_seed,
            )
        )

    session.add(site)
    session.commit()
    session.refresh(site)
    _ = site.credentials
    return site


def delete_site(session: Session, site_id: int) -> None:
    from aespa.models import CrawledPage, PageLink, TestRun

    site = get_site(session, site_id)
    # Manually cascade to test runs and their children (SQLite FK off by default)
    runs = session.exec(select(TestRun).where(TestRun.site_id == site_id)).all()
    for run in runs:
        links = session.exec(select(PageLink).where(PageLink.test_run_id == run.id)).all()
        for lnk in links:
            session.delete(lnk)
        views = session.exec(select(PageCredentialView).where(PageCredentialView.test_run_id == run.id)).all()
        for view in views:
            session.delete(view)
        pages = session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run.id)).all()
        for pg in pages:
            session.delete(pg)
        session.delete(run)
    session.delete(site)
    session.commit()


def add_credential(session: Session, site_id: int, payload: CredentialIn) -> Credential:
    site = get_site(session, site_id)
    if not site.requires_auth:
        raise SiteServiceError("Cannot add credentials to a site that does not require auth")
    if not site.login_url and not payload.login_url:
        raise SiteServiceError(
            "Credential login_url is required when the site has no default login_url"
        )
    cred = Credential(
        site_id=site.id,
        username=payload.username,
        password=payload.password,
        label=payload.label,
        login_url=str(payload.login_url) if payload.login_url else None,
        auth_mode=payload.auth_mode,
        totp_seed=payload.totp_seed,
    )
    site.updated_at = _utcnow()
    session.add(cred)
    session.add(site)
    session.commit()
    session.refresh(cred)
    return cred


def delete_credential(session: Session, site_id: int, credential_id: int) -> None:
    cred = session.get(Credential, credential_id)
    if cred is None or cred.site_id != site_id:
        raise CredentialNotFound(
            f"Credential id={credential_id} not found for site {site_id}"
        )
    session.delete(cred)
    session.commit()


# ── Export / Import ──────────────────────────────────────────────────────────

def export_site(session: Session, site_id: int) -> dict:
    """Return a portable dict containing the site and every related row.

    All primary keys are preserved as export-local IDs so that import_site()
    can remap them.  Datetimes are serialised to ISO-8601 strings via
    model_dump(mode="json").
    """
    from aespa.models import (
        CrawledPage,
        PageLink,
        PageCredentialView,
        PentestHypothesis,
        PentestTask,
        ScanFinding,
        ScanLog,
        ScannerSession,
        TargetIntelItem,
        TestRun,
        TrafficEntry,
    )

    site = get_site(session, site_id)

    def _row(obj) -> dict:
        return obj.model_dump(mode="json")

    creds = [_row(c) for c in site.credentials]
    runs = list(session.exec(select(TestRun).where(TestRun.site_id == site_id)).all())

    run_bundles = []
    for run in runs:
        rid = run.id
        pages   = list(session.exec(select(CrawledPage).where(CrawledPage.test_run_id == rid)).all())
        links   = list(session.exec(select(PageLink).where(PageLink.test_run_id == rid)).all())
        traffic = list(session.exec(select(TrafficEntry).where(TrafficEntry.test_run_id == rid)).all())
        sessions_ = list(session.exec(select(ScannerSession).where(ScannerSession.test_run_id == rid)).all())
        views   = list(session.exec(select(PageCredentialView).where(PageCredentialView.test_run_id == rid)).all())
        intel   = list(session.exec(select(TargetIntelItem).where(TargetIntelItem.test_run_id == rid)).all())
        hyps    = list(session.exec(select(PentestHypothesis).where(PentestHypothesis.test_run_id == rid)).all())
        tasks   = list(session.exec(select(PentestTask).where(PentestTask.test_run_id == rid)).all())
        findings = list(session.exec(select(ScanFinding).where(ScanFinding.test_run_id == rid)).all())
        logs    = list(session.exec(select(ScanLog).where(ScanLog.test_run_id == rid)).all())

        run_bundles.append({
            "test_run": _row(run),
            "crawled_pages": [_row(p) for p in pages],
            "page_links": [_row(l) for l in links],
            "traffic_entries": [_row(t) for t in traffic],
            "scanner_sessions": [_row(s) for s in sessions_],
            "page_credential_views": [_row(v) for v in views],
            "target_intel_items": [_row(i) for i in intel],
            "pentest_hypotheses": [_row(h) for h in hyps],
            "pentest_tasks": [_row(t) for t in tasks],
            "scan_findings": [_row(f) for f in findings],
            "scan_logs": [_row(l) for l in logs],
        })

    return {
        "export_version": 1,
        "exported_at": _utcnow().isoformat(),
        "site": _row(site),
        "credentials": creds,
        "test_runs": run_bundles,
    }


def import_site(session: Session, bundle: dict) -> Site:
    """Create a new site from a bundle produced by export_site().

    All primary keys are re-mapped so the import never collides with existing
    rows.  If the site name already exists a numeric suffix is appended.
    TestRun.llm_config_id is set to None because the target installation may
    have a different LLM config table.
    """
    from aespa.models import (
        CrawledPage,
        PageLink,
        PageCredentialView,
        PentestHypothesis,
        PentestTask,
        ScanFinding,
        ScanLog,
        ScannerSession,
        TargetIntelItem,
        TestRun,
        TrafficEntry,
    )

    if bundle.get("export_version") != 1:
        raise SiteServiceError(
            f"Unsupported export bundle version: {bundle.get('export_version')!r}"
        )

    # ── Site ─────────────────────────────────────────────────────────────────
    site_data = {k: v for k, v in bundle["site"].items()
                 if k not in ("id", "created_at", "updated_at")}
    name = site_data["name"]
    candidate, counter = name, 2
    while get_site_by_name(session, candidate) is not None:
        candidate = f"{name} ({counter})"
        counter += 1
    site_data["name"] = candidate

    site = Site(**site_data)
    session.add(site)
    session.flush()
    new_site_id: int = site.id  # type: ignore[assignment]

    # ── Credentials ──────────────────────────────────────────────────────────
    cred_id_map: dict[int, int] = {}
    for c in bundle.get("credentials", []):
        c = dict(c)
        old_id = c.pop("id")
        c["site_id"] = new_site_id
        cred = Credential(**c)
        session.add(cred)
        session.flush()
        cred_id_map[old_id] = cred.id  # type: ignore[index]

    # ── Test runs ─────────────────────────────────────────────────────────────
    for rb in bundle.get("test_runs", []):
        run_data = {k: v for k, v in rb["test_run"].items()
                    if k not in ("id",)}
        run_data["site_id"] = new_site_id
        run_data["llm_config_id"] = None  # cannot map across installations
        _parse_datetimes(run_data, "created_at", "started_at", "completed_at")

        run = TestRun(**run_data)
        session.add(run)
        session.flush()
        new_run_id: int = run.id  # type: ignore[assignment]

        # ── CrawledPages ────────────────────────────────────────────────────
        page_id_map: dict[int, int] = {}
        for p in rb.get("crawled_pages", []):
            p = dict(p)
            old_pid = p.pop("id")
            p["test_run_id"] = new_run_id
            _parse_datetimes(p, "discovered_at")
            page = CrawledPage(**p)
            session.add(page)
            session.flush()
            page_id_map[old_pid] = page.id  # type: ignore[index]

        # ── PageLinks ───────────────────────────────────────────────────────
        for l in rb.get("page_links", []):
            l = dict(l)
            l.pop("id")
            l["test_run_id"] = new_run_id
            src = l.get("source_page_id")
            tgt = l.get("target_page_id")
            if src is not None:
                l["source_page_id"] = page_id_map.get(src, src)
            if tgt is not None:
                l["target_page_id"] = page_id_map.get(tgt, tgt)
            session.add(PageLink(**l))

        # ── TrafficEntries ──────────────────────────────────────────────────
        for t in rb.get("traffic_entries", []):
            t = dict(t)
            t.pop("id")
            t["test_run_id"] = new_run_id
            _parse_datetimes(t, "created_at")
            session.add(TrafficEntry(**t))

        # ── ScannerSessions ─────────────────────────────────────────────────
        for s in rb.get("scanner_sessions", []):
            s = dict(s)
            s.pop("id")
            s["test_run_id"] = new_run_id
            old_cid = s.get("credential_id")
            if old_cid is not None:
                s["credential_id"] = cred_id_map.get(old_cid)
            _parse_datetimes(s, "created_at", "updated_at")
            session.add(ScannerSession(**s))

        # ── PageCredentialViews ─────────────────────────────────────────────
        for v in rb.get("page_credential_views", []):
            v = dict(v)
            v.pop("id")
            v["test_run_id"] = new_run_id
            old_pid = v.get("page_id")
            if old_pid is not None:
                v["page_id"] = page_id_map.get(old_pid, old_pid)
            old_cid = v.get("credential_id")
            if old_cid is not None:
                v["credential_id"] = cred_id_map.get(old_cid)
            session.add(PageCredentialView(**v))

        # ── TargetIntelItems ────────────────────────────────────────────────
        for i in rb.get("target_intel_items", []):
            i = dict(i)
            i.pop("id")
            i["test_run_id"] = new_run_id
            _parse_datetimes(i, "discovered_at")
            session.add(TargetIntelItem(**i))

        # ── PentestHypotheses ───────────────────────────────────────────────
        hyp_id_map: dict[int, int] = {}
        for h in rb.get("pentest_hypotheses", []):
            h = dict(h)
            old_hid = h.pop("id")
            h["test_run_id"] = new_run_id
            _parse_datetimes(h, "created_at", "updated_at")
            hyp = PentestHypothesis(**h)
            session.add(hyp)
            session.flush()
            hyp_id_map[old_hid] = hyp.id  # type: ignore[index]

        # ── PentestTasks ────────────────────────────────────────────────────
        for t in rb.get("pentest_tasks", []):
            t = dict(t)
            t.pop("id")
            t["test_run_id"] = new_run_id
            old_hid = t.get("hypothesis_id")
            if old_hid is not None:
                t["hypothesis_id"] = hyp_id_map.get(old_hid)
            _parse_datetimes(t, "created_at", "updated_at")
            session.add(PentestTask(**t))

        # ── ScanFindings ────────────────────────────────────────────────────
        for f in rb.get("scan_findings", []):
            f = dict(f)
            f.pop("id")
            f["test_run_id"] = new_run_id
            old_pid = f.get("page_id")
            if old_pid is not None:
                f["page_id"] = page_id_map.get(old_pid)
            _parse_datetimes(f, "created_at")
            session.add(ScanFinding(**f))

        # ── ScanLogs ────────────────────────────────────────────────────────
        for sl in rb.get("scan_logs", []):
            sl = dict(sl)
            sl.pop("id")
            sl["test_run_id"] = new_run_id
            _parse_datetimes(sl, "created_at")
            session.add(ScanLog(**sl))

    session.commit()
    session.refresh(site)
    _ = site.credentials
    return site
