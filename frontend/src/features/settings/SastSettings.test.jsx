import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { defaultPolicyForm, policyPayload } from "../../shared/runs/policy.js";
import { SastSettings } from "./SastSettings.jsx";

vi.mock("../../shared/api/settings.js");

beforeEach(() => {
  const policy = policyPayload(defaultPolicyForm());
  settingsApi.getScannerPolicy.mockResolvedValue(policy);
  settingsApi.upsertScannerPolicy.mockImplementation(async (payload) => payload);
});

test("shows adaptive budget controls and saves fixed mode", async () => {
  render(<SastSettings />);

  expect((await screen.findByLabelText("Budget mode")).value).toBe("adaptive");
  expect(screen.getByLabelText("Worker maximum").value).toBe("250");

  fireEvent.change(screen.getByLabelText("Budget mode"), {
    target: { value: "fixed" },
  });

  expect(screen.queryByLabelText("Worker maximum")).toBeNull();
  expect(screen.getByLabelText("Threat worker budget").value).toBe("60");
  fireEvent.click(screen.getByRole("button", { name: "Save policy" }));

  await waitFor(() =>
    expect(settingsApi.upsertScannerPolicy).toHaveBeenCalledWith(
      expect.objectContaining({ sast_budget_mode: "fixed", sast_worker_budget_max: 250 }),
    ),
  );
});
