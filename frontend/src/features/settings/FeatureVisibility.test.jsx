import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { DebugPage } from "./DebugPage.jsx";

vi.mock("../../shared/api/settings.js");

beforeEach(() => {
  localStorage.clear();
  settingsApi.getBrowserDebugConfig.mockResolvedValue({
    browser_engine: "playwright_chromium",
    browser_visible: false,
    playwright_chromium_available: true,
    playwright_chromium_installing: false,
    graphical_display_available: true,
  });
  settingsApi.getBenchmarkLabConfig.mockResolvedValue({ panel_enabled: false });
  settingsApi.getReportingDebugConfig.mockResolvedValue({
    capture_enabled: false,
    panel_enabled: false,
  });
  settingsApi.getCloudflareAccessConfig.mockResolvedValue({ audience: null });
});

test("hides Playwright Chromium and selects system Chrome after provisioning fails", async () => {
  settingsApi.getBrowserDebugConfig.mockResolvedValue({
    browser_engine: "system_chrome",
    browser_visible: false,
    playwright_chromium_available: false,
    playwright_chromium_installing: false,
    graphical_display_available: true,
  });

  render(
    <DebugPage
      showUsername={true}
      setShowUsername={vi.fn()}
      showSystems={true}
      setShowSystems={vi.fn()}
      showDeepScan={false}
      setShowDeepScan={vi.fn()}
      showTeamScan={false}
      setShowTeamScan={vi.fn()}
      username=""
      reportingDebugCfg={{ capture_enabled: false, panel_enabled: false }}
      setReportingDebugCfg={vi.fn()}
      benchmarkLabCfg={{ panel_enabled: false }}
      setBenchmarkLabCfg={vi.fn()}
    />,
  );

  await waitFor(() => expect(screen.getByLabelText("Browser engine").value).toBe("system_chrome"));
  expect(screen.queryByRole("option", { name: /Playwright Chromium/ })).toBeNull();
  expect(screen.getByText(/could not be installed/)).toBeTruthy();
});

test("groups Systems, Deep Scan, and Team Scan under Experimental Features", () => {
  const setShowDeepScan = vi.fn();
  const setShowTeamScan = vi.fn();
  render(
    <DebugPage
      showUsername={true}
      setShowUsername={vi.fn()}
      showSystems={true}
      setShowSystems={vi.fn()}
      showDeepScan={false}
      setShowDeepScan={setShowDeepScan}
      showTeamScan={false}
      setShowTeamScan={setShowTeamScan}
      username=""
      reportingDebugCfg={{ capture_enabled: false, panel_enabled: false }}
      setReportingDebugCfg={vi.fn()}
      benchmarkLabCfg={{ panel_enabled: false }}
      setBenchmarkLabCfg={vi.fn()}
    />,
  );

  expect(screen.getByText("Experimental Features")).toBeTruthy();
  expect(screen.getByLabelText("Systems scanning").checked).toBe(true);
  const deepScanToggle = screen.getByLabelText("DAST Deep Scan Mode");
  expect(deepScanToggle.checked).toBe(false);

  fireEvent.click(deepScanToggle);

  expect(setShowDeepScan).toHaveBeenCalledWith(true);
  expect(localStorage.getItem("aespa_show_deep_scan")).toBe("true");

  const teamScanToggle = screen.getByLabelText("DAST Team Scan Mode");
  expect(teamScanToggle.checked).toBe(false);
  fireEvent.click(teamScanToggle);
  expect(setShowTeamScan).toHaveBeenCalledWith(true);
  expect(localStorage.getItem("aespa_show_team_scan")).toBe("true");
});
