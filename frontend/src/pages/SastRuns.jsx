import { useState, useEffect, useRef, useCallback } from "react";
import { LeadsPanel } from "./ApiCollections/LeadsPanel";
import { api } from "../lib/api";
import { nav } from "../lib/router";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageHeader, Crumb, Sep } from "../components/PageHeader";
import { usePolling } from "../hooks/usePolling";

// ── SastRunDetail ─────────────────────────────────────────────────────────────

const SAST_TABS = [{
  key: "progress",
  label: "Progress"
}, {
  key: "leads",
  label: "Leads"
}];

// ── SastRunsListPage ──────────────────────────────────────────────────────────
export function SastRunsListPage() {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);
  const load = useCallback(async () => {
    try {
      setRuns(await api.listAllSastRuns());
    } catch (e) {
      setError(e.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const onUpload = async e => {
    const file = e.target.files && e.target.files[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const run = await api.createStandaloneSastRun(file);
      await api.startSastScan(run.id);
      nav(`#/sast-runs/${run.id}/progress`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };
  return <>
    <PageHeader title="SAST Scans" actions={<>
        <input ref={fileInputRef} type="file" accept=".zip" style={{
          display: "none"
        }} onChange={onUpload} />
        <button className="btn primary sm" disabled={uploading} onClick={() => fileInputRef.current && fileInputRef.current.click()}>
          {uploading ? "Uploading…" : "New SAST Scan"}
        </button>
      </>} />
    <div className="content scroll-content">
      {error && <div className="alert error" style={{
        marginBottom: 16
      }}>{error}</div>}
      {runs === null && <div className="subtle">Loading…</div>}
      {runs !== null && runs.length === 0 && <EmptyState icon="🔍"
        title="No SAST scans yet"
        sub={'Click "New SAST Scan" to upload a source ZIP and analyse it. Leads can then be imported into a web or API test run.'} />}
      {runs && runs.length > 0 && <div className="table-wrap">
          <table>
            <colgroup>
              <col style={{
              width: "24%"
            }} /><col style={{
              width: "12%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "18%"
            }} /><col style={{
              width: "18%"
            }} /><col />
            </colgroup>
            <thead><tr><th>Name</th><th>Status</th><th>Leads</th><th>Linked scan</th><th>Started</th><th></th></tr></thead>
            <tbody>{runs.map(r => <tr key={r.id}>
                <td><a href={`#/sast-runs/${r.id}/progress`} style={{
                  fontWeight: 600
                }}>{r.name}</a></td>
                <td><StatusBadge status={r.status} /></td>
                <td>{r.leads_count}</td>
                <td>{r.triggered_by_run_id ? <a href={`#/api-runs/${r.triggered_by_run_id}/status`}>API run #{r.triggered_by_run_id}</a> : <span className="subtle">{r.source_filename || "standalone"}</span>}</td>
                <td>{r.started_at ? new Date(r.started_at).toLocaleString() : <span className="subtle">—</span>}</td>
                <td><a className="btn ghost sm" href={`#/sast-runs/${r.id}/progress`}>View →</a></td>
              </tr>)}
            </tbody>
          </table>
        </div>}
    </div>
  </>;
}
export function SastRunDetail({
  runId,
  initialTab
}) {
  const [run, setRun] = useState(null);
  const [tab, setTab] = useState(initialTab || "progress");
  const [error, setError] = useState(null);
  const [scanRunning, setScanRunning] = useState(false);
  const [startBusy, setStartBusy] = useState(false);
  const loadRun = useCallback(async () => {
    try {
      const r = await api.getSastRun(runId);
      setRun(r);
    } catch (e) {
      setError(e.message);
    }
  }, [runId]);
  const pollStatus = useCallback(async () => {
    try {
      const st = await api.getSastScanStatus(runId);
      setScanRunning(st.running);
      if (!st.running) loadRun();
    } catch {}
  }, [runId, loadRun]);
  useEffect(() => {
    loadRun();
  }, [runId, loadRun]);
  useEffect(() => {
    const t = setInterval(pollStatus, 3000);
    return () => clearInterval(t);
  }, [runId, pollStatus]);
  const onStart = async () => {
    setStartBusy(true);
    setError(null);
    try {
      await api.startSastScan(runId);
      setScanRunning(true);
      loadRun();
    } catch (e) {
      setError(e.message);
    } finally {
      setStartBusy(false);
    }
  };
  const onStop = async () => {
    try {
      await api.stopSastScan(runId);
    } catch (e) {
      setError(e.message);
    }
  };
  const onDelete = async () => {
    if (!confirm("Delete this SAST run and all its leads?")) return;
    try {
      const collId = run?.collection_id;
      await api.deleteSastRun(runId);
      nav(collId ? `#/apis/${collId}/files` : "#/sast-runs");
    } catch (e) {
      setError(e.message);
    }
  };
  
  const canStart = run && !scanRunning && ["pending", "completed", "failed", "cancelled"].includes(run.status);
  return <>
    <PageHeader
      title={<>
        {run && run.collection_id ? <><Crumb href={`#/apis/${run.collection_id}`}>API collection</Crumb><Sep /></> : run ? <><Crumb href="#/sast-runs">SAST</Crumb><Sep /></> : ""}
        {run ? run.name : "…"}
        {run && <> <StatusBadge status={scanRunning ? "scanning" : run.status} /></>}
        {run?.triggered_by_run_id && <>
          <span className="breadcrumb-sep"> · </span>
          <a href={`#/api-runs/${run.triggered_by_run_id}/status`} style={{
            fontSize: 12,
            color: "var(--muted)"
          }}>API Run #{run.triggered_by_run_id}</a></>}
      </>}
      actions={<>
        {canStart && <button className="btn" disabled={startBusy} onClick={onStart}>{startBusy ? "Starting…" : "Start SAST Scan"}</button>}
        {scanRunning && <button className="btn danger-outline" onClick={onStop}>Stop</button>}
        {run && <button className="btn danger-outline" onClick={onDelete}>Delete</button>}
      </>} />
    <div className="tab-bar">
      {SAST_TABS.map(t => <button key={t.key} className={"tab-btn" + (tab === t.key ? " active" : "")} onClick={() => {
        setTab(t.key);
        nav(`#/sast-runs/${runId}/${t.key}`);
      }}>
          {t.label}
        </button>)}
    </div>
    <div className={tab === "progress" ? "content no-padding flex-fill-noscroll" : "content scroll-content"}>
      {error && <div className="alert error">{error}</div>}
      {tab === "progress" && <SastProgressTab runId={runId} scanRunning={scanRunning} />}
      {tab === "leads" && <SastLeadsTab runId={runId} scanRunning={scanRunning} runName={run?.name} />}
    </div>
  </>;
}
export function SastProgressTab({
  runId,
  scanRunning
}) {
  const [log, setLog] = useState([]);
  const [subTab, setSubTab] = useState("activity");
  const bottomRef = useRef(null);
  const load = useCallback(() => {
    const request = subTab === "activity" ? api.getSastScanLog(runId) : api.getSastAgentLog(runId);
    return request.then(setLog).catch(() => {});
  }, [runId, subTab]);

  usePolling(load, { enabled: scanRunning, intervalMs: 3000 });

  // Auto-scroll to bottom while running
  useEffect(() => {
    if (scanRunning && bottomRef.current) {
      bottomRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
      });
    }
  }, [log.length, scanRunning]);

  // Phase → display helpers
  const phaseIcon = phase => {
    if (phase === "sast_extract") return "📦";
    if (phase === "sast_tool") return "🔍";
    if (phase === "sast_candidate") return "⚠️";
    if (phase === "sast_filter") return "🔬";
    if (phase === "sast_complete") return "✅";
    if (phase === "sast_cancelled") return "🛑";
    if (phase === "sast_failed") return "❌";
    return "▸";
  };
  const phaseCls = (phase, status) => {
    if (phase === "sast_candidate") return "phase-warn";
    if (phase === "sast_filter") return status === "running" ? "phase-ok" : "phase-other";
    if (phase === "sast_complete") return "phase-ok";
    if (phase === "sast_failed" || phase === "sast_cancelled") return "phase-danger";
    return "phase-other";
  };
  const statusCls = s => s === "active" ? "phase-probes" : s === "complete" || s === "completed" ? "phase-ok" : "phase-other";
  return <div className="activity-panel" style={{
    margin: 0,
    display: "flex",
    flexDirection: "column",
    height: "100%"
  }}>
    <div className="activity-log-toolbar" style={{
      flexShrink: 0
    }}>
      <div style={{
        display: "flex",
        gap: 4
      }}>
        <button className={"activity-sub-tab-btn" + (subTab === "activity" ? " active" : "")} onClick={() => setSubTab("activity")}>Log</button>
        <button className={"activity-sub-tab-btn" + (subTab === "agents" ? "  active" : "")} onClick={() => setSubTab("agents")}>Agent Activity</button>
      </div>
      <span className="activity-count-label">{log.length} entr{log.length !== 1 ? "ies" : "y"}</span>
      {scanRunning && <span className="activity-mode-badge running">● Scanning</span>}
      <a className="btn ghost sm" href={`/api/sast-runs/${runId}/agent-log/export`} download>Export ↓</a>
    </div>
    <div style={{
      flex: 1,
      overflow: "auto",
      minHeight: 0
    }}>
      {log.length === 0 ? <div className="subtle" style={{
        padding: "24px",
        textAlign: "center"
      }}>
                 {scanRunning ? "SAST scan in progress — activity will appear here shortly." : "No activity yet. Start the scan to begin."}
               </div> : subTab === "activity" ? <div className="activity-feed">
              {log.map(r => {
          const ts = r.created_at ? new Date(r.created_at).toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
          }) : "";
          const icon = phaseIcon(r.phase);
          const cls = phaseCls(r.phase, r.status);
          return <div key={r.id} className="activity-entry">
                  <span className="activity-ts">{ts}</span>
                  <span className={"activity-badge " + cls}>{icon} {r.phase || ""}</span>
                  <span className="activity-msg">{r.message || ""}</span>
                </div>;
        })}
              <div ref={bottomRef} />
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
              <div ref={bottomRef} />
            </div>}
    </div>
  </div>;
}
export function SastLeadsTab({
  runId,
  scanRunning,
  runName
}) {
  const [leads, setLeads] = useState(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback((isInitial = false) => {
    if (isInitial) setLoading(true);
    api.getSastLeads(runId).then(d => {
      setLeads(d);
      if (isInitial) setLoading(false);
    }).catch(() => {
      if (isInitial) setLoading(false);
    });
  }, [runId]);
  useEffect(() => {
    load(true);
  }, [load]);
  useEffect(() => {
    if (!scanRunning) return;
    const t = setInterval(() => load(false), 5000);
    return () => clearInterval(t);
  }, [scanRunning, load]);
  return <LeadsPanel leads={leads} loading={loading} scanRunning={scanRunning} exportName={runName || `sast-run-${runId}`} emptyMsg={scanRunning ? "SAST scan in progress — leads will appear here as they are found." : "No leads yet. Start the SAST scan to analyse the source code."} />;
}

// The directive sent to A.L.I.C.E. when the user clicks "AI Review Issues".
// Shared by the web scan (TestRunDetail) and the API scan (ApiRunFindingsTab) so
// both buttons behave identically.
export const ALICE_DEDUP_DIRECTIVE = "Review all of the findings recorded for this scan and remove duplicates. " + "Use the finding_list context tool to load every finding, then identify the ones that " + "describe the same vulnerability on the same endpoint or target, and remove the duplicates. " + "If multiple findings describe the same underlying issue but with somewhat different details, " + "you can consolidate them into a single finding by re-writing it (write a new issue then delete the " + "superseded ones). Do not run any new HTTP requests, browser actions, or probes — this is a " + "findings cleanup task only. When you finish, briefly summarize the changes made.";
