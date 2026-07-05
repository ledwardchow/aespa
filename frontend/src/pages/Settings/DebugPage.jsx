import { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { IconApis, IconPlus, IconCheck, IconStop, IconChevronLeft, IconBug, IconSend } from "../../components/Icons";


export function DebugPage({
  showUsername,
  setShowUsername,
  username,
  reportingDebugCfg,
  setReportingDebugCfg
}) {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [hdrCfg, setHdrCfg] = useState(null);
  const [hdrForm, setHdrForm] = useState({
    header_name: "",
    header_value: ""
  });
  const [hdrSaving, setHdrSaving] = useState(false);
  const [hdrSaved, setHdrSaved] = useState(false);
  const [hdrError, setHdrError] = useState(null);
  const [repSaving, setRepSaving] = useState(false);
  const [repSaved, setRepSaved] = useState(false);
  const [repError, setRepError] = useState(null);
  const [cfAud, setCfAud] = useState("");
  const [cfSaving, setCfSaving] = useState(false);
  const [cfSaved, setCfSaved] = useState(false);
  const [cfError, setCfError] = useState(null);
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
        const h = await api.getGlobalHttpHeader();
        setHdrCfg(h);
        setHdrForm({
          header_name: h.header_name || "",
          header_value: h.header_value || ""
        });
      } catch (e) {
        setHdrError(e.message);
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
  const saveHeader = async e => {
    e.preventDefault();
    setHdrSaved(false);
    setHdrSaving(true);
    setHdrError(null);
    try {
      const updated = await api.upsertGlobalHttpHeader({
        header_name: hdrForm.header_name.trim() || null,
        header_value: hdrForm.header_value.trim() || null
      });
      setHdrCfg(updated);
      setHdrForm({
        header_name: updated.header_name || "",
        header_value: updated.header_value || ""
      });
      setHdrSaved(true);
    } catch (e) {
      setHdrError(e.message);
    } finally {
      setHdrSaving(false);
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
  return <>
    <div className="topbar">
      <div className="topbar-title">Debug</div>
    </div>
    <div className="content scroll-content">
      {!cfg && !hdrCfg && !error && !hdrError && <div className="subtle">Loading…</div>}

      <div className="card">
        <div className="form-section-title">Global Extra HTTP Header</div>
        <div className="field-hint" style={{
          marginBottom: 12
        }}>
          Inject an additional HTTP header into every request made by the scanner and crawler
          (Playwright and HTTPX). Does not affect requests sent to LLMs. Leave the header name
          empty to disable.
        </div>
        {hdrError && <div className="alert error">{hdrError}</div>}
        {hdrCfg !== null && <form onSubmit={saveHeader}>
            <div className="form-row">
              <label className="form-label">Header Name</label>
              <input className="form-input" type="text" placeholder="e.g. X-Debug-Token" value={hdrForm.header_name} disabled={hdrSaving} onInput={e => {
              setHdrSaved(false);
              setHdrForm(f => ({
                ...f,
                header_name: e.target.value
              }));
            }} />
            </div>
            <div className="form-row">
              <label className="form-label">Header Value</label>
              <input className="form-input" type="text" placeholder="e.g. my-secret-value" value={hdrForm.header_value} disabled={hdrSaving} onInput={e => {
              setHdrSaved(false);
              setHdrForm(f => ({
                ...f,
                header_value: e.target.value
              }));
            }} />
            </div>
            <div style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginTop: 8
          }}>
              <button className="btn btn-primary" type="submit" disabled={hdrSaving}>
                {hdrSaving ? "Saving…" : "Save"}
              </button>
              {hdrSaved && <span className="save-confirm"><IconCheck /> Saved</span>}
            </div>
          </form>}
      </div>

      {error && <div className="alert error">{error}</div>}
      {cfg && <div className="card">
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
        marginTop: 16
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
        marginTop: 16
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
