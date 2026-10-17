import { expect, test } from "@playwright/test";
import { installFixtures } from "./fixtures.js";

test("key sign-in remembers the browser and preserves the requested page", async ({ page }) => {
  await installFixtures(page);
  let authenticated = false;
  await page.route("**/api/auth/session", (route) =>
    route.fulfill({ json: { authenticated, csrf_token: authenticated ? "csrf" : null } }),
  );
  await page.route("**/api/auth/login", (route) => {
    if (route.request().postDataJSON().key !== "correct-key")
      return route.fulfill({ status: 401, json: { detail: "Invalid authentication key." } });
    authenticated = true;
    return route.fulfill({ json: { authenticated: true, csrf_token: "csrf" } });
  });
  await page.goto("/#/settings/authentication");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByLabel("Authentication key", { exact: true }).fill("wrong-key");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Invalid authentication key.");
  await page.getByLabel("Authentication key", { exact: true }).fill("correct-key");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Authentication key", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/#\/settings\/authentication$/);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Authentication key", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toHaveCount(0);
});

test("Settings only requests the key when Show is pressed", async ({ page }) => {
  await installFixtures(page);
  let requests = 0;
  await page.route("**/api/auth/key", (route) => {
    requests += 1;
    return route.fulfill({ json: { key: "management-key" } });
  });
  await page.goto("/#/settings/authentication");
  const field = page.getByLabel("Authentication key", { exact: true });
  await expect(field).toHaveAttribute("type", "password");
  expect(requests).toBe(0);
  await page.getByRole("button", { name: "Show", exact: true }).click();
  await expect(field).toHaveValue("management-key");
  await page.getByRole("button", { name: "Hide", exact: true }).click();
  await expect(field).toHaveAttribute("type", "password");
  await expect(field).not.toHaveValue("management-key");
  expect(requests).toBe(1);
});

test("a launcher link exchanges its secret and cleans the address", async ({ page }) => {
  await installFixtures(page);
  let exchanges = 0;
  await page.route("**/api/auth/exchange", (route) => {
    exchanges += 1;
    expect(route.request().postDataJSON()).toEqual({ token: "single-use-secret" });
    return route.fulfill({ json: { authenticated: true, csrf_token: "csrf" } });
  });
  await page.goto("/#aespa-login=single-use-secret&next=%23%2Fsettings%2Fauthentication");
  await expect(
    page.getByRole("heading", { name: "Authentication key", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/#\/settings\/authentication$/);
  expect(exchanges).toBe(1);
});
