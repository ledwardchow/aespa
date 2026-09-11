import { useMemo, useState } from "react";

import { AgentGroupRow, AgentStatusRow } from "../../shared/runs/AgentStatusRows.jsx";
import { buildSastAgentRoster } from "./sastAgentPresentation.js";

export function SastAgentRoster({ agentLog, analysisMode, scanRunning }) {
  const roster = useMemo(
    () => buildSastAgentRoster(agentLog, analysisMode, scanRunning),
    [agentLog, analysisMode, scanRunning],
  );
  const [collapsedIds, setCollapsedIds] = useState(() => new Set());
  const [expandedChildIds, setExpandedChildIds] = useState(() => new Set());
  const toggle = (setter, id) =>
    setter((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="agents-panel sast-agents-panel">
      {roster.map((entry) =>
        entry.children ? (
          <AgentGroupRow
            key={entry.id}
            group={entry}
            expanded={!collapsedIds.has(entry.id)}
            onToggle={() => toggle(setCollapsedIds, entry.id)}
            expandedChildren={expandedChildIds}
            onToggleChild={(id) => toggle(setExpandedChildIds, id)}
          />
        ) : (
          <AgentStatusRow
            key={entry.id}
            agent={entry}
            expanded={!collapsedIds.has(entry.id)}
            onToggle={() => toggle(setCollapsedIds, entry.id)}
          />
        ),
      )}
    </div>
  );
}

export function SastAgentGroupView({ agentLog, analysisMode, scanRunning, groupId }) {
  const group = useMemo(
    () =>
      buildSastAgentRoster(agentLog, analysisMode, scanRunning).find(
        (entry) => entry.id === groupId,
      ),
    [agentLog, analysisMode, scanRunning, groupId],
  );
  const [collapsedIds, setCollapsedIds] = useState(() => new Set());
  const toggleAgent = (id) =>
    setCollapsedIds((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (!group?.children.length) {
    return <div className="sast-empty-state">No {group?.name.toLowerCase()} dispatched yet.</div>;
  }

  return (
    <div className="agents-panel sast-agents-panel">
      {group.children.map((agent) => (
        <AgentStatusRow
          key={agent.id}
          agent={agent}
          expanded={!collapsedIds.has(agent.id)}
          onToggle={() => toggleAgent(agent.id)}
        />
      ))}
    </div>
  );
}
