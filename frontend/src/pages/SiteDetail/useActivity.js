import { useState, useEffect, useRef } from "react";
import { api } from "../../lib/api";
import { isDynamicScanActive } from "./_helpers";
import { parseDate, truncUrl } from "../../lib/utilities";

// Owns the Activity tab's world: the event log, the derived agent roster and
// its label/task/status helpers, token usage, and the site-plan card. The live
// SSE stream stays in TestRunDetail; it writes through the setAgents /
// setActivityLog / setTokenUsage / setSitePlanData / upsertAgent returned here.
export function useActivity(runId, activeTab, {
  run,
  thinkingStatus,
  aliceIsThinking,
  lastRunPollOkRef
}) {
  const [activityLog, setActivityLog] = useState([]);
  const [expandedLogIds, setExpandedLogIds] = useState(new Set());
  const toggleLogId = id => setExpandedLogIds(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });
  const [activitySubTab, setActivitySubTab] = useState("agents");
  const [agents, setAgents] = useState([]);
  const [tokenUsage, setTokenUsage] = useState(null); // {total_input, total_output, by_model}
  const [tokenExpanded, setTokenExpanded] = useState(false);
  const [sitePlanData, setSitePlanData] = useState(null);
  const activityFeedRef = useRef(null);

  const agentRoleLabel = agent => {
    if (agent?.id === "crawler") return "Crawler";
    if (agent?.id === "scanner") return "Test Lead";
    if (agent?.id === "alice") return "A.L.I.C.E";
    return agent?.role || "Agent";
  };
  const normalizeAgentForRun = agent => {
    if (agent?.id !== "crawler") return agent;
    if (run?.status === "running") return {
      ...agent,
      status: "active"
    };
    if (Date.now() - lastRunPollOkRef.current > 10000) {
      return {
        ...agent,
        status: "idle",
        currentTask: "Crawler connection stale"
      };
    }
    return {
      ...agent,
      status: agent.status === "failed" ? "failed" : "idle",
      currentTask: agent.currentTask || "Crawl is not running"
    };
  };
  const defaultAgentRoster = () => [{
    id: "alice",
    role: "A.L.I.C.E",
    status: aliceIsThinking ? "active" : "idle",
    currentTask: aliceIsThinking ? "Processing directive..." : "Waiting for instruction"
  }, {
    id: "crawler",
    role: "Crawler",
    status: run?.status === "running" ? "active" : "idle",
    currentTask: run?.status === "running" ? "" : "Waiting for crawl"
  }, {
    id: "scanner",
    role: "Test Lead",
    status: isDynamicScanActive(thinkingStatus?.status) ? "active" : "idle",
    currentTask: isDynamicScanActive(thinkingStatus?.status) ? "Coordinating pentest" : "Standing by"
  }, {
    id: "specialist",
    role: "Specialist",
    status: "idle",
    currentTask: "No specialist dispatched"
  }, {
    id: "burp",
    role: "Burp",
    status: "idle",
    currentTask: "No active scan dispatched"
  }, {
    id: "validator",
    role: "Validator",
    status: "idle",
    currentTask: "No validation running"
  }, {
    id: "reporting",
    role: "Reporting",
    status: thinkingStatus?.status === "analysing" ? "active" : "idle",
    currentTask: thinkingStatus?.status === "analysing" ? "Analysing probe results…" : "Standing by"
  }];
  const representsAgent = (agent, placeholder) => {
    if (agent.id === placeholder.id) return true;
    if (placeholder.id === "burp") return agent.role === "Burp" || agent.id?.startsWith("burp-");
    if (placeholder.id === "validator") return agent.role === "Validator" || agent.id?.startsWith("validator-");
    if (placeholder.id === "specialist") return agent.role === "Specialist" || agent.id?.startsWith("specialist-");
    if (placeholder.id === "reporting") return agent.role === "Reporting" || agent.id === "reporting";
    return false;
  };
  const fmtEventTime = value => {
    if (!value) return "--:--:--";
    try {
      return parseDate(value).toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
    } catch {
      return "--:--:--";
    }
  };
  const crawlEventsFromRun = () => {
    const progress = run?.per_user_progress || {};
    const labelByUsername = new Map((run?.credentials || []).map(c => [c.username, c.label || c.username]));
    return Object.entries(progress).filter(([, p]) => p && (p.current_url || p.done || p.pages_visited)).map(([username, p]) => ({
      ts: fmtEventTime(p.updated_at),
      username: labelByUsername.get(username) || username || "anonymous",
      url: p.current_url || "",
      pagesVisited: p.pages_visited || 0,
      done: !!p.done
    }));
  };
  const mergeCrawlEvents = (liveEvents, threadEvents) => {
    const seen = new Set();
    return [...(liveEvents || []), ...threadEvents].filter(event => {
      const key = `${event.username || ""}:${event.url || ""}:${event.pagesVisited || 0}:${event.done ? 1 : 0}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };
  const agentCrawlEvents = agent => agent?.id === "crawler" ? mergeCrawlEvents(agent.crawlEvents || [], crawlEventsFromRun()) : [];
  const compactAgentText = (value, max = 180) => {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > max ? text.slice(0, max - 1) + "…" : text;
  };
  const thinkingStepTitle = entry => {
    const step = entry.data?.step;
    const prefix = step ? `Step ${step}` : "Step";
    const message = String(entry.message || "").replace(/^Step\s+\d+:\s*/i, "").trim();
    const isDuplicateStep = value => !value || /^Step\s+\d+$/i.test(String(value).trim());
    let detail = entry.data?.payload_purpose || entry.data?.hypothesis || entry.data?.observation || entry.data?.payload_summary || message;
    if (isDuplicateStep(detail)) {
      if (entry.data?.tool) {
        detail = `Context tool: ${entry.data.tool}`;
      } else if (entry.data?.method && entry.data?.url) {
        detail = `${entry.data.method} ${truncUrl(entry.data.url, 110)}${entry.data.status !== undefined ? ` → ${entry.data.status}` : ""}`;
      } else if (message && !isDuplicateStep(message)) {
        detail = message;
      } else if (entry.status === "deciding") {
        detail = "LLM deciding next action";
      } else {
        detail = "Reviewing scan state";
      }
    }
    const cleaned = compactAgentText(detail || "Reviewing next action");
    return `${prefix}: ${cleaned}`;
  };
  const thinkingStepOutcome = entry => {
    const parts = [];
    if (entry.data?.tool) parts.push(`Tool: ${entry.data.tool}`);
    if (entry.data?.method && entry.data?.url) parts.push(`${entry.data.method}: ${truncUrl(entry.data.url, 120)}`);
    if (entry.data?.observation) parts.push(`Observed: ${compactAgentText(entry.data.observation, 140)}`);
    if (entry.data?.hypothesis) parts.push(`Hypothesis: ${compactAgentText(entry.data.hypothesis, 140)}`);
    if (entry.data?.payload_purpose) parts.push(`Purpose: ${compactAgentText(entry.data.payload_purpose, 140)}`);
    if (entry.data?.payload_summary) parts.push(`Payload: ${compactAgentText(entry.data.payload_summary, 120)}`);
    if (entry.data?.status !== undefined) parts.push(`Status: ${entry.data.status}`);
    return parts.join(" · ");
  };
  const testLeadHistory = () => activityLog.filter(entry => entry.phase === "thinking_step").map(entry => ({
    ts: entry._ts || "--:--:--",
    task: thinkingStepTitle(entry),
    outcome: thinkingStepOutcome(entry)
  }));
  const agentTaskHistory = agent => agent?.id === "scanner" && testLeadHistory().length ? testLeadHistory() : agent?.taskHistory || [];
  const agentCurrentTask = agent => {
    agent = normalizeAgentForRun(agent);
    const crawlEvents = agentCrawlEvents(agent);
    if (agent?.id === "crawler" && crawlEvents.length) {
      if (agent.status !== "active") {
        const label = run?.status === "failed" ? "Crawl failed" : run?.status === "stopped" ? "Crawl stopped" : run?.status === "complete" ? "Crawl complete" : "Crawl is not running";
        return agent.outcome ? `${label} · ${agent.outcome}` : label;
      }
      const active = [...crawlEvents].reverse().find(h => !h.done && h.url);
      const latest = active || crawlEvents[crawlEvents.length - 1];
      if (latest.done) return `Completed crawl as ${latest.username || "anonymous"} (${latest.pagesVisited || 0} pg)`;
      return `Crawling ${truncUrl(latest.url || "", 88)} as ${latest.username || "anonymous"}`;
    }
    if (agent?.id === "scanner" && testLeadHistory().length) {
      if (agent.status !== "active") return "Standing by";
      return testLeadHistory()[testLeadHistory().length - 1].task;
    }
    return agent?.currentTask || "Waiting for work";
  };
  const agentStatusLabel = agent => {
    if (agent?.status === "active") return "ACTIVE";
    if (agent?.status === "idle") return "IDLE";
    if (agent?.status === "failed") return "FAILED";
    return "COMPLETE";
  };
  const upsertAgent = (items, patch, histEntry = null) => {
    const normalized = {
      ...patch,
      role: patch.id === "crawler" ? "Crawler" : patch.id === "scanner" ? "Test Lead" : patch.role
    };
    const idx = items.findIndex(a => a.id === normalized.id);
    if (idx === -1) {
      return [...items, {
        ...normalized,
        taskHistory: histEntry ? [histEntry] : [],
        crawlEvents: normalized.crawlEvents || []
      }];
    }
    const updated = [...items];
    const prev = updated[idx];
    updated[idx] = {
      ...prev,
      ...normalized,
      taskHistory: histEntry ? [...(prev.taskHistory || []), histEntry].slice(-200) : prev.taskHistory || [],
      crawlEvents: normalized.crawlEvents || prev.crawlEvents || []
    };
    return updated;
  };

  // Seed activity log from persisted DB entries on mount so it survives navigation.
  useEffect(() => {
    api.getScanLog(runId).then(entries => {
      if (!entries || entries.length === 0) return;
      setActivityLog(entries.map(e => {
        const ts = e._persisted_at ? parseDate(e._persisted_at).toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        }) : "--:--:--";
        return {
          ...e,
          _ts: ts,
          _id: "db-" + e._persisted_at + "-" + e.phase + "-" + e.status
        };
      }));
      // Restore site plan data from persisted log.
      const planComplete = entries.find(e => e.phase === "site_plan" && e.status === "complete" && e.data);
      if (planComplete) setSitePlanData(planComplete.data);
    }).catch(() => {});
  }, [runId]);

  // Seed agents panel from persisted DB entries on mount.
  // Also fetches the live scan status so stale "active" agents left by a
  // force-killed process are reconciled back to "idle" immediately.
  useEffect(() => {
    Promise.all([api.getAgentLog(runId), api.getThinkingStatus(runId)]).then(([entries, scanStatus]) => {
      if (!entries || entries.length === 0) return;
      const scanRunning = isDynamicScanActive(scanStatus?.status);
      const agentsMap = new Map();
      for (const e of entries) {
        const entryTs = e.created_at ? parseDate(e.created_at).toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        }) : "--:--:--";
        const role = e.agent_id === "crawler" ? "Crawler" : e.agent_id === "scanner" ? "Test Lead" : e.role;
        const existing = agentsMap.get(e.agent_id) || {
          id: e.agent_id,
          role,
          status: e.status,
          currentTask: e.current_task,
          taskHistory: [],
          crawlEvents: []
        };
        existing.status = e.status;
        existing.role = role;
        existing.currentTask = e.current_task;
        existing.taskHistory.push({
          ts: entryTs,
          task: e.current_task,
          outcome: e.outcome
        });
        agentsMap.set(e.agent_id, existing);
      }
      // If no scan is running, reset any stale "active" agents to "idle".
      if (!scanRunning) {
        for (const [id, agent] of agentsMap) {
          if (agent.status === "active" && id !== "crawler") {
            agentsMap.set(id, {
              ...agent,
              status: "idle"
            });
          }
        }
      }
      setAgents([...agentsMap.values()]);
    }).catch(() => {});
  }, [runId]);

  // Load token usage from the API on mount (in-process memory, best effort).
  useEffect(() => {
    api.getTokenUsage(runId).then(d => {
      if (d) setTokenUsage(d);
    }).catch(() => {});
  }, [runId]);

  // Auto-scroll activity feed when new entries arrive
  useEffect(() => {
    if (activeTab !== "activity" || !activityFeedRef.current) return;
    activityFeedRef.current.scrollTop = activityFeedRef.current.scrollHeight;
  }, [activityLog.length, activeTab]);

  return {
    activityLog,
    setActivityLog,
    expandedLogIds,
    toggleLogId,
    activitySubTab,
    setActivitySubTab,
    agents,
    setAgents,
    tokenUsage,
    setTokenUsage,
    tokenExpanded,
    setTokenExpanded,
    sitePlanData,
    setSitePlanData,
    activityFeedRef,
    upsertAgent,
    normalizeAgentForRun,
    defaultAgentRoster,
    representsAgent,
    agentRoleLabel,
    agentCurrentTask,
    agentCrawlEvents,
    agentTaskHistory,
    agentStatusLabel
  };
}
