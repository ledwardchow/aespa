import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import { BenchmarkFindingReview } from "./BenchmarkFindingReview.jsx";

vi.mock("../../shared/api/benchmarkLab.js");
beforeEach(() => vi.clearAllMocks());

const result = {
  id: 8,
  ground_truth: {
    items: [
      { external_id: "GT-1", title: "Full match", category: "A03", severity: "high" },
      { external_id: "GT-2", title: "Partial match", category: "A01", severity: "medium" },
      { external_id: "GT-3", title: "Missing match", category: "A01", severity: "critical" },
    ],
  },
  rows: [
    { external_id: "GT-1", disposition: "full", finding_ids: [10], reason: "Confirmed" },
    { external_id: "GT-2", disposition: "partial", finding_ids: [10], reason: "Some evidence" },
    { external_id: "GT-3", disposition: "missing", finding_ids: [], reason: "No evidence" },
  ],
  findings: [{ id: 10, reference: "SITE-010", title: "Scan match" }],
};

test("puts missing and partial findings first, then filters and reviews a finding", async () => {
  const user = userEvent.setup();
  const onSaved = vi.fn();
  benchmarkApi.reviewBenchmarkResult.mockResolvedValue(result);
  render(<BenchmarkFindingReview result={result} onSaved={onSaved} />);
  const list = screen.getByLabelText("Ground truth findings");
  expect(
    within(list)
      .getAllByRole("button")
      .map((button) => button.textContent),
  ).toEqual(["GT-3missingMissing match", "GT-2partialPartial match", "GT-1fullFull match"]);
  expect(screen.getByRole("region", { name: "Finding review" }).textContent).toContain(
    "No evidence",
  );
  await user.selectOptions(screen.getByLabelText("Result"), "partial");
  expect(within(list).getAllByRole("button")).toHaveLength(1);
  await user.selectOptions(screen.getByLabelText("Result"), "all");
  await user.selectOptions(screen.getByLabelText("Group by"), "category");
  expect(within(list).getByRole("heading", { name: "A01 (2)" })).toBeTruthy();
  await user.type(screen.getByLabelText("Search findings"), "GT-2");
  expect(within(list).getAllByRole("button")).toHaveLength(1);
  await user.click(screen.getByRole("button", { name: "Review result" }));
  await user.selectOptions(
    screen.getByLabelText("Result", { selector: ".benchmark-review-form select" }),
    "full",
  );
  await user.type(screen.getByLabelText("Reason"), "Reviewed evidence");
  await user.click(screen.getByRole("button", { name: "Save review" }));
  expect(benchmarkApi.reviewBenchmarkResult).toHaveBeenCalledWith(8, "GT-2", {
    disposition: "full",
    finding_ids: [10],
    note: "Reviewed evidence",
  });
  expect(onSaved).toHaveBeenCalledWith(result);
});

test("clears an unfinished review when filters change and groups severity in risk order", async () => {
  const user = userEvent.setup();
  render(<BenchmarkFindingReview result={result} onSaved={vi.fn()} />);
  await user.click(screen.getByRole("button", { name: "Review result" }));
  await user.selectOptions(
    screen.getByLabelText("Result", { selector: ".benchmark-review-form select" }),
    "full",
  );
  await user.selectOptions(screen.getByLabelText("Group by"), "severity");
  expect(screen.queryByRole("button", { name: "Save review" })).toBeNull();
  const headings = within(screen.getByLabelText("Ground truth findings"))
    .getAllByRole("heading", { level: 4 })
    .map((heading) => heading.textContent);
  expect(headings).toEqual(["critical (1)", "high (1)", "medium (1)"]);
  expect(benchmarkApi.reviewBenchmarkResult).not.toHaveBeenCalled();
});
