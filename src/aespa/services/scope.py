"""Live scope enforcement for the dynamic scanner.

All checks do a fresh DB read — no caching — so changes take effect immediately.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, Site, TestRun
from aespa.services import events as events_svc

log = logging.getLogger(__name__)


def _same_root_domain(a: str, b: str) -> bool:
    """Return True if *a* and *b* share the same registrable domain (heuristic).

    Uses the last-2-labels rule, extended to 3 labels when the second-to-last
    label is <= 3 chars (e.g. co.uk, com.au).
    """

    def _root(h: str) -> str:
        parts = h.lower().rstrip(".").split(".")
        if len(parts) >= 3 and len(parts[-2]) <= 3:
            return ".".join(parts[-3:])
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return h

    return bool(a and b and _root(a) == _root(b))


def _urls_match(a: str, b: str) -> bool:
    """Compare URLs ignoring trailing slashes and fragments."""

    def _norm(u: str) -> str:
        p = urlparse(u)
        return f"{p.scheme}://{p.netloc}{p.path.rstrip('/') or '/'}"

    return _norm(a) == _norm(b)


def register_scope_host_for_run(run_id: int, url: str) -> bool:
    """Auto-add *url*'s hostname to the site's scope_hosts if it is in the
    same root domain as the site's base_url and not already listed.

    Emits a ``scope_hosts_updated`` SSE event on the run when a host is added.
    Returns True if a new host was added.
    """
    hostname = (urlparse(url).hostname or "").lower()
    if not hostname:
        return False

    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return False
        site = s.get(Site, run.site_id)
        if site is None:
            return False

        base_hostname = (urlparse(site.base_url).hostname or "").lower()
        if not base_hostname or not _same_root_domain(hostname, base_hostname):
            return False

        current: list[str] = json.loads(site.scope_hosts or "[]")
        if hostname in current:
            return False

        current.append(hostname)
        site.scope_hosts = json.dumps(current)
        s.add(site)
        s.commit()
        log.info(
            "scope: auto-added host %s to site %d (run %d)", hostname, site.id, run_id
        )

    events_svc.emit(
        run_id,
        {
            "type": "scope_hosts_updated",
            "scope_hosts": current,
        },
    )
    return True


def check_scope(url: str, site_id: int, run_id: int) -> str | None:
    """Live scope check — opens a fresh DB session on every call.

    Returns a human-readable rejection reason if the request should be
    blocked, or ``None`` if it is permitted.

    Rules (in order):
      1. If ``site.scope_hosts`` is non-empty, the URL's hostname must be in it.
      2. The URL must not correspond to a ``CrawledPage`` marked ``in_scope=False``.
    """
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    with Session(get_engine()) as s:
        site = s.get(Site, site_id)
        scope_hosts: list[str] = json.loads(
            (site.scope_hosts if site else None) or "[]"
        )

        # ── Host-level check ──────────────────────────────────────────────────
        if scope_hosts and hostname not in scope_hosts:
            allowed = ", ".join(scope_hosts)
            return (
                f"Host '{hostname}' is outside the authorised attack scope "
                f"(allowed: {allowed}). "
                "If this host is part of the application, add it via the "
                "Attack Scope panel in the Site Map."
            )

        # ── Page-level check ──────────────────────────────────────────────────
        out_of_scope_pages = s.exec(
            select(CrawledPage).where(
                CrawledPage.test_run_id == run_id,
                CrawledPage.in_scope == False,  # noqa: E712
            )
        ).all()
        for page in out_of_scope_pages:
            if _urls_match(url, page.url):
                return (
                    f"'{url}' is marked out-of-scope in the Site Map. "
                    "Un-mark it to include it in testing."
                )

    return None
