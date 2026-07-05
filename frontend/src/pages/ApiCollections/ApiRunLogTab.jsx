import { useState, useEffect, useCallback, useContext } from "react";
import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { IconSites, IconApis, IconSettings, IconPlus, IconCheck, IconPlay, IconStop, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconMessageSquare, IconSend, IconBrain } from "../../components/Icons";


export function ApiRunLogTab({
  runId,
  scanRunning
}) {
  const [log, setLog] = useState([]);
  const [clearBusy, setClearBusy] = useState(false);
  const [error, setError] = useState(null);
  const load = () => api.getApiAgentLog(runId).then(setLog).catch(e => setError(e.message));
  useEffect(() => {
    load();
  }, [runId]);
  useEffect(() => {
    if (!scanRunning) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [scanRunning, runId]);
  const onClear = async () => {
    if (!confirm("Clear all agent log entries for this run?")) return;
    setClearBusy(true);
    setError(null);
    try {
      await api.clearApiAgentLog(runId);
      setLog([]);
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
        <span className="activity-count-label">{log.length} entr{log.length !== 1 ? "ies" : "y"}</span>
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

