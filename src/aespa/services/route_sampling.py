"""Conservative, opt-in admission of repeated URL pages to a web crawl."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from typing import Callable
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

MIN_SIBLINGS = 10
# Once one route of a URL shape is confirmed (for example /tech/{id}/{slug}),
# other routes with the same shape (/games/{id}/{slug}) need fewer links.
KNOWN_SHAPE_SIBLINGS = 2
INITIAL_SAMPLES = 3
CONFIRM_SAMPLES = 5
MAX_UNCERTAIN_SAMPLES = 12
# Pages that fail to load are replaced by other examples, up to this many.
MAX_FAILED_SAMPLES = 2
# Patterns still below MIN_SIBLINGS are counted across pages. Cap the number
# tracked so a site with many unrelated URL shapes cannot grow this forever.
MAX_TRACKED_PATTERNS = 2_000
SAVE_INTERVAL_SECONDS = 5.0
# Layout similarity between pages of one template varies by site: about 0.65
# for large retail pages with many optional panels, 0.95 or more for simple
# themes. So an example belongs to a group when it is at least OUTLIER_RATIO as
# similar to the group's most typical page as the other examples are, and
# never below SIMILARITY_FLOOR.
SIMILARITY_FLOOR = 0.5
OUTLIER_RATIO = 0.75
# A route is confirmed when this share of its examples belong to one group.
# The other examples are still visited and reported as different.
DOMINANT_SHARE = 0.75
LAYOUT_SKETCH_SIZE = 256
_ACTION_SEGMENTS = {
    "account",
    "admin",
    "cart",
    "checkout",
    "create",
    "delete",
    "edit",
    "login",
    "logout",
    "new",
    "register",
    "search",
    "settings",
    "signin",
    "signup",
    "update",
}
IsQueued = Callable[[str], bool]


def _value_like(text: str) -> bool:
    """Return whether a path segment or query value looks like an ID or slug.

    IDs contain digits or are long tokens; slugs are several joined words.
    Short words such as ``products`` or ``p`` name a section instead.
    """
    text = unquote(text)
    if re.search(r"\d", text) or len(text) >= 20:
        return True
    return len([word for word in re.split(r"[-_.+~= ]+", text) if word]) >= 3


def _fragment(fragment: str) -> str:
    # Match the crawler: only client-side routes (#/...) are separate pages.
    return fragment if fragment.startswith("/") else ""


def _identity(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            parts.query,
            _fragment(parts.fragment),
        )
    )


def _path_identity(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            "",
            _fragment(parts.fragment),
        )
    )


def _member_identity(url: str, key: str) -> str:
    """Return what makes a link a distinct member of a route.

    Routes found from the path ignore the query string, so the same item
    linked with different tracking or sorting values is counted once.
    """
    return _identity(url) if "?" in key else _path_identity(url)


def _key_shape(key: str) -> str:
    """Describe a route by which parts are fixed words and which vary."""
    route, _, query = key.partition("?")
    path = route.split("://", 1)[-1].partition("/")[2]
    path_shape = "/".join(
        "V" if seg == "{value}" or _value_like(seg) else "L"
        for seg in path.split("/")
        if seg
    )
    query_shape = "&".join(
        sorted(
            f"{name}=V" if value == "{value}" else name
            for name, value in parse_qsl(query, keep_blank_values=True)
        )
    )
    return path_shape + ("?" + query_shape if query_shape else "")


def _seen_hash(identity: str) -> str:
    return hashlib.sha256(identity.encode()).hexdigest()[:12]


def _candidate_keys(url: str) -> list[str]:
    parts = urlsplit(url)
    if parts.fragment.startswith("/"):
        return []
    segments = [segment for segment in parts.path.split("/") if segment]
    # An action word may be a fixed part of a route (/admin/products/{value})
    # but never the part that varies: /products/new or /orders/5/delete is an
    # operation, not another member of the route.
    actions = {
        index
        for index, segment in enumerate(segments)
        if segment.lower() in _ACTION_SEGMENTS
    }
    base = f"{parts.scheme.lower()}://{parts.netloc.lower()}"
    keys = []
    # Path routes ignore the query string. Whether a query value changes the
    # page is decided by comparing the visited examples, not by its name.
    # A URL ending in an action (/admin/products/new) is a form for one kind of
    # record. Only its IDs may vary, so forms for different records stay apart.
    ends_in_action = len(segments) - 1 in actions
    for index in range(1, len(segments)):
        if index in actions or (ends_in_action and not _value_like(segments[index])):
            continue
        template = segments.copy()
        template[index] = "{value}"
        keys.append(f"{base}/{'/'.join(template)}")
    # Routes such as /{slug}/p/{id} or /2024/10/23/{id}/{slug} change in more
    # than one place. Vary every ID- or slug-like segment together.
    variable = {
        index
        for index, seg in enumerate(segments)
        if _value_like(seg) and index not in actions
    }
    if (len(variable) >= 2 or 0 in variable) and (
        len(variable) < len(segments) or len(segments) >= 3
    ):
        template = [
            "{value}" if index in variable else seg
            for index, seg in enumerate(segments)
        ]
        key = f"{base}/{'/'.join(template)}"
        if key not in keys:
            keys.append(key)
    # Query routes such as ?p=123 or ?page=7 vary every ID-like value; other
    # query values stay fixed so different operations are not merged.
    query = parse_qsl(parts.query, keep_blank_values=True)
    if any(_value_like(value) for _name, value in query):
        query_template = "&".join(
            sorted(
                f"{name}={{value}}" if _value_like(value) else f"{name}={value}"
                for name, value in query
            )
        )
        keys.append(f"{base}{parts.path or '/'}?{query_template}")
    return keys


def _spread(items: list[dict], count: int) -> list[dict]:
    if count <= 0:
        return []
    if len(items) <= count:
        return items.copy()
    if count == 1:
        return [items[0]]
    indexes = {round(index * (len(items) - 1) / (count - 1)) for index in range(count)}
    return [items[index] for index in sorted(indexes)]


def _phase() -> dict:
    return {"status": "candidate", "samples": [], "observed": {}, "pending": []}


def page_similarity(first: dict | str, second: dict | str) -> float:
    """Estimate how alike two visited pages are, from 0 to 1.

    Pages are compared by their layout: the set of elements identified by tag,
    id and class names. Text, product details and repeated cards do not
    change that set much, while a different kind of page does.
    """
    if isinstance(first, str) or isinstance(second, str):
        return 1.0 if first == second else 0.0
    first_blocked = first.get("kind") == "blocked"
    second_blocked = second.get("kind") == "blocked"
    if first_blocked or second_blocked:
        return 1.0 if first_blocked and second_blocked else 0.0
    first_sketch = first.get("layout") or []
    second_sketch = second.get("layout") or []
    if not first_sketch or not second_sketch:
        # An empty page gives no evidence that two pages are alike.
        return 0.0
    first_set, second_set = set(first_sketch), set(second_sketch)
    if (
        first.get("size", len(first_set)) <= LAYOUT_SKETCH_SIZE
        and second.get("size", len(second_set)) <= LAYOUT_SKETCH_SIZE
    ):
        return len(first_set & second_set) / len(first_set | second_set)
    # Each sketch holds the smallest element hashes of its page. The smallest
    # hashes of the union estimate the share of elements both pages have.
    count = min(len(first_set), len(second_set))
    union = sorted(first_set | second_set)[:count]
    return (
        sum(1 for value in union if value in first_set and value in second_set) / count
    )


def _cluster(loaded: list[dict]) -> tuple[int, list[int], float]:
    """Find the most typical example and the examples that look like it."""
    sims = [[page_similarity(a, b) for b in loaded] for a in loaded]
    if len(loaded) == 1:
        return 0, [0], SIMILARITY_FLOOR
    averages = [
        sum(row[j] for j in range(len(row)) if j != i) / (len(row) - 1)
        for i, row in enumerate(sims)
    ]
    medoid = max(range(len(loaded)), key=lambda index: averages[index])
    others = sorted(sims[medoid][j] for j in range(len(loaded)) if j != medoid)
    middle = len(others) // 2
    typical = (
        others[middle] if len(others) % 2 else (others[middle - 1] + others[middle]) / 2
    )
    cutoff = max(SIMILARITY_FLOOR, OUTLIER_RATIO * typical)
    members = [
        index
        for index in range(len(loaded))
        if index == medoid or sims[medoid][index] >= cutoff
    ]
    return medoid, members, cutoff


class RouteSampler:
    """Keep a small browser queue while a repeated URL pattern is checked.

    Links held for a candidate are retained until its examples have been checked.
    A rejected candidate releases every held link to the ordinary queue, and
    ``drain`` releases links for any check that cannot finish.
    State is JSON so a quota pause can resume without dropping those links.
    """

    def __init__(self, snapshot: str | None = None) -> None:
        self.groups: dict[str, dict] = {}
        self.tallies: dict[str, list[str]] = {}
        self._seen: dict[str, set[str]] = {}
        self.dirty = False
        self._status_changed = False
        self._last_save = 0.0
        try:
            parsed = json.loads(snapshot or "{}")
        except (TypeError, ValueError):
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        groups = parsed.get("groups", {})
        tallies = parsed.get("tallies", {})
        if isinstance(groups, dict):
            self.groups = groups
        if isinstance(tallies, dict):
            self.tallies = tallies
        for key, group in self.groups.items():
            self._seen[key] = set(group.get("seen") or [])
            group.setdefault("features", None)
        # Links counted so far per URL shape, across every route not yet found.
        self._shape_counts: dict[str, int] = defaultdict(int)
        for key, identities in self.tallies.items():
            self._shape_counts[_key_shape(key)] += len(identities)

    # ── Persistence ──────────────────────────────────────────────────────────

    def snapshot(self) -> str:
        for key, group in self.groups.items():
            group["seen"] = sorted(self._seen.get(key, ()))
        return json.dumps(
            {"groups": self.groups, "tallies": self.tallies}, separators=(",", ":")
        )

    def take_snapshot(
        self, *, force: bool = False, now: float | None = None
    ) -> tuple[str, str] | None:
        """Return state and summaries to save, or None when a save can wait.

        Status changes save immediately. Count-only changes are saved at most
        every SAVE_INTERVAL_SECONDS, and ``force`` saves any unsaved change.
        """
        if not self.dirty:
            return None
        now = time.monotonic() if now is None else now
        if not (
            force
            or self._status_changed
            or now - self._last_save >= SAVE_INTERVAL_SECONDS
        ):
            return None
        self.dirty = False
        self._status_changed = False
        self._last_save = now
        return self.snapshot(), json.dumps(self.summaries())

    def _mark(self, status_changed: bool = False) -> None:
        self.dirty = True
        if status_changed:
            self._status_changed = True

    # ── Read-only views ──────────────────────────────────────────────────────

    def summaries(self) -> list[dict]:
        result = []
        for key, group in sorted(self.groups.items()):
            if group["status"] != "confirmed":
                continue
            examples = []
            for phase in group["phases"].values():
                if phase["status"] != "confirmed":
                    continue
                examples.extend(
                    item["url"]
                    for item in phase["samples"]
                    if phase["observed"].get(_identity(item["url"])) is not None
                )
            examples = list(dict.fromkeys(examples))
            features = group.get("features")
            kind = (
                features.get("kind")
                if isinstance(features, dict)
                else str(features or "").partition(":")[0]
            )
            label = {"product": "Product pages", "article": "Articles"}.get(
                kind, "Similar pages"
            )
            result.append(
                {
                    "route_pattern": key,
                    "label": label,
                    "links_seen": len(self._seen.get(key, ())),
                    "example_urls": examples[:MAX_UNCERTAIN_SAMPLES],
                    "pages_sampled": len(examples),
                    "examples_different": sum(
                        phase.get("different", 0)
                        for phase in group["phases"].values()
                        if phase["status"] == "confirmed"
                    ),
                }
            )
        return result

    def resume_items(self, phase_key: str) -> list[dict]:
        return [
            item
            for group in self.groups.values()
            for phase in [group["phases"].get(phase_key)]
            if phase is not None and phase["status"] == "candidate"
            for item in phase["samples"]
            if _identity(item["url"]) not in phase["observed"]
        ]

    def wants_observation(self, url: str, phase_key: str) -> bool:
        identity = _identity(url)
        return any(
            any(_identity(item["url"]) == identity for item in phase["samples"])
            and identity not in phase["observed"]
            for group in self.groups.values()
            for phase in [group["phases"].get(phase_key)]
            if phase is not None
        )

    # ── Link admission ───────────────────────────────────────────────────────

    def _assign_keys(self, unique: list[dict]) -> tuple[dict[str, str], dict]:
        buckets: dict[str, set[str]] = defaultdict(set)
        for item in unique:
            for key in _candidate_keys(item["url"]):
                buckets[key].add(_member_identity(item["url"], key))
        # Shapes of routes already found. A news site links a few articles
        # from each of many sections; once one section is a route, the others
        # with the same URL shape are checked from two links.
        known_shapes = {
            group.get("shape")
            for group in self.groups.values()
            if group["status"] != "rejected"
        }
        combined_by_key = {
            key: set(self.tallies.get(key, ())) | identities
            for key, identities in buckets.items()
            if key not in self.groups
        }
        shape_totals: dict[str, int] = defaultdict(int, self._shape_counts)
        for key, combined in combined_by_key.items():
            new = len(combined) - len(self.tallies.get(key, ()))
            shape_totals[_key_shape(key)] += new
        counts: dict[str, int] = {}
        seeds: dict[str, set[str]] = {}
        for key, identities in buckets.items():
            if key in self.groups:
                counts[key] = len(
                    self._seen[key] | {_seen_hash(identity) for identity in identities}
                )
                continue
            # Count siblings across pages: a catalogue can be reached only
            # through pages that each link to a few related products.
            known = set(self.tallies.get(key, ()))
            combined = combined_by_key[key]
            shape = _key_shape(key)
            threshold = (
                KNOWN_SHAPE_SIBLINGS
                if shape in known_shapes or shape_totals[shape] >= MIN_SIBLINGS
                else MIN_SIBLINGS
            )
            if len(combined) >= threshold:
                counts[key] = len(combined)
                seeds[key] = known
            elif key in self.tallies or len(self.tallies) < MAX_TRACKED_PATTERNS:
                if len(combined) != len(known):
                    self.tallies[key] = sorted(combined)
                    self._shape_counts[shape] += len(combined) - len(known)
                    self._mark()
        # A link can match several possible templates. Prefer the largest
        # sibling family, then the more specific pattern.
        chosen: dict[str, str] = {}
        for key in sorted(counts, key=lambda k: (-counts[k], -k.count("/"), k)):
            for item in unique:
                if _member_identity(item["url"], key) in buckets[key]:
                    chosen.setdefault(_identity(item["url"]), key)
        return chosen, seeds

    def offer(
        self, links: list[dict], phase_key: str, is_queued: IsQueued | None = None
    ) -> list[dict]:
        """Return the links admitted to the browser queue.

        ``is_queued`` reports links this account has already queued or visited.
        Those count as seen but are never chosen as examples or held, since
        the crawler would not visit them again.
        """
        is_queued = is_queued or (lambda _url: False)
        unique = list({_identity(item["url"]): item for item in links}.values())
        chosen, seeds = self._assign_keys(unique)

        admitted = []
        by_group: dict[str, list[dict]] = defaultdict(list)
        for item in unique:
            key = chosen.get(_identity(item["url"]))
            if key is None:
                admitted.append(item)
            else:
                by_group[key].append(item)

        # Larger routes first, so they lead their URL shape (see _advance).
        for key, members in sorted(by_group.items(), key=lambda kv: -len(kv[1])):
            group = self.groups.get(key)
            if group is None:
                group = self.groups[key] = {
                    "status": "candidate",
                    "features": None,
                    "shape": _key_shape(key),
                    "seen": [],
                    "phases": {},
                }
                self._seen[key] = {_seen_hash(identity) for identity in seeds[key]}
                self._shape_counts[_key_shape(key)] -= len(self.tallies.pop(key, ()))
                self._mark(status_changed=True)
            seen = self._seen[key]
            for item in members:
                digest = _seen_hash(_member_identity(item["url"], key))
                if digest not in seen:
                    seen.add(digest)
                    self._mark()
            phase = group["phases"].get(phase_key)
            if phase is None and group["status"] == "rejected":
                admitted.extend(members)
                continue
            if phase is None:
                phase = group["phases"][phase_key] = _phase()
                self._mark()
            if phase["status"] in {"rejected", "released"}:
                admitted.extend(members)
                continue
            if phase["status"] == "confirmed":
                admitted.extend(item for item in members if is_queued(item["url"]))
                continue
            already = {
                _member_identity(item["url"], key)
                for item in phase["samples"] + phase["pending"]
            }
            for item in members:
                member = _member_identity(item["url"], key)
                if is_queued(item["url"]):
                    admitted.append(item)
                elif member not in already:
                    already.add(member)
                    phase["pending"].append(item)
                    self._mark()
            admitted.extend(self._advance(group, phase, phase_key, is_queued))
        return admitted

    def observe(
        self,
        url: str,
        features: dict | None,
        phase_key: str,
        is_queued: IsQueued | None = None,
    ) -> list[dict]:
        """Record a visited example; return links to add to the queue.

        ``features`` is None when the page failed to load, or
        ``{"kind": "blocked"}`` when it needed a login this account lacked.
        """
        identity = _identity(url)
        for group in self.groups.values():
            phase = group["phases"].get(phase_key)
            if not phase:
                continue
            if not any(_identity(item["url"]) == identity for item in phase["samples"]):
                continue
            if identity in phase["observed"]:
                return []
            phase["observed"][identity] = features
            self._mark()
            return self._advance(
                group, phase, phase_key, is_queued or (lambda _url: False)
            )
        return []

    def drain(self, phase_key: str) -> list[dict]:
        """Release held links for checks that can no longer finish.

        Called when an account's queue is empty. Any example still unvisited
        was skipped by the crawler, so its held links go to the normal crawl.
        """
        released = []
        for group in self.groups.values():
            phase = group["phases"].get(phase_key)
            if not phase or phase["status"] != "candidate" or not phase["pending"]:
                continue
            released.extend(phase["pending"])
            phase["pending"] = []
            phase["status"] = "released"
            self._mark(status_changed=True)
        return released

    # ── Decisions ────────────────────────────────────────────────────────────

    def _templates(self, phase_key: str, exclude: dict) -> list[dict]:
        """Return page templates this account has confirmed on other routes."""
        return [
            phase["template"]
            for group in self.groups.values()
            if group is not exclude
            for phase in [group["phases"].get(phase_key)]
            if phase is not None
            and phase["status"] == "confirmed"
            and isinstance(phase.get("template"), dict)
            and phase["template"].get("features", {}).get("kind") != "blocked"
        ]

    def _advance(
        self, group: dict, phase: dict, phase_key: str, is_queued: IsQueued
    ) -> list[dict]:
        if phase["status"] != "candidate":
            return []
        if any(
            _identity(item["url"]) not in phase["observed"] for item in phase["samples"]
        ):
            return []
        observed = [
            phase["observed"][_identity(item["url"])] for item in phase["samples"]
        ]
        loaded = [features for features in observed if features is not None]
        failed = len(observed) - len(loaded)
        if failed > MAX_FAILED_SAMPLES:
            return self._reject(group, phase, phase_key, is_queued)
        blocked = sum(
            1
            for features in loaded
            if isinstance(features, dict) and features.get("kind") == "blocked"
        )
        if 0 < blocked < len(loaded):
            # Some pages need a login and others do not: an access difference
            # that sampling could miss, so every link is crawled.
            return self._reject(group, phase, phase_key, is_queued)
        templates = self._templates(phase_key, group)
        # The same template often serves many routes, such as articles in
        # every news section. One matching example is enough for those.
        for template in templates:
            if loaded and all(
                page_similarity(template["features"], features) >= template["cutoff"]
                for features in loaded
            ):
                return self._confirm(
                    group,
                    phase,
                    phase_key,
                    is_queued,
                    template["features"],
                    template["cutoff"],
                    0,
                )
        # Each account compares its own examples. Accounts may legitimately
        # see different pages (a signed-in user gets a review form), and that
        # access difference is what visiting the same example URLs records.
        confirmed_elsewhere = group["status"] == "confirmed"
        target = INITIAL_SAMPLES if confirmed_elsewhere else CONFIRM_SAMPLES
        # Links queued since they were held will be visited anyway.
        phase["pending"] = [
            item for item in phase["pending"] if not is_queued(item["url"])
        ]
        if not phase["pending"]:
            # Every link of this route has been visited, so confirming it
            # skips nothing. It still gives sibling routes a template to match.
            target = INITIAL_SAMPLES
        if len(loaded) >= INITIAL_SAMPLES:
            medoid, members, cutoff = _cluster(loaded)
            if len(members) < 2:
                # No two examples look alike: these are different pages.
                return self._reject(group, phase, phase_key, is_queued)
            if len(loaded) >= target and len(members) >= DOMINANT_SHARE * len(loaded):
                return self._confirm(
                    group,
                    phase,
                    phase_key,
                    is_queued,
                    loaded[medoid],
                    cutoff,
                    len(loaded) - len(members),
                )
        room = MAX_UNCERTAIN_SAMPLES - len(phase["samples"])
        if room <= 0:
            return self._reject(group, phase, phase_key, is_queued)
        if (
            not phase["samples"]
            and not templates
            and self._lead_in_progress(group, phase_key)
        ):
            # Another route with this URL shape is being checked. Wait for it:
            # if it is confirmed, one example will be enough here.
            return []
        if not phase["samples"] and templates:
            # Try one page first: it may match a template already confirmed.
            wanted = 1
        elif len(loaded) < INITIAL_SAMPLES:
            wanted = INITIAL_SAMPLES - len(loaded)
        else:
            # Some examples differed: look at more before deciding.
            wanted = max(target - len(loaded), 2)
        selected = self._pick(group, phase["pending"], min(wanted, room))
        if not selected:
            # Wait for more links; drain() releases this check if none arrive.
            return []
        picked = {id(item) for item in selected}
        phase["samples"].extend(selected)
        phase["pending"] = [item for item in phase["pending"] if id(item) not in picked]
        self._mark()
        return selected

    def _confirm(
        self,
        group: dict,
        phase: dict,
        phase_key: str,
        is_queued: IsQueued,
        template: dict,
        cutoff: float,
        different: int,
    ) -> list[dict]:
        phase["status"] = "confirmed"
        phase["pending"] = []
        phase["template"] = {"features": template, "cutoff": cutoff}
        phase["different"] = different
        # Keep only the typical page's layout; the others are no longer needed.
        phase["observed"] = {
            identity: (
                {"kind": features.get("kind")}
                if isinstance(features, dict)
                else features
            )
            for identity, features in phase["observed"].items()
        }
        if group["status"] != "confirmed":
            group["status"] = "confirmed"
            group["features"] = {"kind": template.get("kind")}
        self._mark(status_changed=True)
        return self._wake_siblings(group, phase_key, is_queued)

    def _pick(self, group: dict, pending: list[dict], count: int) -> list[dict]:
        # Reuse another account's example URLs so access can be compared.
        preferred = {
            _identity(item["url"])
            for phase in group["phases"].values()
            if phase["status"] == "confirmed"
            for item in phase["samples"]
        }
        selected = [item for item in pending if _identity(item["url"]) in preferred]
        selected = selected[:count]
        rest = [item for item in pending if item not in selected]
        selected.extend(_spread(rest, count - len(selected)))
        return selected

    def _reject(
        self, group: dict, phase: dict, phase_key: str, is_queued: IsQueued
    ) -> list[dict]:
        phase["status"] = "rejected"
        if group["status"] != "confirmed":
            group["status"] = "rejected"
        released = phase["pending"]
        phase["pending"] = []
        self._mark(status_changed=True)
        return released + self._wake_siblings(group, phase_key, is_queued)

    def _lead_in_progress(self, group: dict, phase_key: str) -> bool:
        return any(
            other is not group
            and other.get("shape") == group.get("shape")
            and phase is not None
            and phase["status"] == "candidate"
            and phase["samples"]
            for other in self.groups.values()
            for phase in [other["phases"].get(phase_key)]
        )

    def _wake_siblings(
        self, group: dict, phase_key: str, is_queued: IsQueued
    ) -> list[dict]:
        """Start checks that waited for this route's decision."""
        woken = []
        for other in list(self.groups.values()):
            if other is group or other.get("shape") != group.get("shape"):
                continue
            phase = other["phases"].get(phase_key)
            if (
                phase is not None
                and phase["status"] == "candidate"
                and not phase["samples"]
                and phase["pending"]
            ):
                woken.extend(self._advance(other, phase, phase_key, is_queued))
        return woken


_LAYOUT_SCRIPT = (
    """() => {
  const norm = text => String(text).replace(/[0-9a-f]{8,}/gi, '{h}').replace(/\\d+/g, '{n}');
  const fnv = text => {
    let hash = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 0x01000193);
    }
    return hash >>> 0;
  };
  const token = (el, withParent) => {
    const classes = Array.from(el.classList).map(norm).filter(c => c.length < 40).sort().slice(0, 3).join('.');
    const id = el.id ? '#' + norm(el.id) : '';
    if (!withParent && !classes && !id) return null;
    const parent = withParent && el.parentElement ? el.parentElement.tagName + '>' : '';
    return parent + el.tagName + id + '.' + classes;
  };
  const collect = withParent => {
    const tokens = new Set();
    for (const el of document.querySelectorAll('body *')) {
      const value = token(el, withParent);
      if (value) tokens.add(fnv(value));
      if (tokens.size >= 20000) break;
    }
    return tokens;
  };
  let tokens = collect(false);
  // Pages with little class markup are compared by element nesting instead.
  if (tokens.size < 30) tokens = collect(true);
  const types = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
    .map(el => el.textContent || '').join(' ');
  const ogType = (document.querySelector('meta[property="og:type"]')?.content || '').toLowerCase();
  const product = !!document.querySelector('[itemtype*="schema.org/Product" i]')
    || /"@type"\\s*:\\s*"Product"/i.test(types) || ogType.includes('product');
  const article = !!document.querySelector('[itemtype*="Article" i]')
    || /"@type"\\s*:\\s*"(News|Blog)?(Article|Posting)"/i.test(types) || ogType === 'article';
  return {
    kind: product ? 'product' : (article ? 'article' : 'page'),
    layout: Array.from(tokens).sort((a, b) => a - b).slice(0, %d),
    size: tokens.size,
  };
}"""
    % LAYOUT_SKETCH_SIZE
)


async def page_features(page, api_calls: list[dict] | None = None) -> dict | None:
    """Describe a page's layout so pages from one template can be recognised.

    Text, prices, product options and the number of repeated cards change from
    page to page; the set of element types and class names mostly does not.
    ``api_calls`` is accepted for compatibility and not used.
    """
    try:
        surface = await page.evaluate(_LAYOUT_SCRIPT)
    except Exception:
        return None
    if not isinstance(surface, dict):
        return None
    layout = [value for value in surface.get("layout") or [] if isinstance(value, int)][
        :LAYOUT_SKETCH_SIZE
    ]
    kind = surface.get("kind")
    return {
        "kind": kind if kind in {"product", "article", "page"} else "page",
        "layout": layout,
        "size": int(surface.get("size") or len(layout)),
    }
