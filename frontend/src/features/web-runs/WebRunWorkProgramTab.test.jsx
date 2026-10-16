import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { useEventStream } from "../../shared/hooks/useEventStream.js";
import { WebRunWorkProgramTab } from "./WebRunWorkProgramTab.jsx";

vi.mock("../../shared/api/webRuns.js", () => ({
  getWebCoverageMatrix: vi.fn(),
  getWorkflowCoverage: vi.fn(),
}));
vi.mock("../../shared/hooks/useEventStream.js", () => ({ useEventStream: vi.fn() }));

beforeEach(() => {
  window.location.hash = "#/";
  window.dispatchEvent(new Event("hashchange"));
});

test("does not report grouped display totals as completion when root progress is missing", async () => {
  webRunsApi.getWebCoverageMatrix.mockResolvedValue({
    seeded: true,
    pages: [],
    column_totals: { covered: 1 },
  });
  webRunsApi.getWorkflowCoverage.mockResolvedValue({ items: [] });
  render(<WebRunWorkProgramTab runId={7} run={{ name: "Shop" }} scanRunning={false} />);
  expect(await screen.findByText("Coverage unavailable")).toBeTruthy();
  expect(screen.queryByText(/100% coverage/)).toBeNull();
});

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

  const panel = await screen.findByRole("tabpanel", { name: "Workflow coverage" });
  expect(within(panel).getByText("2 of 3 checks covered, 1 blocked.")).toBeTruthy();
  expect(within(panel).getByText("Place an order")).toBeTruthy();
  expect(within(panel).getByText("View another order")).toBeTruthy();
  expect(within(panel).getAllByText("https://shop.test/orders")).toHaveLength(2);
  expect(
    within(panel)
      .getAllByRole("columnheader")
      .map((th) => th.textContent),
  ).toEqual(["Workflow", "A01Access Control", "A04Insecure Design"]);
  expect(within(panel).queryByText("Reached")).toBeNull();
  expect(within(panel).queryByText("Needs input")).toBeNull();
  expect(within(panel).queryByText("Not reached")).toBeNull();

  fireEvent.click(within(panel).getByRole("button", { name: "A04 Place an order: Passed" }));
  expect(
    within(panel).getByText("The order was rejected after the payment step was skipped."),
  ).toBeTruthy();

  fireEvent.click(within(panel).getByRole("button", { name: "A01 View another order: Blocked" }));
  expect(within(panel).getByText("A second account is required.")).toBeTruthy();

  fireEvent.click(
    within(panel).getByRole("button", { name: "A01 Change shipping address: Finding" }),
  );
  expect(window.location.hash).toContain("#/runs/7/findings?");
  expect(window.location.hash).toContain("finding_ids=31");
  expect(window.location.hash).toContain("from=workflows");
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

test("shows a workflow awaiting crawl with no security checks", async () => {
  webRunsApi.getWebCoverageMatrix.mockResolvedValue({ seeded: true, pages: [], totals: {} });
  webRunsApi.getWorkflowCoverage.mockResolvedValue({
    items: [],
    workflows: [
      {
        workflow_key: "note:24",
        name: "Payment setup",
        goal: "Add a payment method",
        url: "https://shop.test/account",
        crawl_status: "needs_input",
      },
      {
        workflow_key: "note:25",
        name: "Apply a discount",
        crawl_status: "not_reached",
      },
    ],
  });
  render(<WebRunWorkProgramTab runId={9} run={{ name: "Shop" }} scanRunning={false} />);
  fireEvent.click(screen.getByRole("tab", { name: "Workflows" }));
  const panel = await screen.findByRole("tabpanel", { name: "Workflow coverage" });
  const paymentRow = within(panel).getByText("Payment setup").closest("tr");
  const discountRow = within(panel).getByText("Apply a discount").closest("tr");
  expect(within(paymentRow).getByText("Needs input")).toBeTruthy();
  expect(within(discountRow).getByText("Not reached")).toBeTruthy();
  expect(within(paymentRow).getAllByText("Awaiting crawl")).toHaveLength(10);
  expect(within(discountRow).getAllByText("Awaiting crawl")).toHaveLength(10);
  expect(within(panel).queryByRole("columnheader", { name: "Crawl progress" })).toBeNull();
  expect(within(panel).queryByRole("columnheader", { name: "Security testing" })).toBeNull();
  expect(within(panel).queryByText("No workflows identified yet.")).toBeNull();
});

test("keeps a previously tested category awaiting crawl when the workflow is unreached", async () => {
  webRunsApi.getWebCoverageMatrix.mockResolvedValue({ seeded: true, pages: [], totals: {} });
  webRunsApi.getWorkflowCoverage.mockResolvedValue({
    items: [
      {
        id: 42,
        workflow_key: "note:24",
        owasp_category: "A01",
        test_kind: "access",
        status: "finding",
        finding_ids: [31],
      },
    ],
    workflows: [{ workflow_key: "note:24", name: "Payment setup", crawl_status: "needs_input" }],
  });

  render(<WebRunWorkProgramTab runId={9} run={{ name: "Shop" }} scanRunning={false} />);
  fireEvent.click(screen.getByRole("tab", { name: "Workflows" }));
  const panel = await screen.findByRole("tabpanel", { name: "Workflow coverage" });
  const row = within(panel).getByText("Payment setup").closest("tr");
  expect(within(row).getByText("Needs input")).toBeTruthy();
  expect(within(row).getByText("Awaiting crawl")).toBeTruthy();
  expect(within(row).queryByRole("button", { name: /A01 Payment setup/ })).toBeNull();
});

test("page finding marker opens the filtered Findings tab", async () => {
  webRunsApi.getWebCoverageMatrix.mockResolvedValue({
    seeded: true,
    columns: [{ key: "A01", category: "A01", label: "Access Control" }],
    pages: [
      {
        page_id: 3,
        page_ids: [3],
        url: "https://shop.test/account",
        state_label: "Account",
        cells: {
          A01: { status: "finding", finding_ids: [31, 32], cell_ids: [8] },
        },
      },
    ],
    totals: { finding: 1 },
  });
  webRunsApi.getWorkflowCoverage.mockResolvedValue({ items: [] });
  const { container } = render(
    <WebRunWorkProgramTab runId={7} run={{ name: "Shop" }} scanRunning={false} />,
  );
  await screen.findByRole("tabpanel", { name: "Page coverage" });
  await waitFor(() => expect(container.querySelector(".cov-cell.has-findings")).toBeTruthy());
  fireEvent.click(container.querySelector(".cov-cell.has-findings"));
  expect(window.location.hash).toContain("#/runs/7/findings?");
  expect(window.location.hash).toContain("finding_ids=31%2C32");
  expect(window.location.hash).toContain("from=coverage");
});

test("shows page progress only on the Pages view", async () => {
  webRunsApi.getWebCoverageMatrix.mockResolvedValue({ seeded: true, pages: [], totals: {} });
  webRunsApi.getWorkflowCoverage.mockResolvedValue({ items: [] });

  render(
    <WebRunWorkProgramTab
      runId={9}
      run={{ name: "Shop" }}
      scanRunning={false}
      pagesProgress={<div>Page progress</div>}
    />,
  );

  expect(await screen.findByText("Page progress")).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: "Workflows" }));
  await screen.findByRole("tabpanel", { name: "Workflow coverage" });
  expect(screen.queryByText("Page progress")).toBeNull();
  fireEvent.click(screen.getByRole("tab", { name: "Pages" }));
  expect(await screen.findByText("Page progress")).toBeTruthy();
});

test("keeps a finding visible while another selected access check is pending", async () => {
  const matrix = {
    seeded: true,
    columns: [{ key: "A01", category: "A01", label: "Access Control" }],
    completion: { exercised_units: 1, applicable_units: 2, resolved_units: 1, target_met: false },
    column_totals: { finding: 1 },
    pages: [
      {
        page_id: 3,
        page_ids: [3, 4],
        url: "https://shop.test/orders?id={id}",
        cells: {
          A01: {
            status: "finding",
            finding_ids: [31],
            cell_ids: [8],
            selected_checks: {
              tested: 1,
              total: 2,
              unresolved: 1,
              items: [
                {
                  id: 1,
                  url: "https://shop.test/orders?id=101",
                  method: "GET",
                  baseline_actor: "Alice",
                  comparison_actor: "Bob",
                  status: "finding",
                  finding_ids: [31],
                  crawled: true,
                },
                {
                  id: 2,
                  url: "https://shop.test/orders?id=202",
                  method: "GET",
                  baseline_actor: "Bob",
                  comparison_actor: "Alice",
                  status: "queued",
                  finding_ids: [],
                  crawled: false,
                },
              ],
            },
          },
        },
      },
    ],
  };
  webRunsApi.getWebCoverageMatrix.mockResolvedValue(matrix);
  webRunsApi.getWorkflowCoverage.mockResolvedValue({ items: [] });
  const { container } = render(
    <WebRunWorkProgramTab runId={7} run={{ name: "Shop" }} scanRunning />,
  );
  expect(await screen.findByText("50% coverage (1/2 units)")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /1 \/ 2 tested/ }));
  const detail = screen.getByLabelText("Selected security checks");
  expect(within(detail).getByText("1 of 2 selected checks tested, 1 pending")).toBeTruthy();
  expect(within(detail).getByText("https://shop.test/orders?id=202")).toBeTruthy();
  expect(within(detail).getByText("Bob → Alice")).toBeTruthy();
  expect(within(detail).getByText("Pending")).toBeTruthy();
  const callsBefore = webRunsApi.getWebCoverageMatrix.mock.calls.length;
  useEventStream.mock.calls.at(-1)[1].onMessage({
    data: JSON.stringify({
      type: "coverage_update",
      page_id: 3,
      owasp_category: "A01",
      status: "finding",
    }),
  });
  await waitFor(() =>
    expect(webRunsApi.getWebCoverageMatrix.mock.calls.length).toBeGreaterThan(callsBefore),
  );
  expect(screen.getByText("1 pending")).toBeTruthy();
  fireEvent.click(container.querySelector(".cov-cell.has-findings"));
  expect(window.location.hash).toContain("finding_ids=31");
});
