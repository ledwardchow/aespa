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
  localStorage.removeItem("aespa_sast_alice_drawer_open");
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
  sastRunsApi.getSastLiveTargets.mockResolvedValue([]);
  sastRunsApi.getSastAliceSessions.mockResolvedValue({ chats: [] });
  sastRunsApi.getSastAliceStatus.mockResolvedValue({ running: false });
  sastRunsApi.saveSastAliceSessions.mockResolvedValue({});
  settingsApi.listLLMProfiles.mockResolvedValue([]);
});

test("collapses SAST chat to a right rail and remembers the drawer state", async () => {
  const user = userEvent.setup();
  sastRunsApi.getSastRun.mockResolvedValue({ ...run, source_archive_path: "/tmp/source.zip" });
  render(<SastRunDetailExperience runId={249} initialTab="coverage" />);

  await user.click(await screen.findByRole("button", { name: "Collapse A.L.I.C.E. chat" }));
  const rail = screen.getByRole("button", { name: "Show A.L.I.C.E. chat" });
  expect(rail.getAttribute("aria-expanded")).toBe("false");
  expect(document.querySelector(".sast-alice-sidebar--collapsed")).toBeTruthy();
  expect(localStorage.getItem("aespa_sast_alice_drawer_open")).toBe("false");

  await user.click(rail);
  expect(screen.getByRole("button", { name: "Collapse A.L.I.C.E. chat" })).toBeTruthy();
  expect(document.querySelector(".sast-alice-sidebar--collapsed")).toBeNull();
  expect(localStorage.getItem("aespa_sast_alice_drawer_open")).toBe("true");
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
  expect(sastRunsApi.getSastLiveTargets).toHaveBeenCalledTimes(1);
});

test("shows token usage on the coverage tab", async () => {
  sastRunsApi.getSastTokenUsage.mockResolvedValue({ total_input: 1200, total_output: 300 });
  render(<SastRunDetailExperience runId={249} initialTab="coverage" />);

  expect(await screen.findByText("↑1.2K in")).toBeTruthy();
  expect(screen.getByText("↓300 out")).toBeTruthy();
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

test("shows a source failure and resumes preparation on the same run", async () => {
  const user = userEvent.setup();
  const failedRun = {
    ...run,
    status: "failed",
    source_provider: "aespa.githubrepository",
    source_archive_path: null,
    error_message: "GitHub authentication expired. Sign in, then resume source preparation.",
  };
  sastRunsApi.getSastRun.mockResolvedValue(failedRun);
  sastRunsApi.getSastScanStatus.mockResolvedValue({ running: false });
  sastRunsApi.resumeSastSource.mockResolvedValue({ ...failedRun, status: "preparing" });

  render(<SastRunDetailExperience runId={249} initialTab="coverage" />);

  expect(await screen.findByText(/GitHub authentication expired/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Start SAST Scan" })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Resume source preparation" }));
  expect(sastRunsApi.resumeSastSource).toHaveBeenCalledWith(249);
});

test("shows Resume failed work for unfinished work without a failed worker count", async () => {
  const user = userEvent.setup();
  sastRunsApi.getSastRun.mockResolvedValue({ ...run, status: "completed" });
  sastRunsApi.getSastScanStatus.mockResolvedValue({
    running: false,
    resumable_work: true,
  });
  sastRunsApi.resumeSastScan.mockResolvedValue({ running: true });

  render(<SastRunDetailExperience runId={249} initialTab="coverage" />);

  await user.click(await screen.findByRole("button", { name: "Resume failed work" }));
  expect(sastRunsApi.resumeSastScan).toHaveBeenCalledWith(249);
});
