import { IconPlay, IconStop } from "../../components/Icons";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";

const STATUS_COLOR = { neutral: "var(--muted)", pending: "var(--muted)", running: "var(--warn)", stopping: "var(--warn)", partial: "var(--text-2)", ok: "var(--ok)", danger: "var(--danger)" };

export function WebRunHeader({ run, siteName, profiles, headerStatus, canStart, canStop, canStartScan, canStopScan, canResume, canImportCrawl, crawlStopping, scanStopping, coverageMode, onCoverageMode, onStart, onStop, onStartScan, onStopScan, onResume, onExportCrawl, onImportCrawl, aliceRunning, onStopAlice }) {
  const profile = profiles.find(item => item.id === run?.llm_profile_id);
  return <PageHeader titleStyle={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }} title={<>
    <div className="row" style={{ alignItems: "center", gap: 0 }}><Crumb href={run ? `#/sites/${run.site_id}` : "#/"}>{siteName || "Site"}</Crumb><Sep />{run ? run.name : "…"}{run && <span className={'run-status-badge' + (["running", "stopping"].includes(headerStatus.key) ? " running" : "")} style={{ color: STATUS_COLOR[headerStatus.key] || "var(--muted)" }}>● {headerStatus.label}</span>}</div>
    {run?.llm_profile_id && profiles.length > 0 && <div style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)" }}>Profile: {profile?.name || '#' + run.llm_profile_id}</div>}
  </>} actions={<>
    {canStart && <button className="btn sm" onClick={onStart}><IconPlay /> Start crawl</button>}
    {run?.pages_discovered > 0 && !crawlStopping && <button className="btn secondary sm" onClick={onExportCrawl}>Export crawl</button>}
    {canImportCrawl && <button className="btn secondary sm" onClick={onImportCrawl}>Import crawl</button>}
    {!scanStopping && canStartScan && <><label className="subtle" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }} title="Track: observe coverage as the scan runs. Enforce: drive every applicable page × category to covered or skipped-with-reason.">Coverage:<select value={coverageMode} onChange={event => onCoverageMode(event.target.value)}><option value="track">Track</option><option value="enforce">Enforce</option></select></label><button className="btn sm" title="Run the adaptive Pentest" onClick={onStartScan}><IconPlay /> Start Pentest</button></>}
    {canResume && <button className="btn sm" style={{ background: "var(--warn)", color: "#000", borderColor: "var(--warn)" }} onClick={onResume}><IconPlay /> Resume Pentest</button>}
    {canStop && <button className="btn danger-outline" onClick={onStop}><IconStop /> Stop crawl</button>}
    {crawlStopping && <button className="btn danger-outline" disabled><IconStop /> Stopping…</button>}
    {!canStop && !crawlStopping && canStopScan && <button className="btn danger-outline" onClick={onStopScan} disabled={scanStopping}><IconStop /> {scanStopping ? "Stopping…" : "Stop Dynamic Scan"}</button>}
    {aliceRunning && <button className="btn danger-outline" style={{ borderColor: "var(--danger)", color: "var(--danger)", background: "rgba(239,68,68,.08)" }} onClick={onStopAlice}><IconStop /> Stop A.L.I.C.E.</button>}
  </>} />;
}
