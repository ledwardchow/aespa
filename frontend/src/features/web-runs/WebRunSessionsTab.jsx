import * as webRunsApi from "../../shared/api/webRuns.js";
import { useCallback, useEffect, useState } from "react";

import { usePolling } from "../../shared/hooks/usePolling.js";
import { ScannerSessionsPanel } from "../../shared/sessions/ScannerSessionsPanel.jsx";

/** Keeps web-run scanner-session polling and the tab badge outside the run detail page. */
export function WebRunSessionsTab({ runId, active, scanActive, onTotalChange }) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => {
    const result = await webRunsApi.getScannerSessions(runId);
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
    intervalMs: scanActive ? 4000 : undefined,
  });

  return (
    <div
      style={{ display: active ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}
    >
      <ScannerSessionsPanel
        data={data}
        refresh={() => void load().catch(() => {})}
        onUpdate={(sessionId, update) => webRunsApi.updateScannerSession(runId, sessionId, update)}
        onValidate={() => webRunsApi.validateScannerSessions(runId)}
      />
    </div>
  );
}
