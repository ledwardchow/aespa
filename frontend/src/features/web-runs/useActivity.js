import { parseDate } from "../../shared/lib/dates.js";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { useState, useEffect, useCallback } from "react";

import { isDynamicScanActive } from "../../shared/runs/presentation.jsx";

// Stored activity and usage data share the route event subscription.
// Display helpers and local interactions live with the activity components.
export function useActivity(runId) {
  const [activityLog, setActivityLog] = useState([]);
  const [agents, setAgents] = useState([]);
  const [tokenUsage, setTokenUsage] = useState(null); // {total_input, total_output, by_model}
  const [sitePlanData, setSitePlanData] = useState(null);

  const upsertAgent = useCallback((items, patch, histEntry = null) => {
    const normalized = {
      ...patch,
      role: patch.id === "crawler" ? "Crawler" : patch.id === "scanner" ? "Test Lead" : patch.role,
    };
    const idx = items.findIndex((a) => a.id === normalized.id);
    if (idx === -1) {
      return [
        ...items,
        {
          ...normalized,
          taskHistory: histEntry ? [histEntry] : [],
          crawlEvents: normalized.crawlEvents || [],
        },
      ];
    }
    const updated = [...items];
    const prev = updated[idx];
    updated[idx] = {
      ...prev,
      ...normalized,
      taskHistory: histEntry
        ? [...(prev.taskHistory || []), histEntry].slice(-200)
        : prev.taskHistory || [],
      crawlEvents: normalized.crawlEvents || prev.crawlEvents || [],
    };
    return updated;
  }, []);

  // Seed activity log from persisted DB entries on mount so it survives navigation.
  useEffect(() => {
    webRunsApi
      .getScanLog(runId)
      .then((entries) => {
        entries = entries || [];
        setActivityLog(
          entries.map((e) => {
            const ts = e._persisted_at
              ? parseDate(e._persisted_at).toLocaleTimeString("en-US", {
                  hour12: false,
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })
              : "--:--:--";
            return {
              ...e,
              _ts: ts,
              _id: "db-" + e._persisted_at + "-" + e.phase + "-" + e.status,
            };
          }),
        );
        // Restore site plan data from persisted log.
        const planComplete = entries.find(
          (e) => e.phase === "site_plan" && e.status === "complete" && e.data,
        );
        if (planComplete) setSitePlanData(planComplete.data);
      })
      .catch(() => {});
  }, [runId]);

  // Seed agents panel from persisted DB entries on mount. Reconcile stale
  // active agents, while preserving validators whose managed validation task
  // is still running after the pentest itself has completed.
  useEffect(() => {
    Promise.all([
      webRunsApi.getAgentLog(runId),
      webRunsApi.getThinkingStatus(runId),
      webRunsApi.getValidateStatus(runId),
      webRunsApi.getCrawlStatus(runId).catch(() => null),
    ])
      .then(([entries, scanStatus, validationStatus, crawlStatus]) => {
        entries = entries || [];
        const scanRunning = isDynamicScanActive(scanStatus?.status);
        const validationRunning = validationStatus?.status === "running";
        const agentsMap = new Map();
        for (const e of entries) {
          const entryTs = e.created_at
            ? parseDate(e.created_at).toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })
            : "--:--:--";
          const role =
            e.agent_id === "crawler" ? "Crawler" : e.agent_id === "scanner" ? "Test Lead" : e.role;
          const existing = agentsMap.get(e.agent_id) || {
            id: e.agent_id,
            role,
            status: e.status,
            currentTask: e.current_task,
            taskHistory: [],
            crawlEvents: [],
          };
          existing.status = e.status;
          existing.role = role;
          existing.currentTask = e.current_task;
          existing.taskHistory.push({
            ts: entryTs,
            task: e.current_task,
            outcome: e.outcome,
          });
          agentsMap.set(e.agent_id, existing);
        }
        const crawler = agentsMap.get("crawler");
        if (crawlStatus?.running) {
          agentsMap.set("crawler", {
            id: "crawler",
            role: "Crawler",
            currentTask: crawler?.currentTask || "Crawling application…",
            taskHistory: crawler?.taskHistory || [],
            crawlEvents: crawler?.crawlEvents || [],
            ...crawler,
            status: "active",
          });
        } else if (crawler?.status === "active") {
          agentsMap.set("crawler", {
            ...crawler,
            status: "idle",
            currentTask: "Crawl is not running",
          });
        }
        // If no scan is running, reset stale "active" agents to "idle". A
        // validator is an exception: it can legitimately continue after scan
        // completion when the user clicked Validate Issues.
        if (!scanRunning) {
          for (const [id, agent] of agentsMap) {
            const activeValidator =
              validationRunning && (id.startsWith("validator-") || agent.role === "Validator");
            if (agent.status === "active" && id !== "crawler" && !activeValidator) {
              agentsMap.set(id, {
                ...agent,
                status: "idle",
              });
            }
          }
        }
        setAgents([...agentsMap.values()]);
      })
      .catch(() => {});
  }, [runId]);

  // Load token usage from the API on mount (in-process memory, best effort).
  useEffect(() => {
    webRunsApi
      .getTokenUsage(runId)
      .then((d) => {
        if (d) setTokenUsage(d);
      })
      .catch(() => {});
  }, [runId]);

  return {
    activityLog,
    setActivityLog,
    agents,
    setAgents,
    tokenUsage,
    setTokenUsage,
    sitePlanData,
    setSitePlanData,
    upsertAgent,
  };
}
