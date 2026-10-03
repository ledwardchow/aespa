import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ScanPolicyPage } from "./ScanPolicyPage.jsx";

vi.mock("./ScannerPolicySettings.jsx", () => ({
  GlobalPolicySettings: () => <div>Global settings</div>,
  ScannerPolicySettings: () => <div>Test Lead settings</div>,
}));
vi.mock("./DebugPage.jsx", () => ({
  SystemSettingsPanels: ({ tab }) => <div>{tab} settings</div>,
}));
vi.mock("./ValidatorSettings.jsx", () => ({
  ValidatorSettings: () => <div>Validator settings</div>,
}));
vi.mock("./SpecialistAgentSettings.jsx", () => ({
  SpecialistAgentSettings: () => <div>Specialist settings</div>,
}));
vi.mock("./ReportingSettings.jsx", () => ({
  ReportingSettings: () => <div>Reporting settings</div>,
}));
vi.mock("./CrawlerSettings.jsx", () => ({
  CrawlerSettings: () => <div>Crawler settings</div>,
}));
vi.mock("./ComponentMapperSettings.jsx", () => ({
  ComponentMapperSettings: () => <div>Component Mapper settings</div>,
}));
vi.mock("./CodeExecutionSettings.jsx", () => ({
  CodeExecutionSettings: () => <div>Python Sandbox settings</div>,
}));
vi.mock("./DeepScanSettings.jsx", () => ({
  DeepScanSettings: () => <div>Deep Scan settings</div>,
}));
vi.mock("./SastSettings.jsx", () => ({ SastSettings: () => <div>SAST settings</div> }));
vi.mock("./UpstreamProxySettings.jsx", () => ({
  UpstreamProxySettings: () => <div>Proxy settings form</div>,
}));

test("only shows Deep Scan settings when its feature preference is enabled", () => {
  const { rerender } = render(<ScanPolicyPage showDeepScan={false} />);

  fireEvent.click(screen.getByRole("tab", { name: "DAST" }));

  expect(screen.queryByRole("tab", { name: "Deep Scan" })).toBeNull();

  rerender(<ScanPolicyPage showDeepScan={true} />);

  expect(screen.getByRole("tab", { name: "Deep Scan" })).toBeTruthy();
  const dastTabs = screen.getByRole("tablist", { name: "DAST agent settings" });
  expect(dastTabs.lastElementChild?.textContent).toBe("Deep Scan");
});

test("shows SAST settings in its own tab", () => {
  render(<ScanPolicyPage />);

  fireEvent.click(screen.getByRole("tab", { name: "SAST" }));

  expect(screen.getByText("SAST settings")).toBeTruthy();
  expect(window.location.hash).toBe("#/scan-policy/sast");
});

test("groups DAST settings under a nested tab bar", () => {
  render(<ScanPolicyPage showDeepScan />);

  fireEvent.click(screen.getByRole("tab", { name: "DAST" }));
  expect(screen.getByText("Global settings")).toBeTruthy();
  const dastTabs = screen.getByRole("tablist", { name: "DAST agent settings" });
  expect([...dastTabs.children].slice(0, 2).map((tab) => tab.textContent)).toEqual([
    "Scan Behaviour",
    "HTTP Headers",
  ]);

  fireEvent.click(screen.getByRole("tab", { name: "Crawler" }));
  expect(screen.getByText("Crawler settings")).toBeTruthy();
  expect(window.location.hash).toBe("#/scan-policy/dast/crawler");
  expect(screen.getByRole("tab", { name: "Specialist" })).toBeTruthy();

  fireEvent.click(screen.getByRole("tab", { name: "Validator" }));
  expect(screen.getByText("Validator settings")).toBeTruthy();
});

test("shows feature visibility and debug settings under Global", () => {
  render(<ScanPolicyPage />);

  expect(screen.getByText("features settings")).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: "Debug Settings" }));
  expect(screen.getByText("debug settings")).toBeTruthy();
  expect(window.location.hash).toBe("#/scan-policy/global/debug");
  fireEvent.click(screen.getByRole("tab", { name: "Upstream Proxy" }));
  expect(screen.getByText("Proxy settings form")).toBeTruthy();
  expect(window.location.hash).toBe("#/scan-policy/global/proxy");
  expect(screen.queryByText("debug settings")).toBeNull();
  expect(screen.queryByRole("tab", { name: "Scan Behaviour" })).toBeNull();
});

test("opens a nested tab from its URL", () => {
  render(<ScanPolicyPage initialTab="global" initialSubTab="proxy" />);
  expect(screen.getByRole("tab", { name: "Upstream Proxy" }).getAttribute("aria-selected")).toBe(
    "true",
  );
  expect(screen.getByText("Proxy settings form")).toBeTruthy();
});

test("opens the first Global tab by default", () => {
  render(<ScanPolicyPage />);
  expect(
    screen.getByRole("tab", { name: "Feature Visibility" }).getAttribute("aria-selected"),
  ).toBe("true");
});

test("only shows Systems and Component Mapper when Systems is enabled", () => {
  const { rerender } = render(<ScanPolicyPage showSystems={false} />);
  expect(screen.queryByRole("tab", { name: "Systems" })).toBeNull();

  rerender(<ScanPolicyPage showSystems />);
  fireEvent.click(screen.getByRole("tab", { name: "Systems" }));
  expect(screen.getByText("Component Mapper settings")).toBeTruthy();
});
