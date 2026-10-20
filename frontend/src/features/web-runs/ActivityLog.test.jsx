import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ActivityLog } from "./ActivityLog.jsx";
import { buildRefusalTraces, logEventTypes } from "./activityLogFilters.js";

const event = (id, phase, message, status = "complete", data = {}) => ({
  _id: id,
  _ts: `${id}:00`,
  phase,
  message,
  status,
  data,
});

test("classifies refusal retries and recovery outcomes as LLM errors", () => {
  const refusalEvents = [
    event(1, "llm_response", "Provider refused this request; retrying", "warning"),
    event(2, "llm_response", "Retrying the OpenAI cyber refusal", "retrying"),
    event(3, "llm_response", "Shorter OpenAI retry accepted", "complete", {
      refusal_recovery: "accepted",
    }),
    event(4, "llm_response", "Shorter OpenAI retry was refused", "warning", {
      refusal_recovery: "refused",
    }),
    event(
      8,
      "llm_response",
      "Step 4: shorter OpenAI retry was refused. Leaving this test unresolved and moving to a different target.",
      "warning",
      { step: 4, refusal_recovery: "refused", refusal_skips: 1 },
    ),
  ];
  for (const entry of refusalEvents) {
    expect(logEventTypes(entry).has("llm-errors")).toBe(true);
  }
  expect(
    logEventTypes(event(5, "llm_request", "Sending 9 messages to LLM")).has("llm-errors"),
  ).toBe(false);
  expect(
    logEventTypes(event(6, "llm_response", "LLM returned a tool call")).has("llm-errors"),
  ).toBe(false);
  expect(
    logEventTypes(
      event(7, "scan_failed", "LLM provider refusal: request denied", "error", {
        error_type: "LLMRefusalError",
      }),
    ).has("llm-errors"),
  ).toBe(true);
});

test("classifies validator steps separately from Test Lead steps", () => {
  expect(logEventTypes(event(1, "thinking_step", "Validating finding: X")).has("validator")).toBe(
    true,
  );
  expect(logEventTypes(event(1, "thinking_step", "Validating finding: X")).has("test-lead")).toBe(
    false,
  );
  expect(logEventTypes(event(2, "thinking_step", "Testing endpoint")).has("test-lead")).toBe(true);
  expect(logEventTypes(event(3, "specialist_step", "Testing XSS")).has("specialist")).toBe(true);
  expect(logEventTypes(event(4, "reporting_turn", "Writing findings")).has("reporting")).toBe(true);
});

test("display options filter events and reverse their order", () => {
  render(
    <ActivityLog
      runId={7}
      activityLog={[
        event(1, "thinking_step", "Test Lead step"),
        event(2, "llm_request", "Sending to LLM"),
        event(3, "llm_response", "Provider refused this request", "warning"),
        event(4, "llm_response", "Shorter retry accepted", "complete", {
          refusal_recovery: "accepted",
        }),
      ]}
      active={false}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const messages = () =>
    [...document.querySelectorAll(".activity-msg")].map((node) => node.textContent);
  expect(messages()).toEqual([
    "Shorter retry accepted",
    "Provider refused this request",
    "Sending to LLM",
    "Test Lead step",
  ]);
  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  expect(screen.getByRole("group", { name: "Display options" })).toBeTruthy();
  expect(screen.getByLabelText("Newest first").checked).toBe(true);
  expect(screen.queryByLabelText("LLM Errors")).toBeNull();
  fireEvent.click(screen.getByLabelText("Test Lead"));
  expect(messages()).toEqual(["Test Lead step"]);
  fireEvent.click(screen.getByLabelText("Newest first"));
  expect(messages()).toEqual(["Test Lead step"]);
  fireEvent.click(screen.getByLabelText("All"));
  expect(messages()[0]).toBe("Test Lead step");
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("group", { name: "Display options" })).toBeNull();
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Display options" }));
  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  fireEvent.pointerDown(document.body);
  expect(screen.queryByRole("group", { name: "Display options" })).toBeNull();
});

test("builds a shorter retry trace and uses the later recorded action", () => {
  const entries = [
    event(1, "llm_request", "Step 2: sending to LLM", "pending", { step: 2 }),
    event(1.5, "llm_heartbeat", "Step 2: waiting for LLM response", "pending", { step: 2 }),
    event(2, "llm_response", "Step 2: LLM provider refused the scan request", "warning", {
      step: 2,
      error_type: "LLMRefusalError",
    }),
    event(3, "specialist_step", "Specialist checking a route"),
    event(4, "llm_response", "Step 2: retrying the OpenAI cyber refusal", "retrying", {
      step: 2,
      recovery_template: "shorter",
    }),
    event(5, "llm_request", "Step 2: sending shorter retry", "pending", { step: 2 }),
    event(
      6,
      "llm_response",
      "Step 2: shorter OpenAI retry accepted; continuing with browser",
      "complete",
      { step: 2, refusal_recovery: "accepted" },
    ),
    event(7, "thinking_step", "Step 2: browser GET /admin → 200", "complete", { step: 2 }),
  ];
  const { traces, usedIndices } = buildRefusalTraces(entries);
  expect(traces).toHaveLength(1);
  expect(traces[0].outcome).toBe("succeeded");
  expect(traces[0].attempts.map(({ label, outcome }) => [label, outcome])).toEqual([
    ["Original request", "refused"],
    ["Shorter prompt", "accepted"],
  ]);
  expect(traces[0].nextAction.message).toContain("browser GET /admin");
  expect(traces[0].events.map((entry) => entry._id)).toContain(1.5);
  expect([...usedIndices]).not.toContain(3);
});

test("trace shows one result per try through a fresh-context refusal and later success", () => {
  const entries = [
    event(1, "llm_request", "Step 2: sending to LLM", "pending", { step: 2 }),
    event(2, "llm_response", "Step 2: provider refused", "warning", {
      step: 2,
      error_type: "LLMRefusalError",
    }),
    event(3, "llm_response", "Step 2: shorter retry", "retrying", {
      step: 2,
      recovery_template: "shorter",
    }),
    event(4, "llm_request", "Step 2: sending shorter retry", "pending", { step: 2 }),
    event(5, "llm_response", "Step 2: provider refused again", "warning", {
      step: 2,
      error_type: "LLMRefusalError",
    }),
    event(6, "llm_response", "Step 2: retrying with fresh context", "retrying", {
      step: 2,
      refusal_recovery: "fresh_context",
    }),
    event(7, "llm_request", "Step 2: sending fresh retry", "pending", { step: 2 }),
    event(8, "llm_response", "Step 2: fresh context refused", "warning", {
      step: 2,
      error_type: "LLMRefusalError",
    }),
    event(9, "llm_response", "Step 2: leaving test unresolved", "warning", {
      step: 2,
      refusal_skips: 1,
    }),
    event(10, "llm_request", "Step 2: another request", "pending", { step: 2 }),
    event(11, "llm_response", "Step 2: later request accepted", "complete", { step: 2 }),
  ];
  const { traces } = buildRefusalTraces(entries);
  expect(traces).toHaveLength(1);
  expect(traces[0].outcome).toBe("succeeded");
  expect(traces[0].attempts.map(({ label, outcome }) => [label, outcome])).toEqual([
    ["Original request", "refused"],
    ["Shorter prompt", "refused"],
    ["Fresh context", "refused"],
    ["Another try", "accepted"],
  ]);
  const { container } = render(
    <ActivityLog
      view="errors"
      runId={319}
      activityLog={entries}
      active={false}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );
  expect(container.querySelectorAll(".activity-refusal-trace-point")).toHaveLength(4);
});

test("keeps repeated refusals for one scanner step in one trace", () => {
  const entries = [
    event(1, "llm_request", "Step 266: sending to LLM", "pending", { step: 266 }),
    event(2, "llm_response", "Step 266: provider refused", "warning", {
      step: 266,
      error_type: "LLMRefusalError",
    }),
    event(3, "llm_response", "Step 266: skipping test", "warning", {
      step: 266,
      refusal_skips: 1,
    }),
    event(4, "llm_request", "Step 266: sending to LLM", "pending", { step: 266 }),
    event(5, "llm_response", "Step 266: provider refused", "warning", {
      step: 266,
      error_type: "LLMRefusalError",
    }),
    event(6, "llm_response", "Step 266: skipping test", "warning", {
      step: 266,
      refusal_skips: 2,
    }),
    event(7, "llm_request", "Step 266: sending to LLM", "pending", { step: 266 }),
    event(8, "llm_response", "Step 266: LLM called http_request", "complete", { step: 266 }),
  ];
  const { traces } = buildRefusalTraces(entries);
  expect(traces).toHaveLength(1);
  expect(traces[0].outcome).toBe("succeeded");
  expect(traces[0].rejectedPrompts).toHaveLength(0);
  expect(traces[0].events).toHaveLength(entries.length);
  expect(traces[0].attempts.map(({ label, outcome }) => [label, outcome])).toEqual([
    ["Original request", "refused"],
    ["Another try", "refused"],
    ["Another try", "accepted"],
  ]);
  const { container } = render(
    <ActivityLog
      view="errors"
      runId={319}
      activityLog={entries}
      active={false}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );
  expect(container.querySelector(".activity-count-label").textContent).toContain(
    "1 succeeded · 2 failed",
  );
});

test("original log data stays closed until its own control is opened", async () => {
  render(
    <ActivityLog
      view="errors"
      runId={319}
      activityLog={[
        event(1, "llm_request", "Step 266: sending to LLM", "pending", { step: 266 }),
        event(2, "llm_response", "Step 266: provider refused", "warning", {
          step: 266,
          error_type: "LLMRefusalError",
          extra: "full raw log marker",
        }),
      ]}
      active={false}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );
  expect(screen.queryByText(/full raw log marker/)).toBeNull();
  fireEvent.click(screen.getByText("Show original log events"));
  expect(screen.queryByText(/full raw log marker/)).toBeNull();
  fireEvent.click(screen.getAllByText("View event data")[1]);
  await waitFor(() => expect(screen.getByText(/full raw log marker/)).toBeTruthy());
});

test("identical retry success and a later refusal stay in separate traces", () => {
  const entries = [
    event(1, "llm_request", "Step 3: sending to LLM", "pending", { step: 3 }),
    event(2, "llm_response", "Step 3: provider refused this request", "warning", {
      step: 3,
      error_type: "LLMRefusalError",
    }),
    event(3, "llm_response", "Step 3: provider refused this request; retrying once", "warning", {
      step: 3,
      refusal_retry: 1,
    }),
    event(4, "llm_request", "Step 3: sending to LLM", "pending", { step: 3 }),
    event(5, "llm_response", "Step 3: LLM → browser", "complete", { step: 3 }),
    event(6, "thinking_step", "Step 3: browser GET /first → 200", "complete", { step: 3 }),
    event(7, "llm_request", "Step 3: sending to LLM", "pending", { step: 3 }),
    event(8, "llm_response", "Step 3: provider refused this request", "warning", {
      step: 3,
      error_type: "LLMRefusalError",
    }),
    event(9, "llm_response", "Step 3: provider refused this request; retrying once", "warning", {
      step: 3,
      refusal_retry: 1,
    }),
    event(10, "llm_request", "Step 3: sending to LLM", "pending", { step: 3 }),
    event(11, "llm_response", "Step 3: provider refused this request", "warning", {
      step: 3,
      error_type: "LLMRefusalError",
    }),
    event(
      12,
      "llm_response",
      "Step 3: provider refused this request twice; skipping it",
      "warning",
      { step: 3, refusal_skips: 1 },
    ),
    event(13, "thinking_step", "Step 4: LLM deciding next action", "deciding", { step: 4 }),
    event(14, "llm_request", "Step 4: sending to LLM", "pending", { step: 4 }),
  ];
  const { traces } = buildRefusalTraces(entries);
  expect(traces.map((trace) => trace.outcome)).toEqual(["succeeded", "skipped"]);
  expect(traces[0].nextAction.message).toContain("GET /first");
  expect(traces[1].nextAction.message).toBe("Another LLM request was sent");
  expect(traces[1].attempts.at(-1).outcome).toBe("refused");
});

test("pending and terminal refusals do not invent a later action", () => {
  const pending = [
    event(1, "llm_request", "Step 5: sending to LLM", "pending", { step: 5 }),
    event(2, "llm_response", "Step 5: provider refused this request", "warning", {
      step: 5,
      error_type: "LLMRefusalError",
    }),
    event(3, "llm_response", "Step 5: retrying the OpenAI cyber refusal", "retrying", {
      step: 5,
      recovery_template: "shorter",
    }),
  ];
  expect(buildRefusalTraces(pending).traces[0]).toMatchObject({
    outcome: "pending",
    nextAction: null,
  });
  const terminal = [
    ...pending,
    event(4, "llm_response", "Step 5: shorter retry refused; refusal limit reached", "error", {
      step: 5,
      refusal_skips: 4,
      refusal_recovery: "refused",
    }),
    event(5, "scan_failed", "LLM provider refusal", "error", { error_type: "LLMRefusalError" }),
  ];
  expect(buildRefusalTraces(terminal).traces[0]).toMatchObject({
    outcome: "stopped",
    nextAction: { message: "LLM provider refusal" },
  });
});

test("LLM Errors renders traces in the existing feed and keeps other errors below", () => {
  render(
    <ActivityLog
      view="errors"
      runId={7}
      activityLog={[
        event(1, "llm_request", "Step 8: sending to LLM", "pending", { step: 8 }),
        event(2, "llm_response", "Step 8: provider refused this request", "warning", {
          step: 8,
          error_type: "LLMRefusalError",
        }),
        event(
          3,
          "llm_response",
          "Step 8: provider refused this request; retrying once",
          "warning",
          { step: 8, refusal_retry: 1 },
        ),
        event(4, "llm_request", "Step 8: sending retry", "pending", { step: 8 }),
        event(5, "llm_response", "Step 8: LLM → browser", "complete", { step: 8 }),
        event(6, "llm_protocol", "Provider connection error", "error"),
      ]}
      active={false}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  expect(screen.queryByText("Event type")).toBeNull();
  expect(document.querySelectorAll(".activity-refusal-trace")).toHaveLength(1);
  expect(document.querySelector(".activity-count-label").textContent).toContain(
    "1 succeeded · 0 failed",
  );
  expect(screen.getByText("Retry succeeded")).toBeTruthy();
  expect(screen.getByText("No later action recorded")).toBeTruthy();
  expect(screen.getByText("Other LLM errors")).toBeTruthy();
  expect(document.querySelectorAll(".activity-msg")).toHaveLength(1);
  fireEvent.click(screen.getByText("Show original log events"));
  expect(screen.getByText("Step 8: sending retry")).toBeTruthy();
});

test("shows the preceding test and copies each complete rejected prompt", async () => {
  const originalPrompt = `Original system and conversation\n${"x".repeat(10000)}\nlast message`;
  const retryPrompt = "Shorter system and conversation\nretry message";
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
  render(
    <ActivityLog
      view="errors"
      runId={7}
      activityLog={[
        event(1, "thinking_step", "Step 1: GET /accounts/7", "running", {
          step: 1,
          method: "GET",
          url: "https://target.test/accounts/7",
          hypothesis: "Check whether another user can read this account",
        }),
        event(2, "llm_request", "Step 2: sending to LLM", "pending", { step: 2 }),
        event(3, "llm_response", "Step 2: provider refused this request", "warning", {
          step: 2,
          error_type: "LLMRefusalError",
          prompt: originalPrompt,
        }),
        event(4, "llm_response", "Step 2: trying shorter instructions", "retrying", {
          step: 2,
          recovery_template: "shorter",
        }),
        event(5, "llm_request", "Step 2: sending shorter retry", "pending", { step: 2 }),
        event(6, "llm_response", "Step 2: provider refused this request", "warning", {
          step: 2,
          error_type: "LLMRefusalError",
          prompt: retryPrompt,
        }),
        event(7, "llm_response", "Step 2: leaving the test unresolved", "warning", {
          step: 2,
          refusal_skips: 1,
        }),
      ]}
      active={false}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );

  expect(screen.getByText("Check whether another user can read this account")).toBeTruthy();
  expect(screen.getByText("https://target.test/accounts/7")).toBeTruthy();
  const buttons = screen.getAllByRole("button", { name: "Copy prompt" });
  expect(buttons).toHaveLength(2);
  fireEvent.click(buttons[0]);
  expect(await screen.findByRole("button", { name: "Copied" })).toBeTruthy();
  expect(writeText).toHaveBeenCalledWith(originalPrompt);
  fireEvent.click(buttons[1]);
  expect(writeText).toHaveBeenLastCalledWith(retryPrompt);
});

test("newest first reverses trace cards while each timeline stays in time order", () => {
  render(
    <ActivityLog
      view="errors"
      runId={7}
      activityLog={[
        event(1, "llm_request", "Step 1: request", "pending", { step: 1 }),
        event(2, "llm_response", "Step 1: provider refused this request", "warning", {
          step: 1,
          error_type: "LLMRefusalError",
        }),
        event(3, "llm_response", "Step 1: retrying once", "warning", { step: 1, refusal_retry: 1 }),
        event(4, "llm_response", "Step 1: accepted", "complete", { step: 1 }),
        event(5, "llm_request", "Step 2: request", "pending", { step: 2 }),
        event(6, "llm_response", "Step 2: provider refused this request", "warning", {
          step: 2,
          error_type: "LLMRefusalError",
        }),
        event(7, "llm_response", "Step 2: retrying once", "warning", { step: 2, refusal_retry: 1 }),
        event(8, "llm_response", "Step 2: refused again", "warning", { step: 2, refusal_skips: 1 }),
      ]}
      active={false}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );
  expect(document.querySelector(".activity-count-label").textContent).toContain(
    "1 succeeded · 1 failed",
  );
  const cards = [...document.querySelectorAll(".activity-refusal-trace")];
  expect(
    cards.map((card) => card.querySelector(".activity-refusal-trace-heading strong").textContent),
  ).toEqual(["Step 2", "Step 1"]);
  expect(
    [...cards[0].querySelectorAll(".activity-refusal-trace-point strong")].map(
      (node) => node.textContent,
    ),
  ).toEqual(["Try 1"]);
  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  fireEvent.click(screen.getByLabelText("Newest first"));
  expect(
    [...document.querySelectorAll(".activity-refusal-trace")].map(
      (card) => card.querySelector(".activity-refusal-trace-heading strong").textContent,
    ),
  ).toEqual(["Step 1", "Step 2"]);
});
