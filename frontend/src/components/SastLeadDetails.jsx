function jsonValue(value, fallback) {
  if (value && typeof value === "object") return value;
  try {
    const parsed = JSON.parse(value || "");
    return parsed == null ? fallback : parsed;
  } catch {
    return fallback;
  }
}

function displayValue(value, fallback = "—") {
  if (value == null || value === "") return fallback;
  return String(value);
}

function TraceBlock({ label, value, empty = "Not recorded" }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return <div className="sast-flow-step">
    <span>{label}</span>
    {text && text !== "{}" && text !== "[]" ? <pre>{text}</pre> : <p>{empty}</p>}
  </div>;
}

function MetaItem({ label, value, code = false }) {
  const text = displayValue(value);
  return <div>
    <span>{label}</span>
    {code ? <code>{text}</code> : <strong>{text}</strong>}
  </div>;
}

function PathSection({ label, value, empty = "Not recorded" }) {
  if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) {
    return <TraceBlock label={label} value={value} empty={empty} />;
  }
  return <TraceBlock label={label} value={value} empty={empty} />;
}

export function SastLeadDetails({ lead, showSummary = true, findingHref }) {
  if (!lead) return null;

  const source = jsonValue(lead.source_trace_json, {});
  const controls = jsonValue(lead.control_trace_json, []);
  const sink = jsonValue(lead.sink_trace_json, {});
  const counterevidence = jsonValue(lead.counterevidence_json, []);
  const proofGaps = jsonValue(lead.proof_gaps_json, []);
  const attackPath = jsonValue(lead.attack_path_json, {});

  return <div className="sast-lead-details">
    {showSummary && <>
      <div className="sast-evidence-kicker">
        {lead.category || "Unclassified"} · {(lead.severity || "medium").toUpperCase()}
      </div>
      <h3>{lead.title || "Untitled candidate"}</h3>
      <div className="sast-lead-meta-grid">
        <MetaItem label="Lead" value={lead.id ? `#${lead.id}` : null} />
        <MetaItem label="Source" value={lead.source} />
        <MetaItem label="Source SAST run" value={lead.producer_run_id ? `${lead.producer_run_type || "run"} #${lead.producer_run_id}` : null} />
        <MetaItem label="Confidence" value={lead.confidence == null ? null : `${Math.round(lead.confidence * 100)}%`} />
        <MetaItem label="Status" value={lead.status} />
        <MetaItem label="Validation" value={lead.validation_status} />
        <MetaItem label="Reportable" value={lead.reportable == null ? null : lead.reportable ? "Yes" : "No"} />
        <MetaItem label="Location" value={lead.location} code />
        <MetaItem label="Suggested endpoint" value={lead.suggested_endpoint} code />
        <MetaItem label="Fingerprint" value={lead.fingerprint} code />
      </div>
    </>}

    {lead.description && <div className="sast-evidence-callout sast-evidence-callout-info">
      <strong>Description</strong>
      <p>{lead.description}</p>
    </div>}
    <TraceBlock label="Source" value={Object.keys(source).length ? source : lead.location} />
    <TraceBlock label="Controls encountered" value={controls} empty="No controls recorded" />
    <TraceBlock label="Sink" value={sink} />
    <TraceBlock label="Counterevidence" value={counterevidence} empty="No counterevidence recorded" />
    <TraceBlock label="Proof gaps" value={proofGaps} empty="No unresolved static proof gaps" />
    {attackPath.perspective === "frontend" ? <>
      <PathSection label="Live frontend context" value={attackPath.live_frontend_context} empty="Not resolved against a crawl yet" />
      <PathSection label="Final frontend test objective" value={attackPath.dynamic_test} />
      <PathSection label="Post-crawl changes" value={attackPath.post_crawl_changes} empty="No post-crawl changes" />
      <PathSection label="Approved pre-crawl path" value={attackPath.approved_pre_crawl_path} empty="No approved pre-crawl path" />
      <PathSection label="Frontend component hops" value={attackPath.approved_pre_crawl_path?.hops || attackPath.hops} empty="No ordered hops recorded" />
      <PathSection label="Prerequisites and roles" value={attackPath.approved_pre_crawl_path?.prerequisites || attackPath.prerequisites} />
      <PathSection label="Mutation points" value={attackPath.live_frontend_context?.request?.mutation_points || attackPath.mutation_points} />
      <PathSection label="Proof gaps" value={attackPath.approved_pre_crawl_path?.proof_gaps || attackPath.proof_gaps} />
      <PathSection label="Original backend attack path" value={attackPath.origin_attack_path} empty="Original backend path not retained" />
    </> : <TraceBlock label="Attack path" value={attackPath} empty="Not available for this candidate" />}
    {lead.validation_reasoning && <div className="sast-evidence-callout">
      <strong>Validator reasoning</strong>
      <p>{lead.validation_reasoning}</p>
    </div>}
    {lead.evidence && <div className="sast-evidence-callout">
      <strong>Code evidence</strong>
      <pre>{lead.evidence}</pre>
    </div>}
    {lead.note && <div className="sast-evidence-callout sast-evidence-callout-info">
      <strong>Investigation note</strong>
      <p>{lead.note}</p>
    </div>}
    {(lead.linked_finding_id || lead.investigated_by_run_id) && <div className="sast-lead-investigation-meta">
      {lead.linked_finding_id && <span>Linked finding {findingHref ? <a href={findingHref}>#{lead.linked_finding_id}</a> : `#${lead.linked_finding_id}`}</span>}
      {lead.investigated_by_run_id && <span>Investigated by {lead.investigated_by_run_type || "run"} #{lead.investigated_by_run_id}</span>}
    </div>}
  </div>;
}
