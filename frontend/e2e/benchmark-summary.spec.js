import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 600, height: 800 },
]) {
  test(`summary filters and graph fit at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    const results = [
      {
        id: 1,
        run_name: "DAST only",
        run_kind: "site",
        scan_models: { primary: { name: "Sonnet" } },
      },
      {
        id: 2,
        run_name: "Combined scan",
        run_kind: "site",
        scan_models: { primary: { name: "Sonnet" }, sast: [{ run_id: 7 }] },
      },
      {
        id: 3,
        run_name: "Source scan",
        run_kind: "sast",
        scan_models: { primary: { name: "Sonnet" } },
      },
      ...Array.from({ length: 12 }, (_, i) => ({
        id: i + 4,
        run_name: `Scan ${i + 4}`,
        run_kind: "site",
        scan_models: { primary: { name: i < 2 ? "Other model" : `Model ${i + 4}` } },
      })),
    ].map((result) => ({
      ...result,
      target_kind: "site",
      target_id: 1,
      scan_cost_usd: result.id / 10,
      scan_started_at: new Date(Date.UTC(2026, 8, result.id, 9)).toISOString(),
      summary: { full: result.id, partial: 0, missing: 0 },
      ground_truth: { name: "Fixture truth", items: [] },
      findings: [],
      rows: [],
      created_at: "2026-09-30T09:00:00Z",
    }));
    results.push({
      ...results[0],
      id: 99,
      run_name: "Non-optimal single",
      scan_models: { primary: { name: "Hidden single model" } },
      scan_cost_usd: 1.5,
      summary: { full: 1, partial: 0, missing: 0 },
    });
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      const data =
        endpoint === "targets"
          ? { sites: [{ id: 1, name: "Bank of Ed", runs: [] }], apis: [], sast_runs: [] }
          : endpoint === "results"
            ? results
            : endpoint === "settings"
              ? { default_model_id: 1 }
              : [];
      await route.fulfill({ json: data });
    });
    await page.goto("/#/benchmark-lab");
    await expect(page).toHaveTitle("AESPA");
    await page.getByLabel("Site", { exact: true }).selectOption("1");
    await expect(page.getByLabel("Display", { exact: true })).toHaveValue("optimal");
    await expect(page.getByRole("img", { name: "Optimal: best findings for cost" })).toBeVisible();
    await page.getByLabel("Display", { exact: true }).selectOption("model");
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    const hiddenSingle = page.getByRole("button", { name: "Hidden single model", exact: true });
    await expect(hiddenSingle).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByRole("button", { name: /^Non-optimal single,/ })).toHaveCount(0);
    await hiddenSingle.click();
    await expect(page.getByRole("button", { name: /^Non-optimal single,/ })).toBeVisible();
    await hiddenSingle.click();
    await expect(page.getByRole("button", { name: /^Non-optimal single,/ })).toHaveCount(0);
    const point = (name) => page.getByRole("button", { name: new RegExp(`^${name},`) });
    await expect(point("Combined scan").locator("rect")).toBeVisible();
    await expect(point("DAST only").locator("circle")).toBeVisible();
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toBeVisible();
    await expect(page.getByRole("img", { name: "Other model linear trend" })).toBeVisible();
    const labels = await page.locator('[aria-label$="linear trend"] text').evaluateAll((elements) =>
      elements.map((element) => {
        const box = element.getBoundingClientRect();
        return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
      }),
    );
    const placements = await page.locator('[aria-label$="linear trend"]').evaluateAll((groups) =>
      groups.map((group) => {
        const line = group.querySelector("line");
        const text = group.querySelector("text");
        if (!text) return null;
        const x1 = Number(line.getAttribute("x1"));
        const y1 = Number(line.getAttribute("y1"));
        const dx = Number(line.getAttribute("x2")) - x1;
        const dy = Number(line.getAttribute("y2")) - y1;
        const x = Number(text.getAttribute("x"));
        const y = Number(text.getAttribute("y"));
        return {
          distance: Math.abs(dx * (y - y1) - dy * (x - x1)) / Math.hypot(dx, dy),
          transform: text.getAttribute("transform"),
        };
      }),
    );
    expect(labels).toHaveLength(2);
    for (const placement of placements) {
      expect(placement.distance).toBeLessThanOrEqual(7.1);
      expect(placement.transform).toMatch(/^rotate\(/);
    }
    await expect(page.locator('[aria-label="Model 6 single scan"]')).toBeVisible();
    const modelToggle = page.getByRole("button", { name: "Sonnet", exact: true });
    await modelToggle.hover();
    await expect(point("Combined scan")).toHaveCSS("opacity", "1");
    await expect(point("Scan 4")).toHaveCSS("opacity", "0.15");
    await expect(page.getByRole("img", { name: "Other model linear trend" })).toHaveCSS(
      "opacity",
      "0.15",
    );
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toHaveCSS("opacity", "1");
    await page.screenshot({
      path: path.join(tmpdir(), `aespa-legend-hover-${viewport.width}.png`),
    });
    await page.getByRole("heading", { name: "Scan cost and findings" }).hover();
    await expect(point("Scan 4")).toHaveCSS("opacity", "1");
    await page.getByRole("button", { name: "Model 6", exact: true }).hover();
    await expect(point("Scan 6")).toHaveCSS("opacity", "1");
    await expect(point("Combined scan")).toHaveCSS("opacity", "0.15");
    const typeToggle = page.getByRole("button", { name: "DAST", exact: true });
    await typeToggle.hover();
    await expect(point("DAST only")).toHaveCSS("opacity", "1");
    await expect(point("Combined scan")).toHaveCSS("opacity", "0.15");
    await expect(typeToggle).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("img", { name: "DAST scan type linear trend" })).toHaveCount(0);
    await page.getByLabel("Display", { exact: true }).selectOption("scan-type");
    await expect(page.getByRole("img", { name: "DAST scan type linear trend" })).toBeVisible();
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toHaveCount(0);
    await expect(page.getByRole("img", { name: "Optimal: best findings for cost" })).toHaveCount(0);
    await page.getByRole("heading", { name: "Scan cost and findings" }).hover();
    await page.screenshot({
      path: path.join(tmpdir(), `aespa-category-trend-${viewport.width}.png`),
    });
    await typeToggle.click();
    await expect(page.getByRole("img", { name: "DAST scan type linear trend" })).toHaveCount(0);
    await expect(point("DAST only")).toHaveCount(0);
    await typeToggle.click();
    await page.getByLabel("Display", { exact: true }).selectOption("model");
    expect(
      labels[0].right <= labels[1].left ||
        labels[1].right <= labels[0].left ||
        labels[0].bottom <= labels[1].top ||
        labels[1].bottom <= labels[0].top,
    ).toBe(true);
    await page.locator('summary[aria-label="Scan type"]').click();
    await page.getByRole("checkbox", { name: "Select all", exact: true }).uncheck();
    await expect(point("Combined scan")).toHaveCount(0);
    await page.getByRole("checkbox", { name: "Select all", exact: true }).check();
    await page.getByRole("checkbox", { name: "DAST", exact: true }).uncheck();
    await expect(point("DAST only")).toHaveCount(0);
    await expect(point("Combined scan")).toBeVisible();
    await page.getByRole("checkbox", { name: "DAST", exact: true }).check();
    await page.getByRole("checkbox", { name: "DAST with SAST Leads", exact: true }).uncheck();
    await expect(point("Combined scan")).toHaveCount(0);
    await expect(point("DAST only")).toBeVisible();
    await page.getByRole("checkbox", { name: "DAST with SAST Leads", exact: true }).check();
    await page.getByLabel("Model", { exact: true }).click();
    await page.getByRole("checkbox", { name: "Select all", exact: true }).check();
    await page.getByRole("checkbox", { name: "Select all", exact: true }).uncheck();
    await expect(point("DAST only")).toHaveCount(0);
    await page.getByRole("checkbox", { name: "Select all", exact: true }).check();
    await page.getByRole("checkbox", { name: "Sonnet", exact: true }).uncheck();
    await expect(point("DAST only")).toHaveCount(0);
    await expect(point("Combined scan")).toHaveCount(0);
    await page.getByRole("checkbox", { name: "Sonnet", exact: true }).check();
    await page.getByRole("checkbox", { name: "Sonnet", exact: true }).press("Escape");
    await page.getByRole("button", { name: "Sonnet", exact: true }).click();
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toHaveCount(0);
    await expect(point("Combined scan")).toHaveCount(0);
    await expect(point("DAST only")).toHaveCount(0);
    await expect(modelToggle).toHaveAttribute("aria-pressed", "false");
    await page.getByRole("button", { name: "Sonnet", exact: true }).click();
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toBeVisible();
    await expect(point("Combined scan")).toBeVisible();
    await expect(modelToggle).toHaveAttribute("aria-pressed", "true");
    const singleModel = page.getByRole("button", { name: "Model 6", exact: true });
    await expect(singleModel).toBeEnabled();
    await expect(singleModel).toHaveAttribute("aria-pressed", "true");
    await singleModel.click();
    await expect(singleModel).toHaveAttribute("aria-pressed", "false");
    await expect(singleModel).toHaveCSS("opacity", "0.5");
    await expect(point("Scan 6")).toHaveCount(0);
    await expect(page.locator('[aria-label="Model 6 single scan"]')).toHaveCount(0);
    await expect(point("Combined scan")).toHaveCSS("opacity", "1");
    await page.screenshot({
      path: path.join(tmpdir(), `aespa-model-hidden-${viewport.width}.png`),
    });
    await singleModel.click();
    await expect(point("Scan 6")).toBeVisible();
    await page.getByLabel("Compare by").selectOption("date");
    await expect(page.getByRole("img", { name: "Sonnet linear trend" })).toBeVisible();
    await expect(
      page.getByRole("img", { name: "Scan date versus full and partial findings" }),
    ).toBeVisible();
    await expect(point("Combined scan")).toBeVisible();
    const bounds = await page.locator(".benchmark-summary-page").evaluate((element) => ({
      scroll: element.scrollHeight,
      height: element.clientHeight,
      width: document.body.scrollWidth,
      viewport: innerWidth,
      graphBottom: element.querySelector("svg").getBoundingClientRect().bottom,
      pageBottom: element.getBoundingClientRect().bottom,
    }));
    expect(bounds.scroll).toBeLessThanOrEqual(bounds.height + 1);
    expect(bounds.width).toBeLessThanOrEqual(bounds.viewport);
    expect(bounds.graphBottom).toBeLessThanOrEqual(bounds.pageBottom);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-summary-${viewport.width}.png`) });
    await page.getByLabel("Display", { exact: true }).selectOption("optimal");
    await expect(page.getByLabel("Compare by")).toHaveValue("cost");
    const optimalLine = page.getByRole("img", { name: "Optimal: best findings for cost" });
    await expect(optimalLine).toBeVisible();
    await expect(optimalLine.locator("text")).toHaveText("Optimal");
    await expect(page.getByLabel("Sonnet optimal model", { exact: true })).toBeVisible();
    const guides = await page.locator("[data-guide-label]").evaluateAll((groups) =>
      groups.map((guide) => {
        const points = [...guide.ownerSVGElement.querySelectorAll(".benchmark-chart-point")];
        const [outline, line] = guide.querySelectorAll("line");
        const marker = guide.querySelector("circle");
        return {
          abovePoints: points.every(
            (point) => !!(guide.compareDocumentPosition(point) & Node.DOCUMENT_POSITION_PRECEDING),
          ),
          pointerEvents: getComputedStyle(guide).pointerEvents,
          outlined:
            Number(outline.getAttribute("stroke-width")) >
            Number(line.getAttribute("stroke-width")),
          sourceMatches:
            marker.getAttribute("cx") === line.getAttribute("x1") &&
            marker.getAttribute("cy") === line.getAttribute("y1"),
        };
      }),
    );
    expect(guides.length).toBeGreaterThan(0);
    for (const guide of guides)
      expect(guide).toEqual({
        abovePoints: true,
        pointerEvents: "none",
        outlined: true,
        sourceMatches: true,
      });
    await expect(page.locator('text[aria-label$="optimal model"]')).toHaveCount(12);
    const legendBounds = await page.locator(".benchmark-chart-legend").evaluateAll((legends) =>
      legends.map((legend) => ({
        scroll: legend.scrollHeight,
        height: legend.clientHeight,
        width: legend.clientWidth,
        scrollWidth: legend.scrollWidth,
        bottom: legend.getBoundingClientRect().bottom,
        pageBottom: legend.closest(".benchmark-summary-page").getBoundingClientRect().bottom,
      })),
    );
    for (const bounds of legendBounds) {
      expect(bounds.scroll).toBeLessThanOrEqual(bounds.height + 1);
      expect(bounds.scrollWidth).toBeLessThanOrEqual(bounds.width + 1);
      expect(bounds.bottom).toBeLessThanOrEqual(bounds.pageBottom);
    }
    await expect(page.getByRole("button", { name: "Sonnet, Optimal", exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /^Optimal, Combined scan,/ }).locator("circle"),
    ).toBeVisible();
    await page.getByRole("heading", { name: "Scan cost and findings" }).hover();
    await page.screenshot({ path: path.join(tmpdir(), `aespa-optimal-${viewport.width}.png`) });
    await page.getByLabel("Display", { exact: true }).selectOption("model");
    await expect(optimalLine).toHaveCount(0);
    await point("Combined scan").hover();
    await expect(page.getByRole("tooltip")).toContainText("Combined scan");
    await expect(page.getByRole("tooltip")).toContainText("Sonnet");
    await expect(page.getByRole("tooltip")).toContainText("DAST with SAST Leads");
    await page.screenshot({
      path: path.join(tmpdir(), `aespa-summary-tooltip-${viewport.width}.png`),
    });
    await point("Combined scan").click();
    await expect(page.getByRole("tab", { name: "Analyses" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(errors).toEqual([]);
  });
}

for (const width of [1440, 600]) {
  test(`MiniMax label stays clear of crowded scan points at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    const results = [
      ["minimax-m3", 0.1, 16],
      ["minimax-m3", 0.2, 16],
      ["Other model", 0.05, 17],
      ["Other model", 0.1, 18],
      ["Other model", 0.2, 17],
      ["Other model", 0.3, 18],
      ["Other model", 0.3, 16],
      ["Expensive model", 5, 25],
      ["Expensive model", 10, 30],
    ].map(([name, cost, findings], index) => ({
      id: index + 1,
      run_name: `Scan ${index + 1}`,
      run_kind: "site",
      target_kind: "site",
      target_id: 1,
      scan_models: { primary: { name } },
      scan_cost_usd: cost,
      summary: { full: findings, partial: 0, missing: 0 },
    }));
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      await route.fulfill({
        json:
          endpoint === "targets"
            ? { sites: [{ id: 1, name: "Crowded site", runs: [] }], apis: [], sast_runs: [] }
            : endpoint === "results"
              ? results
              : endpoint === "settings"
                ? { default_model_id: 1 }
                : [],
      });
    });
    await page.goto("/#/benchmark-lab");
    await expect(page).toHaveTitle("AESPA");
    await page.getByLabel("Site", { exact: true }).selectOption("1");
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    await page.getByLabel("Display", { exact: true }).selectOption("model");
    const trend = page.getByRole("img", { name: "minimax-m3 linear trend" });
    await expect(trend.locator("text")).toBeVisible();
    const overlapsPoints = await trend.locator("text").evaluate((text) => {
      const label = text.getBoundingClientRect();
      return [...text.ownerSVGElement.querySelectorAll(".benchmark-chart-point")].some((point) => {
        const box = point.getBoundingClientRect();
        return (
          label.left < box.right &&
          label.right > box.left &&
          label.top < box.bottom &&
          label.bottom > box.top
        );
      });
    });
    expect(overlapsPoints).toBe(false);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-minimax-label-${width}.png`) });
    expect(errors).toEqual([]);
  });

  test(`every crowded trendline has a visible label at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await installFixtures(page);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    const results = Array.from({ length: 24 }, (_, index) => ({
      id: index + 1,
      run_name: `Scan ${index + 1}`,
      run_kind: "site",
      target_kind: "site",
      target_id: 1,
      scan_models: { primary: { name: `Crowded model ${Math.floor(index / 2)}` } },
      scan_cost_usd: 1 + (index % 2) * 0.001,
      summary: { full: 10, partial: 0, missing: 0 },
    }));
    await page.route("**/extension/aespa.benchmarking/**", async (route) => {
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      await route.fulfill({
        json:
          endpoint === "targets"
            ? { sites: [{ id: 1, name: "Crowded site", runs: [] }], apis: [], sast_runs: [] }
            : endpoint === "results"
              ? results
              : endpoint === "settings"
                ? { default_model_id: 1 }
                : [],
      });
    });
    await page.goto("/#/benchmark-lab");
    await expect(page).toHaveTitle("AESPA");
    await page.getByLabel("Site", { exact: true }).selectOption("1");
    await expect(page.locator("vite-error-overlay")).toHaveCount(0);
    await page.getByLabel("Display", { exact: true }).selectOption("model");
    const groups = page.locator('[aria-label$="linear trend"]');
    await expect(groups).toHaveCount(12);
    await expect(groups.locator("text")).toHaveCount(12);
    await expect(groups.locator("path")).toHaveCount(0);
    const distances = await groups.evaluateAll((items) =>
      items.map((group) => {
        const line = group.querySelector("line");
        const text = group.querySelector("text");
        const dx = Number(line.getAttribute("x2")) - Number(line.getAttribute("x1"));
        const dy = Number(line.getAttribute("y2")) - Number(line.getAttribute("y1"));
        return (
          Math.abs(
            dx * (Number(text.getAttribute("y")) - Number(line.getAttribute("y1"))) -
              dy * (Number(text.getAttribute("x")) - Number(line.getAttribute("x1"))),
          ) / Math.hypot(dx, dy)
        );
      }),
    );
    for (const distance of distances) expect(distance).toBeLessThanOrEqual(7.1);
    const clipped = await groups.locator("text").evaluateAll(
      (labels) =>
        labels.filter((label) => {
          const box = label.getBoundingClientRect();
          const svg = label.ownerSVGElement.getBoundingClientRect();
          return (
            box.left < svg.left ||
            box.right > svg.right ||
            box.top < svg.top ||
            box.bottom > svg.bottom
          );
        }).length,
    );
    expect(clipped).toBe(0);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-all-trend-labels-${width}.png`) });
    await page.getByRole("button", { name: "Crowded model 0", exact: true }).click();
    await expect(groups).toHaveCount(11);
    await expect(groups.locator("text")).toHaveCount(11);
    expect(errors).toEqual([]);
  });
}
