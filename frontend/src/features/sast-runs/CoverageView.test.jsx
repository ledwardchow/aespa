import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

test("browses nested folders and shows direct read totals", async () => {
  const user = userEvent.setup();
  render(
    <CoverageView
      coverage={{
        files: [
          { path: "README.md", language: "Other", read_count: 1, reviewed: true },
          { path: "app/account/Profile.tsx", language: "tsx", read_count: 3, reviewed: true },
          { path: "app/account/Settings.tsx", language: "tsx", read_count: 0, reviewed: false },
          { path: "app/routes.ts", language: "typescript", read_count: 2, reviewed: true },
        ],
      }}
    />,
  );

  expect(screen.getByText("README.md")).toBeTruthy();
  expect(screen.queryByText("Profile.tsx")).toBeNull();
  const app = screen.getByRole("button", { name: "Expand app" });
  expect(app.getAttribute("aria-expanded")).toBe("false");
  expect(app.closest(".sast-file-row").textContent).toContain("2/3 opened");
  expect(app.closest(".sast-file-row").textContent).toContain("5");

  await user.click(app);
  expect(screen.getByText("routes.ts")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Expand app/account" }));
  expect(screen.getByText("Profile.tsx")).toBeTruthy();
  expect(screen.getByText("Settings.tsx").closest(".sast-file-row").textContent).toContain(
    "Not opened",
  );
  expect(screen.getByText("Profile.tsx").closest(".sast-file-row").textContent).toContain("3");
  await user.click(screen.getByRole("button", { name: "Collapse app" }));
  expect(screen.queryByText("Profile.tsx")).toBeNull();
});

test("searches all inventoried files and keeps matching folders visible", async () => {
  const user = userEvent.setup();
  const files = Array.from({ length: 260 }, (_, index) => ({
    path: `src/file-${index}.ts`,
    language: "typescript",
    read_count: 0,
    reviewed: false,
  }));
  render(<CoverageView coverage={{ files }} />);
  await user.type(screen.getByRole("searchbox", { name: "Find a file or folder" }), "file-259");
  expect(screen.getByText("file-259.ts")).toBeTruthy();
  expect(screen.queryByText("file-258.ts")).toBeNull();
  expect(screen.getByText("src")).toBeTruthy();
  await user.clear(screen.getByRole("searchbox", { name: "Find a file or folder" }));
  expect(screen.getByRole("button", { name: "Expand src" })).toBeTruthy();
});
