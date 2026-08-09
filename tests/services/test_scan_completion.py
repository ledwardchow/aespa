from __future__ import annotations

from aespa.services.scan_completion import ScanCompletionPolicy


def _gaps() -> dict:
    return {
        "next_actions": [
            {
                "method": "GET",
                "url": f"https://target.local/api/items/{index}",
                "owasp_category": "A01",
                "reason": "authenticated object route",
            }
            for index in range(8)
        ]
    }


def test_failed_session_attempt_cannot_trap_completion():
    policy = ScanCompletionPolicy()
    policy.session_created(
        "forged_admin", lifecycle_state="verified", challenge_eligible=True
    )

    allowed, feedback, _ = policy.check_done()
    assert allowed is False
    assert "forged_admin" in feedback

    policy.session_attempted("forged_admin", 401)
    assert policy.pending_session_labels() == []

    allowed, _, message = policy.check_done()
    assert allowed is True
    assert "accepted" in message.lower()


def test_declined_session_challenge_is_only_issued_once():
    policy = ScanCompletionPolicy()
    policy.session_created(
        "unused", lifecycle_state="verified", challenge_eligible=True
    )

    assert policy.check_done()[0] is False
    allowed, _, message = policy.check_done()

    assert allowed is True
    assert "declined" in message


def test_coverage_challenges_are_bounded_and_progress_aware():
    policy = ScanCompletionPolicy()

    first = policy.check_done(_gaps)
    assert first[0] is False
    assert "round (1/1)" in first[1]

    for index in range(3):
        policy.record_progress(f"coverage:{index}")
    second = policy.check_done(_gaps)
    assert second[0] is True
    assert policy.total_rejections == 1


def test_candidate_session_does_not_block_completion_and_403_does_not_evict():
    policy = ScanCompletionPolicy()
    policy.session_created("auto_token")
    assert policy.pending_session_labels() == []
    assert policy.check_done()[0] is True

    policy.session_attempted("auto_token", 403)
    assert policy.sessions["auto_token"]["active"] is True
    assert policy.sessions["auto_token"]["lifecycle_state"] == "verified"


def test_unproductive_coverage_challenge_allows_next_done():
    policy = ScanCompletionPolicy()
    assert policy.check_done(_gaps)[0] is False

    allowed, _, message = policy.check_done(_gaps)

    assert allowed is True
    assert "fewer than three" in message


def test_identical_probe_is_suppressed_after_three_same_outcomes():
    policy = ScanCompletionPolicy()
    signature = policy.probe_signature(
        method="GET",
        url="https://target.local/api/profile",
        body=None,
        session_label="forged_admin",
        owasp_category="A01",
    )
    for _ in range(3):
        assert policy.repeated_probe_message(signature) is None
        policy.record_probe_outcome(signature, 401, '{"error":"unauthorized"}')

    message = policy.repeated_probe_message(signature)
    assert message is not None
    assert "SUPPRESSED" in message
    assert "3 times" in message


def test_intentional_repeat_limit_overrides_default_probe_suppression():
    policy = ScanCompletionPolicy()
    signature = policy.probe_signature(
        method="POST",
        url="https://target.local/api/auth/login",
        body={"email": "known@example.com", "password": "wrong"},
        session_label=None,
        owasp_category="A07",
        test_class="rate_limit",
    )
    for _ in range(6):
        assert (
            policy.repeated_probe_message(signature, intentional_repeat_limit=6) is None
        )
        policy.record_probe_outcome(signature, 401, '{"error":"unauthorized"}')

    message = policy.repeated_probe_message(signature, intentional_repeat_limit=6)
    assert message is not None
    assert "6 times" in message


def test_stagnation_warns_then_terminates_and_progress_resets_it():
    policy = ScanCompletionPolicy(stagnation_warning_calls=3, stagnation_stop_calls=5)
    assert "STAGNATION" not in policy.observe_tool_result("one")
    assert "STAGNATION" not in policy.observe_tool_result("two")
    assert "STAGNATION" in policy.observe_tool_result("three")
    assert policy.check_termination() is None

    policy.record_progress("coverage:new")
    policy.observe_tool_result("productive")
    assert policy.nonprogress_tool_calls == 0

    for _ in range(5):
        policy.observe_tool_result("same")
    assert "without measurable progress" in policy.check_termination()


def test_completion_state_round_trip_preserves_session_and_challenge_state():
    policy = ScanCompletionPolicy()
    policy.session_created(
        "customer", lifecycle_state="verified", challenge_eligible=True
    )
    policy.check_done()
    policy.record_progress("coverage:one")

    restored = ScanCompletionPolicy.from_state(policy.to_state())

    assert restored.pending_session_labels() == ["customer"]
    assert restored.session_challenges == 1
    assert restored.progress_generation == 1
