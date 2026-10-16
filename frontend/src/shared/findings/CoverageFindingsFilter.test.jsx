import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { CoverageFindingsFilter, filterCoverageFindings } from "./CoverageFindingsFilter.jsx";

test("filters by finding ID and keeps normal findings links available", () => {
  const findings = [{ id: 11 }, { id: 12 }, { id: 13 }];
  expect(filterCoverageFindings(findings, [11, 13])).toEqual([findings[0], findings[2]]);
  expect(filterCoverageFindings(findings, undefined)).toEqual(findings);
  render(
    <CoverageFindingsFilter
      runKind="web"
      runId={7}
      findingIds={[11, 13]}
      coverageReturn="workflows"
      visibleCount={2}
    />,
  );
  expect(screen.getByRole("link", { name: "Back to coverage" }).getAttribute("href")).toBe(
    "#/runs/7/attack?subtab=owasp&coverage=workflows",
  );
  expect(screen.getByRole("link", { name: "Show all findings" }).getAttribute("href")).toBe(
    "#/runs/7/findings",
  );
});

test("API coverage return goes to the work program", () => {
  render(
    <CoverageFindingsFilter
      runKind="api"
      runId={9}
      findingIds={[42]}
      coverageReturn="owasp"
      visibleCount={1}
    />,
  );
  expect(screen.getByRole("link", { name: "Back to coverage" }).getAttribute("href")).toBe(
    "#/api-runs/9/workprogram",
  );
});
