import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ScanPolicyPage } from "./ScanPolicyPage.jsx";

vi.mock("./ScannerPolicySettings.jsx", () => ({
  GlobalPolicySettings: () => <div>Global settings</div>,
  GlobalPolicySubTabs: () => null,
  ScannerPolicySettings: () => null,
}));
vi.mock("./ValidatorSettings.jsx", () => ({ ValidatorSettings: () => null }));
vi.mock("./SpecialistAgentSettings.jsx", () => ({ SpecialistAgentSettings: () => null }));
vi.mock("./ReportingSettings.jsx", () => ({ ReportingSettings: () => null }));
vi.mock("./CrawlerSettings.jsx", () => ({ CrawlerSettings: () => null }));
vi.mock("./ComponentMapperSettings.jsx", () => ({ ComponentMapperSettings: () => null }));
vi.mock("./CodeExecutionSettings.jsx", () => ({ CodeExecutionSettings: () => null }));
vi.mock("./DeepScanSettings.jsx", () => ({ DeepScanSettings: () => null }));

test("only shows Deep Scan settings when its feature preference is enabled", () => {
  const { rerender } = render(<ScanPolicyPage showDeepScan={false} />);

  expect(screen.queryByRole("tab", { name: "Deep Scan" })).toBeNull();

  rerender(<ScanPolicyPage showDeepScan={true} />);

  expect(screen.getByRole("tab", { name: "Deep Scan" })).toBeTruthy();
});
