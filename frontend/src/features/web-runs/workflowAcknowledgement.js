import { isRetryBusy } from "./workflowRetries.js";

const storageKey = (runId) => `aespa_workflow_input_acknowledged:${runId}`;

export function readAcknowledgedWorkflowIds(runId) {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(runId)) || "[]");
    return new Set(Array.isArray(saved) ? saved.filter(Number.isInteger) : []);
  } catch {
    return new Set();
  }
}

export function acknowledgeWorkflowIds(runId, current, ids) {
  const next = new Set([...current, ...ids.filter(Number.isInteger)]);
  try {
    localStorage.setItem(storageKey(runId), JSON.stringify([...next]));
  } catch {
    // The current page still hides the acknowledged attempts when storage is unavailable.
  }
  return next;
}

export function visibleWorkflowInputNotes(notes, retries, acknowledgedIds) {
  return notes.filter(
    (note) =>
      note.needs_input &&
      note.status !== "crawled" &&
      !note.superseded &&
      !note.acknowledged &&
      !isRetryBusy(retries[note.id]) &&
      !acknowledgedIds.has(note.id),
  );
}
