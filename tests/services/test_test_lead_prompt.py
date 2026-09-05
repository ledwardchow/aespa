from __future__ import annotations

from aespa.services.prompts.test_lead import get_thinking_agent_system


def test_track_prompt_requires_broad_context_aware_xss_testing() -> None:
    prompt = get_thinking_agent_system(False)

    assert "XSS is a primary objective, separate from SQL injection" in prompt
    assert "distinct input and rendering contexts" in prompt
    assert "A single generic payload" in prompt
    assert "SQL injection probes do not count as XSS testing" in prompt
    assert "Before step" not in prompt
    assert "at least two input-bearing routes" not in prompt
