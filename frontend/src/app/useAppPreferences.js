import * as settingsApi from "../shared/api/settings.js";
import * as extensionsApi from "../shared/api/extensions.js";
import { PLAN_USAGE_EXTENSION_ID } from "../shared/api/chatgptPlanUsage.js";
import { useEffect, useState } from "react";

export function useAppPreferences() {
  const [appVersion, setAppVersion] = useState("");
  const [username, setUsername] = useState("");
  const [showUsername, setShowUsername] = useState(() => {
    try {
      const val = localStorage.getItem("aespa_show_username");
      return val === null ? true : val === "true";
    } catch {
      return true;
    }
  });
  const [showSystems, setShowSystems] = useState(() => {
    try {
      const val = localStorage.getItem("aespa_show_systems");
      const legacyVal = localStorage.getItem("aespa_show_applications");
      return val === null ? (legacyVal === null ? true : legacyVal === "true") : val === "true";
    } catch {
      return true;
    }
  });
  const [showDeepScan, setShowDeepScan] = useState(() => {
    try {
      return localStorage.getItem("aespa_show_deep_scan") === "true";
    } catch {
      return false;
    }
  });
  const [showTeamScan, setShowTeamScan] = useState(() => {
    try {
      return localStorage.getItem("aespa_show_team_scan") === "true";
    } catch {
      return false;
    }
  });
  const [showSastDeepScan, setShowSastDeepScan] = useState(() => {
    try {
      return localStorage.getItem("aespa_show_sast_deep_scan") === "true";
    } catch {
      return false;
    }
  });
  const [reportingDebugCfg, setReportingDebugCfg] = useState(null);
  const [benchmarkLabCfg, setBenchmarkLabCfg] = useState(null);
  const [planUsageCfg, setPlanUsageCfg] = useState(null);
  useEffect(() => {
    settingsApi
      .getVersion()
      .then((d) => {
        setAppVersion(d.version);
        setUsername(d.username || "");
      })
      .catch(() => {});
    settingsApi
      .getReportingDebugConfig()
      .then(setReportingDebugCfg)
      .catch(() => {});
    extensionsApi
      .listExtensions()
      .then((extensions) => {
        const loaded = (id) =>
          extensions.some(
            (extension) =>
              extension.id === id && extension.enabled && extension.status === "loaded",
          );
        setBenchmarkLabCfg({ panel_enabled: loaded("aespa.benchmarking") });
        setPlanUsageCfg({ panel_enabled: loaded(PLAN_USAGE_EXTENSION_ID) });
      })
      .catch(() => {});
  }, []);

  return {
    appVersion,
    username,
    showUsername,
    setShowUsername,
    showSystems,
    setShowSystems,
    showDeepScan,
    setShowDeepScan,
    showTeamScan,
    setShowTeamScan,
    showSastDeepScan,
    setShowSastDeepScan,
    reportingDebugCfg,
    setReportingDebugCfg,
    benchmarkLabCfg,
    setBenchmarkLabCfg,
    planUsageCfg,
    setPlanUsageCfg,
  };
}
