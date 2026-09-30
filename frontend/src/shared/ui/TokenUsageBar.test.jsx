import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { TokenUsageBar } from "./TokenUsageBar.jsx";

test("shows an estimated input count while an LLM request is pending", () => {
  render(
    <TokenUsageBar
      tokenUsage={{
        total_input: 0,
        total_output: 0,
        pending_requests: 1,
        pending_input_tokens: 56_724,
        by_model: {},
      }}
      tokenExpanded={false}
    />,
  );

  expect(screen.getByText("≈56.7K input pending")).toBeTruthy();
  expect(screen.queryByText("No usage data yet")).toBeNull();
});

test("shows uncached input in totals and model details without changing cost", () => {
  render(
    <TokenUsageBar
      tokenExpanded
      tokenUsage={{
        total_input: 450,
        total_uncached_input: 100,
        total_output: 20,
        total_cache_read: 300,
        total_cache_write: 50,
        estimated_cost_available: true,
        estimated_total_cost_usd: 1.25,
        by_model: {
          grok: {
            provider: "bedrock",
            input: 450,
            uncached_input: 100,
            output: 20,
            cache_read: 300,
            cache_write: 50,
          },
        },
      }}
    />,
  );
  expect(screen.getByText("↑100 in")).toBeTruthy();
  expect(screen.getByText("↑100")).toBeTruthy();
  expect(screen.getByText("⚡300 cached")).toBeTruthy();
  expect(screen.getByText("✎50 written")).toBeTruthy();
  expect(screen.getByText("≈$1.25 est. cost")).toBeTruthy();
  expect(screen.queryByText("↑450 in")).toBeNull();
});

test("keeps cached-only usage visible with zero uncached input", () => {
  render(
    <TokenUsageBar
      tokenExpanded
      tokenUsage={{
        total_input: 0,
        total_uncached_input: 0,
        total_output: 0,
        total_cache_read: 300,
        total_cache_write: 0,
        by_model: { claude: { input: 0, uncached_input: 0, cache_read: 300 } },
      }}
    />,
  );
  expect(screen.getByText("↑0 in")).toBeTruthy();
  expect(screen.getByText("↑0")).toBeTruthy();
  expect(screen.getByText("⚡300 cached")).toBeTruthy();
  expect(screen.queryByText("No usage data yet")).toBeNull();
});
