import { useMemo, useState } from "react";
import { truncUrl } from "../../lib/utilities";

const STATUS_LABELS = {
  not_started: "Not started",
  in_progress: "In progress",
  covered: "Covered",
  finding: "Finding",
  skipped: "Skipped"
};

function Section({ id, title, detail, expanded, onToggle, children }) {
  return <div className="attack-surface-section">
    <button type="button" className="attack-surface-section-head" onClick={() => onToggle(id)}>
      <span className="attack-surface-toggle">{expanded ? "▾" : "▸"}</span>
      <span className="attack-surface-section-title">{title}</span>
      {detail ? <span className="subtle">{detail}</span> : null}
    </button>
    {expanded ? <div className="attack-surface-body">{children}</div> : null}
  </div>;
}

function CoverageBadges({ statuses = {} }) {
  return <div className="surface-statuses">
    {Object.entries(STATUS_LABELS).map(([status, label]) => statuses[status] ?
      <span key={status} className={`surface-status status-${status}`}>{label} {statuses[status]}</span> : null)}
  </div>;
}

export function AttackSurfacePanel({ summary }) {
  const [expanded, setExpanded] = useState({ coverage: true, routes: true, access: false, signals: true, meta: false });
  const [query, setQuery] = useState("");
  const [accessFilter, setAccessFilter] = useState("all");
  const toggle = key => setExpanded(previous => ({ ...previous, [key]: !previous[key] }));

  const routes = useMemo(() => summary?.routes || [], [summary]);
  const filteredRoutes = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return routes.filter(route => {
      if (accessFilter !== "all" && route.access?.classification !== accessFilter) return false;
      if (!needle) return true;
      return [route.canonical_url, ...(route.parameters || []), ...(route.sources || [])]
        .some(value => String(value).toLowerCase().includes(needle));
    });
  }, [accessFilter, query, routes]);

  if (!summary) {
    return <div className="attack-surface-empty">
      <span className="subtle">No attack surface is available yet. Complete or import a crawl first.</span>
    </div>;
  }

  const coverage = summary.coverage || {};
  const inputs = summary.input_surface || {};
  const access = summary.access || {};
  const signals = summary.signals || { items: [] };
  const technologies = summary.technologies || [];
  const shownRoutes = filteredRoutes.slice(0, 100);

  return <div className="attack-surface-panel">
    <div className="surface-summary-grid">
      <div className="surface-summary-card"><strong>{summary.route_count || routes.length}</strong><span>Canonical routes</span></div>
      <div className="surface-summary-card"><strong>{inputs.routes || 0}</strong><span>Input routes</span></div>
      <div className="surface-summary-card"><strong>{inputs.parameters || 0}</strong><span>Parameters</span></div>
      <div className="surface-summary-card"><strong>{coverage.completion_percent || 0}%</strong><span>Coverage resolved</span></div>
    </div>

    <Section id="coverage" title="Coverage Gaps" detail={coverage.seeded ? `${coverage.resolved || 0} of ${coverage.total || 0} cells resolved` : "Workprogram not seeded"} expanded={expanded.coverage} onToggle={toggle}>
      <CoverageBadges statuses={coverage.statuses} />
      {(coverage.by_category || []).length ? <div className="surface-coverage-list">
        {coverage.by_category.map(item => {
          const resolved = item.total - item.remaining;
          const percent = item.total ? Math.round(100 * resolved / item.total) : 0;
          return <div key={item.category} className="surface-coverage-row">
            <span className="owasp-badge">{item.category}</span>
            <span className="surface-coverage-name">{item.label}</span>
            <span className="surface-progress"><span style={{ width: `${percent}%` }} /></span>
            <span className="surface-coverage-count">{item.remaining} remaining</span>
            {item.gap_route_total > 0 ? <span className="subtle">{item.gap_route_total} routes</span> : null}
          </div>;
        })}
      </div> : <div className="subtle">Coverage appears here after the OWASP workprogram is seeded.</div>}
    </Section>

    <Section id="routes" title="Route & Input Inventory" detail={`${filteredRoutes.length} of ${routes.length} routes`} expanded={expanded.routes} onToggle={toggle}>
      <div className="surface-filters">
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Filter route, parameter, or source…" />
        <select value={accessFilter} onChange={event => setAccessFilter(event.target.value)}>
          <option value="all">All access</option>
          <option value="anonymous">Anonymous</option>
          <option value="authenticated">Authenticated</option>
          <option value="mixed">Mixed access</option>
          <option value="unknown">Unknown access</option>
        </select>
      </div>
      <div className="surface-route-table-wrap">
        <table className="surface-route-table">
          <thead><tr><th>Methods</th><th>Canonical route</th><th>Access evidence</th><th>Inputs</th><th>Coverage</th><th>Provenance</th></tr></thead>
          <tbody>{shownRoutes.map(route => <tr key={route.canonical_url}>
            <td>{(route.methods || []).map(method => <span key={method} className="method-badge">{method}</span>)}</td>
            <td><span className="mono surface-route-url" title={route.canonical_url}>{truncUrl(route.canonical_url, 76)}</span>
              {(route.example_urls || []).length > 1 ? <span className="subtle surface-route-note">{route.example_urls.length} observed examples</span> : null}</td>
            <td><span className={`surface-access access-${route.access?.classification || "unknown"}`}>{route.access?.classification || "unknown"}</span>
              {(route.access?.labels || []).length ? <span className="subtle surface-route-note">{route.access.labels.join(", ")}</span> : null}</td>
            <td><div className="surface-chip-list">{(route.parameters || []).slice(0, 5).map(parameter => <span key={parameter} className="surface-chip mono">{parameter}</span>)}
              {(route.parameters || []).length > 5 ? <span className="subtle">+{route.parameters.length - 5}</span> : null}</div></td>
            <td>{route.coverage?.total ? <CoverageBadges statuses={route.coverage.statuses} /> : <span className="subtle">Not applicable</span>}</td>
            <td><div className="surface-chip-list">{(route.sources || []).slice(0, 3).map(source => <span key={source} className="surface-chip">{source.replace(/_/g, " ")}</span>)}</div></td>
          </tr>)}</tbody>
        </table>
      </div>
      {filteredRoutes.length > shownRoutes.length ? <div className="subtle">Showing the first 100 of {filteredRoutes.length} matching routes. Refine the filter to narrow the inventory.</div> : null}
    </Section>

    <Section id="signals" title="Evidence-backed Signals" detail={`${signals.shown || 0} of ${signals.total || 0} shown`} expanded={expanded.signals} onToggle={toggle}>
      {(signals.items || []).length ? <div className="surface-signal-grid">{signals.items.map((signal, index) =>
        <div className="surface-signal" key={`${signal.type}-${signal.url}-${signal.label}-${index}`}>
          <div><span className="surface-signal-type">{signal.type.replace(/_/g, " ")}</span><strong>{signal.label}</strong><span className="subtle">{Math.round((signal.confidence || 0) * 100)}% · {signal.source.replace(/_/g, " ")}{signal.observations > 1 ? ` · ${signal.observations} observations` : ""}</span></div>
          <span className="mono" title={signal.url}>{truncUrl(signal.url, 80)}</span>
          <span className="surface-signal-evidence">{signal.evidence}</span>
        </div>)}</div> : <div className="subtle">No high-value evidence signals have been observed.</div>}
    </Section>

    <Section id="access" title="Access Observations" detail={`${(access.profiles || []).length} credential profiles`} expanded={expanded.access} onToggle={toggle}>
      <div className="surface-access-counts">{Object.entries(access.counts || {}).map(([classification, count]) =>
        <span key={classification} className={`surface-access access-${classification}`}>{classification}: {count}</span>)}</div>
      {(access.profiles || []).length ? <div className="surface-profile-list">{access.profiles.map((profile, index) =>
        <span key={`${profile.credential_id}-${profile.username}-${index}`} className="surface-chip">{profile.label}{profile.username && profile.label !== profile.username ? ` (${profile.username})` : ""}</span>)}</div> : null}
      {(access.mixed_routes || []).length ? <div className="surface-callout">{access.mixed_routes.length} routes were observed in both anonymous and authenticated contexts. This is evidence to investigate, not an automatic vulnerability classification.</div> : null}
    </Section>

    <Section id="meta" title="Observed Technologies" detail={`${technologies.length} detected`} expanded={expanded.meta} onToggle={toggle}>
      <div className="surface-profile-list">{technologies.map(item => <span key={item.name} className="surface-chip">{item.name} <span className="subtle">via {item.source}</span></span>)}</div>
    </Section>
  </div>;
}
