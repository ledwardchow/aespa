import { ActivityAgents } from "./ActivityAgents.jsx";
import { ActivitySpecialists } from "./ActivitySpecialists.jsx";
import { useEffect } from "react";
import { ActivityLog } from "./ActivityLog.jsx";
import { ActivityDeepQueue } from "./ActivityDeepQueue.jsx";
import { WebRunNotificationsTab } from "./WebRunNotificationsTab.jsx";
import { useHashTab } from "../../shared/navigation/useHashTab.js";

const SPECIALIST_WORKERS = [{ prefix: "specialist-", label: "Specialist" }];

export function WebRunActivityTab(props) {
  const {
    activeTab,
    runId,
    notificationFocus,
    focusedNotificationId,
    workflowNotificationCount,
    onWorkflowNotesChange,
    onWorkflowRetryStatusChange,
    onViewWorkflow,
    run,
    thinkingStatus,
    activityLog,
    agents,
    sitePlanData,
    onClearLog,
    onError,
  } = props;
  const [activitySubTab, setActivitySubTab] = useHashTab(
    "subtab",
    ["agents", "workers", "deep-queue", "notifications", "log"],
    "agents",
  );
  const isDeep = run?.coverage_mode === "deep";
  useEffect(() => {
    if (isDeep && activitySubTab === "workers") setActivitySubTab("deep-queue");
  }, [activitySubTab, isDeep, setActivitySubTab]);
  useEffect(() => {
    if (notificationFocus) setActivitySubTab("notifications");
  }, [notificationFocus, setActivitySubTab]);
  return (
    <>
      <div className="activity-panel">
        {(() => {
          return (
            <>
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
                {!isDeep && (
                  <button
                    className={
                      "activity-sub-tab-btn" + (activitySubTab === "workers" ? " active" : "")
                    }
                    onClick={() => setActivitySubTab("workers")}
                  >
                    Workers
                    {agents
                      .filter((a) => a.id.startsWith("specialist-"))
                      .some((a) => a.status === "active")
                      ? " ●"
                      : ""}
                  </button>
                )}
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
                  className={
                    "activity-sub-tab-btn" + (activitySubTab === "notifications" ? " active" : "")
                  }
                  onClick={() => setActivitySubTab("notifications")}
                >
                  Notifications
                  {workflowNotificationCount > 0 && (
                    <span className="workflow-notification-badge" aria-hidden="true">
                      {workflowNotificationCount}
                    </span>
                  )}
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
        {activitySubTab === "workers" && (
          <ActivitySpecialists agents={agents} workerTypes={SPECIALIST_WORKERS} />
        )}
        {activitySubTab === "deep-queue" && (
          <ActivityDeepQueue runId={runId} thinkingStatus={thinkingStatus} agents={agents} />
        )}
        {activitySubTab === "notifications" && (
          <WebRunNotificationsTab
            runId={runId}
            onNotesChange={onWorkflowNotesChange}
            onRetryStatusChange={onWorkflowRetryStatusChange}
            onViewWorkflow={onViewWorkflow}
            focusedNoteId={focusedNotificationId}
            focusSequence={notificationFocus}
          />
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
