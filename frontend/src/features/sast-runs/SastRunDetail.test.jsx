import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";
import { SastRunDetailExperience } from "./SastRunDetail.jsx";

vi.mock("../../shared/api/sastRuns.js");
vi.mock("../../shared/api/settings.js");

class FakeEventSource {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.close = vi.fn();
    FakeEventSource.instances.push(this);
  }
}

const run = {
  id: 249,
  name: "BankOfEd-main.zip",
  analysis_mode: "deep",
  status: "scanning",
  llm_profile_id: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
  sastRunsApi.getSastRun.mockResolvedValue(run);
  sastRunsApi.getSastScanStatus.mockResolvedValue({ running: true });
  sastRunsApi.getSastAnalysis.mockResolvedValue({
    phases: {},
    coverage: { files: [], summary: {} },
    work_program: {},
    assurance: {},
    report: {},
  });
  sastRunsApi.getSastScanLog.mockResolvedValue([]);
  sastRunsApi.getSastAgentLog.mockResolvedValue([]);
  sastRunsApi.getSastLeads.mockResolvedValue([]);
  sastRunsApi.getSastTokenUsage.mockResolvedValue({});
  sastRunsApi.getSastHandoffTargets.mockResolvedValue([]);
  settingsApi.listLLMProfiles.mockResolvedValue([]);
});

afterEach(() => {
  delete window.HTMLElement.prototype.scrollIntoView;
  vi.unstubAllGlobals();
});

test("shows scanner events without reloading every SAST endpoint", async () => {
  const user = userEvent.setup();
  render(<SastRunDetailExperience runId={249} initialTab="activity" />);

  expect(await screen.findByText("BankOfEd-main.zip")).toBeTruthy();
  await waitFor(() => expect(sastRunsApi.getSastRun).toHaveBeenCalledTimes(1));
  await user.click(screen.getByRole("button", { name: "Log" }));

  act(() => {
    FakeEventSource.instances[0].onmessage({
      data: JSON.stringify({
        type: "scanner_phase",
        phase: "discovery",
        status: "running",
        message: "read_file: src/Router.php",
      }),
    });
  });

  expect(await screen.findByText("read_file: src/Router.php")).toBeTruthy();
  expect(sastRunsApi.getSastRun).toHaveBeenCalledTimes(1);
  expect(sastRunsApi.getSastScanStatus).toHaveBeenCalledTimes(1);
  expect(sastRunsApi.getSastAnalysis).toHaveBeenCalledTimes(1);
  expect(sastRunsApi.getSastScanLog).toHaveBeenCalledTimes(1);
  expect(sastRunsApi.getSastAgentLog).toHaveBeenCalledTimes(1);
  expect(sastRunsApi.getSastLeads).toHaveBeenCalledTimes(1);
  expect(sastRunsApi.getSastTokenUsage).toHaveBeenCalledTimes(1);
  expect(sastRunsApi.getSastHandoffTargets).toHaveBeenCalledTimes(1);
});

test("opens legacy security check links in the consolidated Threats view", async () => {
  sastRunsApi.getSastAnalysis.mockResolvedValue({
    phases: {
      threat_model: {
        data: {
          summary: "One source-backed scenario.",
          scenarios: [
            {
              scenario_key: "scenario-1",
              title: "Protect account access",
              status: "planned",
              priority: "high",
              confidence: 0.8,
            },
          ],
        },
      },
      planning: {
        data: {
          obligations: [
            {
              obligation_key: "obligation-1",
              source_scenario_key: "scenario-1",
              status: "pending",
            },
          ],
        },
      },
    },
    coverage: { files: [], summary: {} },
    work_program: {},
    assurance: {},
    report: {},
  });

  render(<SastRunDetailExperience runId={249} initialTab="obligations" />);

  expect(await screen.findByText("Protect account access")).toBeTruthy();
  expect(screen.getByRole("tab", { name: "Threats 1" }).getAttribute("aria-selected")).toBe("true");
  expect(screen.queryByRole("tab", { name: /Security checks/ })).toBeNull();
});
