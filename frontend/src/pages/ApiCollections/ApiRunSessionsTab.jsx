import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { ScannerSessionsPanel } from "../SiteDetail/ScannerSessionsPanel";

export function ApiRunSessionsTab({
  runId,
  scanRunning
}) {
  const [data, setData] = useState(null);
  const load = () => api.getApiScannerSessions(runId).then(setData).catch(() => {});
  useEffect(() => {
    load();
  }, [runId]);
  useEffect(() => {
    if (!scanRunning) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [scanRunning, runId]);
  return <ScannerSessionsPanel runId={runId} data={data} refresh={load} updateSession={(sessionId, b) => api.updateApiScannerSession(runId, sessionId, b).then(load)} />;
}
