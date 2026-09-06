"""Stable identity and ownership checks for campaign-derived paths.

The path graph contains database ids and source line numbers.  Those values
are useful evidence, but they are poor identity keys: a mapper retry can
produce an equivalent path with different fact ids or nearby line locations.
This module keeps the identity and target-safety rules in one place so lead
generation and mapping code use the same rules.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping


def _text(value: object) -> str:
    return str(value or "").strip()


def _normalise_method(value: object) -> str:
    return _text(value).upper()


def _normalise_path(value: object) -> str:
    path = _text(value)
    if not path:
        return ""
    # Query strings are request detail, rather than endpoint identity.  Keep
    # route templates and parameter names intact so /orders/{id} remains
    # distinct from /orders/{order_id} when the source says they differ.
    return path.split("?", 1)[0].rstrip("/") or "/"


def _decode(value: object) -> object:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        return {}
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return decoded


def _fact_signature(fact: Mapping[str, object]) -> tuple[str, ...]:
    """Return identity fields for one serialized ComponentFact node."""
    detail = _decode(fact.get("detail"))
    if not isinstance(detail, Mapping):
        detail = {}
    handler = detail.get("handler")
    if isinstance(handler, Mapping):
        handler = (
            handler.get("name") or handler.get("function") or handler.get("method")
        )
    return (
        _text(fact.get("component_name") or fact.get("component_id")).casefold(),
        _text(fact.get("kind")).casefold(),
        _text(fact.get("request_role")).casefold(),
        _normalise_method(fact.get("method")),
        _normalise_path(fact.get("path")),
        _text(fact.get("name")).casefold(),
        _text(handler).casefold(),
        _text(detail.get("action_kind") or detail.get("trigger")).casefold(),
    )


def serialized_path_facts(
    attack_path: Mapping[str, object],
) -> list[Mapping[str, object]]:
    """Extract ordered fact nodes from a schema-v3 or legacy path."""
    static_trace = attack_path.get("static_trace")
    if isinstance(static_trace, Mapping):
        facts = static_trace.get("facts")
        if isinstance(facts, list):
            return [fact for fact in facts if isinstance(fact, Mapping)]

    # Older paths store the same nodes in service_hops and a separate frontend
    # surface.  Preserve their semantic order for stable identity.
    surface = attack_path.get("frontend_surface")
    result: list[Mapping[str, object]] = []
    if isinstance(surface, Mapping):
        for key in ("ui_route", "ui_action", "browser_request"):
            value = surface.get(key)
            if isinstance(value, Mapping):
                result.append(value)
    hops = attack_path.get("service_hops")
    if isinstance(hops, list):
        result.extend(value for value in hops if isinstance(value, Mapping))
    return result


def canonical_static_path_key(attack_path: Mapping[str, object]) -> str:
    """Return a run-independent key for an equivalent static path.

    Fact ids, connection ids, and source line numbers are deliberately
    excluded.  The source finding id remains the caller's namespace, so this
    key is safe to combine with ``origin_lead_id``.
    """
    facts = serialized_path_facts(attack_path)
    material = json.dumps(
        [
            _fact_signature(fact)
            for fact in facts
            if fact.get("kind") not in {"lead_anchor", "handler"}
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def canonical_path_identity(
    origin_lead_id: int | None, attack_path: Mapping[str, object]
) -> str:
    """Combine the origin finding and semantic path into a stable identity."""
    return f"{origin_lead_id or ''}:{canonical_static_path_key(attack_path)}"


def path_component_ids(attack_path: Mapping[str, object]) -> frozenset[int]:
    """Return component ids explicitly evidenced by a serialized path."""
    values: set[int] = set()
    for fact in serialized_path_facts(attack_path):
        value = fact.get("component_id")
        try:
            if value is not None:
                values.add(int(value))
        except (TypeError, ValueError):
            continue
    return frozenset(values)


def single_component_path_matches_target(
    attack_path: Mapping[str, object], target_component_id: int | None
) -> bool:
    """Whether a path's single evidenced component owns the selected target.

    A complete path with one component must never be proposed to a different
    site's component.  Returning false for an unknown target also keeps an
    unowned site review-gated instead of guessing from host similarity.
    """
    component_ids = path_component_ids(attack_path)
    if len(component_ids) != 1 or target_component_id is None:
        return False
    try:
        return next(iter(component_ids)) == int(target_component_id)
    except (TypeError, ValueError):
        return False


def complete_path_can_map_to_site(
    attack_path: Mapping[str, object], target_component_id: int | None
) -> bool:
    """Apply the wrong-target guard to a complete frontend path."""
    if _text(attack_path.get("path_status")).casefold() != "complete":
        return True
    component_ids = path_component_ids(attack_path)
    if len(component_ids) == 1:
        return single_component_path_matches_target(attack_path, target_component_id)
    return True


def choose_canonical_trace_paths(paths: Iterable[object]) -> list[object]:
    """Keep the strongest representative of each semantic trace variant.

    This helper accepts ``TracePath`` instances without importing
    ``route_tracing``.  It is also useful to callers that already converted a
    path to JSON and need to select among equivalent mapper variants.
    """
    selected: dict[str, object] = {}
    candidates = list(paths)

    def anchor_matches_preceding_route(path: object) -> bool:
        facts = getattr(path, "facts", ()) or ()
        for index, anchor in enumerate(facts):
            if getattr(anchor, "fact_type", "") != "lead_anchor" or index == 0:
                continue
            route = facts[index - 1]
            if getattr(route, "fact_type", "") != "route":
                continue
            anchor_method = _text(getattr(anchor, "method", ""))
            route_method = _text(getattr(route, "method", ""))
            anchor_path = _normalise_path(getattr(anchor, "path", ""))
            route_path = _normalise_path(getattr(route, "path", ""))
            if (
                anchor_method
                and route_method
                and anchor_method.upper() == route_method.upper()
                and anchor_path
                and route_path
                and anchor_path == route_path
            ):
                return True
        return False

    def rank(path: object) -> tuple[object, ...]:
        facts = getattr(path, "facts", ()) or ()
        kinds = {getattr(fact, "fact_type", "") for fact in facts}
        has_handler = "handler" in kinds
        gaps = getattr(path, "proof_gaps", ()) or ()
        return (
            not bool(getattr(path, "complete", False)),
            not has_handler,
            not anchor_matches_preceding_route(path),
            -float(getattr(path, "confidence", 0.0) or 0.0),
            len(gaps),
            -len(facts),
            str(getattr(path, "key", "")),
        )

    def core_signature(path: object) -> str:
        """Identify the request/service/anchor chain without UI wrappers."""
        facts = getattr(path, "facts", ()) or ()
        return json.dumps(
            [
                (
                    _text(getattr(fact, "component_id", "")).casefold(),
                    _text(getattr(fact, "fact_type", "")).casefold(),
                    _text(getattr(fact, "method", "")).upper(),
                    _normalise_path(getattr(fact, "path", "")),
                    _text(getattr(fact, "name", "")).casefold(),
                )
                for fact in facts
                if getattr(fact, "fact_type", "")
                not in {"ui_route", "ui_action", "handler", "lead_anchor"}
            ],
            separators=(",", ":"),
        )

    by_core: dict[str, list[object]] = {}
    for path in candidates:
        by_core.setdefault(core_signature(path), []).append(path)

    # A direct action-to-request edge is a useful fallback, but it is weaker
    # than a path that names the handler which owns the same request.  Apply
    # that preference only when the handler-backed path is complete.  Distinct
    # handler-backed paths stay independent because separate forms can invoke
    # the same request through different handlers.
    filtered: list[object] = []
    for group in by_core.values():
        complete_with_handler = any(
            bool(getattr(path, "complete", False))
            and any(
                getattr(fact, "fact_type", "") == "handler"
                for fact in (getattr(path, "facts", ()) or ())
            )
            for path in group
        )
        if complete_with_handler:
            group = [
                path
                for path in group
                if any(
                    getattr(fact, "fact_type", "") == "handler"
                    for fact in (getattr(path, "facts", ()) or ())
                )
            ]
        filtered.extend(group)

    for path in filtered:
        facts = getattr(path, "facts", ()) or ()
        handlers = tuple(
            (
                _text(getattr(fact, "component_id", "")).casefold(),
                _text(getattr(fact, "name", "")).casefold()
                or _text(getattr(fact, "evidence_location", "")).casefold(),
            )
            for fact in facts
            if getattr(fact, "fact_type", "") == "handler"
        )
        ui_context = tuple(
            (
                _text(getattr(fact, "fact_type", "")).casefold(),
                _normalise_path(getattr(fact, "path", "")),
                _text(getattr(fact, "name", "")).casefold(),
            )
            for fact in facts
            if getattr(fact, "fact_type", "") in {"ui_route", "ui_action"}
        )
        signature = json.dumps(
            (core_signature(path), handlers, ui_context if handlers else ()),
            separators=(",", ":"),
        )
        current = selected.get(signature)
        if current is None or rank(path) < rank(current):
            selected[signature] = path
    return list(selected.values())
