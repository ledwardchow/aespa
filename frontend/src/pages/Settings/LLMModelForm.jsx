import { useState, useEffect, useMemo } from "react";
import { llmProfileToForm, llmPayload } from "../Settings";
import { API_FORMAT_LABELS } from "./BurpRestApiSettings";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";
import { sortModelNames } from "../../lib/modelSorting";


export function LLMModelForm({
  mode,
  profile,
  providers,
  onSaved,
  onCancel
}) {
  const [form, setForm] = useState(() => llmProfileToForm(profile, providers));
  const [nameTouched, setNameTouched] = useState(mode === "edit");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [discoveredCapabilities, setDiscoveredCapabilities] = useState({});
  const [loadingCapabilities, setLoadingCapabilities] = useState(false);
  const upd = p => {
    setSaved(false);
    setForm(f => ({
      ...f,
      ...p
    }));
  };
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const payload = llmPayload(form);
      const savedProfile = mode === "edit" ? await api.updateLLMModel(profile.id, payload) : await api.createLLMModel(payload);
      setSaved(true);
      onSaved?.(savedProfile);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const selectedProvider = providers.find(p => p.id === Number(form.provider_id));
  const models = useMemo(() => sortModelNames(selectedProvider?.models), [selectedProvider?.models]);
  const storedCapabilities = selectedProvider?.model_capabilities || {};
  const hasStoredCapability = Object.prototype.hasOwnProperty.call(storedCapabilities, form.model);
  useEffect(() => {
    if (!selectedProvider || !form.model || hasStoredCapability) {
      setDiscoveredCapabilities({});
      setLoadingCapabilities(false);
      return undefined;
    }
    let cancelled = false;
    setLoadingCapabilities(true);
    api.discoverModelOptions({
      provider_id: selectedProvider.id,
      api_format: selectedProvider.api_format,
      api_key: "",
      base_url: selectedProvider.base_url || null,
      username: selectedProvider.username || null,
      models
    }).then(result => {
      if (!cancelled) setDiscoveredCapabilities(result?.capabilities || {});
    }).catch(() => {
      if (!cancelled) setDiscoveredCapabilities({});
    }).finally(() => {
      if (!cancelled) setLoadingCapabilities(false);
    });
    return () => { cancelled = true; };
  }, [selectedProvider, models, form.model, hasStoredCapability]);
  const capability = hasStoredCapability ? storedCapabilities[form.model] || {} : discoveredCapabilities[form.model] || {};
  const levels = Array.isArray(capability.supported_efforts) ? capability.supported_efforts : [];
  return <>
    {error && <div className="alert error">{error}</div>}
    <form className="card" onSubmit={onSubmit}>
      <div className="form-section-title">Model</div>
      <div className="field"><label>Name</label>
        <input
          type="text"
          required
          maxLength="120"
          value={form.name}
          onChange={e => {
            setNameTouched(true);
            upd({ name: e.target.value });
          }}
        />
      </div>
      <div className="field">
        <label>Provider</label>
        <select
          className="select"
          required
          value={form.provider_id}
          onChange={e => {
            const newProviderId = e.target.value;
            const provider = providers.find(p => p.id === Number(newProviderId));
            const newModel = sortModelNames(provider?.models)[0] || "";
            const updates = {
              provider_id: newProviderId,
              model: newModel,
              reasoning_effort: ""
            };
            if (!nameTouched || !form.name.trim()) {
              updates.name = provider?.name && newModel ? `${provider.name}/${newModel}` : newModel;
            }
            upd(updates);
          }}
        >
          {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({API_FORMAT_LABELS[p.api_format] || p.api_format})</option>)}
        </select>
      </div>
      <div className="field"><label>Model</label>
        <select
          className="select"
          required
          value={form.model}
          onChange={e => {
            const newModel = e.target.value;
            const updates = {
              model: newModel,
              reasoning_effort: ""
            };
            if (!nameTouched || !form.name.trim()) {
              const provider = providers.find(p => p.id === Number(form.provider_id));
              updates.name = provider?.name && newModel ? `${provider.name}/${newModel}` : newModel;
            }
            upd(updates);
          }}
        >
          {models.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>
      <div className="field">
        <label>Thinking level <span className="field-optional">(optional)</span></label>
        <select className="select" value={form.reasoning_effort || ""} onChange={e => upd({ reasoning_effort: e.target.value })}>
          <option value="">Default{capability.default_effort ? ` (${capability.default_effort})` : " (provider decides)"}</option>
          {levels.map(level => <option key={level} value={level}>{level}</option>)}
          {form.reasoning_effort && !levels.includes(form.reasoning_effort) && <option value={form.reasoning_effort}>{form.reasoning_effort} (saved)</option>}
        </select>
        <div className="field-hint">Leave this at Default to keep the provider's current behavior.</div>
        {loadingCapabilities && <div className="field-hint">Loading available levels…</div>}
        {capability.strategy === "documented_registry" && <div className="field-hint">Levels from the provider's documented model family.</div>}
        {capability.source === "openrouter" && <div className="field-hint">Levels matched from OpenRouter because this provider did not expose them directly.</div>}
      </div>
      <div className="divider" />
      <div className="form-section-title">Sampling</div>
      <div className="two-col">
        <div className="field"><label>Max tokens</label>
          <input type="number" required min="1" max="256000" value={form.max_tokens} onChange={e => upd({
            max_tokens: e.target.value
          })} /></div>
        <div className="field">
          <label style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            cursor: "pointer"
          }}>
            <input type="checkbox" checked={form.use_temperature} onChange={e => upd({
              use_temperature: e.target.checked
            })} style={{
              width: "14px",
              height: "14px",
              accentColor: "var(--accent)",
              cursor: "pointer",
              margin: 0
            }} />
            <span>Temperature <span className="field-hint-inline">(0-2)</span></span>
          </label>
          <input type="number" required={form.use_temperature} disabled={!form.use_temperature} min="0" max="2" step="0.05" value={form.temperature} onChange={e => upd({
            temperature: e.target.value
          })} />
        </div>
      </div>
      <div className="divider" />
      <div className="form-section-title">Vision</div>
      <label className="toggle-row">
        <input type="checkbox" checked={form.use_vision} onChange={e => upd({
          use_vision: e.target.checked
        })} />
        <span>Include page screenshots in LLM prompts (requires vision-capable model)</span>
      </label>
      <div className="divider" />
      <div className="form-section-title">Advanced</div>
      <label className="toggle-row">
        <input type="checkbox" checked={form.force_tool_choice} onChange={e => upd({
          force_tool_choice: e.target.checked
        })} />
        <span>Force tool execution</span>
      </label>
      <div className="field-hint" style={{
        marginBottom: "12px"
      }}>
        Enforces tool execution constraints on the LLM via standard OpenAI wire parameters. 
        Recommended for standard models to maintain high scanning density. 
        Disable if using custom reasoning/thinking models that reject forced tool choice (e.g. DeepSeek-R1, deepseek-reasoner).
      </div>
      <div className="divider" />
      <div className="row spread">
        <div>{saved && <span className="save-confirm"><IconCheck /> Saved</span>}</div>
        <div className="row">
          {onCancel && <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>}
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : mode === "edit" ? "Save model" : "Create model"}</button>
        </div>
      </div>
    </form></>;
}

// Agent roles a scan profile can assign a Model to (mirrors AGENT_ROLES in
// services/settings.py). Order/labels drive the profile editor rows.
export const AGENT_ROLE_LABELS = [["crawler", "Crawler", "Page discovery & classification (high volume, light reasoning)"], ["test_lead", "Test Lead", "The agentic reasoning loop (keep this on your best model)"], ["mentor", "Mentor", "Supervises stalled execution; inherits Test Lead when unassigned"], ["specialist", "Specialist", "Focused per-lead attack agents"], ["validator", "Validator", "Adversarial false-positive checks (high volume)"], ["api_scanner", "API Scanner", "API (OpenAPI/Postman) agentic scan loop"], ["sast", "SAST", "Static analysis over uploaded source"], ["component_mapper", "Component Mapper", "Cross-repository interface discovery (bounded, suitable for a cheaper code-capable model)"], ["alice", "A.L.I.C.E.", "Interactive user-directed pentest chat agent"]];
