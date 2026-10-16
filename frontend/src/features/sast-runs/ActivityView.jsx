import { fmtTime } from "../../shared/lib/dates.js";
import { useHashTab } from "../../shared/navigation/useHashTab.js";

import { SastAgentGroupView, SastAgentRoster } from "./SastAgentRoster.jsx";
import { sastGroupHasActiveAgent, sastGroupHasAgents } from "./sastAgentPresentation.js";

const GROUP_TABS = [
  { key: "review", label: "Review", groupId: "sast-review-workers" },
  { key: "injection", label: "Injection", groupId: "sast-injection-workers", legacy: true },
  { key: "access", label: "Access", groupId: "sast-access-workers", legacy: true },
  { key: "logic", label: "Logic", groupId: "sast-logic-workers", legacy: true },
  { key: "sink", label: "Sink", groupId: "sast-sink-workers" },
  { key: "validator", label: "Validators", groupId: "sast-validators" },
];

export function ActivityView({ logs, agentLog, scanRunning, runId, analysisMode }) {
  const groupTabs = GROUP_TABS.filter(
    (item) => !item.legacy || sastGroupHasAgents(agentLog, item.key),
  );
  const [subTab, setSubTab] = useHashTab(
    "subtab",
    ["agents", ...groupTabs.map((item) => item.key), "log"],
    "agents",
  );
  const selectedGroup = groupTabs.find((item) => item.key === subTab);
  return (
    <div className="sast-activity-panel">
      <div className="sast-activity-toolbar">
        <div className="sast-activity-tabs">
          <button
            className={subTab === "agents" ? "active" : ""}
            onClick={() => setSubTab("agents")}
          >
            Agents
            {scanRunning && agentLog.some((entry) => entry.status === "active") ? " ●" : ""}
          </button>
          {groupTabs.map((item) => (
            <button
              key={item.key}
              className={subTab === item.key ? "active" : ""}
              onClick={() => setSubTab(item.key)}
            >
              {item.label}
              {scanRunning && sastGroupHasActiveAgent(agentLog, item.key) ? " ●" : ""}
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
              <time>{fmtTime(item.created_at)}</time>
              <span className="sast-activity-phase">{item.phase || "event"}</span>
              <span className="sast-activity-message">{item.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
