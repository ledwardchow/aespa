import { expect, test } from "@playwright/test";
import { installFixtures, sast } from "./fixtures.js";

test("rename and move a SAST scan from the list", async ({ page }) => {
  await installFixtures(page);
  let saved = { ...sast, collection_id: null, site_id: null, associated_collection_id: null };
  await page.route("**/api/sast-runs/page?*", (route) => {
    const group = new URL(route.request().url()).searchParams.get("association");
    const shown = group === "site" ? Boolean(saved.site_id) : !saved.site_id;
    return route.fulfill({
      json: {
        items: shown ? [{ ...saved, associated_name: saved.site_id ? "Fixture site" : null }] : [],
        total: shown ? 1 : 0,
      },
    });
  });
  await page.route("**/api/sast-runs/1", (route) => {
    if (route.request().method() === "PATCH") {
      saved = { ...saved, ...route.request().postDataJSON(), group_override: true };
    }
    return route.fulfill({ json: saved });
  });

  await page.goto("/#/sast-runs/unassociated");
  await page.getByRole("button", { name: "Edit" }).click();
  const form = page.getByRole("form", { name: "Edit SAST scan" });
  await expect(form.getByRole("textbox", { name: "Name" })).toBeFocused();
  await form.getByRole("textbox", { name: "Name" }).fill("Renamed SAST scan");
  await form.getByRole("combobox", { name: "Group" }).selectOption("site");
  await form.getByRole("combobox", { name: "Site" }).selectOption("1");
  await form.getByRole("button", { name: "Save changes" }).click();

  await page.getByRole("tab", { name: "Site" }).click();
  await expect(page.getByRole("link", { name: "Renamed SAST scan" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Fixture site" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("link", { name: "Renamed SAST scan" })).toBeVisible();
});
