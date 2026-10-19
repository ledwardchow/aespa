export const LOG_EVENT_TYPES = [
  ["test-lead", "Test Lead"],
  ["specialist", "Specialist"],
  ["reporting", "Reporting"],
  ["validator", "Validator"],
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
  const matching = selectedTypes.size
    ? entries.filter((entry) => [...logEventTypes(entry)].some((type) => selectedTypes.has(type)))
    : entries;
  return newestFirst ? [...matching].reverse() : matching;
}

function logStep(entry) {
  const step = entry.data?.step ?? Number(/^Step (\d+):/.exec(entry.message || "")?.[1]);
  return Number.isFinite(step) ? step : null;
}

function isRefusal(entry) {
  return (
    entry.phase === "llm_response" &&
    !entry.data?.refusal_retry &&
    !entry.data?.refusal_skips &&
    !entry.data?.refusal_recovery &&
    (entry.data?.error_type === "LLMRefusalError" ||
      /provider refused|refused the scan request/i.test(entry.message || ""))
  );
}

function traceAttempts(events) {
  const attempts = [];
  let nextLabel = null;
  for (const entry of events) {
    if (entry.data?.refusal_recovery === "fresh_context") nextLabel = "Fresh context";
    else if (entry.data?.recovery_template) nextLabel = "Shorter prompt";
    else if (entry.data?.refusal_retry && !nextLabel) nextLabel = "Retry";

    if (entry.phase === "llm_request") {
      attempts.push({
        label: nextLabel ?? (attempts.length ? "Another try" : "Original request"),
        startedAt: entry._ts,
        finishedAt: null,
        outcome: "pending",
      });
      nextLabel = null;
    }
    if (isRefusal(entry) || entry.data?.refusal_skips) {
      if (!attempts.length) {
        attempts.push({
          label: "Original request",
          startedAt: entry._ts,
          finishedAt: null,
          outcome: "pending",
        });
      }
      attempts.at(-1).outcome = "refused";
      attempts.at(-1).finishedAt = entry._ts;
    } else if (
      entry.data?.refusal_recovery === "accepted" ||
      (entry.phase === "llm_response" && entry.status === "complete")
    ) {
      attempts.at(-1).outcome = "accepted";
      attempts.at(-1).finishedAt = entry._ts;
    }
  }
  return attempts;
}

function nextRecordedAction(entries, startIndex) {
  let nextRequest = null;
  for (let index = startIndex; index < entries.length; index += 1) {
    const entry = entries[index];
    if (isRefusal(entry)) break;
    if (
      entry.phase === "thinking_step" &&
      entry.status !== "deciding" &&
      /^Step \d+:/.test(entry.message || "")
    ) {
      return { message: entry.message, time: entry._ts };
    }
    if (!nextRequest && entry.phase === "llm_request" && logStep(entry) !== null) {
      nextRequest = { message: "Another LLM request was sent", time: entry._ts };
    }
  }
  return nextRequest;
}

function precedingTest(entries, requestIndex, step) {
  for (let index = requestIndex - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.phase === "thinking_scan" && entry.status === "start") break;
    if (
      entry.phase !== "thinking_step" ||
      entry.status !== "running" ||
      logStep(entry) !== step - 1
    ) {
      continue;
    }
    const data = entry.data || {};
    return {
      purpose: data.hypothesis || data.payload_purpose || data.note || data.test_class || null,
      action: entry.message,
      target: data.url || entry.page_url || null,
    };
  }
  return null;
}

// A trace owns one scanner step, including retries after a skipped request.
export function buildRefusalTraces(entries) {
  const traces = [];
  const usedIndices = new Set();
  const latestRequestByStep = new Map();
  let active = null;

  const finish = (endIndex) => {
    if (!active) return;
    active.attempts = traceAttempts(active.events);
    active.nextAction ??= nextRecordedAction(entries, endIndex + 1);
    traces.push(active);
    active = null;
  };

  entries.forEach((entry, index) => {
    const step = logStep(entry);
    if (active && step !== null && step !== active.step && entry.phase === "llm_request") {
      finish(index - 1);
    }
    if (entry.phase === "llm_request" && step !== null) latestRequestByStep.set(step, index);
    if (isRefusal(entry) && step !== null) {
      if (active && active.step !== step) finish(index - 1);
      if (!active) {
        const requestIndex = latestRequestByStep.get(step);
        const request = requestIndex === undefined ? null : entries[requestIndex];
        active = {
          id: entry._id ?? index,
          step,
          time: request?._ts ?? entry._ts,
          outcome: "pending",
          events: [],
          nextAction: null,
          precedingTest: precedingTest(entries, requestIndex ?? index, step),
          rejectedPrompts: [],
        };
        if (request) {
          for (let preludeIndex = requestIndex; preludeIndex < index; preludeIndex += 1) {
            const preludeEntry = entries[preludeIndex];
            if (
              logStep(preludeEntry) !== step ||
              !["llm_request", "llm_heartbeat"].includes(preludeEntry.phase)
            ) {
              continue;
            }
            active.events.push(preludeEntry);
            usedIndices.add(preludeIndex);
          }
        }
      }
    }
    if (!active) return;
    if (entry.phase === "scan_failed" && entry.data?.error_type === "LLMRefusalError") {
      active.outcome = "stopped";
      active.nextAction = { message: entry.message, time: entry._ts };
      active.events.push(entry);
      usedIndices.add(index);
      finish(index);
      return;
    }
    if (
      step !== active.step ||
      !["llm_request", "llm_response", "llm_heartbeat"].includes(entry.phase)
    ) {
      return;
    }
    if (!active.events.includes(entry)) {
      active.events.push(entry);
      usedIndices.add(index);
    }
    if (entry.phase === "llm_request" && active.outcome === "skipped") {
      active.outcome = "pending";
    }
    if (isRefusal(entry)) {
      const prompt =
        entry.data?.prompt ||
        (active.rejectedPrompts.length === 0 ? active.events[0]?.data?.prompt : null);
      if (typeof prompt === "string" && prompt) {
        active.rejectedPrompts.push({ text: prompt, time: entry._ts });
      }
    }
    if (
      entry.data?.refusal_recovery === "accepted" ||
      (entry.phase === "llm_response" && entry.status === "complete")
    ) {
      active.outcome = "succeeded";
      finish(index);
    } else if (entry.data?.refusal_skips) {
      active.outcome = entry.status === "error" ? "stopped" : "skipped";
    }
  });
  finish(entries.length - 1);
  return { traces, usedIndices };
}
