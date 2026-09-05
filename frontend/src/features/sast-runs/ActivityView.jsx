import { useState } from "react";

import { TokenUsageBar } from "../../shared/ui/TokenUsageBar.jsx";

export function formatTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function ActivityView({
  logs,
  agentLog,
  scanRunning,
  tokenUsage,
  tokenExpanded,
  setTokenExpanded,
  runId,
}) {
  const [subTab, setSubTab] = useState("log");
  const entries = subTab === "log" ? logs : agentLog;
  return (
    <div className="sast-activity-panel">
      <TokenUsageBar
        tokenUsage={tokenUsage}
        tokenExpanded={tokenExpanded}
        setTokenExpanded={setTokenExpanded}
      />
      <div className="sast-activity-toolbar">
        <div className="sast-activity-tabs">
          <button className={subTab === "log" ? "active" : ""} onClick={() => setSubTab("log")}>
            Phase log
          </button>
          <button
            className={subTab === "agents" ? "active" : ""}
            onClick={() => setSubTab("agents")}
          >
            Agent activity
          </button>
        </div>
        <span className="subtle">{entries.length} entries</span>
        {scanRunning && <span className="activity-mode-badge running">● Scanning</span>}
        <a className="btn ghost sm" href={`/api/sast-runs/${runId}/agent-log/export`} download>
          Export ↓
        </a>
      </div>
      {!entries.length ? (
        <div className="sast-empty-state">No activity has been recorded yet.</div>
      ) : (
        <div className="sast-activity-feed">
          {entries.map((item) => (
            <div className="sast-activity-entry" key={item.id}>
              <time>{formatTime(item.created_at)}</time>
              <span className="sast-activity-phase">
                {subTab === "log" ? item.phase || "event" : item.status || "event"}
              </span>
              <span className="sast-activity-message">
                {subTab === "log"
                  ? item.message
                  : `${item.role || "Agent"}: ${item.current_task || ""}${item.outcome ? ` → ${item.outcome}` : ""}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
