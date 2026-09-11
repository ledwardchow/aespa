import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

const finding = {
  id: 7,
  reference: "WEB-7",
  page_id: null,
  owasp_category: "A01",
  owasp_api_category: "API1",
  severity: "low",
  validation_status: "confirmed",
  title: "Fixture finding",
  affected_url: "http://example.test/item",
  description: "Fixture description",
  impact: "Fixture impact",
  likelihood: "Fixture likelihood",
  recommendation: "Fixture recommendation",
  cvss_score: 2.5,
  cvss_vector: "CVSS:3.1",
  evidence: "Synthetic evidence",
  evidence_items: [],
  evidence_json: "[]",
  finding_source: "manual_import",
  created_at: "2026-09-05T00:00:00Z",
};
async function findingFixtures(page) {
  await installFixtures(page);
  const records = {
    web: { ...finding },
    api: { ...finding, reference: "API-7", title: "API fixture finding" },
  };
  const saves = [];
  await page.route(
    /\/api\/(?:test-runs|api-test-runs)\/1\/findings(?:\/7)?(?:\?.*)?$/,
    async (route) => {
      const api = route.request().url().includes("api-test-runs");
      const kind = api ? "api" : "web";
      if (route.request().method() === "PATCH") {
        const body = route.request().postDataJSON();
        saves.push({ kind, body });
        records[kind] = { ...records[kind], ...body };
        return route.fulfill({ json: records[kind] });
      }
      return route.fulfill({ json: [records[kind]] });
    },
  );
  return { saves };
}
function checkConsole(page) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

// Flow: finding deep link -> edit -> activity tab -> back -> save the retained draft.
test("web finding drafts survive tab switches and activity layout stays flush", async ({
  page,
}) => {
  const errors = checkConsole(page);
  const { saves } = await findingFixtures(page);
  await page.goto("/#/runs/1/findings?finding=WEB-7");
  await expect(page).toHaveTitle("AESPA");
  await expect(page.getByText("Fixture description", { exact: true })).toBeVisible();
  await page.getByTitle("Edit", { exact: true }).click();
  await page.getByLabel("Title", { exact: true }).fill("Retained draft");
  await page.locator(".web-run-tab-bar .tab-btn").filter({ hasText: "Status" }).click();
  await expect(page.getByRole("button", { name: "Log", exact: true })).toBeVisible();
  const bounds = await page.locator(".activity-panel .activity-sub-tab-bar").evaluate((bar) => {
    const parent = bar.closest(".activity-panel").getBoundingClientRect();
    const child = bar.getBoundingClientRect();
    return {
      left: Math.abs(parent.left - child.left),
      right: Math.abs(parent.right - child.right),
    };
  });
  expect(bounds.left).toBeLessThanOrEqual(1);
  expect(bounds.right).toBeLessThanOrEqual(1);
  await page.getByRole("button", { name: "Log", exact: true }).click();
  await expect(page.getByText("No activity yet.", { exact: false })).toBeVisible();
  await expect(page.locator(".activity-panel .activity-sub-tab-btn.active")).toHaveText("Log");
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await page.screenshot({ path: path.join(tmpdir(), "aespa-refactor-activity-desktop.png") });
  await page.locator(".web-run-tab-bar .tab-btn").filter({ hasText: "Findings" }).click();
  await expect(page.getByLabel("Title", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue("Retained draft");
  await expect(page.locator(".web-run-tab-bar .tab-btn.active")).toContainText("Findings");
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await page.screenshot({ path: path.join(tmpdir(), "aespa-refactor-findings-desktop.png") });
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByLabel("Title", { exact: true })).toHaveCount(0);
  expect(saves).toEqual([
    expect.objectContaining({
      kind: "web",
      body: expect.objectContaining({ title: "Retained draft" }),
    }),
  ]);
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("matching web and API IDs keep editing separate and API cancellation works at narrow width", async ({
  page,
}) => {
  const errors = checkConsole(page);
  const { saves } = await findingFixtures(page);
  await page.goto("/#/runs/1/findings?finding=WEB-7");
  await page.getByTitle("Edit", { exact: true }).click();
  await page.getByLabel("Title", { exact: true }).fill("Unsaved web draft");
  await page.evaluate(() => {
    window.location.hash = "#/api-runs/1/findings?finding=API-7";
  });
  await page.getByTitle("Edit finding", { exact: true }).click();
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue("API fixture finding");
  await page.getByLabel("Title", { exact: true }).fill("Discard API draft");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByTitle("Edit finding", { exact: true }).click();
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue("API fixture finding");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByLabel("Title", { exact: true }).fill("API saved title");
  await page.screenshot({ path: path.join(tmpdir(), "aespa-refactor-api-mobile.png") });
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByLabel("Title", { exact: true })).toHaveCount(0);
  expect(saves).toEqual([
    expect.objectContaining({
      kind: "api",
      body: expect.objectContaining({ title: "API saved title" }),
    }),
  ]);
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
});
