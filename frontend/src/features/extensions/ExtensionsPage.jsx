import * as extensionsApi from "../../shared/api/extensions.js";
import { useEffect, useState } from "react";

import { PageHeader } from "../../shared/ui/PageHeader.jsx";

function ExtensionSettingField({ extensionId, field, value, onChange }) {
  const inputId = `extension-${extensionId}-${field.key}`;
  if (field.type === "boolean") {
    return (
      <label className="checkbox-row" htmlFor={inputId}>
        <input
          id={inputId}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span>{field.label}</span>
      </label>
    );
  }
  return (
    <div className="field" style={{ marginTop: 12 }}>
      <label htmlFor={inputId}>{field.label}</label>
      {field.type === "select" ? (
        <select
          id={inputId}
          className="select"
          value={value ?? field.default ?? ""}
          onChange={(event) => onChange(event.target.value)}
        >
          {(field.options || []).map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={inputId}
          type={field.type === "number" ? "number" : "text"}
          value={value ?? field.default ?? ""}
          placeholder={field.placeholder || ""}
          onChange={(event) =>
            onChange(field.type === "number" ? Number(event.target.value) : event.target.value)
          }
        />
      )}
      {field.help ? (
        <div className="subtle" style={{ marginTop: 5, fontSize: 12 }}>
          {field.help}
        </div>
      ) : null}
    </div>
  );
}

function ExtensionCard({ extension, onUpdated }) {
  const [settings, setSettings] = useState(extension.settings || {});
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState(null);
  const providers = extension.source_providers || [];
  const ready =
    extension.enabled &&
    extension.status === "loaded" &&
    providers.every((item) => item.availability?.available);

  useEffect(() => {
    setSettings(extension.settings || {});
  }, [extension.settings]);

  const setEnabled = async (enabled) => {
    setToggling(true);
    setError(null);
    try {
      onUpdated(await extensionsApi.setExtensionEnabled(extension.id, enabled));
    } catch (toggleError) {
      setError(toggleError.message);
    } finally {
      setToggling(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      onUpdated(await extensionsApi.updateExtensionSettings(extension.id, settings));
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  };

  const check = async () => {
    setChecking(true);
    setError(null);
    try {
      onUpdated(await extensionsApi.checkExtension(extension.id));
    } catch (checkError) {
      setError(checkError.message);
    } finally {
      setChecking(false);
    }
  };

  return (
    <section className="card" style={{ maxWidth: 720 }}>
      <div className="row spread" style={{ alignItems: "flex-start", gap: 16 }}>
        <div>
          <div className="form-section-title" style={{ marginBottom: 3 }}>
            {extension.name}
          </div>
          <div className="subtle">
            {extension.id} · v{extension.version} · API {extension.aespa_api}
          </div>
        </div>
        <div className="row" style={{ gap: 12 }}>
          <span
            className={`badge ${ready ? "ok" : extension.status === "failed" ? "error" : "neutral"}`}
          >
            {!extension.enabled
              ? "Disabled"
              : extension.status === "failed"
                ? "Failed"
                : ready
                  ? "Ready"
                  : "Setup required"}
          </span>
          <label className="checkbox-row">
            <input
              type="checkbox"
              aria-label={`Enable ${extension.name}`}
              checked={extension.enabled !== false}
              disabled={toggling}
              onChange={(event) => setEnabled(event.target.checked)}
            />
            <span>Enabled</span>
          </label>
        </div>
      </div>

      {extension.error ? (
        <div className="alert error" style={{ marginTop: 14 }}>
          {extension.error}
        </div>
      ) : null}

      {extension.enabled ? (
        providers.map((provider) => (
          <div key={provider.id} style={{ marginTop: 14 }}>
            <div style={{ fontWeight: 600 }}>{provider.label}</div>
            <div className="subtle" style={{ marginTop: 3 }}>
              {provider.description}
            </div>
            <div className={`alert ${provider.availability?.available ? "success" : "warning"}`}>
              {provider.availability?.message}
            </div>
          </div>
        ))
      ) : (
        <div className="subtle" style={{ marginTop: 14 }}>
          Enable this extension to use its features and settings.
        </div>
      )}

      {extension.enabled
        ? (extension.settings_fields || []).map((field) => (
            <ExtensionSettingField
              key={field.key}
              extensionId={extension.id}
              field={field}
              value={settings[field.key]}
              onChange={(value) => setSettings((previous) => ({ ...previous, [field.key]: value }))}
            />
          ))
        : null}

      {error ? (
        <div className="alert error" style={{ marginTop: 14 }}>
          {error}
        </div>
      ) : null}
      {extension.enabled ? (
        <div className="row" style={{ justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
          <button className="btn secondary" type="button" disabled={checking} onClick={check}>
            {checking ? "Checking…" : "Check"}
          </button>
          {(extension.settings_fields || []).length ? (
            <button className="btn" type="button" disabled={saving} onClick={save}>
              {saving ? "Saving…" : "Save settings"}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export function ExtensionsPage() {
  const [extensions, setExtensions] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    extensionsApi
      .listExtensions()
      .then((items) => setExtensions(items || []))
      .catch((loadError) => setError(loadError.message));
  }, []);

  const updateExtension = (updated) =>
    setExtensions((previous) =>
      (previous || []).map((item) => (item.id === updated.id ? updated : item)),
    );

  return (
    <>
      <PageHeader title="Extensions" />
      <div className="content scroll-content">
        {error ? <div className="alert error">{error}</div> : null}
        {extensions === null && !error ? <div className="subtle">Loading…</div> : null}
        <div style={{ display: "grid", gap: 14 }}>
          {(extensions || []).map((extension) => (
            <ExtensionCard key={extension.id} extension={extension} onUpdated={updateExtension} />
          ))}
        </div>
      </div>
    </>
  );
}
