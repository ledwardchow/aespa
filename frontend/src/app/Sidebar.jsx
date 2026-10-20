import {
  IconSites,
  IconApis,
  IconPlay,
  IconShield,
  IconChevronLeft,
  IconChevronRight,
  IconBug,
  IconChart,
  IconSystems,
  IconCpu,
  IconPuzzle,
  IconSliders,
  IconGauge,
  IconFlask,
} from "../shared/ui/Icons.jsx";
export function Sidebar({ section, collapsed, onToggle, preferences }) {
  const {
    appVersion,
    username,
    showUsername,
    showSystems,
    reportingDebugCfg,
    benchmarkLabCfg,
    planUsageCfg,
  } = preferences;
  const onSites = section === "sites";
  const onApis = section === "apis";
  const onSystems = section === "systems";
  const onActiveJobs = section === "active-jobs";
  const onSettings = section === "settings";
  const onScanPolicy = section === "scan-policy";
  const onExtensions = section === "extensions";
  const onSast = section === "sast";
  const onReportingDebug = section === "reporting-debug";
  const onBenchmarkLab = section === "benchmark-lab";
  const onStats = section === "stats";
  const onPlanUsage = section === "chatgpt-plan-usage";

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
        {showSystems && (
          <a href="#/systems" className={"nav-item" + (onSystems ? " active" : "")} title="Systems">
            <span className="nav-icon">
              <IconSystems />
            </span>
            {!collapsed && " Systems"}
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
        <a href="#/sast-runs" className={"nav-item" + (onSast ? " active" : "")} title="SAST Scans">
          <span className="nav-icon">
            <IconShield />
          </span>
          {!collapsed && " SAST Scans"}
        </a>
        {!collapsed && (
          <div className="nav-section-label" style={{ marginTop: 8 }}>
            Activity
          </div>
        )}
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
        <a href="#/stats/usage" className={"nav-item" + (onStats ? " active" : "")} title="Usage">
          <span className="nav-icon">
            <IconChart />
          </span>
          {!collapsed && " Usage"}
        </a>
        {planUsageCfg?.panel_enabled && (
          <a
            href="#/stats/chatgpt-plan"
            className={"nav-item" + (onPlanUsage ? " active" : "")}
            title="ChatGPT Plan Usage"
          >
            <span className="nav-icon">
              <IconGauge />
            </span>
            {!collapsed && " ChatGPT Plan Usage"}
          </a>
        )}
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
          href="#/settings/profiles"
          className={"nav-item" + (onSettings ? " active" : "")}
          title="LLM Configuration"
        >
          <span className="nav-icon">
            <IconCpu />
          </span>
          {!collapsed && " LLM Configuration"}
        </a>
        <a
          href="#/extensions"
          className={"nav-item" + (onExtensions ? " active" : "")}
          title="Extensions"
        >
          <span className="nav-icon">
            <IconPuzzle />
          </span>
          {!collapsed && " Extensions"}
        </a>
        <a
          href="#/scan-policy"
          className={"nav-item" + (onScanPolicy ? " active" : "")}
          title="Settings"
        >
          <span className="nav-icon">
            <IconSliders />
          </span>
          {!collapsed && " Settings"}
        </a>
        {(reportingDebugCfg?.panel_enabled || benchmarkLabCfg?.panel_enabled) && (
          <>
            {!collapsed && (
              <div
                className="nav-section-label"
                style={{
                  marginTop: 8,
                }}
              >
                Labs
              </div>
            )}
            {reportingDebugCfg?.panel_enabled && (
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
            )}
            {benchmarkLabCfg?.panel_enabled && (
              <a
                href="#/benchmark-lab"
                className={"nav-item" + (onBenchmarkLab ? " active" : "")}
                title="Benchmark Lab"
              >
                <span className="nav-icon">
                  <IconFlask />
                </span>
                {!collapsed && " Benchmark Lab"}
              </a>
            )}
          </>
        )}
      </nav>
    </aside>
  );
}
