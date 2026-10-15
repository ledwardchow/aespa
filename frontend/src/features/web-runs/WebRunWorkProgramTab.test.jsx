import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { WebRunWorkProgramTab } from "./WebRunWorkProgramTab.jsx";

vi.mock("../../shared/api/webRuns.js", () => ({
  getWebCoverageMatrix: vi.fn(),
  getWorkflowCoverage: vi.fn(),
}));
vi.mock("../../shared/hooks/useEventStream.js", () => ({ useEventStream: vi.fn() }));

test("shows separate workflow checks for workflows that reach the same page", async () => {
  webRunsApi.getWebCoverageMatrix.mockResolvedValue({ seeded: true, pages: [], totals: {} });
  webRunsApi.getWorkflowCoverage.mockResolvedValue({
    items: [
      {
        id: 12,
        name: "Place an order",
        goal: "Complete checkout",
        reached_page_url: "https://shop.test/orders",
        owasp_category: "A04",
        test_kind: "sequence",
        status: "passed",
        evidence_summary: "The order was rejected after the payment step was skipped.",
        finding_ids: [],
      },
      {
        id: 13,
        name: "View another order",
        goal: "Open an order owned by a different account",
        reached_page_url: "https://shop.test/orders",
        owasp_category: "A01",
        test_kind: "ownership",
        status: "blocked",
        reason: "A second account is required.",
        finding_ids: [],
      },
      {
        id: 14,
        name: "Change shipping address",
        goal: "Change another account's saved address",
        reached_page_url: "https://shop.test/account/address",
        owasp_category: "A01",
        test_kind: "access",
        status: "finding",
        evidence_summary: "The other account's address changed.",
        finding_ids: [31],
      },
    ],
  });

  render(<WebRunWorkProgramTab runId={7} run={{ name: "Shop" }} scanRunning={false} />);

  await waitFor(() => expect(webRunsApi.getWorkflowCoverage).toHaveBeenCalledWith(7));
  fireEvent.click(screen.getByRole("tab", { name: "Workflows" }));

  const panel = screen.getByRole("tabpanel", { name: "Workflow coverage" });
  expect(within(panel).getByText("2 of 3 checks covered, 1 blocked.")).toBeTruthy();
  expect(within(panel).getByText("Place an order")).toBeTruthy();
  expect(within(panel).getByText("View another order")).toBeTruthy();
  expect(within(panel).getAllByText("https://shop.test/orders")).toHaveLength(2);
  expect(
    within(panel)
      .getAllByRole("columnheader")
      .map((th) => th.textContent),
  ).toEqual(["Workflow", "A01Access Control", "A04Insecure Design"]);

  fireEvent.click(within(panel).getByRole("button", { name: "A04 Place an order: Passed" }));
  expect(
    within(panel).getByText("The order was rejected after the payment step was skipped."),
  ).toBeTruthy();

  fireEvent.click(within(panel).getByRole("button", { name: "A01 View another order: Blocked" }));
  expect(within(panel).getByText("A second account is required.")).toBeTruthy();

  fireEvent.click(
    within(panel).getByRole("button", { name: "A01 Change shipping address: Finding" }),
  );
  expect(within(panel).getByText("#31")).toBeTruthy();
  expect(screen.queryByText("Populate from Site Map")).toBeNull();
});

test("shows a workflow coverage load error in its tab", async () => {
  webRunsApi.getWebCoverageMatrix.mockResolvedValue({ seeded: true, pages: [], totals: {} });
  webRunsApi.getWorkflowCoverage.mockRejectedValue(new Error("Request failed"));

  render(<WebRunWorkProgramTab runId={8} run={{ name: "Shop" }} scanRunning={false} />);
  fireEvent.click(screen.getByRole("tab", { name: "Workflows" }));

  const panel = await screen.findByRole("tabpanel", { name: "Workflow coverage" });
  await waitFor(() =>
    expect(within(panel).getByRole("alert").textContent).toContain("Request failed"),
  );
});
