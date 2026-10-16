import { useEffect, useRef, useState } from "react";
import { WorkflowInputPill } from "./WorkflowInputDrawer.jsx";
import { IconChevronDown, IconPlay, IconStop } from "../../shared/ui/Icons.jsx";
import { PageHeader, Breadcrumbs } from "../../shared/ui/PageHeader.jsx";
import { resolveRunPrimaryAction, RUN_PRIMARY_ACTION } from "./runState.js";
import { LoadSavedCrawlButton, SaveCrawlButton } from "./SavedCrawlControls.jsx";

const RUN_ACTION_DETAILS = {
  [RUN_PRIMARY_ACTION.START_CRAWL]: { label: "Start crawl", className: "run-start-action" },
  [RUN_PRIMARY_ACTION.START_CRAWL_THEN_PENTEST]: {
    label: "Start crawl then scan",
    className: "run-start-action",
  },
  [RUN_PRIMARY_ACTION.START_PENTEST]: { label: "Start scan", className: "run-start-action" },
  [RUN_PRIMARY_ACTION.RESUME_PENTEST]: { label: "Resume scan", className: "run-start-action" },
};

function RunStartControl({
  primaryAction,
  canStartCrawl,
  canStartPentest,
  canResumePentest,
  onStartCrawl,
  onStartCrawlThenPentest,
  onStartPentest,
  onResumePentest,
}) {
  const [open, setOpen] = useState(false);
  const controlRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!controlRef.current?.contains(event.target)) setOpen(false);
    };
    const closeOnEscape = (event) => {
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
    [RUN_PRIMARY_ACTION.START_CRAWL_THEN_PENTEST]: onStartCrawlThenPentest,
    [RUN_PRIMARY_ACTION.START_PENTEST]: onStartPentest,
    [RUN_PRIMARY_ACTION.RESUME_PENTEST]: onResumePentest,
  };
  const menuActions = [
    canStartPentest &&
      primaryAction !== RUN_PRIMARY_ACTION.START_PENTEST &&
      RUN_PRIMARY_ACTION.START_PENTEST,
    canResumePentest &&
      primaryAction !== RUN_PRIMARY_ACTION.RESUME_PENTEST &&
      RUN_PRIMARY_ACTION.RESUME_PENTEST,
    canStartCrawl &&
      primaryAction !== RUN_PRIMARY_ACTION.START_CRAWL &&
      RUN_PRIMARY_ACTION.START_CRAWL,
    canStartCrawl && canStartPentest && RUN_PRIMARY_ACTION.START_CRAWL_THEN_PENTEST,
  ].filter(Boolean);
  const primary = RUN_ACTION_DETAILS[primaryAction];
  const hasMenu = menuActions.length > 0;

  const runAction = (action) => {
    setOpen(false);
    handlers[action]?.();
  };

  return (
    <div
      className={`run-start-control${hasMenu ? "" : " run-start-control-single"}`}
      ref={controlRef}
    >
      <button
        className={`btn sm run-start-primary ${primary.className}`}
        onClick={() => runAction(primaryAction)}
      >
        <IconPlay /> {primary.label}
      </button>
      {hasMenu && (
        <button
          className={`btn sm run-start-toggle ${primary.className}`}
          aria-label="More crawl and scan options"
          aria-haspopup="menu"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <IconChevronDown />
        </button>
      )}
      {hasMenu && open && (
        <div className="run-start-menu" role="menu">
          {menuActions.map((action) => (
            <button
              key={action}
              className={RUN_ACTION_DETAILS[action].className}
              role="menuitem"
              onClick={() => runAction(action)}
            >
              <IconPlay /> {RUN_ACTION_DETAILS[action].label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function WebRunHeader({
  run,
  siteName,
  profiles,
  crawlerActive,
  testLeadActive,
  canStart,
  canStop,
  canStartScan,
  canStopScan,
  canResume,
  canImportCrawl,
  crawlStopping,
  scanStopping,
  coverageMode,
  showDeepScan = false,
  showTeamScan = false,
  onCoverageMode,
  onStart,
  onStartCrawlThenPentest,
  onStop,
  onStartScan,
  onStopScan,
  onResume,
  onImportCrawl,
  onSavedCrawlLoaded,
  onError,
  aliceRunning,
  onStopAlice,
  workflowInputCount = 0,
  workflowInputOpen = false,
  onToggleWorkflowInput,
}) {
  const profile = profiles.find((item) => item.id === run?.llm_profile_id);
  const hasCrawlResult = (run?.pages_discovered || 0) > 0;
  const experimentalMode = ["deep", "team"].includes(run?.coverage_mode) ? run.coverage_mode : null;
  const experimentalModeLocked = run?.scan_mode_locked && experimentalMode;
  const ordinaryModeLocked = run?.scan_mode_locked && !experimentalMode;
  const showDeepOption = showDeepScan || run?.coverage_mode === "deep";
  const showTeamOption = showTeamScan || run?.coverage_mode === "team";
  const runActive = crawlerActive || testLeadActive || aliceRunning;
  const canStartPentest = !scanStopping && canStartScan;
  const primaryAction = resolveRunPrimaryAction({
    hasCrawlResult,
    canStartCrawl: canStart,
    canStartPentest,
    canResumePentest: canResume,
  });
  return (
    <PageHeader
      className="web-run-topbar"
      titleStyle={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }}
      title={
        <>
          <div className="row" style={{ alignItems: "center", gap: 8 }}>
            <Breadcrumbs
              items={[
                { label: "Sites", href: "#/" },
                { label: siteName || "Site", href: run ? `#/sites/${run.site_id}` : "#/" },
                { label: run ? run.name : "…" },
              ]}
            />
            {run && (
              <span className="run-agent-badges">
                <span
                  className={`badge ${runActive ? "ok" : "neutral"}`}
                  title={`Test run is ${runActive ? "active" : "inactive"}`}
                >
                  {runActive ? "Active" : "Inactive"}
                </span>
              </span>
            )}
            <WorkflowInputPill
              count={workflowInputCount}
              open={workflowInputOpen}
              onClick={onToggleWorkflowInput}
            />
          </div>
          {run?.llm_profile_id && profiles.length > 0 && (
            <div style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)" }}>
              Profile: {profile?.name || "#" + run.llm_profile_id}
            </div>
          )}
        </>
      }
      actions={
        <>
          {canImportCrawl && (
            <button className="btn secondary sm" onClick={onImportCrawl}>
              Import crawl
            </button>
          )}
          {canImportCrawl && onSavedCrawlLoaded && (
            <LoadSavedCrawlButton
              siteId={run?.site_id}
              runId={run?.id}
              onLoaded={onSavedCrawlLoaded}
              onError={onError}
            />
          )}
          {hasCrawlResult && !crawlerActive && !crawlStopping && onError && (
            <SaveCrawlButton run={run} onError={onError} />
          )}
          {canStartPentest && (
            <label
              className="subtle"
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}
              title="Quick: adaptive scan with coverage tracking. Standard: require the configured percentage of applicable coverage cells. Full: run every applicable test on every page. Deep: use a persistent tester queue and attack workers. Team: run independent Standard Test Leads followed by a coverage and chain review. SAST Validate: validate only imported SAST leads."
            >
              Scan mode:
              <select
                value={coverageMode}
                onChange={(event) => onCoverageMode(event.target.value)}
                disabled={Boolean(experimentalModeLocked)}
                title={
                  run?.scan_mode_locked
                    ? "This run cannot switch scan engines after its first pentest starts."
                    : undefined
                }
              >
                <option value="track" disabled={Boolean(experimentalModeLocked)}>
                  Quick
                </option>
                <option value="standard" disabled={Boolean(experimentalModeLocked)}>
                  Standard
                </option>
                <option value="enforce" disabled={Boolean(experimentalModeLocked)}>
                  Full
                </option>
                {showDeepOption && (
                  <option value="deep" disabled={ordinaryModeLocked || experimentalMode === "team"}>
                    Deep
                  </option>
                )}
                {showTeamOption && (
                  <option value="team" disabled={ordinaryModeLocked || experimentalMode === "deep"}>
                    Team
                  </option>
                )}
                <option value="sast_validate" disabled={Boolean(experimentalModeLocked)}>
                  SAST Validate
                </option>
              </select>
            </label>
          )}
          {primaryAction && (
            <RunStartControl
              primaryAction={primaryAction}
              canStartCrawl={canStart}
              canStartPentest={canStartPentest}
              canResumePentest={canResume}
              onStartCrawl={onStart}
              onStartCrawlThenPentest={onStartCrawlThenPentest}
              onStartPentest={onStartScan}
              onResumePentest={onResume}
            />
          )}
          {canStop && (
            <button className="btn danger-outline" onClick={onStop}>
              <IconStop /> Stop crawl
            </button>
          )}
          {crawlStopping && (
            <button className="btn danger-outline" disabled>
              <IconStop /> Stopping…
            </button>
          )}
          {!canStop && !crawlStopping && canStopScan && (
            <button className="btn danger-outline" onClick={onStopScan} disabled={scanStopping}>
              <IconStop /> {scanStopping ? "Stopping…" : "Stop scan"}
            </button>
          )}
          {aliceRunning && (
            <button
              className="btn danger-outline"
              style={{
                borderColor: "var(--danger)",
                color: "var(--danger)",
                background: "rgba(239,68,68,.08)",
              }}
              onClick={onStopAlice}
            >
              <IconStop /> Stop A.L.I.C.E.
            </button>
          )}
        </>
      }
    />
  );
}
