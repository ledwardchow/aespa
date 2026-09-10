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
