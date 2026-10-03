import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { ScanProfileForm } from "./ScanProfileForm.jsx";

vi.mock("../../shared/api/settings.js");

const models = [
  {
    id: 11,
    name: "OpenAI fast",
    model: "gpt-fast",
    provider_id: 1,
    provider_name: "OpenAI",
  },
  {
    id: 12,
    name: "OpenAI strong",
    model: "gpt-strong",
    provider_id: 1,
    provider_name: "OpenAI",
  },
  {
    id: 21,
    name: "Anthropic strong",
    model: "claude-strong",
    provider_id: 2,
    provider_name: "Anthropic",
  },
];

const profile = {
  id: 7,
  name: "Full scan",
  default_model_id: 12,
  role_models: { crawler: 11 },
};

beforeEach(() => {
  vi.clearAllMocks();
});

test("selects the provider before showing its models", async () => {
  const user = userEvent.setup();
  render(<ScanProfileForm mode="edit" profile={profile} models={models} />);

  expect(screen.getByLabelText("Default model provider").value).toBe("1");
  expect(screen.getByLabelText("Default model").value).toBe("12");
  expect(screen.getByLabelText("Crawler provider").value).toBe("1");
  expect(screen.getByLabelText("Crawler model").value).toBe("11");

  await user.selectOptions(screen.getByLabelText("Default model provider"), "2");

  const defaultModel = screen.getByLabelText("Default model");
  expect(defaultModel.value).toBe("");
  expect(
    within(defaultModel).getByRole("option", { name: "Anthropic strong (claude-strong)" }),
  ).toBeTruthy();
  expect(
    within(defaultModel).queryByRole("option", { name: "OpenAI strong (gpt-strong)" }),
  ).toBeNull();
});

test("saves model ids after provider and model selection", async () => {
  const user = userEvent.setup();
  settingsApi.updateLLMProfile.mockResolvedValue(profile);
  render(<ScanProfileForm mode="edit" profile={profile} models={models} />);

  await user.selectOptions(screen.getByLabelText("Crawler provider"), "2");
  await user.selectOptions(screen.getByLabelText("Crawler model"), "21");
  await user.click(screen.getByRole("button", { name: "Save profile" }));

  expect(settingsApi.updateLLMProfile).toHaveBeenCalledWith(7, {
    name: "Full scan",
    default_model_id: 12,
    role_models: { crawler: 21 },
  });
});
