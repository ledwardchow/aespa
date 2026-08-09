import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export function ReportingSettings() {
  const [form, setForm] = useState(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => { api.getReportingDebugConfig().then(cfg => setForm(cfg)).catch(e => setError(e.message)); }, []);
  if (!form) return error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>;
  const save = async e => {
    e.preventDefault(); setError(null); setSaved(false); setSaving(true);
    try { setForm(await api.upsertReportingDebugConfig({...form, batch_max_concurrent: Number(form.batch_max_concurrent)})); setSaved(true); }
    catch (err) { setError(err.message); }
    finally { setSaving(false); }
  };
  return <form className="card" onSubmit={save}>
    <div className="form-section-title">Reporting</div>
    <div className="field"><label>Concurrent probe-analysis batches</label>
      <input type="number" min="1" max="8" value={form.batch_max_concurrent} onChange={e => setForm({...form, batch_max_concurrent: Number(e.target.value)})} />
      <div className="field-hint">Final Reporting probe-analysis batches to run in parallel (1–8). Default: 4.</div>
    </div>
    <div className="row" style={{ gap: 12, alignItems: "center" }}>
      <button className="btn" type="submit" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
      {saved && <span className="saved-indicator">Saved</span>}
    </div>
  </form>;
}
