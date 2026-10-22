import * as extensionsApi from "../../shared/api/extensions.js";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";
import * as sitesApi from "../../shared/api/sites.js";
import * as apiCollectionsApi from "../../shared/api/apiCollections.js";
import { useEffect, useRef, useState } from "react";

import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";

const UPLOAD_PROVIDER_ID = "core.upload";

function ProviderField({ field, value, onChange }) {
  const inputId = `sast-source-${field.key}`;
  if (field.type === "boolean") {
    return (
      <label className="field checkbox-row" htmlFor={inputId}>
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
    <div className="field">
      <label htmlFor={inputId}>
        {field.label} {field.required ? <span className="field-required">*</span> : null}
      </label>
      {field.type === "select" ? (
        <select
          id={inputId}
          className="select"
          value={value ?? field.default ?? ""}
          required={field.required}
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
          required={field.required}
          placeholder={field.placeholder || ""}
          onChange={(event) =>
            onChange(field.type === "number" ? Number(event.target.value) : event.target.value)
          }
        />
      )}
      {field.help ? (
        <div className="subtle" style={{ marginTop: 6, fontSize: 13 }}>
          {field.help}
        </div>
      ) : null}
    </div>
  );
}

export function SastRunForm({ showSastDeepScan = false }) {
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [llmProfileId, setLlmProfileId] = useState("");
  const [analysisMode, setAnalysisMode] = useState("light");
  const [profiles, setProfiles] = useState([]);
  const [sites, setSites] = useState([]);
  const [apiCollections, setApiCollections] = useState([]);
  const [associationType, setAssociationType] = useState("");
  const [associationId, setAssociationId] = useState("");
  const [providers, setProviders] = useState([]);
  const [providerId, setProviderId] = useState(UPLOAD_PROVIDER_ID);
  const [providerValues, setProviderValues] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    Promise.all([settingsApi.listLLMProfiles(), extensionsApi.listSourceProviders()])
      .then(([profileItems, providerItems]) => {
        setProfiles(profileItems || []);
        setProviders(providerItems || []);
      })
      .catch((loadError) => setError(loadError.message));
  }, []);

  useEffect(() => {
    Promise.all([sitesApi.listSites(), apiCollectionsApi.listApiCollections()])
      .then(([siteItems, apiItems]) => {
        setSites(siteItems || []);
        setApiCollections(apiItems || []);
      })
      .catch((loadError) => setError(loadError.message));
  }, []);

  const effectiveAnalysisMode = showSastDeepScan ? analysisMode : "light";
  const provider = providers.find((item) => item.id === providerId);
  const providerAvailable = provider?.availability?.available !== false;
  const sourceReady =
    providerId === UPLOAD_PROVIDER_ID
      ? Boolean(file)
      : Boolean(provider) &&
        providerAvailable &&
        (provider.request_fields || []).every(
          (field) => !field.required || String(providerValues[field.key] || "").trim(),
        );

  const onSubmit = async (event) => {
    event.preventDefault();
    if (!sourceReady) {
      setError(
        providerId === UPLOAD_PROVIDER_ID
          ? "Please select a source ZIP file."
          : "Complete the required source fields before creating the scan.",
      );
      return;
    }
    if (associationType && !associationId) {
      setError(`Choose a ${associationType === "site" ? "Site" : "API"} or select Unassociated.`);
      return;
    }
    const association = associationId
      ? {
          [associationType === "site" ? "site_id" : "associated_collection_id"]:
            Number(associationId),
        }
      : {};
    setSaving(true);
    setError(null);
    try {
      let run;
      if (providerId === UPLOAD_PROVIDER_ID) {
        run = await sastRunsApi.createStandaloneSastRun(
          file,
          name.trim() || null,
          llmProfileId ? +llmProfileId : null,
          effectiveAnalysisMode,
          association,
        );
        await sastRunsApi.startSastScan(run.id);
      } else {
        run = await sastRunsApi.createSastRunFromSource({
          provider_id: providerId,
          parameters: providerValues,
          name: name.trim() || null,
          llm_profile_id: llmProfileId ? +llmProfileId : null,
          analysis_mode: effectiveAnalysisMode,
          ...association,
        });
      }
      nav(`#/sast-runs/${run.id}/progress`);
    } catch (submitError) {
      setError(submitError.message);
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/sast-runs">SAST</Crumb>
            <Sep />
            New SAST scan
          </>
        }
      />
      <div className="content scroll-content">
        <form className="card" style={{ maxWidth: 620 }} onSubmit={onSubmit}>
          <div className="form-section-title">New SAST scan</div>

          <div className="field">
            <label htmlFor="sast-source-provider">Source</label>
            <select
              id="sast-source-provider"
              className="select"
              value={providerId}
              onChange={(event) => {
                setProviderId(event.target.value);
                setError(null);
              }}
            >
              <option value={UPLOAD_PROVIDER_ID}>Upload ZIP</option>
              {providers.map((item) => (
                <option key={item.id} value={item.id} disabled={!item.availability?.available}>
                  {item.label}
                  {!item.availability?.available ? " - setup required" : ""}
                </option>
              ))}
            </select>
          </div>

          {providerId === UPLOAD_PROVIDER_ID ? (
            <div className="field">
              <label>
                Source Archive <span className="field-required">*</span>{" "}
                <span className="subtle">(max 250 MB)</span>
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                style={{ display: "none" }}
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
              <div className="row" style={{ gap: 8, alignItems: "center" }}>
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {file ? "Change ZIP file" : "Choose ZIP file"}
                </button>
                <span className="subtle" style={{ fontSize: 13 }}>
                  {file ? file.name : "No file selected"}
                </span>
              </div>
            </div>
          ) : provider ? (
            <>
              <div className={`alert ${providerAvailable ? "success" : "warning"}`}>
                {provider.availability?.message}
                {!providerAvailable ? (
                  <>
                    {" "}
                    <a href="#/extensions">Configure extensions</a>
                  </>
                ) : null}
              </div>
              {(provider.request_fields || []).map((field) => (
                <ProviderField
                  key={field.key}
                  field={field}
                  value={providerValues[field.key]}
                  onChange={(value) =>
                    setProviderValues((previous) => ({ ...previous, [field.key]: value }))
                  }
                />
              ))}
            </>
          ) : null}

          <div className="field">
            <label htmlFor="sast-run-name">
              Name <span className="subtle">(optional - auto-generated if blank)</span>
            </label>
            <input
              id="sast-run-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Payments API review"
            />
          </div>

          <div className="field">
            <label htmlFor="sast-association-type">Associate with</label>
            <select
              id="sast-association-type"
              className="select"
              value={associationType}
              onChange={(event) => {
                setAssociationType(event.target.value);
                setAssociationId("");
              }}
            >
              <option value="">Unassociated</option>
              <option value="site">Site</option>
              <option value="api">API</option>
            </select>
          </div>
          {associationType && (
            <div className="field">
              <label htmlFor="sast-association-target">
                {associationType === "site" ? "Site" : "API"}
              </label>
              <select
                id="sast-association-target"
                className="select"
                value={associationId}
                required
                onChange={(event) => setAssociationId(event.target.value)}
              >
                <option value="">Choose {associationType === "site" ? "Site" : "API"}</option>
                {(associationType === "site" ? sites : apiCollections).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {showSastDeepScan && (
            <div className="field">
              <label htmlFor="sast-analysis-mode">Analysis mode</label>
              <select
                id="sast-analysis-mode"
                className="select"
                value={analysisMode}
                onChange={(event) => setAnalysisMode(event.target.value)}
              >
                <option value="light">Light - lower-cost source analysis</option>
                <option value="deep">Deep - full threat-directed analysis</option>
              </select>
              <div className="subtle" style={{ marginTop: 6, fontSize: 13 }}>
                {analysisMode === "light"
                  ? "Lists the source files, looks for possible issues, confirms them, and checks how they could be reached."
                  : "Also maps the application, builds threat scenarios, plans security checks, merges duplicate findings, and reviews areas that may have been missed."}
              </div>
            </div>
          )}

          <div className="field">
            <label htmlFor="sast-llm-profile">
              LLM profile{" "}
              <span className="subtle">
                (optional - uses the globally active profile if not set)
              </span>
            </label>
            <select
              id="sast-llm-profile"
              className="select"
              value={llmProfileId}
              onChange={(event) => setLlmProfileId(event.target.value)}
            >
              <option value="">Use global active profile</option>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name}
                  {profile.default_model_name ? ` · ${profile.default_model_name}` : ""}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="alert error form-error" role="alert">
              {error}
            </div>
          )}
          <div className="row spread" style={{ marginTop: 16 }}>
            <button type="button" className="btn ghost" onClick={() => nav("#/sast-runs")}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={saving || !sourceReady}>
              {saving ? "Creating…" : "Create and start scan"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
