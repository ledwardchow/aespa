import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as sitesApi from "../../shared/api/sites.js";
import * as settingsApi from "../../shared/api/settings.js";
import { SiteRunsTab } from "./SiteRunsTab.jsx";

vi.mock("../../shared/api/sites.js");
vi.mock("../../shared/api/settings.js");
vi.mock("../../shared/hooks/useBenchmarkLinks.js", () => ({ useBenchmarkLinks: () => ({}) }));

beforeEach(() => {
  vi.clearAllMocks();
  settingsApi.listLLMProfiles.mockResolvedValue([]);
  sitesApi.listSiteRunsPage.mockImplementation(async (_siteId, { page }) => ({
    items: [
      {
        id: page,
        name: `Site run ${page}`,
        status: "complete",
        phase: "finished",
        thinking_status: "idle",
        pages_discovered: 3,
        created_at: "2026-10-01T00:00:00Z",
      },
    ],
    total: 26,
  }));
});

test("loads one site run page and changes page size", async () => {
  const user = userEvent.setup();
  render(<SiteRunsTab siteId={5} />);

  expect(await screen.findByText("Site run 1")).toBeTruthy();
  await user.selectOptions(screen.getByRole("combobox", { name: "Runs per page" }), "10");
  await user.click(screen.getByRole("button", { name: "Next" }));

  expect(await screen.findByText("Site run 2")).toBeTruthy();
  expect(sitesApi.listSiteRunsPage).toHaveBeenCalledWith(
    5,
    { page: 2, pageSize: 10, sortField: "created_at", sortDir: "desc" },
    expect.anything(),
  );
});
