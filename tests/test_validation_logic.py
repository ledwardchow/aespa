import asyncio

from aespa.services import llm
from aespa.services import scanner
from aespa.services import validator
from aespa.services.validator import _body_contains_page_evidence, _looks_like_spa_shell


def test_validate_finding_result_without_probe_results_is_false_positive():
    result = asyncio.run(llm.validate_finding_result(
        config=None,
        title="Possible issue",
        description="A finding that could not be reproduced.",
        evidence="REQUEST... RESPONSE...",
        probe_results=[],
    ))

    assert result["verdict"] == "false_positive"
    assert "No validation probes" in result["reasoning"]


def test_spa_shell_is_not_treated_as_protected_content():
    body = """
    <!doctype html>
    <html><head><script src="/assets/app.js"></script></head>
    <body><div id="root"></div></body></html>
    """

    assert _looks_like_spa_shell(body, "text/html; charset=utf-8") is True
    assert _body_contains_page_evidence(body, "Admin Dashboard", "Secret invoice data") is False


def test_page_evidence_detection_matches_authorized_content():
    body = "<html><body><h1>Admin Dashboard</h1><p>Quarterly revenue export is ready.</p></body></html>"

    assert _body_contains_page_evidence(
        body,
        "Admin Dashboard",
        "Quarterly revenue export is ready.",
    ) is True


def test_bac_evidence_requires_original_user_content():
    original_text = """
    Account overview
    Statement balance for Alice Example is GBP 1,204.55
    Recent transfer reference ALICE-7781 is pending review
    """
    alternate_body = """
    <html><body>
      <h1>Account overview</h1>
      <p>Statement balance for Bob Example is GBP 88.10</p>
      <p>Recent transfer reference BOB-4412 is pending review</p>
    </body></html>
    """

    assert scanner._body_contains_original_page_evidence(
        alternate_body,
        "Account overview",
        original_text,
    ) is False


def test_bac_evidence_matches_original_user_content():
    original_text = """
    Account overview
    Statement balance for Alice Example is GBP 1,204.55
    Recent transfer reference ALICE-7781 is pending review
    """
    leaked_body = """
    <html><body>
      <h1>Account overview</h1>
      <p>Statement balance for Alice Example is GBP 1,204.55</p>
    </body></html>
    """

    assert scanner._body_contains_original_page_evidence(
        leaked_body,
        "Account overview",
        original_text,
    ) is True


def test_request_stop_cancels_running_validation(monkeypatch):
    class FakeTask:
        cancelled = False

        def cancel(self):
            self.cancelled = True

    task = FakeTask()
    reset_calls = []
    monkeypatch.setattr(validator, "_reset_validating_findings", lambda run_id, note: reset_calls.append((run_id, note)))
    validator._validation_tasks[123] = task
    validator._stop_requested.discard(123)

    try:
        assert validator.request_stop(123) is True
        assert task.cancelled is True
        assert 123 in validator._stop_requested
        assert reset_calls == [(123, "Validation stopped by user.")]
    finally:
        validator._validation_tasks.pop(123, None)
        validator._stop_requested.discard(123)


def test_request_stop_noops_when_validation_not_running(monkeypatch):
    reset_calls = []
    monkeypatch.setattr(validator, "_reset_validating_findings", lambda run_id, note: reset_calls.append((run_id, note)))
    validator._validation_tasks.pop(456, None)
    validator._stop_requested.discard(456)

    assert validator.request_stop(456) is False
    assert 456 not in validator._stop_requested
    assert reset_calls == []
