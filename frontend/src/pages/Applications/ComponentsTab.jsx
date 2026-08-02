import { useState, useRef } from "react";
import { useComponents } from "./useComponents";
import { EmptyState } from "../../components/EmptyState";
import { IconPlus } from "../../components/Icons";
import { fmtDate } from "../../lib/utilities";
import { formatBytes, shortHash } from "./_helpers";

// ── ComponentsTab ────────────────────────────────────────────────────────────
// Cards for each code component: role, latest snapshot filename/hash/date,
// older saved versions, plus create/edit/delete and multi-ZIP upload.

export function ComponentsTab({ applicationId, onChanged }) {
  const {
    components, error, setError,
    snapshotsByComponent, loadSnapshotHistory,
    createComponent, updateComponent, deleteComponent,
    uploadSnapshot, deleteSnapshot
  } = useComponents(applicationId, onChanged);
  const [creating, setCreating] = useState(false);

  return <div>
    {error && <div className="alert error" style={{ marginBottom: 16 }}>{error}</div>}
    <div className="row spread" style={{ marginBottom: 14 }}>
      <div className="form-section-title" style={{ margin: 0, border: "none", padding: 0 }}>Code components</div>
      <button className="btn secondary sm" onClick={() => setCreating(c => !c)}><IconPlus /> Add component</button>
    </div>
    {creating && <NewComponentForm
      onCancel={() => setCreating(false)}
      onCreate={async body => { await createComponent(body).catch(e => setError(e.message)); setCreating(false); }}
    />}
    {components === null && <div className="subtle">Loading…</div>}
    {components !== null && components.length === 0 && !creating && <EmptyState
      title="No code components yet"
      sub="Add a component for each repository or micro-frontend that makes up this application, then upload its ZIP snapshot."
      action={<button className="btn" onClick={() => setCreating(true)}><IconPlus /> Add component</button>} />}
    {components && components.length > 0 && <div className="app-component-grid">
      {components.map(c => <ComponentCard
        key={c.id}
        component={c}
        snapshots={snapshotsByComponent[c.id]}
        onExpandHistory={() => loadSnapshotHistory(c.id)}
        onUpdate={body => updateComponent(c.id, body).catch(e => setError(e.message))}
        onDelete={() => {
          if (!confirm(`Delete component "${c.name}"? This removes all of its snapshots and cannot be undone.`)) return;
          deleteComponent(c.id).catch(e => setError(e.status === 409 ? `Cannot delete "${c.name}" — it is still referenced by a campaign.` : e.message));
        }}
        onUpload={file => uploadSnapshot(c.id, file).catch(e => setError(e.message))}
        onDeleteSnapshot={snapshotId => deleteSnapshot(c.id, snapshotId).catch(e => setError(e.status === 409 ? "Cannot delete this snapshot — a campaign still references it." : e.message))}
      />)}
    </div>}
  </div>;
}

function NewComponentForm({ onCancel, onCreate }) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async e => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    await onCreate({ name: name.trim(), role: role.trim() || null, description: description.trim() || null });
    setSaving(false);
  };

  return <form className="card" style={{ marginBottom: 14, maxWidth: 480 }} onSubmit={submit}>
    <div className="field">
      <label>Component name <span className="field-required">*</span></label>
      <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. checkout-ui" autoFocus />
    </div>
    <div className="field">
      <label>Role <span className="subtle">(optional)</span></label>
      <input type="text" value={role} onChange={e => setRole(e.target.value)} placeholder="e.g. Micro-frontend, Backend API" />
    </div>
    <div className="field">
      <label>Description <span className="subtle">(optional)</span></label>
      <textarea rows={2} value={description} onChange={e => setDescription(e.target.value)} />
    </div>
    <div className="row spread">
      <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
      <button type="submit" className="btn" disabled={saving || !name.trim()}>{saving ? "Adding…" : "Add component"}</button>
    </div>
  </form>;
}

function ComponentCard({ component, snapshots, onExpandHistory, onUpdate, onDelete, onUpload, onDeleteSnapshot }) {
  const [editing, setEditing] = useState(false);
  const [role, setRole] = useState(component.role || "");
  const [description, setDescription] = useState(component.description || "");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const toggleHistory = () => {
    if (!historyOpen) onExpandHistory();
    setHistoryOpen(o => !o);
  };

  const onFileChosen = async e => {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try { await onUpload(file); } finally { setUploading(false); }
  };

  const saveEdit = async () => {
    await onUpdate({ role: role.trim() || null, description: description.trim() || null });
    setEditing(false);
  };

  const latest = component.latest_snapshot;

  return <div className="card app-component-card">
    <div className="row spread" style={{ alignItems: "flex-start" }}>
      <div>
        <div style={{ fontWeight: 700, fontSize: 14 }}>{component.name}</div>
        {component.role && !editing && <div className="subtle" style={{ fontSize: 12 }}>{component.role}</div>}
      </div>
      <button className="btn ghost sm" onClick={() => setEditing(e => !e)}>{editing ? "Close" : "Edit"}</button>
    </div>

    {editing ? <div className="field" style={{ marginTop: 8 }}>
      <label>Role</label>
      <input type="text" value={role} onChange={e => setRole(e.target.value)} />
      <label style={{ marginTop: 6 }}>Description</label>
      <textarea rows={2} value={description} onChange={e => setDescription(e.target.value)} />
      <div className="row spread" style={{ marginTop: 6 }}>
        <button className="btn danger-outline sm" onClick={onDelete}>Delete component</button>
        <button className="btn sm" onClick={saveEdit}>Save</button>
      </div>
    </div> : <>
      {component.description && <div className="subtle" style={{ fontSize: 12, marginTop: 6 }}>{component.description}</div>}
      <div className="app-snapshot-summary">
        {latest ? <>
          <div className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{latest.filename}</div>
          <div className="subtle" style={{ fontSize: 11 }}>
            SHA {shortHash(latest.sha256)} · {formatBytes(latest.size_bytes)} · {fmtDate(latest.created_at)} · latest
          </div>
        </> : <div className="subtle" style={{ fontSize: 12 }}>No snapshot uploaded yet</div>}
      </div>
      <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: "wrap" }}>
        <input ref={fileRef} type="file" accept=".zip" style={{ display: "none" }} onChange={onFileChosen} />
        <button className="btn secondary sm" disabled={uploading} onClick={() => fileRef.current && fileRef.current.click()}>
          {uploading ? "Uploading…" : "Upload new version"}
        </button>
        {component.snapshot_count > 0 && <button className="btn ghost sm" onClick={toggleHistory}>
          {historyOpen ? "Hide" : "Show"} version history ({component.snapshot_count})
        </button>}
      </div>
      {historyOpen && <div className="app-snapshot-history">
        {snapshots === undefined && <div className="subtle" style={{ fontSize: 12 }}>Loading…</div>}
        {snapshots && snapshots.map(s => <div key={s.id} className="app-snapshot-row">
          <div>
            <div className="mono" style={{ fontSize: 12 }}>{s.filename}</div>
            <div className="subtle" style={{ fontSize: 11 }}>SHA {shortHash(s.sha256)} · {formatBytes(s.size_bytes)} · {fmtDate(s.created_at)}</div>
          </div>
          <button className="btn danger-outline sm" onClick={() => onDeleteSnapshot(s.id)}>Delete</button>
        </div>)}
        {snapshots && snapshots.length === 0 && <div className="subtle" style={{ fontSize: 12 }}>No snapshots.</div>}
      </div>}
    </>}
  </div>;
}
