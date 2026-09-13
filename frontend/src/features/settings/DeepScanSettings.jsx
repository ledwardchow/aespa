import { useEffect, useState } from "react";
import * as settingsApi from "../../shared/api/settings.js";
import { IconCheck } from "../../shared/ui/Icons.jsx";

const DEFAULTS = {
  max_concurrent_workers: 6,
  max_concurrent_planners: 4,
  max_tasks: 200,
  max_steps_per_task: 30,
  initial_variants_per_campaign: 2,
  max_variants_per_campaign: 4,
  max_total_variants: 400,
  adaptive_follow_up: true,
  minimum_signal_strength: 2,
  reuse_captured_baselines: true,
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
        max_concurrent_planners: Number(form.max_concurrent_planners),
        max_tasks: Number(form.max_tasks),
        max_steps_per_task: Number(form.max_steps_per_task),
        initial_variants_per_campaign: Number(form.initial_variants_per_campaign),
        max_variants_per_campaign: Number(form.max_variants_per_campaign),
        max_total_variants: Number(form.max_total_variants),
        minimum_signal_strength: Number(form.minimum_signal_strength),
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
              Maximum number of execution variants tested at the same time.
            </div>
          </div>
          <div className="field">
            <label htmlFor="deep-planners">Concurrent planner calls</label>
            <input
              id="deep-planners"
              type="number"
              min="1"
              max="20"
              value={form.max_concurrent_planners}
              onChange={(event) =>
                update({ max_concurrent_planners: Number(event.target.value) })
              }
            />
            <div className="field-hint">
              Plans independent testers in parallel. Provider request and token limits still apply.
            </div>
          </div>
          <div className="field">
            <label htmlFor="deep-tasks">Maximum queued testers</label>
            <input
              id="deep-tasks"
              type="number"
              min="1"
              max="1000"
              value={form.max_tasks}
              onChange={(event) => update({ max_tasks: Number(event.target.value) })}
            />
            <div className="field-hint">Limits the saved Deep tester queue for each run.</div>
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
          <div className="form-section-title">Tester Variants</div>
          <div className="field">
            <label htmlFor="deep-initial-variants">Initial variants per tester</label>
            <input
              id="deep-initial-variants"
              type="number"
              min="1"
              max="8"
              value={form.initial_variants_per_campaign}
              onChange={(event) =>
                update({ initial_variants_per_campaign: Number(event.target.value) })
              }
            />
            <div className="field-hint">
              Distinct worker purposes planned after the baseline completes.
            </div>
          </div>
          <div className="field">
            <label htmlFor="deep-max-variants">Maximum variants per tester</label>
            <input
              id="deep-max-variants"
              type="number"
              min="1"
              max="12"
              value={form.max_variants_per_campaign}
              onChange={(event) =>
                update({ max_variants_per_campaign: Number(event.target.value) })
              }
            />
            <div className="field-hint">Includes the baseline and any evidence-led follow-up.</div>
          </div>
          <div className="field">
            <label htmlFor="deep-total-variants">Maximum variants per run</label>
            <input
              id="deep-total-variants"
              type="number"
              min="1"
              max="4000"
              value={form.max_total_variants}
              onChange={(event) => update({ max_total_variants: Number(event.target.value) })}
            />
            <div className="field-hint">
              Stops a large route inventory from producing an unbounded worker queue.
            </div>
          </div>
          <div className="field">
            <label htmlFor="deep-signal">Minimum signal for a follow-up</label>
            <select
              id="deep-signal"
              value={form.minimum_signal_strength}
              onChange={(event) => update({ minimum_signal_strength: Number(event.target.value) })}
            >
              <option value={1}>Any new response</option>
              <option value={2}>Error or denial difference</option>
              <option value={3}>Confirmed finding only</option>
            </select>
          </div>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.adaptive_follow_up}
              onChange={(event) => update({ adaptive_follow_up: event.target.checked })}
            />
            <span>Queue a confirmation variant when a worker finds a new signal</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.reuse_captured_baselines}
              onChange={(event) => update({ reuse_captured_baselines: event.target.checked })}
            />
            <span>Reuse matching crawl traffic as the tester baseline</span>
          </label>
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
