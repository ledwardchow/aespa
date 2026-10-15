import { FindingFileControls } from "../../shared/findings/FindingFileControls.tsx";
import { FindingsList } from "../../shared/findings/FindingsList.tsx";
import { useState } from "react";
import { useFindings } from "./useFindings.js";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { isDynamicScanActive } from "../../shared/runs/presentation.jsx";
import { Notice } from "../../shared/ui/Notice.jsx";

export function WebRunFindingsTab({
  runId,
  activeTab,
  run,
  siteName,
  initialFindingRef,
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
          <div className="findings-actions">
            <FindingFileControls
              hasFindings={findings.length > 0}
              onExport={onExportFindingsMarkdown}
              onImport={onImportFindingsFile}
            />
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
            {findings.length > 0 && (
              <button
                className="btn danger-outline sm"
                disabled={clearBusy === "findings"}
                onClick={async () => {
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
                }}
              >
                {clearBusy === "findings" ? "Clearing…" : "Clear all"}
              </button>
            )}
          </div>
        </div>
        <FindingsList
          findings={findings}
          runKind="web"
          findingHref={(reference) =>
            `#/runs/${runId}/findings?finding=${encodeURIComponent(reference)}`
          }
          editor={editor}
          emptyMessage={
            isDynamicScanActive(thinkingStatus?.status)
              ? "Scan running… findings will appear here."
              : "No findings yet. Start a Dynamic Scan to begin."
          }
          initialFindingRef={initialFindingRef}
          collapseToken={collapseToken}
          onDeleteFinding={onDeleteFinding}
          onDeleteGroup={onDeleteFindingGroup}
          onValidateFinding={onValidateFinding}
        />
      </div>
    </>
  );
}
