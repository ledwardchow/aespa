import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";

export function TestRunForm({
  siteId
}) {
  const [form, setForm] = useState({
    name: "",
    max_depth: 3,
    max_pages: 50,
    llm_profile_id: null
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const upd = p => setForm(f => ({
    ...f,
    ...p
  }));
  useEffect(() => {
    (async () => {
      try {
        const profs = await api.listLLMProfiles();
        setProfiles(profs || []);
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const run = await api.createRun(siteId, {
        name: form.name.trim() || null,
        max_depth: Number(form.max_depth),
        max_pages: Number(form.max_pages),
        llm_profile_id: form.llm_profile_id || null
      });
      nav(`#/runs/${run.id}`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href={`#/sites/${siteId}`} style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>Site</a>
        <span className="breadcrumb-sep"> / </span>New test run
      </div>
    </div>
    <div className="content scroll-content">
      <form className="card" onSubmit={onSubmit}>
        {error && <div className="alert error">{error}</div>}
        <div className="form-section-title">Run Configuration</div>
        <div className="field">
          <label>Name <span className="field-optional">(optional — auto-generated if blank)</span></label>
          <input type="text" value={form.name} placeholder="e.g. Initial crawl" onChange={e => upd({
            name: e.target.value
          })} />
        </div>
        <div className="two-col">
          <div className="field">
            <label>Max depth <span className="field-hint-inline">(1–10)</span></label>
            <input type="number" required min="1" max="10" value={form.max_depth} onChange={e => upd({
              max_depth: e.target.value
            })} />
          </div>
          <div className="field">
            <label>Max pages <span className="field-hint-inline">(5–500)</span></label>
            <input type="number" required min="5" max="500" value={form.max_pages} onChange={e => upd({
              max_pages: e.target.value
            })} />
          </div>
        </div>
        <div className="alert" style={{
          marginTop: 12
        }}>
          This run will use the global scan policy from Settings.
        </div>
        <div className="divider" />
        <div className="form-section-title">LLM Profile</div>
        <div className="field">
          <label>LLM profile <span className="field-optional">(optional — uses the globally active profile if not set)</span></label>
          <select className="select" value={form.llm_profile_id || ""} onChange={e => upd({
            llm_profile_id: e.target.value ? Number(e.target.value) : null
          })}>
            <option value="">— Use global active profile —</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="row spread">
          <button type="button" className="btn ghost" onClick={() => nav(`#/sites/${siteId}`)}>Cancel</button>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Creating…" : "Create run"}</button>
        </div>
      </form>
    </div></>;
}
