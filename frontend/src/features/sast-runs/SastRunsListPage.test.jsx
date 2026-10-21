import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";
import { SastRunsListPage } from "./SastRunsListPage.jsx";

vi.mock("../../shared/api/benchmarkLab.js");
vi.mock("../../shared/api/sastRuns.js");
vi.mock("../../shared/api/settings.js");

const run = {
  id: 17,
  name: "Checkout service",
  status: "completed",
  leads_count: 3,
  started_at: "2026-09-10T01:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  sastRunsApi.listSastRunsPage.mockResolvedValue({ items: [run], total: 1 });
  sastRunsApi.deleteSastRun.mockResolvedValue(undefined);
  settingsApi.listLLMProfiles.mockResolvedValue([]);
  benchmarkApi.listBenchmarkLinks.mockResolvedValue({ results: [], evaluations: [] });
  vi.stubGlobal(
    "confirm",
    vi.fn(() => true),
  );
});

afterEach(() => vi.unstubAllGlobals());

test("shows delete beside Open without a Linked scan column", async () => {
  render(<SastRunsListPage />);

  expect(await screen.findByRole("link", { name: "Open" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Delete" })).toBeTruthy();
  expect(screen.queryByRole("columnheader", { name: /Linked scan/ })).toBeNull();
});

test("confirms and deletes a SAST run from the list", async () => {
  const user = userEvent.setup();
  render(<SastRunsListPage />);

  await user.click(await screen.findByRole("button", { name: "Delete" }));

  expect(confirm).toHaveBeenCalledWith('Delete "Checkout service" and all its leads?');
  expect(sastRunsApi.deleteSastRun).toHaveBeenCalledWith(17);
});

test("tags new results and completed legacy evaluations without mixing scan types", async () => {
  sastRunsApi.listSastRunsPage.mockResolvedValue({
    items: [
      run,
      { ...run, id: 18, name: "Legacy scan" },
      { ...run, id: 19, name: "Unevaluated scan" },
    ],
    total: 3,
  });
  benchmarkApi.listBenchmarkLinks.mockResolvedValue({
    results: [
      { id: 4, run_kind: "sast", run_id: 17 },
      { id: 5, run_kind: "site", run_id: 19 },
      { id: 6, run_kind: "api", run_id: 19 },
    ],
    evaluations: [{ id: 7, sast_run_id: 18 }],
  });
  render(<SastRunsListPage />);
  const badges = await screen.findAllByRole("link", { name: "Evaluated" });
  expect(badges.map((badge) => badge.getAttribute("href"))).toEqual([
    "#/benchmark-lab/results/4",
    "#/benchmark-lab/evaluations/7",
  ]);
});

test("changes page size and loads the next page", async () => {
  const user = userEvent.setup();
  sastRunsApi.listSastRunsPage.mockImplementation(async ({ page }) => ({
    items: [{ ...run, id: page, name: `Scan ${page}` }],
    total: 26,
  }));
  render(<SastRunsListPage />);

  expect(await screen.findByText("Scan 1")).toBeTruthy();
  await user.selectOptions(screen.getByRole("combobox", { name: "Scans per page" }), "10");
  await user.click(screen.getByRole("button", { name: "Next" }));

  expect(await screen.findByText("Scan 2")).toBeTruthy();
  expect(sastRunsApi.listSastRunsPage).toHaveBeenCalledWith(
    { page: 2, pageSize: 10, sortField: "started_at", sortDir: "desc" },
    expect.anything(),
  );
});
