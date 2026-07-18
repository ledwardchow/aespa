import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";
import { ScannerSessionsPanel } from "./ScannerSessionsPanel";

/** Keeps web-run scanner-session polling and the tab badge outside the run detail page. */
export function WebRunSessionsTab({ runId, active, scanActive, onTotalChange }) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => {
    const result = await api.getScannerSessions(runId);
    setData(result);
    onTotalChange(result?.counts?.total || 0);
  }, [onTotalChange, runId]);

  useEffect(() => {
    setData(null);
    onTotalChange(0);
  }, [onTotalChange, runId]);

  const shouldLoad = active || scanActive;
  usePolling(load, {
    enabled: shouldLoad,
    immediate: shouldLoad,
    intervalMs: scanActive ? 4000 : undefined
  });

  return <div style={{ display: active ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}>
    <ScannerSessionsPanel
      data={data}
      refresh={() => void load().catch(() => {})}
      onUpdate={(sessionId, update) => api.updateScannerSession(runId, sessionId, update)}
      onValidate={() => api.validateScannerSessions(runId)}
    />
  </div>;
}
