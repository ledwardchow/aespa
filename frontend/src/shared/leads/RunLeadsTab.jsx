import * as apiRunsApi from "../api/apiRuns.js";
import * as webRunsApi from "../api/webRuns.js";
import { useState, useEffect, useCallback, useRef } from "react";

import { SastImportDialog } from "./SastImportDialog.tsx";

import { leadsExportFilename, leadsToMarkdown } from "./files.js";
import { downloadTextFile } from "../lib/download.js";
import { usePolling } from "../hooks/usePolling.js";
import { SastLeadDetails } from "../ui/SastLeadDetails.jsx";
import { LeadReferenceLink } from "../ui/FindingReferenceLink.jsx";
import { Notice, PageError } from "../ui/Notice.jsx";

export function WebRunSastLeadsTab({ runId, scanRunning, runKind = "web", initialLeadRef }) {
  const isApi = runKind === "api";
  const [leads, setLeads] = useState([]);
  const [importOpen, setImportOpen] = useState(false);
  const [clearBusy, setClearBusy] = useState(false);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const prevScanRunning = useRef(scanRunning);
  const loadLeads = useCallback(
    () =>
      (isApi ? apiRunsApi.getApiRunLeads(runId) : webRunsApi.getRunLeads(runId))
        .then(setLeads)
        .catch(() => {}),
    [isApi, runId],
  );
  usePolling(loadLeads, { enabled: scanRunning, intervalMs: 3000 });
  // Final refresh when the scan stops so the last investigation outcomes appear.
  useEffect(() => {
    if (initialLeadRef) {
      const match = leads.find((lead) => lead.reference === initialLeadRef);
      if (match) setExpanded((previous) => new Set(previous).add(match.id));
    }
  }, [initialLeadRef, leads]);
  useEffect(() => {
    if (prevScanRunning.current && !scanRunning) {
      loadLeads();
    }
    prevScanRunning.current = scanRunning;
  }, [scanRunning, loadLeads]);
  const toggle = (id) =>
    setExpanded((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const onClearAll = async () => {
    if (
      !confirm(
        "Remove all imported leads from this run?\nThe source scans and reports are not affected.",
      )
    )
      return;
    setClearBusy(true);
    setError(null);
    setMsg(null);
    try {
      await (isApi ? apiRunsApi.clearApiRunLeads(runId) : webRunsApi.clearRunLeads(runId));
      setLeads([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setClearBusy(false);
    }
  };
  const onDeleteRow = async (leadId) => {
    setError(null);
    try {
      await (isApi
        ? apiRunsApi.deleteApiRunLead(runId, leadId)
        : webRunsApi.deleteRunLead(runId, leadId));
      setLeads((prev) => prev.filter((l) => l.id !== leadId));
    } catch (e) {
      setError(e.message);
    }
  };
  const sevCls = (s) =>
    ({
      high: "sev-high",
      critical: "sev-high",
      medium: "sev-medium",
      low: "sev-low",
      info: "sev-info",
    })[s] || "sev-medium";
  const statCls = (s) =>
    ({
      open: "neutral",
      investigating: "warning",
      confirmed: "success",
      dismissed: "neutral",
      inconclusive: "neutral",
    })[s] || "neutral";
  return (
    <div className={"findings-panel" + (isApi ? " flush" : "")}>
      {importOpen && (
        <SastImportDialog
          runId={runId}
          runKind={runKind}
          onClose={() => setImportOpen(false)}
          onImported={async (count) => {
            setError(null);
            setMsg(
              count > 0
                ? `Imported ${count} lead${count === 1 ? "" : "s"}.`
                : "Already imported (no new leads).",
            );
            await loadLeads();
          }}
        />
      )}
      <div
        className="findings-status-bar"
        style={{
          flexWrap: "wrap",
        }}
      >
        <span
          className="badge neutral"
          style={{
            fontSize: 12,
          }}
        >
          {leads.length} lead{leads.length !== 1 ? "s" : ""}
        </span>
        {scanRunning && (
          <span
            className="badge warning"
            style={{
              fontSize: 12,
            }}
          >
            Scan running…
          </span>
        )}
        <div
          style={{
            flex: 1,
          }}
        ></div>
        <div
          className="row"
          style={{
            gap: 8,
            flexWrap: "wrap",
            maxWidth: "100%",
          }}
        >
          <button className="btn sm" onClick={() => setImportOpen(true)}>
            Import SAST leads
          </button>
          {leads.length > 0 && (
            <button
              className="btn sm"
              onClick={() =>
                downloadTextFile(
                  leadsExportFilename(`${isApi ? "api" : "web"}-run-${runId}`),
                  leadsToMarkdown(leads, {
                    runName: `${isApi ? "API" : "Web"} run #${runId}`,
                    generatedAt: new Date(),
                  }),
                  "text/markdown;charset=utf-8",
                )
              }
            >
              Export leads
            </button>
          )}
          {leads.length > 0 && (
            <button className="btn danger-outline sm" disabled={clearBusy} onClick={onClearAll}>
              {clearBusy ? "Clearing…" : "Clear all"}
            </button>
          )}
        </div>
      </div>
      <PageError error={error} onDismiss={() => setError(null)} />
      {msg && (
        <Notice variant="success" onDismiss={() => setMsg(null)}>
          {msg}
        </Notice>
      )}
      {leads.length === 0 ? (
        <div
          className="subtle"
          style={{
            padding: 24,
            textAlign: "center",
          }}
        >
          No leads imported into this run yet. Click Import SAST leads to choose a source scan.
        </div>
      ) : (
        <div className="findings-table-wrap">
          <table className="findings-table">
            <thead>
              <tr>
                <th
                  style={{
                    width: 90,
                  }}
                >
                  Severity
                </th>
                <th>Title</th>
                <th
                  style={{
                    width: 90,
                  }}
                >
                  Category
                </th>
                <th
                  style={{
                    width: 90,
                  }}
                >
                  Conf.
                </th>
                <th>Location</th>
                <th
                  style={{
                    width: 110,
                  }}
                >
                  Status
                </th>
                <th
                  style={{
                    width: 70,
                  }}
                ></th>
              </tr>
            </thead>
            <tbody>
              {leads.map((l) => {
                const isExpanded = expanded.has(l.id);
                const investigated = l.status && l.status !== "open";
                return [
                  <tr
                    key={l.id}
                    style={{
                      cursor: "pointer",
                      background: investigated
                        ? "var(--surface, rgba(255,255,255,0.02))"
                        : undefined,
                    }}
                    onClick={() => toggle(l.id)}
                  >
                    <td>
                      <span className={"sev-badge " + sevCls(l.severity)}>
                        {l.severity || "medium"}
                      </span>
                    </td>
                    <td
                      style={{
                        fontWeight: 600,
                      }}
                    >
                      <LeadReferenceLink
                        reference={l.reference}
                        title={l.title}
                        description={l.description}
                        severity={l.severity}
                        href={`#/runs/${runId}/leads?lead=${encodeURIComponent(l.reference || "")}`}
                      />{" "}
                      <span>{l.title}</span>
                    </td>
                    <td>{l.category || "—"}</td>
                    <td>{Math.round((l.confidence || 0) * 100)}%</td>
                    <td
                      className="subtle"
                      style={{
                        fontSize: "0.85em",
                      }}
                    >
                      {l.location || "—"}
                    </td>
                    <td>
                      <span
                        className={"badge " + statCls(l.status)}
                        style={{
                          fontSize: 11,
                        }}
                      >
                        {l.status || "open"}
                      </span>
                    </td>
                    <td
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        justifyContent: "flex-end",
                      }}
                    >
                      <span
                        className="subtle"
                        style={{
                          fontSize: 11,
                        }}
                      >
                        {isExpanded ? "▲" : "▼"}
                      </span>
                      <button
                        className="btn ghost sm"
                        title="Delete lead"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteRow(l.id);
                        }}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>,
                  isExpanded && (
                    <tr key={l.id + "-detail"} className="findings-detail-row">
                      <td
                        colSpan={7}
                        style={{
                          padding: "12px 16px",
                          background: "var(--bg, rgba(0,0,0,0.15))",
                          borderTop: "1px solid var(--border, rgba(255,255,255,0.06))",
                        }}
                      >
                        <SastLeadDetails
                          lead={l}
                          findingHref={`#/${isApi ? "api-runs" : "runs"}/${runId}/findings`}
                        />
                      </td>
                    </tr>
                  ),
                ];
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── WebRunWorkProgramTab ───────────────────────────────────────────────────────
