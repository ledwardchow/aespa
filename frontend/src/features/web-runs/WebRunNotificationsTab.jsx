import { useCallback, useEffect, useRef, useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { anyRetryBusy, isRetryBusy, mergeRetries, retriesByNote } from "./workflowRetries.js";

export function WebRunNotificationsTab({
  runId,
  onNotesChange,
  onRetryStatusChange,
  onViewWorkflow,
  focusedNoteId,
  focusSequence,
}) {
  const [notes, setNotes] = useState([]);
  const [retries, setRetries] = useState({});
  const [drafts, setDrafts] = useState({});
  const [saveToSite, setSaveToSite] = useState({});
  const [expandedId, setExpandedId] = useState(null);
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
    setRetries((current) => mergeRetries(current, retriesByNote(status)));
    setLoading(false);
  }, [runId, onNotesChange]);

  useEffect(() => {
    onRetryStatusChange?.(retries);
  }, [retries, onRetryStatusChange]);

  usePolling(load, {
    intervalMs: anyRetryBusy(retries) ? 1000 : 15000,
  });

  useEffect(() => {
    if (focusSequence) setExpandedId(null);
  }, [focusSequence]);

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
    const setProgress = (progress) =>
      setRetries((current) => ({ ...current, [note.id]: progress }));
    setProgress({
      status: "submitting",
      note_id: note.id,
      message: generateSampleData ? "Starting with generated test data" : "Starting the workflow",
      generate_sample_data: generateSampleData,
      actions_done: 0,
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
      setProgress(status);
      onViewWorkflow(note.id);
    } catch (cause) {
      const message = cause.message || "Could not continue this workflow.";
      setProgress({ status: "error", note_id: note.id, error: message });
    }
  };

  const waiting = notes.filter(
    (note) => note.needs_input && note.status !== "crawled" && !note.superseded,
  );
  const recentNotes = notes.filter(
    (note) =>
      ["submitting", "running", "error"].includes(retries[note.id]?.status) &&
      !waiting.some((item) => item.id === note.id),
  );
  const visibleNotes = [...recentNotes, ...waiting];
  const openId = visibleNotes.some((note) => note.id === expandedId)
    ? expandedId
    : visibleNotes.some((note) => note.id === focusedNoteId)
      ? focusedNoteId
      : visibleNotes[0]?.id;
  return (
    <div className="workflow-input-panel">
      <div className="workflow-notifications-head">
        <div>
          <h3>Needs input</h3>
          <p className="subtle">
            The crawler stopped at these workflows. Add sample data or instructions to continue.
          </p>
        </div>
        {!loading && visibleNotes.length > 0 ? (
          <span className="workflow-notification-count">{visibleNotes.length} waiting</span>
        ) : null}
      </div>
      {loading ? (
        <p className="subtle">Loading workflows…</p>
      ) : visibleNotes.length ? (
        <div className="workflow-input-list">
          {visibleNotes.map((note) => {
            const progress = retries[note.id] || null;
            const busy = isRetryBusy(progress);
            const result = progress?.result_status;
            const canProvideMore =
              note.needs_input &&
              note.status !== "crawled" &&
              !note.superseded &&
              !busy &&
              !(progress?.status === "complete" && result === "crawled");
            const expanded = note.id === openId;
            return (
              <article className="workflow-notification" key={note.id}>
                <div className="workflow-notification-main">
                  <span className="workflow-notification-icon" aria-hidden="true">
                    !
                  </span>
                  <div>
                    <button
                      type="button"
                      className="workflow-notification-title"
                      aria-expanded={expanded}
                      onClick={() => setExpandedId(note.id)}
                    >
                      <strong>{note.name}</strong>
                      <span>{busy ? "In progress" : "Input needed"}</span>
                    </button>
                    {expanded && note.reason ? <p className="subtle">{note.reason}</p> : null}
                    {expanded && canProvideMore ? <p>{note.request || note.detail}</p> : null}
                    {expanded && canProvideMore && note.save_to_site_requested ? (
                      <p className="subtle">
                        This attempt's sample data was not saved to the site.
                      </p>
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
                {expanded && canProvideMore ? (
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
                      Save sample data to site if reached
                    </label>
                    <div className="workflow-input-actions">
                      <button
                        type="button"
                        className="btn sm"
                        disabled={!(drafts[note.id] ?? note.instructions ?? "").trim()}
                        onClick={() => continueWorkflow(note)}
                      >
                        Continue workflow
                      </button>
                      <span className="subtle">or</span>
                      <button
                        type="button"
                        className="btn sm secondary"
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
