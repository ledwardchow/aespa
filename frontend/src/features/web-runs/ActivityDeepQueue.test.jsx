import { render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { ActivityDeepQueue } from "./ActivityDeepQueue.jsx";

vi.mock("../../shared/api/webRuns.js", () => ({
  getDeepQueue: vi.fn(),
}));

test("shows the input and identity comparison that distinguish Deep queue tasks", async () => {
  webRunsApi.getDeepQueue.mockResolvedValue({
    total: 2,
    counts: { queued: 2 },
    tasks: [
      {
        id: 119,
        attack_class: "sqli",
        status: "queued",
        title: "sqli on https://target.test/dashboard",
        http_method: "GET",
        target_url: "https://target.test/dashboard",
        parameter: "avatar-url",
        session_label: null,
        priority: 9,
      },
      {
        id: 126,
        attack_class: "auth_bypass",
        status: "queued",
        title: "auth vs unauth on https://target.test/dashboard",
        http_method: "GET",
        target_url: "https://target.test/dashboard",
        parameter: null,
        session_label: "authenticated_vs_anonymous",
        priority: 9,
      },
    ],
  });

  render(<ActivityDeepQueue runId={232} thinkingStatus={{ status: "complete" }} />);

  await waitFor(() => expect(webRunsApi.getDeepQueue).toHaveBeenCalledWith(232));
  expect(screen.getByText("avatar-url")).toBeTruthy();
  expect(screen.getByText("Compare: authenticated vs anonymous")).toBeTruthy();
});
