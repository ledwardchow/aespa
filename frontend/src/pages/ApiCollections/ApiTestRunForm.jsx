import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";

export function ApiTestRunForm({
  collectionId
}) {
  const [form, setForm] = useState({
    name: "",
    llm_profile_id: "",
    coverage_mode: "track"
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const upd = p => setForm(f => ({
    ...f,
    ...p
  }));
  useEffect(() => {
    api.listLLMProfiles().then(p => setProfiles(p || [])).catch(e => setError(e.message));
  }, []);
  const onSubmit = async e => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name: form.name.trim() || null,
        llm_profile_id: form.llm_profile_id ? +form.llm_profile_id : null,
        coverage_mode: form.coverage_mode
      };
      const run = await api.createApiRun(collectionId, payload);
      nav(`#/api-runs/${run.id}/status`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href={`#/apis/${collectionId}`} style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>API collection</a>
        <span className="breadcrumb-sep"> / </span>New test run
      </div>
    </div>
    <div className="content scroll-content">
      {error && <div className="alert error">{error}</div>}
      <form className="card" style={{
        maxWidth: 560
      }} onSubmit={onSubmit}>
        <div className="form-section-title">New API test run</div>
        <div className="field">
          <label>Name <span className="subtle">(optional — auto-generated if blank)</span></label>
          <input type="text" value={form.name} onInput={e => upd({
            name: e.target.value
          })} placeholder="e.g. Sprint 12 auth test" />
        </div>
        <div className="field">
          <label>LLM profile</label>
          <select value={form.llm_profile_id} onChange={e => upd({
            llm_profile_id: e.target.value
          })}>
            <option value="">— Use global active profile —</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Coverage mode</label>
          <select value={form.coverage_mode} onChange={e => upd({
            coverage_mode: e.target.value
          })}>
            <option value="track">Track — record coverage but don't enforce it</option>
            <option value="enforce">Enforce — block completion until all endpoints covered</option>
          </select>
        </div>
        <div className="row spread" style={{
          marginTop: 16
        }}>
          <button type="button" className="btn ghost" onClick={() => nav(`#/apis/${collectionId}`)}>Cancel</button>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Creating…" : "Create run"}</button>
        </div>
      </form>
    </div></>;
}
