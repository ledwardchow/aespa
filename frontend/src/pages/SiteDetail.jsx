import { ScopeHostsPanel } from "./Settings/ScopeHostsPanel";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { api } from "../lib/api";
import { nav } from "../lib/router";
import { useAliceChat } from "./SiteDetail/useAliceChat";
import { useFindings } from "./SiteDetail/useFindings";
import { useActivity } from "./SiteDetail/useActivity";
import { fmtDate } from "../lib/utilities";
import { IconPlus } from "../components/Icons";
import { EmptyState } from "../components/EmptyState";
import { PageHeader, Crumb, Sep } from "../components/PageHeader";
import { WebRunFindingsTab } from "./SiteDetail/WebRunFindingsTab";
import { WebRunActivityTab } from "./SiteDetail/WebRunActivityTab";
import { WebRunTrafficTab } from "./SiteDetail/WebRunTrafficTab";
import { WebRunAttackSurfaceTab } from "./SiteDetail/WebRunAttackSurfaceTab";
import { WebRunSessionsTab } from "./SiteDetail/WebRunSessionsTab";
import { WebRunNavigation } from "./SiteDetail/WebRunNavigation";
import { useWebRunEvents } from "./SiteDetail/useWebRunEvents";
import { GuidedLoginNotices } from "./SiteDetail/GuidedLoginNotices";
import { WebRunSitemapMeta } from "./SiteDetail/WebRunSitemapMeta";
import { WebRunSitemapGraph } from "./SiteDetail/WebRunSitemapGraph";
import { WebRunCrawlProgress } from "./SiteDetail/WebRunCrawlProgress";
import { WebRunHeader } from "./SiteDetail/WebRunHeader";
import { WebRunSastLeadsTab } from "./SiteDetail/WebRunSastLeadsTab";
import { isDynamicScanActive, runWorkflowStatus, workflowBadge } from "./SiteDetail/_helpers";
export { SiteForm } from "./SiteDetail/SiteForm";
export { TestRunForm } from "./SiteDetail/TestRunForm";
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
      crawler_mode: run.crawler_mode || "url",
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
        crawler_mode: editForm.crawler_mode,
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
    <PageHeader
      title={<><Crumb href="#/">Sites</Crumb><Sep />{site ? site.name : "…"}</>}
      actions={<>
        {site && <button className="btn secondary" onClick={() => nav(`#/sites/${siteId}/edit`)}>Edit site</button>}
        <button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}><IconPlus /> New run</button>
      </>} />
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
            <div className="field" style={{ margin: 0 }}>
              <label>Crawler mode</label>
              <select className="select" value={editForm.crawler_mode} onChange={e => setEditForm(f => ({ ...f, crawler_mode: e.target.value }))}>
                <option value="url">URL</option>
                <option value="interactive">Interactive SPA</option>
              </select>
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
                    <div className="site-credential-name">{c.label || (c.login_fields?.[0]?.key === "username" ? c.username : "Test account")}</div>
                    <div className="site-credential-user">{(c.login_fields || []).map(field => field.label).join(" + ") || "Username + Password"}</div>
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
        {runs !== null && runs.length === 0 && <EmptyState icon={null} style={{ padding: "32px" }}
            title="No test runs yet"
            sub="Create a new run to start crawling this site."
            action={<button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}><IconPlus /> New run</button>} />}
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
  const [activeTab, setActiveTab] = useState(["tasks", "workprogram", "intelligence"].includes(initialTab) ? "attack" : initialTab || "activity");
  const [scopeHosts, setScopeHosts] = useState([]);
  const [graphView, setGraphView] = useState("scope"); // "scope" | "user"
  const [intelligenceTotal, setIntelligenceTotal] = useState(0);
  const [attackSurfaceTotal, setAttackSurfaceTotal] = useState(0);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [crawlUsername, setCrawlUsername] = useState(null);
  const [clearBusy, setClearBusy] = useState(""); // which section is clearing
  const [,setClearError] = useState(null);
  // per-user crawl progress is read directly from run.per_user_progress (kept in sync
  // by the periodic poll + SSE run_update events) — no separate state needed.
  const [runProfiles, setRunProfiles] = useState([]);

  // Guided login: list of {credential_id, username} waiting for "I'm Done" confirmation
  const [guidedLoginPending, setGuidedLoginPending] = useState([]);
  const [guidedLoginErrors, setGuidedLoginErrors] = useState([]);
  const [entraPrompts, setEntraPrompts] = useState([]);

  // Load LLM profiles once so the read-only display and edit dropdown both work.
  useEffect(() => {
    api.listLLMProfiles().then(setRunProfiles).catch(() => {});
  }, []);
  const [collapsedAgentIds, setCollapsedAgentIds] = useState(new Set());
  const toggleAgentId = aid => setCollapsedAgentIds(prev => {
    const next = new Set(prev);
    if (next.has(aid)) next.delete(aid);
    else next.add(aid);
    return next;
  });
  const {
    aliceChats,
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
  const [crawlStopRequested, setCrawlStopRequested] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState(null);
  const [thinkingStopRequested, setThinkingStopReq] = useState(false);
  const [coverageMode, setCoverageMode] = useState("track");
  const [wpReloadKey, setWpReloadKey] = useState(0); // bump to force workprogram reload
  const [checkpointStatus, setCheckpointStatus] = useState(null);
  const [trafficTotal, setTrafficTotal] = useState(0);
  const crawlImportInputRef = useRef(null);

  
  
  
  
  
  const [error, setError] = useState(null);
  const lastRunPollOkRef = useRef(Date.now());
  // Findings state, effects and handlers live in this hook; the SSE stream
  // below writes through the setFindings/setValidateStatus it returns.
  const {
    findings,
    setFindings,
    validateStatus,
    setValidateStatus,
    validateBusy,
    setValidateBusy,
    dedupeBusy,
    expandedFinding,
    setExpandedFinding,
    editingFinding,
    editDraft,
    setEditDraft,
    editBusy,
    expandedGroups,
    toggleGroup,
    issueImportInputRef,
    findColW,
    startFindResize,
    onDeleteFinding,
    onDeleteFindingGroup,
    onValidateAll,
    onDeduplicateFindings,
    onExportFindingsMarkdown,
    onImportFindingsClick,
    onImportFindingsFile,
    onValidateFinding,
    onEditFinding,
    onCancelEditFinding,
    onSaveEditFinding,
    onStopValidation
  } = useFindings(runId, activeTab, {
    run,
    siteName,
    submitAliceDirective,
    aliceIsThinking,
    setRun,
    setGraph,
    setError
  });
  // Activity log, agent roster + its label/task helpers, and token usage. The
  // SSE stream below writes through the setters this returns.
  const {
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
  } = useActivity(runId, activeTab, {
    run,
    thinkingStatus,
    aliceIsThinking,
    lastRunPollOkRef
  });

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

  useWebRunEvents({
    runId, setGraph, setCrawlUsername, setRun, setCrawlStopRequested, setAgents, upsertAgent,
    setThinkingStatus, setThinkingStopReq, setActivityLog, setSitePlanData,
    setFindings, setValidateStatus, setValidateBusy, setTokenUsage, setScopeHosts,
    setGuidedLoginPending, setGuidedLoginErrors, setEntraPrompts, setCheckpointStatus
  });

  // Fetch checkpoint status whenever dynamic scan transitions to an inactive status (stopped/complete/failed/idle)
  useEffect(() => {
    if (thinkingStatus?.status && !isDynamicScanActive(thinkingStatus.status)) {
      api.getCheckpointStatus(runId).then(setCheckpointStatus).catch(() => {});
    }
  }, [runId, thinkingStatus?.status]);

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
  }, [run?.status, runId, crawlStopRequested, setAgents]);

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
  }, [runId, thinkingStatus?.status, thinkingStopRequested, setFindings]);

  const onStopThinkingScan = async () => {
    try {
      setThinkingStopReq(true);
      const s = await api.stopThinkingScan(runId);
      setThinkingStatus(s);
      if (!isDynamicScanActive(s.status)) {
        setThinkingStopReq(false);
        api.getCheckpointStatus(runId).then(setCheckpointStatus).catch(() => {});
      }
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
  const onExportCrawl = () => api.exportCrawl(runId);
  const onImportCrawlClick = () => crawlImportInputRef.current?.click();
  const onImportCrawlFile = async event => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const imported = await api.importCrawl(runId, file);
      const importedGraph = await api.getGraph(runId);
      setRun(imported);
      setGraph(importedGraph);
      setWpReloadKey(key => key + 1);
      setActiveTab("sitemap");
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
  const canStart = run && !crawlStopRequested && ["pending", "stopped", "failed", "complete"].includes(run.status);
  const canImportCrawl = run?.status === "pending" && !crawlStopRequested && !isDynamicScanActive(effectiveThinkingStatus);
  const canClearCrawl = run && !crawlStopRequested && ["stopped", "failed", "complete"].includes(run.status);
  const canStop = run?.status === "running" && !crawlStopRequested;
  const canStopThinking = isDynamicScanActive(effectiveThinkingStatus);
  const canStartAnyScan = run?.status !== "running" && !crawlStopRequested && !isDynamicScanActive(effectiveThinkingStatus);
  const canStartThinking = !thinkingStopRequested && canStartAnyScan && ["idle", "complete", "stopped", "failed", null].includes(effectiveThinkingStatus);
  const hasCheckpoint = checkpointStatus?.exists === true && canStartAnyScan && !isDynamicScanActive(effectiveThinkingStatus);
  const interactiveLogins = useMemo(() => (run?.credentials || []).flatMap(credential => {
    const authMode = credential.auth_mode || "auto";
    if (authMode === "guided") {
      return [{
        credential_id: credential.id,
        username: credential.username,
        label: credential.label,
        mode: "Guided"
      }];
    }
    if (authMode === "entra_id" && !credential.has_totp_seed) {
      return [{
        credential_id: credential.id,
        username: credential.username,
        label: credential.label,
        mode: "Entra ID"
      }];
    }
    return [];
  }), [run?.credentials]);
  if (!run) {
    return <div className="content scroll-content">{error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}</div>;
  }
  return <>
    <WebRunHeader
      run={run} siteName={siteName} profiles={runProfiles} headerStatus={headerStatus}
      canStart={canStart} canStop={canStop} canStartScan={canStartThinking}
      canStopScan={canStopThinking} canResume={hasCheckpoint} canImportCrawl={canImportCrawl} crawlStopping={crawlStopRequested}
      scanStopping={thinkingStopRequested} coverageMode={coverageMode} onCoverageMode={setCoverageMode}
      onStart={onStart} onStop={onStop} onStartScan={onStartThinkingScan}
      onStopScan={onStopThinkingScan} onResume={onResumeThinkingScan}
      onExportCrawl={onExportCrawl} onImportCrawl={onImportCrawlClick}
      aliceRunning={aliceGlobalRunning} onStopAlice={handleAliceStop}
    />
    <input ref={crawlImportInputRef} type="file" accept="application/json,.json" hidden onChange={onImportCrawlFile} />

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

      <GuidedLoginNotices
        runId={runId}
        pending={guidedLoginPending}
        errors={guidedLoginErrors}
        entraPrompts={entraPrompts}
        interactiveLogins={interactiveLogins}
        onDismissError={credentialId => setGuidedLoginErrors(previous => previous.filter(item => item.credential_id !== credentialId))}
        onDismissEntraPrompt={id => setEntraPrompts(previous => previous.filter(item => item.id !== id))}
        onRetryEntraPrompt={async prompt => {
          try {
            const response = await fetch(`/api/test-runs/${runId}/entra-authenticator/${prompt.credential_id}/retry`, {
              method: "POST"
            });
            if (!response.ok) {
              const body = await response.json().catch(() => null);
              throw new Error(body?.detail || `Retry failed: ${response.status}`);
            }
            setEntraPrompts(previous => previous.map(item => item.id === prompt.id ? {
              ...item,
              status: "pending",
              message: `Retrying Entra login as ${prompt.username} - waiting for a new Authenticator number`
            } : item));
          } catch (err) {
            setError(err.message || "Could not retry Entra Authenticator approval");
          }
        }}
        onConfirmed={credentialId => setGuidedLoginPending(previous => previous.filter(item => item.credential_id !== credentialId))}
      />

      <WebRunNavigation
        activeTab={activeTab}
        onSelect={tab => { setActiveTab(tab); nav("#/runs/" + runId + "/" + tab); }}
        activityLive={isDynamicScanActive(thinkingStatus?.status) && activityLog.length > 0}
        counts={{ attack: attackSurfaceTotal, sessions: sessionsTotal, findings: findings.length, traffic: trafficTotal }}
        canClearCrawl={canClearCrawl}
        onClearCrawl={onClearCrawl}
        multiUser={run?.credentials?.length > 1}
        graphView={graphView}
        onGraphView={setGraphView}
      />

      {activeTab === "sitemap" && run && <>
        <WebRunSitemapMeta run={run} crawlUsername={crawlUsername} profiles={runProfiles} onRunUpdate={setRun} onError={setError} />
        {activeTab === "sitemap" && run && <ScopeHostsPanel siteId={run.site_id} hosts={scopeHosts} onChange={setScopeHosts} />}
        <WebRunCrawlProgress run={run} /></>}

      <WebRunSitemapGraph
        runId={runId}
        run={run}
        graph={graph}
        active={activeTab === "sitemap"}
        graphView={graphView}
        onGraphChange={setGraph}
        onStart={onStart}
        onStartThinkingScan={onStartThinkingScan}
        hasCheckpoint={hasCheckpoint}
        onResumeThinkingScan={onResumeThinkingScan}
        checkpointStatus={checkpointStatus}
        onError={setError}
      />

      {activeTab === "findings" && <WebRunFindingsTab
        thinkingStatus={thinkingStatus} thinkingStopRequested={thinkingStopRequested}
        validateStatus={validateStatus} onStopValidation={onStopValidation}
        dedupeBusy={dedupeBusy} findings={findings}
        onExportFindingsMarkdown={onExportFindingsMarkdown} onImportFindingsClick={onImportFindingsClick}
        issueImportInputRef={issueImportInputRef} onImportFindingsFile={onImportFindingsFile}
        validateBusy={validateBusy} onValidateAll={onValidateAll} aliceIsThinking={aliceIsThinking}
        onDeduplicateFindings={onDeduplicateFindings} clearBusy={clearBusy}
        setClearBusy={setClearBusy} setClearError={setClearError} runId={runId} setFindings={setFindings}
        editingFinding={editingFinding} setExpandedFinding={setExpandedFinding} expandedFinding={expandedFinding}
        onValidateFinding={onValidateFinding} onEditFinding={onEditFinding} onDeleteFinding={onDeleteFinding}
        editDraft={editDraft} setEditDraft={setEditDraft} editBusy={editBusy}
        onCancelEditFinding={onCancelEditFinding} onSaveEditFinding={onSaveEditFinding}
        toggleGroup={toggleGroup} expandedGroups={expandedGroups} findColW={findColW}
        startFindResize={startFindResize} onDeleteFindingGroup={onDeleteFindingGroup}
      />}

      <WebRunAttackSurfaceTab
        runId={runId}
        run={run}
        active={activeTab === "attack"}
        scanActive={isDynamicScanActive(thinkingStatus?.status)}
        onTotalChange={setAttackSurfaceTotal}
        intelligenceTotal={intelligenceTotal}
        onIntelligenceTotalChange={setIntelligenceTotal}
        intelligenceCaptureActive={run?.status === "running"}
        reloadKey={wpReloadKey}
        initialSubTab={initialTab === "tasks" ? "attack-surface" : initialTab === "intelligence" ? "intelligence" : "owasp"}
      />

      <WebRunSessionsTab
        runId={runId}
        active={activeTab === "sessions"}
        scanActive={isDynamicScanActive(thinkingStatus?.status)}
        onTotalChange={setSessionsTotal}
      />

      {activeTab === "activity" && <WebRunActivityTab
        activityLog={activityLog} tokenUsage={tokenUsage} setTokenExpanded={setTokenExpanded}
        tokenExpanded={tokenExpanded} activitySubTab={activitySubTab} setActivitySubTab={setActivitySubTab}
        agents={agents} normalizeAgentForRun={normalizeAgentForRun} activityFeedRef={activityFeedRef}
        runId={runId} clearBusy={clearBusy} setClearBusy={setClearBusy} setClearError={setClearError}
        setActivityLog={setActivityLog} setSitePlanData={setSitePlanData} setTokenUsage={setTokenUsage}
        sitePlanData={sitePlanData} expandedLogIds={expandedLogIds} toggleLogId={toggleLogId}
        collapsedAgentIds={collapsedAgentIds} toggleAgentId={toggleAgentId}
        defaultAgentRoster={defaultAgentRoster} representsAgent={representsAgent}
        aliceChats={aliceChats} activeAliceTabId={activeAliceTabId} setActiveAliceTabId={setActiveAliceTabId}
        deleteAliceTab={deleteAliceTab} createAliceTab={createAliceTab} aliceChatHeight={aliceChatHeight}
        aliceMessages={aliceMessages} aliceExpandedThinkIds={aliceExpandedThinkIds}
        setAliceExpandedThinkIds={setAliceExpandedThinkIds} aliceThinkingTabId={aliceThinkingTabId}
        startAliceResize={startAliceResize} aliceInputText={aliceInputText} aliceIsThinking={aliceIsThinking}
        handleAliceSend={handleAliceSend} setAliceInputText={setAliceInputText} handleAliceStop={handleAliceStop}
        agentRoleLabel={agentRoleLabel} agentCurrentTask={agentCurrentTask} agentCrawlEvents={agentCrawlEvents}
        agentTaskHistory={agentTaskHistory} agentStatusLabel={agentStatusLabel}
      />}

      <WebRunTrafficTab
        runId={runId}
        active={activeTab === "traffic"}
        captureActive={run?.status === "running" || isDynamicScanActive(thinkingStatus?.status) || crawlStopRequested || thinkingStopRequested}
        runStatus={run?.status}
        onTotalChange={setTrafficTotal}
      />
      {activeTab === "leads" && <WebRunSastLeadsTab runId={runId} scanRunning={isDynamicScanActive(thinkingStatus?.status)} />}
    </div></>;
}
