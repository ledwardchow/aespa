import { renderHook } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../shared/api/settings.js";
import { useAppPreferences } from "./useAppPreferences.js";

vi.mock("../shared/api/settings.js");

beforeEach(() => {
  localStorage.clear();
  settingsApi.getVersion.mockResolvedValue({ version: "test" });
  settingsApi.getReportingDebugConfig.mockResolvedValue({});
  settingsApi.getBenchmarkLabConfig.mockResolvedValue({});
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
