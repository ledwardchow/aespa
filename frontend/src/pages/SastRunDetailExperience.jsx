import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import { nav } from "../lib/router";
import { downloadTextFile, sastCandidatesToMarkdown, sastReportFilename } from "../lib/utilities";
import { SastLeadDetails } from "../components/SastLeadDetails";
import { PageHeader, Crumb, Sep } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { TokenUsageBar } from "../components/TokenUsageBar";
import { LeadReferenceLink } from "../components/FindingReferenceLink";

const PHASES = [
  { key: "scope", label: "Scope", short: "Archive and inventory", view: "coverage" },
  { key: "discovery", label: "Discovery", short: "Source-to-sink candidates", view: "candidates" },
  { key: "validation", label: "Validation", short: "Controls and counterevidence", view: "candidates" },
  { key: "attack_path", label: "Attack paths", short: "Reachability and severity", view: "candidates" },
  { key: "report", label: "Report", short: "Findings and coverage", view: "coverage" },
];

const TAB_ALIASES = { overview: "coverage", progress: "coverage", leads: "candidates" };
const CANDIDATE_COLUMN_WIDTHS_KEY = "sast-candidate-columns:v1";
const CANDIDATE_SPLIT_KEY = "sast-candidate-split:v1";
const DEFAULT_CANDIDATE_COLUMN_WIDTHS = [88, null, 96, 132];
const MIN_CANDIDATE_SPLIT = 35;
const MAX_CANDIDATE_SPLIT = 72;
const DEFAULT_CANDIDATE_SPLIT = 54;

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function readStoredValue(key, fallback, validate) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return validate(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

function normaliseTab(tab) {
  const candidate = TAB_ALIASES[tab] || tab;
  return ["coverage", "candidates", "activity"].includes(candidate) ? candidate : "coverage";
}

function jsonValue(value, fallback) {
  if (value && typeof value === "object") return value;
  try { return JSON.parse(value || ""); } catch { return fallback; }
}

function formatTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function phaseIcon(status) {
  if (status === "complete") return "✓";
  if (status === "running") return "●";
  if (status === "failed") return "!";
  if (status === "cancelled") return "×";
  return "";
}

function profileLabel(profile) {
  if (!profile) return "Unknown profile";
  return `${profile.name}${profile.default_model_name ? ` · ${profile.default_model_name}` : ""}`;
}

function SastModelSelector({ run, profiles, disabled, saving, onChange }) {
  const activeProfile = profiles.find(profile => profile.is_active);
  return <label className="sast-model-selector">
    <span>Model</span>
    <select
      className="select"
      aria-label="SAST model profile"
      value={run.llm_profile_id || ""}
      disabled={disabled || saving}
      onChange={event => onChange(event.target.value ? Number(event.target.value) : null)}
      title={disabled ? "Stop the scan before changing its model profile" : "Model profile used by the next SAST scan"}
    >
      <option value="">Global active{activeProfile ? ` · ${profileLabel(activeProfile)}` : ""}</option>
      {profiles.map(profile => <option key={profile.id} value={profile.id}>{profileLabel(profile)}</option>)}
    </select>
    {saving && <em>Saving…</em>}
  </label>;
}

function SastRunActionsMenu({ runId, onDelete }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = event => {
      if (!menuRef.current?.contains(event.target)) setOpen(false);
    };
    const closeOnEscape = event => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return <div className="sast-actions-menu" ref={menuRef}>
    <button
      className="btn ghost sast-actions-menu-trigger"
      type="button"
      aria-label="More run actions"
      aria-haspopup="menu"
      aria-expanded={open}
      title="More run actions"
      onClick={() => setOpen(current => !current)}
    >⋯</button>
    {open && <div className="sast-actions-popover" role="menu">
      <a href={`/api/sast-runs/${runId}/export`} download role="menuitem" onClick={() => setOpen(false)}>Export run</a>
      <button type="button" className="danger" role="menuitem" onClick={() => { setOpen(false); onDelete(); }}>Delete run</button>
    </div>}
  </div>;
}

function CandidateTable({ leads, selectedId, onSelect }) {
  const [widths, setWidths] = useState(() => readStoredValue(
    CANDIDATE_COLUMN_WIDTHS_KEY,
    DEFAULT_CANDIDATE_COLUMN_WIDTHS,
    value => Array.isArray(value) && value.length === DEFAULT_CANDIDATE_COLUMN_WIDTHS.length,
  ));
  const widthsRef = useRef(widths);

  const updateWidth = (index, width) => {
    const next = [...widthsRef.current];
    next[index] = Math.max(index === 1 ? 220 : 64, Math.round(width));
    widthsRef.current = next;
    setWidths(next);
  };
  const saveWidths = () => {
    try { localStorage.setItem(CANDIDATE_COLUMN_WIDTHS_KEY, JSON.stringify(widthsRef.current)); } catch {}
  };
  const startColumnResize = (index, event) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const header = event.currentTarget.closest("th");
    const startWidth = widthsRef.current[index] ?? header?.getBoundingClientRect().width ?? 100;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = moveEvent => updateWidth(index, startWidth + moveEvent.clientX - startX);
    const onEnd = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onEnd);
      document.removeEventListener("pointercancel", onEnd);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      saveWidths();
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onEnd);
    document.addEventListener("pointercancel", onEnd);
  };
  const resizeColumnWithKeyboard = (index, event) => {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    const header = event.currentTarget.closest("th");
    updateWidth(index, (widthsRef.current[index] ?? header?.getBoundingClientRect().width ?? 100) + direction * 12);
    saveWidths();
  };
  const header = (label, index) => <th>{label}<span
    className="sast-column-resizer"
    role="separator"
    aria-label={`Resize ${label} column`}
    aria-orientation="vertical"
    tabIndex="0"
    onPointerDown={event => startColumnResize(index, event)}
    onKeyDown={event => resizeColumnWithKeyboard(index, event)}
  /></th>;

  if (!leads.length) return <div className="sast-empty-state">No discovery candidates have been persisted yet.</div>;
  return <div className="sast-table-wrap">
    <table className="sast-candidate-table">
      <colgroup>{widths.map((width, index) => <col key={index} style={{ width: width == null ? undefined : `${width}px` }} />)}</colgroup>
      <thead><tr>{header("Severity", 0)}{header("Candidate", 1)}{header("Confidence", 2)}{header("Validation", 3)}</tr></thead>
      <tbody>{leads.map(lead => <tr
        key={lead.id}
        className={selectedId === lead.id ? "selected" : ""}
        onClick={() => onSelect(lead.id)}
        onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(lead.id); } }}
        tabIndex={0}
        role="button"
        aria-pressed={selectedId === lead.id}
      >
        <td><span className={`sast-severity sast-severity-${(lead.severity || "medium").toLowerCase()}`}>{(lead.severity || "medium").toUpperCase()}</span></td>
        <td><span className="sast-candidate-title">{lead.title || "Untitled candidate"}</span><code>{lead.location || "Location not provided"}</code></td>
        <td>{Math.round((lead.confidence || 0) * 100)}%</td>
        <td><span className={`sast-state sast-state-${lead.validation_status || "pending"}`}>{lead.validation_status || "pending"}</span></td>
      </tr>)}</tbody>
    </table>
  </div>;
}

function CandidatesView({ leads, selectedLead, onSelect, targets, onQueue, queueBusy, reportableCount, onExport }) {
  const [ledgerWidth, setLedgerWidth] = useState(() => readStoredValue(
    CANDIDATE_SPLIT_KEY,
    DEFAULT_CANDIDATE_SPLIT,
    value => Number.isFinite(value) && value >= MIN_CANDIDATE_SPLIT && value <= MAX_CANDIDATE_SPLIT,
  ));
  const ledgerWidthRef = useRef(ledgerWidth);
  const layoutRef = useRef(null);

  const updateLedgerWidth = width => {
    const next = clamp(width, MIN_CANDIDATE_SPLIT, MAX_CANDIDATE_SPLIT);
    ledgerWidthRef.current = next;
    setLedgerWidth(next);
  };
  const saveLedgerWidth = () => {
    try { localStorage.setItem(CANDIDATE_SPLIT_KEY, JSON.stringify(ledgerWidthRef.current)); } catch {}
  };
  const startSplitResize = event => {
    event.preventDefault();
    const bounds = layoutRef.current?.getBoundingClientRect();
    if (!bounds?.width) return;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = moveEvent => updateLedgerWidth((moveEvent.clientX - bounds.left) / bounds.width * 100);
    const onEnd = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onEnd);
      document.removeEventListener("pointercancel", onEnd);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      saveLedgerWidth();
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onEnd);
    document.addEventListener("pointercancel", onEnd);
  };
  const resizeSplitWithKeyboard = event => {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    updateLedgerWidth(ledgerWidthRef.current + direction * 2);
    saveLedgerWidth();
  };

  return <div className="sast-candidates-layout" ref={layoutRef} style={{ "--sast-ledger-width": `${ledgerWidth}%` }}>
    <section className="sast-panel sast-candidate-ledger"><div className="sast-panel-header"><div><div className="sast-panel-title">Candidate ledger</div><div className="sast-panel-sub">Discovery hypotheses with independent validation outcomes</div></div><div className="row"><span className="sast-state sast-state-open">{reportableCount} reportable</span><button className="btn ghost sm" disabled={!leads.length} onClick={onExport}>Export report ↓</button></div></div><CandidateTable leads={leads} selectedId={selectedLead?.id} onSelect={onSelect} /></section>
    <div className="sast-layout-resizer" role="separator" aria-label="Resize candidate ledger and evidence chain" aria-orientation="vertical" aria-valuemin={MIN_CANDIDATE_SPLIT} aria-valuemax={MAX_CANDIDATE_SPLIT} aria-valuenow={Math.round(ledgerWidth)} tabIndex="0" onPointerDown={startSplitResize} onKeyDown={resizeSplitWithKeyboard}><span aria-hidden="true" /></div>
    <LeadEvidence lead={selectedLead} targets={targets} onQueue={onQueue} queueBusy={queueBusy} />
  </div>;
}

function LeadEvidence({ lead, targets, onQueue, queueBusy }) {
  const [targetKey, setTargetKey] = useState("");
  useEffect(() => { setTargetKey(""); }, [lead?.id]);
  if (!lead) return <aside className="sast-evidence-panel"><div className="sast-panel-empty">Select a candidate to inspect its evidence chain.</div></aside>;
  const selectedTarget = targets.find(target => `${target.run_type}:${target.run_id}` === targetKey);
  return <aside className="sast-evidence-panel">
    <div className="sast-panel-header"><div><div className="sast-panel-title">Evidence chain</div><div className="sast-panel-sub"><LeadReferenceLink reference={lead.reference || `#${lead.id}`} title={lead.title} description={lead.description} severity={lead.severity} /> · {lead.fingerprint?.slice(0, 10) || "unfingerprinted"}</div></div><span className={`sast-state sast-state-${lead.validation_status || "pending"}`}>{lead.validation_status || "pending"}</span></div>
    <div className="sast-evidence-body">
      <SastLeadDetails lead={lead} showSummary={false} />
      <div className="sast-handoff-box">
        <strong>Dynamic confirmation</strong>
        <span>{lead.reportable ? "Send this validated lead to a web or API run for live reproduction." : "Only independently confirmed, reportable leads can be handed off."}</span>
        <select aria-label="Dynamic target run" value={targetKey} disabled={!lead.reportable || queueBusy} onChange={event => setTargetKey(event.target.value)}>
          <option value="">Select target run…</option>
          {targets.map(target => <option key={`${target.run_type}:${target.run_id}`} value={`${target.run_type}:${target.run_id}`}>{target.run_type.toUpperCase()} · {target.target} · {target.name}</option>)}
        </select>
        <button className="btn sm" disabled={!lead.reportable || !selectedTarget || queueBusy} onClick={() => onQueue(lead, selectedTarget)}>{queueBusy ? "Queuing…" : "Queue live test"}</button>
      </div>
    </div>
  </aside>;
}

function CoverageView({ coverage, workProgram }) {
  const summary = coverage?.summary || {};
  const files = coverage?.files || [];
  const total = workProgram?.files?.total ?? summary.files_total ?? 0;
  const directlyOpened = workProgram?.files?.directly_opened ?? summary.files_reviewed ?? 0;
  const percent = total ? Math.round(directlyOpened / total * 100) : 0;
  const languages = Object.entries(summary.languages || {}).sort((a, b) => b[1].total - a[1].total);
  return <div className="sast-coverage-layout">
    <section className="sast-panel">
      <div className="sast-panel-header"><div><div className="sast-panel-title">Direct file reads</div><div className="sast-panel-sub">A search across a directory does not count as opening every file</div></div><span className="sast-state sast-state-confirmed">{directlyOpened} / {total} opened</span></div>
      <div className="sast-coverage-grid">
        <div className="sast-coverage-row"><div className="sast-coverage-name">All files</div><div className="sast-coverage-bar"><span style={{ width: `${percent}%` }} /></div><div className="sast-coverage-count">{percent}%</div></div>
        {languages.map(([language, counts]) => { const languagePercent = counts.total ? Math.round(counts.reviewed / counts.total * 100) : 0; return <div className="sast-coverage-row" key={language}><div className="sast-coverage-name">{language}</div><div className="sast-coverage-bar"><span style={{ width: `${languagePercent}%` }} /></div><div className="sast-coverage-count">{counts.reviewed}/{counts.total}</div></div>; })}
      </div>
    </section>
    <section className="sast-panel sast-file-receipts">
      <div className="sast-panel-header"><div><div className="sast-panel-title">Direct read receipts</div><div className="sast-panel-sub">{files.length} inventoried files</div></div></div>
      <div className="sast-file-list">{files.slice(0, 250).map(file => <div key={file.path}><span className={`sast-evidence-status status-${file.reviewed ? "complete" : "pending"}`}>{file.reviewed ? "✓" : "·"}</span><code title={file.path}>{file.path}</code><small>{file.language} · {file.read_count} read{file.read_count === 1 ? "" : "s"}</small></div>)}</div>
    </section>
  </div>;
}

function ActivityView({ logs, agentLog, scanRunning, tokenUsage, tokenExpanded, setTokenExpanded, runId }) {
  const [subTab, setSubTab] = useState("log");
  const entries = subTab === "log" ? logs : agentLog;
  return <div className="sast-activity-panel">
    <TokenUsageBar tokenUsage={tokenUsage} tokenExpanded={tokenExpanded} setTokenExpanded={setTokenExpanded} />
    <div className="sast-activity-toolbar"><div className="sast-activity-tabs"><button className={subTab === "log" ? "active" : ""} onClick={() => setSubTab("log")}>Phase log</button><button className={subTab === "agents" ? "active" : ""} onClick={() => setSubTab("agents")}>Agent activity</button></div><span className="subtle">{entries.length} entries</span>{scanRunning && <span className="activity-mode-badge running">● Scanning</span>}<a className="btn ghost sm" href={`/api/sast-runs/${runId}/agent-log/export`} download>Export ↓</a></div>
    {!entries.length ? <div className="sast-empty-state">No activity has been recorded yet.</div> : <div className="sast-activity-feed">{entries.map(item => <div className="sast-activity-entry" key={item.id}><time>{formatTime(item.created_at)}</time><span className="sast-activity-phase">{subTab === "log" ? (item.phase || "event") : (item.status || "event")}</span><span className="sast-activity-message">{subTab === "log" ? item.message : `${item.role || "Agent"}: ${item.current_task || ""}${item.outcome ? ` → ${item.outcome}` : ""}`}</span></div>)}</div>}
  </div>;
}

export function SastRunDetailExperience({ runId, initialTab, initialLeadRef }) {
  const [run, setRun] = useState(null);
  const [analysis, setAnalysis] = useState({ phases: {}, coverage: { files: [], summary: {} }, work_program: {}, assurance: {}, report: {} });
  const [logs, setLogs] = useState([]);
  const [agentLog, setAgentLog] = useState([]);
  const [leads, setLeads] = useState([]);
  const [targets, setTargets] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [tokenUsage, setTokenUsage] = useState(null);
  const [tab, setTab] = useState(normaliseTab(initialTab));
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
      const [runData, status, analysisData, logData, agentData, leadData, usage, targetData] = await Promise.all([
        api.getSastRun(runId), api.getSastScanStatus(runId), api.getSastAnalysis(runId), api.getSastScanLog(runId), api.getSastAgentLog(runId), api.getSastLeads(runId), api.getSastTokenUsage(runId), api.getSastHandoffTargets(runId),
      ]);
      setRun(runData); setScanRunning(status.running); setAnalysis(analysisData); setLogs(logData || []); setAgentLog(agentData || []); setLeads(leadData || []); setTokenUsage(usage); setTargets(targetData || []);
      setSelectedLeadId(previous => previous ?? leadData?.find(lead => lead.reference === initialLeadRef)?.id ?? leadData?.[0]?.id ?? null);
    } catch (err) { setError(err.message); }
  }, [runId, initialLeadRef]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { api.listLLMProfiles().then(items => setProfiles(items || [])).catch(err => setError(err.message)); }, []);
  useEffect(() => { const timer = setInterval(loadData, scanRunning ? 3000 : 8000); return () => clearInterval(timer); }, [loadData, scanRunning]);
  useEffect(() => { const es = new EventSource(`/api/sast-runs/${runId}/events`); es.onmessage = event => { try { const payload = JSON.parse(event.data); if (payload.type === "token_usage_update") setTokenUsage(payload.totals); if (payload.type === "scanner_phase" || payload.type === "agent_status") loadData(); } catch {} }; return () => es.close(); }, [runId, loadData]);
  useEffect(() => { if (tab === "activity" && scanRunning) bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [logs.length, tab, scanRunning]);

  const statuses = useMemo(() => Object.fromEntries(PHASES.map(phase => [phase.key, analysis.phases?.[phase.key]?.status || "pending"])), [analysis.phases]);
  const currentPhase = PHASES.find(phase => statuses[phase.key] === "running")?.key || PHASES.find(phase => statuses[phase.key] === "pending")?.key || "report";
  const displayedPhase = activePhase || currentPhase;
  const selectedLead = useMemo(() => leads.find(lead => lead.id === selectedLeadId) || leads[0] || null, [leads, selectedLeadId]);
  const reportableCount = leads.filter(lead => lead.reportable).length;
  const proofGapCount = leads.reduce((count, lead) => count + jsonValue(lead.proof_gaps_json, []).length, 0);
  const workItemSummary = analysis.work_program?.work_items || {};
  const workerSummary = analysis.work_program?.workers || {};
  const fileSummary = analysis.work_program?.files || {};
  const failedWorkers = (workerSummary.failed || 0) + (workerSummary.blocked || 0);
  const unfinishedWorkers = Math.max((workerSummary.total || 0) - (workerSummary.complete || 0) - failedWorkers, 0);
  const goTab = nextTab => { setTab(nextTab); nav(`#/sast-runs/${runId}/${nextTab}`); };
  const onStart = async () => { setStartBusy(true); setError(null); try { await api.startSastScan(runId); setActivePhase(null); setScanRunning(true); await loadData(); } catch (err) { setError(err.message); } finally { setStartBusy(false); } };
  const onPause = async () => { setStartBusy(true); setError(null); try { await api.pauseSastScan(runId); await loadData(); } catch (err) { setError(err.message); } finally { setStartBusy(false); } };
  const onStop = async () => { try { await api.stopSastScan(runId); await loadData(); } catch (err) { setError(err.message); } };
  const onResume = async () => { setStartBusy(true); setError(null); try { await api.resumeSastScan(runId); setScanRunning(true); await loadData(); } catch (err) { setError(err.message); } finally { setStartBusy(false); } };
  const onDelete = async () => { if (!confirm("Delete this SAST run and all its leads?")) return; try { const collId = run?.collection_id; await api.deleteSastRun(runId); nav(collId ? `#/apis/${collId}/files` : "#/sast-runs"); } catch (err) { setError(err.message); } };
  const onQueue = async (lead, target) => { setQueueBusy(true); setError(null); setNotice(null); try { const result = await api.handoffSastLead(runId, lead.id, { run_type: target.run_type, run_id: target.run_id }); setNotice(`Lead ${lead.reference || `#${lead.id}`} queued as ${result.lead_reference || `#${result.lead_id}`} in ${target.run_type.toUpperCase()} run #${target.run_id}.`); } catch (err) { setError(err.message); } finally { setQueueBusy(false); } };
  const onExportReport = () => downloadTextFile(sastReportFilename(run?.name, runId), sastCandidatesToMarkdown(leads, { runName: run?.name, generatedAt: new Date() }), "text/markdown;charset=utf-8");
  const onProfileChange = async llmProfileId => { setProfileBusy(true); setError(null); setNotice(null); try { const updated = await api.updateSastRun(runId, { llm_profile_id: llmProfileId }); setRun(updated); const selected = profiles.find(profile => profile.id === llmProfileId); setNotice(llmProfileId ? `Model profile changed to ${profileLabel(selected)}. It will be used by the next scan.` : "This run now follows the globally active model profile for its next scan."); } catch (err) { setError(err.message); } finally { setProfileBusy(false); } };
  const canStart = run && !scanRunning && ["pending", "completed", "failed", "cancelled"].includes(run.status);

  if (!run) return <div className="content scroll-content">{error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}</div>;
  const phaseEntry = analysis.phases?.[displayedPhase] || {};
  return <>
    <PageHeader className="sast-run-topbar" title={<span className="sast-header-title"><Crumb href="#/sast-runs">SAST</Crumb><Sep /><span className="sast-header-name">{run.name}</span><StatusBadge status={scanRunning ? "scanning" : run.status} /></span>} actions={<><SastModelSelector run={run} profiles={profiles} disabled={scanRunning} saving={profileBusy} onChange={onProfileChange} />{canStart && <button className="btn" disabled={startBusy} onClick={onStart}>{startBusy ? "Starting…" : "Start SAST Scan"}</button>}{run.status === "paused" && <button className="btn" disabled={startBusy} onClick={onResume}>{startBusy ? "Resuming…" : "Resume SAST Scan"}</button>}{scanRunning && <button className="btn secondary" disabled={startBusy} onClick={onPause}>{startBusy ? "Pausing…" : "Pause"}</button>}{scanRunning && <button className="btn danger-outline" onClick={onStop}>Stop</button>}<SastRunActionsMenu runId={runId} onDelete={onDelete} /></>} />
    <div className="sast-run-shell">
      <div className="sast-phase-rail" role="tablist" aria-label="SAST scan phases">{PHASES.map((phase, index) => <button key={phase.key} className={`sast-phase-step ${displayedPhase === phase.key ? "active" : ""} status-${statuses[phase.key]}`} onClick={() => { setActivePhase(phase.key); goTab(phase.view); }} role="tab" aria-selected={displayedPhase === phase.key}>{statuses[phase.key] === "running" ? <span className="agent-dot agent-dot--active sast-phase-running-dot" aria-label="running" /> : <span className="sast-phase-marker">{phaseIcon(statuses[phase.key]) || index + 1}</span>}<span className="sast-phase-label">{phase.label}</span><span className="sast-phase-meta">{statuses[phase.key] === "pending" ? phase.short : statuses[phase.key]}</span></button>)}</div>
      <div className="sast-view-tabs" role="tablist" aria-label="SAST run views">{[{ key: "coverage", label: "Coverage" }, { key: "candidates", label: `Candidates ${leads.length}` }, { key: "activity", label: "Activity" }].map(item => <button key={item.key} className={tab === item.key ? "active" : ""} onClick={() => goTab(item.key)} role="tab" aria-selected={tab === item.key}>{item.label}</button>)}</div>
      <div className="sast-run-content">
        {error && <div className="alert error">{error}</div>}{notice && <div className="alert info sast-inline-notice">{notice}</div>}
        <div className="sast-phase-banner"><div><strong>{PHASES.find(item => item.key === displayedPhase)?.label}</strong><span>{phaseEntry.message || "This phase has not started."}</span></div><span className="sast-phase-banner-status">{statuses[displayedPhase]}</span></div>
        <div className="sast-summary-grid sast-run-summary-grid"><div><span>Security checks</span><strong>{workItemSummary.resolved || 0}/{workItemSummary.total || 0}</strong><small>{workItemSummary.unresolved || 0} remaining</small></div><div><span>Analysis batches</span><strong>{workerSummary.complete || 0}/{workerSummary.total || 0}</strong><small>{unfinishedWorkers} unfinished{failedWorkers ? ` · ${failedWorkers} failed` : ""}</small></div><div><span>Direct file reads</span><strong>{fileSummary.directly_opened || 0}/{fileSummary.total || 0}</strong><small>grep excluded</small></div><div><span>Search matches</span><strong>{fileSummary.with_search_matches || 0}</strong><small>files returned</small></div><div><span>Candidates</span><strong>{leads.length}</strong><small>persisted hypotheses</small></div><div><span>Reportable</span><strong>{reportableCount}</strong><small>independently confirmed</small></div><div><span>Proof gaps</span><strong>{proofGapCount}</strong><small>unresolved evidence</small></div></div>
        {tab === "candidates" && <CandidatesView leads={leads} selectedLead={selectedLead} onSelect={setSelectedLeadId} targets={targets} onQueue={onQueue} queueBusy={queueBusy} reportableCount={reportableCount} onExport={onExportReport} />}
        {tab === "coverage" && <div className="sast-assurance-note"><span><strong>Coverage assurance:</strong> {analysis.assurance?.reasons?.length ? analysis.assurance.reasons.join(" ") : "Every generated source and sink obligation was closed."}</span><span className={`sast-state sast-state-${analysis.assurance?.status === "full" ? "confirmed" : "inconclusive"}`}>{analysis.assurance?.status || "pending"}</span></div>}
        {tab === "coverage" && <CoverageView coverage={analysis.coverage} workProgram={analysis.work_program} />}
        {tab === "activity" && <ActivityView logs={logs} agentLog={agentLog} scanRunning={scanRunning} tokenUsage={tokenUsage} tokenExpanded={tokenExpanded} setTokenExpanded={setTokenExpanded} runId={runId} />}
        <div ref={bottomRef} />
      </div>
    </div>
  </>;
}
