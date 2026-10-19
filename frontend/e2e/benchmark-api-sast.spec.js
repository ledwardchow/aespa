import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const width of [1440, 600]) {
  test(`API and SAST benchmark views at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const results = [
      {
        id: 10,
        run_kind: "api",
        run_id: 2,
        target_id: 1,
        run_name: "Saved API scan",
      },
      {
        id: 11,
        run_kind: "sast",
        run_id: 4,
        run_name: "Saved source scan",
      },
    ].map((result) => ({
      ...result,
      created_at: "2026-10-20T00:00:00Z",
      summary: { full: 0, partial: 0, missing: 1 },
      ground_truth: {
        name: "Fixture truth",
        items: [{ external_id: "GT-1", title: "Missing check", severity: "high" }],
      },
      rows: [{ external_id: "GT-1", disposition: "missing", finding_ids: [], reason: "Not found" }],
      findings: [],
    }));
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      const data =
        endpoint === "targets"
          ? {
              sites: [],
              apis: [
                {
                  id: 1,
                  name: "Shop API",
                  runs: [
                    { id: 1, name: "Pending API scan", status: "complete" },
                    { id: 2, name: "Saved API scan", status: "complete" },
                  ],
                },
              ],
              sast_runs: [
                { id: 3, name: "Pending source scan", status: "completed" },
                { id: 4, name: "Saved source scan", status: "completed" },
                { id: 5, name: "Legacy source scan", status: "completed" },
              ],
            }
          : endpoint === "results"
            ? results
            : endpoint === "evaluations"
              ? [{ id: 9, sast_run_id: 5, name: "Earlier source result", status: "completed" }]
              : endpoint === "settings"
                ? { default_model_id: 1 }
                : [];
      await route.fulfill({ json: data });
    });
    await page.goto("/#/benchmark-lab?tab=api");
    const apiScans = page.getByRole("region", { name: "API finished scans" });
    await expect(apiScans.getByRole("link", { name: "Pending API scan" })).toBeVisible();
    await expect(apiScans.getByRole("link", { name: "Saved API scan" })).toHaveCount(0);
    await apiScans.getByLabel("Application").selectOption("1");
    await apiScans.getByRole("checkbox", { name: "Select Pending API scan" }).check();
    await apiScans.getByRole("button", { name: "Benchmark selected" }).click();
    await expect(apiScans.getByLabel("Ground truth for bulk benchmarks")).toBeVisible();
    await apiScans.getByRole("button", { name: "Close setup" }).click();
    await apiScans.getByLabel("Benchmark status").selectOption("done");
    await expect(apiScans.getByRole("link", { name: "Saved API scan" })).toBeVisible();
    await page.getByRole("tab", { name: /Saved results/ }).click();
    await page.getByRole("link", { name: "Open Saved API scan" }).click();
    await expect(page.getByRole("region", { name: "Finding review" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Back to results" })).toHaveAttribute(
      "href",
      "#/benchmark-lab?tab=api&view=results",
    );
    await page.getByRole("link", { name: "Back to results" }).click();
    await page.getByRole("tab", { name: "SAST" }).click();
    const sastScans = page.getByRole("region", { name: "SAST finished scans" });
    await expect(sastScans.getByRole("link", { name: "Pending source scan" })).toBeVisible();
    await expect(sastScans.getByLabel("Application")).toHaveCount(0);
    await sastScans.getByLabel("Benchmark status").selectOption("done");
    await expect(sastScans.getByRole("link", { name: "Legacy source scan" })).toBeVisible();
    await expect(sastScans.getByRole("link", { name: "Open benchmark" })).toHaveAttribute(
      "href",
      "#/benchmark-lab/evaluations/9",
    );
    await page.getByRole("tab", { name: /Saved results/ }).click();
    await expect(page.getByRole("link", { name: "Earlier source result" })).toBeVisible();
    await page.getByRole("link", { name: "Open Saved source scan" }).click();
    await expect(page.getByRole("region", { name: "Finding review" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Back to results" })).toHaveAttribute(
      "href",
      "#/benchmark-lab?tab=sast&view=results",
    );
    const bounds = await page.getByRole("region", { name: "Finding review" }).evaluate((el) => ({
      right: el.getBoundingClientRect().right,
      viewport: window.innerWidth,
      body: document.body.scrollWidth,
    }));
    expect(bounds.right).toBeLessThanOrEqual(bounds.viewport + 1);
    expect(bounds.body).toBeLessThanOrEqual(bounds.viewport);
    expect(errors).toEqual([]);
  });
}
