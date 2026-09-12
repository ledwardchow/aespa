import { Tabs } from "../../shared/ui/Tabs.tsx";
import styles from "./ScanPolicyPage.module.css";
import { useState } from "react";
import { ValidatorSettings } from "./ValidatorSettings.jsx";
import {
  GlobalPolicySettings,
  GlobalPolicySubTabs,
  ScannerPolicySettings,
} from "./ScannerPolicySettings.jsx";
import { SpecialistAgentSettings } from "./SpecialistAgentSettings.jsx";
import { ReportingSettings } from "./ReportingSettings.jsx";
import { CrawlerSettings } from "./CrawlerSettings.jsx";
import { ComponentMapperSettings } from "./ComponentMapperSettings.jsx";
import { CodeExecutionSettings } from "./CodeExecutionSettings.jsx";
import { DeepScanSettings } from "./DeepScanSettings.jsx";

const AGENT_TABS = [
  { key: "global", label: "Global" },
  { key: "crawler", label: "Crawler" },
  { key: "scanner", label: "Test Lead" },
  { key: "specialists", label: "Specialist Agents" },
  { key: "deep", label: "Deep Scan" },
  { key: "validator", label: "Validator" },
  { key: "reporting", label: "Reporting" },
  { key: "mapper", label: "Component Mapper" },
  { key: "code", label: "Python Sandbox" },
];

export function ScanPolicyPage({ showDeepScan = false }) {
  const [tab, setTab] = useState("global");
  const [globalTab, setGlobalTab] = useState("scan-behaviour");
  const visibleTabs = showDeepScan
    ? AGENT_TABS
    : AGENT_TABS.filter((agentTab) => agentTab.key !== "deep");
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">Agent Settings</div>
      </div>
      <div className={`content ${styles.content}`}>
        <Tabs label="Agent settings" tabs={visibleTabs} value={tab} onChange={setTab} />
        {tab === "global" && <GlobalPolicySubTabs tab={globalTab} setTab={setGlobalTab} />}
        <div className={`scroll-content ${styles.scroll}`}>
          {tab === "global" && <GlobalPolicySettings tab={globalTab} />}
          {tab === "crawler" && <CrawlerSettings />}
          {tab === "mapper" && <ComponentMapperSettings />}
          {tab === "scanner" && <ScannerPolicySettings />}
          {tab === "specialists" && <SpecialistAgentSettings />}
          {tab === "deep" && <DeepScanSettings />}
          {tab === "validator" && <ValidatorSettings />}
          {tab === "reporting" && <ReportingSettings />}
          {tab === "code" && <CodeExecutionSettings />}
        </div>
      </div>
    </>
  );
}
