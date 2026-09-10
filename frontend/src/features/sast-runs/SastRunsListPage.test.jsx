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
  sastRunsApi.listAllSastRuns.mockResolvedValue([run]);
  sastRunsApi.deleteSastRun.mockResolvedValue(undefined);
  settingsApi.listLLMProfiles.mockResolvedValue([]);
  settingsApi.getBenchmarkLabConfig.mockResolvedValue({ panel_enabled: false });
  benchmarkApi.listBenchmarkEvaluations.mockResolvedValue([]);
  vi.stubGlobal(
    "confirm",
    vi.fn(() => true),
  );
});

afterEach(() => vi.unstubAllGlobals());

test("shows delete beside View without a Linked scan column", async () => {
  render(<SastRunsListPage />);

  expect(await screen.findByRole("link", { name: "View →" })).toBeTruthy();
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
