import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";

export function ApiCollectionForm({
  collectionId
}) {
  const isEdit = typeof collectionId === "number";
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    description: ""
  });
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const d = await api.getApiCollection(collectionId);
        setForm({
          name: d.name,
          base_url: d.base_url,
          description: d.description || ""
        });
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [isEdit, collectionId]);
  const upd = p => setForm(f => ({
    ...f,
    ...p
  }));
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      base_url: form.base_url.trim(),
      description: form.description.trim() || null
    };
    try {
      if (isEdit) {
        await api.updateApiCollection(collectionId, payload);
        nav(`#/apis/${collectionId}`);
      } else {
        const c = await api.createApiCollection(payload);
        nav(`#/apis/${c.id}`);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const bc = isEdit ? <><a href={`#/apis/${collectionId}`} style={{
      color: "var(--muted)",
      fontWeight: 400
    }}>{form.name || "API collection"}</a><span className="breadcrumb-sep"> / </span>Edit</> : <><a href="#/apis" style={{
      color: "var(--muted)",
      fontWeight: 400
    }}>APIs</a><span className="breadcrumb-sep"> / </span>New API collection</>;
  return <>
    <div className="topbar"><div className="topbar-title">{bc}</div></div>
    <div className="content scroll-content">
      {loading && <div className="subtle">Loading…</div>}
      {!loading && <form className="card" onSubmit={onSubmit}>
          {error && <div className="alert error">{error}</div>}
          <div className="form-section-title">API collection</div>
          <div className="field"><label>Name</label>
            <input type="text" required value={form.name} placeholder="e.g. Payments API" onChange={e => upd({
            name: e.target.value
          })} /></div>
          <div className="field"><label>Base URL</label>
            <input type="url" required value={form.base_url} placeholder="https://api.example.com" onChange={e => upd({
            base_url: e.target.value
          })} /></div>
          <div className="field"><label>Description (optional)</label>
            <textarea value={form.description} placeholder="What these APIs do, scope, contacts…" onChange={e => upd({
            description: e.target.value
          })} /></div>
          <div className="divider" />
          <div className="row spread">
            <button type="button" className="btn ghost" onClick={() => isEdit ? nav(`#/apis/${collectionId}`) : nav("#/apis")}>Cancel</button>
            <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : isEdit ? "Save changes" : "Create collection"}</button>
          </div>
        </form>}
    </div></>;
}
