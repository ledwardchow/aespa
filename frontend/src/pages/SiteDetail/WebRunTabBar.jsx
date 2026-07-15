const WEB_RUN_TABS = [
  { key: "activity", label: "Status" },
  { key: "sitemap", label: "Site Map" },
  { key: "attack", label: "Attack Surface & Coverage" },
  { key: "sessions", label: "Sessions" },
  { key: "findings", label: "Findings" },
  { key: "traffic", label: "Traffic Log" },
  { key: "leads", label: "SAST Leads" }
];

export function WebRunTabBar({
  activeTab,
  onSelect,
  counts,
  activityLive,
  children
}) {
  return <div className="tab-bar">
    {WEB_RUN_TABS.map(tab => {
      const count = counts[tab.key] || 0;
      return <button
        key={tab.key}
        className={"tab-btn" + (activeTab === tab.key ? " active" : "")}
        onClick={() => onSelect(tab.key)}
      >
        {tab.label}
        {tab.key === "activity" && activityLive ? <span className="activity-live-dot">●</span> : null}
        {count > 0 ? <span className={tab.key === "findings" ? "findings-badge" : "traffic-count"}>{count}</span> : null}
      </button>;
    })}
    <div style={{ flex: 1 }}></div>
    {children}
  </div>;
}
