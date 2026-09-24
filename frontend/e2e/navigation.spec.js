import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures, model, profile, provider, run } from "./fixtures.js";

const screens = [
  ["#/", "Fixture site"],
  ["#/sites/1", "Fixture site"],
  ["#/sites/new", "New Site"],
  ["#/settings", "LLM Profiles"],
  ["#/scan-policy", "Settings"],
  ["#/external-integrations", "Upstream Proxy"],
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

test("upstream proxy settings are under Global", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/scan-policy");
  await expect(page.getByRole("link", { name: "External Integrations" })).toHaveCount(0);
  await page.getByRole("tab", { name: "Upstream Proxy" }).click();
  await expect(page).toHaveURL(/#\/scan-policy\/global\/proxy$/);
  await expect(page.getByText("Send target requests through an upstream proxy")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("tab", { name: "Upstream Proxy" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const settingsTabs = await page
    .getByRole("tablist", { name: "Settings", exact: true })
    .boundingBox();
  const globalTabs = await page.getByRole("tablist", { name: "Global settings" }).boundingBox();
  expect(globalTabs.x).toBe(settingsTabs.x);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-global-upstream-proxy.png") });
});

test("Settings tabs restore from their URLs and browser history", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/scan-policy");
  await expect(page.getByRole("tab", { name: "Feature Visibility" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.getByRole("tab", { name: "DAST", exact: true }).click();
  await expect(page).toHaveURL(/#\/scan-policy\/dast\/scan-behaviour$/);
  await page.getByRole("tab", { name: "HTTP Headers" }).click();
  await expect(page).toHaveURL(/#\/scan-policy\/dast\/headers$/);
  await page.reload();
  await expect(page.getByRole("tab", { name: "HTTP Headers" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.goBack();
  await expect(page.getByRole("tab", { name: "Scan Behaviour" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.getByRole("tab", { name: "SAST", exact: true }).click();
  await expect(page).toHaveURL(/#\/scan-policy\/sast$/);
  await page.reload();
  await expect(page.getByRole("tab", { name: "SAST", exact: true })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

test("settings tabs, edit cancellation, and sidebar history work", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/settings/profiles");
  await page.getByRole("tab", { name: "Providers", exact: true }).click();
  await expect(page).toHaveURL(/#\/settings\/providers$/);
  await expect(page.getByText("Fixture provider", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page).toHaveURL(/#\/settings\/providers\/1\/edit$/);
  await expect(page.getByText("Edit LLM Provider", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page).toHaveURL(/#\/settings\/providers$/);
  await expect(page.getByText("LLM Providers", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Sites", exact: true }).click();
  await expect(page.getByText("Fixture site", { exact: true }).first()).toBeVisible();
  await page.goBack();
  await expect(page.getByText("LLM Providers", { exact: true })).toBeVisible();
});

test("provider list shows and sorts configured model counts", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/settings/llm/providers", (route) =>
    route.fulfill({
      json: [
        { ...provider, id: 1, name: "One configured", models: ["available-a", "available-b"] },
        { ...provider, id: 2, name: "Two configured", models: ["available-c"] },
      ],
    }),
  );
  await page.route("**/api/settings/llm/model-configs", (route) =>
    route.fulfill({
      json: [
        { id: 1, provider_id: 1, model: "available-a" },
        { id: 2, provider_id: 2, model: "available-c" },
        { id: 3, provider_id: 2, model: "custom-model" },
      ],
    }),
  );
  await page.goto("/#/settings/providers");

  const rows = page.locator(".settings-list-row");
  await expect(page.getByText("Configured models", { exact: true })).toBeVisible();
  await expect(
    rows.filter({ hasText: "One configured" }).locator(":scope > div").nth(3),
  ).toHaveText("1");
  await expect(
    rows.filter({ hasText: "Two configured" }).locator(":scope > div").nth(3),
  ).toHaveText("2");
  await expect(page.getByText("available-a", { exact: true })).toHaveCount(0);

  await page.getByText("Configured models", { exact: true }).click();
  await expect(rows.first()).toContainText("One configured");
  await page.getByText(/Configured models/).click();
  await expect(rows.first()).toContainText("Two configured");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-provider-model-counts.png") });
});

test("each LLM settings page loads from its URL without a Models tab", async ({ page }) => {
  await installFixtures(page);
  const pages = [
    ["/#/settings/profiles", "LLM Profiles"],
    ["/#/settings/profiles/new", "New LLM Profile"],
    ["/#/settings/profiles/1/edit", "Edit LLM Profile"],
    ["/#/settings/providers", "LLM Providers"],
    ["/#/settings/providers/new", "New LLM Provider"],
    ["/#/settings/providers/1/edit", "Edit LLM Provider"],
    ["/#/settings/models/1/edit", "Edit LLM Model"],
    ["/#/settings/models/new?provider_id=1&model=fixture-model", "New LLM Model"],
  ];
  for (const [url, title] of pages) {
    await page.goto(url);
    await expect(page.getByText(title, { exact: true })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Models", exact: true })).toHaveCount(0);
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  }
});

test("provider models use a table and open their model configuration", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/settings/llm/providers", (route) =>
    route.fulfill({ json: [{ ...provider, models: ["aaa-unconfigured", "fixture-model"] }] }),
  );
  await page.goto("/#/settings");
  await page.getByRole("tab", { name: "Providers", exact: true }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();

  const apiKey = page.getByLabel("API Key (optional)");
  const modelTable = page.getByRole("table");
  await expect(apiKey).toBeVisible();
  await expect(modelTable).toBeVisible();
  await expect(page.getByText("No model configured", { exact: true })).toHaveCount(0);
  await expect(modelTable.locator("tbody tr").first()).toContainText("fixture-model");
  await expect(modelTable.getByText("Used by: Fixture profile", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove fixture-model" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Remove aaa-unconfigured" })).toBeEnabled();
  const apiKeyBounds = await apiKey.boundingBox();
  const modelTableBounds = await modelTable.boundingBox();
  expect(apiKeyBounds.y).toBeLessThan(modelTableBounds.y);
  await page.screenshot({
    path: path.join(tmpdir(), "aespa-provider-model-table.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "fixture-model", exact: true }).click();
  await expect(page).toHaveURL(/#\/settings\/models\/1\/edit$/);
  await expect(page.getByText("Edit LLM Model", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("fixture-model");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-provider-model-configuration.png") });

  await page.getByRole("tab", { name: "Providers", exact: true }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "aaa-unconfigured", exact: true }).click();
  await expect(page).toHaveURL(/#\/settings\/models\/new\?provider_id=1&model=aaa-unconfigured$/);
  await expect(page.getByText("New LLM Model", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("aaa-unconfigured");
});

test("loading provider models keeps models used by scan profiles", async ({ page }) => {
  const errors = [];
  const savedPayloads = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/settings/llm/model-configs", (route) =>
    route.fulfill({ json: [model] }),
  );
  await page.route("**/api/settings/llm/profiles", (route) => route.fulfill({ json: [profile] }));
  await page.route("**/api/settings/llm/discover-model-options", (route) =>
    route.fulfill({
      json: {
        models: ["new-api-model"],
        capabilities: { "new-api-model": { context_window_tokens: 128000 } },
      },
    }),
  );
  await page.route("**/api/settings/llm/providers/1", async (route) => {
    const body = route.request().postDataJSON();
    savedPayloads.push(body);
    await route.fulfill({ json: { ...provider, ...body, id: 1 } });
  });

  await page.goto("/#/settings/providers/1/edit");
  await expect(page).toHaveURL(/#\/settings\/providers\/1\/edit$/);
  await expect(page.getByText("Edit LLM Provider", { exact: true })).toBeVisible();
  await expect(page.getByText("Used by: Fixture profile", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Load models from API" }).click();

  await expect(page.getByRole("button", { name: "new-api-model", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "fixture-model", exact: true })).toBeVisible();
  await expect(
    page.getByText("Kept 1 model(s) used by scan profiles.", { exact: false }),
  ).toBeVisible();
  expect(savedPayloads).toHaveLength(1);
  expect(savedPayloads[0].models).toEqual(["new-api-model", "fixture-model"]);
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({
    path: path.join(tmpdir(), "aespa-provider-load-models-keeps-profile-model.png"),
    fullPage: true,
  });
});

test("provider without a configured model shows a setup prompt", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/settings/llm/model-configs", (route) => route.fulfill({ json: [] }));
  await page.goto("/#/settings/providers/1/edit");

  await expect(page.getByText("No model configured", { exact: true })).toBeVisible();
  await expect(page.getByText(/Configure a model before using this provider/)).toBeVisible();
  await page.screenshot({
    path: path.join(tmpdir(), "aespa-provider-model-prompt.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Configure model", exact: true }).click();
  await expect(page).toHaveURL(/#\/settings\/models\/new\?provider_id=1&model=fixture-model$/);
  await expect(page.getByText("New LLM Model", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("fixture-model");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
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

test("Settings groups feature visibility and debug controls under Global", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/scan-policy");

  const featureTab = page.getByRole("tab", { name: "Feature Visibility", exact: true });
  const debugTab = page.getByRole("tab", { name: "Debug Settings", exact: true });
  await expect(featureTab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText("Browser", { exact: true })).toBeVisible();
  await expect(page.getByText("Reporting Lab", { exact: true })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Systems scanning", exact: true })).toBeVisible();
  await expect(page.getByText("Sitemap Graph", { exact: true })).toHaveCount(0);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-settings-global.png") });

  await debugTab.click();
  await expect(debugTab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText("Sitemap Graph", { exact: true })).toBeVisible();
  await expect(page.getByText("Cloudflare Access", { exact: true })).toBeVisible();
  await expect(page.getByText("Browser", { exact: true })).toHaveCount(0);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-settings-debug.png") });
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

test("Settings keeps inner tabs flush with its content column", async ({ page }) => {
  await installFixtures(page);
  await page.goto("/#/scan-policy");
  const outer = page.getByRole("tablist", { name: "Settings", exact: true });
  await expect(outer).toBeVisible();
  const inner = page.locator(".coverage-sub-tab-bar");
  await expect(inner).toBeVisible();
  const a = await outer.boundingBox(),
    b = await inner.boundingBox();
  expect(Math.abs(a.x - b.x)).toBeLessThan(1);
  expect(Math.abs(a.x + a.width - (b.x + b.width))).toBeLessThan(1);
  await page.getByRole("tab", { name: "DAST", exact: true }).click();
  await expect(page.getByRole("tab", { name: "Scan Behaviour", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "HTTP Headers", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save policy", exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-settings-desktop.png") });
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
  await page.getByRole("link", { name: "LLM Configuration", exact: true }).click();
  await expect(page.getByRole("tab", { name: "Providers", exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Providers", exact: true }).click();
  await expect(page.getByRole("button", { name: "New provider", exact: true })).toBeEnabled();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-settings-mobile.png") });
});

test("the site test-run list uses its content height up to the remaining viewport height", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  const runs = Array.from({ length: 18 }, (_, index) => ({
    ...run,
    id: index + 1,
    name: `Run ${String(index + 1).padStart(2, "0")}`,
    pages_discovered: index + 1,
    created_at: `2026-09-${String(index + 1).padStart(2, "0")}T01:00:00Z`,
  }));
  await page.route("**/api/sites/1/test-runs", (route) => route.fulfill({ json: runs }));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/#/sites/1");

  await expect(page).toHaveTitle("AESPA");
  await expect(page.locator(".topbar-title")).toContainText("Fixture site");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);

  const measurements = await page.locator(".site-detail-content").evaluate((content) => {
    const table = content.querySelector(".site-runs-table");
    const contentBox = content.getBoundingClientRect();
    const tableBox = table.getBoundingClientRect();
    const paddingBottom = Number.parseFloat(getComputedStyle(content).paddingBottom);
    return {
      bottomGap: contentBox.bottom - paddingBottom - tableBox.bottom,
      tableHeight: tableBox.height,
    };
  });
  expect(measurements.bottomGap).toBeLessThanOrEqual(1);
  expect(measurements.tableHeight).toBeGreaterThan(600);

  await expect(page.locator("tbody tr").first()).toContainText("Run 18");
  await page.getByRole("columnheader", { name: /Created/ }).click();
  await expect(page.locator("tbody tr").first()).toContainText("Run 01");
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-site-runs-full-height.png") });

  await page.setViewportSize({ width: 900, height: 700 });
  const narrowBottomGap = await page.locator(".site-detail-content").evaluate((content) => {
    const table = content.querySelector(".site-runs-table");
    const contentBox = content.getBoundingClientRect();
    const tableBox = table.getBoundingClientRect();
    const paddingBottom = Number.parseFloat(getComputedStyle(content).paddingBottom);
    return contentBox.bottom - paddingBottom - tableBox.bottom;
  });
  expect(narrowBottomGap).toBeLessThanOrEqual(1);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-site-runs-narrow.png") });

  await page.route("**/api/sites/1/test-runs", (route) =>
    route.fulfill({ json: runs.slice(0, 2) }),
  );
  await page.reload();

  const shortListMeasurements = await page.locator(".site-detail-content").evaluate((content) => {
    const table = content.querySelector(".site-runs-table");
    const contentBox = content.getBoundingClientRect();
    const tableBox = table.getBoundingClientRect();
    const paddingBottom = Number.parseFloat(getComputedStyle(content).paddingBottom);
    return {
      bottomGap: contentBox.bottom - paddingBottom - tableBox.bottom,
      tableHeight: tableBox.height,
    };
  });
  expect(shortListMeasurements.bottomGap).toBeGreaterThan(200);
  expect(shortListMeasurements.tableHeight).toBeLessThan(200);
  await expect(page.locator("tbody tr")).toHaveCount(2);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-site-runs-content-height.png") });
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

test("OWASP coverage cells filter the rendered traffic rows", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);

  const traffic = Array.from({ length: 15 }, (_, index) => ({
    id: index + 1,
    created_at: "2026-09-19T00:00:00Z",
    source: "agent",
    purpose: index < 10 ? "A03 test" : "Other test",
    method: "GET",
    status: 200,
    url: `http://example.test/request-${index + 1}`,
    duration_ms: 10,
    coverage_cell_id: index < 10 ? 101 : 202,
    test_class: "xss",
  }));
  await page.route("**/api/test-runs/1/coverage", (route) =>
    route.fulfill({
      json: {
        seeded: true,
        columns: [
          { key: "A03:xss", category: "A03", test_class: "xss", label: "Cross-site scripting" },
        ],
        pages: [
          {
            page_id: 1,
            page_ids: [1],
            url: "http://example.test/form",
            cells: {
              "A03:xss": {
                status: "covered",
                cell_ids: [101],
                finding_ids: [],
                test_classes: {},
              },
            },
          },
        ],
        column_totals: { covered: 1 },
      },
    }),
  );
  await page.route("**/api/test-runs/1/traffic/count", (route) =>
    route.fulfill({ json: { count: traffic.length } }),
  );
  await page.route("**/api/test-runs/1/traffic?**", (route) => {
    const sinceId = Number(new URL(route.request().url()).searchParams.get("since_id") || 0);
    return route.fulfill({ json: traffic.filter((entry) => entry.id > sinceId) });
  });

  await page.goto("/#/runs/1/traffic");
  await expect(page).toHaveTitle("AESPA");
  await expect(page.getByText("Fixture run", { exact: false }).first()).toBeVisible();
  const visibleTrafficPanel = page.locator(".traffic-panel:visible");
  await expect(visibleTrafficPanel.locator(".traffic-table tbody .traffic-row")).toHaveCount(15);
  await visibleTrafficPanel.locator(".traffic-table tbody .traffic-row").last().click();
  await expect(visibleTrafficPanel.locator(".traffic-detail")).toBeVisible();

  await page.getByRole("button", { name: "Attack Surface & Coverage", exact: true }).click();
  await page.locator("td.coverage-traffic-cell").click({ position: { x: 3, y: 3 } });

  await expect(page).toHaveURL(/#\/runs\/1\/traffic\?.*coverage_cells=101/);
  await expect(visibleTrafficPanel.locator(".traffic-count-label")).toHaveText("10 shown of 15");
  await expect(visibleTrafficPanel.locator(".traffic-table tbody .traffic-row")).toHaveCount(10);
  await expect(
    visibleTrafficPanel.locator(".traffic-table tbody .traffic-row").first(),
  ).toContainText("request-1");
  await expect(visibleTrafficPanel.locator('[title="http://example.test/request-11"]')).toHaveCount(
    0,
  );
  await expect(visibleTrafficPanel.locator(".traffic-detail")).toHaveCount(0);
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-coverage-traffic-filter.png") });
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

  for (const tabName of ["Model", /^Threats/, "Execution Summary", /^Candidates/, "Activity"]) {
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

test("SAST threats include security check progress without a duplicate tab", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await installFixtures(page);
  await page.route("**/api/sast-runs/1/analysis", (route) =>
    route.fulfill({
      json: {
        phases: {
          threat_model: {
            data: {
              summary: "One source-backed threat scenario.",
              assets: [{ id: "asset-1", name: "Account records" }],
              stores: [{ id: "store-1", name: "Customer database" }],
              files_reviewed: 12,
              quality: { status: "full", reasons: [] },
              scenarios: [
                {
                  scenario_key: "scenario-1",
                  title: "Protect account access",
                  status: "planned",
                  priority: "high",
                  confidence: 0.92,
                  actor: "authenticated user",
                  security_objective: "enforce account ownership",
                  impact: "unauthorized access to another customer's records",
                  evidence: ["src/accounts.py:12"],
                },
              ],
            },
          },
          planning: {
            data: {
              obligations: [
                {
                  obligation_key: "obligation-1",
                  obligation_type: "threat_scenario",
                  source_scenario_key: "scenario-1",
                  security_question: "Can one user read another account?",
                  priority: "high",
                  status: "assessed_safe",
                  disposition: "assessed_safe",
                  reasoning: "Ownership is checked before the account is loaded.",
                  evidence: ["src/accounts.py:18"],
                  open_questions: [],
                },
              ],
            },
          },
          closure: { data: { status: "full", reasons: [] } },
        },
        coverage: { files: [], summary: {} },
        work_program: {},
        assurance: {},
        report: { candidates: 0, reportable: 0 },
      },
    }),
  );

  await page.goto("/#/sast-runs/1/threats");

  const viewTabs = page.getByRole("tablist", { name: "SAST run views" });
  await expect(page).toHaveTitle("AESPA");
  await expect(page.getByText("Fixture SAST", { exact: true })).toBeVisible();
  await expect(viewTabs.getByRole("tab", { name: "Threats 1" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(viewTabs.getByRole("tab", { name: /Security checks/ })).toHaveCount(0);
  await expect(page.getByText("Security check progress")).toBeVisible();
  await expect(page.getByText("1 of 1 checks completed · 0 reportable candidates")).toBeVisible();

  await page.getByText("Protect account access").click();
  await expect(page.getByText("Can one user read another account?")).toBeVisible();
  await expect(page.getByText("Ownership is checked before the account is loaded.")).toBeVisible();
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-threats-consolidated.png") });

  await page.getByText("Can one user read another account?").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(tmpdir(), "aespa-sast-threats-check-details.png") });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByText("Protect account access")).toBeVisible();
  await expect(page.getByText("Can one user read another account?")).toBeVisible();
  await page.getByText("Can one user read another account?").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(tmpdir(), "aespa-sast-threats-consolidated-mobile.png"),
  });
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
