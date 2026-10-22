import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { defaultPolicyForm } from "../../shared/runs/policy.js";
import { ScannerPolicyFields } from "./ScannerPolicyFields.jsx";
import { SecurityChecksFields } from "./ScannerPolicySettings.jsx";

test("edits the DAST LLM concurrency limit", () => {
  const update = vi.fn();
  render(<ScannerPolicyFields form={defaultPolicyForm()} upd={update} />);

  const input = screen.getByLabelText("Concurrent LLM requests");
  expect(input.value).toBe("4");
  fireEvent.change(input, { target: { value: "9" } });

  expect(update).toHaveBeenCalledWith({ dast_max_concurrent_llm_requests: "9" });
});

test("edits the shared automatic checks setting", () => {
  const update = vi.fn();
  const { unmount } = render(<ScannerPolicyFields form={defaultPolicyForm()} upd={update} />);
  expect(screen.queryByText("Disable automatic security checks")).toBeNull();
  unmount();

  render(<SecurityChecksFields form={defaultPolicyForm()} upd={update} />);
  const checkbox = screen.getByRole("checkbox", { name: "Disable automatic security checks" });
  expect(checkbox.checked).toBe(false);
  expect(screen.getByText(/Applies to Sites, API, and SAST scans/)).toBeTruthy();
  fireEvent.click(checkbox);
  expect(update).toHaveBeenCalledWith({ disable_deterministic_checks: true });
});
