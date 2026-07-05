import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, ScanModeDefinitions, csv, policyToForm } from "../../lib/policy";


export function ScannerPolicyFields({
  form,
  upd,
  disabled = false
}) {
  return <>
    <div className="form-section-title">Mode</div>
    <div className="field">
      <label>Scan mode</label>
      <select className="select" disabled={disabled} value={form.scan_mode} onChange={e => upd({
        scan_mode: e.target.value
      })}>
        {SCAN_MODE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
    </div>
    <ScanModeDefinitions selected={form.scan_mode} />
    <div className="divider" />
    <div className="form-section-title">Limits</div>
    <div className="two-col">
      <div className="field"><label>Max probes per page</label>
        <input type="number" disabled={disabled} min="0" max="500" value={form.max_probes_per_page} onChange={e => upd({
          max_probes_per_page: e.target.value
        })} /></div>
      <div className="field"><label>Request timeout (seconds)</label>
        <input type="number" disabled={disabled} min="1" max="120" step="0.5" value={form.request_timeout_s} onChange={e => upd({
          request_timeout_s: e.target.value
        })} /></div>
      <div className="field"><label>Minimum delay (seconds)</label>
        <input type="number" disabled={disabled} min="0" max="60" step="0.05" value={form.min_delay_s} onChange={e => upd({
          min_delay_s: e.target.value
        })} /></div>
      <div className="field"><label>Max request body bytes</label>
        <input type="number" disabled={disabled} min="0" max={10 * 1024 * 1024} value={form.max_request_body_bytes} onChange={e => upd({
          max_request_body_bytes: e.target.value
        })} /></div>
    </div>
    <div className="field"><label>Response body read limit bytes</label>
      <input type="number" disabled={disabled} min="1024" max={10 * 1024 * 1024} value={form.response_body_read_limit_bytes} onChange={e => upd({
        response_body_read_limit_bytes: e.target.value
      })} /></div>
    <div className="divider" />
    <div className="form-section-title">Scope</div>
    <div className="two-col">
      <div className="field"><label>Allowed schemes</label>
        <input type="text" disabled={disabled} value={form.allowed_schemes} onChange={e => upd({
          allowed_schemes: e.target.value
        })} /></div>
      <div className="field"><label>Blocked headers</label>
        <input type="text" disabled={disabled} value={form.blocked_headers} onChange={e => upd({
          blocked_headers: e.target.value
        })} /></div>
    </div>
    <label className="toggle-row">
      <input type="checkbox" disabled={disabled} checked={form.follow_redirects} onChange={e => upd({
        follow_redirects: e.target.checked
      })} />
      <span>Follow redirects</span>
    </label>
    <label className="toggle-row">
      <input type="checkbox" disabled={disabled} checked={form.allow_subdomains} onChange={e => upd({
        allow_subdomains: e.target.checked
      })} />
      <span>Allow subdomains of the crawled host</span>
    </label>
    <div className="divider" />
    <div className="form-section-title">Methods</div>
    <div className="two-col">
      <div className="field"><label>Passive</label>
        <input type="text" disabled={disabled} value={form.methods_passive} onChange={e => upd({
          methods_passive: e.target.value
        })} /></div>
      <div className="field"><label>Safe active</label>
        <input type="text" disabled={disabled} value={form.methods_safe_active} onChange={e => upd({
          methods_safe_active: e.target.value
        })} /></div>
      <div className="field"><label>Aggressive</label>
        <input type="text" disabled={disabled} value={form.methods_aggressive} onChange={e => upd({
          methods_aggressive: e.target.value
        })} /></div>
      <div className="field"><label>Destructive</label>
        <input type="text" disabled={disabled} value={form.methods_destructive} onChange={e => upd({
          methods_destructive: e.target.value
        })} /></div>
    </div></>;
}
