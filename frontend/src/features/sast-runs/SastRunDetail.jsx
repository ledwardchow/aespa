import { runHref } from "../../shared/navigation/links.ts";
import { SastModelSelector, profileLabel } from "./SastModelSelector.jsx";
import { SastRunActionsMenu } from "./SastRunActionsMenu.jsx";
import { ActivityView } from "./ActivityView.jsx";
import { CoverageView } from "./CoverageView.jsx";
import { CandidatesView } from "./CandidatesView.jsx";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { nav } from "../../shared/navigation/router.js";
import { sastCandidatesToMarkdown, sastReportFilename } from "../../shared/leads/files.js";
import { downloadTextFile } from "../../shared/lib/download.js";

import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";

const PHASES = [
  { key: "scope", label: "Scope", short: "Archive and inventory", view: "coverage" },
  { key: "discovery", label: "Discovery", short: "Source-to-sink candidates", view: "candidates" },
  {
    key: "validation",
    label: "Validation",
    short: "Controls and counterevidence",
    view: "candidates",
  },
  {
    key: "attack_path",
    label: "Attack paths",
    short: "Reachability and severity",
    view: "candidates",
  },
  { key: "report", label: "Report", short: "Findings and coverage", view: "coverage" },
];

const TAB_ALIASES = { overview: "coverage", progress: "coverage", leads: "candidates" };

function normaliseTab(tab) {
  const candidate = TAB_ALIASES[tab] || tab;
  return ["coverage", "candidates", "activity"].includes(candidate) ? candidate : "coverage";
}

function jsonValue(value, fallback) {
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(value || "");
  } catch {
    return fallback;
  }
}

function phaseIcon(status) {
  if (status === "complete") return "✓";
  if (status === "running") return "●";
  if (status === "failed") return "!";
  if (status === "cancelled") return "×";
  return "";
}

export function SastRunDetailExperience({ runId, initialTab, initialLeadRef }) {
  const [run, setRun] = useState(null);
  const [analysis, setAnalysis] = useState({
    phases: {},
    coverage: { files: [], summary: {} },
    work_program: {},
    assurance: {},
    report: {},
  });
  const [logs, setLogs] = useState([]);
  const [agentLog, setAgentLog] = useState([]);
  const [leads, setLeads] = useState([]);
  const [targets, setTargets] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [tokenUsage, setTokenUsage] = useState(null);
  const tab = normaliseTab(initialTab);
  const [activePhase, setActivePhase] = useState(null);
  const [selectedLeadId, setSelectedLeadId] = useState(null);
  const [scanRunning, setScanRunning] = useState(false);
  const [startBusy, setStartBusy] = useState(false);
  const [queueBusy, setQueueBusy] = useState(false);
  const [profileBusy, setProfileBusy] = useState(false);
  const [tokenExpanded, setTokenExpanded] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const bottomRef = useRef(null);

  const loadData = useCallback(async () => {
    try {
      const [runData, status, analysisData, logData, agentData, leadData, usage, targetData] =
        await Promise.all([
          sastRunsApi.getSastRun(runId),
          sastRunsApi.getSastScanStatus(runId),
          sastRunsApi.getSastAnalysis(runId),
          sastRunsApi.getSastScanLog(runId),
          sastRunsApi.getSastAgentLog(runId),
          sastRunsApi.getSastLeads(runId),
          sastRunsApi.getSastTokenUsage(runId),
          sastRunsApi.getSastHandoffTargets(runId),
        ]);
      setRun(runData);
      setScanRunning(status.running);
      setAnalysis(analysisData);
      setLogs(logData || []);
      setAgentLog(agentData || []);
      setLeads(leadData || []);
      setTokenUsage(usage);
      setTargets(targetData || []);
      setSelectedLeadId(
        (previous) =>
          previous ??
          leadData?.find((lead) => lead.reference === initialLeadRef)?.id ??
          leadData?.[0]?.id ??
          null,
      );
    } catch (err) {
      setError(err.message);
    }
  }, [runId, initialLeadRef]);

  useEffect(() => {
    loadData();
  }, [loadData]);
  useEffect(() => {
    settingsApi
      .listLLMProfiles()
      .then((items) => setProfiles(items || []))
      .catch((err) => setError(err.message));
  }, []);
  useEffect(() => {
    const timer = setInterval(loadData, scanRunning ? 3000 : 8000);
    return () => clearInterval(timer);
  }, [loadData, scanRunning]);
  useEffect(() => {
    const es = new EventSource(`/api/sast-runs/${runId}/events`);
    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "token_usage_update") setTokenUsage(payload.totals);
        if (payload.type === "scanner_phase" || payload.type === "agent_status") loadData();
      } catch {}
    };
    return () => es.close();
  }, [runId, loadData]);
  useEffect(() => {
    if (tab === "activity" && scanRunning)
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [logs.length, tab, scanRunning]);

  const statuses = useMemo(
    () =>
      Object.fromEntries(
        PHASES.map((phase) => [phase.key, analysis.phases?.[phase.key]?.status || "pending"]),
      ),
    [analysis.phases],
  );
  const currentPhase =
    PHASES.find((phase) => statuses[phase.key] === "running")?.key ||
    PHASES.find((phase) => statuses[phase.key] === "pending")?.key ||
    "report";
  const displayedPhase = activePhase || currentPhase;
  const selectedLead = useMemo(
    () => leads.find((lead) => lead.id === selectedLeadId) || leads[0] || null,
    [leads, selectedLeadId],
  );
  const reportableCount = leads.filter((lead) => lead.reportable).length;
  const proofGapCount = leads.reduce(
    (count, lead) => count + jsonValue(lead.proof_gaps_json, []).length,
    0,
  );
  const workItemSummary = analysis.work_program?.work_items || {};
  const workerSummary = analysis.work_program?.workers || {};
  const fileSummary = analysis.work_program?.files || {};
  const failedWorkers = (workerSummary.failed || 0) + (workerSummary.blocked || 0);
  const unfinishedWorkers = Math.max(
    (workerSummary.total || 0) - (workerSummary.complete || 0) - failedWorkers,
    0,
  );
  const goTab = (nextTab) => {
    nav(runHref({ runKind: "sast", runId }, nextTab));
  };
  const onStart = async () => {
    setStartBusy(true);
    setError(null);
    try {
      await sastRunsApi.startSastScan(runId);
      setActivePhase(null);
      setScanRunning(true);
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setStartBusy(false);
    }
  };
  const onPause = async () => {
    setStartBusy(true);
    setError(null);
    try {
      await sastRunsApi.pauseSastScan(runId);
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setStartBusy(false);
    }
  };
  const onStop = async () => {
    try {
      await sastRunsApi.stopSastScan(runId);
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  };
  const onResume = async () => {
    setStartBusy(true);
    setError(null);
    try {
      await sastRunsApi.resumeSastScan(runId);
      setScanRunning(true);
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setStartBusy(false);
    }
  };
  const onDelete = async () => {
    if (!confirm("Delete this SAST run and all its leads?")) return;
    try {
      const collId = run?.collection_id;
      await sastRunsApi.deleteSastRun(runId);
      nav(collId ? `#/apis/${collId}/files` : "#/sast-runs");
    } catch (err) {
      setError(err.message);
    }
  };
  const onQueue = async (lead, target) => {
    setQueueBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await sastRunsApi.handoffSastLead(runId, lead.id, {
        run_type: target.run_type,
        run_id: target.run_id,
      });
      setNotice(
        `Lead ${lead.reference || `#${lead.id}`} queued as ${result.lead_reference || `#${result.lead_id}`} in ${target.run_type.toUpperCase()} run #${target.run_id}.`,
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setQueueBusy(false);
    }
  };
  const onExportReport = () =>
    downloadTextFile(
      sastReportFilename(run?.name, runId),
      sastCandidatesToMarkdown(leads, { runName: run?.name, generatedAt: new Date() }),
      "text/markdown;charset=utf-8",
    );
  const onProfileChange = async (llmProfileId) => {
    setProfileBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await sastRunsApi.updateSastRun(runId, { llm_profile_id: llmProfileId });
      setRun(updated);
      const selected = profiles.find((profile) => profile.id === llmProfileId);
      setNotice(
        llmProfileId
          ? `Model profile changed to ${profileLabel(selected)}. It will be used by the next scan.`
          : "This run now follows the globally active model profile for its next scan.",
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setProfileBusy(false);
    }
  };
  const canStart =
    run && !scanRunning && ["pending", "completed", "failed", "cancelled"].includes(run.status);

  if (!run)
    return (
      <div className="content scroll-content">
        {error ? (
          <div className="alert error">{error}</div>
        ) : (
          <div className="subtle">Loading…</div>
        )}
      </div>
    );
  const phaseEntry = analysis.phases?.[displayedPhase] || {};
  return (
    <>
      <PageHeader
        className="sast-run-topbar"
        title={
          <span className="sast-header-title">
            <Crumb href="#/sast-runs">SAST</Crumb>
            <Sep />
            <span className="sast-header-name">{run.name}</span>
            <StatusBadge status={scanRunning ? "scanning" : run.status} />
          </span>
        }
        actions={
          <>
            <SastModelSelector
              run={run}
              profiles={profiles}
              disabled={scanRunning}
              saving={profileBusy}
              onChange={onProfileChange}
            />
            {canStart && (
              <button className="btn" disabled={startBusy} onClick={onStart}>
                {startBusy ? "Starting…" : "Start SAST Scan"}
              </button>
            )}
            {run.status === "paused" && (
              <button className="btn" disabled={startBusy} onClick={onResume}>
                {startBusy ? "Resuming…" : "Resume SAST Scan"}
              </button>
            )}
            {scanRunning && (
              <button className="btn secondary" disabled={startBusy} onClick={onPause}>
                {startBusy ? "Pausing…" : "Pause"}
              </button>
            )}
            {scanRunning && (
              <button className="btn danger-outline" onClick={onStop}>
                Stop
              </button>
            )}
            <SastRunActionsMenu runId={runId} onDelete={onDelete} />
          </>
        }
      />
      <div className="sast-run-shell">
        <div className="sast-phase-rail" role="tablist" aria-label="SAST scan phases">
          {PHASES.map((phase, index) => (
            <button
              key={phase.key}
              className={`sast-phase-step ${displayedPhase === phase.key ? "active" : ""} status-${statuses[phase.key]}`}
              onClick={() => {
                setActivePhase(phase.key);
                goTab(phase.view);
              }}
              role="tab"
              aria-selected={displayedPhase === phase.key}
            >
              {statuses[phase.key] === "running" ? (
                <span
                  className="agent-dot agent-dot--active sast-phase-running-dot"
                  aria-label="running"
                />
              ) : (
                <span className="sast-phase-marker">
                  {phaseIcon(statuses[phase.key]) || index + 1}
                </span>
              )}
              <span className="sast-phase-label">{phase.label}</span>
              <span className="sast-phase-meta">
                {statuses[phase.key] === "pending" ? phase.short : statuses[phase.key]}
              </span>
            </button>
          ))}
        </div>
        <div className="sast-view-tabs" role="tablist" aria-label="SAST run views">
          {[
            { key: "coverage", label: "Coverage" },
            { key: "candidates", label: `Candidates ${leads.length}` },
            { key: "activity", label: "Activity" },
          ].map((item) => (
            <button
              key={item.key}
              className={tab === item.key ? "active" : ""}
              onClick={() => goTab(item.key)}
              role="tab"
              aria-selected={tab === item.key}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="sast-run-content">
          {error && <div className="alert error">{error}</div>}
          {notice && <div className="alert info sast-inline-notice">{notice}</div>}
          <div className="sast-phase-banner">
            <div>
              <strong>{PHASES.find((item) => item.key === displayedPhase)?.label}</strong>
              <span>{phaseEntry.message || "This phase has not started."}</span>
            </div>
            <span className="sast-phase-banner-status">{statuses[displayedPhase]}</span>
          </div>
          <div className="sast-summary-grid sast-run-summary-grid">
            <div>
              <span>Security checks</span>
              <strong>
                {workItemSummary.resolved || 0}/{workItemSummary.total || 0}
              </strong>
              <small>{workItemSummary.unresolved || 0} remaining</small>
            </div>
            <div>
              <span>Analysis batches</span>
              <strong>
                {workerSummary.complete || 0}/{workerSummary.total || 0}
              </strong>
              <small>
                {unfinishedWorkers} unfinished{failedWorkers ? ` · ${failedWorkers} failed` : ""}
              </small>
            </div>
            <div>
              <span>Direct file reads</span>
              <strong>
                {fileSummary.directly_opened || 0}/{fileSummary.total || 0}
              </strong>
              <small>grep excluded</small>
            </div>
            <div>
              <span>Search matches</span>
              <strong>{fileSummary.with_search_matches || 0}</strong>
              <small>files returned</small>
            </div>
            <div>
              <span>Candidates</span>
              <strong>{leads.length}</strong>
              <small>persisted hypotheses</small>
            </div>
            <div>
              <span>Reportable</span>
              <strong>{reportableCount}</strong>
              <small>independently confirmed</small>
            </div>
            <div>
              <span>Proof gaps</span>
              <strong>{proofGapCount}</strong>
              <small>unresolved evidence</small>
            </div>
          </div>
          {tab === "candidates" && (
            <CandidatesView
              leads={leads}
              selectedLead={selectedLead}
              onSelect={setSelectedLeadId}
              targets={targets}
              onQueue={onQueue}
              queueBusy={queueBusy}
              reportableCount={reportableCount}
              onExport={onExportReport}
            />
          )}
          {tab === "coverage" && (
            <div className="sast-assurance-note">
              <span>
                <strong>Coverage assurance:</strong>{" "}
                {analysis.assurance?.reasons?.length
                  ? analysis.assurance.reasons.join(" ")
                  : "Every generated source and sink obligation was closed."}
              </span>
              <span
                className={`sast-state sast-state-${analysis.assurance?.status === "full" ? "confirmed" : "inconclusive"}`}
              >
                {analysis.assurance?.status || "pending"}
              </span>
            </div>
          )}
          {tab === "coverage" && (
            <CoverageView coverage={analysis.coverage} workProgram={analysis.work_program} />
          )}
          {tab === "activity" && (
            <ActivityView
              logs={logs}
              agentLog={agentLog}
              scanRunning={scanRunning}
              tokenUsage={tokenUsage}
              tokenExpanded={tokenExpanded}
              setTokenExpanded={setTokenExpanded}
              runId={runId}
            />
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </>
  );
}
