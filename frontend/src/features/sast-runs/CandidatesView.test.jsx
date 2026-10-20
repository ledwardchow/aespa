import { useState } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { CandidateTable, CandidatesView, LeadEvidence } from "./CandidatesView.jsx";

const leads = [
  {
    id: 1,
    reference: "ABCD-003",
    title: "Beta issue",
    severity: "low",
    confidence: 0.9,
    validation_status: "pending",
  },
  {
    id: 2,
    reference: "ABCD-001",
    title: "Alpha issue",
    severity: "critical",
    confidence: 0.4,
    validation_status: "dismissed",
  },
  {
    id: 3,
    reference: "ABCD-002",
    title: "Gamma issue",
    severity: "medium",
    confidence: 0.7,
    validation_status: "confirmed",
  },
];

function titles() {
  return [...screen.getByRole("table").querySelectorAll("tbody tr")].map(
    (row) => row.querySelector(".sast-candidate-title").textContent,
  );
}

beforeEach(() => localStorage.clear());

test("opens full-width details and returns to the filtered, sorted findings list", () => {
  function Findings() {
    const [selectedId, setSelectedId] = useState(1);
    return (
      <CandidatesView
        runId={249}
        leads={leads}
        selectedLead={leads.find((lead) => lead.id === selectedId)}
        onSelect={setSelectedId}
        targets={[]}
        onQueue={vi.fn()}
        queueBusy={false}
        reportableCount={1}
        onExport={vi.fn()}
        canRevalidate={false}
      />
    );
  }

  render(<Findings />);
  fireEvent.click(screen.getByRole("button", { name: "dismissed 1" }));
  expect(titles()).toEqual(["Gamma issue", "Beta issue"]);

  fireEvent.click(screen.getByRole("button", { name: /Gamma issue/ }));
  expect(screen.queryByRole("table")).toBeNull();
  expect(screen.getByRole("heading", { name: "Gamma issue" })).toBeTruthy();
  expect(screen.getByText("1 of 2")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Next →" }));
  expect(screen.getByRole("heading", { name: "Beta issue" })).toBeTruthy();
  expect(screen.getByText("2 of 2")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "← Back to findings" }));
  expect(titles()).toEqual(["Gamma issue", "Beta issue"]);
});

test("offers Markdown and SARIF from the findings export control", () => {
  const onExport = vi.fn();
  render(
    <CandidatesView
      runId={249}
      leads={leads}
      selectedLead={leads[0]}
      onSelect={vi.fn()}
      targets={[]}
      onQueue={vi.fn()}
      queueBusy={false}
      reportableCount={1}
      onExport={onExport}
      canRevalidate={false}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Export findings ↓" }));
  expect(onExport).not.toHaveBeenCalled();
  expect(screen.getByRole("menuitem", { name: "Export SARIF" }).getAttribute("href")).toBe(
    "/api/sast-runs/249/sarif",
  );
  fireEvent.click(screen.getByRole("menuitem", { name: "Export Markdown" }));
  expect(onExport).toHaveBeenCalledOnce();
  expect(screen.queryByRole("menuitem", { name: "Export SARIF" })).toBeNull();
});

test("re-validates the selected inconclusive finding", () => {
  const onRevalidate = vi.fn();
  const lead = { id: 7, title: "Open question", validation_status: "inconclusive" };
  render(
    <LeadEvidence
      lead={lead}
      targets={[]}
      onQueue={vi.fn()}
      queueBusy={false}
      onRevalidate={onRevalidate}
      revalidatingLeadId={null}
      canRevalidate
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Re-validate" }));
  expect(onRevalidate).toHaveBeenCalledWith(lead);
});

test("creates a live test run from a selected site or API collection", () => {
  const onQueue = vi.fn();
  const lead = {
    id: 8,
    title: "Confirmed issue",
    validation_status: "confirmed",
    reportable: true,
  };
  const targets = [
    { target_type: "site", target_id: 2, name: "Store", url: "https://store.test" },
    { target_type: "api_collection", target_id: 3, name: "Orders API", url: "https://api.test" },
  ];
  render(<LeadEvidence lead={lead} targets={targets} onQueue={onQueue} queueBusy={false} />);

  const selector = screen.getByRole("combobox", { name: "Application for live testing" });
  expect(within(selector).getByRole("group", { name: "Sites" })).toBeTruthy();
  expect(within(selector).getByRole("group", { name: "API collections" })).toBeTruthy();
  fireEvent.change(selector, { target: { value: "api_collection:3" } });
  fireEvent.click(screen.getByRole("button", { name: "Create test run" }));
  expect(onQueue).toHaveBeenCalledWith(lead, targets[1]);
});

test("shows a re-validation action beside each inconclusive finding", () => {
  const onRevalidate = vi.fn();
  const onSelect = vi.fn();
  const inconclusive = { id: 8, title: "Unclear issue", validation_status: "inconclusive" };
  render(
    <CandidateTable
      leads={[inconclusive, leads[2]]}
      selectedId={null}
      onSelect={onSelect}
      onRevalidate={onRevalidate}
      canRevalidate
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Re-validate" }));
  expect(onRevalidate).toHaveBeenCalledWith(inconclusive);
  expect(onSelect).not.toHaveBeenCalled();
});

test("sorts findings when a column header is clicked", () => {
  render(<CandidateTable leads={leads} selectedId={null} onSelect={vi.fn()} />);
  expect(titles()).toEqual(["Alpha issue", "Gamma issue", "Beta issue"]);
  expect(screen.getByRole("table").querySelector("thead th").textContent).toContain("Reference");
  expect(screen.getByRole("columnheader", { name: /Reference/ }).getAttribute("aria-sort")).toBe(
    "ascending",
  );

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(screen.getByRole("columnheader", { name: /Severity/ }).getAttribute("aria-sort")).toBe(
    "descending",
  );

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual(["Beta issue", "Gamma issue", "Alpha issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual(["Beta issue", "Alpha issue", "Gamma issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual(["Alpha issue", "Gamma issue", "Beta issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Finding/ }));
  expect(titles()).toEqual(["Alpha issue", "Beta issue", "Gamma issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Confidence/ }));
  expect(titles()).toEqual(["Beta issue", "Gamma issue", "Alpha issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Status/ }));
  expect(titles()).toEqual(["Gamma issue", "Beta issue", "Alpha issue"]);
});

test("sorts every severity consistently when labels vary or findings refresh", () => {
  const mixed = [
    { id: 1, title: "Low issue", severity: "low" },
    { id: 2, title: "Zeta high issue", severity: "HIGH " },
    { id: 3, title: "Info issue", severity: "informational" },
    { id: 4, title: "Alpha high issue", severity: "high" },
    { id: 5, title: "Critical issue", severity: "critical" },
    { id: 6, title: "Medium issue", severity: "medium" },
  ];
  const { rerender } = render(
    <CandidateTable leads={mixed} selectedId={null} onSelect={vi.fn()} />,
  );
  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual([
    "Critical issue",
    "Alpha high issue",
    "Zeta high issue",
    "Medium issue",
    "Low issue",
    "Info issue",
  ]);

  rerender(<CandidateTable leads={[...mixed].reverse()} selectedId={null} onSelect={vi.fn()} />);
  expect(titles()).toEqual([
    "Critical issue",
    "Alpha high issue",
    "Zeta high issue",
    "Medium issue",
    "Low issue",
    "Info issue",
  ]);
  expect(screen.getByText("INFO")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual([
    "Info issue",
    "Low issue",
    "Medium issue",
    "Alpha high issue",
    "Zeta high issue",
    "Critical issue",
  ]);
});

test("sorts stored references by their number, then reverses that order", () => {
  const referenced = [
    { id: 10, reference: "WXYZ-010", title: "Tenth issue", severity: "critical" },
    { id: 2, reference: "WXYZ-002", title: "Second issue", severity: "low" },
    { id: 1, reference: "WXYZ-001", title: "First issue", severity: "high" },
  ];
  render(<CandidateTable leads={referenced} selectedId={null} onSelect={vi.fn()} />);
  expect(titles()).toEqual(["First issue", "Second issue", "Tenth issue"]);
  expect(
    [...screen.getByRole("table").querySelectorAll("tbody .sast-candidate-reference")].map(
      (cell) => cell.textContent,
    ),
  ).toEqual(["WXYZ-001", "WXYZ-002", "WXYZ-010"]);

  fireEvent.click(screen.getByRole("button", { name: /^Reference/ }));
  expect(titles()).toEqual(["Tenth issue", "Second issue", "First issue"]);
  expect(screen.getByRole("columnheader", { name: /Reference/ }).getAttribute("aria-sort")).toBe(
    "descending",
  );
});

test("keeps saved column widths when the reference column is added", () => {
  localStorage.setItem("sast-candidate-columns:v1", JSON.stringify([95, 290, 105, 200]));
  render(<CandidateTable leads={leads} selectedId={null} onSelect={vi.fn()} />);
  const widths = [...screen.getByRole("table").querySelectorAll("col")].map(
    (column) => column.style.width,
  );
  expect(widths).toEqual(["112px", "95px", "290px", "105px", "200px"]);
});

test("hides findings by status and remembers the choice", () => {
  const { unmount } = render(<CandidateTable leads={leads} selectedId={null} onSelect={vi.fn()} />);
  const filter = screen.getByRole("group", { name: "Show findings by status" });

  fireEvent.click(within(filter).getByRole("button", { name: "dismissed 1" }));
  expect(titles()).toEqual(["Gamma issue", "Beta issue"]);
  expect(screen.getByText("1 hidden")).toBeTruthy();

  fireEvent.click(within(filter).getByRole("button", { name: "pending 1" }));
  fireEvent.click(within(filter).getByRole("button", { name: "confirmed 1" }));
  expect(screen.getByText("All findings are hidden by the status filter.")).toBeTruthy();

  unmount();
  render(<CandidateTable leads={leads} selectedId={null} onSelect={vi.fn()} />);
  expect(screen.getByText("All findings are hidden by the status filter.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "confirmed 1" }));
  expect(screen.getByText("Gamma issue")).toBeTruthy();
});
