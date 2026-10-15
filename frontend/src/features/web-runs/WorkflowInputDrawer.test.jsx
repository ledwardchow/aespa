import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as webRunsApi from "../../shared/api/webRuns.js";
import { WorkflowInputDrawer, WorkflowInputPill } from "./WorkflowInputDrawer.jsx";

afterEach(() => vi.restoreAllMocks());

describe("Workflow input pill", () => {
  it("is hidden when nothing needs input", () => {
    const { container } = render(<WorkflowInputPill count={0} onClick={() => {}} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows the waiting count", () => {
    const onClick = vi.fn();
    const { rerender } = render(<WorkflowInputPill count={1} onClick={onClick} />);
    fireEvent.click(screen.getByRole("button", { name: "1 needs input" }));
    expect(onClick).toHaveBeenCalled();
    rerender(<WorkflowInputPill count={4} onClick={onClick} />);
    expect(screen.getByRole("button", { name: "4 need input" })).toBeTruthy();
  });
});

describe("Workflow input drawer", () => {
  it("closes with the close button and Escape", async () => {
    vi.spyOn(webRunsApi, "getWorkflowNotes").mockResolvedValue({ notes: [] });
    vi.spyOn(webRunsApi, "getWorkflowRetryStatus").mockResolvedValue({ status: "idle" });
    const onClose = vi.fn();
    render(<WorkflowInputDrawer open runId={1} onClose={onClose} onViewWorkflow={() => {}} />);
    expect(screen.getByRole("dialog", { name: "Needs input" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("You're all caught up")).toBeTruthy();
  });

  it("renders nothing when closed", () => {
    render(<WorkflowInputDrawer open={false} runId={1} onClose={() => {}} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
