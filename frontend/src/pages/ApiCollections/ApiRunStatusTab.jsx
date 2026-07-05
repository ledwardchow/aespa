import { useState, useRef, useMemo, useReducer } from "react";
import { ApiRunLogTab } from "./ApiRunLogTab";
import { ApiRunAgentsTab } from "./ApiRunAgentsTab";
import { useRoute, nav } from "../../lib/router";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { IconSites, IconApis, IconSettings, IconPlus, IconCheck, IconPlay, IconStop, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconMessageSquare, IconSend, IconBrain } from "../../components/Icons";


export function ApiRunStatusTab({
  runId,
  scanRunning
}) {
  const [subTab, setSubTab] = useState("agents");
  return <div style={{
    display: "flex",
    flexDirection: "column",
    height: "100%",
    overflow: "hidden"
  }}>
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
      <div style={{
      flex: 1,
      overflow: "auto",
      minHeight: 0
    }}>
        {subTab === "agents" && <ApiRunAgentsTab runId={runId} scanRunning={scanRunning} />}
        {subTab === "log" && <ApiRunLogTab runId={runId} scanRunning={scanRunning} />}
      </div>
    </div>;
}

// ── ApiRunLogTab ───────────────────────────────────────────────────────────────

