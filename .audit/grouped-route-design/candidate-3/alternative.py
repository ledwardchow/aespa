"""Type sketch for the TargetIntelItem-based alternative."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class NavigationTarget:
    url: str
    source_page_id: int | None
    source_state_key: str | None
    identity_key: str
    source: str


@dataclass(frozen=True)
class TargetIntelFilter:
    source: str | None = None
    identity_key: str | None = None
    search: str | None = None


@dataclass(frozen=True)
class NavigationTargetPage:
    items: tuple[NavigationTarget, ...]
    next_cursor: str | None


def record_navigation_targets(
    session: object,
    *,
    run_id: int,
    observations: Sequence[NavigationTarget],
) -> None:
    """Persist exact URLs and identity provenance using an intel upsert."""
    raise NotImplementedError


def page_navigation_targets(
    session: object,
    *,
    run_id: int,
    filter: TargetIntelFilter,
    after: str | None,
    limit: int,
) -> NavigationTargetPage:
    """Return deduplicated exact targets using a stable keyset cursor."""
    raise NotImplementedError
