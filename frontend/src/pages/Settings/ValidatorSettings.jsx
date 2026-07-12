import { useState, useEffect } from "react";
import { validatorPayload, validatorToForm } from "../Settings";
import { api } from "../../lib/api";


export function ValidatorSettings() {
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
        setForm(validatorToForm(await api.getAdversarialValidatorConfig()));
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
      const savedConfig = await api.upsertAdversarialValidatorConfig(validatorPayload(form));
      setForm(validatorToForm(savedConfig));
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
        <div className="form-section-title">Adversarial Validator</div>
        <label className="toggle-row">
          <input type="checkbox" checked={form.enabled} onChange={e => upd({
          enabled: e.target.checked
        })} />
          <span>Enable adversarial validator</span>
        </label>
        <div className="field-hint" style={{
        marginBottom: "12px"
      }}>
          When enabled, each finding is reviewed by an adversarial LLM agent whose explicit
          mandate is to <em>disprove</em> the finding before confirming it. This reduces false
          positives without relying on the scanner's own judgment. When disabled, the legacy
          static-probe validator is used instead.
        </div>

        <div className="form-section-title">Step Budget</div>
        <div className="field">
          <label>Max steps per finding</label>
          <input type="number" min="1" max="50" value={form.max_steps} disabled={dis} onChange={e => upd({
          max_steps: Number(e.target.value)
        })} />
          <div className="field-hint">
            Maximum number of tool calls the validator may make per finding (1–50). Default: 20.
            Higher values give the validator more opportunities to disprove a finding but increase
            cost and latency.
          </div>
        </div>

        <div className="form-section-title">Severity Filter</div>
        <div className="field">
          <label>Minimum severity to validate</label>
          <select value={form.min_severity} disabled={dis} onChange={e => upd({
          min_severity: e.target.value
        })}>
            <option value="critical">Critical only</option>
            <option value="high">High and above</option>
            <option value="medium">Medium and above</option>
            <option value="low">Low and above (default)</option>
            <option value="info">All (including Info)</option>
          </select>
          <div className="field-hint">
            Findings below this severity are skipped by the validator and marked "not validated".
          </div>
        </div>

        <div className="form-section-title">End-of-scan Validation</div>
        <div className="field">
          <label>Concurrent Reporting validators</label>
          <input type="number" min="1" max="8" value={form.end_scan_max_concurrent} disabled={dis} onChange={e => upd({
          end_scan_max_concurrent: Number(e.target.value)
        })} />
          <div className="field-hint">
            Number of Reporting findings to validate in parallel after a scan completes (1–8).
            Default: 4. Lower this for rate-limited models or fragile targets.
          </div>
        </div>

        <div className="form-section-title">Behaviour</div>
        <label className="toggle-row">
          <input type="checkbox" checked={form.auto_validate_inline} disabled={dis} onChange={e => upd({
          auto_validate_inline: e.target.checked
        })} />
          <span>Auto-validate findings inline during scan</span>
        </label>
        <div className="field-hint" style={{
        marginBottom: "12px"
      }}>
          When enabled, each finding is validated immediately after it is written, while the
          scan is still running. When disabled, validation only runs when triggered manually.
        </div>
        <label className="toggle-row">
          <input type="checkbox" checked={form.require_concrete_disproof} disabled={dis} onChange={e => upd({
          require_concrete_disproof: e.target.checked
        })} />
          <span>Require concrete disproof (strict mode)</span>
        </label>
        <div className="field-hint" style={{
        marginBottom: "12px"
      }}>
          When enabled (recommended), the validator must find a specific innocent explanation
          to mark a finding as a false positive — failure to reproduce is not sufficient.
          When disabled, inability to reproduce is treated as a false positive (lenient mode).
        </div>

        <div className="form-row">
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
          {saved && <span className="saved-indicator">Saved</span>}
        </div>
      </form>}</>;
}
