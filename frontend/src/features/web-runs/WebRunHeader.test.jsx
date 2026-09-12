import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { WebRunHeader } from "./WebRunHeader.jsx";

const props = {
  run: { id: 1, name: "Run", site_id: 1, pages_discovered: 1 },
  siteName: "Site",
  profiles: [],
  crawlerActive: false,
  testLeadActive: false,
  canStart: false,
  canStop: false,
  canStartScan: true,
  canStopScan: false,
  canResume: false,
  canImportCrawl: false,
  crawlStopping: false,
  scanStopping: false,
  coverageMode: "track",
  onCoverageMode: vi.fn(),
  onStart: vi.fn(),
  onStop: vi.fn(),
  onStartScan: vi.fn(),
  onStopScan: vi.fn(),
  onResume: vi.fn(),
  onExportCrawl: vi.fn(),
  onImportCrawl: vi.fn(),
  aliceRunning: false,
  onStopAlice: vi.fn(),
};

test("only shows Deep mode when its feature preference is enabled", () => {
  const { rerender } = render(<WebRunHeader {...props} showDeepScan={false} />);

  expect(screen.queryByRole("option", { name: "Deep" })).toBeNull();

  rerender(<WebRunHeader {...props} showDeepScan={true} />);

  expect(screen.getByRole("option", { name: "Deep" })).toBeTruthy();
});
