import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import { CoverageView } from "./CoverageView.jsx";

const workProgram = {
  files: { total: 4, directly_opened: 2 },
  code_graph: {
    files_parsed: 3,
    languages: { c_sharp: 2, typescript: 1 },
    functions: 12,
    calls: 40,
    resolved_calls: 10,
    sink_reachability: { reachable: 6, no_callers: 1, unknown: 1 },
    sink_matches_outside_calls: 2,
  },
};

test("shows parsed code counts and risky calls by reachability", () => {
  render(<CoverageView coverage={{}} workProgram={workProgram} />);
  const panel = screen.getByRole("region", { name: "Code map" });
  expect(within(panel).getByText("C# 2 · TypeScript 1")).toBeTruthy();
  expect(within(panel).getByText("12")).toBeTruthy();
  expect(within(panel).getByText("10 (25%)")).toBeTruthy();
  expect(within(panel).getByText("6/8")).toBeTruthy();
  expect(within(panel).getByText("No callers").closest("[title]").title).toMatch(/framework/);
  expect(within(panel).getAllByText("1/8")).toHaveLength(2);
  expect(within(panel).queryByText("Not reached")).toBeNull();
  expect(within(panel).getByText(/2 matches in comments or strings were skipped/)).toBeTruthy();
});

test("explains when no files could be parsed", () => {
  render(
    <CoverageView
      coverage={{}}
      workProgram={{ files: {}, code_graph: { files_parsed: 0, sink_reachability: {} } }}
    />,
  );
  expect(screen.getByText(/Risky calls were found by text search only/)).toBeTruthy();
});

test("hides the code map for runs without one", () => {
  render(<CoverageView coverage={{}} workProgram={{ files: {} }} />);
  expect(screen.queryByRole("region", { name: "Code map" })).toBeNull();
});
