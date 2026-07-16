import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { StatusBadge } from "../../components/StatusBadge";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { ApiRunStatusTab } from "./ApiRunStatusTab";
import { ApiRunFindingsTab } from "./ApiRunFindingsTab";
import { ApiRunLeadsTab } from "./ApiRunLeadsTab";
import { ApiRunSessionsTab } from "./ApiRunSessionsTab";
import { ApiRunTrafficTab } from "./ApiRunTrafficTab";
import { ApiRunEndpointsTab } from "./ApiRunEndpointsTab";
import { ApiRunWorkProgramTab } from "./ApiRunWorkProgramTab";

const API_RUN_TABS = [{
  key: "status",
  label: "Status"
}, {
  key: "findings",
  label: "Findings"
}, {
  key: "leads",
  label: "SAST Leads"
}, {
  key: "sessions",
  label: "Sessions"
}, {
  key: "traffic",
  label: "Traffic Log"
}, {
  key: "endpoints",
  label: "Endpoints"
}, {
  key: "workprogram",
  label: "OWASP Coverage"
}];

// Reuse the same alice session management infrastructure as TestRunDetail but
// bound to the /api/api-test-runs/{id}/* alias routes.
export function useApiAliceSession(runId) {
  const [aliceSessions, setAliceSessions] = useState(null);
  const [aliceLoaded, setAliceLoaded] = useState(false);
  const [activeTabId, setActiveTabId] = useState("tab-default");
  const [aliceStatus, setAliceStatus] = useState(null);
  const streamRef = useRef(null);
  const cursorRef = useRef(0);
  const loadSessions = useCallback(async () => {
    try {
      const data = await api.getApiAliceSessions(runId);
      setAliceSessions(data.chats || []);
      setActiveTabId(data.active_tab_id || "tab-default");
      setAliceLoaded(true);
    } catch (e) {
      console.error("alice sessions load error", e);
      setAliceLoaded(true);
    }
  }, [runId]);
  const saveSessions = useCallback(async (chats, activeId) => {
    try {
      await api.saveApiAliceSessions(runId, {
        chats,
        active_tab_id: activeId
      });
    } catch (e) {
      console.error("alice sessions save error", e);
    }
  }, [runId]);
  const pollStatus = useCallback(async () => {
    try {
      const st = await api.getApiAliceStatus(runId);
      setAliceStatus(st);
    } catch {}
  }, [runId]);
  return {
    aliceSessions,
    setAliceSessions,
    aliceLoaded,
    activeTabId,
    setActiveTabId,
    aliceStatus,
    setAliceStatus,
    loadSessions,
    saveSessions,
    pollStatus,
    streamRef,
    cursorRef
  };
}
export function ApiTestRunDetail({
  runId,
  initialTab
}) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [scanStatus, setScanStatus] = useState(null);
  const [scanBusy, setScanBusy] = useState(false);
  const [coverageMode, setCoverageMode] = useState("track");
  const tab = initialTab || "status";
  useEffect(() => {
    api.getApiRun(runId).then(r => {
      setRun(r);
      setCoverageMode(r.coverage_mode || "track");
    }).catch(e => setError(e.message));
    api.getApiScanStatus(runId).then(setScanStatus).catch(() => {});
  }, [runId]);

  // Poll scan status while scanning.
  useEffect(() => {
    if (!scanStatus?.running) return;
    const t = setInterval(() => {
      api.getApiScanStatus(runId).then(st => {
        setScanStatus(st);
        if (!st.running) api.getApiRun(runId).then(setRun).catch(() => {});
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [scanStatus?.running, runId]);
  const onStartScan = async () => {
    setScanBusy(true);
    try {
      await api.startApiScan(runId, coverageMode);
      const st = await api.getApiScanStatus(runId);
      setScanStatus(st);
      api.getApiRun(runId).then(r => {
        setRun(r);
        setCoverageMode(r.coverage_mode || "track");
      }).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setScanBusy(false);
    }
  };
  const onStopScan = async () => {
    setScanBusy(true);
    try {
      await api.stopApiScan(runId);
      const st = await api.getApiScanStatus(runId);
      setScanStatus(st);
      api.getApiRun(runId).then(setRun).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setScanBusy(false);
    }
  };
  const onDelete = async () => {
    if (!run) return;
    if (!confirm(`Delete test run "${run.name}"?`)) return;
    try {
      await api.deleteApiRun(runId);
      nav(`#/apis/${run.collection_id}`);
    } catch (e) {
      setError(e.message);
    }
  };
  const scanRunning = scanStatus?.running === true;
  if (!run) {
    return <div className="content scroll-content">{error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}</div>;
  }
  return <>
    <PageHeader
      title={<>
        <Crumb href={run ? `#/apis/${run.collection_id}` : "#/apis"}>API collection</Crumb>
        <Sep />
        {run ? run.name : "…"}
        {run && <> <StatusBadge status={run.status} /></>}
      </>}
      actions={<>
        {scanRunning ? <button className="btn danger-outline" disabled={scanBusy} onClick={onStopScan}>
                   {scanBusy ? "Stopping…" : "Stop Scan"}
                 </button> : <>
            <label className="subtle" style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12
          }} title="Track: observe coverage as the scan runs. Enforce: drive every applicable endpoint × category to covered or skipped-with-reason.">
              Coverage:
              <select value={coverageMode} disabled={scanBusy} onChange={e => setCoverageMode(e.target.value)}>
                <option value="track">Track</option>
                <option value="enforce">Enforce</option>
              </select>
            </label>
            <button className="btn" disabled={scanBusy} onClick={onStartScan}>
              {scanBusy ? "Starting…" : "Start Scan"}
            </button></>}
        {run && <button className="btn danger-outline" onClick={onDelete}>Delete</button>}
      </>} />
    <div className="tab-bar">
      {API_RUN_TABS.map(t => <button key={t.key} className={"tab-btn" + (tab === t.key ? " active" : "")} onClick={() => nav(`#/api-runs/${runId}/${t.key}`)}>{t.label}</button>)}
    </div>
    <div className={"content no-padding" + (tab === "status" ? " flex-fill-noscroll" : " scroll-content")}>
      {error && <div className="alert error">{error}</div>}
      {tab === "status" && <ApiRunStatusTab runId={runId} scanRunning={scanRunning} />}
      {tab === "findings" && <ApiRunFindingsTab runId={runId} scanRunning={scanRunning} run={run} />}
      {tab === "leads" && <ApiRunLeadsTab runId={runId} scanRunning={scanRunning} />}
      {tab === "sessions" && <ApiRunSessionsTab runId={runId} scanRunning={scanRunning} />}
      {tab === "traffic" && <ApiRunTrafficTab runId={runId} scanRunning={scanRunning} />}
      {tab === "endpoints" && <ApiRunEndpointsTab run={run} />}
      {tab === "workprogram" && <ApiRunWorkProgramTab runId={runId} scanRunning={scanRunning} run={run} />}
    </div>
  </>;
}
