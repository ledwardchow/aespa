import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

const screens = [
  ["#/", "Fixture site"],
  ["#/sites/1", "Fixture site"],
  ["#/sites/new", "New Site"],
  ["#/settings", "LLM Profiles"],
  ["#/scan-policy", "Agent Settings"],
  ["#/external-integrations", "External Integrations"],
  ["#/apis", "Fixture API"],
  ["#/apis/1", "Fixture API"],
  ["#/apis/new", "New API"],
  ["#/sast-runs", "Fixture SAST"],
  ["#/sast-runs/1/coverage", "Fixture SAST"],
  ["#/sast-runs/1/candidates", "Fixture SAST"],
  ["#/sast-runs/1/activity", "Fixture SAST"],
  ["#/applications", "Fixture application"],
  ["#/applications/1", "Fixture application"],
  ["#/applications/1/campaigns/1/runs", "Fixture campaign"],
  ["#/api-runs/1/findings", "Fixture run"],
  ["#/api-runs/1/status", "Fixture run"],
  ["#/runs/1/findings", "Fixture run"],
  ["#/runs/1/activity", "Fixture run"],
  ["#/api-runs/1/leads", "Fixture run"],
  ["#/api-runs/1/sessions", "Fixture run"],
  ["#/api-runs/1/traffic", "Fixture run"],
  ["#/api-runs/1/endpoints", "Fixture run"],
  ["#/api-runs/1/workprogram", "Fixture run"],
  ["#/runs/1/sitemap", "Fixture run"],
  ["#/runs/1/attack", "Fixture run"],
  ["#/runs/1/traffic", "Fixture run"],
  ["#/runs/1/sessions", "Fixture run"],
  ["#/runs/1/leads", "Fixture run"],
  ["#/applications/1/campaigns/1/components", "Fixture campaign"],
  ["#/applications/1/campaigns/1/connections", "Fixture campaign"],
  ["#/applications/1/campaigns/1/review", "Fixture campaign"],
  ["#/applications/1/campaigns/1/findings", "Fixture campaign"],
  ["#/applications/1/campaigns/1/activity", "Fixture campaign"],
];
for (const [route, text] of screens) {
  test(`${route} renders without runtime errors`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    await installFixtures(page);
    await page.goto(`/${route}`);
    await expect(page).toHaveTitle("AESPA");
    await expect(page.getByText(text, { exact: false }).first()).toBeVisible();
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    await expect(page.getByText("This page could not be loaded")).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}

test("settings tabs, edit cancellation, and sidebar history work", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/settings");
  await page.getByRole("tab", { name: "Providers", exact: true }).click();
  await expect(page.getByText("Fixture provider", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByText("Edit LLM Provider", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByText("LLM Providers", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Sites", exact: true }).click();
  await expect(page.getByText("Fixture site", { exact: true }).first()).toBeVisible();
  await page.goBack();
  await expect(page.getByText("LLM Profiles", { exact: true })).toBeVisible();
});

test("System Settings groups feature visibility and debug controls into tabs", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/debug");

  const featureTab = page.getByRole("tab", { name: "Feature Visibility", exact: true });
  const debugTab = page.getByRole("tab", { name: "Debug Settings", exact: true });
  await expect(featureTab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText("Browser", { exact: true })).toBeVisible();
  await expect(page.getByText("Reporting Lab", { exact: true })).toBeVisible();
  await expect(page.getByText("Applications", { exact: true })).toBeVisible();
  await expect(page.getByText("Sitemap Graph", { exact: true })).toHaveCount(0);

  await debugTab.click();
  await expect(debugTab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText("Sitemap Graph", { exact: true })).toBeVisible();
  await expect(page.getByText("Cloudflare Access", { exact: true })).toBeVisible();
  await expect(page.getByText("Browser", { exact: true })).toHaveCount(0);
});

test("headless Linux disables browser windows and guided login", async ({ page }) => {
  const message =
    "No graphical display is available. Guided login and visible browser mode are disabled. Set DISPLAY or WAYLAND_DISPLAY, then restart AESPA.";
  await installFixtures(page);
  await page.route("**/api/settings/browser-debug", (route) =>
    route.fulfill({
      json: {
        browser_engine: "playwright_chromium",
        browser_visible: false,
        graphical_display_available: false,
        graphical_display_message: message,
      },
    }),
  );

  await page.goto("/#/debug");
  await expect(page.getByRole("checkbox", { name: "Make browser visible to user" })).toBeDisabled();
  await expect(page.getByText(message, { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-headless-browser-settings.png") });

  await page.goto("/#/sites/new");
  await page.getByRole("checkbox", { name: "This site requires authentication" }).check();
  await page.getByRole("button", { name: "Add credential" }).click();
  const authMode = page.locator(".field", { hasText: "Auth Mode" }).locator("select");
  await expect(authMode.locator('option[value="guided"]')).toBeDisabled();
  await expect(page.getByText(message, { exact: true })).toBeVisible();
  await authMode.scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-headless-guided-login.png") });
});

test("Agent Settings keeps inner tabs flush with its content column", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/scan-policy");
  const outer = page.getByRole("tablist", { name: "Agent settings", exact: true });
  await expect(outer).toBeVisible();
  const inner = page.locator(".coverage-sub-tab-bar");
  await expect(inner).toBeVisible();
  const a = await outer.boundingBox(),
    b = await inner.boundingBox();
  expect(Math.abs(a.x - b.x)).toBeLessThan(1);
  expect(Math.abs(a.x + a.width - (b.x + b.width))).toBeLessThan(1);
  await page.getByRole("tab", { name: "Crawler", exact: true }).click();
  await expect(inner).toHaveCount(0);
  await page.getByRole("tab", { name: "Global", exact: true }).click();
  await expect(inner).toBeVisible();
  await expect(page.getByRole("button", { name: "Save policy", exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-agent-settings-desktop.png") });
});

test("Python Sandbox explains when the Docker service is unavailable", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.goto("/#/scan-policy");
  await page.getByRole("tab", { name: "Python Sandbox", exact: true }).click();

  await expect(page.getByText("Runtime unavailable", { exact: true })).toBeVisible();
  await expect(page.getByText(/Docker is installed, but its service is not running/)).toBeVisible();
  await expect(page.getByText(/Build it with:/)).toHaveCount(0);
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-docker-service-unavailable.png") });
});

test("empty sites and a narrow viewport remain usable", async ({ page }) => {
  await installFixtures(page, { empty: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#/");
  await expect(page.getByText("No sites configured")).toBeVisible();
  await expect(page.locator(".sidebar--collapsed")).toBeVisible();
  await page.getByRole("link", { name: "LLM Settings", exact: true }).click();
  await expect(page.getByRole("tab", { name: "Providers", exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Providers", exact: true }).click();
  await expect(page.getByRole("button", { name: "New provider", exact: true })).toBeEnabled();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-settings-mobile.png") });
});

test("a failed request shows a useful error instead of an empty page", async ({ page }) => {
  await installFixtures(page);
  await page.route("**/api/sites", (route) =>
    route.fulfill({ status: 502, contentType: "text/html", body: "<html>Proxy error</html>" }),
  );
  await page.goto("/#/");
  await expect(page.locator(".alert.error")).toContainText("502");
});

test("back and forward restore the selected run tab", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/sast-runs/1/coverage");
  await page.getByRole("tab", { name: /^Candidates/ }).click();
  await page.getByRole("tab", { name: "Activity", exact: true }).click();
  await page.goBack();
  await expect(page.getByRole("tab", { name: /^Candidates/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.goForward();
  await expect(page.getByRole("tab", { name: "Activity", exact: true })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.goto("/#/runs/1/findings");
  await page.getByRole("button", { name: "Traffic Log", exact: true }).click();
  await page.goBack();
  await expect(page.locator(".web-run-tab-bar .active")).toContainText("Findings");
});
