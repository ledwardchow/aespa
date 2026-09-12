import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { DebugPage } from "./DebugPage.jsx";

vi.mock("../../shared/api/settings.js");

beforeEach(() => {
  localStorage.clear();
  settingsApi.getBrowserDebugConfig.mockResolvedValue({
    browser_engine: "playwright_chromium",
    browser_visible: false,
    graphical_display_available: true,
  });
  settingsApi.getBenchmarkLabConfig.mockResolvedValue({ panel_enabled: false });
  settingsApi.getReportingDebugConfig.mockResolvedValue({
    capture_enabled: false,
    panel_enabled: false,
  });
  settingsApi.getCloudflareAccessConfig.mockResolvedValue({ audience: null });
});

test("groups Applications and Deep Scan under Experimental Features", () => {
  const setShowDeepScan = vi.fn();
  render(
    <DebugPage
      showUsername={true}
      setShowUsername={vi.fn()}
      showApplications={true}
      setShowApplications={vi.fn()}
      showDeepScan={false}
      setShowDeepScan={setShowDeepScan}
      username=""
      reportingDebugCfg={{ capture_enabled: false, panel_enabled: false }}
      setReportingDebugCfg={vi.fn()}
      benchmarkLabCfg={{ panel_enabled: false }}
      setBenchmarkLabCfg={vi.fn()}
    />,
  );

  expect(screen.getByText("Experimental Features")).toBeTruthy();
  expect(screen.getByLabelText("Applications scanning").checked).toBe(true);
  const deepScanToggle = screen.getByLabelText("DAST Deep Scan Mode");
  expect(deepScanToggle.checked).toBe(false);

  fireEvent.click(deepScanToggle);

  expect(setShowDeepScan).toHaveBeenCalledWith(true);
  expect(localStorage.getItem("aespa_show_deep_scan")).toBe("true");
});
