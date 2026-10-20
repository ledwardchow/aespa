import { FindingsMoreMenu } from "../../shared/findings/FindingsMoreMenu.tsx";
import { FindingsList } from "../../shared/findings/FindingsList.tsx";
import {
  CoverageFindingsFilter,
  filterCoverageFindings,
} from "../../shared/findings/CoverageFindingsFilter.jsx";
import { useState } from "react";
import { useFindings } from "./useFindings.js";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { isDynamicScanActive } from "../../shared/runs/presentation.jsx";
import { Notice } from "../../shared/ui/Notice.jsx";
import { runHref } from "../../shared/navigation/links.ts";

export function WebRunFindingsTab({
  runId,
  activeTab,
  run,
  siteName,
  initialFindingRef,
  findingIds,
  coverageReturn,
  thinkingStatus,
  thinkingStopRequested,
  aliceIsThinking,
  submitAliceDirective,
  onRunChange,
  onGraphChange,
  onError,
}) {
  const [clearBusy, setClearBusy] = useState("");
  const setClearError = onError;
  const {
    validateStatus,
    onStopValidation,
    dedupeBusy,
    findings,
    onExportFindingsMarkdown,
    onImportFindingsFile,
    importMessage,
    clearImportMessage,
    validateBusy,
    onValidateAll,
    onDeduplicateFindings,
    setFindings,
    editor,
    collapseToken,
    onValidateFinding,
    onDeleteFinding,
    onDeleteFindingGroup,
  } = useFindings(runId, activeTab, {
    run,
    siteName,
    aliceIsThinking,
    submitAliceDirective,
    setRun: onRunChange,
    setGraph: onGraphChange,
    setError: onError,
  });
  const visibleFindings = filterCoverageFindings(findings, findingIds);
  const onClearFindings = async () => {
    if (
      !confirm(
        "Clear all findings and reset page scan status?\nThis lets you re-run the scanner on the same crawl.",
      )
    )
      return;
    setClearBusy("findings");
    setClearError(null);
    try {
      await webRunsApi.clearFindings(runId);
      setFindings([]);
    } catch (e) {
      setClearError(e.message);
    } finally {
      setClearBusy("");
    }
  };
  return (
    <>
      {importMessage && (
        <Notice variant="success" onDismiss={clearImportMessage}>
          {importMessage}
        </Notice>
      )}
      <div className="findings-panel">
        <div className="findings-status-bar">
          <div className="findings-status-summary">
            {thinkingStatus && thinkingStatus.status && thinkingStatus.status !== "idle" && (
              <span
                className={
                  "scan-status-badge scan-status-" +
                  (thinkingStopRequested ? "stopping" : thinkingStatus.status)
                }
              >
                {thinkingStopRequested
                  ? "Stopping Dynamic Scan…"
                  : thinkingStatus.run_outcome === "incomplete"
                    ? "Validation incomplete — resume available"
                    : thinkingStatus.status === "running"
                      ? "Dynamic Scan running…"
                      : thinkingStatus.status === "analysing" ||
                          thinkingStatus.status === "analyzing"
                        ? "Dynamic Scan analysing…"
                        : thinkingStatus.status === "stopping"
                          ? "Dynamic Scan stopping…"
                          : thinkingStatus.status === "complete"
                            ? "Dynamic Scan complete"
                            : thinkingStatus.status === "stopped"
                              ? "Dynamic Scan stopped"
                              : thinkingStatus.status === "failed"
                                ? "Dynamic Scan failed"
                                : "Dynamic Scan"}
              </span>
            )}
            {validateStatus?.status === "running" ? (
              <span className="val-status-badge val-running">
                Validating…{" "}
                {validateStatus.confirmed +
                  validateStatus.false_positives +
                  (validateStatus.unconfirmed || 0)}
                /{validateStatus.total}
              </span>
            ) : validateStatus?.status === "stopped" ? (
              <span className="val-status-badge val-fp">Validation stopped</span>
            ) : validateStatus?.status === "complete" ? (
              <span className="val-status-badge val-complete">
                {validateStatus.confirmed} confirmed · {validateStatus.unconfirmed || 0} unconfirmed
                · {validateStatus.false_positives} low confidence
              </span>
            ) : null}
            {validateStatus?.status === "running" && (
              <button className="btn danger-outline sm" onClick={onStopValidation}>
                Stop validation
              </button>
            )}
            {dedupeBusy && (
              <span className="val-status-badge val-running dedupe-status">
                <span className="inline-spinner"></span>
                A.L.I.C.E. is reviewing findings…
              </span>
            )}
          </div>
          {!findingIds?.length && (
            <div className="findings-actions">
              {findings.length > 0 && (
                <button
                  className="btn sm"
                  disabled={validateBusy || validateStatus?.status === "running"}
                  onClick={onValidateAll}
                >
                  Validate findings
                </button>
              )}
              {findings.length > 0 && (
                <button
                  className="btn secondary sm"
                  disabled={
                    dedupeBusy ||
                    validateBusy ||
                    aliceIsThinking ||
                    validateStatus?.status === "running"
                  }
                  onClick={onDeduplicateFindings}
                >
                  {dedupeBusy && <span className="inline-spinner"></span>}
                  {dedupeBusy ? "Reviewing…" : "Review with AI"}
                </button>
              )}
              <FindingsMoreMenu
                hasFindings={findings.length > 0}
                onExport={onExportFindingsMarkdown}
                onImport={onImportFindingsFile}
                clearBusy={clearBusy === "findings"}
                onClear={onClearFindings}
              />
            </div>
          )}
        </div>
        <CoverageFindingsFilter
          runKind="web"
          runId={runId}
          findingIds={findingIds}
          coverageReturn={coverageReturn}
          visibleCount={visibleFindings.length}
        />
        <FindingsList
          findings={visibleFindings}
          runKind="web"
          findingHref={(reference) =>
            runHref({ runKind: "web", runId }, "findings", {
              finding: reference,
              finding_ids: findingIds?.join(","),
              from: findingIds?.length
                ? coverageReturn === "workflows"
                  ? "workflows"
                  : "coverage"
                : undefined,
            })
          }
          editor={editor}
          emptyMessage={
            findingIds?.length
              ? "No matching findings remain for this coverage cell."
              : isDynamicScanActive(thinkingStatus?.status)
                ? "Scan running… findings will appear here."
                : "No findings yet. Start a scan to begin."
          }
          initialFindingRef={initialFindingRef}
          collapseToken={collapseToken}
          onDeleteFinding={onDeleteFinding}
          onDeleteGroup={findingIds?.length ? undefined : onDeleteFindingGroup}
          onValidateFinding={onValidateFinding}
        />
      </div>
    </>
  );
}
