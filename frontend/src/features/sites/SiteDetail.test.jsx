import { render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import * as sitesApi from "../../shared/api/sites.js";
import { SiteDetail } from "./SiteDetail.jsx";

vi.mock("../../shared/api/settings.js");
vi.mock("../../shared/api/sites.js");

const site = {
  id: 4,
  name: "Example",
  base_url: "https://example.test",
  requires_auth: false,
  credentials: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  sitesApi.getSite.mockResolvedValue(site);
  settingsApi.listLLMProfiles.mockResolvedValue([]);
});

test("shows a Deep badge beside runs started in Deep mode", async () => {
  sitesApi.listRuns.mockResolvedValue([
    {
      id: 1,
      name: "Deep checkout scan",
      status: "complete",
      coverage_mode: "deep",
      pages_discovered: 12,
      created_at: "2026-09-14T01:00:00Z",
    },
    {
      id: 2,
      name: "Standard checkout scan",
      status: "complete",
      coverage_mode: "standard",
      pages_discovered: 12,
      created_at: "2026-09-14T02:00:00Z",
    },
  ]);

  render(<SiteDetail siteId={site.id} />);

  const deepRow = (await screen.findByText("Deep checkout scan")).closest("tr");
  const standardRow = screen.getByText("Standard checkout scan").closest("tr");

  expect(within(deepRow).getByText("Deep")).toBeTruthy();
  expect(within(standardRow).queryByText("Deep")).toBeNull();
});
