import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import { EmptyState } from "../../components/EmptyState";
import { FindingReferenceLink } from "../../components/FindingReferenceLink";
import { useColResize } from "../SiteDetail/_helpers";
import { severityClass } from "./_helpers";

function TextBlock({ label, value, code = false }) {
  if (!value) return null;
  return <div className="finding-detail-block">
    <strong>{label}</strong>
    {code ? <pre className="finding-evidence">{value}</pre> : <div className="finding-detail-text">{value}</div>}
  </div>;
}

function PathBlock({ label, value }) {
  if (!value || typeof value !== "object" || !Object.keys(value).length) return null;
  return <TextBlock label={label} value={JSON.stringify(value, null, 2)} code />;
}

function FindingDetail({ row }) {
  return <div className="campaign-finding-detail">
    <div className="campaign-finding-detail-grid">
      <TextBlock label="Description" value={row.description} />
      <TextBlock label="Impact" value={row.impact} />
      <TextBlock label="Likelihood" value={row.likelihood} />
      <TextBlock label="Recommendation" value={row.recommendation} />
    </div>
    <div className="campaign-finding-meta-line">
      <span><strong>CVSS:</strong> {row.cvss_score != null ? Number(row.cvss_score).toFixed(1) : "—"}</span>
      {row.cvss_vector && <code>{row.cvss_vector}</code>}
      {row.affected_url && <span><strong>URL:</strong> {row.affected_url}</span>}
      {row.finding_source && <span><strong>Source:</strong> {row.finding_source}</span>}
      {row.origin?.label && <span><strong>Origin:</strong> {row.origin.label}{row.origin.reference ? ` · ${row.origin.reference}` : ""}</span>}
      {row.validated_by?.label && <span><strong>Validated by:</strong> {row.validated_by.label}</span>}
    </div>
    {row.validation_note && <div className="finding-validation-note"><strong>Validation ({row.status}):</strong> {row.validation_note}</div>}
    <TextBlock label="Evidence" value={row.evidence} code />
    <TextBlock label="Request" value={row.request_evidence} code />
    <TextBlock label="Response" value={row.response_evidence} code />
    {row.evidence_items?.length > 0 && <TextBlock label="Structured evidence" value={JSON.stringify(row.evidence_items, null, 2)} code />}
    <TextBlock label="Verified proof of concept" value={row.poc_command} code />
    <TextBlock label="Proof-of-concept setup" value={row.poc_setup} />
    <TextBlock label="Merged instances" value={row.merged_instances !== "[]" ? row.merged_instances : ""} code />
    <PathBlock label="Frontend attack path" value={row.frontend_attack_path} />
    <PathBlock label="Backend attack path" value={row.backend_attack_path} />
  </div>;
}

export function CampaignFindingsTab({ applicationId, campaignId, initialFindingRef }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const [columnWidths, startColumnResize] = useColResize("colw:campaign-findings:v2", [104, 150, 180, 330, 96, 120, 110]);

  const load = useCallback(() => {
    api.getCampaignFindings(applicationId, campaignId)
      .then(data => {
        setRows(data);
        if (initialFindingRef) {
          const match = data.find(row => row.reference === initialFindingRef);
          if (match) setExpanded(previous => new Set(previous).add(match.reference));
        }
      })
      .catch(e => setError(e.message));
  }, [applicationId, campaignId, initialFindingRef]);

  useEffect(() => { load(); }, [load]);

  const groups = useMemo(() => {
    if (!rows) return [];
    const grouped = new Map();
    for (const row of rows) {
      const key = `${row.title}::${row.target_type}::${row.target_name || row.target_run_id}`;
      const current = grouped.get(key) || { key, title: row.title, target: row.target_name, items: [] };
      current.items.push(row);
      grouped.set(key, current);
    }
    return [...grouped.values()].sort((a, b) => (a.items[0].severity || "").localeCompare(b.items[0].severity || ""));
  }, [rows]);

  if (error) return <div className="alert error">{error}</div>;
  if (rows === null) return <div className="subtle">Loading…</div>;
  if (rows.length === 0) return <EmptyState title="No findings yet" sub="Findings from every live-target run this campaign started will appear here as they are recorded." />;

  const toggle = key => setExpanded(previous => {
    const next = new Set(previous);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  });

  const columns = [
    { label: "Reference", className: "campaign-reference-col" },
    { label: "Component" },
    { label: "Live target" },
    { label: "Title" },
    { label: "Severity" },
    { label: "Status", className: "campaign-status-col" },
    { label: "" },
  ];

  return <div className="campaign-findings-view">
      <div className="table-wrap">
      <table className="campaign-findings-table">
        <colgroup>{columns.map((column, index) => <col key={column.label || "actions"} className={column.className} style={{ width: columnWidths[index] == null ? undefined : `${columnWidths[index]}px` }} />)}</colgroup>
        <thead><tr>{columns.map((column, index) => <th key={column.label || "actions"}>{column.label}<span className="col-rh" role="separator" aria-label={`Resize ${column.label || "actions"} column`} onMouseDown={event => startColumnResize(index, event)} /></th>)}</tr></thead>
        <tbody>{groups.map(group => <>
          <tr key={group.key} className="finding-group-row" onClick={() => toggle(group.key)}>
            <td className="campaign-finding-reference-cell">
              <span className="group-chevron">{expanded.has(group.key) ? "▾" : "▸"}</span>{" "}
              <FindingReferenceLink reference={group.items[0].reference} title={group.title} description={group.items[0].description} severity={group.items[0].severity} validation_status={group.items[0].status} href={`#/applications/${applicationId}/campaigns/${campaignId}/findings?finding=${encodeURIComponent(group.items[0].reference || "")}`} />
            </td>
            <td className="subtle">{group.items[0].component_name || "—"}</td>
            <td>{group.target || "—"}</td>
            <td className="finding-title">{group.title} <span className="finding-count-badge">{group.items.length}</span></td>
            <td><span className={`sev-badge ${severityClass(group.items[0].severity)}`}>{group.items[0].severity}</span></td>
            <td>{group.items[0].status}</td>
            <td><button className="btn ghost sm" onClick={event => { event.stopPropagation(); toggle(group.key); }}>{expanded.has(group.key) ? "Collapse" : "Details"}</button></td>
          </tr>
          {expanded.has(group.key) && group.items.map(row => <tr key={row.reference} className="finding-evidence-row">
            <td colSpan="7"><div className="campaign-finding-instance-heading">
              <span className="subtle campaign-finding-run-reference">Run {row.run_reference || "—"}</span>
              <span>{row.target_name || "—"}</span>
              <a className="btn secondary sm" href={row.target_type === "site"
                ? `#/runs/${row.target_run_id}/findings?finding=${encodeURIComponent(row.run_reference || "")}`
                : `#/api-runs/${row.target_run_id}/findings?finding=${encodeURIComponent(row.run_reference || "")}`}>Open Run →</a>
            </div><FindingDetail row={row} /></td>
          </tr>)}
        </>)}</tbody>
      </table>
    </div>
  </div>;
}
