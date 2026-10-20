import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

async function coverageFixtures(page, kind) {
  await installFixtures(page);
  const findings = [
    { id: 7, reference: "F-7", title: "Cell finding", severity: "high" },
    { id: 8, reference: "F-8", title: "Other finding", severity: "low" },
  ].map((finding) => ({
    ...finding,
    validation_status: "confirmed",
    description: `${finding.title} description`,
    owasp_category: "A01",
    owasp_api_category: "API1",
    finding_source: "scanner",
    affected_url: "http://example.test/orders",
    evidence_items: [],
  }));
  const prefix = kind === "api" ? "api-test-runs" : "test-runs";
  await page.route(`**/api/${prefix}/1/findings`, (route) => route.fulfill({ json: findings }));
  const cell = {
    status: "finding",
    finding_ids: [7],
    findings: [findings[0]],
    cell_ids: [11],
    cell_id: 11,
  };
  await page.route(`**/api/${prefix}/1/coverage`, (route) =>
    route.fulfill({
      json:
        kind === "api"
          ? {
              categories: ["API1"],
              totals: { finding: 1 },
              endpoints: [
                { endpoint_id: 1, method: "GET", path: "/orders", cells: { API1: cell } },
              ],
            }
          : {
              seeded: true,
              categories: ["A01"],
              columns: [{ key: "A01", category: "A01", label: "Broken Access Control" }],
              totals: { finding: 1 },
              pages: [
                {
                  page_id: 1,
                  page_ids: [1],
                  url: "http://example.test/orders",
                  cells: { A01: cell },
                },
              ],
            },
    }),
  );
  await page.route("**/api/test-runs/1/workflow-coverage", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            id: 1,
            root_note_id: 1,
            name: "Checkout",
            owasp_category: "A01",
            status: "finding",
            test_kind: "workflow_step_bypass",
            finding_ids: [7],
          },
        ],
      },
    }),
  );
}

for (const kind of ["web", "api", "workflow"]) {
  test(`${kind} coverage opens filtered findings and returns with links and history`, async ({
    page,
  }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await coverageFixtures(page, kind);
    const coverageUrl = kind === "api" ? "/#/api-runs/1/workprogram" : "/#/runs/1/attack";
    await page.goto(coverageUrl);
    if (kind === "workflow")
      await page.getByRole("tab", { name: "Workflows", exact: true }).click();
    const marker = page.locator(".coverage-matrix .cov-cell.has-findings").first();
    await expect(marker).toBeVisible();
    const origin = page.url();
    await marker.click();
    await expect(page).toHaveURL(/\/findings\?/);
    await expect(
      page.locator(".finding-group-row").filter({ hasText: "Cell finding" }),
    ).toBeVisible();
    await expect(
      page.locator(".finding-group-row").filter({ hasText: "Other finding" }),
    ).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Back to coverage" })).toBeVisible();
    await expect(page.locator(".coverage-matrix:visible")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Clear all", exact: true })).toHaveCount(0);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-coverage-findings-${kind}.png`) });
    await page.reload();
    await expect(
      page.locator(".finding-group-row").filter({ hasText: "Cell finding" }),
    ).toBeVisible();
    await expect(
      page.locator(".finding-group-row").filter({ hasText: "Other finding" }),
    ).toHaveCount(0);
    await page.goBack();
    await expect(page).toHaveURL(origin);
    await expect(marker).toBeVisible();
    if (kind === "workflow")
      await expect(page.getByRole("tab", { name: "Workflows" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    await page.goForward();
    await expect(
      page.locator(".finding-group-row").filter({ hasText: "Cell finding" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Back to coverage" }).click();
    await expect(marker).toBeVisible();
    if (kind === "workflow")
      await expect(page.getByRole("tab", { name: "Workflows" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    await marker.click();
    await page.locator(".finding-group-row").filter({ hasText: "Cell finding" }).click();
    await page.getByRole("link", { name: "Finding F-7: Cell finding", exact: true }).click();
    await expect(page.getByText("Cell finding description", { exact: true })).toBeVisible();
    await expect(page).toHaveURL(/finding_ids=/);
    await expect(page.getByRole("link", { name: "Back to coverage" })).toBeVisible();
    await page.getByRole("link", { name: "Show all findings" }).click();
    await expect(
      page.locator(".finding-group-row").filter({ hasText: "Other finding" }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });
}
