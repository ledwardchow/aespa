import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect, useRef } from "react";

import { nav } from "../../shared/navigation/router.js";

import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";

export function SastRunForm() {
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [llmProfileId, setLlmProfileId] = useState("");
  const [profiles, setProfiles] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    settingsApi
      .listLLMProfiles()
      .then((p) => setProfiles(p || []))
      .catch((e) => setError(e.message));
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a source ZIP file.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const run = await sastRunsApi.createStandaloneSastRun(
        file,
        name.trim() || null,
        llmProfileId ? +llmProfileId : null,
      );
      await sastRunsApi.startSastScan(run.id);
      nav(`#/sast-runs/${run.id}/progress`);
    } catch (e) {
      setError(e.message);
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
        <form className="card" style={{ maxWidth: 560 }} onSubmit={onSubmit}>
          <div className="form-section-title">New SAST Scan</div>
          {error && <div className="alert error">{error}</div>}

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
              onChange={(e) =>
                setFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)
              }
            />
            <div className="row" style={{ gap: 8, alignItems: "center" }}>
              <button
                type="button"
                className="btn secondary"
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
              >
                {file ? "Change ZIP file" : "Choose ZIP file"}
              </button>
              <span className="subtle" style={{ fontSize: 13 }}>
                {file ? file.name : "No file selected"}
              </span>
            </div>
          </div>

          <div className="field">
            <label>
              Name <span className="subtle">(optional — auto-generated if blank)</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={file ? `e.g. SAST – ${file.name}` : "e.g. SAST – source.zip"}
            />
          </div>

          <div className="field">
            <label>
              LLM profile{" "}
              <span className="subtle">
                (optional — uses the globally active profile if not set)
              </span>
            </label>
            <select
              className="select"
              value={llmProfileId}
              onChange={(e) => setLlmProfileId(e.target.value)}
            >
              <option value="">— Use global active profile —</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.default_model_name ? ` · ${p.default_model_name}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="row spread" style={{ marginTop: 16 }}>
            <button type="button" className="btn ghost" onClick={() => nav("#/sast-runs")}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={saving || !file}>
              {saving ? "Creating…" : "Create & Start Scan"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
