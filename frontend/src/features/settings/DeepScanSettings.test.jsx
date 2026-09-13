import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { DeepScanSettings } from "./DeepScanSettings.jsx";

vi.mock("../../shared/api/settings.js");

const config = {
  max_concurrent_workers: 6,
  max_concurrent_planners: 4,
  max_tasks: 200,
  max_steps_per_task: 30,
  initial_variants_per_campaign: 2,
  max_variants_per_campaign: 4,
  max_total_variants: 400,
  adaptive_follow_up: true,
  minimum_signal_strength: 2,
  reuse_captured_baselines: true,
  include_sast_leads: true,
  include_recon_checks: true,
};

beforeEach(() => {
  settingsApi.getDeepScanConfig.mockResolvedValue(config);
  settingsApi.upsertDeepScanConfig.mockResolvedValue(config);
});

test("uses the shared settings card and save states", async () => {
  const { container } = render(<DeepScanSettings />);

  expect(await screen.findByText("Deep web scan")).toBeTruthy();
  expect(container.querySelector("form.card")).toBeTruthy();

  fireEvent.change(screen.getByLabelText("Concurrent attack workers"), {
    target: { value: "8" },
  });
  fireEvent.change(screen.getByLabelText("Concurrent planner calls"), {
    target: { value: "3" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Deep Scan Settings" }));

  await waitFor(() =>
    expect(settingsApi.upsertDeepScanConfig).toHaveBeenCalledWith({
      ...config,
      max_concurrent_workers: 8,
      max_concurrent_planners: 3,
    }),
  );
  expect(await screen.findByText("Saved")).toBeTruthy();
});
