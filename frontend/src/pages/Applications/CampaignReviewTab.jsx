import { useState, useMemo } from "react";
import { useReviewLeads } from "./useReviewLeads";
import { EmptyState } from "../../components/EmptyState";
import { SastLeadDetails } from "../../components/SastLeadDetails";
import { severityClass, confidencePct, safeParseJson } from "./_helpers";

const HIGH_CONFIDENCE = 0.8;

// A mapping's contributing component names, always non-empty for display/
// filtering purposes: a resolved list of names when available, otherwise a
// neutral label distinguishing a genuinely cross-repository lead (provenance
// exists on the server but couldn't be named) from an unresolved single lead.
function componentNamesFor(mapping) {
  if (mapping.component_names && mapping.component_names.length > 0) return mapping.component_names;
  return [mapping.lead_producer_run_type === "campaign" ? "Cross-repository" : "Unknown component"];
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
export function CampaignReviewTab({ applicationId, campaignId, campaign, canContinue, continueToLive, continueBusy, onSubmitted }) {
  const { mappings, targets, error, setError, submitReview } = useReviewLeads(applicationId, campaignId);
  const [decisions, setDecisions] = useState({}); // mapping_id -> "approve" | "reject"
  const [selected, setSelected] = useState(new Set());
  const [severityFilter, setSeverityFilter] = useState("");
  const [componentFilter, setComponentFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");
  const [minConfidence, setMinConfidence] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const filtered = useMemo(() => (mappings || []).filter(m => {
    if (severityFilter && (m.lead_severity || "unknown") !== severityFilter) return false;
    if (componentFilter && !componentNamesFor(m).includes(componentFilter)) return false;
    if (targetFilter && String(m.target_id) !== targetFilter) return false;
    if (m.score < minConfidence) return false;
    return true;
  }), [mappings, severityFilter, componentFilter, targetFilter, minConfidence]);

  // Group by lead so proposed targets for the same vulnerability sit together.
  const grouped = useMemo(() => {
    const byLead = new Map();
    for (const m of filtered) {
      const key = m.lead_id;
      if (!byLead.has(key)) byLead.set(key, []);
      byLead.get(key).push(m);
    }
    return [...byLead.values()];
  }, [filtered]);

  const severityOptions = useMemo(() => [...new Set((mappings || []).map(m => m.lead_severity || "unknown"))], [mappings]);
  const componentOptions = useMemo(() => [...new Set((mappings || []).flatMap(componentNamesFor))], [mappings]);
  const targetOptions = useMemo(() => [...new Set((mappings || []).map(m => m.target_id))], [mappings]);

  const setDecision = (mappingId, decision) => setDecisions(prev => ({ ...prev, [mappingId]: decision }));
  const toggleSelected = mappingId => setSelected(prev => {
    const n = new Set(prev);
    if (n.has(mappingId)) n.delete(mappingId); else n.add(mappingId);
    return n;
  });

  const approveSelected = () => { selected.forEach(id => setDecision(id, "approve")); setSelected(new Set()); };
  const rejectSelected = () => { selected.forEach(id => setDecision(id, "reject")); setSelected(new Set()); };

  const highConfidenceCount = filtered.filter(m => m.score >= HIGH_CONFIDENCE && m.status === "proposed").length;
  const bulkApproveHighConfidence = () => {
    filtered.forEach(m => {
      if (m.score >= HIGH_CONFIDENCE && m.status === "proposed") {
        setDecision(m.id, "approve");
      }
    });
  };

  const pendingDecisionCount = Object.keys(decisions).length;

  const onSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const payload = Object.entries(decisions).map(([mappingId, decision]) => ({
        mapping_id: +mappingId,
        approve: decision === "approve"
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

  if (error) return <div className="alert error">{error}</div>;
  if (mappings === null) return <div className="subtle">Loading…</div>;

  if (mappings.length === 0) {
    return <div>
      <EmptyState
        title="No proposed lead-target mappings"
        sub="This campaign's code scans produced no leads with enough evidence to propose a live-target routing. You can still explicitly submit an empty review to move on to live testing." />
      {campaign.review_submitted_at ? <div className="alert success" style={{ marginTop: 12 }}>Review already submitted — zero mappings were proposed.</div> : <div className="row" style={{ marginTop: 12 }}>
        <button className="btn" disabled={submitting} onClick={onSubmitEmpty}>{submitting ? "Submitting…" : "Submit empty review"}</button>
      </div>}
      {canContinue && <div className="row" style={{ marginTop: 12 }}>
        <button className="btn" disabled={continueBusy} onClick={continueToLive}>Continue to live testing</button>
      </div>}
    </div>;
  }

  return <div>
    {result && <div className="alert success" style={{ marginBottom: 14 }}>
      Review recorded — {result.approved} approved, {result.rejected} rejected.
      {canContinue && <> <button className="btn sm" style={{ marginLeft: 10 }} disabled={continueBusy} onClick={continueToLive}>Continue to live testing</button></>}
    </div>}
    <div className="row" style={{ gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
      <select className="select" value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}>
        <option value="">All severities</option>
        {severityOptions.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      <select className="select" value={componentFilter} onChange={e => setComponentFilter(e.target.value)}>
        <option value="">All components</option>
        {componentOptions.map(c => <option key={c} value={c}>{c}</option>)}
      </select>
      <select className="select" value={targetFilter} onChange={e => setTargetFilter(e.target.value)}>
        <option value="">All targets</option>
        {targetOptions.map(id => <option key={id} value={id}>{targets[id] || `#${id}`}</option>)}
      </select>
      <label className="subtle" style={{ display: "flex", alignItems: "center", gap: 6 }}>
        Min confidence
        <input type="range" min="0" max="1" step="0.05" value={minConfidence} onChange={e => setMinConfidence(+e.target.value)} />
        {confidencePct(minConfidence)}
      </label>
    </div>

    <div className="row spread" style={{ marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
      <div className="row" style={{ gap: 8 }}>
        <button className="btn secondary sm" disabled={selected.size === 0} onClick={approveSelected}>Approve selected ({selected.size})</button>
        <button className="btn danger-outline sm" disabled={selected.size === 0} onClick={rejectSelected}>Reject selected</button>
        <button className="btn secondary sm" disabled={highConfidenceCount === 0} onClick={bulkApproveHighConfidence} title="Only mappings scored 80% or higher">
          Approve all high-confidence ({highConfidenceCount})
        </button>
      </div>
      <button className="btn" disabled={submitting || pendingDecisionCount === 0} onClick={onSubmit}>
        {submitting ? "Submitting…" : `Submit review (${pendingDecisionCount} decision${pendingDecisionCount !== 1 ? "s" : ""})`}
      </button>
    </div>

    {grouped.map(group => <LeadGroup
      key={group[0].lead_id}
      mappings={group}
      targets={targets}
      decisions={decisions}
      selected={selected}
      onSetDecision={setDecision}
      onToggleSelected={toggleSelected}
    />)}
  </div>;
}

function LeadGroup({ mappings, targets, decisions, selected, onSetDecision, onToggleSelected }) {
  const [expanded, setExpanded] = useState(false);
  const first = mappings[0];
  const componentNames = componentNamesFor(first);
  const leadObj = {
    id: first.lead_id,
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

  return <div className="card app-review-lead-card" style={{ marginBottom: 14 }}>
    <div className="row spread" style={{ gap: 8, alignItems: "center" }}>
      <div className="row" style={{ gap: 8, alignItems: "center", flex: 1, flexWrap: "wrap" }}>
        <span className={"sev-badge " + severityClass(first.lead_severity || "medium")}>{first.lead_severity || "unknown"}</span>
        <span style={{ fontWeight: 700 }}>{first.lead_title || `Lead #${first.lead_id}`}</span>
        <span className="subtle" style={{ fontSize: 12 }}>
          {componentNames.join(", ")}{first.lead_location ? ` · ${first.lead_location}` : ""}
        </span>
      </div>
      <button className="btn secondary sm" onClick={() => setExpanded(prev => !prev)}>
        {expanded ? "Collapse trace" : "View full trace"}
      </button>
    </div>
    
    {expanded && <div style={{ marginTop: 10, borderTop: "1px solid var(--border-2)", paddingTop: 10 }}>
      <SastLeadDetails lead={leadObj} showSummary={false} />
    </div>}

    <table style={{ marginTop: 12 }}>
      <thead><tr><th></th><th>Proposed target</th><th>Confidence</th><th>Why</th><th>Decision</th></tr></thead>
      <tbody>
        {mappings.map(mapping => {
          const decision = decisions[mapping.id] || (mapping.status !== "proposed" ? mapping.status : null);
          const evidence = safeParseJson(mapping.evidence_json, {});
          const why = mapping.rationale || Object.keys(evidence).join(", ") || "—";
          return <tr key={mapping.id}>
            <td><input type="checkbox" checked={selected.has(mapping.id)} onChange={() => onToggleSelected(mapping.id)} /></td>
            <td>{targets[mapping.target_id] || `#${mapping.target_id}`}</td>
            <td>{confidencePct(mapping.score)}</td>
            <td className="subtle" style={{ fontSize: 12 }}>{why}</td>
            <td>
              <div className="row" style={{ gap: 4 }}>
                <button className={"btn sm" + (decision === "approve" ? "" : " ghost")} onClick={() => onSetDecision(mapping.id, "approve")}>Approve</button>
                <button className={"btn danger-outline sm" + (decision === "reject" ? "" : "")} onClick={() => onSetDecision(mapping.id, "reject")}>Reject</button>
              </div>
            </td>
          </tr>;
        })}
      </tbody>
    </table>
  </div>;
}
