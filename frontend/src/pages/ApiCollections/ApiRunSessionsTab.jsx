import { useState, useCallback } from "react";
import { api } from "../../lib/api";
import { ScannerSessionsPanel } from "../SiteDetail/ScannerSessionsPanel";
import { usePolling } from "../../hooks/usePolling";

export function ApiRunSessionsTab({
  runId,
  scanRunning
}) {
  const [data, setData] = useState(null);
  const load = useCallback(() => api.getApiScannerSessions(runId).then(setData).catch(() => {}), [runId]);
  usePolling(load, { enabled: scanRunning, intervalMs: 4000 });
  return <ScannerSessionsPanel data={data} refresh={load} onUpdate={(sessionId, b) => api.updateApiScannerSession(runId, sessionId, b)} onValidate={() => api.validateApiScannerSessions(runId)} />;
}
