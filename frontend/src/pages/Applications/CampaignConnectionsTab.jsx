import { useState, useEffect, useMemo } from "react";
import { api } from "../../lib/api";
import { safeParseJson, confidencePct } from "./_helpers";
import { EmptyState } from "../../components/EmptyState";

const ORIGIN_LABEL = {
  deterministic: "Direct evidence match",
  llm_assisted: "LLM-assisted match"
};

// ── CampaignConnectionsTab ───────────────────────────────────────────────────
// A simple left-to-right diagram (default) plus an accessible list view —
// selecting a connection (in either view) opens a side panel with its
// confidence, evidence, source facts, and origin type. Handles zero
// connections and large sets without extra dependencies.
export function CampaignConnectionsTab({ applicationId, campaignId }) {
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
  }, [applicationId, campaignId]);

  const selected = useMemo(() => (connections || []).find(c => c.id === selectedId) || null, [connections, selectedId]);

  if (error) return <div className="alert error">{error}</div>;
  if (connections === null) return <div className="subtle">Loading…</div>;
  if (connections.length === 0) return <EmptyState
    title="No connections found"
    sub="Connections appear once the campaign's code scans finish and context matching runs. A component with no outbound calls, or no well-evidenced match, produces none — that's expected, not an error." />;

  const name = id => components[id] || `#${id}`;

  return <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
    <div style={{ flex: "1 1 480px", minWidth: 320 }}>
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
  return <div className="card">
    <div className="form-section-title">{sourceName} → {targetName}</div>
    <div style={{ marginTop: 8 }}><strong>Confidence:</strong> {confidencePct(connection.confidence)}</div>
    <div style={{ marginTop: 4 }}><strong>Origin:</strong> {ORIGIN_LABEL[connection.match_kind] || connection.match_kind}</div>
    {connection.rationale && <div style={{ marginTop: 8 }}><strong>Why:</strong> {connection.rationale}</div>}
    {evidence.call && <div style={{ marginTop: 8 }}>
      <strong>Outbound call ({sourceName}):</strong>
      <div className="mono subtle" style={{ fontSize: 12 }}>{evidence.call.method} {evidence.call.path}{evidence.call.host ? ` @ ${evidence.call.host}` : ""}</div>
    </div>}
    {evidence.route && <div style={{ marginTop: 8 }}>
      <strong>Matched route ({targetName}):</strong>
      <div className="mono subtle" style={{ fontSize: 12 }}>{evidence.route.method} {evidence.route.path}</div>
    </div>}
  </div>;
}
