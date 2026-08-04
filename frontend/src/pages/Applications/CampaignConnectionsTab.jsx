import { useState, useEffect, useMemo } from "react";
import { api } from "../../lib/api";
import { safeParseJson, confidencePct } from "./_helpers";
import { EmptyState } from "../../components/EmptyState";

const ORIGIN_LABEL = {
  deterministic: "Direct evidence match",
  llm_assisted: "LLM-resolved match"
};

// ── CampaignConnectionsTab ───────────────────────────────────────────────────
// A simple left-to-right diagram (default) plus an accessible list view —
// selecting a connection (in either view) opens a side panel with its
// confidence, evidence, source facts, and origin type. Handles zero
// connections and large sets without extra dependencies.
export function CampaignConnectionsTab({ applicationId, campaignId, campaign, rebuildConnections, busy }) {
  const [connections, setConnections] = useState(null);
  const [components, setComponents] = useState({});
  const [error, setError] = useState(null);
  const [view, setView] = useState("diagram"); // "diagram" | "list"
  const [selectedId, setSelectedId] = useState(null);

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

  const selected = useMemo(() => (connections || []).find(c => c.id === selectedId) || null, [connections, selectedId]);
  const canRebuild = ["failed", "interrupted", "awaiting_review", "completed", "stopped"].includes(campaign?.status);
  const retrying = campaign?.status === "failed" || campaign?.status === "interrupted";
  const rebuildLabel = retrying ? "Resume context matching" : "Re-run context matching";
  const matchingControls = <div className="row spread" style={{ marginBottom: 14, gap: 10, flexWrap: "wrap" }}>
    <div>
      <div className="form-section-title">Context matching</div>
      <div className="subtle" style={{ fontSize: 12 }}>
        {retrying
          ? "Retry the matching stage without rerunning completed code scans."
          : "Rebuild the component connection map without rerunning child scans."}
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

  return <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
    <div style={{ flex: "1 1 480px", minWidth: 320 }}>
      {matchingControls}
      <div className="row spread" style={{ marginBottom: 10 }}>
        <span className="subtle">{connections.length} connection{connections.length !== 1 ? "s" : ""}</span>
        <div className="row" style={{ gap: 6 }}>
          <button className={"btn secondary sm" + (view === "diagram" ? " active" : "")} onClick={() => setView("diagram")}>Diagram</button>
          <button className={"btn secondary sm" + (view === "list" ? " active" : "")} onClick={() => setView("list")}>List</button>
        </div>
      </div>
      {view === "diagram" ? <div className="connection-diagram">
        {connections.map(c => <button key={c.id} className={"connection-edge" + (c.id === selectedId ? " selected" : "")} onClick={() => setSelectedId(c.id)}>
          <span className="connection-node">{name(c.source_component_id)}</span>
          <span className="connection-arrow">→</span>
          <span className="connection-node">{name(c.target_component_id)}</span>
          <span className="badge neutral" style={{ marginLeft: 8 }}>{confidencePct(c.confidence)}</span>
        </button>)}
      </div> : <div className="table-wrap">
        <table>
          <thead><tr><th>Source</th><th>Target</th><th>Confidence</th><th>Origin</th></tr></thead>
          <tbody>
            {connections.map(c => <tr key={c.id} className={c.id === selectedId ? "row-selected" : ""} style={{ cursor: "pointer" }} onClick={() => setSelectedId(c.id)}>
              <td>{name(c.source_component_id)}</td>
              <td>{name(c.target_component_id)}</td>
              <td>{confidencePct(c.confidence)}</td>
              <td className="subtle">{ORIGIN_LABEL[c.match_kind] || c.match_kind}</td>
            </tr>)}
          </tbody>
        </table>
      </div>}
    </div>
    <div style={{ flex: "0 0 320px", minWidth: 280 }}>
      {selected ? <ConnectionDetailPanel connection={selected} sourceName={name(selected.source_component_id)} targetName={name(selected.target_component_id)} /> : <div className="subtle card" style={{ padding: 16 }}>Select a connection to see its confidence, evidence, and source facts.</div>}
    </div>
  </div>;
}

function ConnectionDetailPanel({ connection, sourceName, targetName }) {
  const evidence = safeParseJson(connection.evidence_json, {});
  const locations = value => [
    ...(value?.evidence_location ? [value.evidence_location] : []),
    ...(Array.isArray(value?.supporting_locations) ? value.supporting_locations : [])
  ];
  const renderLocations = value => locations(value).map(location =>
    <div key={location} className="mono subtle" style={{ fontSize: 12 }}>{location}</div>
  );
  return <div className="card">
    <div className="form-section-title">{sourceName} → {targetName}</div>
    <div style={{ marginTop: 8 }}><strong>Confidence:</strong> {confidencePct(connection.confidence)}</div>
    <div style={{ marginTop: 4 }}><strong>Origin:</strong> {ORIGIN_LABEL[connection.match_kind] || connection.match_kind}</div>
    {connection.rationale && <div style={{ marginTop: 8 }}><strong>Why:</strong> {connection.rationale}</div>}
    {evidence.call && <div style={{ marginTop: 8 }}>
      <strong>Outbound call ({sourceName}):</strong>
      <div className="mono subtle" style={{ fontSize: 12 }}>{evidence.call.method} {evidence.call.path}{evidence.call.host ? ` @ ${evidence.call.host}` : ""}</div>
      {renderLocations(evidence.call)}
    </div>}
    {evidence.route && <div style={{ marginTop: 8 }}>
      <strong>Matched route ({targetName}):</strong>
      <div className="mono subtle" style={{ fontSize: 12 }}>{evidence.route.method} {evidence.route.path}</div>
      {renderLocations(evidence.route)}
    </div>}
  </div>;
}
