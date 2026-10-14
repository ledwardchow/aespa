import { useCallback, useEffect, useRef, useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { usePolling } from "../../shared/hooks/usePolling.js";

export function WebRunNotificationsTab({
  runId,
  onNotesChange,
  onRetryStatusChange,
  onViewWorkflow,
  focusedNoteId,
  focusSequence,
}) {
  const [notes, setNotes] = useState([]);
  const [retryStatus, setRetryStatus] = useState({ status: "idle" });
  const [drafts, setDrafts] = useState({});
  const [saveToSite, setSaveToSite] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const requestVersion = useRef(0);
  const focusedInput = useRef(null);
  const lastFocusedSequence = useRef(0);

  const load = useCallback(async () => {
    const version = requestVersion.current;
    const [result, status] = await Promise.all([
      webRunsApi.getWorkflowNotes(runId),
      webRunsApi.getWorkflowRetryStatus(runId),
    ]);
    if (version !== requestVersion.current) return;
    setNotes(result?.notes || []);
    onNotesChange?.(result?.notes || []);
    setRetryStatus((current) => {
      if (status?.status === "idle" && current.status === "submitting") return current;
      if (status?.status === "idle" && current.status === "running") {
        return {
          ...current,
          status: "error",
          error: "Workflow progress was lost. Check Workflows for a saved result.",
        };
      }
      return status || { status: "idle" };
    });
    onRetryStatusChange?.(status || { status: "idle" });
    setLoading(false);
  }, [runId, onNotesChange, onRetryStatusChange]);

  usePolling(load, {
    intervalMs: ["submitting", "running"].includes(retryStatus.status) ? 1000 : 15000,
  });

  useEffect(() => {
    if (!focusedNoteId || !focusSequence || !focusedInput.current) return;
    if (lastFocusedSequence.current === focusSequence) return;
    lastFocusedSequence.current = focusSequence;
    focusedInput.current?.scrollIntoView?.({ block: "nearest" });
    focusedInput.current?.focus();
  }, [focusedNoteId, focusSequence, notes]);

  const continueWorkflow = async (note, generateSampleData = false) => {
    const instructions = (drafts[note.id] ?? note.instructions ?? "").trim();
    if (!instructions && !generateSampleData) return;
    requestVersion.current += 1;
    setError("");
    setRetryStatus({
      status: "submitting",
      note_id: note.id,
      message: generateSampleData ? "Starting with generated test data" : "Starting the workflow",
      generate_sample_data: generateSampleData,
      actions_done: 0,
      action_limit: 18,
      actions: [],
    });
    try {
      const status = await webRunsApi.retryWorkflow(
        runId,
        note.id,
        instructions,
        Boolean(saveToSite[note.id]),
        generateSampleData,
      );
      setRetryStatus(status);
      onRetryStatusChange?.(status);
      onViewWorkflow(note.id);
    } catch (cause) {
      const message = cause.message || "Could not continue this workflow.";
      setError(message);
      setRetryStatus({ status: "error", note_id: note.id, error: message });
      onRetryStatusChange?.({ status: "error", note_id: note.id, error: message });
    }
  };

  const waiting = notes.filter((note) => note.needs_input);
  const recentNote = notes.find((note) => note.id === retryStatus.note_id);
  const visibleNotes =
    recentNote &&
    ["submitting", "running", "error"].includes(retryStatus.status) &&
    !waiting.some((note) => note.id === recentNote.id)
      ? [recentNote, ...waiting]
      : waiting;
  return (
    <div className="workflow-input-panel">
      <div className="workflow-notifications-head">
        <div>
          <h3>Notifications</h3>
          <p className="subtle">Workflows waiting for your input appear here.</p>
        </div>
        {!loading && visibleNotes.length > 0 ? (
          <span className="workflow-notification-count">{visibleNotes.length} waiting</span>
        ) : null}
      </div>
      {error && !recentNote ? <p className="notice error">{error}</p> : null}
      {loading ? (
        <p className="subtle">Loading workflows…</p>
      ) : visibleNotes.length ? (
        <div className="workflow-input-list">
          {visibleNotes.map((note) => {
            const progress = retryStatus.note_id === note.id ? retryStatus : null;
            const busy = progress && ["submitting", "running"].includes(progress.status);
            const result = progress?.result_status;
            const canProvideMore =
              note.needs_input &&
              !busy &&
              !(progress?.status === "complete" && result === "crawled");
            return (
              <article className="workflow-notification" key={note.id}>
                <div className="workflow-notification-main">
                  <span className="workflow-notification-icon" aria-hidden="true">
                    !
                  </span>
                  <div>
                    <div className="workflow-notification-title">
                      <strong>{note.name}</strong>
                      <span>{busy ? "In progress" : "Input needed"}</span>
                    </div>
                    {note.reason ? <p className="subtle">{note.reason}</p> : null}
                    {canProvideMore ? <p>{note.request || note.detail}</p> : null}
                    {canProvideMore && note.save_to_site_requested ? (
                      <p className="subtle">This attempt was not saved to the site.</p>
                    ) : null}
                  </div>
                </div>
                {busy ? (
                  <button
                    type="button"
                    className="btn sm secondary workflow-view-progress"
                    onClick={() => onViewWorkflow(note.id)}
                  >
                    View progress in Workflows
                  </button>
                ) : null}
                {progress?.status === "error" ? (
                  <p className="notice error">{progress.error}</p>
                ) : null}
                {canProvideMore ? (
                  <div className="workflow-notification-action">
                    <p className="subtle">
                      What you provide goes to the crawler model and target site. Generate for me
                      lets the crawler make up test values for ordinary fields. Payment details and
                      secrets need values from you. The crawler blocks delete actions.
                    </p>
                    <label className="workflow-input-label" htmlFor={`workflow-input-${note.id}`}>
                      Sample data or instructions
                    </label>
                    <textarea
                      id={`workflow-input-${note.id}`}
                      ref={note.id === focusedNoteId ? focusedInput : null}
                      value={drafts[note.id] ?? note.instructions ?? ""}
                      maxLength={4000}
                      rows={4}
                      placeholder="Describe the steps or provide sample values for this workflow"
                      onChange={(event) =>
                        setDrafts((current) => ({ ...current, [note.id]: event.target.value }))
                      }
                    />
                    <label className="workflow-save-to-site">
                      <input
                        type="checkbox"
                        checked={Boolean(saveToSite[note.id])}
                        onChange={(event) =>
                          setSaveToSite((current) => ({
                            ...current,
                            [note.id]: event.target.checked,
                          }))
                        }
                      />
                      Save to site
                    </label>
                    <div className="workflow-input-actions">
                      <button
                        type="button"
                        className="btn sm"
                        disabled={
                          ["submitting", "running"].includes(retryStatus.status) ||
                          !(drafts[note.id] ?? note.instructions ?? "").trim()
                        }
                        onClick={() => continueWorkflow(note)}
                      >
                        Continue workflow
                      </button>
                      <span className="subtle">or</span>
                      <button
                        type="button"
                        className="btn sm secondary"
                        disabled={["submitting", "running"].includes(retryStatus.status)}
                        onClick={() => continueWorkflow(note, true)}
                      >
                        Generate for me
                      </button>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="workflow-notifications-empty">
          <strong>You're all caught up</strong>
          <p className="subtle">No workflows need your input right now.</p>
        </div>
      )}
    </div>
  );
}
