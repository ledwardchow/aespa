import { useState } from "react";
import { ApiRunLogTab } from "./ApiRunLogTab";
import { ApiRunAgentsTab } from "./ApiRunAgentsTab";


export function ApiRunStatusTab({
  runId,
  scanRunning
}) {
  const [subTab, setSubTab] = useState("agents");
  return <div className="api-run-status-content">
      <div className="activity-sub-tab-bar" style={{
      padding: "8px 16px 0",
      flexShrink: 0,
      position: "sticky",
      top: 0,
      background: "var(--bg)",
      zIndex: 2,
      borderBottom: "1px solid var(--border)"
    }}>
        <button className={"activity-sub-tab-btn" + (subTab === "agents" ? " active" : "")} onClick={() => setSubTab("agents")}>Agents</button>
        <button className={"activity-sub-tab-btn" + (subTab === "log" ? " active" : "")} onClick={() => setSubTab("log")}>Log</button>
      </div>
      <div className="api-run-status-scroll">
        {subTab === "agents" && <ApiRunAgentsTab runId={runId} scanRunning={scanRunning} />}
        {subTab === "log" && <ApiRunLogTab runId={runId} scanRunning={scanRunning} />}
      </div>
    </div>;
}

// ── ApiRunLogTab ───────────────────────────────────────────────────────────────
