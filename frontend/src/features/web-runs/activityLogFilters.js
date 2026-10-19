export const LOG_EVENT_TYPES = [
  ["test-lead", "Test Lead"],
  ["specialist", "Specialist"],
  ["reporting", "Reporting"],
  ["validator", "Validator"],
  ["llm-errors", "LLM Errors"],
];

const REPORTING_PHASES = new Set([
  "thinking_analysis",
  "reporting_turn",
  "post_scan_review",
  "post_review_turn",
]);

export function logEventTypes(entry) {
  const types = new Set();
  const { phase, status, data, message = "" } = entry;
  const validatorStep = phase === "thinking_step" && message.startsWith("Validating finding:");

  if (phase === "poc_verify" || phase === "session_validator" || validatorStep) {
    types.add("validator");
  }
  if (
    phase?.startsWith("specialist_") ||
    (typeof data?.agent_id === "string" && data.agent_id.startsWith("specialist-"))
  ) {
    types.add("specialist");
  }
  if (REPORTING_PHASES.has(phase)) types.add("reporting");
  if (
    phase === "thinking_scan" ||
    (phase === "thinking_step" && !validatorStep) ||
    phase === "test_lead_completion_policy" ||
    phase === "execution_monitor" ||
    phase === "mentor_guidance"
  ) {
    types.add("test-lead");
  }

  const refusalMessage = /refus/i.test(message);
  if (
    (phase === "llm_response" &&
      (status === "error" ||
        status === "warning" ||
        data?.error ||
        data?.refusal_recovery ||
        data?.refusal_retry ||
        data?.refusal_skips ||
        refusalMessage)) ||
    (phase === "llm_protocol" && (status === "error" || status === "warning")) ||
    (phase === "scan_failed" && data?.error_type === "LLMRefusalError")
  ) {
    types.add("llm-errors");
  }
  return types;
}

export function visibleLogEntries(entries, selectedTypes, newestFirst) {
  const failedStepIndices = selectedTypes.has("llm-errors") ? failedLlmStepIndices(entries) : null;
  const matching = selectedTypes.size
    ? entries.filter(
        (entry, index) =>
          failedStepIndices?.has(index) ||
          [...logEventTypes(entry)].some((type) => selectedTypes.has(type)),
      )
    : entries;
  return newestFirst ? [...matching].reverse() : matching;
}

function failedLlmStepIndices(entries) {
  const included = new Set();
  let group = null;
  const finish = () => {
    if (group?.failed) group.indices.forEach((index) => included.add(index));
    group = null;
  };

  entries.forEach((entry, index) => {
    const llmEvent = ["llm_request", "llm_response", "llm_heartbeat"].includes(entry.phase);
    const thinkingStep = entry.phase === "thinking_step" && /^Step \d+:/.test(entry.message || "");
    if (!llmEvent && !thinkingStep) {
      if (entry.phase === "thinking_scan") finish();
      return;
    }
    const step = entry.data?.step ?? Number(/^Step (\d+):/.exec(entry.message || "")?.[1]);
    if (!Number.isFinite(step)) {
      finish();
      return;
    }
    if (
      group &&
      (group.step !== step ||
        (group.finished &&
          ((thinkingStep && entry.status === "deciding") || entry.phase === "llm_request")))
    ) {
      finish();
    }
    group ??= { step, indices: [], failed: false, finished: false };
    group.indices.push(index);
    group.failed ||= logEventTypes(entry).has("llm-errors");
    if (entry.phase === "llm_response") {
      group.finished = entry.status === "complete" || Boolean(entry.data?.refusal_skips);
    }
  });
  finish();
  return included;
}
