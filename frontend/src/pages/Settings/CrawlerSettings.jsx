import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";

export function CrawlerSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setForm(await api.getCrawlerConfig());
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);

  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.upsertCrawlerConfig({
        js_endpoint_discovery_enabled: !!form.js_endpoint_discovery_enabled
      });
      setForm(updated);
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
        <div className="form-section-title">Crawler</div>
        <label className="toggle-row">
          <input type="checkbox" checked={!!form.js_endpoint_discovery_enabled} onChange={e => {
          setSaved(false);
          setForm(f => ({
            ...f,
            js_endpoint_discovery_enabled: e.target.checked
          }));
        }} />
          <span>Proactively add JavaScript-discovered endpoints to scope</span>
        </label>
        <div className="divider" />
        <div className="row spread">
          <div>{saved && <span className="save-confirm"><IconCheck /> Saved</span>}</div>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : "Save Crawler Settings"}</button>
        </div>
      </form>}
  </>;
}
