import { useEffect, useRef, useState } from "react";

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
  const [showDisplayOptions, setShowDisplayOptions] = useState(false);
  const [newestFirst, setNewestFirst] = useState(true);
  const [selectedPhases, setSelectedPhases] = useState(new Set());
  const displayOptionsRef = useRef(null);
  const displayOptionsButtonRef = useRef(null);
  const feedRef = useRef(null);
  const groupTabs = GROUP_TABS.filter(
    (item) => !item.legacy || sastGroupHasAgents(agentLog, item.key),
  );
  const [subTab, setSubTab] = useHashTab(
    "subtab",
    ["agents", ...groupTabs.map((item) => item.key), "log"],
    "agents",
  );
  const selectedGroup = groupTabs.find((item) => item.key === subTab);
  const phases = [...new Set(logs.map((item) => item.phase || "event"))].sort();
  const visibleLogs = selectedPhases.size
    ? logs.filter((item) => selectedPhases.has(item.phase || "event"))
    : logs;
  const displayedLogs = newestFirst ? [...visibleLogs].reverse() : visibleLogs;
  const agentNames = new Map(
    agentLog
      .filter((item) => item.agent_id)
      .map((item) => [item.agent_id, item.display_name || item.role || item.agent_id]),
  );

  useEffect(() => {
    if (!showDisplayOptions) return;
    const onPointerDown = (event) => {
      if (!displayOptionsRef.current?.contains(event.target)) setShowDisplayOptions(false);
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setShowDisplayOptions(false);
        displayOptionsButtonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [showDisplayOptions]);

  useEffect(() => {
    if (subTab !== "log" || !feedRef.current) return;
    feedRef.current.scrollTop = newestFirst ? 0 : feedRef.current.scrollHeight;
  }, [logs.length, newestFirst, selectedPhases, subTab]);

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
        {subTab === "log" && (
          <>
            <span className="subtle">
              {selectedPhases.size ? `${visibleLogs.length} of ` : ""}
              {logs.length} {logs.length === 1 ? "entry" : "entries"}
            </span>
            <div className="activity-log-display-anchor" ref={displayOptionsRef}>
              <button
                ref={displayOptionsButtonRef}
                className="btn ghost sm"
                aria-expanded={showDisplayOptions}
                aria-controls="sast-log-display-options"
                onClick={() => setShowDisplayOptions((value) => !value)}
              >
                Display options
              </button>
              {showDisplayOptions && (
                <div
                  id="sast-log-display-options"
                  className="activity-log-display-options sast-log-display-options"
                  role="group"
                  aria-label="Display options"
                >
                  <label className="activity-log-option">
                    <input
                      type="checkbox"
                      checked={newestFirst}
                      onChange={(event) => setNewestFirst(event.target.checked)}
                    />
                    Newest first
                  </label>
                  {phases.length > 0 && (
                    <>
                      <div className="activity-log-filter-title">Event type</div>
                      <div className="activity-log-filter-options">
                        <label className="activity-log-option">
                          <input
                            type="checkbox"
                            checked={selectedPhases.size === 0}
                            onChange={() => setSelectedPhases(new Set())}
                          />
                          All
                        </label>
                        {phases.map((phase) => (
                          <label className="activity-log-option" key={phase}>
                            <input
                              type="checkbox"
                              checked={selectedPhases.has(phase)}
                              onChange={() =>
                                setSelectedPhases((previous) => {
                                  const next = new Set(previous);
                                  if (next.has(phase)) next.delete(phase);
                                  else next.add(phase);
                                  return next;
                                })
                              }
                            />
                            {phase.replaceAll("_", " ")}
                          </label>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </>
        )}
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
        <div className="sast-activity-feed" ref={feedRef}>
          {displayedLogs.map((item) => (
            <div className="sast-activity-entry" key={item.id}>
              <time>{fmtTime(item.created_at)}</time>
              <span className="sast-activity-phase">{item.phase || "event"}</span>
              <span
                className="sast-activity-agent"
                title={item.agent_id ? `${item.role || "Agent"} (${item.agent_id})` : undefined}
              >
                {item.agent_id === "system"
                  ? "System"
                  : agentNames.get(item.agent_id) || item.role || item.agent_id || "Unknown agent"}
              </span>
              <span className="sast-activity-message">{item.message}</span>
            </div>
          ))}
          {displayedLogs.length === 0 && (
            <div className="sast-empty-state">No events match these filters.</div>
          )}
        </div>
      )}
    </div>
  );
}
