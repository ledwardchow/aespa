import { useFindingEditor } from "../../shared/findings/useFindingEditor.ts";
import { useFindingsData } from "./FindingsData.jsx";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { useState, useEffect } from "react";

import { ALICE_DEDUP_DIRECTIVE } from "../../shared/findings/reviewDirective.js";
import {
  findingsToMarkdown,
  markdownExportFilename,
  parseFindingsMarkdown,
} from "../../shared/findings/files.js";
import { downloadTextFile } from "../../shared/lib/download.js";

// Panel interactions and refreshes share server data with the route event subscription.
export function useFindings(
  runId,
  activeTab,
  { run, siteName, submitAliceDirective, aliceIsThinking, setRun, setGraph, setError },
) {
  const {
    findings,
    setFindings,
    validateStatus,
    setValidateStatus,
    validateBusy,
    setValidateBusy,
  } = useFindingsData();
  const [dedupeBusy, setDedupeBusy] = useState(false);
  const [importMessage, setImportMessage] = useState(null);
  const [collapseToken, setCollapseToken] = useState(0);

  // Poll findings when on findings tab.
  useEffect(() => {
    if (activeTab !== "findings") return;
    webRunsApi
      .getFindings(runId)
      .then(setFindings)
      .catch(() => {});
    const iv = setInterval(() => {
      webRunsApi
        .getFindings(runId)
        .then(setFindings)
        .catch(() => {});
    }, 4000);
    return () => clearInterval(iv);
  }, [runId, activeTab, setFindings]);

  // Poll validation status while validating is running. Keep polling while the
  // local busy flag is true too, because the final SSE event can race with the
  // backend task registry; the next status read is the authoritative state.
  useEffect(() => {
    if (!validateBusy && validateStatus?.status !== "running" && activeTab !== "findings") return;
    const iv = setInterval(() => {
      webRunsApi
        .getValidateStatus(runId)
        .then((vs) => {
          setValidateStatus(vs);
          if (vs.status !== "running") setValidateBusy(false);
          if (vs.status !== "running")
            webRunsApi
              .getFindings(runId)
              .then(setFindings)
              .catch(() => {});
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, [
    runId,
    validateBusy,
    validateStatus?.status,
    activeTab,
    setFindings,
    setValidateStatus,
    setValidateBusy,
  ]);

  // Fetch findings when switching to findings tab
  useEffect(() => {
    if (activeTab !== "findings") return;
    webRunsApi
      .getFindings(runId)
      .then(setFindings)
      .catch(() => {});
    webRunsApi
      .getValidateStatus(runId)
      .then(setValidateStatus)
      .catch(() => {});
  }, [activeTab, runId, setFindings, setValidateStatus]);

  const onDeleteFinding = async (findingId) => {
    try {
      await webRunsApi.deleteFinding(runId, findingId);
      setFindings((prev) => prev.filter((f) => f.id !== findingId));
    } catch (err) {
      setError(err.message);
    }
  };
  const onDeleteFindingGroup = async (title) => {
    if (!confirm(`Delete all instances of "${title}"?`)) return false;
    try {
      await webRunsApi.deleteFindingGroup(runId, title);
      setFindings((prev) => prev.filter((f) => f.title !== title));
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  };
  const onValidateAll = async () => {
    if (validateBusy) return;
    setValidateBusy(true);
    try {
      const vs = await webRunsApi.validateAllFindings(runId);
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
        webRunsApi
          .getFindings(runId)
          .then(setFindings)
          .catch(() => {});
        webRunsApi
          .getValidateStatus(runId)
          .then(setValidateStatus)
          .catch(() => {});
        setCollapseToken((token) => token + 1);
        setDedupeBusy(false);
      },
    });
  };
  const onExportFindingsMarkdown = () => {
    try {
      const md = findingsToMarkdown(findings, {
        runName: run?.name,
        siteName,
        generatedAt: new Date(),
      });
      downloadTextFile(markdownExportFilename(run, siteName), md, "text/markdown;charset=utf-8");
    } catch (err) {
      setError(err.message);
    }
  };
  const onImportFindingsFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = parseFindingsMarkdown(await file.text());
      if (!imported.length) throw new Error("No issues found in the selected file.");
      const result = await webRunsApi.importFindings(runId, imported);
      setFindings(await webRunsApi.getFindings(runId));
      webRunsApi
        .getValidateStatus(runId)
        .then(setValidateStatus)
        .catch(() => {});
      const [r, g] = await Promise.all([webRunsApi.getRun(runId), webRunsApi.getGraph(runId)]);
      setRun(r);
      setGraph(g);
      setImportMessage(`Imported ${result.imported} issue${result.imported === 1 ? "" : "s"}.`);
    } catch (err) {
      setError(err.message);
    }
  };
  const onValidateFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      const updated = await webRunsApi.validateFinding(runId, findingId);
      setFindings((prev) =>
        prev.map((f) =>
          f.id === findingId
            ? {
                ...f,
                ...updated,
              }
            : f,
        ),
      );
      setValidateStatus((vs) =>
        vs
          ? {
              ...vs,
              status: "running",
            }
          : vs,
      );
      setValidateBusy(true);
    } catch (err) {
      setError(err.message);
    }
  };
  const editor = useFindingEditor({
    runId,
    runKind: "web",
    onError: setError,
    onSaved: (id, updated) =>
      setFindings((previous) =>
        previous.map((finding) => (finding.id === id ? { ...finding, ...updated } : finding)),
      ),
  });
  const onStopValidation = async () => {
    try {
      const vs = await webRunsApi.stopValidation(runId);
      setValidateStatus(vs);
      setValidateBusy(false);
      setFindings(await webRunsApi.getFindings(runId));
    } catch (err) {
      setError(err.message);
    }
  };

  return {
    findings,
    setFindings,
    validateStatus,
    setValidateStatus,
    validateBusy,
    setValidateBusy,
    dedupeBusy,
    collapseToken,
    editor,
    onDeleteFinding,
    onDeleteFindingGroup,
    onValidateAll,
    onDeduplicateFindings,
    onExportFindingsMarkdown,
    onImportFindingsFile,
    importMessage,
    clearImportMessage: () => setImportMessage(null),
    onValidateFinding,
    onStopValidation,
  };
}
