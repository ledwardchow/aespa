import { useEffect, useState } from "react";
import { IconCheck } from "../../components/Icons";
import { api } from "../../lib/api";

const ROLE_OPTIONS = [
  ["alice", "A.L.I.C.E."],
  ["specialist", "Specialist agents"],
  ["test_lead", "Test Lead (web and API)"],
];

export function CodeExecutionSettings() {
  const [form, setForm] = useState(null);
  const [runtime, setRuntime] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  const refresh = async () => {
    const [config, status] = await Promise.all([
      api.getCodeExecutionConfig(),
      api.getCodeExecutionStatus(),
    ]);
    setForm(config);
    setRuntime(status);
  };

  useEffect(() => {
    refresh().catch(e => setError(e.message));
  }, []);

  const update = values => {
    setSaved(false);
    setForm(current => ({ ...current, ...values }));
  };

  const save = async event => {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const payload = {
        ...form,
        timeout_s: Number(form.timeout_s),
        memory_mb: Number(form.memory_mb),
        cpu_cores: Number(form.cpu_cores),
        pids_limit: Number(form.pids_limit),
        workspace_mb: Number(form.workspace_mb),
        output_limit_bytes: Number(form.output_limit_bytes),
        artifact_limit_bytes: Number(form.artifact_limit_bytes),
        max_requests_per_execution: Number(form.max_requests_per_execution),
        max_concurrent_requests: Number(form.max_concurrent_requests),
        max_concurrent_executions: Number(form.max_concurrent_executions),
      };
      delete payload.updated_at;
      await api.upsertCodeExecutionConfig(payload);
      await refresh();
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!form) return <div className="subtle">Loading sandbox settings…</div>;
  return <form className="card" onSubmit={save}>
    <section className="policy-group">
      <div className="form-section-title">Sandboxed Python execution</div>
      <div className="policy-section-copy">
        Let selected agents write short Python programs for unusual parsing, payload generation, and bounded workflows. Code runs in a locked-down Docker container with no network. Target requests must use the AESPA runtime API and appear in the Traffic Log.
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className={"alert " + (runtime?.available ? "success" : "warning")}>
        <strong>{runtime?.available ? "Runtime ready" : "Runtime unavailable"}</strong>
        <div>{runtime?.message || "Checking Docker runtime…"}</div>
        {!runtime?.image_present && runtime?.docker_installed && <div className="field-hint">Build it with: <code>docker build -t {form.image_ref} runtime/python-executor</code></div>}
      </div>
      <label className="toggle-row">
        <input type="checkbox" checked={form.enabled} onChange={e => update({ enabled: e.target.checked })} />
        <span>Enable sandboxed Python for agent tools</span>
      </label>
      <label className="toggle-row">
        <input type="checkbox" checked={form.retain_redacted_source} onChange={e => update({ retain_redacted_source: e.target.checked })} />
        <span>Retain redacted source code in the execution audit trail</span>
      </label>
    </section>

    <section className="policy-group">
      <div className="form-section-title">Allowed agents</div>
      <div className="policy-section-copy">A.L.I.C.E., specialists, and Test Leads are enabled by default when the sandbox feature is turned on.</div>
      {ROLE_OPTIONS.map(([value, label]) => <label className="toggle-row" key={value}>
        <input type="checkbox" checked={form.allowed_roles.includes(value)} onChange={e => update({
          allowed_roles: e.target.checked
            ? [...new Set([...form.allowed_roles, value])]
            : form.allowed_roles.filter(role => role !== value),
        })} />
        <span>{label}</span>
      </label>)}
    </section>

    <section className="policy-group">
      <div className="form-section-title">Runtime limits</div>
      <div className="two-col">
        <div className="field"><label htmlFor="code-image">Docker image</label><input id="code-image" value={form.image_ref} onChange={e => update({ image_ref: e.target.value })} /></div>
        <div className="field"><label htmlFor="code-timeout">Timeout (seconds)</label><input id="code-timeout" type="number" min="1" max="60" value={form.timeout_s} onChange={e => update({ timeout_s: e.target.value })} /></div>
        <div className="field"><label htmlFor="code-memory">Memory (MiB)</label><input id="code-memory" type="number" min="64" max="1024" value={form.memory_mb} onChange={e => update({ memory_mb: e.target.value })} /></div>
        <div className="field"><label htmlFor="code-cpu">CPU cores</label><input id="code-cpu" type="number" min="0.25" max="2" step="0.25" value={form.cpu_cores} onChange={e => update({ cpu_cores: e.target.value })} /></div>
        <div className="field"><label htmlFor="code-requests">Requests per execution</label><input id="code-requests" type="number" min="0" max="100" value={form.max_requests_per_execution} onChange={e => update({ max_requests_per_execution: e.target.value })} /></div>
        <div className="field"><label htmlFor="code-request-concurrency">Concurrent requests</label><input id="code-request-concurrency" type="number" min="1" max="10" value={form.max_concurrent_requests} onChange={e => update({ max_concurrent_requests: e.target.value })} /></div>
        <div className="field"><label htmlFor="code-execution-concurrency">Concurrent executions</label><input id="code-execution-concurrency" type="number" min="1" max="8" value={form.max_concurrent_executions} onChange={e => update({ max_concurrent_executions: e.target.value })} /></div>
        <div className="field"><label htmlFor="code-output">Captured output (bytes)</label><input id="code-output" type="number" min="8192" max="262144" value={form.output_limit_bytes} onChange={e => update({ output_limit_bytes: e.target.value })} /></div>
      </div>
    </section>

    <div className="row">
      <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
      {saved && <span className="save-confirm"><IconCheck /> Saved</span>}
    </div>
  </form>;
}
