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
  variants: [
    {
      id: 7,
      kind: "baseline",
      strategy: "baseline",
      status: "complete",
      purpose: "Reuse the captured request as the tester baseline.",
      current_purpose: "Reuse the captured request as the tester baseline.",
      difference: "Records normal behaviour.",
      identities: [],
      finding_count: 0,
      pivot_history: [],
    },
    {
      id: 8,
      kind: "planned",
      strategy: "idor",
      status: "queued",
      purpose: "Compare object access across two users.",
      current_purpose: "Compare object access across two users.",
      difference: "Focuses on cross-user ownership.",
      identities: ["user_a_vs_user_b"],
      finding_count: 0,
      pivot_history: [],
    },
  ],
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
    variants_total: 2,
    planning: { total: 1, complete: 0, active: 1, pending: 0 },
    counts: { queued: 1 },
    tasks: [groupedTask],
  });

  render(<ActivityDeepQueue runId={232} thinkingStatus={{ status: "complete" }} />);

  await waitFor(() => expect(webRunsApi.getDeepQueue).toHaveBeenCalledWith(232));
  expect(screen.getAllByText("2 checks")).toHaveLength(2);
  expect(screen.getByText("Tester 1 · operation")).toBeTruthy();
  expect(screen.queryByText("#119 operation")).toBeNull();
  expect(screen.getByText("0/1 planned")).toBeTruthy();
  expect(screen.getByText("1 planning now")).toBeTruthy();
  expect(screen.getByText("2 inputs")).toBeTruthy();
  expect(screen.getAllByText("2 variants")).toHaveLength(2);
  expect(screen.getByText("1 identity comparison")).toBeTruthy();
  expect(screen.queryByText("Compare ownership across two users.")).toBeNull();

  fireEvent.click(screen.getByRole("button", { expanded: false }));

  expect(screen.getByText("Compare ownership across two users.")).toBeTruthy();
  expect(screen.getByText("Compare: authenticated vs anonymous")).toBeTruthy();
  expect(screen.getByText("search")).toBeTruthy();
  expect(screen.getByText("Compare object access across two users.")).toBeTruthy();
  expect(screen.getByText("Identity: user a vs user b")).toBeTruthy();
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
