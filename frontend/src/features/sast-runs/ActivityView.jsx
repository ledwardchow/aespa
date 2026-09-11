import { useState } from "react";

import { TokenUsageBar } from "../../shared/ui/TokenUsageBar.jsx";
import { SastAgentGroupView, SastAgentRoster } from "./SastAgentRoster.jsx";
import { sastGroupHasActiveAgent } from "./sastAgentPresentation.js";

const GROUP_TABS = [
  { key: "injection", label: "Injection", groupId: "sast-injection-workers" },
  { key: "access", label: "Access", groupId: "sast-access-workers" },
  { key: "logic", label: "Logic", groupId: "sast-logic-workers" },
  { key: "sink", label: "Sink", groupId: "sast-sink-workers" },
  { key: "validator", label: "Validators", groupId: "sast-validators" },
];

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
  analysisMode,
}) {
  const [subTab, setSubTab] = useState("agents");
  const selectedGroup = GROUP_TABS.find((item) => item.key === subTab);
  return (
    <div className="sast-activity-panel">
      <TokenUsageBar
        tokenUsage={tokenUsage}
        tokenExpanded={tokenExpanded}
        setTokenExpanded={setTokenExpanded}
      />
      <div className="sast-activity-toolbar">
        <div className="sast-activity-tabs">
          <button
            className={subTab === "agents" ? "active" : ""}
            onClick={() => setSubTab("agents")}
          >
            Agents
            {agentLog.some((entry) => entry.status === "active") ? " ●" : ""}
          </button>
          {GROUP_TABS.map((item) => (
            <button
              key={item.key}
              className={subTab === item.key ? "active" : ""}
              onClick={() => setSubTab(item.key)}
            >
              {item.label}
              {sastGroupHasActiveAgent(agentLog, item.key) ? " ●" : ""}
            </button>
          ))}
          <button className={subTab === "log" ? "active" : ""} onClick={() => setSubTab("log")}>
            Log
          </button>
        </div>
        <span className="subtle">{subTab === "log" ? `${logs.length} entries` : ""}</span>
        {scanRunning && <span className="activity-mode-badge running">● Scanning</span>}
        <a className="btn ghost sm" href={`/api/sast-runs/${runId}/agent-log/export`} download>
          Export ↓
        </a>
      </div>
      {subTab === "agents" ? (
        <SastAgentRoster
          agentLog={agentLog}
          analysisMode={analysisMode}
          scanRunning={scanRunning}
        />
      ) : selectedGroup ? (
        <SastAgentGroupView
          agentLog={agentLog}
          analysisMode={analysisMode}
          scanRunning={scanRunning}
          groupId={selectedGroup.groupId}
        />
      ) : !logs.length ? (
        <div className="sast-empty-state">No activity has been recorded yet.</div>
      ) : (
        <div className="sast-activity-feed">
          {logs.map((item) => (
            <div className="sast-activity-entry" key={item.id}>
              <time>{formatTime(item.created_at)}</time>
              <span className="sast-activity-phase">{item.phase || "event"}</span>
              <span className="sast-activity-message">{item.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
