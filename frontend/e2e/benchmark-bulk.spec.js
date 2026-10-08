import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const width of [1440, 600]) {
  test(`bulk extension benchmarks at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    const results = [
      { id: 5, run_kind: "site", run_id: 2, summary: { full: 0, partial: 0, missing: 0 } },
    ];
    const runs = [
      {
        id: 1,
        name: "Unbenchmarked scan",
        status: "complete",
        scan_models: {
          primary: { name: "Test Lead", model: "dast-model" },
          sast: [{ run_id: 4 }],
        },
      },
      { id: 2, name: "Already benchmarked scan", status: "complete" },
      { id: 3, name: "Stopped scan", status: "stopped" },
    ];
    const batches = [];
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      if (endpoint === "settings") return route.fulfill({ json: { default_model_id: 1 } });
      if (endpoint === "targets")
        return route.fulfill({
          json: {
            sites: [
              { id: 1, name: "Shop", runs },
              { id: 3, name: "Forum", runs: [{ id: 6, name: "Forum scan", status: "complete" }] },
            ],
            apis: [{ id: 2, name: "Shop API", runs }],
            sast_runs: [
              {
                id: 4,
                name: "Source scan",
                status: "completed",
                scan_models: {
                  primary: { name: "Source model", model: "sast-model" },
                  sast: [{ model: { name: "Source model", model: "sast-model" } }],
                },
              },
            ],
          },
        });
      if (endpoint === "datasets")
        return route.fulfill({
          json:
            route.request().method() === "POST"
              ? { id: 7 }
              : [{ id: 7, name: "Fixture truth", item_count: 1 }],
        });
      if (endpoint === "results") return route.fulfill({ json: results });
      if (endpoint === "benchmark-unbenchmarked") {
        const body = route.request().postDataJSON();
        batches.push(body);
        for (const runId of body.run_ids) {
          results.push({
            id: 5 + runId,
            run_kind: body.run_kind,
            run_id: runId,
            summary: { full: 0, partial: 0, missing: 0 },
          });
        }
        return route.fulfill({ json: { completed: body.run_ids, skipped: [2], failures: [] } });
      }
      return route.fulfill({ json: [] });
    });
    await page.goto("/#/benchmark-lab");
    await expect(page).toHaveTitle("AESPA");
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    await expect(page.getByLabel("Ground truth for bulk benchmarks")).toHaveCount(0);
    await page.getByRole("tab", { name: "DAST", exact: true }).click();
    await expect(page.getByRole("tab", { name: "Summary" })).toHaveCount(0);
    const region = page.getByRole("region", { name: "Sites finished scans" });
    await expect(region.getByRole("link", { name: "Unbenchmarked scan" })).toBeVisible();
    await expect(region.getByRole("link", { name: "Stopped scan" })).toBeVisible();
    await expect(region.getByRole("columnheader", { name: "Scan model" })).toBeVisible();
    await expect(region.getByText("DAST with SAST Leads", { exact: true })).toBeVisible();
    await expect(region.getByText("Test Lead (dast-model)", { exact: true })).toBeVisible();
    await region.getByRole("checkbox", { name: "Select all scans from Shop" }).check();
    await expect(region.getByRole("checkbox", { name: "Select Unbenchmarked scan" })).toBeChecked();
    await expect(region.getByRole("checkbox", { name: "Select Stopped scan" })).toBeChecked();
    await expect(
      region.getByRole("checkbox", { name: "Select Already benchmarked scan" }),
    ).toBeDisabled();
    await expect(region.getByRole("checkbox", { name: "Select Forum scan" })).not.toBeChecked();
    expect(
      await region
        .getByRole("checkbox", { name: "Select all unbenchmarked scans" })
        .evaluate((element) => element.indeterminate),
    ).toBe(true);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-benchmark-selection-${width}.png`) });
    const action = region.getByRole("button", { name: "Benchmark 2 selected scans" });
    await expect(action).toBeDisabled();
    await region.getByLabel("Ground truth for bulk benchmarks").selectOption("7");
    await action.click();
    await expect(region.getByRole("status")).toContainText("Benchmarked 2 scans");
    expect(batches).toEqual([{ run_kind: "site", run_ids: [1, 3], dataset_id: 7 }]);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-benchmark-outcome-${width}.png`) });
    await page.getByRole("tab", { name: "APIs", exact: true }).click();
    await expect(
      page
        .getByRole("region", { name: "API finished scans" })
        .getByText("Test Lead (dast-model)", { exact: true }),
    ).toBeVisible();
    await page.getByRole("tab", { name: "SAST", exact: true }).click();
    await expect(
      page
        .getByRole("region", { name: "SAST finished scans" })
        .getByRole("link", { name: "Source scan" }),
    ).toBeVisible();
    await expect(page.getByText("Source model (sast-model)", { exact: true })).toBeVisible();
    const bounds = await page.getByRole("tablist", { name: "Scan type" }).evaluate((element) => ({
      bar: element.getBoundingClientRect().toJSON(),
      parent: element.parentElement.getBoundingClientRect().toJSON(),
      body: document.body.scrollWidth,
      viewport: innerWidth,
    }));
    expect(Math.abs(bounds.bar.left - bounds.parent.left)).toBeLessThan(2);
    expect(Math.abs(bounds.bar.right - bounds.parent.right)).toBeLessThan(2);
    expect(bounds.body).toBeLessThanOrEqual(bounds.viewport);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-develop-benchmark-${width}.png`) });
    expect(errors).toEqual([]);
  });
}
