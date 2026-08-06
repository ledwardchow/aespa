import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";

const BYTES_PER_MIB = 1024 * 1024;

function toForm(config) {
  return {
    max_tool_calls: config.max_tool_calls ?? 100,
    max_source_files: config.max_source_files ?? 500,
    max_source_bytes: config.max_source_bytes ?? 50 * BYTES_PER_MIB,
    max_facts: config.max_facts ?? 500,
    max_concurrent: config.max_concurrent ?? 4,
    max_trace_edges: config.max_trace_edges ?? 8,
    max_trace_components: config.max_trace_components ?? 6,
    max_paths_per_lead: config.max_paths_per_lead ?? 10,
    min_trace_confidence: config.min_trace_confidence ?? 0.5,
    max_source_mib: Math.round((config.max_source_bytes ?? 50 * BYTES_PER_MIB) / BYTES_PER_MIB)
  };
}

function toPayload(form) {
  return {
    max_tool_calls: Number(form.max_tool_calls),
    max_source_files: Number(form.max_source_files),
    max_source_bytes: Number(form.max_source_mib) * BYTES_PER_MIB,
    max_facts: Number(form.max_facts),
    max_concurrent: Number(form.max_concurrent),
    max_trace_edges: Number(form.max_trace_edges),
    max_trace_components: Number(form.max_trace_components),
    max_paths_per_lead: Number(form.max_paths_per_lead),
    min_trace_confidence: Number(form.min_trace_confidence)
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
            Includes file listing, search, reads, and fact recording. Default: 100.
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
            Facts are retained only when their evidence is validated. Default: 500.
          </div>
        </div>
      </div>

      <div className="form-section-title">Attack-Path Trace Limits</div>
      <div className="two-col">
        <div className="field">
          <label htmlFor="mapper-max-trace-edges">Maximum trace edges</label>
          <input id="mapper-max-trace-edges" type="number" min="1" max="100"
            value={form.max_trace_edges}
            onChange={e => update({ max_trace_edges: Number(e.target.value) })} />
          <div className="field-hint">
            Bounds directed component and route hops per trace. Default: 8.
          </div>
        </div>
        <div className="field">
          <label htmlFor="mapper-max-trace-components">Maximum trace components</label>
          <input id="mapper-max-trace-components" type="number" min="1" max="50"
            value={form.max_trace_components}
            onChange={e => update({ max_trace_components: Number(e.target.value) })} />
          <div className="field-hint">
            Limits distinct components included in one trace. Default: 6.
          </div>
        </div>
        <div className="field">
          <label htmlFor="mapper-max-paths-per-lead">Maximum paths per lead</label>
          <input id="mapper-max-paths-per-lead" type="number" min="1" max="100"
            value={form.max_paths_per_lead}
            onChange={e => update({ max_paths_per_lead: Number(e.target.value) })} />
          <div className="field-hint">
            Limits alternative attack paths retained for each lead. Default: 10.
          </div>
        </div>
        <div className="field">
          <label htmlFor="mapper-min-trace-confidence">Minimum trace confidence</label>
          <input id="mapper-min-trace-confidence" type="number" min="0" max="1" step="0.01"
            value={form.min_trace_confidence}
            onChange={e => update({ min_trace_confidence: Number(e.target.value) })} />
          <div className="field-hint">
            Discards trace edges below this confidence. Default: 0.50.
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
