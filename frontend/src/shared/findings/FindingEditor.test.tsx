import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { FindingEditor } from "./FindingEditor.tsx";
import { useFindingEditor } from "./useFindingEditor.ts";
import { updateFinding } from "../api/findings.ts";
import type { Finding } from "./contracts.ts";

vi.mock("../api/findings.ts", () => ({ updateFinding: vi.fn() }));
const finding: Finding = {
  id: 7,
  reference: "WEB-7",
  test_run_id: 1,
  api_test_run_id: null,
  page_id: null,
  owasp_category: "A01",
  owasp_api_category: "API1",
  severity: "low",
  validation_status: "unvalidated",
  title: "Saved title",
  description: "Description",
  impact: "Impact",
  likelihood: "Likelihood",
  recommendation: "Recommendation",
  cvss_score: 2.5,
  cvss_vector: "CVSS:3.1",
  affected_url: "http://example.test/item",
  evidence: "Evidence",
  request_evidence: "",
  response_evidence: "",
  evidence_json: "[]",
  evidence_items: [],
  screenshot_b64: null,
  finding_source: "manual_import",
  validation_note: null,
  origin: null,
  validated_by: null,
  merged_instances: "[]",
  poc_command: "",
  poc_setup: "",
  created_at: "2026-09-05T00:00:00Z",
};
const onError = vi.fn();
const onSaved = vi.fn();
function Editor({ runKind }: { runKind: "web" | "api" }) {
  const editor = useFindingEditor({ runId: 1, runKind, onError, onSaved });
  return (
    <>
      <button onClick={() => editor.edit(finding)}>Edit</button>
      <FindingEditor editor={editor} runKind={runKind} />
    </>
  );
}
beforeEach(() => vi.clearAllMocks());

test.each(["web", "api"] as const)(
  "%s editor keeps failed drafts, retries, and sends only its editable fields",
  async (runKind) => {
    vi.mocked(updateFinding)
      .mockRejectedValueOnce(new Error("Save failed"))
      .mockResolvedValueOnce({ ...finding, title: "Changed" });
    render(<Editor runKind={runKind} />);
    fireEvent.click(screen.getByText("Edit"));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Changed" } });
    fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "high" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "confirmed" } });
    for (const label of [
      "Affected URL",
      "Description",
      "Impact",
      "Recommendation",
      ...(runKind === "web" ? ["Likelihood", "CVSS Vector"] : ["OWASP API", "Evidence"]),
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: `Changed ${label}` } });
    }
    if (runKind === "web")
      fireEvent.change(screen.getByLabelText("CVSS", { exact: true }), {
        target: { value: "7.3" },
      });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Save failed"));
    expect((screen.getByLabelText("Title") as HTMLInputElement).value).toBe("Changed");
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() =>
      expect(onSaved).toHaveBeenCalledWith(7, expect.objectContaining({ title: "Changed" })),
    );
    expect(screen.queryByLabelText("Title")).toBeNull();
    const [identity, id, body] = vi.mocked(updateFinding).mock.calls[1];
    expect(identity).toEqual({ runKind, runId: 1 });
    expect(id).toBe(7);
    expect(body).toMatchObject({
      title: "Changed",
      severity: "high",
      validation_status: "confirmed",
      description: "Changed Description",
      impact: "Changed Impact",
      recommendation: "Changed Recommendation",
      affected_url: "Changed Affected URL",
    });
    if (runKind === "web") {
      expect(body).toMatchObject({
        cvss_score: 7.3,
        cvss_vector: "Changed CVSS Vector",
        likelihood: "Changed Likelihood",
      });
      expect(body).not.toHaveProperty("owasp_api_category");
      expect(body).not.toHaveProperty("evidence");
    } else {
      expect(body).toMatchObject({
        owasp_api_category: "Changed OWASP API",
        evidence: "Changed Evidence",
      });
      expect(body).not.toHaveProperty("cvss_score");
      expect(body).not.toHaveProperty("likelihood");
    }
  },
);

test("cancel drops the draft and reopening uses saved values", () => {
  render(<Editor runKind="web" />);
  fireEvent.click(screen.getByText("Edit"));
  fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Discard me" } });
  fireEvent.click(screen.getByText("Cancel"));
  expect(updateFinding).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Edit"));
  expect((screen.getByLabelText("Title") as HTMLInputElement).value).toBe("Saved title");
});

test("pending saves disable the controls and cannot be submitted twice", async () => {
  let finish!: (value: Finding) => void;
  vi.mocked(updateFinding).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<Editor runKind="api" />);
  fireEvent.click(screen.getByText("Edit"));
  fireEvent.click(screen.getByText("Save"));
  expect((screen.getByText("Saving…") as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByText("Cancel") as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByText("Saving…"));
  expect(updateFinding).toHaveBeenCalledTimes(1);
  finish(finding);
  await waitFor(() => expect(screen.queryByLabelText("Title")).toBeNull());
});
