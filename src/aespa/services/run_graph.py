"""Queries and presentation for the stored sitemap graph."""

from __future__ import annotations

import json
from urllib.parse import urlparse, urlunparse

from sqlmodel import Session, select

from aespa.models import (
    CrawledPage,
    PageCredentialView,
    PageLink,
    TestRun,
    TestRunStatus,
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


def build_run_graph(session: Session, run: TestRun) -> GraphData:
    run_id = run.id
    pages = session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run_id)
    ).all()
    pages = [
        page
        for page in pages
        if not (
            page.status == "failed"
            and (page.error_message or "").strip().upper() == "HTTP 404"
        )
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
