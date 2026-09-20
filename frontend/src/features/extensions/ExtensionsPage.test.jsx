import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as extensionsApi from "../../shared/api/extensions.js";
import { ExtensionsPage } from "./ExtensionsPage.jsx";

vi.mock("../../shared/api/extensions.js");

const extensions = [
  {
    id: "github.repository",
    name: "GitHub repository source",
    version: "1.0.0",
    aespa_api: "1",
    enabled: true,
    status: "loaded",
    settings: {},
    settings_fields: [
      { key: "git_executable", label: "Git", type: "path", placeholder: "Detected" },
    ],
    source_providers: [
      {
        id: "github.repository",
        label: "GitHub repository",
        description: "Create snapshots from GitHub.",
        availability: { available: true, message: "Ready" },
      },
    ],
  },
  {
    id: "example.reports",
    name: "Example reports",
    version: "2.0.0",
    aespa_api: "1",
    enabled: true,
    status: "loaded",
    settings: {},
    settings_fields: [],
    source_providers: [],
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  extensionsApi.listExtensions.mockResolvedValue(extensions);
  extensionsApi.updateExtensionSettings.mockImplementation(async (id, settings) => ({
    ...extensions[0],
    id,
    settings,
  }));
  extensionsApi.setExtensionEnabled.mockImplementation(async (id, enabled) => {
    const extension = extensions.find((item) => item.id === id);
    return {
      ...extension,
      enabled,
      status: enabled ? "loaded" : "disabled",
      source_providers: enabled ? extension.source_providers : [],
    };
  });
});

test("renders multiple extensions and saves each extension settings separately", async () => {
  const user = userEvent.setup();
  render(<ExtensionsPage />);

  expect(await screen.findByText("GitHub repository source")).toBeTruthy();
  expect(screen.getByText("Example reports")).toBeTruthy();
  await user.type(screen.getByLabelText("Git"), "/usr/bin/git");
  await user.click(screen.getByRole("button", { name: "Save settings" }));

  expect(extensionsApi.updateExtensionSettings).toHaveBeenCalledWith("github.repository", {
    git_executable: "/usr/bin/git",
  });
});

test("enables and disables extensions from the list", async () => {
  const user = userEvent.setup();
  render(<ExtensionsPage />);

  const checkbox = await screen.findByRole("checkbox", { name: "Enable Example reports" });
  await user.click(checkbox);

  expect(extensionsApi.setExtensionEnabled).toHaveBeenCalledWith("example.reports", false);
  expect(await screen.findByText("Disabled")).toBeTruthy();
});
