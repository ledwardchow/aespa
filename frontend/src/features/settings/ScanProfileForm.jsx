import * as settingsApi from "../../shared/api/settings.js";
import { useState } from "react";
import { scanProfileToForm } from "./scanProfileForm.js";
import { AGENT_ROLE_LABELS } from "./agentRoles.js";

import { IconCheck } from "../../shared/ui/Icons.jsx";
import { sortModelConfigs } from "../../shared/lib/modelSorting.js";

export function ScanProfileForm({ mode, profile, models, onSaved, onCancel }) {
  const [form, setForm] = useState(() => scanProfileToForm(profile, models));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = (p) => {
    setSaved(false);
    setForm((f) => ({
      ...f,
      ...p,
    }));
  };
  const updRole = (role, values) => {
    setSaved(false);
    setForm((f) => ({
      ...f,
      role_models: {
        ...f.role_models,
        ...(values.model !== undefined && { [role]: values.model }),
      },
      role_providers: {
        ...f.role_providers,
        ...(values.provider !== undefined && { [role]: values.provider }),
      },
    }));
  };
  const onSubmit = async (e) => {
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
        role_models,
      };
      const savedProfile =
        mode === "edit"
          ? await settingsApi.updateLLMProfile(profile.id, payload)
          : await settingsApi.createLLMProfile(payload);
      setSaved(true);
      onSaved?.(savedProfile);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const modelName = (id) => (models.find((m) => m.id === Number(id)) || {}).name;
  const providers = Array.from(
    models
      .reduce((items, model) => {
        if (model.provider_id != null && !items.has(model.provider_id)) {
          items.set(model.provider_id, {
            id: model.provider_id,
            name: model.provider_name || `Provider #${model.provider_id}`,
          });
        }
        return items;
      }, new Map())
      .values(),
  ).sort((left, right) => left.name.localeCompare(right.name, undefined, { sensitivity: "base" }));
  const modelOptions = (providerId) =>
    sortModelConfigs(models)
      .filter((model) => String(model.provider_id) === providerId)
      .map((model) => (
        <option key={model.id} value={model.id}>
          {model.name} ({model.model})
        </option>
      ));
  const providerOptions = providers.map((provider) => (
    <option key={provider.id} value={provider.id}>
      {provider.name}
    </option>
  ));
  return (
    <>
      {error && <div className="alert error">{error}</div>}
      <form className="card" onSubmit={onSubmit}>
        <div className="form-section-title">Profile</div>
        <div className="field">
          <label>Name</label>
          <input
            type="text"
            required
            maxLength="120"
            value={form.name}
            onChange={(e) =>
              upd({
                name: e.target.value,
              })
            }
          />
        </div>
        <div className="field">
          <label>Default model</label>
          <div className="profile-model-selectors">
            <label>
              <span>Provider</span>
              <select
                aria-label="Default model provider"
                className="select"
                required
                value={form.default_provider_id}
                onChange={(e) =>
                  upd({
                    default_provider_id: e.target.value,
                    default_model_id: "",
                  })
                }
              >
                <option value="">Select a provider…</option>
                {providerOptions}
              </select>
            </label>
            <label>
              <span>Model</span>
              <select
                aria-label="Default model"
                className="select"
                required
                disabled={!form.default_provider_id}
                value={form.default_model_id}
                onChange={(e) => upd({ default_model_id: e.target.value })}
              >
                <option value="">
                  {form.default_provider_id ? "Select a model…" : "Select a provider first"}
                </option>
                {modelOptions(form.default_provider_id)}
              </select>
            </label>
          </div>
          <div className="field-hint">Used for any agent role left on “Use default” below.</div>
        </div>
        <div className="divider" />
        <div className="form-section-title">Per-role overrides</div>
        <div
          className="field-hint"
          style={{
            marginBottom: "10px",
          }}
        >
          Assign a cheaper model to high-volume roles (crawler, validator) and keep the Test Lead on
          your best model.
        </div>
        {AGENT_ROLE_LABELS.map(([role, label, hint]) => (
          <div className="field" key={role}>
            <label>{label}</label>
            <div className="profile-model-selectors">
              <label>
                <span>Provider</span>
                <select
                  aria-label={`${label} provider`}
                  className="select"
                  value={form.role_providers[role]}
                  onChange={(e) =>
                    updRole(role, {
                      provider: e.target.value,
                      model: "",
                    })
                  }
                >
                  <option value="">Use default</option>
                  {providerOptions}
                </select>
              </label>
              <label>
                <span>Model</span>
                <select
                  aria-label={`${label} model`}
                  className="select"
                  disabled={!form.role_providers[role]}
                  required={Boolean(form.role_providers[role])}
                  value={form.role_models[role]}
                  onChange={(e) => updRole(role, { model: e.target.value })}
                >
                  <option value="">
                    {form.role_providers[role]
                      ? "Select a model…"
                      : `Use default${
                          form.default_model_id
                            ? ` (${modelName(form.default_model_id) || "—"})`
                            : ""
                        }`}
                  </option>
                  {modelOptions(form.role_providers[role])}
                </select>
              </label>
            </div>
            <div className="field-hint">{hint}</div>
          </div>
        ))}
        <div className="divider" />
        <div className="row spread">
          <div>
            {saved && (
              <span className="save-confirm">
                <IconCheck /> Saved
              </span>
            )}
          </div>
          <div className="row">
            {onCancel && (
              <button type="button" className="btn ghost" onClick={onCancel}>
                Cancel
              </button>
            )}
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Saving…" : mode === "edit" ? "Save profile" : "Create profile"}
            </button>
          </div>
        </div>
      </form>
    </>
  );
}
