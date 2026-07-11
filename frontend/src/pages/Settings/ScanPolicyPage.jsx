import { useState } from "react";
import { ValidatorSettings } from "./ValidatorSettings";
import { ScannerPolicySettings } from "./ScannerPolicySettings";
import { SpecialistAgentSettings } from "./SpecialistAgentSettings";


export function ScanPolicyPage() {
  const [tab, setTab] = useState("scanner");
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
        <button className={"tab-btn" + (tab === "scanner" ? " active" : "")} onClick={() => setTab("scanner")}>Scanner</button>
        <button className={"tab-btn" + (tab === "specialists" ? " active" : "")} onClick={() => setTab("specialists")}>Specialist Agents</button>
        <button className={"tab-btn" + (tab === "validator" ? " active" : "")} onClick={() => setTab("validator")}>Validator</button>
      </div>
      <div className="scroll-content" style={{
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
        overflowX: "hidden",
        paddingTop: 16,
        paddingBottom: 28
      }}>
        {tab === "scanner" && <ScannerPolicySettings />}
        {tab === "specialists" && <SpecialistAgentSettings />}
        {tab === "validator" && <ValidatorSettings />}
      </div>
    </div></>;
}
