"""Signature sketch for candidate 1. All bodies are intentionally unimplemented."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


@dataclass(frozen=True)
class DiscoveredLink:
    exact_url: str
    source_page_id: int
    source_state_key: str | None
    credential_id: int | None  # None means anonymous, not an unknown credential.
    link_text: str
    target_state_key: str | None = None


@dataclass(frozen=True)
class TargetRef:
    id: int
    exact_url: str
    state_key: str | None
    route_pattern: str  # Display/search grouping only.


@dataclass(frozen=True)
class TargetQuery:
    search: str | None = None
    route: str | None = None
    credential_id: int | None = None
    source: str | None = None
    source_page_id: int | None = None
    limit: int = 50
    cursor: str | None = None


@dataclass(frozen=True)
class TargetPage:
    items: list[TargetRef]
    next_cursor: str | None


class ResponseKind(str, Enum):
    SUCCESS = "success"
    DENIAL = "denial"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class ResponseFact:
    target_id: int
    credential_id: int | None
    traffic_id: int | None
    page_view_id: int | None
    kind: ResponseKind
    content_digest: str | None
    # Success means a positive response for this exact URL. It does not mean ownership.


@dataclass(frozen=True)
class IdorBudget:
    total: int
    per_route: int
    identity_pairs_per_route: int


@dataclass(frozen=True)
class IdorProbe:
    target: TargetRef
    baseline_credential_id: int
    test_credential_id: int
    positive_baseline: ResponseFact
    entitlement_evidence_id: int | None
    # A missing entitlement record permits exploration, never confirmed IDOR.


def record_links(run_id: int, links: list[DiscoveredLink]) -> list[TargetRef]:
    """Validate URLs, insert exact targets and per-source provenance, then return refs.

    A run/exact URL/state key has one target. A source page/state/actor/target has
    one link fact. Both use database uniqueness plus insert-on-conflict, so two
    crawler workers and a resumed crawl converge without JSON lost updates.
    No links are silently capped at 300. The caller keeps all raw links until
    this transaction succeeds, before the sampler can hold any of them.
    """
    raise NotImplementedError


def list_targets(run_id: int, query: TargetQuery) -> TargetPage:
    """Keyset-page exact targets after SQL-side filters and scope checks.

    Cursor includes the last stable target id and a query digest. Invalid or
    mismatched cursors fail at this boundary; the caller never prefetches an
    arbitrary first 1,000 rows. Count, if exposed, is separately qualified.
    """
    raise NotImplementedError


def record_response(run_id: int, fact: ResponseFact, event_key: str) -> None:
    """Persist one observed response, idempotently by run and source event key.

    A response is for one exact target and actor. Absence of a row is unknown.
    PageCredentialView and TrafficEntry remain primary evidence; this row is
    their target/actor index, not a separate claim of authorization.
    """
    raise NotImplementedError


def select_idor_probes(run_id: int, budget: IdorBudget) -> list[IdorProbe]:
    """Select bounded exact-target checks with a positive same-target baseline.

    Group by route only to spend the budget fairly. Prefer objects with distinct
    observed identities and stronger entitlement evidence. Do not compare text
    across different object URLs or infer denial from an unobserved identity.
    A discovered-only target may enter through a separately budgeted positive
    baseline request; a link alone never qualifies as a baseline.
    """
    raise NotImplementedError


@dataclass(frozen=True)
class EvidenceRef:
    kind: Literal["traffic", "lead", "finding", "crawl_observation"]
    id: int


@dataclass(frozen=True)
class Scope:
    attack_class: str
    exact_url: str
    state_key: str | None
    method: str
    parameter: str | None
    session_label: str | None


@dataclass(frozen=True)
class HandoffClaim:
    handoff_id: int
    created: bool
    status: str


def claim_handoff(
    *, run_id: int, run_kind: Literal["web", "api"], scope: Scope,
    evidence: EvidenceRef, agent_id: str, rationale: str, priority: int,
) -> HandoffClaim:
    """Atomically claim one exact scope and evidence event.

    An active exact-scope handoff wins. A terminal handoff suppresses only an
    already-seen evidence event. A new durable event can open a new attempt.
    URL query bytes and meaningful fragment participate in the scope digest.
    Use unique constraints and retry a conflicting insert by rereading, not a
    process-local lock. Operation-level dispatch budgets control volume.
    """
    raise NotImplementedError


def coverage_progress(run_id: int) -> tuple[int, int]:
    """Return exercised and applicable persisted test cells for Standard mode.

    Resolve each PageOwaspTest or selected ScanObligation separately. Display
    rows may group pages, but their highest child status cannot supply either
    count. Inventory-only targets do not add cells to the denominator.
    """
    raise NotImplementedError


def attribute_test_result(
    *, run_id: int, target_id: int, traffic_id: int,
    source_page_id: int | None, source_state_key: str | None,
    obligation_id: int | None, outcome: Literal["passed", "finding", "inconclusive", "blocked"],
) -> None:
    """Attach exact target evidence to a selected test, without route fallback.

    A page cell changes only if source_page_id is the same exact visited target
    and state. Otherwise the outcome belongs to the route obligation and its
    ProbeExecution/TrafficEntry. The source page remains a navigation/replay
    hint. A mutated payload does not create a CrawledPage or broad coverage.
    """
    raise NotImplementedError
