"""Queries and presentation for the stored sitemap graph."""

from __future__ import annotations

import json
from urllib.parse import urlparse, urlunparse

from sqlmodel import Session, func, select

from aespa.models import (
    CrawledPage,
    PageCredentialView,
    PageLink,
    TestRun,
    TestRunStatus,
    TrafficEntry,
)
from aespa.schemas import (
    GraphData,
    GraphLink,
    GraphNode,
)


def _infer_parent_url_candidates(url_str: str) -> list[str]:
    candidates = []
    parsed = urlparse(url_str)
    if parsed.query:
        no_query = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                "",
                parsed.fragment,
            )
        )
        candidates.append(no_query)
        url_str = no_query

    scheme, netloc, path, params, query, fragment = urlparse(url_str)
    if fragment and fragment.startswith("/"):
        frag_parts = [p for p in fragment.split("/") if p]
        while len(frag_parts) > 1:
            frag_parts.pop()
            parent_frag = "/" + "/".join(frag_parts)
            candidates.append(
                urlunparse((scheme, netloc, path, params, "", parent_frag))
            )
        cand_base = urlunparse((scheme, netloc, path, params, "", ""))
        candidates.append(cand_base)
        if cand_base.endswith("/"):
            candidates.append(cand_base.rstrip("/"))
    else:
        path_parts = [p for p in path.split("/") if p]
        while len(path_parts) > 1:
            path_parts.pop()
            parent_path = "/" + "/".join(path_parts)
            cand = urlunparse((scheme, netloc, parent_path, params, "", fragment))
            candidates.append(cand)
            if not parent_path.endswith("/"):
                candidates.append(cand + "/")

    seen = set()
    res = []
    for c in candidates:
        c_norm = c.rstrip("/") if len(c) > len(scheme + "://" + netloc) else c
        if c != url_str and c_norm not in seen:
            seen.add(c_norm)
            res.append(c)
    return res


def _response_url_key(url_str: str) -> str:
    """Normalize a page and traffic URL for response-status matching."""
    try:
        parsed = urlparse(url_str)
        path = parsed.path.rstrip("/") or "/"
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                parsed.params,
                parsed.query,
                "",
            )
        )
    except Exception:
        return url_str


def _is_dynamic_scan_page(page: CrawledPage) -> bool:
    title = (page.title or "").strip()
    context = (page.llm_context or "").strip()
    return title.startswith("Dynamic ") or context.startswith(
        "Discovered during Dynamic Scan."
    )


def build_run_graph(session: Session, run: TestRun) -> GraphData:
    run_id = run.id
    response_ranges_by_url: dict[str, tuple[int, int]] = {}
    response_range_rows = session.exec(
        select(
            TrafficEntry.url,
            func.min(TrafficEntry.status),
            func.max(TrafficEntry.status),
        )
        .where(TrafficEntry.test_run_id == run_id)
        .where(TrafficEntry.status.is_not(None))
        .group_by(TrafficEntry.url)
    ).all()
    for traffic_url, minimum_status, maximum_status in response_range_rows:
        if minimum_status is None or maximum_status is None:
            continue
        key = _response_url_key(traffic_url)
        prior = response_ranges_by_url.get(key)
        response_ranges_by_url[key] = (
            min(prior[0], minimum_status) if prior else minimum_status,
            max(prior[1], maximum_status) if prior else maximum_status,
        )
    only_4xx_urls = {
        url
        for url, (minimum_status, maximum_status) in response_ranges_by_url.items()
        if 400 <= minimum_status and maximum_status < 500
    }

    pages = session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run_id)
    ).all()
    pages = [
        page
        for page in pages
        if page.status != "failed" and _response_url_key(page.url) not in only_4xx_urls
    ]
    links = session.exec(select(PageLink).where(PageLink.test_run_id == run_id)).all()
    anonymously_accessible_page_ids = set(
        session.exec(
            select(PageCredentialView.page_id)
            .where(PageCredentialView.test_run_id == run_id)
            .where(PageCredentialView.credential_id.is_(None))
        ).all()
    )
    run_finished = run.status in {
        TestRunStatus.complete,
        TestRunStatus.failed,
        TestRunStatus.stopped,
    }

    def _analysis_status(page: CrawledPage) -> str:
        if page.status == "redirect":
            return "skipped"
        if page.llm_context:
            return "complete"
        # The crawler waits for all page-analysis tasks before marking a run
        # complete. Empty shell pages in a finished run were therefore
        # skipped (usually because authentication was required), not left in
        # an LLM queue.
        if run_finished and not page.title and not page.page_text:
            return "skipped"
        if run_finished:
            return "complete"
        return "pending"

    nodes = [
        GraphNode(
            id=p.id,
            url=p.url,
            state_label=p.state_label,
            state_kind=p.state_kind,
            title=p.title,
            depth=p.depth,
            status=p.status,
            error_message=p.error_message,
            context=p.llm_context,
            analysis_status=_analysis_status(p),
            in_scope=p.in_scope,
            scan_status=p.scan_status,
            accessible_by=json.loads(p.accessible_by or "[]"),
            accessible_anonymously=p.id in anonymously_accessible_page_ids,
            replay_available=bool(p.replay_steps_json and p.replay_steps_json != "[]"),
            replay_credential_id=p.replay_credential_id,
        )
        for p in pages
    ]
    page_ids = {p.id for p in pages}
    edges = [
        GraphLink(
            source=link.source_page_id,
            target=link.target_page_id,
            link_text=link.link_text,
            action_kind=link.action_kind,
        )
        for link in links
        if link.target_page_id is not None
        and link.source_page_id in page_ids
        and link.target_page_id in page_ids
    ]

    # Older dynamic scans created route nodes without PageLink rows. Recover
    # source-page relationships from the traffic attribution already stored for
    # those requests. Self-attributed traffic is not a useful graph edge.
    traffic_sources_by_url: dict[str, set[int]] = {}
    traffic_source_rows = session.exec(
        select(TrafficEntry.url, TrafficEntry.page_id)
        .where(TrafficEntry.test_run_id == run_id)
        .where(TrafficEntry.page_id.is_not(None))
        .group_by(TrafficEntry.url, TrafficEntry.page_id)
    ).all()
    for traffic_url, source_page_id in traffic_source_rows:
        if source_page_id is None:
            continue
        traffic_sources_by_url.setdefault(_response_url_key(traffic_url), set()).add(
            source_page_id
        )

    incident_page_ids = {edge.source for edge in edges} | {
        edge.target for edge in edges
    }
    for page in pages:
        if page.id in incident_page_ids or not _is_dynamic_scan_page(page):
            continue
        for source_page_id in sorted(
            traffic_sources_by_url.get(_response_url_key(page.url), set())
        ):
            if source_page_id == page.id or source_page_id not in page_ids:
                continue
            edges.append(
                GraphLink(
                    source=source_page_id,
                    target=page.id,
                    link_text="Observed during Dynamic Scan",
                    action_kind=(
                        "dynamic_request"
                        if page.state_kind == "api"
                        else "dynamic_navigation"
                    ),
                )
            )
            incident_page_ids.add(source_page_id)
            incident_page_ids.add(page.id)

    targeted_page_ids = {e.target for e in edges}
    root_page_id = min((p.id for p in pages), default=None)
    page_url_map = {p.url: p.id for p in pages}
    page_url_map_norm = {p.url.rstrip("/"): p.id for p in pages if len(p.url) > 8}

    for p in pages:
        if p.id == root_page_id or p.id in targeted_page_ids:
            continue
        candidates = _infer_parent_url_candidates(p.url)
        parent_id = None
        for cand in candidates:
            cand_norm = cand.rstrip("/")
            if cand in page_url_map:
                parent_id = page_url_map[cand]
                break
            elif cand_norm in page_url_map_norm:
                parent_id = page_url_map_norm[cand_norm]
                break
        if parent_id and parent_id != p.id and parent_id in page_ids:
            edges.append(
                GraphLink(
                    source=parent_id,
                    target=p.id,
                    link_text=None,
                    action_kind="inferred",
                )
            )
            targeted_page_ids.add(p.id)

    return GraphData(nodes=nodes, links=edges)
