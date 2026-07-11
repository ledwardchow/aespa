import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";
import { TaskGraphPanel } from "./TaskGraphPanel";

const taskCount = data => data?.counts?.tasks || 0;

/** Owns task-graph data and mutations while exposing only the tab badge to the run page. */
export function WebRunTasksTab({ runId, active, scanActive, reloadKey, onTotalChange }) {
  const [data, setData] = useState(null);
  const [reconSummary, setReconSummary] = useState(null);
  const [subTab, setSubTab] = useState("attack-surface");
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState(null);

  const loadGraph = useCallback(async () => {
    const result = await api.getTaskGraph(runId);
    setData(result);
    onTotalChange(taskCount(result));
  }, [onTotalChange, runId]);

  useEffect(() => {
    setData(null);
    setReconSummary(null);
    setSubTab("attack-surface");
    setError(null);
    onTotalChange(0);
  }, [onTotalChange, runId]);

  const shouldLoad = active || scanActive;
  usePolling(loadGraph, {
    enabled: shouldLoad,
    immediate: shouldLoad,
    intervalMs: scanActive ? 4000 : undefined
  });

  useEffect(() => {
    if (!reloadKey) return;
    void loadGraph().catch(() => {});
  }, [loadGraph, reloadKey]);

  useEffect(() => {
    if (!shouldLoad) return;
    api.getReconSummary(runId).then(setReconSummary).catch(() => {});
  }, [runId, shouldLoad]);

  const seed = useCallback(async () => {
    setError(null);
    try {
      const result = await api.seedTaskGraph(runId);
      setData(result);
      onTotalChange(taskCount(result));
    } catch (seedError) {
      setError(seedError.message);
    }
  }, [onTotalChange, runId]);

  const clear = useCallback(async () => {
    if (!confirm("Clear all hypotheses and tasks for this run?")) return;
    setClearing(true);
    setError(null);
    try {
      await api.clearTaskGraph(runId);
      setData(null);
      onTotalChange(0);
    } catch (clearError) {
      setError(clearError.message);
    } finally {
      setClearing(false);
    }
  }, [onTotalChange, runId]);

  return <div style={{ display: active ? undefined : "none" }}>
    {error && <div className="alert error">{error}</div>}
    <TaskGraphPanel
      data={data}
      reconSummary={reconSummary}
      subTab={subTab}
      onSubTab={setSubTab}
      refresh={() => void loadGraph().catch(() => {})}
      seed={seed}
      onClear={clear}
      clearing={clearing}
    />
  </div>;
}
