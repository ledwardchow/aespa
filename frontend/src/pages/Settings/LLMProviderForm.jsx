import { useState, useEffect, useCallback } from "react";
import { PROVIDER_MODEL_PLACEHOLDERS, PROVIDER_BASE_URL_PLACEHOLDERS } from "./BurpRestApiSettings";
import { providerPayload, providerToForm } from "../Settings";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";

function CodexConnectionCard() {
  const [state, setState] = useState(null);
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [loginChallenge, setLoginChallenge] = useState(null);
  const refresh = useCallback(async () => {
    try {
      const next = await api.getCodexStatus();
      setState(next);
      setPath(next.executable_path || "");
    } catch (e) { setError(e.message); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (!loginChallenge) return undefined;
    let stopped = false;
    const poll = async () => {
      try {
        const next = await api.getCodexStatus();
        if (stopped) return;
        setState(next);
        if (next.account) {
          setLoginChallenge(null);
          setBusy(false);
        }
      } catch (e) {
        if (!stopped) setError(e.message);
      }
    };
    const timer = window.setInterval(poll, 2000);
    poll();
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [loginChallenge]);
  const save = async () => {
    setBusy(true); setError(null);
    try { await api.saveCodexConfig({ executable_path: path.trim() || null }); await refresh(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const login = async () => {
    setBusy(true); setError(null);
    let pending = false;
    try {
      const result = await api.startCodexLogin();
      if (result.verificationUrl && result.userCode) {
        setLoginChallenge(result);
        pending = true;
      } else {
        throw new Error("Codex did not return a device-code login. Upgrade Codex CLI and try again.");
      }
    } catch (e) { setError(e.message); } finally { setBusy(false); }
    if (pending) setBusy(true);
  };
  const cancelLogin = async () => {
    if (!loginChallenge?.loginId) return;
    setBusy(true); setError(null);
    try {
      await api.cancelCodexLogin({ loginId: loginChallenge.loginId });
      setLoginChallenge(null);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const logout = async () => {
    setBusy(true); setError(null);
    try { await api.logoutCodex(); await refresh(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return <div className="form-section" style={{ marginTop: 12 }}>
    <div className="form-section-title">Codex connection</div>
    <div className="field-hint">Install Codex separately. AESPA uses the default account already signed in through the local Codex CLI and never copies those credentials into its database.</div>
    <div className="field"><label>Codex executable path <span className="field-optional">(optional)</span></label>
      <input value={path} placeholder="Leave blank to use codex from PATH" onChange={e => setPath(e.target.value)} />
    </div>
    <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
      <button type="button" className="btn secondary sm" disabled={busy} onClick={save}>Save path</button>
      <button type="button" className="btn secondary sm" disabled={busy || !state?.installed} onClick={login}>Sign in with ChatGPT</button>
      {state?.account && <button type="button" className="btn ghost sm" disabled={busy} onClick={logout}>Sign out</button>}
      <button type="button" className="btn ghost sm" disabled={busy} onClick={refresh}>Refresh</button>
    </div>
    {loginChallenge && <div className="form-section" style={{ marginTop: 12 }}>
      <div className="form-section-title">Finish signing in</div>
      <div className="field-hint">Open the OpenAI verification page, enter this one-time code, and return to AESPA. This page checks the login automatically.</div>
      <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <code style={{ fontSize: 18, letterSpacing: 1 }}>{loginChallenge.userCode}</code>
        <a className="btn secondary sm" href={loginChallenge.verificationUrl} target="_blank" rel="noreferrer">Open verification page</a>
        <button type="button" className="btn ghost sm" onClick={cancelLogin}>Cancel</button>
      </div>
    </div>}
    {state && <div className="field-hint" style={{ marginTop: 8 }}>
      {state.installed ? `Detected ${state.version || "Codex"} at ${state.detected_executable || "configured path"}.` : "Codex CLI was not found."}
      {state.account ? ` Signed in${state.account.planType ? ` with ${state.account.planType}` : ""}.` : " Not signed in."}
    </div>}
    {error && <div className="alert error" style={{ marginTop: 8 }}>{error}</div>}
  </div>;
}


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
  const [loadingModels, setLoadingModels] = useState(false);
  const [loadMessage, setLoadMessage] = useState(null);

  const onLoadModels = async () => {
    setLoadingModels(true);
    setLoadMessage(null);
    try {
      const fetched = await api.discoverModels({
        api_format: form.api_format,
        api_key: form.api_key,
        base_url: form.base_url,
        username: form.username
      });
      if (fetched && fetched.length > 0) {
        upd({ models: fetched.join("\n") });
        setLoadMessage(`Loaded ${fetched.length} model(s) from API.`);
      } else {
        setLoadMessage("No models returned for this provider.");
      }
    } catch (e) {
      setLoadMessage(`Failed to load models: ${e.message}`);
    } finally {
      setLoadingModels(false);
    }
  };

  const onFormatChange = async api_format => {
    upd({ api_format });
    if (form.models.trim()) return;
    try {
      const defaults = await api.getDefaultModels();
      const fetched = defaults[api_format] || [];
      if (fetched.length > 0) {
        upd({ api_format, models: fetched.join("\n") });
      }
    } catch (e) {
      setError(e.message);
    }
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
        <select className="select" value={form.api_format} onChange={e => onFormatChange(e.target.value)}>
          <option value="anthropic">Anthropic API</option>
          <option value="factory_droid">Factory Droid subscription</option>
          <option value="github_copilot">GitHub Copilot subscription</option>
          <option value="openai_codex">OpenAI Codex subscription</option>
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
      {!(["factory_droid", "openai_codex"].includes(form.api_format)) && <div className="field"><label>Base URL <span className="field-optional">(optional)</span></label>
        <input type="url" value={form.base_url} placeholder={PROVIDER_BASE_URL_PLACEHOLDERS[form.api_format] || ""} onChange={e => upd({
          base_url: e.target.value
        })} />
        {form.api_format === "bedrock" && <div className="field-hint">Leave blank to use the default boto3 Bedrock endpoint for AWS_REGION / AWS_DEFAULT_REGION.</div>}
        {form.api_format === "github_copilot" && <div className="field-hint">No base URL is needed. AESPA uses the official GitHub Copilot SDK.</div>}
        {form.api_format === "bedrock_mantle" && <div className="field-hint">Best left blank — AESPA picks the endpoint per model (the <code>/openai/v1</code> path for <code>openai.gpt-5.x</code>, <code>/v1</code> for <code>gpt-oss</code>) and defaults to the us-east-2 region (or BEDROCK_MANTLE_REGION / AWS_REGION). Set only to point at another region's host, e.g. https://bedrock-mantle.us-west-2.api.aws.</div>}
      </div>}
      {form.api_format === "factory_droid" && <div className="field-hint">Uses the account signed in through Droid CLI. AESPA does not read or store Factory credentials.</div>}
      {form.api_format === "openai_codex" && <>
        <div className="field-hint">Uses the local Codex CLI's default ChatGPT sign-in through the installed Codex app-server. No API key or base URL is used.</div>
        <CodexConnectionCard />
      </>}
      {form.api_format === "bedrock_mantle" && <div className="field"><label>Project ID <span className="field-optional">(optional)</span></label>
        <input type="text" value={form.project_id} placeholder="proj_5d5ykleja6cwpirysbb7" onChange={e => upd({
          project_id: e.target.value
        })} />
        <div className="field-hint">Sent as the OpenAI-Project header to attribute usage/cost to a Bedrock Mantle project. Use the project id (proj_…) from the Bedrock console, not its name. Leave blank for the account default project.</div>
      </div>}
      {form.api_format === "github_copilot" && <div className="field">
        <label>Copilot username <span className="field-optional">(optional)</span></label>
        <input type="text" autoComplete="off" value={form.username} placeholder="Use Copilot CLI's selected default account" onChange={e => upd({
          username: e.target.value
        })} />
        <div className="field-hint">Enter a login from Copilot CLI's <code>/user</code> list. Leave blank to use its selected default account.</div>
      </div>}
      <div className="field">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
          <label style={{ margin: 0 }}>Model names</label>
          <button
            type="button"
            className="btn secondary sm"
            disabled={loadingModels}
            onClick={onLoadModels}
            title="Fetch available model names from API and overwrite current list"
          >
            {loadingModels ? "Loading models…" : "Load models from API"}
          </button>
        </div>
        <textarea rows="5" value={form.models} placeholder={PROVIDER_MODEL_PLACEHOLDERS[form.api_format] || ""} onChange={e => upd({
          models: e.target.value
        })}></textarea>
        {loadMessage && <div className="field-hint" style={{ color: "var(--accent)", marginBottom: "4px" }}>{loadMessage}</div>}
        <div className="field-hint">Enter one model per line, or separate models with commas. Leave blank to use the models shown in the placeholder.</div>
      </div>
      {!(["factory_droid", "openai_codex"].includes(form.api_format)) && <div className="field">
        <label>{form.api_format === "github_copilot" ? "GitHub token" : "API Key"} <span className="field-optional">(optional)</span></label>
        <div className="row" style={{ gap: "8px" }}>
          <input
            type="password"
            value={form.api_key}
            placeholder={
              form.clear_api_key
                ? "Key will be removed on save"
                : form.has_api_key && !form.api_key
                ? "•••••••• (leave blank to keep current key)"
                : form.api_format === "bedrock"
                ? "Leave blank to use boto3 / AWS_PROFILE / IAM role"
                : form.api_format === "bedrock_mantle"
                ? "Bedrock API key, or leave blank for AWS credentials"
                : "Leave blank if not required"
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
        {form.api_format === "bedrock" && <div className="field-hint">When blank, Aespa uses boto3 credentials from AWS_PROFILE, environment variables, SSO, or the instance/task role.</div>}
        {form.api_format === "bedrock_mantle" && <div className="field-hint">With a key, Mantle authenticates via Bearer token. Leave blank to sign requests with AWS credentials (SigV4) from AWS_PROFILE, environment variables, SSO, or an IAM role — the same fallback as the Bedrock Runtime provider.</div>}
        {form.api_format === "github_copilot" && <div className="field-hint">Leave blank to use the Copilot username above, or Copilot CLI's selected default account when no username is set. An explicit token takes precedence. For headless use, enter a GitHub user token whose account has Copilot access or set COPILOT_GITHUB_TOKEN.</div>}
      </div>}
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
