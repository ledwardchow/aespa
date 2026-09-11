import * as applicationsApi from "../../shared/api/applications.js";
import { useState, useMemo } from "react";
import { useReviewLeads } from "./useReviewLeads.js";

import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { SastLeadDetails } from "../../shared/ui/SastLeadDetails.jsx";
import { LeadReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";
import {
  severityClass,
  confidencePct,
  safeParseJson,
} from "../../shared/runs/campaignPresentation.js";
import { ValidationCaseList, ValidationCaseSummary } from "./ValidationCases.jsx";

const HIGH_CONFIDENCE = 0.8;

// A mapping's contributing component names, always non-empty for display/
// filtering purposes: a resolved list of names when available, otherwise a
// neutral label distinguishing a genuinely cross-repository lead (provenance
// exists on the server but couldn't be named) from an unresolved single lead.
function componentNamesFor(mapping) {
  if (mapping.component_names && mapping.component_names.length > 0) return mapping.component_names;
  return [mapping.lead_producer_run_type === "campaign" ? "Cross-repository" : "Unknown component"];
}

function crossRepositoryRootKey(mapping) {
  if (mapping.lead_producer_run_type !== "campaign") return null;
  const path = safeParseJson(mapping.lead_attack_path_json, {});
  const vulnerability = path.vulnerability;
  const backendRoute = path.backend_route;
  if (!vulnerability?.lead_id || !Number.isInteger(backendRoute?.component_id)) return null;
  const backendCase = Array.isArray(path.instances)
    ? path.instances.some((instance) => instance?.case === "backend")
    : /^Cross-repository:\s*Backend lead/i.test(mapping.lead_title || "");
  return [
    "cross-repository",
    mapping.lead_category || "",
    vulnerability.lead_id,
    backendRoute.component_id,
    backendCase ? "backend" : "source",
  ].join(":");
}

function reviewLeadGroupKey(mapping) {
  return (
    crossRepositoryRootKey(mapping) || `lead:${mapping.lead_origin_lead_id || mapping.lead_id}`
  );
}

function endpointInstancesFor(mappings) {
  const instances = new Map();
  for (const mapping of mappings) {
    const path = safeParseJson(mapping.lead_attack_path_json, {});
    const pathInstances = Array.isArray(path.instances)
      ? path.instances
      : [
          {
            case: "legacy",
            source_location: path.frontend_entrypoint?.location,
            source_method: path.frontend_entrypoint?.method,
            source_path: path.frontend_entrypoint?.path,
            target_location: path.backend_route?.location,
            target_method: path.backend_route?.method,
            target_path: path.backend_route?.path,
          },
        ];
    for (const instance of pathInstances) {
      if (!instance?.source_location && !instance?.target_location) continue;
      const key = [
        instance.case,
        instance.source_location,
        instance.source_method,
        instance.source_path,
        instance.target_location,
        instance.target_method,
        instance.target_path,
      ].join("|");
      instances.set(key, instance);
    }
  }
  return [...instances.values()];
}

// ── CampaignReviewTab ────────────────────────────────────────────────────────
// The main human decision point: proposed lead→target routings, grouped by
// source lead, with per-mapping approve/reject, filters, and a guarded bulk
// approve for high-confidence matches only. Explicitly supports the
// zero-proposal case (submits an empty decision list rather than blocking).
// Every lead field (title/description/severity/location/component names) is
// read straight off the server-enriched mapping row — no per-SAST-run lead
// fan-out, and no "detail unavailable" fallback, since the mapping endpoint
// itself now resolves cross-repository leads too.
export function CampaignReviewTab({
  applicationId,
  campaignId,
  campaign,
  canContinue,
  continueToLive,
  continueBusy,
  onSubmitted,
}) {
  const { mappings, targets, validationCases, error, setError, submitReview } = useReviewLeads(
    applicationId,
    campaignId,
  );
  const [decisions, setDecisions] = useState({}); // mapping_id -> "approve" | "reject"
  const [selected, setSelected] = useState(new Set());
  const [severityFilter, setSeverityFilter] = useState("");
  const [componentFilter, setComponentFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");
  const [minConfidence, setMinConfidence] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [supplementalBusy, setSupplementalBusy] = useState(null);
  const [result, setResult] = useState(null);

  const filtered = useMemo(
    () =>
      (mappings || []).filter((m) => {
        if (severityFilter && (m.lead_severity || "unknown") !== severityFilter) return false;
        if (componentFilter && !componentNamesFor(m).includes(componentFilter)) return false;
        if (targetFilter && String(m.target_id) !== targetFilter) return false;
        if (m.score < minConfidence) return false;
        return true;
      }),
    [mappings, severityFilter, componentFilter, targetFilter, minConfidence],
  );

  // Group by lead so proposed targets for the same vulnerability sit together.
  const grouped = useMemo(() => {
    const byLead = new Map();
    for (const m of filtered) {
      const key = reviewLeadGroupKey(m);
      if (!byLead.has(key)) byLead.set(key, []);
      byLead.get(key).push(m);
    }
    return [...byLead.values()];
  }, [filtered]);

  const severityOptions = useMemo(
    () => [...new Set((mappings || []).map((m) => m.lead_severity || "unknown"))],
    [mappings],
  );
  const componentOptions = useMemo(
    () => [...new Set((mappings || []).flatMap(componentNamesFor))],
    [mappings],
  );
  const targetOptions = useMemo(
    () => [...new Set((mappings || []).map((m) => m.target_id))],
    [mappings],
  );

  const setDecision = (mappingId, decision) =>
    setDecisions((prev) => ({ ...prev, [mappingId]: decision }));
  const toggleSelected = (mappingId) =>
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(mappingId)) n.delete(mappingId);
      else n.add(mappingId);
      return n;
    });

  const approveSelected = () => {
    selected.forEach((id) => setDecision(id, "approve"));
    setSelected(new Set());
  };
  const rejectSelected = () => {
    selected.forEach((id) => setDecision(id, "reject"));
    setSelected(new Set());
  };

  const highConfidenceCount = filtered.filter(
    (m) => m.score >= HIGH_CONFIDENCE && m.status === "proposed",
  ).length;
  const bulkApproveHighConfidence = () => {
    filtered.forEach((m) => {
      if (m.score >= HIGH_CONFIDENCE && m.status === "proposed") {
        setDecision(m.id, "approve");
      }
    });
  };

  const proposedCount = filtered.filter((m) => m.status === "proposed").length;
  const bulkApproveAll = () => {
    filtered.forEach((m) => {
      if (m.status === "proposed") setDecision(m.id, "approve");
    });
  };

  const pendingDecisionCount = Object.keys(decisions).length;
  const casesByMapping = useMemo(() => {
    const byMapping = new Map();
    for (const validationCase of validationCases || []) {
      const key = String(validationCase.mapping_id);
      if (key == null) continue;
      if (!byMapping.has(key)) byMapping.set(key, []);
      byMapping.get(key).push(validationCase);
    }
    return byMapping;
  }, [validationCases]);
  const supplementalTargets = useMemo(() => {
    const byTarget = new Map();
    for (const mapping of mappings || []) {
      if (mapping.status !== "approved" || mapping.copied_lead_id) continue;
      const mappingCases = casesByMapping.get(String(mapping.id));
      if (mappingCases?.length > 0) {
        if (!mappingCases.some((validationCase) => validationCase.readiness_status === "resolved"))
          continue;
      } else if (!["live_resolved", "crawl_partial"].includes(mapping.path_status)) continue;
      if (!byTarget.has(mapping.target_id)) byTarget.set(mapping.target_id, []);
      byTarget.get(mapping.target_id).push(mapping.id);
    }
    return byTarget;
  }, [mappings, casesByMapping]);

  const onSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const payload = Object.entries(decisions).map(([mappingId, decision]) => ({
        mapping_id: +mappingId,
        approve: decision === "approve",
      }));
      const res = await submitReview(payload);
      setResult(res);
      setDecisions({});
      await onSubmitted?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const onSubmitEmpty = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitReview([]);
      setResult(res);
      await onSubmitted?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const runSupplementalValidation = async (targetId, mappingIds) => {
    setSupplementalBusy(targetId);
    setError(null);
    try {
      await applicationsApi.supplementalValidateCampaignTarget(
        applicationId,
        campaignId,
        targetId,
        { mapping_ids: mappingIds },
      );
      await onSubmitted?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSupplementalBusy(null);
    }
  };

  if (error) return <div className="alert error">{error}</div>;
  if (mappings === null) return <div className="subtle">Loading…</div>;

  if (mappings.length === 0) {
    return (
      <div>
        <EmptyState
          title="No proposed lead-target mappings"
          sub="This campaign's code scans produced no leads with enough evidence to propose a live-target routing. You can still explicitly submit an empty review to move on to live testing."
        />
        {campaign.review_submitted_at ? (
          <div className="alert success" style={{ marginTop: 12 }}>
            Review already submitted — zero mappings were proposed.
          </div>
        ) : (
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn" disabled={submitting} onClick={onSubmitEmpty}>
              {submitting ? "Submitting…" : "Submit empty review"}
            </button>
          </div>
        )}
        {canContinue && (
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn" disabled={continueBusy} onClick={continueToLive}>
              Continue to live testing
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      {result && (
        <div className="alert success" style={{ marginBottom: 14 }}>
          Review recorded — {result.approved} approved, {result.rejected} rejected.
          {canContinue && (
            <>
              {" "}
              <button
                className="btn sm"
                style={{ marginLeft: 10 }}
                disabled={continueBusy}
                onClick={continueToLive}
              >
                Continue to live testing
              </button>
            </>
          )}
        </div>
      )}
      <div className="app-review-filters">
        <select
          className="select"
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
        >
          <option value="">All severities</option>
          {severityOptions.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={componentFilter}
          onChange={(e) => setComponentFilter(e.target.value)}
        >
          <option value="">All components</option>
          {componentOptions.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={targetFilter}
          onChange={(e) => setTargetFilter(e.target.value)}
        >
          <option value="">All targets</option>
          {targetOptions.map((id) => (
            <option key={id} value={id}>
              {targets[id] || `#${id}`}
            </option>
          ))}
        </select>
        <label className="subtle" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          Min confidence
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={minConfidence}
            onChange={(e) => setMinConfidence(+e.target.value)}
          />
          {confidencePct(minConfidence)}
        </label>
      </div>

      {validationCases.length > 0 && (
        <div className="alert info app-review-readiness" style={{ marginBottom: 14 }}>
          <div className="row spread" style={{ gap: 10, flexWrap: "wrap" }}>
            <div>
              <strong>Validation readiness</strong>
              <div className="subtle" style={{ marginTop: 4 }}>
                Approval allows AESPA to resolve and validate a route. It does not prove that the
                browser can reach it.
              </div>
            </div>
            <ValidationCaseSummary cases={validationCases} />
          </div>
        </div>
      )}

      <div className="row spread" style={{ marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <div className="row" style={{ gap: 8 }}>
          <button
            className="btn secondary sm"
            disabled={selected.size === 0}
            onClick={approveSelected}
          >
            Approve selected ({selected.size})
          </button>
          <button
            className="btn danger-outline sm"
            disabled={selected.size === 0}
            onClick={rejectSelected}
          >
            Reject selected
          </button>
          <button
            className="btn secondary sm"
            disabled={highConfidenceCount === 0}
            onClick={bulkApproveHighConfidence}
            title="Only mappings scored 80% or higher"
          >
            Approve all high-confidence ({highConfidenceCount})
          </button>
          <button
            className="btn secondary sm"
            disabled={proposedCount === 0}
            onClick={bulkApproveAll}
            title="Approve every proposed mapping currently shown"
          >
            Approve all ({proposedCount})
          </button>
        </div>
        <button
          className="btn"
          disabled={submitting || pendingDecisionCount === 0}
          onClick={onSubmit}
        >
          {submitting
            ? "Submitting…"
            : `Submit review (${pendingDecisionCount} decision${pendingDecisionCount !== 1 ? "s" : ""})`}
        </button>
      </div>
      {campaign.status === "completed" && supplementalTargets.size > 0 && (
        <div className="alert info" style={{ marginBottom: 14 }}>
          <strong>New crawl paths</strong> — these approved paths were discovered after the initial
          scan. They can be validated without recrawling.
          <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: "wrap" }}>
            {[...supplementalTargets.entries()].map(([targetId, ids]) => (
              <button
                key={targetId}
                className="btn secondary sm"
                disabled={supplementalBusy !== null}
                onClick={() => runSupplementalValidation(targetId, ids)}
              >
                {supplementalBusy === targetId
                  ? "Validating…"
                  : `Validate ${ids.length} new path${ids.length === 1 ? "" : "s"} on ${targets[targetId] || `target #${targetId}`}`}
              </button>
            ))}
          </div>
        </div>
      )}

      {grouped.map((group) => (
        <LeadGroup
          key={group[0].lead_id}
          mappings={group}
          targets={targets}
          decisions={decisions}
          selected={selected}
          onSetDecision={setDecision}
          onToggleSelected={toggleSelected}
          applicationId={applicationId}
          campaignId={campaignId}
          casesByMapping={casesByMapping}
        />
      ))}
    </div>
  );
}

function LeadGroup({
  mappings,
  targets,
  decisions,
  selected,
  onSetDecision,
  onToggleSelected,
  applicationId,
  campaignId,
  casesByMapping,
}) {
  const [expanded, setExpanded] = useState(false);
  const first = mappings[0];
  const componentNames = componentNamesFor(first);
  const endpointInstances = endpointInstancesFor(mappings);
  const leadObj = {
    id: first.lead_id,
    reference: first.lead_reference,
    origin_reference: first.lead_origin_reference,
    title: first.lead_title,
    description: first.lead_description,
    severity: first.lead_severity,
    location: first.lead_location,
    category: first.lead_category,
    confidence: first.lead_confidence,
    source: first.lead_source,
    fingerprint: first.lead_fingerprint,
    suggested_endpoint: first.lead_suggested_endpoint,
    status: first.lead_status,
    validation_status: first.lead_validation_status,
    validation_reasoning: first.lead_validation_reasoning,
    reportable: first.lead_reportable,
    evidence: first.lead_evidence,
    note: first.lead_note,
    source_trace_json: first.lead_source_trace_json,
    control_trace_json: first.lead_control_trace_json,
    sink_trace_json: first.lead_sink_trace_json,
    counterevidence_json: first.lead_counterevidence_json,
    proof_gaps_json: first.lead_proof_gaps_json,
    attack_path_json: first.lead_attack_path_json,
    producer_run_id: first.lead_producer_run_id,
    producer_run_type: first.lead_producer_run_type,
  };

  return (
    <div className="card app-review-lead-card" style={{ marginBottom: 14 }}>
      <div className="row spread" style={{ gap: 8, alignItems: "center" }}>
        <div className="row" style={{ gap: 8, alignItems: "center", flex: 1, flexWrap: "wrap" }}>
          <span className={"sev-badge " + severityClass(first.lead_severity || "medium")}>
            {first.lead_severity || "unknown"}
          </span>
          {first.lead_reference && (
            <LeadReferenceLink
              reference={first.lead_reference}
              title={first.lead_title}
              description={first.lead_description}
              severity={first.lead_severity}
              finding_source={first.lead_source}
              href={
                first.lead_producer_run_type === "sast" && first.lead_producer_run_id
                  ? `#/sast-runs/${first.lead_producer_run_id}/candidates?lead=${encodeURIComponent(first.lead_reference)}`
                  : undefined
              }
            />
          )}
          <span style={{ fontWeight: 700 }}>{first.lead_title || "Untitled lead"}</span>
          <span className="subtle" style={{ fontSize: 12 }}>
            {componentNames.join(", ")}
            {first.lead_location ? ` · ${first.lead_location}` : ""}
          </span>
          {endpointInstances.length > 1 && (
            <span className="subtle" style={{ fontSize: 12 }}>
              · {endpointInstances.length} endpoint instances
            </span>
          )}
        </div>
        <button className="btn secondary sm" onClick={() => setExpanded((prev) => !prev)}>
          {expanded ? "Collapse trace" : "View full trace"}
        </button>
      </div>

      {expanded && (
        <div style={{ marginTop: 10, borderTop: "1px solid var(--border-2)", paddingTop: 10 }}>
          <SastLeadDetails lead={leadObj} showSummary={false} />
          {endpointInstances.length > 1 && (
            <div className="subtle" style={{ marginTop: 10 }}>
              <strong>Matched endpoints</strong>
              <ul style={{ margin: "6px 0 0 18px" }}>
                {endpointInstances.map((instance, index) => (
                  <li
                    key={`${instance.source_location || "source"}-${instance.source_path || ""}-${instance.target_location || index}-${instance.target_path || ""}`}
                  >
                    {instance.source_method || ""}{" "}
                    {instance.source_path || instance.source_location || "source"}
                    {instance.target_path && (
                      <>
                        {" "}
                        → {instance.target_method || ""} {instance.target_path}
                      </>
                    )}
                    {instance.access === "authenticated" && (
                      <>
                        {" "}
                        (authenticated via {instance.authentication?.acquisition?.method || ""}{" "}
                        {instance.authentication?.acquisition?.path || "credential flow"})
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <table className="app-review-mappings-table" style={{ marginTop: 12 }}>
        <colgroup>
          <col className="review-select-col" />
          <col className="review-target-col" />
          <col className="review-confidence-col" />
          <col className="review-why-col" />
          <col className="review-decision-col" />
        </colgroup>
        <thead>
          <tr>
            <th></th>
            <th>Proposed target</th>
            <th>Confidence</th>
            <th>Why</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {mappings.map((mapping) => (
            <MappingRow
              key={mapping.id}
              mapping={mapping}
              targets={targets}
              decisions={decisions}
              selected={selected}
              onSetDecision={onSetDecision}
              onToggleSelected={onToggleSelected}
              applicationId={applicationId}
              campaignId={campaignId}
              validationCases={casesByMapping.get(String(mapping.id)) || []}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MappingRow({
  mapping,
  targets,
  decisions,
  selected,
  onSetDecision,
  onToggleSelected,
  applicationId,
  campaignId,
  validationCases,
}) {
  const [pathEditorOpen, setPathEditorOpen] = useState(false);
  const decision = decisions[mapping.id] || (mapping.status !== "proposed" ? mapping.status : null);
  const evidence = safeParseJson(mapping.evidence_json, {});
  const why = mapping.rationale || Object.keys(evidence).join(", ") || "—";
  const editorId = `mapping-path-editor-${mapping.id}`;

  return (
    <>
      <tr>
        <td>
          <input
            type="checkbox"
            checked={selected.has(mapping.id)}
            onChange={() => onToggleSelected(mapping.id)}
          />
        </td>
        <td>{targets[mapping.target_id] || `#${mapping.target_id}`}</td>
        <td>{confidencePct(mapping.lead_trace_confidence ?? mapping.score)}</td>
        <td className="subtle" style={{ fontSize: 12 }}>
          {why}
        </td>
        <td>
          <div className="row" style={{ gap: 4 }}>
            <button
              className={"btn sm" + (decision === "approve" ? "" : " ghost")}
              onClick={() => onSetDecision(mapping.id, "approve")}
            >
              Approve for validation
            </button>
            <button
              className={"btn danger-outline sm" + (decision === "reject" ? "" : "")}
              onClick={() => onSetDecision(mapping.id, "reject")}
            >
              Reject
            </button>
          </div>
          <button
            className="btn ghost sm"
            aria-controls={editorId}
            aria-expanded={pathEditorOpen}
            onClick={() => setPathEditorOpen((value) => !value)}
            style={{ marginTop: 6 }}
          >
            {pathEditorOpen ? "Hide path editor" : "Edit frontend path"}
          </button>
        </td>
      </tr>
      {pathEditorOpen && (
        <tr className="app-review-path-editor-row">
          <td colSpan={5}>
            <MappingPathEditor
              applicationId={applicationId}
              campaignId={campaignId}
              mapping={mapping}
              editorId={editorId}
            />
          </td>
        </tr>
      )}
      {validationCases.length > 0 && (
        <tr className="app-review-validation-row">
          <td colSpan={5}>
            <div className="validation-case-inline">
              <div className="validation-detail-label">Validation case</div>
              <ValidationCaseList cases={validationCases} />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function MappingPathEditor({ applicationId, campaignId, mapping, editorId }) {
  const initial = safeParseJson(mapping.path_json, {});
  const [entry, setEntry] = useState(initial.entry || "");
  const [dynamicTest, setDynamicTest] = useState(initial.dynamic_test || "");
  const [proofGaps, setProofGaps] = useState((initial.proof_gaps || []).join("\n"));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const save = async () => {
    setBusy(true);
    setMessage("");
    try {
      const path = {
        entry,
        dynamic_test: dynamicTest,
        proof_gaps: proofGaps
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
      };
      await applicationsApi.editCampaignMapping(applicationId, campaignId, mapping.id, {
        expected_updated_at: mapping.updated_at,
        path,
      });
      setMessage("Saved reviewer guidance.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div id={editorId} className="card app-review-path-editor">
      <div className="row spread" style={{ gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
        <strong>Frontend path guidance</strong>
        <span className="subtle">Reviewer values are marked as guidance until verified.</span>
      </div>
      <label className="field-label">
        Frontend entry route
        <input
          className="input"
          value={entry}
          onChange={(event) => setEntry(event.target.value)}
          placeholder="/checkout"
        />
      </label>
      <label className="field-label">
        Dynamic test objective
        <textarea
          className="textarea"
          value={dynamicTest}
          onChange={(event) => setDynamicTest(event.target.value)}
          rows={3}
        />
      </label>
      <label className="field-label">
        Proof gaps (one per line)
        <textarea
          className="textarea"
          value={proofGaps}
          onChange={(event) => setProofGaps(event.target.value)}
          rows={3}
        />
      </label>
      <div className="row spread">
        <span />
        <button className="btn sm" disabled={busy} onClick={save}>
          {busy ? "Saving…" : "Save path"}
        </button>
      </div>
      {message && (
        <div className="subtle" style={{ marginTop: 6 }}>
          {message}
        </div>
      )}
    </div>
  );
}
