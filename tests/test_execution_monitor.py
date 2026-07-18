from __future__ import annotations

from aespa.services.execution_monitor import (
    ExecutionMonitor,
    InterventionState,
    StrategyVector,
    add_strategy_justification_to_tools,
    normalize_tool_signature,
    normalize_url,
)


def _vector() -> StrategyVector:
    return StrategyVector(
        id="transfer-idor",
        title="Test transfer ownership",
        tool_names=["http_request"],
        route_patterns=["/api/transfers/{id}"],
        owasp_categories=["API1"],
        test_classes=["idor"],
        parameter_names=["account_id"],
    )


def test_normalize_url_strips_noise_but_preserves_route_and_value_order():
    left = "http://EXAMPLE.com/api/users?a=1&a=2&b=3&_=123"
    equivalent = "http://example.com/api/users?b=3&a=1&a=2&ts=999"
    reversed_values = "http://example.com/api/users?b=3&a=2&a=1"
    trailing_slash = "http://example.com/api/users/?b=3&a=1&a=2"

    assert normalize_url(left) == normalize_url(equivalent)
    assert normalize_url(left) != normalize_url(reversed_values)
    assert normalize_url(left) != normalize_url(trailing_slash)


def test_signature_normalizes_json_and_headers_but_keeps_semantic_headers():
    first = {
        "url": "http://example.com/login?ts=123",
        "method": "post",
        "headers": {"Authorization": "Bearer one", "X-Request-ID": "a"},
        "body": '{"username":"admin", "pass":"123"}\n',
    }
    equivalent = {
        "url": "http://example.com/login?_=999",
        "method": "POST",
        "headers": {"authorization": "Bearer one", "x-request-id": "b"},
        "body": {"pass": "123", "username": "admin"},
    }
    different_auth = {**equivalent, "headers": {"Authorization": "Bearer two"}}

    assert normalize_tool_signature("http_request", first) == normalize_tool_signature(
        "http_request", equivalent
    )
    assert normalize_tool_signature("http_request", first) != normalize_tool_signature(
        "http_request", different_auth
    )


def test_browser_signature_includes_current_spa_page_state():
    action = {"steps": [{"op": "dom_check", "selector": "body"}]}

    customer_20 = normalize_tool_signature(
        "browser", action, browser_page_url="http://example.com/admin/#/customers/20"
    )
    customer_21 = normalize_tool_signature(
        "browser", action, browser_page_url="http://example.com/admin/#/customers/21"
    )
    repeated_21 = normalize_tool_signature(
        "browser", action, browser_page_url="http://example.com/admin/#/customers/21"
    )

    assert customer_20 != customer_21
    assert customer_21 == repeated_21


def test_browser_duplicate_details_and_result_comparison_are_explicit():
    monitor = ExecutionMonitor()
    action = {"steps": [{"op": "dom_check", "selector": "body"}]}
    page = "http://example.com/admin/#/customers/21"

    assert (
        monitor.observe_tool_call("browser", action, 31, browser_page_url=page)[0]
        == InterventionState.NORMAL
    )
    assert monitor.observe_executed_result("browser", "same page", 31) is None

    state, reason = monitor.observe_tool_call(
        "browser", action, 32, browser_page_url=page
    )
    assert state == InterventionState.INVOKE_MENTOR_DUPLICATE
    assert "previous step 31, current step 32" in (reason or "")
    assert monitor.last_intervention_details["current_page_url"] == page

    comparison = monitor.observe_executed_result("browser", "same page", 32)
    assert comparison is not None
    assert comparison["result_changed"] is False


def test_duplicate_escalation_and_bounded_hard_block_termination():
    monitor = ExecutionMonitor(max_hard_block_rejections=3)
    tool_input = {"url": "http://example.com/test", "method": "GET"}

    assert (
        monitor.observe_tool_call("http_request", tool_input, 1)[0]
        == InterventionState.NORMAL
    )
    assert (
        monitor.observe_tool_call("http_request", tool_input, 2)[0]
        == InterventionState.INVOKE_MENTOR_DUPLICATE
    )
    assert (
        monitor.observe_tool_call("http_request", tool_input, 3)[0]
        == InterventionState.HARD_BLOCK_DUPLICATE
    )
    assert (
        monitor.observe_tool_call("http_request", tool_input, 4)[0]
        == InterventionState.HARD_BLOCK_DUPLICATE
    )
    assert (
        monitor.observe_tool_call("http_request", tool_input, 5)[0]
        == InterventionState.HARD_BLOCK_DUPLICATE
    )
    assert "hard-blocked duplicate" in (monitor.check_termination() or "")


def test_stagnation_is_driven_by_completed_nonprogress_steps():
    monitor = ExecutionMonitor(stagnation_mentor_threshold=3)
    for _ in range(3):
        monitor.finish_step(progress_made=False, executed=True)

    state, _ = monitor.observe_tool_call(
        "http_request", {"url": "http://example.com/a"}, 4
    )
    assert state == InterventionState.INVOKE_MENTOR_STAGNATION

    monitor.finish_step(progress_made=True, executed=True)
    assert monitor.nonprogress_steps == 0
    assert monitor.stagnation_mentor_emitted is False


def test_contract_blocks_until_a_structured_vector_executes():
    monitor = ExecutionMonitor()
    monitor.set_strategy_contract(4, "Stalled", [_vector()])

    state, message = monitor.observe_tool_call(
        "http_request", {"url": "http://example.com/api/profile"}, 5
    )
    assert state == InterventionState.ENFORCE_STRATEGY_SHIFT
    assert "transfer-idor" in (message or "")
    monitor.finish_step(progress_made=False, executed=False)
    assert monitor.active_contract is not None

    pivot = {
        "method": "GET",
        "url": "http://example.com/api/transfers/7?account_id=9",
        "owasp_category": "API1",
        "test_class": "idor",
    }
    assert (
        monitor.observe_tool_call("http_request", pivot, 6)[0]
        == InterventionState.NORMAL
    )
    assert monitor.active_contract is not None
    monitor.finish_step(progress_made=False, executed=True)
    assert monitor.active_contract is None


def test_contract_third_rejection_stays_blocked_and_terminates():
    monitor = ExecutionMonitor(max_contract_rejections=3)
    monitor.set_strategy_contract(1, "Stalled", [_vector()])
    nonpivot = {"url": "http://example.com/api/profile"}

    for step in range(2, 5):
        state, _ = monitor.observe_tool_call("http_request", nonpivot, step)
        assert state == InterventionState.ENFORCE_STRATEGY_SHIFT
        monitor.finish_step(progress_made=False, executed=False)
    assert monitor.active_contract is not None
    assert "refusing" in (monitor.check_termination() or "")


def test_explicit_justification_satisfies_contract_only_after_execution():
    monitor = ExecutionMonitor()
    monitor.set_strategy_contract(1, "Stalled", [_vector()])
    action = {
        "url": "http://example.com/different",
        "strategy_pivot_justification": "A newly discovered admin route is higher priority.",
    }

    assert (
        monitor.observe_tool_call("http_request", action, 2)[0]
        == InterventionState.NORMAL
    )
    assert monitor.active_contract is not None
    monitor.finish_step(progress_made=False, executed=True)
    assert monitor.active_contract is None


def test_checkpoint_round_trip_preserves_structured_contract_and_counters():
    monitor = ExecutionMonitor()
    monitor.set_strategy_contract(9, "Stalled", [_vector()])
    monitor.finish_step(progress_made=False, executed=False)

    restored = ExecutionMonitor.from_state(monitor.to_state())
    assert restored.nonprogress_steps == 1
    assert restored.active_contract is not None
    assert restored.active_contract.suggested_vectors[0].id == "transfer-idor"


def test_tool_schema_augmentation_is_non_mutating():
    tools = [
        {"name": "http_request", "input_schema": {"type": "object", "properties": {}}}
    ]
    augmented = add_strategy_justification_to_tools(tools)

    assert "strategy_pivot_justification" not in tools[0]["input_schema"]["properties"]
    assert augmented is not None
    assert "strategy_pivot_justification" in augmented[0]["input_schema"]["properties"]
