import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

test("DAST counter shows source SAST costs separately at desktop and narrow widths", async ({
  page,
}) => {
  await installFixtures(page);
  await page.route("**/api/test-runs/1/leads", (route) =>
    route.fulfill({
      json: [
        { producer_run_type: "sast", producer_run_id: 2 },
        { producer_run_type: "sast", producer_run_id: 2 },
        { producer_run_type: "sast", producer_run_id: 3 },
      ],
    }),
  );
  await page.route("**/api/test-runs/1/token-usage", (route) =>
    route.fulfill({
      json: {
        total_input: 1000,
        total_output: 100,
        estimated_cost_available: true,
        estimated_total_cost_usd: 10.68,
        by_model: {},
      },
    }),
  );
  await page.route("**/api/sast-runs/2", (route) =>
    route.fulfill({ json: { name: "Underlying source analysis" } }),
  );
  await page.route("**/api/sast-runs/2/token-usage", (route) =>
    route.fulfill({
      json: {
        estimated_cost_available: true,
        estimated_total_cost_usd: 3.19,
        by_model: { model: { estimated_cost_available: true } },
      },
    }),
  );
  await page.route("**/api/sast-runs/3{,/token-usage}", (route) =>
    route.fulfill({ status: 404, json: { detail: "SAST run not found" } }),
  );
  await page.goto("/#/runs/1/activity");
  await expect(page.getByText("≈$10.68 est. cost", { exact: true })).toBeVisible();
  await expect(page.getByText("≈$3.19 est. cost", { exact: true })).toBeVisible();
  await expect(page.getByText("SAST cost", { exact: true })).toHaveCount(2);
  await expect(page.getByText("Cost unavailable", { exact: true })).toBeVisible();
  await expect(page.getByText("≈$13.87 est. cost", { exact: true })).toHaveCount(0);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-dast-sast-costs-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByTitle("Collapse sidebar").click();
  await expect(page.getByText("≈$10.68 est. cost", { exact: true })).toBeVisible();
  await expect(page.getByText("≈$3.19 est. cost", { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-dast-sast-costs-narrow.png") });
});
