import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as api from "../../shared/api/apiCollections.js";
import { ApiCollectionDetail } from "./ApiCollectionDetail.jsx";

vi.mock("../../shared/api/apiCollections.js");
vi.mock("../../shared/hooks/useBenchmarkLinks.js", () => ({ useBenchmarkLinks: () => ({}) }));

beforeEach(() => {
  vi.clearAllMocks();
  api.getApiCollection.mockResolvedValue({
    id: 8,
    name: "Orders API",
    base_url: "https://api.example",
  });
  api.listApiRunsPage.mockImplementation(async (_collectionId, { page }) => ({
    items: [
      {
        id: page,
        name: `API run ${page}`,
        status: "completed",
        coverage_mode: "track",
        created_at: "2026-10-01T00:00:00Z",
      },
    ],
    total: 26,
  }));
});

test("loads only API runs on the run tab and changes page size", async () => {
  const user = userEvent.setup();
  render(<ApiCollectionDetail collectionId={8} initialTab="runs" />);

  expect(await screen.findByText("API run 1")).toBeTruthy();
  expect(api.listApiEndpoints).not.toHaveBeenCalled();
  expect(api.listApiCredentials).not.toHaveBeenCalled();
  expect(api.getApiReadiness).not.toHaveBeenCalled();
  await user.selectOptions(screen.getByRole("combobox", { name: "Runs per page" }), "10");
  await user.click(screen.getByRole("button", { name: "Next" }));

  expect(await screen.findByText("API run 2")).toBeTruthy();
  expect(api.listApiRunsPage).toHaveBeenCalledWith(
    8,
    { page: 2, pageSize: 10, sortField: "created_at", sortDir: "desc" },
    expect.anything(),
  );
});

test("loads endpoint data only when the Endpoints tab is open", async () => {
  api.listApiEndpoints.mockResolvedValue([]);
  api.getApiReadiness.mockResolvedValue({ status: "not_assessed" });
  render(<ApiCollectionDetail collectionId={8} initialTab="endpoints" />);

  expect(await screen.findByText("No endpoints yet")).toBeTruthy();
  expect(api.listApiEndpoints).toHaveBeenCalledWith(8);
  expect(api.getApiReadiness).toHaveBeenCalledWith(8);
  expect(api.listApiRunsPage).not.toHaveBeenCalled();
  expect(api.listApiCredentials).not.toHaveBeenCalled();
});
