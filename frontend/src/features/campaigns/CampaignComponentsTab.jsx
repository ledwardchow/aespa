import * as systemsApi from "../../shared/api/systems.js";
import { useState, useEffect } from "react";

import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { shortHash } from "../../shared/runs/campaignPresentation.js";

// ── CampaignComponentsTab ────────────────────────────────────────────────────
// The frozen snapshot/target selection this campaign was created with. Names
// are resolved against the system's current components/targets. The
// campaign only stores ids, so this reads the parent system to label
// them (the snapshot/target rows themselves are still the frozen ones).
export function CampaignComponentsTab({ systemId, campaign }) {
  const [components, setComponents] = useState(null);
  const [targets, setTargets] = useState(null);
  const [snapshotsByComponent, setSnapshotsByComponent] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([systemsApi.listSystemComponents(systemId), systemsApi.listSystemTargets(systemId)])
      .then(async ([comps, tgts]) => {
        if (cancelled) return;
        setComponents(comps);
        setTargets(tgts);
        const neededComponentIds = [...new Set(campaign.source_members.map((m) => m.component_id))];
        const histories = await Promise.all(
          neededComponentIds.map((id) =>
            systemsApi.listComponentSnapshots(systemId, id).catch(() => []),
          ),
        );
        if (cancelled) return;
        const map = {};
        neededComponentIds.forEach((id, i) => {
          map[id] = histories[i];
        });
        setSnapshotsByComponent(map);
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [systemId, campaign.source_members]);

  if (error) return <div className="alert error">{error}</div>;
  if (components === null || targets === null) return <div className="subtle">Loading…</div>;

  const componentName = (id) => (components.find((c) => c.id === id) || {}).name || `#${id}`;
  const targetName = (id) => {
    const t = targets.find((x) => x.id === id);
    return t ? t.name || `#${t.target_id}` : `#${id}`;
  };
  const snapshotFor = (m) =>
    (snapshotsByComponent[m.component_id] || []).find((s) => s.id === m.snapshot_id);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="alert warning">
        This is the frozen selection this campaign was created with. Later changes to the system's
        snapshots or targets do not change it.
      </div>
      <div>
        <div className="form-section-title">Code snapshots ({campaign.source_members.length})</div>
        <div className="app-progress-list">
          {campaign.source_members.map((m) => {
            const snap = snapshotFor(m);
            return (
              <div key={m.id} className="app-progress-row">
                <span style={{ fontWeight: 600 }}>{componentName(m.component_id)}</span>
                {snap ? (
                  <span className="mono subtle" style={{ fontSize: 12 }}>
                    {snap.filename} · SHA {shortHash(snap.sha256)}
                  </span>
                ) : (
                  <span className="subtle">snapshot #{m.snapshot_id}</span>
                )}
                <StatusBadge status={m.status} />
              </div>
            );
          })}
        </div>
      </div>
      <div>
        <div className="form-section-title">Live targets ({campaign.target_members.length})</div>
        <div className="app-progress-list">
          {campaign.target_members.map((m) => (
            <div key={m.id} className="app-progress-row">
              <span className="badge neutral">
                {m.target_type === "site" ? "Site" : "API collection"}
              </span>
              <span style={{ fontWeight: 600 }}>{targetName(m.target_id)}</span>
              <StatusBadge status={m.status} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
