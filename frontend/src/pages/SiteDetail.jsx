import { ALICE_DEDUP_DIRECTIVE, OWASP_WEB_LABELS } from "./SiteDetail/_constants";
import { ScopeHostsPanel } from "./Settings/ScopeHostsPanel";
import { useState, useEffect, useRef, useCallback, useContext } from "react";
import { api, formatError } from "../lib/api";
import { nav } from "../lib/router";
import { renderAliceBlocks, renderMarkdown, parseAliceTurnSegments, renderAliceTraceBox } from "../lib/aliceSession";
import { useAliceChat } from "./SiteDetail/useAliceChat";
import { parseDate, fmtDate, truncUrl, sourceLabel, apiTranscriptText, markdownListValue, slugForFilename, leadsExportFilename, markdownExportFilename, downloadTextFile, findingsToMarkdown, workProgramToMarkdown, parseFindingsMarkdown, markdownBullet, stripMarkdownFence } from "../lib/utilities";
import { IconApis, IconPlus, IconPlay, IconStop, IconChevronLeft, IconBug, IconSend } from "../components/Icons";
import * as d3 from "d3";
import { WebRunFindingsTab } from "./SiteDetail/WebRunFindingsTab";
import { WebRunActivityTab } from "./SiteDetail/WebRunActivityTab";
import { WebRunTrafficTab } from "./SiteDetail/WebRunTrafficTab";
import { WebRunSitemapTab } from "./SiteDetail/WebRunSitemapTab";
import { GuidedLoginItem } from "./SiteDetail/GuidedLoginItem";
import { scopeColor, isDynamicScanActive, userColor, runWorkflowStatus, workflowBadge, useColResize } from "./SiteDetail/_helpers";
export { SiteForm } from "./SiteDetail/SiteForm";
export { useColResize };
// ── Site detail ───────────────────────────────────────────────────────────────

export function SiteDetail({
  siteId
}) {
  const [site, setSite] = useState(null);
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);
  const [editingRun, setEditingRun] = useState(null); // run object being edited
  const [editForm, setEditForm] = useState({});
  const [editProfiles, setEditProfiles] = useState([]);
  const [editSaving, setEditSaving] = useState(false);
  const load = useCallback(async () => {
    try {
      const [s, r, p] = await Promise.all([api.getSite(siteId), api.listRuns(siteId), api.listLLMProfiles()]);
      setSite(s);
      setRuns(r);
      setEditProfiles(p || []);
    } catch (e) {
      setError(e.message);
    }
  }, [siteId]);
  useEffect(() => {
    load();
  }, [load]);
  const openEdit = run => {
    setEditForm({
      max_depth: run.max_depth,
      max_pages: run.max_pages,
      llm_profile_id: run.llm_profile_id || ""
    });
    setEditingRun(run);
  };
  const saveEdit = async () => {
    setEditSaving(true);
    try {
      const updated = await api.updateRun(editingRun.id, {
        max_depth: Number(editForm.max_depth),
        max_pages: Number(editForm.max_pages),
        llm_profile_id: editForm.llm_profile_id ? Number(editForm.llm_profile_id) : null
      });
      setRuns(rs => rs.map(r => r.id === updated.id ? updated : r));
      setEditingRun(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setEditSaving(false);
    }
  };
  const deleteRun = async run => {
    if (!confirm(`Delete run "${run.name}"?`)) return;
    try {
      await api.deleteRun(run.id);
      setRuns(r => r.filter(x => x.id !== run.id));
    } catch (e) {
      setError(e.message);
    }
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href="#/" style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>Sites</a>
        <span className="breadcrumb-sep"> / </span>
        {site ? site.name : "…"}
      </div>
      <div className="topbar-actions">
        {site && <button className="btn secondary" onClick={() => nav(`#/sites/${siteId}/edit`)}>Edit site</button>}
        <button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}><IconPlus /> New run</button>
      </div>
    </div>
    <div className="content scroll-content stack">
      {error && <div className="alert error">{error}</div>}

      {editingRun && <div className="card" style={{
        padding: "20px 24px",
        border: "1px solid var(--accent)",
        marginBottom: 8
      }}>
          <div style={{
          fontWeight: 700,
          marginBottom: 14
        }}>Edit run: {editingRun.name}</div>
          <div className="two-col" style={{
          gap: 12,
          marginBottom: 12
        }}>
            <div className="field" style={{
            margin: 0
          }}>
              <label>Max depth</label>
              <input type="number" min="1" max="10" value={editForm.max_depth} onInput={e => setEditForm(f => ({
              ...f,
              max_depth: e.target.value
            }))} style={{
              width: 80
            }} />
            </div>
            <div className="field" style={{
            margin: 0
          }}>
              <label>Max pages</label>
              <input type="number" min="5" max="500" value={editForm.max_pages} onInput={e => setEditForm(f => ({
              ...f,
              max_pages: e.target.value
            }))} style={{
              width: 90
            }} />
            </div>
          </div>
          <div className="field" style={{
          marginBottom: 14
        }}>
            <label>LLM profile <span className="field-optional">(leave blank to use the globally active profile)</span></label>
            <select className="select" value={editForm.llm_profile_id || ""} onChange={e => setEditForm(f => ({
            ...f,
            llm_profile_id: e.target.value
          }))}>
              <option value="">— Use global active profile —</option>
              {editProfiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="row" style={{
          gap: 8
        }}>
            <button className="btn sm" onClick={saveEdit} disabled={editSaving}>{editSaving ? "Saving…" : "Save"}</button>
            <button className="btn ghost sm" onClick={() => setEditingRun(null)}>Cancel</button>
          </div>
        </div>}

      {site && <div className="card" style={{
        padding: "16px 20px"
      }}>
          <div className="row spread">
            <div className="stack" style={{
            gap: 4
          }}>
              <div style={{
              fontSize: 13,
              color: "var(--muted)"
            }}>Base URL</div>
              <div className="mono" style={{
              fontSize: 13
            }}>{site.base_url}</div>
            </div>
            <div className="row" style={{
            gap: 16
          }}>
              {site.requires_auth ? <span className="badge ok">auth required</span> : <span className="badge neutral">no auth</span>}
              <span className="subtle">{site.credentials.length} credential{site.credentials.length !== 1 ? "s" : ""}</span>
            </div>
          </div>
          {site.notes && <div style={{
          marginTop: 10,
          fontSize: 13,
          color: "var(--muted)"
        }}>{site.notes}</div>}
          {site.scan_guidance && <div style={{
          marginTop: 8,
          fontSize: 13,
          color: "var(--muted)"
        }}><strong>Test Lead guidance:</strong> {site.scan_guidance}</div>}
          {site.requires_auth && site.credentials.length > 0 && <>
            <div className="site-credentials-list">
              {site.credentials.map(c => <div key={c.id} className="site-credential-row">
                  <div>
                    <div className="site-credential-name">{c.label || c.username}</div>
                    {c.label && <div className="site-credential-user">{c.username}</div>}
                  </div>
                  <div className="site-credential-login mono">
                    {c.login_url || site.login_url || "No login URL"}
                  </div>
                </div>)}
            </div>
            {site.credentials.some(c => c.auth_mode === "guided") && <div style={{
            marginTop: 8,
            padding: "8px 12px",
            background: "var(--surface-2,#2a2a2a)",
            border: "1px solid var(--warn,#f59e0b)",
            borderRadius: 5,
            fontSize: 12,
            color: "var(--warn,#f59e0b)"
          }}>
                ⚠️ This site is configured with interactive browser login credentials, which only works if you're running this scanner on your local machine with a GUI. It will not function if the scanner is installed on a headless host (i.e. server).
              </div>}</>}
        </div>}

      <div>
        <div className="row spread" style={{
          marginBottom: 12
        }}>
          <div style={{
            fontSize: 13,
            fontWeight: 700,
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.6px"
          }}>Test Runs</div>
        </div>
        {runs === null && <div className="subtle">Loading…</div>}
        {runs !== null && runs.length === 0 && <div className="empty-state" style={{
          padding: "32px"
        }}>
            <div className="empty-msg">No test runs yet</div>
            <div className="empty-sub">Create a new run to start crawling this site.</div>
            <button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}><IconPlus /> New run</button>
          </div>}
        {runs && runs.length > 0 && <div className="table-wrap">
            <table>
              <colgroup>
                <col style={{
                width: "35%"
              }} /><col style={{
                width: "18%"
              }} /><col style={{
                width: "10%"
              }} /><col style={{
                width: "16%"
              }} /><col style={{
                width: "21%"
              }} />
              </colgroup>
              <thead><tr><th>Name</th><th>Status</th><th>Pages</th><th>Created</th><th></th></tr></thead>
              <tbody>{runs.map(r => <tr key={r.id}>
                  <td>
                    <strong>{r.name}</strong>
                    {r.llm_profile_id && <div style={{
                    fontSize: 11,
                    color: "var(--muted)",
                    marginTop: 2
                  }}>{(editProfiles.find(p => p.id === r.llm_profile_id) || {
                      name: "Profile #" + r.llm_profile_id
                    }).name}</div>}
                  </td>
                  <td>{workflowBadge(r)}</td>
                  <td>{r.pages_discovered}</td>
                  <td className="subtle">{fmtDate(r.created_at)}</td>
                  <td>
                    <div className="row" style={{
                    justifyContent: "flex-end"
                  }}>
                      <button className="btn secondary sm" onClick={() => nav(`#/runs/${r.id}`)}>Open</button>
                      <button className="btn secondary sm" onClick={() => openEdit(r)}>Edit</button>
                      <button className="btn danger-outline sm" onClick={() => deleteRun(r)}>Delete</button>
                    </div>
                  </td>
                </tr>)}
              </tbody>
            </table>
          </div>}
      </div>
    </div>
  </>;
}

// ── Site form (create/edit) ───────────────────────────────────────────────────

export function TestRunDetail({
  runId,
  initialTab
}) {
  const [run, setRun] = useState(null);
  const [siteName, setSiteName] = useState(null);
  const [graph, setGraph] = useState(null);
  const [selectedNode, setSelNode] = useState(null);
  const [pageDetail, setPageDetail] = useState(null);
  const [pageViews, setPageViews] = useState([]);
  const [cascade, setCascade] = useState(false);
  const [scopeBusy, setScopeBusy] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab || "activity");
  const [scopeHosts, setScopeHosts] = useState([]);
  const [graphView, setGraphView] = useState("scope"); // "scope" | "user"
  const [targetIntel, setTargetIntel] = useState(null);
  const [targetIntelKind, setTargetIntelKind] = useState("");
  const [taskGraph, setTaskGraph] = useState(null);
  const [reconSummary, setReconSummary] = useState(null);
  const [tasksSubTab, setTasksSubTab] = useState("attack-surface"); // "attack-surface" | "task-queue"
  const [scannerSessions, setScannerSessions] = useState(null);
  const [crawlUsername, setCrawlUsername] = useState(null);
  const [clearBusy, setClearBusy] = useState(""); // which section is clearing
  const [,setClearError] = useState(null);
  // per-user crawl progress is read directly from run.per_user_progress (kept in sync
  // by the periodic poll + SSE run_update events) — no separate state needed.
  const [editingSettings, setEditingSettings] = useState(false);
  const [editDepth, setEditDepth] = useState("");
  const [editPages, setEditPages] = useState("");
  const [editLlmProfileId, setEditLlmProfileId] = useState(null);
  const [runProfiles, setRunProfiles] = useState([]);

  // Guided login: list of {credential_id, username} waiting for "I'm Done" confirmation
  const [guidedLoginPending, setGuidedLoginPending] = useState([]);
  const [guidedLoginErrors, setGuidedLoginErrors] = useState([]);

  // Load LLM profiles once so the read-only display and edit dropdown both work.
  useEffect(() => {
    api.listLLMProfiles().then(setRunProfiles).catch(() => {});
  }, []);
  const [activityLog, setActivityLog] = useState([]);
  const [expandedLogIds, setExpandedLogIds] = useState(new Set());
  const toggleLogId = id => setExpandedLogIds(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });
  const [activitySubTab, setActivitySubTab] = useState("agents");
  const [agents, setAgents] = useState([]);
  const [collapsedAgentIds, setCollapsedAgentIds] = useState(new Set());
  const toggleAgentId = aid => setCollapsedAgentIds(prev => {
    const next = new Set(prev);
    next.has(aid) ? next.delete(aid) : next.add(aid);
    return next;
  });
  const {
    aliceChats,
    setAliceChats,
    activeAliceTabId,
    setActiveAliceTabId,
    aliceInputText,
    setAliceInputText,
    aliceChatHeight,
    aliceThinkingTabId,
    aliceIsThinking,
    aliceGlobalRunning,
    aliceExpandedThinkIds,
    setAliceExpandedThinkIds,
    aliceMessages,
    createAliceTab,
    deleteAliceTab,
    startAliceResize,
    handleAliceStop,
    handleAliceSend,
    submitAliceDirective
  } = useAliceChat(runId, {
    onActivate: () => setCollapsedAgentIds(prev => {
      if (!prev.has("alice")) return prev;
      const next = new Set(prev);
      next.delete("alice");
      return next;
    })
  });
  const [tokenUsage, setTokenUsage] = useState(null); // {total_input, total_output, by_model}
  const [tokenExpanded, setTokenExpanded] = useState(false);
  const [sitePlanData, setSitePlanData] = useState(null);
  const activityFeedRef = useRef(null);
  const [crawlStopRequested, setCrawlStopRequested] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState(null);
  const [thinkingStopRequested, setThinkingStopReq] = useState(false);
  const [coverageMode, setCoverageMode] = useState("track");
  const [wpReloadKey, setWpReloadKey] = useState(0); // bump to force workprogram reload
  const [checkpointStatus, setCheckpointStatus] = useState(null);
  const [validateStatus, setValidateStatus] = useState(null);
  const [validateBusy, setValidateBusy] = useState(false);
  const [dedupeBusy, setDedupeBusy] = useState(false);
  const [findings, setFindings] = useState([]);
  const [expandedFinding, setExpandedFinding] = useState(null);
  const [editingFinding, setEditingFinding] = useState(null); // finding id being edited
  const [editDraft, setEditDraft] = useState(null); // working copy of the edited finding
  const [editBusy, setEditBusy] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState(new Set(["__unconfirmed__"]));
  const toggleGroup = title => setExpandedGroups(prev => {
    const next = new Set(prev);
    next.has(title) ? next.delete(title) : next.add(title);
    return next;
  });
  const [traffic, setTraffic] = useState([]);

  const [trafficTotal, setTrafficTotal] = useState(0);
  const [selectedTraffic, setSelectedTraffic] = useState(null);

  
  
  
  
  
  const lastTrafficIdRef = useRef(0);
  const issueImportInputRef = useRef(null);
  const [error, setError] = useState(null);
  const svgRef = useRef(null);
  const simRef = useRef(null);
  const prevGraphKeyRef = useRef("");
  const lastRunPollOkRef = useRef(Date.now());
  const [findColW, startFindResize] = useColResize("colw:findings", [80, 52, null, 28, 60]);
  const [trafficColW, startTrafficResize] = useColResize("colw:traffic:v2", [30, 88, 68, 70, 62, 52, null, 66]);

  // Initial load
  const loadAll = useCallback(async () => {
    try {
      const [r, g] = await Promise.all([api.getRun(runId), api.getGraph(runId)]);
      setRun(r);
      setGraph(g);
      if (r?.scope_hosts) setScopeHosts(r.scope_hosts);
      if (r?.coverage_mode) setCoverageMode(r.coverage_mode);
      api.getThinkingStatus(runId).then(setThinkingStatus).catch(() => {});
      api.getCheckpointStatus(runId).then(setCheckpointStatus).catch(() => {});
      api.getSite(r.site_id).then(s => setSiteName(s.name)).catch(() => {});
    } catch (e) {
      setError(e.message);
    }
  }, [runId]);
  useEffect(() => {
    loadAll();
  }, [loadAll]);
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

  // SSE: receive incremental graph + status updates — no graph polling needed
  useEffect(() => {
    const es = new EventSource(`/api/test-runs/${runId}/events`);
    es.onmessage = msg => {
      let evt;
      try {
        evt = JSON.parse(msg.data);
      } catch {
        return;
      }
      if (evt.type === "page_added") {
        setGraph(prev => {
          if (!prev) return prev;
          const exists = prev.nodes.some(n => n.id === evt.node.id);
          if (exists) return prev;
          const node = {
            ...evt.node,
            accessible_by: evt.node.accessible_by || []
          };
          const newLinks = evt.link ? [...prev.links, evt.link] : prev.links;
          return {
            nodes: [...prev.nodes, node],
            links: newLinks
          };
        });
      } else if (evt.type === "crawl_phase") {
        setCrawlUsername(evt.username || null);
      } else if (evt.type === "node_accessible_by") {
        api.getGraph(runId).then(setGraph).catch(() => {});
      } else if (evt.type === "run_update") {
        setRun(prev => prev ? {
          ...prev,
          status: evt.status ?? prev.status,
          pages_discovered: evt.pages_discovered ?? prev.pages_discovered
        } : prev);
        if (evt.status && evt.status !== "running") setCrawlStopRequested(false);
        if (evt.username !== undefined) setCrawlUsername(evt.username || null);
      } else if (evt.type === "crawl_progress") {
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        setAgents(prev => {
          const username = evt.username || "anonymous";
          const crawlEvent = {
            ts,
            username,
            url: evt.current_url || "",
            pagesVisited: evt.pages_visited || 0,
            done: !!evt.done
          };
          const idx = prev.findIndex(a => a.id === "crawler");
          const existingEvents = idx >= 0 ? prev[idx].crawlEvents || [] : [];
          const crawlEvents = [...existingEvents, crawlEvent].slice(-200);
          const currentTask = evt.done ? `Completed crawl as ${username} (${evt.pages_visited || 0} pg)` : `Crawling ${truncUrl(evt.current_url || "", 88)} as ${username}`;
          return upsertAgent(prev, {
            id: "crawler",
            role: "Crawler",
            status: "active",
            currentTask,
            crawlEvents
          });
        });
        // crawl_progress is still used for the done flag
        if (evt.username && evt.done) {
          setRun(prev => {
            if (!prev) return prev;
            const pup = {
              ...(prev.per_user_progress || {})
            };
            pup[evt.username] = {
              ...pup[evt.username],
              done: true
            };
            return {
              ...prev,
              per_user_progress: pup
            };
          });
        }
      } else if (evt.type === "node_scan_status") {
        setGraph(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            nodes: prev.nodes.map(n => n.id === evt.page_id ? {
              ...n,
              scan_status: evt.scan_status
            } : n)
          };
        });
      } else if (evt.type === "thinking_scan_update") {
        setThinkingStatus(evt);
        if (evt.status && !isDynamicScanActive(evt.status)) setThinkingStopReq(false);
      } else if (evt.type === "scanner_phase") {
        setActivityLog(prev => {
          const ts = new Date().toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
          });
          const entry = {
            ...evt,
            _ts: ts,
            _id: Date.now() + Math.random()
          };
          const next = [...prev, entry];
          return next.length > 500 ? next.slice(-500) : next;
        });
        if (evt.phase === "site_plan" && evt.status === "complete" && evt.data) {
          setSitePlanData(evt.data);
        }
      } else if (evt.type === "task_graph_update") {
        api.getTaskGraph(runId).then(setTaskGraph).catch(() => {});
      } else if (evt.type === "finding_validation_update") {
        setFindings(prev => prev.map(f => f.id === evt.finding_id ? {
          ...f,
          validation_status: evt.validation_status ?? f.validation_status,
          validation_note: evt.validation_note ?? f.validation_note,
          evidence_json: evt.evidence_json ?? f.evidence_json,
          evidence_items: evt.evidence_items ?? f.evidence_items,
          poc_command: evt.poc_command ?? f.poc_command,
          poc_setup: evt.poc_setup ?? f.poc_setup
        } : f));
        // Refresh validation status summary when an individual finding resolves.
        api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
      } else if (evt.type === "agent_status") {
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        setAgents(prev => {
          const histEntry = {
            ts,
            task: evt.current_task,
            outcome: evt.outcome
          };
          return upsertAgent(prev, {
            id: evt.agent_id,
            role: evt.role,
            status: evt.status,
            currentTask: evt.current_task,
            outcome: evt.outcome
          }, histEntry);
        });
      } else if (evt.type === "specialist_step") {
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        const agentId = evt.agent_id;
        if (agentId) {
          setAgents(prev => {
            const idx = prev.findIndex(a => a.id === agentId);
            const stepEntry = {
              ts,
              step: evt.step,
              action_type: evt.action_type,
              method: evt.method,
              url: evt.url,
              status: evt.status,
              observation: evt.observation
            };
            if (idx === -1) return prev;
            const updated = [...prev];
            const prev_agent = updated[idx];
            updated[idx] = {
              ...prev_agent,
              stepHistory: [...(prev_agent.stepHistory || []), stepEntry].slice(-200)
            };
            return updated;
          });
        }
      } else if (evt.type === "token_usage_update") {
        setTokenUsage(evt.totals);
      } else if (evt.type === "scope_hosts_updated") {
        setScopeHosts(evt.scope_hosts || []);
      } else if (evt.type === "guided_login_required") {
        setGuidedLoginPending(prev => {
          if (prev.some(p => p.credential_id === evt.credential_id)) return prev;
          return [...prev, {
            credential_id: evt.credential_id,
            username: evt.username,
            browserOpen: false
          }];
        });
      } else if (evt.type === "guided_login_browser_open") {
        setGuidedLoginPending(prev => prev.map(p => p.credential_id === evt.credential_id ? {
          ...p,
          browserOpen: true
        } : p));
      } else if (evt.type === "guided_login_failed") {
        setGuidedLoginErrors(prev => {
          if (prev.some(e => e.credential_id === evt.credential_id)) return prev;
          return [...prev, {
            credential_id: evt.credential_id,
            username: evt.username,
            message: evt.message
          }];
        });
        setGuidedLoginPending(prev => prev.filter(p => p.credential_id !== evt.credential_id));
      } else if (evt.type === "guided_login_confirmed") {
        setGuidedLoginPending(prev => prev.filter(p => p.credential_id !== evt.credential_id));
      }
    };
    es.onerror = () => {/* auto-reconnects */};
    return () => es.close();
  }, [runId]);

  // Poll run metadata (including per_user_progress current URLs) while crawling
  // or while the backend is unwinding after a stop request.
  useEffect(() => {
    if (run?.status !== "running" && !crawlStopRequested) return;
    const iv = setInterval(() => {
      api.getRun(runId).then(r => {
        lastRunPollOkRef.current = Date.now();
        setRun(r);
        if (r.status !== "running") {
          setAgents(prev => prev.map(a => a.id === "crawler" && a.status === "active" ? {
            ...a,
            status: "idle",
            currentTask: "Crawl is not running"
          } : a));
        }
        if (crawlStopRequested && r.completed_at) setCrawlStopRequested(false);
      }).catch(() => {
        setAgents(prev => prev.map(a => a.id === "crawler" && a.status === "active" ? {
          ...a,
          status: "idle",
          currentTask: "Crawler connection stale"
        } : a));
      });
    }, 2000);
    return () => clearInterval(iv);
  }, [run?.status, runId, crawlStopRequested]);

  // Poll findings when on findings tab.
  useEffect(() => {
    if (activeTab !== "findings") return;
    api.getFindings(runId).then(setFindings).catch(() => {});
    const iv = setInterval(() => {
      api.getFindings(runId).then(setFindings).catch(() => {});
    }, 4000);
    return () => clearInterval(iv);
  }, [runId, activeTab]);

  // Poll thinking-scan status independently.
  useEffect(() => {
    const active = isDynamicScanActive(thinkingStatus?.status) || thinkingStopRequested;
    if (!active) return;
    const iv = setInterval(() => {
      api.getThinkingStatus(runId).then(s => {
        setThinkingStatus(s);
        if (thinkingStopRequested && !isDynamicScanActive(s.status)) setThinkingStopReq(false);
        if (!isDynamicScanActive(s.status)) {
          api.getFindings(runId).then(setFindings).catch(() => {});
          // Refresh checkpoint status once the scan finishes so the Resume button
          // appears/disappears correctly without a page reload.
          api.getCheckpointStatus(runId).then(setCheckpointStatus).catch(() => {});
        }
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, [runId, thinkingStatus?.status, thinkingStopRequested]);

  // Poll validation status while validating is running
  useEffect(() => {
    if (validateStatus?.status !== "running" && activeTab !== "findings") return;
    const iv = setInterval(() => {
      api.getValidateStatus(runId).then(vs => {
        setValidateStatus(vs);
        if (vs.status !== "running") setValidateBusy(false);
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, [runId, validateStatus?.status, activeTab]);

  // Fetch findings when switching to findings tab
  useEffect(() => {
    if (activeTab !== "findings") return;
    api.getFindings(runId).then(setFindings).catch(() => {});
    api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
  }, [activeTab, runId]);
  useEffect(() => {
    if (activeTab !== "intelligence" && run?.status !== "running") return;
    const loadIntel = () => api.getTargetIntelligence(runId, targetIntelKind).then(setTargetIntel).catch(() => {});
    loadIntel();
    if (run?.status !== "running") return;
    const iv = setInterval(loadIntel, 4000);
    return () => clearInterval(iv);
  }, [activeTab, runId, targetIntelKind, run?.status]);
  useEffect(() => {
    const active = activeTab === "tasks" || isDynamicScanActive(thinkingStatus?.status);
    if (!active) return;
    const loadTasks = () => api.getTaskGraph(runId).then(setTaskGraph).catch(() => {});
    loadTasks();
    api.getReconSummary(runId).then(setReconSummary).catch(() => {});
    if (!isDynamicScanActive(thinkingStatus?.status)) return;
    const iv = setInterval(loadTasks, 4000);
    return () => clearInterval(iv);
  }, [activeTab, runId, thinkingStatus?.status]);
  useEffect(() => {
    const active = activeTab === "sessions" || isDynamicScanActive(thinkingStatus?.status);
    if (!active) return;
    const loadSessions = () => api.getScannerSessions(runId).then(setScannerSessions).catch(() => {});
    loadSessions();
    if (activeTab === "sessions" && !isDynamicScanActive(thinkingStatus?.status)) return;
    const iv = setInterval(loadSessions, 4000);
    return () => clearInterval(iv);
  }, [activeTab, runId, thinkingStatus?.status]);
  useEffect(() => {
    setTraffic([]);
    lastTrafficIdRef.current = 0;
    setSelectedTraffic(null);
    api.getTrafficCount(runId).then(r => setTrafficTotal(r.count || 0)).catch(() => {});
  }, [runId]);

  // Traffic log polling — always active while crawling or scanning; also when on the tab
  useEffect(() => {
    const poll = async () => {
      try {
        const entries = await api.getTraffic(runId, lastTrafficIdRef.current);
        if (entries.length > 0) {
          lastTrafficIdRef.current = entries[entries.length - 1].id;
          setTraffic(prev => {
            const base = prev.length;
            const stamped = entries.map((e, i) => ({
              ...e,
              _seq: base + i + 1
            }));
            const next = [...prev, ...stamped];
            return next.length > 2000 ? next.slice(-2000) : next;
          });
        }
        if (activeTab === "traffic" || entries.length > 0) {
          api.getTrafficCount(runId).then(r => setTrafficTotal(r.count || 0)).catch(() => {});
        }
      } catch  {}
    };
    const isActive = activeTab === "traffic" || run?.status === "running" || isDynamicScanActive(thinkingStatus?.status) || crawlStopRequested || thinkingStopRequested;
    if (!isActive) return;
    poll();
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, [activeTab, run?.status, thinkingStatus?.status, runId, crawlStopRequested, thinkingStopRequested]);

  // Auto-scroll activity feed when new entries arrive
  useEffect(() => {
    if (activeTab !== "activity" || !activityFeedRef.current) return;
    activityFeedRef.current.scrollTop = activityFeedRef.current.scrollHeight;
  }, [activityLog.length, activeTab]);

  // Fetch page detail when node selected
  useEffect(() => {
    if (!selectedNode) {
      setPageDetail(null);
      setPageViews([]);
      return;
    }
    let cancelled = false;
    const pageId = selectedNode.id;
    setPageDetail(null);
    setPageViews([]);
    api.getPage(runId, pageId).then(detail => {
      if (!cancelled && selectedNode.id === pageId) setPageDetail(detail);
    }).catch(() => {});
    api.getPageViews(runId, pageId).then(views => {
      if (!cancelled && selectedNode.id === pageId) setPageViews(views);
    }).catch(() => {
      if (!cancelled) setPageViews([]);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedNode, runId]);

  // Compute the fill colour for a graph node based on current view mode.
  const nodeColorFn = d => {
    if (graphView === "user") return userColor(d, run?.credentials);
    return scopeColor(d);
  };

  // D3 force graph
  useEffect(() => {
    if (!graph || !svgRef.current) return;
    const structureKey = `${activeTab}:${graphView}:${graph.nodes.length}:${graph.links.length}`;

    // Status-only change (same nodes/links, just colour updates) — update in-place.
    if (structureKey === prevGraphKeyRef.current && simRef.current) {
      const simNodes = simRef.current.nodes();
      graph.nodes.forEach(updated => {
        const sn = simNodes.find(n => n.id === updated.id);
        if (sn) Object.assign(sn, updated);
      });
      d3.select(svgRef.current).selectAll("circle.node-dot").filter(d => d && d.id != null).attr("fill", nodeColorFn);
      return;
    }
    prevGraphKeyRef.current = structureKey;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    const W = svgRef.current.clientWidth || 800;
    const H = svgRef.current.clientHeight || 500;
    const nodes = graph.nodes.map(n => ({
      ...n
    }));
    const links = graph.links.map(l => ({
      ...l
    }));
    const zoom = d3.zoom().scaleExtent([0.2, 4]).on("zoom", e => g.attr("transform", e.transform));
    svg.call(zoom);
    const g = svg.append("g");

    // Arrow marker
    svg.append("defs").append("marker").attr("id", "arrow").attr("viewBox", "0 -4 8 8").attr("refX", 18).attr("refY", 0).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto").append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "var(--border-2)");
    const link = g.append("g").selectAll("line").data(links).join("line").attr("stroke", "var(--border-2)").attr("stroke-width", 1.5).attr("marker-end", "url(#arrow)");
    const node = g.append("g").selectAll("g").data(nodes).join("g").attr("cursor", "pointer").call(d3.drag().on("start", (e, d) => {
      if (!e.active) sim.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }).on("drag", (e, d) => {
      d.fx = e.x;
      d.fy = e.y;
    }).on("end", (e, d) => {
      if (!e.active) sim.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    })).on("click", (e, d) => {
      e.stopPropagation();
      setSelNode(d);
    });
    node.append("circle").attr("class", "node-dot").attr("r", 10).attr("fill", nodeColorFn).attr("stroke", d => d.status === "failed" ? "#fbbf24" : "var(--bg)").attr("stroke-width", 2);
    const rootNode = nodes.find(n => n.depth === 0);
    let baseHost = null;
    try {
      if (rootNode) baseHost = new URL(rootNode.url).host;
    } catch {}
    node.append("text").attr("dy", 22).attr("text-anchor", "middle").attr("fill", "var(--muted)").attr("font-size", "10px").attr("pointer-events", "none").text(d => {
      try {
        const u = new URL(d.url);
        const label = u.host === baseHost ? u.pathname + u.search + u.hash || "/" : d.url;
        return label.length > 36 ? label.slice(0, 35) + "…" : label;
      } catch {
        return truncUrl(d.url, 36);
      }
    });

    // Tooltip on hover
    node.append("title").text(d => d.url);
    svg.on("click", () => setSelNode(null));
    const sim = d3.forceSimulation(nodes).force("link", d3.forceLink(links).id(d => d.id).distance(110).strength(0.8)).force("charge", d3.forceManyBody().strength(-350)).force("center", d3.forceCenter(W / 2, H / 2)).force("collision", d3.forceCollide(22)).on("tick", () => {
      link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });
    simRef.current = sim;
    return () => sim.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- nodeColorFn intentionally excluded: it's a new identity each render, and including it re-runs this effect (killing the running sim mid-settle → clustered nodes)
  }, [graph, activeTab, graphView]);

  // Highlight the node whose URL is currently being crawled.
  // Runs after the D3 graph effect so the SVG is already populated.
  useEffect(() => {
    if (!svgRef.current || !graph) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll(".node-crawl-pulse").remove();
    if (!run?.current_url) return;
    const cur = run.current_url.replace(/\/$/, "");
    svg.select("g").selectAll("g").filter(d => d && d.url && d.url.replace(/\/$/, "") === cur).insert("circle", ":first-child").attr("class", "node-crawl-pulse").attr("r", 10);
  }, [run?.current_url, graph]);


  const onDeleteFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      await api.deleteFinding(runId, findingId);
      setFindings(prev => prev.filter(f => f.id !== findingId));
      if (expandedFinding === findingId) setExpandedFinding(null);
    } catch (err) {
      setError(err.message);
    }
  };
  const onDeleteFindingGroup = async (e, title) => {
    e.stopPropagation();
    if (!confirm(`Delete all instances of "${title}"?`)) return;
    try {
      await api.deleteFindingGroup(runId, title);
      setFindings(prev => prev.filter(f => f.title !== title));
      setExpandedGroups(prev => {
        const next = new Set(prev);
        next.delete(title);
        return next;
      });
    } catch (err) {
      setError(err.message);
    }
  };
  const onValidateAll = async () => {
    if (validateBusy) return;
    setValidateBusy(true);
    try {
      const vs = await api.validateAllFindings(runId);
      setValidateStatus(vs);
    } catch (err) {
      setError(err.message);
      setValidateBusy(false);
    }
  };
  const onDeduplicateFindings = () => {
    if (dedupeBusy || aliceIsThinking) return;
    setDedupeBusy(true);
    submitAliceDirective(ALICE_DEDUP_DIRECTIVE, {
      onComplete: () => {
        api.getFindings(runId).then(setFindings).catch(() => {});
        api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
        setExpandedFinding(null);
        setExpandedGroups(new Set());
        setDedupeBusy(false);
      }
    });
  };
  const onExportFindingsMarkdown = () => {
    try {
      const md = findingsToMarkdown(findings, {
        runName: run?.name,
        siteName,
        generatedAt: new Date()
      });
      downloadTextFile(markdownExportFilename(run, siteName), md, "text/markdown;charset=utf-8");
    } catch (err) {
      setError(err.message);
    }
  };
  const onImportFindingsClick = () => {
    issueImportInputRef.current?.click();
  };
  const onImportFindingsFile = async e => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = parseFindingsMarkdown(await file.text());
      if (!imported.length) throw new Error("No issues found in the selected file.");
      const result = await api.importFindings(runId, imported);
      setFindings(await api.getFindings(runId));
      api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
      const [r, g] = await Promise.all([api.getRun(runId), api.getGraph(runId)]);
      setRun(r);
      setGraph(g);
      alert(`Imported ${result.imported} issue${result.imported === 1 ? "" : "s"}.`);
    } catch (err) {
      setError(err.message);
    }
  };
  const onValidateFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      const updated = await api.validateFinding(runId, findingId);
      setFindings(prev => prev.map(f => f.id === findingId ? {
        ...f,
        ...updated
      } : f));
      setValidateStatus(vs => vs ? {
        ...vs,
        status: "running"
      } : vs);
      setValidateBusy(true);
    } catch (err) {
      setError(err.message);
    }
  };
  const onEditFinding = (e, f) => {
    e.stopPropagation();
    setExpandedFinding(f.id);
    setEditingFinding(f.id);
    setEditDraft({
      severity: f.severity,
      validation_status: f.validation_status,
      title: f.title || "",
      affected_url: f.affected_url || "",
      cvss_score: f.cvss_score ?? 0,
      cvss_vector: f.cvss_vector || "",
      description: f.description || "",
      impact: f.impact || "",
      likelihood: f.likelihood || "",
      recommendation: f.recommendation || ""
    });
  };
  const onCancelEditFinding = e => {
    e?.stopPropagation?.();
    setEditingFinding(null);
    setEditDraft(null);
  };
  const onSaveEditFinding = async (e, findingId) => {
    e?.stopPropagation?.();
    if (!editDraft || editBusy) return;
    setEditBusy(true);
    try {
      const updated = await api.updateFinding(runId, findingId, {
        ...editDraft,
        cvss_score: Number(editDraft.cvss_score) || 0
      });
      setFindings(prev => prev.map(f => f.id === findingId ? {
        ...f,
        ...updated
      } : f));
      setEditingFinding(null);
      setEditDraft(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setEditBusy(false);
    }
  };
  const onStopValidation = async () => {
    try {
      const vs = await api.stopValidation(runId);
      setValidateStatus(vs);
      setValidateBusy(false);
      setFindings(await api.getFindings(runId));
    } catch (err) {
      setError(err.message);
    }
  };
  const onStopThinkingScan = async () => {
    try {
      setThinkingStopReq(true);
      const s = await api.stopThinkingScan(runId);
      setThinkingStatus(s);
      if (!isDynamicScanActive(s.status)) setThinkingStopReq(false);
    } catch (e) {
      setThinkingStopReq(false);
      setError(e.message);
    }
  };
  const onStartThinkingScan = async () => {
    try {
      setThinkingStopReq(false);
      setThinkingStatus({
        status: "running"
      });
      setCheckpointStatus(null);
      const s = await api.startThinkingScan(runId, coverageMode);
      setThinkingStatus(s);
      setWpReloadKey(k => k + 1);
    } catch (e) {
      setThinkingStopReq(false);
      setError(e.message);
    }
  };
  const onResumeThinkingScan = async () => {
    try {
      setThinkingStopReq(false);
      setThinkingStatus({
        status: "running"
      });
      const s = await api.resumeThinkingScan(runId);
      setThinkingStatus(s);
      setWpReloadKey(k => k + 1);
    } catch (e) {
      setThinkingStopReq(false);
      setError(e.message);
    }
  };
  const onEditSettings = () => {
    setEditDepth(String(run.max_depth));
    setEditPages(String(run.max_pages));
    setEditLlmProfileId(run.llm_profile_id || null);
    setEditingSettings(true);
  };
  const onSaveSettings = async () => {
    const d = parseInt(editDepth, 10);
    const p = parseInt(editPages, 10);
    if (!d || !p || d < 1 || d > 10 || p < 5 || p > 500) return;
    try {
      const r = await api.updateRun(runId, {
        max_depth: d,
        max_pages: p,
        llm_profile_id: editLlmProfileId || null
      });
      setRun(r);
      setEditingSettings(false);
    } catch (e) {
      setError(e.message);
    }
  };
  const onToggleScope = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    const newScope = selectedNode.in_scope === false ? true : false;
    try {
      await api.setPageScope(runId, selectedNode.id, {
        in_scope: newScope,
        cascade
      });
      const g = await api.getGraph(runId);
      setGraph(g);
      const updated = g.nodes.find(n => n.id === selectedNode.id);
      if (updated) setSelNode(updated);
    } catch (e) {
      setError(e.message);
    } finally {
      setScopeBusy(false);
    }
  };
  const onDeleteNode = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      await api.deletePage(runId, selectedNode.id, cascade);
      const g = await api.getGraph(runId);
      setGraph(g);
      setSelNode(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setScopeBusy(false);
    }
  };
  const onStart = async () => {
    try {
      setCrawlStopRequested(false);
      const r = await api.startRun(runId);
      // Optimistically mark as running so the poll interval starts immediately.
      // Clear per_user_progress so stale data from the previous crawl is never
      // shown — fresh entries arrive via crawl_progress SSE events.
      setRun({
        ...r,
        status: "running",
        per_user_progress: {}
      });
    } catch (e) {
      setError(e.message);
    }
  };
  const onStop = async () => {
    try {
      setCrawlStopRequested(true);
      const r = await api.stopRun(runId);
      setRun(r);
    } catch (e) {
      setCrawlStopRequested(false);
      setError(e.message);
    }
  };
  const onClearCrawl = async () => {
    if (!confirm("Clear all crawled pages for this run?")) return;
    try {
      setCrawlStopRequested(false);
      setGraph({
        nodes: [],
        links: []
      });
      const r = await api.clearCrawl(runId);
      setRun({
        ...r,
        status: "pending",
        per_user_progress: null
      });
    } catch (e) {
      setError(e.message);
    }
  };
  const effectiveThinkingStatus = thinkingStatus?.status || "idle";
  
  const headerStatus = runWorkflowStatus(run, {
    thinkingStatus: effectiveThinkingStatus,
    crawlStopping: crawlStopRequested,
    thinkingStopping: thinkingStopRequested
  });
  const STATUS_COLOR = {
    neutral: "var(--muted)",
    pending: "var(--muted)",
    running: "var(--warn)",
    stopping: "var(--warn)",
    partial: "var(--text-2)",
    ok: "var(--ok)",
    danger: "var(--danger)"
  };
  const canStart = run && !crawlStopRequested && ["pending", "stopped", "failed", "complete"].includes(run.status);
  const canClearCrawl = run && !crawlStopRequested && ["stopped", "failed", "complete"].includes(run.status);
  const canStop = run?.status === "running" && !crawlStopRequested;
  const canStopThinking = isDynamicScanActive(effectiveThinkingStatus);
  const canStartAnyScan = run?.status !== "running" && !crawlStopRequested && !isDynamicScanActive(effectiveThinkingStatus);
  const hasCheckpoint = checkpointStatus?.exists === true && canStartAnyScan && !isDynamicScanActive(effectiveThinkingStatus);
  // Shared prop bag for the Findings/Activity tabs — bundled once and spread
  // so the two call sites aren't 40-attribute walls. Extra props a tab ignores
  // are harmless. ponytail: object-spread over a context Provider (no middle layer).
  const runProps = {
    activityLog,
    tokenUsage,
    setTokenExpanded,
    tokenExpanded,
    activitySubTab,
    setActivitySubTab,
    agents,
    normalizeAgentForRun,
    activityFeedRef,
    runId,
    clearBusy,
    confirm,
    setClearBusy,
    setClearError,
    api,
    setActivityLog,
    setSitePlanData,
    setTokenUsage,
    sitePlanData,
    expandedLogIds,
    toggleLogId,
    truncUrl,
    collapsedAgentIds,
    toggleAgentId,
    defaultAgentRoster,
    representsAgent,
    aliceChats,
    activeAliceTabId,
    setActiveAliceTabId,
    deleteAliceTab,
    createAliceTab,
    aliceChatHeight,
    aliceMessages,
    parseAliceTurnSegments,
    renderMarkdown,
    renderAliceTraceBox,
    aliceExpandedThinkIds,
    setAliceExpandedThinkIds,
    renderAliceBlocks,
    aliceThinkingTabId,
    startAliceResize,
    aliceInputText,
    aliceIsThinking,
    handleAliceSend,
    setAliceInputText,
    handleAliceStop,
    agentRoleLabel,
    agentCurrentTask,
    agentCrawlEvents,
    agentTaskHistory,
    agentStatusLabel,
    thinkingStatus,
    thinkingStopRequested,
    validateStatus,
    onStopValidation,
    dedupeBusy,
    findings,
    onExportFindingsMarkdown,
    onImportFindingsClick,
    issueImportInputRef,
    onImportFindingsFile,
    validateBusy,
    onValidateAll,
    onDeduplicateFindings,
    setFindings,
    isDynamicScanActive,
    editingFinding,
    setExpandedFinding,
    expandedFinding,
    onValidateFinding,
    onEditFinding,
    onDeleteFinding,
    editDraft,
    setEditDraft,
    editBusy,
    onCancelEditFinding,
    onSaveEditFinding,
    navigator,
    toggleGroup,
    sourceLabel,
    expandedGroups,
    findColW,
    startFindResize,
    onDeleteFindingGroup
  };
  return <>
    <div className="topbar">
      <div className="topbar-title" style={{
        flexDirection: "column",
        alignItems: "flex-start",
        gap: 2
      }}>
        <div className="row" style={{
          alignItems: "center",
          gap: 0
        }}>
          <a href={run ? `#/sites/${run.site_id}` : "#/"} style={{
            color: "var(--muted)",
            fontWeight: 400
          }}>{siteName || "Site"}</a>
          <span className="breadcrumb-sep"> / </span>
          {run ? run.name : "…"}
          {run && <span className={"run-status-badge" + (["running", "stopping"].includes(headerStatus.key) ? " running" : "")} style={{
            color: STATUS_COLOR[headerStatus.key] || "var(--muted)"
          }}>● {headerStatus.label}</span>}
        </div>
        {run && run.llm_profile_id && runProfiles.length > 0 && <div style={{
          fontSize: 11,
          fontWeight: 400,
          color: "var(--muted)",
          marginLeft: 0
        }}>
            Profile: {(runProfiles.find(p => p.id === run.llm_profile_id) || {
            name: "#" + run.llm_profile_id
          }).name}
          </div>}
      </div>
      <div className="topbar-actions">
        {canStart && <button className="btn sm" onClick={onStart}><IconPlay /> Start crawl</button>}
        {!thinkingStopRequested && canStartAnyScan && (effectiveThinkingStatus === "idle" || effectiveThinkingStatus === "complete" || effectiveThinkingStatus === "stopped" || effectiveThinkingStatus === "failed" || effectiveThinkingStatus == null) && <>
          <label className="subtle" style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12
          }} title="Track: observe coverage as the scan runs. Enforce: drive every applicable page × category to covered or skipped-with-reason.">
            Coverage:
            <select value={coverageMode} onChange={e => setCoverageMode(e.target.value)}>
              <option value="track">Track</option>
              <option value="enforce">Enforce</option>
            </select>
          </label>
          <button className="btn sm" title="Run the adaptive Pentest" onClick={onStartThinkingScan}><IconPlay /> Start Pentest</button></>}
        {hasCheckpoint && <button className="btn sm" style={{
          background: "var(--warn)",
          color: "#000",
          borderColor: "var(--warn)"
        }} title={`Resume scan from step ${checkpointStatus.step_count}`} onClick={onResumeThinkingScan}><IconPlay /> Resume Pentest</button>}
        {canStop && <button className="btn danger-outline" onClick={onStop}><IconStop /> Stop crawl</button>}
        {crawlStopRequested && <button className="btn danger-outline" disabled><IconStop /> Stopping…</button>}
        {!canStop && !crawlStopRequested && canStopThinking && <button className="btn danger-outline" onClick={onStopThinkingScan} disabled={thinkingStopRequested}><IconStop /> {thinkingStopRequested ? "Stopping…" : "Stop Dynamic Scan"}</button>}
        {aliceGlobalRunning && <button className="btn danger-outline" style={{
          borderColor: "var(--danger)",
          color: "var(--danger)",
          background: "rgba(239,68,68,.08)"
        }} onClick={handleAliceStop} title="Stop the running A.L.I.C.E. agent"><IconStop /> Stop A.L.I.C.E.</button>}
      </div>
    </div>

    <div className="content" style={{
      paddingBottom: 0,
      display: "flex",
      flexDirection: "column",
      flex: 1,
      minHeight: 0
    }}>
      {error && <div className="alert error" style={{
        marginBottom: 12
      }}>{error}</div>}

      {guidedLoginErrors.length > 0 && <div style={{
        background: "var(--surface-2,#2a2a2a)",
        border: "2px solid var(--danger)",
        borderRadius: 6,
        padding: "12px 16px",
        marginBottom: 12,
        display: "flex",
        flexDirection: "column",
        gap: 6
      }}>
          <div style={{
          fontWeight: 600,
          fontSize: 13,
          color: "var(--danger)"
        }}>⚠️ Guided Browser Login Failed</div>
          {guidedLoginErrors.map(e => <div key={e.credential_id} style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexWrap: "wrap"
        }}>
              <span style={{
            fontSize: 13
          }}>{e.message}</span>
              <button className="btn sm ghost" onClick={() => setGuidedLoginErrors(prev => prev.filter(x => x.credential_id !== e.credential_id))}>Dismiss</button>
            </div>)}
        </div>}

      {guidedLoginPending.length > 0 && <div style={{
        background: "var(--surface-2,#2a2a2a)",
        border: "2px solid var(--warn,#f59e0b)",
        borderRadius: 6,
        padding: "12px 16px",
        marginBottom: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8
      }}>
          <div style={{
          fontWeight: 600,
          fontSize: 13,
          color: "var(--warn,#f59e0b)"
        }}>🖥️ Guided Login Required</div>
          {guidedLoginPending.map(p => <GuidedLoginItem key={p.credential_id} item={p} runId={runId} onConfirmed={() => setGuidedLoginPending(prev => prev.filter(x => x.credential_id !== p.credential_id))} />)}
        </div>}

      <div className="tab-bar">
        <button className={"tab-btn" + (activeTab === "activity" ? " active" : "")} onClick={() => {
          setActiveTab("activity");
          setSelNode(null);
          nav(`#/runs/${runId}/activity`);
        }}>
          Status{isDynamicScanActive(thinkingStatus?.status) && activityLog.length > 0 ? <span className="activity-live-dot">●</span> : ""}
        </button>
        <button className={"tab-btn" + (activeTab === "sitemap" ? " active" : "")} onClick={() => {
          setActiveTab("sitemap");
          setSelNode(null);
          nav(`#/runs/${runId}/sitemap`);
        }}>Site Map</button>
        <button className={"tab-btn" + (activeTab === "intelligence" ? " active" : "")} onClick={() => {
          setActiveTab("intelligence");
          setSelNode(null);
          nav(`#/runs/${runId}/intelligence`);
        }}>
          Intelligence{targetIntel && Object.values(targetIntel.counts || {}).reduce((a, b) => a + b, 0) > 0 ? <span className="traffic-count">{Object.values(targetIntel.counts || {}).reduce((a, b) => a + b, 0)}</span> : ""}
        </button>
        <button className={"tab-btn" + (activeTab === "tasks" ? " active" : "")} onClick={() => {
          setActiveTab("tasks");
          setSelNode(null);
          nav(`#/runs/${runId}/tasks`);
        }}>
          Task Graph{taskGraph?.counts?.tasks > 0 ? <span className="traffic-count">{taskGraph.counts.tasks}</span> : ""}
        </button>
        <button className={"tab-btn" + (activeTab === "sessions" ? " active" : "")} onClick={() => {
          setActiveTab("sessions");
          setSelNode(null);
          nav(`#/runs/${runId}/sessions`);
        }}>
          Sessions{scannerSessions?.counts?.total > 0 ? <span className="traffic-count">{scannerSessions.counts.total}</span> : ""}
        </button>
        <button className={"tab-btn" + (activeTab === "findings" ? " active" : "")} onClick={() => {
          setActiveTab("findings");
          setSelNode(null);
          nav(`#/runs/${runId}/findings`);
        }}>
          Findings{findings.length > 0 ? <span className="findings-badge">{findings.length}</span> : ""}
        </button>
        <button className={"tab-btn" + (activeTab === "traffic" ? " active" : "")} onClick={() => {
          setActiveTab("traffic");
          setSelNode(null);
          nav(`#/runs/${runId}/traffic`);
        }}>
          Traffic Log{trafficTotal > 0 ? <span className="traffic-count">{trafficTotal}</span> : ""}
        </button>
        <button className={"tab-btn" + (activeTab === "workprogram" ? " active" : "")} onClick={() => {
          setActiveTab("workprogram");
          setSelNode(null);
          nav(`#/runs/${runId}/workprogram`);
        }}>
          OWASP Coverage
        </button>
        <button className={"tab-btn" + (activeTab === "leads" ? " active" : "")} onClick={() => {
          setActiveTab("leads");
          setSelNode(null);
          nav(`#/runs/${runId}/leads`);
        }}>
          SAST Leads
        </button>
        <div style={{
          flex: 1
        }}></div>
        {canClearCrawl && activeTab === "sitemap" && <button className="btn danger-outline sm" style={{
          margin: "auto 8px auto 0"
        }} onClick={onClearCrawl}>Clear crawl</button>}
        {activeTab === "sitemap" && run?.credentials?.length > 1 && <div className="view-toggle" style={{
          margin: "auto 8px auto 0"
        }}>
            <button className={"btn ghost sm" + (graphView === "scope" ? " active" : "")} onClick={() => setGraphView("scope")}>By Scope</button>
            <button className={"btn ghost sm" + (graphView === "user" ? " active" : "")} onClick={() => setGraphView("user")}>By User</button>
          </div>}
      </div>

      {activeTab === "sitemap" && run && <>
        <div className="run-meta">
          <div className="run-stat"><span className="run-stat-val">{run.pages_discovered}</span><span className="run-stat-lbl">Pages found</span></div>
          {editingSettings ? <div className="run-stat-edit">
              <div className="run-stat-edit-field">
                <label>Max depth</label>
                <input type="number" min="1" max="10" value={editDepth} onInput={e => setEditDepth(e.target.value)} style={{
                width: 54
              }} />
              </div>
              <div className="run-stat-edit-field">
                <label>Max pages</label>
                <input type="number" min="5" max="500" value={editPages} onInput={e => setEditPages(e.target.value)} style={{
                width: 64
              }} />
              </div>
              <div style={{
              display: "flex",
              gap: 6,
              alignItems: "center"
            }}>
                <button className="btn sm" onClick={onSaveSettings}>Save</button>
                <button className="btn ghost sm" onClick={() => setEditingSettings(false)}>Cancel</button>
              </div>
            </div> : <>
            <div className="run-stat">
              <span className="run-stat-val">{run.max_depth}</span>
              <span className="run-stat-lbl">Max depth</span>
            </div>
            <div className="run-stat">
              <span className="run-stat-val">{run.max_pages}</span>
              <span className="run-stat-lbl">Max pages</span>
            </div>
            {run.llm_profile_id && runProfiles.length > 0 && <div className="run-stat">
                <span className="run-stat-val" style={{
                fontSize: 12
              }}>{(runProfiles.find(p => p.id === run.llm_profile_id) || {
                  name: "#" + run.llm_profile_id
                }).name}</span>
                <span className="run-stat-lbl">LLM profile</span>
              </div>}
            {run.status !== "running" && <button className="btn ghost sm" style={{
              alignSelf: "center",
              marginLeft: 4
            }} title="Edit depth / pages" onClick={onEditSettings}>✎</button>}
          </>}
          {(() => {
            
            const multiUser = run.credentials?.length > 1;
            if (multiUser) return null; // per-user section rendered below
            return <>
              {crawlUsername && <div className="run-stat"><span className="run-stat-lbl">Crawling as</span><span className="run-stat-val" style={{
                  fontSize: 14
                }}>{crawlUsername}</span></div>}
              {run.current_url && <div className="run-stat run-stat-url"><span className="run-stat-lbl">Current URL</span><span className="mono run-stat-url-val">{truncUrl(run.current_url, 50)}</span></div>}
            </>;
          })()}
          {run.error_message && <div style={{
            color: "var(--danger)",
            fontSize: 12,
            flex: 1
          }}>{run.error_message}</div>}
        </div>
        {activeTab === "sitemap" && run && <ScopeHostsPanel siteId={run.site_id} hosts={scopeHosts} onChange={setScopeHosts} />}
        {(() => {
          const credList = run.credentials || [];
          const multiUser = credList.length > 1;
          // Overall progress reaches the cap while crawling, then fills once discovery is complete.
          const overallPct = run.status === "complete" ? 100 : Math.min(100, run.pages_discovered / run.max_pages * 100);
          const progressBar = run.status === "running" || run.pages_discovered > 0 ? <div className="crawl-progress-bar">
              <div className="crawl-progress-fill" style={{
              width: overallPct + "%"
            }}></div>
            </div> : null;
          if (multiUser) {
            const pup = run.per_user_progress || {};
            return <>
              {progressBar}
              <div className="crawl-user-progress">
                {credList.map((c, idx) => {
                  const p = pup[c.username] || {};
                  const color = USER_PALETTE[idx % USER_PALETTE.length];
                  const isActive = run.status === "running" && !p.done;
                  return <div key={c.username} className="crawl-user-row">
                      <span className={"crawl-user-dot" + (isActive ? " active" : "")} style={{
                      background: color
                    }}></span>
                      <span className="crawl-user-name" title={c.username}>{c.label || c.username}</span>
                      <span className="crawl-user-pages">{p.pages_visited || 0} pg</span>
                      <span className="crawl-user-url mono" title={p.current_url || ""}>
                        {p.current_url ? truncUrl(p.current_url, 42) : p.done ? "done" : "waiting…"}
                      </span>
                    </div>;
                })}
              </div></>;
          }
          return progressBar;
        })()}</>}

      <div className="graph-layout" style={{
        display: activeTab === "findings" || activeTab === "traffic" || activeTab === "activity" || activeTab === "intelligence" || activeTab === "tasks" || activeTab === "sessions" || activeTab === "workprogram" || activeTab === "leads" ? "none" : "flex"
      }}>
        <div className="graph-canvas-wrap">
          {graph && graph.nodes.length === 0 && <div className="graph-empty">
              <WebRunSitemapTab activeTab={activeTab} run={run} onStart={onStart} onStartThinkingScan={onStartThinkingScan} hasCheckpoint={hasCheckpoint} onResumeThinkingScan={onResumeThinkingScan} checkpointStatus={checkpointStatus} />
            </div>}
          <svg ref={svgRef} className="graph-svg" width="100%" height="100%" style={{
            pointerEvents: !graph || graph.nodes.length === 0 ? "none" : "all"
          }}></svg>
          {graph && graph.nodes.length > 0 && <div className="graph-legend">
              {graphView === "user" && run?.credentials?.length > 1 ? <>
                {(run.credentials || []).map((c, i) => <div key={c.id} className="legend-item">
                    <span className="legend-dot" style={{
                  background: USER_PALETTE[i % USER_PALETTE.length]
                }}></span>
                    {c.label || c.username}
                  </div>)}
                <div className="legend-item"><span className="legend-dot" style={{
                  background: USER_BOTH_COLOR
                }}></span>All users</div>
              </> : <>
                <div className="legend-item"><span className="legend-dot" style={{
                  background: SCOPE_IN_COLOR
                }}></span>In Scope</div>
                <div className="legend-item"><span className="legend-dot" style={{
                  background: SCOPE_OUT_COLOR
                }}></span>Out of Scope</div>
                <div className="legend-item"><span className="legend-dot" style={{
                  background: "var(--bg)",
                  border: "2px solid #fbbf24"
                }}></span>Failed</div>
              </>}
            </div>}
        </div>

        {selectedNode && <div className="graph-panel">
            <div className="graph-panel-header">
              <div className="graph-panel-url">{selectedNode.url}</div>
              <button className="btn ghost sm" onClick={() => setSelNode(null)}>✕</button>
            </div>
            {pageDetail ? <div className="graph-panel-body">
                {pageDetail.title && <div className="graph-panel-title">{pageDetail.title}</div>}

                <div className="graph-panel-section-label">Scope</div>
                <div className="scope-row">
                  <span className={"scope-badge " + (selectedNode.in_scope === false ? "out" : "in")}>
                    {selectedNode.in_scope === false ? "Out of Scope" : "In Scope"}
                  </span>
                  <button className="btn sm" onClick={onToggleScope} disabled={scopeBusy}>
                    {scopeBusy ? "…" : selectedNode.in_scope === false ? "Mark in scope" : "Mark out of scope"}
                  </button>
                  <button className="btn danger-outline sm" onClick={onDeleteNode} disabled={scopeBusy} title="Delete this node (and children if checkbox is ticked)">🗑</button>
                </div>
                <label className="scope-cascade-label">
                  <input type="checkbox" checked={cascade} onChange={e => setCascade(e.target.checked)} />
                  Also apply to all children
                </label>

                <div className="graph-panel-section-label" style={{
              marginTop: 14
            }}>Page Categories</div>
                <div className="page-cats">
                  {[["req_auth", "Auth Required"], ["takes_input", "Takes Input"], ["has_object_ref", "Object Reference"], ["has_business_logic", "Business Logic"]].map(([key, label]) => {
                const val = pageDetail[key];
                const cls = val === true ? "cat-yes" : val === false ? "cat-no" : "cat-unknown";
                const badge = val === true ? "Yes" : val === false ? "No" : "?";
                return <div key={key} className="cat-row">
                      <span className="cat-label">{label}</span>
                      <span className={"cat-badge " + cls}>{badge}</span>
                    </div>;
              })}
                </div>

                {pageDetail.owasp_applicable && Object.keys(pageDetail.owasp_applicable).length > 0 && <>
                  <div className="graph-panel-section-label" style={{
                marginTop: 14
              }}>OWASP Top 10:2025</div>
                  <div className="page-cats">
                    {Object.entries(pageDetail.owasp_applicable).map(([cat, applicable]) => <div key={cat} className="cat-row">
                        <span className="cat-label" style={{
                    fontSize: 11
                  }}>{cat} {OWASP_WEB_LABELS[cat] || ""}</span>
                        <span className={"cat-badge " + (applicable ? "cat-yes" : "cat-no")}>{applicable ? "Yes" : "No"}</span>
                      </div>)}
                  </div></>}

                {pageViews.length > 0 ? <>
                  <div className="graph-panel-section-label" style={{
                marginTop: 14
              }}>
                    Views by User
                  </div>
                  {pageViews.map(v => {
                const apiTranscript = apiTranscriptText(v.page_text || pageDetail.page_text);
                return <div key={v.id} className="credential-view-card">
                        <div className="credential-view-label">
                          {v.username || "Anonymous"}
                        </div>
                        {v.screenshot_b64 && <img src={"data:image/png;base64," + v.screenshot_b64} className="credential-view-screenshot" alt={"screenshot (" + v.username + ")"} />}
                        {!v.screenshot_b64 && apiTranscript && <>
                          <div className="api-transcript-label">API Request / Response</div>
                          <pre className="api-transcript">{apiTranscript}</pre></>}
                        <div className="credential-view-context">
                          {v.llm_context || "No context."}
                        </div>
                      </div>;
              })}
                </> : <>
                  <div className="graph-panel-section-label" style={{
                marginTop: 14
              }}>LLM Context</div>
                  <div className="graph-panel-context">{pageDetail.llm_context || "No context available."}</div>
                  {pageDetail.screenshot_b64 && <>
                    <div className="graph-panel-section-label" style={{
                  marginTop: 12
                }}>Screenshot</div>
                    <img src={`data:image/png;base64,${pageDetail.screenshot_b64}`} style={{
                  width: "100%",
                  borderRadius: 6,
                  border: "1px solid var(--border)"
                }} alt="screenshot" /></>}
                  {!pageDetail.screenshot_b64 && apiTranscriptText(pageDetail.page_text) && <>
                    <div className="graph-panel-section-label" style={{
                  marginTop: 12
                }}>API Request / Response</div>
                    <pre className="api-transcript">{apiTranscriptText(pageDetail.page_text)}</pre></>}
                </>}
              </div> : <div className="subtle" style={{
            padding: 12
          }}>Loading…</div>}
          </div>}
      </div>

      {activeTab === "findings" && <WebRunFindingsTab {...runProps} />}

      {activeTab === "intelligence" && <TargetIntelligencePanel data={targetIntel} selectedKind={targetIntelKind} onKind={setTargetIntelKind} refresh={() => api.getTargetIntelligence(runId, targetIntelKind).then(setTargetIntel).catch(() => {})} onClear={async () => {
        if (!confirm("Clear all target intelligence for this run?")) return;
        setClearBusy("intel");
        setClearError(null);
        try {
          await api.clearTargetIntel(runId);
          setTargetIntel(null);
          setTargetIntelKind("");
        } catch (e) {
          setClearError(e.message);
        } finally {
          setClearBusy("");
        }
      }} clearing={clearBusy === "intel"} />}

      {activeTab === "tasks" && <TaskGraphPanel data={taskGraph} reconSummary={reconSummary} subTab={tasksSubTab} onSubTab={setTasksSubTab} refresh={() => api.getTaskGraph(runId).then(setTaskGraph).catch(() => {})} seed={() => api.seedTaskGraph(runId).then(setTaskGraph).catch(e => setError(e.message))} onClear={async () => {
        if (!confirm("Clear all hypotheses and tasks for this run?")) return;
        setClearBusy("tasks");
        setClearError(null);
        try {
          await api.clearTaskGraph(runId);
          setTaskGraph(null);
        } catch (e) {
          setClearError(e.message);
        } finally {
          setClearBusy("");
        }
      }} clearing={clearBusy === "tasks"} />}

      {activeTab === "sessions" && <ScannerSessionsPanel runId={runId} data={scannerSessions} refresh={() => api.getScannerSessions(runId).then(setScannerSessions).catch(() => {})} />}

      {activeTab === "activity" && <WebRunActivityTab {...runProps} />}

      {activeTab === "traffic" && <WebRunTrafficTab runId={runId} traffic={traffic} setTraffic={setTraffic} activeTab={activeTab} api={api} lastTrafficIdRef={lastTrafficIdRef} trafficColW={trafficColW} startTrafficResize={startTrafficResize} run={run} isDynamicScanActive={isDynamicScanActive} thinkingStatus={thinkingStatus} trafficTotal={trafficTotal} setTrafficTotal={setTrafficTotal} selectedTraffic={selectedTraffic} setSelectedTraffic={setSelectedTraffic} />}
      {activeTab === "workprogram" && <div className="content scroll-content" style={{
        padding: 0
      }}>
          <WebRunWorkProgramTab runId={runId} run={run} reloadKey={wpReloadKey} scanRunning={isDynamicScanActive(thinkingStatus?.status) || run?.status === "crawling" || run?.status === "crawled"} />
        </div>}
      {activeTab === "leads" && <WebRunSastLeadsTab runId={runId} scanRunning={isDynamicScanActive(thinkingStatus?.status)} />}
    </div></>;
}

// ── WebRunSastLeadsTab ─────────────────────────────────────────────────────────
// Lets a web run import a copy of a completed SAST scan's leads. The copies are
import { WebRunSastLeadsTab } from "./SiteDetail/WebRunSastLeadsTab";
import { WebRunWorkProgramTab } from "./SiteDetail/WebRunWorkProgramTab";
import { TargetIntelligencePanel } from "./SiteDetail/TargetIntelligencePanel";
import { ScannerSessionsPanel } from "./SiteDetail/ScannerSessionsPanel";
import { TaskGraphPanel } from "./SiteDetail/TaskGraphPanel";
import { AttackSurfacePanel } from "./SiteDetail/AttackSurfacePanel";
// independent rows owned by this run; the originals stay open on the SAST tab.


export { WebRunSastLeadsTab };
export { WebRunWorkProgramTab };
export { TargetIntelligencePanel };
export { ScannerSessionsPanel };
export { TaskGraphPanel };
export { AttackSurfacePanel };