import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect } from "react";

import { IconCheck } from "../../shared/ui/Icons.jsx";
import { Tabs } from "../../shared/ui/Tabs.tsx";
import {
  DEFAULT_SITEMAP_GRAVITY,
  getSitemapGravity,
  setSitemapGravity,
} from "../../shared/lib/sitemapPreferences.js";

const SYSTEM_SETTINGS_TABS = [
  { key: "features", label: "Feature Visibility" },
  { key: "debug", label: "Debug Settings" },
];

export function DebugPage({
  showUsername,
  setShowUsername,
  showSystems,
  setShowSystems,
  showDeepScan,
  setShowDeepScan,
  username,
  reportingDebugCfg,
  setReportingDebugCfg,
  benchmarkLabCfg,
  setBenchmarkLabCfg,
}) {
  const [tab, setTab] = useState("features");
  const [browserCfg, setBrowserCfg] = useState(null);
  const [browserSaving, setBrowserSaving] = useState(false);
  const [browserSaved, setBrowserSaved] = useState(false);
  const [browserError, setBrowserError] = useState(null);
  const [repSaving, setRepSaving] = useState(false);
  const [repSaved, setRepSaved] = useState(false);
  const [repError, setRepError] = useState(null);
  const [benchmarkSaving, setBenchmarkSaving] = useState(false);
  const [benchmarkSaved, setBenchmarkSaved] = useState(false);
  const [benchmarkError, setBenchmarkError] = useState(null);
  const [cfAud, setCfAud] = useState("");
  const [cfSaving, setCfSaving] = useState(false);
  const [cfSaved, setCfSaved] = useState(false);
  const [cfError, setCfError] = useState(null);
  const [sitemapGravity, setSitemapGravityState] = useState(getSitemapGravity);
  useEffect(() => {
    (async () => {
      try {
        setBrowserCfg(await settingsApi.getBrowserDebugConfig());
      } catch (e) {
        setBrowserError(e.message);
      }
    })();
    (async () => {
      try {
        setBenchmarkLabCfg(await settingsApi.getBenchmarkLabConfig());
      } catch (e) {
        setBenchmarkError(e.message);
      }
    })();
    (async () => {
      try {
        setReportingDebugCfg(await settingsApi.getReportingDebugConfig());
      } catch (e) {
        setRepError(e.message);
      }
    })();
    (async () => {
      try {
        setCfAud((await settingsApi.getCloudflareAccessConfig()).audience || "");
      } catch (e) {
        setCfError(e.message);
      }
    })();
  }, [setBenchmarkLabCfg, setReportingDebugCfg]);
  const toggleBenchmarkLab = async (patch) => {
    const base = benchmarkLabCfg || {
      panel_enabled: false,
      default_match_mode: "assisted",
      default_repetitions: 1,
    };
    setBenchmarkSaving(true);
    setBenchmarkSaved(false);
    setBenchmarkError(null);
    try {
      const updated = await settingsApi.upsertBenchmarkLabConfig({ ...base, ...patch });
      setBenchmarkLabCfg(updated);
      setBenchmarkSaved(true);
    } catch (e) {
      setBenchmarkError(e.message);
    } finally {
      setBenchmarkSaving(false);
    }
  };
  const saveCloudflareAud = async (e) => {
    e.preventDefault();
    setCfSaved(false);
    setCfSaving(true);
    setCfError(null);
    try {
      const updated = await settingsApi.upsertCloudflareAccessConfig({
        audience: cfAud.trim() || null,
      });
      setCfAud(updated.audience || "");
      setCfSaved(true);
    } catch (e) {
      setCfError(e.message);
    } finally {
      setCfSaving(false);
    }
  };
  const toggleReportingDebug = async (patch) => {
    const base = reportingDebugCfg || {
      capture_enabled: false,
      panel_enabled: false,
    };
    setRepSaving(true);
    setRepSaved(false);
    setRepError(null);
    try {
      const updated = await settingsApi.upsertReportingDebugConfig({
        ...base,
        ...patch,
      });
      setReportingDebugCfg(updated);
      setRepSaved(true);
    } catch (e) {
      setRepError(e.message);
    } finally {
      setRepSaving(false);
    }
  };
  const toggleBrowserDebug = async (patch) => {
    const base = browserCfg || {
      browser_engine: "playwright_chromium",
      browser_visible: false,
    };
    setBrowserSaving(true);
    setBrowserSaved(false);
    setBrowserError(null);
    try {
      const updated = await settingsApi.upsertBrowserDebugConfig({
        ...base,
        ...patch,
      });
      setBrowserCfg(updated);
      setBrowserSaved(true);
    } catch (e) {
      setBrowserError(e.message);
    } finally {
      setBrowserSaving(false);
    }
  };
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">System Settings</div>
      </div>
      <div className="content scroll-content settings-content">
        <Tabs
          label="System settings"
          className="tab-bar settings-tab-bar"
          tabs={SYSTEM_SETTINGS_TABS}
          value={tab}
          onChange={setTab}
        />
        {tab === "features" && !browserCfg && !browserError && (
          <div className="subtle">Loading…</div>
        )}

        {tab === "features" && (
          <div className="card" style={{ marginTop: 16, maxWidth: 680 }}>
            <div className="form-section-title">Browser</div>
            <div className="field-hint" style={{ marginBottom: 12 }}>
              Choose which Chromium build powers crawls, scans, and browser-based testing. The
              bundled Playwright Chromium build is the default. System Chrome uses the stable Google
              Chrome installation on the machine running AESPA.
            </div>
            {browserError && <div className="alert error">{browserError}</div>}
            {browserCfg && (
              <>
                <div className="form-row">
                  <label className="form-label" htmlFor="browser-engine">
                    Browser engine
                  </label>
                  <select
                    id="browser-engine"
                    className="form-input"
                    value={browserCfg.browser_engine}
                    disabled={browserSaving}
                    onChange={(e) => toggleBrowserDebug({ browser_engine: e.target.value })}
                  >
                    <option value="playwright_chromium">
                      Bundled Playwright Chromium (default)
                    </option>
                    <option value="system_chrome">System installed Google Chrome</option>
                  </select>
                </div>
                <label className="toggle-row" style={{ marginTop: 12 }}>
                  <input
                    type="checkbox"
                    checked={browserCfg.browser_visible ?? false}
                    disabled={browserSaving || browserCfg.graphical_display_available === false}
                    title={
                      browserCfg.graphical_display_available
                        ? undefined
                        : browserCfg.graphical_display_message
                    }
                    onChange={(e) => toggleBrowserDebug({ browser_visible: e.target.checked })}
                  />
                  <span>Make browser visible to user</span>
                </label>
                {browserCfg.graphical_display_available === false && (
                  <div className="alert warning" style={{ marginTop: 8 }}>
                    {browserCfg.graphical_display_message}
                  </div>
                )}
                <div className="field-hint" style={{ marginTop: 8 }}>
                  Leave this off for normal headless operation. Turn it on when AESPA is running on
                  a desktop with a graphical display and you need to watch browser activity. Guided
                  login remains visible when it needs user interaction.
                </div>
                {browserSaved && (
                  <div className="save-confirm" style={{ marginTop: 8 }}>
                    <IconCheck /> Saved
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {tab === "features" && (
          <div
            className="card"
            style={{
              marginTop: 16,
              maxWidth: 680,
            }}
          >
            <div className="form-section-title">Reporting Lab</div>
            <div
              className="field-hint"
              style={{
                marginBottom: 12,
              }}
            >
              Capture reporting LLM messages from real scans and expose the replay lab in the
              sidebar. Captures include final reporting batches and during-scan writeups, and are
              stored in a separate SQLite database next to the main AESPA database.
            </div>
            {repError && <div className="alert error">{repError}</div>}
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={reportingDebugCfg?.capture_enabled ?? false}
                disabled={repSaving}
                onChange={(e) =>
                  toggleReportingDebug({
                    capture_enabled: e.target.checked,
                  })
                }
              />
              <span>Capture reporting LLM messages during scans</span>
            </label>
            <label
              className="toggle-row"
              style={{
                marginTop: 8,
              }}
            >
              <input
                type="checkbox"
                checked={reportingDebugCfg?.panel_enabled ?? false}
                disabled={repSaving}
                onChange={(e) =>
                  toggleReportingDebug({
                    panel_enabled: e.target.checked,
                  })
                }
              />
              <span>Show Reporting Lab in the sidebar</span>
            </label>
            {repSaved && (
              <div
                className="save-confirm"
                style={{
                  marginTop: 8,
                }}
              >
                <IconCheck /> Saved
              </div>
            )}
          </div>
        )}

        {tab === "features" && (
          <div className="card" style={{ marginTop: 16, maxWidth: 680 }}>
            <div className="form-section-title">Benchmark Lab</div>
            <div className="field-hint" style={{ marginBottom: 12 }}>
              Evaluate completed SAST scans against separately stored ground truth. Ground truth is
              never exposed to scanner agents or ordinary SAST analysis APIs.
            </div>
            {benchmarkError && <div className="alert error">{benchmarkError}</div>}
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={benchmarkLabCfg?.panel_enabled ?? false}
                disabled={benchmarkSaving}
                onChange={(e) => toggleBenchmarkLab({ panel_enabled: e.target.checked })}
              />
              <span>Show Benchmark Lab in the sidebar</span>
            </label>
            {benchmarkSaved && (
              <div className="save-confirm" style={{ marginTop: 8 }}>
                <IconCheck /> Saved
              </div>
            )}
          </div>
        )}

        {tab === "features" && (
          <div
            className="card"
            style={{
              marginTop: 16,
              maxWidth: 680,
            }}
          >
            <div className="form-section-title">Experimental Features</div>
            <div
              className="field-hint"
              style={{
                marginBottom: 12,
              }}
            >
              These features are still being tested. Enable them when you want to use them.
            </div>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={showSystems ?? false}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setShowSystems(checked);
                  try {
                    localStorage.setItem("aespa_show_systems", String(checked));
                  } catch {}
                }}
              />
              <span>Systems scanning</span>
            </label>
            <div className="field-hint" style={{ marginTop: 6 }}>
              Show multi-repository system campaign scanning under Targets in the sidebar.
            </div>
            <label className="toggle-row" style={{ marginTop: 16 }}>
              <input
                type="checkbox"
                checked={showDeepScan ?? false}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setShowDeepScan(checked);
                  try {
                    localStorage.setItem("aespa_show_deep_scan", String(checked));
                  } catch {}
                }}
              />
              <span>DAST Deep Scan Mode</span>
            </label>
            <div className="field-hint" style={{ marginTop: 6 }}>
              Show Deep mode for web DAST runs and its settings under Agent Settings.
            </div>
          </div>
        )}

        {tab === "debug" && (
          <div
            className="card"
            style={{
              marginTop: 16,
              maxWidth: 680,
            }}
          >
            <div className="form-section-title">Sitemap Graph</div>
            <div
              className="field-hint"
              style={{
                marginBottom: 12,
              }}
            >
              Controls how strongly nodes in the sitemap graph (Sites → run → Sitemap tab) are
              pulled toward the centre. Lower values let the layout spread out more; higher values
              pull it in tighter. Default is {DEFAULT_SITEMAP_GRAVITY}.
            </div>
            <div className="form-row">
              <label className="form-label">Gravity ({sitemapGravity.toFixed(2)})</label>
              <input
                type="range"
                min={0}
                max={0.2}
                step={0.01}
                value={sitemapGravity}
                onChange={(e) => {
                  const value = parseFloat(e.target.value);
                  setSitemapGravityState(value);
                  setSitemapGravity(value);
                }}
              />
            </div>
            <button
              className="btn ghost sm"
              type="button"
              style={{ marginTop: 8 }}
              onClick={() => {
                setSitemapGravityState(DEFAULT_SITEMAP_GRAVITY);
                setSitemapGravity(DEFAULT_SITEMAP_GRAVITY);
              }}
            >
              Reset to default
            </button>
          </div>
        )}

        {tab === "debug" && (
          <div
            className="card"
            style={{
              marginTop: 16,
              maxWidth: 680,
            }}
          >
            <div className="form-section-title">Cloudflare Access</div>
            <div
              className="field-hint"
              style={{
                marginBottom: 12,
              }}
            >
              Show the authenticated user's email/username above the application version on the
              bottom left of the sidebar.
            </div>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={showUsername}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setShowUsername(checked);
                  try {
                    localStorage.setItem("aespa_show_username", String(checked));
                  } catch {}
                }}
              />
              <span>Show Username in Sidebar</span>
            </label>
            {showUsername && (
              <div
                className="field-hint"
                style={{
                  marginTop: 8,
                }}
              >
                Current verified username:{" "}
                <strong className="mono">
                  {username || "None (will only be displayed in sidebar if verified)"}
                </strong>
              </div>
            )}
            <div
              className="field-hint"
              style={{
                marginTop: 16,
                marginBottom: 8,
              }}
            >
              <strong>Application Audience (AUD) tag.</strong> When set, the Cloudflare Access JWT
              is verified against this AUD so only tokens issued for this application are accepted.
              Leave empty to skip the audience check (legacy behaviour — any Cloudflare Access
              tenant's token is accepted).
            </div>
            {cfError && <div className="alert error">{cfError}</div>}
            <form onSubmit={saveCloudflareAud}>
              <div className="form-row">
                <label className="form-label">Audience (AUD)</label>
                <input
                  className="form-input mono"
                  type="text"
                  placeholder="e.g. 64-char hex AUD from the Access application"
                  value={cfAud}
                  disabled={cfSaving}
                  onInput={(e) => {
                    setCfSaved(false);
                    setCfAud(e.target.value);
                  }}
                />
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginTop: 8,
                }}
              >
                <button className="btn btn-primary" type="submit" disabled={cfSaving}>
                  {cfSaving ? "Saving…" : "Save"}
                </button>
                {cfSaved && (
                  <span className="save-confirm">
                    <IconCheck /> Saved
                  </span>
                )}
              </div>
            </form>
          </div>
        )}
      </div>
    </>
  );
}
