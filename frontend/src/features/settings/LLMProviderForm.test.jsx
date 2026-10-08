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

test("shows Mantle's selected API for a discovered model", () => {
  render(
    <LLMProviderForm
      mode="edit"
      provider={{
        ...provider,
        api_format: "bedrock_mantle",
        models: ["anthropic.claude-sonnet-5"],
        model_capabilities: {
          "anthropic.claude-sonnet-5": { inference_api: "messages" },
        },
      }}
      models={[]}
      profiles={[]}
      onProviderUpdated={vi.fn()}
      onConfigureModel={vi.fn()}
    />,
  );

  expect(screen.getByText("Anthropic Messages API")).toBeTruthy();
});

test("saves the selected AWS profile for Bedrock", async () => {
  const user = userEvent.setup();
  settingsApi.updateLLMProvider.mockResolvedValue({
    ...provider,
    api_format: "bedrock",
    aws_profile: "scan-operator",
  });
  render(
    <LLMProviderForm
      mode="edit"
      provider={{ ...provider, api_format: "bedrock" }}
      models={[]}
      profiles={[]}
      onProviderUpdated={vi.fn()}
      onConfigureModel={vi.fn()}
    />,
  );

  await user.type(screen.getByLabelText("AWS profile (optional)"), "scan-operator");
  await user.click(screen.getByRole("button", { name: "Save provider" }));
  await waitFor(() => expect(settingsApi.updateLLMProvider).toHaveBeenCalledTimes(1));
  expect(settingsApi.updateLLMProvider.mock.calls[0][1].aws_profile).toBe("scan-operator");
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
      "Loaded 1 model(s) from the API. Kept 1 model(s) used by scan profiles.",
    ),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: "existing-model" })).toBeTruthy();
});

test("shows the selected ChatGPT account's Daybreak access", async () => {
  settingsApi.getChatGPTPlanStatus.mockResolvedValue({
    active: "oaiapp_test",
    accounts: [{ client_id: "oaiapp_test", email: "user@example.test", signed_in: true }],
  });
  settingsApi.checkChatGPTPlanAccess.mockResolvedValue({
    models: ["gpt-6-sol", "gpt-6-luna"],
    daybreak: { blue: true, red: false },
  });

  render(
    <LLMProviderForm
      mode="edit"
      provider={{ ...provider, api_format: "openai_chatgpt_plan", username: "oaiapp_test" }}
      models={[]}
      profiles={[]}
    />,
  );

  await waitFor(() => expect(screen.getByText("Daybreak Blue: Available")).toBeTruthy());
  expect(screen.getByText("Daybreak Red: Not available")).toBeTruthy();
  expect(settingsApi.checkChatGPTPlanAccess).toHaveBeenCalledWith("oaiapp_test");
});

test("warns when the selected ChatGPT account has no Daybreak access", async () => {
  settingsApi.getChatGPTPlanStatus.mockResolvedValue({
    active: "oaiapp_test",
    accounts: [{ client_id: "oaiapp_test", signed_in: true }],
  });
  settingsApi.checkChatGPTPlanAccess.mockResolvedValue({
    models: [], daybreak: { blue: false, red: false },
  });

  render(
    <LLMProviderForm
      mode="edit"
      provider={{ ...provider, api_format: "openai_chatgpt_plan", username: "oaiapp_test" }}
      models={[]}
      profiles={[]}
    />,
  );

  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain("does not have Daybreak Blue or Red access"),
  );
  expect(screen.getByText("Daybreak Blue: Not available")).toBeTruthy();
  expect(screen.getByText("Daybreak Red: Not available")).toBeTruthy();
});

test("shows Daybreak Red when the access check confirms it", async () => {
  settingsApi.getChatGPTPlanStatus.mockResolvedValue({
    active: "oaiapp_test",
    accounts: [{ client_id: "oaiapp_test", signed_in: true }],
  });
  settingsApi.checkChatGPTPlanAccess.mockResolvedValue({
    models: ["gpt-daybreak-red-latest"],
    daybreak: { blue: false, red: true },
  });

  render(
    <LLMProviderForm
      mode="edit"
      provider={{ ...provider, api_format: "openai_chatgpt_plan", username: "oaiapp_test" }}
      models={[]}
      profiles={[]}
    />,
  );

  await waitFor(() => expect(screen.getByText("Daybreak Red: Available")).toBeTruthy());
  expect(screen.queryByRole("alert")).toBeNull();
});

test("loads ChatGPT models verified for the account when the catalog omits them", async () => {
  const user = userEvent.setup();
  settingsApi.getChatGPTPlanStatus.mockResolvedValue({
    active: "oaiapp_test",
    accounts: [{ client_id: "oaiapp_test", signed_in: true }],
  });
  settingsApi.discoverModelOptions.mockResolvedValue({
    models: ["gpt-6-astra"], capabilities: {},
  });
  settingsApi.checkChatGPTPlanAccess.mockResolvedValue({
    models: ["gpt-6-sol", "gpt-6-luna"],
    daybreak: { blue: true, red: false },
  });
  settingsApi.updateLLMProvider.mockImplementation(async (_id, payload) => ({
    ...provider,
    api_format: "openai_chatgpt_plan",
    username: "oaiapp_test",
    models: payload.models,
  }));

  render(
    <LLMProviderForm
      mode="edit"
      provider={{ ...provider, api_format: "openai_chatgpt_plan", username: "oaiapp_test" }}
      models={[]}
      profiles={[]}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Load models from API" }));
  await waitFor(() => expect(settingsApi.updateLLMProvider).toHaveBeenCalledTimes(1));
  expect(settingsApi.checkChatGPTPlanAccess).toHaveBeenCalledWith("oaiapp_test", true);
  expect(settingsApi.updateLLMProvider.mock.calls[0][1].models).toEqual([
    "gpt-6-astra", "gpt-6-sol", "gpt-6-luna",
  ]);
});

test("loads ChatGPT account models automatically when the account is selected", async () => {
  settingsApi.getChatGPTPlanStatus.mockResolvedValue({
    active: "oaiapp_test",
    accounts: [{ client_id: "oaiapp_test", signed_in: true }],
  });
  settingsApi.discoverModelOptions.mockResolvedValue({
    models: ["gpt-6-sol", "gpt-6-luna"],
    capabilities: {
      "gpt-6-sol": { context_window_tokens: 1050000, max_output_tokens: 128000 },
      "gpt-6-luna": { context_window_tokens: 1050000, max_output_tokens: 128000 },
    },
  });
  settingsApi.checkChatGPTPlanAccess.mockResolvedValue({
    models: ["gpt-6-sol", "gpt-6-luna"],
    daybreak: { blue: true, red: false },
  });
  settingsApi.updateLLMProvider.mockImplementation(async (_id, payload) => ({
    ...provider,
    api_format: "openai_chatgpt_plan",
    username: payload.username,
    models: payload.models,
    model_capabilities: payload.model_capabilities,
  }));

  render(
    <LLMProviderForm
      mode="edit"
      provider={{ ...provider, api_format: "openai_chatgpt_plan", username: null, models: [] }}
      models={[]}
      profiles={[]}
    />,
  );

  await waitFor(() => expect(settingsApi.updateLLMProvider).toHaveBeenCalledTimes(1));
  expect(settingsApi.updateLLMProvider.mock.calls[0][1]).toMatchObject({
    username: "oaiapp_test",
    models: ["gpt-6-sol", "gpt-6-luna"],
    model_capabilities: {
      "gpt-6-sol": { context_window_tokens: 1050000, max_output_tokens: 128000 },
    },
  });
});
