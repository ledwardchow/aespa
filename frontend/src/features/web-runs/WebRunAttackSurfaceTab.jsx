import * as webRunsApi from "../../shared/api/webRuns.js";
import { useCallback, useEffect, useState } from "react";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { useHashTab } from "../../shared/navigation/useHashTab.js";

import { AttackSurfacePanel, CoverageGapsPanel } from "./AttackSurfacePanel.jsx";
import { WebRunIntelligenceTab } from "./WebRunIntelligenceTab.jsx";
import { WebRunWorkProgramTab } from "./WebRunWorkProgramTab.jsx";
import { groupWorkflowNotes, WebRunWorkflowsTab } from "./WebRunWorkflowsTab.jsx";

export function WebRunAttackSurfaceTab({
  runId,
  workflowFocus,
  onWorkflowNotesChange,
  onWorkflowRetryStatusChange,
  onOpenWorkflowNotification,
  run,
  active,
  scanActive,
  onTotalChange,
  intelligenceTotal,
  onIntelligenceTotalChange,
  intelligenceCaptureActive,
  reloadKey = 0,
  initialSubTab = "owasp",
}) {
  const [summary, setSummary] = useState(null);
  const [subTab, setSubTab] = useHashTab(
    "subtab",
    ["owasp", "attack-surface", "workflows", "intelligence"],
    initialSubTab,
  );
  const workflowCount = groupWorkflowNotes(summary?.crawl_notes || []).length;

  useEffect(() => {
    if (workflowFocus?.sequence) setSubTab("workflows");
  }, [workflowFocus?.sequence, setSubTab]);

  const load = useCallback(async () => {
    const result = await webRunsApi.getReconSummary(runId);
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
    intervalMs: scanActive ? 4000 : undefined,
  });

  return (
    <div
      className="web-run-coverage-tab"
      style={{ display: active ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}
    >
      <div className="activity-sub-tab-bar coverage-sub-tab-bar">
        <button
          className={
            "activity-sub-tab-btn coverage-sub-tab-btn" + (subTab === "owasp" ? " active" : "")
          }
          onClick={() => setSubTab("owasp")}
        >
          OWASP
        </button>
        <button
          className={
            "activity-sub-tab-btn coverage-sub-tab-btn" +
            (subTab === "attack-surface" ? " active" : "")
          }
          onClick={() => setSubTab("attack-surface")}
        >
          Attack Surface
        </button>
        <button
          className={
            "activity-sub-tab-btn coverage-sub-tab-btn" + (subTab === "workflows" ? " active" : "")
          }
          onClick={() => setSubTab("workflows")}
        >
          Workflows
          {workflowCount > 0 ? <span className="traffic-count">{workflowCount}</span> : null}
        </button>
        <button
          className={
            "activity-sub-tab-btn coverage-sub-tab-btn" +
            (subTab === "intelligence" ? " active" : "")
          }
          onClick={() => setSubTab("intelligence")}
        >
          Intelligence
          {intelligenceTotal > 0 ? (
            <span className="traffic-count">{intelligenceTotal}</span>
          ) : null}
        </button>
      </div>
      {subTab === "owasp" ? (
        <div className="coverage-owasp-content">
          <div className="coverage-workprogram-wrap">
            <WebRunWorkProgramTab
              runId={runId}
              run={run}
              pagesProgress={<CoverageGapsPanel summary={summary} />}
              reloadKey={reloadKey}
              scanRunning={scanActive || run?.status === "crawling" || run?.status === "crawled"}
            />
          </div>
        </div>
      ) : subTab === "attack-surface" ? (
        <AttackSurfacePanel
          summary={summary}
          routeGroups={summary?.route_groups || run?.route_groups}
        />
      ) : subTab === "workflows" ? (
        <WebRunWorkflowsTab
          runId={runId}
          summary={summary}
          focusedNoteId={workflowFocus?.noteId}
          focusSequence={workflowFocus?.sequence}
          onNotesChange={onWorkflowNotesChange}
          onRetryStatusChange={onWorkflowRetryStatusChange}
          onRetryFinished={load}
          onOpenNotification={onOpenWorkflowNotification}
        />
      ) : null}
      <WebRunIntelligenceTab
        runId={runId}
        active={active && subTab === "intelligence"}
        captureActive={intelligenceCaptureActive}
        onTotalChange={onIntelligenceTotalChange}
      />
    </div>
  );
}
