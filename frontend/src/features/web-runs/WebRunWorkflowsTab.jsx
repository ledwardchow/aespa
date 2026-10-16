import { useCallback, useEffect, useRef, useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { truncUrl } from "../../shared/lib/urls.js";
import { anyRetryBusy, isRetryBusy, mergeRetries, retriesByNote } from "./workflowRetries.js";

export function statusLabel(note) {
  if (note.status === "crawled") return "Crawled";
  if (note.needs_input || note.status === "needs_input") return "Needs input";
  if (note.status === "not_attempted") return (note.steps || []).length ? "Stopped" : "Not tried";
  return "Could not reach";
}

export function groupWorkflowNotes(notes) {
  const byId = new Map(
    notes.filter((note) => Number.isInteger(note.id)).map((note) => [note.id, note]),
  );
  const groups = new Map();
  notes.forEach((note, index) => {
    let root = note;
    const visited = new Set();
    while (Number.isInteger(root.retry_of) && byId.has(root.retry_of) && !visited.has(root.id)) {
      visited.add(root.id);
      root = byId.get(root.retry_of);
    }
    const key = Number.isInteger(root.id) ? root.id : `unlinked-${index}`;
    if (!groups.has(key)) groups.set(key, { root, attempts: [] });
    groups.get(key).attempts.push(note);
  });
  return [...groups.values()];
}

export function WebRunWorkflowsTab({
  runId,
  summary,
  focusedNoteId,
  focusSequence,
  onNotesChange,
  onRetryStatusChange,
  onRetryFinished,
  onOpenNotification,
}) {
  const [notes, setNotes] = useState(null);
  const [retries, setRetries] = useState({});
  const focusedElement = useRef(null);
  const requestVersion = useRef(0);
  const finishedNotes = useRef(null);

  const load = useCallback(async () => {
    const version = requestVersion.current;
    const [noteResult, retryResult] = await Promise.all([
      webRunsApi.getWorkflowNotes(runId),
      webRunsApi.getWorkflowRetryStatus(runId),
    ]);
    if (version !== requestVersion.current) return;
    setNotes(noteResult?.notes || []);
    onNotesChange?.(noteResult?.notes || []);
    setRetries((current) => mergeRetries(current, retriesByNote(retryResult)));
  }, [runId, onNotesChange]);

  useEffect(() => {
    onRetryStatusChange?.(retries);
  }, [retries, onRetryStatusChange]);

  const retryWorkflow = async (note) => {
    requestVersion.current += 1;
    const setProgress = (progress) =>
      setRetries((current) => ({ ...current, [note.id]: progress }));
    setProgress({
      status: "submitting",
      note_id: note.id,
      message: "Starting the workflow",
      actions_done: 0,
      actions: [],
    });
    try {
      const status = await webRunsApi.retryWorkflow(
        runId,
        note.id,
        note.instructions || "",
        Boolean(note.save_to_site_requested),
      );
      setProgress(status);
    } catch (cause) {
      setProgress({
        status: "error",
        note_id: note.id,
        error: cause.message || "Could not retry this workflow.",
      });
    }
  };

  usePolling(load, {
    enabled: Boolean(runId),
    immediate: Boolean(runId),
    intervalMs: anyRetryBusy(retries) ? 1000 : 15000,
  });

  useEffect(() => {
    if (focusSequence) void load();
  }, [focusSequence, load]);

  useEffect(() => {
    const complete = Object.values(retries)
      .filter((item) => item.status === "complete")
      .map((item) => item.note_id);
    const previous = finishedNotes.current;
    finishedNotes.current = new Set(complete);
    // Reload once for each retry that finishes while this tab is open.
    if (previous && complete.some((noteId) => !previous.has(noteId))) onRetryFinished?.();
  }, [retries, onRetryFinished]);

  const shownNotes = notes?.length ? notes : summary?.crawl_notes || [];
  const workflows = groupWorkflowNotes(shownNotes);

  useEffect(() => {
    if (focusedNoteId) focusedElement.current?.scrollIntoView({ block: "nearest" });
  }, [focusedNoteId, focusSequence, notes?.length]);

  if (!summary && !notes) return <p className="attack-surface-empty subtle">Loading workflows…</p>;
  return (
    <div className="surface-workflows-panel">
      <h3>Workflows</h3>
      <p className="subtle">Pages the crawler tried to reach after its main crawl.</p>
      {workflows.length ? (
        <div className="surface-crawl-notes">
          {workflows.map(({ root, attempts }, index) => {
            const latest = attempts.at(-1);
            const progressNoteId =
              [...attempts].reverse().find((attempt) => retries[attempt.id])?.id ?? null;
            const progress = progressNoteId === null ? null : retries[progressNoteId];
            const busy = attempts.some((attempt) => isRetryBusy(retries[attempt.id]));
            const focused = attempts.some((attempt) => attempt.id === focusedNoteId);
            return (
              <div
                className={`surface-crawl-note${focused ? " workflow-focused" : ""}`}
                key={root.id ?? `${root.name}-${index}`}
                ref={focused ? focusedElement : null}
              >
                <div className="surface-crawl-note-head">
                  <strong>{root.name}</strong>
                  <span
                    className={`surface-crawl-note-status status-${busy ? "running" : latest.status}`}
                  >
                    {busy ? "In progress" : statusLabel(latest)}
                  </span>
                </div>
                {root.reason ? <p>{root.reason}</p> : null}
                {progress ? (
                  <div className="workflow-retry-progress" role="status" aria-live="polite">
                    <div className="workflow-retry-heading">
                      {busy ? <span className="workflow-retry-spinner" aria-hidden="true" /> : null}
                      <strong>
                        {busy
                          ? progress.generate_sample_data
                            ? "Generating test data and continuing"
                            : "Continuing workflow"
                          : progress.status === "error"
                            ? "Could not start"
                            : statusLabel(latest)}
                      </strong>
                    </div>
                    <p>{progress.error || progress.message}</p>
                    {progress.current_path ? (
                      <p className="subtle mono">Page: {progress.current_path}</p>
                    ) : null}
                    {busy ? (
                      <p className="subtle">
                        {progress.actions_done || 0}{" "}
                        {progress.actions_done === 1 ? "action" : "actions"} completed
                      </p>
                    ) : null}
                    {(progress.actions || []).length ? (
                      <ol className="workflow-retry-actions">
                        {progress.actions.map((action, actionIndex) => (
                          <li key={`${actionIndex}-${action}`}>{action}</li>
                        ))}
                      </ol>
                    ) : null}
                    {progress.saved_to_site ? <p className="subtle">Saved to site</p> : null}
                    {progress.save_to_site_requested && !progress.saved_to_site ? (
                      <p className="subtle">
                        {busy ? "Will save to site if reached" : "Not saved to site"}
                      </p>
                    ) : null}
                  </div>
                ) : null}
                {attempts.length > 1 ? (
                  <div className="workflow-attempts">
                    <strong>Attempts</strong>
                    <ol>
                      {attempts.map((attempt, attemptIndex) => (
                        <li key={attempt.id ?? attemptIndex}>
                          <strong>
                            {attemptIndex === 0 ? "Initial crawl" : `Retry ${attemptIndex}`}:{" "}
                            {statusLabel(attempt)}
                          </strong>
                          {attempt.detail ? <span> - {attempt.detail}</span> : null}
                          {(attempt.steps || []).length ? (
                            <span> Actions: {attempt.steps.join(" → ")}</span>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : (
                  <>
                    {(latest.steps || []).length ? (
                      <p>Actions: {latest.steps.join(" → ")}</p>
                    ) : null}
                    {!busy && latest.detail ? <p>{latest.detail}</p> : null}
                  </>
                )}
                {latest.needs_input && !busy && (
                  <>
                    {latest.request ? <p className="subtle">{latest.request}</p> : null}
                    {Number.isInteger(latest.id) && onOpenNotification ? (
                      <button
                        type="button"
                        className="btn sm secondary"
                        onClick={() => onOpenNotification(latest.id)}
                      >
                        Provide input
                      </button>
                    ) : (
                      <p className="subtle">
                        Add or correct sample data from Needs input at the top of the run.
                      </p>
                    )}
                  </>
                )}
                {latest.retryable ? (
                  <button
                    type="button"
                    className="btn sm secondary"
                    disabled={busy}
                    onClick={() => retryWorkflow(latest)}
                  >
                    Retry workflow
                  </button>
                ) : null}
                {latest.status === "crawled" && latest.url ? (
                  <span className="mono subtle">{truncUrl(latest.url, 100)}</span>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="subtle">
          {summary?.crawl_notes_failed
            ? "Could not check for additional workflows after the crawl."
            : summary?.crawl_notes_checked
              ? "No additional workflows were identified after the crawl."
              : "No workflow check has been recorded for this run."}
        </p>
      )}
    </div>
  );
}
