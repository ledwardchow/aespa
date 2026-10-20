import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { RouteGroupsTable } from "./RouteGroupsPanel.jsx";

vi.mock("../../shared/api/webRuns.js", () => ({ getDiscoveredTargets: vi.fn() }));

beforeEach(() => vi.clearAllMocks());

test("opens a group and pages exact links without treating a sighting as access", async () => {
  const pattern = "https://shop.test/orders?id={id}";
  webRunsApi.getDiscoveredTargets
    .mockResolvedValueOnce({
      items: [
        {
          id: 1,
          url: "https://shop.test/orders?id=101&tag=a&tag=b",
          state_key: null,
          seen_by: [{ label: "Alice" }],
          crawled: false,
          access: [],
          selected_checks: [],
        },
      ],
      next_cursor: "after-101",
      total: 200,
      discovery_completeness: "recorded",
    })
    .mockResolvedValueOnce({
      items: [
        {
          id: 2,
          url: "https://shop.test/orders?id=202",
          state_key: "tab:details",
          seen_by: [{ label: "Bob" }],
          crawled: true,
          access: [{ label: "Bob", method: "GET", result: "reached" }],
          selected_checks: [{ id: 10 }],
        },
      ],
      next_cursor: null,
      total: 200,
      discovery_completeness: "recorded",
    });

  render(
    <RouteGroupsTable
      runId={7}
      groups={[{ label: "Orders", route_pattern: pattern, links_seen: 200, pages_sampled: 5 }]}
    />,
  );
  expect(webRunsApi.getDiscoveredTargets).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "View links" }));
  const links = await screen.findByLabelText(`Links for ${pattern}`);
  expect(webRunsApi.getDiscoveredTargets).toHaveBeenCalledWith(7, {
    routePattern: pattern,
    search: "",
    cursor: null,
  });
  expect(within(links).getByText("No direct access observed")).toBeTruthy();
  fireEvent.click(
    within(links).getByRole("button", { name: "https://shop.test/orders?id=101&tag=a&tag=b" }),
  );
  expect(within(links).getByText("No security check selected")).toBeTruthy();
  fireEvent.click(within(links).getByRole("button", { name: "Next" }));
  await waitFor(() =>
    expect(webRunsApi.getDiscoveredTargets).toHaveBeenLastCalledWith(7, {
      routePattern: pattern,
      search: "",
      cursor: "after-101",
    }),
  );
  expect(await within(links).findByText("Bob: GET reached")).toBeTruthy();
  expect(within(links).getByRole("button", { name: /orders\?id=202/ })).toBeTruthy();
});

test("searches the selected route from its first cursor", async () => {
  const pattern = "https://shop.test/orders?id={id}";
  webRunsApi.getDiscoveredTargets.mockResolvedValue({
    items: [],
    next_cursor: null,
    total: 0,
    discovery_completeness: "recorded",
  });
  render(
    <RouteGroupsTable
      runId={7}
      groups={[{ label: "Orders", route_pattern: pattern, links_seen: 200, pages_sampled: 5 }]}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "View links" }));
  fireEvent.change(await screen.findByPlaceholderText("URL or account"), {
    target: { value: "id=202" },
  });
  await waitFor(() =>
    expect(webRunsApi.getDiscoveredTargets).toHaveBeenCalledWith(7, {
      routePattern: pattern,
      search: "id=202",
      cursor: null,
    }),
  );
});

test("a rapid double click requests only the next link page", async () => {
  const pattern = "https://shop.test/orders?id={id}";
  let resolveNext;
  webRunsApi.getDiscoveredTargets
    .mockResolvedValueOnce({
      items: [{ id: 1, url: "https://shop.test/orders?id=101" }],
      next_cursor: "after-101",
      total: 100,
    })
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveNext = resolve;
        }),
    );

  render(
    <RouteGroupsTable
      runId={7}
      groups={[{ label: "Orders", route_pattern: pattern, links_seen: 100, pages_sampled: 5 }]}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "View links" }));
  const next = await screen.findByRole("button", { name: "Next" });
  fireEvent.click(next);
  fireEvent.click(next);

  await waitFor(() => expect(webRunsApi.getDiscoveredTargets).toHaveBeenCalledTimes(2));
  expect(webRunsApi.getDiscoveredTargets).toHaveBeenLastCalledWith(7, {
    routePattern: pattern,
    search: "",
    cursor: "after-101",
  });
  resolveNext({
    items: [{ id: 2, url: "https://shop.test/orders?id=202" }],
    next_cursor: null,
    total: 100,
  });
  expect(await screen.findByText("https://shop.test/orders?id=202")).toBeTruthy();
  expect(screen.getByText("51-51 of 100 links")).toBeTruthy();
});
