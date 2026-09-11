export const AGENT_ROLE_LABELS = [
  ["crawler", "Crawler", "Page discovery & classification (high volume, light reasoning)"],
  ["test_lead", "Test Lead", "The agentic reasoning loop (keep this on your best model)"],
  ["mentor", "Mentor", "Supervises stalled execution; inherits Test Lead when unassigned"],
  ["specialist", "Specialist", "Focused per-lead attack agents"],
  ["validator", "Validator", "Adversarial false-positive checks (high volume)"],
  ["api_scanner", "API Scanner", "API (OpenAPI/Postman) agentic scan loop"],
  ["sast", "SAST", "Static analysis over uploaded source"],
  [
    "component_mapper",
    "Component Mapper",
    "Cross-repository interface discovery (bounded, suitable for a cheaper code-capable model)",
  ],
  ["alice", "A.L.I.C.E.", "Interactive user-directed pentest chat agent"],
];
