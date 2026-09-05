import * as settingsApi from "../shared/api/settings.js";
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
  const [showApplications, setShowApplications] = useState(() => {
    try {
      const val = localStorage.getItem("aespa_show_applications");
      return val === null ? true : val === "true";
    } catch {
      return true;
    }
  });
  const [reportingDebugCfg, setReportingDebugCfg] = useState(null);
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
  }, []);

  return {
    appVersion,
    username,
    showUsername,
    setShowUsername,
    showApplications,
    setShowApplications,
    reportingDebugCfg,
    setReportingDebugCfg,
  };
}
