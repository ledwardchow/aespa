from __future__ import annotations

import json

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    DiscoveredTarget,
    TargetAccessObservation,
    TestRun,
    WorkflowTargetReservation,
)
from aespa.services.target_catalog import exact_url


def _confirmed_group(session: Session, run: TestRun, example_url: str) -> str | None:
    try:
        groups = json.loads(run.route_groups_json or "[]")
        example = exact_url(example_url)
    except (TypeError, ValueError):
        return None
    if not isinstance(groups, list):
        return None
    source = session.exec(
        select(DiscoveredTarget).where(
            DiscoveredTarget.test_run_id == run.id,
            DiscoveredTarget.url == example,
        )
    ).first()
    if source is None:
        return None
    for group in groups:
        if not isinstance(group, dict):
            continue
        pattern = group.get("route_pattern")
        if isinstance(pattern, str) and pattern == source.route_pattern:
            return pattern
    return None


def workflow_group_for_example(run_id: int, example_url: str) -> str | None:
    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        return _confirmed_group(session, run, example_url) if run else None


def get_workflow_target(run_id: int, owner_key: str) -> dict | None:
    with Session(get_engine()) as session:
        claim = session.exec(
            select(WorkflowTargetReservation).where(
                WorkflowTargetReservation.test_run_id == run_id,
                WorkflowTargetReservation.owner_key == owner_key,
            )
        ).first()
        if claim is None:
            return None
        return {
            "target_url": claim.target_url,
            "route_pattern": claim.route_pattern,
            "example_url": claim.example_url,
            "owner_key": claim.owner_key,
        }


def reserve_workflow_target(
    run_id: int,
    owner_key: str,
    example_url: str,
    *,
    actor_key: str | None = None,
    exclude_urls: set[str] | None = None,
    preferred_url: str | None = None,
) -> dict | None:
    """Claim one exact member of an observed route group for a workflow attempt.

    A unique database constraint prevents another worker from claiming the item.
    Claims survive retries and process restarts. Callers must check the page's
    action controls before acting on an uncrawled item.
    """
    for _ in range(4):
        with Session(get_engine()) as session:
            run = session.get(TestRun, run_id)
            if run is None:
                raise ValueError("Web run does not exist")
            prior = session.exec(
                select(WorkflowTargetReservation).where(
                    WorkflowTargetReservation.test_run_id == run_id,
                    WorkflowTargetReservation.owner_key == owner_key,
                )
            ).first()
            if prior:
                return {
                    "target_url": prior.target_url,
                    "route_pattern": prior.route_pattern,
                    "example_url": prior.example_url,
                    "owner_key": prior.owner_key,
                }
            pattern = _confirmed_group(session, run, example_url)
            if pattern is None:
                return None
            targets = list(
                session.exec(
                    select(DiscoveredTarget).where(
                        DiscoveredTarget.test_run_id == run_id,
                        DiscoveredTarget.route_pattern == pattern,
                    )
                )
            )
            if not targets:
                return None
            if preferred_url is not None:
                try:
                    preferred_url = exact_url(preferred_url)
                except ValueError:
                    return None
                if all(target.url != preferred_url for target in targets):
                    return None
            reached = set()
            if actor_key:
                reached = set(
                    session.exec(
                        select(TargetAccessObservation.target_id).where(
                            TargetAccessObservation.test_run_id == run_id,
                            TargetAccessObservation.actor_key == actor_key,
                            TargetAccessObservation.result == "reached",
                        )
                    )
                )
            reserved = set(
                session.exec(
                    select(WorkflowTargetReservation.target_url).where(
                        WorkflowTargetReservation.test_run_id == run_id
                    )
                )
            )
            try:
                example = exact_url(example_url)
            except ValueError:
                return None
            candidates = sorted(
                (
                    target
                    for target in targets
                    if target.url not in reserved
                    and target.url not in (exclude_urls or set())
                    and (preferred_url is None or target.url == preferred_url)
                ),
                key=lambda target: (
                    target.id not in reached,
                    target.url != example,
                    target.id,
                ),
            )
            if not candidates:
                return None
            target = candidates[0]
            claim = WorkflowTargetReservation(
                test_run_id=run_id,
                owner_key=owner_key,
                target_url=target.url,
                route_pattern=pattern,
                example_url=example_url,
            )
            session.add(claim)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                continue
            return {
                "target_url": target.url,
                "route_pattern": pattern,
                "example_url": example_url,
                "owner_key": owner_key,
            }
    raise RuntimeError("Could not reserve a workflow target after concurrent claims")


def release_workflow_target(run_id: int, owner_key: str, target_url: str) -> None:
    """Release a claim only before the workflow has changed the item."""
    with Session(get_engine()) as session:
        claim = session.exec(
            select(WorkflowTargetReservation).where(
                WorkflowTargetReservation.test_run_id == run_id,
                WorkflowTargetReservation.owner_key == owner_key,
                WorkflowTargetReservation.target_url == target_url,
            )
        ).first()
        if claim is not None:
            session.delete(claim)
            session.commit()
