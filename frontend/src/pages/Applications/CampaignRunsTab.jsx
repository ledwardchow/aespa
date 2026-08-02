import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";

// ── CampaignRunsTab ──────────────────────────────────────────────────────────
// Every child SAST/web/API run this campaign created, with a deep link to its
// existing detail route. No local state lifecycle is duplicated here — the
// campaign record (already loaded by the shell) is the only source of truth;
// this only additionally resolves component/target names for readability.
export function CampaignRunsTab({ applicationId, campaign }) {
  const [componentNames, setComponentNames] = useState({});
  const [targetNames, setTargetNames] = useState({});

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listAppComponents(applicationId), api.listAppTargets(applicationId)]).then(([comps, tgts]) => {
      if (cancelled) return;
      const cMap = {}; comps.forEach(c => { cMap[c.id] = c.name; });
      const tMap = {}; tgts.forEach(t => { tMap[t.id] = t.name || `#${t.target_id}`; });
      setComponentNames(cMap);
      setTargetNames(tMap);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [applicationId]);

  const sourceRuns = campaign.source_members.filter(m => m.sast_run_id);
  const targetRuns = campaign.target_members.filter(m => m.test_run_id || m.api_test_run_id);

  return <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
    <div>
      <div className="form-section-title">Code scans (SAST)</div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Component</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {sourceRuns.map(m => <tr key={m.id}>
              <td>{componentNames[m.component_id] || `Component #${m.component_id}`}</td>
              <td><StatusBadge status={m.status} /></td>
              <td><a className="btn secondary sm" href={`#/sast-runs/${m.sast_run_id}/progress`}>Open →</a></td>
            </tr>)}
            {sourceRuns.length === 0 && <tr><td colSpan={3} className="subtle">No SAST runs created yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
    <div>
      <div className="form-section-title">Live target scans</div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Target</th><th>Type</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {targetRuns.map(m => <tr key={m.id}>
              <td>{targetNames[m.target_id] || `#${m.target_id}`}</td>
              <td>{m.target_type === "site" ? "Web" : "API"}</td>
              <td><StatusBadge status={m.status} /></td>
              <td>
                {m.test_run_id && <a className="btn secondary sm" href={`#/runs/${m.test_run_id}/status`}>Open web run →</a>}
                {m.api_test_run_id && <a className="btn secondary sm" href={`#/api-runs/${m.api_test_run_id}/status`}>Open API run →</a>}
              </td>
            </tr>)}
            {targetRuns.length === 0 && <tr><td colSpan={4} className="subtle">No live target runs created yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  </div>;
}
