import { useEffect, useState } from "react";
import * as settingsApi from "../../shared/api/settings.js";
import { IconCheck } from "../../shared/ui/Icons.jsx";

const DEFAULTS = {
  max_concurrent_workers: 6,
  max_tasks: 200,
  max_steps_per_task: 30,
  include_sast_leads: true,
  include_recon_checks: true,
};

export function DeepScanSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    settingsApi
      .getDeepScanConfig()
      .then((data) => setForm({ ...DEFAULTS, ...data }))
      .catch((requestError) => setError(requestError.message));
  }, []);

  const update = (patch) => {
    setSaved(false);
    setForm((current) => ({ ...current, ...patch }));
  };
  const save = async (event) => {
    event.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const savedConfig = await settingsApi.upsertDeepScanConfig({
        ...form,
        max_concurrent_workers: Number(form.max_concurrent_workers),
        max_tasks: Number(form.max_tasks),
        max_steps_per_task: Number(form.max_steps_per_task),
      });
      setForm({ ...DEFAULTS, ...savedConfig });
      setSaved(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {!form && !error && <div className="subtle">Loading…</div>}
      {error && <div className="alert error">{error}</div>}
      {form && (
        <form className="card" onSubmit={save}>
          <div className="form-section-title">Deep web scan</div>
          <div className="field-hint" style={{ marginBottom: 12 }}>
            These settings apply only when a web run uses Deep mode. Quick, Standard, Full, and SAST
            Validate keep their existing behaviour.
          </div>
          <div className="form-section-title">Concurrency &amp; Budget</div>
          <div className="field">
            <label htmlFor="deep-workers">Concurrent attack workers</label>
            <input
              id="deep-workers"
              type="number"
              min="1"
              max="20"
              value={form.max_concurrent_workers}
              onChange={(event) => update({ max_concurrent_workers: Number(event.target.value) })}
            />
            <div className="field-hint">
              Maximum number of queued tasks tested at the same time.
            </div>
          </div>
          <div className="field">
            <label htmlFor="deep-tasks">Maximum queued tasks</label>
            <input
              id="deep-tasks"
              type="number"
              min="1"
              max="1000"
              value={form.max_tasks}
              onChange={(event) => update({ max_tasks: Number(event.target.value) })}
            />
            <div className="field-hint">Limits the saved Deep work queue for each run.</div>
          </div>
          <div className="field">
            <label htmlFor="deep-steps">Maximum steps per task</label>
            <input
              id="deep-steps"
              type="number"
              min="1"
              max="200"
              value={form.max_steps_per_task}
              onChange={(event) => update({ max_steps_per_task: Number(event.target.value) })}
            />
            <div className="field-hint">Step budget available to each Deep attack worker.</div>
          </div>
          <div className="form-section-title">Task Sources</div>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.include_recon_checks}
              onChange={(event) => update({ include_recon_checks: event.target.checked })}
            />
            <span>Generate route, CORS, component, and workflow recon tasks</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.include_sast_leads}
              onChange={(event) => update({ include_sast_leads: event.target.checked })}
            />
            <span>Queue imported SAST leads for live validation</span>
          </label>
          <div className="divider" />
          <div className="row spread">
            <div>
              {saved && (
                <span className="save-confirm">
                  <IconCheck /> Saved
                </span>
              )}
            </div>
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Saving…" : "Save Deep Scan Settings"}
            </button>
          </div>
        </form>
      )}
    </>
  );
}
