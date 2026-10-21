import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  sitesApi.getSiteHeader.mockResolvedValue({
    id: site.id,
    name: site.name,
    base_url: site.base_url,
    requires_auth: site.requires_auth,
    credential_count: 0,
  });
  settingsApi.listLLMProfiles.mockResolvedValue([]);
  settingsApi.getBrowserDebugConfig.mockResolvedValue({});
});

test("shows a Deep badge beside runs started in Deep mode", async () => {
  sitesApi.listSiteRunsPage.mockResolvedValue({
    items: [
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
    ],
    total: 2,
  });

  render(<SiteDetail siteId={site.id} />);

  const deepRow = (await screen.findByText("Deep checkout scan")).closest("tr");
  const standardRow = screen.getByText("Standard checkout scan").closest("tr");

  expect(within(deepRow).getByText("Deep")).toBeTruthy();
  expect(within(standardRow).queryByText("Deep")).toBeNull();
});

test("shows the site's address and login summary in the header", async () => {
  sitesApi.getSite.mockResolvedValue({
    ...site,
    requires_auth: true,
    credentials: [{ id: 8, label: "Admin account", auth_mode: "form", login_fields: [] }],
  });
  sitesApi.getSiteHeader.mockResolvedValue({
    id: site.id,
    name: site.name,
    base_url: site.base_url,
    requires_auth: true,
    credential_count: 1,
  });

  render(<SiteDetail siteId={site.id} />);

  expect(await screen.findByText("https://example.test")).toBeTruthy();
  expect(screen.getByText("Login required")).toBeTruthy();
  expect(screen.getByText("1 account")).toBeTruthy();
  const tabs = screen.getByRole("tablist", { name: "Site views" });
  expect(within(tabs).getByRole("tab", { name: "Test runs" }).getAttribute("aria-selected")).toBe(
    "true",
  );
});

test("edits the site on the Site details tab and stays on the page", async () => {
  const user = userEvent.setup();
  sitesApi.updateSite.mockImplementation(async (_id, payload) => ({
    ...site,
    ...payload,
    credentials: [],
  }));

  render(<SiteDetail siteId={site.id} initialTab="details" />);

  const name = await screen.findByLabelText("Name");
  await user.clear(name);
  await user.type(name, "Renamed");
  expect(screen.getByText("Unsaved changes")).toBeTruthy();

  await user.click(screen.getByRole("button", { name: "Save changes" }));

  expect(sitesApi.updateSite).toHaveBeenCalledWith(
    site.id,
    expect.objectContaining({ name: "Renamed" }),
  );
  expect(await screen.findByText("Changes saved")).toBeTruthy();
  expect(screen.getByLabelText("Name").value).toBe("Renamed");
  expect(within(document.querySelector(".topbar")).getByText("Renamed")).toBeTruthy();
});

test("discards unsaved site changes", async () => {
  const user = userEvent.setup();
  sitesApi.getSite.mockResolvedValue({
    ...site,
    requires_auth: true,
    credentials: [{ id: 8, label: "Admin account", auth_mode: "form", login_fields: [] }],
  });

  render(<SiteDetail siteId={site.id} initialTab="details" />);

  const name = await screen.findByLabelText("Name");
  expect(screen.queryByText("Unsaved changes")).toBeNull();
  await user.type(name, " draft");
  await user.click(screen.getByRole("button", { name: "Discard changes" }));

  expect(screen.getByLabelText("Name").value).toBe("Example");
  expect(screen.queryByText("Unsaved changes")).toBeNull();
  expect(sitesApi.updateSite).not.toHaveBeenCalled();
});
