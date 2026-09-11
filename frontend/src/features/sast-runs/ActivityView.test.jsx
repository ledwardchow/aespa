import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ActivityView } from "./ActivityView.jsx";

const baseProps = {
  logs: [],
  scanRunning: true,
  tokenUsage: null,
  tokenExpanded: false,
  setTokenExpanded: vi.fn(),
  runId: 14,
  analysisMode: "deep",
};

test("shows the SAST agent roster by default and expands worker history", () => {
  render(
    <ActivityView
      {...baseProps}
      agentLog={[
        {
          id: 1,
          agent_id: "sast-worker-4",
          role: "SAST Injection Worker",
          status: "spawned",
          current_task: "Queued analysis worker routes:injection",
          display_name: "routes:injection",
          class_group: "injection",
          created_at: "2026-09-11T01:00:00Z",
        },
        {
          id: 2,
          agent_id: "sast-worker-4",
          role: "SAST Injection Worker",
          status: "active",
          current_task: "Reviewing 8 assigned checks",
          display_name: "routes:injection",
          class_group: "injection",
          created_at: "2026-09-11T01:00:01Z",
        },
      ]}
    />,
  );

  expect(screen.getByText("Threat Modeller")).toBeTruthy();
  expect(screen.getByText("SAST Analyst")).toBeTruthy();
  expect(screen.getByText("Injection Workers")).toBeTruthy();
  expect(screen.getByText("routes:injection")).toBeTruthy();

  fireEvent.click(screen.getByText("routes:injection"));
  expect(screen.getByText("Queued analysis worker routes:injection")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Injection ●" }));
  expect(screen.getByText("routes:injection")).toBeTruthy();
  expect(screen.queryByText("Threat Modeller")).toBeNull();
});

test("keeps the phase log on a separate tab", () => {
  render(
    <ActivityView
      {...baseProps}
      scanRunning={false}
      agentLog={[]}
      logs={[
        {
          id: 1,
          phase: "scope",
          message: "Source scope ready.",
          created_at: "2026-09-11T01:00:00Z",
        },
      ]}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Log" }));
  expect(screen.getByText("Source scope ready.")).toBeTruthy();
  expect(screen.getByText("1 entries")).toBeTruthy();
});
