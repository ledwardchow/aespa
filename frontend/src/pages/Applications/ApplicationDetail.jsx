import { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { ComponentsTab } from "./ComponentsTab";
import { TargetsTab } from "./TargetsTab";
import { CampaignsTab } from "./CampaignsTab";

const APP_TABS = [
  { key: "campaigns", label: "Campaigns" },
  { key: "components", label: "Code Components" },
  { key: "targets", label: "Live Targets" }
];

// ── ApplicationDetail ────────────────────────────────────────────────────────
// Shell for the three application-management sections. Each tab delegates to
// its own focused component rather than one monolith holding all its state.
export function ApplicationDetail({ applicationId, initialTab }) {
  const [app, setApp] = useState(null);
  const [components, setComponents] = useState([]);
  const [error, setError] = useState(null);
  const tab = APP_TABS.some(t => t.key === initialTab) ? initialTab : "campaigns";
  const [compositionVersion, setCompositionVersion] = useState(0);
  const bumpComposition = useCallback(() => setCompositionVersion(v => v + 1), []);

  const loadApp = useCallback(() => {
    api.getApplication(applicationId).then(setApp).catch(e => setError(e.message));
  }, [applicationId]);

  // Reload the application summary whenever the id changes, the user switches
  // tabs, or a child tab reports a composition change.
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
      {tab === "components" && <ComponentsTab applicationId={applicationId} onChanged={bumpComposition} />}
      {tab === "targets" && <TargetsTab applicationId={applicationId} components={components} onChanged={bumpComposition} />}
      {tab === "campaigns" && <CampaignsTab applicationId={applicationId} />}
    </div>
  </>;
}
