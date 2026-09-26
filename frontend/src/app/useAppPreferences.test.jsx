import { renderHook } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../shared/api/settings.js";
import * as extensionsApi from "../shared/api/extensions.js";
import { useAppPreferences } from "./useAppPreferences.js";

vi.mock("../shared/api/settings.js");
vi.mock("../shared/api/extensions.js");

beforeEach(() => {
  localStorage.clear();
  settingsApi.getVersion.mockResolvedValue({ version: "test" });
  settingsApi.getReportingDebugConfig.mockResolvedValue({});
  extensionsApi.listExtensions.mockResolvedValue([]);
});

test("hides Deep Scan by default", () => {
  const { result } = renderHook(() => useAppPreferences());

  expect(result.current.showDeepScan).toBe(false);
});

test("restores an enabled Deep Scan preference", () => {
  localStorage.setItem("aespa_show_deep_scan", "true");

  const { result } = renderHook(() => useAppPreferences());

  expect(result.current.showDeepScan).toBe(true);
});

test("hides Team Scan by default and restores its experimental preference", () => {
  const hidden = renderHook(() => useAppPreferences());
  expect(hidden.result.current.showTeamScan).toBe(false);
  hidden.unmount();

  localStorage.setItem("aespa_show_team_scan", "true");
  const enabled = renderHook(() => useAppPreferences());
  expect(enabled.result.current.showTeamScan).toBe(true);
});
