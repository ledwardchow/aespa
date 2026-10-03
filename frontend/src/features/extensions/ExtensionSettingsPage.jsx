import { useEffect, useState } from "react";

import * as extensionsApi from "../../shared/api/extensions.js";
import { Crumb, PageHeader, Sep } from "../../shared/ui/PageHeader.jsx";

function ExtensionSettingField({ extensionId, field, value, hasSecret, onChange }) {
  const inputId = `extension-${extensionId}-${field.key}`;
  if (field.type === "secret") {
    return (
      <div className="field" style={{ marginTop: 12 }}>
        <label htmlFor={inputId}>{field.label}</label>
        <div className="row" style={{ gap: 8 }}>
          <input
            id={inputId}
            type="password"
            autoComplete="new-password"
            value={value || ""}
            placeholder={
              value === ""
                ? "Will be removed on save"
                : hasSecret
                  ? "Saved - leave blank to keep"
                  : field.placeholder || ""
            }
            onChange={(event) => onChange(event.target.value || null)}
          />
          {hasSecret ? (
            <button className="btn secondary" type="button" onClick={() => onChange("")}>
              Remove
            </button>
          ) : null}
        </div>
        {field.help ? <div className="subtle">{field.help}</div> : null}
      </div>
    );
  }
  if (field.type === "boolean") {
    return (
      <label className="checkbox-row" htmlFor={inputId}>
        <input
          id={inputId}
          type="checkbox"
          checked={Boolean(value ?? field.default)}
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

export function ExtensionSettingsPage({ extensionId }) {
  const [extension, setExtension] = useState(null);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(null);
  const [checkResult, setCheckResult] = useState(null);

  useEffect(() => {
    let active = true;
    extensionsApi
      .listExtensions()
      .then((items) => {
        if (!active) return;
        const found = items.find((item) => item.id === extensionId);
        setExtension(found || null);
        setSettings(found?.settings || {});
      })
      .catch((loadError) => active && setError(loadError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [extensionId]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await extensionsApi.updateExtensionSettings(extensionId, settings);
      setExtension(updated);
      setSettings(updated.settings || {});
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  };

  const check = async () => {
    setChecking(true);
    setError(null);
    setCheckResult(null);
    try {
      const updated = await extensionsApi.checkExtension(extensionId);
      setExtension(updated);
      const providers = [...(updated.source_providers || []), ...(updated.web_scanners || [])];
      setCheckResult({
        message:
          providers
            .map((item) => item.availability?.message)
            .filter(Boolean)
            .join(" ") || "Check complete.",
        available: providers.every((item) => item.availability?.available),
      });
    } catch (checkError) {
      setError(checkError.message);
    } finally {
      setChecking(false);
    }
  };

  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/extensions">Extensions</Crumb>
            <Sep />
            {extension?.name || extensionId}
          </>
        }
      />
      <div className="content scroll-content">
        {loading ? <div className="subtle">Loading…</div> : null}
        {error ? (
          <div className="alert error" role="alert">
            {error}
          </div>
        ) : null}
        {!loading && !extension && !error ? (
          <div className="subtle">Extension not found.</div>
        ) : null}
        {extension ? (
          <section className="card" style={{ maxWidth: 720 }}>
            <div className="form-section-title">{extension.name} settings</div>
            <div className="subtle" style={{ marginTop: 4 }}>
              {extension.id}
            </div>
            <div className="subtle" style={{ marginTop: 4 }}>
              Author: {extension.author || "Not specified"}
            </div>
            {!extension.enabled ? (
              <div className="alert warning" style={{ marginTop: 16 }}>
                Enable this extension from the <a href="#/extensions">Extensions list</a> to edit
                its settings.
              </div>
            ) : (
              <>
                {(extension.settings_fields || []).length ? (
                  extension.settings_fields.map((field) => (
                    <ExtensionSettingField
                      key={field.key}
                      extensionId={extension.id}
                      field={field}
                      value={settings[field.key]}
                      hasSecret={extension.has_secrets?.[field.key]}
                      onChange={(value) =>
                        setSettings((previous) => ({ ...previous, [field.key]: value }))
                      }
                    />
                  ))
                ) : (
                  <div className="subtle" style={{ marginTop: 16 }}>
                    This extension has no settings.
                  </div>
                )}
                {checkResult ? (
                  <div
                    className={`alert ${checkResult.available ? "success" : "warning"}`}
                    style={{ marginTop: 16 }}
                  >
                    {checkResult.message}
                  </div>
                ) : null}
                <div className="row" style={{ justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
                  <button
                    className="btn secondary"
                    type="button"
                    disabled={checking}
                    onClick={check}
                  >
                    {checking ? "Checking…" : "Check connection"}
                  </button>
                  {(extension.settings_fields || []).length ? (
                    <button className="btn" type="button" disabled={saving} onClick={save}>
                      {saving ? "Saving…" : "Save settings"}
                    </button>
                  ) : null}
                </div>
              </>
            )}
          </section>
        ) : null}
      </div>
    </>
  );
}
