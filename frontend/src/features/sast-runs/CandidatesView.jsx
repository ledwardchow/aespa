import { useEffect, useRef, useState } from "react";

import { SastLeadDetails } from "../../shared/ui/SastLeadDetails.jsx";

import { LeadReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";

export const CANDIDATE_COLUMN_WIDTHS_KEY = "sast-candidate-columns:v1";

export const CANDIDATE_SPLIT_KEY = "sast-candidate-split:v1";

export const DEFAULT_CANDIDATE_COLUMN_WIDTHS = [88, null, 96, 132];

export const MIN_CANDIDATE_SPLIT = 35;

export const MAX_CANDIDATE_SPLIT = 72;

export const DEFAULT_CANDIDATE_SPLIT = 54;

export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export function readStoredValue(key, fallback, validate) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return validate(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

export function CandidateTable({ leads, selectedId, onSelect }) {
  const [widths, setWidths] = useState(() =>
    readStoredValue(
      CANDIDATE_COLUMN_WIDTHS_KEY,
      DEFAULT_CANDIDATE_COLUMN_WIDTHS,
      (value) => Array.isArray(value) && value.length === DEFAULT_CANDIDATE_COLUMN_WIDTHS.length,
    ),
  );
  const widthsRef = useRef(widths);

  const updateWidth = (index, width) => {
    const next = [...widthsRef.current];
    next[index] = Math.max(index === 1 ? 220 : 64, Math.round(width));
    widthsRef.current = next;
    setWidths(next);
  };
  const saveWidths = () => {
    try {
      localStorage.setItem(CANDIDATE_COLUMN_WIDTHS_KEY, JSON.stringify(widthsRef.current));
    } catch {}
  };
  const startColumnResize = (index, event) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const header = event.currentTarget.closest("th");
    const startWidth = widthsRef.current[index] ?? header?.getBoundingClientRect().width ?? 100;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (moveEvent) => updateWidth(index, startWidth + moveEvent.clientX - startX);
    const onEnd = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onEnd);
      document.removeEventListener("pointercancel", onEnd);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      saveWidths();
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onEnd);
    document.addEventListener("pointercancel", onEnd);
  };
  const resizeColumnWithKeyboard = (index, event) => {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    const header = event.currentTarget.closest("th");
    updateWidth(
      index,
      (widthsRef.current[index] ?? header?.getBoundingClientRect().width ?? 100) + direction * 12,
    );
    saveWidths();
  };
  const header = (label, index) => (
    <th>
      {label}
      <span
        className="sast-column-resizer"
        role="separator"
        aria-label={`Resize ${label} column`}
        aria-orientation="vertical"
        tabIndex="0"
        onPointerDown={(event) => startColumnResize(index, event)}
        onKeyDown={(event) => resizeColumnWithKeyboard(index, event)}
      />
    </th>
  );

  if (!leads.length)
    return <div className="sast-empty-state">No discovery candidates have been persisted yet.</div>;
  return (
    <div className="sast-table-wrap">
      <table className="sast-candidate-table">
        <colgroup>
          {widths.map((width, index) => (
            <col key={index} style={{ width: width == null ? undefined : `${width}px` }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {header("Severity", 0)}
            {header("Candidate", 1)}
            {header("Confidence", 2)}
            {header("Validation", 3)}
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr
              key={lead.id}
              className={selectedId === lead.id ? "selected" : ""}
              onClick={() => onSelect(lead.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect(lead.id);
                }
              }}
              tabIndex={0}
              role="button"
              aria-pressed={selectedId === lead.id}
            >
              <td>
                <span
                  className={`sast-severity sast-severity-${(lead.severity || "medium").toLowerCase()}`}
                >
                  {(lead.severity || "medium").toUpperCase()}
                </span>
              </td>
              <td>
                <span className="sast-candidate-title">{lead.title || "Untitled candidate"}</span>
                <code>{lead.location || "Location not provided"}</code>
              </td>
              <td>{Math.round((lead.confidence || 0) * 100)}%</td>
              <td>
                <span className={`sast-state sast-state-${lead.validation_status || "pending"}`}>
                  {lead.validation_status || "pending"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CandidatesView({
  leads,
  selectedLead,
  onSelect,
  targets,
  onQueue,
  queueBusy,
  reportableCount,
  onExport,
}) {
  const [ledgerWidth, setLedgerWidth] = useState(() =>
    readStoredValue(
      CANDIDATE_SPLIT_KEY,
      DEFAULT_CANDIDATE_SPLIT,
      (value) =>
        Number.isFinite(value) && value >= MIN_CANDIDATE_SPLIT && value <= MAX_CANDIDATE_SPLIT,
    ),
  );
  const ledgerWidthRef = useRef(ledgerWidth);
  const layoutRef = useRef(null);

  const updateLedgerWidth = (width) => {
    const next = clamp(width, MIN_CANDIDATE_SPLIT, MAX_CANDIDATE_SPLIT);
    ledgerWidthRef.current = next;
    setLedgerWidth(next);
  };
  const saveLedgerWidth = () => {
    try {
      localStorage.setItem(CANDIDATE_SPLIT_KEY, JSON.stringify(ledgerWidthRef.current));
    } catch {}
  };
  const startSplitResize = (event) => {
    event.preventDefault();
    const bounds = layoutRef.current?.getBoundingClientRect();
    if (!bounds?.width) return;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (moveEvent) =>
      updateLedgerWidth(((moveEvent.clientX - bounds.left) / bounds.width) * 100);
    const onEnd = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onEnd);
      document.removeEventListener("pointercancel", onEnd);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      saveLedgerWidth();
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onEnd);
    document.addEventListener("pointercancel", onEnd);
  };
  const resizeSplitWithKeyboard = (event) => {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    updateLedgerWidth(ledgerWidthRef.current + direction * 2);
    saveLedgerWidth();
  };

  return (
    <div
      className="sast-candidates-layout"
      ref={layoutRef}
      style={{ "--sast-ledger-width": `${ledgerWidth}%` }}
    >
      <section className="sast-panel sast-candidate-ledger">
        <div className="sast-panel-header">
          <div>
            <div className="sast-panel-title">Candidate ledger</div>
            <div className="sast-panel-sub">
              Discovery hypotheses with independent validation outcomes
            </div>
          </div>
          <div className="row">
            <span className="sast-state sast-state-open">{reportableCount} reportable</span>
            <button className="btn ghost sm" disabled={!leads.length} onClick={onExport}>
              Export report ↓
            </button>
          </div>
        </div>
        <CandidateTable leads={leads} selectedId={selectedLead?.id} onSelect={onSelect} />
      </section>
      <div
        className="sast-layout-resizer"
        role="separator"
        aria-label="Resize candidate ledger and evidence chain"
        aria-orientation="vertical"
        aria-valuemin={MIN_CANDIDATE_SPLIT}
        aria-valuemax={MAX_CANDIDATE_SPLIT}
        aria-valuenow={Math.round(ledgerWidth)}
        tabIndex="0"
        onPointerDown={startSplitResize}
        onKeyDown={resizeSplitWithKeyboard}
      >
        <span aria-hidden="true" />
      </div>
      <LeadEvidence lead={selectedLead} targets={targets} onQueue={onQueue} queueBusy={queueBusy} />
    </div>
  );
}

export function LeadEvidence({ lead, targets, onQueue, queueBusy }) {
  const [targetKey, setTargetKey] = useState("");
  useEffect(() => {
    setTargetKey("");
  }, [lead?.id]);
  if (!lead)
    return (
      <aside className="sast-evidence-panel">
        <div className="sast-panel-empty">Select a candidate to inspect its evidence chain.</div>
      </aside>
    );
  const selectedTarget = targets.find(
    (target) => `${target.run_type}:${target.run_id}` === targetKey,
  );
  return (
    <aside className="sast-evidence-panel">
      <div className="sast-panel-header">
        <div>
          <div className="sast-panel-title">Evidence chain</div>
          <div className="sast-panel-sub">
            <LeadReferenceLink
              reference={lead.reference || `#${lead.id}`}
              title={lead.title}
              description={lead.description}
              severity={lead.severity}
            />{" "}
            · {lead.fingerprint?.slice(0, 10) || "unfingerprinted"}
          </div>
        </div>
        <span className={`sast-state sast-state-${lead.validation_status || "pending"}`}>
          {lead.validation_status || "pending"}
        </span>
      </div>
      <div className="sast-evidence-body">
        <SastLeadDetails lead={lead} showSummary={false} />
        <div className="sast-handoff-box">
          <strong>Dynamic confirmation</strong>
          <span>
            {lead.reportable
              ? "Send this validated lead to a web or API run for live reproduction."
              : "Only independently confirmed, reportable leads can be handed off."}
          </span>
          <select
            aria-label="Dynamic target run"
            value={targetKey}
            disabled={!lead.reportable || queueBusy}
            onChange={(event) => setTargetKey(event.target.value)}
          >
            <option value="">Select target run…</option>
            {targets.map((target) => (
              <option
                key={`${target.run_type}:${target.run_id}`}
                value={`${target.run_type}:${target.run_id}`}
              >
                {target.run_type.toUpperCase()} · {target.target} · {target.name}
              </option>
            ))}
          </select>
          <button
            className="btn sm"
            disabled={!lead.reportable || !selectedTarget || queueBusy}
            onClick={() => onQueue(lead, selectedTarget)}
          >
            {queueBusy ? "Queuing…" : "Queue live test"}
          </button>
        </div>
      </div>
    </aside>
  );
}
