import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";
import { TargetIntelligencePanel } from "./TargetIntelligencePanel";

const totalItems = data => Object.values(data?.counts || {}).reduce((total, count) => total + count, 0);

/**
 * Keeps target-intelligence state and live crawl updates local to its tab.
 * It remains mounted while a crawl runs so the tab badge stays current.
 */
export function WebRunIntelligenceTab({ runId, active, captureActive, onTotalChange }) {
  const [data, setData] = useState(null);
  const [selectedKind, setSelectedKind] = useState("");
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState(null);

  const loadIntel = useCallback(async () => {
    const result = await api.getTargetIntelligence(runId, selectedKind);
    setData(result);
    onTotalChange(totalItems(result));
  }, [onTotalChange, runId, selectedKind]);

  useEffect(() => {
    setData(null);
    setSelectedKind("");
    setError(null);
    onTotalChange(0);
  }, [onTotalChange, runId]);

  const shouldLoad = active || captureActive;
  usePolling(loadIntel, {
    enabled: shouldLoad,
    immediate: shouldLoad,
    intervalMs: captureActive ? 4000 : undefined
  });

  const clear = useCallback(async () => {
    if (!confirm("Clear all target intelligence for this run?")) return;
    setClearing(true);
    setError(null);
    try {
      await api.clearTargetIntel(runId);
      setData(null);
      setSelectedKind("");
      onTotalChange(0);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setClearing(false);
    }
  }, [onTotalChange, runId]);

  return <div style={{ display: active ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}>
    {error && <div className="alert error">{error}</div>}
    <TargetIntelligencePanel
      data={data}
      selectedKind={selectedKind}
      onKind={setSelectedKind}
      refresh={() => void loadIntel().catch(() => {})}
      onClear={clear}
      clearing={clearing}
    />
  </div>;
}
