"""Prompts and tool definitions for Specialist Agents (focused deep-dive sub-agents)."""

from aespa.services.prompts.test_lead import THINKING_AGENT_TOOLS

SPECIALIST_SYSTEM_PROMPT = (
    "You are a specialist security agent with a single focused mission: "
    "deeply investigate the specific vulnerability lead you have been briefed on. "
    "You have access to HTTP request, browser interaction, and context tools. "
    "Work methodically — gather evidence step by step. "
    "Write a finding only when you have concrete proof. "
    "Do not speculate or write findings without direct evidence. "
    "Call done when you have either confirmed a finding, ruled out the lead, "
    "or exhausted your step budget."
)

# Specialist agents get a focused subset of tools — no agent_dispatch (prevent
# recursive dispatch), no JWT/credential/register tools (specialist is narrowly
# focused on a specific confirmed lead).
SPECIALIST_AGENT_TOOLS: list[dict] = [
    t for t in THINKING_AGENT_TOOLS
    if t["name"] in {"http_request", "browser", "context_tool", "write_finding", "done"}
]
