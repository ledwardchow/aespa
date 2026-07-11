import { useState } from "react";
import { scanProfileToForm } from "../Settings";
import { AGENT_ROLE_LABELS } from "./LLMModelForm";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";


export function ScanProfileForm({
  mode,
  profile,
  models,
  onSaved,
  onCancel
}) {
  const [form, setForm] = useState(() => scanProfileToForm(profile));
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
  const updRole = (role, v) => {
    setSaved(false);
    setForm(f => ({
      ...f,
      role_models: {
        ...f.role_models,
        [role]: v
      }
    }));
  };
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const role_models = {};
      for (const [role] of AGENT_ROLE_LABELS) {
        const v = form.role_models[role];
        if (v) role_models[role] = Number(v);
      }
      const payload = {
        name: form.name.trim(),
        default_model_id: Number(form.default_model_id),
        role_models
      };
      const savedProfile = mode === "edit" ? await api.updateLLMProfile(profile.id, payload) : await api.createLLMProfile(payload);
      setSaved(true);
      onSaved?.(savedProfile);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const modelName = id => (models.find(m => m.id === Number(id)) || {}).name;
  const modelOpts = models.map(m => <option key={m.id} value={m.id}>{m.name} ({m.model})</option>);
  return <>
    {error && <div className="alert error">{error}</div>}
    <form className="card" onSubmit={onSubmit}>
      <div className="form-section-title">Profile</div>
      <div className="field"><label>Name</label>
        <input type="text" required maxLength="120" value={form.name} onChange={e => upd({
          name: e.target.value
        })} /></div>
      <div className="field"><label>Default model</label>
        <select className="select" required value={form.default_model_id} onChange={e => upd({
          default_model_id: e.target.value
        })}>
          <option value="">Select a model…</option>
          {modelOpts}
        </select>
        <div className="field-hint">Used for any agent role left on “Use default” below.</div>
      </div>
      <div className="divider" />
      <div className="form-section-title">Per-role overrides</div>
      <div className="field-hint" style={{
        marginBottom: "10px"
      }}>
        Assign a cheaper model to high-volume roles (crawler, validator) and keep the Test Lead on your best model.
      </div>
      {AGENT_ROLE_LABELS.map(([role, label, hint]) => <div className="field" key={role}>
          <label>{label}</label>
          <select className="select" value={form.role_models[role]} onChange={e => updRole(role, e.target.value)}>
            <option value="">Use default{form.default_model_id ? ` (${modelName(form.default_model_id) || "—"})` : ""}</option>
            {modelOpts}
          </select>
          <div className="field-hint">{hint}</div>
        </div>)}
      <div className="divider" />
      <div className="row spread">
        <div>{saved && <span className="save-confirm"><IconCheck /> Saved</span>}</div>
        <div className="row">
          {onCancel && <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>}
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : mode === "edit" ? "Save profile" : "Create profile"}</button>
        </div>
      </div>
    </form></>;
}
