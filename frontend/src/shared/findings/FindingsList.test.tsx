import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import type { Finding } from "./contracts.ts";
import { findingGroupKeys, groupFindings } from "./findingGroups.ts";
import { FindingsList } from "./FindingsList.tsx";
import type { FindingsListProps } from "./FindingsList.tsx";
import type { FindingEditorState } from "./useFindingEditor.ts";

const base: Finding = {
  id: 1,
  reference: "F-1",
  test_run_id: 1,
  api_test_run_id: null,
  page_id: null,
  owasp_category: "A03",
  owasp_api_category: null,
  severity: "high",
  validation_status: "confirmed",
  title: "Stored XSS",
  description: "Fixture description",
  impact: "",
  likelihood: "",
  recommendation: "",
  cvss_score: 7.1,
  cvss_vector: "",
  affected_url: "http://example.test/a",
  evidence: "",
  request_evidence: "",
  response_evidence: "",
  evidence_json: "[]",
  evidence_items: [],
  screenshot_b64: null,
  finding_source: "dynamic_scan",
  validation_note: null,
  origin: null,
  validated_by: null,
  merged_instances: "[]",
  poc_command: "",
  poc_setup: "",
  created_at: "2026-10-15T00:00:00Z",
};
const make = (overrides: Partial<Finding>): Finding => ({ ...base, ...overrides });

const findings = [
  make({ id: 1, reference: "F-1", severity: "low", title: "CORS reflection" }),
  make({ id: 2, reference: "F-2", title: "Stored XSS" }),
  make({ id: 3, reference: "F-3", title: "Stored XSS", affected_url: "http://example.test/b" }),
  make({ id: 4, reference: "F-4", title: "Weak header", validation_status: "unconfirmed" }),
  make({ id: 5, reference: "F-5", title: "Noise", validation_status: "low_confidence" }),
  make({ id: 6, reference: "F-6", title: "Probe echo", finding_source: "deterministic_probe" }),
];

function editorStub(): FindingEditorState {
  return {
    editingId: null,
    draft: null,
    setDraft: vi.fn(),
    busy: false,
    edit: vi.fn(),
    cancel: vi.fn(),
    save: vi.fn(),
  } as unknown as FindingEditorState;
}

function renderList(props: Partial<FindingsListProps> = {}) {
  const editor = props.editor || editorStub();
  const result = render(
    <FindingsList
      findings={findings}
      runKind="web"
      findingHref={(reference) => `#/runs/1/findings?finding=${reference}`}
      editor={editor}
      emptyMessage="Nothing yet"
      onDeleteFinding={vi.fn()}
      {...props}
    />,
  );
  return { ...result, editor };
}

const groupTitles = () =>
  [...document.querySelectorAll(".finding-group-row .finding-title")].map((cell) =>
    cell.textContent?.replace(/^[▸▾]/, ""),
  );

test("groups main findings by title, highest severity first, then labelled sections", () => {
  const { main, sections } = groupFindings(findings);
  expect(main.map((group) => [group.title, group.items.length])).toEqual([
    ["Stored XSS", 2],
    ["CORS reflection", 1],
  ]);
  expect(sections.map((section) => [section.label, section.count])).toEqual([
    ["Unconfirmed", 1],
    ["Low confidence", 1],
    ["Deterministic checks", 1],
  ]);
  expect(findingGroupKeys(findings[3])).toEqual(["__unconfirmed__", "__unconfirmed__:Weak header"]);
});

test("shows the empty message when there are no findings", () => {
  renderList({ findings: [] });
  expect(screen.getByText("Nothing yet")).toBeTruthy();
});

test("renders the same columns and sections for web and API runs", () => {
  for (const runKind of ["web", "api"] as const) {
    const { unmount } = renderList({ runKind });
    expect(
      [...document.querySelectorAll(".findings-table th")].map((th) => th.textContent?.trim()),
    ).toEqual(["Severity", "Source", "Title", "OWASP", "Count", ""]);
    // Unconfirmed starts open; the other sections start closed.
    expect(groupTitles()).toEqual(["Stored XSS", "CORS reflection", "Weak header"]);
    expect(screen.getByText("Low confidence")).toBeTruthy();
    expect(screen.getByText("Deterministic checks")).toBeTruthy();
    unmount();
  }
});

test("opens the groups and details of a deep-linked finding", () => {
  renderList({ initialFindingRef: "F-5." });
  expect(groupTitles()).toContain("Noise");
  expect(screen.getByText("Fixture description")).toBeTruthy();
});

test("edit opens the row and hands the finding to the tab's editor", () => {
  const { editor } = renderList();
  fireEvent.click(screen.getByText("CORS reflection"));
  fireEvent.click(screen.getByTitle("Edit finding"));
  expect(editor.edit).toHaveBeenCalledWith(findings[0]);
});

test("validate and group delete appear only when the run type supports them", () => {
  const { unmount } = renderList({ runKind: "api" });
  fireEvent.click(screen.getByText("Weak header"));
  expect(screen.queryByTitle("Validate finding")).toBeNull();
  expect(screen.queryByTitle("Delete group")).toBeNull();
  unmount();

  const onValidateFinding = vi.fn();
  renderList({ onValidateFinding, onDeleteGroup: vi.fn(async () => true) });
  fireEvent.click(screen.getByText("Weak header"));
  fireEvent.click(screen.getByTitle("Validate finding"));
  expect(onValidateFinding).toHaveBeenCalledWith(expect.anything(), 4);
  expect(screen.getAllByTitle("Delete group")).toHaveLength(2);
});

test("collapse token closes open rows and groups", () => {
  const { rerender, editor } = renderList({ initialFindingRef: "F-1", collapseToken: 0 });
  expect(screen.getByText("Fixture description")).toBeTruthy();
  rerender(
    <FindingsList
      findings={findings}
      runKind="web"
      findingHref={(reference) => reference}
      editor={editor}
      emptyMessage="Nothing yet"
      onDeleteFinding={vi.fn()}
      initialFindingRef="F-1"
      collapseToken={1}
    />,
  );
  expect(screen.queryByText("Fixture description")).toBeNull();
  expect(groupTitles()).toEqual(["Stored XSS", "CORS reflection"]);
});
