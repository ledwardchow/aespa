import { useEffect, useRef, useState } from "react";
import { IconChevronDown, IconPlay, IconStop } from "../../components/Icons";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { resolveRunPrimaryAction, RUN_PRIMARY_ACTION } from "./runState";

const RUN_ACTION_DETAILS = {
  [RUN_PRIMARY_ACTION.START_CRAWL]: { label: "Start Crawl", className: "run-start-action" },
  [RUN_PRIMARY_ACTION.START_PENTEST]: { label: "Start Pentest", className: "run-start-action" },
  [RUN_PRIMARY_ACTION.RESUME_PENTEST]: { label: "Resume Pentest", className: "run-resume-action" },
};

function RunStartControl({ primaryAction, canStartCrawl, canStartPentest, canResumePentest, canExportCrawl, onStartCrawl, onStartPentest, onResumePentest, onExportCrawl }) {
  const [open, setOpen] = useState(false);
  const controlRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = event => {
      if (!controlRef.current?.contains(event.target)) setOpen(false);
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

  const handlers = {
    [RUN_PRIMARY_ACTION.START_CRAWL]: onStartCrawl,
    [RUN_PRIMARY_ACTION.START_PENTEST]: onStartPentest,
    [RUN_PRIMARY_ACTION.RESUME_PENTEST]: onResumePentest,
  };
  const menuActions = [
    canStartPentest && primaryAction !== RUN_PRIMARY_ACTION.START_PENTEST && RUN_PRIMARY_ACTION.START_PENTEST,
    canResumePentest && primaryAction !== RUN_PRIMARY_ACTION.RESUME_PENTEST && RUN_PRIMARY_ACTION.RESUME_PENTEST,
    canStartCrawl && primaryAction !== RUN_PRIMARY_ACTION.START_CRAWL && RUN_PRIMARY_ACTION.START_CRAWL,
  ].filter(Boolean);
  const primary = RUN_ACTION_DETAILS[primaryAction];
  const hasMenu = menuActions.length > 0 || canExportCrawl;

  const runAction = action => {
    setOpen(false);
    handlers[action]?.();
  };

  return <div className={`run-start-control${hasMenu ? "" : " run-start-control-single"}`} ref={controlRef}>
    <button className={`btn sm run-start-primary ${primary.className}`} onClick={() => runAction(primaryAction)}><IconPlay /> {primary.label}</button>
    {hasMenu && <button
      className={`btn sm run-start-toggle ${primary.className}`}
      aria-label="More crawl and Pentest options"
      aria-haspopup="menu"
      aria-expanded={open}
      onClick={() => setOpen(value => !value)}
    ><IconChevronDown /></button>}
    {hasMenu && open && <div className="run-start-menu" role="menu">
      {menuActions.map(action => <button key={action} className={RUN_ACTION_DETAILS[action].className} role="menuitem" onClick={() => runAction(action)}><IconPlay /> {RUN_ACTION_DETAILS[action].label}</button>)}
      {canExportCrawl && <button className="run-export-action" role="menuitem" onClick={() => { setOpen(false); onExportCrawl(); }}>Export Crawl</button>}
    </div>}
  </div>;
}

export function WebRunHeader({ run, siteName, profiles, crawlerActive, testLeadActive, canStart, canStop, canStartScan, canStopScan, canResume, canImportCrawl, crawlStopping, scanStopping, coverageMode, onCoverageMode, onStart, onStop, onStartScan, onStopScan, onResume, onExportCrawl, onImportCrawl, aliceRunning, onStopAlice }) {
  const profile = profiles.find(item => item.id === run?.llm_profile_id);
  const hasCrawlResult = (run?.pages_discovered || 0) > 0;
  const canStartPentest = !scanStopping && canStartScan;
  const primaryAction = resolveRunPrimaryAction({ hasCrawlResult, canStartCrawl: canStart, canStartPentest, canResumePentest: canResume });
  return <PageHeader className="web-run-topbar" titleStyle={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }} title={<>
    <div className="row" style={{ alignItems: "center", gap: 0 }}>
      <Crumb href={run ? `#/sites/${run.site_id}` : "#/"}>{siteName || "Site"}</Crumb>
      <Sep />{run ? run.name : "…"}
      {run && (
        <span className="run-agent-badges">
          <span className={`badge ${crawlerActive ? "ok" : "neutral"}`} title={`Crawler agent is ${crawlerActive ? "active" : "inactive"}`}>
            Crawler {crawlerActive ? "active" : "inactive"}
          </span>
          <span className={`badge ${testLeadActive ? "ok" : "neutral"}`} title={`Test Lead agent is ${testLeadActive ? "active" : "inactive"}`}>
            Test Lead {testLeadActive ? "active" : "inactive"}
          </span>
          <span className={`badge ${aliceRunning ? "ok" : "neutral"}`} title={`ALICE agent is ${aliceRunning ? "active" : "inactive"}`}>
            ALICE {aliceRunning ? "active" : "inactive"}
          </span>
        </span>
      )}
    </div>
    {run?.llm_profile_id && profiles.length > 0 && <div style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)" }}>Profile: {profile?.name || '#' + run.llm_profile_id}</div>}
  </>} actions={<>
    {canImportCrawl && <button className="btn secondary sm" onClick={onImportCrawl}>Import crawl</button>}
    {canStartPentest && <label className="subtle" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }} title="Quick: adaptive scan with coverage tracking. Full: test every applicable page × category obligation. SAST Validate: validate only imported SAST leads.">Scan mode:<select value={coverageMode} onChange={event => onCoverageMode(event.target.value)}><option value="track">Quick</option><option value="enforce">Full</option><option value="sast_validate">SAST Validate</option></select></label>}
    {primaryAction && <RunStartControl primaryAction={primaryAction} canStartCrawl={canStart} canStartPentest={canStartPentest} canResumePentest={canResume} canExportCrawl={hasCrawlResult && !crawlStopping} onStartCrawl={onStart} onStartPentest={onStartScan} onResumePentest={onResume} onExportCrawl={onExportCrawl} />}
    {canStop && <button className="btn danger-outline" onClick={onStop}><IconStop /> Stop crawl</button>}
    {crawlStopping && <button className="btn danger-outline" disabled><IconStop /> Stopping…</button>}
    {!canStop && !crawlStopping && canStopScan && <button className="btn danger-outline" onClick={onStopScan} disabled={scanStopping}><IconStop /> {scanStopping ? "Stopping…" : "Stop Dynamic Scan"}</button>}
    {aliceRunning && <button className="btn danger-outline" style={{ borderColor: "var(--danger)", color: "var(--danger)", background: "rgba(239,68,68,.08)" }} onClick={onStopAlice}><IconStop /> Stop A.L.I.C.E.</button>}
  </>} />;
}
