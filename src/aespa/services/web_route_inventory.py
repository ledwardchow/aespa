"""Shared route classification and enrichment for web crawl and dynamic scans."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, TestRun
from aespa.services import llm as llm_svc

log = logging.getLogger(__name__)

_OWASP_CATEGORIES = tuple(f"A{i:02d}" for i in range(1, 11))
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_INPUT_METHODS = _MUTATING_METHODS
_SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
}


def classify_http_exchange(
    exchange: dict[str, Any], *, authenticated: bool = False
) -> dict[str, Any]:
    """Return conservative route flags and OWASP applicability from HTTP evidence."""
    method = str(exchange.get("method") or "GET").upper()
    url = str(exchange.get("url") or "")
    request_body = _body_text(exchange.get("request_body"))
    url_lower = url.lower()
    body_lower = request_body.lower()
    is_mutating = method in _MUTATING_METHODS
    has_id = _url_has_object_ref(url) or _body_has_object_ref(request_body)
    is_auth_endpoint = any(
        keyword in url_lower
        for keyword in (
            "/login",
            "/logout",
            "/auth",
            "/token",
            "/session",
            "/password",
            "/reset",
            "/register",
            "/signup",
            "/oauth",
        )
    )
    has_url_param = bool(
        re.search(
            r"[?&](?:url|uri|href|src|redirect|callback|proxy|fetch|target)=",
            url_lower,
        )
    ) or bool(
        re.search(
            r'"(?:url|uri|href|src|redirect|callback|proxy|fetch|target)"\s*:',
            body_lower,
        )
    )

    return {
        "req_auth": authenticated,
        "takes_input": method in _INPUT_METHODS or bool(request_body),
        "has_object_ref": has_id,
        "has_business_logic": True if is_mutating else None,
        "owasp_applicable": {
            "A01": has_id or authenticated,
            "A02": is_auth_endpoint
            or bool(re.search(r"password|secret|token|key|credential", body_lower)),
            "A03": is_mutating or bool(request_body),
            "A04": is_mutating,
            "A05": True,
            "A06": False,
            "A07": is_auth_endpoint or authenticated,
            "A08": is_mutating,
            "A09": is_mutating,
            "A10": has_url_param,
        },
    }


def merge_route_categories(
    baseline: dict[str, Any], additional: dict[str, Any]
) -> dict[str, Any]:
    """OR-merge route evidence so later observations cannot erase prior signals."""
    merged = dict(baseline)
    for key in ("req_auth", "takes_input", "has_object_ref", "has_business_logic"):
        old = baseline.get(key)
        new = additional.get(key)
        if old is True or new is True:
            merged[key] = True
        elif new is not None:
            merged[key] = new
        else:
            merged[key] = old

    old_owasp = baseline.get("owasp_applicable") or {}
    new_owasp = additional.get("owasp_applicable") or {}
    merged["owasp_applicable"] = {
        category: bool(old_owasp.get(category)) or bool(new_owasp.get(category))
        for category in _OWASP_CATEGORIES
    }
    return merged


async def enrich_dynamic_route(
    *,
    run_id: int,
    llm_cfg,
    url: str,
    method: str = "GET",
    request_headers: dict[str, Any] | None = None,
    request_body: Any = None,
    response_status: int | None = None,
    response_headers: dict[str, Any] | None = None,
    response_body: Any = None,
    authenticated: bool = False,
    browser_observation: bool = False,
) -> int | None:
    """Upsert and classify a route observed during a dynamic web scan.

    Deterministic HTTP heuristics are always OR-merged. The LLM page classifier is
    called only when the route is new or has no prior applicability classification.
    Newly applicable workprogram cells are then seeded idempotently.
    """
    url = (url or "").strip()
    if not url or response_status is None or response_status == 404:
        return None

    exchange = {
        "url": url,
        "method": method,
        "request_headers": request_headers or {},
        "request_body": request_body,
        "status": response_status,
        "response_headers": response_headers or {},
        "body": response_body,
    }
    heuristic = classify_http_exchange(exchange, authenticated=authenticated)

    page_id, needs_llm = _upsert_route_shell(
        run_id=run_id,
        url=url,
        browser_observation=browser_observation,
    )
    if page_id is None:
        return None

    llm_categories: dict[str, Any] = {}
    llm_context = ""
    if needs_llm and llm_cfg is not None:
        try:
            llm_context, _suggested, llm_categories = await llm_svc.analyse_page(
                llm_cfg,
                url,
                _route_title(exchange, browser_observation=browser_observation),
                http_exchange_text(exchange),
                None,
            )
        except Exception as exc:
            log.warning("Dynamic route analysis failed for %s: %s", url, exc)

    observed = merge_route_categories(heuristic, llm_categories)
    _merge_route_observation(
        page_id=page_id,
        exchange=exchange,
        observed=observed,
        llm_context=llm_context,
        browser_observation=browser_observation,
    )

    from aespa.services.web_workprogram import seed_web_workprogram

    seed_web_workprogram(run_id)
    return page_id


def http_exchange_text(exchange: dict[str, Any]) -> str:
    """Build bounded, credential-redacted analysis text for an HTTP exchange."""
    method = str(exchange.get("method") or "GET").upper()
    request_body = _body_text(exchange.get("request_body"))[:8000]
    response_body = _body_text(exchange.get("body"))[:8000]
    return (
        "=== HTTP exchange observed during scan ===\n\n"
        f"REQUEST\n{method} {exchange.get('url') or ''}\n"
        f"Headers:\n{_format_headers(exchange.get('request_headers') or {})}\n\n"
        f"Body:\n{request_body or '(none)'}\n\n"
        f"RESPONSE\nStatus: {exchange.get('status', 'unknown')}\n"
        f"Headers:\n{_format_headers(exchange.get('response_headers') or {})}\n\n"
        f"Body:\n{response_body or '(none)'}"
    )


def _upsert_route_shell(
    *, run_id: int, url: str, browser_observation: bool
) -> tuple[int | None, bool]:
    from aespa.services.web_workprogram import _match_page_for_url

    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        if run is None:
            return None, False
        pages = list(
            session.exec(
                select(CrawledPage)
                .where(CrawledPage.test_run_id == run_id)
                .where(CrawledPage.in_scope == True)  # noqa: E712
            ).all()
        )
        page_id = _match_page_for_url(url, pages)
        page = session.get(CrawledPage, page_id) if page_id is not None else None
        if page is None:
            page = CrawledPage(
                test_run_id=run_id,
                url=url,
                title="Dynamic browser route"
                if browser_observation
                else "Dynamic API route",
                page_text="",
                llm_context="Discovered during Dynamic Scan.",
                depth=0,
                status="crawled",
                in_scope=True,
                scan_status="pending",
                state_kind="url" if browser_observation else "api",
            )
            session.add(page)
            session.flush()
            run.pages_discovered = (run.pages_discovered or 0) + 1
            session.add(run)
        try:
            prior_applicability = json.loads(page.owasp_applicable_json or "{}")
        except (TypeError, ValueError):
            prior_applicability = {}
        needs_llm = not bool(prior_applicability)
        session.commit()
        return page.id, needs_llm


def _merge_route_observation(
    *,
    page_id: int,
    exchange: dict[str, Any],
    observed: dict[str, Any],
    llm_context: str,
    browser_observation: bool,
) -> None:
    with Session(get_engine()) as session:
        page = session.get(CrawledPage, page_id)
        if page is None:
            return
        try:
            current_owasp = json.loads(page.owasp_applicable_json or "{}")
        except Exception:
            current_owasp = {}
        current = {
            "req_auth": page.req_auth,
            "takes_input": page.takes_input,
            "has_object_ref": page.has_object_ref,
            "has_business_logic": page.has_business_logic,
            "owasp_applicable": current_owasp,
        }
        merged = merge_route_categories(current, observed)
        for key in ("req_auth", "takes_input", "has_object_ref", "has_business_logic"):
            setattr(page, key, merged.get(key))
        page.owasp_applicable_json = json.dumps(
            merged["owasp_applicable"], sort_keys=True
        )
        if not page.page_text:
            page.page_text = http_exchange_text(exchange)[:10_000]
        if llm_context:
            existing_context = (page.llm_context or "").strip()
            page.llm_context = (
                f"{existing_context}\n\n{llm_context}"
                if existing_context
                else llm_context
            )
        if not browser_observation:
            page.state_kind = "api"
        session.add(page)
        session.commit()


def _route_title(exchange: dict[str, Any], *, browser_observation: bool) -> str:
    parsed = urlparse(str(exchange.get("url") or ""))
    if browser_observation:
        return f"Dynamic browser route {parsed.path or '/'}"
    method = str(exchange.get("method") or "GET").upper()
    return f"API {method} {parsed.path or '/'}"


def _format_headers(headers: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in headers.items():
        if str(key).lower() in _SENSITIVE_HEADER_NAMES:
            rendered = "[redacted]"
        else:
            rendered = str(value)
            if len(rendered) > 200:
                rendered = rendered[:200] + "…"
        lines.append(f"  {key}: {rendered}")
    return "\n".join(lines) if lines else "  (none)"


def _body_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)


def _url_has_object_ref(url: str) -> bool:
    parsed = urlparse(url or "")
    if any(_looks_like_id(segment) for segment in parsed.path.split("/") if segment):
        return True
    return bool(
        re.search(
            r"(?:^|[?&])(?:id|account|accountid|user|userid|customer|customerid|order|orderid)=[^&]+",
            parsed.query.lower(),
        )
    )


def _looks_like_id(value: str) -> bool:
    return bool(
        re.fullmatch(r"\d+", value)
        or re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            value,
            re.IGNORECASE,
        )
    )


def _body_has_object_ref(body: str) -> bool:
    text = (body or "")[:20_000].lower()
    if not text:
        return False
    if re.search(
        r'"(?:id|[a-z0-9_]*(?:id|account|user|customer|order)[a-z0-9_]*)"\s*:\s*"?\d+',
        text,
    ):
        return True
    return bool(
        re.search(
            r"(?:^|[&?])(?:id|account|accountid|user|userid|customer|customerid|order|orderid)=\d+",
            text,
        )
    )
