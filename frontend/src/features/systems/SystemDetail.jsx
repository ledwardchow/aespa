import * as systemsApi from "../../shared/api/systems.js";
import { useState, useEffect, useCallback } from "react";

import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";
import { ComponentsTab } from "./ComponentsTab.jsx";
import { TargetsTab } from "./TargetsTab.jsx";
import { CampaignsTab } from "../campaigns/public.js";

const APP_TABS = [
  { key: "campaigns", label: "Campaigns" },
  { key: "components", label: "Code Components" },
  { key: "targets", label: "Live Targets" },
];

// ── SystemDetail ────────────────────────────────────────────────────────
// Shell for the three system-management sections. Each tab delegates to
// its own focused component rather than one monolith holding all its state.
export function SystemDetail({ systemId, initialTab }) {
  const [app, setApp] = useState(null);
  const [components, setComponents] = useState([]);
  const [error, setError] = useState(null);
  const tab = APP_TABS.some((t) => t.key === initialTab) ? initialTab : "campaigns";
  const [compositionVersion, setCompositionVersion] = useState(0);
  const bumpComposition = useCallback(() => setCompositionVersion((v) => v + 1), []);

  const loadApp = useCallback(() => {
    systemsApi
      .getSystem(systemId)
      .then(setApp)
      .catch((e) => setError(e.message));
  }, [systemId]);

  // Reload the system summary whenever the id changes, the user switches
  // tabs, or a child tab reports a composition change.
  useEffect(() => {
    loadApp();
  }, [loadApp, tab, compositionVersion]);

  // Components are needed by both the Components tab and the Targets tab's
  // hint editor, so they are loaded once here rather than duplicated — same
  // refresh triggers as the system summary above.
  useEffect(() => {
    systemsApi
      .listSystemComponents(systemId)
      .then(setComponents)
      .catch(() => {});
  }, [systemId, tab, compositionVersion]);

  const onDelete = async () => {
    if (!app) return;
    if (
      !confirm(
        `Delete system "${app.name}"? Its components, targets, and hints will be removed. Campaigns must be deleted first.`,
      )
    )
      return;
    try {
      await systemsApi.deleteSystem(systemId);
      nav("#/systems");
    } catch (e) {
      setError(
        e.status === 409
          ? "Cannot delete — this system still has a campaign. Delete its campaigns first."
          : e.message,
      );
    }
  };

  if (!app) {
    return (
      <div className="content scroll-content">
        {error ? (
          <div className="alert error">{error}</div>
        ) : (
          <div className="subtle">Loading…</div>
        )}
      </div>
    );
  }

  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/systems">Systems</Crumb>
            <Sep />
            {app.name}
          </>
        }
        actions={
          <>
            <button className="btn secondary" onClick={() => nav(`#/systems/${systemId}/edit`)}>
              Edit
            </button>
            <button className="btn" onClick={() => nav(`#/systems/${systemId}/campaigns/new`)}>
              Start campaign
            </button>
            <button className="btn danger-outline" onClick={onDelete}>
              Delete
            </button>
          </>
        }
      />
      <div className="tab-bar">
        {APP_TABS.map((t) => (
          <button
            key={t.key}
            className={"tab-btn" + (tab === t.key ? " active" : "")}
            onClick={() => nav(`#/systems/${systemId}/${t.key}`)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="content scroll-content">
        {error && (
          <div className="alert error" style={{ marginBottom: 16 }}>
            {error}
          </div>
        )}
        {tab === "components" && <ComponentsTab systemId={systemId} onChanged={bumpComposition} />}
        {tab === "targets" && (
          <TargetsTab systemId={systemId} components={components} onChanged={bumpComposition} />
        )}
        {tab === "campaigns" && <CampaignsTab systemId={systemId} />}
      </div>
    </>
  );
}
