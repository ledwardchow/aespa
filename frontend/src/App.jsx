import { ApiCollectionsList, ApiCollectionForm, ApiCollectionDetail, ApiFilesManager, ApiTestRunForm, ApiTestRunDetail, ApiRunLeadsTab, ApiRunEndpointsTab, ApiRunTrafficTab, _buildAgentsFromLog, ApiRunLogTab, TestRunForm } from "./pages/ApiCollections";
import { SastRunsListPage, SastRunDetail, SastLeadsTab } from "./pages/SastRuns";
import { SiteDetail, SiteForm, useColResize, TestRunDetail, WebRunWorkProgramTab, ScannerSessionsPanel, AttackSurfacePanel } from "./pages/SiteDetail";
import { SettingsPage, ScanPolicyPage, ExternalIntegrationsPage, DebugPage, ReportingDebugPage } from "./pages/Settings";
import { ActiveJobsPage } from "./pages/ActiveJobs";
import { SitesList } from "./pages/SitesList";
import React, { useEffect, useState } from "react";
import * as d3 from "d3";

// ── API client ────────────────────────────────────────────────────────────────

import { api, formatError } from "./lib/api";
import { useRoute } from "./lib/router";
import { IconSites, IconApis, IconSettings, IconCheck, IconPlay, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconSend } from "./components/Icons";

// ── Shell ──────────────────────────────────────────────────────────────────────

function App() {
  const route = useRoute();
  const onSites = ["list", "site-new", "site-edit", "site-detail", "run-new", "run-detail"].includes(route.name);
  const onApis = ["api-list", "api-new", "api-edit", "api-detail", "api-files"].includes(route.name);
  const onActiveJobs = route.name === "active-jobs";
  const onSettings = route.name === "settings";
  const onScanPolicy = route.name === "scan-policy";
  const onExternalIntegrations = route.name === "external-integrations";
  const onSast = route.name === "sast-list" || route.name === "sast-run-detail";
  const onDebug = route.name === "debug";
  const onReportingDebug = route.name === "reporting-debug";
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
  const [collapsed, setCollapsed] = useState(false);
  const [reportingDebugCfg, setReportingDebugCfg] = useState(null);
  useEffect(() => {
    api.getVersion().then(d => {
      setAppVersion(d.version);
      setUsername(d.username || "");
    }).catch(() => {});
    api.getReportingDebugConfig().then(setReportingDebugCfg).catch(() => {});
  }, []);
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
          <a href="#/debug" className={"nav-item" + (onDebug ? " active" : "")} title="Debug">
            <span className="nav-icon"><IconBug /></span>{!collapsed && " Debug"}
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
        {route.name === "sast-run-detail" && <SastRunDetail key={route.id} runId={route.id} initialTab={route.tab} />}
        {route.name === "active-jobs" && <ActiveJobsPage />}
        {route.name === "run-new" && <TestRunForm key={route.siteId} siteId={route.siteId} />}
        {route.name === "run-detail" && <TestRunDetail key={route.id} runId={route.id} initialTab={route.tab} />}
        {route.name === "settings" && <SettingsPage />}
        {route.name === "scan-policy" && <ScanPolicyPage />}
        {route.name === "external-integrations" && <ExternalIntegrationsPage />}
        {route.name === "debug" && <DebugPage showUsername={showUsername} setShowUsername={setShowUsername} username={username} reportingDebugCfg={reportingDebugCfg} setReportingDebugCfg={setReportingDebugCfg} />}
        {route.name === "reporting-debug" && <ReportingDebugPage />}
      </div>
    </div>;
}
export default App;