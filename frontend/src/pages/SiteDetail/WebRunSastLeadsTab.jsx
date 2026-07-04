import { useState, useEffect, useCallback, useContext } from "react";
import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { fmtDate, sourceLabel, markdownText, markdownCodeBlock, leadImportPayload, leadsExportFilename, leadsToMarkdown, downloadTextFile, WP_STATUS_MARK, findingImportPayload, parseFindingsMarkdownSections, markdownSection } from "../../lib/utilities";
import * as d3 from "d3";

export function WebRunSastLeadsTab({
  runId,
  scanRunning
}) {
  const [available, setAvailable] = useState([]);
  const [leads, setLeads] = useState([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [clearBusy, setClearBusy] = useState(false);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const loadLeads = useCallback(() => api.getRunLeads(runId).then(setLeads).catch(() => {}), [runId]);
  const loadAvailable = useCallback(() => api.getRunAvailableSastRuns(runId).then(setAvailable).catch(() => {}), [runId]);
  useEffect(() => {
    loadLeads();
    loadAvailable();
  }, [loadLeads, loadAvailable]);
  // Refresh while a dynamic scan runs so investigation outcomes show live.
  useEffect(() => {
    if (!scanRunning) return;
    const t = setInterval(loadLeads, 6000);
    return () => clearInterval(t);
  }, [scanRunning, loadLeads]);
  const onImport = async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const r = await api.importSastLeads(runId, {
        sast_run_id: +selected
      });
      setMsg(r.imported > 0 ? `Imported ${r.imported} lead(s).` : "Already imported (no new leads).");
      await loadLeads();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const onClearAll = async () => {
    if (!confirm("Remove all imported SAST leads from this run?\nThe original SAST scan is not affected.")) return;
    setClearBusy(true);
    setError(null);
    setMsg(null);
    try {
      await api.clearRunLeads(runId);
      setLeads([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setClearBusy(false);
    }
  };
  const onDeleteRow = async leadId => {
    setError(null);
    try {
      await api.deleteRunLead(runId, leadId);
      setLeads(prev => prev.filter(l => l.id !== leadId));
    } catch (e) {
      setError(e.message);
    }
  };
  const sevCls = s => ({
    high: "sev-high",
    critical: "sev-high",
    medium: "sev-medium",
    low: "sev-low",
    info: "sev-info"
  })[s] || "sev-medium";
  const statCls = s => ({
    open: "neutral",
    investigating: "warning",
    confirmed: "success",
    dismissed: "neutral",
    inconclusive: "neutral"
  })[s] || "neutral";
  return <div className="findings-panel">
      <div className="findings-status-bar">
        <span className="badge neutral" style={{
        fontSize: 12
      }}>{leads.length} lead{leads.length !== 1 ? "s" : ""}</span>
        {scanRunning && <span className="badge warning" style={{
        fontSize: 12
      }}>Scan running…</span>}
        <div style={{
        flex: 1
      }}></div>
        <div className="row" style={{
        gap: 8
      }}>
          <select value={selected} onChange={e => setSelected(e.target.value)} style={{
          minWidth: 240
        }}>
            <option value="">Import from SAST scan…</option>
            {available.map(r => <option key={r.id} value={r.id}>
              {r.name} ({r.leads_count} lead{r.leads_count === 1 ? "" : "s"})
            </option>)}
          </select>
          <button className="btn sm" disabled={!selected || busy} onClick={onImport}>
            {busy ? "Importing…" : "Import leads"}
          </button>
          {leads.length > 0 && <button className="btn sm" onClick={() => downloadTextFile(leadsExportFilename(`web-run-${runId}`), leadsToMarkdown(leads, {
          runName: `Web run #${runId}`,
          generatedAt: new Date()
        }), "text/markdown;charset=utf-8")}>Export leads</button>}
          {leads.length > 0 && <button className="btn danger-outline sm" disabled={clearBusy} onClick={onClearAll}>
              {clearBusy ? "Clearing…" : "Clear all"}
            </button>}
        </div>
      </div>
      {error && <div className="alert error" style={{
      margin: "8px 16px"
    }}>{error}</div>}
      {msg && <div className="subtle" style={{
      margin: "8px 16px"
    }}>{msg}</div>}
      {leads.length === 0 ? <div className="subtle" style={{
      padding: 24,
      textAlign: "center"
    }}>
            {available.length === 0 ? "No completed SAST scans with leads yet. Run one from the SAST tab, then import its leads here." : "No leads imported into this run yet. Pick a SAST scan above and click Import leads."}
          </div> : <div className="findings-table-wrap">
            <table className="findings-table">
              <thead><tr>
                <th style={{
              width: 90
            }}>Severity</th>
                <th>Title</th>
                <th style={{
              width: 90
            }}>Category</th>
                <th style={{
              width: 90
            }}>Conf.</th>
                <th>Location</th>
                <th style={{
              width: 110
            }}>Status</th>
                <th style={{
              width: 44
            }}></th>
              </tr></thead>
              <tbody>{leads.map(l => <tr key={l.id}>
                  <td><span className={"sev-badge " + sevCls(l.severity)}>{l.severity || "medium"}</span></td>
                  <td style={{
              fontWeight: 600
            }}>{l.title}</td>
                  <td>{l.category || "—"}</td>
                  <td>{Math.round((l.confidence || 0) * 100)}%</td>
                  <td className="subtle" style={{
              fontSize: "0.85em"
            }}>{l.location || "—"}</td>
                  <td><span className={"badge " + statCls(l.status)} style={{
                fontSize: 11
              }}>{l.status || "open"}</span></td>
                  <td>
                    <button className="btn ghost sm" title="Delete lead" onClick={() => onDeleteRow(l.id)}>✕</button>
                  </td>
                </tr>)}
              </tbody>
            </table>
          </div>}
    </div>;
}

// ── WebRunWorkProgramTab ───────────────────────────────────────────────────────

export const OWASP_WEB_CATEGORIES = ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10"];
