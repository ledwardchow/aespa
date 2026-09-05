import {
  IconSites,
  IconApis,
  IconSettings,
  IconPlay,
  IconShield,
  IconChevronLeft,
  IconChevronRight,
  IconBug,
  IconChart,
  IconApplications,
} from "../shared/ui/Icons.jsx";
export function Sidebar({ section, collapsed, onToggle, preferences }) {
  const { appVersion, username, showUsername, showApplications, reportingDebugCfg } = preferences;
  const onSites = section === "sites";
  const onApis = section === "apis";
  const onApplications = section === "applications";
  const onActiveJobs = section === "active-jobs";
  const onSettings = section === "settings";
  const onScanPolicy = section === "scan-policy";
  const onExternalIntegrations = section === "external-integrations";
  const onSast = section === "sast";
  const onDebug = section === "debug";
  const onReportingDebug = section === "reporting-debug";
  const onStats = section === "stats";

  return (
    <aside className={"sidebar" + (collapsed ? " sidebar--collapsed" : "")}>
      <div className="sidebar-brand">
        <div className="logo">
          {!collapsed && (
            <div className="logo-codename">
              <span>CODE</span>
              <span>NAME</span>
            </div>
          )}
          <img src="/icon-sm.png" className="logo-icon" alt="AESPA" />
          {!collapsed && <span className="logo-text">ESPA</span>}
        </div>
        {!collapsed && <div className="logo-sub">AI-Enabled Security Pentesting Agent</div>}
        {!collapsed && (
          <a
            className="logo-link"
            href="https://github.com/ledwardchow/aespa"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/ledwardchow/aespa
          </a>
        )}
      </div>
      <div className="sidebar-meta">
        <button
          className="sidebar-toggle"
          onClick={onToggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <IconChevronRight /> : <IconChevronLeft />}
        </button>
        {!collapsed && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "2px",
              overflow: "hidden",
              minWidth: 0,
              lineHeight: 1.2,
            }}
          >
            {showUsername && username ? (
              <>
                <span
                  className="sidebar-username"
                  style={{
                    color: "var(--text-2)",
                    fontWeight: "500",
                    fontSize: "11px",
                    textOverflow: "ellipsis",
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                  }}
                  title={username}
                >
                  {username}
                </span>
                {appVersion && (
                  <span
                    style={{
                      color: "var(--muted)",
                      fontSize: "9.5px",
                    }}
                  >
                    v{appVersion}
                  </span>
                )}
              </>
            ) : (
              <>{appVersion && <span>v{appVersion}</span>}</>
            )}
          </div>
        )}
      </div>
      <nav className="sidebar-nav">
        {!collapsed && <div className="nav-section-label">Targets</div>}
        {showApplications && (
          <a
            href="#/applications"
            className={"nav-item" + (onApplications ? " active" : "")}
            title="Applications"
          >
            <span className="nav-icon">
              <IconApplications />
            </span>
            {!collapsed && " Applications"}
          </a>
        )}
        <a href="#/" className={"nav-item" + (onSites ? " active" : "")} title="Sites">
          <span className="nav-icon">
            <IconSites />
          </span>
          {!collapsed && " Sites"}
        </a>
        <a href="#/apis" className={"nav-item" + (onApis ? " active" : "")} title="APIs">
          <span className="nav-icon">
            <IconApis />
          </span>
          {!collapsed && " APIs"}
        </a>
        <a href="#/sast-runs" className={"nav-item" + (onSast ? " active" : "")} title="SAST">
          <span className="nav-icon">
            <IconShield />
          </span>
          {!collapsed && " SAST"}
        </a>
        <a
          href="#/active-jobs"
          className={"nav-item" + (onActiveJobs ? " active" : "")}
          title="Active Jobs"
        >
          <span className="nav-icon">
            <IconPlay />
          </span>
          {!collapsed && " Active Jobs"}
        </a>
        {!collapsed && (
          <div className="nav-section-label" style={{ marginTop: 8 }}>
            Stats
          </div>
        )}
        <a
          href="#/stats/usage"
          className={"nav-item" + (onStats ? " active" : "")}
          title="Usage statistics"
        >
          <span className="nav-icon">
            <IconChart />
          </span>
          {!collapsed && " Usage"}
        </a>
        {!collapsed && (
          <div
            className="nav-section-label"
            style={{
              marginTop: 8,
            }}
          >
            Configuration
          </div>
        )}
        <a
          href="#/settings"
          className={"nav-item" + (onSettings ? " active" : "")}
          title="LLM Settings"
        >
          <span className="nav-icon">
            <IconSettings />
          </span>
          {!collapsed && " LLM Settings"}
        </a>
        <a
          href="#/scan-policy"
          className={"nav-item" + (onScanPolicy ? " active" : "")}
          title="Agent Settings"
        >
          <span className="nav-icon">
            <IconShield />
          </span>
          {!collapsed && " Agent Settings"}
        </a>
        <a
          href="#/external-integrations"
          className={"nav-item" + (onExternalIntegrations ? " active" : "")}
          title="External Integrations"
        >
          <span className="nav-icon">
            <IconShield />
          </span>
          {!collapsed && " External Integrations"}
        </a>
        <a
          href="#/debug"
          className={"nav-item" + (onDebug ? " active" : "")}
          title="System Settings"
        >
          <span className="nav-icon">
            <IconBug />
          </span>
          {!collapsed && " System Settings"}
        </a>
        {reportingDebugCfg?.panel_enabled && (
          <>
            {!collapsed && (
              <div
                className="nav-section-label"
                style={{
                  marginTop: 8,
                }}
              >
                Testing Features
              </div>
            )}
            <a
              href="#/reporting-debug"
              className={"nav-item" + (onReportingDebug ? " active" : "")}
              title="Reporting Lab"
            >
              <span className="nav-icon">
                <IconBug />
              </span>
              {!collapsed && " Reporting Lab"}
            </a>
          </>
        )}
      </nav>
    </aside>
  );
}
