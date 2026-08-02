import { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";
import { EmptyState } from "../../components/EmptyState";
import { severityClass } from "./_helpers";

// ── CampaignFindingsTab ──────────────────────────────────────────────────────
// One combined table across every child run's findings, with Component and
// Live target columns plus a deep link back to the child run that owns the
// finding. Never creates a second finding copy or its own status lifecycle —
// this only reads GET .../campaigns/{id}/findings.
export function CampaignFindingsTab({ applicationId, campaignId }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api.getCampaignFindings(applicationId, campaignId).then(setRows).catch(e => setError(e.message));
  }, [applicationId, campaignId]);

  useEffect(() => { load(); }, [load]);

  if (error) return <div className="alert error">{error}</div>;
  if (rows === null) return <div className="subtle">Loading…</div>;
  if (rows.length === 0) return <EmptyState title="No findings yet" sub="Findings from every live-target run this campaign started will appear here as they are recorded." />;

  const runLink = r => r.target_type === "site" ? `#/runs/${r.target_run_id}/findings` : `#/api-runs/${r.target_run_id}/findings`;
  const componentLabel = r => (r.component_names && r.component_names.length > 0) ? r.component_names.join(", ") : (r.component_name || "—");

  return <div className="table-wrap">
    <table>
      <thead><tr><th>Component</th><th>Live target</th><th>Title</th><th>Severity</th><th>Status</th><th></th></tr></thead>
      <tbody>
        {rows.map(r => <tr key={r.finding_id}>
          <td className="subtle">{componentLabel(r)}</td>
          <td>{r.target_name || "—"}</td>
          <td>{r.title}</td>
          <td><span className={"sev-badge " + severityClass(r.severity)}>{r.severity}</span></td>
          <td>{r.status}</td>
          <td><a className="btn secondary sm" href={runLink(r)}>Open run →</a></td>
        </tr>)}
      </tbody>
    </table>
  </div>;
}
