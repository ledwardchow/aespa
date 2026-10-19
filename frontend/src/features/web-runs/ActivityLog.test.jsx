import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ActivityLog } from "./ActivityLog.jsx";
import { logEventTypes, visibleLogEntries } from "./activityLogFilters.js";

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

test("LLM Errors includes every LLM event in a refused step and excludes healthy steps", () => {
  const entries = [
    event(1, "thinking_step", "Step 1: LLM deciding next action", "deciding", { step: 1 }),
    event(2, "llm_request", "Step 1: sending to LLM (9 messages in context)", "pending", {
      step: 1,
    }),
    event(3, "llm_response", "Step 1: LLM returned a tool call", "complete", { step: 1 }),
    event(4, "thinking_step", "Step 2: LLM deciding next action", "deciding", { step: 2 }),
    event(5, "llm_request", "Step 2: sending to LLM (10 messages in context)", "pending", {
      step: 2,
    }),
    event(6, "llm_heartbeat", "Step 2: waiting for LLM response (30s elapsed)", "pending"),
    event(7, "specialist_step", "Specialist checking a route", "complete", { step: 2 }),
    event(8, "llm_response", "Step 2: LLM provider refused the scan request", "warning", {
      step: 2,
      error_type: "LLMRefusalError",
    }),
    event(
      9,
      "llm_response",
      "Step 2: retrying the OpenAI cyber refusal with shorter instructions.",
      "retrying",
      { step: 2, recovery_template: "shorter" },
    ),
    event(9.5, "thinking_step", "Step 2: LLM deciding next action", "deciding", { step: 2 }),
    event(10, "llm_request", "Step 2: sending to LLM (11 messages in context)", "pending", {
      step: 2,
    }),
    event(
      11,
      "llm_response",
      "Step 2: shorter OpenAI retry accepted; continuing with browser.",
      "complete",
      { step: 2, refusal_recovery: "accepted" },
    ),
    event(11.5, "thinking_step", "Step 2: browser GET /admin", "running", { step: 2 }),
    event(11.6, "thinking_step", "Step 2: LLM deciding next action", "deciding", { step: 2 }),
    event(11.7, "llm_request", "Step 2: sending to LLM (9 messages in context)", "pending", {
      step: 2,
    }),
    event(11.8, "llm_response", "Step 2: LLM returned a tool call", "complete", { step: 2 }),
    event(12, "thinking_step", "Step 3: LLM deciding next action", "deciding", { step: 3 }),
    event(13, "llm_request", "Step 3: sending to LLM (12 messages in context)", "pending", {
      step: 3,
    }),
    event(14, "llm_response", "Step 3: LLM returned a tool call", "complete", { step: 3 }),
  ];
  expect(
    visibleLogEntries(entries, new Set(["llm-errors"]), false).map((entry) => entry._id),
  ).toEqual([4, 5, 6, 8, 9, 9.5, 10, 11, 11.5]);
});

test("LLM Errors includes the request and repeated refusal failure", () => {
  const entries = [
    event(1, "thinking_step", "Step 4: LLM deciding next action", "deciding", { step: 4 }),
    event(2, "llm_request", "Step 4: sending to LLM (12 messages in context)", "pending", {
      step: 4,
    }),
    event(
      3,
      "llm_response",
      "Step 4: provider refused this request; retrying once before skipping it.",
      "warning",
      { step: 4, refusal_retry: 1 },
    ),
    event(3.5, "thinking_step", "Step 4: LLM deciding next action", "deciding", { step: 4 }),
    event(4, "llm_request", "Step 4: sending to LLM (12 messages in context)", "pending", {
      step: 4,
    }),
    event(
      5,
      "llm_response",
      "Step 4: provider refused this request twice — skipping it and moving to a different target.",
      "warning",
      { step: 4, refusal_skips: 1 },
    ),
    event(6, "thinking_step", "Step 5: LLM deciding next action", "deciding", { step: 5 }),
    event(7, "llm_request", "Step 5: sending to LLM (12 messages in context)", "pending", {
      step: 5,
    }),
  ];
  expect(
    visibleLogEntries(entries, new Set(["llm-errors"]), false).map((entry) => entry._id),
  ).toEqual([1, 2, 3, 3.5, 4, 5]);
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
    "Test Lead step",
    "Sending to LLM",
    "Provider refused this request",
    "Shorter retry accepted",
  ]);
  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  expect(screen.getByRole("group", { name: "Display options" })).toBeTruthy();
  fireEvent.click(screen.getByLabelText("LLM Errors"));
  expect(messages()).toEqual(["Provider refused this request", "Shorter retry accepted"]);
  fireEvent.click(screen.getByLabelText("Newest first"));
  expect(messages()).toEqual(["Shorter retry accepted", "Provider refused this request"]);
  fireEvent.click(screen.getByLabelText("All"));
  expect(messages()[0]).toBe("Shorter retry accepted");
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("group", { name: "Display options" })).toBeNull();
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Display options" }));
  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  fireEvent.pointerDown(document.body);
  expect(screen.queryByRole("group", { name: "Display options" })).toBeNull();
});
