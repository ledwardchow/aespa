"""Proposed interfaces only. This module is not imported by AESPA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType

TargetId = NewType("TargetId", int)
CheckId = NewType("CheckId", int)
ObservationId = NewType("ObservationId", int)
HandoffId = NewType("HandoffId", int)
HttpMethod = NewType("HttpMethod", str)


@dataclass(frozen=True)
class RunRef:
    kind: Literal["web", "api"]
    id: int


@dataclass(frozen=True)
class AnonymousActor:
    pass


@dataclass(frozen=True)
class CredentialActor:
    credential_id: int


@dataclass(frozen=True)
class UnknownActor:
    source_identity: str


Actor = AnonymousActor | CredentialActor | UnknownActor


@dataclass(frozen=True)
class SingleActor:
    actor: Actor


@dataclass(frozen=True)
class AccountComparison:
    baseline: CredentialActor
    comparison: CredentialActor | AnonymousActor


@dataclass(frozen=True)
class ExactTarget:
    url: str
    state_key: str | None = None


@dataclass(frozen=True)
class EvidenceRef:
    kind: Literal[
        "traffic", "page_view", "probe", "lead", "coverage_evidence", "intel", "retry"
    ]
    id: int
    snapshot_revision: str | None = None


@dataclass(frozen=True)
class DirectResponseRef:
    kind: Literal["traffic", "page_view", "probe"]
    id: int
    snapshot_revision: str | None = None


@dataclass(frozen=True)
class EvaluationRef:
    coverage_evidence_id: int


@dataclass(frozen=True)
class EvidenceSet:
    refs: tuple[EvidenceRef, ...]


@dataclass(frozen=True)
class RequestScope:
    method: HttpMethod
    target: ExactTarget
    body_identity: str | None = None
    request_template: EvidenceRef | None = None


@dataclass(frozen=True)
class InvestigationScope:
    request: RequestScope
    attack_class: str
    parameter: str | None
    actors: SingleActor | AccountComparison


@dataclass(frozen=True)
class AccessComparisonScope(InvestigationScope):
    actors: AccountComparison


@dataclass(frozen=True)
class DiscoverySource:
    page_id: int | None
    state_key: str | None
    actor: Actor
    kind: Literal["dom_link", "script_route", "form", "traffic", "archive"]
    evidence: EvidenceRef | None = None


@dataclass(frozen=True)
class TargetQuery:
    route: str | None = None
    actor: Actor | None = None
    source_page_id: int | None = None
    search: str | None = None
    after: str | None = None
    limit: int = 50


@dataclass(frozen=True)
class TargetRecord:
    id: TargetId
    target: ExactTarget
    route_pattern: str
    seen_by: tuple[Actor, ...]
    observation_ids: tuple[ObservationId, ...]


@dataclass(frozen=True)
class TargetPage:
    items: tuple[TargetRecord, ...]
    next_cursor: str | None
    discovery_completeness: Literal["recorded", "legacy_unknown", "incomplete"]


@dataclass(frozen=True)
class RecordedResponse:
    request: RequestScope
    actor: Actor
    source: DirectResponseRef


@dataclass(frozen=True)
class AccessObservation:
    id: ObservationId
    target_id: TargetId
    method: HttpMethod
    actor: Actor
    source: DirectResponseRef
    reachability: Literal["reached", "denied", "unknown"]


class TargetCatalog:
    def record_discoveries(
        self,
        run_id: int,
        *,
        source: DiscoverySource,
        targets: tuple[ExactTarget, ...],
    ) -> None:
        """Commit exact targets and sightings before sampling can discard links."""
        raise NotImplementedError

    def targets(self, run_id: int, query: TargetQuery) -> TargetPage:
        """Filter before keyset paging; discovery creates no page or test work."""
        raise NotImplementedError

    def record_response(
        self, run_id: int, response: RecordedResponse
    ) -> AccessObservation:
        """Verify run, target/state, method, actor and direct response before indexing."""
        raise NotImplementedError


@dataclass(frozen=True)
class PageCoverageUnit:
    page_cell_id: int
    test_class: str | None = None


@dataclass(frozen=True)
class SelectedObjectUnit:
    check_id: CheckId


CoverageUnit = PageCoverageUnit | SelectedObjectUnit


@dataclass(frozen=True)
class AccessCheckRequest:
    request: RequestScope
    technique: str
    parameter: str | None
    actors: AccountComparison
    baseline: ObservationId
    entitlement: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class SelectedCheck:
    id: CheckId
    scope: AccessComparisonScope
    baseline: ObservationId
    coverage_unit: CoverageUnit


@dataclass(frozen=True)
class IdorBudget:
    targets: int = 80
    comparison_actors_per_target: int = 3


@dataclass(frozen=True)
class EvaluatedCheckResult:
    target: ExactTarget
    actors: AccountComparison
    execution: DirectResponseRef
    evaluation: EvaluationRef
    outcome: Literal["passed", "finding", "inconclusive"]


@dataclass(frozen=True)
class BlockedCheckResult:
    target: ExactTarget
    actors: AccountComparison
    reason: str
    evidence: EvidenceRef


CheckResult = EvaluatedCheckResult | BlockedCheckResult


@dataclass(frozen=True)
class Completion:
    exercised_units: int
    applicable_units: int
    resolved_units: int
    unresolved_units: tuple[CoverageUnit, ...]
    target_met: bool


class WebWorkprogram:
    def select_check(self, run_id: int, request: AccessCheckRequest) -> SelectedCheck:
        """Upsert one chosen object check and derive its exact parent unit."""
        raise NotImplementedError

    def select_idor_checks(
        self,
        run_id: int,
        active_actors: tuple[CredentialActor, ...],
        budget: IdorBudget,
    ) -> tuple[SelectedCheck, ...]:
        """Select bounded same-object comparisons with positive identified baselines."""
        raise NotImplementedError

    def record_result(
        self, run_id: int, check_id: CheckId, result: CheckResult
    ) -> None:
        """Validate evidence attribution and update only this check and exact parent."""
        raise NotImplementedError

    def completion(
        self,
        run_id: int,
        *,
        mode: Literal["standard", "enforce"],
        target_percent: int,
    ) -> Completion:
        """Project distinct root units; neither inventory nor display totals count."""
        raise NotImplementedError


@dataclass(frozen=True)
class HandoffClaim:
    status: Literal[
        "created",
        "already_investigated",
        "deferred",
        "insufficient_new_evidence",
    ]
    handoff_id: HandoffId | None
    reason: str


class SpecialistHandoffs:
    def claim(
        self,
        *,
        run: RunRef,
        scope: InvestigationScope,
        evidence: EvidenceSet,
    ) -> HandoffClaim:
        """Admit evidence revision and atomically claim or retain exact-scope work."""
        raise NotImplementedError
