import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { defaultPolicyForm } from "../../shared/runs/policy.js";
import { ScannerPolicyFields } from "./ScannerPolicyFields.jsx";

test("edits the DAST LLM concurrency limit", () => {
  const update = vi.fn();
  render(<ScannerPolicyFields form={defaultPolicyForm()} upd={update} />);

  const input = screen.getByLabelText("Concurrent LLM requests");
  expect(input.value).toBe("4");
  fireEvent.change(input, { target: { value: "9" } });

  expect(update).toHaveBeenCalledWith({ dast_max_concurrent_llm_requests: "9" });
});
