import { useState, useEffect, useRef, useCallback } from "react";
import { DEFAULT_SPECIALIST_AGENT_FORM } from "./Settings/UpstreamProxySettings";
import { PROVIDER_DEFAULT_BASE_URLS, DEFAULT_PROVIDER_FORM, DEFAULT_LLM_FORM, API_FORMAT_LABELS } from "./Settings/BurpRestApiSettings";
import { AGENT_ROLE_LABELS } from "./Settings/LLMModelForm";
import { DEFAULT_BURP_REST_API_FORM } from "./Settings/SpecialistAgentSettings";
import { api } from "../lib/api";

import { ScannerPolicyFields } from "./Settings/ScannerPolicyFields";
import { ScannerPolicySettings } from "./Settings/ScannerPolicySettings";
import { UpstreamProxySettings } from "./Settings/UpstreamProxySettings";
import { SpecialistAgentSettings } from "./Settings/SpecialistAgentSettings";
import { BurpRestApiSettings } from "./Settings/BurpRestApiSettings";
import { LLMProviderForm } from "./Settings/LLMProviderForm";
import { LLMModelForm } from "./Settings/LLMModelForm";
import { ScanProfileForm } from "./Settings/ScanProfileForm";
import { ValidatorSettings } from "./Settings/ValidatorSettings";
import { ScopeHostsPanel } from "./Settings/ScopeHostsPanel";
import { ScanPolicyPage } from "./Settings/ScanPolicyPage";
import { ExternalIntegrationsPage } from "./Settings/ExternalIntegrationsPage";
import { DebugPage } from "./Settings/DebugPage";
import { ReportingDebugPage } from "./Settings/ReportingDebugPage";
import { DebugFindingsTable } from "./Settings/DebugFindingsTable";
// ── Settings ──────────────────────────────────────────────────────────────────

export function specialistAgentToForm(cfg) {
  return cfg ? {
    enabled: cfg.enabled ?? true,
    max_concurrent: cfg.max_concurrent ?? 5,
    max_steps: cfg.max_steps ?? 30,
    min_priority: cfg.min_priority ?? 7,
    dispatch_idor: cfg.dispatch_idor ?? true,
    dispatch_auth_bypass: cfg.dispatch_auth_bypass ?? true,
    dispatch_sqli: cfg.dispatch_sqli ?? true,
    dispatch_xss: cfg.dispatch_xss ?? true,
    dispatch_business_logic: cfg.dispatch_business_logic ?? true,
    dispatch_ssrf: cfg.dispatch_ssrf ?? true,
    dispatch_path_traversal: cfg.dispatch_path_traversal ?? true,
    dispatch_cors: cfg.dispatch_cors ?? false,
    dispatch_crypto: cfg.dispatch_crypto ?? true,
    dispatch_config: cfg.dispatch_config ?? false,
    trigger_specialist_on_burp: cfg.trigger_specialist_on_burp ?? false
  } : {
    ...DEFAULT_SPECIALIST_AGENT_FORM
  };
}
export function specialistAgentPayload(form) {
  return {
    enabled: !!form.enabled,
    max_concurrent: Number(form.max_concurrent),
    max_steps: Number(form.max_steps),
    min_priority: Number(form.min_priority),
    dispatch_idor: !!form.dispatch_idor,
    dispatch_auth_bypass: !!form.dispatch_auth_bypass,
    dispatch_sqli: !!form.dispatch_sqli,
    dispatch_xss: !!form.dispatch_xss,
    dispatch_business_logic: !!form.dispatch_business_logic,
    dispatch_ssrf: !!form.dispatch_ssrf,
    dispatch_path_traversal: !!form.dispatch_path_traversal,
    dispatch_cors: !!form.dispatch_cors,
    dispatch_crypto: !!form.dispatch_crypto,
    dispatch_config: !!form.dispatch_config,
    trigger_specialist_on_burp: !!form.trigger_specialist_on_burp
  };
}
export function burpRestApiToForm(cfg) {
  return cfg ? {
    enabled: cfg.enabled ?? false,
    api_url: cfg.api_url || DEFAULT_BURP_REST_API_FORM.api_url,
    api_key: "",
    has_api_key: cfg.has_api_key ?? false,
    clear_api_key: false,
    scan_configuration_name: cfg.scan_configuration_name || "",
    scan_sqli: cfg.scan_sqli ?? true,
    scan_xss: cfg.scan_xss ?? true,
    scan_command_injection: cfg.scan_command_injection ?? true,
    scan_path_traversal: cfg.scan_path_traversal ?? true,
    scan_ssrf: cfg.scan_ssrf ?? true,
    scan_xxe: cfg.scan_xxe ?? true,
    scan_ssti: cfg.scan_ssti ?? true
  } : {
    ...DEFAULT_BURP_REST_API_FORM,
    has_api_key: false,
    clear_api_key: false
  };
}
export function burpRestApiPayload(form) {
  let apiKeyPayload = null;
  if (form.clear_api_key) {
    apiKeyPayload = "";
  } else if (form.api_key.trim()) {
    apiKeyPayload = form.api_key.trim();
  } else {
    apiKeyPayload = null;
  }
  return {
    enabled: !!form.enabled,
    api_url: form.api_url.trim(),
    api_key: apiKeyPayload,
    scan_configuration_name: form.scan_configuration_name.trim() || null,
    scan_sqli: !!form.scan_sqli,
    scan_xss: !!form.scan_xss,
    scan_command_injection: !!form.scan_command_injection,
    scan_path_traversal: !!form.scan_path_traversal,
    scan_ssrf: !!form.scan_ssrf,
    scan_xxe: !!form.scan_xxe,
    scan_ssti: !!form.scan_ssti
  };
}
export function providerToForm(provider) {
  return provider ? {
    name: provider.name || "",
    api_format: provider.api_format || "anthropic",
    base_url: provider.base_url || "",
    project_id: provider.project_id || "",
    models: (provider.models || []).join("\n"),
    api_key: "",
    has_api_key: provider.has_api_key ?? false,
    clear_api_key: false,
    max_tpm: provider.max_tpm != null ? provider.max_tpm : "",
    max_rpm: provider.max_rpm != null ? provider.max_rpm : ""
  } : {
    ...DEFAULT_PROVIDER_FORM,
    has_api_key: false,
    clear_api_key: false
  };
}
export function providerPayload(form) {
  let apiKeyPayload = null;
  if (form.clear_api_key) {
    apiKeyPayload = "";
  } else if (form.api_key.trim()) {
    apiKeyPayload = form.api_key.trim();
  } else {
    apiKeyPayload = null;
  }
  return {
    name: form.name.trim(),
    api_format: form.api_format,
    base_url: form.base_url.trim() || null,
    project_id: form.api_format === "bedrock_mantle" ? form.project_id.trim() || null : null,
    models: form.models.split(/\r?\n|,/).map(m => m.trim()).filter(Boolean),
    api_key: apiKeyPayload,
    max_tpm: form.max_tpm !== "" ? Number(form.max_tpm) : null,
    max_rpm: form.max_rpm !== "" ? Number(form.max_rpm) : null
  };
}
export function llmProfileToForm(cfg, providers = []) {
  const providerId = cfg?.provider_id || providers[0]?.id || "";
  const provider = providers.find(p => p.id === providerId) || providers[0];
  if (cfg) {
    const hasTemp = cfg.temperature !== null && cfg.temperature !== undefined;
    return {
      name: cfg.name ?? "Default",
      provider_id: providerId,
      model: cfg.model,
      max_tokens: cfg.max_tokens,
      temperature: hasTemp ? cfg.temperature : 0.2,
      use_temperature: hasTemp,
      use_vision: cfg.use_vision ?? false,
      force_tool_choice: cfg.force_tool_choice ?? false
    };
  }
  return {
    ...DEFAULT_LLM_FORM,
    provider_id: provider?.id || "",
    model: provider?.models?.[0] || ""
  };
}
export function llmPayload(form) {
  return {
    name: form.name.trim(),
    provider_id: Number(form.provider_id),
    model: form.model.trim(),
    max_tokens: Number(form.max_tokens),
    temperature: form.use_temperature ? Number(form.temperature) : null,
    use_vision: form.use_vision,
    force_tool_choice: form.force_tool_choice
  };
}
export function scanProfileToForm(profile) {
  const rm = profile && profile.role_models || {};
  const role_models = {};
  for (const [role] of AGENT_ROLE_LABELS) role_models[role] = rm[role] ? String(rm[role]) : "";
  return {
    name: profile?.name || "",
    default_model_id: profile?.default_model_id ? String(profile.default_model_id) : "",
    role_models
  };
}
export function SettingsPage() {
  const [profiles, setProfiles] = useState(null); // scan profiles (LLMProfile)
  const [models, setModels] = useState(null); // models (LLMConfig)
  const [providers, setProviders] = useState(null);
  const [tab, setTab] = useState("profiles");
  const [screen, setScreen] = useState("list");
  const [editing, setEditing] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const importRef = useRef(null);
  const load = useCallback(async () => {
    setError(null);
    try {
      const [profItems, modelItems, providerItems] = await Promise.all([api.listLLMProfiles(), api.listLLMModels(), api.listLLMProviders()]);
      setProfiles(profItems);
      setModels(modelItems);
      setProviders(providerItems);
    } catch (e) {
      setError(e.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const onSaved = async () => {
    await load();
    setScreen("list");
    setEditing(null);
  };
  const onEdit = item => {
    setEditing(item);
    setScreen("edit");
    setError(null);
  };
  const onNew = () => {
    setEditing(null);
    setScreen("new");
    setError(null);
  };
  const onCancel = () => {
    setScreen("list");
    setEditing(null);
    setError(null);
  };
  const onActivate = async item => {
    setBusyId(item.id);
    setError(null);
    try {
      if (tab === "profiles") await api.activateLLMProfile(item.id);else await api.activateLLMModel(item.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };
  const onDelete = async item => {
    const what = tab === "profiles" ? "profile" : "model";
    if (!confirm(`Delete LLM ${what} "${item.name}"?`)) return;
    setBusyId(item.id);
    setError(null);
    try {
      if (tab === "profiles") await api.deleteLLMProfile(item.id);else await api.deleteLLMModel(item.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };
  const onDeleteProvider = async provider => {
    if (!confirm(`Delete LLM provider "${provider.name}"?`)) return;
    setBusyId(provider.id);
    setError(null);
    try {
      await api.deleteLLMProvider(provider.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };
  const switchTab = next => {
    setTab(next);
    setScreen("list");
    setEditing(null);
    setError(null);
  };
  const onExport = async () => {
    setError(null);
    try {
      const data = await api.exportLLMConfig();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json"
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aespa-llm-config-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    }
  };
  const onImportClick = () => {
    if (importRef.current) importRef.current.click();
  };
  const onImportFile = async e => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setError(null);
    setImporting(true);
    try {
      const text = await file.text();
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch {
        throw new Error("Invalid JSON file");
      }
      const result = await api.importLLMConfig(parsed);
      await load();
      alert(`Import complete: ${result.providers_created} provider(s) created, ${result.providers_updated} updated; ${result.profiles_created} model(s) created, ${result.profiles_updated} updated.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  };
  const TAB_NOUN = {
    profiles: "Profile",
    models: "Model",
    providers: "Provider"
  };
  const noun = TAB_NOUN[tab];
  const title = screen === "new" ? `New LLM ${noun}` : screen === "edit" ? `Edit LLM ${noun}` : `LLM ${noun}s`;
  const canCreateModel = (providers || []).length > 0;
  const canCreateProfile = (models || []).length > 0;
  const newDisabled = tab === "models" && !canCreateModel || tab === "profiles" && !canCreateProfile;
  const loaded = profiles && models && providers;
  return <>
    <div className="topbar">
      <div className="topbar-title">{title}</div>
      <div className="topbar-actions">
        <button className="btn secondary sm" disabled={importing} onClick={onExport}>Export</button>
        <button className="btn secondary sm" disabled={importing} onClick={onImportClick}>{importing ? "Importing…" : "Import"}</button>
        <input ref={importRef} type="file" accept=".json,application/json" style={{
          display: "none"
        }} onChange={onImportFile} />
        {screen === "list" && <button className="btn" disabled={newDisabled} onClick={onNew}>New {noun.toLowerCase()}</button>}
      </div>
    </div>
    <div className="content scroll-content settings-content">
      <div className="tab-bar settings-tab-bar">
        <button className={"tab-btn " + (tab === "profiles" ? "active" : "")} onClick={() => switchTab("profiles")}>Profiles</button>
        <button className={"tab-btn " + (tab === "models" ? "active" : "")} onClick={() => switchTab("models")}>Models</button>
        <button className={"tab-btn " + (tab === "providers" ? "active" : "")} onClick={() => switchTab("providers")}>Providers</button>
      </div>
      {!loaded && !error && <div className="subtle">Loading…</div>}
      {error && <div className="alert error">{error}</div>}
      {loaded && tab === "profiles" && screen === "list" && <>
        {models.length === 0 && <div className="alert">Create a model before adding scan profiles.</div>}
        <div className="settings-list settings-list-scanprofiles">
          <div className="settings-list-head">
            <div>Name</div><div>Default model</div><div>Overrides</div><div>Status</div><div></div>
          </div>
          {profiles.map(p => <div className="settings-list-row" key={p.id}>
              <div><strong>{p.name}</strong></div>
              <div className="mono">{p.default_model_name || (p.default_model_id ? `#${p.default_model_id}` : "—")}</div>
              <div>{Object.keys(p.role_models || {}).length || <span className="subtle">none</span>}</div>
              <div>{p.is_active ? <span className="badge ok">Active</span> : <span className="subtle">Inactive</span>}</div>
              <div className="row settings-list-actions">
                {!p.is_active && <button className="btn sm secondary" disabled={busyId === p.id} onClick={() => onActivate(p)}>Use</button>}
                <button className="btn sm" disabled={busyId === p.id} onClick={() => onEdit(p)}>Edit</button>
                <button className="btn danger-outline sm" disabled={busyId === p.id} onClick={() => onDelete(p)}>Delete</button>
              </div>
            </div>)}
        </div></>}
      {loaded && tab === "models" && screen === "list" && <>
        {providers.length === 0 && <div className="alert">Create a provider before adding models.</div>}
        <div className="settings-list settings-list-profiles">
          <div className="settings-list-head">
            <div>Name</div><div>Provider</div><div>Model</div><div>Vision</div><div>Status</div><div></div>
          </div>
          {models.map(p => <div className="settings-list-row" key={p.id}>
              <div><strong>{p.name}</strong></div>
              <div>{p.provider_name || `Provider #${p.provider_id}`}</div>
              <div className="mono">{p.model}</div>
              <div>{p.use_vision ? "On" : "Off"}</div>
              <div>{p.is_active ? <span className="badge ok">Active</span> : <span className="subtle">Inactive</span>}</div>
              <div className="row settings-list-actions">
                {!p.is_active && <button className="btn sm secondary" disabled={busyId === p.id} onClick={() => onActivate(p)}>Use</button>}
                <button className="btn sm" disabled={busyId === p.id} onClick={() => onEdit(p)}>Edit</button>
                <button className="btn danger-outline sm" disabled={busyId === p.id} onClick={() => onDelete(p)}>Delete</button>
              </div>
            </div>)}
        </div></>}
      {loaded && tab === "providers" && screen === "list" && <div className="settings-list settings-list-providers">
          <div className="settings-list-head">
            <div>Name</div><div>API</div><div>Base URL</div><div>Models</div><div>Limits</div><div></div>
          </div>
          {providers.map(p => <div className="settings-list-row" key={p.id}>
              <div><strong>{p.name}</strong></div>
              <div>{API_FORMAT_LABELS[p.api_format] || p.api_format}</div>
              <div className="mono">{p.base_url || PROVIDER_DEFAULT_BASE_URLS[p.api_format] || "(must be set)"}</div>
              <div className="mono">{(p.models || []).join(", ")}</div>
              <div>
                {p.max_tpm || p.max_rpm ? <>
                  {p.max_tpm ? <div>{Number(p.max_tpm).toLocaleString()} TPM</div> : ""}
                  {p.max_rpm ? <div style={{
                fontSize: 11,
                color: "var(--muted)",
                marginTop: 1
              }}>{Number(p.max_rpm).toLocaleString()} RPM</div> : ""}
                </> : <span className="subtle">Unlimited</span>}
              </div>
              <div className="row settings-list-actions">
                <button className="btn sm" disabled={busyId === p.id} onClick={() => onEdit(p)}>Edit</button>
                <button className="btn danger-outline sm" disabled={busyId === p.id} onClick={() => onDeleteProvider(p)}>Delete</button>
              </div>
            </div>)}
        </div>}
      {loaded && tab === "profiles" && screen === "new" && <ScanProfileForm mode="new" models={models} onSaved={onSaved} onCancel={profiles.length ? onCancel : null} />}
      {loaded && tab === "profiles" && screen === "edit" && editing && <ScanProfileForm mode="edit" profile={editing} models={models} onSaved={onSaved} onCancel={onCancel} />}
      {loaded && tab === "models" && screen === "new" && <LLMModelForm mode="new" providers={providers} onSaved={onSaved} onCancel={models.length ? onCancel : null} />}
      {loaded && tab === "models" && screen === "edit" && editing && <LLMModelForm mode="edit" profile={editing} providers={providers} onSaved={onSaved} onCancel={onCancel} />}
      {loaded && tab === "providers" && screen === "new" && <LLMProviderForm mode="new" onSaved={onSaved} onCancel={providers.length ? onCancel : null} />}
      {loaded && tab === "providers" && screen === "edit" && editing && <LLMProviderForm mode="edit" provider={editing} onSaved={onSaved} onCancel={onCancel} />}
    </div></>;
}
export const DEFAULT_VALIDATOR_FORM = {
  enabled: true,
  max_steps: 20,
  min_severity: "low",
  end_scan_max_concurrent: 4,
  auto_validate_inline: true,
  require_concrete_disproof: true
};
export function validatorToForm(cfg) {
  return {
    enabled: cfg.enabled ?? true,
    max_steps: cfg.max_steps ?? 20,
    min_severity: cfg.min_severity ?? "low",
    end_scan_max_concurrent: cfg.end_scan_max_concurrent ?? 4,
    auto_validate_inline: cfg.auto_validate_inline ?? true,
    require_concrete_disproof: cfg.require_concrete_disproof ?? true
  };
}
export function validatorPayload(form) {
  return {
    enabled: form.enabled,
    max_steps: Number(form.max_steps),
    min_severity: form.min_severity,
    end_scan_max_concurrent: Number(form.end_scan_max_concurrent),
    auto_validate_inline: form.auto_validate_inline,
    require_concrete_disproof: form.require_concrete_disproof
  };
}

export { ScannerPolicyFields };
export { ScannerPolicySettings };
export { UpstreamProxySettings };
export { SpecialistAgentSettings };
export { BurpRestApiSettings };
export { LLMProviderForm };
export { LLMModelForm };
export { ScanProfileForm };
export { ValidatorSettings };
export { ScopeHostsPanel };
export { ScanPolicyPage };
export { ExternalIntegrationsPage };
export { DebugPage };
export { ReportingDebugPage };
export { DebugFindingsTable };
