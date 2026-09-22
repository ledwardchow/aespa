import { Tabs } from "../../shared/ui/Tabs.tsx";
import styles from "./ScanPolicyPage.module.css";
import { useState } from "react";
import { ValidatorSettings } from "./ValidatorSettings.jsx";
import { GlobalPolicySettings, ScannerPolicySettings } from "./ScannerPolicySettings.jsx";
import { SpecialistAgentSettings } from "./SpecialistAgentSettings.jsx";
import { ReportingSettings } from "./ReportingSettings.jsx";
import { CrawlerSettings } from "./CrawlerSettings.jsx";
import { ComponentMapperSettings } from "./ComponentMapperSettings.jsx";
import { CodeExecutionSettings } from "./CodeExecutionSettings.jsx";
import { DeepScanSettings } from "./DeepScanSettings.jsx";
import { SastSettings } from "./SastSettings.jsx";
import { SystemSettingsPanels } from "./DebugPage.jsx";

const TOP_LEVEL_TABS = [
  { key: "global", label: "Global" },
  { key: "systems", label: "Systems" },
  { key: "dast", label: "DAST" },
  { key: "sast", label: "SAST" },
];

const DAST_TABS = [
  { key: "scan-behaviour", label: "Scan Behaviour" },
  { key: "headers", label: "HTTP Headers" },
  { key: "crawler", label: "Crawler" },
  { key: "scanner", label: "Test Lead" },
  { key: "specialists", label: "Specialist" },
  { key: "validator", label: "Validator" },
  { key: "reporting", label: "Reporting" },
  { key: "code", label: "Python Sandbox" },
  { key: "deep", label: "Deep Scan" },
];

const GLOBAL_TABS = [
  { key: "features", label: "Feature Visibility" },
  { key: "debug", label: "Debug Settings" },
];

export function ScanPolicyPage({
  showUsername,
  setShowUsername,
  showSystems = true,
  setShowSystems,
  showDeepScan = false,
  setShowDeepScan,
  showTeamScan,
  setShowTeamScan,
  username,
  reportingDebugCfg,
  setReportingDebugCfg,
  benchmarkLabCfg,
  setBenchmarkLabCfg,
}) {
  const [tab, setTab] = useState("global");
  const [globalTab, setGlobalTab] = useState("features");
  const [dastTab, setDastTab] = useState("scan-behaviour");
  const topLevelTabs = showSystems
    ? TOP_LEVEL_TABS
    : TOP_LEVEL_TABS.filter((agentTab) => agentTab.key !== "systems");
  const dastTabs = showDeepScan
    ? DAST_TABS
    : DAST_TABS.filter((agentTab) => agentTab.key !== "deep");
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">Settings</div>
      </div>
      <div className={`content ${styles.content}`}>
        <Tabs label="Settings" tabs={topLevelTabs} value={tab} onChange={setTab} />
        {tab === "global" && (
          <Tabs
            label="Global settings"
            tabs={GLOBAL_TABS}
            value={globalTab}
            onChange={setGlobalTab}
            className={`activity-sub-tab-bar coverage-sub-tab-bar ${styles.subTabs}`}
            buttonClassName="activity-sub-tab-btn coverage-sub-tab-btn"
          />
        )}
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
          {tab === "global" && (
            <div className={styles.systemSettingsPanels}>
              <SystemSettingsPanels
                tab={globalTab}
                showUsername={showUsername}
                setShowUsername={setShowUsername}
                showSystems={showSystems}
                setShowSystems={setShowSystems}
                showDeepScan={showDeepScan}
                setShowDeepScan={setShowDeepScan}
                showTeamScan={showTeamScan}
                setShowTeamScan={setShowTeamScan}
                username={username}
                reportingDebugCfg={reportingDebugCfg}
                setReportingDebugCfg={setReportingDebugCfg}
                benchmarkLabCfg={benchmarkLabCfg}
                setBenchmarkLabCfg={setBenchmarkLabCfg}
              />
            </div>
          )}
          {tab === "systems" && <ComponentMapperSettings />}
          {tab === "dast" && dastTab === "scan-behaviour" && (
            <GlobalPolicySettings tab="scan-behaviour" />
          )}
          {tab === "dast" && dastTab === "headers" && <GlobalPolicySettings tab="headers" />}
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
