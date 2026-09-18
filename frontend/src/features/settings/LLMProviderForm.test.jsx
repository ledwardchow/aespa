import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { LLMProviderForm } from "./LLMProviderForm.jsx";

vi.mock("../../shared/api/settings.js");

const provider = {
  id: 7,
  name: "Example provider",
  api_format: "openai",
  base_url: "https://api.openai.com/v1",
  username: null,
  project_id: null,
  location: null,
  models: ["existing-model"],
  model_capabilities: {},
  has_api_key: false,
};

beforeEach(() => {
  vi.clearAllMocks();
});

test("saves an edited provider before exposing an added model link", async () => {
  const user = userEvent.setup();
  const savedProvider = { ...provider, models: ["existing-model", "new-model"] };
  settingsApi.updateLLMProvider.mockResolvedValue(savedProvider);
  const onProviderUpdated = vi.fn();
  const onConfigureModel = vi.fn();

  render(
    <LLMProviderForm
      mode="edit"
      provider={provider}
      models={[]}
      profiles={[]}
      onProviderUpdated={onProviderUpdated}
      onConfigureModel={onConfigureModel}
    />,
  );

  await user.type(screen.getByLabelText("New model name"), "new-model");
  await user.click(screen.getByRole("button", { name: "Add model" }));

  await waitFor(() => expect(settingsApi.updateLLMProvider).toHaveBeenCalledTimes(1));
  expect(settingsApi.updateLLMProvider.mock.calls[0][0]).toBe(7);
  expect(settingsApi.updateLLMProvider.mock.calls[0][1].models).toEqual([
    "existing-model",
    "new-model",
  ]);
  expect(onProviderUpdated).toHaveBeenCalledWith(savedProvider);

  await user.click(screen.getByRole("button", { name: "new-model" }));
  expect(onConfigureModel).toHaveBeenCalledWith("new-model", undefined);
});

test("saves models loaded from the provider API", async () => {
  const user = userEvent.setup();
  const savedProvider = {
    ...provider,
    models: ["loaded-model"],
    model_capabilities: { "loaded-model": { context_window_tokens: 128000 } },
  };
  settingsApi.discoverModelOptions.mockResolvedValue({
    models: ["loaded-model"],
    capabilities: savedProvider.model_capabilities,
  });
  settingsApi.updateLLMProvider.mockResolvedValue(savedProvider);
  const onProviderUpdated = vi.fn();

  render(
    <LLMProviderForm
      mode="edit"
      provider={provider}
      models={[]}
      profiles={[]}
      onProviderUpdated={onProviderUpdated}
      onConfigureModel={vi.fn()}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Load models from API" }));

  await waitFor(() => expect(settingsApi.updateLLMProvider).toHaveBeenCalledTimes(1));
  expect(settingsApi.updateLLMProvider.mock.calls[0][1]).toMatchObject({
    models: ["loaded-model"],
    model_capabilities: savedProvider.model_capabilities,
  });
  expect(onProviderUpdated).toHaveBeenCalledWith(savedProvider);
  expect(screen.getByRole("button", { name: "loaded-model" })).toBeTruthy();
});

test("keeps profile models when loading models from the provider API", async () => {
  const user = userEvent.setup();
  const configuredModel = {
    id: 42,
    name: "Existing model settings",
    provider_id: provider.id,
    model: "existing-model",
  };
  const providerWithCapabilities = {
    ...provider,
    model_capabilities: { "existing-model": { context_window_tokens: 64000 } },
  };
  const savedProvider = {
    ...providerWithCapabilities,
    models: ["loaded-model", "existing-model"],
    model_capabilities: {
      "loaded-model": { context_window_tokens: 128000 },
      "existing-model": { context_window_tokens: 64000 },
    },
  };
  settingsApi.discoverModelOptions.mockResolvedValue({
    models: ["loaded-model"],
    capabilities: { "loaded-model": { context_window_tokens: 128000 } },
  });
  settingsApi.updateLLMProvider.mockResolvedValue(savedProvider);

  render(
    <LLMProviderForm
      mode="edit"
      provider={providerWithCapabilities}
      models={[configuredModel]}
      profiles={[
        {
          id: 9,
          name: "Full scan",
          default_model_id: configuredModel.id,
          role_models: {},
        },
      ]}
      onProviderUpdated={vi.fn()}
      onConfigureModel={vi.fn()}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Load models from API" }));

  await waitFor(() => expect(settingsApi.updateLLMProvider).toHaveBeenCalledTimes(1));
  expect(settingsApi.updateLLMProvider.mock.calls[0][1]).toMatchObject({
    models: ["loaded-model", "existing-model"],
    model_capabilities: savedProvider.model_capabilities,
  });
  expect(
    screen.getByText(
      "Loaded 1 model(s) and capability metadata from API. Kept 1 model(s) used by scan profiles.",
    ),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: "existing-model" })).toBeTruthy();
});
