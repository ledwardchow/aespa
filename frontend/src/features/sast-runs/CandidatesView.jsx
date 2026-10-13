import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { SastLeadDetails } from "../../shared/ui/SastLeadDetails.jsx";

import { getSastSarifUrl } from "../../shared/api/sastRuns.js";
import { LeadReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";
import { normalizeSeverity, severityRank } from "../../shared/findings/severity.js";

export const CANDIDATE_COLUMN_WIDTHS_KEY = "sast-candidate-columns:v2";

export const CANDIDATE_HIDDEN_STATUSES_KEY = "sast-candidate-hidden-statuses:v1";

export const DEFAULT_CANDIDATE_COLUMN_WIDTHS = [112, 88, null, 96, 190];

const severityLabel = (lead) => normalizeSeverity(lead.severity, "medium");
const referenceLabel = (lead) => lead.reference || (lead.id == null ? "—" : `#${lead.id}`);

const VALIDATION_RANK = {
  confirmed: 5,
  inconclusive: 4,
  validating: 3,
  pending: 2,
  dismissed: 1,
  superseded: 0,
};

const SORT_VALUES = {
  reference: referenceLabel,
  severity: (lead) => severityRank(lead.severity, "medium"),
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
        typeof left === "string"
          ? left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" })
          : left < right
            ? -1
            : left > right;
      if (result) return Number(result) * direction;
      if (sort.key === "severity") {
        const titleOrder = SORT_VALUES.title(a.lead).localeCompare(SORT_VALUES.title(b.lead));
        if (titleOrder) return titleOrder;
      }
      return a.index - b.index;
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

function FindingsExportMenu({ runId, onExport, disabled }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!menuRef.current?.contains(event.target)) setOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="sast-actions-menu" ref={menuRef}>
      <button
        type="button"
        className="btn ghost sm"
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        Export findings ↓
      </button>
      {open && (
        <div className="sast-actions-popover" role="menu">
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onExport();
            }}
          >
            Export Markdown
          </button>
          <a href={getSastSarifUrl(runId)} download role="menuitem" onClick={() => setOpen(false)}>
            Export SARIF
          </a>
        </div>
      )}
    </div>
  );
}

export function CandidateTable({
  leads,
  selectedId,
  onSelect,
  onRevalidate,
  revalidatingLeadId,
  canRevalidate,
  onVisibleLeadsChange,
}) {
  const [widths, setWidths] = useState(() => {
    const previousWidths = readStoredValue(
      "sast-candidate-columns:v1",
      null,
      (value) => Array.isArray(value) && value.length === 4,
    );
    return readStoredValue(
      CANDIDATE_COLUMN_WIDTHS_KEY,
      previousWidths ? [112, ...previousWidths] : DEFAULT_CANDIDATE_COLUMN_WIDTHS,
      (value) => Array.isArray(value) && value.length === DEFAULT_CANDIDATE_COLUMN_WIDTHS.length,
    );
  });
  const widthsRef = useRef(widths);
  const [sort, setSort] = useState({ key: "reference", direction: "asc" });
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
  useEffect(() => {
    onVisibleLeadsChange?.(sortedLeads.map((lead) => lead.id));
  }, [onVisibleLeadsChange, sortedLeads]);
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
      const firstDirection = key === "title" || key === "reference" ? "asc" : "desc";
      if (current.key !== key) return { key, direction: firstDirection };
      if (current.direction === firstDirection)
        return { key, direction: firstDirection === "asc" ? "desc" : "asc" };
      return { key: null, direction: "desc" };
    });

  const updateWidth = (index, width) => {
    const next = [...widthsRef.current];
    next[index] = Math.max(index === 2 ? 220 : index === 4 ? 150 : 64, Math.round(width));
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
                {header("Reference", 0, "reference")}
                {header("Severity", 1, "severity")}
                {header("Finding", 2, "title")}
                {header("Confidence", 3, "confidence")}
                {header("Status", 4, "validation")}
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
                  <td className="sast-candidate-reference">{referenceLabel(lead)}</td>
                  <td>
                    <span className={`sast-severity sast-severity-${severityLabel(lead)}`}>
                      {severityLabel(lead).toUpperCase()}
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
  runId,
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
  initialLeadRef,
  onCloseDetail,
}) {
  const [detailOpen, setDetailOpen] = useState(Boolean(initialLeadRef));
  const [visibleLeadIds, setVisibleLeadIds] = useState([]);
  const layoutRef = useRef(null);
  const backButtonRef = useRef(null);
  const listScrollTop = useRef(0);
  const restoreListScroll = useRef(false);
  const currentIndex = visibleLeadIds.indexOf(selectedLead?.id);

  useEffect(() => {
    if (initialLeadRef) setDetailOpen(true);
  }, [initialLeadRef]);

  useLayoutEffect(() => {
    if (detailOpen) {
      backButtonRef.current?.focus({ preventScroll: true });
      return;
    }
    if (!restoreListScroll.current) return;
    restoreListScroll.current = false;
    const scrollArea = layoutRef.current?.closest(".sast-run-content");
    if (scrollArea) scrollArea.scrollTop = listScrollTop.current;
    layoutRef.current
      ?.querySelector(".sast-candidate-table tr.selected")
      ?.focus({ preventScroll: true });
  }, [detailOpen]);

  const openLead = (id) => {
    const scrollArea = layoutRef.current?.closest(".sast-run-content");
    listScrollTop.current = scrollArea?.scrollTop || 0;
    if (scrollArea) scrollArea.scrollTop = 0;
    onSelect(id);
    setDetailOpen(true);
  };
  const closeLead = () => {
    restoreListScroll.current = true;
    setDetailOpen(false);
    onCloseDetail?.();
  };
  const moveLead = (direction) => {
    const nextId = visibleLeadIds[currentIndex + direction];
    if (nextId == null) return;
    onSelect(nextId);
    const scrollArea = layoutRef.current?.closest(".sast-run-content");
    if (scrollArea) scrollArea.scrollTop = 0;
  };

  return (
    <div className="sast-findings-view" ref={layoutRef}>
      <section className="sast-panel sast-candidate-ledger" hidden={detailOpen}>
        <div className="sast-panel-header">
          <div>
            <div className="sast-panel-title">Findings</div>
            <div className="sast-panel-sub">Review possible issues found in the source.</div>
          </div>
          <div className="row">
            <span className="sast-state sast-state-open">{reportableCount} reportable</span>
            <FindingsExportMenu runId={runId} onExport={onExport} disabled={!leads.length} />
          </div>
        </div>
        <CandidateTable
          leads={leads}
          selectedId={selectedLead?.id}
          onSelect={openLead}
          onRevalidate={onRevalidate}
          revalidatingLeadId={revalidatingLeadId}
          canRevalidate={canRevalidate}
          onVisibleLeadsChange={setVisibleLeadIds}
        />
      </section>
      {detailOpen && (
        <div className="sast-finding-detail">
          <div className="sast-finding-toolbar">
            <button
              type="button"
              className="sast-finding-back"
              onClick={closeLead}
              ref={backButtonRef}
            >
              ← Back to findings
            </button>
            <div className="sast-finding-navigation" aria-label="Finding navigation">
              <button
                type="button"
                className="btn ghost sm"
                onClick={() => moveLead(-1)}
                disabled={currentIndex <= 0}
              >
                ← Previous
              </button>
              <span>
                {currentIndex >= 0 ? `${currentIndex + 1} of ${visibleLeadIds.length}` : "Finding"}
              </span>
              <button
                type="button"
                className="btn ghost sm"
                onClick={() => moveLead(1)}
                disabled={currentIndex < 0 || currentIndex >= visibleLeadIds.length - 1}
              >
                Next →
              </button>
            </div>
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
      )}
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
      <section className="sast-evidence-panel">
        <div className="sast-panel-empty">Select a finding to see its details.</div>
      </section>
    );
  const selectedTarget = targets.find(
    (target) => `${target.target_type}:${target.target_id}` === targetKey,
  );
  const canTestLive = lead.reportable && lead.validation_status === "confirmed";
  return (
    <section className="sast-evidence-panel">
      <div className="sast-panel-header sast-finding-header">
        <div className="sast-finding-header-main">
          <span className={`sast-severity sast-severity-${severityLabel(lead)}`}>
            {severityLabel(lead).toUpperCase()}
          </span>
          <span className={`sast-state sast-state-${lead.validation_status || "pending"}`}>
            {lead.validation_status || "pending"}
          </span>
          <h2>{lead.title || "Untitled finding"}</h2>
          <div className="sast-panel-sub">
            {lead.location || "Location not provided"} · {Math.round((lead.confidence || 0) * 100)}%
            confidence ·{" "}
            <LeadReferenceLink
              reference={lead.reference || `#${lead.id}`}
              title={lead.title}
              description={lead.description}
              severity={lead.severity}
            />
          </div>
        </div>
        <div className="sast-finding-header-actions">
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
          <div className="sast-live-testing">
            <strong>Live testing</strong>
            <span>
              {canTestLive
                ? "Create a run for this finding. You can start the test from the new run."
                : "Confirm this finding before testing it live."}
            </span>
            <div className="sast-live-testing-controls">
              <select
                aria-label="Application for live testing"
                value={targetKey}
                disabled={!canTestLive || queueBusy}
                onChange={(event) => setTargetKey(event.target.value)}
              >
                <option value="">Select app…</option>
                <optgroup label="Sites">
                  {targets
                    .filter((target) => target.target_type === "site")
                    .map((target) => (
                      <option key={`site:${target.target_id}`} value={`site:${target.target_id}`}>
                        {target.name} · {target.url}
                      </option>
                    ))}
                </optgroup>
                <optgroup label="API collections">
                  {targets
                    .filter((target) => target.target_type === "api_collection")
                    .map((target) => (
                      <option
                        key={`api_collection:${target.target_id}`}
                        value={`api_collection:${target.target_id}`}
                      >
                        {target.name} · {target.url}
                      </option>
                    ))}
                </optgroup>
              </select>
              <button
                type="button"
                className="btn sm"
                disabled={!canTestLive || !selectedTarget || queueBusy}
                onClick={() => onQueue(lead, selectedTarget)}
              >
                {queueBusy ? "Creating…" : "Create test run"}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="sast-evidence-body">
        <SastLeadDetails lead={lead} showSummary={false} />
      </div>
    </section>
  );
}
