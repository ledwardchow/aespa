import { useCallback, useEffect, useState } from "react";
import { usePolling } from "../../hooks/usePolling";
import { api } from "../../lib/api";
import { AttackSurfacePanel, CoverageGapsPanel } from "./AttackSurfacePanel";
import { WebRunIntelligenceTab } from "./WebRunIntelligenceTab";
import { WebRunWorkProgramTab } from "./WebRunWorkProgramTab";

export function WebRunAttackSurfaceTab({
  runId,
  run,
  active,
  scanActive,
  onTotalChange,
  intelligenceTotal,
  onIntelligenceTotalChange,
  intelligenceCaptureActive,
  reloadKey = 0,
  initialSubTab = "owasp"
}) {
  const [summary, setSummary] = useState(null);
  const [subTab, setSubTab] = useState(initialSubTab);

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

  return <div className="web-run-coverage-tab" style={{ display: active ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}>
    <div className="activity-sub-tab-bar coverage-sub-tab-bar">
      <button className={"activity-sub-tab-btn coverage-sub-tab-btn" + (subTab === "owasp" ? " active" : "")} onClick={() => setSubTab("owasp")}>OWASP</button>
      <button className={"activity-sub-tab-btn coverage-sub-tab-btn" + (subTab === "attack-surface" ? " active" : "")} onClick={() => setSubTab("attack-surface")}>Attack Surface</button>
      <button className={"activity-sub-tab-btn coverage-sub-tab-btn" + (subTab === "intelligence" ? " active" : "")} onClick={() => setSubTab("intelligence")}>
        Intelligence{intelligenceTotal > 0 ? <span className="traffic-count">{intelligenceTotal}</span> : null}
      </button>
    </div>
    {subTab === "owasp" ? <div className="coverage-owasp-content">
      <CoverageGapsPanel summary={summary} />
      <div className="coverage-workprogram-wrap">
        <WebRunWorkProgramTab runId={runId} run={run} reloadKey={reloadKey} scanRunning={scanActive || run?.status === "crawling" || run?.status === "crawled"} />
      </div>
    </div> : subTab === "attack-surface" ? <AttackSurfacePanel summary={summary} /> : null}
    <WebRunIntelligenceTab
      runId={runId}
      active={active && subTab === "intelligence"}
      captureActive={intelligenceCaptureActive}
      onTotalChange={onIntelligenceTotalChange}
    />
  </div>;
}
