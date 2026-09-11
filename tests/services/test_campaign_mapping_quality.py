"""Regression tests for campaign path identity and target ownership."""

from __future__ import annotations

from dataclasses import dataclass

from aespa.services.campaign_mapping_quality import (
    canonical_path_identity,
    canonical_static_path_key,
    choose_canonical_trace_paths,
    complete_path_can_map_to_site,
    path_component_ids,
)


def _path(*, component_id: int, handler: str | None = None, status: str = "complete"):
    facts = [
        {
            "fact_id": 100,
            "component_id": component_id,
            "component_name": "FACE",
            "kind": "ui_action",
            "detail": {"action_kind": "form_submit"},
        },
        {
            "fact_id": 101,
            "component_id": component_id,
            "component_name": "FACE",
            "kind": "http_call",
            "request_role": "browser_request",
            "method": "POST",
            "path": "/api/payment/process?cache=false",
        },
    ]
    if handler:
        facts.append(
            {
                "fact_id": 102,
                "component_id": component_id,
                "component_name": "FACE",
                "kind": "handler",
                "name": handler,
            }
        )
    facts.append(
        {
            "fact_id": 103,
            "component_id": component_id,
            "component_name": "FACE",
            "kind": "lead_anchor",
        }
    )
    return {
        "path_status": status,
        "static_trace": {"facts": facts},
    }


def test_equivalent_paths_ignore_fact_ids_and_query_strings():
    left = _path(component_id=8, handler="processPayment")
    right = _path(component_id=8, handler="processPayment")
    for index, fact in enumerate(right["static_trace"]["facts"], start=900):
        fact["fact_id"] = index
    right["static_trace"]["facts"][1]["path"] = "/api/payment/process/"

    assert canonical_static_path_key(left) == canonical_static_path_key(right)
    assert canonical_path_identity(42, left) == canonical_path_identity(42, right)


def test_single_component_complete_path_cannot_map_to_other_site():
    path = _path(component_id=8)

    assert path_component_ids(path) == frozenset({8})
    assert complete_path_can_map_to_site(path, 8) is True
    assert complete_path_can_map_to_site(path, 9) is False
    assert complete_path_can_map_to_site(path, None) is False


def test_incomplete_path_remains_reviewable_without_ownership_match():
    path = _path(component_id=8, status="incomplete")

    assert complete_path_can_map_to_site(path, 9) is True


@dataclass(frozen=True)
class _Fact:
    fact_type: str
    component_id: int
    method: str = ""
    path: str = ""
    name: str = ""


@dataclass(frozen=True)
class _Trace:
    facts: tuple[_Fact, ...]
    complete: bool
    confidence: float
    proof_gaps: tuple[str, ...] = ()
    key: str = ""


def test_canonical_trace_selection_prefers_handler_path():
    browser = _Fact("http_call", 8, "POST", "/api/payment/process")
    anchor = _Fact("lead_anchor", 8)
    without_handler = _Trace((browser, anchor), True, 0.95, key="short")
    with_handler = _Trace(
        (
            _Fact("handler", 8, name="processPayment"),
            browser,
            anchor,
        ),
        True,
        0.80,
        key="handler",
    )

    selected = choose_canonical_trace_paths([without_handler, with_handler])

    assert selected == [with_handler]


def test_canonical_prefilter_keeps_distinct_handler_entrypoints():
    browser = _Fact("http_call", 8, "POST", "/api/payment/process")
    anchor = _Fact("lead_anchor", 8)
    direct = _Trace(
        (_Fact("ui_action", 8, name="Direct pay"), browser, anchor),
        True,
        0.99,
        key="direct",
    )
    first_handler = _Trace(
        (
            _Fact("ui_action", 8, name="Pay with card"),
            _Fact("handler", 8, name="payByCard"),
            browser,
            anchor,
        ),
        True,
        0.80,
        key="card",
    )
    second_handler = _Trace(
        (
            _Fact("ui_action", 8, name="Pay with bank"),
            _Fact("handler", 8, name="payByBank"),
            browser,
            anchor,
        ),
        True,
        0.75,
        key="bank",
    )

    selected = choose_canonical_trace_paths([direct, first_handler, second_handler])

    assert selected == [first_handler, second_handler]


def test_canonical_selection_prefers_anchor_matching_preceding_route():
    route = _Fact("route", 8, "POST", "/api/quotes/motor")
    handler = _Fact("handler", 8, name="submitMotorQuote")
    action = _Fact("ui_action", 8, name="Get motor quote")
    request = _Fact("http_call", 8, "POST", "/api/quotes/motor")
    mismatched_anchor = _Fact("lead_anchor", 8, "POST", "/api/policy/bind")
    matching_anchor = _Fact("lead_anchor", 8, "POST", "/api/quotes/motor")
    wrong_anchor_path = _Trace(
        (action, handler, request, route, mismatched_anchor), True, 0.95, key="bind"
    )
    right_anchor_path = _Trace(
        (action, handler, request, route, matching_anchor), True, 0.80, key="quote"
    )

    selected = choose_canonical_trace_paths([wrong_anchor_path, right_anchor_path])

    assert selected == [right_anchor_path]
    assert choose_canonical_trace_paths([wrong_anchor_path]) == [wrong_anchor_path]
