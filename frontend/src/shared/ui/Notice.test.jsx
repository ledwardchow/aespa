import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { Notice } from "./Notice.jsx";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

test("shows errors in the corner stack until dismissed", () => {
  const onDismiss = vi.fn();
  render(<Notice onDismiss={onDismiss}>Could not delete the site.</Notice>);

  const alert = screen.getByRole("alert");
  expect(alert.closest(".notice-stack")).toBeTruthy();
  expect(alert.textContent).toContain("Could not delete the site.");
  fireEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));
  expect(onDismiss).toHaveBeenCalledOnce();
});

test("closes success messages on their own, even when the parent re-renders", () => {
  vi.useFakeTimers();
  const onDismiss = vi.fn();
  const { rerender } = render(
    <Notice variant="success" onDismiss={() => onDismiss()}>
      Imported 3 issues.
    </Notice>,
  );
  act(() => vi.advanceTimersByTime(4000));
  rerender(
    <Notice variant="success" onDismiss={() => onDismiss()}>
      Imported 3 issues.
    </Notice>,
  );
  act(() => vi.advanceTimersByTime(2500));
  expect(onDismiss).toHaveBeenCalledOnce();
});
