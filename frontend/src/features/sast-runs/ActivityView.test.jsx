import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";

import { ActivityView } from "./ActivityView.jsx";

const baseProps = {
  logs: [],
  scanRunning: true,
  runId: 14,
  analysisMode: "deep",
};

beforeEach(() => {
  window.location.hash = "#/sast-runs/14/activity";
});

test("shows the SAST agent roster by default and expands worker history", async () => {
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
  await waitFor(() => expect(screen.queryByText("Threat Modeller")).toBeNull());
  expect(window.location.hash).toBe("#/sast-runs/14/activity?subtab=injection");
});

test("keeps the phase log on a separate tab", async () => {
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
  await waitFor(() => expect(screen.getByText("Source scope ready.")).toBeTruthy());
  expect(screen.getByText("1 entry")).toBeTruthy();
  expect(window.location.hash).toBe("#/sast-runs/14/activity?subtab=log");
});

test("shows newest SAST events first and lets the user change order and filter", async () => {
  const { container } = render(
    <ActivityView
      {...baseProps}
      scanRunning={false}
      agentLog={[
        { agent_id: "sast-worker-4", role: "SAST Review Worker", display_name: "routes:review" },
      ]}
      logs={[
        {
          id: 1,
          phase: "scope",
          message: "Scope ready",
          created_at: "2026-09-11T01:00:00Z",
          agent_id: "system",
          role: "System",
        },
        {
          id: 2,
          phase: "discovery",
          message: "Read source",
          created_at: "2026-09-11T01:01:00Z",
          agent_id: "sast-worker-4",
          role: "SAST Review Worker",
        },
        {
          id: 3,
          phase: "discovery",
          message: "Found lead",
          created_at: "2026-09-11T01:02:00Z",
          agent_id: "sast-worker-4",
          role: "SAST Review Worker",
        },
      ]}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Log" }));
  const messages = () =>
    [...container.querySelectorAll(".sast-activity-message")].map((row) => row.textContent);
  await waitFor(() => expect(messages()).toEqual(["Found lead", "Read source", "Scope ready"]));
  expect(screen.getAllByText("routes:review")).toHaveLength(2);

  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  const newestFirst = screen.getByRole("checkbox", { name: "Newest first" });
  expect(newestFirst.checked).toBe(true);
  fireEvent.click(newestFirst);
  expect(messages()).toEqual(["Scope ready", "Read source", "Found lead"]);

  fireEvent.click(screen.getByRole("checkbox", { name: "discovery" }));
  expect(messages()).toEqual(["Read source", "Found lead"]);
  expect(screen.getByText("2 of 3 entries")).toBeTruthy();
});
