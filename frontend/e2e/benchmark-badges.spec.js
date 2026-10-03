import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const [kind, routeHash] of [
  ["sast", "sast-runs"],
  ["site", "sites/1"],
  ["api", "apis/1"],
]) {
  test(`saved ${kind} benchmark badge opens its result`, async ({ page }) => {
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const result = {
      id: 10,
      run_kind: kind,
      run_id: 1,
      run_name: "Saved benchmark scan",
      target_kind: kind === "sast" ? null : kind,
      target_id: kind === "sast" ? null : 1,
      created_at: "2026-09-30T00:00:00Z",
      summary: { full: 1, partial: 0, missing: 0 },
      ground_truth: {
        name: "Fixture truth",
        items: [{ external_id: "GT-1", title: "SQL injection" }],
      },
      findings: [],
      rows: [{ external_id: "GT-1", disposition: "full", finding_ids: [], reason: "Matched" }],
    };
    await page.route("**/api/extensions", (route) =>
      route.fulfill({
        json: [
          {
            id: "aespa.benchmarking",
            name: "Benchmark Lab",
            enabled: true,
            status: "loaded",
            capabilities: [],
            settings: {},
            settings_fields: [],
          },
        ],
      }),
    );
    await page.route("**/extension/aespa.benchmarking/results", (route) =>
      route.fulfill({ json: [result] }),
    );
    await page.goto(`/#/${routeHash}`);
    const badge = page.getByRole("link", { name: /Evaluated$/ });
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute("href", "#/benchmark-lab/results/10");
    await badge.click();
    await expect(page).toHaveURL(/#\/benchmark-lab\/results\/10$/);
    await expect(page.getByRole("heading", { name: "Saved benchmark scan" })).toBeVisible();
    await expect(page.getByText("GT-1 - SQL injection")).toBeVisible();
    expect(errors).toEqual([]);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-benchmark-badge-${kind}.png`) });
  });
}
