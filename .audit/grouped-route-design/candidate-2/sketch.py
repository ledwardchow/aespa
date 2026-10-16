"""Design sketch only. Bodies intentionally do not implement persistence or requests."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from sqlmodel import Session


@dataclass(frozen=True)
class DiscoverySource:
    run_id: int
    page_id: int
    state_key: str | None
    credential_id: int | None
    kind: Literal["dom_link", "script_route", "form", "traffic"]


@dataclass(frozen=True)
class DiscoveredLink:
    url: str  # Preserve path, raw query bytes, repeated/empty keys, and SPA fragment.
    text: str = ""


@dataclass(frozen=True)
class FetchObservation:
    run_id: int
    url: str
    state_key: str | None
    credential_id: int | None
    page_id: int | None
    traffic_id: int | None
    result: Literal["reached", "denied", "unknown"]
    content_fingerprint: str | None


@dataclass(frozen=True)
class TargetRecord:
    id: int
    url: str
    state_key: str | None
    route_pattern: str  # Display/planning label only, never the exact-target key.
    discovery_count: int


@dataclass(frozen=True)
class TargetPage:
    records: tuple[TargetRecord, ...]
    next_after_id: int | None


@dataclass(frozen=True)
class SelectedIdorTest:
    obligation_id: int
    url: str
    state_key: str | None
    owner_credential_id: int
    other_credential_id: int
    baseline_observation_id: int


@dataclass(frozen=True)
class SelectedResultEvidence:
    traffic_id: int | None
    outcome: Literal["passed", "finding", "inconclusive", "blocked"]
    evidence_hash: str | None


class TargetCatalog:
    """Owns exact target facts and bounded security-test selection."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        raise NotImplementedError

    def record_discoveries(
        self, source: DiscoverySource, links: Sequence[DiscoveredLink]
    ) -> None:
        """Upsert exact targets and per-source/actor sightings in one transaction."""
        raise NotImplementedError

    def record_fetch(self, observation: FetchObservation) -> int:
        """Return durable observation ID; a sighting alone is never reached."""
        raise NotImplementedError

    def targets(self, run_id: int, *, after_id: int | None, limit: int) -> TargetPage:
        """Keyset pagination; apply source/scope filters in SQL before LIMIT."""
        raise NotImplementedError

    def select_idor_tests(
        self, run_id: int, *, active_credential_ids: set[int],
        max_targets: int, max_other_actors: int
    ) -> tuple[SelectedIdorTest, ...]:
        """Persist bounded selected ScanObligations with positive baselines."""
        raise NotImplementedError

    def record_selected_result(
        self, obligation_id: int, evidence: SelectedResultEvidence
    ) -> None:
        """Persist a result once; repeat delivery must not duplicate proof."""
        raise NotImplementedError


@dataclass(frozen=True)
class SpecialistScope:
    attack_class: str
    url: str
    state_key: str | None
    parameter: str | None
    actor_ids: tuple[int, ...]  # One actor normally; IDOR has an ordered owner/other pair.


@dataclass(frozen=True)
class EvidenceToken:
    source: Literal["traffic", "access_observation", "manual"]
    source_id: int | None  # None only for manual; repeat manual requests share a token.


@dataclass(frozen=True)
class HandoffClaim:
    status: Literal["created", "duplicate", "active_conflict"]
    handoff_id: int


def claim_specialist_handoff(
    session_factory: Callable[[], Session], *, run_id: int, run_kind: Literal["web", "api"],
    scope: SpecialistScope, evidence: EvidenceToken
) -> HandoffClaim:
    """Atomically claim exact scope plus evidence; terminal rows do not own future evidence."""
    raise NotImplementedError
