import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as apiRunsApi from "../../shared/api/apiRuns.js";
import { ApiRunWorkProgramTab } from "./ApiRunWorkProgramTab.jsx";

vi.mock("../../shared/api/apiRuns.js", () => ({ getApiCoverageMatrix: vi.fn() }));

beforeEach(() => {
  window.location.hash = "#/";
});

test("API finding marker opens the filtered Findings tab", async () => {
  apiRunsApi.getApiCoverageMatrix.mockResolvedValue({
    categories: ["API1"],
    totals: { finding: 1 },
    endpoints: [
      {
        endpoint_id: 3,
        method: "GET",
        path: "/orders",
        auth_required: false,
        cells: {
          API1: { status: "finding", finding_ids: [41], cell_id: 8 },
        },
      },
    ],
  });
  const { container } = render(
    <ApiRunWorkProgramTab runId={9} run={{ name: "Orders" }} scanRunning={false} />,
  );
  await screen.findByText("/orders");
  await waitFor(() => expect(container.querySelector(".cov-cell.has-findings")).toBeTruthy());
  fireEvent.click(container.querySelector(".cov-cell.has-findings"));
  expect(window.location.hash).toContain("#/api-runs/9/findings?");
  expect(window.location.hash).toContain("finding_ids=41");
  expect(window.location.hash).toContain("from=coverage");
});
