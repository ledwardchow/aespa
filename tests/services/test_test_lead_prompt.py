from __future__ import annotations

from aespa.services.prompts.test_lead import (
    THINKING_AGENT_TOOLS,
    get_api_test_lead_tools,
    get_sast_validate_tools,
    get_thinking_agent_system,
)


def test_track_prompt_requires_broad_context_aware_xss_testing() -> None:
    prompt = get_thinking_agent_system(False)

    assert "XSS is a primary objective, separate from SQL injection" in prompt
    assert "distinct input and rendering contexts" in prompt
    assert "A single generic payload" in prompt
    assert "SQL injection probes do not count as XSS testing" in prompt
    assert "Before step" not in prompt
    assert "at least two input-bearing routes" not in prompt


def _http_request_tool(tools: list[dict]) -> dict:
    return next(tool for tool in tools if tool["name"] == "http_request")


def test_http_request_requires_role_but_allows_uncategorized_setup() -> None:
    toolsets = [
        THINKING_AGENT_TOOLS,
        get_api_test_lead_tools(),
        get_sast_validate_tools(is_api_run=False),
        get_sast_validate_tools(is_api_run=True),
    ]

    for tools in toolsets:
        schema = _http_request_tool(tools)["input_schema"]
        assert "request_role" in schema["required"]
        assert "owasp_category" not in schema["required"]
        assert schema["properties"]["request_role"]["enum"] == [
            "setup",
            "recon",
            "test",
        ]
