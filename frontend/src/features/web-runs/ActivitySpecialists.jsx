import { useWebRunChat } from "./WebRunChat.jsx";
import { truncUrl } from "../../shared/lib/urls.js";

const SPECIALIST_WORKER_TYPES = [{ prefix: "specialist-", label: "Specialist" }];

const readableLabel = (value) => String(value || "").replaceAll("_", " ");

function stepDescription(step) {
  const description =
    step.description || step.hypothesis || step.payload_purpose || step.observation;
  if (description) return String(description);
  if (step.method) return `Send ${step.method} request`;
  if (step.context_tool) return `Look up ${readableLabel(step.context_tool)}`;
  if (step.tool_name === "browser" || step.action_type === "browser") return "Use the browser";
  return `Use ${readableLabel(step.tool_name || step.action_type || "scan tool")}`;
}

function stepSupportingDetail(step) {
  const details = [];
  if (step.method) {
    details.push(`${step.method}${step.url ? ` ${truncUrl(step.url, 100)}` : " request"}`);
  } else if (step.context_tool) {
    details.push(`Context: ${readableLabel(step.context_tool)}`);
  } else if (step.tool_name || step.action_type) {
    const toolLabel = step.tool_name || step.action_type;
    details.push(
      toolLabel === "tool"
        ? "Context lookup"
        : toolLabel === "browser"
          ? "Browser action"
          : `Tool: ${readableLabel(toolLabel)}`,
    );
  }
  if (step.observation && step.observation !== stepDescription(step)) {
    details.push(`Observed: ${String(step.observation).slice(0, 140)}`);
  }
  if (step.payload_summary) details.push(`Payload: ${String(step.payload_summary).slice(0, 100)}`);
  return details.join(" · ");
}

export function ActivitySpecialists({
  agents,
  workerTypes = SPECIALIST_WORKER_TYPES,
  emptyMessage = "No workers dispatched yet.",
}) {
  const { collapsedAgentIds, toggleAgentId } = useWebRunChat();
  return (
    <div className="agents-panel">
      {(() => {
        const specialistAgents = agents.flatMap((agent) => {
          const workerType = workerTypes.find(({ prefix }) => agent.id.startsWith(prefix));
          return workerType ? [{ ...agent, workerType }] : [];
        });
        if (specialistAgents.length === 0)
          return (
            <div
              className="subtle"
              style={{
                padding: "24px",
                textAlign: "center",
              }}
            >
              {emptyMessage}
            </div>
          );
        return specialistAgents.map((sa) => {
          const saActive = sa.status === "active";
          const saTask = sa.currentTask || sa.taskHistory?.slice(-1)[0]?.task || "Initialising…";
          const saSteps = sa.stepHistory || [];
          const saExpanded = saSteps.length > 0 && !collapsedAgentIds.has(sa.id);
          const workerId = sa.id.replace(sa.workerType.prefix, "");
          const deepMatch = workerId.match(/^(\d+)-task-(\d+)$/);
          const threadLabel = deepMatch
            ? `${sa.workerType.label} ${deepMatch[1]} · Task #${deepMatch[2]}`
            : `${sa.workerType.label} ${workerId.replace(/-([0-9]+)$/, " #$1")}`;
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
                    .map((s, i) => {
                      const description = stepDescription(s);
                      const supportingDetail = stepSupportingDetail(s);
                      return (
                        <div key={i} className="agent-history-entry">
                          <span className="activity-ts">{s.ts}</span>
                          <span className="agent-step-description" title={description}>
                            {s.step ? `Step ${s.step}: ` : ""}
                            {description}
                          </span>
                          {supportingDetail && (
                            <span className="agent-history-outcome" title={supportingDetail}>
                              {supportingDetail}
                            </span>
                          )}
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          );
        });
      })()}
    </div>
  );
}
