import * as applicationsApi from "../../shared/api/applications.js";
import { useState, useEffect } from "react";

import { safeParseJson, confidencePct } from "../../shared/runs/campaignPresentation.js";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";

const ORIGIN_LABEL = {
  deterministic: "Direct evidence match",
  llm_assisted: "LLM-resolved match",
};

const EVIDENCE_KEY_LABELS = {
  call: "Outbound call",
  route: "Matched route",
  action: "UI action",
  handler: "Backend handler",
  source: "Source evidence",
  target: "Target evidence",
  lead_anchor: "SAST lead anchor",
};

// ── CampaignConnectionsTab ───────────────────────────────────────────────────
// A detailed connection diagram view — folds confidence, evidence, source facts,
// and origin type directly into each row.
export function CampaignConnectionsTab({
  applicationId,
  campaignId,
  campaign,
  rebuildConnections,
  busy,
}) {
  const [connections, setConnections] = useState(null);
  const [components, setComponents] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      applicationsApi.getCampaignConnections(applicationId, campaignId, "cross_component"),
      applicationsApi.listAppComponents(applicationId),
    ])
      .then(([conns, comps]) => {
        if (cancelled) return;
        setConnections(conns);
        const map = {};
        comps.forEach((c) => {
          map[c.id] = c.name;
        });
        setComponents(map);
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [applicationId, campaignId, campaign?.status, campaign?.updated_at]);

  const canRebuild = ["failed", "interrupted", "awaiting_review", "completed", "stopped"].includes(
    campaign?.status,
  );
  const retrying = campaign?.status === "failed" || campaign?.status === "interrupted";
  const rebuildLabel = retrying ? "Resume context matching" : "Re-run context matching";
  const matchingControls = (
    <div className="row spread" style={{ marginBottom: 14, gap: 10, flexWrap: "wrap" }}>
      <div>
        <div className="form-section-title">Context matching</div>
        <div className="subtle" style={{ fontSize: 12 }}>
          Trace data flows by discovering API calls between components.
        </div>
      </div>
      {canRebuild && (
        <button className="btn secondary sm" disabled={busy} onClick={rebuildConnections}>
          {busy ? "Matching context…" : rebuildLabel}
        </button>
      )}
    </div>
  );

  if (error)
    return (
      <>
        {matchingControls}
        <div className="alert error">{error}</div>
      </>
    );
  if (connections === null)
    return (
      <>
        {matchingControls}
        <div className="subtle">Loading…</div>
      </>
    );

  const name = (id) => components[id] || `#${id}`;

  if (connections.length === 0)
    return (
      <>
        {matchingControls}
        <EmptyState
          title="No connections found"
          sub={
            campaign?.status === "failed" || campaign?.status === "interrupted"
              ? "Connection mapping did not complete. Resume context matching to retry it without rerunning completed code scans."
              : "No evidence-backed cross-component connection has been resolved yet. Review campaign activity to see whether mapping is still running or needs attention."
          }
        />
      </>
    );

  return (
    <div>
      {matchingControls}
      <div className="row spread" style={{ marginBottom: 12 }}>
        <span className="subtle">
          {connections.length} connection{connections.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="connection-diagram">
        {connections.map((c) => (
          <ConnectionCard
            key={c.id}
            connection={c}
            sourceName={name(c.source_component_id)}
            targetName={name(c.target_component_id)}
          />
        ))}
      </div>
    </div>
  );
}

function ConnectionCard({ connection, sourceName, targetName }) {
  const evidence = safeParseJson(connection.evidence_json, {});
  const locations = (value) => [
    ...(value?.evidence_location ? [value.evidence_location] : []),
    ...(Array.isArray(value?.supporting_locations) ? value.supporting_locations : []),
  ];
  const renderLocations = (value) =>
    locations(value).map((location) => (
      <div key={location} className="mono subtle" style={{ fontSize: 12 }}>
        {location}
      </div>
    ));

  const evidenceEntries = Object.entries(evidence).filter(
    ([_, value]) =>
      value &&
      (value.evidence_location ||
        (Array.isArray(value.supporting_locations) && value.supporting_locations.length > 0) ||
        value.method ||
        value.path),
  );

  return (
    <div className="connection-card">
      <div className="connection-card-header">
        <div className="connection-flow">
          <span className="connection-node">{sourceName}</span>
          <span className="connection-arrow">→</span>
          <span className="connection-node">{targetName}</span>
        </div>
        <div className="connection-badges">
          <span className="badge neutral">{confidencePct(connection.confidence)}</span>
          <span className="badge neutral" style={{ marginLeft: 6 }}>
            {connection.edge_kind || "calls"}
          </span>
          <span className="badge info" style={{ marginLeft: 6 }}>
            {ORIGIN_LABEL[connection.match_kind] || connection.match_kind}
          </span>
        </div>
      </div>

      {(connection.rationale || evidenceEntries.length > 0) && (
        <div className="connection-card-body">
          {connection.rationale && (
            <div className="connection-rationale">
              <strong>Why:</strong> {connection.rationale}
            </div>
          )}
          {evidenceEntries.length > 0 && (
            <div className="connection-evidence-grid">
              {evidenceEntries.map(([key, item]) => {
                const defaultLabel = EVIDENCE_KEY_LABELS[key] || key;
                const componentOwner =
                  key === "call" || key === "source" || key === "action" ? sourceName : targetName;
                const label = `${defaultLabel} (${componentOwner})`;
                return (
                  <div key={key} className="connection-evidence-item">
                    <span className="evidence-label">{label}</span>
                    {(item.method || item.path) && (
                      <div className="mono subtle" style={{ fontSize: 12, marginTop: 2 }}>
                        <strong>{item.method}</strong> {item.path}
                        {item.host ? ` @ ${item.host}` : ""}
                      </div>
                    )}
                    {renderLocations(item)}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
