import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as extensionsApi from "../../shared/api/extensions.js";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";
import { nav } from "../../shared/navigation/router.js";
import { SastRunForm } from "./SastRunForm.jsx";

vi.mock("../../shared/api/extensions.js");
vi.mock("../../shared/api/sastRuns.js");
vi.mock("../../shared/api/settings.js");
vi.mock("../../shared/navigation/router.js", () => ({ nav: vi.fn() }));

beforeEach(() => {
  vi.clearAllMocks();
  settingsApi.listLLMProfiles.mockResolvedValue([]);
  extensionsApi.listSourceProviders.mockResolvedValue([
    {
      id: "aespa.githubrepository",
      label: "GitHub repository",
      availability: { available: true, message: "GitHub CLI is authenticated." },
      request_fields: [
        { key: "repository", label: "Repository", type: "text", required: true },
        { key: "ref", label: "Branch, tag, or commit", type: "text", required: false },
      ],
    },
  ]);
  sastRunsApi.createSastRunFromSource.mockResolvedValue({ id: 41, status: "preparing" });
});

test("creates a SAST run from fields supplied by a source extension", async () => {
  const user = userEvent.setup();
  render(<SastRunForm />);

  await user.selectOptions(await screen.findByLabelText("Source"), "aespa.githubrepository");
  await user.type(screen.getByLabelText(/Repository/), "acme/payments");
  await user.type(screen.getByLabelText(/Branch, tag, or commit/), "release/1");
  await user.click(screen.getByRole("button", { name: "Create & Start Scan" }));

  expect(sastRunsApi.createSastRunFromSource).toHaveBeenCalledWith(
    expect.objectContaining({
      provider_id: "aespa.githubrepository",
      parameters: { repository: "acme/payments", ref: "release/1" },
    }),
  );
  expect(sastRunsApi.startSastScan).not.toHaveBeenCalled();
  expect(nav).toHaveBeenCalledWith("#/sast-runs/41/progress");
});
