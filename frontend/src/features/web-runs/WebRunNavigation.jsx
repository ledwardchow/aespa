import { WebRunTabBar } from "./WebRunTabBar.jsx";

export function WebRunNavigation({
  activeTab,
  onSelect,
  activityLive,
  counts,
  canClearCrawl,
  onClearCrawl,
  multiUser,
  graphView,
  onGraphView,
}) {
  return (
    <WebRunTabBar
      activeTab={activeTab}
      onSelect={onSelect}
      activityLive={activityLive}
      counts={counts}
    >
      {canClearCrawl && activeTab === "sitemap" && (
        <button className="btn danger-outline sm" onClick={onClearCrawl}>
          Clear crawl
        </button>
      )}
      {activeTab === "sitemap" && multiUser && (
        <div className="view-toggle">
          <button
            className={"btn ghost sm" + (graphView === "scope" ? " active" : "")}
            onClick={() => onGraphView("scope")}
          >
            By Scope
          </button>
          <button
            className={"btn ghost sm" + (graphView === "user" ? " active" : "")}
            onClick={() => onGraphView("user")}
          >
            By User
          </button>
        </div>
      )}
    </WebRunTabBar>
  );
}
