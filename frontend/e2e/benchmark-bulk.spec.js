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
    const results = [{ id: 5, run_kind: "site", run_id: 2 }];
    const runs = [
      { id: 1, name: "Unbenchmarked scan", status: "complete" },
      { id: 2, name: "Already benchmarked scan", status: "complete" },
      { id: 3, name: "Stopped scan", status: "stopped" },
    ];
    const batches = [];
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      if (endpoint === "targets")
        return route.fulfill({
          json: {
            sites: [{ id: 1, name: "Shop", runs }],
            apis: [{ id: 2, name: "Shop API", runs }],
            sast_runs: [{ id: 4, name: "Source scan", status: "completed" }],
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
        results.push({ id: 6, run_kind: body.run_kind, run_id: 1 });
        return route.fulfill({ json: { completed: [1], skipped: [2], failures: [] } });
      }
      return route.fulfill({ json: [] });
    });
    await page.goto("/#/benchmark-lab");
    const region = page.getByRole("region", { name: "Sites completed scans" });
    await expect(region.getByRole("link", { name: "Unbenchmarked scan" })).toBeVisible();
    await expect(region.getByText("Stopped scan")).toHaveCount(0);
    const action = region.getByRole("button", { name: "Benchmark 1 unbenchmarked scans" });
    await expect(action).toBeDisabled();
    await region.getByLabel("Ground truth for bulk benchmarks").selectOption("7");
    await action.click();
    await expect(region.getByRole("status")).toContainText("Benchmarked 1 scans");
    expect(batches).toEqual([{ run_kind: "site", dataset_id: 7 }]);
    await page.getByRole("tab", { name: "APIs", exact: true }).click();
    await expect(page.getByRole("region", { name: "API completed scans" })).toBeVisible();
    await page.getByRole("tab", { name: "SAST", exact: true }).click();
    await expect(
      page
        .getByRole("region", { name: "SAST completed scans" })
        .getByRole("link", { name: "Source scan" }),
    ).toBeVisible();
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
