import { isDynamicScanActive } from "../../shared/runs/presentation.jsx";
import { truncUrl } from "../../shared/lib/urls.js";
import { parseDate } from "../../shared/lib/dates.js";
export function activityPresentation({ run, thinkingStatus, aliceIsThinking, activityLog }) {
  const agentRoleLabel = (agent) => {
    if (agent?.id === "crawler") return "Crawler";
    if (agent?.id === "scanner") return "Test Lead";
    if (agent?.id === "alice") return "A.L.I.C.E";
    return agent?.role || "Agent";
  };
  const normalizeAgentForRun = (agent) => {
    if (agent?.id !== "crawler") return agent;
    return agent;
  };
  const defaultAgentRoster = () => [
    {
      id: "alice",
      role: "A.L.I.C.E",
      status: aliceIsThinking ? "active" : "idle",
      currentTask: aliceIsThinking ? "Processing directive..." : "Waiting for instruction",
    },
    {
      id: "crawler",
      role: "Crawler",
      status: "idle",
      currentTask: "Waiting for crawl",
    },
    {
      id: "scanner",
      role: "Test Lead",
      status: isDynamicScanActive(thinkingStatus?.status) ? "active" : "idle",
      currentTask: isDynamicScanActive(thinkingStatus?.status)
        ? "Coordinating pentest"
        : "Standing by",
    },
    {
      id: "specialist",
      role: "Specialist",
      status: "idle",
      currentTask: "No specialist dispatched",
    },
    {
      id: "burp",
      role: "Burp",
      status: "idle",
      currentTask: "No active scan dispatched",
    },
    {
      id: "validator",
      role: "Validator",
      status: "idle",
      currentTask: "No validation running",
    },
    {
      id: "reporting",
      role: "Reporting",
      status:
        thinkingStatus?.status === "analysing" || thinkingStatus?.status === "analyzing"
          ? "active"
          : "idle",
      currentTask:
        thinkingStatus?.status === "analysing" || thinkingStatus?.status === "analyzing"
          ? "Analysing probe results…"
          : "Standing by",
    },
  ];
  const representsAgent = (agent, placeholder) => {
    if (agent.id === placeholder.id) return true;
    if (placeholder.id === "burp") return agent.role === "Burp" || agent.id?.startsWith("burp-");
    if (placeholder.id === "validator")
      return agent.role === "Validator" || agent.id?.startsWith("validator-");
    if (placeholder.id === "specialist")
      return agent.role === "Specialist" || agent.id?.startsWith("specialist-");
    if (placeholder.id === "reporting")
      return agent.role === "Reporting" || agent.id === "reporting";
    return false;
  };
  const fmtEventTime = (value) => {
    if (!value) return "--:--:--";
    try {
      return parseDate(value).toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return "--:--:--";
    }
  };
  const crawlEventsFromRun = () => {
    const progress = run?.per_user_progress || {};
    const labelByUsername = new Map(
      (run?.credentials || []).map((c) => [c.username, c.label || c.username]),
    );
    return Object.entries(progress)
      .filter(([, p]) => p && (p.current_url || p.done || p.pages_visited))
      .map(([username, p]) => ({
        ts: fmtEventTime(p.updated_at),
        username: labelByUsername.get(username) || username || "anonymous",
        url: p.current_url || "",
        pagesVisited: p.pages_visited || 0,
        done: !!p.done,
        stage: p.stage || (p.done ? "phase_complete" : "page_visit"),
        stageLabel: p.stage_label || (p.done ? "Credential phase complete" : "Opening page"),
        phaseIndex: p.phase_index,
        phaseTotal: p.phase_total,
      }));
  };
  const crawlEventsFromActivityLog = () =>
    activityLog
      .filter(
        (entry) =>
          ["crawl", "reconcile"].includes(entry.phase) &&
          entry.data?.stage &&
          (entry.page_url || entry.data?.username),
      )
      .map((entry) => ({
        ts: entry._ts || "--:--:--",
        username: entry.data?.username || "",
        url: entry.page_url || "",
        pagesVisited: entry.data?.pages_visited || 0,
        done: entry.data?.stage === "phase_complete",
        stage: entry.data.stage,
        stageLabel: entry.data.stage_label || entry.message,
        phaseIndex: entry.data.phase_index,
        phaseTotal: entry.data.phase_total,
        task: entry.message,
      }));
  const mergeCrawlEvents = (liveEvents, threadEvents) => {
    const seen = new Set();
    return [...(liveEvents || []), ...threadEvents].filter((event) => {
      const key = `${event.username || ""}:${event.url || ""}:${event.pagesVisited || 0}:${event.stage || ""}:${event.done ? 1 : 0}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };
  const agentCrawlEvents = (agent) =>
    agent?.id === "crawler"
      ? mergeCrawlEvents(agent.crawlEvents || [], [
          ...crawlEventsFromRun(),
          ...crawlEventsFromActivityLog(),
        ])
      : [];
  const compactAgentText = (value, max = 180) => {
    const text = String(value || "")
      .replace(/\s+/g, " ")
      .trim();
    return text.length > max ? text.slice(0, max - 1) + "…" : text;
  };
  const thinkingStepTitle = (entry) => {
    const step = entry.data?.step;
    const prefix = step ? `Step ${step}` : "Step";
    const message = String(entry.message || "")
      .replace(/^Step\s+\d+:\s*/i, "")
      .trim();
    const isDuplicateStep = (value) => !value || /^Step\s+\d+$/i.test(String(value).trim());
    let detail =
      entry.data?.payload_purpose ||
      entry.data?.hypothesis ||
      entry.data?.observation ||
      entry.data?.payload_summary ||
      message;
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
  const thinkingStepOutcome = (entry) => {
    const parts = [];
    if (entry.data?.tool) parts.push(`Tool: ${entry.data.tool}`);
    if (entry.data?.method && entry.data?.url)
      parts.push(`${entry.data.method}: ${truncUrl(entry.data.url, 120)}`);
    if (entry.data?.observation)
      parts.push(`Observed: ${compactAgentText(entry.data.observation, 140)}`);
    if (entry.data?.hypothesis)
      parts.push(`Hypothesis: ${compactAgentText(entry.data.hypothesis, 140)}`);
    if (entry.data?.payload_purpose)
      parts.push(`Purpose: ${compactAgentText(entry.data.payload_purpose, 140)}`);
    if (entry.data?.payload_summary)
      parts.push(`Payload: ${compactAgentText(entry.data.payload_summary, 120)}`);
    if (entry.data?.status !== undefined) parts.push(`Status: ${entry.data.status}`);
    return parts.join(" · ");
  };
  const testLeadHistory = () =>
    activityLog
      .filter((entry) => entry.phase === "thinking_step")
      .map((entry) => ({
        ts: entry._ts || "--:--:--",
        task: thinkingStepTitle(entry),
        outcome: thinkingStepOutcome(entry),
      }));
  const agentTaskHistory = (agent) =>
    agent?.id === "scanner" && testLeadHistory().length
      ? testLeadHistory()
      : agent?.taskHistory || [];
  const formatCrawlEvent = (event) => {
    const phaseLabel =
      event.phaseIndex && event.phaseTotal
        ? `Phase ${event.phaseIndex}/${event.phaseTotal} · `
        : "";
    if (event.done)
      return `${phaseLabel}Completed crawl as ${event.username || "anonymous"} (${event.pagesVisited || 0} pg)`;
    if (event.task && !event.url) return event.task;
    return `${phaseLabel}${event.stageLabel || "Crawling"} · ${event.username || "anonymous"}${event.url ? `: ${truncUrl(event.url, 88)}` : ""}`;
  };
  const agentCurrentTask = (agent) => {
    agent = normalizeAgentForRun(agent);
    const crawlEvents = agentCrawlEvents(agent);
    const explicitCrawlerStage =
      agent?.id === "crawler" &&
      agent.status === "active" &&
      /^(?:Preparing|Authenticating|Signing in|Access check|Verifying page access|Finali[sz]ing crawl|Phase \d+\/\d+)/i.test(
        String(agent.currentTask || ""),
      );
    if (explicitCrawlerStage) return agent.currentTask;
    if (agent?.id === "crawler" && crawlEvents.length) {
      if (agent.status !== "active") {
        const label =
          run?.status === "failed"
            ? "Crawl failed"
            : run?.status === "stopped"
              ? "Crawl stopped"
              : run?.status === "complete"
                ? "Crawl complete"
                : "Crawl is not running";
        return agent.outcome ? `${label} · ${agent.outcome}` : label;
      }
      const active = [...crawlEvents].reverse().find((h) => !h.done && h.url);
      const latest = active || crawlEvents[crawlEvents.length - 1];
      return formatCrawlEvent(latest);
    }
    // Lifecycle updates are emitted by the backend after the Test Lead has
    // delegated probe analysis (and again once every finalisation phase ends).
    // They must take precedence over the last per-step activity-log entry,
    // otherwise the UI incorrectly keeps showing "Step N: LLM deciding…".
    const lifecycleTasks = new Set([
      // Keep scans that were already running during the wording update visible.
      "Handed probe analysis to Reporting",
      "Testing complete - handed traffic to reporting agent for analysis...",
      "Scan complete",
      "Scan stopped",
    ]);
    if (agent?.id === "scanner" && lifecycleTasks.has(agent.currentTask)) {
      return agent.currentTask;
    }
    if (agent?.id === "scanner" && testLeadHistory().length) {
      if (agent.status !== "active") return "Standing by";
      return testLeadHistory()[testLeadHistory().length - 1].task;
    }
    return agent?.currentTask || "Waiting for work";
  };
  const agentStatusLabel = (agent) => {
    if (agent?.status === "active") return "ACTIVE";
    if (agent?.status === "idle") return "IDLE";
    if (agent?.status === "failed") return "FAILED";
    return "COMPLETE";
  };
  return {
    normalizeAgentForRun,
    defaultAgentRoster,
    representsAgent,
    agentRoleLabel,
    agentCurrentTask,
    agentCrawlEvents,
    agentTaskHistory,
    agentStatusLabel,
  };
}
