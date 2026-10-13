import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

for (const kind of ["web", "api"]) {
  test(`${kind} DAST imports SAST leads through a searchable dialog`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      // Production registration is intentionally blocked by the fixture configuration.
      if (message.text() === "Service Worker registration blocked by Playwright") return;
      if (message.type() === "error" || message.type() === "warning") errors.push(message.text());
    });
    await installFixtures(page);
    const base = `/api/${kind === "api" ? "api-test-runs" : "test-runs"}/1`;
    let imported = false;
    await page.route(`**${base}/sast-runs/available?*`, (route) => {
      const url = new URL(route.request().url());
      const query = url.searchParams.get("q");
      const number = Number(url.searchParams.get("page"));
      const scan = {
        id: 248,
        name: "Customer portal — release 2.8",
        source_filename: "portal-source.zip",
        completed_at: "2026-10-13T01:00:00Z",
        leads_count: 12,
        imported_count: imported ? 12 : 0,
        new_count: imported ? 0 : 12,
      };
      const scans = [
        scan,
        { ...scan, id: 247, name: "Portal baseline", imported_count: 12, new_count: 0 },
        ...Array.from({ length: 20 }, (_, index) => ({
          ...scan,
          id: 246 - index,
          name: `Portal archive ${index + 1}`,
        })),
      ];
      const matches = scans.filter((item) =>
        `${item.name} ${item.source_filename} ${item.id}`
          .toLowerCase()
          .includes((query || "").toLowerCase()),
      );
      return route.fulfill({
        json: {
          items: matches.slice((number - 1) * 10, number * 10),
          total: matches.length,
          page: number,
          page_size: 10,
        },
      });
    });
    await page.route(`**${base}/import-leads`, async (route) => {
      expect(route.request().postDataJSON()).toEqual({ sast_run_id: 248 });
      imported = true;
      await route.fulfill({ json: { imported: 12 } });
    });
    await page.goto(kind === "api" ? "/#/api-runs/1/leads" : "/#/runs/1/leads");
    await expect(page).toHaveURL(kind === "api" ? /api-runs\/1\/leads/ : /runs\/1\/leads/);
    await expect(page).toHaveTitle(/AESPA/i);
    await page.getByRole("button", { name: "Import SAST leads", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Import SAST leads" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Customer portal — release 2.8", { exact: true })).toBeVisible();
    await expect(dialog.getByRole("radio").nth(1)).toBeDisabled();
    await dialog.getByRole("button", { name: "Next", exact: true }).click();
    await expect(dialog.getByText("11–20 of 22")).toBeVisible();
    await dialog.getByLabel("Search scans").fill("missing");
    await expect(dialog.getByText(/No scans match your search/)).toBeVisible();
    await dialog.getByLabel("Search scans").fill("portal");
    await expect(dialog.getByText("1–10 of 22")).toBeVisible();
    await dialog.getByRole("radio").first().check();
    await page.screenshot({ path: path.join(tmpdir(), `aespa-${kind}-sast-import-desktop.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    const bounds = await dialog.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(390);
    expect(await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-${kind}-sast-import-narrow.png`) });
    await dialog.getByRole("button", { name: "Import 12 new leads", exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText("Imported 12 leads.", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Import SAST leads", exact: true }).click();
    await expect(dialog.getByRole("radio").first()).toBeDisabled();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(
      page.getByRole("button", { name: "Import SAST leads", exact: true }),
    ).toBeFocused();
    expect(errors).toEqual([]);
  });
}

test("running older backend supports search, retry, and the existing import action", async ({
  page,
}) => {
  await installFixtures(page);
  let fail = true;
  await page.route("**/api/test-runs/1/sast-runs/available?*", (route) => {
    if (fail)
      return route.fulfill({ status: 503, json: { detail: "Scans temporarily unavailable" } });
    return route.fulfill({
      json: [
        {
          id: 8,
          name: "Portal source",
          source_filename: "portal.zip",
          leads_count: 3,
          completed_at: null,
        },
        {
          id: 9,
          name: "Payments source",
          source_filename: "payments.zip",
          leads_count: 2,
          completed_at: null,
        },
      ],
    });
  });
  await page.route("**/api/test-runs/1/import-leads", (route) =>
    route.fulfill({ json: { imported: 2 } }),
  );
  await page.goto("/#/runs/1/leads");
  await page.getByRole("button", { name: "Import SAST leads", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("alert")).toContainText("Scans temporarily unavailable");
  fail = false;
  await dialog.getByRole("button", { name: "Retry" }).click();
  await expect(dialog.getByRole("radio")).toHaveCount(2);
  await dialog.getByLabel("Search scans").fill("payments.zip");
  await expect(dialog.getByRole("radio")).toHaveCount(1);
  await dialog.getByRole("radio").check();
  await expect(dialog.getByRole("button", { name: "Import leads", exact: true })).toBeEnabled();
  await dialog.getByRole("button", { name: "Import leads", exact: true }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText("Imported 2 leads.", { exact: true })).toBeVisible();
});

for (const kind of ["web", "api"]) {
  test(`${kind} DAST previews and imports an external scanner report`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await installFixtures(page);
    const base = `/api/${kind === "api" ? "api-test-runs" : "test-runs"}/1`;
    const requests = [];
    const format = kind === "api" ? "Markdown" : "SARIF";
    const filename = kind === "api" ? "external.md" : "external.sarif";
    await page.route(`**${base}/import-report`, (route) => {
      const body = route.request().postDataBuffer().toString();
      const preview = body.includes('name="preview"\r\n\r\ntrue');
      requests.push(preview ? "preview" : "import");
      expect(body).toContain('name="file"');
      return route.fulfill({
        json: {
          filename,
          format,
          total: 2,
          new_count: 1,
          already_imported: 1,
          skipped: 0,
          imported: preview ? 0 : 1,
          preview_limit: 100,
          warnings: ["No confidence is inferred."],
          items: [
            {
              title: "SQL injection",
              severity: "high",
              scanner: "Example scanner",
              location: "src/query.py:42",
              already_imported: false,
            },
            {
              title: "Access check missing",
              severity: "medium",
              scanner: "Example scanner",
              location: "src/auth.py:12",
              already_imported: true,
            },
          ],
        },
      });
    });
    await page.goto(kind === "api" ? "/#/api-runs/1/leads" : "/#/runs/1/leads");
    await page.getByRole("button", { name: "Import SAST leads", exact: true }).click();
    const dialog = page.getByRole("dialog");
    const dialogBounds = await dialog.boundingBox();
    const tabBounds = await dialog.getByRole("tablist").boundingBox();
    expect(Math.abs(tabBounds.x - dialogBounds.x - 1)).toBeLessThan(1);
    expect(Math.abs(tabBounds.width - dialogBounds.width + 2)).toBeLessThan(1);
    await dialog.getByRole("tab", { name: "AESPA scans", exact: true }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(dialog.getByRole("tab", { name: "Import from file" })).toBeFocused();
    await expect(dialog.getByRole("tab", { name: "Import from file" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      dialog.getByRole("button", { name: "Download Markdown template" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("sast-leads-template.md");
    await dialog.getByLabel("Scanner report").setInputFiles({
      name: filename,
      mimeType: kind === "api" ? "text/markdown" : "application/json",
      buffer: Buffer.from(
        kind === "api"
          ? "## SQL injection\n- Severity: high\n- Location: src/query.py:42"
          : '{"version":"2.1.0","runs":[]}',
      ),
    });
    await dialog.getByRole("button", { name: "Preview report" }).click();
    await expect(dialog.getByText("SQL injection", { exact: true })).toBeVisible();
    await expect(dialog.getByText("1 new lead · 1 already imported · 0 skipped")).toBeVisible();
    expect(requests).toEqual(["preview"]);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-${kind}-report-import-desktop.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
    await page.screenshot({ path: path.join(tmpdir(), `aespa-${kind}-report-import-narrow.png`) });
    await dialog.getByRole("button", { name: "Import 1 new lead", exact: true }).click();
    await expect(dialog).toBeHidden();
    expect(requests).toEqual(["preview", "import"]);
    await expect(page.getByText("Imported 1 lead.", { exact: true })).toBeVisible();
    expect(errors).toEqual([]);
  });
}

test("file preview handles invalid reports and an older backend", async ({ page }) => {
  await installFixtures(page);
  let status = 422;
  await page.route("**/api/test-runs/1/import-report", (route) =>
    route.fulfill({
      status,
      json: { detail: status === 422 ? "Upload a SARIF 2.1.0 report." : "Not Found" },
    }),
  );
  await page.goto("/#/runs/1/leads");
  await page.getByRole("button", { name: "Import SAST leads", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: "Import from file" }).click();
  await dialog
    .getByLabel("Scanner report")
    .setInputFiles({ name: "bad.json", mimeType: "application/json", buffer: Buffer.from("{}") });
  await dialog.getByRole("button", { name: "Preview report" }).click();
  await expect(dialog.getByRole("alert")).toContainText("Upload a SARIF 2.1.0 report.");
  status = 404;
  await dialog.getByRole("button", { name: "Preview report" }).click();
  await expect(dialog.getByRole("alert")).toContainText("Wait until running scans finish");
  await dialog.getByRole("tab", { name: "AESPA scans", exact: true }).click();
  await expect(dialog.getByLabel("Search scans")).toBeVisible();
});
