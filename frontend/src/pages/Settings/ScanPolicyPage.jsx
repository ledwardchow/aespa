import { useState } from "react";
import { ValidatorSettings } from "./ValidatorSettings";
import { GlobalPolicySettings, GlobalPolicySubTabs, ScannerPolicySettings } from "./ScannerPolicySettings";
import { SpecialistAgentSettings } from "./SpecialistAgentSettings";
import { ReportingSettings } from "./ReportingSettings";
import { CrawlerSettings } from "./CrawlerSettings";


export function ScanPolicyPage() {
  const [tab, setTab] = useState("global");
  const [globalTab, setGlobalTab] = useState("scan-behaviour");
  return <>
    <div className="topbar"><div className="topbar-title">Agent Settings</div></div>
    <div className="content" style={{
      paddingLeft: 16,
      paddingRight: 0,
      paddingBottom: 0,
      display: "flex",
      flexDirection: "column",
      flex: 1,
      minHeight: 0
    }}>
      <div className="tab-bar">
        <button className={"tab-btn" + (tab === "global" ? " active" : "")} onClick={() => setTab("global")}>Global</button>
        <button className={"tab-btn" + (tab === "crawler" ? " active" : "")} onClick={() => setTab("crawler")}>Crawler</button>
        <button className={"tab-btn" + (tab === "scanner" ? " active" : "")} onClick={() => setTab("scanner")}>Test Lead</button>
        <button className={"tab-btn" + (tab === "specialists" ? " active" : "")} onClick={() => setTab("specialists")}>Specialist Agents</button>
        <button className={"tab-btn" + (tab === "validator" ? " active" : "")} onClick={() => setTab("validator")}>Validator</button>
        <button className={"tab-btn" + (tab === "reporting" ? " active" : "")} onClick={() => setTab("reporting")}>Reporting</button>
      </div>
      {tab === "global" && <GlobalPolicySubTabs tab={globalTab} setTab={setGlobalTab} />}
      <div className="scroll-content" style={{
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
        overflowX: "hidden",
        paddingTop: 16,
        paddingBottom: 28
      }}>
        {tab === "global" && <GlobalPolicySettings tab={globalTab} />}
        {tab === "crawler" && <CrawlerSettings />}
        {tab === "scanner" && <ScannerPolicySettings />}
        {tab === "specialists" && <SpecialistAgentSettings />}
        {tab === "validator" && <ValidatorSettings />}
        {tab === "reporting" && <ReportingSettings />}
      </div>
    </div></>;
}
