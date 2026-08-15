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

_DEFAULT_PORTS = {"http": 80, "https": 443}


def scope_authority(url: str, *, default_scheme: str | None = None) -> str:
    """Return a lower-case ``host:port`` identity for a URL or scope entry.

    Bare scope entries such as ``example.com`` use ``default_scheme`` to resolve
    their effective port. This keeps existing saved scopes working while making
    ``example.com:8443`` a different application from ``example.com:443``.
    """
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        return ""
    try:
        port = parsed.port
    except ValueError:
        return ""
    scheme = (parsed.scheme or default_scheme or "").lower()
    port = _DEFAULT_PORTS.get(scheme) if port is None else port
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{display_host}:{port}" if port is not None else display_host


def authority_is_allowed(
    url: str,
    scope_entries: list[str],
    *,
    default_url: str,
    allow_subdomains: bool = False,
) -> bool:
    """Check a URL against scope entries using hostname and effective port."""
    default_scheme = urlparse(default_url).scheme
    candidate = scope_authority(url, default_scheme=default_scheme)
    if not candidate:
        return False
    candidate_url = urlparse(url)
    candidate_host = (candidate_url.hostname or "").lower().rstrip(".")
    try:
        candidate_port = candidate_url.port
        if candidate_port is None:
            candidate_port = _DEFAULT_PORTS.get(candidate_url.scheme.lower())
    except ValueError:
        return False
    for entry in scope_entries:
        if candidate == scope_authority(entry, default_scheme=default_scheme):
            return True
        if not allow_subdomains:
            continue
        parsed_entry = urlparse(entry if "://" in entry else f"//{entry}")
        entry_host = (parsed_entry.hostname or "").lower().rstrip(".")
        try:
            entry_port = parsed_entry.port
            if entry_port is None:
                entry_port = _DEFAULT_PORTS.get(default_scheme)
        except ValueError:
            continue
        if (
            entry_host
            and candidate_host.endswith(f".{entry_host}")
            and candidate_port == entry_port
        ):
            return True
    return False


def normalize_scope_entries(entries: list[str], *, default_url: str) -> list[str]:
    """Canonicalise user-provided scope entries as unique ``host:port`` values."""
    default_scheme = urlparse(default_url).scheme
    normalized: list[str] = []
    for entry in entries:
        authority = scope_authority(entry, default_scheme=default_scheme)
        if authority and authority not in normalized:
            normalized.append(authority)
    return normalized


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
    """Auto-add *url*'s authority to the site's scope if it is in the same
    root domain and uses the same effective port as the configured base URL.

    Emits a ``scope_hosts_updated`` SSE event on the run when a host is added.
    Returns True if a new host was added.
    """
    parsed_url = urlparse(url)
    hostname = (parsed_url.hostname or "").lower()
    authority = scope_authority(url)
    if not hostname or not authority:
        return False

    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            return False
        site = s.get(Site, run.site_id)
        if site is None:
            return False

        parsed_base = urlparse(site.base_url)
        base_hostname = (parsed_base.hostname or "").lower()
        if not base_hostname or not _same_root_domain(hostname, base_hostname):
            return False

        try:
            url_port = parsed_url.port
            if url_port is None:
                url_port = _DEFAULT_PORTS.get(parsed_url.scheme.lower())
            base_port = parsed_base.port
            if base_port is None:
                base_port = _DEFAULT_PORTS.get(parsed_base.scheme.lower())
        except ValueError:
            return False
        if url_port != base_port:
            return False

        current: list[str] = json.loads(site.scope_hosts or "[]")
        if authority_is_allowed(url, current, default_url=site.base_url):
            return False

        current.append(authority)
        site.scope_hosts = json.dumps(current)
        s.add(site)
        s.commit()
        log.info(
            "scope: auto-added authority %s to site %d (run %d)",
            authority,
            site.id,
            run_id,
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
      1. If ``site.scope_hosts`` is non-empty, the URL's host and effective port
         must be in it.
      2. The URL must not correspond to a ``CrawledPage`` marked ``in_scope=False``.
    """
    authority = scope_authority(url)

    with Session(get_engine()) as s:
        site = s.get(Site, site_id)
        scope_hosts: list[str] = json.loads(
            (site.scope_hosts if site else None) or "[]"
        )

        # ── Host-level check ──────────────────────────────────────────────────
        if scope_hosts and not authority_is_allowed(
            url, scope_hosts, default_url=site.base_url if site else url
        ):
            allowed = ", ".join(scope_hosts)
            return (
                f"Host and port '{authority}' are outside the authorised attack scope "
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
