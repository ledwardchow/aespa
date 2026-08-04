import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";

const BYTES_PER_MIB = 1024 * 1024;

function toForm(config) {
  return {
    ...config,
    max_source_mib: Math.round(config.max_source_bytes / BYTES_PER_MIB)
  };
}

function toPayload(form) {
  return {
    max_tool_calls: Number(form.max_tool_calls),
    max_source_files: Number(form.max_source_files),
    max_source_bytes: Number(form.max_source_mib) * BYTES_PER_MIB,
    max_facts: Number(form.max_facts),
    max_concurrent: Number(form.max_concurrent)
  };
}

export function ComponentMapperSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setForm(toForm(await api.getComponentMapperConfig()));
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);

  const update = patch => {
    setSaved(false);
    setForm(current => ({ ...current, ...patch }));
  };

  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.upsertComponentMapperConfig(toPayload(form));
      setForm(toForm(updated));
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return <>
    {!form && !error && <div className="subtle">Loading…</div>}
    {error && <div className="alert error">{error}</div>}
    {form && <form className="card" onSubmit={onSubmit}>
      <div className="form-section-title">Component Mapper</div>
      <div className="field-hint" style={{ marginBottom: 16 }}>
        Controls the bounded LLM agent that discovers inbound and outbound interfaces
        during campaign correlation. The selected model is configured in the
        Component Mapper role under LLM Profiles.
      </div>

      <div className="form-section-title">Execution Budget</div>
      <div className="two-col">
        <div className="field">
          <label htmlFor="mapper-max-tool-calls">Maximum tool calls per component</label>
          <input id="mapper-max-tool-calls" type="number" min="1" max="1000"
            value={form.max_tool_calls}
            onChange={e => update({ max_tool_calls: Number(e.target.value) })} />
          <div className="field-hint">
            Includes file listing, search, reads, and fact recording. Default: 120.
          </div>
        </div>
        <div className="field">
          <label htmlFor="mapper-max-concurrent">Concurrent component mappings</label>
          <input id="mapper-max-concurrent" type="number" min="1" max="32"
            value={form.max_concurrent}
            onChange={e => update({ max_concurrent: Number(e.target.value) })} />
          <div className="field-hint">
            Lower this for rate-limited providers. Default: 4.
          </div>
        </div>
      </div>

      <div className="form-section-title">Source and Fact Limits</div>
      <div className="two-col">
        <div className="field">
          <label htmlFor="mapper-max-source-files">Maximum source files per component</label>
          <input id="mapper-max-source-files" type="number" min="1" max="10000"
            value={form.max_source_files}
            onChange={e => update({ max_source_files: Number(e.target.value) })} />
          <div className="field-hint">
            Limits distinct files returned as mapper evidence. Default: 500.
          </div>
        </div>
        <div className="field">
          <label htmlFor="mapper-max-source-mib">Maximum source returned (MiB)</label>
          <input id="mapper-max-source-mib" type="number" min="1" max="250"
            value={form.max_source_mib}
            onChange={e => update({ max_source_mib: Number(e.target.value) })} />
          <div className="field-hint">
            Limits source bytes returned by read tools. Default: 50 MiB.
          </div>
        </div>
        <div className="field">
          <label htmlFor="mapper-max-facts">Maximum accepted interface facts</label>
          <input id="mapper-max-facts" type="number" min="1" max="1000"
            value={form.max_facts}
            onChange={e => update({ max_facts: Number(e.target.value) })} />
          <div className="field-hint">
            Facts are retained only when their evidence is validated. Default: 200.
          </div>
        </div>
      </div>

      <div className="form-row">
        <button type="submit" className="btn" disabled={saving}>
          {saving ? "Saving…" : "Save Component Mapper Settings"}
        </button>
        {saved && <span className="saved-indicator"><IconCheck /> Saved</span>}
      </div>
    </form>}
  </>;
}
