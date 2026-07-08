import { useState, useEffect, useRef } from "react";
import { api } from "../../lib/api";
import { useColResize } from "./_helpers";
import { ALICE_DEDUP_DIRECTIVE } from "./_constants";
import { findingsToMarkdown, downloadTextFile, markdownExportFilename, parseFindingsMarkdown } from "../../lib/utilities";

// Owns everything the Findings tab needs: the findings list, validation +
// dedup status, per-row edit/expand UI state, and the handlers that mutate
// them. Extracted from TestRunDetail so the tab is driven by one cohesive
// object instead of ~40 loose props. The live SSE stream still lives in the
// parent; it writes through the setFindings/setValidateStatus this returns.
export function useFindings(runId, activeTab, {
  run,
  siteName,
  submitAliceDirective,
  aliceIsThinking,
  setRun,
  setGraph,
  setError
}) {
  const [validateStatus, setValidateStatus] = useState(null);
  const [validateBusy, setValidateBusy] = useState(false);
  const [dedupeBusy, setDedupeBusy] = useState(false);
  const [findings, setFindings] = useState([]);
  const [expandedFinding, setExpandedFinding] = useState(null);
  const [editingFinding, setEditingFinding] = useState(null); // finding id being edited
  const [editDraft, setEditDraft] = useState(null); // working copy of the edited finding
  const [editBusy, setEditBusy] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState(new Set(["__unconfirmed__"]));
  const toggleGroup = title => setExpandedGroups(prev => {
    const next = new Set(prev);
    next.has(title) ? next.delete(title) : next.add(title);
    return next;
  });
  const issueImportInputRef = useRef(null);
  const [findColW, startFindResize] = useColResize("colw:findings", [80, 52, null, 28, 60]);

  // Poll findings when on findings tab.
  useEffect(() => {
    if (activeTab !== "findings") return;
    api.getFindings(runId).then(setFindings).catch(() => {});
    const iv = setInterval(() => {
      api.getFindings(runId).then(setFindings).catch(() => {});
    }, 4000);
    return () => clearInterval(iv);
  }, [runId, activeTab]);

  // Poll validation status while validating is running. Keep polling while the
  // local busy flag is true too, because the final SSE event can race with the
  // backend task registry; the next status read is the authoritative state.
  useEffect(() => {
    if (!validateBusy && validateStatus?.status !== "running" && activeTab !== "findings") return;
    const iv = setInterval(() => {
      api.getValidateStatus(runId).then(vs => {
        setValidateStatus(vs);
        if (vs.status !== "running") setValidateBusy(false);
        if (vs.status !== "running") api.getFindings(runId).then(setFindings).catch(() => {});
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, [runId, validateBusy, validateStatus?.status, activeTab]);

  // Fetch findings when switching to findings tab
  useEffect(() => {
    if (activeTab !== "findings") return;
    api.getFindings(runId).then(setFindings).catch(() => {});
    api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
  }, [activeTab, runId]);

  const onDeleteFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      await api.deleteFinding(runId, findingId);
      setFindings(prev => prev.filter(f => f.id !== findingId));
      if (expandedFinding === findingId) setExpandedFinding(null);
    } catch (err) {
      setError(err.message);
    }
  };
  const onDeleteFindingGroup = async (e, title) => {
    e.stopPropagation();
    if (!confirm(`Delete all instances of "${title}"?`)) return;
    try {
      await api.deleteFindingGroup(runId, title);
      setFindings(prev => prev.filter(f => f.title !== title));
      setExpandedGroups(prev => {
        const next = new Set(prev);
        next.delete(title);
        return next;
      });
    } catch (err) {
      setError(err.message);
    }
  };
  const onValidateAll = async () => {
    if (validateBusy) return;
    setValidateBusy(true);
    try {
      const vs = await api.validateAllFindings(runId);
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
        api.getFindings(runId).then(setFindings).catch(() => {});
        api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
        setExpandedFinding(null);
        setExpandedGroups(new Set());
        setDedupeBusy(false);
      }
    });
  };
  const onExportFindingsMarkdown = () => {
    try {
      const md = findingsToMarkdown(findings, {
        runName: run?.name,
        siteName,
        generatedAt: new Date()
      });
      downloadTextFile(markdownExportFilename(run, siteName), md, "text/markdown;charset=utf-8");
    } catch (err) {
      setError(err.message);
    }
  };
  const onImportFindingsClick = () => {
    issueImportInputRef.current?.click();
  };
  const onImportFindingsFile = async e => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = parseFindingsMarkdown(await file.text());
      if (!imported.length) throw new Error("No issues found in the selected file.");
      const result = await api.importFindings(runId, imported);
      setFindings(await api.getFindings(runId));
      api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
      const [r, g] = await Promise.all([api.getRun(runId), api.getGraph(runId)]);
      setRun(r);
      setGraph(g);
      alert(`Imported ${result.imported} issue${result.imported === 1 ? "" : "s"}.`);
    } catch (err) {
      setError(err.message);
    }
  };
  const onValidateFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      const updated = await api.validateFinding(runId, findingId);
      setFindings(prev => prev.map(f => f.id === findingId ? {
        ...f,
        ...updated
      } : f));
      setValidateStatus(vs => vs ? {
        ...vs,
        status: "running"
      } : vs);
      setValidateBusy(true);
    } catch (err) {
      setError(err.message);
    }
  };
  const onEditFinding = (e, f) => {
    e.stopPropagation();
    setExpandedFinding(f.id);
    setEditingFinding(f.id);
    setEditDraft({
      severity: f.severity,
      validation_status: f.validation_status,
      title: f.title || "",
      affected_url: f.affected_url || "",
      cvss_score: f.cvss_score ?? 0,
      cvss_vector: f.cvss_vector || "",
      description: f.description || "",
      impact: f.impact || "",
      likelihood: f.likelihood || "",
      recommendation: f.recommendation || ""
    });
  };
  const onCancelEditFinding = e => {
    e?.stopPropagation?.();
    setEditingFinding(null);
    setEditDraft(null);
  };
  const onSaveEditFinding = async (e, findingId) => {
    e?.stopPropagation?.();
    if (!editDraft || editBusy) return;
    setEditBusy(true);
    try {
      const updated = await api.updateFinding(runId, findingId, {
        ...editDraft,
        cvss_score: Number(editDraft.cvss_score) || 0
      });
      setFindings(prev => prev.map(f => f.id === findingId ? {
        ...f,
        ...updated
      } : f));
      setEditingFinding(null);
      setEditDraft(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setEditBusy(false);
    }
  };
  const onStopValidation = async () => {
    try {
      const vs = await api.stopValidation(runId);
      setValidateStatus(vs);
      setValidateBusy(false);
      setFindings(await api.getFindings(runId));
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
  };
}
