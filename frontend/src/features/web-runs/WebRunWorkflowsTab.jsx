import { useCallback, useEffect, useRef, useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { truncUrl } from "../../shared/lib/urls.js";

function statusLabel(note) {
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
  const [retry, setRetry] = useState({ status: "idle" });
  const focusedElement = useRef(null);
  const requestVersion = useRef(0);

  const load = useCallback(async () => {
    const version = requestVersion.current;
    const [noteResult, retryResult] = await Promise.all([
      webRunsApi.getWorkflowNotes(runId),
      webRunsApi.getWorkflowRetryStatus(runId),
    ]);
    if (version !== requestVersion.current) return;
    setNotes(noteResult?.notes || []);
    onNotesChange?.(noteResult?.notes || []);
    setRetry((current) => {
      if (retryResult?.status === "idle" && ["submitting", "running"].includes(current.status)) {
        return current;
      }
      return retryResult || { status: "idle" };
    });
    onRetryStatusChange?.(retryResult || { status: "idle" });
  }, [runId, onNotesChange, onRetryStatusChange]);

  const retryWorkflow = async (note) => {
    requestVersion.current += 1;
    const pending = {
      status: "submitting",
      note_id: note.id,
      message: "Starting the workflow",
      actions_done: 0,
      actions: [],
    };
    setRetry(pending);
    onRetryStatusChange?.(pending);
    try {
      const status = await webRunsApi.retryWorkflow(
        runId,
        note.id,
        note.instructions || "",
        Boolean(note.save_to_site_requested),
      );
      setRetry(status);
      onRetryStatusChange?.(status);
    } catch (cause) {
      const failed = {
        status: "error",
        note_id: note.id,
        error: cause.message || "Could not retry this workflow.",
      };
      setRetry(failed);
      onRetryStatusChange?.(failed);
    }
  };

  usePolling(load, {
    enabled: Boolean(runId),
    immediate: Boolean(runId),
    intervalMs: ["submitting", "running"].includes(retry.status) ? 1000 : 15000,
  });

  useEffect(() => {
    if (focusSequence) void load();
  }, [focusSequence, load]);

  useEffect(() => {
    if (retry.status === "complete") onRetryFinished?.();
  }, [retry.status, onRetryFinished]);

  const shownNotes = notes?.length ? notes : summary?.crawl_notes || [];
  const workflows = groupWorkflowNotes(shownNotes);
  const anyRetryBusy = ["submitting", "running"].includes(retry.status);

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
            const activeRetry = attempts.some((attempt) => attempt.id === retry.note_id)
              ? retry
              : null;
            const busy = ["submitting", "running"].includes(activeRetry?.status);
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
                {activeRetry && activeRetry.status !== "idle" ? (
                  <div className="workflow-retry-progress" role="status" aria-live="polite">
                    <div className="workflow-retry-heading">
                      {busy ? <span className="workflow-retry-spinner" aria-hidden="true" /> : null}
                      <strong>
                        {busy
                          ? activeRetry.generate_sample_data
                            ? "Generating test data and continuing"
                            : "Continuing workflow"
                          : activeRetry.status === "error"
                            ? "Could not start"
                            : statusLabel(latest)}
                      </strong>
                    </div>
                    <p>{activeRetry.error || activeRetry.message}</p>
                    {activeRetry.current_path ? (
                      <p className="subtle mono">Page: {activeRetry.current_path}</p>
                    ) : null}
                    {busy ? (
                      <p className="subtle">
                        {activeRetry.actions_done || 0}{" "}
                        {activeRetry.actions_done === 1 ? "action" : "actions"} completed
                      </p>
                    ) : null}
                    {(activeRetry.actions || []).length ? (
                      <ol className="workflow-retry-actions">
                        {activeRetry.actions.map((action, actionIndex) => (
                          <li key={`${actionIndex}-${action}`}>{action}</li>
                        ))}
                      </ol>
                    ) : null}
                    {activeRetry.saved_to_site ? <p className="subtle">Saved to site</p> : null}
                    {activeRetry.save_to_site_requested && !activeRetry.saved_to_site ? (
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
                    disabled={anyRetryBusy}
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
