import * as apiCollectionsApi from "../../shared/api/apiCollections.js";
import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect } from "react";

import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Breadcrumbs } from "../../shared/ui/PageHeader.jsx";
import { useRecordName } from "../../shared/hooks/useRecordName.ts";

export function ApiTestRunForm({ collectionId }) {
  const [form, setForm] = useState({
    name: "",
    llm_profile_id: "",
    coverage_mode: "track",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const upd = (p) =>
    setForm((f) => ({
      ...f,
      ...p,
    }));
  const collectionName = useRecordName(apiCollectionsApi.getApiCollection, collectionId);
  useEffect(() => {
    settingsApi
      .listLLMProfiles()
      .then((p) => setProfiles(p || []))
      .catch((e) => setError(e.message));
  }, []);
  const onSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name: form.name.trim() || null,
        llm_profile_id: form.llm_profile_id ? +form.llm_profile_id : null,
        coverage_mode: form.coverage_mode,
      };
      const run = await apiCollectionsApi.createApiRun(collectionId, payload);
      nav(`#/api-runs/${run.id}/status`);
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
            <Breadcrumbs
              items={[
                { label: "APIs", href: "#/apis" },
                { label: collectionName || "API collection", href: `#/apis/${collectionId}` },
                { label: "New test run" },
              ]}
            />
          </>
        }
      />
      <div className="content scroll-content">
        <form
          className="card"
          style={{
            maxWidth: 560,
          }}
          onSubmit={onSubmit}
        >
          <div className="form-section-title">New API test run</div>
          <div className="field">
            <label>
              Name <span className="subtle">(optional — auto-generated if blank)</span>
            </label>
            <input
              type="text"
              value={form.name}
              onInput={(e) =>
                upd({
                  name: e.target.value,
                })
              }
              placeholder="e.g. Sprint 12 auth test"
            />
          </div>
          <div className="field">
            <label>LLM profile</label>
            <select
              value={form.llm_profile_id}
              onChange={(e) =>
                upd({
                  llm_profile_id: e.target.value,
                })
              }
            >
              <option value="">— Use global active profile —</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Scan mode</label>
            <select
              value={form.coverage_mode}
              onChange={(e) =>
                upd({
                  coverage_mode: e.target.value,
                })
              }
            >
              <optgroup label="Scan depth">
                <option value="track">Quick — adaptive scan with coverage tracking</option>
                <option value="standard">Standard — meet the configured coverage target</option>
                <option value="enforce">Full — run every applicable test</option>
              </optgroup>
              <optgroup label="Other">
                <option value="sast_validate">
                  Check SAST leads only — test only imported SAST leads
                </option>
              </optgroup>
            </select>
          </div>
          {error && (
            <div className="alert error form-error" role="alert">
              {error}
            </div>
          )}
          <div
            className="row spread"
            style={{
              marginTop: 16,
            }}
          >
            <button
              type="button"
              className="btn ghost"
              onClick={() => nav(`#/apis/${collectionId}`)}
            >
              Cancel
            </button>
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Creating…" : "Create run"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
