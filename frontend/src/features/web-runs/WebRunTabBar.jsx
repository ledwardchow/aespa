import { WEB_RUN_TABS } from "./tabs.js";

export function WebRunTabBar({ activeTab, onSelect, counts, activityLive, children }) {
  return (
    <div className="tab-bar web-run-tab-bar">
      <label className="web-run-section-select">
        <span>View</span>
        <select
          aria-label="Run section"
          value={activeTab}
          onChange={(event) => onSelect(event.target.value)}
        >
          {WEB_RUN_TABS.map((tab) => (
            <option key={tab.key} value={tab.key}>
              {tab.label}
              {counts[tab.key] ? ` (${counts[tab.key]})` : ""}
            </option>
          ))}
        </select>
      </label>
      <div className="web-run-tab-links">
        {WEB_RUN_TABS.map((tab) => {
          const count = counts[tab.key] || 0;
          return (
            <button
              key={tab.key}
              className={"tab-btn" + (activeTab === tab.key ? " active" : "")}
              onClick={() => onSelect(tab.key)}
            >
              {tab.label}
              {tab.key === "activity" && activityLive ? (
                <span className="activity-live-dot">●</span>
              ) : null}
              {count > 0 ? (
                <span className={tab.key === "findings" ? "findings-badge" : "traffic-count"}>
                  {count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <div className="web-run-tab-actions">{children}</div>
    </div>
  );
}
