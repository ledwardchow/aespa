import * as apiRunsApi from "../../shared/api/apiRuns.js";
import { useState, useCallback } from "react";

import { ScannerSessionsPanel } from "../../shared/sessions/ScannerSessionsPanel.jsx";
import { usePolling } from "../../shared/hooks/usePolling.js";

export function ApiRunSessionsTab({ runId, scanRunning }) {
  const [data, setData] = useState(null);
  const load = useCallback(
    () =>
      apiRunsApi
        .getApiScannerSessions(runId)
        .then(setData)
        .catch(() => {}),
    [runId],
  );
  usePolling(load, { enabled: scanRunning, intervalMs: 4000 });
  return (
    <ScannerSessionsPanel
      data={data}
      refresh={load}
      onUpdate={(sessionId, b) => apiRunsApi.updateApiScannerSession(runId, sessionId, b)}
      onValidate={() => apiRunsApi.validateApiScannerSessions(runId)}
    />
  );
}
