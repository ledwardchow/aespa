import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { safeParseJson, confidencePct } from "./_helpers";
import { EmptyState } from "../../components/EmptyState";

const ORIGIN_LABEL = {
  deterministic: "Direct evidence match",
  llm_assisted: "LLM-resolved match"
};

// ── CampaignConnectionsTab ───────────────────────────────────────────────────
// A detailed connection diagram view — folds confidence, evidence, source facts,
// and origin type directly into each row.
export function CampaignConnectionsTab({ applicationId, campaignId, campaign, rebuildConnections, busy }) {
  const [connections, setConnections] = useState(null);
  const [components, setComponents] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.getCampaignConnections(applicationId, campaignId),
      api.listAppComponents(applicationId)
    ]).then(([conns, comps]) => {
      if (cancelled) return;
      setConnections(conns);
      const map = {};
      comps.forEach(c => { map[c.id] = c.name; });
      setComponents(map);
    }).catch(e => !cancelled && setError(e.message));
    return () => { cancelled = true; };
  }, [applicationId, campaignId, campaign?.status, campaign?.updated_at]);

  const canRebuild = ["failed", "interrupted", "awaiting_review", "completed", "stopped"].includes(campaign?.status);
  const retrying = campaign?.status === "failed" || campaign?.status === "interrupted";
  const rebuildLabel = retrying ? "Resume context matching" : "Re-run context matching";
  const matchingControls = <div className="row spread" style={{ marginBottom: 14, gap: 10, flexWrap: "wrap" }}>
    <div>
      <div className="form-section-title">Context matching</div>
      <div className="subtle" style={{ fontSize: 12 }}>
        Trace data flows by discovering API calls between components.
      </div>
    </div>
    {canRebuild && <button className="btn secondary sm" disabled={busy} onClick={rebuildConnections}>
      {busy ? "Matching context…" : rebuildLabel}
    </button>}
  </div>;

  if (error) return <>{matchingControls}<div className="alert error">{error}</div></>;
  if (connections === null) return <>{matchingControls}<div className="subtle">Loading…</div></>;

  const name = id => components[id] || `#${id}`;

  if (connections.length === 0) return <>{matchingControls}<EmptyState
    title="No connections found"
    sub={campaign?.status === "failed" || campaign?.status === "interrupted"
      ? "Connection mapping did not complete. Resume context matching to retry it without rerunning completed code scans."
      : "No evidence-backed cross-component connection has been resolved yet. Review campaign activity to see whether mapping is still running or needs attention."} /></>;

  return <div>
    {matchingControls}
    <div className="row spread" style={{ marginBottom: 12 }}>
      <span className="subtle">{connections.length} connection{connections.length !== 1 ? "s" : ""}</span>
    </div>
    <div className="connection-diagram">
      {connections.map(c => <ConnectionCard key={c.id} connection={c} sourceName={name(c.source_component_id)} targetName={name(c.target_component_id)} />)}
    </div>
  </div>;
}

function ConnectionCard({ connection, sourceName, targetName }) {
  const evidence = safeParseJson(connection.evidence_json, {});
  const locations = value => [
    ...(value?.evidence_location ? [value.evidence_location] : []),
    ...(Array.isArray(value?.supporting_locations) ? value.supporting_locations : [])
  ];
  const renderLocations = value => locations(value).map(location =>
    <div key={location} className="mono subtle" style={{ fontSize: 12 }}>{location}</div>
  );

  return <div className="connection-card">
    <div className="connection-card-header">
      <div className="connection-flow">
        <span className="connection-node">{sourceName}</span>
        <span className="connection-arrow">→</span>
        <span className="connection-node">{targetName}</span>
      </div>
      <div className="connection-badges">
        <span className="badge neutral">{confidencePct(connection.confidence)}</span>
        <span className="badge info" style={{ marginLeft: 6 }}>{ORIGIN_LABEL[connection.match_kind] || connection.match_kind}</span>
      </div>
    </div>

    {(connection.rationale || evidence.call || evidence.route) && <div className="connection-card-body">
      {connection.rationale && <div className="connection-rationale">
        <strong>Why:</strong> {connection.rationale}
      </div>}
      {(evidence.call || evidence.route) && <div className="connection-evidence-grid">
        {evidence.call && <div className="connection-evidence-item">
          <span className="evidence-label">Outbound call ({sourceName})</span>
          <div className="mono subtle" style={{ fontSize: 12, marginTop: 2 }}>
            <strong>{evidence.call.method}</strong> {evidence.call.path}{evidence.call.host ? ` @ ${evidence.call.host}` : ""}
          </div>
          {renderLocations(evidence.call)}
        </div>}
        {evidence.route && <div className="connection-evidence-item">
          <span className="evidence-label">Matched route ({targetName})</span>
          <div className="mono subtle" style={{ fontSize: 12, marginTop: 2 }}>
            <strong>{evidence.route.method}</strong> {evidence.route.path}
          </div>
          {renderLocations(evidence.route)}
        </div>}
      </div>}
    </div>}
  </div>;
}
