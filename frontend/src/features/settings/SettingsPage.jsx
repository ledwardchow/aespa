import { Tabs } from "../../shared/ui/Tabs.tsx";
import { ProfilesList } from "./ProfilesList.jsx";
import { ProvidersList } from "./ProvidersList.jsx";
import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect, useRef, useCallback } from "react";
import { nav } from "../../shared/navigation/router.js";

import { LLMProviderForm } from "./LLMProviderForm.jsx";
import { LLMModelForm } from "./LLMModelForm.jsx";
import { ScanProfileForm } from "./ScanProfileForm.jsx";

// ── Settings ──────────────────────────────────────────────────────────────────

const SETTINGS_TABS = [
  { key: "profiles", label: "Profiles" },
  { key: "providers", label: "Providers" },
];

const settingsListHref = (section) => `#/settings/${section}`;
const settingsNewHref = (section) => `#/settings/${section}/new`;
const settingsEditHref = (section, id) => `#/settings/${section}/${id}/edit`;

export function SettingsPage({
  section = "profiles",
  screen = "list",
  itemId,
  initialProviderId,
  initialModel,
}) {
  const [profiles, setProfiles] = useState(null); // scan profiles (LLMProfile)
  const [models, setModels] = useState(null); // models (LLMConfig)
  const [providers, setProviders] = useState(null);
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
  const loaded = profiles && models && providers;
  const editing = loaded
    ? section === "profiles"
      ? profiles.find((item) => item.id === itemId)
      : section === "providers"
        ? providers.find((item) => item.id === itemId)
        : models.find((item) => item.id === itemId)
    : null;
  const onSaved = async (savedItem) => {
    await load();
    if (section === "models") {
      const providerId = savedItem?.provider_id || editing?.provider_id || initialProviderId;
      nav(providerId ? settingsEditHref("providers", providerId) : settingsListHref("providers"));
      return;
    }
    nav(settingsListHref(section));
  };
  const onEdit = (item) => {
    nav(settingsEditHref(section, item.id));
  };
  const onNew = () => {
    nav(settingsNewHref(section));
  };
  const onConfigureProviderModel = (provider, modelName, configuredModel) => {
    if (configuredModel) {
      nav(settingsEditHref("models", configuredModel.id));
      return;
    }
    const query = new URLSearchParams({
      provider_id: String(provider.id),
      model: modelName,
    });
    nav(`#/settings/models/new?${query}`);
  };
  const onCancel = () => {
    if (section === "models") {
      const providerId = editing?.provider_id || initialProviderId;
      nav(providerId ? settingsEditHref("providers", providerId) : settingsListHref("providers"));
      return;
    }
    nav(settingsListHref(section));
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
    if (!confirm(`Delete LLM profile "${item.name}"?`)) return;
    setBusyId(item.id);
    setError(null);
    try {
      await settingsApi.deleteLLMProfile(item.id);
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
    nav(settingsListHref(next));
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
  const noun = TAB_NOUN[section];
  const title =
    screen === "new" ? `New LLM ${noun}` : screen === "edit" ? `Edit LLM ${noun}` : `LLM ${noun}s`;
  const canCreateProfile = (models || []).length > 0;
  const newDisabled = section === "profiles" && !canCreateProfile;
  const visibleTab = section === "models" ? "providers" : section;
  const missingItem = loaded && screen === "edit" && !editing;
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
          {screen === "list" && section !== "models" && (
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
          value={visibleTab}
          onChange={switchTab}
        />
        {!loaded && !error && <div className="subtle">Loading…</div>}
        {error && <div className="alert error">{error}</div>}
        {missingItem && (
          <div className="alert error">The requested {noun.toLowerCase()} was not found.</div>
        )}
        {loaded && (
          <ProfilesList
            visible={section === "profiles" && screen === "list"}
            profiles={profiles}
            models={models}
            busyId={busyId}
            onActivate={onActivate}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        )}
        {loaded && (
          <ProvidersList
            visible={section === "providers" && screen === "list"}
            providers={providers}
            models={models}
            busyId={busyId}
            onEdit={onEdit}
            onDeleteProvider={onDeleteProvider}
          />
        )}
        {loaded && section === "profiles" && screen === "new" && (
          <ScanProfileForm
            mode="new"
            models={models}
            onSaved={onSaved}
            onCancel={profiles.length ? onCancel : null}
          />
        )}
        {loaded && section === "profiles" && screen === "edit" && editing && (
          <ScanProfileForm
            mode="edit"
            profile={editing}
            models={models}
            onSaved={onSaved}
            onCancel={onCancel}
          />
        )}
        {loaded && section === "models" && screen === "new" && (
          <LLMModelForm
            mode="new"
            providers={providers}
            initialProviderId={initialProviderId}
            initialModel={initialModel}
            onSaved={onSaved}
            onCancel={onCancel}
          />
        )}
        {loaded && section === "models" && screen === "edit" && editing && (
          <LLMModelForm
            mode="edit"
            profile={editing}
            providers={providers}
            onSaved={onSaved}
            onCancel={onCancel}
          />
        )}
        {loaded && section === "providers" && screen === "new" && (
          <LLMProviderForm
            mode="new"
            models={models}
            profiles={profiles}
            onSaved={onSaved}
            onCancel={providers.length ? onCancel : null}
          />
        )}
        {loaded && section === "providers" && screen === "edit" && editing && (
          <LLMProviderForm
            mode="edit"
            provider={editing}
            models={models}
            profiles={profiles}
            onConfigureModel={(modelName, configuredModel) =>
              onConfigureProviderModel(editing, modelName, configuredModel)
            }
            onSaved={onSaved}
            onCancel={onCancel}
          />
        )}
      </div>
    </>
  );
}
