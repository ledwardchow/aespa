import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 600, height: 800 },
]) {
  test(`summary filters and graph fit at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    const results = [
      {
        id: 1,
        run_name: "DAST only",
        run_kind: "site",
        scan_models: { primary: { name: "Sonnet" } },
      },
      {
        id: 2,
        run_name: "Combined scan",
        run_kind: "site",
        scan_models: { primary: { name: "Sonnet" }, sast: [{ run_id: 7 }] },
      },
      {
        id: 3,
        run_name: "Source scan",
        run_kind: "sast",
        scan_models: { primary: { name: "Sonnet" } },
      },
      ...Array.from({ length: 12 }, (_, i) => ({
        id: i + 4,
        run_name: `Scan ${i + 4}`,
        run_kind: "site",
        scan_models: { primary: { name: i < 2 ? "Other model" : `Model ${i + 4}` } },
      })),
    ].map((result) => ({
      ...result,
      target_kind: "site",
      target_id: 1,
      scan_cost_usd: result.id / 10,
      scan_started_at: new Date(Date.UTC(2026, 8, result.id, 9)).toISOString(),
      summary: { full: result.id, partial: 0, missing: 0 },
      ground_truth: { name: "Fixture truth", items: [] },
      findings: [],
      rows: [],
      created_at: "2026-09-30T09:00:00Z",
    }));
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      const data =
        endpoint === "targets"
          ? { sites: [{ id: 1, name: "Bank of Ed", runs: [] }], apis: [], sast_runs: [] }
          : endpoint === "results"
            ? results
            : endpoint === "settings"
              ? { default_model_id: 1 }
              : [];
      await route.fulfill({ json: data });
    });
    await page.goto("/#/benchmark-lab");
    await expect(page).toHaveTitle("AESPA");
    await page.getByLabel("Site", { exact: true }).selectOption("1");
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    const point = (name) => page.getByRole("button", { name: new RegExp(`^${name},`) });
    await expect(point("Combined scan").locator("rect")).toBeVisible();
    await expect(point("DAST only").locator("circle")).toBeVisible();
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toBeVisible();
    await expect(page.getByRole("img", { name: "Other model linear trend" })).toBeVisible();
    const labels = await page.locator('[aria-label$="linear trend"] text').evaluateAll((elements) =>
      elements.map((element) => {
        const box = element.getBoundingClientRect();
        return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
      }),
    );
    expect(labels).toHaveLength(2);
    expect(
      labels[0].right <= labels[1].left ||
        labels[1].right <= labels[0].left ||
        labels[0].bottom <= labels[1].top ||
        labels[1].bottom <= labels[0].top,
    ).toBe(true);
    await page.locator('summary[aria-label="Scan type"]').click();
    await page.getByRole("checkbox", { name: "Select all", exact: true }).uncheck();
    await expect(point("Combined scan")).toHaveCount(0);
    await page.getByRole("checkbox", { name: "Select all", exact: true }).check();
    await page.getByRole("checkbox", { name: "DAST", exact: true }).uncheck();
    await expect(point("DAST only")).toHaveCount(0);
    await expect(point("Combined scan")).toBeVisible();
    await page.getByRole("checkbox", { name: "DAST", exact: true }).check();
    await page.getByRole("checkbox", { name: "SAST+DAST", exact: true }).uncheck();
    await expect(point("Combined scan")).toHaveCount(0);
    await expect(point("DAST only")).toBeVisible();
    await page.getByRole("checkbox", { name: "SAST+DAST", exact: true }).check();
    await page.getByLabel("Model", { exact: true }).click();
    await page.getByRole("checkbox", { name: "Select all", exact: true }).uncheck();
    await expect(point("DAST only")).toHaveCount(0);
    await page.getByRole("checkbox", { name: "Select all", exact: true }).check();
    await page.getByRole("checkbox", { name: "Sonnet", exact: true }).uncheck();
    await expect(point("DAST only")).toHaveCount(0);
    await expect(point("Combined scan")).toHaveCount(0);
    await page.getByRole("checkbox", { name: "Sonnet", exact: true }).check();
    await page.getByRole("checkbox", { name: "Sonnet", exact: true }).press("Escape");
    await page.getByRole("button", { name: "Sonnet", exact: true }).click();
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toHaveCount(0);
    await page.getByRole("button", { name: "Sonnet", exact: true }).click();
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toBeVisible();
    await page.getByLabel("Compare by").selectOption("date");
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toBeVisible();
    await expect(
      page.getByRole("img", { name: "Scan date versus full and partial findings" }),
    ).toBeVisible();
    await expect(point("Combined scan")).toBeVisible();
    const bounds = await page.locator(".benchmark-summary-page").evaluate((element) => ({
      scroll: element.scrollHeight,
      height: element.clientHeight,
      width: document.body.scrollWidth,
      viewport: innerWidth,
      graphBottom: element.querySelector("svg").getBoundingClientRect().bottom,
      pageBottom: element.getBoundingClientRect().bottom,
    }));
    expect(bounds.scroll).toBeLessThanOrEqual(bounds.height + 1);
    expect(bounds.width).toBeLessThanOrEqual(bounds.viewport);
    expect(bounds.graphBottom).toBeLessThanOrEqual(bounds.pageBottom);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-summary-${viewport.width}.png`) });
    await point("Combined scan").hover();
    await expect(page.getByRole("tooltip")).toContainText("Combined scan");
    await expect(page.getByRole("tooltip")).toContainText("Sonnet");
    await expect(page.getByRole("tooltip")).toContainText("SAST+DAST");
    await page.screenshot({
      path: path.join(tmpdir(), `aespa-summary-tooltip-${viewport.width}.png`),
    });
    await point("Combined scan").click();
    await expect(page.getByRole("tab", { name: "Analyses" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(errors).toEqual([]);
  });
}
