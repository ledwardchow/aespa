import { Tabs } from "../../shared/ui/Tabs.tsx";
import { ProfilesList } from "./ProfilesList.jsx";
import { ModelsList } from "./ModelsList.jsx";
import { ProvidersList } from "./ProvidersList.jsx";
import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect, useRef, useCallback } from "react";

import { LLMProviderForm } from "./LLMProviderForm.jsx";
import { LLMModelForm } from "./LLMModelForm.jsx";
import { ScanProfileForm } from "./ScanProfileForm.jsx";

// ── Settings ──────────────────────────────────────────────────────────────────

const SETTINGS_TABS = [
  { key: "profiles", label: "Profiles" },
  { key: "models", label: "Models" },
  { key: "providers", label: "Providers" },
];

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
      const [profItems, modelItems, providerItems] = await Promise.all([
        settingsApi.listLLMProfiles(),
        settingsApi.listLLMModels(),
        settingsApi.listLLMProviders(),
      ]);
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
  const onEdit = (item) => {
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
  const onActivate = async (item) => {
    setBusyId(item.id);
    setError(null);
    try {
      await settingsApi.activateLLMProfile(item.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };
  const onDelete = async (item) => {
    const what = tab === "profiles" ? "profile" : "model";
    if (!confirm(`Delete LLM ${what} "${item.name}"?`)) return;
    setBusyId(item.id);
    setError(null);
    try {
      if (tab === "profiles") await settingsApi.deleteLLMProfile(item.id);
      else await settingsApi.deleteLLMModel(item.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };
  const onDeleteProvider = async (provider) => {
    if (!confirm(`Delete LLM provider "${provider.name}"?`)) return;
    setBusyId(provider.id);
    setError(null);
    try {
      await settingsApi.deleteLLMProvider(provider.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };
  const switchTab = (next) => {
    setTab(next);
    setScreen("list");
    setEditing(null);
    setError(null);
  };
  const onExport = async () => {
    setError(null);
    try {
      const data = await settingsApi.exportLLMConfig();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
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
  const onImportFile = async (e) => {
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
      const result = await settingsApi.importLLMConfig(parsed);
      await load();
      alert(
        `Import complete: ${result.providers_created} provider(s) created, ${result.providers_updated} updated; ${result.profiles_created} model(s) created, ${result.profiles_updated} updated.`,
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  };
  const TAB_NOUN = {
    profiles: "Profile",
    models: "Model",
    providers: "Provider",
  };
  const noun = TAB_NOUN[tab];
  const title =
    screen === "new" ? `New LLM ${noun}` : screen === "edit" ? `Edit LLM ${noun}` : `LLM ${noun}s`;
  const canCreateModel = (providers || []).length > 0;
  const canCreateProfile = (models || []).length > 0;
  const newDisabled =
    (tab === "models" && !canCreateModel) || (tab === "profiles" && !canCreateProfile);
  const loaded = profiles && models && providers;
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">{title}</div>
        <div className="topbar-actions">
          <button className="btn secondary sm" disabled={importing} onClick={onExport}>
            Export
          </button>
          <button className="btn secondary sm" disabled={importing} onClick={onImportClick}>
            {importing ? "Importing…" : "Import"}
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".json,application/json"
            style={{
              display: "none",
            }}
            onChange={onImportFile}
          />
          {screen === "list" && (
            <button className="btn" disabled={newDisabled} onClick={onNew}>
              New {noun.toLowerCase()}
            </button>
          )}
        </div>
      </div>
      <div className="content scroll-content settings-content">
        <Tabs
          label="LLM settings"
          className="tab-bar settings-tab-bar"
          tabs={SETTINGS_TABS}
          value={tab}
          onChange={switchTab}
        />
        {!loaded && !error && <div className="subtle">Loading…</div>}
        {error && <div className="alert error">{error}</div>}
        {loaded && (
          <ProfilesList
            visible={tab === "profiles" && screen === "list"}
            profiles={profiles}
            models={models}
            busyId={busyId}
            onActivate={onActivate}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        )}
        {loaded && (
          <ModelsList
            visible={tab === "models" && screen === "list"}
            models={models}
            providers={providers}
            busyId={busyId}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        )}
        {loaded && (
          <ProvidersList
            visible={tab === "providers" && screen === "list"}
            providers={providers}
            busyId={busyId}
            onEdit={onEdit}
            onDeleteProvider={onDeleteProvider}
          />
        )}
        {loaded && tab === "profiles" && screen === "new" && (
          <ScanProfileForm
            mode="new"
            models={models}
            onSaved={onSaved}
            onCancel={profiles.length ? onCancel : null}
          />
        )}
        {loaded && tab === "profiles" && screen === "edit" && editing && (
          <ScanProfileForm
            mode="edit"
            profile={editing}
            models={models}
            onSaved={onSaved}
            onCancel={onCancel}
          />
        )}
        {loaded && tab === "models" && screen === "new" && (
          <LLMModelForm
            mode="new"
            providers={providers}
            onSaved={onSaved}
            onCancel={models.length ? onCancel : null}
          />
        )}
        {loaded && tab === "models" && screen === "edit" && editing && (
          <LLMModelForm
            mode="edit"
            profile={editing}
            providers={providers}
            onSaved={onSaved}
            onCancel={onCancel}
          />
        )}
        {loaded && tab === "providers" && screen === "new" && (
          <LLMProviderForm
            mode="new"
            onSaved={onSaved}
            onCancel={providers.length ? onCancel : null}
          />
        )}
        {loaded && tab === "providers" && screen === "edit" && editing && (
          <LLMProviderForm mode="edit" provider={editing} onSaved={onSaved} onCancel={onCancel} />
        )}
      </div>
    </>
  );
}
