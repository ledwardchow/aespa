import { useRef, useState } from "react";
import { updateFinding } from "../api/findings.ts";
import type { Finding, FindingUpdate } from "./contracts.ts";

export type FindingDraft = Partial<Record<keyof FindingUpdate, string>>;
export const commonFields = [
  "title",
  "affected_url",
  "description",
  "impact",
  "recommendation",
] as const;
export function makeFindingDraft(finding: Finding, runKind: "web" | "api"): FindingDraft {
  const fields =
    runKind === "web"
      ? ([...commonFields, "likelihood", "cvss_vector"] as const)
      : ([...commonFields, "owasp_api_category", "evidence"] as const);
  const draft: FindingDraft = {
    severity: finding.severity,
    validation_status: finding.validation_status,
  };
  for (const field of fields) draft[field] = finding[field] || "";
  if (runKind === "web") draft.cvss_score = String(finding.cvss_score ?? 0);
  return draft;
}

// The panel owns this hook so collapsing a row does not discard its draft.
export function useFindingEditor({
  runId,
  runKind,
  onSaved,
  onError,
}: {
  runId: number;
  runKind: "web" | "api";
  onSaved: (findingId: number, updated: Finding | null) => void;
  onError: (message: string) => void;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<FindingDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  function edit(finding: Finding) {
    setEditingId(finding.id);
    setDraft(makeFindingDraft(finding, runKind));
  }
  function cancel() {
    setEditingId(null);
    setDraft(null);
  }
  async function save() {
    if (!draft || editingId === null || pending.current) return;
    pending.current = true;
    setBusy(true);
    try {
      const { cvss_score, ...text } = draft;
      const body: FindingUpdate = { ...text };
      if (runKind === "web") body.cvss_score = Number(cvss_score) || 0;
      const updated = await updateFinding({ runKind, runId }, editingId, body);
      onSaved(editingId, updated);
      cancel();
    } catch (error) {
      onError(error instanceof Error ? error.message : String(error));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return { editingId, draft, setDraft, busy, edit, cancel, save };
}
export type FindingEditorState = ReturnType<typeof useFindingEditor>;
