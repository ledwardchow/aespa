import { useState, useEffect } from "react";
import { ScannerPolicyFields } from "./ScannerPolicyFields";
import { api } from "../../lib/api";
import { policyToForm, policyPayload, SCAN_MODE_OPTIONS } from "../../lib/policy";
import { IconCheck } from "../../components/Icons";


const SCAN_MODE_DETAILS = {
  passive: "Read-only requests for low-impact reconnaissance.",
  safe_active: "Active checks that avoid delete-capable methods.",
  aggressive: "Broader active testing, including update-style methods.",
  destructive: "Testing that may delete data or trigger irreversible actions.",
};

const METHOD_FIELDS = {
  passive: "methods_passive",
  safe_active: "methods_safe_active",
  aggressive: "methods_aggressive",
  destructive: "methods_destructive",
};


function GlobalPolicyFields({ form, upd }) {
  return <>
    <section className="policy-group">
      <div className="form-section-title">Scan behaviour</div>
      <div className="policy-section-copy">
        Choose how much active testing to perform. The selected mode determines which HTTP method list the scan uses.
      </div>
      <div className="scan-mode-picker">
        <div className="field">
          <label htmlFor="global-scan-mode">Scan mode</label>
          <select id="global-scan-mode" className="select" value={form.scan_mode} onChange={e => upd({
            scan_mode: e.target.value
          })}>
            {SCAN_MODE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        <div className="scan-mode-summary" aria-live="polite">
          <span className="scan-mode-summary-label">Currently selected</span>
          <strong>{SCAN_MODE_OPTIONS.find(([value]) => value === form.scan_mode)?.[1] || form.scan_mode}</strong>
          <span>{SCAN_MODE_DETAILS[form.scan_mode]}</span>
        </div>
      </div>
      <div className="policy-subsection">
        <div className="policy-subsection-title">HTTP methods by mode</div>
        <div className="field-hint">
          Enter comma-separated methods, for example GET, POST. The highlighted list is active; the other lists are saved for when you switch modes.
        </div>
        <div className="scan-method-grid">
          {SCAN_MODE_OPTIONS.map(([value, label]) => {
            const field = METHOD_FIELDS[value];
            const selected = form.scan_mode === value;
            const inputId = `global-methods-${value}`;
            return <div className={"scan-method-card" + (selected ? " active" : "")} key={value}>
              <div className="scan-method-card-header">
                <label htmlFor={inputId}>{label}</label>
                {selected && <span className="scan-method-active">In use</span>}
              </div>
              <input id={inputId} type="text" value={form[field]} onChange={e => upd({
                [field]: e.target.value
              })} aria-describedby={`${inputId}-hint`} />
              <div id={`${inputId}-hint`} className="field-hint">{SCAN_MODE_DETAILS[value]}</div>
            </div>;
          })}
        </div>
      </div>
    </section>

    <section className="policy-group">
      <div className="form-section-title">Request limits</div>
      <div className="policy-section-copy">
        These limits apply to the scan as a whole. They are independent of the selected mode and its HTTP methods.
      </div>
      <div className="two-col">
        <div className="field"><label htmlFor="global-max-probes">Maximum probes per page</label>
          <input id="global-max-probes" type="number" min="0" max="500" value={form.max_probes_per_page} onChange={e => upd({
            max_probes_per_page: e.target.value
          })} /></div>
        <div className="field"><label htmlFor="global-request-timeout">Request timeout (seconds)</label>
          <input id="global-request-timeout" type="number" min="1" max="120" step="0.5" value={form.request_timeout_s} onChange={e => upd({
            request_timeout_s: e.target.value
          })} /></div>
        <div className="field"><label htmlFor="global-min-delay">Minimum delay between requests (seconds)</label>
          <input id="global-min-delay" type="number" min="0" max="60" step="0.05" value={form.min_delay_s} onChange={e => upd({
            min_delay_s: e.target.value
          })} /></div>
        <div className="field"><label htmlFor="global-max-request-body">Maximum request body size (bytes)</label>
          <input id="global-max-request-body" type="number" min="0" max={10 * 1024 * 1024} value={form.max_request_body_bytes} onChange={e => upd({
            max_request_body_bytes: e.target.value
          })} /></div>
      </div>
      <div className="field"><label htmlFor="global-response-body-limit">Maximum response data read (bytes)</label>
        <input id="global-response-body-limit" type="number" min="1024" max={10 * 1024 * 1024} value={form.response_body_read_limit_bytes} onChange={e => upd({
          response_body_read_limit_bytes: e.target.value
        })} /></div>
    </section>

    <section className="policy-group">
      <div className="form-section-title">Scope &amp; request handling</div>
      <div className="policy-section-copy">
        Control which URL types the scanner can follow and how it handles requests and redirects.
      </div>
      <div className="two-col">
        <div className="field"><label htmlFor="global-allowed-schemes">Allowed URL schemes</label>
          <input id="global-allowed-schemes" type="text" value={form.allowed_schemes} onChange={e => upd({
            allowed_schemes: e.target.value
          })} />
          <div className="field-hint">Comma-separated, for example: http, https</div>
        </div>
        <div className="field"><label htmlFor="global-blocked-headers">Blocked request headers</label>
          <input id="global-blocked-headers" type="text" value={form.blocked_headers} onChange={e => upd({
            blocked_headers: e.target.value
          })} />
          <div className="field-hint">Comma-separated header names, for example: host, cookie</div>
        </div>
      </div>
      <label className="toggle-row">
        <input type="checkbox" checked={form.follow_redirects} onChange={e => upd({
          follow_redirects: e.target.checked
        })} />
        <span>Follow redirects</span>
      </label>
      <label className="toggle-row">
        <input type="checkbox" checked={form.allow_subdomains} onChange={e => upd({
          allow_subdomains: e.target.checked
        })} />
        <span>Allow subdomains of the crawled host</span>
      </label>
    </section>
  </>;
}

function GlobalHttpHeadersSettings() {
  const [hdrCfg, setHdrCfg] = useState(null);
  const [hdrForm, setHdrForm] = useState([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const config = await api.getGlobalHttpHeader();
        setHdrCfg(config);
        setHdrForm(config.headers || []);
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);

  const saveHeader = async e => {
    e.preventDefault();
    setSaved(false);
    setSaving(true);
    setError(null);
    try {
      const updated = await api.upsertGlobalHttpHeader({
        headers: hdrForm
          .filter(header => header.header_name.trim() || header.header_value.trim())
          .map(header => ({
            header_name: header.header_name.trim(),
            header_value: header.header_value.trim()
          }))
      });
      setHdrCfg(updated);
      setHdrForm(updated.headers || []);
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return <section className="card global-http-headers-card">
    <div className="form-section-title">Global Extra HTTP Headers</div>
    <div className="field-hint" style={{ marginBottom: 12 }}>
      Add headers to every request made by the scanner and crawler (Playwright and HTTPX).
      These do not affect requests sent to LLMs.
    </div>
    {error && <div className="alert error">{error}</div>}
    {hdrCfg !== null && <form onSubmit={saveHeader}>
        <div className="table-wrap global-header-table-wrap">
          <table className="global-header-table">
            <colgroup>
              <col style={{ width: "34%" }} />
              <col />
              <col style={{ width: 48 }} />
            </colgroup>
            <thead>
              <tr><th>Header name</th><th>Header value</th><th aria-label="Actions" /></tr>
            </thead>
            <tbody>
              {hdrForm.length === 0 && <tr><td colSpan="3" className="subtle global-header-empty">No headers configured.</td></tr>}
              {hdrForm.map((header, index) => <tr key={index}>
                <td><input className="form-input" type="text" placeholder="e.g. X-Debug-Token" value={header.header_name} disabled={saving} onInput={e => {
                  setSaved(false);
                  setHdrForm(headers => headers.map((item, itemIndex) => itemIndex === index ? { ...item, header_name: e.target.value } : item));
                }} /></td>
                <td><input className="form-input" type="text" placeholder="e.g. my-secret-value" value={header.header_value} disabled={saving} onInput={e => {
                  setSaved(false);
                  setHdrForm(headers => headers.map((item, itemIndex) => itemIndex === index ? { ...item, header_value: e.target.value } : item));
                }} /></td>
                <td><button className="btn ghost sm" type="button" aria-label="Delete header" title="Delete header" disabled={saving} onClick={() => {
                  setSaved(false);
                  setHdrForm(headers => headers.filter((_, itemIndex) => itemIndex !== index));
                }}>×</button></td>
              </tr>)}
            </tbody>
          </table>
        </div>
        <button className="btn ghost sm" type="button" disabled={saving} style={{ marginTop: 10 }} onClick={() => {
          setSaved(false);
          setHdrForm(headers => [...headers, { header_name: "", header_value: "" }]);
        }}>Add header</button>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
          {saved && <span className="save-confirm"><IconCheck /> Saved</span>}
        </div>
      </form>}
  </section>;
}

function PolicySettings({ Fields }) {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => {
    setSaved(false);
    setForm(f => ({
      ...f,
      ...p
    }));
  };
  useEffect(() => {
    (async () => {
      try {
        setForm(policyToForm(await api.getScannerPolicy()));
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const savedPolicy = await api.upsertScannerPolicy(policyPayload(form));
      setForm(policyToForm(savedPolicy));
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  return <>
    {!form && !error && <div className="subtle">Loading…</div>}
    {error && <div className="alert error">{error}</div>}
    {form && <form className="card" onSubmit={onSubmit}>
        <Fields form={form} upd={upd} />
        <div className="divider" />
        <div className="row spread">
          <div>{saved && <span className="save-confirm"><IconCheck /> Saved</span>}</div>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : "Save policy"}</button>
        </div>
      </form>}</>;
}

export function GlobalPolicySubTabs({ tab, setTab }) {
  return <div className="activity-sub-tab-bar coverage-sub-tab-bar global-policy-sub-tab-bar" role="tablist" aria-label="Global agent settings">
      <button
        type="button"
        role="tab"
        id="global-scan-behaviour-tab"
        aria-selected={tab === "scan-behaviour"}
        aria-controls="global-scan-behaviour-panel"
        className={"activity-sub-tab-btn" + (tab === "scan-behaviour" ? " active" : "")}
        onClick={() => setTab("scan-behaviour")}
      >Scan Behaviour</button>
      <button
        type="button"
        role="tab"
        id="global-headers-tab"
        aria-selected={tab === "headers"}
        aria-controls="global-headers-panel"
        className={"activity-sub-tab-btn" + (tab === "headers" ? " active" : "")}
        onClick={() => setTab("headers")}
      >HTTP Headers</button>
  </div>;
}

export function GlobalPolicySettings({ tab = "scan-behaviour" }) {
  return <>
    {tab === "scan-behaviour" && <div id="global-scan-behaviour-panel" role="tabpanel" aria-labelledby="global-scan-behaviour-tab">
      <PolicySettings Fields={GlobalPolicyFields} />
    </div>}
    {tab === "headers" && <div id="global-headers-panel" role="tabpanel" aria-labelledby="global-headers-tab">
      <GlobalHttpHeadersSettings />
    </div>}
  </>;
}

export function ScannerPolicySettings() {
  return <PolicySettings Fields={ScannerPolicyFields} />;
}
