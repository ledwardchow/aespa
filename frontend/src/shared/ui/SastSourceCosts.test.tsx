import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { getSastSourceCosts } from "../api/sastSourceCosts";
import { SastSourceCosts } from "./SastSourceCosts";

vi.mock("../api/sastSourceCosts", () => ({ getSastSourceCosts: vi.fn() }));

afterEach(() => vi.clearAllMocks());

test("does not show a SAST cost error before any source is known", async () => {
  vi.mocked(getSastSourceCosts).mockRejectedValue(new Error("Leads unavailable"));

  await act(async () => {
    render(<SastSourceCosts runId={10} />);
  });

  expect(getSastSourceCosts).toHaveBeenCalledOnce();
  expect(screen.queryByText("Could not load SAST costs")).toBeNull();
});
