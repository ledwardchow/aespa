import * as apiRunsApi from "../../shared/api/apiRuns.js";
import { buildAgentsFromLog } from "./agentLog.js";
import { useState, useEffect } from "react";

import { FindingReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";

import { ApiAlicePanel } from "./ApiAlicePanel.jsx";

export function ApiRunAgentsTab({ runId, scanRunning }) {
  // ── Agent list state ──────────────────────────────────────────────────────
  const [agents, setAgents] = useState([]);
  const [collapsedAgentIds, setCollapsedAgentIds] = useState(new Set());
  const toggleAgentId = (id) =>
    setCollapsedAgentIds((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const [aliceRunning, setAliceRunning] = useState(false);
  // ── SSE: real-time agent_status events ───────────────────────────────────
  useEffect(() => {
    const es = new EventSource(`/api/api-test-runs/${runId}/events`);
    es.onmessage = (ev) => {
      try {
        const evt = JSON.parse(ev.data);
        if (evt.type !== "agent_status") return;
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        setAgents((prev) => {
          const idx = prev.findIndex((a) => a.id === evt.agent_id);
          const histEntry = {
            ts,
            task: evt.current_task || "",
            outcome: evt.outcome || "",
          };
          const existing =
            idx >= 0
              ? prev[idx]
              : {
                  id: evt.agent_id,
                  name: evt.role || evt.agent_id,
                  status: evt.status,
                  task: evt.current_task || "",
                  taskHistory: [],
                };
          const updated = {
            ...existing,
            name: evt.role || existing.name,
            status: evt.status,
            task: evt.current_task || "",
            findingReference: evt.finding_reference || existing.findingReference,
            taskHistory: [...(existing.taskHistory || []), histEntry],
          };
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = updated;
            return next;
          }
          return [...prev, updated];
        });
      } catch {}
    };
    return () => es.close();
  }, [runId]);

  // ── Poll agent log while scanning or alice is running ────────────────────
  // Merge with existing state so SSE-only (non-persisted) step history is
  // not wiped on every poll cycle.
  useEffect(() => {
    if (!aliceRunning && !scanRunning) return;
    const t = setInterval(() => {
      apiRunsApi
        .getApiAgentLog(runId)
        .then((rows) => {
          const fromLog = buildAgentsFromLog(rows);
          setAgents((prev) => {
            const prevMap = new Map(prev.map((a) => [a.id, a]));
            const merged = fromLog.map((a) => {
              const existing = prevMap.get(a.id);
              if (!existing) return a;
              // Prefer the longer history — SSE may have more non-persisted entries
              const history =
                existing.taskHistory.length >= a.taskHistory.length
                  ? existing.taskHistory
                  : a.taskHistory;
              return {
                ...a,
                taskHistory: history,
              };
            });
            // Keep SSE-only agents not yet written to the DB
            for (const a of prev) {
              if (!merged.find((m) => m.id === a.id)) merged.push(a);
            }
            return merged;
          });
        })
        .catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [aliceRunning, scanRunning, runId]);

  useEffect(() => {
    apiRunsApi
      .getApiAgentLog(runId)
      .then((rows) => {
        setAgents(buildAgentsFromLog(rows));
      })
      .catch(() => {});
  }, [runId]);
  // ── Build agent roster ────────────────────────────────────────────────────
  // API scan roster: A.L.I.C.E. → Test Lead → Specialist → Validator → Reporting
  const buildRoster = () => {
    const byId = Object.fromEntries(agents.map((a) => [a.id, a]));
    const specialistChildren = agents.filter((a) => a.id.startsWith("specialist-"));

    return [
      {
        id: "alice",
        name: "A.L.I.C.E.",
        status: aliceRunning ? "active" : byId["alice"]?.status || "idle",
        task: aliceRunning
          ? "Processing directive…"
          : byId["alice"]?.task || "Waiting for instruction",
        taskHistory: byId["alice"]?.taskHistory || [],
      },
      {
        id: "scanner",
        name: "Test Lead",
        status: scanRunning && !byId["scanner"] ? "active" : byId["scanner"]?.status || "idle",
        task:
          scanRunning && !byId["scanner"]
            ? "Coordinating API pentest"
            : byId["scanner"]?.task || "Standing by",
        taskHistory: byId["scanner"]?.taskHistory || [],
      },
      {
        id: "specialist",
        name: "Specialist",
        children: specialistChildren,
      },
      {
        id: "reporting",
        name: "Reporting",
        status: byId["reporting"]?.status || "idle",
        task: byId["reporting"]?.task || "Standing by",
        taskHistory: byId["reporting"]?.taskHistory || [],
      },
    ];
  };
  const roster = buildRoster();
  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      className="agents-panel"
      style={{
        padding: "8px 0",
      }}
    >
      {roster.map((agent) => {
        // ── A.L.I.C.E. row with embedded chat ─────────────────────────────
        if (agent.id === "alice")
          return (
            <ApiAlicePanel
              key="alice"
              runId={runId}
              agent={agent}
              onRunningChange={setAliceRunning}
            />
          );

        // ── Specialist container row ───────────────────────────────────────
        if (agent.id === "specialist") {
          const children = agent.children || [];
          const anyActive = children.some((c) => c.status === "active");
          const activeCount = children.filter((c) => c.status === "active").length;
          const doneCount = children.length - activeCount;
          const summaryTask =
            children.length === 0
              ? "No specialist dispatched"
              : activeCount > 0 && doneCount > 0
                ? `${activeCount} running, ${doneCount} complete`
                : activeCount > 0
                  ? `${activeCount} thread${activeCount !== 1 ? "s" : ""} running`
                  : `${doneCount} thread${doneCount !== 1 ? "s" : ""} complete`;
          const canExpand = children.length > 0;
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
                {anyActive ? "ACTIVE" : children.length > 0 ? "COMPLETE" : "IDLE"}
              </span>
              <span className="agent-current-task">{summaryTask}</span>
              {canExpand && (
                <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
              )}
              {canExpand && isExpanded && (
                <div className="agent-task-history">
                  {children.map((c) => {
                    const cActive = c.status === "active";
                    const cTask =
                      c.task || (c.taskHistory || []).slice(-1)[0]?.task || "Initialising…";
                    return (
                      <div
                        key={c.id}
                        className={
                          "agent-thread-row" + (cActive ? " agent-thread-row--active" : "")
                        }
                      >
                        <span
                          className={
                            "agent-dot agent-dot--sm" + (cActive ? " agent-dot--active" : "")
                          }
                          aria-hidden="true"
                        ></span>
                        <span className="agent-thread-id">
                          {c.id.replace("specialist-", "").replace(/-([0-9]+)$/, " #$1")}
                        </span>
                        <span
                          className={
                            "agent-badge agent-badge--sm" +
                            (cActive ? " agent-badge-active" : " agent-badge-complete")
                          }
                        >
                          {cActive ? "ACTIVE" : "DONE"}
                        </span>
                        <span className="agent-current-task" title={cTask}>
                          {cTask.length > 90 ? cTask.slice(0, 89) + "…" : cTask}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        }

        // ── Validator container row ────────────────────────────────────────
        if (agent.id === "validator") {
          const children = agent.children || [];
          const anyActive = children.some((c) => c.status === "active");
          const activeCount = children.filter((c) => c.status === "active").length;
          const doneCount = children.length - activeCount;
          const summaryTask =
            children.length === 0
              ? "No validation running"
              : activeCount > 0 && doneCount > 0
                ? `${activeCount} validating, ${doneCount} complete`
                : activeCount > 0
                  ? `${activeCount} finding${activeCount !== 1 ? "s" : ""} validating`
                  : `${doneCount} finding${doneCount !== 1 ? "s" : ""} validated`;
          const canExpand = children.length > 0;
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
                {anyActive ? "ACTIVE" : children.length > 0 ? "COMPLETE" : "IDLE"}
              </span>
              <span className="agent-current-task">{summaryTask}</span>
              {canExpand && (
                <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
              )}
              {canExpand && isExpanded && (
                <div className="agent-task-history">
                  {children.map((va) => {
                    const vaActive = va.status === "active";
                    const vaTask =
                      va.task || (va.taskHistory || []).slice(-1)[0]?.task || "Initialising…";
                    const vaOutcome = (va.taskHistory || []).slice(-1)[0]?.outcome;
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
                          reference={va.findingReference || `#${va.id.replace("validator-", "")}`}
                          href={
                            va.findingReference
                              ? `#/api-runs/${runId}/findings?finding=${encodeURIComponent(va.findingReference)}`
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

        // ── Standard agent row (Test Lead, Reporting, etc.) ────────────────
        const isActive = agent.status === "active";
        const isComplete = ["complete", "completed", "done"].includes(agent.status);
        const taskHistory = agent.taskHistory || [];
        const canExpand = taskHistory.length > 1 || taskHistory.some((h) => h.outcome);
        const isExpanded = canExpand && !collapsedAgentIds.has(agent.id);
        const task = agent.task || taskHistory.slice(-1)[0]?.task || "";
        return (
          <div
            key={agent.id}
            className={
              "agent-row" +
              (isActive ? " agent-row--active" : " agent-row--complete") +
              (canExpand ? " agent-row--expandable" : "")
            }
            onClick={canExpand ? () => toggleAgentId(agent.id) : undefined}
          >
            <span
              className={"agent-dot" + (isActive ? " agent-dot--active" : "")}
              aria-hidden="true"
            ></span>
            <span className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}>
              {agent.name}
            </span>
            <span
              className={
                "agent-badge" + (isActive ? " agent-badge-active" : " agent-badge-complete")
              }
            >
              {isActive ? "ACTIVE" : isComplete ? "DONE" : (agent.status || "IDLE").toUpperCase()}
            </span>
            {task && (
              <span className="agent-current-task" title={task}>
                {task.length > 90 ? task.slice(0, 89) + "…" : task}
              </span>
            )}
            {canExpand && <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>}
            {canExpand && isExpanded && (
              <div className="agent-task-history">
                {taskHistory
                  .slice()
                  .reverse()
                  .map((h, i) => (
                    <div key={i} className="agent-history-entry">
                      <span className="activity-ts">{h.ts || ""}</span>
                      <span className="agent-history-task">{h.task || ""}</span>
                      {h.outcome && <span className="agent-history-outcome">{h.outcome}</span>}
                    </div>
                  ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
