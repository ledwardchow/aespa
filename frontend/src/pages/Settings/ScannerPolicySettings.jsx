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
      <div className="form-section-title">Scan behavior</div>
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

export function GlobalPolicySettings() {
  return <PolicySettings Fields={GlobalPolicyFields} />;
}

export function ScannerPolicySettings() {
  return <PolicySettings Fields={ScannerPolicyFields} />;
}
