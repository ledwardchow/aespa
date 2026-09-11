import { ActivityAgents } from "./ActivityAgents.jsx";
import { ActivitySpecialists } from "./ActivitySpecialists.jsx";
import { useState } from "react";
import { ActivityLog } from "./ActivityLog.jsx";
import { TokenUsageBar } from "../../shared/ui/TokenUsageBar.jsx";

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
                    "activity-sub-tab-btn" + (activitySubTab === "specialists" ? " active" : "")
                  }
                  onClick={() => setActivitySubTab("specialists")}
                >
                  Specialist
                  {agents
                    .filter((a) => a.id.startsWith("specialist-"))
                    .some((a) => a.status === "active")
                    ? " ●"
                    : ""}
                </button>
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
        {activitySubTab === "specialists" && <ActivitySpecialists agents={agents} />}
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
