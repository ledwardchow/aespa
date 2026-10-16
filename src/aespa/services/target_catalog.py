from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from sqlalchemy import func, or_
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    CrawledPage,
    Credential,
    DiscoveredTarget,
    ScanFinding,
    ScanObligation,
    TargetAccessObservation,
    TargetDiscovery,
    TestRun,
    TrafficEntry,
)


def exact_url(url: str) -> str:
    """Normalize the origin while retaining every resource selector byte."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError("Target must be an HTTP URL")
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    netloc = host + (f":{parts.port}" if parts.port else "")
    return urlunsplit(
        (parts.scheme.lower(), netloc, parts.path or "/", parts.query, parts.fragment)
    )


def state_identity(state_key: str | None) -> str:
    return json.dumps([state_key], separators=(",", ":"))


def route_pattern(url: str) -> str:
    parts = urlsplit(url)
    path = re.sub(r"(?<=/)\d+(?=/|$)", "{id}", parts.path or "/")
    query = parse_qsl(parts.query, keep_blank_values=True)
    if not query:
        return path
    return (
        path
        + "?"
        + "&".join(f"{key}={{{key}}}" if value else f"{key}=" for key, value in query)
    )


def actor_key(credential_id: int | None = None, *, unknown: str | None = None) -> str:
    if credential_id is not None:
        return f"credential:{credential_id}"
    if unknown is not None:
        return "unknown:" + unknown
    return "anonymous"


@dataclass(frozen=True)
class DiscoverySource:
    page_id: int | None
    state_key: str | None
    actor: str
    kind: str
    evidence: str | None = None


def _source_key(source: DiscoverySource) -> str:
    return json.dumps(
        [source.page_id, source.state_key, source.actor, source.kind, source.evidence],
        separators=(",", ":"),
    )


def record_discoveries(
    run_id: int,
    urls: list[str] | tuple[str, ...],
    *,
    source: DiscoverySource,
    state_key: str | None = None,
    session: Session | None = None,
) -> int:
    owned = session is None
    s = session or Session(get_engine())
    try:
        if s.get(TestRun, run_id) is None:
            raise ValueError("Web run does not exist")
        if source.page_id is not None:
            page = s.get(CrawledPage, source.page_id)
            if page is None or page.test_run_id != run_id:
                raise ValueError("Discovery page does not belong to this run")
        unique = list(dict.fromkeys(exact_url(url) for url in urls))
        key = _source_key(source)
        for start in range(0, len(unique), 200):
            for url in unique[start : start + 200]:
                s.exec(
                    insert(DiscoveredTarget)
                    .values(
                        test_run_id=run_id,
                        url=url,
                        state_key=state_key,
                        state_identity=state_identity(state_key),
                        route_pattern=route_pattern(url),
                    )
                    .on_conflict_do_nothing(
                        index_elements=["test_run_id", "url", "state_identity"]
                    )
                )
                target = s.exec(
                    select(DiscoveredTarget)
                    .where(DiscoveredTarget.test_run_id == run_id)
                    .where(DiscoveredTarget.url == url)
                    .where(DiscoveredTarget.state_identity == state_identity(state_key))
                ).one()
                s.exec(
                    insert(TargetDiscovery)
                    .values(
                        test_run_id=run_id,
                        target_id=target.id,
                        source_key=key,
                        source_page_id=source.page_id,
                        source_state_key=source.state_key,
                        actor_key=source.actor,
                        source_kind=source.kind,
                        source_ref=source.evidence,
                    )
                    .on_conflict_do_nothing(index_elements=["target_id", "source_key"])
                )
            if owned:
                s.commit()
        return len(unique)
    except Exception:
        s.rollback()
        if owned:
            with Session(get_engine()) as failure_session:
                run = failure_session.get(TestRun, run_id)
                if run is not None:
                    run.discovery_completeness = "incomplete"
                    failure_session.add(run)
                    failure_session.commit()
        raise
    finally:
        if owned:
            s.close()


def assign_route_patterns(run_id: int, offered: list[dict]) -> None:
    with Session(get_engine()) as s:
        for item in offered:
            key = item.get("route_pattern")
            if not key:
                continue
            target = s.exec(
                select(DiscoveredTarget)
                .where(DiscoveredTarget.test_run_id == run_id)
                .where(DiscoveredTarget.url == exact_url(item["url"]))
                .where(DiscoveredTarget.state_identity == state_identity(None))
            ).first()
            if target is not None and target.route_pattern != key:
                target.route_pattern = key
                s.add(target)
        s.commit()


def backfill_group_patterns(run_id: int, new_keys: set[str]) -> None:
    if not new_keys:
        return
    from aespa.services.route_sampling import _candidate_keys

    with Session(get_engine()) as s:
        targets = s.exec(
            select(DiscoveredTarget).where(DiscoveredTarget.test_run_id == run_id)
        )
        for target in targets:
            match = next(
                (key for key in sorted(new_keys) if key in _candidate_keys(target.url)),
                None,
            )
            if match and target.route_pattern != match:
                target.route_pattern = match
                s.add(target)
        s.commit()


def record_traffic_response(
    run_id: int,
    traffic_id: int,
    *,
    actor: str,
    state_key: str | None = None,
    verified_credential_id: int | None = None,
    session: Session | None = None,
) -> TargetAccessObservation:
    owned = session is None
    s = session or Session(get_engine(), expire_on_commit=False)
    try:
        traffic = s.get(TrafficEntry, traffic_id)
        if (
            traffic is None
            or traffic.test_run_id != run_id
            or traffic.api_test_run_id is not None
        ):
            raise ValueError("Traffic is not a direct response for this web run")
        url = exact_url(traffic.url)
        target = s.exec(
            select(DiscoveredTarget)
            .where(DiscoveredTarget.test_run_id == run_id)
            .where(DiscoveredTarget.url == url)
            .where(DiscoveredTarget.state_identity == state_identity(state_key))
        ).first()
        if target is None:
            record_discoveries(
                run_id,
                [url],
                source=DiscoverySource(
                    traffic.page_id, state_key, actor, "traffic", str(traffic.id)
                ),
                state_key=state_key,
                session=s,
            )
            target = s.exec(
                select(DiscoveredTarget)
                .where(DiscoveredTarget.test_run_id == run_id)
                .where(DiscoveredTarget.url == url)
                .where(DiscoveredTarget.state_identity == state_identity(state_key))
            ).one()
        if state_key is not None:
            page = s.get(CrawledPage, traffic.page_id) if traffic.page_id else None
            if (
                page is None
                or page.test_run_id != run_id
                or page.state_key != state_key
                or exact_url(page.url) != url
            ):
                raise ValueError("Traffic does not prove the selected browser state")
        run = s.get(TestRun, run_id)
        if actor.startswith("credential:"):
            try:
                credential = s.get(Credential, int(actor.partition(":")[2]))
            except ValueError as exc:
                raise ValueError("Invalid credential actor") from exc
            if (
                credential is None
                or credential.site_id != run.site_id
                or not traffic.username
                or credential.username != traffic.username
                or verified_credential_id != credential.id
            ):
                raise ValueError(
                    "Traffic actor needs the credential selected for the actual request"
                )
        elif actor == "anonymous":
            try:
                headers = json.loads(traffic.request_headers or "{}")
            except (ValueError, TypeError) as exc:
                raise ValueError("Cannot verify anonymous request headers") from exc
            if (
                not isinstance(headers, dict)
                or traffic.username
                or any(
                    key.lower()
                    in {"cookie", "authorization", "proxy-authorization", "x-api-key"}
                    and value
                    for key, value in headers.items()
                )
            ):
                raise ValueError(
                    "Authenticated traffic cannot be attributed to anonymous"
                )
        elif not actor.startswith("unknown:"):
            raise ValueError("Unknown actor type")
        body = (traffic.response_body or "")[:2000].lower()
        login_shell = traffic.status == 200 and any(
            marker in body
            for marker in ('type="password"', 'name="password"', "sign in to continue")
        )
        result = (
            "denied"
            if traffic.status in {401, 403}
            else "reached"
            if traffic.status is not None
            and 200 <= traffic.status < 300
            and not login_shell
            else "unknown"
        )
        s.exec(
            insert(TargetAccessObservation)
            .values(
                test_run_id=run_id,
                target_id=target.id,
                method=traffic.method.upper(),
                actor_key=actor,
                source_kind="traffic",
                source_id=traffic_id,
                result=result,
            )
            .on_conflict_do_nothing(
                index_elements=["test_run_id", "source_kind", "source_id"]
            )
        )
        row = s.exec(
            select(TargetAccessObservation)
            .where(TargetAccessObservation.test_run_id == run_id)
            .where(TargetAccessObservation.source_kind == "traffic")
            .where(TargetAccessObservation.source_id == traffic_id)
        ).one()
        if (
            row.target_id != target.id
            or row.actor_key != actor
            or row.method != traffic.method.upper()
        ):
            raise ValueError(
                "Traffic already has different target or actor attribution"
            )
        if owned:
            s.commit()
        return row
    finally:
        if owned:
            s.close()


def _cursor_id(
    cursor: str | None, run_id: int, route: str | None, search: str | None
) -> int:
    if not cursor:
        return 0
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        digest = hashlib.sha256(
            json.dumps([run_id, route, search]).encode()
        ).hexdigest()[:16]
        if value[0] != digest or not isinstance(value[1], int) or value[1] < 0:
            raise ValueError
        return value[1]
    except Exception as exc:
        raise ValueError("Invalid inventory cursor") from exc


def _next_cursor(
    row_id: int, run_id: int, route: str | None, search: str | None
) -> str:
    digest = hashlib.sha256(json.dumps([run_id, route, search]).encode()).hexdigest()[
        :16
    ]
    return (
        base64.urlsafe_b64encode(json.dumps([digest, row_id]).encode())
        .decode()
        .rstrip("=")
    )


def list_targets(
    run_id: int,
    *,
    route_pattern_filter: str | None = None,
    search: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    session: Session | None = None,
) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    after = _cursor_id(cursor, run_id, route_pattern_filter, search)
    owned = session is None
    s = session or Session(get_engine())
    try:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError("Web run does not exist")
        query = select(DiscoveredTarget).where(DiscoveredTarget.test_run_id == run_id)
        if route_pattern_filter:
            query = query.where(DiscoveredTarget.route_pattern == route_pattern_filter)
        if search:
            matched_credentials = s.exec(
                select(Credential.id)
                .where(Credential.site_id == run.site_id)
                .where(
                    or_(
                        Credential.username.contains(search, autoescape=True),
                        Credential.label.contains(search, autoescape=True),
                    )
                )
            ).all()
            actor_keys = [
                f"credential:{credential_id}" for credential_id in matched_credentials
            ]
            if "anonymous".startswith(search.lower()):
                actor_keys.append("anonymous")
            actor_targets = (
                select(TargetDiscovery.target_id)
                .where(
                    TargetDiscovery.test_run_id == run_id,
                    TargetDiscovery.actor_key.in_(actor_keys),
                )
                .union(
                    select(TargetAccessObservation.target_id).where(
                        TargetAccessObservation.test_run_id == run_id,
                        TargetAccessObservation.actor_key.in_(actor_keys),
                    )
                )
            )
            query = query.where(
                or_(
                    DiscoveredTarget.url.contains(search, autoescape=True),
                    DiscoveredTarget.id.in_(actor_targets),
                )
            )
        total = s.exec(select(func.count()).select_from(query.subquery())).one()
        rows = list(
            s.exec(
                query.where(DiscoveredTarget.id > after)
                .order_by(DiscoveredTarget.id)
                .limit(limit + 1)
            )
        )
        page = rows[:limit]
        ids = [row.id for row in page]
        sightings = (
            list(
                s.exec(
                    select(TargetDiscovery).where(TargetDiscovery.target_id.in_(ids))
                )
            )
            if ids
            else []
        )
        observations = (
            list(
                s.exec(
                    select(TargetAccessObservation).where(
                        TargetAccessObservation.target_id.in_(ids)
                    )
                )
            )
            if ids
            else []
        )
        checks = (
            list(
                s.exec(
                    select(ScanObligation)
                    .where(ScanObligation.run_kind == "web")
                    .where(ScanObligation.run_id == run_id)
                    .where(ScanObligation.scope_kind == "object")
                    .where(ScanObligation.target_id.in_(ids))
                )
            )
            if ids
            else []
        )
        check_ids = [check.id for check in checks]
        findings = (
            list(
                s.exec(
                    select(ScanFinding)
                    .where(ScanFinding.test_run_id == run_id)
                    .where(ScanFinding.object_check_id.in_(check_ids))
                )
            )
            if check_ids
            else []
        )
        finding_ids = {}
        confirmed_checks = set()
        for finding in findings:
            finding_ids.setdefault(finding.object_check_id, []).append(finding.id)
            if finding.validation_status == "confirmed":
                confirmed_checks.add(finding.object_check_id)
        pages = list(
            s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id))
        )
        crawled = {
            (page.url, state_identity(page.state_key))
            for page in pages
            if page.status == "crawled"
        }
        credentials = {
            f"credential:{row.id}": row
            for row in s.exec(
                select(Credential).where(Credential.site_id == run.site_id)
            )
        }

        def actor(value: str) -> dict:
            credential = credentials.get(value)
            return {
                "actor_key": value,
                "label": (credential.label or credential.username)
                if credential
                else ("Anonymous" if value == "anonymous" else "Unknown account"),
            }

        items = []
        for row in page:
            seen = sorted(
                {entry.actor_key for entry in sightings if entry.target_id == row.id}
            )
            access = [entry for entry in observations if entry.target_id == row.id]
            items.append(
                {
                    "id": row.id,
                    "url": row.url,
                    "state_key": row.state_key,
                    "route_pattern": row.route_pattern,
                    "seen_by": [actor(value) for value in seen],
                    "crawled": (row.url, row.state_identity) in crawled,
                    "access": [
                        {
                            **actor(entry.actor_key),
                            "result": entry.result,
                            "method": entry.method,
                        }
                        for entry in access
                    ],
                    "selected_checks": [
                        {
                            "id": check.id,
                            "category": check.owasp_category,
                            "method": check.http_method,
                            "baseline_actor": actor(check.baseline_actor_key),
                            "comparison_actor": actor(check.comparison_actor_key),
                            "status": "finding"
                            if check.id in confirmed_checks
                            else check.status,
                            "finding_ids": finding_ids.get(check.id, []),
                            "reason": check.exemption_reason,
                        }
                        for check in checks
                        if check.target_id == row.id
                    ],
                }
            )
        return {
            "items": items,
            "next_cursor": _next_cursor(
                page[-1].id, run_id, route_pattern_filter, search
            )
            if len(rows) > limit
            else None,
            "total": total,
            "discovery_completeness": run.discovery_completeness,
        }
    finally:
        if owned:
            s.close()
