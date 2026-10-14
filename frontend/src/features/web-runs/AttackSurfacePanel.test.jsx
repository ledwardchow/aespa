import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as webRunsApi from "../../shared/api/webRuns.js";
import { AttackSurfacePanel } from "./AttackSurfacePanel.jsx";
import { WebRunNotificationsTab } from "./WebRunNotificationsTab.jsx";
import { WebRunWorkflowsTab } from "./WebRunWorkflowsTab.jsx";

afterEach(() => vi.restoreAllMocks());

describe("Workflow crawl notes", () => {
  it("shows workflows in their own panel", () => {
    const summary = {
      routes: [],
      route_count: 0,
      route_groups: [{ route_pattern: "/p/{value}", pages_sampled: 2, links_seen: 12 }],
      technologies: [{ name: "Next.js", source: "response headers" }],
      crawl_notes: [
        {
          name: "Checkout",
          reason: "Cart was empty and products have Add to cart controls.",
          status: "crawled",
          steps: ["click Add to cart", "click Secure Checkout"],
          detail: "Reached the workflow.",
          url: "https://shop.test/checkout",
        },
        {
          name: "Refund",
          reason: "Orders show refund controls.",
          status: "not_attempted",
          steps: [],
          detail: "Not tried because this workflow appears destructive.",
        },
      ],
    };

    const { unmount } = render(
      <AttackSurfacePanel summary={summary} routeGroups={summary.route_groups} />,
    );
    expect(screen.getByText("Grouped pages")).toBeTruthy();
    expect(screen.queryByText("Checkout")).toBeNull();
    unmount();
    render(<WebRunWorkflowsTab summary={summary} />);
    expect(screen.getByText("Checkout")).toBeTruthy();
    expect(screen.getByText("Refund")).toBeTruthy();
    expect(screen.getByText("Not tried")).toBeTruthy();
    expect(screen.getByText(/click Add to cart/)).toBeTruthy();
  });

  it("shows retries within the original workflow item", () => {
    render(
      <WebRunWorkflowsTab
        summary={{
          crawl_notes_checked: true,
          crawl_notes: [
            { id: 10, name: "Checkout", status: "needs_input", detail: "No address supplied." },
            {
              id: 11,
              retry_of: 10,
              name: "Checkout",
              status: "not_reached",
              detail: "The form could not be opened.",
            },
            {
              id: 12,
              retry_of: 11,
              name: "Checkout",
              status: "needs_input",
              needs_input: true,
              detail: "A phone number is needed.",
            },
          ],
        }}
      />,
    );
    expect(document.querySelectorAll(".surface-crawl-note")).toHaveLength(1);
    expect(screen.getByText(/Retry 1: Could not reach/)).toBeTruthy();
    expect(screen.getByText(/Retry 2: Needs input/)).toBeTruthy();
  });

  it("retries an unfinished workflow using its last instructions", async () => {
    vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({
      notes: [
        {
          id: 7,
          name: "Address",
          status: "not_reached",
          retryable: true,
          instructions: "Use 1 Test Street",
          save_to_site_requested: true,
        },
        { id: 8, name: "Checkout", status: "crawled", retryable: false },
      ],
    });
    vi.spyOn(webRunsApi, "getWorkflowRetryStatus").mockResolvedValue({ status: "idle" });
    const retry = vi.spyOn(webRunsApi, "retryWorkflow").mockResolvedValue({
      status: "running",
      note_id: 7,
      message: "Opening browser",
      actions: [],
    });
    render(<WebRunWorkflowsTab runId={1} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry workflow" }));
    await waitFor(() => expect(retry).toHaveBeenCalledWith(1, 7, "Use 1 Test Street", true));
    expect(await screen.findByText("Opening browser")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Retry workflow" })).toHaveLength(1);
  });

  it("opens the matching notification when a workflow needs input", async () => {
    const openNotification = vi.fn();
    render(
      <WebRunWorkflowsTab
        summary={{
          crawl_notes: [
            {
              id: 10,
              name: "Address",
              status: "needs_input",
              needs_input: true,
              request: "Provide a test address.",
            },
          ],
        }}
        onOpenNotification={openNotification}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Provide input" }));
    expect(openNotification).toHaveBeenCalledWith(10);
  });

  it("focuses the requested notification's input", async () => {
    vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({
      notes: [
        { id: 10, name: "Address", needs_input: true },
        { id: 11, name: "Checkout", needs_input: true },
      ],
    });
    vi.spyOn(webRunsApi, "getWorkflowRetryStatus").mockResolvedValue({ status: "idle" });
    render(
      <WebRunNotificationsTab
        runId={1}
        focusedNoteId={11}
        focusSequence={1}
        onViewWorkflow={() => {}}
      />,
    );
    await waitFor(() => expect(document.activeElement?.id).toBe("workflow-input-11"));
  });
});
