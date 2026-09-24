import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import * as extensionsApi from "../../shared/api/extensions.js";
import { ExtensionSettingsPage } from "./ExtensionSettingsPage.jsx";
import { ExtensionsPage } from "./ExtensionsPage.jsx";

vi.mock("../../shared/api/extensions.js");

const extensions = [
  {
    id: "aespa.githubrepository",
    name: "GitHub repository source",
    author: "aespa",
    version: "1.0.0",
    aespa_api: "1",
    capabilities: ["sast.source_provider"],
    enabled: true,
    status: "loaded",
    settings: {},
    settings_fields: [
      { key: "git_executable", label: "Git", type: "path", placeholder: "Detected" },
    ],
    source_providers: [
      {
        id: "aespa.githubrepository",
        label: "GitHub repository",
        availability: { available: true, message: "Ready" },
      },
    ],
  },
  {
    id: "example.reports",
    name: "Example reports",
    version: "2.0.0",
    aespa_api: "1",
    capabilities: ["report.provider"],
    enabled: false,
    status: "disabled",
    settings: {},
    settings_fields: [],
    source_providers: [],
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  extensionsApi.listExtensions.mockResolvedValue(extensions);
  extensionsApi.updateExtensionSettings.mockImplementation(async (id, settings) => ({
    ...extensions.find((item) => item.id === id),
    settings,
  }));
  extensionsApi.setExtensionEnabled.mockImplementation(async (id, enabled) => ({
    ...extensions.find((item) => item.id === id),
    enabled,
    status: enabled ? "loaded" : "disabled",
  }));
});

test("lists extensions with status, actions, and separate settings links", async () => {
  render(<ExtensionsPage />);

  const table = await screen.findByRole("table");
  const rows = within(table).getAllByRole("row");
  expect(rows).toHaveLength(3);
  expect(within(rows[1]).getByText("Ready")).toBeTruthy();
  expect(within(rows[1]).getByText("aespa")).toBeTruthy();
  expect(within(rows[1]).getByRole("button", { name: "Disable" })).toBeTruthy();
  expect(
    within(rows[1])
      .getByRole("link", { name: "Settings for GitHub repository source" })
      .getAttribute("href"),
  ).toBe("#/extensions/aespa.githubrepository/settings");
  expect(within(rows[2]).getByRole("button", { name: "Enable" })).toBeTruthy();
  expect(screen.queryByLabelText("Git")).toBeNull();
});

test("enables and disables extensions from the table", async () => {
  const user = userEvent.setup();
  render(<ExtensionsPage />);

  await user.click(await screen.findByRole("button", { name: "Enable" }));
  expect(extensionsApi.setExtensionEnabled).toHaveBeenCalledWith("example.reports", true);
  expect(await screen.findAllByRole("button", { name: "Disable" })).toHaveLength(2);
});

test("settings page edits only the selected extension", async () => {
  const user = userEvent.setup();
  render(<ExtensionSettingsPage extensionId="aespa.githubrepository" />);

  await user.type(await screen.findByLabelText("Git"), "/usr/bin/git");
  await user.click(screen.getByRole("button", { name: "Save settings" }));
  expect(extensionsApi.updateExtensionSettings).toHaveBeenCalledWith("aespa.githubrepository", {
    git_executable: "/usr/bin/git",
  });
  expect(screen.getByRole("link", { name: "Extensions" }).getAttribute("href")).toBe(
    "#/extensions",
  );
  expect(screen.getByText("Author: aespa")).toBeTruthy();
});

test("disabled extension settings page links back to the list", async () => {
  render(<ExtensionSettingsPage extensionId="example.reports" />);

  expect(await screen.findByText(/Enable this extension from the/)).toBeTruthy();
  expect(screen.getByText("Author: Not specified")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Save settings" })).toBeNull();
});

test("secret settings use a password field and do not display saved values", async () => {
  const user = userEvent.setup();
  extensionsApi.listExtensions.mockResolvedValueOnce([
    {
      ...extensions[1],
      enabled: true,
      status: "loaded",
      secrets_namespace: "example.reports",
      settings_fields: [{ key: "api_key", label: "API key", type: "secret" }],
      has_secrets: { api_key: true },
    },
  ]);
  render(<ExtensionSettingsPage extensionId="example.reports" />);

  const field = await screen.findByLabelText("API key");
  expect(field.type).toBe("password");
  expect(field.value).toBe("");
  await user.type(field, "replacement-key");
  await user.click(screen.getByRole("button", { name: "Save settings" }));
  expect(extensionsApi.updateExtensionSettings).toHaveBeenCalledWith("example.reports", {
    api_key: "replacement-key",
  });
});

test("boolean settings show extension defaults until explicitly changed", async () => {
  extensionsApi.listExtensions.mockResolvedValueOnce([
    {
      ...extensions[0],
      settings: { scan_xss: false },
      settings_fields: [
        { key: "scan_sqli", label: "Scan SQL Injection", type: "boolean", default: true },
        { key: "scan_xss", label: "Scan XSS", type: "boolean", default: true },
      ],
    },
  ]);
  render(<ExtensionSettingsPage extensionId="aespa.githubrepository" />);

  expect(await screen.findByRole("checkbox", { name: "Scan SQL Injection" })).toHaveProperty(
    "checked",
    true,
  );
  expect(screen.getByRole("checkbox", { name: "Scan XSS" })).toHaveProperty("checked", false);
});
