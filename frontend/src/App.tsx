import { Link, Outlet, useMatch } from "react-router-dom";

function IconSites() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="1" y="1" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
      <rect x="9" y="1" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
      <rect x="1" y="9" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
      <rect x="9" y="9" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
    </svg>
  );
}

function IconSettings() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.4"/>
      <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M2.93 2.93l1.06 1.06M12.01 12.01l1.06 1.06M2.93 13.07l1.06-1.06M12.01 3.99l1.06-1.06"
        stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  );
}

export default function App() {
  const onSites    = useMatch({ path: "/",        end: false });
  const onSettings = useMatch({ path: "/settings", end: true  });

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="logo">
            <div className="logo-icon">A</div>
            <span className="logo-text">AESPA</span>
          </div>
          <div className="logo-sub">LLM Pentesting Agent</div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Targets</div>
          <Link to="/" className={`nav-item${onSites && !onSettings ? " active" : ""}`}>
            <span className="nav-icon"><IconSites /></span>
            Sites
          </Link>

          <div className="nav-section-label" style={{ marginTop: 8 }}>Configuration</div>
          <Link to="/settings" className={`nav-item${onSettings ? " active" : ""}`}>
            <span className="nav-icon"><IconSettings /></span>
            LLM Settings
          </Link>
        </nav>

        <div className="sidebar-footer">v0.1.0</div>
      </aside>

      <div className="main">
        <Outlet />
      </div>
    </div>
  );
}
