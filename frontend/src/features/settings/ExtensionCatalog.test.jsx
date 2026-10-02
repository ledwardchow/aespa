import { render, screen, waitFor, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { SettingsPage } from "./SettingsPage.jsx";

vi.mock("../../shared/api/settings.js");

test("shows selectable extension profiles and extension-owned providers", async () => {
  settingsApi.listLLMProfiles.mockResolvedValue([
    {
      id: 41,
      name: "Review",
      default_model_name: "Claude",
      role_models: {},
      extension_id: "example.llm",
      extension_name: "Example",
    },
  ]);
  settingsApi.listLLMModels.mockResolvedValue([]);
  settingsApi.listLLMProviders.mockResolvedValue([]);
  settingsApi.listExtensionLLMCatalog.mockResolvedValue({
    providers: [
      {
        id: "extension:example.llm:provider:aws",
        name: "AWS account",
        api_format: "bedrock",
        models: ["claude"],
        extension_id: "example.llm",
        extension_name: "Example",
      },
    ],
    models: [
      {
        id: "extension:example.llm:model:claude",
        name: "Claude",
        model: "claude",
        provider_id: "extension:example.llm:provider:aws",
        extension_id: "example.llm",
      },
    ],
    profiles: [],
  });

  const view = render(<SettingsPage section="profiles" />);
  const profileRow = (await screen.findByText("Review")).closest(".settings-list-row");
  expect(within(profileRow).getByText("Extension storage")).toBeTruthy();
  expect(within(profileRow).queryByRole("button", { name: "Edit" })).toBeNull();
  expect(within(profileRow).getByRole("button", { name: "Set as default" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "New profile" }).disabled).toBe(true);

  view.rerender(<SettingsPage section="providers" />);
  const providerRow = (await screen.findByText("AWS account")).closest(".settings-list-row");
  expect(within(providerRow).getByText("Extension storage")).toBeTruthy();
  expect(within(providerRow).getByText("1")).toBeTruthy();
  expect(within(providerRow).queryByRole("button", { name: "Delete" })).toBeNull();
  await waitFor(() => expect(settingsApi.listExtensionLLMCatalog).toHaveBeenCalledTimes(1));
});
