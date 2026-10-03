import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const width of [1440, 600]) {
  test(`manage ground truth datasets at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (
        (message.type() === "error" || message.type() === "warning") &&
        message.text() !== "Service Worker registration blocked by Playwright"
      )
        errors.push(message.text());
    });
    let datasets = [
      {
        id: 7,
        name: "BankOfEd - Intentional Vulnerabilities (OWASP Top 10)",
        item_count: 23,
        label: "",
        assignments: [],
      },
    ];
    let saved;
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const url = new URL(route.request().url()).pathname;
      if (url.endsWith("/settings")) return route.fulfill({ json: { default_model_id: 1 } });
      if (url.endsWith("/targets"))
        return route.fulfill({
          json: {
            sites: [{ id: 1, name: "Bank of Ed", runs: [] }],
            apis: [{ id: 2, name: "Bank API", runs: [] }],
            sast_runs: [],
          },
        });
      if (route.request().method() === "PATCH") {
        saved = route.request().postDataJSON();
        datasets = [
          {
            ...datasets[0],
            label: saved.label,
            assignments: [{ target_kind: saved.target_kind, target_id: saved.target_id }],
            updated_at: "2026-09-30T12:00:00Z",
          },
        ];
        return route.fulfill({ json: datasets[0] });
      }
      if (route.request().method() === "DELETE") {
        datasets = [];
        return route.fulfill({ status: 204 });
      }
      return route.fulfill({ json: url.endsWith("/datasets") ? datasets : [] });
    });
    await page.goto("/#/benchmark-lab");
    await page.getByRole("tab", { name: "Settings" }).click();
    await expect(page.getByRole("heading", { name: "Ground truth datasets" })).toBeVisible();
    await expect(page).toHaveTitle("AESPA");
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    await page.getByRole("button", { name: "Save benchmark model" }).click();
    await expect(page.getByRole("status")).toContainText("Benchmark model saved.");
    await page.getByLabel("App or API").selectOption("site:1");
    await page.getByLabel("Custom label").fill("Bank of Ed source");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect
      .poll(() => saved)
      .toEqual({ label: "Bank of Ed source", target_kind: "site", target_id: 1 });
    await expect(page.getByLabel("Custom label")).toHaveValue("Bank of Ed source");
    await expect(page.getByLabel("App or API")).toHaveValue("site:1");
    const bounds = await page.getByRole("tablist", { name: "Scan type" }).evaluate((element) => ({
      left: element.getBoundingClientRect().left,
      right: element.getBoundingClientRect().right,
      parentLeft: element.parentElement.getBoundingClientRect().left,
      parentRight: element.parentElement.getBoundingClientRect().right,
      body: document.body.scrollWidth,
      viewport: innerWidth,
    }));
    expect(Math.abs(bounds.left - bounds.parentLeft)).toBeLessThan(2);
    expect(Math.abs(bounds.right - bounds.parentRight)).toBeLessThan(2);
    expect(bounds.body).toBeLessThanOrEqual(bounds.viewport);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-ground-truth-${width}.png`) });
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await page.getByRole("button", { name: "Delete dataset", exact: true }).click();
    await expect(page.getByText("No saved datasets.", { exact: false })).toBeVisible();
    expect(errors).toEqual([]);
  });
}
