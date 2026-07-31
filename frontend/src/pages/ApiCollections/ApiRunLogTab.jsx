import { useState, useCallback, useEffect, useRef } from "react";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";

const LOG_PAGE_SIZE = 200;

function mergeLogEntries(current, incoming) {
  const byId = new Map(current.map(entry => [entry.id, entry]));
  for (const entry of incoming) byId.set(entry.id, entry);
  return [...byId.values()].sort((a, b) => a.id - b.id);
}


export function ApiRunLogTab({
  runId,
  scanRunning
}) {
  const [log, setLog] = useState([]);
  const [hasEarlier, setHasEarlier] = useState(false);
  const [loadingEarlier, setLoadingEarlier] = useState(false);
  const [clearBusy, setClearBusy] = useState(false);
  const [error, setError] = useState(null);
  const pageLoadedRef = useRef(false);
  useEffect(() => {
    setLog([]);
    setHasEarlier(false);
    setError(null);
    pageLoadedRef.current = false;
  }, [runId]);
  const load = useCallback(() => api.getApiAgentLogPage(runId, { limit: LOG_PAGE_SIZE }).then(page => {
    setLog(previous => mergeLogEntries(previous, page.entries));
    if (!pageLoadedRef.current && page.entries.length > 0) {
      setHasEarlier(page.hasMore);
      pageLoadedRef.current = true;
    }
  }).catch(e => setError(e.message)), [runId]);
  usePolling(load, { enabled: scanRunning, intervalMs: 4000 });
  const loadEarlier = async () => {
    const firstId = log[0]?.id;
    if (loadingEarlier || firstId == null) return;
    setLoadingEarlier(true);
    setError(null);
    try {
      const page = await api.getApiAgentLogPage(runId, {
        limit: LOG_PAGE_SIZE,
        beforeId: firstId
      });
      setLog(previous => mergeLogEntries(page.entries, previous));
      setHasEarlier(page.hasMore);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingEarlier(false);
    }
  };
  const onClear = async () => {
    if (!confirm("Clear all agent log entries for this run?")) return;
    setClearBusy(true);
    setError(null);
    try {
      await api.clearApiAgentLog(runId);
      setLog([]);
      setHasEarlier(false);
      pageLoadedRef.current = false;
    } catch (e) {
      setError(e.message);
    } finally {
      setClearBusy(false);
    }
  };
  const statusCls = s => s === "active" ? "phase-probes" : s === "complete" || s === "completed" || s === "done" ? "phase-ok" : "phase-other";
  return <div className="activity-panel" style={{
    margin: 0
  }}>
      <div className="activity-log-toolbar">
        <span className="activity-count-label">{log.length}{hasEarlier ? "+" : ""} entr{log.length !== 1 ? "ies" : "y"}</span>
        {scanRunning && <span className="activity-mode-badge">Scan running</span>}
        <a className="btn ghost sm" href={`/api/api-test-runs/${runId}/agent-log/export`} download>Export log ↓</a>
        {log.length > 0 && <button className="btn danger-outline sm" disabled={clearBusy} onClick={onClear}>{clearBusy ? "Clearing…" : "Clear"}</button>}
      </div>
      {error && <div className="alert error" style={{
      margin: "0 16px 8px"
    }}>{error}</div>}
      {log.length === 0 ? <div className="subtle" style={{
      padding: "24px",
      textAlign: "center"
    }}>
                 {scanRunning ? "Scan in progress — agent activity will appear here." : "No agent log entries yet."}
               </div> : <div className="activity-feed">
          {hasEarlier && <div style={{ padding: "4px 16px 10px", textAlign: "center" }}>
            <button className="btn ghost sm" disabled={loadingEarlier} onClick={loadEarlier}>
              {loadingEarlier ? "Loading older entries…" : "Load older entries"}
            </button>
          </div>}
          {log.map(r => {
        const ts = r.created_at ? new Date(r.created_at).toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        }) : "";
        return <div key={r.id} className="activity-entry">
                <span className="activity-ts">{ts}</span>
                <span className={"activity-badge " + statusCls(r.status)}>{(r.status || "").toUpperCase() || "—"}</span>
                <span className="activity-url mono">{r.role} ({r.agent_id})</span>
                <span className="activity-msg">{r.current_task || ""}{r.outcome ? " → " + r.outcome : ""}</span>
              </div>;
      })}
        </div>}
    </div>;
}

// ── ApiRunAgentsTab ────────────────────────────────────────────────────────────
