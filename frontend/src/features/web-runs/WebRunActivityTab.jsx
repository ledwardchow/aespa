import { ActivityAgents } from "./ActivityAgents.jsx";
import { ActivitySpecialists } from "./ActivitySpecialists.jsx";
import { useState } from "react";
import { ActivityLog } from "./ActivityLog.jsx";
import { TokenUsageBar } from "../../shared/ui/TokenUsageBar.jsx";
import { ActivityDeepQueue } from "./ActivityDeepQueue.jsx";

const SPECIALIST_WORKERS = [{ prefix: "specialist-", label: "Specialist" }];
const DEEP_WORKERS = [...SPECIALIST_WORKERS, { prefix: "deep-worker-", label: "Attack worker" }];

export function WebRunActivityTab(props) {
  const {
    activeTab,
    runId,
    run,
    thinkingStatus,
    activityLog,
    agents,
    tokenUsage,
    sitePlanData,
    onClearLog,
    onError,
  } = props;
  const [activitySubTab, setActivitySubTab] = useState("agents");
  const [tokenExpanded, setTokenExpanded] = useState(false);
  const isDeep = run?.coverage_mode === "deep";
  return (
    <>
      <div className="activity-panel">
        {(() => {
          return (
            <>
              <TokenUsageBar
                tokenUsage={tokenUsage}
                tokenExpanded={tokenExpanded}
                setTokenExpanded={setTokenExpanded}
              />
              <div className="activity-sub-tab-bar">
                <button
                  className={
                    "activity-sub-tab-btn" + (activitySubTab === "agents" ? " active" : "")
                  }
                  onClick={() => setActivitySubTab("agents")}
                >
                  Agents
                  {agents.some((a) => a.status === "active") ? " ●" : ""}
                </button>
                <button
                  className={
                    "activity-sub-tab-btn" + (activitySubTab === "workers" ? " active" : "")
                  }
                  onClick={() => setActivitySubTab("workers")}
                >
                  Workers
                  {agents
                    .filter(
                      (a) =>
                        a.id.startsWith("specialist-") ||
                        (isDeep && a.id.startsWith("deep-worker-")),
                    )
                    .some((a) => a.status === "active")
                    ? " ●"
                    : ""}
                </button>
                {isDeep && (
                  <button
                    className={
                      "activity-sub-tab-btn" + (activitySubTab === "deep-queue" ? " active" : "")
                    }
                    onClick={() => setActivitySubTab("deep-queue")}
                  >
                    Work Queue
                  </button>
                )}
                <button
                  className={"activity-sub-tab-btn" + (activitySubTab === "log" ? " active" : "")}
                  onClick={() => setActivitySubTab("log")}
                >
                  Log
                </button>
              </div>
            </>
          );
        })()}
        <div style={{ display: activitySubTab === "log" ? "contents" : "none" }}>
          <ActivityLog
            runId={runId}
            activityLog={activityLog}
            sitePlanData={sitePlanData}
            active={activeTab === "activity" && activitySubTab === "log"}
            onClearLog={onClearLog}
            onError={onError}
          />
        </div>
        {activitySubTab === "workers" && (
          <ActivitySpecialists
            agents={agents}
            workerTypes={isDeep ? DEEP_WORKERS : SPECIALIST_WORKERS}
          />
        )}
        {activitySubTab === "deep-queue" && (
          <ActivityDeepQueue runId={runId} thinkingStatus={thinkingStatus} />
        )}
        {activitySubTab === "agents" && (
          <ActivityAgents
            runId={runId}
            agents={agents}
            run={run}
            thinkingStatus={thinkingStatus}
            activityLog={activityLog}
          />
        )}
      </div>
    </>
  );
}
