import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const width of [1440, 600]) {
  test(`import and export benchmark data at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (
        ["error", "warning"].includes(message.type()) &&
        message.text() !== "Service Worker registration blocked by Playwright"
      )
        errors.push(message.text());
    });
    let imported = false;
    let payload;
    const bundle = { format: "aespa-benchmark-lab", version: 1, datasets: [] };
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const url = new URL(route.request().url()).pathname;
      if (url.endsWith("/export"))
        return route.fulfill({
          contentType: "application/json",
          headers: { "Content-Disposition": 'attachment; filename="aespa-benchmark-lab.json"' },
          body: JSON.stringify(bundle),
        });
      if (url.endsWith("/import")) {
        payload = route.request().postDataJSON();
        imported = true;
        return route.fulfill({
          json: {
            datasets_added: 1,
            imported: 1,
            skipped: 2,
            conflicts: [{ key: "conflict", kind: "results", name: "Locally reviewed scan" }],
          },
        });
      }
      if (url.endsWith("/settings")) return route.fulfill({ json: { default_model_id: 1 } });
      if (url.endsWith("/targets"))
        return route.fulfill({ json: { sites: [], apis: [], sast_runs: [] } });
      if (url.endsWith("/datasets"))
        return route.fulfill({
          json: imported ? [{ id: 7, name: "Shared dataset", item_count: 1, assignments: [] }] : [],
        });
      if (url.endsWith("/results"))
        return route.fulfill({
          json: imported
            ? [
                {
                  id: 1,
                  run_kind: "site",
                  run_id: 0,
                  target_id: null,
                  imported: true,
                  dataset_id: 7,
                  run_name: "Remote scan",
                  target_name: "Shared application",
                  findings: [],
                  rows: [],
                  ground_truth: { items: [] },
                  summary: { full: 1, partial: 0, missing: 0 },
                  scan_models: { primary: { model: "remote-model" } },
                  scan_cost_usd: 0.42,
                  created_at: "2026-10-02T01:00:00Z",
                },
              ]
            : [],
        });
      return route.fulfill({ json: [] });
    });
    await page.goto("/#/benchmark-lab");
    await expect(page).toHaveTitle("AESPA");
    await page.getByRole("tab", { name: "Settings" }).click();
    await expect(page.getByRole("heading", { name: "Share benchmark data" })).toBeVisible();
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Export benchmark data" }).click();
    expect((await downloadPromise).suggestedFilename()).toBe("aespa-benchmark-lab.json");
    const chooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Import benchmark data" }).click();
    await (
      await chooserPromise
    ).setFiles({
      name: "benchmarks.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(bundle)),
    });
    await expect(page.getByRole("status")).toContainText(
      "Datasets added: 1. Records imported: 1. Duplicates skipped: 2.",
    );
    await expect(page.getByRole("status")).toContainText("Locally reviewed scan");
    expect(payload).toEqual(bundle);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-benchmark-transfer-${width}.png`) });
    await page.getByRole("tab", { name: "Results", exact: true }).click();
    await page.getByLabel("Site", { exact: true }).selectOption("dataset:7");
    await page.getByRole("tab", { name: "Analyses", exact: true }).click();
    await expect(page.getByText("Remote scan (imported)")).toBeVisible();
    await page.getByRole("button", { name: "Open Remote scan" }).click();
    await expect(page.getByText("remote-model", { exact: false }).first()).toBeVisible();
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}
