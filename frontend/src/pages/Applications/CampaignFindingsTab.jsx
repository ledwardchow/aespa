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
  const [expanded, setExpanded] = useState(new Set());

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
        {rows.map(r => <FindingRows key={r.finding_id} row={r} expanded={expanded.has(r.finding_id)} onToggle={() => setExpanded(current => {
          const next = new Set(current);
          if (next.has(r.finding_id)) next.delete(r.finding_id); else next.add(r.finding_id);
          return next;
        })} runLink={runLink} componentLabel={componentLabel} />)}
      </tbody>
    </table>
  </div>;
}

function FindingRows({ row, expanded, onToggle, runLink, componentLabel }) {
  return <>
    <tr>
      <td className="subtle">{componentLabel(row)}</td>
      <td>{row.target_name || "—"}</td>
      <td><button className="btn ghost sm" onClick={onToggle}>{row.title}</button></td>
      <td><span className={"sev-badge " + severityClass(row.severity)}>{row.severity}</span></td>
      <td>{row.status}</td>
      <td><a className="btn secondary sm" href={runLink(row)}>Open run →</a></td>
    </tr>
    {expanded && <tr>
      <td colSpan="6">
        {row.frontend_attack_path && <div className="sast-evidence-callout sast-evidence-callout-info">
          <strong>Frontend reproduction</strong>
          <pre>{JSON.stringify(row.frontend_attack_path, null, 2)}</pre>
        </div>}
        {row.backend_attack_path && <div className="sast-evidence-callout">
          <strong>Backend source evidence</strong>
          <pre>{JSON.stringify(row.backend_attack_path, null, 2)}</pre>
        </div>}
        {!row.frontend_attack_path && !row.backend_attack_path && <span className="subtle">No attack-path details recorded.</span>}
      </td>
    </tr>}
  </>;
}
