"""Conservative, opt-in admission of repeated URL pages to a web crawl."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from typing import Callable
from urllib.parse import parse_qsl, urlsplit, urlunsplit

MIN_SIBLINGS = 10
INITIAL_SAMPLES = 3
CONFIRM_SAMPLES = 5
MAX_UNCERTAIN_SAMPLES = 12
# Pages that fail to load are replaced by other examples, up to this many.
MAX_FAILED_SAMPLES = 2
# Patterns still below MIN_SIBLINGS are counted across pages. Cap the number
# tracked so a site with many unrelated URL shapes cannot grow this forever.
MAX_TRACKED_PATTERNS = 2_000
SAVE_INTERVAL_SECONDS = 5.0
REQUEST_OVERLAP = 0.8
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


def _identity(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            parts.query,
            parts.fragment,
        )
    )


def _seen_hash(identity: str) -> str:
    return hashlib.sha256(identity.encode()).hexdigest()[:12]


def _candidate_keys(url: str) -> list[tuple[str, str]]:
    parts = urlsplit(url)
    segments = [segment for segment in parts.path.split("/") if segment]
    if parts.fragment:
        return []
    if any(segment.lower() in _ACTION_SEGMENTS for segment in segments):
        return []
    keys = []
    for index in range(1, len(segments)):
        if segments[index].lower() in _ACTION_SEGMENTS:
            continue
        template = segments.copy()
        template[index] = "{value}"
        pattern = (
            f"{parts.scheme.lower()}://{parts.netloc.lower()}/{'/'.join(template)}"
        )
        # Query names may describe different operations. Do not merge them.
        query_names = tuple(
            sorted(part.partition("=")[0] for part in parts.query.split("&") if part)
        )
        key = pattern + ("?" + "&".join(query_names) if query_names else "")
        keys.append((key, segments[index]))
    query = parse_qsl(parts.query, keep_blank_values=True)
    for name, value in query:
        if name.lower() not in {"id", "item", "product", "product_id", "sku", "slug"}:
            continue
        rest = sorted((key, val) for key, val in query if key != name)
        suffix = "&".join([f"{key}={val}" for key, val in rest] + [f"{name}={{value}}"])
        keys.append(
            (
                f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path}?{suffix}",
                value,
            )
        )
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


def features_match(first: dict | str, second: dict | str) -> bool:
    """Return whether two visited examples look like the same kind of page."""
    if isinstance(first, str) or isinstance(second, str):
        return first == second
    if first.get("kind") != second.get("kind"):
        return False
    if first.get("kind") == "blocked":
        return True
    for field in ("forms", "actions", "text"):
        if first.get(field) != second.get(field):
            return False
    first_requests = set(first.get("requests") or [])
    second_requests = set(second.get("requests") or [])
    if not first_requests and not second_requests:
        return True
    overlap = len(first_requests & second_requests) / len(
        first_requests | second_requests
    )
    return overlap >= REQUEST_OVERLAP


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
            result.append(
                {
                    "route_pattern": key,
                    "label": "Product pages" if kind == "product" else "Similar pages",
                    "links_seen": len(self._seen.get(key, ())),
                    "example_urls": examples[:MAX_UNCERTAIN_SAMPLES],
                    "pages_sampled": len(examples),
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
            for key, _value in _candidate_keys(item["url"]):
                buckets[key].add(_identity(item["url"]))
        counts: dict[str, int] = {}
        seeds: dict[str, set[str]] = {}
        for key, identities in buckets.items():
            if key in self.groups:
                counts[key] = len(self._seen[key] | identities)
                continue
            # Count siblings across pages: a catalogue can be reached only
            # through pages that each link to a few related products.
            known = set(self.tallies.get(key, ()))
            combined = known | identities
            if len(combined) >= MIN_SIBLINGS:
                counts[key] = len(combined)
                seeds[key] = known
            elif key in self.tallies or len(self.tallies) < MAX_TRACKED_PATTERNS:
                if len(combined) != len(known):
                    self.tallies[key] = sorted(combined)
                    self._mark()
        # A link can match several possible templates. Prefer the largest
        # sibling family, then the more specific pattern.
        chosen: dict[str, str] = {}
        for key in sorted(counts, key=lambda k: (-counts[k], -k.count("/"), k)):
            for identity in buckets[key]:
                chosen.setdefault(identity, key)
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

        for key, members in by_group.items():
            group = self.groups.get(key)
            if group is None:
                group = self.groups[key] = {
                    "status": "candidate",
                    "features": None,
                    "seen": [],
                    "phases": {},
                }
                self._seen[key] = {_seen_hash(identity) for identity in seeds[key]}
                self.tallies.pop(key, None)
                self._mark(status_changed=True)
            seen = self._seen[key]
            for item in members:
                digest = _seen_hash(_identity(item["url"]))
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
                _identity(item["url"]) for item in phase["samples"] + phase["pending"]
            }
            for item in members:
                if is_queued(item["url"]):
                    admitted.append(item)
                elif _identity(item["url"]) not in already:
                    phase["pending"].append(item)
                    self._mark()
            admitted.extend(self._advance(group, phase, is_queued))
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
            return self._advance(group, phase, is_queued or (lambda _url: False))
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

    def _advance(self, group: dict, phase: dict, is_queued: IsQueued) -> list[dict]:
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
        # Another account already confirmed this route: check that this
        # account sees the same kind of page on the same example URLs.
        confirmed_elsewhere = group["status"] == "confirmed"
        reference = group["features"] if confirmed_elsewhere else None
        if reference is None and loaded:
            reference = loaded[0]
        if any(not features_match(reference, features) for features in loaded):
            return self._reject(group, phase)
        if failed > MAX_FAILED_SAMPLES:
            return self._reject(group, phase)
        target = INITIAL_SAMPLES if confirmed_elsewhere else CONFIRM_SAMPLES
        if len(loaded) >= target:
            phase["status"] = "confirmed"
            phase["pending"] = []
            if not confirmed_elsewhere:
                group["status"] = "confirmed"
                group["features"] = loaded[0]
            self._mark(status_changed=True)
            return []
        room = MAX_UNCERTAIN_SAMPLES - len(phase["samples"])
        if room <= 0:
            return self._reject(group, phase)
        wanted = target - len(loaded)
        if not phase["samples"] and not confirmed_elsewhere:
            # Visit three first so a mismatch costs as few pages as possible.
            wanted = INITIAL_SAMPLES
        # Links queued since they were held will be visited anyway.
        phase["pending"] = [
            item for item in phase["pending"] if not is_queued(item["url"])
        ]
        selected = self._pick(group, phase["pending"], min(wanted, room))
        if not selected:
            # Wait for more links; drain() releases this check if none arrive.
            return []
        picked = {id(item) for item in selected}
        phase["samples"].extend(selected)
        phase["pending"] = [item for item in phase["pending"] if id(item) not in picked]
        self._mark()
        return selected

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

    def _reject(self, group: dict, phase: dict) -> list[dict]:
        phase["status"] = "rejected"
        if group["status"] != "confirmed":
            group["status"] = "rejected"
        released = phase["pending"]
        phase["pending"] = []
        self._mark(status_changed=True)
        return released


_ACTION_WORDS = re.compile(
    r"^(add|buy|order|wishlist|save|review|submit|share|subscribe|pay|checkout|"
    r"delete|edit|remove|apply|notify|book|reserve|compare|follow|download|"
    r"sign in|log in|register)\b"
)


async def page_features(page, api_calls: list[dict] | None = None) -> dict | None:
    """Describe a page's controls and request shapes, ignoring product text.

    Only action controls are kept, so buttons that differ between products,
    such as sizes or colours, do not make two product pages look different.
    """
    try:
        surface = await page.evaluate(
            """() => {
              const clean = text => (text || '').replace(/\\s+/g, ' ').trim().toLowerCase();
              const controls = Array.from(document.querySelectorAll('button,[role="button"],input[type="submit"]'))
                .map(el => clean(el.getAttribute('aria-label') || el.value || el.textContent))
                .filter(Boolean).slice(0, 200);
              const links = Array.from(document.querySelectorAll('main a[href],article a[href]'))
                .map(el => clean(el.textContent)).filter(Boolean).slice(0, 200);
              const forms = Array.from(document.forms).map(form => ({
                method: form.method.toUpperCase(),
                fields: Array.from(form.querySelectorAll('input,select,textarea'))
                  .map(el => `${el.tagName.toLowerCase()}:${el.getAttribute('name') || ''}:${el.getAttribute('type') || ''}`)
                  .sort()
              })).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
              const product = !!document.querySelector('[itemtype*="schema.org/Product"], [itemtype*="schema.org/product"]')
                || Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
                  .some(el => /schema.org\\/Product|"@type"\\s*:\\s*"Product"/i.test(el.textContent || ''))
                || controls.some(text => /add to (cart|basket|bag)/.test(text));
              const heading = clean(document.querySelector('main h1, article h1, h1')?.textContent);
              const mainText = clean(document.querySelector('main, article')?.textContent).slice(0, 600);
              return {controls, links, forms, product, heading, mainText};
            }"""
        )
    except Exception:
        return None
    if not isinstance(surface, dict):
        return None
    actions = sorted(
        {
            " ".join(text.split()[:3])
            for text in [
                *(surface.get("controls") or []),
                *(surface.get("links") or []),
            ]
            if isinstance(text, str) and _ACTION_WORDS.match(text)
        }
    )
    requests = set()
    for call in api_calls or []:
        parts = urlsplit(str(call.get("url") or ""))
        segments = [
            "{value}"
            if segment.isdigit() or re.fullmatch(r"[0-9a-f-]{16,}", segment, re.I)
            else segment
            for segment in parts.path.split("/")
            if segment
        ]
        if len(segments) >= 2 and segments[-1].lower() not in _ACTION_SEGMENTS:
            segments[-1] = "{value}"
        requests.add(f"{call.get('method', 'GET')} /{'/'.join(segments)}")
    kind = "product" if surface.get("product") else "page"
    text = None
    if kind == "page":
        # Without product evidence, pages must also share their heading and
        # opening text, so ten different features are not merged into one.
        heading = surface.get("heading") or ""
        main_text = surface.get("mainText") or ""
        text = hashlib.sha256(
            json.dumps([heading, main_text] if heading else [page.url]).encode()
        ).hexdigest()[:20]
    return {
        "kind": kind,
        "forms": surface.get("forms") or [],
        "actions": actions,
        "requests": sorted(requests)[:60],
        "text": text,
    }
