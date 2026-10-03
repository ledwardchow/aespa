import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { LLMModelForm } from "./LLMModelForm.jsx";

vi.mock("../../shared/api/settings.js");

const provider = {
  id: 7,
  name: "Example provider",
  api_format: "openai",
  base_url: "https://api.openai.com/v1",
  models: ["model-a", "model-b"],
  model_capabilities: {
    "model-a": { context_window_tokens: 128000 },
    "model-b": { context_window_tokens: 128000 },
  },
};

const profile = {
  id: 11,
  name: "Primary model",
  provider_id: provider.id,
  model: "model-a",
  max_tpm: 120000,
  max_rpm: 60,
  max_tokens: 4096,
  max_context_tokens: 128000,
  context_limit_source: "provider",
  temperature: null,
  use_vision: false,
  force_tool_choice: false,
  reasoning_effort: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  settingsApi.discoverModelOptions.mockResolvedValue({ capabilities: {} });
});

test("edits rate limits on the selected provider and model pair", async () => {
  const user = userEvent.setup();
  settingsApi.updateLLMModel.mockResolvedValue({ ...profile, max_tpm: 240000, max_rpm: 90 });

  render(
    <LLMModelForm
      mode="edit"
      profile={profile}
      providers={[provider]}
      modelConfigs={[
        profile,
        {
          ...profile,
          id: 12,
          name: "Secondary model",
          model: "model-b",
          max_tpm: 240000,
          max_rpm: 90,
        },
      ]}
    />,
  );

  expect(screen.getByLabelText("Max Tokens Per Minute (TPM)").value).toBe("120000");
  expect(screen.getByLabelText("Max Requests Per Minute (RPM)").value).toBe("60");

  await user.selectOptions(screen.getByLabelText("Model"), "model-b");
  expect(screen.getByLabelText("Max Tokens Per Minute (TPM)").value).toBe("240000");
  expect(screen.getByLabelText("Max Requests Per Minute (RPM)").value).toBe("90");

  await user.click(screen.getByRole("button", { name: "Save model" }));

  await waitFor(() => expect(settingsApi.updateLLMModel).toHaveBeenCalledTimes(1));
  expect(settingsApi.updateLLMModel).toHaveBeenCalledWith(
    profile.id,
    expect.objectContaining({
      provider_id: provider.id,
      model: "model-b",
      max_tpm: 240000,
      max_rpm: 90,
    }),
  );
});

test("loads thinking levels on the first edit when only the context window was saved", async () => {
  settingsApi.discoverModelOptions.mockResolvedValue({
    capabilities: {
      "model-a": {
        context_window_tokens: 128000,
        supported_efforts: ["low", "medium", "high"],
        default_effort: "medium",
      },
    },
  });

  render(<LLMModelForm mode="edit" profile={profile} providers={[provider]} />);

  await waitFor(() => expect(settingsApi.discoverModelOptions).toHaveBeenCalledTimes(1));
  expect(settingsApi.discoverModelOptions).toHaveBeenCalledWith(
    expect.objectContaining({ provider_id: provider.id }),
  );
  const thinkingLevel = screen.getByLabelText(/Thinking level/);
  await waitFor(() => expect(thinkingLevel.options).toHaveLength(4));
  expect([...thinkingLevel.options].map((option) => option.value)).toEqual([
    "",
    "low",
    "medium",
    "high",
  ]);
  expect(thinkingLevel.options[0].textContent).toContain("medium");
});
