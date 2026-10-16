import { useEffect } from "react";
import { WebRunNotificationsTab } from "./WebRunNotificationsTab.jsx";

export function WorkflowInputPill({ count, open, onClick }) {
  if (!count) return null;
  return (
    <button
      type="button"
      className="workflow-input-pill"
      aria-expanded={open}
      aria-controls="workflow-input-drawer"
      title="Open workflows that need your input"
      onClick={onClick}
    >
      <span className="workflow-input-pill-icon" aria-hidden="true">
        !
      </span>
      {count} need{count === 1 ? "s" : ""} input
    </button>
  );
}

export function WorkflowInputDrawer({
  open,
  runId,
  onClose,
  onNotesChange,
  onRetryStatusChange,
  onViewWorkflow,
  focusedNoteId,
  focusSequence,
}) {
  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <aside
      id="workflow-input-drawer"
      className="workflow-input-drawer"
      role="dialog"
      aria-label="Needs input"
    >
      <button
        type="button"
        className="workflow-input-drawer-close"
        aria-label="Close"
        onClick={onClose}
      >
        ×
      </button>
      <WebRunNotificationsTab
        runId={runId}
        onNotesChange={onNotesChange}
        onRetryStatusChange={onRetryStatusChange}
        onViewWorkflow={onViewWorkflow}
        focusedNoteId={focusedNoteId}
        focusSequence={focusSequence}
      />
    </aside>
  );
}
