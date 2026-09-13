import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { ActivityDeepQueue } from "./ActivityDeepQueue.jsx";

vi.mock("../../shared/api/webRuns.js", () => ({ getDeepQueue: vi.fn() }));

const groupedTask = {
  id: 119,
  source: "coverage",
  task_kind: "operation",
  attack_class: "business_logic",
  status: "queued",
  title: "Test GET https://target.test/api/accounts/{id}",
  http_method: "GET",
  target_url: "https://target.test/api/accounts/12?search=Ada",
  route_template: "https://target.test/api/accounts/{id}",
  inputs: ["account_id", "search"],
  identities: ["authenticated_vs_anonymous"],
  finding_count: 0,
  priority: 9,
  checks: [
    {
      id: 1,
      attack_class: "idor",
      owasp_category: "A01",
      parameter: "account_id",
      session_label: "authenticated_vs_anonymous",
      status: "queued",
      hypothesis: "Compare ownership across two users.",
    },
    {
      id: 2,
      attack_class: "sqli",
      owasp_category: "A03",
      parameter: "search",
      status: "queued",
      hypothesis: "Compare a quote probe with the baseline.",
    },
  ],
};

test("shows one operation task with counts and expandable checks", async () => {
  webRunsApi.getDeepQueue.mockResolvedValue({
    total: 1,
    checks_total: 2,
    counts: { queued: 1 },
    tasks: [groupedTask],
  });

  render(<ActivityDeepQueue runId={232} thinkingStatus={{ status: "complete" }} />);

  await waitFor(() => expect(webRunsApi.getDeepQueue).toHaveBeenCalledWith(232));
  expect(screen.getAllByText("2 checks")).toHaveLength(2);
  expect(screen.getByText("2 inputs")).toBeTruthy();
  expect(screen.getByText("1 identity comparison")).toBeTruthy();
  expect(screen.queryByText("Compare ownership across two users.")).toBeNull();

  fireEvent.click(screen.getByRole("button", { expanded: false }));

  expect(screen.getByText("Compare ownership across two users.")).toBeTruthy();
  expect(screen.getByText("Compare: authenticated vs anonymous")).toBeTruthy();
  expect(screen.getByText("search")).toBeTruthy();
});

test("labels finished tasks as complete and keeps finding counts on the task row", async () => {
  webRunsApi.getDeepQueue.mockResolvedValue({
    total: 1,
    checks_total: 2,
    counts: { finding: 1 },
    tasks: [{ ...groupedTask, status: "finding", finding_count: 2 }],
  });

  render(<ActivityDeepQueue runId={232} thinkingStatus={{ status: "complete" }} />);

  await waitFor(() => expect(webRunsApi.getDeepQueue).toHaveBeenCalledWith(232));
  expect(screen.getByText("Complete")).toBeTruthy();
  expect(screen.getAllByText("2 findings")).toHaveLength(2);
});
