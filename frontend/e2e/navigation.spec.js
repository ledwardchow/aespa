import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures, run } from "./fixtures.js";

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
  ["#/systems", "Fixture system"],
  ["#/systems/1", "Fixture system"],
  ["#/systems/1/campaigns/1/runs", "Fixture campaign"],
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
  ["#/systems/1/campaigns/1/components", "Fixture campaign"],
  ["#/systems/1/campaigns/1/connections", "Fixture campaign"],
  ["#/systems/1/campaigns/1/review", "Fixture campaign"],
  ["#/systems/1/campaigns/1/findings", "Fixture campaign"],
  ["#/systems/1/campaigns/1/activity", "Fixture campaign"],
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

test("site and SAST navigation rows open from their non-interactive cells", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);

  await page.goto("/#/");
  const siteRow = page.getByRole("row", { name: /Open Fixture site/ });
  await expect(siteRow).toBeVisible();
  await siteRow.focus();
  await expect(siteRow).toBeFocused();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-navigation-row-site.png") });
  await siteRow.locator("td").nth(1).click();
  await expect(page).toHaveURL(/#\/sites\/1$/);
  await expect(page.getByText("Test Runs", { exact: true })).toBeVisible();

  await page.goto("/#/sast-runs");
  const sastRow = page.getByRole("row", { name: /View Fixture SAST/ });
  await expect(sastRow).toBeVisible();
  await sastRow.locator("td").nth(1).click();
  await expect(page).toHaveURL(/#\/sast-runs\/1\/progress$/);
  await expect(page.getByText("Fixture SAST", { exact: true })).toBeVisible();
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("site map groups page and API variants with individual modes", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/test-runs/1/graph", (route) =>
    route.fulfill({
      json: {
        nodes: [
          { id: 1, url: "http://example.test/", depth: 0, in_scope: true },
          { id: 2, url: "http://example.test/assets/logo.svg", depth: 1, in_scope: true },
          { id: 3, url: "http://example.test/account", depth: 1, in_scope: true },
          {
            id: 4,
            url: "http://example.test/api/account?id=123",
            title: "API GET 200 /api/account",
            context: "[API endpoint] Observed GET request during crawl.",
            depth: 1,
            in_scope: true,
          },
          { id: 5, url: "http://example.test/assets/app.js", depth: 1, in_scope: true },
          {
            id: 6,
            url: "http://example.test/api/account?id=456&view=full",
            title: "API GET 200 /api/account",
            context: "[API endpoint] Observed GET request during crawl.",
            depth: 2,
            in_scope: true,
          },
          {
            id: 7,
            url: "http://example.test/orders/123?tab=summary",
            title: "Order 123",
            depth: 1,
            in_scope: true,
          },
          {
            id: 8,
            url: "http://example.test/orders/456?tab=history",
            title: "Order 456",
            depth: 1,
            in_scope: true,
          },
        ],
        links: [
          { source: 1, target: 2 },
          { source: 1, target: 3 },
          { source: 1, target: 4 },
          { source: 1, target: 5 },
          { source: 3, target: 6 },
          { source: 1, target: 7 },
          { source: 1, target: 8 },
          { source: 7, target: 4 },
          { source: 8, target: 6 },
        ],
      },
    }),
  );

  await page.goto("/#/runs/1/sitemap");
  await expect(page).toHaveTitle("AESPA");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);

  const extensionFilter = page.getByLabel("Exclude site map extensions");
  const pageDisplay = page.getByLabel("Page display");
  const apiDisplay = page.getByLabel("API display");
  const displayApis = page.getByRole("checkbox", { name: "Display APIs" });
  const displaySettings = page.getByRole("button", { name: "Display settings" });
  const displayControls = page.locator("#sitemap-display-settings");
  await expect(displaySettings).toHaveAttribute("aria-expanded", "false");
  await expect(displayControls).toBeHidden();
  await expect(extensionFilter).toBeHidden();
  await expect(extensionFilter).toHaveValue(".svg, .js");
  await expect(pageDisplay).toHaveValue("grouped");
  await expect(apiDisplay).toHaveValue("grouped");
  await expect(displayApis).not.toBeChecked();
  await expect(apiDisplay).toBeDisabled();
  const searchBounds = await page.locator(".sitemap-search").boundingBox();
  const apiToggleBounds = await page.locator(".sitemap-api-toggle").boundingBox();
  expect(apiToggleBounds.y).toBeGreaterThanOrEqual(searchBounds.y + searchBounds.height + 4);
  await expect(
    page.getByText("3 shown · 2 pages in 1 routes · 2 APIs hidden · 2 files hidden", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator("g.node-group")).toHaveCount(3);
  await displayApis.check();
  await expect(apiDisplay).toBeEnabled();
  await expect(
    page.getByText(
      "4 shown · 2 pages in 1 routes · 2 API requests in 1 endpoints · 2 files hidden",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.locator("g.node-group")).toHaveCount(4);
  await expect(page.locator(".sitemap-lane-labels")).toHaveCount(0);
  const nodeSearch = page.getByRole("searchbox", { name: "Search site map nodes" });
  await nodeSearch.fill("ORDER 456");
  await expect(page.locator(".sitemap-search-match")).toHaveCount(1);
  await expect(page.locator(".sitemap-search-match")).toContainText("/orders/{id}");
  await expect(page.locator(".sitemap-search [role=status]")).toHaveText("1 match");
  await expect(page.locator("g.node-group")).toHaveCount(4);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-node-search.png") });
  await nodeSearch.fill("no-such-node");
  await expect(page.locator(".sitemap-search-match")).toHaveCount(0);
  await expect(page.locator(".sitemap-search [role=status]")).toHaveText("0 matches");
  await nodeSearch.press("Escape");
  await expect(nodeSearch).toHaveValue("");
  await nodeSearch.fill("account");
  await expect(page.locator(".sitemap-search-match")).toHaveCount(2);
  await page.getByRole("button", { name: "Clear node search" }).click();
  await expect(page.locator(".sitemap-search-match")).toHaveCount(0);

  await page.screenshot({ path: path.join(tmpdir(), "aespa-sitemap-settings-collapsed.png") });

  await displaySettings.click();
  await expect(displaySettings).toHaveAttribute("aria-expanded", "true");
  await expect(displayControls).toBeVisible();
  await expect(extensionFilter).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sitemap-settings-expanded.png") });
  await displaySettings.click();
  await expect(displayControls).toBeHidden();

  const pageRouteNode = page.locator("g.node-group", { hasText: "/orders/{id}" });
  await expect(pageRouteNode).toBeVisible();
  await pageRouteNode.dispatchEvent("click");
  const pagePanel = page.locator(".page-group-panel");
  await expect(
    pagePanel.locator(".graph-panel-section-label", { hasText: "Page variants" }),
  ).toBeVisible();
  await expect(pagePanel.locator(".api-parameter-row code", { hasText: "id" })).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sitemap-grouped-page-route.png") });

  await page.getByRole("button", { name: "Show individual pages" }).click();
  await expect(pageDisplay).toHaveValue("individual");
  await expect(
    page.getByText("5 shown · 2 API requests in 1 endpoints · 2 files hidden", { exact: true }),
  ).toBeVisible();
  await displaySettings.click();
  await pageDisplay.selectOption("grouped");
  await expect(page.locator("g.node-group")).toHaveCount(4);
  await displaySettings.click();

  const apiNode = page.locator("g.node-group", { hasText: "GET /api/account" });
  await expect(apiNode).toBeVisible();
  await apiNode.dispatchEvent("click");
  const apiPanel = page.locator(".api-group-panel");
  await expect(
    apiPanel.locator(".graph-panel-section-label", { hasText: "Request variants" }),
  ).toBeVisible();
  await expect(
    apiPanel.locator(".graph-panel-section-label", { hasText: "Calling pages" }),
  ).toBeVisible();
  await expect(apiPanel.locator(".api-parameter-row code", { hasText: "id" })).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sitemap-grouped-api.png") });

  await page.getByRole("button", { name: "Show individual requests" }).click();
  await expect(apiDisplay).toHaveValue("individual");
  await expect(
    page.getByText("5 shown · 2 pages in 1 routes · 2 files hidden", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("g.node-group")).toHaveCount(5);

  await displaySettings.click();
  await displayApis.uncheck();
  await expect(apiDisplay).toBeDisabled();
  await expect(apiDisplay).toHaveValue("individual");
  await expect(apiPanel).toBeHidden();
  await expect(page.locator(".graph-panel")).toBeHidden();
  await expect(
    page.getByText("3 shown · 2 pages in 1 routes · 2 APIs hidden · 2 files hidden", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator("g.node-group")).toHaveCount(3);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-apis-hidden.png") });

  await extensionFilter.fill("");
  await expect(
    page.getByText("5 shown · 2 pages in 1 routes · 2 APIs hidden", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("g.node-group")).toHaveCount(5);
  await displayApis.check();
  await expect(apiDisplay).toBeEnabled();
  await expect(apiDisplay).toHaveValue("individual");
  await expect(page.locator("g.node-group")).toHaveCount(7);
  expect(errors).toEqual([]);
});

test("multi-user crawl progress expands and collapses", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route(/\/api\/test-runs\/1(?:\?.*)?$/, (route) =>
    route.fulfill({
      json: {
        ...run,
        status: "complete",
        phase: "complete",
        credentials: [
          { id: 1, username: "alice@example.test", label: "Alice" },
          { id: 2, username: "bob@example.test", label: "Bob" },
        ],
        per_user_progress: {
          "alice@example.test": {
            pages_visited: 3,
            current_url: "http://example.test/account",
            done: false,
          },
          "bob@example.test": { pages_visited: 2, current_url: null, done: true },
        },
      },
    }),
  );

  await page.goto("/#/runs/1/sitemap");
  await expect(page).toHaveTitle("AESPA");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);

  const toggle = page.getByRole("button", { name: "User crawl progress" });
  const details = page.locator("#crawl-user-progress-details");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(details).toBeHidden();
  await expect(page.getByText("2 users · 5 pages · 1 done", { exact: true })).toBeVisible();
  const displayToggle = page.getByRole("button", { name: "Display settings" });
  const progressBounds = await toggle.boundingBox();
  const displayBounds = await displayToggle.boundingBox();
  expect(Math.abs(progressBounds.y - displayBounds.y)).toBeLessThan(2);
  const barBounds = await page.locator(".sitemap-filter-panel").boundingBox();
  expect(barBounds.height).toBeLessThan(70);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-user-progress-collapsed.png") });

  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(details).toBeVisible();
  await expect(details.getByText("Alice", { exact: true })).toBeVisible();
  await expect(details.getByText("Bob", { exact: true })).toBeVisible();
  await expect(details.getByText("3 pg", { exact: true })).toBeVisible();
  await expect(details.getByText("done", { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-user-progress-expanded.png") });

  await displayToggle.click();
  await expect(page.getByLabel("Page display")).toBeVisible();
  await expect(details).toBeVisible();
  const detailsBounds = await details.boundingBox();
  const settingsBounds = await page.locator("#sitemap-display-settings").boundingBox();
  expect(settingsBounds.y).toBeGreaterThanOrEqual(detailsBounds.y + detailsBounds.height);
  await toggle.click();
  await expect(details).toBeHidden();
  await expect(page.getByLabel("Page display")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(displayToggle).toBeVisible();
  await expect(page.getByLabel("Page display")).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sitemap-toolbar-mobile.png") });
  expect(errors).toEqual([]);
});

test("System Settings groups feature visibility and debug controls into tabs", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/debug");

  const featureTab = page.getByRole("tab", { name: "Feature Visibility", exact: true });
  const debugTab = page.getByRole("tab", { name: "Debug Settings", exact: true });
  await expect(featureTab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText("Browser", { exact: true })).toBeVisible();
  await expect(page.getByText("Reporting Lab", { exact: true })).toBeVisible();
  await expect(page.getByText("Systems", { exact: true })).toBeVisible();
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

test("validator outcomes stay beside their finding titles", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  const agentLog = [
    {
      agent_id: "validator-1809",
      role: "Validator",
      status: "done",
      current_task: "Registration permits one-character passwords",
      outcome: "Confirmed",
      created_at: "2026-09-08T00:00:00Z",
    },
    {
      agent_id: "validator-1810",
      role: "Validator",
      status: "done",
      current_task: "Profile API exposes password hash and TOTP field",
      outcome: "Unconfirmed",
      created_at: "2026-09-08T00:00:01Z",
    },
  ];
  await page.route("**/api/test-runs/1/agent-log", (route) => route.fulfill({ json: agentLog }));
  await page.goto("/#/runs/1/activity");
  await expect(page).toHaveURL(/#\/runs\/1\/activity$/);
  await expect(page).toHaveTitle("AESPA");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  const validator = page.locator(".agent-row", { hasText: "Validator" });
  for (const label of ["Confirmed", "Unconfirmed"]) {
    const outcome = validator.getByText(label, { exact: true });
    const row = outcome.locator("..");
    await expect(row).toBeVisible();
    const taskBox = await row.locator(".agent-current-task").boundingBox();
    const outcomeBox = await outcome.boundingBox();
    const overlap =
      Math.min(taskBox.y + taskBox.height, outcomeBox.y + outcomeBox.height) -
      Math.max(taskBox.y, outcomeBox.y);
    expect(overlap).toBeGreaterThan(0);
  }

  await validator.click();
  await expect(validator.locator(".agent-thread-row")).toHaveCount(0);
  await validator.click();
  await expect(validator.locator(".agent-thread-row")).toHaveCount(2);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-validator-outcome-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByText("Confirmed", { exact: true })).toBeVisible();
  const mobileUnconfirmed = page.getByText("Unconfirmed", { exact: true });
  await expect(mobileUnconfirmed).toBeVisible();
  await mobileUnconfirmed.scrollIntoViewIfNeeded();
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-validator-outcome-mobile.png") });
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

test("SAST summary cards only appear on the Coverage tab", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.goto("/#/sast-runs/1/coverage");

  const summary = page.locator(".sast-run-summary-grid");
  const viewTabs = page.getByRole("tablist", { name: "SAST run views" });
  await expect(page).toHaveURL(/#\/sast-runs\/1\/coverage$/);
  await expect(page).toHaveTitle("AESPA");
  await expect(page.getByText("Fixture SAST", { exact: true })).toBeVisible();
  await expect(summary).toBeVisible();
  await expect(summary.locator(":scope > div")).toHaveCount(7);

  for (const tabName of [
    "Model",
    /^Threats/,
    /^Security checks/,
    "Execution Summary",
    /^Candidates/,
    "Activity",
  ]) {
    await viewTabs.getByRole("tab", { name: tabName }).click();
    await expect(summary).toHaveCount(0);
  }

  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-no-summary.png") });
  await viewTabs.getByRole("tab", { name: "Coverage", exact: true }).click();
  await expect(summary).toBeVisible();
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-coverage-summary.png") });
});

test("light SAST phases fill the available progress row", async ({ page }) => {
  await installFixtures(page);
  await page.route("**/api/sast-runs/1", (route) =>
    route.fulfill({
      json: {
        id: 1,
        name: "Fixture SAST",
        status: "pending",
        phase: "scope",
        analysis_mode: "light",
        llm_profile_id: 1,
        leads_count: 0,
        source_filename: "fixture.zip",
      },
    }),
  );
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/#/sast-runs/1/coverage");

  const rail = page.getByRole("tablist", { name: "SAST scan phases" });
  const phases = rail.getByRole("tab");
  await expect(phases).toHaveCount(5);
  await expect
    .poll(async () => {
      const railBox = await rail.boundingBox();
      const lastBox = await phases.last().boundingBox();
      if (!railBox || !lastBox) return Infinity;
      return Math.abs(railBox.x + railBox.width - (lastBox.x + lastBox.width));
    })
    .toBeLessThan(1);

  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-light-phase-width.png") });
});

test("a running SAST scan explains that semantic analysis is still being generated", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/sast-runs/1/scan/status", (route) =>
    route.fulfill({ json: { running: true, status: "running", resumable: false } }),
  );

  await page.goto("/#/sast-runs/1/efficiency");
  await expect(page).toHaveTitle("AESPA");
  await expect(page.getByRole("tab", { name: "Execution Summary", exact: true })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByText("Efficiency telemetry is being collected.")).toBeVisible();
  await expect(
    page.getByText(
      "This analysis will appear after the scan finishes and the final report is ready.",
    ),
  ).toBeVisible();
  await expect(page.getByText(/Run the scan again with the current SAST workflow/)).toHaveCount(0);

  await page.getByRole("tab", { name: /^Threats/ }).click();
  await expect(page.getByText("Threat model is not ready yet.")).toBeVisible();
  await expect(page.getByText("This analysis will appear as the scan progresses.")).toBeVisible();
  await expect(page.getByText(/Run the scan again with the current SAST workflow/)).toHaveCount(0);

  await page.getByRole("tab", { name: /^Security checks/ }).click();
  await expect(page.getByText("Security check analysis is not ready yet.")).toBeVisible();
  await expect(page.getByText("This analysis will appear as the scan progresses.")).toBeVisible();
  await expect(page.getByText(/Run the scan again with the current SAST workflow/)).toHaveCount(0);
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-analysis-running.png") });
});

test("the SAST agent list scrolls without an enclosing activity box", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  const workers = Array.from({ length: 28 }, (_, index) => ({
    id: index + 1,
    agent_id: `sast-worker-${index + 1}`,
    role: "SAST Injection Worker",
    status: "complete",
    current_task: `Completed assigned checks ${index + 1}`,
    display_name: `injection-worker-${index + 1}`,
    class_group: "injection",
    created_at: "2026-09-11T01:00:00Z",
  }));
  await page.route("**/api/sast-runs/1/agent-log", (route) => route.fulfill({ json: workers }));
  await page.setViewportSize({ width: 1100, height: 650 });
  await page.goto("/#/sast-runs/1/activity");

  const activityPanel = page.locator(".sast-activity-panel");
  const agentList = page.locator(".sast-agents-panel");
  await expect(page.getByRole("button", { name: "Agents" })).toBeVisible();
  await expect(page.locator(".sast-run-content")).toHaveCSS("padding-left", "0px");
  await expect(activityPanel).toHaveCSS("border-top-width", "0px");
  await expect
    .poll(() => agentList.evaluate((element) => element.scrollHeight > element.clientHeight))
    .toBe(true);

  await agentList.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await expect.poll(() => agentList.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  await expect(page.getByText("injection-worker-28", { exact: true })).toBeVisible();
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-agents-scroll.png") });
});

test("Deep work queue groups checks under an expandable operation", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/test-runs/1", (route) =>
    route.fulfill({
      json: {
        id: 1,
        site_id: 1,
        name: "Fixture Deep run",
        status: "complete",
        phase: "finished",
        thinking_status: "complete",
        coverage_mode: "deep",
        scope_hosts: [],
        per_user_progress: [],
        llm_profile_id: 1,
      },
    }),
  );
  await page.route("**/api/test-runs/1/deep-queue", (route) =>
    route.fulfill({
      json: {
        total: 1,
        checks_total: 2,
        planning: { total: 1, complete: 1, active: 0, pending: 0 },
        counts: { finding: 1 },
        tasks: [
          {
            id: 42,
            task_kind: "operation",
            status: "finding",
            title: "Test GET http://example.test/api/accounts/{id}",
            http_method: "GET",
            target_url: "http://example.test/api/accounts/12?search=Ada",
            route_template: "http://example.test/api/accounts/{id}",
            inputs: ["account_id", "search"],
            identities: ["user_a_vs_user_b"],
            finding_count: 1,
            priority: 9,
            checks: [
              {
                id: 1,
                attack_class: "idor",
                owasp_category: "A01",
                parameter: "account_id",
                session_label: "user_a_vs_user_b",
                status: "finding",
                hypothesis: "Compare account ownership across two users.",
              },
              {
                id: 2,
                attack_class: "sqli",
                owasp_category: "A03",
                parameter: "search",
                status: "complete",
                hypothesis: "Compare a quote probe with the baseline.",
              },
            ],
          },
        ],
      },
    }),
  );

  await page.goto("/#/runs/1/activity");
  await page.getByRole("button", { name: "Work Queue", exact: true }).click();
  await expect(page.getByText("1 testers", { exact: false })).toBeVisible();
  const task = page.locator(".deep-task-toggle");
  await expect(task.getByText("Tester 1 · operation", { exact: true })).toBeVisible();
  await expect(task.getByText("#42 operation", { exact: true })).toHaveCount(0);
  await expect(task).toHaveAttribute("aria-expanded", "false");
  await expect(task.getByText("2 inputs", { exact: true })).toBeVisible();
  await expect(task.getByText("1 identity comparison", { exact: true })).toBeVisible();
  await task.click();
  await expect(page.getByText("Compare account ownership across two users.")).toBeVisible();
  await expect(page.getByText("Compare a quote probe with the baseline.")).toBeVisible();
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-deep-grouped-queue.png") });
});

test("site map controls remain reachable across widths", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await installFixtures(page);
  await page.route(/\/api\/test-runs\/1(?:\?.*)?$/, (route) =>
    route.fulfill({
      json: {
        ...run,
        status: "complete",
        phase: "complete",
        pages_discovered: 286,
        max_depth: 3,
        max_pages: 500,
        credentials: ["staff", "manager", "admin"].map((username, id) => ({
          id: id + 1,
          username,
        })),
        per_user_progress: Object.fromEntries(
          ["staff", "manager", "admin"].map((name) => [name, { pages_visited: 123, done: true }]),
        ),
      },
    }),
  );
  await page.route("**/api/test-runs/1/graph", (route) =>
    route.fulfill({
      json: {
        nodes: [
          ...Array.from({ length: 20 }, (_, id) => ({
            id: id + 1,
            url: `http://example.test/orders/${id + 1}`,
            depth: 1,
            in_scope: true,
          })),
          ...Array.from({ length: 20 }, (_, id) => ({
            id: id + 21,
            url: `http://example.test/api/orders/${id + 1}`,
            title: "API GET 200 /api/orders",
            context: "[API endpoint] Observed GET request during crawl.",
            depth: 1,
            in_scope: true,
          })),
        ],
        links: [],
      },
    }),
  );
  await page.goto("/#/runs/1/sitemap");
  await expect(page).toHaveTitle("AESPA");
  await expect(page.getByRole("button", { name: "User crawl progress" })).toBeVisible();
  for (const width of [2560, 1440, 1100, 900, 768, 640, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    if (await page.getByLabel("Run section").isVisible()) {
      await expect(page.getByLabel("Run section").locator("option")).toHaveCount(7);
    } else {
      await expect(page.locator(".web-run-tab-links button:visible")).toHaveCount(7);
    }
    const overflow = await page
      .locator(".web-run-tab-bar, .sitemap-filter-panel, .sitemap-meta, .scope-hosts-panel")
      .evaluateAll((elements) =>
        elements.filter((el) => el.scrollWidth > el.clientWidth + 1).map((el) => el.className),
      );
    expect(overflow, `overflow at ${width}px`).toEqual([]);
    for (const selector of [
      ".web-run-tab-links button",
      ".web-run-tab-actions button",
      ".sitemap-filter-summary .traffic-count-label",
      ".crawl-user-progress-count",
    ]) {
      for (const element of await page.locator(selector).all()) {
        if (!(await element.isVisible())) continue;
        const bounds = await element.boundingBox();
        expect(bounds.x).toBeGreaterThanOrEqual(0);
        expect(bounds.x + bounds.width).toBeLessThanOrEqual(width + 1);
      }
    }
    await page.getByRole("button", { name: "Display settings" }).click();
    await expect(page.getByLabel("API display")).toBeVisible();
    if (width > 1100) {
      const stats = await page.locator(".sitemap-meta > .run-stat").all();
      for (const stat of stats) {
        const bounds = await stat.boundingBox();
        expect(bounds.width, `stat width at ${width}px`).toBeLessThan(250);
      }
      const input = await page.getByLabel("Exclude site map extensions").boundingBox();
      expect(input.width).toBeLessThan(200);
    }
    await page.screenshot({ path: path.join(tmpdir(), `aespa-responsive-${width}.png`) });
    await page.getByRole("button", { name: "Display settings" }).click();
  }
  await page.getByRole("button", { name: "By User", exact: true }).click();
  await expect(page.getByRole("button", { name: "By User", exact: true })).toHaveClass(/active/);
  await page.getByLabel("Run section").selectOption({ label: "SAST Leads" });
  await expect(page.getByLabel("Run section")).toHaveValue("leads");
  expect(errors).toEqual([]);
});
