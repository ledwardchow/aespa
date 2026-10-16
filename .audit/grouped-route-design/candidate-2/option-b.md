# Option B - target fact journal

## Caller usage

The crawler appends link facts in bounded batches before sampling. It appends a separate direct-fetch fact after a response is classified. The scanner asks the journal for a bounded selection, and result facts close only those selected checks.

```python
journal = TargetJournal(session_factory)
journal.append_links(source, [DiscoveredLink(url=url, text=text) for url, text in batch])
admitted = sampler.offer(link_items, phase_key, route_is_queued)
journal.append_fetch(fetch_observation)
targets = journal.targets(run_id, after_target_key=cursor, limit=100)
checks = journal.select_idor_tests(run_id, active_credential_ids=set(cred_sessions),
                                   max_targets=80, max_other_actors=3)
for check in checks:
    result = await fetch_with_existing_policy(check.url, check.other_credential_id)
    journal.append_result(check.selection_key, result.to_evidence())
```

Specialist claim uses the same `claim_specialist_handoff` signature in `sketch.py`, with exact scope and a persisted evidence token. This is orthogonal to the journal because API and web handoffs share the specialist table.

## Type and signature sketch

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class TargetFact:
    run_id: int
    event_key: str
    kind: Literal["link_seen", "fetch_reached", "fetch_denied", "fetch_unknown",
                  "selected_test", "test_result"]
    exact_url: str
    state_key: str | None
    source_page_id: int | None
    actor_id: int | None
    traffic_id: int | None
    selection_key: str | None
    payload_json: str

@dataclass(frozen=True)
class JournalTargetPage:
    records: tuple[TargetRecord, ...]
    next_after_target_key: str | None

@dataclass(frozen=True)
class JournalSelectedIdorTest:
    selection_key: str
    url: str
    owner_credential_id: int
    other_credential_id: int
    baseline_observation_id: int

class TargetJournal:
    def __init__(self, session_factory): raise NotImplementedError
    def append_links(self, source: DiscoverySource, links: list[DiscoveredLink]) -> None:
        raise NotImplementedError
    def append_fetch(self, observation: FetchObservation) -> int:
        raise NotImplementedError
    def targets(self, run_id: int, *, after_target_key: str | None, limit: int) -> JournalTargetPage:
        raise NotImplementedError
    def select_idor_tests(self, run_id: int, *, active_credential_ids: set[int],
                          max_targets: int, max_other_actors: int) -> tuple[JournalSelectedIdorTest, ...]:
        raise NotImplementedError
    def append_result(self, selection_key: str, evidence: SelectedResultEvidence) -> None:
        raise NotImplementedError
```

`DiscoverySource`, `DiscoveredLink`, `FetchObservation`, `TargetRecord`, and `SelectedResultEvidence` have the definitions in `sketch.py`. The journal's event body is tagged and validated at append time. A typed internal fold refuses illegal field combinations, such as a `link_seen` fact claiming an access result. The public surface hides this event representation.

## Ownership and migration

One `target_fact` table owns discovery, response, selection, and result history. Unique `(run_id, event_key)` and append-only writes make concurrent crawler phases and retries safe. A transaction appends each link batch before the sampler advances. Queries fold facts by exact URL and state, using a materialized SQLite projection or SQL aggregation with keyset pagination. A projection rebuild must be deterministic from facts and must not be a second writable source of truth. The old 300-link producer cap and 1000-row inventory prefilter cap are removed. Link text can be truncated, but URLs cannot. The sampler's member identity includes raw query and meaningful fragment.

Recon folds direct response facts for the same exact object and actor; link sightings never imply access or ownership. Page cells remain tied to visited/replayed pages, including interactive states. Selected-test facts add only bounded checks to the completion denominator. Standard completion reads raw page cells and selected facts, and the frontend uses that same progress value while still showing grouped rows. An arbitrary mutated URL does not become a page or inherit a representative page's status. IDOR requires a positive baseline and compares another actor against that same object, returning inconclusive for ambiguous responses.

An Alembic revision creates the journal and its indexes and changes handoff keys to exact scope plus evidence. Crawl archive v2 exports ordered facts with page, credential, and traffic reference keys; import remaps them and rebuilds projections. Version 1 imports as an empty journal. No old group count can reconstruct lost URLs. Legacy terminal handoffs get row-specific legacy evidence keys, so they cannot suppress future object-specific leads. Active exact-scope handoffs remain exclusive until terminal. Scope and request policy are checked at execution time.

This option has a smaller write schema and a useful audit history. It asks every reader to fold a tagged stream, so the target list, access summary, and selected-work query are more complex and need careful projection invalidation. Option A was chosen because those three reads dominate the current product.
