import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { CandidateTable, LeadEvidence } from "./CandidatesView.jsx";

const leads = [
  { id: 1, title: "Beta issue", severity: "low", confidence: 0.9, validation_status: "pending" },
  {
    id: 2,
    title: "Alpha issue",
    severity: "critical",
    confidence: 0.4,
    validation_status: "dismissed",
  },
  {
    id: 3,
    title: "Gamma issue",
    severity: "medium",
    confidence: 0.7,
    validation_status: "confirmed",
  },
];

function titles() {
  return within(screen.getByRole("table"))
    .getAllByRole("button", { pressed: false })
    .map((row) => within(row).getByText(/issue$/).textContent);
}

beforeEach(() => localStorage.clear());

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
  expect(titles()).toEqual(["Beta issue", "Alpha issue", "Gamma issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual(["Alpha issue", "Gamma issue", "Beta issue"]);
  expect(screen.getByRole("columnheader", { name: /Severity/ }).getAttribute("aria-sort")).toBe(
    "descending",
  );

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual(["Beta issue", "Gamma issue", "Alpha issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Severity/ }));
  expect(titles()).toEqual(["Beta issue", "Alpha issue", "Gamma issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Finding/ }));
  expect(titles()).toEqual(["Alpha issue", "Beta issue", "Gamma issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Confidence/ }));
  expect(titles()).toEqual(["Beta issue", "Gamma issue", "Alpha issue"]);

  fireEvent.click(screen.getByRole("button", { name: /^Status/ }));
  expect(titles()).toEqual(["Gamma issue", "Beta issue", "Alpha issue"]);
});

test("hides findings by status and remembers the choice", () => {
  const { unmount } = render(<CandidateTable leads={leads} selectedId={null} onSelect={vi.fn()} />);
  const filter = screen.getByRole("group", { name: "Show findings by status" });

  fireEvent.click(within(filter).getByRole("button", { name: "dismissed 1" }));
  expect(titles()).toEqual(["Beta issue", "Gamma issue"]);
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
