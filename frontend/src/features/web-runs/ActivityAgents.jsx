import { useWebRunChat } from "./WebRunChat.jsx";
import { activityPresentation } from "./activityPresentation.js";
import { truncUrl } from "../../shared/lib/urls.js";
import { AliceChatPanel } from "./AliceChatPanel.jsx";
import { FindingReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";
export function ActivityAgents({ runId, agents, run, thinkingStatus, activityLog }) {
  const {
    collapsedAgentIds,
    toggleAgentId,
    aliceChats,
    activeAliceTabId,
    setActiveAliceTabId,
    deleteAliceTab,
    createAliceTab,
    aliceChatHeight,
    aliceMessages,
    aliceExpandedThinkIds,
    setAliceExpandedThinkIds,
    aliceThinkingTabId,
    aliceIsThinking,
    startAliceResize,
    aliceInputText,
    handleAliceSend,
    setAliceInputText,
    handleAliceStop,
    submitAliceDirective,
  } = useWebRunChat();
  const {
    normalizeAgentForRun,
    defaultAgentRoster,
    representsAgent,
    agentRoleLabel,
    agentCurrentTask,
    agentCrawlEvents,
    agentTaskHistory,
    agentStatusLabel,
  } = activityPresentation({ run, thinkingStatus, aliceIsThinking, activityLog });
  return (
    <div className="agents-panel">
      {(() => {
        const roster = defaultAgentRoster();
        // Container slots (specialist/burp/validator) must always render as
        // their placeholder so the multi-agent container row fires correctly.
        const CONTAINER_IDS = new Set(["specialist", "burp", "validator"]);
        const rosterAgents = roster.map((p) =>
          CONTAINER_IDS.has(p.id) ? p : agents.find((a) => representsAgent(a, p)) || p,
        );
        const extras = agents.filter((a) => !roster.some((p) => representsAgent(a, p)));
        const shownAgents = [...rosterAgents, ...extras].map(normalizeAgentForRun);
        const renderRow = (a) => {
          // ── Specialist container row ────────────────────────────────
          if (a.id === "specialist") {
            const specialistAgents = agents
              .filter((ag) => ag.id.startsWith("specialist-"))
              .map(normalizeAgentForRun);
            const anyActive = specialistAgents.some((ag) => ag.status === "active");

            const activeCount = specialistAgents.filter((ag) => ag.status === "active").length;
            const doneCount = specialistAgents.length - activeCount;
            const summaryTask =
              specialistAgents.length === 0
                ? "No specialist dispatched"
                : activeCount > 0 && doneCount > 0
                  ? `${activeCount} running, ${doneCount} complete`
                  : activeCount > 0
                    ? `${activeCount} thread${activeCount !== 1 ? "s" : ""} running`
                    : `${doneCount} thread${doneCount !== 1 ? "s" : ""} complete`;
            const canExpand = specialistAgents.length > 0;
            const isExpanded = canExpand && !collapsedAgentIds.has("specialist");
            return (
              <div
                key="specialist"
                className={
                  "agent-row" +
                  (anyActive ? " agent-row--active" : " agent-row--complete") +
                  (canExpand ? " agent-row--expandable" : "")
                }
                onClick={canExpand ? () => toggleAgentId("specialist") : undefined}
              >
                <span
                  className={"agent-dot" + (anyActive ? " agent-dot--active" : "")}
                  aria-hidden="true"
                ></span>
                <span className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}>
                  Specialist
                </span>
                <span
                  className={
                    "agent-badge" + (anyActive ? " agent-badge-active" : " agent-badge-complete")
                  }
                >
                  {anyActive ? "ACTIVE" : specialistAgents.length > 0 ? "COMPLETE" : "IDLE"}
                </span>
                <span className="agent-current-task">{summaryTask}</span>
                {canExpand && (
                  <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                )}
                {canExpand && isExpanded && (
                  <div className="agent-task-history">
                    {specialistAgents.map((sa) => {
                      const saActive = sa.status === "active";
                      const saTask =
                        sa.currentTask || sa.taskHistory?.slice(-1)[0]?.task || "Initialising…";
                      return (
                        <div
                          key={sa.id}
                          className={
                            "agent-thread-row" + (saActive ? " agent-thread-row--active" : "")
                          }
                        >
                          <span
                            className={
                              "agent-dot agent-dot--sm" + (saActive ? " agent-dot--active" : "")
                            }
                            aria-hidden="true"
                          ></span>
                          <span className="agent-thread-id">
                            {sa.id.replace("specialist-", "").replace(/-([0-9]+)$/, " #$1")}
                          </span>
                          <span
                            className={
                              "agent-badge agent-badge--sm" +
                              (saActive ? " agent-badge-active" : " agent-badge-complete")
                            }
                          >
                            {saActive ? "ACTIVE" : "DONE"}
                          </span>
                          <span className="agent-current-task" title={saTask}>
                            {saTask.length > 90 ? saTask.slice(0, 89) + "…" : saTask}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          }
          // ── Validator container row ────────────────────────────────
          if (a.id === "validator") {
            const validatorAgents = agents
              .filter((ag) => ag.id.startsWith("validator-"))
              .map(normalizeAgentForRun);
            const anyActive = validatorAgents.some((ag) => ag.status === "active");
            const activeCount = validatorAgents.filter((ag) => ag.status === "active").length;
            const doneCount = validatorAgents.length - activeCount;
            const summaryTask =
              validatorAgents.length === 0
                ? "No validation running"
                : activeCount > 0 && doneCount > 0
                  ? `${activeCount} validating, ${doneCount} complete`
                  : activeCount > 0
                    ? `${activeCount} finding${activeCount !== 1 ? "s" : ""} validating`
                    : `${doneCount} finding${doneCount !== 1 ? "s" : ""} validated`;
            const canExpand = validatorAgents.length > 0;
            const isExpanded = canExpand && !collapsedAgentIds.has("validator");
            return (
              <div
                key="validator"
                className={
                  "agent-row" +
                  (anyActive ? " agent-row--active" : " agent-row--complete") +
                  (canExpand ? " agent-row--expandable" : "")
                }
                onClick={canExpand ? () => toggleAgentId("validator") : undefined}
              >
                <span
                  className={"agent-dot" + (anyActive ? " agent-dot--active" : "")}
                  aria-hidden="true"
                ></span>
                <span className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}>
                  Validator
                </span>
                <span
                  className={
                    "agent-badge" + (anyActive ? " agent-badge-active" : " agent-badge-complete")
                  }
                >
                  {anyActive ? "ACTIVE" : validatorAgents.length > 0 ? "COMPLETE" : "IDLE"}
                </span>
                <span className="agent-current-task">{summaryTask}</span>
                {canExpand && (
                  <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                )}
                {canExpand && isExpanded && (
                  <div className="agent-task-history">
                    {validatorAgents.map((va) => {
                      const vaActive = va.status === "active";
                      const vaTask =
                        va.currentTask || va.taskHistory?.slice(-1)[0]?.task || "Initialising…";
                      const vaOutcome = va.outcome || va.taskHistory?.slice(-1)[0]?.outcome;
                      const findingNum = va.id.replace("validator-", "");
                      return (
                        <div
                          key={va.id}
                          className={
                            "agent-thread-row" + (vaActive ? " agent-thread-row--active" : "")
                          }
                        >
                          <span
                            className={
                              "agent-dot agent-dot--sm" + (vaActive ? " agent-dot--active" : "")
                            }
                            aria-hidden="true"
                          ></span>
                          <FindingReferenceLink
                            reference={va.findingReference || `#${findingNum}`}
                            href={
                              va.findingReference
                                ? `#/runs/${runId}/findings?finding=${encodeURIComponent(va.findingReference)}`
                                : undefined
                            }
                          />
                          <span
                            className={
                              "agent-badge agent-badge--sm" +
                              (vaActive ? " agent-badge-active" : " agent-badge-complete")
                            }
                          >
                            {vaActive ? "ACTIVE" : "DONE"}
                          </span>
                          <span className="agent-current-task" title={vaTask}>
                            {vaTask.length > 90 ? vaTask.slice(0, 89) + "…" : vaTask}
                          </span>
                          {vaOutcome && !vaActive && (
                            <span className="agent-history-outcome">{vaOutcome}</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          }
          // ── Burp container row ──────────────────────────────────────
          if (a.id === "burp") {
            const burpAgents = agents
              .filter((ag) => ag.id.startsWith("burp-"))
              .map(normalizeAgentForRun);
            const anyActive = burpAgents.some((ag) => ag.status === "active");

            const activeCount = burpAgents.filter((ag) => ag.status === "active").length;
            const doneCount = burpAgents.length - activeCount;
            const summaryTask =
              burpAgents.length === 0
                ? "No active scan dispatched"
                : activeCount > 0 && doneCount > 0
                  ? `${activeCount} scanning, ${doneCount} complete`
                  : activeCount > 0
                    ? `${activeCount} scan${activeCount !== 1 ? "s" : ""} running`
                    : `${doneCount} scan${doneCount !== 1 ? "s" : ""} complete`;
            const canExpand = burpAgents.length > 0;
            const isExpanded = canExpand && !collapsedAgentIds.has("burp");
            return (
              <div
                key="burp"
                className={
                  "agent-row" +
                  (anyActive ? " agent-row--active" : " agent-row--complete") +
                  (canExpand ? " agent-row--expandable" : "")
                }
                onClick={canExpand ? () => toggleAgentId("burp") : undefined}
              >
                <span
                  className={"agent-dot" + (anyActive ? " agent-dot--active" : "")}
                  aria-hidden="true"
                ></span>
                <span className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}>
                  Burp
                </span>
                <span
                  className={
                    "agent-badge" + (anyActive ? " agent-badge-active" : " agent-badge-complete")
                  }
                >
                  {anyActive ? "ACTIVE" : burpAgents.length > 0 ? "COMPLETE" : "IDLE"}
                </span>
                <span className="agent-current-task">{summaryTask}</span>
                {canExpand && (
                  <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                )}
                {canExpand && isExpanded && (
                  <div className="agent-task-history">
                    {burpAgents.map((ba) => {
                      const baActive = ba.status === "active";
                      const baTask =
                        ba.currentTask || ba.taskHistory?.slice(-1)[0]?.task || "Initialising…";
                      return (
                        <div
                          key={ba.id}
                          className={
                            "agent-thread-row" + (baActive ? " agent-thread-row--active" : "")
                          }
                        >
                          <span
                            className={
                              "agent-dot agent-dot--sm" + (baActive ? " agent-dot--active" : "")
                            }
                            aria-hidden="true"
                          ></span>
                          <span className="agent-thread-id">{ba.id.replace("burp-", "")}</span>
                          <span
                            className={
                              "agent-badge agent-badge--sm" +
                              (baActive ? " agent-badge-active" : " agent-badge-complete")
                            }
                          >
                            {baActive ? "ACTIVE" : ba.status === "failed" ? "FAILED" : "DONE"}
                          </span>
                          <span className="agent-current-task" title={baTask}>
                            {baTask.length > 90 ? baTask.slice(0, 89) + "…" : baTask}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          }
          // ── A.L.I.C.E custom row ────────────────────────────────────
          if (a.id === "alice") {
            const isExpanded = !collapsedAgentIds.has("alice");
            const isActive = a.status === "active";
            const currentTask = a.currentTask;
            return (
              <div
                key="alice"
                className="agent-row agent-row--alice-chat agent-row--expandable"
                onClick={() => toggleAgentId("alice")}
              >
                <span
                  className={"agent-dot agent-dot--alice" + (isActive ? " agent-dot--active" : "")}
                  aria-hidden="true"
                ></span>
                <span className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}>
                  A.L.I.C.E
                </span>
                <span
                  className={
                    "agent-badge" +
                    (isActive ? " agent-badge-alice-active" : " agent-badge-alice-idle")
                  }
                >
                  {isActive ? "ACTIVE" : "STANDBY"}
                </span>
                <span className="agent-current-task" title={currentTask}>
                  {currentTask}
                </span>
                <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                {isExpanded && (
                  <AliceChatPanel
                    runId={runId}
                    aliceChats={aliceChats}
                    activeAliceTabId={activeAliceTabId}
                    setActiveAliceTabId={setActiveAliceTabId}
                    deleteAliceTab={deleteAliceTab}
                    createAliceTab={createAliceTab}
                    aliceChatHeight={aliceChatHeight}
                    aliceMessages={aliceMessages}
                    aliceExpandedThinkIds={aliceExpandedThinkIds}
                    setAliceExpandedThinkIds={setAliceExpandedThinkIds}
                    startAliceResize={startAliceResize}
                    aliceInputText={aliceInputText}
                    setAliceInputText={setAliceInputText}
                    isActiveThinking={aliceThinkingTabId === activeAliceTabId}
                    aliceIsThinking={aliceIsThinking}
                    handleAliceSend={handleAliceSend}
                    handleAliceStop={handleAliceStop}
                    submitAliceDirective={submitAliceDirective}
                    onPopOut={() => toggleAgentId("alice")}
                  />
                )}
              </div>
            );
          }
          const isActive = a.status === "active";
          const roleLabel = agentRoleLabel(a);
          const currentTask = agentCurrentTask(a);
          const crawlEvents = agentCrawlEvents(a);
          const taskHistory = agentTaskHistory(a);
          const canExpand =
            (a.id === "crawler" && crawlEvents.length > 0) ||
            taskHistory.length > 1 ||
            taskHistory.some((h) => h.outcome);
          const isExpanded = canExpand && !collapsedAgentIds.has(a.id);
          return (
            <div
              key={a.id}
              className={
                "agent-row" +
                (isActive ? " agent-row--active" : " agent-row--complete") +
                (canExpand ? " agent-row--expandable" : "")
              }
              onClick={canExpand ? () => toggleAgentId(a.id) : undefined}
            >
              <span
                className={"agent-dot" + (isActive ? " agent-dot--active" : "")}
                aria-hidden="true"
              ></span>
              <span className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}>
                {roleLabel}
                {a.id.includes("-") &&
                !["scanner", "crawler"].includes(a.id) &&
                !a.id.startsWith("burp-") ? (
                  <>
                    <br />
                    <span className="agent-role-sub">
                      {a.id.replace(/^[a-z]+-/, "").replace(/-/g, " ")}
                    </span>
                  </>
                ) : (
                  ""
                )}
              </span>
              <span
                className={
                  "agent-badge" + (isActive ? " agent-badge-active" : " agent-badge-complete")
                }
              >
                {agentStatusLabel(a)}
              </span>
              <span className="agent-current-task" title={currentTask}>
                {currentTask}
              </span>
              {canExpand && (
                <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
              )}
              {canExpand && isExpanded && (
                <div className="agent-task-history">
                  {a.id === "crawler" && crawlEvents.length > 0 ? (
                    <>
                      {crawlEvents
                        .slice()
                        .reverse()
                        .map((h, i) => (
                          <div key={i} className="agent-history-entry agent-history-entry--crawl">
                            <span className="activity-ts">{h.ts}</span>
                            <span className="agent-history-user">{h.username || "crawler"}</span>
                            <span className="agent-history-task mono" title={h.url || ""}>
                              {h.task ||
                                (h.done
                                  ? `Finished (${h.pagesVisited || 0} pg)`
                                  : `${h.stageLabel || "Crawling"} · ${truncUrl(h.url || "", 112)}`)}
                            </span>
                          </div>
                        ))}
                    </>
                  ) : (
                    <>
                      {taskHistory
                        .slice()
                        .reverse()
                        .map((h, i) => (
                          <div key={i} className="agent-history-entry">
                            <span className="activity-ts">{h.ts}</span>
                            <span className="agent-history-task">{h.task}</span>
                            {h.outcome && (
                              <span className="agent-history-outcome">{h.outcome}</span>
                            )}
                          </div>
                        ))}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        };
        return <>{shownAgents.map(renderRow)}</>;
      })()}
    </div>
  );
}
