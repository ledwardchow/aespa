import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { RetireListSettings } from "./RetireListSettings.jsx";

vi.mock("../../shared/api/settings.js");

const shipped = {
  copy: "shipped",
  fetched_at: "2026-10-09T10:38:57+00:00",
  libraries: 74,
  vulnerabilities: 759,
  patterns: 331,
  skipped_patterns: 1,
};

beforeEach(() => {
  settingsApi.getRetireListStatus.mockResolvedValue(shipped);
  settingsApi.getScannerPolicy.mockResolvedValue({ retire_auto_update: true });
});

test("shows the list in use and the automatic update setting", async () => {
  render(<RetireListSettings />);

  expect(await screen.findByText("Copy included with AESPA")).toBeTruthy();
  expect(screen.getByText("74 libraries, 759 known issues")).toBeTruthy();
  expect(screen.getByText(/1 of 331 detection patterns/)).toBeTruthy();
  const toggle = await screen.findByLabelText("Download the latest list when a scan starts");
  expect(toggle.checked).toBe(true);
});

test("refreshes the list on demand", async () => {
  settingsApi.refreshRetireList.mockResolvedValue({
    ...shipped,
    copy: "downloaded",
    status: "updated",
  });
  render(<RetireListSettings />);
  await screen.findByText("Copy included with AESPA");

  fireEvent.click(screen.getByRole("button", { name: "Refresh now" }));

  expect(await screen.findByText("Downloaded the latest list.")).toBeTruthy();
  expect(screen.getByText("Downloaded copy")).toBeTruthy();
});

test("explains a failed download", async () => {
  settingsApi.refreshRetireList.mockResolvedValue({
    ...shipped,
    status: "failed",
    error: "timed out",
  });
  render(<RetireListSettings />);
  await screen.findByText("Copy included with AESPA");

  fireEvent.click(screen.getByRole("button", { name: "Refresh now" }));

  expect(
    await screen.findByText("Could not download the latest list: timed out"),
  ).toBeTruthy();
});
