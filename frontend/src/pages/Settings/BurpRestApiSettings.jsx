import { useState, useEffect } from "react";
import { burpRestApiPayload, burpRestApiToForm } from "../Settings";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";


export function BurpRestApiSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [connTest, setConnTest] = useState(null);
  const [connTesting, setConnTesting] = useState(false);
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
        setForm(burpRestApiToForm(await api.getBurpRestApiConfig()));
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
      const savedConfig = await api.upsertBurpRestApiConfig(burpRestApiPayload(form));
      setForm(burpRestApiToForm(savedConfig));
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const onTestConnection = async () => {
    setConnTest(null);
    setConnTesting(true);
    try {
      const result = await api.testBurpConnection();
      setConnTest(result);
    } catch (e) {
      setConnTest({
        ok: false,
        message: e.message
      });
    } finally {
      setConnTesting(false);
    }
  };
  return <>
    {!form && !error && <div className="subtle">Loading…</div>}
    {error && <div className="alert error">{error}</div>}
    {form && <form className="card" onSubmit={onSubmit}>
        <div className="form-section-title">Burp Suite Active Scan</div>
        <label className="toggle-row">
          <input type="checkbox" checked={form.enabled} onChange={e => upd({
          enabled: e.target.checked
        })} />
          <span>Enable Burp Suite active scan integration</span>
        </label>
        <div className="field-hint" style={{
        marginBottom: "12px"
      }}>
          When enabled, the scanner automatically triggers Burp Suite active scans for
          enabled vulnerability classes as the LLM discovers candidate endpoints.
          Requires Burp Suite Professional with the REST API enabled (Burp menu → Settings → Suite → REST API).
        </div>
        <div className="field">
          <label>REST API URL</label>
          <input type="url" required value={form.api_url} placeholder="http://127.0.0.1:1337" onChange={e => upd({
          api_url: e.target.value
        })} />
          <div className="field-hint">Default: http://127.0.0.1:1337. Configure under Burp → Settings → Suite → REST API.</div>
        </div>
        <div className="field">
          <label>API key <span className="subtle">(optional)</span></label>
          <div className="row" style={{ gap: "8px" }}>
            <input
              type="password"
              value={form.api_key}
              placeholder={
                form.clear_api_key
                  ? "Key will be removed on save"
                  : form.has_api_key && !form.api_key
                  ? "•••••••• (leave blank to keep current key)"
                  : "Leave blank if not configured"
              }
              onChange={e => upd({
                api_key: e.target.value,
                clear_api_key: false
              })}
              style={{ flex: 1 }}
            />
            {form.has_api_key && (
              form.clear_api_key ? (
                <button type="button" className="btn ghost" onClick={() => upd({ clear_api_key: false })}>
                  Undo clear
                </button>
              ) : (
                <button type="button" className="btn ghost" onClick={() => upd({ clear_api_key: true, api_key: "" })}>
                  Clear key
                </button>
              )
            )}
          </div>
          <div className="field-hint">Set an API key in Burp REST API settings and paste it here for authentication.</div>
        </div>
        <div className="field">
          <label>Scan configuration <span className="subtle">(optional)</span></label>
          <input type="text" value={form.scan_configuration_name} placeholder="Audit checks - all except time-based detection methods" onChange={e => upd({
          scan_configuration_name: e.target.value
        })} />
          <div className="field-hint">Only enter a named configuration that exists in your Burp project. Blank avoids Unknown configuration errors.</div>
        </div>
        <div className="divider" />
        <div className="form-section-title">Vulnerability Classes to Active Scan</div>
        <div className="field-hint" style={{
        marginBottom: "8px"
      }}>When the LLM investigates a selected vulnerability class on a URL, Burp will actively scan that endpoint.</div>
        <label className="toggle-row">
          <input type="checkbox" checked={form.scan_sqli} onChange={e => upd({
          scan_sqli: e.target.checked
        })} />
          <span>SQL Injection (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.scan_xss} onChange={e => upd({
          scan_xss: e.target.checked
        })} />
          <span>Cross-Site Scripting / XSS (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.scan_command_injection} onChange={e => upd({
          scan_command_injection: e.target.checked
        })} />
          <span>OS Command Injection (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.scan_path_traversal} onChange={e => upd({
          scan_path_traversal: e.target.checked
        })} />
          <span>Path Traversal / File Inclusion (A01/A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.scan_ssrf} onChange={e => upd({
          scan_ssrf: e.target.checked
        })} />
          <span>Server-Side Request Forgery / SSRF (A10)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.scan_xxe} onChange={e => upd({
          scan_xxe: e.target.checked
        })} />
          <span>XML External Entity / XXE (A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={form.scan_ssti} onChange={e => upd({
          scan_ssti: e.target.checked
        })} />
          <span>Server-Side Template Injection / SSTI (A03)</span>
        </label>
        <div className="divider" />
        {connTest && <div className={"alert " + (connTest.ok ? "success" : "error")} style={{
        marginBottom: "12px"
      }}>{connTest.message}</div>}
        <div className="row spread">
          <div className="row" style={{
          gap: "8px"
        }}>
            {saved && <span className="save-confirm"><IconCheck /> Saved</span>}
            <button type="button" className="btn secondary" disabled={connTesting} onClick={onTestConnection}>
              {connTesting ? "Testing…" : "Test Connection"}
            </button>
          </div>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : "Save Burp Settings"}</button>
        </div>
      </form>}</>;
}
export const API_FORMAT_LABELS = {
  anthropic: "Anthropic API",
  openai: "OpenAI API",
  openai_compatible: "OpenAI-compatible API",
  openrouter: "OpenRouter",
  google: "Google Gemini API",
  bedrock: "Amazon Bedrock Runtime",
  bedrock_mantle: "Amazon Bedrock Mantle",
  azure_openai: "Azure OpenAI",
  azure_foundry: "Azure AI Foundry (OpenAI API)",
  azure_foundry_openai: "Azure AI Foundry (OpenAI API)",
  azure_foundry_anthropic: "Azure AI Foundry (Anthropic API)"
};
export const DEFAULT_PROVIDER_FORM = {
  name: "",
  api_format: "anthropic",
  base_url: "",
  project_id: "",
  models: "",
  api_key: "",
  max_tpm: "",
  max_rpm: ""
};
export const DEFAULT_LLM_FORM = {
  name: "Default",
  provider_id: "",
  model: "",
  max_tokens: 70000,
  temperature: 0.2,
  use_temperature: true,
  use_vision: false,
  force_tool_choice: true
};
export const PROVIDER_BASE_URL_PLACEHOLDERS = {
  anthropic: "https://api.anthropic.com",
  openai: "https://api.openai.com/v1",
  openai_compatible: "http://localhost:1234/v1",
  openrouter: "https://openrouter.ai/api/v1",
  google: "https://generativelanguage.googleapis.com",
  bedrock: "https://bedrock-runtime.us-east-1.amazonaws.com",
  bedrock_mantle: "https://bedrock-mantle.us-east-2.api.aws/v1",
  azure_openai: "https://myresource.openai.azure.com",
  azure_foundry: "https://myresource.services.ai.azure.com",
  azure_foundry_openai: "https://myresource.services.ai.azure.com/openai/v1",
  azure_foundry_anthropic: "https://myresource.services.ai.azure.com/anthropic/v1"
};
// Actual runtime defaults used by the backend when base_url is blank
export const PROVIDER_DEFAULT_BASE_URLS = {
  anthropic: "https://api.anthropic.com",
  openai: "https://api.openai.com/v1",
  openai_compatible: null,
  // no sensible default — must be set
  openrouter: "https://openrouter.ai/api/v1",
  google: "https://generativelanguage.googleapis.com",
  bedrock: "AWS SDK default (us-east-1)",
  bedrock_mantle: "https://bedrock-mantle.us-east-2.api.aws/v1",
  azure_openai: null,
  // must be set
  azure_foundry: null,
  azure_foundry_openai: null,
  azure_foundry_anthropic: null
};
export const PROVIDER_MODEL_PLACEHOLDERS = {
  anthropic: "claude-opus-4-8\nclaude-sonnet-4-5",
  openai: "gpt-5.5\ngpt-5.4\ngpt-4.1",
  openai_compatible: "llama-3.1-8b-instruct\nqwen2.5-coder",
  openrouter: "openrouter/owl-alpha\nnvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
  google: "gemini-2.5-pro-preview-05-06\ngemini-2.5-flash-preview-04-17",
  bedrock: "global.anthropic.claude-opus-4-8\nglobal.anthropic.claude-sonnet-4-6",
  bedrock_mantle: "openai.gpt-5.5\nopenai.gpt-oss-120b",
  azure_openai: "gpt-5.5\ngpt-4o\ngpt-4.1",
  azure_foundry: "gpt-4o\nMeta-Llama-3.3-70B-Instruct",
  azure_foundry_openai: "gpt-4o\nMeta-Llama-3.3-70B-Instruct",
  azure_foundry_anthropic: "claude-sonnet-4-5\nclaude-opus-4-1"
};
