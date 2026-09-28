import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures, sast } from "./fixtures.js";

test("preparing source notice sits close to the SAST phase rail", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 576 });
  await installFixtures(page);
  await page.route("**/api/sast-runs/1", (route) =>
    route.fulfill({
      json: {
        ...sast,
        status: "preparing",
        analysis_mode: "light",
        source_provider: "github",
        source_locator: "ledwardchow/bankofed",
      },
    }),
  );

  await page.goto("/#/sast-runs/1/progress");
  const notice = page.locator(".sast-run-preparing .card");
  const phases = page.getByRole("tablist", { name: "SAST scan phases" });
  await expect(notice).toBeVisible();
  await expect(phases).toBeVisible();

  const noticeBounds = await notice.boundingBox();
  const phaseBounds = await phases.boundingBox();
  expect(phaseBounds.y - (noticeBounds.y + noticeBounds.height)).toBeLessThanOrEqual(20);
  expect(phaseBounds.y).toBeGreaterThanOrEqual(noticeBounds.y + noticeBounds.height);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-preparing-layout.png") });
});

test("resolved source revision appears in the SAST run header", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.setViewportSize({ width: 1440, height: 576 });
  await installFixtures(page);
  await page.route("**/api/sast-runs/1", (route) =>
    route.fulfill({
      json: {
        ...sast,
        status: "completed",
        analysis_mode: "light",
        source_provider: "github",
        source_locator: "https://github.com/ledwardchow/bankofed",
        source_revision: "7cc913742c58abcdef",
      },
    }),
  );

  await page.goto("/#/sast-runs/1/coverage");
  await page.getByTitle("Collapse sidebar").click();
  await expect(page).toHaveTitle("AESPA");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  const source = page.locator(".sast-header-source");
  const header = page.locator(".sast-run-topbar");
  const phases = page.getByRole("tablist", { name: "SAST scan phases" });
  await expect(source).toContainText("7cc913742c58");
  await expect(phases).toBeVisible();

  const sourceBounds = await source.boundingBox();
  const headerBounds = await header.boundingBox();
  const phaseBounds = await phases.boundingBox();
  expect(sourceBounds.y).toBeGreaterThanOrEqual(headerBounds.y);
  expect(sourceBounds.y + sourceBounds.height).toBeLessThanOrEqual(
    headerBounds.y + headerBounds.height,
  );
  expect(headerBounds.height).toBeLessThanOrEqual(80);
  expect(phaseBounds.y - (headerBounds.y + headerBounds.height)).toBeLessThanOrEqual(1);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-resolved-source-layout.png") });

  const candidates = page.getByRole("tablist", { name: "SAST run views" }).getByRole("tab", {
    name: "Findings 0",
  });
  await candidates.click();
  await expect(candidates).toHaveAttribute("aria-selected", "true");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(source).toBeVisible();
  await expect(phases).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-resolved-source-mobile.png") });
  expect(errors).toEqual([]);
});
