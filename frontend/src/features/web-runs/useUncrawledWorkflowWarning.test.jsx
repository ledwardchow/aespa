import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { uncrawledWorkflows, useUncrawledWorkflowWarning } from "./useUncrawledWorkflowWarning.jsx";

function ScanActions({ onStart = vi.fn(), onResume = vi.fn(), onView = vi.fn() }) {
  const [mode, setMode] = useState("track");
  const { requestStart, warning } = useUncrawledWorkflowWarning({
    runId: 7,
    onStart,
    onViewWorkflows: onView,
  });
  return (
    <>
      <button onClick={() => requestStart("scan", mode)}>Start scan</button>
      <button onClick={() => requestStart("crawl-then-scan", mode)}>Start crawl then scan</button>
      <button onClick={onResume}>Resume scan</button>
      <button onClick={() => setMode("deep")}>Choose Deep</button>
      {warning}
    </>
  );
}

beforeEach(() => {
  window.HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  window.HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

afterEach(() => vi.restoreAllMocks());

test("counts only the latest unresolved attempt for each workflow", () => {
  const notes = [
    { id: 1, name: "Checkout", status: "needs_input", superseded: true },
    { id: 2, retry_of: 1, name: "Checkout retry", status: "not_reached" },
    { id: 3, name: "Account", status: "not_reached", superseded: true },
    { id: 4, retry_of: 3, name: "Account retry", status: "crawled" },
    { id: 5, name: "Profile", status: "crawled" },
  ];
  expect(uncrawledWorkflows(notes)).toEqual([
    expect.objectContaining({ id: 2, name: "Checkout", status: "not_reached" }),
  ]);
});

test("fetches current notes on click, then cancels or confirms with the selected mode", async () => {
  const getNotes = vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({
    notes: [{ id: 11, name: "Checkout", status: "needs_input" }],
  });
  const onStart = vi.fn();
  render(<ScanActions onStart={onStart} />);

  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  expect(
    await screen.findByRole("dialog", { name: "Some workflows have not been crawled" }),
  ).toBeTruthy();
  expect(screen.getByText(/1 workflow has not been crawled/)).toBeTruthy();
  expect(screen.getByText(/Checkout/).closest("li").textContent).toContain("Needs input");
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(onStart).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  await screen.findByRole("dialog");
  fireEvent.click(screen.getByRole("button", { name: "Choose Deep" }));
  fireEvent.click(screen.getByRole("button", { name: "Start scan anyway" }));
  await waitFor(() => expect(onStart).toHaveBeenCalledWith("scan", "track"));
  expect(getNotes).toHaveBeenCalledTimes(2);
});

test("acknowledges only the workflow attempts passed over by a successful start", async () => {
  vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({
    notes: [{ id: 11, name: "Checkout", status: "needs_input" }],
  });
  const onStart = vi.fn().mockResolvedValue(true);
  const onAcknowledged = vi.fn();
  function Actions() {
    const { requestStart, warning } = useUncrawledWorkflowWarning({
      runId: 7,
      onStart,
      onViewWorkflows: vi.fn(),
      onAcknowledged,
    });
    return (
      <>
        <button onClick={() => requestStart("scan", "track")}>Start scan</button>
        {warning}
      </>
    );
  }
  render(<Actions />);
  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  fireEvent.click(await screen.findByRole("button", { name: "Start scan anyway" }));
  await waitFor(() => expect(onAcknowledged).toHaveBeenCalledWith([11]));
});

test("does not acknowledge workflows when the start request fails", async () => {
  vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({
    notes: [{ id: 12, name: "Checkout", status: "needs_input" }],
  });
  const onAcknowledged = vi.fn();
  function Actions() {
    const { requestStart, warning } = useUncrawledWorkflowWarning({
      runId: 7,
      onStart: vi.fn().mockResolvedValue(false),
      onViewWorkflows: vi.fn(),
      onAcknowledged,
    });
    return (
      <>
        <button onClick={() => requestStart("scan", "track")}>Start scan</button>
        {warning}
      </>
    );
  }
  render(<Actions />);
  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  fireEvent.click(await screen.findByRole("button", { name: "Start scan anyway" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(onAcknowledged).not.toHaveBeenCalled();
});

test("starts combined crawl and scan without checking unfinished workflows", async () => {
  const getNotes = vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({
    notes: [{ id: 21, name: "Payment", status: "not_attempted", steps: [] }],
  });
  const onStart = vi.fn();
  const onView = vi.fn();
  const onAcknowledged = vi.fn();
  function Actions() {
    const { requestStart, warning } = useUncrawledWorkflowWarning({
      runId: 7,
      onStart: async (...args) => {
        onStart(...args);
        return true;
      },
      onViewWorkflows: onView,
      onAcknowledged,
    });
    return (
      <>
        <button onClick={() => requestStart("crawl-then-scan", "track")}>
          Start crawl then scan
        </button>
        {warning}
      </>
    );
  }
  render(<Actions />);

  fireEvent.click(screen.getByRole("button", { name: "Start crawl then scan" }));
  await waitFor(() => expect(onStart).toHaveBeenCalledWith("crawl-then-scan", "track"));
  expect(getNotes).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(onView).not.toHaveBeenCalled();
  expect(onAcknowledged).not.toHaveBeenCalled();
});

test("starts immediately when all workflows are crawled and prevents duplicate checks", async () => {
  let resolveNotes;
  const getNotes = vi.spyOn(webRunsApi, "getWorkflowNotes").mockReturnValue(
    new Promise((resolve) => {
      resolveNotes = resolve;
    }),
  );
  const onStart = vi.fn();
  render(<ScanActions onStart={onStart} />);

  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  expect(getNotes).toHaveBeenCalledOnce();
  resolveNotes({ notes: [{ id: 4, name: "Payment", status: "crawled" }] });
  await waitFor(() => expect(onStart).toHaveBeenCalledOnce());
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("shows a check failure, permits retry, and leaves Resume outside the warning", async () => {
  const getNotes = vi
    .spyOn(webRunsApi, "getWorkflowNotes")
    .mockRejectedValueOnce(new Error("Server unavailable"))
    .mockResolvedValueOnce({ notes: [{ id: 9, name: "Orders", status: "not_reached" }] });
  const onStart = vi.fn();
  const onResume = vi.fn();
  render(<ScanActions onStart={onStart} onResume={onResume} />);

  fireEvent.click(screen.getByRole("button", { name: "Resume scan" }));
  expect(onResume).toHaveBeenCalledOnce();
  expect(getNotes).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  expect(await screen.findByRole("dialog", { name: "Could not check workflows" })).toBeTruthy();
  expect(screen.getByRole("alert").textContent).toContain("Server unavailable");
  expect(onStart).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(
    await screen.findByRole("dialog", { name: "Some workflows have not been crawled" }),
  ).toBeTruthy();
  expect(getNotes).toHaveBeenCalledTimes(2);
});

test("Escape closes the warning and restores focus to Start scan", async () => {
  vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({
    notes: [{ id: 8, name: "Order", status: "not_reached" }],
  });
  const onStart = vi.fn();
  render(<ScanActions onStart={onStart} />);
  const start = screen.getByRole("button", { name: "Start scan" });
  start.focus();
  fireEvent.click(start);
  const dialog = await screen.findByRole("dialog");
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Cancel" }));
  fireEvent(dialog, new window.Event("cancel", { cancelable: true }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(document.activeElement).toBe(start);
  expect(onStart).not.toHaveBeenCalled();
});

test("blocks starting when the workflow response is incomplete", async () => {
  vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({});
  const onStart = vi.fn();
  render(<ScanActions onStart={onStart} />);
  fireEvent.click(screen.getByRole("button", { name: "Start scan" }));
  expect(await screen.findByRole("dialog", { name: "Could not check workflows" })).toBeTruthy();
  expect(onStart).not.toHaveBeenCalled();
});
