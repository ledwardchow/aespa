import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";

// ── ApplicationForm ──────────────────────────────────────────────────────────
// Create or edit an Application's name/description. Everything else (code
// components, live targets, hints, campaigns) is managed from ApplicationDetail.

export function ApplicationForm({ applicationId }) {
  const editing = applicationId != null;
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!editing) return;
    api.getApplication(applicationId).then(a => {
      setName(a.name || "");
      setDescription(a.description || "");
      setLoading(false);
    }).catch(e => { setError(e.message); setLoading(false); });
  }, [applicationId, editing]);

  const onSubmit = async e => {
    e.preventDefault();
    if (!name.trim()) { setError("Name is required."); return; }
    setSaving(true);
    setError(null);
    try {
      const body = { name: name.trim(), description: description.trim() || null };
      const app = editing ? await api.updateApplication(applicationId, body) : await api.createApplication(body);
      nav(`#/applications/${app.id}`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };

  if (loading) return <div className="content scroll-content"><div className="subtle">Loading…</div></div>;

  return <>
    <PageHeader title={<><Crumb href="#/applications">Applications</Crumb><Sep />{editing ? "Edit application" : "New application"}</>} />
    <div className="content scroll-content">
      <form className="card" style={{ maxWidth: 560 }} onSubmit={onSubmit}>
        <div className="form-section-title">{editing ? "Edit application" : "New application"}</div>
        {error && <div className="alert error">{error}</div>}
        <div className="field">
          <label>Name <span className="field-required">*</span></label>
          <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Acme Customer Portal" autoFocus />
        </div>
        <div className="field">
          <label>Description <span className="subtle">(optional)</span></label>
          <textarea rows={3} value={description} onChange={e => setDescription(e.target.value)} placeholder="What this application is and how its parts fit together." />
        </div>
        <div className="row spread" style={{ marginTop: 16 }}>
          <button type="button" className="btn ghost" onClick={() => nav(editing ? `#/applications/${applicationId}` : "#/applications")}>Cancel</button>
          <button type="submit" className="btn" disabled={saving || !name.trim()}>{saving ? "Saving…" : editing ? "Save" : "Create application"}</button>
        </div>
      </form>
    </div>
  </>;
}
