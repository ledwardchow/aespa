import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures, sast } from "./fixtures.js";

test("SAST findings use one full-width reading area", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await installFixtures(page);
  await page.route("**/api/sast-runs/1", (route) =>
    route.fulfill({ json: { ...sast, analysis_mode: "light", status: "completed" } }),
  );
  await page.route("**/api/sast-runs/1/leads", (route) =>
    route.fulfill({
      json: [
        {
          id: 1,
          reference: "SAST-1",
          title: "Authorization check missing on order lookup",
          severity: "high",
          location: "src/api/orders.py:84",
          confidence: 0.93,
          validation_status: "confirmed",
          reportable: true,
          description: "The order lookup reads an order by ID without checking its owner.",
          evidence: "order = db.get(Order, order_id)\nreturn order",
        },
        {
          id: 2,
          reference: "SAST-2",
          title: "Untrusted redirect URL",
          severity: "medium",
          location: "src/auth/login.py:142",
          confidence: 0.71,
          validation_status: "inconclusive",
          reportable: false,
          description: "The redirect destination comes from a request parameter.",
        },
      ],
    }),
  );
  await page.route("**/api/sast-runs/1/live-targets", (route) =>
    route.fulfill({
      json: [
        { target_type: "site", target_id: 4, name: "Shop", url: "https://shop.test" },
        {
          target_type: "api_collection",
          target_id: 5,
          name: "Shop API",
          url: "https://api.shop.test",
        },
      ],
    }),
  );

  await page.goto("/#/sast-runs/1/candidates");
  const content = page.locator(".sast-run-content");
  const list = page.locator(".sast-candidate-ledger");
  await expect(list).toBeVisible();
  const contentBounds = await content.boundingBox();
  const listBounds = await list.boundingBox();
  expect(listBounds.width).toBeGreaterThan(contentBounds.width - 40);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-findings-list.png") });

  await page.getByRole("button", { name: "Export findings ↓" }).click();
  await expect(page.getByRole("menuitem", { name: "Export Markdown" })).toBeVisible();
  await expect(page.getByRole("menuitem", { name: "Export SARIF" })).toHaveAttribute(
    "href",
    "/api/sast-runs/1/sarif",
  );
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: /Authorization check missing on order lookup/ }).click();
  await expect(list).toBeHidden();
  await expect(
    page.getByRole("heading", { name: "Authorization check missing on order lookup" }),
  ).toBeVisible();
  const detail = page.locator(".sast-evidence-panel");
  const detailBounds = await detail.boundingBox();
  expect(detailBounds.width).toBeGreaterThan(contentBounds.width - 40);
  const bodyBounds = await page.locator(".sast-evidence-body").boundingBox();
  const writeupBounds = await page.locator(".sast-lead-details").boundingBox();
  expect(writeupBounds.width).toBeGreaterThan(bodyBounds.width - 50);
  await expect(page.getByRole("combobox", { name: "Application for live testing" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create test run" })).toBeDisabled();
  await page.getByRole("combobox", { name: "Application for live testing" }).selectOption("site:4");
  await expect(page.getByRole("button", { name: "Create test run" })).toBeEnabled();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-finding-detail.png") });

  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByRole("heading", { name: "Untrusted redirect URL" })).toBeVisible();
  await page.getByRole("button", { name: "← Back to findings" }).click();
  await expect(list).toBeVisible();

  let createdFor = null;
  await page.route("**/api/sast-runs/1/leads/1/live-test-runs", async (route) => {
    createdFor = route.request().postDataJSON();
    await route.fulfill({ status: 201, json: { run_type: "web", run_id: 42, lead_id: 10 } });
  });
  await page.getByRole("button", { name: /Authorization check missing on order lookup/ }).click();
  await page.getByRole("combobox", { name: "Application for live testing" }).selectOption("site:4");
  await page.getByRole("button", { name: "Create test run" }).click();
  await expect(page).toHaveURL(/#\/runs\/42/);
  expect(createdFor).toEqual({ target_type: "site", target_id: 4 });
});
