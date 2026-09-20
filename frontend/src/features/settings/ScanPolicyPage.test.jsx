import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ScanPolicyPage } from "./ScanPolicyPage.jsx";

vi.mock("./ScannerPolicySettings.jsx", () => ({
  GlobalPolicySettings: () => <div>Global settings</div>,
  GlobalPolicySubTabs: () => null,
  ScannerPolicySettings: () => <div>Test Lead settings</div>,
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
});

test("groups DAST settings under a nested tab bar", () => {
  render(<ScanPolicyPage showDeepScan />);

  fireEvent.click(screen.getByRole("tab", { name: "DAST" }));
  expect(screen.getByText("Crawler settings")).toBeTruthy();
  expect(screen.getByRole("tab", { name: "Specialist" })).toBeTruthy();

  fireEvent.click(screen.getByRole("tab", { name: "Validator" }));
  expect(screen.getByText("Validator settings")).toBeTruthy();
});

test("only shows Systems and Component Mapper when Systems is enabled", () => {
  const { rerender } = render(<ScanPolicyPage showSystems={false} />);
  expect(screen.queryByRole("tab", { name: "Systems" })).toBeNull();

  rerender(<ScanPolicyPage showSystems />);
  fireEvent.click(screen.getByRole("tab", { name: "Systems" }));
  expect(screen.getByText("Component Mapper settings")).toBeTruthy();
});
