import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";
import { DEFAULT_SITEMAP_GRAVITY, getSitemapGravity, setSitemapGravity } from "../../lib/utilities";


export function DebugPage({
  showUsername,
  setShowUsername,
  showApplications,
  setShowApplications,
  username,
  reportingDebugCfg,
  setReportingDebugCfg
}) {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [browserCfg, setBrowserCfg] = useState(null);
  const [browserSaving, setBrowserSaving] = useState(false);
  const [browserSaved, setBrowserSaved] = useState(false);
  const [browserError, setBrowserError] = useState(null);
  const [repSaving, setRepSaving] = useState(false);
  const [repSaved, setRepSaved] = useState(false);
  const [repError, setRepError] = useState(null);
  const [cfAud, setCfAud] = useState("");
  const [cfSaving, setCfSaving] = useState(false);
  const [cfSaved, setCfSaved] = useState(false);
  const [cfError, setCfError] = useState(null);
  const [sitemapGravity, setSitemapGravityState] = useState(getSitemapGravity);
  useEffect(() => {
    (async () => {
      try {
        setCfg(await api.getSpecialistAgentConfig());
      } catch (e) {
        setError(e.message);
      }
    })();
    (async () => {
      try {
        setBrowserCfg(await api.getBrowserDebugConfig());
      } catch (e) {
        setBrowserError(e.message);
      }
    })();
    (async () => {
      try {
        setReportingDebugCfg(await api.getReportingDebugConfig());
      } catch (e) {
        setRepError(e.message);
      }
    })();
    (async () => {
      try {
        setCfAud((await api.getCloudflareAccessConfig()).audience || "");
      } catch (e) {
        setCfError(e.message);
      }
    })();
  }, [setReportingDebugCfg]);
  const saveCloudflareAud = async e => {
    e.preventDefault();
    setCfSaved(false);
    setCfSaving(true);
    setCfError(null);
    try {
      const updated = await api.upsertCloudflareAccessConfig({
        audience: cfAud.trim() || null
      });
      setCfAud(updated.audience || "");
      setCfSaved(true);
    } catch (e) {
      setCfError(e.message);
    } finally {
      setCfSaving(false);
    }
  };
  const toggle = async checked => {
    setSaved(false);
    setSaving(true);
    setError(null);
    try {
      const updated = await api.upsertSpecialistAgentConfig({
        ...cfg,
        trigger_specialist_on_burp: checked
      });
      setCfg(updated);
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const toggleReportingDebug = async patch => {
    const base = reportingDebugCfg || {
      capture_enabled: false,
      panel_enabled: false
    };
    setRepSaving(true);
    setRepSaved(false);
    setRepError(null);
    try {
      const updated = await api.upsertReportingDebugConfig({
        ...base,
        ...patch
      });
      setReportingDebugCfg(updated);
      setRepSaved(true);
    } catch (e) {
      setRepError(e.message);
    } finally {
      setRepSaving(false);
    }
  };
  const toggleBrowserDebug = async patch => {
    const base = browserCfg || {
      browser_engine: "playwright_chromium",
      browser_visible: false
    };
    setBrowserSaving(true);
    setBrowserSaved(false);
    setBrowserError(null);
    try {
      const updated = await api.upsertBrowserDebugConfig({
        ...base,
        ...patch
      });
      setBrowserCfg(updated);
      setBrowserSaved(true);
    } catch (e) {
      setBrowserError(e.message);
    } finally {
      setBrowserSaving(false);
    }
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">System Settings</div>
    </div>
    <div className="content scroll-content">
      {!cfg && !browserCfg && !error && !browserError && <div className="subtle">Loading…</div>}

      <div className="card" style={{ marginTop: 16, maxWidth: 680 }}>
        <div className="form-section-title">Browser</div>
        <div className="field-hint" style={{ marginBottom: 12 }}>
          Choose which Chromium build powers crawls, scans, and browser-based testing.
          The bundled Playwright Chromium build is the default. System Chrome uses the
          stable Google Chrome installation on the machine running AESPA.
        </div>
        {browserError && <div className="alert error">{browserError}</div>}
        {browserCfg && <>
          <div className="form-row">
            <label className="form-label" htmlFor="browser-engine">Browser engine</label>
            <select
              id="browser-engine"
              className="form-input"
              value={browserCfg.browser_engine}
              disabled={browserSaving}
              onChange={e => toggleBrowserDebug({ browser_engine: e.target.value })}
            >
              <option value="playwright_chromium">Bundled Playwright Chromium (default)</option>
              <option value="system_chrome">System installed Google Chrome</option>
            </select>
          </div>
          <label className="toggle-row" style={{ marginTop: 12 }}>
            <input
              type="checkbox"
              checked={browserCfg.browser_visible ?? false}
              disabled={browserSaving}
              onChange={e => toggleBrowserDebug({ browser_visible: e.target.checked })}
            />
            <span>Make browser visible to user</span>
          </label>
          <div className="field-hint" style={{ marginTop: 8 }}>
            Leave this off for normal headless operation. Turn it on when AESPA is
            running on a desktop with a graphical display and you need to watch browser activity.
            Guided login remains visible when it needs user interaction.
          </div>
          {browserSaved && <div className="save-confirm" style={{ marginTop: 8 }}><IconCheck /> Saved</div>}
        </>}
      </div>

      {error && <div className="alert error">{error}</div>}
      {cfg && <div className="card" style={{ marginTop: 16, maxWidth: 680 }}>
          <div className="form-section-title">Specialist Agent</div>
          <label className="toggle-row">
            <input type="checkbox" checked={cfg.trigger_specialist_on_burp ?? false} disabled={saving} onChange={e => toggle(e.target.checked)} />
            <span>Trigger a Specialist Agent whenever a Burp active scan is triggered</span>
          </label>
          <div className="field-hint">
            When enabled, a specialist agent is dispatched immediately alongside every Burp active scan,
            independently investigating the same URL. Use this to force specialist agents to fire for
            debugging purposes.
          </div>
          {saved && <div className="save-confirm" style={{
          marginTop: 8
        }}><IconCheck /> Saved</div>}
        </div>}

      <div className="card" style={{
        marginTop: 16,
        maxWidth: 680
      }}>
        <div className="form-section-title">Reporting Lab</div>
        <div className="field-hint" style={{
          marginBottom: 12
        }}>
          Capture reporting LLM messages from real scans and expose the replay lab in the sidebar.
          Captures include final reporting batches and during-scan writeups, and are stored
          in a separate SQLite database next to the main AESPA database.
        </div>
        {repError && <div className="alert error">{repError}</div>}
        <label className="toggle-row">
          <input type="checkbox" checked={reportingDebugCfg?.capture_enabled ?? false} disabled={repSaving} onChange={e => toggleReportingDebug({
            capture_enabled: e.target.checked
          })} />
          <span>Capture reporting LLM messages during scans</span>
        </label>
        <label className="toggle-row" style={{
          marginTop: 8
        }}>
          <input type="checkbox" checked={reportingDebugCfg?.panel_enabled ?? false} disabled={repSaving} onChange={e => toggleReportingDebug({
            panel_enabled: e.target.checked
          })} />
          <span>Show Reporting Lab in the sidebar</span>
        </label>
        {repSaved && <div className="save-confirm" style={{
          marginTop: 8
        }}><IconCheck /> Saved</div>}
      </div>

      <div className="card" style={{
        marginTop: 16,
        maxWidth: 680
      }}>
        <div className="form-section-title">Applications</div>
        <div className="field-hint" style={{
          marginBottom: 12
        }}>
          Show multi-repository application campaign scanning features under Targets in the sidebar.
        </div>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={showApplications ?? false}
            onChange={e => {
              const checked = e.target.checked;
              setShowApplications(checked);
              try {
                localStorage.setItem("aespa_show_applications", String(checked));
              } catch {}
            }}
          />
          <span>Show Applications scanning feature</span>
        </label>
      </div>

      <div className="card" style={{
        marginTop: 16,
        maxWidth: 680
      }}>
        <div className="form-section-title">Sitemap Graph</div>
        <div className="field-hint" style={{
          marginBottom: 12
        }}>
          Controls how strongly nodes in the sitemap graph (Sites → run → Sitemap tab) are
          pulled toward the centre. Lower values let the layout spread out more; higher
          values pull it in tighter. Default is {DEFAULT_SITEMAP_GRAVITY}.
        </div>
        <div className="form-row">
          <label className="form-label">Gravity ({sitemapGravity.toFixed(2)})</label>
          <input
            type="range"
            min={0}
            max={0.2}
            step={0.01}
            value={sitemapGravity}
            onChange={e => {
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

      <div className="card" style={{
        marginTop: 16,
        maxWidth: 680
      }}>
        <div className="form-section-title">Cloudflare Access</div>
        <div className="field-hint" style={{
          marginBottom: 12
        }}>
          Show the authenticated user's email/username above the application version on the bottom left of the sidebar.
        </div>
        <label className="toggle-row">
          <input type="checkbox" checked={showUsername} onChange={e => {
            const checked = e.target.checked;
            setShowUsername(checked);
            try {
              localStorage.setItem("aespa_show_username", String(checked));
            } catch  {}
          }} />
          <span>Show Username in Sidebar</span>
        </label>
        {showUsername && <div className="field-hint" style={{
          marginTop: 8
        }}>
            Current verified username: <strong className="mono">{username || "None (will only be displayed in sidebar if verified)"}</strong>
          </div>}
        <div className="field-hint" style={{
          marginTop: 16,
          marginBottom: 8
        }}>
          <strong>Application Audience (AUD) tag.</strong> When set, the Cloudflare Access
          JWT is verified against this AUD so only tokens issued for this application are
          accepted. Leave empty to skip the audience check (legacy behaviour — any
          Cloudflare Access tenant's token is accepted).
        </div>
        {cfError && <div className="alert error">{cfError}</div>}
        <form onSubmit={saveCloudflareAud}>
          <div className="form-row">
            <label className="form-label">Audience (AUD)</label>
            <input className="form-input mono" type="text" placeholder="e.g. 64-char hex AUD from the Access application" value={cfAud} disabled={cfSaving} onInput={e => {
              setCfSaved(false);
              setCfAud(e.target.value);
            }} />
          </div>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginTop: 8
          }}>
            <button className="btn btn-primary" type="submit" disabled={cfSaving}>
              {cfSaving ? "Saving…" : "Save"}
            </button>
            {cfSaved && <span className="save-confirm"><IconCheck /> Saved</span>}
          </div>
        </form>
      </div>
    </div></>;
}
