import { useState } from "react";
import { saveBenchmarkSettings } from "../../shared/api/benchmarkLab.js";

export function BenchmarkModelSettings({ models, settings, onChange }) {
  const [modelId, setModelId] = useState(String(settings?.default_model_id || ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await saveBenchmarkSettings({ default_model_id: Number(modelId) });
      await onChange();
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="card" onSubmit={save}>
      <h2 className="form-section-title">Benchmark model</h2>
      <div className="policy-section-copy">Used for all new benchmark runs.</div>
      <label className="field">
        Default benchmark model
        <select
          className="select"
          value={modelId}
          disabled={busy}
          onChange={(event) => {
            setModelId(event.target.value);
            setSaved(false);
          }}
        >
          <option value="">Choose a model...</option>
          {models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name}
            </option>
          ))}
        </select>
      </label>
      <div className="form-actions">
        <button className="btn primary" disabled={busy || !modelId}>
          {busy ? "Saving..." : "Save benchmark model"}
        </button>
        {saved && (
          <span className="field-hint" role="status">
            Benchmark model saved.
          </span>
        )}
      </div>
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
