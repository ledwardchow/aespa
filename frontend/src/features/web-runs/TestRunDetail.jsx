import { normaliseWebTab } from "./tabs.js";
import { runHref } from "../../shared/navigation/links.ts";
import * as settingsApi from "../../shared/api/settings.js";
import * as sitesApi from "../../shared/api/sites.js";
import * as webRunsApi from "../../shared/api/webRuns.js";

import { ScopeHostsPanel } from "../../shared/runs/ScopeHostsPanel.jsx";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";

import { nav } from "../../shared/navigation/router.js";
import { useAliceChat } from "./useAliceChat.js";
import { useFindings } from "./useFindings.js";
import { useActivity } from "./useActivity.js";
import { isCrawlerAgentActive } from "./runState.js";

import { WebRunFindingsTab } from "./WebRunFindingsTab.jsx";
import { WebRunActivityTab } from "./WebRunActivityTab.jsx";
import { WebRunTrafficTab } from "./WebRunTrafficTab.jsx";
import { WebRunAttackSurfaceTab } from "./WebRunAttackSurfaceTab.jsx";
import { WebRunSessionsTab } from "./WebRunSessionsTab.jsx";
import { WebRunNavigation } from "./WebRunNavigation.jsx";
import { useWebRunEvents } from "./useWebRunEvents.js";
import { GuidedLoginNotices } from "./GuidedLoginNotices.jsx";
import { WebRunSitemapMeta } from "./WebRunSitemapMeta.jsx";
import { WebRunSitemapGraph } from "./WebRunSitemapGraph.jsx";
import { WebRunCrawlProgress } from "./WebRunCrawlProgress.jsx";
import { WebRunHeader } from "./WebRunHeader.jsx";
import { WebRunSastLeadsTab } from "../../shared/leads/RunLeadsTab.jsx";
import { isDynamicScanActive } from "../../shared/runs/presentation.jsx";

export function TestRunDetail({ runId, initialTab, initialFindingRef, initialLeadRef }) {
  const [run, setRun] = useState(null);
  const [siteName, setSiteName] = useState(null);
  const [graph, setGraph] = useState(null);
  const activeTab = normaliseWebTab(initialTab);
  const setActiveTab = (tab) => nav(runHref({ runKind: "web", runId }, tab));
  const [scopeHosts, setScopeHosts] = useState([]);
  const [graphView, setGraphView] = useState("scope"); // "scope" | "user"
  const [intelligenceTotal, setIntelligenceTotal] = useState(0);
  const [attackSurfaceTotal, setAttackSurfaceTotal] = useState(0);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [crawlUsername, setCrawlUsername] = useState(null);
  const [clearBusy, setClearBusy] = useState(""); // which section is clearing
  const [, setClearError] = useState(null);
  // per-user crawl progress is read directly from run.per_user_progress (kept in sync
  // by the periodic poll + SSE run_update events) — no separate state needed.
  const [runProfiles, setRunProfiles] = useState([]);

  // Guided login: list of {credential_id, username} waiting for "I'm Done" confirmation
  const [guidedLoginPending, setGuidedLoginPending] = useState([]);
  const [guidedLoginErrors, setGuidedLoginErrors] = useState([]);
  const [entraPrompts, setEntraPrompts] = useState([]);

  // Load LLM profiles once so the read-only display and edit dropdown both work.
  useEffect(() => {
    settingsApi
      .listLLMProfiles()
      .then(setRunProfiles)
      .catch(() => {});
  }, []);
  const [collapsedAgentIds, setCollapsedAgentIds] = useState(new Set());
  const toggleAgentId = (aid) =>
    setCollapsedAgentIds((prev) => {
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
    setAliceChats,
    createAliceTab,
    deleteAliceTab,
    startAliceResize,
    handleAliceStop,
    handleAliceSend,
    submitAliceDirective,
  } = useAliceChat(runId, {
    onActivate: () =>
      setCollapsedAgentIds((prev) => {
        if (!prev.has("alice")) return prev;
        const next = new Set(prev);
        next.delete("alice");
        return next;
      }),
  });
  useEffect(() => {
    const reopenAlicePanel = () => {
      setCollapsedAgentIds((prev) => {
        if (!prev.has("alice")) return prev;
        const next = new Set(prev);
        next.delete("alice");
        return next;
      });
    };
    const applyAlicePopoutState = (data) => {
      if (Array.isArray(data?.chats)) setAliceChats(data.chats);
      if (data?.active_tab_id) setActiveAliceTabId(data.active_tab_id);
      reopenAlicePanel();
    };
    const handleAlicePopoutClose = (event) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "aespa-alice-popout-close" || Number(event.data.runId) !== runId)
        return;
      applyAlicePopoutState(event.data);
    };
    const handleAlicePopoutStorage = (event) => {
      if (event.key !== `aespa-alice-popout-close:${runId}`) return;
      try {
        applyAlicePopoutState(JSON.parse(event.newValue || "null"));
      } catch {}
    };
    window.addEventListener("message", handleAlicePopoutClose);
    window.addEventListener("storage", handleAlicePopoutStorage);
    return () => {
      window.removeEventListener("message", handleAlicePopoutClose);
      window.removeEventListener("storage", handleAlicePopoutStorage);
    };
  }, [runId, setActiveAliceTabId, setAliceChats]);
  const [crawlStopRequested, setCrawlStopRequested] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState(null);
  const [thinkingStopRequested, setThinkingStopReq] = useState(false);
  const [coverageMode, setCoverageMode] = useState("track");
  const [crawlCredentialId, setCrawlCredentialId] = useState(null);
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
    onStopValidation,
  } = useFindings(runId, activeTab, {
    run,
    siteName,
    submitAliceDirective,
    aliceIsThinking,
    setRun,
    setGraph,
    setError,
    initialFindingRef,
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
    agentStatusLabel,
  } = useActivity(runId, activeTab, {
    run,
    thinkingStatus,
    aliceIsThinking,
  });

  const crawlerAgent = agents.find((agent) => agent.id === "crawler");
  const crawlerTask = crawlerAgent ? agentCurrentTask(crawlerAgent) : null;
  const crawlerActive = isCrawlerAgentActive(crawlerAgent, crawlStopRequested);

  // Initial load
  const loadAll = useCallback(async () => {
    try {
      const [r, g] = await Promise.all([webRunsApi.getRun(runId), webRunsApi.getGraph(runId)]);
      setRun(r);
      setGraph(g);
      if (r?.scope_hosts) setScopeHosts(r.scope_hosts);
      if (r?.coverage_mode) setCoverageMode(r.coverage_mode);
      webRunsApi
        .getThinkingStatus(runId)
        .then(setThinkingStatus)
        .catch(() => {});
      webRunsApi
        .getCheckpointStatus(runId)
        .then(setCheckpointStatus)
        .catch(() => {});
      sitesApi
        .getSite(r.site_id)
        .then((s) => setSiteName(s.name))
        .catch(() => {});
    } catch (e) {
      setError(e.message);
    }
  }, [runId]);
  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useWebRunEvents({
    runId,
    setGraph,
    setCrawlUsername,
    setRun,
    setCrawlStopRequested,
    setAgents,
    upsertAgent,
    setThinkingStatus,
    setThinkingStopReq,
    setActivityLog,
    setSitePlanData,
    setFindings,
    setValidateStatus,
    setValidateBusy,
    setTokenUsage,
    setScopeHosts,
    setGuidedLoginPending,
    setGuidedLoginErrors,
    setEntraPrompts,
    setCheckpointStatus,
  });

  // Fetch checkpoint status whenever dynamic scan transitions to an inactive status (stopped/complete/failed/idle)
  useEffect(() => {
    if (thinkingStatus?.status && !isDynamicScanActive(thinkingStatus.status)) {
      webRunsApi
        .getCheckpointStatus(runId)
        .then(setCheckpointStatus)
        .catch(() => {});
    }
  }, [runId, thinkingStatus?.status]);

  // Poll run metadata (including per_user_progress current URLs) while crawling
  // or while the backend is unwinding after a stop request.
  useEffect(() => {
    if (!crawlerActive) return;
    const iv = setInterval(() => {
      Promise.all([webRunsApi.getRun(runId), webRunsApi.getCrawlStatus(runId).catch(() => null)])
        .then(([r, crawlStatus]) => {
          lastRunPollOkRef.current = Date.now();
          setRun(r);
          if (crawlStatus?.running === false) {
            setAgents((prev) =>
              prev.map((a) =>
                a.id === "crawler" && a.status === "active"
                  ? {
                      ...a,
                      status: "idle",
                      currentTask: "Crawl is not running",
                    }
                  : a,
              ),
            );
          }
          if (crawlStopRequested && crawlStatus?.running === false) setCrawlStopRequested(false);
        })
        .catch(() => {
          setAgents((prev) =>
            prev.map((a) =>
              a.id === "crawler" && a.status === "active"
                ? {
                    ...a,
                    status: "idle",
                    currentTask: "Crawler connection stale",
                  }
                : a,
            ),
          );
        });
    }, 2000);
    return () => clearInterval(iv);
  }, [crawlerActive, runId, crawlStopRequested, setAgents]);

  // Poll thinking-scan status independently.
  useEffect(() => {
    const active = isDynamicScanActive(thinkingStatus?.status) || thinkingStopRequested;
    if (!active) return;
    const iv = setInterval(() => {
      webRunsApi
        .getThinkingStatus(runId)
        .then((s) => {
          setThinkingStatus(s);
          if (thinkingStopRequested && !isDynamicScanActive(s.status)) setThinkingStopReq(false);
          if (!isDynamicScanActive(s.status)) {
            webRunsApi
              .getFindings(runId)
              .then(setFindings)
              .catch(() => {});
            // Refresh checkpoint status once the scan finishes so the Resume button
            // appears/disappears correctly without a page reload.
            webRunsApi
              .getCheckpointStatus(runId)
              .then(setCheckpointStatus)
              .catch(() => {});
          }
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, [runId, thinkingStatus?.status, thinkingStopRequested, setFindings]);

  const onStopThinkingScan = async () => {
    try {
      setThinkingStopReq(true);
      const s = await webRunsApi.stopThinkingScan(runId);
      setThinkingStatus(s);
      if (!isDynamicScanActive(s.status)) {
        setThinkingStopReq(false);
        webRunsApi
          .getCheckpointStatus(runId)
          .then(setCheckpointStatus)
          .catch(() => {});
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
        status: "running",
      });
      setCheckpointStatus(null);
      const s = await webRunsApi.startThinkingScan(runId, coverageMode);
      setThinkingStatus(s);
      setWpReloadKey((k) => k + 1);
    } catch (e) {
      setThinkingStopReq(false);
      setError(e.message);
    }
  };
  const onResumeThinkingScan = async () => {
    try {
      setThinkingStopReq(false);
      setThinkingStatus({
        status: "running",
      });
      const s = await webRunsApi.resumeThinkingScan(runId);
      setThinkingStatus(s);
      setWpReloadKey((k) => k + 1);
    } catch (e) {
      setThinkingStopReq(false);
      setError(e.message);
    }
  };
  const onStart = async () => {
    try {
      setCrawlStopRequested(false);
      const body = crawlCredentialId ? { crawl_credential_id: crawlCredentialId } : undefined;
      const r = await webRunsApi.startRun(runId, body);
      // Optimistically mark as running so the poll interval starts immediately.
      // Clear per_user_progress so stale data from the previous crawl is never
      // shown — fresh entries arrive via crawl_progress SSE events.
      setRun({
        ...r,
        status: "running",
        per_user_progress: {},
      });
    } catch (e) {
      setError(e.message);
    }
  };
  const onStop = async () => {
    try {
      setCrawlStopRequested(true);
      const r = await webRunsApi.stopRun(runId);
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
        links: [],
      });
      const r = await webRunsApi.clearCrawl(runId);
      setRun({
        ...r,
        status: "pending",
        per_user_progress: null,
      });
    } catch (e) {
      setError(e.message);
    }
  };
  const onExportCrawl = () => webRunsApi.exportCrawl(runId);
  const onImportCrawlClick = () => crawlImportInputRef.current?.click();
  const onImportCrawlFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const imported = await webRunsApi.importCrawl(runId, file);
      const importedGraph = await webRunsApi.getGraph(runId);
      setRun(imported);
      setGraph(importedGraph);
      setWpReloadKey((key) => key + 1);
      setActiveTab("sitemap");
    } catch (e) {
      setError(e.message);
    }
  };
  const effectiveThinkingStatus = thinkingStatus?.status || "idle";
  const testLeadActive = isDynamicScanActive(effectiveThinkingStatus) || thinkingStopRequested;
  const canStart =
    run && !crawlStopRequested && ["pending", "stopped", "failed", "complete"].includes(run.status);
  const canImportCrawl =
    run?.status === "pending" &&
    !crawlStopRequested &&
    !isDynamicScanActive(effectiveThinkingStatus);
  const canClearCrawl =
    run && !crawlStopRequested && ["stopped", "failed", "complete"].includes(run.status);
  const canStop = isCrawlerAgentActive(crawlerAgent) && !crawlStopRequested;
  const canStopThinking = isDynamicScanActive(effectiveThinkingStatus);
  const canStartAnyScan =
    run?.status !== "running" &&
    !crawlStopRequested &&
    !isDynamicScanActive(effectiveThinkingStatus);
  const canStartThinking =
    !thinkingStopRequested &&
    canStartAnyScan &&
    ["idle", "complete", "stopped", "failed", null].includes(effectiveThinkingStatus);
  const hasCheckpoint =
    checkpointStatus?.exists === true &&
    canStartAnyScan &&
    !isDynamicScanActive(effectiveThinkingStatus);
  const interactiveLogins = useMemo(
    () =>
      (run?.credentials || []).flatMap((credential) => {
        const authMode = credential.auth_mode || "auto";
        if (authMode === "guided") {
          return [
            {
              credential_id: credential.id,
              username: credential.username,
              label: credential.label,
              mode: "Guided",
            },
          ];
        }
        if (authMode === "entra_id" && !credential.has_totp_seed) {
          return [
            {
              credential_id: credential.id,
              username: credential.username,
              label: credential.label,
              mode: "Entra ID",
            },
          ];
        }
        return [];
      }),
    [run?.credentials],
  );
  if (!run) {
    return (
      <div className="content scroll-content">
        {error ? (
          <div className="alert error">{error}</div>
        ) : (
          <div className="subtle">Loading…</div>
        )}
      </div>
    );
  }
  return (
    <>
      <WebRunHeader
        run={run}
        siteName={siteName}
        profiles={runProfiles}
        crawlerActive={crawlerActive}
        testLeadActive={testLeadActive}
        canStart={canStart}
        canStop={canStop}
        canStartScan={canStartThinking}
        canStopScan={canStopThinking}
        canResume={hasCheckpoint}
        canImportCrawl={canImportCrawl}
        crawlStopping={crawlStopRequested}
        scanStopping={thinkingStopRequested}
        coverageMode={coverageMode}
        onCoverageMode={setCoverageMode}
        onStart={onStart}
        onStop={onStop}
        onStartScan={onStartThinkingScan}
        onStopScan={onStopThinkingScan}
        onResume={onResumeThinkingScan}
        onExportCrawl={onExportCrawl}
        onImportCrawl={onImportCrawlClick}
        aliceRunning={aliceGlobalRunning}
        onStopAlice={handleAliceStop}
      />
      <input
        ref={crawlImportInputRef}
        type="file"
        accept="application/json,.json"
        hidden
        onChange={onImportCrawlFile}
      />

      <div
        className="content"
        style={{
          paddingTop: 0,
          paddingBottom: 0,
          display: "flex",
          flexDirection: "column",
          flex: 1,
          minHeight: 0,
        }}
      >
        {error && (
          <div
            className="alert error"
            style={{
              marginBottom: 12,
            }}
          >
            {error}
          </div>
        )}

        <GuidedLoginNotices
          runId={runId}
          pending={guidedLoginPending}
          errors={guidedLoginErrors}
          entraPrompts={entraPrompts}
          interactiveLogins={interactiveLogins}
          onDismissError={(credentialId) =>
            setGuidedLoginErrors((previous) =>
              previous.filter((item) => item.credential_id !== credentialId),
            )
          }
          onDismissEntraPrompt={(id) =>
            setEntraPrompts((previous) => previous.filter((item) => item.id !== id))
          }
          onRetryEntraPrompt={async (prompt) => {
            try {
              const response = await fetch(
                `/api/test-runs/${runId}/entra-authenticator/${prompt.credential_id}/retry`,
                {
                  method: "POST",
                },
              );
              if (!response.ok) {
                const body = await response.json().catch(() => null);
                throw new Error(body?.detail || `Retry failed: ${response.status}`);
              }
              setEntraPrompts((previous) =>
                previous.map((item) =>
                  item.id === prompt.id
                    ? {
                        ...item,
                        status: "pending",
                        message: `Retrying Entra login as ${prompt.username} - waiting for a new Authenticator number`,
                      }
                    : item,
                ),
              );
            } catch (err) {
              setError(err.message || "Could not retry Entra Authenticator approval");
            }
          }}
          onConfirmed={(credentialId) =>
            setGuidedLoginPending((previous) =>
              previous.filter((item) => item.credential_id !== credentialId),
            )
          }
        />

        <WebRunNavigation
          activeTab={activeTab}
          onSelect={(tab) => {
            setActiveTab(tab);
          }}
          activityLive={
            (run?.status === "running" || isDynamicScanActive(thinkingStatus?.status)) &&
            activityLog.length > 0
          }
          counts={{
            attack: attackSurfaceTotal,
            sessions: sessionsTotal,
            findings: findings.length,
            traffic: trafficTotal,
          }}
          canClearCrawl={canClearCrawl}
          onClearCrawl={onClearCrawl}
          multiUser={run?.credentials?.length > 1}
          graphView={graphView}
          onGraphView={setGraphView}
        />

        {activeTab === "sitemap" && run && (
          <>
            <WebRunSitemapMeta
              run={run}
              graph={graph}
              crawlUsername={crawlUsername}
              profiles={runProfiles}
              onRunUpdate={setRun}
              onError={setError}
              crawlCredentialId={crawlCredentialId}
              onCrawlCredentialChange={setCrawlCredentialId}
            />
            {activeTab === "sitemap" && run && (
              <ScopeHostsPanel siteId={run.site_id} hosts={scopeHosts} onChange={setScopeHosts} />
            )}
            <WebRunCrawlProgress
              run={run}
              crawlerTask={crawlerTask}
              crawlerActive={crawlerActive}
            />
          </>
        )}

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

        {activeTab === "findings" && (
          <WebRunFindingsTab
            thinkingStatus={thinkingStatus}
            thinkingStopRequested={thinkingStopRequested}
            validateStatus={validateStatus}
            onStopValidation={onStopValidation}
            dedupeBusy={dedupeBusy}
            findings={findings}
            onExportFindingsMarkdown={onExportFindingsMarkdown}
            onImportFindingsClick={onImportFindingsClick}
            issueImportInputRef={issueImportInputRef}
            onImportFindingsFile={onImportFindingsFile}
            validateBusy={validateBusy}
            onValidateAll={onValidateAll}
            aliceIsThinking={aliceIsThinking}
            onDeduplicateFindings={onDeduplicateFindings}
            clearBusy={clearBusy}
            setClearBusy={setClearBusy}
            setClearError={setClearError}
            runId={runId}
            setFindings={setFindings}
            editingFinding={editingFinding}
            setExpandedFinding={setExpandedFinding}
            expandedFinding={expandedFinding}
            onValidateFinding={onValidateFinding}
            onEditFinding={onEditFinding}
            onDeleteFinding={onDeleteFinding}
            editDraft={editDraft}
            setEditDraft={setEditDraft}
            editBusy={editBusy}
            onCancelEditFinding={onCancelEditFinding}
            onSaveEditFinding={onSaveEditFinding}
            toggleGroup={toggleGroup}
            expandedGroups={expandedGroups}
            findColW={findColW}
            startFindResize={startFindResize}
            onDeleteFindingGroup={onDeleteFindingGroup}
          />
        )}

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
          initialSubTab={
            initialTab === "tasks"
              ? "attack-surface"
              : initialTab === "intelligence"
                ? "intelligence"
                : "owasp"
          }
        />

        <WebRunSessionsTab
          runId={runId}
          active={activeTab === "sessions"}
          scanActive={isDynamicScanActive(thinkingStatus?.status)}
          onTotalChange={setSessionsTotal}
        />

        {activeTab === "activity" && (
          <WebRunActivityTab
            activityLog={activityLog}
            tokenUsage={tokenUsage}
            setTokenExpanded={setTokenExpanded}
            tokenExpanded={tokenExpanded}
            activitySubTab={activitySubTab}
            setActivitySubTab={setActivitySubTab}
            agents={agents}
            normalizeAgentForRun={normalizeAgentForRun}
            activityFeedRef={activityFeedRef}
            runId={runId}
            clearBusy={clearBusy}
            setClearBusy={setClearBusy}
            setClearError={setClearError}
            setActivityLog={setActivityLog}
            setSitePlanData={setSitePlanData}
            setTokenUsage={setTokenUsage}
            sitePlanData={sitePlanData}
            expandedLogIds={expandedLogIds}
            toggleLogId={toggleLogId}
            collapsedAgentIds={collapsedAgentIds}
            toggleAgentId={toggleAgentId}
            defaultAgentRoster={defaultAgentRoster}
            representsAgent={representsAgent}
            aliceChats={aliceChats}
            activeAliceTabId={activeAliceTabId}
            setActiveAliceTabId={setActiveAliceTabId}
            deleteAliceTab={deleteAliceTab}
            createAliceTab={createAliceTab}
            aliceChatHeight={aliceChatHeight}
            aliceMessages={aliceMessages}
            aliceExpandedThinkIds={aliceExpandedThinkIds}
            setAliceExpandedThinkIds={setAliceExpandedThinkIds}
            aliceThinkingTabId={aliceThinkingTabId}
            startAliceResize={startAliceResize}
            aliceInputText={aliceInputText}
            aliceIsThinking={aliceIsThinking}
            handleAliceSend={handleAliceSend}
            setAliceInputText={setAliceInputText}
            handleAliceStop={handleAliceStop}
            submitAliceDirective={submitAliceDirective}
            agentRoleLabel={agentRoleLabel}
            agentCurrentTask={agentCurrentTask}
            agentCrawlEvents={agentCrawlEvents}
            agentTaskHistory={agentTaskHistory}
            agentStatusLabel={agentStatusLabel}
          />
        )}

        <WebRunTrafficTab
          runId={runId}
          graph={graph}
          active={activeTab === "traffic"}
          captureActive={
            run?.status === "running" ||
            isDynamicScanActive(thinkingStatus?.status) ||
            crawlStopRequested ||
            thinkingStopRequested
          }
          runStatus={run?.status}
          onTotalChange={setTrafficTotal}
        />
        {activeTab === "leads" && (
          <WebRunSastLeadsTab
            runId={runId}
            scanRunning={isDynamicScanActive(thinkingStatus?.status)}
            initialLeadRef={initialLeadRef}
          />
        )}
      </div>
    </>
  );
}
