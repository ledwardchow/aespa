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
import { SastSettings } from "./SastSettings.jsx";

const TOP_LEVEL_TABS = [
  { key: "global", label: "Global" },
  { key: "systems", label: "Systems" },
  { key: "dast", label: "DAST" },
  { key: "sast", label: "SAST" },
];

const DAST_TABS = [
  { key: "crawler", label: "Crawler" },
  { key: "scanner", label: "Test Lead" },
  { key: "specialists", label: "Specialist" },
  { key: "validator", label: "Validator" },
  { key: "reporting", label: "Reporting" },
  { key: "code", label: "Python Sandbox" },
  { key: "deep", label: "Deep Scan" },
];

export function ScanPolicyPage({ showDeepScan = false, showSystems = true }) {
  const [tab, setTab] = useState("global");
  const [globalTab, setGlobalTab] = useState("scan-behaviour");
  const [dastTab, setDastTab] = useState("crawler");
  const topLevelTabs = showSystems
    ? TOP_LEVEL_TABS
    : TOP_LEVEL_TABS.filter((agentTab) => agentTab.key !== "systems");
  const dastTabs = showDeepScan
    ? DAST_TABS
    : DAST_TABS.filter((agentTab) => agentTab.key !== "deep");
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">Agent Settings</div>
      </div>
      <div className={`content ${styles.content}`}>
        <Tabs label="Agent settings" tabs={topLevelTabs} value={tab} onChange={setTab} />
        {tab === "global" && <GlobalPolicySubTabs tab={globalTab} setTab={setGlobalTab} />}
        {tab === "dast" && (
          <Tabs
            label="DAST agent settings"
            tabs={dastTabs}
            value={dastTab}
            onChange={setDastTab}
            className={`activity-sub-tab-bar coverage-sub-tab-bar ${styles.subTabs}`}
            buttonClassName="activity-sub-tab-btn coverage-sub-tab-btn"
          />
        )}
        <div className={`scroll-content ${styles.scroll}`}>
          {tab === "global" && <GlobalPolicySettings tab={globalTab} />}
          {tab === "systems" && <ComponentMapperSettings />}
          {tab === "dast" && dastTab === "crawler" && <CrawlerSettings />}
          {tab === "dast" && dastTab === "scanner" && <ScannerPolicySettings />}
          {tab === "dast" && dastTab === "specialists" && <SpecialistAgentSettings />}
          {tab === "dast" && dastTab === "validator" && <ValidatorSettings />}
          {tab === "dast" && dastTab === "reporting" && <ReportingSettings />}
          {tab === "dast" && dastTab === "code" && <CodeExecutionSettings />}
          {tab === "dast" && dastTab === "deep" && <DeepScanSettings />}
          {tab === "sast" && <SastSettings />}
        </div>
      </div>
    </>
  );
}
