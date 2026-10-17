import { useEffect, useRef, useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { groupWorkflowNotes, statusLabel } from "./WebRunWorkflowsTab.jsx";
import styles from "./UncrawledWorkflowWarning.module.css";

export function uncrawledWorkflows(notes) {
  return groupWorkflowNotes(notes)
    .map(({ root, attempts }) => ({ ...attempts.at(-1), name: root.name }))
    .filter((note) => !note.superseded && note.status !== "crawled");
}

function WarningDialog({ pending, onCancel, onView, onConfirm, onRetry }) {
  const dialog = useRef(null);

  useEffect(() => {
    const element = dialog.current;
    const opener = document.activeElement;
    element?.showModal();
    element?.querySelector("button")?.focus();
    return () => {
      element?.close();
      if (opener instanceof window.HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);

  const failed = pending.kind === "error";
  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      aria-labelledby="uncrawled-workflow-heading"
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
    >
      <h2 id="uncrawled-workflow-heading">
        {failed ? "Could not check workflows" : "Some workflows have not been crawled"}
      </h2>
      {failed ? (
        <p role="alert">{pending.message} Try again before starting the scan.</p>
      ) : (
        <>
          <p>
            {pending.workflows.length}{" "}
            {pending.workflows.length === 1 ? "workflow has" : "workflows have"} not been crawled.
            These workflows may not be tested by the scan if they remain uncrawled.
          </p>
          <ul>
            {pending.workflows.map((note) => (
              <li key={note.id ?? note.name}>
                <strong>{note.name || "Unnamed workflow"}</strong> - {statusLabel(note)}
              </li>
            ))}
          </ul>
        </>
      )}
      <div className={styles.actions}>
        <button type="button" className="btn secondary" onClick={onCancel}>
          Cancel
        </button>
        {failed ? (
          <button type="button" className="btn" onClick={onRetry}>
            Try again
          </button>
        ) : (
          <>
            <button type="button" className="btn secondary" onClick={onView}>
              View workflows
            </button>
            <button type="button" className="btn" onClick={onConfirm}>
              {pending.action === "crawl-then-scan" ? "Continue anyway" : "Start scan anyway"}
            </button>
          </>
        )}
      </div>
    </dialog>
  );
}

export function useUncrawledWorkflowWarning({ runId, onStart, onViewWorkflows, onAcknowledged }) {
  const [pending, setPending] = useState(null);
  const pendingRef = useRef(null);
  const busy = useRef(false);
  const updatePending = (next) => {
    pendingRef.current = next;
    setPending(next);
  };

  const check = async (action, coverageMode) => {
    if (busy.current) return;
    busy.current = true;
    updatePending(null);
    try {
      const result = await webRunsApi.getWorkflowNotes(runId);
      if (!Array.isArray(result?.notes)) throw new Error("Workflow notes could not be loaded.");
      const workflows = uncrawledWorkflows(result.notes);
      if (workflows.length) {
        updatePending({ kind: "warning", action, coverageMode, workflows });
      } else {
        await onStart(action, coverageMode);
      }
    } catch (error) {
      updatePending({
        kind: "error",
        action,
        coverageMode,
        message: error?.message || "Workflow notes could not be loaded",
      });
    } finally {
      busy.current = false;
    }
  };

  const requestStart = (action, coverageMode) => {
    if (pendingRef.current || busy.current) return;
    void check(action, coverageMode);
  };
  const confirm = async () => {
    if (!pendingRef.current || busy.current) return;
    busy.current = true;
    const { action, coverageMode, workflows } = pendingRef.current;
    updatePending(null);
    try {
      const started = await onStart(action, coverageMode);
      if (started === true) onAcknowledged?.(workflows.map((note) => note.id));
    } finally {
      busy.current = false;
    }
  };

  return {
    requestStart,
    warning: pending ? (
      <WarningDialog
        pending={pending}
        onCancel={() => updatePending(null)}
        onView={() => {
          const noteId = pending.workflows[0]?.id;
          updatePending(null);
          onViewWorkflows(noteId);
        }}
        onConfirm={() => void confirm()}
        onRetry={() => void check(pending.action, pending.coverageMode)}
      />
    ) : null,
  };
}
