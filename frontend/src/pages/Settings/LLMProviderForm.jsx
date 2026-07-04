import { useState, useRef, useMemo } from "react";
import { PROVIDER_MODEL_PLACEHOLDERS, PROVIDER_BASE_URL_PLACEHOLDERS } from "./BurpRestApiSettings";
import { providerPayload, providerToForm } from "../Settings";
import { api } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { IconApis, IconPlus, IconCheck, IconStop, IconChevronLeft, IconBug, IconSend } from "../../components/Icons";


export function LLMProviderForm({
  mode,
  provider,
  onSaved,
  onCancel
}) {
  const [form, setForm] = useState(() => providerToForm(provider));
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
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const payload = providerPayload(form);
      const savedProvider = mode === "edit" ? await api.updateLLMProvider(provider.id, payload) : await api.createLLMProvider(payload);
      setSaved(true);
      onSaved?.(savedProvider);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  return <>
    {error && <div className="alert error">{error}</div>}
    <form className="card" onSubmit={onSubmit}>
      <div className="form-section-title">Provider</div>
      <div className="field"><label>Name</label>
        <input type="text" required maxLength="120" value={form.name} onChange={e => upd({
          name: e.target.value
        })} /></div>
      <div className="field">
        <label>API format</label>
        <select className="select" value={form.api_format} onChange={e => upd({
          api_format: e.target.value
        })}>
          <option value="anthropic">Anthropic API</option>
          <option value="openai">OpenAI API</option>
          <option value="openai_compatible">OpenAI-compatible API</option>
          <option value="openrouter">OpenRouter</option>
          <option value="google">Google Gemini API</option>
          <option value="bedrock">Amazon Bedrock Runtime</option>
          <option value="bedrock_mantle">Amazon Bedrock Mantle</option>
          <option value="azure_openai">Azure OpenAI</option>
          <option value="azure_foundry_openai">Azure AI Foundry (OpenAI API)</option>
          <option value="azure_foundry_anthropic">Azure AI Foundry (Anthropic API)</option>
        </select>
      </div>
      <div className="field"><label>Base URL <span className="field-optional">(optional)</span></label>
        <input type="url" value={form.base_url} placeholder={PROVIDER_BASE_URL_PLACEHOLDERS[form.api_format] || ""} onChange={e => upd({
          base_url: e.target.value
        })} />
        {form.api_format === "bedrock" && <div className="field-hint">Leave blank to use the default boto3 Bedrock endpoint for AWS_REGION / AWS_DEFAULT_REGION.</div>}
        {form.api_format === "bedrock_mantle" && <div className="field-hint">Best left blank — AESPA picks the endpoint per model (the <code>/openai/v1</code> path for <code>openai.gpt-5.x</code>, <code>/v1</code> for <code>gpt-oss</code>) and defaults to the us-east-2 region (or BEDROCK_MANTLE_REGION / AWS_REGION). Set only to point at another region's host, e.g. https://bedrock-mantle.us-west-2.api.aws.</div>}
      </div>
      {form.api_format === "bedrock_mantle" && <div className="field"><label>Project ID <span className="field-optional">(optional)</span></label>
        <input type="text" value={form.project_id} placeholder="proj_5d5ykleja6cwpirysbb7" onChange={e => upd({
          project_id: e.target.value
        })} />
        <div className="field-hint">Sent as the OpenAI-Project header to attribute usage/cost to a Bedrock Mantle project. Use the project id (proj_…) from the Bedrock console, not its name. Leave blank for the account default project.</div>
      </div>}
      <div className="field"><label>Model names</label>
        <textarea required rows="5" value={form.models} placeholder={PROVIDER_MODEL_PLACEHOLDERS[form.api_format] || ""} onChange={e => upd({
          models: e.target.value
        })}></textarea>
        <div className="field-hint">Enter one model per line, or separate models with commas.</div>
      </div>
      <div className="field"><label>API Key <span className="field-optional">(optional)</span></label>
        <input type="password" value={form.api_key} placeholder={form.api_format === "bedrock" ? "Leave blank to use boto3 / AWS_PROFILE / IAM role" : form.api_format === "bedrock_mantle" ? "Bedrock API key, or leave blank for AWS credentials" : "Leave blank if not required"} onChange={e => upd({
          api_key: e.target.value
        })} />
        {form.api_format === "bedrock" && <div className="field-hint">When blank, Aespa uses boto3 credentials from AWS_PROFILE, environment variables, SSO, or the instance/task role.</div>}
        {form.api_format === "bedrock_mantle" && <div className="field-hint">With a key, Mantle authenticates via Bearer token. Leave blank to sign requests with AWS credentials (SigV4) from AWS_PROFILE, environment variables, SSO, or an IAM role — the same fallback as the Bedrock Runtime provider.</div>}
      </div>
      <div className="divider" />
      <div className="form-section-title">Rate Limits <span className="field-optional">(optional)</span></div>
      <div className="field-hint" style={{
        marginBottom: "8px"
      }}>Set token and request limits to automatically pace requests and prevent API rate-limiting errors (429).</div>
      <div className="two-col" style={{
        gap: "16px",
        marginBottom: "8px"
      }}>
        <div className="field">
          <label>Max Tokens Per Minute (TPM)</label>
          <input type="number" min="1" placeholder="Unlimited" value={form.max_tpm} onChange={e => upd({
            max_tpm: e.target.value
          })} />
        </div>
        <div className="field">
          <label>Max Requests Per Minute (RPM)</label>
          <input type="number" min="1" placeholder="Unlimited" value={form.max_rpm} onChange={e => upd({
            max_rpm: e.target.value
          })} />
        </div>
      </div>
      <div className="divider" />
      <div className="row spread">
        <div>{saved && <span className="save-confirm"><IconCheck /> Saved</span>}</div>
        <div className="row">
          {onCancel && <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>}
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : mode === "edit" ? "Save provider" : "Create provider"}</button>
        </div>
      </div>
    </form></>;
}
