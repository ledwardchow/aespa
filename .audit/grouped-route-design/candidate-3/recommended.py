"""Type sketch for Candidate 3. Bodies intentionally remain unimplemented."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence


class IdentityKind(StrEnum):
    ANONYMOUS = "anonymous"
    CREDENTIAL = "credential"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DiscoveryIdentity:
    kind: IdentityKind
    credential_id: int | None = None
    label: str | None = None


@dataclass(frozen=True)
class Discovery:
    url: str
    state_key: str | None
    source_page_id: int | None
    source_state_key: str | None
    identity: DiscoveryIdentity
    source: str


@dataclass(frozen=True)
class TargetFilter:
    kind: str | None = None
    source: str | None = None
    identity: DiscoveryIdentity | None = None


@dataclass(frozen=True)
class TargetRecord:
    target_key: str
    url: str
    state_key: str | None
    discovered_by: tuple[DiscoveryIdentity, ...]


@dataclass(frozen=True)
class TargetPage:
    items: tuple[TargetRecord, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class IdorSelection:
    target_key: str
    target_url: str
    baseline_page_id: int
    baseline_credential_id: int
    comparison_credential_id: int
    route_template: str


@dataclass(frozen=True)
class HandoffRequest:
    run_id: int
    run_kind: str
    attack_class: str
    target_url: str
    parameter: str | None
    session_label: str | None
    evidence_key: str


def record_discoveries(
    session: object, *, run_id: int, discoveries: Sequence[Discovery]
) -> None:
    """Upsert exact targets and idempotent source/identity evidence."""
    raise NotImplementedError


def page_targets(
    session: object,
    *,
    run_id: int,
    filter: TargetFilter,
    after: str | None,
    limit: int,
) -> TargetPage:
    """Return a keyset page; never create pages or obligations."""
    raise NotImplementedError


def select_idor_work(
    session: object,
    *,
    run_id: int,
    object_limit: int = 80,
    identities_per_object: int = 3,
) -> tuple[IdorSelection, ...]:
    """Select exact visited objects with a positive identified baseline."""
    raise NotImplementedError


def ensure_object_obligation(
    session: object, *, run_id: int, selection: IdorSelection
) -> int:
    """Insert once by a stable obligation scope fingerprint."""
    raise NotImplementedError


def create_or_get_handoff(
    session: object, request: HandoffRequest
) -> tuple[int, bool]:
    """Deduplicate identical evidence and reopen completed scope for new evidence."""
    raise NotImplementedError

