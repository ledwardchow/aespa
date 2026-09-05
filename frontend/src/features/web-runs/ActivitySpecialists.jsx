import { useWebRunChat } from "./WebRunChat.jsx";
import { truncUrl } from "../../shared/lib/urls.js";
export function ActivitySpecialists({ agents }) {
  const { collapsedAgentIds, toggleAgentId } = useWebRunChat();
  return (
    <div className="agents-panel">
      {(() => {
        const specialistAgents = agents.filter((ag) => ag.id.startsWith("specialist-"));
        if (specialistAgents.length === 0)
          return (
            <div
              className="subtle"
              style={{
                padding: "24px",
                textAlign: "center",
              }}
            >
              No specialist agents dispatched yet.
            </div>
          );
        return specialistAgents.map((sa) => {
          const saActive = sa.status === "active";
          const saTask = sa.currentTask || sa.taskHistory?.slice(-1)[0]?.task || "Initialising…";
          const saSteps = sa.stepHistory || [];
          const saExpanded = saSteps.length > 0 && !collapsedAgentIds.has(sa.id);
          const threadLabel = sa.id.replace("specialist-", "").replace(/-([0-9]+)$/, " #$1");
          return (
            <div
              key={sa.id}
              className={
                "agent-row" +
                (saActive ? " agent-row--active" : " agent-row--complete") +
                (saSteps.length > 0 ? " agent-row--expandable" : "")
              }
              onClick={saSteps.length > 0 ? () => toggleAgentId(sa.id) : undefined}
            >
              <span
                className={"agent-dot" + (saActive ? " agent-dot--active" : "")}
                aria-hidden="true"
              ></span>
              <span
                className={"agent-role-name" + (saActive ? " agent-role-name--pulse" : "")}
                style={{
                  textTransform: "capitalize",
                }}
              >
                {threadLabel}
              </span>
              <span
                className={
                  "agent-badge" + (saActive ? " agent-badge-active" : " agent-badge-complete")
                }
              >
                {saActive ? "ACTIVE" : "DONE"}
              </span>
              <span className="agent-current-task" title={saTask}>
                {saTask.length > 90 ? saTask.slice(0, 89) + "…" : saTask}
              </span>
              {saSteps.length > 0 && (
                <span className="activity-expand-chevron">{saExpanded ? "▲" : "▼"}</span>
              )}
              {saSteps.length > 0 && saExpanded && (
                <div className="agent-task-history">
                  {saSteps
                    .slice()
                    .reverse()
                    .map((s, i) => (
                      <div key={i} className="agent-history-entry">
                        <span className="activity-ts">{s.ts}</span>
                        <span className="agent-step-method">
                          {s.method ? (
                            <>
                              {s.method}{" "}
                              {s.url ? <span title={s.url}>{truncUrl(s.url, 80)}</span> : ""}
                            </>
                          ) : (
                            s.action_type || "tool"
                          )}
                        </span>
                        {s.observation && (
                          <span className="agent-history-outcome" title={s.observation}>
                            {String(s.observation).slice(0, 80)}
                          </span>
                        )}
                      </div>
                    ))}
                </div>
              )}
            </div>
          );
        });
      })()}
    </div>
  );
}
