import { useState, useEffect, useCallback } from "react";
import { specialistAgentPayload, specialistAgentToForm } from "../Settings";
import { api } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { IconApis, IconPlus, IconCheck, IconStop, IconChevronLeft, IconBug, IconSend } from "../../components/Icons";


export function SpecialistAgentSettings() {
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
        setForm(specialistAgentToForm(await api.getSpecialistAgentConfig()));
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
      const savedConfig = await api.upsertSpecialistAgentConfig(specialistAgentPayload(form));
      setForm(specialistAgentToForm(savedConfig));
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const dis = form && !form.enabled;
  return <>
    {!form && !error && <div className="subtle">Loading…</div>}
    {error && <div className="alert error">{error}</div>}
    {form && <form className="card" onSubmit={onSubmit}>
        <div className="form-section-title">Specialist Agent Dispatch</div>
        <label className="toggle-row">
          <input type="checkbox" checked={form.enabled} onChange={e => upd({
          enabled: e.target.checked
        })} />
          <span>Enable specialist agent dispatch</span>
        </label>
        <div className="field-hint" style={{
        marginBottom: "12px"
      }}>
          When enabled, the Test Lead can dispatch focused specialist agents to investigate
          specific vulnerability leads in parallel. Each specialist receives an independent
          LLM session and a subset of tools (HTTP, browser, context, write_finding).
        </div>

        <div className="form-section-title">Concurrency &amp; Budget</div>
        <div className="field">
          <label>Max concurrent specialists</label>
          <input type="number" min="0" max="20" value={form.max_concurrent} disabled={dis} onChange={e => upd({
          max_concurrent: Number(e.target.value)
        })} />
          <div className="field-hint">Maximum number of specialist agents running at the same time (0 = effectively disabled). Default: 5.</div>
        </div>
        <div className="field">
          <label>Max steps per specialist</label>
          <input type="number" min="1" max="200" value={form.max_steps} disabled={dis} onChange={e => upd({
          max_steps: Number(e.target.value)
        })} />
          <div className="field-hint">Step budget for each specialist agent before it is stopped. Default: 30.</div>
        </div>
        <div className="field">
          <label>Minimum priority to dispatch</label>
          <input type="number" min="1" max="10" value={form.min_priority} disabled={dis} onChange={e => upd({
          min_priority: Number(e.target.value)
        })} />
          <div className="field-hint">Only dispatch a specialist if the lead's priority score meets this threshold (1–10). Default: 7.</div>
        </div>

        <div className="divider" />
        <div className="form-section-title">Attack Classes to Dispatch</div>
        <div className="field-hint" style={{
        marginBottom: "8px"
      }}>
          Only dispatch specialists for the selected vulnerability classes. Disable classes
          you don't need to keep token usage under control.
        </div>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_idor} disabled={dis} onChange={e => upd({
          dispatch_idor: e.target.checked
        })} />
          <span>IDOR / Broken Object Level Authorization (A01)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_auth_bypass} disabled={dis} onChange={e => upd({
          dispatch_auth_bypass: e.target.checked
        })} />
          <span>Authentication Bypass / Broken Auth (A07)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_sqli} disabled={dis} onChange={e => upd({
          dispatch_sqli: e.target.checked
        })} />
          <span>SQL Injection (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_xss} disabled={dis} onChange={e => upd({
          dispatch_xss: e.target.checked
        })} />
          <span>Cross-Site Scripting / XSS (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_business_logic} disabled={dis} onChange={e => upd({
          dispatch_business_logic: e.target.checked
        })} />
          <span>Business Logic (A04)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_ssrf} disabled={dis} onChange={e => upd({
          dispatch_ssrf: e.target.checked
        })} />
          <span>Server-Side Request Forgery / SSRF (A10)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_path_traversal} disabled={dis} onChange={e => upd({
          dispatch_path_traversal: e.target.checked
        })} />
          <span>Path Traversal / LFI (A01/A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_crypto} disabled={dis} onChange={e => upd({
          dispatch_crypto: e.target.checked
        })} />
          <span>Cryptographic Failures (A02)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_cors} disabled={dis} onChange={e => upd({
          dispatch_cors: e.target.checked
        })} />
          <span>CORS Misconfiguration (A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.dispatch_config} disabled={dis} onChange={e => upd({
          dispatch_config: e.target.checked
        })} />
          <span>Security Misconfiguration (A05)</span>
        </label>

        <div className="divider" />
        <div className="row spread">
          <div>{saved && <span className="save-confirm"><IconCheck /> Saved</span>}</div>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : "Save Specialist Settings"}</button>
        </div>
      </form>}</>;
}
export const DEFAULT_BURP_REST_API_FORM = {
  api_key: "",
  scan_configuration_name: "Audit checks - all except time-based detection methods",
  scan_sqli: true,
  scan_xss: true,
  scan_command_injection: true,
  scan_path_traversal: true,
  scan_ssrf: true,
  scan_xxe: true,
  scan_ssti: true
};
