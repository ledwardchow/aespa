import { useEffect, useMemo, useRef, useState } from "react";

import { SastLeadDetails } from "../../shared/ui/SastLeadDetails.jsx";

import { LeadReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";

export const CANDIDATE_COLUMN_WIDTHS_KEY = "sast-candidate-columns:v1";

export const CANDIDATE_SPLIT_KEY = "sast-candidate-split:v1";

export const CANDIDATE_HIDDEN_STATUSES_KEY = "sast-candidate-hidden-statuses:v1";

export const DEFAULT_CANDIDATE_COLUMN_WIDTHS = [88, null, 96, 132];

export const MIN_CANDIDATE_SPLIT = 35;

export const MAX_CANDIDATE_SPLIT = 72;

export const DEFAULT_CANDIDATE_SPLIT = 54;

export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const SEVERITY_RANK = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };

const VALIDATION_RANK = {
  confirmed: 5,
  inconclusive: 4,
  validating: 3,
  pending: 2,
  dismissed: 1,
  superseded: 0,
};

const SORT_VALUES = {
  severity: (lead) => SEVERITY_RANK[(lead.severity || "medium").toLowerCase()] ?? -1,
  title: (lead) => (lead.title || "").toLowerCase(),
  confidence: (lead) => Number(lead.confidence || 0),
  validation: (lead) => VALIDATION_RANK[lead.validation_status || "pending"] ?? 0,
};

export function sortLeads(leads, sort) {
  if (!sort?.key || !SORT_VALUES[sort.key]) return leads;
  const value = SORT_VALUES[sort.key];
  const direction = sort.direction === "asc" ? 1 : -1;
  return leads
    .map((lead, index) => ({ lead, index }))
    .sort((a, b) => {
      const left = value(a.lead);
      const right = value(b.lead);
      const result =
        typeof left === "string" ? left.localeCompare(right) : left < right ? -1 : left > right;
      return Number(result) * direction || a.index - b.index;
    })
    .map((item) => item.lead);
}

export function readStoredValue(key, fallback, validate) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return validate(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

export function CandidateTable({
  leads,
  selectedId,
  onSelect,
  onRevalidate,
  revalidatingLeadId,
  canRevalidate,
}) {
  const [widths, setWidths] = useState(() =>
    readStoredValue(
      CANDIDATE_COLUMN_WIDTHS_KEY,
      DEFAULT_CANDIDATE_COLUMN_WIDTHS,
      (value) => Array.isArray(value) && value.length === DEFAULT_CANDIDATE_COLUMN_WIDTHS.length,
    ),
  );
  const widthsRef = useRef(widths);
  const [sort, setSort] = useState({ key: null, direction: "desc" });
  const [hiddenStatuses, setHiddenStatuses] = useState(() =>
    readStoredValue(
      CANDIDATE_HIDDEN_STATUSES_KEY,
      [],
      (value) => Array.isArray(value) && value.every((item) => typeof item === "string"),
    ),
  );
  const statusCounts = useMemo(() => {
    const counts = new Map();
    for (const lead of leads) {
      const status = lead.validation_status || "pending";
      counts.set(status, (counts.get(status) || 0) + 1);
    }
    return [...counts.entries()].sort(
      ([left], [right]) => (VALIDATION_RANK[right] ?? 0) - (VALIDATION_RANK[left] ?? 0),
    );
  }, [leads]);
  const visibleLeads = useMemo(
    () => leads.filter((lead) => !hiddenStatuses.includes(lead.validation_status || "pending")),
    [leads, hiddenStatuses],
  );
  const sortedLeads = useMemo(() => sortLeads(visibleLeads, sort), [visibleLeads, sort]);
  const toggleStatus = (status) =>
    setHiddenStatuses((current) => {
      const next = current.includes(status)
        ? current.filter((item) => item !== status)
        : [...current, status];
      try {
        localStorage.setItem(CANDIDATE_HIDDEN_STATUSES_KEY, JSON.stringify(next));
      } catch {}
      return next;
    });
  const toggleSort = (key) =>
    setSort((current) => {
      if (current.key !== key) return { key, direction: key === "title" ? "asc" : "desc" };
      const firstDirection = key === "title" ? "asc" : "desc";
      if (current.direction === firstDirection)
        return { key, direction: firstDirection === "asc" ? "desc" : "asc" };
      return { key: null, direction: "desc" };
    });

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
  const header = (label, index, sortKey) => {
    const active = sort.key === sortKey;
    const ariaSort = active ? (sort.direction === "asc" ? "ascending" : "descending") : "none";
    return (
      <th aria-sort={ariaSort}>
        <button
          type="button"
          className={`sast-sort-button${active ? " active" : ""}`}
          onClick={() => toggleSort(sortKey)}
          title={`Sort by ${label.toLowerCase()}`}
        >
          {label}
          <span className="sast-sort-indicator" aria-hidden="true">
            {active ? (sort.direction === "asc" ? "▲" : "▼") : "↕"}
          </span>
        </button>
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
  };

  if (!leads.length) return <div className="sast-empty-state">No findings yet.</div>;
  const hiddenCount = leads.length - visibleLeads.length;
  return (
    <>
      <div className="sast-status-filter" role="group" aria-label="Show findings by status">
        <span className="sast-status-filter-label">Show</span>
        {statusCounts.map(([status, count]) => {
          const shown = !hiddenStatuses.includes(status);
          return (
            <button
              key={status}
              type="button"
              className={`sast-status-filter-chip sast-state sast-state-${status}${shown ? "" : " hidden"}`}
              aria-pressed={shown}
              title={shown ? `Hide ${status} findings` : `Show ${status} findings`}
              onClick={() => toggleStatus(status)}
            >
              {status} {count}
            </button>
          );
        })}
        {hiddenCount ? (
          <span className="sast-status-filter-hidden">{hiddenCount} hidden</span>
        ) : null}
      </div>
      {sortedLeads.length ? (
        <div className="sast-table-wrap">
          <table className="sast-candidate-table">
            <colgroup>
              {widths.map((width, index) => (
                <col key={index} style={{ width: width == null ? undefined : `${width}px` }} />
              ))}
            </colgroup>
            <thead>
              <tr>
                {header("Severity", 0, "severity")}
                {header("Finding", 1, "title")}
                {header("Confidence", 2, "confidence")}
                {header("Status", 3, "validation")}
              </tr>
            </thead>
            <tbody>
              {sortedLeads.map((lead) => (
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
                    <span className="sast-candidate-title">{lead.title || "Untitled finding"}</span>
                    <code>{lead.location || "Location not provided"}</code>
                  </td>
                  <td>{Math.round((lead.confidence || 0) * 100)}%</td>
                  <td>
                    <div className="sast-lead-validation-actions">
                      <span
                        className={`sast-state sast-state-${lead.validation_status || "pending"}`}
                      >
                        {lead.validation_status || "pending"}
                      </span>
                      {lead.validation_status === "inconclusive" && onRevalidate && (
                        <button
                          type="button"
                          className="btn ghost sm"
                          disabled={!canRevalidate || revalidatingLeadId != null}
                          onClick={(event) => {
                            event.stopPropagation();
                            onRevalidate(lead);
                          }}
                        >
                          {revalidatingLeadId === lead.id ? "Starting…" : "Re-validate"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="sast-empty-state">All findings are hidden by the status filter.</div>
      )}
    </>
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
  onRevalidate,
  revalidatingLeadId,
  canRevalidate,
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
            <div className="sast-panel-title">Findings</div>
          </div>
          <div className="row">
            <span className="sast-state sast-state-open">{reportableCount} reportable</span>
            <button className="btn ghost sm" disabled={!leads.length} onClick={onExport}>
              Export report ↓
            </button>
          </div>
        </div>
        <CandidateTable
          leads={leads}
          selectedId={selectedLead?.id}
          onSelect={onSelect}
          onRevalidate={onRevalidate}
          revalidatingLeadId={revalidatingLeadId}
          canRevalidate={canRevalidate}
        />
      </section>
      <div
        className="sast-layout-resizer"
        role="separator"
        aria-label="Resize findings list and finding details"
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
      <LeadEvidence
        lead={selectedLead}
        targets={targets}
        onQueue={onQueue}
        queueBusy={queueBusy}
        onRevalidate={onRevalidate}
        revalidatingLeadId={revalidatingLeadId}
        canRevalidate={canRevalidate}
      />
    </div>
  );
}

export function LeadEvidence({
  lead,
  targets,
  onQueue,
  queueBusy,
  onRevalidate,
  revalidatingLeadId,
  canRevalidate,
}) {
  const [targetKey, setTargetKey] = useState("");
  useEffect(() => {
    setTargetKey("");
  }, [lead?.id]);
  if (!lead)
    return (
      <aside className="sast-evidence-panel">
        <div className="sast-panel-empty">Select a finding to see its details.</div>
      </aside>
    );
  const selectedTarget = targets.find(
    (target) => `${target.run_type}:${target.run_id}` === targetKey,
  );
  return (
    <aside className="sast-evidence-panel">
      <div className="sast-panel-header">
        <div>
          <div className="sast-panel-title">Finding details</div>
          <div className="sast-panel-sub">
            <LeadReferenceLink
              reference={lead.reference || `#${lead.id}`}
              title={lead.title}
              description={lead.description}
              severity={lead.severity}
            />{" "}
            · {lead.fingerprint?.slice(0, 10) || "no fingerprint"}
          </div>
        </div>
        <div className="sast-lead-validation-actions">
          <span className={`sast-state sast-state-${lead.validation_status || "pending"}`}>
            {lead.validation_status || "pending"}
          </span>
          {lead.validation_status === "inconclusive" && onRevalidate && (
            <button
              type="button"
              className="btn ghost sm"
              disabled={!canRevalidate || revalidatingLeadId != null}
              onClick={() => onRevalidate(lead)}
            >
              {revalidatingLeadId === lead.id ? "Starting…" : "Re-validate"}
            </button>
          )}
        </div>
      </div>
      <div className="sast-evidence-body">
        <SastLeadDetails lead={lead} showSummary={false} />
        <div className="sast-handoff-box">
          <strong>Live testing</strong>
          <span>
            {lead.reportable
              ? "Send this confirmed finding to a web or API run to test it against the live app."
              : "Only confirmed, reportable findings can be sent for live testing."}
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
