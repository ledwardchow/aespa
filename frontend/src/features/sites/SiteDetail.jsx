import * as sitesApi from "../../shared/api/sites.js";
import { useEffect, useState } from "react";
import { nav } from "../../shared/navigation/router.js";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import { PageError } from "../../shared/ui/Notice.jsx";
import { Breadcrumbs, PageHeader } from "../../shared/ui/PageHeader.jsx";
import { Tabs } from "../../shared/ui/Tabs.tsx";
import { SavedCrawlsPanel } from "./SavedCrawlsPanel.jsx";
import { SiteForm } from "./SiteForm.jsx";
import { SiteRunsTab } from "./SiteRunsTab.jsx";
import styles from "./SiteDetail.module.css";

const SITE_TABS = [
  { key: "runs", label: "Test runs" },
  { key: "saved-crawls", label: "Saved crawls" },
  { key: "details", label: "Site details" },
];

export function SiteDetail({ siteId, initialTab }) {
  const tab = SITE_TABS.some((item) => item.key === initialTab) ? initialTab : "runs";
  const [site, setSite] = useState(null);
  const [error, setError] = useState(null);
  // The settings form keeps unsaved edits while another tab is open.
  const [detailsOpened, setDetailsOpened] = useState(tab === "details");

  useEffect(() => {
    sitesApi
      .getSite(siteId)
      .then(setSite)
      .catch((e) => setError(e.message));
  }, [siteId]);
  useEffect(() => {
    if (tab === "details") setDetailsOpened(true);
  }, [tab]);

  const accountCount = site?.credentials.length || 0;
  return (
    <>
      <PageHeader
        titleStyle={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }}
        title={
          <>
            <Breadcrumbs items={[{ label: "Sites", href: "#/" }, { label: site?.name || "…" }]} />
            {site && (
              <div className={styles.summary}>
                <span className="mono">{site.base_url}</span>
                <span className={`badge ${site.requires_auth ? "ok" : "neutral"}`}>
                  {site.requires_auth ? "Login required" : "No login"}
                </span>
                {site.requires_auth && (
                  <span>
                    {accountCount} account{accountCount !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            )}
          </>
        }
        actions={
          <button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}>
            <IconPlus /> New test run
          </button>
        }
      />
      <Tabs
        label="Site views"
        tabs={SITE_TABS}
        value={tab}
        onChange={(key) => nav(key === "runs" ? `#/sites/${siteId}` : `#/sites/${siteId}/${key}`)}
      />
      {error && (
        <div className="content">
          <PageError error={error} inline onDismiss={() => setError(null)} />
        </div>
      )}
      {tab === "runs" && <SiteRunsTab siteId={siteId} />}
      {tab === "saved-crawls" && (
        <div className="content scroll-content stack">
          <SavedCrawlsPanel siteId={siteId} />
        </div>
      )}
      {detailsOpened && (
        <div className={styles.details} hidden={tab !== "details"}>
          <SiteForm siteId={siteId} onSaved={setSite} />
        </div>
      )}
    </>
  );
}
