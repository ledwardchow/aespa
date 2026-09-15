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

test("only shows Team mode when its feature preference is enabled", () => {
  const { rerender } = render(<WebRunHeader {...props} showTeamScan={false} />);
  expect(screen.queryByRole("option", { name: "Team" })).toBeNull();

  rerender(<WebRunHeader {...props} showTeamScan />);
  expect(screen.getByRole("option", { name: "Team" })).toBeTruthy();
});

test("locks a started Team run to Team mode", () => {
  render(
    <WebRunHeader
      {...props}
      run={{ ...props.run, coverage_mode: "team", scan_mode_locked: true }}
      coverageMode="team"
      showDeepScan
    />,
  );

  expect(screen.getByRole("combobox", { name: "Scan mode:" }).disabled).toBe(true);
  expect(screen.getByRole("option", { name: "Team" }).disabled).toBe(false);
  expect(screen.getByRole("option", { name: "Standard" }).disabled).toBe(true);
  expect(screen.getByRole("option", { name: "Deep" }).disabled).toBe(true);
  expect(screen.getByTitle("Test run is inactive").textContent).toBe("Inactive");
});

test.each([
  ["crawler", { crawlerActive: true }],
  ["Test Lead", { testLeadActive: true }],
  ["ALICE", { aliceRunning: true }],
])("shows one Active badge while %s is running", (_agent, activeProp) => {
  render(<WebRunHeader {...props} {...activeProp} />);

  expect(screen.getByTitle("Test run is active").textContent).toBe("Active");
  expect(screen.queryByTitle(/agent is/)).toBeNull();
});

test("locks a started Deep run to Deep mode", () => {
  render(
    <WebRunHeader
      {...props}
      run={{ ...props.run, coverage_mode: "deep", scan_mode_locked: true }}
      coverageMode="deep"
      showDeepScan={false}
    />,
  );

  expect(screen.getByRole("combobox", { name: "Scan mode:" }).disabled).toBe(true);
  expect(screen.getByRole("option", { name: "Deep" }).disabled).toBe(false);
  expect(screen.getByRole("option", { name: "Quick" }).disabled).toBe(true);
  expect(screen.getByRole("option", { name: "Standard" }).disabled).toBe(true);
  expect(screen.getByRole("option", { name: "Full" }).disabled).toBe(true);
});

test("prevents a started non-Deep run from selecting Deep", () => {
  render(
    <WebRunHeader
      {...props}
      run={{ ...props.run, coverage_mode: "track", scan_mode_locked: true }}
      showDeepScan
      showTeamScan
    />,
  );

  expect(screen.getByRole("option", { name: "Deep" }).disabled).toBe(true);
  expect(screen.getByRole("option", { name: "Team" }).disabled).toBe(true);
  expect(screen.getByRole("option", { name: "Standard" }).disabled).toBe(false);
});
