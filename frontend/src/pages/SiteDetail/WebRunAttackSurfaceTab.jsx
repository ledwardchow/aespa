import { useCallback, useEffect, useState } from "react";
import { usePolling } from "../../hooks/usePolling";
import { api } from "../../lib/api";
import { AttackSurfacePanel } from "./AttackSurfacePanel";

export function WebRunAttackSurfaceTab({ runId, active, scanActive, onTotalChange }) {
  const [summary, setSummary] = useState(null);

  const load = useCallback(async () => {
    const result = await api.getReconSummary(runId);
    setSummary(result);
    onTotalChange(result?.route_count || result?.routes?.length || 0);
  }, [onTotalChange, runId]);

  useEffect(() => {
    setSummary(null);
    onTotalChange(0);
  }, [onTotalChange, runId]);

  const shouldLoad = active || scanActive;
  usePolling(load, {
    enabled: shouldLoad,
    immediate: shouldLoad,
    intervalMs: scanActive ? 4000 : undefined
  });

  return <div style={{ display: active ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}>
    <AttackSurfacePanel summary={summary} />
  </div>;
}
