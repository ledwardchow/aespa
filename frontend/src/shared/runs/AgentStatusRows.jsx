const ACTIVE_STATUSES = new Set(["active", "running"]);
const QUEUED_STATUSES = new Set(["spawned", "queued", "pausing"]);
const PAUSED_STATUSES = new Set(["paused"]);
const FAILED_STATUSES = new Set(["failed", "blocked", "cancelled", "stopped"]);

export function normaliseAgentStatus(status) {
  const value = String(status || "idle").toLowerCase();
  if (ACTIVE_STATUSES.has(value)) return "active";
  if (QUEUED_STATUSES.has(value)) return "queued";
  if (PAUSED_STATUSES.has(value)) return "paused";
  if (FAILED_STATUSES.has(value)) return "failed";
  if (["complete", "completed", "skipped", "done"].includes(value)) return "complete";
  return "idle";
}

export function agentStatusLabel(status) {
  const normalised = normaliseAgentStatus(status);
  if (normalised === "active") return "ACTIVE";
  if (normalised === "queued") return "QUEUED";
  if (normalised === "paused") return "PAUSED";
  if (normalised === "failed") return "FAILED";
  if (normalised === "complete") return "COMPLETE";
  return "IDLE";
}

function statusClasses(status, small = false) {
  const normalised = normaliseAgentStatus(status);
  return ["agent-badge", small ? "agent-badge--sm" : "", `agent-badge-${normalised}`]
    .filter(Boolean)
    .join(" ");
}

function History({ entries }) {
  return (
    <div className="agent-task-history">
      {[...entries].reverse().map((entry, index) => (
        <div className="agent-history-entry" key={entry.id || `${entry.ts}-${index}`}>
          <span className="activity-ts">{entry.ts}</span>
          <span className="agent-history-task">{entry.task || "Waiting for work"}</span>
          {entry.outcome ? <span className="agent-history-outcome">{entry.outcome}</span> : null}
        </div>
      ))}
    </div>
  );
}

function keyboardToggle(event, onToggle) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  onToggle();
}

export function AgentStatusRow({ agent, expanded, onToggle }) {
  const status = normaliseAgentStatus(agent.status);
  const history = agent.taskHistory || [];
  const canExpand = history.length > 1 || history.some((entry) => entry.outcome);
  const toggle = canExpand ? onToggle : undefined;
  return (
    <div
      className={
        "agent-row" +
        (status === "active" ? " agent-row--active" : " agent-row--complete") +
        (canExpand ? " agent-row--expandable" : "")
      }
      onClick={toggle}
      onKeyDown={toggle ? (event) => keyboardToggle(event, toggle) : undefined}
      role={toggle ? "button" : undefined}
      tabIndex={toggle ? 0 : undefined}
    >
      <span
        className={"agent-dot" + (status === "active" ? " agent-dot--active" : "")}
        aria-hidden="true"
      />
      <span className={"agent-role-name" + (status === "active" ? " agent-role-name--pulse" : "")}>
        {agent.name}
      </span>
      <span className={statusClasses(status)}>{agentStatusLabel(status)}</span>
      <span className="agent-current-task" title={agent.task}>
        {agent.task || "Waiting for work"}
      </span>
      {canExpand ? (
        <span className="activity-expand-chevron" aria-hidden="true">
          {expanded ? "▲" : "▼"}
        </span>
      ) : null}
      {canExpand && expanded ? <History entries={history} /> : null}
    </div>
  );
}

export function AgentGroupRow({ group, expanded, onToggle, expandedChildren, onToggleChild }) {
  const status = normaliseAgentStatus(group.status);
  const canExpand = group.children.length > 0;
  const toggle = canExpand ? onToggle : undefined;
  return (
    <div
      className={
        "agent-row" +
        (status === "active" ? " agent-row--active" : " agent-row--complete") +
        (canExpand ? " agent-row--expandable" : "")
      }
      onClick={toggle}
      onKeyDown={toggle ? (event) => keyboardToggle(event, toggle) : undefined}
      role={toggle ? "button" : undefined}
      tabIndex={toggle ? 0 : undefined}
    >
      <span
        className={"agent-dot" + (status === "active" ? " agent-dot--active" : "")}
        aria-hidden="true"
      />
      <span className={"agent-role-name" + (status === "active" ? " agent-role-name--pulse" : "")}>
        {group.name}
      </span>
      <span className={statusClasses(status)}>{agentStatusLabel(status)}</span>
      <span className="agent-current-task" title={group.task}>
        {group.task}
      </span>
      {canExpand ? (
        <span className="activity-expand-chevron" aria-hidden="true">
          {expanded ? "▲" : "▼"}
        </span>
      ) : null}
      {canExpand && expanded ? (
        <div className="agent-task-history">
          {group.children.map((child) => {
            const childStatus = normaliseAgentStatus(child.status);
            const childHistory = child.taskHistory || [];
            const childCanExpand =
              childHistory.length > 1 || childHistory.some((entry) => entry.outcome);
            const childExpanded = expandedChildren.has(child.id);
            return (
              <div key={child.id} className="agent-thread-block">
                <div
                  className={
                    "agent-thread-row" +
                    (childStatus === "active" ? " agent-thread-row--active" : "") +
                    (childCanExpand ? " agent-thread-row--expandable" : "")
                  }
                  onClick={
                    childCanExpand
                      ? (event) => {
                          event.stopPropagation();
                          onToggleChild(child.id);
                        }
                      : (event) => event.stopPropagation()
                  }
                  onKeyDown={
                    childCanExpand
                      ? (event) => {
                          event.stopPropagation();
                          keyboardToggle(event, () => onToggleChild(child.id));
                        }
                      : undefined
                  }
                  role={childCanExpand ? "button" : undefined}
                  tabIndex={childCanExpand ? 0 : undefined}
                >
                  <span
                    className={
                      "agent-dot agent-dot--sm" +
                      (childStatus === "active" ? " agent-dot--active" : "")
                    }
                    aria-hidden="true"
                  />
                  <span className="agent-thread-id">{child.name}</span>
                  <span className={statusClasses(childStatus, true)}>
                    {agentStatusLabel(childStatus)}
                  </span>
                  <span className="agent-current-task" title={child.task}>
                    {child.task || "Waiting for work"}
                  </span>
                  {childCanExpand ? (
                    <span className="activity-expand-chevron" aria-hidden="true">
                      {childExpanded ? "▲" : "▼"}
                    </span>
                  ) : null}
                </div>
                {childCanExpand && childExpanded ? <History entries={childHistory} /> : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
