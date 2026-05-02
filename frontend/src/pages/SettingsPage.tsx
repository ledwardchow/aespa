import { FormEvent, useEffect, useState } from "react";
import { api, LLMConfigPayload, LLMProvider } from "../api";

const PROVIDER_LABELS: Record<LLMProvider, string> = {
  anthropic:        "Anthropic",
  openai:           "OpenAI",
  openai_compatible:"OpenAI-compatible (LM Studio, Ollama, etc.)",
};

const PROVIDER_PLACEHOLDERS: Record<LLMProvider, string> = {
  anthropic:        "claude-opus-4-5",
  openai:           "gpt-4o",
  openai_compatible:"e.g. llama-3.1-8b-instruct",
};

function IconCheck() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 7l4 4 6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

type FormState = {
  provider: LLMProvider;
  api_key: string;
  base_url: string;
  model: string;
  max_tokens: number;
  temperature: number;
};

const defaults: FormState = {
  provider: "anthropic", api_key: "", base_url: "",
  model: "claude-opus-4-5", max_tokens: 4096, temperature: 0,
};

export default function SettingsPage() {
  const [form, setForm]             = useState<FormState | null>(null);
  const [defaultModels, setDMs]     = useState<Record<string, string[]>>({});
  const [saving, setSaving]         = useState(false);
  const [saved, setSaved]           = useState(false);
  const [error, setError]           = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [cfg, dms] = await Promise.all([api.getLLMConfig(), api.getDefaultModels()]);
        setDMs(dms);
        setForm(cfg ? {
          provider:    cfg.provider as LLMProvider,
          api_key:     cfg.api_key    ?? "",
          base_url:    cfg.base_url   ?? "",
          model:       cfg.model,
          max_tokens:  cfg.max_tokens,
          temperature: cfg.temperature,
        } : { ...defaults });
      } catch (e) { setError((e as Error).message); }
    })();
  }, []);

  const update = (patch: Partial<FormState>) => { setSaved(false); setForm((f) => f ? { ...f, ...patch } : f); };

  const changeProvider = (p: LLMProvider) => {
    const models = defaultModels[p] ?? [];
    update({ provider: p, model: models[0] ?? "", api_key: "", base_url: "" });
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setError(null); setSaving(true); setSaved(false);
    const payload: LLMConfigPayload = {
      provider:    form.provider,
      api_key:     form.api_key.trim() || null,
      base_url:    form.provider === "openai_compatible" ? form.base_url.trim() : null,
      model:       form.model.trim(),
      max_tokens:  Number(form.max_tokens),
      temperature: Number(form.temperature),
    };
    try { await api.upsertLLMConfig(payload); setSaved(true); }
    catch (e2) { setError((e2 as Error).message); }
    finally    { setSaving(false); }
  };

  if (!form && !error) return <><div className="topbar"><div className="topbar-title">LLM Settings</div></div><div className="content"><div className="subtle">Loading…</div></div></>;

  const models = form ? (defaultModels[form.provider] ?? []) : [];
  const isCustom = form ? (models.length > 0 && !models.includes(form.model) && form.model !== "") : false;

  return (
    <>
      <div className="topbar">
        <div className="topbar-title">LLM Settings</div>
      </div>

      <div className="content">
        {error && <div className="alert error">{error}</div>}
        {form && (
          <form className="card" onSubmit={onSubmit}>

            <div className="form-section-title">Provider</div>

            <div className="provider-grid">
              {(Object.entries(PROVIDER_LABELS) as [LLMProvider, string][]).map(([key, label]) => (
                <label key={key} className={`provider-card${form.provider === key ? " selected" : ""}`}>
                  <input type="radio" name="provider" value={key}
                    checked={form.provider === key}
                    onChange={() => changeProvider(key)} />
                  <span className="provider-name">{label}</span>
                </label>
              ))}
            </div>

            <div className="divider" />
            <div className="form-section-title">{PROVIDER_LABELS[form.provider]} Configuration</div>

            {(form.provider === "anthropic" || form.provider === "openai") && (
              <div className="field">
                <label>API Key</label>
                <input type="password" required
                  value={form.api_key}
                  placeholder={form.provider === "anthropic" ? "sk-ant-…" : "sk-…"}
                  onChange={(e) => update({ api_key: e.target.value })} />
              </div>
            )}

            {form.provider === "openai_compatible" && (
              <>
                <div className="field">
                  <label>Base URL</label>
                  <input type="url" required
                    value={form.base_url}
                    placeholder="http://localhost:1234/v1"
                    onChange={(e) => update({ base_url: e.target.value })} />
                  <div className="field-hint">
                    LM Studio default: http://localhost:1234/v1 · Ollama: http://localhost:11434/v1
                  </div>
                </div>
                <div className="field">
                  <label>API Key <span className="field-optional">(optional)</span></label>
                  <input type="password"
                    value={form.api_key}
                    placeholder="Leave blank if not required"
                    onChange={(e) => update({ api_key: e.target.value })} />
                </div>
              </>
            )}

            <div className="field">
              <label>Model</label>
              {models.length > 0 ? (
                <div className="model-select-group">
                  <select className="select"
                    value={isCustom ? "__custom__" : form.model}
                    onChange={(e) => {
                      if (e.target.value !== "__custom__") update({ model: e.target.value });
                      else update({ model: "" });
                    }}>
                    {models.map((m) => <option key={m} value={m}>{m}</option>)}
                    <option value="__custom__">Custom…</option>
                  </select>
                  {isCustom && (
                    <input type="text" required value={form.model}
                      placeholder="Enter model name"
                      onChange={(e) => update({ model: e.target.value })} />
                  )}
                </div>
              ) : (
                <input type="text" required value={form.model}
                  placeholder={PROVIDER_PLACEHOLDERS[form.provider]}
                  onChange={(e) => update({ model: e.target.value })} />
              )}
            </div>

            <div className="divider" />
            <div className="form-section-title">Sampling</div>

            <div className="two-col">
              <div className="field">
                <label>Max tokens</label>
                <input type="number" required min={1} max={32768}
                  value={form.max_tokens}
                  onChange={(e) => update({ max_tokens: Number(e.target.value) })} />
              </div>
              <div className="field">
                <label>Temperature <span className="field-hint-inline">(0 – 2)</span></label>
                <input type="number" required min={0} max={2} step={0.05}
                  value={form.temperature}
                  onChange={(e) => update({ temperature: Number(e.target.value) })} />
              </div>
            </div>

            <div className="divider" />
            <div className="row spread">
              <div>
                {saved && <span className="save-confirm"><IconCheck /> Saved</span>}
              </div>
              <button type="submit" className="btn" disabled={saving}>
                {saving ? "Saving…" : "Save settings"}
              </button>
            </div>
          </form>
        )}
      </div>
    </>
  );
}
