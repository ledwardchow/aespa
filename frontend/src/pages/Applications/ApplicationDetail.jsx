import { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { ComponentsTab } from "./ComponentsTab";
import { TargetsTab } from "./TargetsTab";
import { CampaignsTab } from "./CampaignsTab";

const APP_TABS = [
  { key: "overview", label: "Overview" },
  { key: "components", label: "Code Components" },
  { key: "targets", label: "Live Targets" },
  { key: "campaigns", label: "Campaigns" }
];

// ── ApplicationDetail ────────────────────────────────────────────────────────
// Shell for the four application-management sections. Overview shows
// name/description + a quick summary; the other tabs delegate to their own
// focused components rather than one monolith holding all their state.
export function ApplicationDetail({ applicationId, initialTab }) {
  const [app, setApp] = useState(null);
  const [components, setComponents] = useState([]);
  const [error, setError] = useState(null);
  const tab = initialTab || "overview";
  // Bumped by ComponentsTab/TargetsTab (via useComponents/useTargets/useHints'
  // onChanged) after any composition-changing mutation, so Overview's counts
  // and "missing snapshot" warning refresh immediately rather than only on
  // the next tab switch. A single counter prop — not a wider prop bag.
  const [compositionVersion, setCompositionVersion] = useState(0);
  const bumpComposition = useCallback(() => setCompositionVersion(v => v + 1), []);

  const loadApp = useCallback(() => {
    api.getApplication(applicationId).then(setApp).catch(e => setError(e.message));
  }, [applicationId]);

  // Reload the application summary (counts, last campaign status) whenever
  // the id changes, the user switches tabs (so returning to Overview is
  // always fresh), or a child tab reports a composition change.
  useEffect(() => { loadApp(); }, [loadApp, tab, compositionVersion]);

  // Components are needed by both the Components tab and the Targets tab's
  // hint editor, so they are loaded once here rather than duplicated — same
  // refresh triggers as the application summary above.
  useEffect(() => {
    api.listAppComponents(applicationId).then(setComponents).catch(() => {});
  }, [applicationId, tab, compositionVersion]);

  const onDelete = async () => {
    if (!app) return;
    if (!confirm(`Delete application "${app.name}"? Its components, targets, and hints will be removed. Campaigns must be deleted first.`)) return;
    try {
      await api.deleteApplication(applicationId);
      nav("#/applications");
    } catch (e) {
      setError(e.status === 409 ? "Cannot delete — this application still has a campaign. Delete its campaigns first." : e.message);
    }
  };

  if (!app) {
    return <div className="content scroll-content">{error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}</div>;
  }

  return <>
    <PageHeader
      title={<><Crumb href="#/applications">Applications</Crumb><Sep />{app.name}</>}
      actions={<>
        <button className="btn secondary" onClick={() => nav(`#/applications/${applicationId}/edit`)}>Edit</button>
        <button className="btn" onClick={() => nav(`#/applications/${applicationId}/campaigns/new`)}>Start campaign</button>
        <button className="btn danger-outline" onClick={onDelete}>Delete</button>
      </>}
    />
    <div className="tab-bar">
      {APP_TABS.map(t => <button key={t.key} className={"tab-btn" + (tab === t.key ? " active" : "")} onClick={() => nav(`#/applications/${applicationId}/${t.key}`)}>{t.label}</button>)}
    </div>
    <div className="content scroll-content">
      {error && <div className="alert error" style={{ marginBottom: 16 }}>{error}</div>}
      {tab === "overview" && <OverviewTab app={app} components={components} />}
      {tab === "components" && <ComponentsTab applicationId={applicationId} onChanged={bumpComposition} />}
      {tab === "targets" && <TargetsTab applicationId={applicationId} components={components} onChanged={bumpComposition} />}
      {tab === "campaigns" && <CampaignsTab applicationId={applicationId} />}
    </div>
  </>;
}

function OverviewTab({ app, components }) {
  return <div>
    <div className="card" style={{ maxWidth: 640 }}>
      <div className="form-section-title">Overview</div>
      <div style={{ marginTop: 8 }}>{app.description || <span className="subtle">No description yet.</span>}</div>
      <div className="row" style={{ gap: 24, marginTop: 16, flexWrap: "wrap" }}>
        <div className="stat-card"><span>Code components</span><strong>{app.component_count}</strong></div>
        <div className="stat-card"><span>Sites</span><strong>{app.site_count}</strong></div>
        <div className="stat-card"><span>API collections</span><strong>{app.api_collection_count}</strong></div>
      </div>
      {app.component_count > 0 && components.some(c => !c.latest_snapshot) && <div className="alert" style={{ marginTop: 16 }}>
        {components.filter(c => !c.latest_snapshot).length} component(s) have no uploaded snapshot yet — upload one before starting a campaign.
      </div>}
    </div>
  </div>;
}
