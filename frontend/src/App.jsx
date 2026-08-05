import { SitesList } from "./pages/SitesList";
import React, { useEffect, useState } from "react";

// ── API client ────────────────────────────────────────────────────────────────

import { api } from "./lib/api";
import { useRoute } from "./lib/router";
import { IconSites, IconApis, IconSettings, IconPlay, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconChart, IconApplications } from "./components/Icons";

const lazyNamed = (loader, name) => React.lazy(() => loader().then(module => ({
  default: module[name]
})));
const loadApiPages = () => import("./pages/ApiCollections");
const loadSastPages = () => import("./pages/SastRuns");
const loadSitePages = () => import("./pages/SiteDetail");
const loadSettingsPages = () => import("./pages/Settings");
const loadApplicationsPages = () => import("./pages/Applications");

const ApiCollectionsList = lazyNamed(loadApiPages, "ApiCollectionsList");
const ApiCollectionForm = lazyNamed(loadApiPages, "ApiCollectionForm");
const ApiCollectionDetail = lazyNamed(loadApiPages, "ApiCollectionDetail");
const ApiFilesManager = lazyNamed(loadApiPages, "ApiFilesManager");
const ApiTestRunForm = lazyNamed(loadApiPages, "ApiTestRunForm");
const ApiTestRunDetail = lazyNamed(loadApiPages, "ApiTestRunDetail");
const SastRunsListPage = lazyNamed(loadSastPages, "SastRunsListPage");
const SastRunDetail = lazyNamed(loadSastPages, "SastRunDetail");
const SastRunForm = lazyNamed(loadSastPages, "SastRunForm");
const SiteDetail = lazyNamed(loadSitePages, "SiteDetail");
const SiteForm = lazyNamed(loadSitePages, "SiteForm");
const TestRunDetail = lazyNamed(loadSitePages, "TestRunDetail");
const TestRunForm = lazyNamed(loadSitePages, "TestRunForm");
const AliceChatPopout = lazyNamed(loadSitePages, "AliceChatPopout");
const SettingsPage = lazyNamed(loadSettingsPages, "SettingsPage");
const ScanPolicyPage = lazyNamed(loadSettingsPages, "ScanPolicyPage");
const ExternalIntegrationsPage = lazyNamed(loadSettingsPages, "ExternalIntegrationsPage");
const DebugPage = lazyNamed(loadSettingsPages, "DebugPage");
const ReportingDebugPage = lazyNamed(loadSettingsPages, "ReportingDebugPage");
const ActiveJobsPage = lazyNamed(() => import("./pages/ActiveJobs"), "ActiveJobsPage");
const StatisticsPage = lazyNamed(() => import("./pages/Statistics"), "StatisticsPage");
const ApplicationsList = lazyNamed(loadApplicationsPages, "ApplicationsList");
const ApplicationForm = lazyNamed(loadApplicationsPages, "ApplicationForm");
const ApplicationDetail = lazyNamed(loadApplicationsPages, "ApplicationDetail");
const CampaignNewForm = lazyNamed(loadApplicationsPages, "CampaignNewForm");
const CampaignDetail = lazyNamed(loadApplicationsPages, "CampaignDetail");

// ── Shell ──────────────────────────────────────────────────────────────────────

function App() {
  const route = useRoute();
  const onSites = ["list", "site-new", "site-edit", "site-detail", "run-new", "run-detail"].includes(route.name);
  const onApis = ["api-list", "api-new", "api-edit", "api-detail", "api-files"].includes(route.name);
  const onApplications = ["app-list", "app-new", "app-edit", "app-detail", "campaign-new", "campaign-detail"].includes(route.name);
  const onActiveJobs = route.name === "active-jobs";
  const onSettings = route.name === "settings";
  const onScanPolicy = route.name === "scan-policy";
  const onExternalIntegrations = route.name === "external-integrations";
  const onSast = ["sast-list", "sast-run-detail", "sast-run-new"].includes(route.name);
  const onDebug = route.name === "debug";
  const onReportingDebug = route.name === "reporting-debug";
  const onStats = route.name === "stats";
  const [appVersion, setAppVersion] = useState("");
  const [username, setUsername] = useState("");
  const [showUsername, setShowUsername] = useState(() => {
    try {
      const val = localStorage.getItem("aespa_show_username");
      return val === null ? true : val === "true";
    } catch  {
      return true;
    }
  });
  const [showApplications, setShowApplications] = useState(() => {
    try {
      return localStorage.getItem("aespa_show_applications") === "true";
    } catch {
      return false;
    }
  });
  const [collapsed, setCollapsed] = useState(() => window.innerWidth <= 700);
  useEffect(() => {
    const onResize = () => { if (window.innerWidth <= 700) setCollapsed(true); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  const [reportingDebugCfg, setReportingDebugCfg] = useState(null);
  useEffect(() => {
    api.getVersion().then(d => {
      setAppVersion(d.version);
      setUsername(d.username || "");
    }).catch(() => {});
    api.getReportingDebugConfig().then(setReportingDebugCfg).catch(() => {});
  }, []);
  if (route.name === "alice-popout") {
    return <React.Suspense fallback={<div className="alice-popout-page"><div className="subtle">Loading A.L.I.C.E.…</div></div>}>
      <AliceChatPopout runId={route.id} />
    </React.Suspense>;
  }
  return <div className={"shell" + (collapsed ? " sidebar-collapsed" : "")}>
      <aside className={"sidebar" + (collapsed ? " sidebar--collapsed" : "")}>
        <div className="sidebar-brand">
          <div className="logo">
            {!collapsed && <div className="logo-codename"><span>CODE</span><span>NAME</span></div>}
            <img src="/icon-sm.png" className="logo-icon" alt="AESPA" />
            {!collapsed && <span className="logo-text">ESPA</span>}
          </div>
          {!collapsed && <div className="logo-sub">AI-Enabled Security Pentesting Agent</div>}
          {!collapsed && <a className="logo-link" href="https://github.com/ledwardchow/aespa" target="_blank" rel="noopener noreferrer">github.com/ledwardchow/aespa</a>}
        </div>
        <div className="sidebar-meta">
          <button className="sidebar-toggle" onClick={() => setCollapsed(c => !c)} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <IconChevronRight /> : <IconChevronLeft />}
          </button>
          {!collapsed && <div style={{
          display: "flex",
          flexDirection: "column",
          gap: "2px",
          overflow: "hidden",
          minWidth: 0,
          lineHeight: 1.2
        }}>
              {showUsername && username ? <>
                <span className="sidebar-username" style={{
              color: "var(--text-2)",
              fontWeight: "500",
              fontSize: "11px",
              textOverflow: "ellipsis",
              overflow: "hidden",
              whiteSpace: "nowrap"
            }} title={username}>
                  {username}
                </span>
                {appVersion && <span style={{
              color: "var(--muted)",
              fontSize: "9.5px"
            }}>v{appVersion}</span>}
              </> : <>
                {appVersion && <span>v{appVersion}</span>}
              </>}
            </div>}
        </div>
        <nav className="sidebar-nav">
          {!collapsed && <div className="nav-section-label">Targets</div>}
          {showApplications && (
            <a href="#/applications" className={"nav-item" + (onApplications ? " active" : "")} title="Applications">
              <span className="nav-icon"><IconApplications /></span>{!collapsed && " Applications"}
            </a>
          )}
          <a href="#/" className={"nav-item" + (onSites ? " active" : "")} title="Sites">
            <span className="nav-icon"><IconSites /></span>{!collapsed && " Sites"}
          </a>
          <a href="#/apis" className={"nav-item" + (onApis ? " active" : "")} title="APIs">
            <span className="nav-icon"><IconApis /></span>{!collapsed && " APIs"}
          </a>
          <a href="#/sast-runs" className={"nav-item" + (onSast ? " active" : "")} title="SAST">
            <span className="nav-icon"><IconShield /></span>{!collapsed && " SAST"}
          </a>
          <a href="#/active-jobs" className={"nav-item" + (onActiveJobs ? " active" : "")} title="Active Jobs">
            <span className="nav-icon"><IconPlay /></span>{!collapsed && " Active Jobs"}
          </a>
          {!collapsed && <div className="nav-section-label" style={{ marginTop: 8 }}>Stats</div>}
          <a href="#/stats/usage" className={"nav-item" + (onStats ? " active" : "")} title="Usage statistics">
            <span className="nav-icon"><IconChart /></span>{!collapsed && " Usage"}
          </a>
          {!collapsed && <div className="nav-section-label" style={{
          marginTop: 8
        }}>Configuration</div>}
          <a href="#/settings" className={"nav-item" + (onSettings ? " active" : "")} title="LLM Settings">
            <span className="nav-icon"><IconSettings /></span>{!collapsed && " LLM Settings"}
          </a>
          <a href="#/scan-policy" className={"nav-item" + (onScanPolicy ? " active" : "")} title="Agent Settings">
            <span className="nav-icon"><IconShield /></span>{!collapsed && " Agent Settings"}
          </a>
          <a href="#/external-integrations" className={"nav-item" + (onExternalIntegrations ? " active" : "")} title="External Integrations">
            <span className="nav-icon"><IconShield /></span>{!collapsed && " External Integrations"}
          </a>
          <a href="#/debug" className={"nav-item" + (onDebug ? " active" : "")} title="System Settings">
            <span className="nav-icon"><IconBug /></span>{!collapsed && " System Settings"}
          </a>
          {reportingDebugCfg?.panel_enabled && <>
            {!collapsed && <div className="nav-section-label" style={{
            marginTop: 8
          }}>Testing Features</div>}
            <a href="#/reporting-debug" className={"nav-item" + (onReportingDebug ? " active" : "")} title="Reporting Lab">
              <span className="nav-icon"><IconBug /></span>{!collapsed && " Reporting Lab"}
            </a></>}
        </nav>
      </aside>


      <div className="main">
        <React.Suspense fallback={<div className="content scroll-content"><div className="subtle">Loading…</div></div>}>
          {route.name === "list" && <SitesList />}
          {route.name === "site-new" && <SiteForm key="new" />}
          {route.name === "site-edit" && <SiteForm key={route.id} siteId={route.id} />}
          {route.name === "site-detail" && <SiteDetail key={route.id} siteId={route.id} />}
          {route.name === "api-list" && <ApiCollectionsList />}
          {route.name === "api-new" && <ApiCollectionForm key="api-new" />}
          {route.name === "api-edit" && <ApiCollectionForm key={route.id} collectionId={route.id} />}
          {route.name === "api-detail" && <ApiCollectionDetail key={route.id} collectionId={route.id} />}
          {route.name === "api-files" && <ApiFilesManager key={route.id} collectionId={route.id} />}
          {route.name === "api-run-new" && <ApiTestRunForm key={route.id} collectionId={route.id} />}
          {route.name === "api-run-detail" && <ApiTestRunDetail key={route.id} runId={route.id} initialTab={route.tab} />}
          {route.name === "sast-list" && <SastRunsListPage />}
          {route.name === "sast-run-new" && <SastRunForm key="sast-new" />}
          {route.name === "sast-run-detail" && <SastRunDetail key={route.id} runId={route.id} initialTab={route.tab} />}
          {route.name === "app-list" && <ApplicationsList />}
          {route.name === "app-new" && <ApplicationForm key="app-new" />}
          {route.name === "app-edit" && <ApplicationForm key={route.id} applicationId={route.id} />}
          {route.name === "app-detail" && <ApplicationDetail key={route.id} applicationId={route.id} initialTab={route.tab} />}
          {route.name === "campaign-new" && <CampaignNewForm key={route.id} applicationId={route.id} />}
          {route.name === "campaign-detail" && <CampaignDetail key={`${route.id}-${route.campaignId}`} applicationId={route.id} campaignId={route.campaignId} initialTab={route.tab} />}
          {route.name === "active-jobs" && <ActiveJobsPage />}
          {route.name === "stats" && <StatisticsPage />}
          {route.name === "run-new" && <TestRunForm key={route.siteId} siteId={route.siteId} />}
          {route.name === "run-detail" && <TestRunDetail key={route.id} runId={route.id} initialTab={route.tab} />}
          {route.name === "settings" && <SettingsPage />}
          {route.name === "scan-policy" && <ScanPolicyPage />}
          {route.name === "external-integrations" && <ExternalIntegrationsPage />}
          {route.name === "debug" && <DebugPage showUsername={showUsername} setShowUsername={setShowUsername} showApplications={showApplications} setShowApplications={setShowApplications} username={username} reportingDebugCfg={reportingDebugCfg} setReportingDebugCfg={setReportingDebugCfg} />}
          {route.name === "reporting-debug" && <ReportingDebugPage />}
        </React.Suspense>
      </div>
    </div>;
}
export default App;
